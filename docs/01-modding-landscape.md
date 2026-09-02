# 01 · BG3 Mod 开发方式总览（截至 2026-09-02）

> 引用约定：`A[15]` 表示 `research/A-tooling-pipeline.md` 来源表第 15 条；`G[G4]` 表示 `research/G-official-docs-browser.md` 的来源 G4。研究报告里每条结论都带来源与"仅摘要 / 直读"标记，本文只保留结论。

## 1. 三条开发路线，最终都产出同一种东西

BG3 的 mod 本质上是一个 `.pak` 包，里面是 Larian 数据格式（`.lsx/.lsf` 表、stats `.txt`、`.loca` 本地化、DDS 图标）。不同路线只是"用什么工具生产这些文件"。

| 路线 | 工具 | 适合做什么 | 平台 | 备注 |
|---|---|---|---|---|
| **① 官方 Toolkit**（2024-09 Patch 7 随游戏发布） | Steam "Tools" 分类免费应用 + BG3 属性里启用 "BG3 Toolkit Data" DLC；GOG 同样提供 G[G2] | 官方文档明确列出 "Classes and Subclasses：Create new class types or modify existing ones" G[G9]；有官方逐步教程《Adding Classes and Subclasses》G[G4] | **仅 Windows**（官方要求 32 GB 内存、8 GB 显存、约 160 GB 磁盘）A[1][2][14]；Linux/Proton 有卡在 "Starting Services" 的报告，未确认可用 A[12][13] | 唯一能发布到 mod.io（游戏内 Mod 管理器 / 主机）的通道 G[G5]；也能 "Publish Local" 只出 `.pak` 给 Nexus |
| **② 纯文本数据 + 社区工具**（Patch 7 之前的主流方式，现在仍然有效） | VS Code 手写/脚本生成 `.lsx`、`.txt`、`.xml`，用 LSLib（Divine/ConverterApp）或 Modder's Multitool 打包 G[G17] E[6][7] | 和 Toolkit 产出完全相同的数据文件；Toolkit 的 UUID Object Editor 本质上就是这些表的表格视图 G[G17] | 编辑在任何平台；**打包工具是 Windows 程序**（Divine 是 .NET 8 但工程引用 C++/CLI 原生库，Mac 上未验证）E[本机核查] G[G10][G11] | 适合 git 协作、diff、脚本校验；本项目 Mac 侧的主要工作方式 |
| **③ Script Extender（BG3SE）脚本层** | Norbyte 的 `DWrite.dll` 注入 + Lua/Osiris API E[1][2] | 运行时逻辑：跨回合状态机、自定义 UI（IMGUI/MCM）、动态改 stats、跨 mod 注入（Compatibility Framework 依赖它） E[2][25][46] | Windows；Linux/Steam Deck 需 `WINEDLLOVERRIDES="DWrite.dll=n,b"`；**Mac 原生版无官方 SE**（社区有非官方逆向重写 `bg3se-macos`） A[33][36][38][42] | 依赖 SE 的 mod 进不了主机目录（主机排除 `.dll`）G[G9]；社区惯例发 Nexus |

**结论**：职业 mod 的主体（进阶表、被动、法术、资源、反应）全部可以只用路线 ①/② 的"纯数据"完成，官方职业教程全程没有 Lua/Osiris E[15][20] G[G4]。SE 是可选增强层，应该拆成独立模块。

## 2. 工具链清单与现状（2026-09）

| 工具 | 作者 | 最新状态 | 作用 | 备注 |
|---|---|---|---|---|
| Baldur's Gate 3 Toolkit | Larian | Patch 8 数据已并入（2025-04）B[37]；官方文档站持续更新（职业页 2025-05、本地化页 2025-10）B[1][2] | 建表、Stats、图集、图标转换、Osiris/Anubis、本地打包、mod.io 发布 | 需要 Larian 账号 + mod.io 账号绑定 G[G2] |
| LSLib / ExportTool（ConverterApp GUI + Divine CLI） | Norbyte | v1.20.4（发布日期存在分歧：A 报告记 2025-01-24，H 报告经 GitHub Releases API 核实为 2026-01-24、其前一版 v1.20.3 为 2025-09-22，以 H 为准 H[9]），需 .NET 8 Desktop Runtime A[15] | 解/打包 `.pak`、`.lsf↔.lsx`、`.loca↔.xml`、GR2 模型 A[16] | CLI 参数已从源码核实（见 05 文档）E[7] |
| BG3 Modder's Multitool | ShinyHobo | v0.10.6；GitHub + GitLab 双托管，source-available 非开源 A[21][22] G[G12][G13] | 索引式解包与搜索、一键打包、UUID/handle 生成、`x.lsf.lsx`→`x.lsf` 自动转换 | 依赖 LSLib ≥ 1.15.9 |
| BG3 Mod Manager (BG3MM) | LaughingLeader | 1.0.12.9（2025-05），.NET 8，适配 Patch 7 新 modsettings 格式 A[30][31] | 加载顺序、导出到游戏、Version64 生成 | 与游戏内管理器写同一个 `modsettings.lsx`，二选一使用 D[4][39] |
| 游戏内 Mod Manager + mod.io | Larian | Patch 7 起 A[11] | 浏览/安装/更新 mod.io mod；第三方 mod 显示为 "third-party" 但不能在此更新 G[G9] | 主机/Mac/GeForce NOW 玩家的唯一渠道 G[G9] |
| Script Extender (BG3SE) | Norbyte | 启动器 v32（2026-06-21）"Supports patch 8"，本体自动在线更新；v31 起内嵌离线回退 A[33] E[4] | Lua/Osiris API、控制台、调试器 | 只支持最新游戏版本；补丁日会有失效期 D[9] |
| Compatibility Framework (CF) | BG3 Community Library Team | 2.8.2.0；SCF 已并入 C[3][33] | 运行时把子职业/法术/列表/专长注入原版数据，避免覆盖冲突；≥2.6.5.8 只要 `ParentGuid` 正确就自动注入子职业 B[9][11] | **依赖 SE**；放加载顺序最底部 C[3] |
| ImprovedUI (ImpUI) | Djmr 等 | 原仓库"无积极维护计划"，Patch 8 有 `ImpUI_P8_Fork` C[6][37] | 旧版自定义职业图标/角色创建 UI 的必需品 | **Patch 7 起类图标原生支持，不再需要 ImpUI**；只有自定义行动资源图标仍依赖它 B[1][4][18] |
| Community Library (CL) | 同上 | MIT；含 ReferenceScripts、Building a Class Mod wiki C[2][47] | 公共法术/被动/脚本库、参考实现 | 可选依赖 |
| Mod Configuration Menu (MCM) | Volitio (AtilioA) | AGPL-3.0；需 SE v18+ C[5] E[46] | 游戏内 mod 设置界面 | IMGUI 字体对非拉丁字符（含中文）支持不确定 E[46] |
| ModFixer | — | **Patch 7 起不再需要** C[42] D[5] | 旧时代让 pak 被识别 | 新 mod 不要再捆绑 |
| Vortex | Nexus | Patch 7 后一度失效；bg3.wiki 明确不推荐 A[25][32] | 通用 mod 管理器 | 不建议 |
| bg3se-macos | tdimino（社区） | v0.42.0，自称 94.8% API 对齐；非官方逆向工程 A[38] | Mac 原生版跑 SE mod | 只能作参考，不能替代 Windows 验证 |

## 3. 文件格式速查

| 格式 | 说明 | 转换 |
|---|---|---|
| `.pak` | Larian 资源包，游戏数据与 mod 都是它 | Divine `create-package` / `extract-package`；Multitool；Toolkit Publish Local |
| `.lsx` / `.lsf` / `.lsb` / `.lsj` | 同一种资源树的 XML 明文 / 二进制 / 旧二进制 / JSON 形式 | Divine `convert-resource`；Multitool 按 `x.lsf.lsx` 命名自动转回 |
| `.loca` / `.xml` | 本地化二进制 / 明文（`<content contentuid="…" version="1">`） | Divine `convert-loca`；Multitool 按 `x.loca.xml` 自动转 |
| stats `.txt` | `new entry` / `type` / `using` / `data` 文本，无需转换 | — |
| `.dds` | 图标纹理；类图标 BC7/BC1，技能图集 DXT5 无 mipmap | Toolkit Convert UI Assets / Texture Atlas Editor；GIMP、Paint.net、NVIDIA Texture Tools |
| `.gr2` | 模型/动画 | ExportTool（需 Windows 原生 `granny2.dll`）A[23] |
| `meta.lsx` | mod 元数据：`Folder`（必须与 `Mods/<Folder>`、`Public/<Folder>` 一致）、`Name`、`UUID`、`Version64`、`Dependencies` A[24][26] | 保持 `.lsx` 明文，不要转 `.lsf` D[1] |

原版数据包：`Shared.pak`（职业/进阶/列表等主要在其 `Public/Shared` 与 `Public/SharedDev`）、`Gustav.pak`（关卡、对话、装备 stats）、`English.pak`（本地化）、`Icons`、`Textures`、`Models` 等；做数据 mod 至少解包 English / Gustav / Shared / Icons A[23]。

**Toolkit 工程落盘位置**（官方）G[G3]：`Data/Projects/<Mod>`（工程元数据）、`Data/Editor/Mods/<Mod>`（编辑器专用，不打包）、`Data/Mods/<Mod>`（打包：UI 资源、**本地化**、Osiris）、`Data/Public/<Mod>`（打包：**stats、UUID 表、图集**）、`Data/Generated/Public/<Mod>`（虚拟纹理）。git 要同步的就是后三个。

## 4. 发布渠道与规则

| | mod.io（官方管线） | Nexus Mods |
|---|---|---|
| 上传方式 | Toolkit → Project Settings → Authenticate → Publish；先过自动扫描再 Go live G[G5] | 网页上传 `.pak`/zip；后续版本可用官方 `Nexus-Mods/upload-action` 自动化（Upload API 仍是 beta）E[18][19] |
| 覆盖平台 | PC、PS5、Xbox、Mac、GeForce NOW（主机需额外人工审核）G[G9] | PC（Windows；Linux 经 Proton） |
| 依赖声明 | Toolkit 里设一次（管加载顺序）+ mod.io 里设一次（管自动下载）G[G5] | 页面文字说明 |
| 冲突声明 | Toolkit Conflicts 标签：检测到冲突时自动禁用本 mod G[G5][G6] | 无 |
| 硬性规则 | 原创或已授权；不得与可识别的第三方品牌/角色相似；不得含歧视/露骨/违法内容；不得解锁付费或成就物品；缩略图不得含裸露；AI 生图需遵守所用服务的许可 G[G9] | 免费可得、素材授权（Nexus 总则本次未检索 D[3.3]） |
| 主机排除项 | 改 shader、增加裸露/暴力、含 `.exe/.dll/.zip`、**新增可玩种族**、内测失败、崩溃 G[G9] | — |
| Script Extender | 页面**没有**明文禁止 PC 端 SE 依赖，但主机排除 `.dll`；社区惯例：SE mod 发 Nexus G[G9] A[6][8] | 允许 |
| 成就 | 官方准则页：启用任何 mod（第三方或 mod.io）后**成就自动禁用** G[G9]（SE 有重新开启成就的设置 A[34]） | 同 |
| 联机 | 所有人需相同 mod；加入大厅时提示下载缺失 mod / 启停不匹配项 G[G9] | 同 |
| 同 ID 冲突 | "所有 mod 文件合并加载；两个 mod 改同一 ID 条目时，加载顺序靠后者胜出" G[G9] | 同 |
| 长期支持 | Larian："除发布后的关键修复外，目前没有技术能力提供长期支持" G[G9] | — |

**本项目的发布策略**（详见 06 文档）：核心职业包做成纯数据 → Toolkit 发 mod.io（含主机）+ Nexus 双轨；SE 增强模块只发 Nexus。两边 `UUID` 相同、`Version64` 同步，否则玩家联机会因版本不一致失败 D[1][12]。

## 5. 时间线（影响 mod 的关键版本）

- **Patch 7（2024-09）**：官方 Toolkit + 游戏内 Mod 管理器 + mod.io；`modsettings.lsx` 位置不变但格式与写入方变了；ModFixer 不再需要；类图标原生支持；Progression 节点可合并（SubClasses / PassivesAdded / Boosts / Selectors 等）A[11][25] B[17] C[42]。
- **Patch 8（2025-04-15，官方称"最后一次大补丁"）**：12 个原版职业各加 1 个子职业（经 CF 方式加入以免被旧子职业 mod 挤掉）、照片模式、跨平台联机；修复"部分 mod 职业无法升级"的 bug；Toolkit 补入 Patch 8 数据 B[26][37] D[26][27] F[18]。
- **2026**：BG3SE v31（04-17）/ v32（06-21）仍在更新；5e Fighter Subclasses Combined 2026-08-21 仍在更新并标 Patch 8 Compatible；ImpUI 停更但有 P8 fork A[33] C[30][37]。截至 2026-09-02 未见 Patch 9 的迹象（未直接确认）A[2.5]。

## 6. 对本项目的直接结论

1. **能做**：自创全新职业（含子职业、自定义资源、法术、被动、反应）在官方管线内是明确支持、有官方教程的类型。
2. **主体不用 SE**：把 SE 留给"确实需要运行时逻辑"的功能，并拆成独立可选模块；这样核心包能上 mod.io/主机、补丁日风险最小。
3. **双机分工**：Mac 负责 git 里的明文数据、脚本校验、图标源图、Lua；Windows 负责 Toolkit 校验/图标转换/打包/发布、SE 与游戏内验证（详见 05 文档）。
4. **依赖清单最小化**：不列 ModFixer；类图标不依赖 ImpUI；CF 仅在"给原版职业加子职业"或需要跨 mod 注入时作可选依赖；避免自定义行动资源图标（仍依赖已停更的 ImpUI）B[18][25]。
