# 05 · 研发环境与基建：Mac 编辑 + Windows 验证 的双机闭环

> 来源：`research/A-tooling-pipeline.md`（A）§7、`research/E-scripting-infra.md`（E）§2.4–2.7、`research/G-official-docs-browser.md`（G）。前提：你有一台 Mac（本机：Apple M4、16 GB、macOS 26，未装 dotnet/Steam）和一台 Windows 电脑。

## 1. 分工总览

```
┌──────────────── Mac（设计 / 编辑 / 脚本）────────────────┐      ┌──────────── Windows（工具 / 验证 / 发布）────────────┐
│ VS Code：.lsx / stats .txt / .xml 本地化 / Lua / 设计文档  │      │ Baldur's Gate 3（Patch 8）+ BG3 Toolkit Data DLC     │
│ Python 脚本：UUID / handle / Version64 / check_mod.py     │ git  │ 官方 Toolkit：建表校验、图标转换、Publish Local/mod.io │
│ 图标源图 PNG（300×300 / 64 / 144 / 380）                    │ ───▶ │ LSLib（Divine / ConverterApp）、Multitool、BG3MM       │
│ git 仓库 = 唯一事实源                                       │ ◀─── │ Script Extender（控制台 / 调试器）、游戏内验证          │
└──────────────────────────────────────────────────────────┘ 反馈  └──────────────────────────────────────────────────────┘
```

| 环节 | 机器 | 依据 |
|---|---|---|
| 编辑 `.lsx` / `.txt` / `.xml` / Lua / `meta.lsx`、写设计文档、图标源图 | Mac | 纯文本/图片；VS Code 扩展多为语法/片段类 E[42][43][44] |
| 生成 UUID / handle / Version64、结构校验 | Mac | 本仓库 `scripts/` |
| 打包 `.pak`、`xml→loca`、`png→dds` | **Windows（默认）** | Divine 是 .NET 8 但工程引用 C++/CLI 原生库，Mac 未验证 E[本机核查] G[G10][G11] |
| 官方 Toolkit（校验、图标 metadata、mod.io 发布） | Windows | 仅 Windows A[1][14] |
| 部署到游戏、SE 控制台/日志、VS Code Lua 调试器、游戏内验证 | Windows | 调试适配器是 `.exe` 且需连本机游戏 E[3] |
| 发布 Nexus（后续版本自动化） | 任一机器 / CI | Nexus 官方 upload-action E[18] |

## 2. Windows 侧安装清单 A[7.1] G[G2]

| 组件 | 版本 / 来源 | 要求 | 备注 |
|---|---|---|---|
| Baldur's Gate 3（Steam 或 GOG，Patch 8） | — | 游戏本体 | mod 验证宿主 |
| **官方 Toolkit** | Steam "Tools" 免费 / GOG 商店 | Windows 10 64-bit；**32 GB 内存、8 GB+ 显存、约 160 GB 磁盘**（Steam 商店页数字）；需在 BG3 属性 → DLC 启用 **BG3 Toolkit Data** | 需 Larian 账号 + mod.io 账号绑定；首次启动填 Data 路径（路径不能含 `|`） G[G3] |
| **LSLib / ExportTool** | v1.20.4（2026-01-24，GitHub Releases API，见 research/H[9]；A 报告的 2025-01-24 疑为误读）| .NET 8.0 Desktop Runtime | GR2 需先装 1.15.13 取得 `granny2.dll`（只有做模型才需要）A[15][23] |
| **BG3 Modder's Multitool** | v0.10.6（GitHub/GitLab/Thunderstore） | LSLib ≥ 1.15.9 | 索引式解包（省磁盘）、搜索、UUID/handle 生成 A[21][22] |
| **BG3 Mod Manager** | 1.0.12.9 | .NET 8 + VC++ Redistributable | 记得 "Export to Game"；与游戏内管理器二选一 A[30] |
| **Script Extender** | 启动器 v32（2026-06-21） | `DWrite.dll` 放 `Baldurs Gate 3\bin` | 仅 SE 增强模块需要；`bin\ScriptExtenderSettings.json` 开 `CreateConsole` / `EnableLuaDebugger` E[1][34] |
| VS Code + Lua Debugger 扩展 | bg3se-updates 仓库的 DebugAdapter | — | 先启动游戏再 F5 E[3] |

**先核对 Windows 机的硬件是否达到 Toolkit 门槛（尤其 32 GB 内存与 160 GB 磁盘）**；达不到时 Toolkit 可能无法运行，但 LSLib / Multitool / BG3MM / SE 这条"纯文本 + 打包"路线仍然可用，只是失去 mod.io 发布与图标转换器（图标可用 GIMP/Paint.net/NVIDIA Texture Tools 手动出 DDS，但类图标 metadata 需实测 B[4]）。

## 3. Mac 侧安装清单
- 已有：git 2.50、Python 3.14、Node 24、Homebrew。
- 装：VS Code + `bg3-mod-helper`（UUID/handle、实例查找、模板）+ `bg3txt-formatter`（stats 高亮）+ `BG3-SE-Snippets` / `vscode-bg3-modding`（片段）+ Lua 语言服务器（LuaLS）配合 SE 仓库的 `ExtIdeHelpers.lua` 做 `Ext.*` 补全 E[2][41]-[44]。
- 可选实验（半小时）：`brew install dotnet@8` 后运行 `dotnet Divine.dll --help` 并依次试 `extract-package` / `convert-resource` / `convert-loca` / `create-package`；成功则 Mac 也能出 pak，失败就维持"Windows 打包"。风险点：`LSLib.csproj` 无条件引用 C++/CLI 的 `LSLibNative`（仅 GR2 解压用），运行时可能不触发但工程层面不支持 macOS E[2.7.2]。
- 参考数据：从 Windows 解包出的原版 `.lsx/.txt/.xml`（版权资产）按需复制到 Mac 的未入库目录（`reference/`，已在 `.gitignore`），不进公开仓库。

## 4. 仓库布局（本仓库已按此初始化）E[2.4.1] G[G18]

```
Baldur's-Gate-Mod/
├── README.md                 # 入口与文档地图
├── docs/                     # 本调研的合成文档（01–07）
├── research/                 # 原始研究报告（带来源与审计）
├── templates/                # 设计单 / 测试矩阵 / bug 模板 / mod 骨架
├── scripts/                  # gen_ids.py / version64.py / check_mod.py / build.ps1（示意）
├── mods/<ModName>/           # 每个 mod 一个目录（后续创建）
│   └── Source/               # Divine create-package 的源根
│       ├── Mods/<ModName>/   # meta.lsx、Localization/、GUI/、ScriptExtender/
│       └── Public/<ModName>/ # ClassDescriptions/、Progressions/、Lists/、Stats/、GUI/、Assets/
├── assets-src/               # 图标源图 PNG / PSD、页面素材（可用 Git LFS）
├── build/                    # .pak 产物（.gitignore）
└── reference/                # 解包的原版数据（.gitignore，版权资产不入库）
```

- `.gitattributes`：文本类固定行尾（`*.lsx *.txt *.xml *.lua text eol=lf`），`*.pak *.lsf *.dds *.gr2 *.loca binary`；大图走 Git LFS（社区无专门指引，属通用实践）A[7.3]。
- `.pak` 是构建产物，不入库；发布物走 GitHub Releases / Nexus。
- 路径注意：游戏目录含撇号（`Baldur's Gate 3`），脚本一律加引号；macOS/Windows 默认不区分大小写但 Linux/CI 区分，`Folder` 与文件名大小写在仓库里保持与 `meta.lsx` 一致。

## 5. 身份标识与版本

| 项 | 做法 |
|---|---|
| mod `UUID` | v4 UUID，一经发布终身不变（`scripts/gen_ids.py`） |
| 本地化 handle | 官方允许任意无空格字母数字串；本仓库脚本生成社区惯例格式 `h` + 无连字符、`g` 分段的 UUID |
| `Version64` | `(Major<<55) | (Minor<<47) | (Revision<<31) | Build`（从 LSLib `Resource.cs` 核实；`1.0.0.0 = 36028797018963968`）E[2.4.3]；`scripts/version64.py` 可互转 |
| 版本语义 | 官方建议：Major = 大改/新内容，Minor = 改进修复，Revision = 微调，Build 自动递增；Build 用于判断"可更新"与联机版本匹配 G[G6] |
| git tag | `vX.Y.Z` ↔ `Version64`，发布时同步写入 `meta.lsx` 与 mod.io/Nexus 版本字段 |

## 6. 打包与部署（Windows 侧，示意脚本 `scripts/build.ps1`）E[2.4.5]

Divine CLI 参数已从源码核实（`-g bg3`、`-a create-package|extract-package|convert-resource|convert-resources|convert-loca`、`-s/-d`、`-c lz4hc` 默认）：

```powershell
# 1) 本地化 xml -> loca（若不用 Multitool 的 *.loca.xml 自动转换）
Divine.exe -g bg3 -a convert-loca -s ".\Source\Mods\MyClass\Localization\English\MyClass.xml" -d ".\Source\Mods\MyClass\Localization\English\MyClass.loca"
# 2) 打包
Divine.exe -g bg3 -a create-package -s ".\Source" -d ".\build\MyClass.pak"
# 3) 部署到游戏（路径为社区惯例，请在 Windows 核对）
Copy-Item ".\build\MyClass.pak" "$env:LOCALAPPDATA\Larian Studios\Baldur's Gate 3\Mods\"
# 参考：只解包原版进阶表用于对照
Divine.exe -g bg3 -a extract-package -s "<Game>\Data\Shared.pak" -d ".\reference\Shared" -x "*/Progressions/*"
```
以上命令拼接自已核实的参数，**尚未实际运行**；首次在 Windows 上跑通后把真实输出记入 `docs/07`。替代：Toolkit 的 **Publish Local** 无需认证即可出 `.pak` G[G5]；Multitool 一键打包并自动转换 `x.lsf.lsx` / `x.loca.xml` A[21]。

## 7. 校验（Mac 侧，`scripts/check_mod.py`）
检查项：所有 `.lsx/.xml` 可解析；`meta.lsx` 的 `Folder` 与 `Mods/<Folder>`、`Public/<Folder>` 一致；`Name` 不含 `-b`；UUID 全仓唯一；每个 ClassDescription 的 `ProgressionTableUUID` 有对应 Level 1 的 Progression 节点；`SubClasses/SubClass.Object` 指向存在的 ClassDescription；lsx/txt 中引用的 handle 在 Localization xml 中存在；`Version64` 可解析。它是"能否被引擎解析"之前的静态兜底，不能替代 Toolkit/游戏内验证。

## 8. 测试与调试 G[G4][G8] E[2.3.4][2.6]
- **Toolkit 内快速回路**：加载 `Basic_Level_A` → Game Mode → 悬停头像 `Ctrl+Shift+L` 升级 → Add Class；`Ctrl+Shift+F11` 调试台：`addDebugSpell <Type_Name>`、`spawnItem <Template>`、`reloadLoca`。
- **游戏内验证**：BG3MM/游戏内管理器启用 → 新档创建角色 → 逐级升到 12 → 多职业 → Withers 重置 → 读旧档 → 联机（host + client）。
- **SE 控制台**（若有 SE 模块）：`bin\ScriptExtenderSettings.json` `{"CreateConsole": true}`；进入后 Enter 切输入模式，`server`/`client` 切换，`reset` 重建 Lua VM，`!cmd` 自定义命令；官方 Osiris API 有 `SetLevel`、`AddExplorationExperience`、`RequestRespec`、`AddPassive`、`AddSpell` 等调用，控制台里以 `Osi.<Name>()` 调用（用法为背景知识，签名以官方页为准）G[G16]。
- **测试存档集**：营地 + Withers 可用 + 1/3/5/12 级各一份，随仓库 Releases 分发给测试者（存档含 mod 信息，注意不要带私人内容）。
- 日志：SE 可把控制台/脚本输出写日志、开 Osiris 日志；崩溃日志与默认路径本次未核实 E[1]。

## 9. CI 与发布自动化 E[2.4.6][2.4.7]
- **现在不做 CI**；等流程稳定后用 `windows-latest` runner：下载 LSLib release → `Divine.exe create-package` → 打 zip → `Nexus-Mods/upload-action`（需 API key、file id；Upload API 仍是 beta，只支持更新既有 mod，首次建页手动）。
- **mod.io 只能经 Toolkit 发布**（Authenticate → Publish → 自动扫描 → 编辑资料 → Go live）；网页直传 `.pak` 是否可行未确认 G[G5] A[4.9]。
- 页面描述与 changelog 放在仓库里版本化（Volition Cabinet 的 `nexus_description.bb` 做法）C[35]。

## 10. 最小闭环（每次迭代）
1. Mac：改数据 → `python3 scripts/check_mod.py mods/<Mod>/Source` → commit → push。
2. Windows：pull → `build.ps1`（或 Toolkit Publish Local）→ 部署 → 游戏内按测试矩阵验证 → 把控制台/日志/截图贴回 issue 或直接 commit 修正。
3. 发布：打 tag → 更新 `Version64` → Toolkit 发 mod.io + Nexus 上传 → 页面 changelog。
