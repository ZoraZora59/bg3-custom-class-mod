# H · BG3 .loca 文件格式与转换 / 翻译工具调研

调研日期：2026-09-02 · 调研者：子代理 H · 目的：为「给别人的 BG3 mod 做中文汉化」确定 .loca 的读写方式与可用工具链（Mac 编辑 + Windows 验证）。
所有事实均带来源编号 `[n]`（见第 4 节）；非本次检索得到的内容一律标 `[背景知识—非本次检索]`。

## 1. 结论摘要

1. **.loca 是极简二进制格式，可用 Python `struct` 在 50 行内实现读写**：12 字节文件头（`"LOCA"` 魔数、条目数、文本区偏移）+ 每条 70 字节的条目表（64 字节 NUL 填充的 UTF-8 handle、uint16 version、uint32 长度）+ 连续的 UTF-8 文本区（每条以 `\0` 结尾，长度字段含该 `\0`）。全部小端、无对齐、无压缩、无校验。[1][2]
2. **LSLib 的 XML 侧格式**：`<contentList><content contentuid="h…" version="1">文本</content></contentList>`，用 .NET `XmlWriter`（Indent=true，缩进为 Tab）写出，正文经 `WriteString` 输出，因此 `<` `>` `&` 会被转义成 `&lt; &gt; &amp;`；读取端只认 `contentList`/`content` 两种元素，遇到其它元素直接抛异常，`version` 缺省为 1。**正文里的 `<LSTag>`/`<br>` 必须以转义实体存在**，否则 LSLib 读取会报 "Unknown element"。[1]
3. **Divine CLI 的 loca 转换只有单文件模式**：`Divine -g bg3 -a convert-loca -s in.loca -d out.xml`（反向同理），输入/输出格式**仅由扩展名**决定（`.loca`↔`.xml`），`--input-format/--output-format` 不接受 `loca`/`xml`，`convert-resources` 批量动作只处理 lsx/lsb/lsf/lsj；`-g`、`-s`、`-a` 三者必填。[3][4][5][6]
4. **Divine 在 macOS/Linux 上开箱即用的可能性低**：项目虽已是 `net8.0`，但 `TryToValidatePath` 用 `Uri.IsFile` 校验路径，在 POSIX 绝对路径上会抛 `InvalidOperationException`（issue #220，2024-03 开至今未关；社区补丁：改成 `UriKind.Absolute` 重新编译即可）；LSLib 还引用 C++ 的 LSLibNative 与 Windows 专用的 gplex/gppg 预编译步骤（issue #196、PR #107、PR #301 均未合并）。不过 **loca 代码路径是纯托管代码**（只用 `Marshal`+`System.Xml`），用 pythonnet 直接调 `LSLib.dll` 的 `LocaUtils` 在理论上可绕过 Divine 的路径校验（LaughingLeader 的 `convert_loca.py` 就是这么做的，但只在 Windows 验证过）。[4][7][10][11][12]
5. **可在 macOS 原生运行的替代实现已经出现，但都是 2026 年的小众新项目（0–2 star）**：Rust 的 `maclarian`（MacPak，`cargo install maclarian`，PAK 读写 + LSF↔LSX + LOCA↔XML）、`bg3rustpaklib`（PAK v15/16/18 读写 + LOCA 工具，仅库）、Python 的 `bg3-forge`（PAK v15/16/18 解包/打包 + .loca 解析，MIT）。PyPI 上**没有**任何 lslib/bg3/loca 相关包。[27][28][29][52]
6. **BG3 Modder's Multitool 的 GitHub 仓库与作者账号已于 2026 年中消失（API 404）**，项目迁到 GitLab（2026-06-06 建库，README 里的 wiki 链接全部指向 web.archive.org 快照），最新版 0.13.4（2025-06-01），"source available, not open source"，Windows .NET 应用（Linux 用 Bottles）。自动转换约定：README 明示 `x.lsf.lsx→x.lsf`、`x.lsb.lsx→x.lsb`；`x.loca.xml→x.loca` 由 bg3.wiki 与社区 wiki 证实（"repacking 时自动转回 .loca"）。[14][17][18][19][20]
7. **LarinStudios Localization Helper（Nexus 3136，即 3DM 圈子里的 "BG3 LocaHelper"）的 GitHub 源码已在 2024-01-08 被 DMCA 下架**——投诉人正是 Multitool 作者，称其 FileHelper.cs 等文件被抄袭。该工具是 Windows .NET 桌面程序（需 .NET 6/7 或 Framework 4.8.1），3DM 有 Juij 编译的 v3.3.1 汉化版（2023-11-06，帖子正文现已被论坛屏蔽）与两篇汉化教程（要求 Win10 22H2+、.NET 4.8.1）。**不适合 Mac 工作流，且已无源码维护。**[21][22][23][24][25]
8. **翻译辅助工具现状**：Nexus 上的 Python 类工具（script translator 23203、XML TRANSLATOR 19280、Mod Auto Translator 15778）走 Google/DeepL 机翻；Gemini 驱动的 BG3 Mod Translator（23274，GitHub anboyu-alt/BG3-Auto-Korean，v7 起自研 pak/loca 解析，支持简繁中文，Windows exe）；Electron 的 Icosa（15976，自研 LSPK v18，仅 Windows 包）。**最贴近本项目的是两个 2026 年的中文 AI 汉化项目**：`YiYan129600/bg3-mod-ai-translator-zh`（Python、MIT、跨平台、严格 XML/LOCA 校验、术语表/翻译记忆、只生成本地化 pak，但打包仍调外部 LSLib/Divine）和 `BenChao1998/BG3ModTranslation`（Rust+Tauri+CLI `bg3mt`，自研 LSPK v18 解包/打包，支持 DeepSeek/Qwen/GLM/Kimi 等国内模型）。[35][36][37][38][46][47][48]
9. **VS Code 扩展 BG3 Mod Helper**（ghostboats）最新 2.2.63（2024-11-04，Marketplace），能生成 handle、把条目写进 `.loca.xml`、做 LSX/XML/LOCA 转换与打包，但**依赖设置中指定的 `LSLib.dll` 目录**，实质绑定 Windows/.NET；Nexus 23204 "Update Helper Edition" 是另一个 mod 更新器，与之无关。[44][55]
10. 中文本地化目录名：简体中文放 `Localization/Chinese/`，繁体为 `Localization/ChineseTraditional/`（游戏本体 `Data/Localization/ChineseTraditional/ChineseTraditional.pak`）；社区惯例是汉化 mod 文件夹/pak 名加 `CHS` 后缀并换新 UUID。（搜索摘要 + 3DM 教程，未从官方文档核实）[25][53]

## 2. 证据细节

### 2.1 .loca 二进制格式（一手：`LSLib/LS/Localization.cs`，master@2026-03-31）[1][2]

LSLib 里没有 `LocaFormat.cs`（404），实际文件是 `LSLib/LS/Localization.cs`（315 行），结构体用 `[StructLayout(Sequential, Pack=1)]` 并通过 `BinUtils.ReadStruct/WriteStruct`（`Marshal.PtrToStructure/StructureToPtr`）原样读写，因此布局就是内存布局、小端（x64）。

**文件头 `LocaHeader`（12 字节）**

| 偏移 | 字段 | 类型 | 说明 |
|---|---|---|---|
| 0 | Signature | uint32 | 常量 `0x41434F4C`，小端字节序即 ASCII `LOCA`；不符则抛 "Incorrect signature" |
| 4 | NumEntries | uint32 | 条目数 N |
| 8 | TextsOffset | uint32 | 文本区起始偏移。写入时 = `12 + 70*N`；读取时若当前位置≠此值会 `seek`，所以 Python 读取应以该字段为准 |

**条目表 `LocaEntry`（每条 70 字节，紧跟文件头，共 N 条）**

| 偏移 | 字段 | 类型 | 说明 |
|---|---|---|---|
| 0 | Key | byte[64] | handle 的 UTF-8 字节，余下 `\0` 填充；读取时截到第一个 0 字节；写入用 `Array.Copy`，**超过 64 字节直接抛异常**（BG3 handle `h`+36 字符=37 字节，安全） |
| 64 | Version | uint16 | 对应 XML `version` 属性 |
| 66 | Length | uint32 | 文本 UTF-8 字节数 **+1**（含结尾 `\0`） |

**文本区**：按条目顺序连续存放，每条 = UTF-8 字节 + `0x00`；读取端 `ReadBytes(Length-1)` 后再 `ReadByte()` 跳过 NUL。没有对齐、填充、压缩或校验；文本不做任何转义（loca 里是原始 `<LSTag …>`，XML 里才是 `&lt;LSTag …&gt;`）。

Python 读写伪代码（自行实现时照此即可）：

```python
# read
sig, n, texts_off = struct.unpack('<III', f.read(12)); assert sig == 0x41434F4C
entries = [struct.unpack('<64sHI', f.read(70)) for _ in range(n)]
f.seek(texts_off)
for key, ver, length in entries:
    text = f.read(length - 1).decode('utf-8'); f.read(1)      # skip NUL
    key = key.split(b'\0', 1)[0].decode('utf-8')
# write
body = [t.encode('utf-8') for t in texts]
hdr = struct.pack('<III', 0x41434F4C, len(body), 12 + 70 * len(body))
tbl = b''.join(struct.pack('<64sHI', k.encode('utf-8').ljust(64, b'\0'), v, len(b) + 1) ...)
out = hdr + tbl + b''.join(b + b'\0' for b in body)
```

**XML 侧（同一文件内的 `LocaXmlWriter` / `LocaXmlReader`）**

- 写：`XmlWriter.Create(stream, {Indent=true, IndentChars="\t"})` → `<contentList>` 根元素，每条 `WriteStartElement("content")` + `WriteAttributeString("contentuid", key)` + `WriteAttributeString("version", ver)` + `WriteString(text)`。`version` 总是写出。没有用 `XmlSerializer`，无任何 `[XmlRoot]` 注解。[1]
  - `WriteString` 会把正文中的 `<` `>` `&` 转义为 `&lt; &gt; &amp;`，属性值另转义 `"`；`XmlWriter.Create(Stream)` 默认输出 `<?xml version="1.0" encoding="utf-8"?>` 声明并带 UTF-8 BOM，文本中的换行按 `NewLineHandling.Replace` 规范化为平台换行 `[背景知识—非本次检索：.NET XmlWriter 默认行为]`。Python 用 `xml.etree.ElementTree` 写出时同样会转义这三个字符，语义兼容；解析时请用二进制模式打开以容忍 BOM。
- 读：`XmlReader.Create(stream)`（默认设置），遍历所有 Element 节点：`contentList` 跳过；`content` 取 `reader["contentuid"]`（缺失则 key 为 null，之后写 loca 会崩）、`reader["version"]`（缺失→1，否则 `UInt16.Parse`）、`reader.ReadString()` 取正文（实体自动解码）；**任何其它元素名都抛 `InvalidFormatException("Unknown element encountered")`**。推论：`<content>` 内不能有真实子元素，富文本标签必须是转义实体。[1]
- `LocaUtils.ExtensionToFileFormat`：`.loca`→Loca、`.xml`→Xml、其它扩展名抛 "Unrecognized file extension"（`x.loca.xml` 的扩展名是 `.xml`，正常）。公开 API：`LocaUtils.Load(path[, format])`、`Load(stream, format)`、`Save(resource, path[, format])`；数据类 `LocaResource{ List<LocalizedText> Entries }`、`LocalizedText{ Key, Version, Text }`；枚举 `LocaFormat{ Loca, Xml }`。[1]

### 2.2 Divine CLI（一手：`Divine/CLI/*.cs`、`Divine.csproj`）[3][4][5][6][7]

- 解析库：CommandLineArgumentsParser 3.0.23，`IgnoreCase=true`，空参数时打印用法；致命错误退出码 1。`Divine.csproj` 目标 `net8.0`、`OutputType Exe`、`PlatformTarget x64`，无 Windows 专属开关。[7]
- 动作 `-a`（必填，默认值 `extract-package` 仅作提示）：`create-package; list-package; extract-single-file; extract-package; extract-packages; convert-model; convert-models; convert-resource; convert-resources; convert-loca; build-vt`。[3]

| 选项 | 必填 | 取值 / 说明 |
|---|---|---|
| `-g/--game` | 是（所有动作，包括 convert-loca） | `dos; dosee; dos2; dos2de; bg3`；`create-package` 时决定 pak 版本（BG3 → V18，`PackageFormat.CurrentVersion=V18`）[3][4][8] |
| `-s/--source` | 是 | 文件或目录 |
| `-d/--destination` | 除 `list-package`/`build-vt` 外都会校验 | 文件或目录 |
| `-i/-o` `--input-format/--output-format` | 仅 batch 动作（`extract-packages`、`convert-models`、`convert-resources`）必填 | 声明的枚举是 `dae;glb;gltf;gr2;lsv;pak;lsj;lsx;lsb;lsf`，但 `GetResourceFormatByString` 只接受 `lsb/lsf/lsj/lsx`，**没有 loca/xml** |
| `-c/--compression-method` | 否 | `zlib; zlibfast; lz4; lz4hc(默认); none` |
| `-x/--expression` / `--use-regex` | 否 | extract/list 的 glob（默认 `*`）或正则 |
| `-l/--loglevel` | 否 | `off…all`，默认 info；另有 `--legacy-guids`、`--use-package-name`、`--package-priority`、`-e/--gr2-options`、`--conform-path`、`--vt-root` |

- `convert-loca`：`CommandLineDataProcessor.ConvertLoca()` 只做 `LocaUtils.Load(source)` → `LocaUtils.Save(loca, destination)`，格式完全由两端扩展名决定。用法：
  `Divine -g bg3 -a convert-loca -s "English.loca" -d "English.xml"`；反向把 `-s`/`-d` 对调即可。[5]
- **没有目录批量 loca 模式**：`convert-loca` 不在 `batchActions` 里；`convert-resources` 走 `ResourceUtils.ConvertResources`，递归 `Directory.GetFiles/GetDirectories`，按 `IsA(ext)` 过滤（lsx/lsb/lsf|lsbc|lsfx/lsj），输出保持相对路径并 `ChangeExtension`。批量 loca 要自己在 shell/Python 里循环。[4][6]
- 其它常用组合（供 Windows 验证机使用）：`-a extract-package -s Mod.pak -d outdir`、`-a create-package -s moddir -d Mod.pak -c lz4hc`、`-a convert-resources -i lsf -o lsx -s in -d out`。bg3.wiki 的示例与此一致。[15]
- **路径校验缺陷（跨平台关键）**：`TryToValidatePath` 先 `Uri.TryCreate(path, RelativeOrAbsolute)`，再判断 `!Path.IsPathRooted(path) || !uri.IsFile`。Linux 上 POSIX 绝对路径被解析成相对 Uri，`uri.IsFile` 直接抛 `InvalidOperationException`（未被 catch）；相对路径则触发 E2 致命错误。issue #220（2024-03-02，open）复现命令为 `dotnet Divine.dll -a create-package -g bg3 -s /abs/path`；2025-09-06 有人回复把 `RelativeOrAbsolute` 改为 `UriKind.Absolute` 后重新编译即可在 Linux 正常运行。master 代码仍未改。[4][10]
- 跨平台现状：PR #107 "Add Linux support"（2023-07）open；issue #196 "能否在 macOS 编译"（2023-11）open，卡在 gplex/gppg 只有 Windows exe；PR #301（2026-05-24）"升级 .NET 10 并跨平台化" 仍是草稿。`LSLib.csproj` 引用 `LSLibNative.vcxproj`（C++：granny2wrapper、lz4wrapper、fastlz）和 Windows 批处理预编译步骤。[7][11]
- 发布：v1.20.4（2026-01-24，资产 `ExportTool-v1.20.4.zip`，需 .NET 8），此前 v1.20.3（2025-09-22）、v1.20.2（2025-09-05）；仓库最后推送 2026-03-31，926 star，MIT。zip 内是否含 `Divine.dll` 未下载核实。[9]
- 替代调用方式：`LaughingLeader/BG3ModdingTools/scripts/convert_loca.py` 用 `pythonnet.load('coreclr')` + `clr.AddReference("LSLib")` 直接调 `LocaUtils.Load(stream, LocaFormat.Xml/Loca)` 与 `LocaUtils.Save`，按扩展名决定方向；默认路径写死 Windows 风格，未声明 macOS 支持。由于 loca 代码只依赖 `Marshal` 与 `System.Xml`，在 macOS 的 .NET 8 上加载 `LSLib.dll` 走这条路径**理论可行但未实测**。[1][2][12]

### 2.3 跨平台 / Python 替代工具（GitHub API 元数据截至 2026-09-02）

| 项目 | 语言 / 形态 | PAK v18 | loca | 最近推送 · star · 许可 | 功能范围 / 可信度 |
|---|---|---|---|---|---|
| CyberDeco/MacPak + crate `maclarian` [28] | Rust；macOS 应用 + CLI（`cargo install maclarian`，0.1.3，2026-02-12） | PAK 浏览/解包/打包（版本未明示，面向 BG3） | LOCA↔XML | 2026-02-21 · 2★ · 自定义许可 | 还做 LSF↔LSX↔LSJ、GR2→glTF、GTS/GTP；Apple Silicon 测试过，Intel/Windows "testing"，应用 Release 标 "Coming Soon"。**Mac 上最完整的原生方案，但极新** |
| defakof/bg3rustpaklib [27] | Rust 库（crates.io 0.1.5，2026-04-25），无 CLI | v15/16/18 读/搜/解/建，LZ4/Zstd/zlib，solid | 二进制 .loca↔XML 工具 | 2026-04-25 · 1★ · MIT | 附 LSF 处理、async、C FFI，自称对标 lslib 有基准；单人项目 |
| crazyace/bg3-forge [29] | Python 3.10–3.13 | v15/16/18 解包 + **打包** | .loca 解析 | 2026-07-26 · 0★ · MIT | LSF/LSX、JSON/CSV/SQLite 导出、mod lint；核心无强制依赖，lz4/zstd 为可选 extra；v0.2.0 对应游戏版本 4.8.700 |
| danielsamuels/bg3-savefile-parser [30] | Python（+TS 移植） | 读 | 读，且 `FORMAT.md` 记录 LSPK/LSF/LSMF/.loca 二进制布局 | 2026-07-03 · 3★ | 存档读取器；只读，可作格式对照 |
| Wahkah/BG3SE [31] | Python 3.10+ | v18（.lsv）读 | 否 | 2026-07-31 · 0★ · MIT | 存档库，LSF v6/v7、LSMF；只读 |
| ShaiLaric/BG3MacModManager [32] | Swift/SwiftUI macOS | 原生 v18 **只读**（LZ4/zlib，系统 Compression 框架） | 否 | v1.4.0 2026-07-13 · 9★ · GPL-3.0 | Mac 端 mod 管理器，读 meta.lsx 写 modsettings.lsx |
| BenChao1998/BG3ModTranslation [36] | Rust + Tauri 桌面 + CLI `bg3mt` | 自研 v18 解包/打包（LZ4/Zlib/Zstd） | XML/JSON/Lua/Stats 四类文本 | 2026-07-05 · 0★ · MIT · v0.1.0 | AI 汉化工具，见 2.5；Actions 只出 Windows 包，macOS 未声明 |
| divadretlaw/LSKit [33]；caffineehacker/bg3modmanager、Ruttolomeo/pakrat、smacx250/BG3、clemarescx/bg3d [34] | Swift 包 / Rust / Python / Perl / Rust | 均只读（读 meta/lsx，pakrat 用 python-lz4） | 否 | 2024-10 / 2023-08 / 2026-09-01 / 2023-11 / 2026-04 | 只读小工具；bg3d 是 LSLib 子集的 Rust 1:1 移植（LSV） |
| enorsona/BG3LocalisationTool、arkennia/bg3parser [54] | Python | 否 | 仅 XML 层 | 2023-11 / 2023-10 · 0★ | 早期个人脚本，README 近乎为空 |
| PyPI [52] | — | — | — | — | `lslib/pylslib/bg3/bg3-loca/bg3loca/lspk/bg3pak/pylarian…` 共 22 个候选名全部 404；PyPI 搜索 `bg3/baldur/lslib/larian` 无结果 |

Windows 侧新出现的 C# 工具（Paramonov86/Para_Tool 7★、0x7A2C9E5D/BG3PakViewer，均 2026-09 推送）与本项目 Mac 工作流无关，略。[52]

### 2.4 BG3 Modder's Multitool [17][18][19][20][14]

- 可达性：`github.com/ShinyHobo/BG3-Modders-Multitool`、wiki 页、`api.github.com/repos/...`、`api.github.com/users/ShinyHobo` **全部 404**（各试 1 次）；搜索引擎索引仍残留旧链接。GitLab `ShinyHobo/bg3-modders-multitool` 可达：2026-06-06 建库，默认分支 develop，1122 次提交，最后一次提交 "Updated readme with archive links"（2026-06-06），README 的 wiki 链接全部指向 web.archive.org 的 2026-04/05 快照——说明 GitHub 仓库大约在 2026 年 5–6 月消失。Release 0.13.4（2025-06-01）。Thunderstore 镜像停在 0.10.6（2023-09-04）。
- 性质：Windows .NET 桌面工具（依赖 LSLib，"source available, not open source"，禁止再分发/修改）；README 提示 Linux 可用 Bottles 跑；含 CLI（packing、unpacking、indexing、search），另有第三方 `doombubbles/BG3-Modders-Unitool`（C#，2024-04）封装其打包功能。
- 自动转换约定：README 原文列出 `example.lsf.lsx`→`example.lsf`、`example.lsb.lsx`→`example.lsb`（打包时自动转换，"不必手动转换再复制"）；`.loca.xml`→`.loca`：bg3.wiki Modding:Localization 写明用 Multitool 解包得到的 `.loca.xml` 可以保留扩展名，"repacking 时会转回 .loca"，社区 wiki 的发型 mod 教程也说打包 Main 文件夹时自动把 `.loca.xml` 转成 `.loca`（后者仅搜索摘要）。解包方向：`.loca`→`.loca.xml`、`.lsf`→`.lsf.lsx`。

### 2.5 翻译辅助工具

| 工具 | 是什么 | 平台 / 技术 | 现状 | 来源 |
|---|---|---|---|---|
| BG3 script translator（Nexus 23203） | Google 翻译自动汉化 .loca/XML，含 .pak 解包/重打包、批量模式、**内置 LOCA↔XML 转换器**（不依赖外部工具），保护 LSTag/占位符/换行 | Python；`setup.bat/setup.sh` 自建 venv，自称跨平台；UI 葡/英/西 | 未找到 GitHub；Nexus 403 | 搜索摘要 [46] |
| XML TRANSLATOR（Nexus 19280） | 批量翻译文件夹内 XML（deep-translator→Google），自动检测源语言，保护 XML/LSTag，输出到 `Translated/` | Python + Tkinter；只处理 XML | Nexus 403 | 搜索摘要 [48] |
| BG3 Mod Auto Translator（Nexus 15778） | 抽取 XML `<content>` 用 DeepL API 翻译，保留结构 | Python | Nexus 403 | 搜索摘要 [47] |
| BG3 Mod Translator（Nexus 23274）= anboyu-alt/BG3-Auto-Korean | Gemini API 自动翻译 mod，解包→翻译→重打包；15 种目标语言含简/繁中；可引用已装官方语言包统一术语；批量目录 | Python；v7.0 起**自研 .pak/.loca 解析**，不再依赖 LSLib；发布 Windows 便携 exe | 2026-07-02 推送 · 3★ · MIT | [37] |
| Icosa – BG3 Translation Tool（Nexus 15976）= Kaironn2/Asmodeus-BG3-Mod-Translator-Desktop | 导入 XML/.pak/.zip，左右对照编辑，词典 CSV，OpenAI/Claude/Gemini/Grok/GLM/DeepSeek/DeepL/Google | Electron + React 19 + TS；Node 内**自研 LSPK v18 读写**（LZ4/Zstd），无需 .NET | 2026-09-02 推送 · 7★；**仅 Windows x64 便携包**，macOS/Linux 未发布 | [38] |
| LarinStudios Localization Helper（Nexus 3136）= Bg3LocaHelper（Tenvan） | XML 编辑器；导入 mod pak 直接生成翻译 mod；RapidAPI 微软/MyMemory 机翻 | .NET（v3.2+ 需 .NET 6/7 或 Framework 4.8.1/4.7.2），Windows | GitHub 451（DMCA 2024-01-08，投诉人为 Multitool 作者）；Nexus 页面据搜索摘要仍在（最后见 2024-01-27） | [21][22][23] |
| 3DM "BG3 LocaHelper" 汉化版 / 教程 | Juij 编译汉化版 v3.3.1（2023-11-06，帖子正文已被屏蔽）；教程（2023-10-22/11-05）流程：LSLib 解包→`Localization/Chinese/` 复制 English XML→LocaHelper 2.3 编辑并自动生成 loca→LSLib 或 LocaHelper "Pack Mod" 封包 | Windows 10 22H2+、.NET 4.8.1 | 无 GitHub（源码即被下架的 Tenvan 仓库） | [24][25] |
| 3DM 原创"快速本地化辅助工具" v1.0.0.6（iceriny） | 一键解 zip/pak→编辑 XML→一键回包，改 meta.lsx | 依赖 divine.exe；Windows | 2023-08-28；GitHub `iceriny/QuickLocalizationAids` 已 404 | [26] |
| YiYan129600/bg3-mod-ai-translator-zh | 英→简中 AI 工作流：OpenAI 兼容接口（OpenAI/DeepSeek/OpenRouter/SiliconFlow）、术语表 + 翻译记忆、严格校验（缺失/重复 handle、version、标签、占位符、残留英文）、只生成本地化 pak 并解包回验、双语覆盖率 CSV | Python 3.10+，Win/macOS/Linux；**pak/loca 转换调用外部 LSLib/Divine** | 2026-08-13 建库/推送 · 0★ · MIT | [35] |
| BenChao1998/BG3ModTranslation | AI 汉化：Ollama/OpenAI 兼容/Claude/Gemini + DeepSeek/Qwen/GLM/Kimi；SQLite 翻译缓存、术语一致性检查 | Rust + Tauri + CLI `bg3mt`，自研 LSPK v18 | 2026-07-05 · 0★ · MIT · v0.1.0；仅出 Windows 包 | [36] |
| mattarilightcha/BG3-Translation-DB-Tool | 日语向翻译辅助：SQLite/FTS5 词典、导入 `.loca.xml`（strict/replace）、导出 JSONL/TSV/CSV、与官方译文对齐、LSTag 工具提示插入 | Python 3.11 + FastAPI + 浏览器 UI；Win/macOS/Linux；纯 ElementTree，不依赖 LSLib | 2025-10-04 · 0★ · MIT | [39] |
| jestelf/BG3-rulocalizer | Google 翻译生成 russian.xml，配合 Multitool 解包 | Python / Windows exe | 2025-01-14 · 0★ · 非商业许可 | [40] |
| JungleDruid/BG3LocalizationMerger | 合并两种官方语言包（双语显示），需 Multitool 解包官方数据 | C# WPF，Windows | v1.1.1.0 2024-11-25 · 6★ · MIT | [41] |
| Bolganoth/BaldursGate3ChineseEnglishMergeTool | 本体中英双语自动合并（ConvertLoca/ConvertXml/ExtractPackage/CreatePackage 模块） | C#，基于 LSLib，Windows | 2023-10-12 · 46★ | [43] |
| BG3 Simple Translator（Nexus 10652）= Odashikonbu/BG3-Simple-Translator | 最简 .loca 翻译工具 | C# WPF，Windows | 2024-06-30 · 0★ | [42] |
| BG3 Translation Dictionary tool（Nexus 10527） | 用英文 + 目标语言官方 XML 建 `translation.db`，查原版译法（类 xTranslator） | 未知 | Nexus 403 | 搜索摘要 [49] |
| LWizard（Nexus 22349） | MO2 原生 C++ 插件：扫描 mod 翻译状态、找 Nexus 译文、在 MO2 内建翻译 mod | Windows/MO2 | Nexus 403 | 搜索摘要 [50] |
| VS Code BG3 Mod Helper（ghostboats） | UUID/handle 生成、把 handle 写入 `.loca.xml`、LSX/XML/LOCA 转换、打包/解包、模板、图集 | JS 扩展；需在设置里指定含 `LSLib.dll` 的目录 | Marketplace 2.2.63（2024-11-04），open-vsx 2.2.3（2024-05-24），GitHub 2024-11-04 · 6★ | [44] |
| Shresht7/vscode-bg3-modding | 片段、UUID/handle 生成、版本号换算；无 loca 转换 | TS 扩展，MIT | 2025-02-18 · 0★ | [45] |
| LaughingLeader/BG3ModdingTools | `convert_loca.py`（pythonnet 调 LSLib）、`convert_lsf.py`、`extract_game.py` 等；VS Code 片段含 handle 模板 | Python 3.10+ + LSLib.dll | 2025-09-27 · 59★ · MIT | [12] |

其它：`ulkyome/BG3-Tools`（C#、LSLib、俄语、README 为空，2023）、`TheCliffRacer/BG3-Localization-Updater`（1 次提交，无 README）、`vhof/bg3-uuid-dict-tool`（占位名→UUID/handle，2024-09）、`fireundubh/divine`（Divine 原作者 fork，2022 后无更新，README 未列 convert-loca）均无实际价值。[13][54]

## 3. 信息缺口 / 未核实

1. Nexus 全部页面（3136、23203、15778、19280、10652、10527、23274、15976、22349、6574、23204）与 `docs.baldursgate3.game/Adding_Localisation` 返回 403，描述均来自搜索摘要；3136 是否仍在线未直接核实。
2. Multitool 的 `.loca.xml→.loca` 规则：GitLab README 原文只写了 `.lsf.lsx/.lsb.lsx`；`.loca.xml` 依据 bg3.wiki（抓取成功）与 wiki.bg3.community（抓取被阻，仅搜索摘要）。GitHub 仓库/账号消失的原因未查到。
3. Divine/LSLib 在 macOS 的实际运行、pythonnet 调 `LSLib.dll` 的可行性、`ExportTool-v1.20.4.zip` 内是否含 `Divine.dll`：均未实测/未下载核实（避免下载二进制）。issue #220 仍 open，master 代码未修。
4. LSLibNative 在 pak 读写路径上是否被调用（影响 macOS 下用 LSLib.dll 解 pak）：GitHub 树 API 触发限流，未能逐文件确认；只能确认 loca 路径不涉及。
5. `.NET XmlWriter` 的转义/BOM/换行细节为背景知识，未在本次检索中找到 LSLib 输出样本逐字节验证。
6. maclarian/MacPak 的 PAK 版本号、bg3-forge 打包产物能否被游戏加载：README 未明示、未实测。
7. BG3 script translator（23203）的 GitHub 仓库、"BG3 LocaHelper" 3DM 汉化版的正文与下载：论坛屏蔽/未找到。`ilslli/BG3ModTool`、`iceriny/QuickLocalizationAids` 仓库已 404。
8. 简体中文目录名 `Chinese` 仅有 3DM 教程与搜索摘要佐证，官方文档页 403 未核实。
9. lslib issue #220 的两条评论通过 `gh api` 取得；#107/#196/#301 只读了标题与前几条评论，Norbyte 本人未见回复。

## 4. 来源表

| # | 标题 | URL | 一手/二手 | 抓取状态 | 日期 |
|---|---|---|---|---|---|
| 1 | LSLib `LSLib/LS/Localization.cs`（master） | https://raw.githubusercontent.com/Norbyte/lslib/master/LSLib/LS/Localization.cs | 一手 | 抓取成功（另 `LocaFormat.cs` 404） | 2026-09-02 |
| 2 | LSLib `LSLib/LS/BinUtils.cs` | https://raw.githubusercontent.com/Norbyte/lslib/master/LSLib/LS/BinUtils.cs | 一手 | 抓取成功 | 2026-09-02 |
| 3 | Divine `CLI/CommandLineArguments.cs` | https://raw.githubusercontent.com/Norbyte/lslib/master/Divine/CLI/CommandLineArguments.cs | 一手 | 抓取成功 | 2026-09-02 |
| 4 | Divine `CLI/CommandLineActions.cs` | https://raw.githubusercontent.com/Norbyte/lslib/master/Divine/CLI/CommandLineActions.cs | 一手 | 抓取成功 | 2026-09-02 |
| 5 | Divine `CLI/CommandLineDataProcessor.cs`、`Program.cs` | https://raw.githubusercontent.com/Norbyte/lslib/master/Divine/CLI/CommandLineDataProcessor.cs | 一手 | 抓取成功 | 2026-09-02 |
| 6 | LSLib `LSLib/LS/ResourceUtils.cs` | https://raw.githubusercontent.com/Norbyte/lslib/master/LSLib/LS/ResourceUtils.cs | 一手 | 抓取成功 | 2026-09-02 |
| 7 | `Divine/Divine.csproj`、`LSLib/LSLib.csproj`、仓库树 API | https://raw.githubusercontent.com/Norbyte/lslib/master/Divine/Divine.csproj | 一手 | 抓取成功 | 2026-09-02 |
| 8 | LSLib `LSLib/LS/PackageFormat.cs` | https://raw.githubusercontent.com/Norbyte/lslib/master/LSLib/LS/PackageFormat.cs | 一手 | 抓取成功 | 2026-09-02 |
| 9 | Norbyte/lslib README、GitHub API repo/releases | https://github.com/Norbyte/lslib/releases | 一手 | 抓取成功 | 2026-09-02 |
| 10 | lslib issue #220（Linux 路径校验） | https://github.com/Norbyte/lslib/issues/220 | 一手 | 抓取成功（评论经 gh api） | 2026-09-02 |
| 11 | lslib PR #107 / issue #196 / PR #301 | https://github.com/Norbyte/lslib/pull/301 | 一手 | 抓取成功（gh api） | 2026-09-02 |
| 12 | LaughingLeader/BG3ModdingTools `scripts/convert_loca.py` | https://github.com/LaughingLeader/BG3ModdingTools | 一手 | 抓取成功 | 2026-09-02 |
| 13 | fireundubh/divine README | https://github.com/fireundubh/divine | 二手 | 抓取成功 | 2026-09-02 |
| 14 | bg3.wiki Modding:Localization | https://bg3.wiki/wiki/Modding:Localization | 二手 | 抓取成功 | 2026-09-02 |
| 15 | bg3.wiki Guide:Unpacking and Converting Files | https://bg3.wiki/wiki/Guide:Unpacking_and_Converting_Files | 二手 | 抓取成功 | 2026-09-02 |
| 16 | bg3.wiki Modding:PAK files / Modding:Packaging mods | https://bg3.wiki/wiki/Modding:Packaging_mods | 二手 | 抓取成功 | 2026-09-02 |
| 17 | Multitool GitLab 项目 + API + README | https://gitlab.com/ShinyHobo/bg3-modders-multitool | 一手 | 抓取成功 | 2026-09-02 |
| 18 | Multitool GitHub 仓库 / wiki / 用户 API | https://github.com/ShinyHobo/BG3-Modders-Multitool | 一手 | 失败（404） | 2026-09-02 |
| 19 | Thunderstore Multitool 页面 + API | https://thunderstore.io/c/baldurs-gate-3/p/ShinyHobo/BG3_Modders_Multitool/ | 二手 | 抓取成功 | 2026-09-02 |
| 20 | wiki.bg3.community File-Setup（.loca.xml 自动转换） | https://wiki.bg3.community/en/Tutorials/Visual/Creating-A-Hair-Mod/File-Setup | 二手 | 搜索摘要（抓取被阻） | 2026-09-02 |
| 21 | GitHub DMCA 通知 2024-01-04-source-code-2 | https://github.com/github/dmca/blob/master/2024/01/2024-01-04-source-code-2.md | 一手 | 抓取成功 | 2026-09-02 |
| 22 | Tenvan/Bg3LocaHelper（GitHub） | https://github.com/Tenvan/Bg3LocaHelper | 一手 | 失败（451 DMCA） | 2026-09-02 |
| 23 | Nexus 3136 LarinStudios Localization Helper | https://www.nexusmods.com/baldursgate3/mods/3136 | 二手 | 搜索摘要 | 2026-09-02 |
| 24 | 3DM：Bg3LocaHelper v3.3.1 Juij 编译汉化版 | https://bbs.3dmgame.com/thread-6464459-1-1.html | 二手 | 抓取成功（正文被论坛屏蔽） | 2023-11-06 |
| 25 | 3DM：基于 LocaHelper 的 mod 汉化教程 | https://bbs.3dmgame.com/thread-6461116-1-1.html | 二手 | 抓取成功 | 2023-10-22 |
| 26 | 3DM：原创快速本地化辅助工具（iceriny） | https://bbs.3dmgame.com/thread-6448157-1-1.html | 二手 | 抓取成功（GitHub 仓库 404） | 2023-08-28 |
| 27 | defakof/bg3rustpaklib + crates.io API | https://github.com/defakof/bg3rustpaklib | 一手 | 抓取成功 | 2026-09-02 |
| 28 | CyberDeco/MacPak + crates.io `maclarian` | https://github.com/CyberDeco/MacPak | 一手 | 抓取成功 | 2026-09-02 |
| 29 | crazyace/bg3-forge | https://github.com/crazyace/bg3-forge | 一手 | 抓取成功 | 2026-09-02 |
| 30 | danielsamuels/bg3-savefile-parser | https://github.com/danielsamuels/bg3-savefile-parser | 一手 | 抓取成功 | 2026-09-02 |
| 31 | Wahkah/BG3SE | https://github.com/Wahkah/BG3SE | 一手 | 抓取成功 | 2026-09-02 |
| 32 | ShaiLaric/BG3MacModManager | https://github.com/ShaiLaric/BG3MacModManager | 一手 | 抓取成功 | 2026-09-02 |
| 33 | divadretlaw/LSKit | https://github.com/divadretlaw/LSKit | 一手 | 抓取成功 | 2026-09-02 |
| 34 | caffineehacker/bg3modmanager；Ruttolomeo/pakrat；smacx250/BG3；clemarescx/bg3d | https://github.com/caffineehacker/bg3modmanager https://github.com/Ruttolomeo/pakrat https://github.com/smacx250/BG3 https://github.com/clemarescx/bg3d | 一手 | 抓取成功 | 2026-09-02 |
| 35 | YiYan129600/bg3-mod-ai-translator-zh | https://github.com/YiYan129600/bg3-mod-ai-translator-zh | 一手 | 抓取成功 | 2026-09-02 |
| 36 | BenChao1998/BG3ModTranslation | https://github.com/BenChao1998/BG3ModTranslation | 一手 | 抓取成功 | 2026-09-02 |
| 37 | anboyu-alt/BG3-Auto-Korean（= Nexus 23274） | https://github.com/anboyu-alt/BG3-Auto-Korean | 一手 | 抓取成功 | 2026-09-02 |
| 38 | Kaironn2/Asmodeus-BG3-Mod-Translator-Desktop（= Nexus 15976 Icosa） | https://github.com/Kaironn2/Asmodeus-BG3-Mod-Translator-Desktop | 一手 | 抓取成功 | 2026-09-02 |
| 39 | mattarilightcha/BG3-Translation-DB-Tool | https://github.com/mattarilightcha/BG3-Translation-DB-Tool | 一手 | 抓取成功 | 2026-09-02 |
| 40 | jestelf/BG3-rulocalizer | https://github.com/jestelf/BG3-rulocalizer | 一手 | 抓取成功 | 2026-09-02 |
| 41 | JungleDruid/BG3LocalizationMerger | https://github.com/JungleDruid/BG3LocalizationMerger | 一手 | 抓取成功 | 2026-09-02 |
| 42 | Odashikonbu/BG3-Simple-Translator（= Nexus 10652） | https://github.com/Odashikonbu/BG3-Simple-Translator | 一手 | 抓取成功 | 2026-09-02 |
| 43 | Bolganoth/BaldursGate3ChineseEnglishMergeTool | https://github.com/Bolganoth/BaldursGate3ChineseEnglishMergeTool | 一手 | 抓取成功 | 2026-09-02 |
| 44 | ghostboats/bg3_mod_helper README + VS Marketplace API + open-vsx API | https://github.com/ghostboats/bg3_mod_helper | 一手 | 抓取成功 | 2026-09-02 |
| 45 | Shresht7/vscode-bg3-modding | https://github.com/Shresht7/vscode-bg3-modding | 一手 | 抓取成功 | 2026-09-02 |
| 46 | Nexus 23203 BG3 script translator | https://www.nexusmods.com/baldursgate3/mods/23203 | 二手 | 搜索摘要（抓取 403） | 2026-09-02 |
| 47 | Nexus 15778 BG3 Mod Auto Translator | https://www.nexusmods.com/baldursgate3/mods/15778 | 二手 | 搜索摘要 | 2026-09-02 |
| 48 | Nexus 19280 XML TRANSLATOR | https://www.nexusmods.com/baldursgate3/mods/19280 | 二手 | 搜索摘要 | 2026-09-02 |
| 49 | Nexus 10527 BG3 Translation Dictionary tool | https://www.nexusmods.com/baldursgate3/mods/10527 | 二手 | 搜索摘要 | 2026-09-02 |
| 50 | Nexus 22349 LWizard | https://www.nexusmods.com/baldursgate3/mods/22349 | 二手 | 搜索摘要 | 2026-09-02 |
| 51 | docs.baldursgate3.game Adding Localisation | https://docs.baldursgate3.game/index.php?title=Adding_Localisation | 一手（官方） | 失败（403） | 2026-09-02 |
| 52 | GitHub 搜索 API（bg3 loca / lspk / bg3 pak 等 12 组查询）、PyPI JSON API | https://api.github.com/search/repositories?q=bg3+loca | 一手 | 抓取成功 | 2026-09-02 |
| 53 | 中文目录名/CHS 惯例（Nexus 3073 教程、GameMale、bilibili 搜索结果） | https://www.nexusmods.com/baldursgate3/mods/3073 | 二手 | 搜索摘要 | 2026-09-02 |
| 54 | ulkyome/BG3-Tools；enorsona/BG3LocalisationTool；arkennia/bg3parser；TheCliffRacer/BG3-Localization-Updater | https://github.com/ulkyome/BG3-Tools https://github.com/enorsona/BG3LocalisationTool https://github.com/arkennia/bg3parser | 一手 | 抓取成功（README 近空） | 2026-09-02 |
| 55 | Nexus 23204 "BG3 Mod Helper - Update Helper Edition" | https://www.nexusmods.com/baldursgate3/mods/23204 | 二手 | 搜索摘要 | 2026-09-02 |

## 5. 抓取统计

- WebFetch：65 次，成功 51，失败 14（404×5：LocaFormat.cs、Multitool GitHub 仓库/wiki、ilslli/BG3ModTool、iceriny 仓库；451×2：Tenvan 两个仓库；403×2：Nexus 23203、docs.baldursgate3.game；域名拦截/代理拒绝×3：pypi.org、wiki.bg3.community、nightabyss.fun；仅返回标题×2：wiki.bg3.community 两页）。
- WebSearch：33 次，全部返回结果。
- 脚本直连（python urllib + `gh api`，对 raw.githubusercontent / api.github.com / gitlab / crates.io / pypi / open-vsx / VS Marketplace / thunderstore）：约 135 次请求，约 21 次失败（GitHub 404/451、一次触发未认证限流后改用 `gh api` 补齐关键项）；PyPI 22 个候选包名的 404 视为"包不存在"的有效结果，不计入失败。
- 未使用任何浏览器类工具；未下载任何二进制发布包。
