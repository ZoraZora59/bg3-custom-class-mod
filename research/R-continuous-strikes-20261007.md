# 连贯出剑：原生费用替换修复

记录日期：2026-10-07（Asia/Shanghai）。本轮修复实现，不调整职业设计数值。本记录区分原版数据、官方说明、源码方案与实际运行证据；尚未取得本轮 Toolkit 或客户端验收。

## 根因与旧测试边界

修复前，生成器将后续出剑写为 `ModifyUseCosts(Replace,ActionPoint,1,0,ESC_SwordOpportunity)`。对照原版 `EXTRA_ATTACK_WAR_MAGIC`，`Replace` 的第二参数是替换后的资源，最后一个参数是要被替换的原资源。因此该声明方向反了，不能将原有 `ActionPoint` 费用改成剑术机会。

生产 Lua 曾在 `BeginCast` 仅凭机会池余额与 `ESC_EXTRA_ATTACK` 状态推断 `usedOpportunity`，再在 `FinishCast` 决定是否补充机会。这个推断不能证明引擎实际支付了哪种资源。旧 `test_one_full_sword_action_opportunities_never_refill_bonus_offhand_or_internal_hits` 在镜像中手动调用 `spendResource(...,1)` 扣机会，直接假定原生费用替换正确，因而掩盖了声明方向错误。静态解析通过也不能证明资源替换的运行行为。

修复前证据位于 `scripts/generate-sword-cultivator.py` 的额外攻击状态生成、生产 `Runtime.lua` 的 `BeginCast`／`FinishCast`，以及 `scripts/tests/test_esc_bridge.py` 的上述测试。旧副本保存在 `build/sword-cultivator/continuous-strikes-20261007/originals/`；当前源码已完成下述修复。

## 已核对的原版模式

| 原版入口 | 直接观察到的声明 | 对本轮的意义 |
|---|---|---|
| `PassiveData ExtraAttack` | `StatsFunctorContext = OnCast;OnStatusRemoved;OnStatusApplied`；`OnCast` 条件检查 `ExtraAttackSpellCheck()`、`HasUseCosts('ActionPoint',true)` 与回合制，随后进入额外攻击状态队列。 | 额外攻击由实际支付动作的首招启动；照搬全体原版武器攻击匹配会超出剑修设计范围。 |
| `EXTRA_ATTACK` | `UnlockSpellVariant(ExtraAttackCheck(),ModifyUseCosts(Replace,ActionPoint,0,0,ActionPoint),ModifyIconGlow(),ModifyTooltipDescription())`；`RemoveEvents = OnSpellCast`。 | 原版用状态修改后续费用，并由原生施法事件结束机会。 |
| `ExtraAttack_2`／`EXTRA_ATTACK_2` | Passive 继承 `ExtraAttack`；状态沿用零动作费用，并在条件移除时衔接下一层额外攻击状态。 | 战士多次攻击有明确的原生续接方式，不能只增加描述中的次数。 |
| `EXTRA_ATTACK_WAR_MAGIC` | `ModifyUseCosts(Replace,BonusActionPoint,1,0,ActionPoint)`。 | 参数方向可由不同资源的原版实例确认：将动作费用替换为一个附赠动作。 |
| `CommonConditions.khn` | `ExtraAttackCheck()` 为 `ExtraAttackSpellCheck() & HasUseCosts('ActionPoint',false)`；`ExtraAttackSpellCheck()` 包含武器、徒手、投掷及若干特例。 | 费用变体匹配使用原技能的动作费用；本职业应使用自己的执行技能清单。 |

本机原版文件：

- `build/sword-reference/Public/Shared/Stats/Generated/Data/Passive.txt:747–755`：`ExtraAttack`。
- `build/sword-reference/Public/Shared/Stats/Generated/Data/Status_BOOST.txt:2687–2699`：`EXTRA_ATTACK`。
- `build/sword-reference/Public/SharedDev/Stats/Generated/Data/Passive.txt:591–599`：`ExtraAttack_2`；`1797–1805`：`WarMagic`。
- `build/sword-reference/Public/SharedDev/Stats/Generated/Data/Status_BOOST.txt:1739–1749`：`EXTRA_ATTACK_2`；`1839–1847`：`EXTRA_ATTACK_WAR_MAGIC`。
- `build/sword-cultivator/native-condition-error-reference/Mods/Shared/Scripts/thoth/helpers/CommonConditions.khn:1312–1318`：原生技能与费用匹配条件。

## 本轮修复方案

`ESC_P_continuous_strikes` 增加原生 `OnCast`。仅当本职业的一次出剑执行技能满足 `HasUseCosts('ActionPoint',true)`、回合制与职业等级条件时，原生 functor 填入当前动作剩余的机会，并施加 `ESC_EXTRA_ATTACK`。该条件检查生效费用，而非读取一张独立扣费收据。后续费用替换为机会资源后，不应再次满足首招的动作费用条件；这项不循环补满的行为仍须实际引擎验证。

| 分支与职业等级 | 每个完整动作总出剑次数 | 首招后填入剩余机会 |
|---|---:|---:|
| 太玄／天倾／血魇5–9级 | 3 | 2 |
| 太玄／天倾／血魇10–12级 | 4 | 3 |
| 行歌5–12级 | 2 | 1 |

1–4级仍为一个动作一次；等级判断使用本职业等级。额外完整动作可启动另一组同级出剑次数；副手附赠出剑、免费协同、反击及呼应不启动整组。

`ESC_SwordOpportunity` 改用 `ReplenishType = Never`，不在回合开始自动获得机会。机会状态的费用变体使用正确方向：

```text
UnlockSpellVariant(<本职业执行技能条件>,ModifyUseCosts(Replace,ESC_SwordOpportunity,1,0,ActionPoint))
```

只替换动作费用，剑元等其他费用仍由原技能支付。条件清单仅纳入本职业 `action = sword` 的实际执行技能；父容器、`bonusOnly`、`continuation` 与 `internal` 不参与。普通武器攻击仍遵循原版职业的额外攻击规则。范围或多段招式整招只支付一次机会；内部命中和续剑不会再次启动机会池。

机会父状态使用原生 `RemoveEvents = OnSpellCast`，在机会池不足一次费用时移除，并通过 `OnRemoveFunctors` 删除所有分组变体状态。Lua 删除 `usedOpportunity` 推断与 `FinishCast` 补池逻辑，只在回合／战斗边界、读取或刷新、倒地／死亡及失去职业等生命周期节点清理过期机会；不能用 Lua 回补或手动扣费模拟替代原生资源支付。

旧存档通过 `nativeContinuous = 1` 标记进行一次性迁移：首次清理旧 Lua 留下的机会，并补齐原生隐藏触发 Passive。已经迁移且状态仍有效的角色加载时保留剩余次数；`TurnStarted`、`LeftCombat`、降级／洗点、机会状态移除与死亡会清理残余。生命周期模拟已覆盖这些边界，实际存档加载与引擎回调顺序仍待客户端验证。

## 官方资料与推断边界

- [Larian 技能教程：UseCosts](https://docs.baldursgate3.game/index.php?title=Making_a_Basic_Spell#UseCosts) 明确 `ActionPoint:1` 消耗一个动作；[职业教程](https://docs.baldursgate3.game/index.php?title=Adding_Classes_and_Subclasses#Defining_Progressions) 演示成长节点的 `ActionResource` 声明。官方教程未给出本轮费用修改器的完整参数表；上文替换方向依据本机原版 `WAR_MAGIC` 声明。
- [Norbyte SE 的 Spell.h](https://github.com/Norbyte/bg3se/blob/main/BG3Extender/GameDefinitions/Components/Spell.h#L72) 定义 `ModifyUseCosts` 的 `Type`、`Resource`、`Expression`、`Level`、`Resource2` 五字段；[Boosts.h](https://github.com/Norbyte/bg3se/blob/main/BG3Extender/GameDefinitions/Components/Boosts.h#L343) 定义 `UnlockSpellVariant` 的条件字符串与修改器数组。它们确认数据结构，不证明本轮实时扣费与时序。
- [Larian UsingSpell](https://docs.baldursgate3.game/index.php?title=UsingSpell) 说明成功施法可为每个目标触发 `CastSpell`，所有目标处理后才触发 `CastedSpell`。本轮采用原生 Passive／Status 事件，不把 Osiris `CastSpell` 的次数当作整招次数，也不依据名称推定它与 `StatsFunctorContext.OnCast` 同步。
- 社区开发者[Khonsu 映射](https://github.com/NellyDevo/Bg3-Khn-Libs/blob/master/Khn.HardcodedConditions.lua#L273) 将第二参数记录为 `applyModifications`。这是不完整开发者映射；`true/false` 的本轮行为还须由生成声明、费用镜像与实际引擎验证共同确认。

## 验证状态

| 本轮检查 | 结果与证据 |
|---|---|
| 源码生成与 Toolkit 源表准备 | 生成 43 个命名技能、312 条本地化；源表准备成功。记录：`build/sword-cultivator/continuous-strikes-20261007/generate.log`、`prepare.log`。 |
| `python scripts/check_mod.py Source` | 0 错误、0 警告；其中 `Source` 为本模块源码目录。 |
| `python scripts/test-sword-cultivator.py` | 176 项测试全部通过，`SourceChangedDuringTests = false`。包含新增原生费用独立模型 9 项及 Runtime 迁移／生命周期 1 项；记录：`build/sword-cultivator/continuous-strikes-20261007/regression.log`。 |
| 原生 StatsParser | 退出码 0；`build/sword-cultivator/continuous-strikes-20261007/stats-check.txt` 为空，未出现 WARN／ERR。 |

新原生费用模型读取实际生成的 `Replace` 参数、技能 selector、补池 functor 与付款时的费用快照，再执行机会消耗及状态移除检查，改善了旧测试手动假定扣费成功的缺口。它仍是独立模型，不能证明真实引擎的资源扣费、Passive 与 Status 事件时序。

生成过程的 `--skip-art` 仍重生了 21 个语义未变的 VFX `.lsf`。本轮已按修复前保存的原始字节恢复，并核对对应原 `.lsx` 哈希；既有护体等未提交修改保持原样。本轮没有执行交付 PAK 的打包或安装。

本轮尚未运行 Toolkit 或正式游戏。仍需实际验证首招、连续机会、耗尽后重新支付动作、额外完整动作、5／10级与行歌次数、近身／御剑换手、剑元费用、失败或取消、范围与多段、回合清理、加载与重置。旧包与历史客户端记录不证明本次修复通过。
