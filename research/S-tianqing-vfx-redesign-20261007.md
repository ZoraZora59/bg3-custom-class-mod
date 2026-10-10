# 天倾巨剑特效重设计：2026-10-07

记录日期：2026-10-07（Asia/Shanghai）。依据用户实际体验反馈编写重设计方案，重新区分垂直落剑、横扫、冲阵和自身恢复。用户要求检查巨剑从天而降的预期并重新设计；本文具体剑数、方位和节奏是本轮方案，尚无用户逐招选择记录。本文的源码描述是重设计开始时的基线审查；方案不是已完成视觉验收的声明。工作只改变表现构形，伤害、费用、选点、范围、目标、豁免、控制、增益、出剑机会和真实结算次数均沿用现有规格。

## 1. 实际源码为何偏横向

| 基线来源 | 已观察的源码事实 | 对画面的限制 |
|---|---|---|
| [效果生成器](../scripts/generate-sword-vfx.py) 的 `projectile`、`branch_projectile` | Common 飞剑源来自 `VFX_Projectiles_Force_MagicMissile_Projectile_01.lsefx`；天倾换成原生双手巨剑模型，三轴倍率 `(2.4,2.4,3.0)`，尾迹倍率 `3.0` | 放大剑体、换模型及染成淡金不改变生成位置和运动方向，不能据此证明目标上空垂落 |
| 同文件 `impact`、`branch_impact` | 基础命中源来自 `VFX_Actions_Cast_WeaponAttack_Target_BladeFlourish_Slash_01.lsefx`；天倾加大挥斩并叠加 Thunderous Smite 冲击波 | 结果主要是横斩与目标局部冲击；冲击波并不包含完整的上空巨剑与下落过程 |
| [资源生成器](../scripts/sword_vfx_resources.py) 的 `_projectile`、Pathfind child | Cast Bone 为 `Dummy_CastFX`，通用轨迹使用 `TrajectoryType=0` 的 Bezier3，候选使用 `TrajectoryType=2` 的 Pathfind；所有天倾御剑共用分支飞行资源 | 基线是人物发射至目标的通用传输，没有为万钧／裂天的目标上空起点另建明确路径 |
| [绑定规则](../scripts/sword_vfx_bindings.py) 的 `spell_vfx_fields` | ranged 子项绑定分支 Projectile，其他伤害子项绑定分支 Impact；`TianjianImpact`、`TiandiStage` 等回到天倾分支，人物 movement 保留原运动呈现 | 分支共享不能保证每招一柄、八个固定方位或每真实段一柄；逐敌命中效果也不能承载整招的巨剑数量 |
| [机制规格](../scripts/sword_cultivator_spec.py) | 用 `area_attack`、`attack`、`leap_area_save`、`self_area_save` 等区分施展机制；天地 `segments=3`，八方 `segments=1` | 机制类型和 Projectile 技术名本身不定义巨剑从哪生成、朝哪运动；效果构形必须单独明确 |
| [Runtime](../mods/EasternSwordCultivator/Source/Mods/EasternSwordCultivator_6560ea02-fe1e-5fdb-8631-b41a2e53af90/ScriptExtender/Lua/Runtime.lua) 的 `StatusApplied`／`ESC_TIANDI_TARGET`（约 1054—1062 行） | 每个目标第一次收到该标记时，立即调用两次 `internal_tiandi_stage`，补上主招之后的两次攻击 | `TiandiStage` 是逐目标伤害 helper，不是全场统一的视觉阶段；绑定完整落剑会随 N 个目标产生 2N 次补段落剑 |

上述事实解释了用户看到的方向偏差，不代替对已安装客户端画面的逐帧记录。旧裂天御剑子项曾施展、命中且没有对应失败，只能作为旧施展链和伤害证据；旧 AllSpark 模型预览、十项编译和安装记录也不能扩展为本轮五种垂落构形通过。

### 用户当前安装包的只读核对

[安装包审查记录](../build/sword-vfx/tianqing-redesign-20261007/installed-audit.json)与[解包回读目录](../build/sword-vfx/tianqing-redesign-20261007/installed-readback)确认当前安装包 PAK SHA256 为 `AB78E073313E93865AC8DDAAF1723FAB83A2521D15112E632D938B33B659E3B5`，`Version64=36028797018963977`，即 `1.0.0.9`。其中天倾现有 `VFX_ESC_Tianqing_Projectile_01.lsfx` 与 `VFX_ESC_Tianqing_Impact_01.lsfx` 均与 Source 精确字节一致。

回读的 `Projectile_ESC_tianqing_lietian_Main` 仍为 Projectile，Trajectories 为 `c9bcde8e-d653-5d63-afcd-3a96050f848a,7ca79282-35da-5293-9d68-32055b6e18d9`，`PositionEffect` 为空，`CastEffect=f573afc5-f018-4a87-a3a9-d1c0fe4e5b0d` 沿用原 Flourish。此审查把用户反馈与已安装的现有资源／绑定关联起来；它是只读包提取和字段核对，未修改安装，也不是审查者新做的实际视觉观察。

## 2. 本轮重设计方案

| 招式 | 运动与数量 | 几何构形与节奏读点 | 保持的机制边界 |
|---|---|---|---|
| 逆锋 | 近身横扫；御剑沿直线贯斩 | 近身厚刃展开扇面，御剑剑尖领着重剑横向贯行；命中沿真实目标分布 | 原 6 米近身扇面／12 米×2 米御剑直线，不改为天降区域 |
| 万钧剑势 | 区域中心上空一柄垂直落剑 | 暗金厚剑在目标区域上空显出完整轮廓，剑尖朝下，竖直压落；地面单一撞击峰值后扩出厚重压场环，逐敌另有小型命中／镇压反馈 | 18 米内选点，原半径 6 米，逐敌一次攻击；不会按敌人数复制巨剑 |
| 裂天一剑 | 单目标上空一柄垂直落剑 | 细长的高位剑身轮廓先给出方向，随后厚刃竖直砸向目标；局部亮峰和破甲裂纹迅速收束 | 近身／18 米御剑都保留原目标资格和攻击规则；无新增范围伤害 |
| 天崩剑啸 | 扇面重斩 | 肩与剑体带动一次沉重横斩，剑啸打开 12 米、90 度扇面；主目标额外局部重击随真实 helper 反馈 | 原扇面与主目标额外伤害；局部额外反馈不再播放整招起势，不改为巨剑齐落 |
| 天锋破阵 | 巨剑锋楔随人物冲阵 | 角色与锋楔沿既有移动路线向前，两侧厚风迹展开；终点承重收势，后续自身强化只留近体标记 | 原 18 米×3 米冲阵，每敌一次，原击退／倒地／削弱和自身强化 |
| 天剑坠世 | 最终落点一柄定点垂落 | 人物保留 Jump／Fly 等原移动；在真正落地攻击段，落点上空一柄剑尖朝下的巨剑坠下，随后形成 9 米放射冲击；6 米余威低亮循环 | 原 24 米选点与移动，9 米落区、6 米周期余威及自身强化；移动和余威不重复生成巨剑 |
| 八方灭阵 | 八个固定方位各一柄同时垂落 | 以施展者为中心，在外圈八个等角方位各布置一柄剑；八柄分别从自己的落点上空同时垂直坠落，撞击尘浪与环形剑势覆盖战场，保留清楚圆形边界 | 原身周半径 18 米，每单位本次一次结算；八柄是视觉构形，不能变成八次攻击或八条可命中路径 |
| 天地剑劫 | 全场统一三个视觉阶段，每阶段一柄垂落 | 主招固定同一选点、同一 9 米区域；阶段索引 1／2／3 各显现一柄、坠落一次、撞击一次，需协调对应的真实结算；逐目标 `TiandiStage` 只留局部命中 | 原 24 米选点，三次逐敌独立攻击，首次命中控制规则不变。单个 bank 不自循环三柄，父容器和逐敌 helper 不再生成整招巨剑；协调逻辑尚未实现 |
| 调息／旧蓄势标识 | 自身聚合回元 | 承重站稳、呼吸与淡金剑气向自身收拢，恢复时短亮 | 现行回元提升已并入调息；保留旧标识兼容，不恢复独立蓄势入口 |
| 逆息回生 | 自身回流疗伤 | 厚重剑气逆卷入体，暖金回流形成一次恢复亮峰 | 原附赠动作、自身治疗、费用和恢复比例 |

八方八点的外圈半径、落剑高度、各剑长短与尘浪亮度均是效果试样参数；八点不替代 18 米圆形结算边界，也不把其间空间解释成不受伤区域。万钧／天地的整招效果在选定区域中心触发，八方在自身中心组织八点，裂天跟随单一目标落点；不让逐敌 HitEffect 决定整招剑数。天剑移动路线由现有动作和机制负责，垂落剑只表现最终落地攻击。

八方当前效果源的八点共用中心 Y 平面，尚未逐点进行真实地面高度采样。源中的触地时点与 bounds 只针对平地模型；坡地、台阶和高低差需要后续地面适配与场景验证，不能把八个理想落点称为已贴合实际地形。

## 3. 时间尺度与触发约束

[本轮效果设计常量](../scripts/tianqing_vfx_design.py) 的首轮试样从 `0.1 秒` Lead In 起步；万钧／裂天／坠世／八方／天地单柄的视觉撞击时点分别为 `0.60／0.72／0.85／0.70／0.80 秒`，各 bank 总时长为该时点再加 `0.85 秒`，模型在撞击后 `0.20—0.45 秒` 退去。这些是未编译效果源的时间尺度，只供制作比较，不是已观察的客户端节奏；最终应跟随原动作 Cast 事件、真实落地事件或统一阶段的实际结算校准，不新增蓄力、扣费等待、攻击间隔或额外伤害时点。模型先给出暗面和剑尖方向，最亮部分留给撞击，余势降亮后让下一次出剑仍可辨认。

天地使用“一全场视觉阶段一柄”的单次 bank，接入需新增统一协调，固定主招落区并以阶段索引 1／2／3 触发。现有 Runtime 对各目标立即发起两次补段，尚无全场统一的三段时间协调，不能把单柄源制作称为同步已经完成。协调须保持每目标三次攻击及首次命中控制规则，不在效果内部另开三次循环，也不把试样总时长写成机制承诺。即使某目标落空，全场阶段仍可有区域落剑构形；成功破甲、控制和局部命中闪光仍随该目标真实结果发生。父容器与选项切换不扣费、不伤敌，也不提前播放落剑。

八方八柄共用一次视觉触发，要求同时下落；不得为追求八个峰值复制伤害结算。万钧、天地在多目标或空区域仍维持同样整招剑数。取消瞄准不应留下落剑，持续余威、状态到期、人物倒地／死亡和连续出剑均需单独检查残留与清理。

## 4. 当前设计文本的冲突与处理

| 来源 | 基线文字 | 本轮处理 |
|---|---|---|
| [逐招规格](../docs/19-skill-specifications-draft.md) 的天地剑劫 | 原为“三把巨剑齐落” | 本轮已同步为“接连坠落”，并链接特效方案、注明新视觉未编译安装。本轮目标为全场统一三个阶段各落一柄，需新增协调；不直接把逐目标 helper 当全场阶段，数值与三次攻击保持 |
| [玩家说明](../docs/21-player-facing-skill-text-draft.md) 的天地剑劫 | “三把巨剑接连坠落，每剑独立进行攻击检定” | 保留这一段义，以真实段触发，具体秒数不承诺 |
| 旧 [特效动作设计](../docs/22-skill-vfx-and-animation.md) 的八方 | “由中心向八方同时扩张” | 本轮改为八个固定方位各一柄从上空同时垂落；外圈压场，身周 18 米一次结算 |
| 万钧／裂天旧说明与旧特效文字 | “剑气镇压”“重斩一敌”“沿单目标方向落下”未明确空间来向 | 本轮明确目标落点上空、剑尖向下、垂直运动。近身／御剑仍遵循原选敌范围，不增加新攻击类型 |
| 玩家说明的独立“蓄势·3级”与[职业总稿](../docs/20-eastern-sword-cultivator-gdd.md) | 玩家草稿仍有独立标题；总稿已明确回元提升并入调息 | 本轮表现遵循已合并入口，旧标识仅保留兼容；不在本次视觉重设计中恢复技能 |

本轮更新特效动作设计与本记录，并将逐招规格中天地剑劫的这一句表现用语同步为“接连坠落”、补充设计链接和当前状态；数值总稿、技能数值与玩家文本均未因本轮视觉重设计改动。历史 44 项首批包数量仍保留在历史验收段；当前命名设计键清单为删去召剑后的 43 项。

## 5. 原生依据、编译门槛与验收状态

实现须用已核对的原生资源字段表达生成位置、模型朝向和向下运动，不以扩大现有 Bezier3 尾迹代替空间构形。本轮依据由设计常量的 `NATIVE_REFERENCES`／`GREAT_SWORD` 与原生资源审查分别记录：

| 原生依据 | 本轮核对的事实 | 可支持的结论与边界 |
|---|---|---|
| Spiritual Weapon `VFX_Spells_Cast_Intent_Summon_TargetSummon_SpiritualWeapon_Root_01.lsefx` 的 Downward Energy 组件，实例 `d1618392-8443-4be9-9808-8009a478625d` | 原生 Offset 为 `(0,13,0)`，Y 键帧在 `0—0.5 秒` 从 `0` 变为 `−10`；Offset 属性 `37b047c1-8fb7-4e7c-9319-58db9da44e77`，模块 `7a790ae7-3b1c-463e-bb1f-5cc14980b78c` | 支持用原生模型位置键帧沿 Y 下落；原生终点并不自动证明自定义剑尖已接地，仍需结合模型尺度和锚点试样 |
| `Target_CallLightning` 的 PositionEffect，原生 MEI `de5e4e60-e2b7-44f4-aca8-c11390b4cc48` | Target pivot，目标骨骼为空，Detach Source／Target 为 true，Keep Rotation 为 true，Orient Direction 为 false，起始 textkey 为 Cast | 支持原生 Target 选点地面效果的附件结构；不能直接推定 Projectile、Shout 或 CreateExplosion helper 支持同一字段和锚点 |
| Thunderous Smite `VFX_Spells_Cast_Paladin_Target_ThunderousSmite_Impact_BodyFX_01.lsefx`，组件 `920ec035-71e5-4d4e-bd5d-920dfde922c6` | 原生寿命通道为 Min `0.6`／Max `0`，实际回退寿命未建立；本轮源显式设为 `0.6／0.6 秒`，并保留 AlignToCamera／AlignToVelocity 设置 | 支持落剑后的原生冲击波组件复用；源寿命与原生通道分别记录，不据原生 Min 值声称固定寿命。圆环实际地面朝向仍待 AllSpark 和场景观察，效果参数不改变范围和伤害 |
| 原生 `WPN_HUM_Greatsword_A_0`，GUID `12f3193c-ce1a-5a69-1bf0-8537b9b606f9`，[资源 bounds 记录](../build/vfx-reference-research/human-weapons.lsx) | Z 范围约 `−1.57971…0.35004446`，长轴为 Z，长侧在 −Z；初始 X 轴旋转／pitch 试用 `−90°`，将该方向朝向 −Y | 不对称 bounds 用于剑尖方向和接地高度的制作试样，不是顶点层面的剑尖核对或实际画面通过；仍需 AllSpark 和场景观察 |
| 原生 SharedDev `MultiEffectInfos/95cfcd2b-fccb-4415-9b6a-c24208bd0f06.mei` 的 Aspect of Elk 条目 | 对应 EffectInfo `a65ce712…`，`Dummy_Root`、StartTextKey Cast、DetachTarget true、Pivot Target | 为八方 Shout CastEffect 的自身附件和事件提供原生参考；只借对应条目的结构，不复制其多项整表叠加，也不据此声称八方地面八点已经验证 |

官方流程仍是 AllSpark 保存源 → Build → Compile Effect 产出 `.lsfx` → Effect resource／MEI／Projectile 登记 → 实际技能绑定 → Game Mode 观察；本轮核对了官方 Part 1／Part 3／Part 4，各阶段分开留证。[官方 VFX Part 1](https://docs.baldursgate3.game/VFX_%E2%80%93_Part_1:_Making_Effects)、[Part 2](https://docs.baldursgate3.game/index.php?title=VFX_%E2%80%93_Part_2:_Creating_Resources)、[Part 3](https://docs.baldursgate3.game/index.php?title=VFX_%E2%80%93_Part_3:_Assigning_and_Testing_Effects)、[Part 4](https://docs.baldursgate3.game/index.php?title=VFX_%E2%80%93_Part_4:_Advanced_Information)、[Projectiles](https://docs.baldursgate3.game/index.php?title=Projectiles)

本机 Toolkit 的 `Glasse.exe` 与 `AllSpark.EffectCompiler.dll` 存在，但官方 Part 1 确认的是 GUI 的 Build → Compile Effect。现有 Divine 工具用于 LSX／LSF 转换，不能作为 `.lsefx` 原生编译器；本轮未找到已验证的无界面 CLI／API，且没有可调用的桌面 UI 能力。因此效果源制作与真正游戏可用的编译／绑定明确分层，不声称已替换当前安装包的游戏特效。

仅有新 `.lsefx`、资源声明或静态检查不启用新绑定；必须先回收相应原生编译产物，确认资源登记对应新构形，再启用。天地还须新增全场视觉阶段协调，未完成时不把完整巨剑直接挂到现有逐目标 `TiandiStage`。当前 Runtime 未为本轮改动。旧已编译资源作为未完成阶段的可用路径，与新设计的完成状态分别记录；裂天仍需核对施展形式与地面锚点，坠世需核对 CreateExplosion 落点的 PositionEffect，八方需核对自身 CastEffect 的地面构形，不能仅填写字段便启用。

| 本轮层次 | 当前记录状态 | 完成所需证据 |
|---|---|---|
| 用户视觉方向与逐招几何 | 用户反馈已记录；逐招方案已编写 | 本文与特效动作设计同步；具体几何不标为用户逐招已确认 |
| 效果源制作与源审查 | 五份可编辑源已生成，9 项新增源检查通过 | 详见第 6 节；源字段与 bounds 检查不代替模型顶点或实际画面验证 |
| 原生编译与资源登记 | 待完成 | 新 `.lsfx` 原生编译日志、回收哈希及对应 Effect／MEI／Projectile 登记 |
| 天地全场视觉阶段协调 | 待实现 | 固定主招落区，阶段索引 1／2／3 各播放一柄；逐目标 helper 只留局部命中，真实结算次数和首次控制不变 |
| Toolkit 垂落视觉 | 待完成 | 万钧／裂天各一柄、坠世落地一柄、八方固定八柄同时落、天地全场每阶段一柄的实际连续画面；检查不同高度、狭窄场景、空区域、多目标、近身／御剑、落空、取消和连续施展 |
| 实际 SE 客户端行为 | 待完成 | 原结算范围／次数与费用保持，helper 不重复／打断整招，余威不重落，状态与结束清理正常 |
| 包与安装／发布 | 由后续明确操作另行记录 | 与验证版本对应的包回读和安装记录；不从设计或旧安装证据推定 |

本轮没有新的垂落视觉通过记录。历史 AllSpark 预览、十项编译、三派命中、第四轮远程失败、暴击告警、最终包与安装证据原样保留在特效动作设计第 1 节；它们的验收范围不因本轮重设计扩大。

## 6. 本轮交付与静态检查

本轮完成检查、逐招重设计方案与五份可编辑效果源。新增[设计常量与接入计划](../scripts/tianqing_vfx_design.py)、[效果源生成器](../scripts/generate-tianqing-vfx.py)、[独立源几何检查](../scripts/tests/test_tianqing_vfx_design.py)及五份 Editor `.lsefx`，并更新原测试入口以发现新检查。五份源的 SHA256 均与[authoring manifest](../build/sword-vfx/tianqing-redesign-20261007/authoring-manifest.json)一致；该清单明确 `scope=authoring-source-and-plan-only`、`compiled=false`、`binding_enabled=false`，没有写入新游戏资源或启用新技能绑定。

| 验证 | 本轮结果 | 证据与含义 |
|---|---|---|
| 完整回归 | 185 项全部通过，Failures 0、Errors 0、Skipped 0；`SourceChangedDuringTests=false` | [完整日志](../build/sword-vfx/tianqing-redesign-20261007/regression.log)、[结构化报告](../build/sword-vfx/tianqing-redesign-20261007/regression-report.json)；证据层为 `static-and-simulated-lua`，不包含客户端视觉 |
| 新增效果源检查 | 9 项全部通过，已包含在上述 185 项中 | 检查源的剑数、八个等角落点、无横向位移、位置模块、朝向／bounds 平地接地试样、碰撞读点、包围范围及未启用绑定；不含逐点地形高度采样，也不是原生效果运行观察 |
| Mod 检查与文档差异检查 | `check_mod` 0 错误、0 警告；`git diff --check` 通过 | [Mod 检查日志](../build/sword-vfx/tianqing-redesign-20261007/check-mod.log)；不把这些检查替代 `.lsefx` 编译 |
| 原有资源与安装连续性 | Source/Public 无字节变化，既有已编译 bank、Stats、MEI 及旧 Editor 源完整未改；当前安装 PAK SHA256 仍为 `AB78E073313E93865AC8DDAAF1723FAB83A2521D15112E632D938B33B659E3B5` | 与[修改前哈希基线](../build/sword-vfx/tianqing-redesign-20261007/before-hashes.json)对照，并只读核对安装；本轮没有替换用户现有游戏效果 |

对照本轮基线，既有文件的改动只有 `scripts/test-sword-cultivator.py`、逐招规格中的天地表现用语及特效动作设计。其余为两个新脚本、新检查文件、本记录和五份新 Editor 效果源。召剑删除、连贯出剑及其他此前改动均按本轮开始时的文件基线保留。

最终源修订后的复测报告时间为 `2026-10-07T04:42:13.374902+00:00`，仍为 185 项通过、0 失败、0 错误，`SourceChangedDuringTests=false`。随后只读复核报告中的 612 项 SourceSHA256 与当前文件全部一致，五份效果源与最终 manifest 哈希全部一致；编译和绑定标记仍为 false。

本轮未重跑 native Stats parser，因为 Public Stats 未改；也未运行 Toolkit 预览、原生效果编译、游戏视觉／SE 客户端测试、交付打包、安装或发布。完成范围是用户所要求的检查与重新设计，以及可继续编辑的效果源；后续仍需原生编译、按施展类型验证地面锚点、实现天地全场视觉阶段协调，并在实际场景验收后才能接入。

最终参数收紧后重新运行完整检查，仍为 185 项通过、0 失败、0 错误，`SourceChangedDuringTests=false`；当前全部源哈希与报告一致。冲击粒子的 Min／Max 寿命已显式固定为 `.6/.6`，不再把原版 Min=.6、Max=0 当作固定寿命证据。八方源及接入计划已明确逐点地形采样未制作，触地检查仅针对锚点 Y 平面。最终[汇总记录](../build/sword-vfx/tianqing-redesign-20261007/summary.json)同时核对五份源清单、Public 完整未变及安装 PAK 未变。
