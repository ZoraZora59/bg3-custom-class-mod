# 03 · 案例研究：职业类 Mod、基础框架与可学习的开源仓库

> 来源：`research/C-case-studies.md`（C）、`research/F-team-workflow.md`（F）。注意：本次 Nexus 页面对抓取工具返回 403、mod.io 为 JS 渲染，所以推荐数/依赖/Credits 多来自搜索摘要，标注"页面未显示"的字段需要在浏览器里人工补看。

## 1. 职业 / 子职业类 mod 案例

| Mod | 类型 | 作者 / 平台 | 依赖与技术特征 | 状态与团队线索 |
|---|---|---|---|---|
| **Artificer class and all subclasses** (Nexus 1779) | 全新基础职业，4 子职业（Alchemist / Armorer / Artillerist / Battle Smith） | Kidel（KiderionLykon）/ Nexus；GitHub `Kidel/BG3_Artificer`（MIT，477 commits，"collaborative project"，Issues 当 TODO）F[4] | 对 5e 做了"适配 BG3 约束的机制改编"；升级界面不能即时显示新增法术位，且只对原版施法者生效 F[4] | 第三方生态：Feat Every Level、12 Levels Option（把 20 级结构压到 12 级）、Artificer Tweaks、CHS/JP 翻译独立页 C[11][12] F[5] |
| **Blood Hunter Class – Lycan and Ghostslayer** (Nexus 2151 + mod.io) | 全新基础职业，改编 Matthew Mercer 2022 版，4 子职业，自定义动画与法术特效 | WolfeTK / Nexus + mod.io；v1.14（2025-11），3,893 endorsements（搜索摘要）C[13][14] | 兼容 UnlockLevelCurve 到 20 级 | 姊妹作 Blood Hunter Expanded 标题即写明 "Patch 8"，自带 FR/UK/RU；社区翻译 PTBR/ES/FR/CH 独立页 C[15][16] |
| **Mystic Class** (Nexus 2786 + mod.io) | 全新基础职业（UA 灵能）：独有资源 Psi Points、38 个 disciplines、全部子职业、做到 20 级 | 作者页面未显示 C[17][18] | 自定义资源系统的典型样本 | Mystic Expansion 可选文件；CHS 翻译至少 3 个独立页 C[19][20] |
| **Death Knight – Champion of the Lich King** (Nexus 1725) | 全新基础职业，30+ 魔兽风格自定义法术/被动 | VivaSortiara / Nexus C[21] | 需求列表：Mod Fixer + SE + ImprovedUI + Assets（Mod Fixer 已过时，说明描述未随补丁更新）C[21][42] | 六种翻译独立页 C[22] |
| **WoWDeathKnight** (mod.io) | 全新基础职业：符文系统，Blood/Frost/Unholy | doombubbles / mod.io；**开源** `doombubbles/bg3-mods`（含 GitHub Actions CI、scripts/、Wiki）C[7][24] | 单仓多 mod | 可作"完整职业 + 自动化打包"参考（作者自评高度定制、非通用脚手架） |
| **Way of the Astral Self** | 武僧子职业，两条实现线（Standalone 版 / 5e RAW 版已标 Deprecated） | Nexus 3044 / 10078 C[27][28] | 子职业包"接入 CF 即可工作" | 有 CHS/ES 翻译 |
| **5e Fighter Subclasses Combined** (Nexus 15060) | 子职业包 | 1.1.9.3，**2026-08-21 更新**，标签 "Patch 8 Compatible"，823 endorsements C[30] | — | 证明 2026 年生态仍活跃 |
| **Bard Sorcerer Subclasses Combined** (Nexus 3446) | 子职业包 | 页面未显示 C[31] | — | — |
| **CF-Example-Mods** (GitHub) | 3 个最小示例（SpellContainer / SpellLists / Boosts 三种注入） | BG3-Community-Library-Team，MIT C[4] | 接入 CF 的最小骨架 | 教学性质 |

补充观察 C[2.1]：
- 同一主题多实现并存是常态（Death Knight 至少 5 个实现、Astral Self 两条线）——**命名与描述要能区分自己**。
- Patch 8 后 Double Subclass 等 mod 需要把官方新子职业加回 progressions；5e Spells 移除了官方已收编的 Shadow Blade——**官方补丁新增内容会直接影响改 Progressions/法术库的 mod**。
- 没接 CF 的子职业 mod 会催生第三方"CF 补丁 mod"（Compatibility Framework Patch for Modded Subclasses、CF Subclass Patches…）——自己接好比让别人打补丁好。

## 2. 基础框架类 mod（"标准依赖栈"）

| 框架 | 解决什么 | 仓库 / 许可 | 协作方式 | 现状 |
|---|---|---|---|---|
| **Script Extender (bg3se)** | Lua/Osiris 脚本、控制台、调试器 | `Norbyte/bg3se`（1.5k star）C[1] | GitHub Issues/PR | v32（2026-06）支持 Patch 8 |
| **Community Library (CL)** | 公共法术/脚本/物品/状态/被动 + ReferenceScripts + wiki（Building a Class Mod） | `BG3-Community-Library-Team/BG3-Community-Library`，MIT C[2] | 三条路径：Discord 找 @NellsRelo 加入团队 / fork+PR（团队 review 并测试）/ Issue 模板 F[1][2] | 组织下 23 个仓库；提供 Sample-Template 起步模板 F[24] |
| **Compatibility Framework (CF)** | 运行时注入子职业/法术/列表/专长/资源，避免覆盖冲突 | `…/BG3-Compatibility-Framework`；Nexus 1933 C[3][33] | Wiki（Class Module / Selector API）、Issues | 2.8.2.0；SCF 已并入；需放加载顺序最底部 |
| **ImprovedUI (ImpUI)** | 旧版自定义职业/种族/神祇/资源图标与 CC UI | `TheRealDjmr/BG3ImprovedUI` C[6] | Discord + Issues；核心作者接力（AlanaSP → ShinyHobo → Djmr → Zee），Patch 8 期间 bibsan 补功能，Djmr 授权 `ImpUI_P8_Fork` F[6] | "无积极维护计划"；Patch 7 起类图标不再需要它 |
| **Mod Configuration Menu (MCM)** | 游戏内统一设置界面 | `AtilioA/BG3-MCM`，**AGPL-3.0**（注意衍生代码许可）C[5] | Issues/PR | 需 SE v18+ |
| **Volition Cabinet** | Volitio 系列 mod 的 Lua 公共库 | `AtilioA/BG3-volition-cabinet`，仓库内维护 `nexus_description.bb` C[35] | Actions CI | 2026-08 仍更新 |
| **5e Spells** | 补齐 5e 缺失法术，大量职业 mod 的法术来源 | Nexus 125；GitHub `Celestro/5eSpells`（数据全部开源作为兼容策略）C[43] F[7] | 作者 Celes + 上传/维护者 DiZ91891 | 2020-11 首发，2026-05 仍更新 |
| **UnlockLevelCurve** | 13–20 级 | Nexus 377 / mod.io，"Patch 8 Tested" C[46] B[28] | — | 职业 mod 缺 13–20 级节点会黑屏 |
| **ModFixer** | 旧版让 pak 被识别 | — | — | **Patch 7 起不需要** C[42] |

其他顺带发现：Character Preset Framework、FrederickEngelhardt 的 progressions-compatibility-patches、BG3ModStudio（Windows 一体化编辑器，2026-02 更新）、bg3d、BG3LocalizationMerger、Mod Change Tracker（导出所有 mod 对 stat 条目的修改，排查冲突用）C[64] F[23]。

## 3. 可作为模板 / 参考的开源仓库

| 仓库 | 适合学什么 | 许可 |
|---|---|---|
| `BG3-Community-Library-Team/Sample-Template` | "A Starting Point for your Own Mods"：目录骨架 F[24] G[G18] | 未显示 |
| `BG3-Community-Library-Team/CF-Example-Mods` | 接入 CF 的最小示例 C[4] | MIT |
| `BG3-Community-Library-Team/BG3-Community-Library` | 真实的 ClassDescriptions / ActionResourceDefinitions / DefaultValues / Tags / 图集文件（Death Knight 示例）B[15] | MIT |
| `doombubbles/bg3-mods` | 完整职业（WoWDeathKnight）+ `scripts/` + GitHub Actions C[7] | 未显示 |
| `Kidel/BG3_Artificer` | 大型职业 mod 的 Issues 驱动协作 F[4] | MIT |
| `AtilioA/BG3-volition-cabinet` | SE Lua 项目布局 + CI + 版本化 Nexus 描述 C[35] | 未显示 |
| `ZerdBG3/DnD-Rebalancing (RAW)` | 多语言 Localization 布局、隐藏型行动资源 B[16] | 未显示 |
| `FrederickEngelhardt/bg3-progressions-compatibility-patches` | 多 mod 改 Progressions 的补丁做法 C[53] | 未显示 |

未找到：Artificer 之外的头部职业 mod（Blood Hunter、Mystic、DK CotLK）的源码仓库；GitHub 上没有通用的"职业 mod 模板"仓库（多为工具类）C[2.3]。

## 4. 中文社区资源 C[2.4]

| 类型 | 资源 | 说明 |
|---|---|---|
| B 站职业制作教程 | 《博德之门3【MOD制作教学】：从0开始制作一个新的子职业》14 集（UP 主 18915063321，2023-09，约 3.5 万播放）C[9] | 本次唯一找到的中文职业制作系列；附工具包与示例子职业"幽暗之刃"；**上传于 Patch 7 之前，工具链可能过时** |
| B 站安装/整合 | 8 号补丁子职 mod 合集、200+ 职业整合包（自称附 MOD 制作文档）、职业 mod 技能一览等 C[60]-[64] | 中文玩家对职业 mod 需求旺盛；整合包作者是潜在分发渠道 |
| 3DM 汉化流程 | 《基于 BG3 LocaHelper 制作独立汉化 mod 教程》两版（2023-10/11）C[65][66] | 解包 → 只取 `Localization` 下 `.loca/.xml` → 翻译 → 转回 → 打包 |
| 贴吧 / GameMale / 知乎 / 豆瓣 / 游侠 | 汉化求助、装备 mod 流程、MOD 制作讨论、工作流教程下载 C[69]-[74] | 未见职业类制作教程 |
| Nexus 中文翻译者 | Artificer CHS、Mystic CHS×3、Blood Hunter CH、DK CotLK CHT、Astral Self CHS | **Localization 结构规范的英文原版很容易被社区汉化** |
| 交流平台 | 搜索摘要出现 QQ 群号（719701536、934517281，来源未定位，**需核实**）；未找到 Discord 中文频道 | 建议以 3DM 论坛、贴吧、B 站评论区为触点 |

## 5. 从案例提炼的"成功职业 mod 的共同做法" C[2.5] F[2.1]

1. **不覆盖原版文件，靠合并节点 / CF 运行时注入**（未接 CF 的子职业 mod 会被第三方打补丁）。
2. **类图标走官方路径**；旧教程的"fork ImpUI 改 IUI_ClassIcons"已过时。
3. **Nexus + mod.io 双发布**（Blood Hunter、Mystic、WoWDeathKnight、ImpUI、5e Spells 均如此）。
4. **标题/标签明示补丁版本**（"Patch 8 Compatible"）。
5. **模块化**：核心 + 可选扩展（Mystic Expansion）+ 允许第三方附属（Artificer 的 Feat Every Level / 12 Levels Option）。
6. **支持或明确声明不支持 13–20 级**。
7. **本地化开放**：保持 `Localization/` 规范，允许翻译；或自带多语言。
8. **开源 + CI + 版本化页面描述**（doombubbles、Volition Cabinet、CL 的 MIT）。
9. **清晰的弃用/迁移与所有权交接**（Astral Self 标 Deprecated；SCF 并入 CF；ImpUI 授权 fork）——长寿命 mod 靠这个活过多次大补丁。
10. **及时清理过时依赖**（反例：DK CotLK 仍列 Mod Fixer）。
11. **同主题多实现时靠命名/描述区分**。
12. **随官方补丁核对 Progressions 与法术库**（Double Subclass、5e Spells 的做法）。

## 6. 头部团队的组织形态（供 06 文档的职能设计参考）F[2.1]
- 团队普遍很小且松散，没有任何案例公开过分工表或工时；职能只能从 Credits、仓库结构和衍生 mod 反推。
- Community Library：GitHub 组织 + Discord 招募（"Ask!"），贡献流程 fork → 改动 → 自测（可能需要辅助测试 mod）→ PR → 团队 review 并测试 → 合并或说明理由。
- ImpUI：4 位核心作者接力 + 补丁期贡献者 + 授权 fork。
- 5e Spells：作者与上传/维护者分离；公开数据仓库本身是兼容策略。
- 反复出现的职能：设计/平衡、数据实现、脚本、图标（可用 CC 素材）、VFX（复用原版为主）、本地化（社区独立翻译 mod）、测试、兼容性/框架维护、社区支持与文档。工具事实标准：GitHub（仓库/Issue 模板/Wiki/Releases）+ 官方 BG3 Discord 的 #bg3-modding / #bg3-scripting。
