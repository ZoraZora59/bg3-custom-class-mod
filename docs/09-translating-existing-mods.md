# 09 · 给别人的 mod 做汉化：直接改原 mod，还是做独立汉化 mod？

> 调研日期 2026-09-02。证据来自 research/H（loca 格式与工具）、I（引擎行为）、J（社区惯例与政策）、K（主控浏览器直读）以及此前的 G（官方文档）。引用写法 `I[10]` = 报告 I 来源表第 10 条。

## 0. 一句话结论

**做独立汉化 mod**：一个只含 `Localization/Chinese/<名字>.loca` 和 `Mods/<Folder>/meta.lsx` 的小 pak，放在原 mod **之下（更晚）**加载。不要解包原 mod、塞进中文再重新打包分发。这是 bg3.wiki、Nexus 规则、Larian/mod.io 准则、3DM 中文教程第二版和几乎所有 N 网 CHS 条目共同指向的做法 K[K1] J[21][27] J[43] J[1]。

只有两种情况可以"直接改原 mod"：① 只是自己玩、不分发；② 原作者同意把你的译文**合并进原 mod**（这时不是你改，而是你把 xml 交给作者）。

## 1. 两种做法逐项对比

| 维度 | A. 直接改原 mod（解包 → 加 `Localization/Chinese` → 重打包） | B. 独立汉化 mod（推荐） |
|---|---|---|
| 工作量（首次） | 略少：不用写 meta.lsx | 多一个 meta.lsx（LocaHelper 可自动生成；本仓库骨架里有模板） K[K4] |
| 原 mod 更新后 | 每次都要重新解包整个新版、重放译文、重打包 | 只翻新增/变更的 handle，其余不动；"原 mod 未新增字符串则无需更新" J[17] |
| 许可与平台规则 | 等于再分发他人的全部资产：Nexus 规定翻译"只能作为与原文件配合使用的附加文件"，未获许可可被删除 J[21]；mod.io/Larian 要求扩展、翻译、重制他人 mod 须先取得许可 K[K2] | 只含你的译文 + 原 mod 的 handle；仍需征得作者同意，但合规路径清晰，Nexus 上传时可直接标记为 "Translation of an existing mod" J[22] |
| 与原 mod 的身份关系 | 与原 pak 同名/同 UUID 会互相顶替，被管理器当成另一版本，联机校验也会不一致 J[17] I[2] | 新 UUID、新 Folder，原 mod 原样保留 K[K1] |
| 联机 | 全员必须用你改过的版本 | 全员都装这个小 mod 即可（对英文客户端无副作用，只多一个 Chinese 目录）I[43]（推断） |
| 主机（PS5/Xbox） | 不可能 | 只有经官方 Toolkit 发布到 mod.io 并通过 Larian 审核才可能 K[K2][K7] |
| 一包多译 | 不适用 | 一个汉化包可以覆盖同系列多个 mod（3DM 版主的 "Chinese Patch Collection" 就是这样）K[K4] |
| 覆盖不走 loca 的文本（Lua/JSON 硬编码） | 可以直接改文件 | 做不到（同路径覆盖理论可行但脆弱），见 §2.6 I[31][12] |
| 社区观感 | 早期（2023-09/10）教程这么教，现在被视为过渡形态；贴吧楼主学会后把一体包隐藏、改发独立补丁 J[48][49] | 主流 J[1] |

## 2. 引擎层面必须知道的 6 件事

1. **缺失 handle 不会显示裸 handle。** 引擎的翻译仓库带 `FallbackPool`/`VersionedFallbackPool`，查询顺序是当前语言池 → 版本回退池 → 回退池（bg3se 对游戏结构的定义，已核实）I[10][11]；原版俄语缺行时回退英文 I[36]；handle 在所有池都没有时显示 "Not Found" I[42][35]。**"只带 English 的 mod 在简中客户端显示英文"是高置信推断，无一手明文**，mod.io 上一位翻译作者的经验描述也是这个顺序 K[K7]。→ 汉化是体验问题，不是"能不能玩"的问题；这也是 docs/07 V6 的答案（待 Windows 5 分钟实测封口）。
2. **多 pak 的同语言文本按 handle 逐条合并，后加载者覆盖；同路径同名文件则整体替换。** 日语社区原话"后读取者胜" I[31]；Nexus App 文档 "last loaded wins" I[4]；Larian 论坛实验证明同名 `English.loca` 会整体顶掉原文件 I[5]。加载顺序 = `modsettings.lsx` 里 `ModOrder` 从上到下，被依赖者在上、依赖者在下 K[K6]，所以**"翻译补丁放在原 mod 之下" = 更晚加载 = 优先级更高** K[K1]。稳妥做法：汉化 pak 排在原 mod 之后，且 loca 文件名与原 mod 不同（例如 `<Mod>_CHS.loca`），避免误触发整体替换 I[5]（推断）。
3. **`contentuid` 与 `version` 原样保留。** 引擎查表只比较 handle、忽略 version（源码已核实）I[10]，官方定义 version 用于"更新自己的行或覆盖游戏已有的行" K[K8]；bg3.wiki 明令"不要改 version 或 contentuid" K[K1]。不要靠抬 version 去"压过"原 mod，覆盖靠加载顺序即可。
4. **手工打包的 pak 里必须是 `.loca`。** 所有社区流程都在打包前转换 I[1][5][30][33]；3DM 教程明说"游戏只能识别 loca" K[K4]；`.xml` 只是官方 Toolkit 项目里的源格式，发布时转换 K[K7][K8]。Multitool 会把 `x.loca.xml` 自动转回 `x.loca` H[14]，但它会把多个 xml 合并、同 handle 在 mod 内部互相覆盖，官方 Toolkit 不会 K[K7]。
5. **目录名固定：简体 `Localization/Chinese/`，繁体 `Localization/ChineseTraditional/`**（官方 15 语言列表）G[G7] K[K8]；写成 `ChineseSimplified`、`zh-CN` 都不会被读取。
6. **哪些文本不走 loca**：Script Extender 的 Lua 里硬编码的字符串、pak 内直写英文的 JSON、贴图上的文字。日语社区点名 Trials of Tav Reloaded（Lua UI）和 Automatic Inventory Manager 装了语言包仍是英文 I[31]。MCM（Mod Configuration Menu）的配置界面只有在作者给每个字段写了 `Handles` 时才能用 loca 汉化，否则只能覆盖它的 `MCM_blueprint.json` I[23][24]。SE 提供 `Ext.Loca.UpdateTranslatedString` 可在运行时替换任意 handle 文本，但只写内存、每次会话重跑 I[9][11]。SE 的 IMGUI 中文字形已扩到全字集（v19+），但 4K 分辨率下有乱码报告未解决 I[14][16]。

## 3. 推荐流程（Mac 编辑 + Windows 验证）

### Step 0 · 先要许可，再动手
- 看原 mod 的 Nexus 页面 Permissions 区块和作者写的 Permission notes（Nexus 没有单独的 "Translation permission" 下拉项，翻译政策通常写在自由文本或 Modification permission 里）J[24]；私信作者，说明你要发独立汉化补丁并会互链。"99% 的作者都乐意，但把原 mod 设为依赖并不会通知作者" K[K1]。
- 作者失联也不能自我授权；可以在评论区/论坛公开征求 J[25]。
- 把许可截图/链接留档，发布页写明。

### Step 1 · 解包，只取本地化
- Windows：LSLib ConverterApp 的 PAK/LSV 工具，或 `Divine -g bg3 -a extract-package -s Mod.pak -d out` H[4][15]；Multitool 解出的是 `.loca.xml`（可直接编辑）K[K1]。
- Mac：Rust 工具 `maclarian`（MacPak，`cargo install maclarian`）声称支持 PAK 读写与 LOCA↔XML，但是 2026 年 2★ 的新项目，未实测 H[28]；Python 的 `bg3-forge` 也能解包/打包 v18 H[29]。**当前建议解包/打包交给 Windows**，Mac 只做文本层。
- 只需要 `Localization/English/*.loca`（或 `.loca.xml`），其它目录一律不要 K[K1]。顺便记下原 mod `meta.lsx` 里的 `UUID`/`Folder`/`Name`/`Version64`（写依赖用）。
- 检查是否已有 `Localization/Chinese`：有的话，多半是作者把英文复制了一份"占位"，你的汉化 pak 只要在它之后加载就能逐条覆盖（§2.2）。

### Step 2 · loca → xml（Mac 可做）
```bash
python3 scripts/loca_convert.py to-xml path/to/English/Mod.loca      # 输出 Mod.loca.xml
python3 scripts/loca_convert.py check  path/to/English/Mod.loca.xml   # 重复/超长 handle、非法子元素
```
`scripts/loca_convert.py` 是按 LSLib `Localization.cs` 的二进制布局用纯 Python 写的（12 字节头 + 每条 70 字节 + NUL 结尾文本）H[1][2]，已做字节级往返自测，**尚未用游戏真实 .loca 验证**（docs/07 V13）。Windows 上等价命令：`Divine -g bg3 -a convert-loca -s Mod.loca -d Mod.xml`（方向只看扩展名，无批量模式）H[3][5]。

### Step 3 · 建汉化工程目录
```
<Mod>_CHS/
├── Localization/
│   └── Chinese/
│       └── <Mod>_CHS.xml        # 从 English 复制并翻译；打包前转成 <Mod>_CHS.loca
└── Mods/
    └── <Mod>_CHS/
        └── meta.lsx             # 新 UUID；Folder/Name = <Mod>_CHS；可选 Dependencies
```
- 目录名 `Chinese`、文件名与原 mod 不同、`Mods/<Folder>` 与 meta 的 `Folder` 逐字一致（docs/04 A2）。
- meta.lsx 从 `templates/mod-skeleton/Source/Mods/ExampleClass/meta.lsx` 复制，用 `scripts/gen_ids.py` 换 UUID、`scripts/version64.py encode <与原 mod 对应的版本>` 生成 Version64；`Dependencies` 节点填原 mod 的 UUID/Folder/Name/Version64（MD5 留空）I[3]。声明依赖的好处是游戏先加载依赖、BG3MM 能按依赖排序并对缺失标红 I[4][26]；坏处是原 mod 换 UUID 或大幅升版本时会报缺依赖。bg3.wiki 的建议是"先不加，出问题再加" K[K1]；社区 CHS 条目多数只在描述里写"需原 mod、加载于其下" J[9]。

### Step 4 · 翻译规则
- **只改 `>` 与 `<` 之间的正文**，不动 `contentuid`/`version`；改错 handle 的后果是 "Not Found" J[49]。
- 正文里的富文本以转义实体形式存在：`&lt;LSTag Type="Spell" Tooltip="Bless"&gt;Bless&lt;/LSTag&gt;`、`&lt;br&gt;`——翻译标签内的显示文本（`Bless` → `祝福术`），**不要翻译 `Tooltip=` 等属性值**，不要把实体还原成真实标签（LSLib 与本仓库脚本都会拒绝真实子元素）H[1]。
- 描述里的 `[1]`、`[2]` 是 `DescriptionParams` 占位符，原样保留；术语与官方简中对齐：解包 `Data/Localization/Chinese.pak` 得到官方译文 J[53]，或查 B 站 BWIKI / VG 百科法术表 J[54][55]；mod 若直接复用了原版 handle，那些条目已经有官方中文，不必翻译 J[36]。
- 机翻初稿：跨平台的 `YiYan129600/bg3-mod-ai-translator-zh`（Python，术语表 + 翻译记忆 + 严格校验，打包需外部 LSLib）H[35]、`BenChao1998/BG3ModTranslation`（Rust，自研 pak 解析，只出 Windows 包）H[36]；Nexus 上的 script translator / XML TRANSLATOR / Mod Auto Translator 走 Google/DeepL H[46][47][48]。初稿后必须人工校对；社区 CHS 页面常标注"新增文本先机翻待校" J[11]。
- 想让某条保持英文：直接从中文 xml 删掉该 handle 即可（回退到英文）K[K7]。

### Step 5 · xml → loca、打包
```bash
python3 scripts/loca_convert.py batch <Mod>_CHS/Localization --to loca --delete-source   # Mac：只留 .loca
```
- 打包（Windows）：`Divine -g bg3 -a create-package -s <Mod>_CHS -d <Mod>_CHS.pak -c lz4hc` H[4]，或 Multitool 拖拽打包，或官方 Toolkit "Publish Local"（Toolkit 管线要放 xml、由它转换）K[K7] G[G6]。
- 不要与原 mod 同名：同名 pak 会互相顶替甚至崩溃 J[17]。

### Step 6 · 游戏内验证（Windows）
- 游戏语言切到简体中文；BG3MM 或游戏内管理器里把汉化 mod 放在原 mod **之下** K[K1][K6]；只用一个管理器写 `modsettings.lsx`（docs/04 B2）。
- 检查：角色创建里的职业/子职业名与描述、升级面板、法术/被动 tooltip、物品名、对话字幕；长句在 tooltip 里的折行；是否有 "Not Found"。
- 改完 xml 想快速重载：Toolkit 调试台 `reloadLoca` K[K8]；纯游戏则重启。

### Step 7 · 发布
- **Nexus**：上传时选 "Translation of a file/mod that already exists"，语言选 "Mandarin"（Nexus 的简中标签名）J[22][26]；标题惯例 `<原 mod 名> - CHS` / `<原 mod 名> 简体中文汉化`；描述写：对应原 mod 版本号（常与原 mod 同步）J[11][4]、"仅含翻译文件，需另装原 mod，加载于原 mod 之下" J[9]、许可来源与作者链接。翻译会出现在原 mod 页面的 Translations 区块。
- **mod.io / 主机**：只能通过官方 Toolkit 新建项目 → 复制 `Localization/Chinese/*.xml` 进项目 → 填信息与 Dependencies → Publish；mod.io 无翻译分区，打 `translation` + 语言 tag；主机还要 Larian 审核 K[K2][K7]。原 mod 不在 mod.io 时没有意义。
- **中文社区**：3DM 论坛"正式版MOD/补丁"区、3DM Mod 站、贴吧、B 站 J[47][50][51]。

### Step 8 · 原 mod 更新后
```bash
python3 scripts/loca_sync.py diff old_English.xml new_English.xml   # 新增/变更/删除的 handle 清单
python3 scripts/loca_sync.py sync <工程>/Localization --langs Chinese  # 缺失条目以英文占位并标 [TODO]
python3 scripts/loca_convert.py check <工程>/Localization/Chinese/<Mod>_CHS.xml   # [TODO] 归零才发布
```
只翻新增/变更的条目；版本号跟着原 mod 走；过时的症状是新增文本显示英文或 "Not Found" J[15][49]。LocaHelper 类工具把新增文本标蓝做的就是这件事 K[K4]。

## 4. 什么时候可以（或只能）改原 mod

| 情形 | 做法 |
|---|---|
| 自己玩，不分发 | 随便改；但更新时同样痛苦，独立包其实更省事 |
| 文本量小、作者活跃 | 把翻译好的 `Chinese/*.xml` 直接发给作者合并进原 mod（mod.io 那位翻译作者的建议：文本少且少更新 ⇒ 合并；文本多或持续更新 ⇒ 主 mod + 独立翻译 mod）K[K7] |
| 文本在 Lua/JSON 里硬编码 | 请作者改用 handle / MCM `Handles`；实在不行只能发"改过 Lua 的整包"，需作者明确许可，且每次更新重做 I[31][23] |
| 原 mod 自带 `Chinese` 目录但翻得差 | 仍用独立包：加载在其后即可逐条覆盖 I[31][4] |

## 5. 工具清单（按机器）

| 工具 | 平台 | 用途 | 现状 / 备注 |
|---|---|---|---|
| LSLib ConverterApp / Divine 1.20.4 | Windows（.NET 8） | 解包、打包、loca↔xml | 事实标准；macOS 上 Divine 因路径校验 bug 无法直接用（issue #220 未修）H[9][10] |
| BG3 Modder's Multitool 0.13.4 | Windows | 解/打包，`x.loca.xml` 自动转 `.loca` | GitHub 仓库已消失，迁到 GitLab；"source available" H[17][18] |
| 官方 Toolkit | Windows | mod.io 发布必经；Publish Local 可当打包器 | 门槛 32 GB 内存 / 160 GB 磁盘（docs/05） |
| `scripts/loca_convert.py` | Mac/任意（纯 Python） | loca↔xml、批量、校验 | 本仓库；未在真实文件上验证（V13） |
| `scripts/loca_sync.py` | Mac | 新旧英文 diff、缺失条目占位 | 本仓库 |
| `maclarian` / MacPak；`bg3-forge` | Mac（Rust）/ Python | 原生解包/打包/loca | 2026 年新项目、0–2★，未实测 H[28][29] |
| BG3 LocaHelper（LarinStudios Localization Helper） | Windows | 3DM 教程的主力：对照编辑、自动 loca、自动生成独立 mod | 源码 2024-01 被 DMCA 下架，Nexus 3136 仍在但已无维护；3DM 有 Juij 汉化版 3.3.1 H[21][22] K[K3][K4] |
| bg3-mod-ai-translator-zh / BG3ModTranslation / Icosa / BG3 Mod Translator | 见 §3 Step 4 | AI/机翻初稿 | 均为 2025–2026 新工具，质量需人工校对 H[35][36][37][38] |
| VS Code BG3 Mod Helper | Windows（需 LSLib.dll） | handle 生成、loca 转换 | 与 Mac 工作流不搭 H[44] |

## 6. 坑清单（汉化专用，补充 docs/04）

| 症状 | 原因 | 解决 |
|---|---|---|
| 中文完全不显示、仍是英文 | 目录名不是 `Chinese`；xml 没转 loca；游戏语言没切；汉化 pak 排在原 mod 之上被其自带的 Chinese 覆盖 | 逐项检查 §2.4/§2.5、加载顺序 |
| 某几条显示 "Not Found" | 改坏了 contentuid；原 mod 更新新增了 handle 而汉化未跟进；xml 里出现真实子元素导致条目丢失 | `loca_convert.py check`；重新 diff |
| 装了汉化后原 mod"消失"或版本错乱 | 汉化 pak 与原 mod 同名 / 复用了原 UUID | 新 UUID、新 Folder、新文件名 J[17] I[2] |
| 汉化 mod 在 BG3MM 出现在橙色 Overrides 区、Patch 7 后不生效 | 没有 meta.lsx 的 override 型 pak | 必须带 meta.lsx I[2][45] |
| 联机提示 mod 不匹配 | 只有一个人装了汉化 mod | 全员安装同一版本，顺序一致 I[43][27] |
| SE 配置界面还是英文 / 中文乱码 | Lua 硬编码；MCM 无 Handles；IMGUI 4K 字形问题 | 见 §2.6 |
| Multitool 打包后部分条目"被自己覆盖" | 多个 xml 被合并、同 handle 互相覆盖 | 一种语言只放一个 xml，或用 Divine/Toolkit 打包 K[K7] |
| 加载顺序改完又回滚 | Steam Cloud 同步 modsettings.lsx | 关闭该游戏云同步（docs/04 B3） |

## 7. 与本项目（自创职业 mod）的关系
- 反过来看，我们发布自己的 mod 时要让别人容易汉化/翻译：仓库内保留 `Localization/English/*.xml` 源文件、Nexus 权限写明允许翻译、changelog 列出新增/变更 handle（docs/08 §3.4 已定）。
- 本文的脚本（`loca_convert.py` + `loca_sync.py`）同时服务两个方向：翻译别人的 mod，和维护自己 mod 的 15 种语言。

## 8. 待验证（并入 docs/07）
- V13 `scripts/loca_convert.py` 产物与 LSLib 输出字节一致、游戏可读。
- V14 只带 English 目录的 mod 在简中客户端显示英文还是 "Not Found"（决定 V6 的最终答案）。
- V15 汉化 pak 排在原 mod 之后能否逐条覆盖其自带的 `Chinese` 目录；排在之前是否被覆盖。
- V16 `maclarian`/`bg3-forge` 在 Mac 上解/打包的 pak 能否被游戏加载（若能，Mac 可独立完成整条汉化流水线）。

## 9. 证据来源
- research/H-loca-format-and-tools.md：`.loca` 二进制布局与 XML 转义规则（LSLib 源码一手）、Divine 参数、Mac 替代工具、翻译工具现状、Multitool/LocaHelper 现状。
- research/I-translation-mod-semantics.md：回退池与 "Not Found"、逐条合并与整体替换、version 语义、meta.lsx/override、联机、SE/MCM/IMGUI。
- research/J-community-practice-policy.md：N 网 CHS 条目形态与命名、Nexus 提交规则与上传流程、Larian/mod.io 政策与主机、中文教程演进、术语资源、更新跟进。
- research/K-browser-direct-read.md：bg3.wiki Localization/Installing mods、mod.io 准则与翻译转换指南、3DM 两版教程、官方 Adding Localisation 原文；Nexus 被人机验证拦下未读。
