# 子课题 A：工具链、文件格式与发布渠道（BG3 自创职业 mod）

- 调研日期：2026-09-02
- 开发环境（本机实测）：macOS 26.6.2（Darwin 25.6.0）、Apple Silicon（arm64）、**未安装 dotnet**；另有一台 Windows 电脑负责官方 Toolkit / Script Extender / 游戏内验证（协调方背景更新）。
- 引用规则：`[n]` 指向文末来源表；标注 `[背景知识—非本次检索]` 的内容来自训练记忆，不计入来源统计；"未能确认"表示本次检索没有拿到可引用的证据。

---

## 1. TL;DR

1. **官方 Toolkit 只有 Windows 版**：Steam 免费"工具"类应用，要求 Windows 10 64-bit、32 GB 内存、8 GB+ 显存显卡、约 160 GB 磁盘，并需绑定 Larian 账号 + mod.io 账号 [1][2][3][14]。GOG 支持中心有专门的 Toolkit 文章，说明 GOG 渠道也提供，但具体安装方式未能确认（页面 403）[9]。Linux/Proton 下有"卡在 Starting Services"的社区报告，且没有找到确定可用的方案 [12][13]。
2. **新职业/子职业是官方文档明确覆盖的 mod 类型**：官方文档站有「Adding Classes and Subclasses」条目 [4]，mod.io 上有「Adding New Classes or Subclasses」指南（讲"新建一个职业并带多个子职业"）[7]；因此纯数据型职业 mod 走官方管线在原则上可行。
3. **mod.io 管线的硬限制**：跨平台/主机不接受直接关卡编辑与故事/过场/对话/任务等核心内容改动；需要 Script Extender 的 mod 不能上 mod.io，只能打包后发到 Nexus 等其它平台 [6][8]。主机端还有一层额外审核 [8]。
4. **LSLib（Norbyte）**：抓取到的最新发布为 **v1.20.4（2025-01-24）**，运行需 **.NET 8.0 Desktop Runtime**；含 ConverterApp（GUI）与 Divine（CLI），支持 PAK 解/打包、LSB/LSF/LSX/LSJ 互转、GR2↔glTF/Collada、LOCA↔XML [15][16][23]。**macOS 官方不支持**（issue #236 自 2024-04 起无人回复）[18]；Linux 下 `dotnet Divine.dll` 能启动但曾有绝对路径被当作相对路径的 bug [17]；GR2 转换依赖 Windows 原生 `granny2.dll` [23]。
5. **BG3 Modder's Multitool（ShinyHobo）**：Windows 工具，Thunderstore 上为 v0.10.6，依赖 LSLib ≥ 1.15.9，功能覆盖解包/索引搜索/一键打包/UUID 与 TranslatedString 句柄生成/LSX 批量转换等 [21][22]。**注意：其 GitHub 仓库地址在 2026-09-02 三次抓取均返回 404**，现状需要复核 [21]。
6. **Mod 管理**：Patch 7（2024-09）引入游戏内 Mod Manager + mod.io 订阅 [11]；BG3 Mod Manager（LaughingLeader）在 2025-04 升级到 .NET 8 并于 1.0.12.x 系列适配新 modsettings.lsx，最新 1.0.12.9（2025-05-18）[30][31]；Vortex 在 Patch 7 时明显掉队，bg3.wiki 明确"不推荐" [25][32]。modsettings.lsx **位置未变**（仍在 `PlayerProfiles\Public\`），变的是格式与写入方 [25][31]。
7. **Script Extender（BG3SE）**：`DWrite.dll` 放入 `Baldurs Gate 3\bin`，启动时自动在线更新；GitHub 最新发布 v32（2026-06-21）与 v31（2026-04-17）均标注支持 Patch 8，v31 起把 SE 内嵌进启动器作为离线回退 [33][35]。Linux/Steam Deck 用 `WINEDLLOVERRIDES="DWrite.dll=n,b" %command%` [33][36]。**macOS 原生版没有官方 SE** [42]；社区从零重写的 `bg3se-macos` 已到 v0.42.0、自称 94.8% API 对齐并在 macOS 26.2 上测试过，但属非官方逆向项目 [38]。
8. **双机分工结论**：Mac 负责文本层（`.lsx` / stats `.txt` / 本地化 `.xml`、UUID/句柄/Version64 生成、git 管理），Windows 负责 Toolkit 校验、打包发布、SE 与游戏内验证。Mac 上用 .NET 8 跑 `Divine.dll` 做解包/转换/打包**理论可行但本次没有直接证据**，需要按第 7 节的实测清单验证。

---

## 2. 分节详细发现

### 2.1 官方 Baldur's Gate 3 Toolkit

**获取方式与账号**
- Steam 商店"Tools"分类下的免费独立应用「Baldur's Gate 3 Toolkit」[1][2][14]；搜索结果中的商店条目标题为「Baldur's Gate 3 Toolkit Data」（`store.steampowered.com/app/2956320/`），可能是数据 depot 而非主程序条目，未能进一步确认 [2]。
- 需要 Larian 账号并与 mod.io 账号关联，之后才能在 Toolkit 内创建/发布 mod [1][3][5]。
- GOG：GOG 支持中心存在标题为「Baldur's Gate 3 Toolkit」的文章 [9]，说明 GOG 用户也有获取途径，但页面抓取 403，安装方式（Galaxy 内 DLC 还是独立下载）未能确认。

**系统要求（来源为搜索摘要，原页面 403）**
- OS：Windows 10 64-bit；CPU：Intel i7 8700K / AMD R5 3600；内存：32 GB；显卡：Nvidia 2060 Super / AMD RX 5700 XT（8 GB+ 显存）；磁盘：约 160 GB [1][2][14]。
- 明确"仅 PC/Windows"，没有 macOS 或 Linux 版本 [1][14]。

**Linux / Proton 社区报告**
- Toolkit 在 Steam 里是独立应用，因而拥有独立的 Proton/Wine prefix；有用户在把它指向游戏 Data 目录后卡在 "Starting Services" 界面，多名 Linux 用户报告同样问题且当时没有可用解法（Patch 7 时期的讨论串）[12]。
- 2025 年出现了一份标题含 "Modding Toolkit" 的 Steam Linux 指南（WIP）[13]，暗示后来可能有可行路径，但本次因 Steam 限流未能读取其内容——**Linux 下 Toolkit 是否可用：未能确认**。
- 与本项目无关但可记录：Steam Deck 原生版会自动下载 mod.io 订阅的 mod [10]。

**功能范围与官方教程**
- Community Update #27 与相关报道：Toolkit 制作的 mod 可上传到 mod.io，玩家在游戏内直接浏览安装 [8][11]；Toolkit 支持使用 Larian 自家的 Osiris 脚本语言 [14]。
- 官方文档站 `docs.baldursgate3.game` 的主页列有「Adding Classes and Subclasses: How to add classes and subclasses to the game」[4]；mod.io 上的官方指南「Adding New Classes or Subclasses」描述为"创建一个新职业并带若干子职业，走完所有主要设置"[7]。**结论：新职业/子职业属于官方明确支持并有教程的 mod 类型。**
- 社区补充：Nexus 上有针对"给现有职业加子职业并新建被动/主动技能"的完整教程 [43]；Larian 论坛有官方置顶的「Modding: Getting Started」系列 [44]。
- 官方文档站本次两次抓取均 403（Cloudflare 类拦截），文档正文未能读取；上述条目来自搜索摘要。

**发布到 mod.io 的规则（来源为搜索摘要，mod.io 域名被本会话抓取工具拦截）**
- 跨平台限制：直接关卡编辑，以及对故事、过场、对话、任务等核心元素的改动，因技术与平台规范限制无法进入跨平台管线 [6][8]。
- 不被管线支持的改动（如脚本改动、NSFW）仍可用工具本地打包后发布到其它平台 [6][8]；"绝对需要 Script Extender 的 mod 不能上 mod.io"这一表述出现在搜索摘要中，其原始出处（mod.io 指南或社区讨论）未能核实，置信度中等 [6]。
- 主机端另有一层额外筛选（curation），并非所有 PC mod 都会开放给主机 [8]。
- 审核流程细节（时长、驳回标准、是否要求必须用 Toolkit 上传）**未能确认**。

### 2.2 Norbyte LSLib / ExportTool / ConverterApp / Divine

**版本与运行时**
- Releases 页面抓取结果：v1.20.4（2025-01-24，最新）、v1.20.3（2024-09-22）、v1.20.2（2024-09-05）、v1.20.1 Beta（2024-08-16）；近期各版均要求 **.NET 8.0 Desktop Runtime** [15]。
- 来源分歧：早期 v1.20.x 发布说明曾写"v1.20 为 beta，稳定版请看 v1.19.5"[15][19]；到 v1.20.4 时 GitHub 已把它作为最新版本展示 [15]。Nexus 论坛也记录过 LSLib 需要 .NET 6/8 Desktop Runtime 的排障帖 [20]。
- 截至 2026-09 是否有比 v1.20.4 更新的版本：抓取页面未显示，**未能确认**。
- v1.20 起以 glTF 2.0 取代 Collada 作为 Blender 导入/导出主格式，配套的 `dos2de_collada_exporter` 插件需同步更新 [15]。

**功能**
- README 列出支持：PAK 包的解包/创建、LSV 存档包、LSB/LSF/LSX/LSJ 资源文件、GR2/glTF/Collada 网格与动画转换、Osiris 故事数据库（OSI）等；工具包含 ConverterApp（GUI）和 Divine（CLI）[16]。
- bg3.wiki 的实操说明：ExportTool 即 `ConverterApp.exe` + Divine；`.loca`→`.xml`、`.gts`→`.dds` 等由 ExportTool 完成；文中建议先安装 1.15.13 以取得 `granny2.dll`，再升级到最新版 [23]——这表明 GR2 处理依赖 Windows 原生 DLL。

**跨平台（macOS / Linux）**
- Linux：有用户以 `dotnet /path/Divine.dll -a create-package -g bg3 -s /abs/path/MyMod` 方式运行，遇到 `System.InvalidOperationException: This operation is not supported for a relative URI`（绝对路径被当成相对路径），说明 Divine 在 Linux 的 .NET 上能启动，但存在过路径处理 bug，该 issue 的最终状态未能确认 [17]。
- 项目早年因 .NET Framework 依赖无法跨平台，issue #137 讨论过迁移到 .NET Core 以支持 Windows/Linux/Steam Deck [19]；现在要求 .NET 8 说明迁移已完成 [15]。
- macOS：issue #236「Mac OS Support」（2024-04-09 开启）询问能否在 macOS 运行、指出 Windows Forms 依赖，并建议仓库注明 "Windows only"；截至抓取时仍为 open、无维护者回复 [18]。**结论：macOS 无官方支持，也没有找到成功案例；ConverterApp（WinForms/WPF）基本可判定不可用，Divine CLI 的可行性需实测。**
- `[背景知识—非本次检索]` Divine 的 PAK/LSF/LSX/LOCA 处理为纯托管代码，理论上在 macOS 的 .NET 8 上可运行；GR2 路径因 `granny2.dll` 为原生 Windows 库而不可用。

### 2.3 BG3 Modder's Multitool（ShinyHobo）

- 定位："BG3 modding 的瑞士军刀"，从解包/搜索游戏文件到简化打包与工作区组织 [21]。
- 功能清单（Thunderstore 页面 + README 摘要）：自动生成 pak/zip/meta 元数据；LSF/LSB 自动转换（`example.lsf.lsx` 打包时自动转回 `example.lsf`）；依赖与多 pak 工作区支持；一次性提取部分/全部游戏资源；文件索引器 + 搜索；文件预览；**UUID 与 TranslatedString（句柄）生成器**；直接启动游戏；GameObject Explorer（stats/属性/图标/模型）；LSX 批量转换器；Collada 模型转换；WEM→OGG [21][22]。
- 本次来源**未见**"图标 atlas 生成"功能的描述——未能确认。
- 依赖：LSLib 1.15.9 或更高 [22]；`[背景知识—非本次检索]` 它是 .NET/WPF 桌面程序，仅 Windows。
- 许可：源码可见但非开源，未经许可禁止再分发/修改 [21]。
- 现状：Thunderstore 显示版本 0.10.6（未显示日期）[22]；**GitHub 仓库 `ShinyHobo/BG3-Modders-Multitool` 在 2026-09-02 的三次抓取（README、仓库根、raw）均 404**，而搜索索引仍列出其 wiki 页面 [21]——可能已改名、转私有或删除，需要在 Windows 侧复核后再决定是否依赖。
- 工作流变化：Multitool 更新后无需整包解压游戏文件，改为"Utilities > Index > Index Pak Files"建立索引、按需解出单个文件；大补丁后需清空重建索引 [23]。

### 2.4 Mod 管理：BG3MM / Vortex / 游戏内管理器 / modsettings.lsx

- **游戏内 Mod Manager**：Patch 7（2024-09，Steam 版本号 1.7）随 Toolkit 一起上线，mod.io 上的 mod 可在游戏内浏览安装 [11]。
- **BG3 Mod Manager（LaughingLeader）**：README 自称"唯一官方来源"[29]。Releases：1.0.12.0（4-15，".NET 8 Update"）→ 1.0.12.9（5-18，最新）；运行需 .NET 8.0 与 Microsoft Visual C++ Redistributable；改动加载顺序后必须 "Export to Game" 才会写入 modsettings.lsx [30]。发布年份在抓取页面未显示，第三方站点称为 2025-05 且"已验证兼容 Patch 7 与 Patch 8"[31]（三手，置信度中等）。
- **Patch 7 对 modsettings.lsx 的影响**：第三方站点称 Patch 7 改变了 modsettings.lsx 的格式，旧版 BG3MM 会卡在 "Loading profiles"，升级到 1.0.12.x 解决；BG3MM 与游戏内管理器写同一个文件，BG3MM 会把 mod.io 条目并入统一加载顺序 [31]。**位置没有变化**：bg3.wiki 给出的路径仍是 `%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\PlayerProfiles\Public\modsettings.lsx`，Mods 目录为 `%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\Mods`；手改后可设只读防止被覆盖 [25]。
- **Vortex**：Nexus 论坛有长达多页的「Patch 7 support for Vortex」讨论，反映 Patch 7 后 Vortex 扩展一度失效、打乱加载顺序 [32]；bg3.wiki 直接写明 Vortex "known to cause issues"、不推荐 [25]。2026 年 Vortex 的现状**未能确认**。
- macOS 路径：bg3.wiki 该页只给了 Windows 路径 [25]。`[背景知识—非本次检索]` Mac 原生版通常在 `~/Documents/Larian Studios/Baldur's Gate 3/` 下有同构的 `Mods/` 与 `PlayerProfiles/Public/modsettings.lsx`，未经本次核实。Nexus 上有社区的「Mod Manager for Mac」[40]。

### 2.5 Script Extender（BG3SE，Norbyte）

- **安装原理**：把 `DWrite.dll` 解压到 `Baldurs Gate 3\bin`（利用系统 DirectWrite 库的加载顺序注入）[33]；`[背景知识—非本次检索]` 这就是"DLL 劫持式注入"，因此 Wine/Proton 需要显式覆盖该 DLL。
- **功能**：为游戏加入 Lua/Osiris 脚本支持；`ScriptExtenderSettings.json` 可开启控制台（CreateConsole）、Osiris 日志、Osiris/Lua 调试器、重开成就等 [34]。
- **更新节奏**：SE 本体在游戏启动时自动在线更新，GitHub 上通常只在"更新器/启动器"变化时才发新 release [33][35]。v31（2026-04-17）起把 SE 内嵌进启动器作为在线更新失败时的回退；v32（2026-06-21）为最新 [33]。
- **Patch 8 兼容**：v31/v32 均标注 "Supports Patch 8"；Nexus 页面说明新版本只面向最新游戏版本（当前为 Patch 8），且不支持 Patch 5 之前的版本 [33][35]。截至 2026-09 的检索结果中没有出现 Patch 9，游戏当前版本仍应为 Patch 8 及其 hotfix（**未见反证，但未直接确认**）。
- **Linux / Steam Deck**：启动参数 `WINEDLLOVERRIDES="DWrite.dll=n,b" %command%`；社区 wiki 另给出加 `PROTON_NO_ESYNC=1` 的变体 [33][36]。Steam Deck 上有安装 BG3MM + SE 的指南 [37]，也有 SE mod 不工作的 issue [46]。
- **macOS 原生版**：Norbyte 的文档未提及 macOS [33][34]；Steam 讨论明确"Mac native doesn't support script extender"[42]。社区项目 `tdimino/bg3se-macos`：从零用 Ghidra 逆向 macOS 二进制重写，v0.42.0，自称约 94.8% 功能对齐，支持 Lua 5.4、Ext.Osiris/Stats/Entity/Events 等，通过 `insert_dylib` 打补丁 + Steam 启动参数包装脚本注入；要求 macOS 12+、推荐 Apple Silicon；自称在 macOS 15.6.1 与 26.2 上测试、验证过 MCM、Community Library 等 10 个热门 SE mod；Ext.UI/Noesis、Lua 调试器、虚拟纹理、输入注入明确不做 [38]。Larian 论坛有对应讨论帖 [39]。**这是非官方逆向工程项目，不能等同于 Norbyte SE，也不在 mod.io 管线内。**
- **mod.io 是否允许 SE 依赖**：见 2.1——搜索摘要表述为"绝对需要 SE 的 mod 不能上 mod.io"[6][8]，原文措辞未能核实。

### 2.6 文件格式速查

| 格式 | 说明 | 转换/工具 | 来源 |
|---|---|---|---|
| `.pak` | Larian 资源包（游戏 Data 目录与 mod 均用此格式） | LSLib Divine/ConverterApp、Multitool 解/打包 | [16][23] |
| `.lsf` | 二进制资源文件（关卡数据、对话、装备 stats、法术等大量以此存放） | `.lsf`→`.lsx`（Multitool "Decompress Files" 或 LSLib） | [16][23] |
| `.lsx` | XML 明文，可直接编辑；打包时可转回 `.lsf` | LSLib；Multitool 支持 `x.lsf.lsx` 命名自动回转 | [16][21][23] |
| `.lsb` / `.lsj` | 另两种资源序列化格式（二进制 / JSON） | LSLib 支持互转 | [16] |
| `.loca` ↔ `.xml` | 本地化；`.xml` 含 `ContentUID`（即句柄）与文本 | ExportTool 转换 | [23] |
| `.gr2` ↔ `.dae` / glTF | 模型与动画 | ExportTool（需 `granny2.dll`）、Blender 插件 | [15][23] |
| `.dds` / `.gts` | 纹理 / 虚拟纹理（`.gts`→`.dds` 走 ExportTool Virtual Textures 页） | GIMP/Paint.net/Photoshop | [23] |
| `.wem` → `.ogg` | 音频 | Multitool / Nexus 脚本 | [22][23] |

**原版数据包**（bg3.wiki 列表）[23]：`English.pak`（本地化字符串）、`Gustav.pak`（关卡数据、对话、装备 stats、法术）、`Shared.pak`（模型数据与材质/肤色/发色/眼色指派等）、`Models.pak`（.gr2）、`Textures.pak`（.dds）、`Materials.pak`、`VirtualTextures.pak`、`Voice.pak`；做数据 mod 建议至少解包 English、Gustav、Icons、Models、Shared、Textures [23]。自 Patch 4 起，每次大补丁会把 hotfix pak 并回主包；发布新 hotfix 后需给新 pak 建索引 [23]。
- `[背景知识—非本次检索]` `SharedDev` / `GustavDev` 是 `Shared.pak` / `Gustav.pak` 内部 `Public/` 下的子目录（正式版 progressions、class descriptions 等主要在这两个 Dev 目录）。**Patch 8 之后的新包名（如 `Patch8_*.pak` 等）：未能确认。**

**meta.lsx 关键字段**（bg3.wiki 完整模板）[24]：
- `ModuleInfo` 下：`Author`、`Description`、`Folder`（必须与 `Mods/<Folder>`、`Public/<Folder>` 目录名一致，"写错就会出问题"）、`MD5`（模板留空）、`Name`（管理器显示名）、`Tags`、`Type="Add-on"`、`UUID`（管理器区分 mod 的唯一键，除非有意覆盖他人 mod 否则必须唯一）、`Version64`（int64）；子节点 `PublishVersion/Version64`、`TargetModes/Target Object="Story"`；顶部 `<version major="4" minor="0" revision="9" build="331"/>`。
- `Dependencies` 下每个依赖是一个 `ModuleShortDesc`，属性为 `Folder`、`MD5`、`Name`、`PublishHandle`、`UUID`、`Version64` [26][28]；被依赖 mod 的 `Folder`/`UUID` 必须与其自身 meta 一致，`MD5` 留空 [27][28]。
- **Version64 计算**：文档只给出示例 `36028797018963968` 显示为 1.0.0.0，并建议用 BG3MM / Multitool / "Padme's mini tool" 生成 [24][27]。`[背景知识—非本次检索]` 位布局为 `(major<<55) | (minor<<47) | (revision<<31) | build`；本机 Python 核对：`1<<55 == 36028797018963968`（与文档示例一致），`1.2.3.4 → 36310278438125572`，反解得 `1 2 3 4`。此公式与文档示例自洽，但公式本身未在本次来源中出现。
- `PublishHandle`：`[背景知识—非本次检索]` 为 mod.io 发布后分配的句柄，本地/Nexus 分发的 mod 通常为 0。

### 2.7 来源间的分歧与可信度备注

- LSLib "最新版"：早期 v1.20.x 说明称 beta（稳定版 v1.19.5）[15][19]，而 releases 页面现以 v1.20.4 为最新 [15]——以 v1.20.4 为准，但生产使用前应看 GitHub 页面的 "Latest/Pre-release" 标记。
- Multitool：搜索索引仍有 GitHub 页面 [21]，实际抓取 404；Thunderstore 仍可下载 v0.10.6 [22]。
- BG3MM 年份：GitHub 抓取只给月日 [30]，"2025-05"来自非官方站点 [31]。
- mod.io 对 SE 的禁令措辞：只有搜索摘要，无原文 [6][8]。
- 官方 Toolkit 系统要求：三条来源数字一致 [1][2][14]，但均为摘要而非原页。

---

## 3. 对"自创职业 mod"项目的具体建议 / 决策点

1. **把 mod 定义为"纯数据 mod"，SE 作为可选层**：新职业/子职业主要改 ClassDescriptions / Progressions / ProgressionDescriptions / Lists / Stats / 本地化 / 图标，这类改动不需要 SE，可同时满足 mod.io（含主机审核）与 Nexus 两条发布线 [4][6][7][8]。若某个机制非 SE 不可，把它拆成独立的可选 pak。
2. **双轨工具链**：文本层（`.lsx`、stats `.txt`、`.xml` 本地化）在 Mac 编辑并纳入 git；官方 Toolkit（Windows）负责校验、图标/atlas、mod.io 发布；Divine（Windows 一定可用，Mac 待实测）负责命令行打包与解包 [15][16][17][18]。
3. **身份标识**：UUID 用 macOS 自带 `uuidgen`；本地化句柄与 Version64 用脚本生成（第 2.6 节公式，需与 BG3MM/Multitool 的输出比对一次）[24][27]。不要依赖 Multitool 的生成器作为唯一来源，因为其仓库现状不明 [21][22]。
4. **兼容性基线**：以 Patch 8 为目标版本；SE 相关验证只在 Windows 做，并以 SE v32 之后的自动更新版本为准 [33][35]。
5. **发布策略决策点**：
   - 需要主机/跨平台 → 只能走 Toolkit + mod.io，内容必须避开脚本改动与核心故事改动 [6][8]。
   - 只面向 PC → Nexus 发布 `.pak`，玩家用 BG3MM 或游戏内 "Third Party" 方式加载 [25][30][31]。
   - 是否可以不经 Toolkit 直接在 mod.io 网页上传 `.pak`：**未能确认**，需在 Windows 侧登录 mod.io 实际查看。
6. **解包策略**：Windows 侧用 Multitool 索引（省磁盘），只解 English/Gustav/Shared/Icons 等必要包 [23]；把解出的参考文件（不含版权资产）同步到 Mac 供对照。
7. **风险清单**：Multitool 仓库 404 [21]；Toolkit 160 GB 与 32 GB 内存门槛 [1][2]；LSLib 自 2025-01 无新版本（若后续补丁改格式可能需要等更新）[15]；mod.io 规则原文未读到 [6]。

---

## 4. 未解决问题与信息缺口

1. `docs.baldursgate3.game`、`larian.com`、`baldursgate3.game`、`support.gog.com` 全部 403，mod.io 域名被抓取工具拦截：**官方 Toolkit 文档、mod.io 规则原文、GOG 获取方式**均只拿到搜索摘要，需在浏览器人工核对。
2. Toolkit 在 Linux/Proton 的可用性（Steam 指南 [13] 未读到）。
3. Multitool 的真实现状（GitHub 404 的原因；是否有新家）。
4. Divine 在 macOS（Apple Silicon，.NET 8）上的实际运行情况——只有 Linux 旁证 [17] 与无人回复的 macOS issue [18]。
5. Patch 8 之后原版 pak 的新命名；`SharedDev`/`GustavDev` 的说法仅为背景知识。
6. Version64 位布局公式来自背景知识，仅用文档示例值做了自洽校验。
7. Vortex 在 2026 年是否已恢复对 Patch 7+/mod.io 的完整支持。
8. macOS 原生版的 Mods/modsettings.lsx 路径未获来源确认。
9. mod.io 是否要求必须通过 Toolkit 发布、审核周期与"Third Party"标签的确切规则。
10. bg3se-macos 的独立可信度（仅有项目自述 [38]，无第三方评测）。

---

## 5. 来源列表

| # | 标题 | URL | 类型 | 获取方式 | 访问日期 |
|---|---|---|---|---|---|
| 1 | Larian Support FAQ「Official Mod Support」 | https://larian.com/support/faqs/official-mod-support_113 | 一手 | 搜索摘要（抓取 403） | 2026-09-02 |
| 2 | Steam 商店「Baldur's Gate 3 Toolkit Data」 | https://store.steampowered.com/app/2956320/ | 一手 | 搜索摘要 | 2026-09-02 |
| 3 | Larian 官方文档「Getting Started: Installing the Toolkit」 | https://docs.baldursgate3.game/Getting_Started:_Installing_the_Toolkit | 一手 | 搜索摘要（抓取 403） | 2026-09-02 |
| 4 | Larian 官方文档主页（含 Adding Classes and Subclasses 条目） | https://docs.baldursgate3.game/index.php?title=Main_Page | 一手 | 搜索摘要（抓取 403） | 2026-09-02 |
| 5 | mod.io 指南「Installing the Toolkit」 | https://mod.io/g/baldursgate3/r/installing-the-toolkit | 一手 | 搜索摘要 | 2026-09-02 |
| 6 | mod.io「Modding Guidelines & FAQ」 | https://mod.io/g/baldursgate3/r/modding-guidelines | 一手 | 搜索摘要（抓取被拦截） | 2026-09-02 |
| 7 | mod.io 指南「Adding New Classes or Subclasses」 | https://mod.io/g/baldursgate3/r/adding-new-classes | 一手 | 抓取仅得标题 + 搜索摘要 | 2026-09-02 |
| 8 | Larian「Community Update #27: Official Modding Support」 | https://baldursgate3.game/news/community-update-27-official-modding-support_118 | 一手 | 搜索摘要（抓取 403） | 2026-09-02 |
| 9 | GOG Support Center「Baldur's Gate 3 Toolkit」 | https://support.gog.com/hc/en-us/articles/21377986182557-Baldur-s-Gate-3-Toolkit | 一手 | 仅标题（抓取 403） | 2026-09-02 |
| 10 | Larian Support FAQ「Steam Deck – Native Version」 | https://larian.com/support/faqs/steam-deck-native-version_121 | 一手 | 搜索摘要 | 2026-09-02 |
| 11 | GamingOnLinux「Baldur's Gate 3 patch 1.7 is out now with a mod manager, modding toolkit…」 | https://www.gamingonlinux.com/2024/09/baldurs-gate-3-patch-17-is-out-now-with-a-mod-manager-modding-toolkit-and-lots-more/ | 二手 | 搜索摘要 | 2026-09-02 |
| 12 | Steam 讨论「linux mod toolkit success? (patch7)」 | https://steamcommunity.com/app/1086940/discussions/0/4758704179140536338 | 二手（社区） | 搜索摘要 | 2026-09-02 |
| 13 | Steam 指南「Linux Guide for BG3, Script Extender, Modding Toolkit, WIP」 | https://steamcommunity.com/sharedfiles/filedetails/?id=3477750360 | 二手（社区） | 仅标题（抓取限流 ×2） | 2026-09-02 |
| 14 | Siliconera「How to Get the Baldur's Gate 3 Toolkit and Install Mods」 | https://www.siliconera.com/how-to-get-the-baldurs-gate-3-toolkit-and-install-mods/ | 三手 | 搜索摘要 | 2026-09-02 |
| 15 | Norbyte/lslib Releases | https://github.com/Norbyte/lslib/releases | 一手 | 抓取成功 | 2026-09-02 |
| 16 | Norbyte/lslib README | https://github.com/Norbyte/lslib | 一手 | 抓取成功 | 2026-09-02 |
| 17 | Norbyte/lslib Issue #220「Linux – Divine thinks the provided path is Relative…」 | https://github.com/Norbyte/lslib/issues/220 | 一手 | 搜索摘要 | 2026-09-02 |
| 18 | Norbyte/lslib Issue #236「Mac OS Support」 | https://github.com/Norbyte/lslib/issues/236 | 一手 | 抓取成功 | 2026-09-02 |
| 19 | Norbyte/lslib Issue #137「Move to .NET Core」/ Issue #277「there is no LSLib v1.20」 | https://github.com/Norbyte/lslib/issues/137 ；https://github.com/Norbyte/lslib/issues/277 | 一手 | 搜索摘要 | 2026-09-02 |
| 20 | Nexus 论坛「Workaround for Baldur's Gate 3 LSLib .NET Runtime issues」 | https://forums.nexusmods.com/topic/13476390-workaround-for-baldurs-gate-3-lslib-net-runtime-issues/ | 二手 | 搜索摘要 | 2026-09-02 |
| 21 | ShinyHobo/BG3-Modders-Multitool（GitHub 仓库、README、wiki） | https://github.com/ShinyHobo/BG3-Modders-Multitool | 一手 | 搜索摘要（抓取 404 ×3） | 2026-09-02 |
| 22 | Thunderstore「BG3 Modders Multitool by ShinyHobo」 | https://thunderstore.io/c/baldurs-gate-3/p/ShinyHobo/BG3_Modders_Multitool/ | 二手 | 抓取成功 | 2026-09-02 |
| 23 | bg3.wiki「Guide: Unpacking and Converting Files」 | https://bg3.wiki/wiki/Guide:Unpacking_and_Converting_Files | 二手 | 抓取成功 | 2026-09-02 |
| 24 | bg3.wiki「Modding: Creating meta.lsx」 | https://bg3.wiki/wiki/Modding:Creating_meta.lsx | 二手 | 抓取成功 | 2026-09-02 |
| 25 | bg3.wiki「Modding: Installing mods」 | https://bg3.wiki/wiki/Modding:Installing_mods | 二手 | 抓取成功 | 2026-09-02 |
| 26 | bg3.wiki「Modding: Dependencies」 | https://bg3.wiki/wiki/Modding:Dependencies | 二手 | 搜索摘要 | 2026-09-02 |
| 27 | wiki.bg3.community「Creating a meta.lsx file」 | https://wiki.bg3.community/Tutorials/General/creating_meta | 二手 | 搜索摘要 | 2026-09-02 |
| 28 | wiki.bg3.community「How to add mod dependencies and eradicate load order problems」 | https://wiki.bg3.community/Tutorials/General/Basic/adding-mod-dependencies | 二手 | 搜索摘要 | 2026-09-02 |
| 29 | LaughingLeader/BG3ModManager README | https://github.com/LaughingLeader/BG3ModManager | 一手 | 搜索摘要 | 2026-09-02 |
| 30 | LaughingLeader/BG3ModManager Releases | https://github.com/LaughingLeader/BG3ModManager/releases | 一手 | 抓取成功 | 2026-09-02 |
| 31 | bg3modmanager.net（非官方站点，多篇 2026 指南） | https://bg3modmanager.net/ | 三手 | 搜索摘要 | 2026-09-02 |
| 32 | Nexus 论坛「Baldur's Gate 3 Patch 7 support for Vortex」 | https://forums.nexusmods.com/topic/13498316-baldurs-gate-3-patch-7-support-for-vortex/ | 二手 | 搜索摘要 | 2026-09-02 |
| 33 | Norbyte/bg3se Releases（v32 2026-06-21、v31 2026-04-17） | https://github.com/Norbyte/bg3se/releases | 一手 | 抓取成功 | 2026-09-02 |
| 34 | Norbyte/bg3se README | https://github.com/Norbyte/bg3se | 一手 | 抓取成功（内容以配置项为主） | 2026-09-02 |
| 35 | Nexus「Baldur's Gate 3 Script Extender (BG3SE)」 | https://www.nexusmods.com/baldursgate3/mods/2172 | 一手（作者发布页） | 搜索摘要 | 2026-09-02 |
| 36 | wiki.bg3.community「Installing Script Extender」 | https://wiki.bg3.community/en/Tutorials/Mod-Use/How-to-install-Script-Extender | 二手 | 搜索摘要 | 2026-09-02 |
| 37 | Steam 指南「Installing BG3 Mod Manager + Script Extender on Steam Deck」 | https://steamcommunity.com/sharedfiles/filedetails/?id=3545134209 | 二手（社区） | 仅标题 | 2026-09-02 |
| 38 | tdimino/bg3se-macos README | https://github.com/tdimino/bg3se-macos | 一手（项目自述） | 抓取成功 | 2026-09-02 |
| 39 | Larian 论坛「Rebuilding Norbyte's BG3 Script Extender for MacOS」 | https://forums.larian.com/ubbthreads.php?ubb=showflat&Number=959421 | 二手 | 仅标题 | 2026-09-02 |
| 40 | Nexus「Mod Manager for Mac」 | https://www.nexusmods.com/baldursgate3/mods/5848 | 二手 | 搜索摘要 | 2026-09-02 |
| 41 | MacGamingDB「Baldur's Gate 3 – Mac Compatibility & Apple Silicon Performance」 | https://macgamingdb.app/games/1086940 | 三手 | 搜索摘要 | 2026-09-02 |
| 42 | Steam 讨论（Mac 原生版不支持 Script Extender） | https://steamcommunity.com/app/1086940/discussions/0/4204741842670561778 | 二手（社区） | 搜索摘要 | 2026-09-02 |
| 43 | Nexus「Full Tutorial. Make New Abilities for Your Subclass (of an Existing Class)」 | https://www.nexusmods.com/baldursgate3/mods/5999 | 二手 | 搜索摘要 | 2026-09-02 |
| 44 | Larian 论坛「Modding: Getting Started」 | https://forums.larian.com/ubbthreads.php?ubb=showflat&Number=943531 | 一手 | 搜索摘要 | 2026-09-02 |
| 45 | Steam 指南「Unpacking .PAK files of Baldur's Gate 3 and packing them back」 | https://steamcommunity.com/sharedfiles/filedetails/?id=2381865525 | 二手（社区） | 仅标题 | 2026-09-02 |
| 46 | Norbyte/bg3se Issue #206「Steam Deck – Script Extender Mods not working」 | https://github.com/Norbyte/bg3se/issues/206 | 一手 | 仅标题 | 2026-09-02 |

---

## 6. 审计

| 项目 | 数量 | 说明 |
|---|---|---|
| WebSearch 调用 | 18 | 全部成功返回结果 |
| WebFetch 调用 | 26 | 成功 12 次；失败 14 次（详见下） |
| 收到的来源（链接） | 约 150 条（含重复；去重约 120 条） | 来自 18 次搜索的结果列表 + 抓取页面 |
| 实际引用的来源 | 46 条 | 见第 5 节；其中"抓取成功"12 条、其余为搜索摘要或仅标题 |
| 失败明细 | 14 | `docs.baldursgate3.game` 403 ×2；mod.io 拦截/仅标题 ×3（连续 3 次失败后停止）；`larian.com` 403 ×1；`baldursgate3.game` 403 ×1；`support.gog.com` 403 ×1；Steam 指南限流 ×2；Multitool GitHub 404 ×3；`wiki.bg3.community/Toolkit` 仅返回标题 ×1 |
| 本地核验 | 2 | Version64 位运算与文档示例值一致；本机 macOS 26.6.2 / arm64 / 无 dotnet |
| 背景知识标注 | 若干 | Version64 位布局、SharedDev/GustavDev 目录含义、macOS 路径、PublishHandle 含义、DLL 劫持原理、Multitool/ConverterApp 为 Windows 桌面程序、Toolkit 项目落盘位置、双机同步实践 |

---

## 7. Mac + Windows 双机分工

> 协调方已确定：Mac 负责编辑/设计/脚本，Windows 负责官方 Toolkit、Script Extender 与游戏内验证。本节只回答"Windows 侧装什么、Mac 侧能独立做什么、两机怎么同步"。Parallels / CrossOver / 云 Windows 等 Mac 单机替代方案本次未研究，且鉴于 Toolkit 的 32 GB 内存 + 8 GB 显存 + 160 GB 磁盘要求 [1][2]，不建议作为主路线。

### 7.1 Windows 侧需要安装什么

| 组件 | 版本/来源 | 运行时要求 | 磁盘占用 | 备注 |
|---|---|---|---|---|
| Baldur's Gate 3（Steam/GOG，Patch 8） | 当前版本 | — | 游戏本体（本次未查数字） | SE 与 mod 验证的宿主 |
| **官方 Toolkit** | Steam "Tools" 免费应用 [1][2]；GOG 亦有支持文章 [9] | Windows 10 64-bit；32 GB RAM；8 GB+ 显存（2060 Super / RX 5700 XT 级）[1][2][14] | **约 160 GB** [1][2][14] | 需 Larian 账号 + mod.io 账号关联 [1][3][5]；负责校验、图标、mod.io 发布 |
| **LSLib / ExportTool（ConverterApp + Divine）** | v1.20.4（2025-01-24）[15] | .NET 8.0 Desktop Runtime [15] | 小体积（来源未给数字） | GR2 转换需 `granny2.dll`（可先装 1.15.13 取得）[23] |
| **BG3 Modder's Multitool** | v0.10.6（Thunderstore）[22]；GitHub 现状不明 [21] | 依赖 LSLib ≥ 1.15.9 [22] | 小体积 + 索引数据库（大小取决于索引范围） | 索引式解包，避免整包解压 [23] |
| **BG3 Mod Manager** | 1.0.12.9（5-18；第三方称 2025）[30][31] | .NET 8.0 + VC++ Redistributable [30] | 小体积 | 记得 "Export to Game" [30]；与游戏内管理器共写 modsettings.lsx [31] |
| **Script Extender** | 启动器 v32（2026-06-21）[33]，本体自动更新 [33][35] | 放入 `Baldurs Gate 3\bin` 的 `DWrite.dll` [33] | 极小 | 仅当 mod 用到 Lua/Osiris 扩展时需要；mod.io 线不可依赖 [6][8] |

`[背景知识—非本次检索]` Toolkit 的项目以松散文件形式落在 Toolkit 数据目录的 `Data/Mods/<Folder>/` 与 `Data/Public/<Folder>/` 下，这两个目录就是需要与 Mac 同步的"源码"。

### 7.2 Mac 侧能独立完成的环节

**确定可以（纯文本/脚本工作，不依赖任何 Windows 工具）**
- 编辑 `.lsx`（ClassDescriptions / Progressions / ProgressionDescriptions / Lists 等）、stats `.txt`、本地化 `.xml`、`meta.lsx`——都是明文格式 [16][23][24]。
- 生成 UUID（`uuidgen`）、本地化句柄、Version64（第 2.6 节公式，已用 Python 核对示例值）。
- 用 git 管理源码、写校验脚本（如 XML 合法性、UUID 唯一性、句柄引用完整性）。
- 阅读从 Windows 同步过来的原版参考文件（`.lsx` / `.txt` / 本地化 `.xml`）。

**理论可行、需实测（Divine CLI on .NET 8）**
- 正向证据：LSLib 已迁到 .NET 8（跨平台运行时）[15][19]；Linux 用户能用 `dotnet Divine.dll -a create-package -g bg3 -s <dir>` 启动 Divine [17]。
- 反向证据：Linux 下出现过绝对路径被当作相对路径的异常 [17]；macOS issue 无人回复、未见成功案例 [18]；GR2 相关操作依赖 Windows 原生 `granny2.dll` [23]；本机目前没有 dotnet。
- 建议的最小实测清单（在 Mac 上，约半小时）：
  1. 安装 .NET 8 Runtime（Apple Silicon 版）；
  2. 从 LSLib releases 下载 ExportTool 压缩包 [15]，解压后运行 `dotnet Divine.dll --help`；
  3. 依次验证 `-a extract-package`（解一个小 pak）、`-a convert-resource`（`.lsf`↔`.lsx`）、`-a convert-loca`（`.loca`↔`.xml`）、`-a create-package`（打包自己的 mod）；
  4. 若遇到 [17] 所述的路径异常，改用相对路径或在 Windows 侧打包。
  5. 记录结果——通过则 Mac 可独立产出可测试的 `.pak`；不通过则 Mac 只负责源码，打包全部交给 Windows。
  （`[背景知识—非本次检索]` 以上 `-a` 参数名来自 Divine 的常规用法，具体以 `--help` 输出为准。）

**Mac 侧做不了或不该做**
- 官方 Toolkit（仅 Windows）[1][14]；ConverterApp GUI 与 Multitool（Windows 桌面程序）[18][21]；GR2 模型转换 [23]。
- Norbyte SE 验证：macOS 原生版没有官方 SE [42]；社区 `bg3se-macos` 可作为"额外参考"，但不能替代 Windows 上的正式验证 [38]。
- mod.io 发布（走 Toolkit）[1][5][8]。

### 7.3 两机之间同步源码 / PAK 的做法

以下为通用工程实践 `[背景知识—非本次检索]`，本次未检索到 BG3 社区专门讨论：
- **git 仓库为主**：仓库根放 mod 的 `Mods/<Folder>/` 与 `Public/<Folder>/`（明文 `.lsx`/`.txt`/`.xml`），Windows 侧把 Toolkit 项目目录中的这两个文件夹做成仓库工作副本（或用目录链接指向仓库）。二进制产物（`.pak`、`.lsf`、`.dds`、`.gr2`）不入库或走 Git LFS，`.pak` 视为构建产物由 CI/脚本生成。
- **`.gitattributes` 固定行尾**：Larian 文件多为 CRLF/LF 混用，统一 `text eol=lf` 或按文件类型声明，避免两机来回改行尾造成大量假 diff；`.lsf/.pak/.dds/.gr2` 标记为 `binary`。
- **共享目录作为"投递箱"**：局域网 SMB / Syncthing / iCloud Drive 同步一个 `build/` 目录，Mac 产出的 `.pak`（若 7.2 实测通过）或 Windows 产出的 `.pak` 放在这里，供另一台机器测试；不要把 Toolkit 的 160 GB 数据目录整体放进同步盘。
- **路径注意事项**：游戏目录名含撇号（`Baldur's Gate 3`），脚本里一律加引号；macOS 默认文件系统不区分大小写、Windows 亦然，但 Linux/CI 区分——`Folder`、文件名的大小写在仓库里保持与 `meta.lsx` 完全一致 [24]。
- **参考数据单向流动**：原版解包出的 `.lsx`/`.txt`（版权资产）只放在 Windows 或本地未入库目录，需要对照时按文件复制到 Mac，不进公开仓库。

### 7.4 分工后的最小闭环

1. Mac：改 `.lsx`/`.txt`/`.xml` → 脚本校验 → git push。
2. Windows：git pull → Toolkit 打开项目校验（或 Divine `create-package`）→ BG3MM/游戏内管理器加载 → 游戏内验证（需要 SE 的部分在此验证）。
3. 发布：mod.io 线用 Toolkit 发布 [1][5][8]；Nexus 线直接上传 `.pak`。
4. 若 7.2 的 Divine 实测通过，则第 2 步中的"打包"可以提前到 Mac 完成，Windows 只做验证与发布。
