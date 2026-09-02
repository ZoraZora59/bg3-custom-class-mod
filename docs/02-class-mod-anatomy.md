# 02 · 职业 / 子职业 Mod 的数据结构（anatomy）

> 来源：`research/B-class-mod-anatomy.md`（B）、`research/G-official-docs-browser.md`（G，官方文档浏览器直读）、`research/E-scripting-infra.md`（E）。字段名、文件名保留英文；示例 UUID 仅示意，落地时以你解包的当前版本原版文件为准。

## 1. 一句话模型

```
ClassDescriptions.lsx ──ProgressionTableUUID──▶ Progressions.lsx（同一 TableUUID 的 1..12 级节点）
        │ ParentGuid（子职业指向父职业 UUID）              │ Selectors / Boosts / PassivesAdded
        │                                                  ├─▶ Lists/*.lsx（SpellLists / PassiveLists / SkillLists / AbilityLists）
        │                                                  ├─▶ Stats/Generated/Data/*.txt（Passive / Spell_* / Status_* / Interrupt）
        │                                                  └─▶ SubClasses 子节点（列出子职业 ClassDescription UUID）
        └─▶ Localization/<Lang>/*.xml（DisplayName / Description / ShortName 的 handle）
        └─▶ GUI/Assets/ClassIcons/<Name>.DDS（文件名 = Name）
```

- 职业若没有 **Level 1** 的 Progression 节点，角色创建界面不会显示它 B[5][13]。
- 子职业 = 一条带 `ParentGuid` 的 ClassDescription + 自己的进阶表（`ProgressionType=1`，独立 `TableUUID`）+ 出现在父职业"解锁等级"节点的 `SubClasses` 子节点里 B[1][5][6] G[G4]。
- 多职业进入本职业 = 再加一条 `Level=1`、`IsMulticlass=true`、同 `TableUUID`、新 `UUID` 的 Progression 节点，通常只保留多职业应得的熟练/选择器 B[13][22]（官方文档把这行描述为"在 ClassDescriptions 表下再加一行"，与文件级证据不一致，按 Progressions 属性理解 G[G4] B[4]）。

## 2. 官方 Toolkit 流程（《Adding Classes and Subclasses》，示例 Battlemage）G[G4]

1. UUID Object Editor → 在你的 mod 下新建 **Progressions** 表：每级一行；`Name` 无空格；`UUID` 每行唯一；`TableUUID` 全职业共享（技巧：复制 UUID 到 TableUUID 后右键 "Regenerate Value" 重生成 UUID）；`Level`；`ProgressionType` 0=class / 1=subclass / 2=race。
2. `Boosts` 列分号分隔，例：`ActionResource(SpellSlot,2,1);Proficiency(LightArmor);Proficiency(MartialWeapons)`；`ActionResource(SpellSlot,2,3)` = 两个 3 环法术位。
3. Lists 区新建 **SpellLists**：每行一个列表；法术引用格式 `Type_TechName`（`Target_ShockingGrasp`、`Zone_BurningHands`）。
4. `Selectors` 列：`AddSpells(<ListUUID>)` 全给；`SelectSpells(<ListUUID>,1,0)` 选 1 个、可替换 0 个；`SelectPassives(<PassiveListUUID>,1,Battlestance)` 第三参数是选择器 ID（配合 ProgressionDescriptions 改显示名）；`AllowImprovement=Yes` 该级可选专长（官方示例 4 级）。
5. 子职业：Progressions 新增行，独立 TableUUID，`Level=3`（解锁级），`ProgressionType=1`；再回到父职业第 3 级行的 **SubClasses** 列把它们加进去。
6. **ClassDescriptions** 表：`Name` 同名；`ProgressionTableUUID` = 职业 TableUUID；`DisplayName`/`Description`/`ShortName`（子职业短名，角色面板显示 "Mace Battlemage"）；`PrimaryAbility`、`SpellCastingAbility`；`LearningStrategy` 对 class 一律 `AllChildren`；`MustPrepareSpells`、`CanLearnSpells`；`CharacterCreationPose = 0f07ec6e-4ef0-434e-9a51-1353260ccff8`（所有职业相同）；`BaseHp`（示例 12）、`HPPerLevel`（示例 7）；`CommonHotbarColumns + ClassHotbarColumns + ItemsHotbarColumns = 16`（默认 9/5/2）。子职业行 `ParentUUID` 选父职业，其余列复制父职业。
7. 多职业行：`IsMulticlass = Yes` 的 1 级副本行。
8. 起始装备：Stats Editor 新建 **Equipment** 表（`EQP_CC_Battlemage`，Initial Weapon Set = Melee，列 1/2/3 选物品），填到 ClassDescriptions 的 `ClassEquipment`（只填职业不填子职业）。
9. **ProgressionDescriptions** 表：`SelectorId = Battlestance` + DisplayName/Description，把 "Class Passives" 改成你的叫法。
10. 类图标：300×300 PNG → DDS，文件名 = ClassDescriptions 的 `Name`，放 `Data/Mods/<Mod>/GUI/Assets/ClassIcons/`（+ `AssetsLowRes`），热键栏版在 `ClassIcons/hotbar/`（社区评论称 112×112 B[4]）；`Project > Convert UI Assets…` 自动转 DDS 并生成 metadata。DDS 压缩：RGBA→BC7_UNORM（sRGB 则 BC7_UNORM_SRGB），RGB→BC1_UNORM。
11. 快速测试：加载 `Basic_Level_A` → Game Mode → 悬停头像 `Ctrl+Shift+L` 升级 → Add Class 选新职业；`Ctrl+Shift+F11` 调试台 `addDebugSpell Target_XXX` 测法术；`reloadLoca` 刷新文本 G[G4][G7][G8]。
12. 官方多次提醒：改 ClassDescriptions / ProgressionDescriptions / 依赖后需要**保存并重启 Editor** 才生效。

## 3. 文件级字段速查（手写 lsx 或审阅 Toolkit 产物时用）

### 3.1 `Public/<Mod>/ClassDescriptions/ClassDescriptions.lsx` B[2.2.1] G[G17]

| 属性 | 类型 | 说明 |
|---|---|---|
| `Name` | FixedString | 技术名，无空格；类图标文件名必须与之一致 |
| `UUID` | guid | 职业/子职业唯一 ID；被 `SubClasses/SubClass.Object` 与 `AbilityDistributionPreset.ClassUUID` 引用 |
| `ParentGuid` | guid | 仅子职业：父职业 UUID（原版 Paladin 为 `ff4d9497-023c-434a-bd14-82fc367e991c` B[6]） |
| `ProgressionTableUUID` | guid | = Progressions 里该职业所有节点的 `TableUUID` |
| `DisplayName` / `Description` / `ShortName` | TranslatedString | `handle="h…" version="1"` |
| `PrimaryAbility` / `SpellCastingAbility` | uint8 | **1=STR 2=DEX 3=CON 4=INT 5=WIS 6=CHA**（Community Library 文档 + 原版 Barbarian `PrimaryAbility=1` 佐证；社区 wiki 写的 "1=dex" 与原版数据矛盾）B[13] G[G17] |
| `BaseHp` / `HpPerLevel` | int32 | 1 级 HP / 每级 HP（社区观察实际每级 +1，未经官方确认）B[5] |
| `CanLearnSpells` / `MustPrepareSpells` | bool | 卷轴学法术 / 需准备法术 |
| `LearningStrategy` | uint8 | Toolkit 里选 `AllChildren`，文件里几乎都是 `1`（Archfey Warlock 为 2；语义未确认）B[13] |
| `ClassEquipment` | FixedString | `Equipment.txt` 里的 `new equipment "EQP_CC_…"` 名，只填职业 |
| `CharacterCreationPose` | guid | 固定 `0f07ec6e-4ef0-434e-9a51-1353260ccff8` |
| `SoundClassType` | FixedString | 借用原版职业名（Barbarian / Paladin / Fighter…） |
| `CommonHotbarColumns` / `ClassHotbarColumns` / `ItemsHotbarColumns` | int32 | 之和必须 16（默认 9/5/2） |
| 子节点 `Tags/Object` | guid | 职业标签（见 3.6） |

### 3.2 `Public/<Mod>/Progressions/Progressions.lsx` B[2.2.2]

| 属性 | 说明 |
|---|---|
| `UUID` | 该节点唯一 ID；覆盖原版节点要用相同 UUID，新增合并节点用新 UUID |
| `TableUUID` | 同职业/子职业共享；= ClassDescription 的 `ProgressionTableUUID` |
| `Name` / `Level` / `ProgressionType` | 技术名 / 等级 / 0 class、1 subclass、2 race（bg3.wiki 写种族为 3，属少数说法）B[22] |
| `Boosts` | 分号分隔：`ActionResource(SpellSlot,2,1)`、`ActionResource(Rage,2,0)`、`Proficiency(HeavyArmor)`、`ProficiencyBonus(SavingThrow,Wisdom)`… |
| `PassivesAdded` / `PassivesRemoved` | 分号分隔的 Passive.txt 条目名；直接授予单个被动时用它而非 selector |
| `Selectors` | 见下表 |
| `AllowImprovement` | `true` = 可选专长（原版 4/8/12 级） |
| `IsMulticlass` | `true` = 多职业进入用的 1 级节点 |
| 子节点 `SubClasses/SubClass.Object` | 该等级可选的子职业 ClassDescription UUID |

**Selector 语法**（参数顺序来自 Compatibility Framework 的 Selector API）B[10]：

| 函数 | 参数 | 示例 |
|---|---|---|
| `SelectSpells` | ListUUID, Amount, SwapAmount, SelectorId, CastingAbility, ActionResource, PrepareType(Default/AlwaysPrepared), CooldownType(Default/UntilRest) | `SelectSpells(2f43a103-…,3,0,,,,AlwaysPrepared)` |
| `AddSpells` | ListUUID, SelectorId, CastingAbility, ActionResource, PrepareType, CooldownType | `AddSpells(fb407d81-…,,,,AlwaysPrepared)` |
| `SelectPassives` | ListUUID, Amount, SelectorId | `SelectPassives(a0bdb113-…,1,Battlestance)` |
| `SelectSkills` | ListUUID, Amount[, SelectorId] | `SelectSkills(627af380-…,2)` |
| `SelectSkillsExpertise` | ListUUID, Amount[, LimitToProficiency][, SelectorId] | — |
| `SelectAbilityBonus` | ListUUID, BonusType, Amounts… | `SelectAbilityBonus(b9149c8e-…,AbilityBonus,2,1)`（+2/+1） |
| `SelectEquipment` | ListUUID, Amount, SelectorId | — |

让法术位在角色创建界面显示：`Boosts="ActionResource(SpellSlot,2,1)"` + `PassivesAdded` 里加 `UnlockedSpellSlotLevel1`（原版 Cleric 1 级即如此）+ 一条 `Type="ActionResource"`、`ParamMatch="0:SpellSlot"` 的 ProgressionDescription B[5][22] G[G17]。

### 3.3 `Public/<Mod>/Progressions/ProgressionDescriptions.lsx` B[2.2.3]
- 官方用法：`SelectorId` + `DisplayName`/`Description`，给 `SelectPassives(...,X)` 的 X 起名 G[G4]。
- 社区扩展：`Type="<ClassName>"` + `ProgressionTableId` 让"职业特性"在角色创建显示；`Type="ActionResource"` + `ParamMatch="0:SpellSlot"` 显示法术位 G[G17]。

### 3.4 Lists（`Public/<Mod>/Lists/`）B[2.2.4]
`SpellLists.lsx`（`Spells`, `UUID`, 可选 `Comment`）、`PassiveLists.lsx`（`Passives`）、`SkillLists.lsx`（`Skills`）、`AbilityLists.lsx`（`Abilities`）、`EquipmentLists.lsx`。分隔符存在逗号/分号两说，以解包的原版 `Shared/Public/Shared/Lists/*.lsx` 为准（原版 SpellLists 用分号）。可直接复用原版列表 UUID（官方教程就复用了 Ranger 战斗风格的 PassiveList）G[G4]。

### 3.5 角色创建默认值 B[2.2.5] G[G17]
- `CharacterCreationPresets/AbilityDistributionPresets.lsx`：`ClassUUID` + 六维默认分配（目录名另有 `AbilityDistributionPresets/` 一说，以 Toolkit 产物为准）。
- `DefaultValues/Abilities.lsx`、`Skills.lsx`、`Passives.lsx`、`Spells.lsx`：`Add`（默认勾选项）、`Level`、`TableUUID`、可选 `SelectorId`。
- 不需要 Origins / 起源角色文件。

### 3.6 `Public/<Mod>/Tags/<uuid>.lsx` B[2.2.6]
职业标签（`Name`、`UUID`、`Description="|Quickster|"`、Categories：Code / Dialog / Class / CharacterSheet），写进 ClassDescription 的 `Tags/Object` 后可用于对话 `.lsj` 的 `TaggedTexts` 条件。**自创职业若不挂任何原版职业 Tag 就没有职业专属对话；若复用原版 Tag（如 WIZARD），NPC 会把你当作该职业** D[C9]（背景知识，需实测）。

### 3.7 `Public/<Mod>/ActionResourceDefinitions/ActionResourceDefinitions.lsx` B[2.2.7]
已确认属性：`Name`、`UUID`、`DisplayName`、`Description`、`Error`、`ReplenishType`（观测到 `Rest`=长休、`ShortRest`、`Turn`）、`MaxLevel`（0 = 无等级）、`MaxValue`、`IsSpellResource`、`UpdatesSpellPowerLevel`、`ShowOnActionResourcePanel`、`PartyActionResource`、`IsHidden`。`DiceType` 未见于任何来源。
使用链路：进阶 `Boosts="ActionResource(<Name>,2,0)"` 授予 → 法术 `UseCosts` 消耗（原版格式如 `ActionPoint:1;SpellSlotsGroup:1:1:2`）→ 被动 `RestoreResource(<Name>,100%,0)` 配 `StatsFunctorContext="OnHealed;OnStatusRemoved"` 让"恢复装置/神圣干预"也能回满 B[19]。
**风险**：自定义资源的 UI 图标至今依赖已停更的 ImpUI（4 类尺寸：热键栏 48×48、CC 128×128、手柄 80×80 / 44×64）B[18]；能复用原版资源（SpellSlot、Rage、KiPoint…）或用隐藏资源（`IsHidden=true`、`ShowOnActionResourcePanel=false`）就优先这么做 B[16]。

### 3.8 Stats 文本（`Public/<Mod>/Stats/Generated/Data/*.txt`）B[2.2.8] E[2.1] G[G14][G15]

通用语法：
```
new entry "<EntryName>"
type "<SpellData|PassiveData|StatusData|InterruptData|…>"
data "SpellType" "Target"        // 仅 SpellData：Projectile/ProjectileStrike/Rush/Shout/Target/Teleportation/Throw/Wall/Zone
using "<BaseEntry>"               // 可选：继承另一条目
data "<Field>" "<Value>"
```
- 文件按类型分：`Spell_Target.txt` / `Spell_Projectile.txt` / `Spell_Shout.txt` / `Spell_Zone.txt` / `Spell_Rush.txt`…、`Passive.txt`、`Status_BOOST.txt` 等、`Interrupt.txt`；`Equipment.txt` 在 `Stats/Generated/` 下（`new equipment` / `add initialweaponset` / `add equipmentgroup` / `add equipment entry`）。
- 被动三件套：`StatsFunctorContext`（触发事件：OnAttack / OnAttacked / OnCast / OnDamage / OnHealed / OnStatusApplied / OnStatusRemoved…）+ `Conditions`（布尔条件，如 `not IsMiss() and IsMeleeWeaponAttack()`）+ `StatsFunctors`（效果，如 `DealDamage(WisdomModifier,Necrotic,Magical)`）；`IF(<cond>):<functor>` 可在同一被动内分流；`DescriptionParams` 以 `[1]`、`[2]` 注入描述 B[13] E[8]。
- 本地化引用：`data "DisplayName" "<handle>;<version>"`。
- **Functors 官方完整列表（41 个，含签名）**见 `research/G-official-docs-browser.md` §11.1：ApplyStatus、DealDamage、RegainHitPoints、RestoreResource、UseActionResource、Summon、SpawnInInventory、CreateSurface、SurfaceChange、Force、TeleportSource、SwapPlaces、UseSpell、UseAttack、ExecuteWeaponFunctors、ResetCooldowns、ResetCombatTurn、ShortRest、BreakConcentration、RemoveStatus、SetStatusDuration、Resurrect、Stabilize… G[G14]。
- **Stats Expressions**（数值表达式）：`+ - * /`、骰子、括号；关键字 `SpellCastingAbility`、`ProficiencyBonus`、`Level`、`SpellDC`、`MaxHP`、**`ClassLevel(<class>)`**、属性/技能名（`DexterityModifier`、`AthleticsFlat`…）、`Target.` 前缀取目标；函数 `max()`、`foreach()`、`ResourceRoll(<Resource>, n)`、`<Status>.Amount/.Duration` G[G15]。`ClassLevel(<你的职业>)` 让特性只随本职业等级缩放，多职业安全。
- Boosts / Conditions **没有官方参考页**（已用 AllPages 逐段核查）G[G16]；权威来源是社区 wiki 与解包的原版 Stats 文本。已证实可用的 Boosts：`ActionResource()`、`ActionResourceMultiplier()`、`Proficiency()`、`ProficiencyBonus(SavingThrow,…)`、`UnlockSpell()`、`UnlockedSpellSlotLevelN`（被动名）E[8][21][31] B[5][7]。

## 4. 本地化 G[G7] B[2.3]
- 目录：`Mods/<Mod>/Localization/<Language>/<any>.xml`；语言名固定：BrazilianPortuguese, **Chinese, ChineseTraditional**, English, French, German, Italian, Japanese, Korean, LatinSpanish, Polish, Russian, Spanish, Turkish, Ukrainian。
- 格式：`<contentList><content contentuid="…" version="1">文本</content></contentList>`；**自定义 handle 可以是任意无空格字母数字串**（官方），社区惯例用 `h` + 去掉连字符、以 `g` 分段的 UUID（如 `hc25377a0g8e44g4645g90c5gee05d6c5e31b`）；复用原版 handle 并提高 `version` 可覆盖原版文本。
- Toolkit 生成 handle 失败会写 `ls::TranslatedStringRepository::s_HandleUnknown`：**先建 Localization 文件再填 DisplayName**。
- 性别语法：`Localization/<Lang>/Gender/Female|Neutral/`，文件后缀 `_to_F`、`_to_X`。
- 改 xml 后需重载模块或 `reloadLoca`。

## 5. 图标 G[G4][G8] B[2.4]
| 用途 | 尺寸 | 位置 / 工具 |
|---|---|---|
| 类 / 子职业图标 | 300×300 PNG → DDS（BC7/BC1）；热键栏版（评论称 112×112） | `Mods/<Mod>/GUI/Assets/ClassIcons/<Name>.DDS`（+`AssetsLowRes`、`/hotbar`）；Convert UI Assets。**Patch 7 起不需要 ImpUI** |
| 技能 / 被动 / 物品 | 64×64（热键栏，进图集）+ 144×144（手柄，透明底）+ 380×380（tooltip，透明底渐隐），三者同名且全游戏唯一 | Texture Atlas Editor（512² = 64 格，1024² = 256 格）→ `Public/<Mod>/Assets/Textures/Icons/<Atlas>.dds` + `Public/<Mod>/GUI/<Atlas>.lsx`；144/380 用 Convert UI Assets 输出到 `Mods/<Mod>/GUI/Assets/ControllerUIIcons/skills_png/`、`Tooltips/Icons/` |
| 自定义行动资源 | 48×48 / 128×128 / 80×80 / 44×64 | 仍依赖 ImpUI（已停更）B[18] |
| 旧方法（识别旧教程用） | `Public/Game/GUI/Assets/ClassIcons/*.DDS`（大写扩展名、DXT5、无 mipmap）+ ImpUI | Patch 7 之前 D[C4] B[20] |

免费素材：Game-Icons.net（CC BY 3.0），Community Library 即采用 F[1]。

## 6. "给原版职业加子职业" vs "全新基础职业" B[2.5] G[G19]

| | 全新职业 | 原版职业的子职业 |
|---|---|---|
| 要写的东西 | 全部：ClassDescriptions、完整进阶、Lists、装备、图标、六维预设、多职业行 | ClassDescription 一条（`ParentGuid`）+ 子职业进阶表 + 把 UUID 加进父职业解锁级的 `SubClasses` |
| 冲突 | 零（不碰原版节点） | Patch 7 前只能整节点覆盖 → 子职业 mod 互斥；Patch 7 起可"新 UUID + 原版 TableUUID + 同 Level"合并节点（可合并 SubClasses / PassivesAdded / PassivesRemoved / Boosts / AllowImprovement / Selectors 与各类 Lists）；"非 1 级解锁 + 多职业"的合并 bug 在 Patch 8 仍存在 B[17] |
| Compatibility Framework | 不需要 | 可选：≥2.6.5.8 只要 `ParentGuid` 正确就自动注入；也可写 `Mods/<Mod>/ScriptExtender/CompatibilityFrameworkConfig.json`（`FileVersion:1, Progressions:[{UUID(s), Subclasses:[{UUID(s)}]}]`）或 Lua API `Mods.SubclassCompatibilityFramework.Api.InsertSubClasses`；你的 mod 必须比 CF 先加载；CF 依赖 SE G[G19] B[9] |
| 主机可用性 | 可（纯数据） | 若依赖 CF 则不可 |

**建议**：自创职业走"全新职业"路线，天然零冲突、可上主机；若以后想给原版职业出子职业包，再用合并节点 + CF 可选依赖。

## 7. Patch 8 与等级上限 B[2.6]
- Patch 8 把 12 个新子职业加进原版解锁级节点的 `SubClasses`；旧式整节点覆盖的子职业 mod 会把它们挤掉，合并式节点/CF 不受影响。
- 等级上限仍为 12；若玩家用 UnlockLevelCurve（13–20），你的职业缺 13–20 级节点会在 12→13 升级时黑屏 B[28]——要么补空节点（至少 `AllowImprovement`），要么在页面声明不兼容。

## 8. 最小可行职业 mod（MVP）文件树 B[2.7]

```
MyClass/
├── Mods/MyClass/
│   ├── meta.lsx                                   【必需】
│   ├── Localization/English/MyClass.xml           【必需】（Chinese/、ChineseTraditional/ 同结构）
│   ├── GUI/Assets/ClassIcons/MyClass.DDS          【推荐】300×300；子职业同目录同名规则
│   ├── GUI/Assets/ClassIcons/hotbar/MyClass.DDS   【推荐】
│   ├── GUI/AssetsLowRes/ClassIcons/...            【推荐】Convert UI Assets 自动生成
│   ├── GUI/Assets/ControllerUIIcons/skills_png/   【可选】自定义法术 144×144
│   ├── GUI/Assets/Tooltips/Icons/                 【可选】自定义法术 380×380
│   └── ScriptExtender/                            【可选】仅 SE 增强模块 / CF 配置
└── Public/MyClass/
    ├── ClassDescriptions/ClassDescriptions.lsx    【必需】
    ├── Progressions/Progressions.lsx              【必需】1..12 级 + IsMulticlass 1 级 + 各子职业
    ├── Progressions/ProgressionDescriptions.lsx   【推荐】
    ├── CharacterCreationPresets/AbilityDistributionPresets.lsx 【推荐】
    ├── DefaultValues/Abilities.lsx, Skills.lsx    【推荐】
    ├── Lists/SkillLists.lsx, AbilityLists.lsx     【推荐】（可复用原版 UUID）
    ├── Lists/SpellLists.lsx, PassiveLists.lsx     【按需】
    ├── ActionResourceDefinitions/…                【可选】
    ├── Tags/<uuid>.lsx                            【可选】
    ├── Stats/Generated/Equipment.txt              【推荐】
    ├── Stats/Generated/Data/Passive.txt, Spell_*.txt, Status_BOOST.txt, Interrupt.txt 【按需】
    ├── GUI/<Atlas>.lsx + Assets/Textures/Icons/<Atlas>.dds 【可选】技能图集
```

`templates/mod-skeleton/` 提供了一份按此结构写好的空壳（见 README），`scripts/check_mod.py` 可做结构与引用校验。

## 9. 进阶表设计清单（每个职业开工前过一遍）B[3.4]
1 级：`Proficiency()` 熟练、`ProficiencyBonus(SavingThrow,…)` 豁免、`SelectSkills`、`SelectAbilityBonus(…,AbilityBonus,2,1)`、`AddSpells`/`SelectSpells`、`ActionResource()`、`PassivesAdded`（施法职业加 `UnlockedSpellSlotLevel1`）；4/8/12 级 `AllowImprovement=true`；子职业解锁级 `SubClasses`；另一条 `IsMulticlass=true` 的 1 级节点；所有 `Name`/条目名加作者前缀避免撞名；维护一张 UUID 对照表（职业 UUID、各 TableUUID、各列表 UUID、各 Progression UUID）。
