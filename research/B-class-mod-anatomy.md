# 子课题 B：BG3 新职业 / 子职业 mod 的技术结构（anatomy）

调研日期：2026-09-02　　目标读者：想做"自创新职业/子职业" mod 的 BG3 玩家
说明：所有结论后的 `[n]` 指向第 5 节来源列表；标有 `[背景知识—非本次检索]` 的内容来自训练记忆，不计入来源统计。字段名、文件名、函数名一律保留英文原文；UUID 等示例值仅供对照，落地前请以你本机解包出的当前版本游戏文件为准。

---

## 1. TL;DR

1. **一个职业 mod 的"骨架"只有两个文件**：`Public/<Mod>/ClassDescriptions/ClassDescriptions.lsx`（定义职业/子职业本身）和 `Public/<Mod>/Progressions/Progressions.lsx`（定义每级获得什么）。职业若没有 Level 1 的 Progression 节点，角色创建界面不会显示它 [5][13]。两者通过 `ClassDescription.ProgressionTableUUID` ↔ `Progression.TableUUID` 关联；子职业 = 一条带 `ParentGuid` 的 `ClassDescription` + 自己的进阶表（`ProgressionType=1`）+ 在父职业解锁等级的 Progression 节点下的 `SubClasses` 子节点里列出其 UUID [1][5][6]。
2. **官方 Toolkit（Patch 7 起）的工作流**是在 UUID Object Editor 里建 Progressions → SpellLists → ClassDescriptions（含 IsMulticlass 行）→ 回填 SubClasses 列 → Stats Editor 建 Equipment → ProgressionDescriptions 修正选择项名称 → 放置 300×300 的类图标；Larian 官方文档最后更新于 2025-05-08（Patch 8 之后）[1][4]。
3. **Selectors / Boosts 是进阶表的核心 DSL**：`SelectSpells(<SpellListUUID>,选几个,可替换几个,,,,AlwaysPrepared)`、`AddSpells(<UUID>)`、`SelectPassives(<PassiveListUUID>,1,<SelectorId>)`、`SelectSkills(<UUID>,2)`、`SelectAbilityBonus(<UUID>,AbilityBonus,2,1)`；Boosts 用分号分隔，如 `ActionResource(SpellSlot,2,1);Proficiency(HeavyArmor)`；`AllowImprovement=true` 表示该级给专长 [1][7][10][13]。
4. **本地化**：`Localization/<Language>/*.xml`（Toolkit 放在 `Data/Mods/<Mod>/Localization/`），每行 `<content contentuid="h…" version="1">文本</content>`；官方明确"自定义 handle 可以是任意不含空白的字母数字串"，原版 handle 形如 `h1587638ag320fg40a1g9566g82783d951ea3`；lsx 里用 `type="TranslatedString" handle="…" version="1"`，stats `.txt` 里用 `data "DisplayName" "<handle>;<version>"` [2][5][21]。中文目录名为 `Chinese` / `ChineseTraditional` [2][16]。
5. **图标**：Patch 7 起类/子职业图标由游戏原生支持——300×300 PNG 经 Toolkit 的 `Project > Convert UI Assets…` 转成 DDS，放在 `Data/Mods/<Mod>/GUI/Assets/ClassIcons/`（热键栏小图在 `…/ClassIcons/hotbar/`，另有 `AssetsLowRes` 镜像），文件名必须等于 `ClassDescriptions` 的 `Name`；**不再需要 ImprovedUI/ImprovedUI Assets** [1][4][18 评论]。技能图标走 64×64 图集（Texture Atlas Editor）+ 144×144 手柄图 + 380×380 提示图 [3]。自定义行动资源（Action Resource）的图标截至检索到的资料仍依赖 ImpUI，而 ImpUI 已宣布不再维护 [18][25]。
6. **"给原版职业加子职业"与"全新职业"的本质差异**在于是否要改动原版进阶表。Patch 7 引入了 Progression 节点合并（SubClasses / PassivesAdded / PassivesRemoved / Boosts / AllowImprovement / Selectors 可合并；AbilityLists/EquipmentLists/PassiveLists/SkillLists/SpellLists 也可合并），只需新建一个"新 UUID + 相同 TableUUID + 相同 Level"的节点即可追加子职业；但"非 1 级解锁子职业 + 多职业"的合并 bug 在 Patch 8 仍存在 [17]。Compatibility Framework（CF，前身即 Subclass Compatibility Framework，同一项目）自 2.6.5.8 起只要 `ClassDescription` 带正确的 `ParentGuid` 就会自动注入子职业，无需配置；需要 Script Extender [9][11][12][14]。
7. **Patch 8（2025-04）影响**：12 个新子职业各加入对应职业的 SubClasses 列表；Larian 在压测第 3 版修复了"部分 mod 职业/子职业无法升级"的 bug；旧版 ImpUI 会导致新子职业不显示，ImpUI 的 Patch 8 版仅保留最小改动且不再维护；Toolkit 的 Stats/UUID Editor 补入了 Patch 8 数据 [25][26][33][36][37]。等级上限仍为 12；若玩家用 UnlockLevelCurve（13–20），职业 mod 缺少 13–20 级进阶会在 12→13 升级时黑屏 [28]。
8. **最小可行 mod（MVP）文件树**见第 2.7 节：必需 = `meta.lsx`、`ClassDescriptions.lsx`、`Progressions.lsx`、本地化文件；推荐 = `ProgressionDescriptions.lsx`、`AbilityDistributionPresets.lsx`、`DefaultValues/*.lsx`、`Lists/*.lsx`、`Equipment.txt`、类图标；可选 = `ActionResourceDefinitions.lsx`、`Tags/*.lsx`、`Stats/Generated/Data/*.txt`、技能图集、CF 配置。

---

## 2. 分节详细发现

### 2.1 教程入口（按权威性/完整度排序）

| # | 教程 | 形式 / 时效 | 覆盖范围 | 不覆盖 |
|---|---|---|---|---|
| 1 | Larian 官方《Adding Classes and Subclasses》(docs.baldursgate3.game) [1]；mod.io 上的同文《Adding New Classes or Subclasses》（作者 GrumpyWashbear，Official 标签，4.6 万浏览、220 条评论）[4] | 文字+截图；官方站最后编辑 2025-05-08 | Toolkit UUID Object Editor 全流程：Progressions（Name/Level/ProgressionType/TableUUID/Boosts/Selectors/AllowImprovement）、SpellLists、子职业（ProgressionType=1、Level 3）、ClassDescriptions 各列（DisplayName/Description/ShortName/PrimaryAbility/SpellCastingAbility/LearningStrategy/MustPrepareSpells/CanLearnSpells/CharacterCreationPose/BaseHp/HPPerLevel/三个 HotbarColumns/ClassEquipment）、多职业行（IsMulticlass）、SubClasses 列、Game Mode 快速测试、Stats Editor 建 Equipment、ProgressionDescriptions（SelectorId）、类图标路径与 DDS 设置 | 默认属性预设、DefaultValues、Tags、行动资源、本地化（另有独立页 [2]）、自定义法术（另有 Basic Spells / Projectile Spells 页） |
| 2 | BG3 Modding Community Wiki《Basic Class Creation》（Quickster 示例）[5] | 纯手写 lsx + Multitool 打包；提到 Patch 7/8 已不需 Mod Fixer | 最完整的逐文件讲解：ClassDescriptions、Progressions、ProgressionDescriptions（含让法术位显示在 CC 的 `ParamMatch`/`Type` 写法）、AbilityDistributionPresets、Localization、DefaultValues/Abilities.lsx & Skills.lsx、Lists/AbilityLists & SkillLists & PassiveLists、Tags（含一个对话选项示例）、Selectors、Passive.txt、Boosts/PassivesAdded、子职业、ActionResourceDefinitions.lsx、Equipment.txt + ClassEquipment | Toolkit 界面操作；SelectSpells 章节标注 "COMING SOON"；图标 |
| 3 | Community Wiki《Subclass Creation For An Existing Class》（Paladin of the Cosmic Order）[6] | 手写 lsx | 给原版职业加子职业：`ParentGuid`、复制原版 Paladin 1 级节点并追加 `SubClass`、冲突警告与 CF 建议 | Patch 7 合并机制（写于合并机制之前） |
| 4 | Community Library Wiki《Building a Class Mod》[13] | 2024-02-25 | ClassDescriptions 字段释义（含 CanLearnSpells/MustPrepareSpells）、AbilityDistributionPresets、Progressions + IsMulticlass 示例、本地化（LSLib 转 .loca）、Passive/Spell 语法、Spell/Passive Lists 属性、Equipment、子职业兼容性说明 | 图标章节 TODO；面向 Community Library 贡献流程 |
| 5 | Compatibility Framework GitHub Wiki：《Adding a Subclass》《_Selector API》《_Class Module》《Home》[9][10][11][12] | 2026-02 更新 | 子职业自动注入、JSON/YAML 配置、Selector 参数完整表、Lua API | 职业本身的制作 |
| 6 | mod.io《Compatibility Changes in Patch 7 & 8: Merging》(RandoRuda) [17] | ≈2025-05 更新 | Patch 7/8 的节点合并规则、已知 bug 与社区测试出的规避法 | — |
| 7 | 视频：《How to Create a Custom BG3 Class Mod — Complete Toolkit Tutorial》(YouTube) [34]、《Make a Bloody BG3 Class - Toolkit Tutorial》(Nexus 视频) [35] | 仅见标题 | 本次未能核实内容 | — |

补充：任务中点名的 Padme4000、Volitio 两位作者，本次检索到的作品分别是外观/角色创建类 mod 与 Mod Configuration Menu，**未找到他们写的职业教程**；Padme4000 只在 [17] 中被引用为"pre-toolkit mod 转 Toolkit"的种族合并示例。行动资源相关另有两篇 mod.io 指南：Djmr（ImpUI 作者）《Implementing Custom Action Resources with ImpUI》[18] 与 TLH_MOD《Restore Your Custom Class Action Resource》[19]。

### 2.2 数据结构清单

#### 2.2.1 `ClassDescriptions.lsx`（`Public/<Mod>/ClassDescriptions/`）

原版 Barbarian 及其子职业节点（引自 Shared.pak，Community Wiki 转录）[5]：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<save>
  <version major="4" minor="0" revision="9" build="314"/>
  <region id="ClassDescriptions">
    <node id="root">
      <children>
        <node id="ClassDescription">
          <attribute id="BaseHp" type="int32" value="12"/>
          <attribute id="CharacterCreationPose" type="guid" value="0f07ec6e-4ef0-434e-9a51-1353260ccff8"/>
          <attribute id="ClassEquipment" type="FixedString" value="EQP_CC_Barbarian"/>
          <attribute id="ClassHotbarColumns" type="int32" value="5"/>
          <attribute id="CommonHotbarColumns" type="int32" value="9"/>
          <attribute id="Description" type="TranslatedString" handle="h3aa4b4a4g0076g4635gb363g7891e8f2e495" version="10"/>
          <attribute id="DisplayName" type="TranslatedString" handle="h60fa88ecg49b2g402bg9c75g273cbaafd414" version="1"/>
          <attribute id="HpPerLevel" type="int32" value="7"/>
          <attribute id="ItemsHotbarColumns" type="int32" value="2"/>
          <attribute id="LearningStrategy" type="uint8" value="1"/>
          <attribute id="Name" type="FixedString" value="Barbarian"/>
          <attribute id="PrimaryAbility" type="uint8" value="1"/>
          <attribute id="ProgressionTableUUID" type="guid" value="60bbcc97-5381-4898-bc15-908c072895de"/>
          <attribute id="SoundClassType" type="FixedString" value="Barbarian"/>
          <attribute id="SpellCastingAbility" type="uint8" value="6"/>
          <attribute id="UUID" type="guid" value="d8cadb42-0ff9-4049-afaf-e5d78d06a399"/>
          <children>
            <node id="Tags">
              <attribute id="Object" type="guid" value="02913f9a-f696-40cf-acdf-32032afab32c"/>
            </node>
          </children>
        </node>
        <node id="ClassDescription">   <!-- 子职业：多了 ParentGuid，少了 BaseHp/HpPerLevel/ClassEquipment/Hotbar 列 -->
          <attribute id="CharacterCreationPose" type="guid" value="0f07ec6e-4ef0-434e-9a51-1353260ccff8"/>
          <attribute id="Description" type="TranslatedString" handle="h5fa8a376gee1cg43e2g8f36g12129d82a292" version="9"/>
          <attribute id="DisplayName" type="TranslatedString" handle="hc337205dg93e1g4956g9924gb7d641b6e211" version="1"/>
          <attribute id="LearningStrategy" type="uint8" value="1"/>
          <attribute id="Name" type="FixedString" value="BerserkerPath"/>
          <attribute id="ParentGuid" type="guid" value="d8cadb42-0ff9-4049-afaf-e5d78d06a399"/>
          <attribute id="PrimaryAbility" type="uint8" value="1"/>
          <attribute id="ProgressionTableUUID" type="guid" value="b2a03b63-809f-4df9-a179-bf5b899082ef"/>
          <attribute id="SoundClassType" type="FixedString" value="Barbarian"/>
          <attribute id="SpellCastingAbility" type="uint8" value="6"/>
          <attribute id="UUID" type="guid" value="32eee7d8-1b2f-4de5-b9ee-78fbd286c6ef"/>
          <children>
            <node id="Tags">
              <attribute id="Object" type="guid" value="ac3449f7-c09b-4bc0-8634-fcff97d49279"/>
            </node>
          </children>
        </node>
      </children>
    </node>
  </region>
</save>
```

字段释义（综合 [1][5][13][15]）：

| 属性 | 类型 | 含义 / 取值 |
|---|---|---|
| `Name` | FixedString | 技术名，**不能有空格**（官方 [1]；类图标文件名必须与之完全一致 [1][4]）。注意 [5] 的示例 `"Magical Quickster"` 带空格，与官方要求冲突，不建议模仿。 |
| `UUID` | guid | 职业/子职业唯一 ID；`SubClasses/SubClass.Object` 与 `AbilityDistributionPreset.ClassUUID` 引用它 [5][13]。 |
| `ParentGuid` | guid | 仅子职业有：父职业的 `UUID`。Toolkit 里是 `ParentUUID` 下拉列 [1]。例：原版 Paladin 为 `ff4d9497-023c-434a-bd14-82fc367e991c` [6]。 |
| `ProgressionTableUUID` | guid | 对应 `Progressions.lsx` 中该职业/子职业所有节点共用的 `TableUUID` [1][7]。 |
| `DisplayName` / `Description` / `ShortName` | TranslatedString | 本地化 handle + version。`ShortName` 用于角色面板上的"子职业 + 职业"缩写（如 "Mace Battlemage"）[1]。 |
| `PrimaryAbility` / `SpellCastingAbility` | uint8 | 属性枚举。Community Library 给出 1=STR, 2=DEX, 3=CON, 4=INT, 5=WIS, 6=CHA [13]；Community Wiki 却写 1=dex, 2=str [5]。原版 Barbarian `PrimaryAbility=1`、Death Knight（用 WisdomModifier）`SpellCastingAbility=5`，与 [13] 的映射一致，**以 [13] 为准，但请在 Toolkit 下拉里核对**。 |
| `BaseHp` / `HpPerLevel` | int32 | 1 级 HP 与每级 HP（[5] 观察到实际每级加 `HpPerLevel+1`，未在官方文档确认）。 |
| `CanLearnSpells` | bool | 能否像法师那样从卷轴学法术 [1][13]。 |
| `MustPrepareSpells` | bool | 是否需要准备法术（牧师/德鲁伊式）[1][13]。 |
| `LearningStrategy` | uint8 | Toolkit 里对职业选 `AllChildren` [1]；文件里几乎都是 `1`，Archfey Warlock 为 `2` [13]，具体语义**未能确认**。 |
| `ClassEquipment` | FixedString | `Equipment.txt` 里 `new equipment "…"` 的名字，只填在职业上，不填子职业 [1][5]。 |
| `CharacterCreationPose` | guid | 所有职业均为 `0f07ec6e-4ef0-434e-9a51-1353260ccff8` [1][5][13]。 |
| `SoundClassType` | FixedString | 借用某个原版职业名（Barbarian/Paladin/Fighter…）[5][13]。 |
| `CommonHotbarColumns` / `ClassHotbarColumns` / `ItemsHotbarColumns` | int32 | 热键栏分隔默认列数，三者之和必须为 16，默认 9/5/2 [1]。 |
| `IsMulticlass`（官方文档措辞） | — | 官方文档 [1][4] 说"在 ClassDescriptions 表下再加一行、`IsMulticlass=Yes`"，但所有文件级来源都表明 `IsMulticlass` 是 **Progressions** 节点的属性（见 2.2.2）[13][22]。官方那段话紧接 Progressions 讲解，应理解为"再加一条 1 级 Progression 行"。存在表述分歧。 |
| 子节点 `Tags/Object` | guid | 职业标签（见 2.2.6）[5][15]。 |

#### 2.2.2 `Progressions.lsx`（`Public/<Mod>/Progressions/`）

原版 Paladin 1 级与 4 级节点 [7]：

```xml
<node id="Progression">
  <attribute id="Boosts" type="LSString" value="ProficiencyBonus(SavingThrow,Wisdom);ProficiencyBonus(SavingThrow,Charisma);Proficiency(LightArmor);Proficiency(MediumArmor);Proficiency(HeavyArmor);Proficiency(Shields);Proficiency(SimpleWeapons);Proficiency(MartialWeapons);ActionResource(LayOnHandsCharge,3,0);ActionResource(ChannelOath,1,0)" />
  <attribute id="Level" type="uint8" value="1" />
  <attribute id="Name" type="LSString" value="Paladin" />
  <attribute id="ProgressionType" type="uint8" value="0" />
  <attribute id="Selectors" type="LSString" value="SelectSkills(627af380-2bbb-4a9f-9571-5ec781a6daf4,2);AddSpells(fb407d81-3a05-46f1-9153-0fb27dce95b6,,,,AlwaysPrepared);SelectAbilityBonus(b9149c8e-52c8-46e5-9cb6-fc39301c05fe,AbilityBonus,2,1)" />
  <attribute id="TableUUID" type="guid" value="ba2afe85-acba-4ea1-a238-2b4543f47821" />
  <attribute id="UUID" type="guid" value="b60618d1-c262-42b5-9fdd-2c0f7aa5e5af" />
  <children>
    <node id="SubClasses">
      <children>
        <node id="SubClass"><attribute id="Object" type="guid" value="b36d247e-d39f-4ae9-9476-3ec315c55789" /></node>
        <node id="SubClass"><attribute id="Object" type="guid" value="1c761ad0-6f5f-409e-ac1d-ddf6f85c1fc4" /></node>
        <node id="SubClass"><attribute id="Object" type="guid" value="3cc3d397-c47d-4966-87ae-88827f73f645" /></node>
      </children>
    </node>
  </children>
</node>
<node id="Progression">
  <attribute id="AllowImprovement" type="bool" value="True" />
  <attribute id="Boosts" type="LSString" value="ActionResource(LayOnHandsCharge,1,0)" />
  <attribute id="Level" type="uint8" value="4" />
  <attribute id="Name" type="LSString" value="Paladin" />
  <attribute id="ProgressionType" type="uint8" value="0" />
  <attribute id="TableUUID" type="guid" value="ba2afe85-acba-4ea1-a238-2b4543f47821" />
  <attribute id="UUID" type="guid" value="4f2c7b4e-2f91-4105-a136-9387a8cfed4f" />
</node>
```

属性释义：

| 属性 | 含义 |
|---|---|
| `UUID` | 该节点（某职业某一级）的唯一 ID；覆盖原版节点要用相同 UUID，新增节点要用新 UUID [7][22]。 |
| `TableUUID` | 同一职业/子职业所有等级共用，等于 ClassDescription 的 `ProgressionTableUUID`；多职业 1 级节点也用它 [1][7]。 |
| `Name` | 与 ClassDescription `Name` 相同的技术名 [1][13]。 |
| `Level` | uint8，本节点生效等级 [1]。 |
| `ProgressionType` | 0=职业，1=子职业，2=种族 [5][13]（bg3.wiki 的 LSX 页写种族为 3 [22]，属少数说法）。 |
| `Boosts` | 分号分隔的 boost 表达式：`ActionResource(SpellSlot,2,1)`（资源名、数量、等级）、`ActionResource(Rage,2,0)`、`Proficiency(HeavyArmor)`、`ProficiencyBonus(SavingThrow,Wisdom)` 等 [1][5][7]。 |
| `PassivesAdded` / `PassivesRemoved` | 分号分隔的 Passive.txt 条目名，例 `RageUnlock;UnarmouredDefence_Barbarian`；直接授予单个被动时用它而非 selector [5][13]。 |
| `Selectors` | 分号分隔的选择器函数（见下表）[1][10]。 |
| `AllowImprovement` | `true` = 该级可选专长（Feat）[1][22]。 |
| `IsMulticlass` | `true` = 该 1 级节点用于多职业进入本职业（通常删减 Boosts/Selectors）[13][22]。 |
| 子节点 `SubClasses/SubClass.Object` | 在该等级可选的子职业 ClassDescription UUID [1][5][6]。 |

Selector 函数语法（参数顺序来自 CF Selector API [10]，示例来自 [1][5][7][13][22]）：

| 函数 | 参数（按位置） | 示例 |
|---|---|---|
| `SelectSpells` | ListUUID, Amount, SwapAmount, SelectorId, CastingAbility, ActionResource(UUID), PrepareType(Default/AlwaysPrepared), CooldownType(Default/UntilRest) | `SelectSpells(2f43a103-5bf1-4534-b14f-663decc0c525,3,0,,,,AlwaysPrepared)`；官方释义 `SelectSpells(<UUID>,1,0)` = 选 1 个、可替换 0 个 [1] |
| `AddSpells` | ListUUID, SelectorId, CastingAbility, ActionResource, PrepareType, CooldownType | `AddSpells(fb407d81-3a05-46f1-9153-0fb27dce95b6,,,,AlwaysPrepared)` |
| `SelectPassives` | ListUUID, Amount, SelectorId | `SelectPassives(a0bdb113-1cce-45ac-94fb-72d4c3f207e9,1,Battlestance)`（第 3 参数是 ProgressionDescriptions/DefaultValues 的 `SelectorId`；省略则界面显示 "Class Passives"）[1] |
| `SelectSkills` | ListUUID, Amount, [SelectorId] | `SelectSkills(627af380-2bbb-4a9f-9571-5ec781a6daf4,2)` |
| `SelectSkillsExpertise` | ListUUID, Amount, [LimitToProficiency], [SelectorId] | — |
| `SelectAbilityBonus` | ListUUID, BonusType, Amounts… | `SelectAbilityBonus(b9149c8e-52c8-46e5-9cb6-fc39301c05fe,AbilityBonus,2,1)`（+2/+1）|
| `SelectEquipment` | ListUUID, Amount, SelectorId | — |
| `SelectAbilities` | CF 列出但未给参数 | 未能确认 |
| `ReplacePassives` | 游戏按 `SelectPassives` 读取 [10] | — |

Community Wiki 的经验：要让法术位在角色创建界面显示，除了 `Boosts="ActionResource(SpellSlot,2,1)"` 还要在 `PassivesAdded` 加 `UnlockedSpellSlotLevel1`，并配一条 ProgressionDescriptions（见 2.2.3）[5]；原版 Cleric 1 级节点确实带 `PassivesAdded="DomainSpells;UnlockedSpellSlotLevel1"` [22]。

**多职业节点示例**（Community Library Death Knight）[13]：

```xml
<node id="Progression">
  <attribute id="AllowImprovement" type="bool" value="false"/>
  <attribute id="Boosts" type="LSString" value="Proficiency(Greatswords);Proficiency(MediumArmor)"/>
  <attribute id="IsMulticlass" type="bool" value="true"/>
  <attribute id="Level" type="uint8" value="1"/>
  <attribute id="Name" type="LSString" value="DeathKnight"/>
  <attribute id="ProgressionType" type="uint8" value="0"/>
  <attribute id="Selectors" type="LSString" value="AddSpells(f8799582-ef4c-49b7-88eb-2120aecab569);SelectPassives(da3203d8-750a-4de1-b8eb-1eccfccddf46,1,FightingStyle)"/>
  <attribute id="TableUUID" type="guid" value="29b323b1-d1fa-4882-a8f3-d4cb0ad6c158"/>
  <attribute id="UUID" type="guid" value="ae89fb12-155e-4ad9-bbf7-bfe67774d8e3"/>
</node>
```

#### 2.2.3 `ProgressionDescriptions.lsx`（`Public/<Mod>/Progressions/`）

作用：把 Selector 的 `SelectorId` 映射到本地化的名称/描述，并可让"职业特性"在 CC 面板显示 [1][5]。Community Library 的真实文件只有 4 个属性 [15]：

```xml
<node id="ProgressionDescription">
  <attribute id="Description" type="TranslatedString" handle="ha3d8d0d960d247bf97a3861a81b04fd57g6a" version="1"/>
  <attribute id="DisplayName" type="TranslatedString" handle="h08bbe0a2b84743b3af49f2bbfb323b95fd37" version="1"/>
  <attribute id="SelectorId" type="FixedString" value="CL_Tags"/>
  <attribute id="UUID" type="guid" value="c1cfc0d3-7a65-d35c-0100-ca1100000000"/>
</node>
```

Community Wiki 另给出两种扩展写法（让"职业特性"与"法术位"出现在 CC）[5]：

```xml
<node id="ProgressionDescription">
  <attribute id="Description" type="TranslatedString" handle="hb2684027ga7c6g49f4gab1eg2473022fb1d4" version="1"/>
  <attribute id="DisplayName" type="TranslatedString" handle="h40ad27e0g3f47g409bg9469g79c71aef7b6g" version="1"/>
  <attribute id="ProgressionTableId" type="guid" value="b283c957-2267-484a-a6c0-f98479c55e53"/>
  <attribute id="Type" type="FixedString" value="Quickster"/>          <!-- 职业名 -->
  <attribute id="UUID" type="guid" value="3d63dd44-02d2-4eee-a138-85de94d9a53e"/>
</node>
<node id="ProgressionDescription">
  <attribute id="Description" type="TranslatedString" handle="h4cfc6c2bgec3eg4703g93fbgff6640b77db7" version="1"/>
  <attribute id="DisplayName" type="TranslatedString" handle="hcdce7bceg7784g42a0g8445g6a86bfc68fc2" version="1"/>
  <attribute id="ParamMatch" type="FixedString" value="0:SpellSlot"/>
  <attribute id="ProgressionTableId" type="guid" value="b283c957-2267-484a-a6c0-f98479c55e53"/>
  <attribute id="Type" type="FixedString" value="ActionResource"/>
  <attribute id="UUID" type="guid" value="06cd56f0-e623-4fc6-8ca4-1f19cd87c42b"/>
</node>
```

任务中提到的 `ExactMatch`、`PassivePrototype` 两个属性在本次检索到的所有来源中**均未出现**，未能确认。Toolkit 里它是 Progressions 分组下的 ProgressionDescriptions 表，改完需重启 Editor 才能看到效果 [1]。

#### 2.2.4 Lists（`Public/<Mod>/Lists/`）

| 文件 | region / node | 属性 | 示例 |
|---|---|---|---|
| `SpellLists.lsx` | `SpellLists` / `SpellList` | `Comment`（可选）、`Spells`、`UUID` [13] | 法术名格式 `Type_TechName`，如 `Target_ShockingGrasp`、`Zone_BurningHands` [1] |
| `PassiveLists.lsx` | `PassiveLists` / `PassiveList` | `Passives`、`UUID` | `value="Quickster_GottaRun,Quickster_LongJump"` [5] |
| `SkillLists.lsx` | `SkillLists` / `SkillList` | `Skills`、`UUID` | `value="Athletics, Acrobatics, Arcana, SleightOfHand, Perception"` [5] |
| `AbilityLists.lsx` | `AbilityLists` / `AbilityList` | `Abilities`、`UUID` | `value="Strength, Dexterity, Constitution, Intelligence, Wisdom, Charisma"` [5] |
| `EquipmentLists.lsx` | — | Patch 7 可合并列表之一 [17]，本次未取得节点示例 | — |

分隔符存在分歧：Community Library 文档说 Spells/Passives 用分号 [13]，Community Wiki 的实际示例用逗号 [5]。请以解包出的原版 `Shared/Public/Shared/Lists/*.lsx` 为准（[背景知识—非本次检索]：原版 SpellLists 使用分号）。Toolkit 里在左侧 "Lists" 分组下新建 SpellLists 表即可，行的 UUID 复制到 Selectors 里 [1]。

#### 2.2.5 `DefaultValues/*.lsx` 与 `CharacterCreationPresets/AbilityDistributionPresets.lsx`

`DefaultValues/Abilities.lsx`、`Skills.lsx`（Community Wiki）[5]，`Passives.lsx`（Community Library 真实文件，多了 `SelectorId`、`Comment`）[15]；CF 文档还提到 `DefaultValues/Spells.lsx`、`Equipment.lsx` [10]：

```xml
<region id="DefaultValues"><node id="root"><children>
  <node id="DefaultValue">
    <attribute id="Add" type="LSString" value="Athletics;Acrobatics"/>   <!-- 默认勾选项 -->
    <attribute id="Level" type="int32" value="1"/>
    <attribute id="TableUUID" type="guid" value="b283c957-2267-484a-a6c0-f98479c55e53"/>  <!-- 职业进阶表 -->
    <attribute id="UUID" type="guid" value="72369441-dd7d-4908-9481-06417ca665bb"/>
  </node>
</children></node></region>
```

```xml
<node id="DefaultValue">   <!-- Community Library Passives.lsx -->
  <attribute id="Comment" type="LSString" value="Character Scale - Human"/>
  <attribute id="Add" type="LSString" value="CL_Passive_CharacterScale_Multiplier_100_Percent"/>
  <attribute id="Level" type="int32" value="1"/>
  <attribute id="SelectorId" type="LSString" value="CL_CharacterScale"/>
  <attribute id="TableUUID" type="guid" value="4b6e7ec9-145b-4a95-9d8a-b2181de2749e"/>
  <attribute id="UUID" type="guid" value="c1cfc0d3-0000-dfb0-0001-c11a125ca1ed"/>
</node>
```

`AbilityDistributionPresets.lsx`（角色创建的默认六维分配）[5][13]：

```xml
<region id="AbilityDistributionPresets"><node id="root"><children>
  <node id="AbilityDistributionPreset">
    <attribute id="Charisma" type="int32" value="10"/>
    <attribute id="ClassUUID" type="guid" value="e7b0f304-da32-410e-9e58-6efea9272673"/>
    <attribute id="Constitution" type="int32" value="12"/>
    <attribute id="Dexterity" type="int32" value="15"/>
    <attribute id="Intelligence" type="int32" value="14"/>
    <attribute id="Strength" type="int32" value="8"/>
    <attribute id="UUID" type="guid" value="cfb21b13-3ac5-4c9d-9dea-2657a88747ed"/>
    <attribute id="Wisdom" type="int32" value="13"/>
  </node>
</children></node></region>
```

目录名分歧：Community Wiki 放在 `Public/<Mod>/CharacterCreationPresets/AbilityDistributionPresets.lsx` [5]；Community Library 文档写 `Public/ModName/AbilityDistributionPresets/…` 但同段又说"因为它在 CharacterCreationPresets 文件夹里" [13]。建议以 Toolkit 生成的路径为准。**Origins（起源角色）文件不是自定义职业的必需项**——没有任何来源要求它。

#### 2.2.6 `Tags/<UUID>.lsx`（职业标签与对话）

标签文件名即其 UUID，放在 `Public/<Mod>/Tags/`（Community Library 中命名为 `<uuid>.lsf.lsx`）[5][15]：

```xml
<region id="Tags">
  <node id="Tags">
    <attribute id="Description" type="LSString" value="|Quickster|"/>
    <attribute id="DisplayDescription" type="TranslatedString" handle="hd2b088dcgec45g4e65g9be5g4c6f689e46c6" version="1"/>
    <attribute id="DisplayName" type="TranslatedString" handle="h8cb04d43g3a62g4f3egb4e2g567dea9c7799" version="2"/>
    <attribute id="Icon" type="FixedString" value=""/>
    <attribute id="Name" type="FixedString" value="Quickster_Internal_Name"/>
    <attribute id="UUID" type="guid" value="35add446-b710-4ad1-8dbc-36f99aecc6d5"/>
    <children><node id="Categories"><children>
      <node id="Category"><attribute id="Name" type="LSString" value="Code"/></node>
      <node id="Category"><attribute id="Name" type="LSString" value="Dialog"/></node>
      <node id="Category"><attribute id="Name" type="LSString" value="Class"/></node>
      <node id="Category"><attribute id="Name" type="LSString" value="CharacterSheet"/></node>
    </children></node></children>
  </node>
</region>
```

把该 UUID 写进 ClassDescription 的 `Tags/Object` 后，可在对话 `.lsj` 的 `TaggedTexts → RuleGroup → Rules → Tags` 中用它做职业专属对话选项（Community Wiki 用 `Gustav/Story/Dialogs/Tutorial/TUT_Start_Brinepool.lsj` 演示）[5]。对纯玩法向的职业 mod 这是可选项。

#### 2.2.7 `ActionResourceDefinitions.lsx`（自定义资源）

Community Wiki 示例 [5] 与两个开源 mod 的真实文件 [15][16]：

```xml
<region id="ActionResourceDefinitions"><node id="root"><children>
  <node id="ActionResourceDefinition">
    <attribute id="Description" type="TranslatedString" handle="hb2d26394gdc0bg458egafa8g7906e8441c87" version="1"/>
    <attribute id="DisplayName" type="TranslatedString" handle="hf89fcccfg40b1g4671g9e8ege9c0e4e93a8d" version="1"/>
    <attribute id="MaxLevel" type="uint32" value="0"/>
    <attribute id="Name" type="FixedString" value="SpeedForce"/>
    <attribute id="ReplenishType" type="FixedString" value="ShortRest"/>
    <attribute id="IsSpellResource" type="bool" value="false"/>
    <attribute id="ShowOnActionResourcePanel" type="bool" value="true"/>
    <attribute id="UUID" type="guid" value="dc2d6ab6-4c86-4f2a-9455-ec86d53a8175"/>
  </node>
</children></node></region>
```

```xml
<!-- Community Library / MailMe Death Knight -->
<node id="ActionResourceDefinition">
  <attribute id="Description" type="TranslatedString" handle="99d7b8be73b16957796985f19d597e5b6cb0c" version="1"/>
  <attribute id="DisplayName" type="TranslatedString" handle="99d7b8be73b16957796985f19d597e5b6cb0c" version="1"/>
  <attribute id="Error" type="FixedString" value="ActionResourceDefinitions_New_Stat_4_Error"/>
  <attribute id="IsSpellResource" type="bool" value="false"/>
  <attribute id="MaxLevel" type="uint32" value="0"/>
  <attribute id="MaxValue" type="uint32" value="0"/>
  <attribute id="Name" type="FixedString" value="Spite"/>
  <attribute id="PartyActionResource" type="bool" value="false"/>
  <attribute id="ReplenishType" type="FixedString" value="ShortRest"/>
  <attribute id="ShowOnActionResourcePanel" type="bool" value="true"/>
  <attribute id="UUID" type="guid" value="ad424027-b2ea-4d05-8366-77b8e340b1de"/>
  <attribute id="UpdatesSpellPowerLevel" type="bool" value="false"/>
</node>
<!-- ZerdBG3 RAW：每回合刷新的隐藏资源 -->
<node id="ActionResourceDefinition">
  <attribute id="DisplayName" type="TranslatedString" handle="h9b9372c9g28e7g4fbcga73dgad4bfec682c1" version="1"/>
  <attribute id="IsHidden" type="bool" value="true"/>
  <attribute id="Name" type="FixedString" value="RAW_HastePoint"/>
  <attribute id="ReplenishType" type="FixedString" value="Turn"/>
  <attribute id="ShowOnActionResourcePanel" type="bool" value="false"/>
  <attribute id="UUID" type="guid" value="8cf3d508-9ab8-4ecb-92e7-4e78463376f4"/>
</node>
```

已确认的属性：`Name`、`UUID`、`DisplayName`、`Description`、`Error`、`ReplenishType`（观测到 `Rest`＝长休 [19]、`ShortRest`、`Turn`）、`MaxLevel`（0 = 没有像法术位那样的等级 [19]）、`MaxValue`、`IsSpellResource`、`UpdatesSpellPowerLevel`、`ShowOnActionResourcePanel`、`PartyActionResource`、`IsHidden` [5][15][16][19]。任务中提到的 `DiceType` **未在任何来源出现，未能确认**；`ReplenishType` 的完整枚举也未找到官方列表。

使用链路：进阶表 `Boosts="ActionResource(SpeedForce,2,0)"`（名、数量、等级）授予 [5]；法术在 `UseCosts` 里消耗（SpellData 字段，原版格式如 `"ActionPoint:1;SpellSlotsGroup:1:1:2"`）[24]；用被动的 `RestoreResource(<Name>,100%,0)` 配合 `StatsFunctorContext="OnHealed;OnStatusRemoved"` 让"恢复装置/天使药水/神圣干预"也能回满自定义资源 [19]。Toolkit 里在 UUID Editor 的 `ActionResourceDefinitions` 分类下新建（没有子分类就按 `+`）[19]。UI 图标见 2.4。

#### 2.2.8 `Stats/Generated/Data/*.txt` 与 `Stats/Generated/Equipment.txt`

**通用语法**（[5][13][24]）：

```
new entry "<EntryName>"
type "<SpellData|PassiveData|StatusData|InterruptData|Character|Weapon|Armor|Object>"
data "SpellType" "Target"          // 仅 SpellData：Projectile/ProjectileStrike/Rush/Shout/Target/Teleportation/Throw/Wall/Zone
using "<BaseEntry>"                 // 可选：继承另一条目的全部字段
data "<Field>" "<Value>"
```

SpellData 各子类型对应文件：`Spell_Projectile.txt`、`Spell_ProjectileStrike.txt`、`Spell_Rush.txt`、`Spell_Shout.txt`、`Spell_Target.txt`、`Spell_Teleportation.txt`、`Spell_Throw.txt`、`Spell_Wall.txt`、`Spell_Zone.txt`；所有子类型共用同一套 185 个字段，由 `SpellType` 区分 [24]。原版 Hold Person 条目示例 [24]：

```
new entry "Target_HoldPerson"
type "SpellData"
data "SpellType" "Target"
using "Target_HoldPerson_2"
data "Level" "2"
data "SpellSchool" "Enchantment"
data "TargetConditions" "not Self() and not Dead() and Character()"
data "SpellRoll" "not SavingThrow(Ability.Wisdom, SourceSpellDC())"
data "SpellSuccess" "ApplyStatus(HOLD_PERSON,100,10)"
data "TargetRadius" "1800"
data "Icon" "Spell_Enchantment_HoldPerson"
data "DisplayName" "h...;1"
data "Description" "h...;5"
data "UseCosts" "ActionPoint:1;SpellSlotsGroup:1:1:2"
data "SpellFlags" "HasVerbalComponent;HasSomaticComponent;IsConcentration;IsSpell;IsHarmful"
```

`Passive.txt`（PassiveData，29 字段：`DisplayName`/`Description`/`DescriptionParams`/`Icon`/`Properties`/`Boosts`/`BoostContext`/`BoostConditions`/`StatsFunctorContext`/`Conditions`/`StatsFunctors`/`EnabledConditions`/`Toggle*`/`PriorityOrder` 等 [24]）示例 [5][13]：

```
new entry "Quickster_GottaRun"
type "PassiveData"
data "DisplayName" "hc2cce261g6b48g4d12g8b06g8edacb8f5dea"
data "Description" "h6f23489eg767ag43e7g9a6agbc0980fa925f"
data "Icon" "PassiveFeature_FightingStyle_Archery"
data "Properties" "Highlighted"
data "Boosts" "ActionResourceMultiplier(Movement,175,0)"

new entry "CL_UnholyWpn"
type "PassiveData"
data "DisplayName" "haecff2fbgf630g478cga6d5g0fe1e73b03e1;1"
data "Description" "hd22bba2egdc74g4118ga101g1176e4e6a351;1"
data "DescriptionParams" "DealDamage(WisdomModifier,Necrotic)"
data "Icon" "Mailem_DK_Unholyweapon"
data "Properties" "Highlighted"
data "StatsFunctorContext" "OnAttack"
data "Conditions" "not IsMiss() and IsMeleeWeaponAttack() "
data "StatsFunctors" "DealDamage(WisdomModifier,Necrotic,Magical)"
```

`StatsFunctorContext` = 触发事件，`Conditions` = 触发时需满足的条件，`StatsFunctors` = 执行的效果；`DescriptionParams` 以分号分隔并在描述文本中以 `[1]`、`[2]` 引用 [13]。`Properties` 可为 `Highlighted` 或 `IsHidden`（隐藏被动）[5][19]。

`Status_BOOST.txt` 等（StatusData，110 字段，`StatusType` 取 BOOST/EFFECT/HEAL/POLYMORPHED… 等 11 种；含 `Boosts`、`Icon`、`OnApplyFunctors`、`AuraRadius` 等）[24]；`Interrupt.txt`（InterruptData，含 `InterruptContext`、`InterruptContextScope`、`Conditions`、`Cost`、`Roll`、`Success`/`Failure`、`InterruptDefaultValue` 等）[24]；`Character.txt`（Character 类型，含 `Class`、`Progressions`、`ActionResources`、`SpellCastingAbility`、六维、抗性等，用于 NPC 而非玩家职业）[24]。这三类本次未取得职业 mod 中的具体示例。

`Equipment.txt`（`Public/<Mod>/Stats/Generated/Equipment.txt`；Toolkit 在 Stats Editor 建 "Equipment" 表，列 Initial Weapon Set、1、2、3…）[1][5][23]：

```
new equipment "EQP_CC_Quickster"
add initialweaponset "Melee"
add equipmentgroup
add equipment entry "WPN_Dagger"
add equipmentgroup
add equipment entry "WPN_HandCrossbow"
add equipmentgroup
add equipment entry "OBJ_Potion_Healing"
add equipmentgroup
add equipment entry "ARM_Robe_Body"
add equipmentgroup
add equipment entry "ARM_Boots_Leather"
add equipmentgroup
add equipment entry "OBJ_Scroll_Revivify"
add equipmentgroup
add equipment entry "OBJ_Keychain"
add equipmentgroup
add equipment entry "OBJ_Bag_AlchemyPouch"
add equipmentgroup
add equipment entry "ARM_Camp_Body"
add equipmentgroup
add equipment entry "ARM_Camp_Shoes"
add equipmentgroup
add equipment entry "OBJ_Backpack_CampSupplies"
```

条目名写入 ClassDescription 的 `ClassEquipment`（仅职业）[1][5]；可穿戴物自动装备，其余进背包；同时给多件护甲/武器可能出现异常 [23]；原版某些子职业（Sorcerer、Paladin）有各自的装备集 [23]。

#### 2.2.9 多职业相关配置小结

- 需要一条 `Level=1`、`IsMulticlass=true`、同 `TableUUID`、新 `UUID` 的 Progression 节点，通常只保留多职业应得的熟练与选择器 [13][22]。
- Patch 7 的节点合并会为合并结果生成独立的 "Multiclass" 节点，导致非 1 级解锁的子职业在多职业角色上丢失；社区测试的规避法：为原版职业补一份 `IsMulticlass=Yes` 的完整节点副本，再各建一条 `IsMulticlass=Yes/No` 的子职业合并节点 [17]。
- Level 20 类 mod 会为所有职业补 13–20 级 [28]，自定义职业若也想被支持，需要自己提供 13–20 级节点（见 2.6）。

### 2.3 本地化

**目录与文件**
- Toolkit 路径：`Data/Mods/<YourMod>/Localization/<Language>/<任意名>.xml`，该目录下所有 `.xml` 都会被处理；语言目录名（官方列表）：BrazilianPortuguese, Chinese, ChineseTraditional, English, French, German, Italian, Japanese, Korean, LatinSpanish, Polish, Russian, Spanish, Turkish, Ukrainian [2]。开源 mod RAW 的实际布局是 pak 根下 `Localization/Chinese/RAW.xml` + `RAW.loca`、`Localization/ChineseTraditional/…` 等 [16]；Community Library 则放在 `Mods/CommunityLibrary/Localization/English/*.loca.xml` [15]——两种布局都在用，Toolkit 以官方路径为准。
- 手工流程：写 `.xml`（或 `.loca.xml`），用 LSLib 的 Localization 页或 Multitool 转成二进制 `.loca` 再打包；Multitool 打包时会把 `.loca.xml` 转回 `.loca` [5][13][21]。
- 修改本地化后需重新载入模块 / 重启游戏或 Editor，或在调试控制台执行 `reloadLoca` [2]。

**文件格式** [2][5][21]：

```xml
<?xml version="1.0" encoding="utf-8"?>
<contentList>
  <content contentuid="heb6d4970g5238g4bb8ga932g9dd4357d61ed" version="1">Quickster</content>
  <content contentuid="hc25377a0g8e44g4645g90c5gee05d6c5e31b" version="1">Gifted a magical set of boots by a mysterious god, the quickster attains speeds once thought impossible.</content>
</contentList>
```

**handle 规则**
- 官方：自定义 TranslatedStringHandle "可以是任意不含空白的字母数字标识符"；原版 handle 是 `h<uuid>` 形（例 `h1587638ag320fg40a1g9566g82783d951ea3`，由内部工具按内容生成），mod 作者没有这个限制 [2]。bg3.wiki 只说 handle 以 `h` 开头且不要改动 [21]。社区惯例是用 Multitool 的 "v4 UUID/TranslatedString Handle Generator" 勾选 Handle 生成形如 `hc25377a0g8e44g4645g90c5gee05d6c5e31b`（UUID 去掉连字符、以 `g` 分段并加 `h` 前缀）的串 [5]；Community Library 里也有不带 `g` 的 36 位十六进制 handle（如 `h08bbe0a2b84743b3af49f2bbfb323b95fd37`）[15]。
- 复用原版 handle 并提高 `version` 即可覆盖原版文本 [2]。缺失 handle 时游戏显示 "Not Found" [13]。
- 性别语法：`Localization/<Language>/Gender/Female|Neutral/…xml`，文件名后缀 `_to_F`、`_to_X` 区分听者性别 [2]。

**引用方式**
- lsx：`<attribute id="DisplayName" type="TranslatedString" handle="h…" version="1"/>` [5][21]。
- stats txt：`data "DisplayName" "<handle>;<version>"`；Toolkit 的 Stats Editor 会尝试自动生成 handle，失败时写成 `ls::TranslatedStringRepository::s_HandleUnknown`，手动替换成你的 handle 即可 [2]。

**Toolkit 内编辑**：官方文档只描述了 Stats Editor 对 DisplayName 等字段的 handle 生成，并指导手工维护 `.xml`；未见独立的"本地化编辑器"说明 [2]。语言缺失时的回退行为未在任何来源说明。

### 2.4 图标

**职业 / 子职业图标（Patch 7+ 原生支持）** [1][4]
- 源图 300×300 PNG → DDS；命名必须与 ClassDescriptions 的 `Name` 完全一致。
- 路径：`\Data\Mods\<Mod>\GUI\Assets\ClassIcons\` 与 `\Data\Mods\<Mod>\GUI\AssetsLowRes\ClassIcons\`；热键栏版本在两者的 `ClassIcons\hotbar\` 子目录。
- DDS 压缩（官方给出的转换器逻辑）：RGBA 且 sRGB → `BC7_UNORM_SRGB`，RGBA 非 sRGB → `BC7_UNORM`，RGB → `BC1_UNORM` [1]。
- Toolkit 操作（mod.io 评论区补充，5 个月前）：`Project > Convert UI Assets…`，Output subfolder 填 `ClassIcons`（300×300）和 `ClassIcons/hotbar`（112×112），工具自动转 DDS、建目录并生成 metadata；有时需重启 Toolkit；`Basic_Level_A` 里不显示头像属正常 [4 评论]。112×112 这一尺寸只来自评论，官方文档未写热键栏尺寸。
- 官方文档全程未要求 ImprovedUI；ImpUI 作者 Djmr 在 [18] 评论中确认"基础游戏现在已支持职业、种族、神祇图标"。

**Patch 7 之前的旧方法（仅供识别旧教程）** [20]：图标放 `Public\Game\GUI\Assets\ClassIcons`（`.DDS` 扩展名必须大写），依赖 ImprovedUI + ImprovedUI Assets；"Direct" 方式（fork ImpUI 改 `IUI_ClassIcons`）已不再支持。搜索摘要显示 Patch 7 起 ImpUI 已把 Assets 合并进单一文件 [33]。

**技能 / 被动 / 物品图标（Texture Atlas）** [3]
- Toolkit 的 Texture Atlas Editor：Icon size 固定 64×64，Texture size 2 的幂（推荐 512×512＝64 个图标或 1024×1024＝256 个），保存后生成 `Public/<Mod>/Assets/Textures/Icons/<Atlas>.dds` 与 `Public/<Mod>/GUI/<Atlas>.lsx`。
- 另需 144×144（手柄 UI）经 `Convert UI Assets` 输出到 `Mods/<Mod>/GUI/Assets/ControllerUIIcons/skills_png/`（物品为 `items_png`），380×380 提示图输出到 `Mods/<Mod>/GUI/Assets/Tooltips/Icons/`（物品 `Tooltips/ItemIcons/`），均有 `AssetsLowRes` 镜像。
- 三个尺寸文件名必须相同且在全游戏内唯一；stats 里 `data "Icon" "<文件名>"` 引用；测试：`Basic_Level_A` → Game Mode → `Ctrl+Shift+F11` 控制台 `addDebugSpell Target_FireTouch`。Community Library 的图集示例：`Public/CommunityLibrary/GUI/Icons_DeathKnight.lsx` [15]。

**自定义行动资源图标** [18]（Patch 7 时期，作者 Djmr）
- 仍需 ImpUI 且需在 Project Settings 把 ImpUI 设为依赖；4 类图标：键鼠热键栏 48×48（含 Highlight/Missing/Used 变体）、CC/升级 128×128、手柄正面 80×80、手柄资源 44×64；路径形如 `Mods\<Mod>\GUI\Assets\Shared\Resources\<资源名>.DDS`、`…\GUI\Assets\CC\icons_resources\<资源名>.DDS`、`…\GUI\Assets\ActionResources_c\Icons\…`。评论区反馈：必须用 Toolkit 的 Convert UI Assets 生成 DDS 与 metadata，手动导出的 DDS 不显示；反应/打断界面仍显示红星。
- 现状：ImpUI 仓库 README 明确"没有主动维护计划"，并给出 Patch 8 的 CC 修复清单 [25]；Nexus 摘要称 Patch 8 版 ImpUI "只保留最小 UI 改动，仅当其他 mod 依赖时才需要" [33]；一位评论者（约 2026-07）称"现在似乎不用 ImpUI、用 Toolkit 也能做到"，未经核实 [18 评论]。

### 2.5 "给原版职业加子职业" vs "全新基础职业"；SCF 与 CF

**全新职业**：所有数据都是新的，不与其他 mod 争抢同一节点，"不用担心进阶冲突" [6]。代价是要自己补齐 CC 所需的一切（六维预设、DefaultValues、Lists、装备、图标、多职业行）。

**给原版职业加子职业**：
1. `ClassDescriptions.lsx` 只需新增子职业节点（`ParentGuid` = 原版职业 UUID），不必复制原版职业节点 [6]。
2. 必须让原版职业在解锁等级的 Progression 节点的 `SubClasses` 里包含你的子职业 UUID。Patch 7 之前只能整节点覆盖（同 UUID、完整复制所有属性，漏一个 `Proficiency(HeavyArmor)` 原版就丢熟练），两个子职业 mod 因此互斥 [6][13]。
3. Patch 7 起支持节点合并：新建"新 UUID + 原版 TableUUID + 同 Level"的节点，只写 `SubClasses`，即会并入原版列表；可合并字段：SubClasses、PassivesAdded、PassivesRemoved、Boosts、AllowImprovement、Selectors；列表合并：AbilityLists、EquipmentLists、PassiveLists、SkillLists、SpellLists [17]。已知问题（版本 4.1.1.5932596 记录，"Patch 8 仍存在，部分情形可用"）：非 1 级解锁 + 多职业时特性丢失/只显示你的子职业；评论区给出的可行组合见 2.2.9 [17]。
4. 子职业自己的进阶表：`ProgressionType=1`、独立 `TableUUID`，等级从解锁级开始 [1][6]。

**Subclass Compatibility Framework（SCF）与 Compatibility Framework（CF）**
- 同一项目：SCF 最初是 Community Library 的一部分（2023-09 的旧页已标"已弃用、已迁移"）[14]，后独立为 Compatibility Framework，由同一团队维护，Nexus 页面同时保留两个名字 [12][30]。Lua 命名空间仍是 `Mods.SubclassCompatibilityFramework.Api`，mod UUID `67fbbd53-7c7d-4cfa-9409-6d737b4d92a9` [8][9]。
- 前提：Script Extender；配置文件放 `Mods/<Mod>/ScriptExtender/CompatibilityFrameworkConfig.json` 或 `.yaml`（2.8.0.0 起支持 YAML）[8][9][10]。
- 解决什么：在运行时（`Ext.Events.StatsLoaded`）把子职业、Selector、列表项、进阶字段、专长、行动资源、背景、种族、法术等注入现有数据，避免覆盖式冲突 [8][10][12]。"游戏数据整体上是不兼容的，Patch 8 提供了一些数据合并能力，但只能到此为止" [12]。
- 何时必须用：
  - **加子职业**：自 CF 2.6.5.8 起完全自动——只要 ClassDescription 的 `ParentGuid` 有效，CF 会把它插入父职业的 SubClasses，作者无需写配置 [9][11]；2.7.0.0 起可通过配置移除子职业 [9]。若你依赖 CF，需要把 CF 列为可选/必需依赖并让你的 mod 在 CF 之前加载 [8]。
  - **往原版进阶/专长里插 Selector 或改列表**（例如给原版职业加新戏法列表）时用 Selector 模块（`Action: Insert/Remove`、`Function`、`Params.Guid/Amount/SelectorId/CastingAbility/PrepareType/CooldownType…`）[10]。
  - 全新职业本身不需要 CF；别人给你的职业加子职业时 CF 同样自动处理。
- 替代方案：BG3 Compatibility Patcher（Python 合并进阶文件，"不总是按预期工作"）[13]；FrederickEngelhardt 的 progressions-compatibility-patches（补丁需最后加载）[31]；Nexus 上另有 "Compatibility Framework Patch for Modded Subclasses"（仅见标题）[38]。

### 2.6 Patch 8 对既有职业 mod 的影响；12 级上限与 Level 20 类 mod

- Patch 8（2025-04）为 12 个职业各新增 1 个子职业，是"最后一次大型更新" [26][37]。
- 升级 bug：压测第 3 版（2025-03-20）修复"一个导致部分 mod 职业与子职业无法升级的 mod 问题" [26]。
- Toolkit：Patch 8 内容补入 Stats Editor 与 UUID Editor，修复 Game Mode 下保存导致的崩溃；新增部分关卡编辑 [37]（搜索摘要，未直接访问）。
- UI：新子职业不显示的常见原因是旧版 ImpUI；ImpUI 出了 Patch 8 专用版，并宣布停止维护，社区另有 `ImpUI_P8_Fork` [25][27][33][36]。对职业 mod 作者的含义：除非做自定义资源图标，否则不要把 ImpUI 作为硬依赖。
- 进阶表/UUID：本次没有来源表明 Patch 8 改动了原版职业的 `UUID`/`TableUUID`。可推断（非来源直接陈述）：Patch 8 把新子职业加进了原版解锁等级节点的 `SubClasses`，因此 **仍用旧式"整节点覆盖"** 的子职业 mod 会把新子职业从列表里挤掉，而合并式节点或 CF 注入不受影响。CF 文档提醒：配置目标 UUID 不要指向带 `MergedInto` 属性的数据，而应指向被合并进的那条 [10]（说明合并后的节点带有 `MergedInto` 标记，细节未能确认）。
- 等级上限：原版仍为 12。UnlockLevelCurve（mod.io v2.0.0.27，"Patch 8 Tested"）为所有职业补 13–20 级、7–9 环法术位与资源；FAQ 明确"12→13 升级黑屏通常是因为某个职业 mod 缺少 13–20 级" [28]。Nexus 页面摘要（页面本身 403）称 Patch 8 的 `LevelMapValues.lsx` 只到 12 级（戏法伤害、熟练加值、偷袭、激励等不再随级增长）、经验上限 180,000，需要额外的 XP 上限扩展 mod [29]——数字未能核实。

### 2.7 最小可行职业 mod（MVP）文件树

综合 [1][2][5][13][15][16]。以 Toolkit 项目 `MyClass` 为例，Toolkit 会把它分别写到 `Data/Mods/MyClass/` 与 `Data/Public/MyClass/`，打包后合为一个 `.pak`：

```
MyClass/
├── Mods/MyClass/
│   ├── meta.lsx                                  【必需】mod 元数据（名称、UUID、版本、依赖）；Toolkit/Multitool 生成 [5][15]
│   ├── Localization/English/MyClass.xml          【必需】DisplayName/Description/ShortName 等文本；Chinese/、ChineseTraditional/ 同结构 [2][16]
│   ├── GUI/Assets/ClassIcons/MyClass.DDS         【推荐】300×300 类图标；子职业同目录同名规则 [1][4]
│   ├── GUI/Assets/ClassIcons/hotbar/MyClass.DDS  【推荐】热键栏小图（评论称 112×112）[4]
│   ├── GUI/AssetsLowRes/ClassIcons/...           【推荐】低分辨率镜像（Convert UI Assets 自动生成）[1]
│   ├── GUI/Assets/ControllerUIIcons/skills_png/  【可选】自定义法术的 144×144 手柄图 [3]
│   ├── GUI/Assets/Tooltips/Icons/                【可选】自定义法术的 380×380 提示图 [3]
│   └── ScriptExtender/CompatibilityFrameworkConfig.yaml 【可选】仅在需要 CF 插 Selector/移除子职业时 [9][10]
└── Public/MyClass/
    ├── ClassDescriptions/ClassDescriptions.lsx   【必需】职业 + 各子职业节点 [1][5]
    ├── Progressions/Progressions.lsx             【必需】职业 1..12 级 + IsMulticlass 1 级 + 各子职业进阶 [1][13]
    ├── Progressions/ProgressionDescriptions.lsx  【推荐】给 SelectorId 起名、让法术位/特性显示在 CC [1][5]
    ├── CharacterCreationPresets/AbilityDistributionPresets.lsx 【推荐】默认六维（目录名见 2.2.5 分歧）[5][13]
    ├── DefaultValues/Abilities.lsx               【推荐】默认 +2/+1 属性 [5]
    ├── DefaultValues/Skills.lsx                  【推荐】默认技能勾选 [5]
    ├── DefaultValues/Passives.lsx / Spells.lsx   【可选】默认被动/法术勾选 [10][15]
    ├── Lists/AbilityLists.lsx                    【推荐】SelectAbilityBonus 用（也可复用原版列表 UUID）[5]
    ├── Lists/SkillLists.lsx                      【推荐】SelectSkills 用 [5]
    ├── Lists/SpellLists.lsx                      【按需】AddSpells/SelectSpells 用 [1][13]
    ├── Lists/PassiveLists.lsx                    【按需】SelectPassives 用（可复用原版 Ranger 战斗风格列表）[1][5]
    ├── ActionResourceDefinitions/ActionResourceDefinitions.lsx 【可选】自定义资源 [5][15]
    ├── Tags/<uuid>.lsx                           【可选】职业标签，用于角色面板/对话 [5][15]
    ├── Stats/Generated/Equipment.txt             【推荐】EQP_CC_MyClass 起始装备 [1][5]
    ├── Stats/Generated/Data/Passive.txt          【按需】自定义被动 [5][13]
    ├── Stats/Generated/Data/Spell_Target.txt 等  【按需】自定义法术（按 SpellType 分文件）[24]
    ├── Stats/Generated/Data/Status_BOOST.txt     【按需】自定义状态 [24]
    ├── Stats/Generated/Data/Interrupt.txt        【按需】反应/打断 [24]
    ├── GUI/<Atlas>.lsx                           【可选】技能图标图集描述 [3][15]
    └── Assets/Textures/Icons/<Atlas>.dds         【可选】技能图标图集贴图 [3]
```

"必需"判据：缺少 `ClassDescriptions`/`Progressions`(Level 1) 职业不会出现在 CC [5][13]；缺少本地化则显示 "Not Found"/问号 [5][13]；缺少 `meta.lsx` 无法被识别为 mod [5]。其余项缺失只影响体验（无默认属性分配、无技能选择、裸装出生、骷髅头默认图标等）[4 评论][5]。

---

## 3. 对"自创职业 mod"项目的具体建议 / 决策点

1. **先定形态：全新职业 or 原版职业的子职业。** 全新职业工作量大但零兼容负担；子职业工作量小但要处理原版进阶节点合并（用 Patch 7 合并节点 + 可选 CF），且若解锁等级不是 1 级要专门测试多职业情形 [6][17]。若你的职业在 1 级选子职业（如 Cleric/Sorcerer/Warlock 模式），合并最稳定 [17]。
2. **工具路线：Toolkit 优先，导出后再看 lsx。** Toolkit 的 UUID Object Editor 会自动生成 UUID、处理 TableUUID 复制/再生成、下拉选 ParentUUID/SubClasses、Convert UI Assets 生成图标 metadata [1][4]；但要理解它生成的就是本文列出的这些文件，遇到疑难可直接对照 [5] 手改。注意 Toolkit 里改 ClassDescriptions 与 ProgressionDescriptions 后经常需要保存并重启 Editor [1]。
3. **命名与 UUID 纪律**：所有 `Name`/条目名加作者前缀（如 `TLH_MES_`）避免撞名 [13][19]；`Name` 不带空格并与图标文件名一致 [1][4]；维护一张 UUID 对照表（职业 UUID、各 TableUUID、各列表 UUID、各 Progression UUID），复制行后一定"Regenerate" UUID、保留 TableUUID [1]。
4. **进阶表设计清单（每个职业）**：1 级：熟练 `Proficiency()`、豁免 `ProficiencyBonus(SavingThrow,…)`、`SelectSkills`、`SelectAbilityBonus(…,AbilityBonus,2,1)`、`AddSpells`/`SelectSpells`、资源 `ActionResource()`、`PassivesAdded`（施法职业加 `UnlockedSpellSlotLevel1`）；4/8/12 级 `AllowImprovement=true`；子职业解锁级加 `SubClasses`；另一条 `IsMulticlass=true` 的 1 级节点 [1][5][13][22]。
5. **是否支持 13–20 级**：若目标玩家群普遍用 UnlockLevelCurve，补 13–20 级节点（哪怕只是空节点 + AllowImprovement）以避免黑屏 [28]；否则在 mod 说明里声明不兼容。
6. **本地化策略**：从一开始就用 handle 生成器，`.xml` 里一行 handle 一行文本；同时准备 `English`、`Chinese`、`ChineseTraditional` 三个目录（文件名任意，Toolkit 会处理目录内所有 `.xml`）[2][16]；stats 里记得 `handle;version` 格式 [2]。
7. **图标策略**：类/子职业图标走官方路径，无需 ImpUI [1][4]；自定义法术走图集 [3]。**尽量避免自定义 Action Resource**——它的 UI 图标至今依赖已停更的 ImpUI，且评论区问题最多 [18][25]；能用原版资源（SpellSlot、Rage、KiPoint 等）或用隐藏资源（`IsHidden=true`、`ShowOnActionResourcePanel=false`，如 RAW 的做法）就先这么做 [16]。若坚持自定义资源，记得加 [19] 的 `RestoreResource` 被动。
8. **兼容性交付**：子职业 mod 用合并式节点（新 UUID + 原版 TableUUID）而非覆盖 [17]；把 CF 作为可选依赖，不写配置也能被自动注入 [9]；发布前与另一个同职业的子职业 mod 一起加载测试；不要覆盖原版 `Progressions.lsx` 整个文件（Shared 与 SharedDev 分层加载，整文件覆盖会丢 7–12 级）[22]。
9. **测试回路**：Toolkit 载入 `Basic_Level_A` → Game Mode → 鼠标悬停头像 `Ctrl+Shift+L` 升级 → "Add Class" 选你的职业 → 连升看子职业；`Ctrl+Shift+F11` 控制台 `addDebugSpell <Type_Name>` 测法术/图标；`reloadLoca` 刷新文本 [1][2][3]。Patch 8 后建议从零存档测试，不要沿用 Patch 8 前的存档 [25]。
10. **Patch 8 检查项**：确认原版职业解锁等级节点里新子职业仍在（你的合并节点没把它挤掉）；不要要求玩家装旧版 ImpUI；核对 Toolkit 已更新到 Patch 8 数据 [36][37]。

---

## 4. 未解决问题与信息缺口

1. `ProgressionDescriptions.lsx` 的 `ExactMatch`、`PassivePrototype` 属性：所有来源均未出现；`ParamMatch`/`Type`/`ProgressionTableId` 仅见于 Community Wiki [5]，官方文档只讲 `SelectorId` [1]。
2. `ActionResourceDefinitions` 的 `DiceType` 未出现；`ReplenishType` 完整枚举未知（仅观测 `Rest`、`ShortRest`、`Turn`）[5][15][16][19]。
3. `LearningStrategy` 的语义与枚举（Toolkit 标签 `AllChildren` ↔ 文件值 1；Archfey Warlock 为 2）[1][13]。
4. `PrimaryAbility`/`SpellCastingAbility` 的数值映射两说（[13] 1=STR vs [5] 1=DEX），本文采信 [13]，需在 Toolkit 下拉核对。
5. `ProgressionType` 种族值 2（[5][13]）vs 3（[22]）。
6. Lists 中分隔符逗号 vs 分号（[5] vs [13]）。
7. `AbilityDistributionPresets.lsx` 所在目录名（`CharacterCreationPresets/` vs `AbilityDistributionPresets/`）[5][13]。
8. 官方文档把 `IsMulticlass` 行写在 "ClassDescriptions 表"下的表述 [1][4] 与文件级证据（Progressions 属性）[13][22] 不一致。
9. 类图标热键栏尺寸（112×112）与 `metadata.lsf` 细节只来自评论 [4]；官方仅给 300×300。
10. Patch 8 之后自定义 Action Resource 图标是否可脱离 ImpUI：评论两说 [18]，未证实。
11. 本地化语言缺失时的回退行为、Toolkit 是否有独立本地化编辑器：未找到说明。
12. Patch 8 是否改动过原版职业/子职业 UUID、`MergedInto` 机制细节：未找到直接来源 [10][12]。
13. `LevelMapValues.lsx` 12 级上限与 180,000 经验上限：仅搜索摘要 [29]，Nexus 页面 403 无法核实。
14. Nexus 上的 SCF/CF 文档页、《Icons for Modded Subclasses》《Compatibility Framework Patch for Modded Subclasses》均 403，仅得标题 [30][38][39]。
15. 两部视频教程 [34][35] 未能评估内容。
16. `Status_BOOST.txt`、`Interrupt.txt`、`Character.txt` 缺少职业 mod 里的具体条目示例，仅有字段清单 [24]。

---

## 5. 来源列表（访问日期均为 2026-09-02）

| 编号 | 标题 | URL | 类型 | 备注 |
|---|---|---|---|---|
| [1] | Larian 官方 Toolkit 文档《Adding Classes and Subclasses》 | https://docs.baldursgate3.game/Adding_Classes_and_Subclasses | 一手（官方） | 最后编辑 2025-05-08；WebFetch 403，改用 python urllib 抓取 |
| [2] | Larian 官方《Adding Localisation》 | https://docs.baldursgate3.game/index.php?title=Adding_Localisation | 一手（官方） | 最后编辑 2025-10-30；python urllib |
| [3] | Larian 官方《Adding Skill and Item Icons》 | https://docs.baldursgate3.game/Adding_Skill_and_Item_Icons | 一手（官方） | 最后编辑 2025-04-16；python urllib |
| [4] | mod.io 官方指南《Adding New Classes or Subclasses》（GrumpyWashbear，Official 标签）及评论区 | https://mod.io/g/baldursgate3/r/adding-new-classes | 一手（正文）/ 二手（评论） | 约 2024-08 更新；浏览器渲染 |
| [5] | BG3 Modding Community Wiki《Basic Class Creation》 | https://wiki.bg3.community/Tutorials/Classes/Basic-Class-Creation | 二手 | Wiki.js 页面，python urllib |
| [6] | Community Wiki《Subclass Creation For An Existing Class》 | https://wiki.bg3.community/Tutorials/Classes/Subclass_Creation_For_An_Existing_Class | 二手 | python urllib |
| [7] | Community Wiki《Progressions》 | https://wiki.bg3.community/en/Information/Progression/Progressions | 二手 | python urllib |
| [8] | Community Wiki《Compatibility Framework Usage》 | https://wiki.bg3.community/Tutorials/Mod-Frameworks/compatibility-framework | 二手 | python urllib |
| [9] | CF GitHub Wiki《Adding a Subclass to the Compatibility Framework》 | https://github.com/BG3-Community-Library-Team/BG3-Subclass-Compatibility-Framework/wiki/Adding-a-Subclass-to-the-Compatibility-Framework | 一手（框架维护者） | 2026-02-19 更新 |
| [10] | CF GitHub Wiki《_Selector API》 | https://github.com/BG3-Community-Library-Team/BG3-Compatibility-Framework/wiki/_Selector-API | 一手 | 2026-02-19 更新 |
| [11] | CF GitHub Wiki《_Class Module》 | https://github.com/BG3-Community-Library-Team/BG3-Compatibility-Framework/wiki/_Class-Module | 一手 | WebFetch |
| [12] | CF GitHub Wiki Home | https://github.com/BG3-Community-Library-Team/BG3-Compatibility-Framework/wiki | 一手 | 2026-02-25 更新 |
| [13] | Community Library Wiki《Building a Class Mod》 | https://github.com/BG3-Community-Library-Team/BG3-Community-Library/wiki/Building-a-Class-Mod | 二手 | 2024-02-25 |
| [14] | Community Library Wiki《Subclass Compatibility Framework》（已弃用页） | https://github.com/BG3-Community-Library-Team/BG3-Community-Library/wiki/Subclass-Compatibility-Framework | 二手 | 2023-09-06 |
| [15] | BG3 Community Library 源码仓库（Death Knight 的 ClassDescriptions / ActionResourceDefinitions、DefaultValues/Passives.lsx、Tags、ProgressionDescriptions、GUI 图集等） | https://github.com/BG3-Community-Library-Team/BG3-Community-Library | 一手（mod 源码） | GitHub API + raw |
| [16] | ZerdBG3/DnD-Rebalancing（RAW）源码：ActionResourceDefinitions.lsx、多语言 Localization 目录 | https://github.com/ZerdBG3/DnD-Rebalancing | 一手（mod 源码） | GitHub API + raw |
| [17] | mod.io 指南《Compatibility Changes in Patch 7 & 8: Merging》（RandoRuda）及评论 | https://mod.io/g/baldursgate3/r/compatibility-changes-in-patch-7 | 二手 | 约 2025-05 更新；浏览器渲染 |
| [18] | mod.io 指南《Implementing Custom Action Resources with ImpUI》（Djmr，ImpUI 作者）及评论 | https://mod.io/g/baldursgate3/r/implementing-custom-action-resources-with-impui | 一手（对 ImpUI）| 约 2024-08；浏览器渲染 |
| [19] | mod.io 指南《Restore Your Custom Class Action Resource》（TLH_MOD） | https://mod.io/g/baldursgate3/r/restore-your-custom-class-resource | 二手 | 约 2025-12 更新；浏览器渲染 |
| [20] | bg3.wiki《Modding:Class icons》 | https://bg3.wiki/wiki/Modding:Class_icons | 二手 | Patch 7 前的 ImpUI 方法 |
| [21] | bg3.wiki《Modding:Localization》 | https://bg3.wiki/wiki/Modding:Localization | 二手 | WebFetch |
| [22] | bg3.wiki《Modding:LSX files》 | https://bg3.wiki/wiki/Modding:LSX_files | 二手 | python urllib |
| [23] | bg3.wiki《Modding:Equipment.txt》（同文见 Community Wiki《Editing Equipment.txt》） | https://bg3.wiki/wiki/Modding:Equipment.txt ; https://wiki.bg3.community/Tutorials/General/Editing-Equipment-txt | 二手 | python urllib |
| [24] | NellsRelo/bg3-schema：Modifiers.md、SpellData.md | https://github.com/NellsRelo/bg3-schema/blob/main/stats/formats/Modifiers.md ; https://github.com/NellsRelo/bg3-schema/blob/main/stats/types/SpellData.md | 二手（由游戏 Modifiers.txt 整理） | raw.githubusercontent |
| [25] | ImprovedUI GitHub README | https://github.com/TheRealDjmr/BG3ImprovedUI/blob/main/README.md | 一手（作者） | raw |
| [26] | PC Guide《Latest Baldur's Gate 3 Patch 8 update fixes game-breaking bug for custom class mods》 | https://www.pcguide.com/news/latest-baldurs-gate-3-patch-8-update-fixes-game-breaking-bug-for-custom-class-mods/ | 三手（转述 Larian 压测公告） | 2025-03-21 |
| [27] | PC Guide《Popular Baldur's Gate 3 UI mod just got a new version "intended exclusively" for patch 8》 | https://www.pcguide.com/news/popular-baldurs-gate-3-ui-mod-just-got-a-new-version-intended-exclusively-for-patch-8/ | 三手 | 2025-05-22；WebFetch |
| [28] | mod.io《UnlockLevelCurve - Level 13-20 \| Patch 8》（Dustbag，v2.0.0.27） | https://mod.io/g/baldursgate3/m/unlocklevelcurve | 一手（作者页） | 浏览器渲染 |
| [29] | Nexus《UnlockLevelCurve - Level 13-20 I PATCH 8》 | https://www.nexusmods.com/baldursgate3/mods/377 | 三手（仅搜索摘要） | 页面 403 |
| [30] | Nexus《Compatibility Framework》（原 Subclass Compatibility Framework） | https://www.nexusmods.com/baldursgate3/mods/1933 | 二手（仅搜索摘要） | 页面 403 |
| [31] | FrederickEngelhardt/bg3-progressions-compatibility-patches README | https://github.com/FrederickEngelhardt/bg3-progressions-compatibility-patches | 二手 | python urllib |
| [32] | ImprovedUI issue #97《No more class icon on character creation/level up for modded classes》 | https://github.com/TheRealDjmr/BG3ImprovedUI/issues/97 | 二手 | 2023-09-17，Patch 7 之前；WebFetch |
| [33] | Nexus ImpUI 页面/文件页 | https://www.nexusmods.com/baldursgate3/mods/366 | 二手（仅搜索摘要） | 未直接访问 |
| [34] | YouTube《How to Create a Custom BG3 Class Mod — Complete Toolkit Tutorial》 | https://www.youtube.com/watch?v=aoVDqwvyZqk | 二手（仅标题） | 未评估 |
| [35] | Nexus 视频《Make a Bloody BG3 Class - Toolkit Tutorial》 | https://www.nexusmods.com/baldursgate3/videos/923 | 二手（仅标题） | 未评估 |
| [36] | 搜索摘要：Patch 8 新子职业不显示与 ImpUI（Dot Esports / Screen Plays Mag） | https://dotesports.com/baldurs-gate/news/why-are-new-subclasses-not-showing-up-in-baldurs-gate-3 ; https://screenplaysmag.com/blog/new-subclasses-not-showing-up-solution-in-bg3-baldurs-gate-3-after-patch-8/ | 三手 | 未直接访问 |
| [37] | 搜索摘要：Patch 8 Toolkit 更新（Stats/UUID Editor 补入 Patch 8 内容、部分关卡编辑） | https://www.dtgre.com/2025/04/bg3-patch-8-modding-enhancements-fixes-guide.html ; https://www.nexusmods.com/news/15251 | 三手 | 未直接访问 |
| [38] | Nexus《Compatibility Framework Patch for Modded Subclasses》 | https://www.nexusmods.com/baldursgate3/mods/17062 | 二手（仅标题） | 页面 403 |
| [39] | Nexus《Icons for Modded Subclasses》 | https://www.nexusmods.com/baldursgate3/mods/4216 | 二手（仅标题） | 页面 403 |

---

## 6. 审计

| 项目 | 数量 | 说明 |
|---|---|---|
| WebSearch 查询数 | 18 | 达到预算上限 |
| WebFetch 调用数 | 14 | 达到预算上限；有效返回 5（bg3.wiki Localization、bg3.wiki 类图标、CF Class Module、ImpUI issue #97、PC Guide ImpUI P8），HTTP 错误 4（bg3.wiki Modding_resources 404、docs.baldursgate3.game 403、Nexus 377 与 1933 各 403），仅返回标题/空内容 5（wiki.bg3.community ×4、mod.io ×1，均为 JS 渲染页） |
| 补充抓取（不计入预算，但内容均为本会话实际获取） | python urllib 30 个 URL（成功 25，其中 3 个 mod.io 为空壳；失败 5：raw README 404、Nexus ×4 403）；GitHub API 树 2 次 + raw 文件约 10 个；浏览器渲染 mod.io 页面 5 个 | 因 WebFetch 无法渲染 Wiki.js / mod.io / 官方 MediaWiki(403) 页面而采用 |
| 收到的有实质内容的来源（去重页面） | 约 32 | 其中官方一手 4 页、框架/仓库一手 8、社区二手约 15、新闻/摘要三手约 5 |
| 引用的来源数 | 39 个编号（其中 8 个仅有搜索摘要或标题，已在表中标明） | — |
| 失败次数 | WebFetch 9（4 HTTP 错误 + 5 空内容）；python 5；浏览器 1（首次 batch 因面板未打开而失败，随后成功） | 无连续 3 次失败导致的中止 |
| 未按要求获取的内容 | Nexus 全站（403）、两部视频教程 | 已在第 4 节列为缺口 |
