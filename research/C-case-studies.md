# 子课题 C：案例研究（职业类 mod 与基础框架 mod）+ 中文社区资源

- 调研日期：2026-09-02
- 范围：BG3 职业/子职业类知名 mod 案例、基础框架类 mod、可作模板的开源仓库、中文社区资源、可迁移的共同做法
- 引用约定：`[n]` 指向文末来源列表；标注 `[背景知识—非本次检索]` 的内容来自训练记忆，不计入来源统计
- 重要限制：本次会话中 **Nexus Mods 页面对 WebFetch 返回 HTTP 403，mod.io 页面为纯 JS 渲染无正文，web.archive.org 被工具封禁**。因此所有 Nexus / mod.io 数据均来自 WebSearch 返回的摘要（在来源列表中标为"一手页面·仅经搜索摘要"），页面上未在摘要中出现的字段一律写"页面未显示"。

---

## 1. TL;DR

1. **职业类 mod 的"标准依赖栈"已经固定**：Script Extender（Lua/Osiris 脚本）[1] + Compatibility Framework（运行时把子职业/法术注入 Progressions 与各类 List，避免覆盖）[3][33] + ImprovedUI/ImprovedUI Assets（自定义职业/子职业图标等 UI 资源）[6][36]。Death Knight – Champion of the Lich King 的需求列表（Mod Fixer + SE + ImprovedUI + Assets）就是典型样本 [21]。
2. **"全新基础职业"与"子职业包"是两条难度差异很大的路线**：Artificer [10]、Blood Hunter [13]、Mystic [17]、三个 Death Knight [21][23][24] 都是自带资源系统/大量自定义法术的基础职业；而 Way of the Astral Self [27][28]、5e Fighter Subclasses Combined [30]、Bard Sorcerer Subclasses Combined [31] 等子职业包只需接入 CF 即"custom subclasses just work" [57]。
3. **Patch 7（2024-09）后 ModFixer 已不再需要**（wiki.bg3.community 明确写明）[42]；**Patch 8（2025-04）后** 出现 ImpUI_P8_Fork（Djmr 授权、开放贡献）[37][38]，ImprovedUI 原仓库表示"没有积极维护的计划"但已支持 Patch 7/8 [6]；5e Spells 针对 Patch 8 做了移除 Shadow Blade、修复借机攻击等更新 [43]；5e Fighter Subclasses Combined 最近一次更新为 2026-08-21，标记 Patch 8 Compatible [30]。
4. **双平台发布（Nexus + mod.io）已成主流**：Blood Hunter [13][14]、Mystic [17][18]、WoWDeathKnight [24]、ImprovedUI [36]、5e Spells（mod.io 版与 Nexus 作者 Diz 合作）[44] 都同时存在于两个平台。
5. **多语言主要靠社区"翻译版单独上传"**：Blood Hunter 有 PTBR/ES/FR/CH 独立翻译页 [16]，Death Knight CotLK 有 ES/CHT/PTBR/KOR/ITA/RU 六种 [22]，Artificer/Mystic/Astral Self 都有 CHS 版 [12][20][29]；少数 mod 选择内置翻译（Blood Hunter Expanded 自带 FR/UK/RU）[15]。
6. **可作学习模板的开源仓库有限但够用**：CF-Example-Mods（MIT，3 个最小示例）[4]、doombubbles/bg3-mods（含 WoWDeathKnight 完整职业、GitHub Actions CI、scripts/ 构建脚本）[7]、BG3-Community-Library（MIT，含 ReferenceScripts）[2]、AtilioA/BG3-volition-cabinet（Lua 库、Actions、仓库内维护 nexus_description.bb）[35]。Artificer / Blood Hunter / Mystic 本次未找到 GitHub 源码。
7. **中文社区资源以"安装/整合/汉化"为主，"从零做职业 mod"教程极少**：B 站 2023-09 的 14 集《从0开始制作一个新的子职业》系列（3.5 万播放，附完整工具包与示例子职业"幽暗之刃"）[9] 是本次唯一找到的中文职业制作系列；3DM 的 BG3 LocaHelper 汉化教程（2023-10/11）[65][66]、贴吧汉化求助帖 [69]、知乎装备 mod 流程 [71]、豆瓣 MOD 制作讨论 [73] 构成其余生态。QQ 群号在搜索摘要中出现但来源页面未能定位，需核实。
8. **共同做法**：依赖 SE+CF+ImprovedUI 而不是覆盖原版文件；标题/标签写明 "Patch 8"；用附属 mod（Feat Every Level、12 Levels Option、Expansion 可选文件）实现模块化；兼容 UnlockLevelCurve 做到 20 级；旧版本明确标 "(Deprecated)"；维护者退出时授权 fork。

---

## 2. 详细发现

### 2.1 职业 / 子职业类知名 mod 案例

> 表中"页面未显示"= 搜索摘要未给出该字段（Nexus 页面 403 无法直接读取）；"未能确认"= 截至 2026-09 无法从本次来源判断。

| # | Mod（类型） | 作者 | 平台 | 下载/推荐 | 依赖 | 开源 | 更新 / Patch 7·8 适配 | 翻译与团队线索 |
|---|---|---|---|---|---|---|---|---|
| A | **Artificer class and all subclasses**（全新基础职业，4 子职业：Alchemist / Armorer / Artillerist / Battle Smith）[10] | KiderionLykon（由附属 mod "Feat every level addon for KiderionLykon's Artificer class mod" 的描述反推）[11] | Nexus 1779 [10] | 页面未显示 | 页面未显示 | 未找到 GitHub | 页面未显示；Patch 8 适配未能确认 | 有 CHS 独立翻译页 [12]；存在第三方附属 mod 生态：Feat Every Level、12 Levels Option（把 20 级解锁压缩到 12 级）、Artificer Tweaks [11]；被 ScreenRant 报道 [75] |
| B | **Blood Hunter Class – Lycan and Ghostslayer Subclasses**（全新基础职业，改编 Matthew Mercer 2022 版，4 子职业，配合 level unlock mod 可到 20 级，含自定义动画与法术特效）[13] | WolfeTK [13] | Nexus 2151 [13] + mod.io [14] | 搜索摘要：2025-11 时 3,893 endorsements，版本 1.14 [13] | 页面未显示 | 未找到 GitHub | 版本 1.14（2025-11）[13]；Patch 8 适配未能确认。姊妹作 **Blood Hunter Expanded (Profane Soul and Mutant) Full Release Patch 8** 标题即写明 Patch 8，且自带 FR/UK/RU 翻译 [15] | 第三方翻译页：PTBR、ES（两版，其中一版标"Actualizado 1.12"）、FR、CH [16]；团队构成页面未显示 |
| C | **Mystic Class**（全新基础职业，Unearthed Arcana 灵能职业；独有资源 Psi Points；Psionic Talents 当戏法；38 个 psionic disciplines；含全部子职业；兼容 UnlockLevelCurve，内容做到 20 级）[17][18] | 页面未显示 | Nexus 2786 [17] + mod.io [18] | 页面未显示 | 页面未显示 | 未找到 GitHub | 有 "Mystic Expansion" 可选文件（Nexus 文章 390）[19]；PTBR 翻译页标题含 "Patch7" [20]；Patch 8 适配未能确认 | CHS 翻译至少 3 个独立页面（15581 / 12935 / 14301），PTBR 2 个 [20] |
| D | **Death Knight Class – Champion of the Lich King**（全新基础职业，30+ 魔兽世界风格自定义法术/被动）[21] | VivaSortiara [21] | Nexus 1725 [21] | 页面未显示 | 页面列出：Baldur's Gate 3 Mod Fixer、Script Extender、ImprovedUI + ImprovedUI Assets [21] | 未找到 GitHub | 需求列表仍含 Mod Fixer（Patch 7 后已不需要 [42]），提示描述可能未随补丁更新；维护状态未能确认 | 六种翻译独立页：ES、CHT、PTBR、KOR、ITA、RU [22] |
| E | **WoWDeathKnight**（全新基础职业：符文系统，Blood（开发中）/ Frost / Unholy 三子职业，CHA 施法，重甲+军用武器、不能用盾）[24] | doombubbles（源码仓库归属）[7] | mod.io [24]；Nexus 上另有同名主题 mod 15103（是否同一作者页面未显示）[25] | 页面未显示 | 页面未显示 | **是**：doombubbles/bg3-mods 单一仓库含 WoWDeathKnight、WoWSubclasses、DoombubblesTweaks 等 [7] | 仓库有 .github/workflows CI、scripts/、Wiki [7]；最近更新日期页面未显示 | 被 PCGamesN 报道 [76] |
| F | **The Death Knight**（全新基础职业，武术型半施法者、死灵伤害，5 个子职业各对应一种不死生物）[23] | 页面未显示（mod.io 页面无法读取正文） | mod.io [23] | 页面未显示 | 页面未显示 | 未找到 | 未能确认 | — |
| G | **Way of the Astral Self**（武僧子职业；两条实现线）：① "Monk – Way of the Astral Self Subclass Standalone"，基于 Alternate Monk mod 中的 Astral Warrior 独立拆出 [27]；② "5e Way of the Astral Self – Monk Subclass"，5e RAW 忠实版，现标题带 "(Deprecated)" [28] | 页面未显示 | Nexus 3044 / 10078 [27][28] | 第三方聚合站 discovermods 称 Standalone 版 54,974 downloads（三手数据，不作依据）[79] | 页面未显示 | 未找到 | ②已标 Deprecated [28] | CHS、Spanish 翻译独立页 [29] |
| H | **5e Fighter Subclasses Combined**（子职业包）[30] | 页面未显示 | Nexus 15060 [30] | 搜索摘要：823 endorsements [30] | 页面未显示 | 未找到 | 版本 1.1.9.3，更新于 2026-08-21，标签 "Patch 8 Compatible" [30] | — |
| I | **Bard Sorcerer Subclasses Combined**（子职业包）[31] | 页面未显示 | Nexus 3446 [31] | 页面未显示 | 页面未显示 | 未找到 | 未能确认 | — |
| J | **CF-Example-Mods**（3 个最小示例：Pact of the Gunblade / Warlock OneD&D UA7 Spell List Additions / Monk OneD&D UA8 Weapon Proficiency Additions）[4] | BG3-Community-Library-Team [4] | GitHub | — | Compatibility Framework [4] | **是**，MIT [4] | 仓库标注版本 2.6.3.5、22 次提交 [4] | 教学性质 |

补充观察：

- Death Knight 主题在 mod.io 上至少有 4 个不同实现（the-death-knight、death-knight、deathknight2、wowdeathknight）[23][24]，Nexus 上还有 Lord Soth 风格的 "Knights of the Duskrose" [26]——同一主题多实现并存是常态，**命名和描述要能区分自己**。
- Double Subclass（选两个子职业）在 Patch 8 后把官方新增子职业加入 progressions.lsx，并修改了 Death Cleric、Crown Paladin、Shadow Sorcerer、Hexblade Warlock [32]——说明官方补丁新增子职业会直接影响改 Progressions 的 mod。
- 针对"子职业 mod 不显示、多职业坏掉、重复解锁"的问题，Nexus 上存在一类"CF 补丁 mod"（Compatibility Framework Patch for Modded Subclasses、CF Subclass Patches、Subclass Compatch）[57]，说明**未接 CF 的子职业 mod 会由第三方补丁"代为接入"**，也就是自己接好 CF 能避免这类补丁需求。
- Mystic 之外，灵能主题还有 Psionics – Wizard Subclass（Nexus 10014）和 mod.io 的 "The Psion: Unearthed Arcana 2025" [83]，同样体现"同主题多实现"。

### 2.2 基础框架类 mod

| 框架 | 解决什么问题 | GitHub / 页面 | 许可证 | 协作方式 | 现状（截至本次检索） |
|---|---|---|---|---|---|
| **Script Extender (bg3se)** | 为游戏加入 Lua/Osiris 脚本能力，附调试器与 API 文档 [1] | github.com/Norbyte/bg3se [1] | 仓库有 LICENSE 文件，类型摘要未显示 [1] | GitHub Issues（196 open）/ PR（12 open）；README 未见 Discord 链接 [1] | 1.5k star、106 fork；README 未标 Patch 7/8 [1]。第三方 macOS 复刻 tdimino/bg3se-macos（57 star，2026-08 更新）[8] |
| **Community Library** | 提供公共法术/脚本/物品/状态/被动，减少重复造轮子 [2] | github.com/BG3-Community-Library-Team/BG3-Community-Library [2]；组织下共 23 个仓库 [56] | MIT [2] | 三条路径：联系 @NellsRelo 加入团队（官方 Discord）/ fork+PR / 用 Bug Report、Feature Request 模板提 Issue；官方 BG3 Discord #bg3-modding [2] | 目录：CommunityLibrary、ReferenceScripts、TreasureVault、WikiRes [2]；2.0.4.1 起 CF 拆分为独立项目但仍依赖 CL 的 Lua 函数 [2]；wiki 有 "Building a Class Mod" 页 [47] |
| **Compatibility Framework (CF)** | 让 SE 模组在运行时把数据注入既有 Progressions / Spell·Skill·PassiveList / Feats，不覆盖原数据，实现"完全兼容" [3][33] | github.com/BG3-Community-Library-Team/BG3-Compatibility-Framework [3]；Nexus 1933 [33] | 页面未显示（README 摘要未见） | fork+PR；11 个 open issue；Wiki 有 Class/Subclass、Selector、Boosts/Passives、Lists 四个模块文档 [3][49] | 最新 2.8.2.0 [3]；需加载在列表最底部 [3]；≥2.3.0 后 "SubclassCompatibilityFramework" 可删除（已更名合并）[33] |
| **Subclass Compatibility Framework (SCF)** | CF 的前身，专为子职业兼容 [48] | CL wiki 页 [48]；旧仓库名 BG3-Subclass-Compatibility-Framework（搜索摘要提及，未验证是否仍可访问）[53] | — | — | 已并入 CF（见上）[33] |
| **ImprovedUI (ImpUI) + ImprovedUI Assets** | 改进角色创建/升级 UI；支持自定义职业、种族、神祇、行动资源、背景图标；Assets 维护"Supported Mods"清单 [6][36] | github.com/TheRealDjmr/BG3ImprovedUI [6]；Nexus 366 [36]；mod.io impui；Thunderstore 镜像（署名 ShinyHobo_Djmr_AlanaSP）[41] | 页面未显示 [6] | Larian Discord 模组频道 + GitHub Issues（13 open）[6]；职业图标做法：fork ImprovedUI，修改 IUI_ClassIcons（bg3.wiki）[40]；社区 fork 示例：CovelissLyvain/BG3ImprovedUI-with-Illrigger（为 Illrigger 职业 mod 加图标）[39] | 原作者 Djmr、AlanaSP、ShinyHobo、Zee [37]；README 已含 Patch 8 改动，但声明"没有积极维护的计划"，并警告不要叠加未更新到 Patch 8 的 UI mod [6]；**ImpUI_P8_Fork**（Nexus 16649，GitHub valsan-azerty-boi/BG3ImprovedUI）为 Patch 8 专用、Djmr 授权、开放贡献 [37][38] |
| **Mod Configuration Menu (MCM)** | 游戏内（ESC 菜单 / INSERT 键）统一的 mod 设置与键位界面，玩家不必手改 JSON，作者不必自管配置 [5] | github.com/AtilioA/BG3-MCM [5] | AGPL-3.0 [5] | Issues/PR 开放；Ko-fi/Patreon [5] | 1,518 commits、22 star、4 open issue；UI 无关设计（无 IMGUI 也可用）；支持 SE ModVars 存档级持久化 [5]；其 JSON 加载与配置引导代码分别改自 CF 与 Volition Cabinet（MIT）[33] |
| **Volition Cabinet** | Volitio（AtilioA）系列 mod 的公共 Lua 库，Focus Core 的 fork [34][35] | github.com/AtilioA/BG3-volition-cabinet [35]；Nexus 7676 [34] | 页面未显示 [34] | GitHub Issues + Actions CI；仓库内维护 nexus_description.bb（Nexus 描述随代码版本化）[35] | 11 star，Lua，2026-08-09 更新 [8]；有第三方扩展库 novus213/BG3_KendersLabsCoreLibs [59] |
| **ModFixer** | 旧版让 .pak mod 被识别的修复器 | Nexus（本次未直接检索页面） | — | — | **Patch 7 起不再需要**："ModFixer is not broken in Patch 7, but it is not needed anymore" [42]。ScreenRant 称 Patch 7 后 ModFixer 与 SE 都不再必要 [77]——后半句与一手事实冲突（CF 等仍要求 SE [3]），按媒体误读处理 |
| **5e Spells** | 补齐 5e 缺失法术，是大量职业 mod 的法术来源 | Nexus 125 [43]；mod.io "5e Spells: WIP"（与 Nexus 作者 Diz 合作）[44] | 未找到 GitHub | — | Patch 8 更新：移除 Larian 已加入的 Shadow Blade；修复 Patch 8 interrupt/reaction 数据变化导致的借机攻击问题 [43]；周边生态：5e Spells Compatibility Patch、5eSpells and Expansion Patch（hawchangJA，2.4.3.0，Patch 8 Compatible）、Practical 5e Spells（KaiJai，轻量子集）[45] |
| **UnlockLevelCurve** | 13–20 级 | Nexus 377，标题含 "PATCH 8" [46] | — | — | Blood Hunter、Mystic 都声明兼容它以到 20 级 [13][17] |

其他与职业 mod 相关的工具/框架（顺带检索到）：Character Preset Framework（Nexus 19805）[58]；progressions compatibility patches（FrederickEngelhardt，Nexus 1572 + GitHub）[53]；BG3 Mod Manager（LaughingLeader，官方唯一源）[54]、macOS 版 BaldursModManager [82]；Yet-Another-BG3-Native-Mod-Loader（Rust）、BG3ModStudio（C++，Windows 一体化编辑器，2026-02 更新）、bg3d（LSV 检视/解包）、BG3LocalizationMerger（合并两种语言）[8]。

### 2.3 可作学习模板的开源仓库

| 仓库 | 目录结构（摘要可见部分） | 许可证 | 构建脚本 | 适合当模板？ |
|---|---|---|---|---|
| **BG3-Community-Library-Team/CF-Example-Mods** [4] | 每个示例一个子目录，内含 `Mods/`（摘要未见 Public/、Localization/、ScriptExtender/ 明细） | MIT | 摘要未见 | **适合作"接入 CF 的最小骨架"**：三个示例分别演示 SpellContainer、SpellLists、Boosts 三种注入方式 |
| **doombubbles/bg3-mods** [7] | `.github/workflows`（CI）、`.vscode`、`Wiki/`、`bin/`、`docs/`、`images/`、`scripts/`，以及 DoombubblesTweaks、WoWDeathKnight、WoWSubclasses、DoombubblesDifficulty、DoombubblesREL 各自的 mod 目录 | 页面未显示 | 有 `scripts/` 与 GitHub Actions | **适合作"完整职业 + 自动化打包"的参考**，但作者摘要评价为高度定制、不是通用脚手架；WoW 风格 Wizard 三子职业、Oath of Retribution 圣武士、法术降阶施放等都是可读的子职业实现 |
| **BG3-Community-Library-Team/BG3-Community-Library** [2] | `CommunityLibrary/`、`ReferenceScripts/`、`TreasureVault/`、`WikiRes/` | MIT | 摘要未见 | 作为**参考脚本库**与 wiki（Building a Class Mod、SCF 页）[47][48]，不是模板 |
| **AtilioA/BG3-volition-cabinet** [35] | Lua 库；仓库内含 `nexus_description.bb`、`.gitignore`、Actions | 页面未显示 | GitHub Actions | 适合参考 **SE Lua 项目布局 + CI + 在仓库内维护 Nexus 描述**的做法 |
| **novus213/BG3_RacialASI** [8] | Lua 小型 mod（PHB 种族 ASI 回退） | 页面未显示 | — | 小体量 SE mod 样例 |
| **FrederickEngelhardt/bg3-progressions-compatibility-patches** [53] | Progressions 补丁集合 | 页面未显示 | — | 学习"多 mod 改 Progressions 冲突如何打补丁" |
| **valsan-azerty-boi/BG3ImprovedUI**、**CovelissLyvain/BG3ImprovedUI-with-Illrigger** [38][39] | ImprovedUI fork | 页面未显示 | — | 学习"为自创职业加图标 = fork ImprovedUI 改 IUI_ClassIcons" [40] |

目录结构的一手说明：
- wiki.bg3.community "Basic Class Creation"：mod 源码目录 `Source` 由 `Localization`、`Mods`、`Public` 三个文件夹组成 [50]；同站另有 "Subclass Creation For An Existing Class" 与 "Dev Environment Set-up" [51][52]。
- Community Library wiki "Building a Class Mod"：职业定义存于 `Public/ModName/ClassDescriptions/ClassDescriptions.lsx`，与 Localization 无关 [47]。
- Compatibility Framework wiki "_Class Module" 给出子职业注入 API [49]。

**没有找到**：Artificer、Blood Hunter、Mystic、Death Knight CotLK 的 GitHub 仓库；GitHub topic 页 `baldurs-gate-3` 中未见通用"职业 mod 模板"仓库（多为工具类）[8]。

### 2.4 中文社区资源

| 类型 | 资源 | 说明 |
|---|---|---|
| **B 站·职业制作教程** | 《博德之门3【MOD制作教学】：从0开始制作一个新的子职业（持续更新中：设计制作一个必杀技：伸腿瞪眼刀）》，UP 主 18915063321，2023-09-12 上传，约 3.5 万播放，14 集 [9] | 作者称"找遍全网也不见教做子职业MOD的教程，只好硬着头皮自己研究"；提供百度网盘完整工具包与示例 mod"游荡者子职业-幽暗之刃"；分集：前置准备 → 子职业创建 → 打包进游戏 → 被动设计 → 主动技能 → 多技能打包 [9]。注意：上传于 Patch 7 之前，工具链可能过时 |
| **B 站·安装/整合** | 《8号补丁子职mod合集 抢先体验 完美整合！职业介绍和mod安装教程》[60]；《我们把"系统"做进了游戏！真正代码级优化的mod整合包》（自称含 200+ 新职业、并附 MOD 制作文档）[61]；《职业mod升级技能一览【德鲁伊篇】星辰结社》[62]；《v4.1 重燃费伦 V1 … 全新职业，附带超详细安装教程&模组管理器》[63]；专栏《全网最全200+Mod整合包与指南(Patch#4 Hotfix#10)》[64]（本次抓取被 B 站验证码拦截） | 中文玩家对"职业 mod"的消费需求很旺盛，整合包作者是潜在的分发渠道 |
| **3DM 论坛·汉化流程** | 《基于强大的本地化助手 BG3 LocaHelper 制作独立汉化mod 教程》2023-11-05 第二版 [65]；《基于 BG3 Locahelper 的mod 汉化教程》2023-10-22 第一版 [66]；3DM 博德之门3 论坛（含"求助""修改"分区）[67]；3DM mod 站 / 补丁站 [68] | 汉化流程要点（搜索摘要）：用 LSLib 解包 .pak → 只需 `Localization` 目录下的 .loca/.xml → 翻译 xml 转回 loca → 重新打包 [69][70] |
| **百度贴吧** | 《关于MOD汉化过程的求助》[69] | 帖内附汉化教程链接，指向 3DM 与 B 站 |
| **GameMale** | 《非常简单的MOD汉化过程教学！》[70] | 汉化教程 |
| **知乎** | 《【小枕の日常】〈博德之门3〉装备mod制作流程大纲》[71]；《怎么给博德之门3上mod？》[72] | 有制作流程（装备类），未见职业类 |
| **豆瓣小组** | 《博德之门3MOD制作（装备/纹身）》讨论帖 [73] | 新手入门讨论 |
| **游侠补丁站** | 《博德之门3基本MOD制作内容工作流程教程下载》[74] | 制作流程教程下载 |
| **Nexus 中文翻译者** | Artificer CHS [12]、Mystic CHS×3 [20]、Blood Hunter CH [16]、Death Knight CotLK CHT [22]、Astral Self CHS [29] | 说明 Nexus 上存在活跃的中文翻译者群体，**自创职业 mod 若提供 Localization 结构清晰的英文原文，容易被社区汉化** |
| **交流平台** | 搜索摘要出现 QQ 群 719701536、934517281（来源页面未定位，**需核实**）；Discord 中文频道：本次未找到 | 建议以 3DM 论坛、贴吧、B 站评论区为主要中文触点 |
| **本地化工具（英文社区）** | LarinStudios Localization Helper（Nexus 3136）[55]；BG3LocalizationMerger（GitHub）[8] | 可与 LocaHelper 流程互补 |

### 2.5 从案例中提炼的"成功职业 mod 的共同做法"

| 做法 | 案例佐证 |
|---|---|
| 1. **不覆盖原版文件，通过 SE + CF 运行时注入** | CF 的设计目标就是"注入而不覆盖" [3]；社区经验："If using Compatibility Framework, custom subclasses just work"，且 CF 内置多职业兼容 [57]；未接 CF 的子职业 mod 会催生第三方"CF 补丁" [57] |
| 2. **图标走 ImprovedUI 体系** | DK CotLK 需求列出 ImprovedUI + Assets [21]；bg3.wiki 明确"fork ImprovedUI、改 IUI_ClassIcons" [40]；Illrigger 作者即以 fork 方式加图标 [39] |
| 3. **Nexus + mod.io 双发布** | Blood Hunter [13][14]、Mystic [17][18]、WoWDeathKnight [24]、ImpUI [36]、5e Spells WIP [44] |
| 4. **在标题/标签明示补丁版本** | "Blood Hunter Expanded … Full Release Patch 8" [15]；"UnlockLevelCurve – Level 13-20 I PATCH 8" [46]；5e Fighter Subclasses Combined 标签 "Patch 8 Compatible" [30]；ImpUI_P8_Fork 名字即版本 [37] |
| 5. **模块化：核心 + 可选扩展 + 第三方附属** | Artificer 有 Feat Every Level / 12 Levels Option / Tweaks 三种附属 [11]；Mystic 有 Expansion 可选文件 [19]；Blood Hunter 主 mod + Expanded 拆分 [13][15]；5e Spells 周边补丁生态 [45] |
| 6. **支持 20 级（兼容 UnlockLevelCurve）** | Blood Hunter [13]、Mystic [17] 都声明兼容；Artificer 反而有人做"压缩到 12 级"附属 [11]，说明两种需求都存在 |
| 7. **多语言：开放 Localization 让社区翻译，或自带翻译** | 社区翻译独立页：Blood Hunter 4 语 [16]、DK 6 语 [22]；自带：Blood Hunter Expanded FR/UK/RU [15] |
| 8. **开源 + CI + 版本化 Nexus 描述** | doombubbles 单仓多 mod + Actions + scripts/ [7]；Volition Cabinet 仓库内 nexus_description.bb [35]；CL/CF-Example-Mods 采用 MIT [2][4]；MCM 采用 AGPL-3.0 [5] |
| 9. **清晰的弃用/迁移策略** | Astral Self 5e 版标 "(Deprecated)" [28]；SCF 更名并入 CF，并告知 ≥2.3.0 可删旧文件 [33]；CL 2.0.4.1 拆出 CF [2]；Djmr 授权 P8 fork [37] |
| 10. **及时清理过时依赖** | 反例：DK CotLK 需求仍列 Mod Fixer [21]，而 Patch 7 起已不需要 [42]——玩家会被误导 |
| 11. **可发现性：同主题多实现时靠命名/描述区分** | Death Knight 至少 5 个实现 [23][24][25][26]；Astral Self 两条线 [27][28] |
| 12. **随官方补丁新增内容调整 Progressions** | Double Subclass 在 Patch 8 后加入官方新子职业并修改 Hexblade 等 [32]；5e Spells 移除官方已加入的 Shadow Blade [43] |

---

## 3. 对"自创职业 mod"项目的具体建议 / 决策点

1. **先决定"子职业"还是"基础职业"**
   - 子职业：只需 Progressions 注入 + 少量法术/被动，接入 CF 后兼容性问题基本消失 [3][57]；可直接以 CF-Example-Mods 为骨架 [4]。
   - 基础职业：需要 `Public/<Mod>/ClassDescriptions/ClassDescriptions.lsx` [47]、完整 Progressions、专属资源系统（如 Mystic 的 Psi Points [17]、WoW DK 的符文 [24]）、以及 ImprovedUI 图标 PR [40]。工作量与维护成本显著更高。
   - 折中方案：先做一个"子职业包"验证流程，再升级为基础职业（Blood Hunter → Blood Hunter Expanded 的演进路径可参考 [13][15]）。

2. **依赖清单建议（最小化但不省略必需项）**：Script Extender [1] + Compatibility Framework [3] + ImprovedUI/Assets [6]（仅当有自定义图标）。不要再列 ModFixer [42]。是否依赖 Community Library 视是否复用其法术/脚本而定 [2]。若要做游戏内可调参数，再加 MCM（注意其 AGPL-3.0 许可证对衍生代码的影响）[5]。

3. **等级上限**：默认做到 12 级，并测试与 UnlockLevelCurve（Patch 8 版）[46] 共存时 13–20 级的 Progressions（Blood Hunter、Mystic 的做法 [13][17]）。

4. **图标与 UI**：提前在 GitHub 上 fork ImprovedUI 并按 bg3.wiki 步骤修改 IUI_ClassIcons [40]；鉴于原仓库"无积极维护计划" [6]，同时向 ImpUI_P8_Fork [37][38] 提交。

5. **发布**：Nexus + mod.io 双平台 [13][14][17][18]。（`[背景知识—非本次检索]`：mod.io 版本通常需用官方 Toolkit 打包，本次未检索验证。）标题或标签写明 "Patch 8"。

6. **本地化**：保持 `Localization/` 结构规范，至少提供 English + 简体中文；中文可用 3DM LocaHelper 流程 [65][66] 自行生成，或开放给 Nexus 中文翻译者（大量先例 [12][16][20][22][29]）。

7. **仓库与流程**：GitHub 开源（MIT 是社区主流 [2][4]）；参照 doombubbles 的 `scripts/` + GitHub Actions 打包 [7]、Volition Cabinet 的 `nexus_description.bb` 版本化描述 [35]；README 写清依赖、加载顺序（CF 放最底 [3]）、已知冲突。

8. **模块化设计**：核心包 + 可选扩展（如 Mystic Expansion [19]）+ 允许第三方附属（如 Artificer 的 Feat Every Level [11]）。避免把可选调整硬塞进核心。

9. **中文社区触达**：B 站发演示视频（参考 [60][62] 的"职业介绍 + 安装教程"形式）、3DM 论坛"原创"区发帖 [67]、贴吧答疑 [69]；QQ 群号需先核实。

10. **随补丁维护**：每次官方补丁后核对 Progressions 是否与官方新增子职业冲突（Double Subclass 案例 [32]）、法术是否已被官方收编（5e Spells 移除 Shadow Blade 案例 [43]）；旧版本明确标 "(Deprecated)" [28]。

---

## 4. 未解决问题与信息缺口

1. **Nexus 页面无法直接读取（HTTP 403）**：Artificer、Mystic、DK CotLK、Astral Self、5e Fighter Subclasses Combined 的 endorsements/downloads/依赖/Credits/更新时间线仅有搜索摘要片段；Artificer、Mystic 的推荐数与依赖完全缺失。
2. **mod.io 页面为 JS 渲染**：The Death Knight、Mystic、Blood Hunter 的 mod.io 订阅数、更新日期均未获取。
3. **作者信息缺口**：Mystic Class、The Death Knight (mod.io)、Astral Self 两版、5e Fighter Subclasses Combined、Bard Sorcerer Subclasses Combined 的作者页面未显示。
4. **Credits / 团队构成**：因页面不可读，各职业 mod 的设计/实现/图标/本地化/测试分工基本未能确认；仅 ImprovedUI（Djmr、AlanaSP、ShinyHobo、Zee）[37] 与 Community Library（@NellsRelo 联系人）[2] 可见。
5. **Patch 8 适配**：Artificer、Mystic、DK CotLK、Astral Self Standalone 截至 2026-09 的适配状态未能确认；Blood Hunter 主 mod 仅知 2025-11 为 v1.14。
6. **许可证缺口**：Script Extender（有 LICENSE 文件但类型未显示）[1]、ImprovedUI [6]、Volition Cabinet [34]、doombubbles/bg3-mods [7]、CF [3] 的许可证类型页面未显示。
7. **开源情况**：Artificer / Blood Hunter / Mystic / DK CotLK 是否有源码仓库未找到。
8. **中文交流平台**：QQ 群号（719701536 / 934517281）来源页面未定位；是否存在 Discord 中文频道未找到；B 站专栏 [64] 抓取被验证码拦截。
9. **web.archive.org 被工具封禁**，无法用快照绕过 Nexus 403。
10. 建议主课题在有浏览器或 Nexus API key 的环境补抓上述 Nexus 页面。

---

## 5. 来源列表（访问日期均为 2026-09-02）

类型说明：一手 = 项目/作者自己的页面且本次直接抓取到正文；一手·摘要 = 项目/作者页面但仅经 WebSearch 摘要获取；二手 = 社区 wiki/论坛转述；三手 = 媒体/聚合站。

### 5.1 直接抓取（WebFetch 成功）
| # | 标题 | URL | 类型 |
|---|---|---|---|
| [1] | GitHub – Norbyte/bg3se（Script Extender） | https://github.com/Norbyte/bg3se | 一手 |
| [2] | GitHub – BG3-Community-Library-Team/BG3-Community-Library | https://github.com/BG3-Community-Library-Team/BG3-Community-Library | 一手 |
| [3] | GitHub – BG3-Compatibility-Framework Readme.md | https://github.com/BG3-Community-Library-Team/BG3-Compatibility-Framework/blob/main/Readme.md | 一手 |
| [4] | GitHub – BG3-Community-Library-Team/CF-Example-Mods | https://github.com/BG3-Community-Library-Team/CF-Example-Mods | 一手 |
| [5] | GitHub – AtilioA/BG3-MCM（Mod Configuration Menu） | https://github.com/AtilioA/BG3-MCM | 一手 |
| [6] | GitHub – TheRealDjmr/BG3ImprovedUI | https://github.com/TheRealDjmr/BG3ImprovedUI | 一手 |
| [7] | GitHub – doombubbles/bg3-mods | https://github.com/doombubbles/bg3-mods | 一手 |
| [8] | GitHub topic 页 "baldurs-gate-3" | https://github.com/topics/baldurs-gate-3 | 一手（GitHub 索引页） |
| [9] | bilibili《博德之门3【MOD制作教学】：从0开始制作一个新的子职业》 | https://www.bilibili.com/video/BV1Ch4y1w73Z/ | 一手（作者自述） |

### 5.2 一手页面·仅经搜索摘要
| # | 标题 | URL | 类型 |
|---|---|---|---|
| [10] | Nexus – Artificer class and all subclasses | https://www.nexusmods.com/baldursgate3/mods/1779 | 一手·摘要 |
| [11] | Nexus – Artificer 附属：Feat Every Level / 12 Levels Option / Artificer Tweaks | https://www.nexusmods.com/baldursgate3/mods/5566 ; https://www.nexusmods.com/baldursgate3/mods/3224 ; https://www.nexusmods.com/baldursgate3/mods/16873 | 一手·摘要 |
| [12] | Nexus – Artificer class and all subclasses CHS | https://www.nexusmods.com/baldursgate3/mods/15477 | 一手·摘要 |
| [13] | Nexus – Blood Hunter Class – Lycan and Ghostslayer Subclasses | https://www.nexusmods.com/baldursgate3/mods/2151 | 一手·摘要 |
| [14] | mod.io – Blood Hunter Class | https://mod.io/g/baldursgate3/m/blood-hunter | 一手·摘要 |
| [15] | Nexus – Blood Hunter Expanded (Profane Soul and Mutant) Full Release Patch 8 | https://www.nexusmods.com/baldursgate3/mods/5527 | 一手·摘要 |
| [16] | Nexus – Blood Hunter 翻译：PTBR / ES / ES(1.12) / FR / CH | https://www.nexusmods.com/baldursgate3/mods/4569 ; https://www.nexusmods.com/baldursgate3/mods/4646 ; https://www.nexusmods.com/baldursgate3/mods/11140 ; https://www.nexusmods.com/baldursgate3/mods/5576 ; https://www.nexusmods.com/baldursgate3/mods/16818 | 一手·摘要 |
| [17] | Nexus – Mystic Class | https://www.nexusmods.com/baldursgate3/mods/2786 | 一手·摘要 |
| [18] | mod.io – Mystic Class | https://mod.io/g/baldursgate3/m/mystic-class1 | 一手·摘要 |
| [19] | Nexus 文章 – Mystic Expansion details | https://www.nexusmods.com/baldursgate3/articles/390 | 一手·摘要 |
| [20] | Nexus – Mystic 翻译：CHS ×3 / PTBR-Patch7 / PTBR | https://www.nexusmods.com/baldursgate3/mods/15581 ; https://www.nexusmods.com/baldursgate3/mods/12935 ; https://www.nexusmods.com/baldursgate3/mods/14301 ; https://www.nexusmods.com/baldursgate3/mods/12244 ; https://www.nexusmods.com/baldursgate3/mods/15482 | 一手·摘要 |
| [21] | Nexus – Death Knight Class – Champion of the Lich King | https://www.nexusmods.com/baldursgate3/mods/1725 | 一手·摘要 |
| [22] | Nexus – DK CotLK 翻译：ES / CHT / PTBR / KOR / ITA / RU | https://www.nexusmods.com/baldursgate3/mods/9195 ; https://www.nexusmods.com/baldursgate3/mods/13838 ; https://www.nexusmods.com/baldursgate3/mods/2024 ; https://www.nexusmods.com/baldursgate3/mods/19962 ; https://www.nexusmods.com/baldursgate3/mods/9223 ; https://www.nexusmods.com/baldursgate3/mods/2008 | 一手·摘要 |
| [23] | mod.io – The Death Knight（另有 death-knight、deathknight2） | https://mod.io/g/baldursgate3/m/the-death-knight ; https://mod.io/g/baldursgate3/m/death-knight ; https://mod.io/g/baldursgate3/m/deathknight2 | 一手·摘要（直接抓取仅得标题） |
| [24] | mod.io – WoWDeathKnight | https://mod.io/g/baldursgate3/m/wowdeathknight | 一手·摘要 |
| [25] | Nexus – Death Knight Class – From World of Warcraft；Death Knight (13495) | https://www.nexusmods.com/baldursgate3/mods/15103 ; https://www.nexusmods.com/baldursgate3/mods/13495 | 一手·摘要 |
| [26] | Nexus – Deathknight – Knights of the Duskrose | https://www.nexusmods.com/baldursgate3/mods/1472 | 一手·摘要 |
| [27] | Nexus – Monk – Way of the Astral Self Subclass Standalone | https://www.nexusmods.com/baldursgate3/mods/3044 | 一手·摘要 |
| [28] | Nexus – 5e Way of the Astral Self – Monk Subclass (Deprecated) | https://www.nexusmods.com/baldursgate3/mods/10078 | 一手·摘要 |
| [29] | Nexus – Astral Self 翻译：CHS / Spanish | https://www.nexusmods.com/baldursgate3/mods/13131 ; https://www.nexusmods.com/baldursgate3/mods/11539 | 一手·摘要 |
| [30] | Nexus – 5e Fighter Subclasses Combined | https://www.nexusmods.com/baldursgate3/mods/15060 | 一手·摘要 |
| [31] | Nexus – Bard Sorcerer Subclasses Combined | https://www.nexusmods.com/baldursgate3/mods/3446 | 一手·摘要 |
| [32] | Nexus – Double Subclass (choose two subclasses) | https://www.nexusmods.com/baldursgate3/mods/13636 | 一手·摘要 |
| [33] | Nexus – Compatibility Framework（含 docs 标签页 "Subclass Compatibility Framework"） | https://www.nexusmods.com/baldursgate3/mods/1933 | 一手·摘要 |
| [34] | Nexus – Volition Cabinet | https://www.nexusmods.com/baldursgate3/mods/7676 | 一手·摘要 |
| [35] | GitHub – AtilioA/BG3-volition-cabinet（README、nexus_description.bb、Actions） | https://github.com/AtilioA/BG3-volition-cabinet | 一手·摘要 |
| [36] | Nexus – ImpUI (ImprovedUI)；mod.io – ImpUI | https://www.nexusmods.com/baldursgate3/mods/366 ; https://mod.io/g/baldursgate3/m/impui | 一手·摘要 |
| [37] | Nexus – ImpUI_P8_Fork (ImprovedUI) | https://www.nexusmods.com/baldursgate3/mods/16649 | 一手·摘要 |
| [38] | GitHub – valsan-azerty-boi/BG3ImprovedUI（P8 fork） | https://github.com/valsan-azerty-boi/BG3ImprovedUI | 一手·摘要 |
| [39] | GitHub – CovelissLyvain/BG3ImprovedUI-with-Illrigger | https://github.com/CovelissLyvain/BG3ImprovedUI-with-Illrigger | 一手·摘要 |
| [40] | bg3.wiki – Modding: Class icons | https://bg3.wiki/wiki/Modding:Modding_class_icons | 二手（社区 wiki） |
| [41] | Thunderstore – ImprovedUI（ShinyHobo_Djmr_AlanaSP） | https://thunderstore.io/c/baldurs-gate-3/p/ShinyHobo_Djmr_AlanaSP/ImprovedUI/ | 一手·摘要（镜像） |
| [42] | BG3 Modding Community Wiki – Patch 7 Troubleshooting | https://wiki.bg3.community/en/Tutorials/patch7-troubleshooting | 二手（社区 wiki） |
| [43] | Nexus – 5e Spells | https://www.nexusmods.com/baldursgate3/mods/125 | 一手·摘要 |
| [44] | mod.io – 5e Spells: WIP | https://mod.io/g/baldursgate3/m/5e-spells-wip | 一手·摘要 |
| [45] | Nexus – 5e Spells 生态：Compatibility Patch / 5eSpells and Expansion Patch / Practical 5e Spells / Chiz's Adjustments / Veenab Homebrew / Miscellaneous Spell Patches | https://www.nexusmods.com/baldursgate3/mods/7054 ; https://www.nexusmods.com/baldursgate3/mods/22565 ; https://www.nexusmods.com/baldursgate3/mods/20940 ; https://www.nexusmods.com/baldursgate3/mods/19247 ; https://www.nexusmods.com/baldursgate3/mods/14824 ; https://www.nexusmods.com/baldursgate3/mods/17233 | 一手·摘要 |
| [46] | Nexus – UnlockLevelCurve – Level 13-20 I PATCH 8 | https://www.nexusmods.com/baldursgate3/mods/377 | 一手·摘要 |
| [47] | CL wiki – Building a Class Mod | https://github.com/BG3-Community-Library-Team/BG3-Community-Library/wiki/Building-a-Class-Mod | 二手（社区 wiki） |
| [48] | CL wiki – Subclass Compatibility Framework | https://github.com/BG3-Community-Library-Team/BG3-Community-Library/wiki/Subclass-Compatibility-Framework | 二手（社区 wiki） |
| [49] | CF wiki – _Class Module | https://github.com/BG3-Community-Library-Team/BG3-Compatibility-Framework/wiki/_Class-Module | 一手·摘要 |
| [50] | wiki.bg3.community – Basic Class Creation | https://wiki.bg3.community/Tutorials/Classes/Basic-Class-Creation | 二手（社区 wiki） |
| [51] | wiki.bg3.community – Subclass Creation For An Existing Class | https://wiki.bg3.community/Tutorials/Classes/Subclass_Creation_For_An_Existing_Class | 二手（社区 wiki） |
| [52] | wiki.bg3.community – Dev Environment Set-up | https://wiki.bg3.community/Tutorials/General/setting-up-a-dev-environment | 二手（社区 wiki） |
| [53] | GitHub – FrederickEngelhardt/bg3-progressions-compatibility-patches；Nexus 1572；旧 SCF 仓库名 | https://github.com/FrederickEngelhardt/bg3-progressions-compatibility-patches ; https://www.nexusmods.com/baldursgate3/mods/1572 ; https://github.com/BG3-Community-Library-Team/BG3-Subclass-Compatibility-Framework（未验证） | 一手·摘要 |
| [54] | GitHub – LaughingLeader/BG3ModManager | https://github.com/laughingleader/bg3modmanager | 一手·摘要 |
| [55] | Nexus – LarinStudios Localization Helper | https://www.nexusmods.com/baldursgate3/mods/3136 | 一手·摘要 |
| [56] | GitHub 组织 – BG3-Community-Library-Team（23 个仓库） | https://github.com/BG3-Community-Library-Team | 一手·摘要 |
| [57] | Nexus – CF 补丁类：Compatibility Framework Patch for Modded Subclasses / CF Subclass Patches / Subclass Compatch / Plus Subclasses – Previewer | https://www.nexusmods.com/baldursgate3/mods/17062 ; https://www.nexusmods.com/baldursgate3/mods/6996 ; https://www.nexusmods.com/baldursgate3/mods/6786 ; https://www.nexusmods.com/baldursgate3/mods/3867 | 一手·摘要 |
| [58] | Nexus – Character Preset Framework (CPF) | https://www.nexusmods.com/baldursgate3/mods/19805 | 一手·摘要 |
| [59] | GitHub – novus213/BG3_KendersLabsCoreLibs | https://github.com/novus213/BG3_KendersLabsCoreLibs | 一手·摘要 |

### 5.3 中文社区
| # | 标题 | URL | 类型 |
|---|---|---|---|
| [60] | bilibili《8号补丁子职mod合集 抢先体验 完美整合！职业介绍和mod安装教程》 | https://www.bilibili.com/video/av113609518617938/ | 二手 |
| [61] | bilibili《我们把"系统"做进了游戏！真正代码级优化的mod整合包！》 | https://www.bilibili.com/video/BV16ag96jEo4/ | 二手 |
| [62] | bilibili《博德之门3职业mod升级技能一览【德鲁伊篇】星辰结社》 | https://www.bilibili.com/video/BV1yH4y1y7SK/ | 二手 |
| [63] | bilibili《博德之门3 v4.1：重燃费伦 V1 … 全新职业，附带超详细安装教程&模组管理器》 | https://www.bilibili.com/video/BV1dHjA6kEJQ/ | 二手 |
| [64] | bilibili 专栏《全网最全200+Mod整合包与指南(Patch#4 Hotfix#10)》（抓取被验证码拦截） | https://www.bilibili.com/opus/835217843121291301 | 二手 |
| [65] | 3DM《基于强大的本地化助手 BG3 LocaHelper 制作独立汉化mod 教程 2023.11.5 第二版》 | https://bbs.3dmgame.com/thread-6464902-1-1.html | 二手 |
| [66] | 3DM《mod 汉化教程 基于 BG3 Locahelper 2023.10.22 第一版》 | https://bbs.3dmgame.com/thread-6461116-1-1.html | 二手 |
| [67] | 3DM 博德之门3 论坛（含求助/修改分区） | https://bbs.3dmgame.com/forum-3000-1.html | 二手 |
| [68] | 3DM mod 站 / 补丁站 | https://mod.3dmgame.com/baldursgate3 ; https://dl.3dmgame.com/patch/b3mod.html | 二手 |
| [69] | 百度贴吧《关于MOD汉化过程的求助》 | https://tieba.baidu.com/p/9320998751 | 二手 |
| [70] | GameMale《非常简单的MOD汉化过程教学！》 | https://www.gamemale.com/thread-119405-1-1.html | 二手 |
| [71] | 知乎《【小枕の日常】〈博德之门3〉装备mod制作流程大纲》 | https://zhuanlan.zhihu.com/p/1927830072301166898 | 二手 |
| [72] | 知乎《怎么给博德之门3上mod？》 | https://zhuanlan.zhihu.com/p/661683997 | 二手 |
| [73] | 豆瓣小组《博德之门3MOD制作（装备/纹身）》 | https://www.douban.com/group/topic/295142051/ | 二手 |
| [74] | 游侠补丁《博德之门3基本MOD制作内容工作流程教程下载》 | https://patch.ali213.net/showpatch/256005.html | 二手 |

### 5.4 媒体 / 聚合站（三手）
| # | 标题 | URL | 类型 |
|---|---|---|---|
| [75] | ScreenRant – Baldur's Gate 3 Gets Another Popular D&D Class Thanks To Fan（Artificer） | https://screenrant.com/baldurs-gate-3-artificer-dnd-mod/ | 三手 |
| [76] | PCGamesN – You can now play Baldur's Gate 3 as one of WoW's most iconic classes | https://www.pcgamesn.com/baldurs-gate-3/world-of-warcraft-class | 三手 |
| [77] | ScreenRant – Mod Manager Guide (How To Fix Common Problems) | https://screenrant.com/baldurs-gate-3-mod-manager-fix/ | 三手 |
| [78] | bg3modmanager.net – BG3 Crashes After Patch 8 with Mods: 2026 Fix Guide | https://bg3modmanager.net/bg3-crashes-patch-8-mods-fix/ | 三手 |
| [79] | discovermods – Monk – Way of the Astral Self Subclass Standalone | https://discovermods.com/baldurs-gate-3/monk---way-of-the-astral-self-subclass-standalone/ | 三手 |
| [80] | TheGamer – Baldur's Gate 3 Mod Adds More D&D 5e Subclasses | https://www.thegamer.com/baldurs-gate-3-more-dungeons-and-dragons-fifth-edition-subclasses-mod/ | 三手 |
| [81] | Nexus 新闻 – Baldur's Gate 3 – Patch 8 | https://www.nexusmods.com/news/15251 | 二手 |
| [82] | GitHub – revblaze/BaldursModManager（macOS） | https://github.com/revblaze/BaldursModManager | 一手·摘要 |
| [83] | Nexus – Psionics – Wizard Subclass；mod.io – The Psion: Unearthed Arcana 2025 / The Psion Class | https://www.nexusmods.com/baldursgate3/mods/10014 ; https://mod.io/g/baldursgate3/m/the-psion-unearthed-arcana-2025 ; https://mod.io/g/baldursgate3/m/thepsion | 一手·摘要 |

---

## 6. 审计

| 项目 | 数值 |
|---|---|
| WebSearch 查询数 | 20（全部返回结果） |
| WebFetch 调用数 | 14 |
| WebFetch 成功（取得正文） | 9：[1][2][3][4][5][6][7][8][9] |
| WebFetch 失败 / 无有效正文 | 5：Nexus 1779（HTTP 403）、Nexus 2151（HTTP 403）、mod.io the-death-knight（仅返回标题）、web.archive.org 快照（工具禁止访问该域）、bilibili 专栏 opus（验证码页） |
| 重试情况 | 403 为确定性封禁，未做同 URL 重试；改用 web.archive.org 作替代路径（亦失败）。未出现"连续 3 次失败"停机情形 |
| 收到的去重来源（URL）数 | 约 110 个（含搜索结果中未引用的 Steam 讨论帖、YouTube 视频、维基百科等） |
| 引用来源条目数 | 83 条（[1]–[83]，部分条目合并多个同类 URL） |
| 标注为背景知识的内容 | 1 处（mod.io 需 Toolkit 打包，见第 3 节第 5 条） |
| 预算执行 | 达到约 20 次搜索 + 14 次抓取的预算后收尾 |
