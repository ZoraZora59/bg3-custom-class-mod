# L · 最小职业骨架验证：官方资料复核

复核日期：2026-09-28。范围：职业工程、编辑器测试、本地发布、第三方 Mod 排障。此记录补充 `G-official-docs-browser.md`，不覆盖其他会话的东方剑修设计。

## 结论与当前状态

下一轮应建立 **Toolkit 生成的最小职业基线**，先在编辑器验证升级，再本地导出到游戏验证角色创建。手工包的若干调整没有证明加载故障的原因，不能把“能生成 PAK”记为“游戏验证通过”。

截至本记录：

| 检查 | 结果与证据边界 |
|---|---|
| 占位符替换、静态检查 | 已完成；`check_mod.py` 曾返回 0 errors / 0 warnings |
| 中英本地化转换 | 已完成；中文 Python 与 Divine 产物逐字节一致 |
| PAK 生成与解包回读 | 已完成；第一次 API 包的 9 个文件与 staging 一致 |
| 游戏识别与启用 | 前三轮未在已安装列表看到 SkeletonSmokeTest；首轮显式配置被游戏重置 |
| 最新候选包 | 已转换 4 份非 meta LSX 为 LSF，并准备过显式 ModOrder；尚未启动验证该组合 |
| 新职业角色创建、升级、子职业选择 | **未验证，不能报通过** |
| 恢复用户环境 | 游戏关闭后已恢复原 modsettings，删除仅本次部署的 SkeletonSmokeTest.pak；未加载或覆盖旧存档 |

原配置恢复 SHA256：`4621819A07E594C035EBDB3FB91E4FC7C23138AADEA200776CD7EEC860AD8F2F`。
备份：`build/smoke-test-20260928/backup/modsettings.lsx`。候选包和工具留在忽略目录 `build/`；源文件在 `mods/SkeletonSmokeTest/Source/`。

## 官方资料确认的路径

### 1. 编辑器与游戏数据是两项安装

Toolkit 在 Steam 的 Tools 分类；还需要 BG3 属性里的 Toolkit Data DLC。[安装教程](https://docs.baldursgate3.game/Getting_Started:_Installing_the_Toolkit)

本机已检查的 D、E 两个 Steam 库只有 BG3 的安装清单，未发现 Toolkit 清单；BG3 清单此前显示 Toolkit Data DLC。**有 DLC 数据不等于已经安装编辑器。** 后续须在 Steam 核实工具安装状态，不能直接假定可启动。

### 2. 仓库源码目录不等于编辑器工程

官方区分 `Data/Projects` 的工程信息、`Data/Editor/Mods` 的编辑器数据，以及会打包的 `Data/Mods`、`Data/Public`、`Data/Generated/Public`。[新建工程教程](https://docs.baldursgate3.game/Getting_Started:_Creating_a_New_Mod)

现有骨架主要提供打包输入，没有 Toolkit 的工程和 UUID/Stats 编辑器数据。它可保留作源码参考，但下一轮要由 Toolkit 新建工程得到可比较的导出基线。

### 3. 职业和升级的官方验证入口

官方职业教程确认：各等级共享 TableUUID，行 UUID 各自唯一；主职业 ProgressionType 为 0，子职业为 1；ClassDescriptions 连接对应进阶表；Learning Strategy 使用 AllChildren。子职业还需父职业关联及指定等级的 SubClasses 选择。

官方快速测试使用 `Basic_Level_A` → Game Mode；鼠标悬停头像按 `Ctrl+Shift+L`，在升级界面 Add Class 选择自定义职业，再升级到子职业等级。[职业教程](https://docs.baldursgate3.game/Adding_Classes_and_Subclasses)

这些快捷键属于 **Toolkit 测试环境**，不能假定正式游戏客户端同样支持。下一轮不需要先修改 XP 阈值或跑完整教程关卡。

### 4. 本地导出无需上传

Project Settings 的 Publish Local 生成 PAK，无需认证，也不上传 mod.io。发布设置要求 Name、Description、Thumbnail。[发布教程](https://docs.baldursgate3.game/Getting_Started:_Publishing_a_Mod)

应先让 Toolkit 导出自己的正确工程，再比较其 meta、目录、资源格式与当前手工包。是否缺 NumPlayers、是否需要特定包标记，必须由对比或隔离测试确认。

### 5. 不可把 PAK 导入视为完整工程恢复

Patch 8 的 Import 功能明确不导入 Stats 和 UUID 文件，无法完整还原本骨架核心的职业与进阶表；编辑器日志会报告跳过的文件。[导入限制](https://docs.baldursgate3.game/index.php?title=Importing_a_Mod)

因此下一轮应新建最小工程并按表建立数据，不采用“把现有 PAK 导入后就直接编辑所有内容”的路线。

### 6. 本地化与诊断

官方确认本地化源文件放 `Mods/<Mod>/Localization/<Language>/*.xml`，简体语言目录为 Chinese；修改后需要重载模块或重启。[本地化教程](https://docs.baldursgate3.game/index.php?title=Adding_Localisation)

官方排障页确认游戏使用 LocalAppData，第三方 Mod 仍可使用；启动器的 alteredFiles 日志可用于检查路径和数据不匹配。[Mod Issues](https://larian.com/support/faqs/mod-issues_112)

“第三方包不能在游戏中使用”不是当前故障的结论。当前未取得能定位本包失败原因的加载错误，不能凭界面列表缺失就断言是包标记、某字段或第三方限制。

## 尚不能由官方资料直接确认的事项

| 尝试/问题 | 应如何处理 |
|---|---|
| AllowMemoryMapping 与归档校验值 | 是按现有包对比作的尝试；第二轮仍未识别，尚无因果证明 |
| meta 增加 NumPlayers=4 | 第三轮仍未识别；不能称为已修复根因 |
| LSX → LSF | 当前资料未提供通用的手工打包格式规范；以 Toolkit 实际导出与原版资源为下一轮基线，最新候选未实测 |
| 手工 ModOrder | 最新显式顺序未实测；不反复改配置碰运气，优先使用选定管理器写入并保存前后差异 |
| 多职业字段位置 | 官方教程在该节写 ClassDescriptions，但描述 Level 1 / IsMulticlass；仓库骨架把该标记放在 Progressions。两者需要通过当前编辑器列和实际导出结果核对，勿直接照文字添加未知属性 |

## 下一轮验收顺序

1. 核实并配置 Toolkit，Data 指向本机 `E:/SteamLibrary/steamapps/common/Baldurs Gate 3/Data`。
2. 新建独立工程，仅建一个主职业、1–3 级进阶和一个 3 级子职业，先复用原版效果，避免混入正式剑修机制。
3. 编辑器保存、按教程重启，在 Basic_Level_A 验证职业入口、1→2→3 级和子职业选择，记录 Message Log。
4. Publish Local，解包核对 meta、表格式、名称与 UUID；一次只比较一个变量。
5. 备份用户配置，用一个管理器启用该包，新开测试角色，验证创建和进入游戏；结束后恢复原配置。
6. 分开记录“编辑器升级通过”“正式游戏创建通过”“正式游戏升级通过”。图标、战斗数值、完整 12 级成长和正式剑修设计另行验收。

本次官方资料复核没有恢复电脑界面操作，也没有安装编辑器、发布 Mod 或修改用户旧存档。

## 继续执行记录（2026-09-28）

用户授权继续后，已安装 Steam Toolkit（App 2934770），配置 Data 路径，新建独立 `SkeletonToolkitTest` 工程，并首次载入 Basic_Level_A。

源表已由 UUID Object Editor 打开验证：2 条职业描述、15 条进阶、1 条技能列表、1 条属性列表。表可读出英文名称和描述，且子职业 ParentUUID 以及 3 级 SubClasses 关联正确。

初次游戏模式职业列表只显示原版职业。检查后发现 `.tbl` 源表尚未导出。逐表使用 File → Export 后，实际生成四个 Public `.lsx`。Ctrl+S 在未修改表时禁用，不能当作已导出的证据。

Publish Local 已生成 12,980 字节的本地 PAK，解包确认它包含 Public 的 **LSX** 以及 Localization 的 **XML**；因此不能把“必须转 LSF/LOCA”视为 Toolkit 导出的普遍要求。包还包含 `Mods/.../GUI/metadata.lsf`，当前不能仅凭新增文件就认定旧包未识别的唯一根因。

本机官方 `Editor/Mods/SharedDev/Progressions/Progressions.tbl` 第 24–35 行明确存在 Barbarian 多职业 1 级节点，字段为 `IsMulticlass`、`BoolTableFieldDefinition`、`True`。官方教程该节将表名写成 ClassDescriptions，与本机源表不一致；后续按已验证的 Progressions 字段实现。当前第一次本地包仍排除该节点，先测主职业创建。

正式游戏验证已另行备份原 modsettings（SHA256 `4621819A07E594C035EBDB3FB91E4FC7C23138AADEA200776CD7EEC860AD8F2F`），临时仅保留 GustavX，准备通过游戏界面启用测试包。结束后须恢复这个备份。

正式游戏 v4.1.1.7398727 的 Mod 管理器已识别并列出 `SkeletonToolkitTest`，通过复选框成功启用。读取 modsettings 确认测试模块 UUID、Folder、Version64 与已发布包一致；当前没有启用其他用户 Mod。这证明本地包已被管理器接受，尚不能证明角色创建、升级或战斗效果通过。

随后按已核对的 SharedDev 进阶字段准备包含多职业节点的 Editor 源表（16 行）；它尚需 Toolkit 导出，当前已发布包及 Public 副本仍为 15 行。不要直接将这两个阶段混为同一已验证版本。

## 编辑器验收与新版包（2026-09-29）

已经重新打开并导出 Progressions，确认 Public 为 16 行、包含 `IsMulticlass=true` 的 1 级入口。重启后在 Basic_Level_A 按官方教程测试，职业网格向下滚到底部后出现第 13 个 ExampleClass。此前“仅原版职业”的观察没有覆盖完整列表，应予纠正。

实际角色为 Wyll：保留邪术师 1 级，Add Class 添加 ExampleClass 1 级并确认；再次升级选择示例职业，取得 2 级；第三次取得 3 级并在 Subclass 页确认 ExamplePath，接受升级后返回测试场景。三个阶段生命值为 18、26、34。它证明编辑器多职业升级链和子职业关联有效，不等于正式客户端主职业创建或升级已经通过，也不证明附加伤害已在战斗中生效。

新增的明确资源错误是缺少 `Assets/ClassIcons/SkeletonToolkitTest.png` 和 hotbar 对应图标；当前职业按钮图标空白，但能选择并完成升级。Basic_Level_A 的头像渲染警告尚未证明会影响正式客户端。

升级验证后 Publish Local 一次访问异常退出，崩溃栈包含 `ls::File::Seek`、`ls::PackedFile::PackedFile`、`PublishBackend.PackCurrentMod`，旧包未改变。关闭正式游戏后重新载入工程，不加载关卡，再次 Publish Local 成功，日志明确显示本地发布成功。无法据此隔离证明根因。

新版包：13,173 字节；Version64 `36028797018963971`；SHA256 `D917201F2B5FC6302741E670786338DC90371709A232642661831EF56C4593C5`。解包回读为 16 行进阶（其中 1 行多职业），同时包含中英 XML、本地发布缩略图和 GUI metadata。源文件检查为 0 个错误、0 个警告。

## 正式客户端创建验收与恢复（2026-09-29）

新版包第一次正式创建观察未见自定义职业。关闭游戏后检查发现 modsettings 中测试模块仍记录旧 Version64 `36028797018963969`，而包元数据为 `36028797018963971`；仅更新临时配置中的这个版本号，随后通过 Steam 启动正式游戏。

复测过程中用户误按 Esc 中断了电脑操作，随后明确授权继续。重新读取现场时，创建列表已经显示并选中中文“示例职业”，说明文本和职业特性可读。继续完成敏捷 +2、感知 +1、运动和体操两项技能熟练，确认角色与守护者并进入鹦鹉螺。场景内角色生命值为 12/12，快捷栏具有“示例职业”分类。正式客户端新建角色和进入场景通过。

该次观察包含版本刷新、重启与现场短暂手动输入，尚未分别隔离变量；不可把版本号认定为唯一根因。小复选框的自动化点击也曾未响应，调整点击位置后正常完成，不应把输入未命中当作数据失效。

最终验收边界：正式游戏创建通过；Toolkit 中邪术师 1 + 示例职业 1→2→3 及 3 级子职业选择通过；正式游戏升级、战斗伤害与完整 12 级成长尚未验证。职业图标仍缺失。

已通过游戏菜单正常退出；确认 bg3、bg3_dx11 与 Glasses 均未运行后恢复原 modsettings，SHA256 与备份一致：`4621819A07E594C035EBDB3FB91E4FC7C23138AADEA200776CD7EEC860AD8F2F`。游戏 Mods 中恢复为原有 14 个 PAK；只移出本次测试 PAK。新建角色的 `AutoSave_0` 与测试 PAK 均归档在忽略目录 `build/toolkit-test/retired-20260929/`，既有用户存档没有载入或改写。工程源文件、官方发布包和完整测试记录保留供后续复测。
