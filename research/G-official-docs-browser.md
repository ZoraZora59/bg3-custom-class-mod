# 子课题 G（主控补充）：用内置浏览器直读官方文档与 mod.io 准则

- 调研日期：2026-09-02
- 背景：A/B/D/F 四个代理的 WebFetch 对 `docs.baldursgate3.game`、`mod.io`、`larian.com` 均被 403/JS 渲染拦截，只能引用搜索摘要。主控用 Claude 内置浏览器直接打开页面并提取正文，本文件记录一手原文要点，供合成时替换"仅摘要"结论。
- 引用规则：`[Gn]` 指向文末来源；均为一手（官方站点正文，浏览器直读）。

## 1. 官方文档站结构 [G1]
- 站点自称 "the official home of documentation on the Baldur's Gate 3 Toolkit and all things modding"。
- Getting Started：Installing the Toolkit / Creating a New Mod / Publishing a Mod / Best Practices；Editor：Navigation / Shortcuts and Tips / Overriding Resources。
- Guides by Topic：**Classes and Subclasses（Adding Classes and Subclasses）**、Spells and Skills（Making a Basic Spell / Making a Projectile Spell / Projectiles）、Equipment、Hair and Beards、Scripting（Osiris、Anubis、Journal）、UI（Setting Up / Extending UI / Generating Icons for Character Creation / Adding Skill and Item Icons / Adding Dice）、VFX（4 部分）、Animation、Localisation（Adding Localisation）、Photo Mode。
- 页面 URL 形如 `https://docs.baldursgate3.game/index.php?title=<Title_With_Underscores>`。

## 2. Installing the Toolkit [G2]
- 需要 Larian 账号 + mod.io 账号并互相关联；创建 mod.io 账号后"send that mod.io username to our community team to gain access to the Baldur's Gate 3 mods page and guides hosted on mod.io"。
- Steam：Toolkit 在商店 Tools 分类免费；另需在 BG3 属性 → DLC 中启用 **"BG3 Toolkit Data" DLC**（Editor 数据）。GOG：GOG 商店有 Toolkit，同样要在 Manage installation → Configure → DLC 启用 BG3 Toolkit Data。
- 页面未列系统要求（内存/显存数字来自 Steam 商店页，见 A 报告）。

## 3. Creating a New Mod [G3]
- 首次启动要填 Data 路径（Steam 默认 `C:\Program Files (x86)\Steam\steamapps\common\Baldur's Gate 3\Data`）；路径中不能有 `|`；配置在 `%LOCALAPPDATA%\Larian Studios\Glasses\Config.xml`。
- 新建工程后需选一个关卡加载，建议小关卡 `WLD_Crashsite_D`（Act_1A_WLD）。
- **工程文件分布在 Data 下 5 个目录**：
  1. `Data/Projects/<YourMod>`：工程元数据（可放 thumbnail.png）
  2. `Data/Editor/Mods/<YourMod>`：仅编辑器用，不打包
  3. `Data/Mods/<YourMod>`：会打包——UI 资源、**本地化**、Osiris 脚本、部分关卡数据
  4. `Data/Public/<YourMod>`：会打包——**stats 文件、root templates、UUID 表（Progressions/ClassDescriptions/Lists 等）、资源与图集**
  5. `Data/Generated/Public/<YourMod>`：虚拟纹理、覆盖纹理的 .dds
- 结论：git 仓库要同步的是 3/4/5（以及 1 的 thumbnail），2 可忽略。

## 4. Adding Classes and Subclasses（官方职业教程，示例 Battlemage）[G4]
- 流程：UUID Object Editor → 新建 **Progressions** 表 → 每级一行（Name 无空格；UUID 每行唯一；**TableUUID 同一职业各级共享**；`Level`；`ProgressionType`：0 = class、1 = subclass、2 = race）。
- `Boosts` 列用分号分隔，例：`ActionResource(SpellSlot,2,1);Proficiency(LightArmor);...;Proficiency(MartialWeapons)`。`ActionResource(SpellSlot,2,3)` = 2 个 3 环法术位。
- **SpellLists** 表（Lists 区）每行一个列表；法术引用格式 `Type_TechName`（如 `Target_ShockingGrasp`、`Zone_BurningHands`）。
- `Selectors` 列：`AddSpells(<ListUUID>)`（全给）；`SelectSpells(<ListUUID>,1,0)`（选 1 个、可替换 0 个）；`SelectPassives(<PassiveListUUID>,1,Battlestance)`（第三参数为选择器 ID，用于 ProgressionDescriptions 里改显示名）；`AllowImprovement = Yes` 表示该级可选专长（示例在 4 级）。
- 子职业：Progressions 里新增行，各自独立 TableUUID，`Level = 3`（子职业进入等级），`ProgressionType = 1`；在父职业第 3 级行的 **SubClasses** 列把子职业加进去。
- **ClassDescriptions** 表：Name 与 Progressions 同名；`ProgressionTableUUID` = 职业 TableUUID；DisplayName / Description / ShortName（子职业短名，用于角色面板 "Mace Battlemage"）；PrimaryAbility；SpellCastingAbility；`LearningStrategy` 对 class 一律 `AllChildren`；MustPrepareSpells；CanLearnSpells；`CharacterCreationPose = 0f07ec6e-4ef0-434e-9a51-1353260ccff8`（所有职业相同）；BaseHp（示例 12）；HPPerLevel（示例 7）；`CommonHotbarColumns + ClassHotbarColumns + ItemsHotbarColumns` 必须 = 16（默认 9/5/2）。子职业行 `ParentUUID` 选父职业，其余列复制父职业。
- **多职业支持**：ClassDescriptions 再加一行"副本 Level 1"，UUID 不同、`IsMulticlass = Yes`。
- 教程多次要求"保存后关闭并重启 Editor"才能看到新表/新名称（属官方已知行为）。
- **快速测试**：加载 `Basic_Level_A` → 切到 Game Mode → 鼠标悬停头像按 `Ctrl+Shift+L` 升级 → Level Up 界面 Add Class 选新职业。
- 起始装备：Stats Editor 新建 **Equipment** 表（示例 `EQP_CC_Battlemage`，Initial Weapon Set = Melee，列 1/2/3 选物品如 `WPN_Greatsword`、`ARM_ScaleMail_Body`），再填到 ClassDescriptions 的 `ClassEquipment`（只填 class 不填 subclass）。
- **ProgressionDescriptions** 表：`SelectorId = Battlestance` + DisplayName/Description，用于把 "Class Passives" 改名。
- **职业图标**：300×300 PNG 转 DDS；文件名必须与 ClassDescriptions 的 Name 完全一致；路径 `\Data\Mods\<Mod>\GUI\Assets\ClassIcons`、`\Data\Mods\<Mod>\GUI\AssetsLowRes\ClassIcons`，热键栏版在同目录下 `\hotbar`。DDS 转换：RGBA → `BC7_UNORM`（sRGB 则 `BC7_UNORM_SRGB`），RGB → `BC1_UNORM`。
  - 与 bg3.wiki 的差异：wiki（D 报告 [31]）写的是 `Public\Game\GUI\Assets\ClassIcons` + 大写 `.DDS` + DXT5；官方 Toolkit 流程是 `Mods\<Mod>\GUI\Assets\ClassIcons` + BC7/BC1。两者是"覆盖原版 GUI 目录"与"mod 自有 GUI 目录"两条路径，合成时要并列说明。

## 5. Publishing a Mod [G5]
- Project → Project Settings：Name / Description / Thumbnail 必填；**Dependencies** 标签选依赖（决定加载顺序，被依赖者先加载；改依赖后需重启 Toolkit）；**Conflicts** 标签声明冲突（检测到冲突时自动禁用本 mod 及其独有依赖）。
- 依赖要在 Toolkit 和 mod.io 两边各设一次（Toolkit 管加载顺序，mod.io 管自动下载）。
- **Publish Local**：只生成 `.pak`，无需认证——即 Toolkit 可以作为纯打包器为 Nexus 出包。
- Publish 到 mod.io：Authenticate（接受 Larian 与 mod.io 条款；Steam 或 Larian 账号登录）→ Publish → 自动打开 mod.io File Manager；文件先过"automation scanning"，扫描完成前不能 Go live；期间可编辑 Mod Profile（名称/摘要/描述/成人内容标记/Tags）、Media（截图 png、YouTube）、Dependencies。

## 6. Best Practices [G6]
- 备份：推荐版本控制（历史、回滚、协作、误删保护）。
- 版本：Major（大改/新内容）/ Minor（改进修复）/ Revision（微调）/ **Build 自动递增**，"used when checking if a player has mods that can be updated, or when checking if players can join each other in multiplayer"；测试期不要动版本号。
- 冲突：用 Project Settings → Conflicts 标记，游戏检测到冲突会自动卸载本 mod。

## 7. Adding Localisation [G7]
- 目录：`Data/Mods/<YourMod>/Localization/<Language>/<any>.xml`（该目录下所有 xml 都会被处理）。语言名列表：BrazilianPortuguese、**Chinese、ChineseTraditional**、English、French、German、Italian、Japanese、Korean、LatinSpanish、Polish、Russian、Spanish、Turkish、Ukrainian。
- 骨架：`<contentList date="..."><content contentuid="h000..." version="1">Your line here.</content></contentList>`。
- **自定义 handle 可以是任意无空格字母数字标识符**（如 `MyNewString`）；原版 handle 形如 `h1587638ag320fg40a1g9566g82783d951ea3` 是内部工具按内容生成的；用原版 handle 可覆盖原版文本。
- 改 xml 后需重载模块/重启，或 debug console 执行 `reloadLoca`。
- Stats 对象的 DisplayName：Editor 生成失败会写 `ls::TranslatedStringRepository::s_HandleUnknown`；手工写法 `data "DisplayName" "<Handle>;<version>"`。
- 性别语法：`Localization/<Lang>/Gender/Female|Neutral/`，文件名后缀 `_to_F`、`_to_X`。

## 8. Adding Skill and Item Icons [G8]
- 三种尺寸：**64×64**（热键栏，进 atlas）、**144×144**（手柄 UI，透明底）、**380×380**（tooltip，透明底 + 渐隐），三者同名。
- Atlas：Texture Atlas Editor 新建，图标 64×64，纹理 2 的幂（推荐 512 或 1024；512 = 64 格，1024 = 256 格），保存产物 `Public/<Mod>/Assets/Textures/Icons/<Atlas>.dds` + `Public/<Mod>/GUI/<Atlas>.lsx`。图标文件名不能与游戏已有 icon ID 重复。
- 144/380 用 Project → Convert UI Assets… 转换，输出到 `Mods/<Mod>/GUI/Assets/ControllerUIIcons/skills_png/`、`Mods/<Mod>/GUI/Assets/Tooltips/Icons/`（含 AssetsLowRes）。
- 绑定：法术在 Stats Editor 的 Icon 列填图标名；物品在 Root Template 的 Item > Icon。
- 测试：`Basic_Level_A` → Game Mode → `Ctrl+Shift+F11` 打开 debug console → `addDebugSpell Target_FireTouch` / `spawnItem CONS_Potion_Healing_A`。图标不显示时先保存并重启 Editor。

## 9. mod.io《Modding Guidelines & FAQ》（官方，页面显示最近更新约 7 个月前）[G9]
- Toolkit 支持的修改类型明确包含 **Classes and Subclasses**（"Create new class types or modify existing ones"）、Races、Spells、Scripting Changes（Osiris）、UI 等；"We do not plan to limit modding to only our official pipeline!"（第三方 modding 仍允许）。
- 上传最佳实践：清晰描述（支持 markdown）、相关缩略图、图库、**署名团队成员与灵感来源，但未获许可不得把他人 mod 扩展/翻译/重制后署原作者**、列出依赖、只用相关 tag。
- ToS 要点：所有元素（音频/代码/资源/视觉）必须原创或已获许可；不得歧视/淫秽/损害 Larian 声誉；**不得与任何可识别的第三方品牌、角色或人物相似**；未经许可不得含 Larian 其他游戏或第三方内容；不得含恶意代码。
- 下架情形：大量崩溃报告；描述/标题/tag 不准确或标"仅个人使用"；新增或放大敏感内容；冒犯/露骨/违法内容；歧视性删改；缩略图含裸露；移除基础游戏要素；**解锁付费或成就相关物品**；只用来给付费/第三方 mod 打广告；不尊重他人。多次违规或原样重传会被取消上传权限。
- AI 生图：使用文生图服务做视觉素材需自行遵守该服务的许可条款。
- **主机（PS5/Xbox）排除项**：改动 shader（.bshd）；增加裸露/暴力；内部测试失败；干扰启动或 mod 管理；崩溃；**含不支持的文件格式（.exe、.dll、.zip）**；**新增可玩种族**。主机审核流程：在 mod.io File Manager 勾选平台 → Pending approval → 分批上线 → 每次文件更新需重新测试（描述/图片更新不需要）；建议隐藏而非删除 mod。
- 第三方 mod：游戏内界面会把非 mod.io 的 mod 标为 "third-party"，但不能在该窗口更新。
- **成就**："If you run your game with mods enabled, whether they're third-party or installed through the Mod browser, your in-game achievements will automatically be disabled."（解决 D 报告 E5 的矛盾：以此官方页为准）
- 联机：所有人需装相同 mod；加入大厅时会提示下载缺失 mod 或启停不匹配 mod。
- 长期支持："Outside of critical fixing post-release, we do not currently have the technical capacity to provide long-term support while also lending our focus to future projects."
- **同一 ID 冲突**："all mods will load their files and merge them together. However, if two separate mods edit the same existing ID-based entry, the load order will win out."
- 翻译：mod.io 无翻译分区，用 'translation' tag + 语言 tag。
- 注意：该页**没有**出现"依赖 Script Extender 的 mod 不能上传 mod.io"的原话；只有主机排除 `.dll` 格式。A 报告中该说法来源于搜索摘要，置信度中等，合成时表述为"主机目录不可能包含 SE 依赖；PC 端 mod.io 未见明文禁止，但社区惯例是 SE mod 发 Nexus"。

## 10. 其他补充核实
- **LSLib 源码**：`Divine/Divine.csproj` = `net8.0`、OutputType Exe、PlatformTarget x64、无 UseWindowsForms/UseWPF，依赖 CommandLineArgumentsParser 与 LSLib 项目 [G10]；`LSLib/LSLib.csproj` = `net8.0`、x64，NuGet 依赖 BCnEncoder.Net、K4os LZ4、OpenTK.Mathematics、Newtonsoft.Json、SharpGLTF、System.IO.Hashing、ZstdSharp.Port（均为托管包），但 **ProjectReference 了 C++ 工程 `LSLibNative.vcxproj`** [G11]。含义：Divine 本身不依赖 WinForms，PAK/LSF/LOCA 路径用的压缩库是托管实现；`LSLibNative`（推测为 Granny/GR2 相关）在 macOS 上无法构建，纯打包/转换是否会触发它需实测——与 A 报告"理论可行需实测"一致，并给出了更具体的风险点。
- **Multitool 现状**：GitHub 搜索索引显示仓库 `ShinyHobo/BG3-Modders-Multitool`（main/develop 分支、wiki "Packaging Mod Files"）仍存在，另有 GitLab 镜像 `gitlab.com/ShinyHobo/bg3-modders-multitool`（1,122 commits、1 release）[G12][G13]。A 报告的 404 更可能是抓取工具问题，而非项目消失；"source available、非开源"与 A 报告一致。
- `larian.com/support/faqs/official-mod-support_113` 在浏览器中被重定向到支持首页，未读到正文。

## 来源
| # | 标题 | URL | 类型 | 访问日期 |
|---|---|---|---|---|
| G1 | Baldur's Gate 3 Modding – Main Page | https://docs.baldursgate3.game/index.php?title=Main_Page | 一手（浏览器直读） | 2026-09-02 |
| G2 | Getting Started: Installing the Toolkit | https://docs.baldursgate3.game/index.php?title=Getting_Started:_Installing_the_Toolkit | 一手 | 2026-09-02 |
| G3 | Getting Started: Creating a New Mod | https://docs.baldursgate3.game/index.php?title=Getting_Started:_Creating_a_New_Mod | 一手 | 2026-09-02 |
| G4 | Adding Classes and Subclasses | https://docs.baldursgate3.game/index.php?title=Adding_Classes_and_Subclasses | 一手 | 2026-09-02 |
| G5 | Getting Started: Publishing a Mod | https://docs.baldursgate3.game/index.php?title=Getting_Started:_Publishing_a_Mod | 一手 | 2026-09-02 |
| G6 | Getting Started: Best Practices | https://docs.baldursgate3.game/index.php?title=Getting_Started:_Best_Practices | 一手 | 2026-09-02 |
| G7 | Adding Localisation | https://docs.baldursgate3.game/index.php?title=Adding_Localisation | 一手 | 2026-09-02 |
| G8 | Adding Skill and Item Icons | https://docs.baldursgate3.game/index.php?title=Adding_Skill_and_Item_Icons | 一手 | 2026-09-02 |
| G9 | mod.io – Modding Guidelines & FAQ（Larian 官方账号 GrumpyWashbear 发布） | https://mod.io/g/baldursgate3/r/modding-guidelines | 一手 | 2026-09-02 |
| G10 | Norbyte/lslib – Divine/Divine.csproj | https://raw.githubusercontent.com/Norbyte/lslib/master/Divine/Divine.csproj | 一手 | 2026-09-02 |
| G11 | Norbyte/lslib – LSLib/LSLib.csproj | https://raw.githubusercontent.com/Norbyte/lslib/master/LSLib/LSLib.csproj | 一手 | 2026-09-02 |
| G12 | GitHub – ShinyHobo/BG3-Modders-Multitool（搜索索引：tree/main、README@develop、wiki） | https://github.com/ShinyHobo/BG3-Modders-Multitool | 一手·摘要 | 2026-09-02 |
| G13 | GitLab – ShinyHobo/bg3-modders-multitool | https://gitlab.com/ShinyHobo/bg3-modders-multitool | 一手（WebFetch 部分） | 2026-09-02 |

## 审计
- 浏览器页面读取：10 次（docs 站 8 页 + mod.io 1 页含二次提取 + larian.com 1 页失败）；WebFetch 3 次（2 成功 1 部分）；WebSearch 1 次。
- 引用来源 13 条；未使用背景知识；`LSLibNative` 用途为推测，已标注。

## 11. 官方 Stats 参考页（补读，填补 E 报告缺口 #1）

### 11.1 Functors（官方定义与完整签名）[G14]
- 定义原文："Functors are immediate changes to game state. They fire and forget, used by passives, spells, statuses and interrupts."
- 参数记法：`<arg>` 必填；`<arg?=value>` 可选带默认值；`<arg!deprecated>` 已弃用；前缀 `i` 整数（后加 `<%>` 表示百分比）、`f` 浮点、`b` 布尔、`e` 枚举。
- 官方列表（共 41 个，含签名）：
  - `ApplyStatus(<StatusID>, <Chance!deprecated>, <LifeTimeExpression>, <ExtraData?!deprecated>, <iIntParam1?=0!deprecated>, <iIntParam2?=0!deprecated>, <RollConditions?>, <bExtendConcentration?=false>)`；`ApplyEquipmentStatus(<eEquipmentSlot>, ...)` 同参数前置装备槽
  - `DealDamage(<Expression>, <eDamageType>, <bMagical?=false>, <bNonlethal?=false>, <iPerGoldAmount?=0>, <ExtraTooltipTextUUID?="">, <bExcludeDamageBonus?=false>, <bDisablePassiveOnDamageEvent?=false>, <bConsumeGold?=false>, <bIgnoreResistance?=false>)`
  - `RegainHitPoints(<Expression>, <eHealingType?=Living>)`；`RegainTemporaryHitPoints(<Expression>)`；`GainTemporaryHitPoints(<Expression>)`（仅 tooltip 用，无功能）
  - `RestoreResource(<ResourceName>, <iAmount><%>, <iLevel?=0>)`（不提高上限）；`UseActionResource(<ResourceName>, <Amount><%>, <Level?=0>, <bIgnoreMultipliers?>)`
  - `Summon(<TemplateUUID>, <Lifetime>, <SpellOverrideForAI?>, <bExtendConcentration?=false>, <StackID?>, <Status1..4?>, <bLateJoinPenalty?=false>, <bUseCasterPassives?=false>)`；`SummonInInventory(...)`；`Spawn(...)`；`SpawnInInventory(...)`；`Unsummon()`
  - `CreateSurface(<fRadius>, <iSurfaceLifeTime>, <SurfaceType>, <bIsControlledByConcentration?=true>, <iExcludeRadius?=0>, <bExtendConcentration?=false>)`；`SurfaceChange(<SurfaceChangeType>, <Chance!deprecated>, <iLifeTime?=0>, <iStatusChance?>, <iRadius?>)`；`SurfaceClearLayer(<eType>)`；`CreateConeSurface(...)`（BG3 未用，建议用 Zone 法术）；`TargetCreateSurface`（已弃用）
  - `ExecuteWeaponFunctors(<eHandSlot>)`；`UseAttack(<IgnoreBlindness?=false>)`；`UseSpell(<SpellID>, <IgnoreHasSpell?=false>, <IgnoreChecks?=false>, <ResetCooldown?=false>, <ClassID?>, <IgnoreBlindness?=false>)`；`CreateExplosion(<SpellID>)`；`SpawnExtraProjectiles(<SpellID>)`；`TriggerRandomCast(<iRandomCastDC>, <fDelay?=0>, <OutcomeGroupName?>, ...)`
  - `Force(<iDistance>, <eDirectionMode?=OriginToEntity>, <eAggression?=Aggressive>, <bIsPhysical?=false>, <bUseDistanceToOrigin?=false>)`；`TeleportSource(<bShortestPath?=false>, <bFaceTarget?=false>)`；`SwapPlaces(<EffectNames>, <bIsIntentionalForSource?=false>, <bIsIntentionalForTarget?=false>)`
  - `RemoveStatus(<StatusID>)`；`RemoveAuraByChildStatus(<StatusID>)`；`SetStatusDuration(<StatusID>, <iLifeTime>, <eMode?=SetMinimum>)`；`BreakConcentration()`
  - `ResetCombatTurn()`；`ResetCooldowns(<eCooldownType>)`；`ShortRest()`（不消耗短休次数）；`Resurrect(<Chance!deprecated>, <iHitPointPercentage>, <eHealingType?=Living>)`；`Stabilize()`；`SwitchDeathType(<eDeathType>)`
  - `DisarmWeapon()`；`Pickup(<Effect?>)`；`Unlock()`；`CustomDescription(<Description>)`（假 functor，只加描述文本）
- 对职业设计的含义：资源恢复/消耗、召唤、状态、伤害、位移、重置回合/冷却等"职业特性常用动作"全部有官方 functor，**不需要 SE**。

### 11.2 Stats Expressions（表达式 DSL）[G15]
- 支持 `+ - * /`（`* /` 右侧不能是骰子/伤害列表）、骰子 `3d6 + 8`、tooltip 里 `(1+(Level-1)/2)d6` 形式、括号。
- 关键字：`SpellCastingAbility`、`ProficiencyBonus`、`Level`、`SpellDC`、`WeaponActionDC`、`LockDC`、`UnarmedMeleeAbility`、`MaxHP`、**`ClassLevel(<class>)`**；属性名（如 `Dexterity` 默认为属性检定，`DexterityFlat` / `DexterityModifier` / `DexteritySavingThrow`）；技能名（`Athletics`、`AthleticsModifier`…）；状态组计数（`SG_Charmed`）。
- 默认取施法者数据，`Target.` 前缀取目标（无目标时回退 0，`Level` 回退 1）。
- 函数：`max()`（比较加值只掷一次）、`foreach(<count>, <expr>)`、`ResourceRoll(<ActionResource>, <dice count>)`（从最大可用骰子开始，用于类似超凡骰的资源）、`<StatusId|StatusGroup>.Amount` / `.Duration`。
- 对职业设计的含义：`ClassLevel(<class>)` 让自创职业的特性随本职业等级缩放（多职业安全）；`ResourceRoll` 可实现"骰子型资源"。

### 11.3 官方文档站页面清单（Special:AllPages 第一页）[G16]
- 站点除教程外，还逐页收录 Osiris API（`AddPassive`、`AddSpell`、`ApplyStatus`、`CharacterGiveEquipmentSet`、`CombatRoundStarted`… 数百页）与 Anubis（AI 行为脚本）教程；说明官方文档是 Osiris/Anubis 的权威参考，而 Boosts / Conditions 是否有独立参考页见下节核查。

### 11.4 Boosts / Conditions / Progressions 在官方站没有独立参考页 [G16]
- 用 `Special:AllPages`（隐藏重定向）逐段核查：`Bo…` 段直接从 `CalculatePassiveSkill` 开始，`Con…` 段只有 `Concatenate*`/`ConstellationTriggerInputSocket`，`Pr…` 段从 `PreMovedBy` 跳到 `Projectiles`——即**没有 `Boosts`、`Conditions`、`Progressions`、`Interrupts` 参考页**；官方站的 Stats 参考只有 `Functors`（含每个 functor 的子页）与 `Stats Expressions`。
- 结论：Boosts / Conditions 的权威来源仍是社区（bg3.wiki、wiki.bg3.community）或直接解包 `Shared.pak` / `Gustav.pak` 的 Stats 文本对照；这与 E 报告的判断一致。
- 官方站另收录完整 **Osiris API** 页面（`Osiris API` 索引 + 每个调用/事件一页），与职业测试相关的调用包括：`SetLevel`、`AddExplorationExperience`、`RequestAutoLevel`、`RequestRespec` / `StartRespec` / `StartRespecToSubclass` / `RespecCompleted`、`AddPassive` / `RemovePassive`、`AddSpell` / `RemoveSpell`、`ApplyStatus` / `RemoveStatus`、`CharacterGiveEquipmentSet`、`LeveledUp`、`ShortRested` / `LongRestFinished`、`TurnStarted` / `TurnEnded`、`ReactionInterruptUsed`、`UserAvatarCreated`。`[背景知识—非本次检索]`：Script Extender 控制台里可用 `Osi.<CallName>(...)` 直接调用这些 Osiris 函数，是快速升级/重置/加被动的测试手段，具体签名以官方页为准。
- 来源 G16：https://docs.baldursgate3.game/index.php?title=Special:AllPages（含 `from=Bo` / `from=Int` / `from=Pr` / `from=Sta` 四段），2026-09-02 浏览器直读。
- 来源 G14：Functors https://docs.baldursgate3.game/index.php?title=Functors ；G15：Stats Expressions https://docs.baldursgate3.game/index.php?title=Stats_Expressions（均 2026-09-02 浏览器直读）。

## 12. 社区 wiki（wiki.bg3.community）浏览器直读补充

### 12.1 Basic Class Creation（不用 Toolkit、纯文本 lsx 建职业）[G17]
- 示例 mod "Quickster" 的最小目录：`Localization/English/Quickster.xml`（→ 用 Multitool 转 `.loca`）、`Mods/`（打包时 Multitool 生成 `Mods/<Mod>/meta.lsx`）、`Public/Quickster/ClassDescriptions/ClassDescriptions.lsx`、`Public/Quickster/Progressions/Progressions.lsx`、`Public/Quickster/CharacterCreationPresets/AbilityDistributionPresets.lsx`（起始属性点预设）。
- 原版 `ClassDescriptions.lsx`（Shared.pak）逐字片段：`<node id="ClassDescription">` 属性含 `BaseHp`(int32) / `CharacterCreationPose`(guid, 0f07ec6e-…) / `ClassEquipment`(FixedString, 如 `EQP_CC_Barbarian`) / `ClassHotbarColumns`=5 / `CommonHotbarColumns`=9 / `ItemsHotbarColumns`=2 / `Description` 与 `DisplayName`(TranslatedString handle+version) / `HpPerLevel` / `LearningStrategy`(uint8=1) / `Name` / `PrimaryAbility`(uint8) / `ProgressionTableUUID`(guid) / `SoundClassType` / `SpellCastingAbility`(uint8) / `UUID`；子节点 `<node id="Tags"><attribute id="Object" type="guid" .../>`。子职业条目多一个 `ParentGuid` 指向父职业 UUID。
- 原版 `Progressions.lsx` 逐字片段：`<node id="Progression">` 属性 `Boosts`(LSString, 分号分隔，如 `ProficiencyBonus(SavingThrow,Strength);Proficiency(LightArmor);ActionResource(Rage,2,0)`) / `Level`(uint8) / `Name` / `PassivesAdded`(分号分隔被动名) / `ProgressionType`(uint8：0 class、1 subclass、2 race) / `Selectors`(如 `SelectSkills(<SkillListUUID>,2)`) / `TableUUID` / `UUID`；子节点 `<node id="SubClasses"><children><node id="SubClass"><attribute id="Object" type="guid" value="<子职业 ClassDescription UUID>"/>`。
- 教程对字段的解释：`HpPerLevel` 实际每级 +1（作者实测：BaseHp 6 + HpPerLevel 4 → 11）；`LearningStrategy` 留 1；`PrimaryAbility` 教程写 "1 = dex, 2 = str, 3 = con, 4 = int, 5 = wis, 6 = chr"——**与同页原版 Barbarian 条目 `PrimaryAbility=1` 矛盾**（野蛮人主属性是力量），按标准属性顺序更可能是 1=Strength、2=Dexterity、3=Constitution、4=Intelligence、5=Wisdom、6=Charisma（推断，需解包核对）。
- `ProgressionDescriptions.lsx` 示例：类型 `Type="<ClassName>"` 的条目用于"职业特性"展示；`Type="ActionResource"` + `ParamMatch="0:SpellSlot"` 让法术位出现在角色创建的职业特性列表；每条独立 UUID，`ProgressionTableId` 指向职业进阶表。
- 让法术位显示在 CC 界面需要 Boosts `ActionResource(SpellSlot,2,1)` 与 `PassivesAdded` 里的 `UnlockedSpellSlotLevel1`（与 E 报告 [21] 一致）。
- lsx 头部 `<version major="4" minor="3" revision="0" build="333"/>`（教程用值；原版为 4.0.9.328 等），教程作者建议独立 mod 用较高的版本号但未解释原理（标注 TODO）。
- 与官方 Toolkit 流程的关系：Toolkit 的 UUID Object Editor 本质上就是在编辑这些 lsx 表；因此"Mac 上手写/脚本生成 lsx → Windows 打包"与"Windows Toolkit 表格编辑"是同一份数据的两种编辑方式。

### 12.2 Dev Environment Set-up [G18]
- Community Library 团队提供基础模板（GitHub）与 SE 模板；推荐目录：`Mods/ProjectName/{Readme, Source/{Localization/<Lang>/*.xml, Mods/<MOD>/meta.lsx, Public/<MOD>/}, Assets/, Releases/}`；SE 结构 `Source/Mods/<MOD>/ScriptExtender/{Config.json, Lua/BootstrapServer.lua, Lua/BootstrapClient.lua}`。
- 工具：LSLib ≥ 1.19.5（xml→loca 等）、BG3 Mod Manager、Git（有《A Modder's Guide to Git》）、VS Code/VSCodium + **BG3 Mod Helper**（UUID 生成/导航/本地化/模板，未来支持打包）+ **BG3 Text Support**（stats .txt 高亮/格式化）。

### 12.3 Compatibility Framework Usage [G19]
- 两种接入方式：(1) **JSON 配置**（推荐）：`Mods/<Mod>/ScriptExtender/CompatibilityFrameworkConfig.json`，结构 `{"FileVersion":1,"Progressions":[{"UUID"|"UUIDs": <父职业"可选子职业那一级"的 Progression UUID>, "Subclasses":[{"UUID"|"UUIDs": <子职业 ClassDescription UUID>, "modGuid": 可选}]}]}`；(2) **Lua API**：`Ext.Mod.IsModLoaded("67fbbd53-7c7d-4cfa-9409-6d737b4d92a9")`（CF 的 mod UUID）后在 `Ext.Events.StatsLoaded` 时调用 `Mods.SubclassCompatibilityFramework.Api.InsertSubClasses({...})`，参数含 `modGuid`、`subClassGuid`、`class`（小写父职业名或进阶 UUID）、`subClassName`。
- CF 还支持 Spells、Spell Lists、Race Data、Action Resource Groups、Progressions、Feats 的注入；**你的 mod 必须比 CompatibilityFramework 先加载**。
- 注意：JSON 配置方式也放在 `ScriptExtender/` 目录下，说明 CF 的运行仍依赖玩家安装 SE（与 C/D 报告一致）。

### 来源
| # | 标题 | URL | 类型 | 访问日期 |
|---|---|---|---|---|
| G17 | BG3 Modding Community Wiki – Basic Class Creation | https://wiki.bg3.community/Tutorials/Classes/Basic-Class-Creation | 二手（社区教程，浏览器直读，含原版数据逐字片段） | 2026-09-02 |
| G18 | BG3 Modding Community Wiki – Dev Environment Set-up | https://wiki.bg3.community/Tutorials/General/setting-up-a-dev-environment | 二手（浏览器直读） | 2026-09-02 |
| G19 | BG3 Modding Community Wiki – Compatibility Framework Usage | https://wiki.bg3.community/Tutorials/Mod-Frameworks/compatibility-framework | 二手（框架文档，浏览器直读） | 2026-09-02 |
