# I. 引擎本地化行为与独立翻译 mod 的技术语义（调研报告）

- 日期：2026-09-02
- 课题：给别人的 BG3 mod 做中文汉化——直接改原 mod 还是做独立汉化 mod？本篇只回答"引擎层面怎么读 loca / 独立翻译 pak 怎么被合并"这一层。
- 方法：bg3.wiki、Larian 论坛、GitHub（bg3se / lslib / MCM / BG3MM 源码与 issue）、日韩中社区教程直接抓取；nexusmods / docs.baldursgate3.game / larian.com / baldursgate3.game 全部 403，只能用搜索摘要（来源表标注）。未使用浏览器类工具。
- 标注约定：**已核实** = 直接抓到原文；**仅搜索摘要** = 只拿到搜索引擎摘要；**推断** = 由多条证据合成，未见直接陈述。

## 1. 结论摘要

1. **缺失 handle 不会显示裸 handle，也不会空白；两种结局：回退到另一池的文本，或显示 "Not Found"。** 引擎的 `TranslatedStringRepository` 带 `FallbackPool` / `VersionedFallbackPool`，查询顺序为当前池 → 版本回退池 → 回退池 [10][11]（已核实）；俄语正式版缺 2 万行时，引擎"用英文原文替代" [36]（已核实）。handle 在所有池都不存在时，UI 显示 "Not Found"（整文件覆盖漏掉新补丁文本、xml 改坏 handle、全局文本损坏等场景均报此现象 [35][42][51][21]，推断）。没有找到任何 BG3 显示 `h1587…` 裸 handle 的玩家报告；`ls::TranslatedStringRepository::s_HandleUnknown` 只是编辑器生成失败时写进 stats 的占位符 [20][37]。
2. **"mod 只带 English loca、客户端设中文 → 显示英文"是高置信推断，未找到一手明文。** 证据链：引擎有回退池 [10]、基础游戏对缺失行回退英文 [36]、日语社区把"只剩英文"归因于 Lua 硬编码而非 loca 缺失 [31]、Larian 论坛称语言包"叠在 English.pak 之上" [7]。建议在 Windows 机上用一个英文-only mod 做 5 分钟实测后再拍板。**结论：汉化不是"能不能玩"的必需品，而是体验问题。**
3. **多 pak 同语言 loca 按 handle 逐条合并，后加载者覆盖同 handle；同路径同名文件则整体替换。** 日语教程原话"翻訳は後から読んだ側が勝ちます"（后读取者胜）[31]（已核实）；Nexus App 开发文档："last loaded wins" [4]（已核实）；bg3.wiki："To be safe load it below the original mod" [1]（已核实）。同路径 `Localization/English/English.loca` 会整体顶替原文件，漏带原内容会"移除游戏里除已编辑外的所有字符串" [5]（已核实）。同一语言目录内还存在**文件名字母序**规则（文件名要排在语言名之后，用前缀 Z 调序）[41][42]（仅搜索摘要）。"放在原 mod 之下(below)" = modsettings `ModOrder` 里更靠后 = 更晚加载 = 更高优先级 [4][26]（已核实+推断）。
4. **version：翻译条目保持与原 mod 相同的 version 即可。** `.loca` 的 version 是 uint16，xml 缺省为 1 [22]（已核实）；引擎查表 key `RuntimeStringHandle` 的 `==` 与 hash **只比较 Handle、忽略 Version** [10]（已核实），所以 stats 里 `h…;1` 与 loca `version="1"` 不一致大概率不影响查找（推断）。官方文档用更高 version（示例 `version="2"`）覆盖原版文本 [37]（仅搜索摘要）；bg3.wiki 明确"do not edit version or the contentuid" [1]；日语翻译工具专门提供"把 version 对齐英文"的功能 [32]（已核实）。version 是否参与优先级裁决（`VersionedFallbackPool` 的语义）未核实。
5. **pak 内放 `.loca`，不要指望 `.xml`。** 所有社区流程（bg3.wiki、Larian 论坛、Murica、韩/中教程）都在打包前转成 `.loca` [1][5][30][33][35]（已核实）；Multitool 会在重打包时把 `.loca.xml` 自动转回 `.loca` [1]（已核实）；Toolkit 项目里用 xml、发布时转换 [37]（仅搜索摘要）。"手工 pak 里的 .xml 是否被游戏读取"没有直接证据，按**不生效**处理。
6. **独立翻译 pak 结构：自带 `Mods/<Folder>/meta.lsx` + `Localization/Chinese/<名字>.loca`，新 UUID。** bg3.wiki："we need to create our own Meta.lsx" [1]；只有"basegame override"可以没有 meta.lsx [2]（已核实）。Patch 7 之后社区一致认为无 meta 的 override 型 pak 大多失效 [45][49]（仅搜索摘要/二手），因此**不要做无 meta 的 override 汉化包**。Dependencies 可选：好处是游戏会先加载依赖、BG3MM 能按依赖排序并对缺失标红 [3][4][26]；坏处是原 mod 换 UUID/Version64 时会报缺依赖（推断）；bg3.wiki 建议"仍有问题时再加依赖" [1]。命名惯例：`Mods\<原名>_<语言>`、文件夹名与 meta `Folder` 一致 [39][2]；韩语教程保留原 loca 文件名、只把 `English` 目录改名 [34]。
7. **联机：官方要求所有玩家 mod 与版本完全一致 [43]（仅搜索摘要）；社区补充加载顺序也要一致 [45]。** 带 meta.lsx 的汉化 mod 会进入 mod 列表，只有一人装就会触发不一致（推断，基于 [43][27]）。**建议全员都装**：它只增加 `Localization/Chinese`，对英文客户端无副作用（推断）。无 meta 的 loca-only pak 是否参与校验未核实。
8. **Script Extender：`Ext.Loca.UpdateTranslatedString` 能在运行时替换任意 handle 文本，但只写内存池 [0]，每次会话都要重跑 [9][11]（已核实）。** v32 新增 `GetAllTranslatedStringKeys / GetTranslatedStringKey / UpdateTranslatedStringKey` [18]。SE 通过游戏文件读取器 `MakeFileReader(path, PathRootType::Data)` 读 `Mods/<Folder>/ScriptExtender/Lua/…` [12]（已核实），所以同路径文件理论上可被后加载 pak 遮蔽（推断）；但只有在 `LoadOrderedModules` 中、带 `ScriptExtender/Config.json` 且 FeatureFlags 含 "Lua" 的 mod 才会被 bootstrap [12]。MCM 蓝图任何面向用户的字符串都可加 `Handles`（NameHandle/DescriptionHandle/TooltipHandle/ChoicesHandles/EventButtonHandles），handle 找不到就回退到蓝图里的字面量 [23][24]（已核实）——原 mod 没写 Handles 的话，汉化只能靠覆盖 `MCM_blueprint.json`（推断）。IMGUI 中文：主线代码对 Chinese 用 `NotoSerifSC-Regular.otf` + `GetGlyphRangesChineseFull` [13]，Norbyte 在 #427 承诺 v19 起扩到全字集 [14]；#453 报告 4K 分辨率下中文乱码、1080p 正常，串内无官方结论 [16]。
9. **不走 loca 的文本：Lua 硬编码字符串、pak 内直写英文、贴图文字——独立翻译 mod 无法用 loca 覆盖。** 日语社区明文："Luaでメニューを描いているMOD…英語のまま残る" [31]（已核实）。性别变体 `Localization/<Lang>/Gender/Female/<lang>_to_F.xml`、`_to_X` [37]（仅搜索摘要）——引擎的 9 个文本池疑似对应说话者×听者性别组合（推断）。对话 `.lsj` 已弃用，对话文本通过 handle 走 loca [47]；RootTemplate `DisplayName` 是 `type="TranslatedString" handle= version=` 属性，同样走 loca [48]（仅搜索摘要）。

## 2. 证据细节

### 2.1 缺失 handle 的回退行为

- 引擎数据结构（bg3se 对游戏结构的逆向定义）[10]：`TextPool* TranslatedStrings[9]; TextPool* FallbackPool; TextPool* VersionedFallbackPool;`，每个 `TextPool` 是 `HashMap<RuntimeStringHandle, LSStringView> Texts`。
- SE 的 `GetTranslatedString`：先 `TranslatedStrings[0]->Texts.try_get(handle)`，未命中依次查 `VersionedFallbackPool`、`FallbackPool` [11]。这是引擎里存在"回退池"的直接证据；池的填充来源（是否含 mod 的 English 目录）源码里看不到。
- 基础游戏实证：DTF 报道俄语版缺 2 万行，本地化团队说明引擎"при пропуске строк… подставляет… из английской версии"（缺行时代入英文原版）[36]。
- "Not Found" 现象：Nexus 9213 指出整文件覆盖后新补丁文本会"register as Not Found" [42]；中文教程称 xml 改错会让说明文显示 "Not Found" [35]；日语站用户评论"説明文が「not fonud」になり" [32]；Steam 有"所有文本都显示 NOT FOUND"的求助串 [51]；bg3se #145 是一张对话显示 NOT FOUND 的截图（2023-11-04，patch 4 后）[21]。
- 反向证据（裸 handle）：BG3 相关检索（英/中/日/韩/俄）没有任何"看到 h 开头一串字符"的报告。DOS2 时代的裸 handle 经验不适用于 BG3 [背景知识—非本次检索]。
- 对 mod 的推断：若引擎把所有挂载 pak 的 `Localization/English/*.loca` 装入回退池，则英文-only mod 在中文客户端显示英文；若不装入，则显示 "Not Found"。倾向前者的理由：中日韩社区把"只剩英文"统一归因于 Lua 硬编码 [31]，而非 loca 缺失；且 [7] 描述语言包"layer on top of English.pak"。需实测。

### 2.2 多 pak 同语言 loca 的合并与覆盖

- 跨 pak 逐条覆盖：日语教程用独立日语 pak（自带 `Localization/Japanese`）放在加载顺序最底，并说明"このパックより下に別の日本語xml…があると、そっちに上書きされます"（下方有别的日语文件会被其覆盖）[31]。
- 加载顺序语义：Nexus App 文档 "Pak mods are loaded in order defined in… modsettings.lsx… last loaded wins" [4]；BG3MM 列表即 modsettings 顺序，1.0.9.x 起显示 override 类 pak [26]。
- 同路径整体替换：Larian 论坛"两 mod 法"——Mod0 放完整原版 `Localization/English/English.loca`，Mod1 放只含改动行的同名文件；作者警告漏掉 Mod0 会"removes every string from the game except…" [5]。这说明同路径文件是整体顶替而非逐条合并。
- 目录内字母序（仅搜索摘要）[41][42]：基础游戏文本覆盖需让 loca 文件名排在语言名之后（英文要以 F–Z 开头），通过增减前缀 Z 调整同目录内先后。是否跨 pak 也按字母序，未见明文；**稳妥做法是"加载顺序在原 mod 之后 + 文件名不同于原 mod 且字母序靠后"双保险**（推断）。
- bg3.wiki 原文 [1]："To be safe load it below the original mod in the load order"；"If you are still running into issues try adding the original mod as a Dependency"。搜索摘要另提到 BG3MM 不把本地化覆盖识别为 override（仅搜索摘要，直接抓取未复现该句）。
- 基础游戏语言包分层：Larian 论坛老帖称语言 pak 叠在 English.pak 上以保持联机兼容 [7]。

### 2.3 `version` 属性语义

- 二进制格式：LSLib `LocaEntry { byte[64] Key; UInt16 Version; UInt32 Length; }`，xml 读取时 `version` 缺省为 1 [22]。
- 引擎 key：`RuntimeStringHandle { FixedString Handle; uint16_t Version; }`，`operator==` 为 `Handle == fs.Handle`，hash 为 `HashMapHash(v.Handle)` [10]——同 handle 不同 version 在 HashMap 里是同一个 key。
- 官方文档（仅搜索摘要）[37]：示例 `contentuid="h1587638a…" version="2"` 配文 "This line is now overridden"，另有 `version="3"` 示例；含义是"用原版 handle + 更高 version 覆盖原版文本"。
- 社区做法：bg3.wiki 禁改 version/contentuid [1]；日语工具"verをENに合わせる"保持与英文一致 [32]；stats/RootTemplate 引用格式 `<handle>;<version>` [48]。
- 结论：翻译条目复制原 mod 的 version；不要为了"压过原 mod"去抬 version——覆盖靠加载顺序即可（推断）。`VersionedFallbackPool` 的具体裁决规则未核实（见 §3）。

### 2.4 游戏读 `.xml` 还是只读 `.loca`

- bg3.wiki [1]："If .loca you will want to convert it to xml via lslib"；用 Multitool 解包可保留 `.loca.xml`，"will convert back to .loca on repacking"。
- Larian 论坛 [5]、Murica [30]、韩语教程 [33]（"ExportTool에서 .loca파일로 변경하고 .pak로 다시 압축"）、中文教程 [35]（LSLib ConverterApp 转 loca）均在打包前转换。
- 官方 Toolkit（仅搜索摘要）[37]：正式版本地化是二进制 `.loca`，mod 项目里"creating an XML file in your mod folder"——xml 是 Toolkit 项目源格式，发布/打包时转换（推断）。
- 未找到"手工 pak 里直接放 .xml 也能生效"的报告。

### 2.5 独立翻译 pak 的结构

- meta.lsx：bg3.wiki Meta.lsx 页——"Most pak mods need a meta.lsx"，例外仅"classed as a basegame override"（BG3MM 里橙色 Overrides 区）[2]；UUID 必须唯一"unless you want to override another mod" [2]；Folder 须与 `Mods/` 下文件夹同名 [2]。bg3.wiki Localization："we need to create our own Meta.lsx" [1]。
- 结构范例：Nexus 7288 把 meta.lsx 放到 `Mods\ModName_YourLanguage` [39]（仅搜索摘要）；韩语教程只保留 `Localization`、`Mods` 两个文件夹和 meta.lsx，`English`→`Korean`，loca 文件名不变 [34]；Nexus 3023 称独立翻译 mod 在原 mod 更新且未新增字符串时无需更新 [40]（仅搜索摘要）。
- Override pak（无 meta）：BG3MM 1.0.9.0 起显示"paks that only override files and have no metadata" [26]；Nexus App 文档：未列入 modsettings 的 pak 被游戏视为禁用，但"may still override those files" [4]。Patch 7 后：bg3.community 称 Override 类型"discontinued with Patch 7… no longer work" [45]（仅搜索摘要）；bg3modmanager.net（非官方站）同样称 override-style 已弃用 [49]。没有 Larian 官方原文（403）。
- Dependencies：bg3.wiki 说明其用途与写法（复制原 mod meta 的 Folder/Name/UUID/Version64，MD5 留空）[3]；Nexus App 文档：游戏"will try to load before the mod itself" [4]；BG3MM 对缺失依赖标红、可按依赖排序 [26][49]。
- 联机相关结构影响见 §2.6。

### 2.6 多人联机

- 官方 FAQ（仅搜索摘要）[43]：多人游戏需"exact same mods installed… same version"。
- 社区 [45]（仅搜索摘要）：还要求相同加载顺序，包括未激活区与 loose file mod。
- 实际报错：BG3MM #364（2024-09-11）同 mod 同版本同顺序仍报 mismatch，需逐个在游戏内重新勾选 [27]；#374 归因于 modsettings.lsx 缩进格式差异 [28]；Larian 论坛 "Wrong Mod Version" 案例由损坏文件引起，建议 Data 目录只保留 Localization [8]。
- 推断：带 meta.lsx 的汉化 mod 是独立列表项，一人装、其他人不装即为不一致；全员安装最省事，且对英文客户端无影响（只多一个 Chinese 目录）。无 meta 的 loca-only pak 是否被校验：未核实。

### 2.7 Script Extender

- `Ext.Loca` API [9][19]：`GetTranslatedString(handle, fallback?) → string`、`UpdateTranslatedString(handle, text) → boolean`，文档称"Updates/overrides translated text for a handle at runtime"。v32 新增三个 key 函数 [18]。
- 实现 [11]：Update 直接 `TranslatedStrings[0]->Texts.set(handle, …)`，无任何持久化——存档不保存，须在每次会话（如 `SessionLoaded`/`StatsLoaded`）重放（推断）。
- Lua 加载 [12]：路径 `Mods/<Directory>/ScriptExtender/Lua/<file>`，通过 `GetStaticSymbols().MakeFileReader(path)`（默认 `PathRootType::Data`）读取，即走游戏自身文件系统；只对 `LoadOrderedModules` 中带 Config.json 且 FeatureFlags 含 "Lua" 的 mod 执行 bootstrap，无"不在加载顺序也能生效"的分支。因此用独立 pak 同路径覆盖 Lua 文件在理论上可行但脆弱（推断）；日语社区实际做法是接受 Lua UI 留英文 [31]。
- MCM [23][24]：`Handles` 对象可挂在顶层、Tab、Section、Setting 上；"If the handle is not found, the usual string will be used"；handle 需列在 mod 自己的 loca 中。MCM 自身只随附 English 与 BrazilianPortuguese 本地化 [25]。
- IMGUI 字体 [13]：Chinese → `Public/Game/GUI/Assets/Fonts/NotoSerifSC-Regular.otf` + `GetGlyphRangesChineseFull()`；字体经 `LoadExternalFile(path, PathRootType::Data)` 从游戏 pak 读取；`LoadFont(name, path, size)` 存在但不暴露字形范围。Issue 时间线：#406（2024-06-09）提出按语言选字形范围 [17]；#422（2024-07-16）日文误用 KR 字体 [15]；#427（2024-07-31）中文只有 2500 字，Norbyte 答复 v19 扩全 [14]；#453（2024-09-19）4K 下中文乱码、1080p 正常，串内无维护者结论 [16]。

### 2.8 其它文本载体

- Lua 硬编码 / pak 内直写英文：日语教程点名 Trials of Tav Reloaded（Lua UI）与 Automatic Inventory Manager（pak 内英文直写）在装了日语包后仍"英語のまま残る" [31]。独立翻译 mod 无法通过 loca 处理；只能同路径覆盖 Lua/JSON（脆弱）或请原作者改用 handle。
- 贴图文字：属于 Public/…/Assets 纹理，与 loca 无关 [背景知识—非本次检索]。
- 性别变体（仅搜索摘要）[37]：`Localization/<Lang>/Gender/Female/<lang>_to_F.xml` 供女性说话者对女性听者，`_to_X` 对中性听者；翻译 mod 可按同样目录结构提供（推断）。引擎 `TranslatedStrings[9]` 疑似 3×3 性别组合池（推断）。
- 对话 `.lsj`（仅搜索摘要）[47]：bg3.community 明确 `.lsj` 已弃用、"don't do anything in the game"，对话文本由 DialogsBinary 里的 handle 引用 → 走 loca，可被独立翻译覆盖。
- RootTemplate `DisplayName`（仅搜索摘要）[48]：`<attribute id="DisplayName" type="TranslatedString" handle="h…" version="2"/>` → 走 loca。
- stats 占位符：`ls::TranslatedStringRepository::s_HandleUnknown` 是编辑器生成 loca 失败时写入的占位 [20][37]，不是运行时显示值。

## 3. 信息缺口 / 未核实

1. **英文-only mod 在中文客户端到底显示英文还是 "Not Found"**：无一手明文，仅结构性推断。建议 Windows 实测（装一个只有 English 目录的 mod，语言切中文，看物品名）。
2. **跨 pak 时"加载顺序"与"文件名字母序"谁优先**：8604/9213 的字母序规则只拿到搜索摘要，且描述的是对基础游戏文本的覆盖。
3. **`version` 是否参与裁决**（`VersionedFallbackPool` 语义、同 handle 不同 version 谁赢）：源码只见查询顺序，未见写入/裁决逻辑。
4. **Patch 7 后无 meta.lsx 的 loca-only override pak 是否仍被加载**：只有社区二手陈述，Larian 原文 403。
5. **联机校验是否覆盖无 meta 的 pak**、以及游戏比对的是 UUID/Version64 还是 MD5：未核实。
6. **手工 pak 内 `.xml` 是否被读取**：无实验报告。
7. Nexus 文章 643 / mod 7288 / 8604 / 9213、docs.baldursgate3.game、Larian FAQ、baldursgate3.game 均未拿到原文；wiki.bg3.community 全站只返回标题（SPA 渲染）；web.archive.org 被工具拦截。

## 4. 来源表

| # | 标题 | URL | 一手/二手 | 抓取状态 | 日期 |
|---|---|---|---|---|---|
| 1 | bg3.wiki Modding:Localization | https://bg3.wiki/wiki/Modding:Localization | 一手(社区wiki) | 抓取成功 | — |
| 2 | bg3.wiki Modding:Meta.lsx | https://bg3.wiki/wiki/Modding:Meta.lsx | 一手(社区wiki) | 抓取成功 | — |
| 3 | bg3.wiki Modding:Dependencies | https://bg3.wiki/wiki/Modding:Dependencies | 一手(社区wiki) | 抓取成功 | — |
| 4 | Nexus Mods App 开发文档：BaldursGate3 | https://nexus-mods.github.io/NexusMods.App/developers/games/0003-BaldursGate3/ | 二手 | 抓取成功 | — |
| 5 | Larian 论坛 Simple mod to fix English text [Solved] | https://forums.larian.com/ubbthreads.php?ubb=showflat&Number=949981 | 一手(玩家实验) | 抓取成功 | — |
| 6 | Larian 论坛 Localization mod Balder's Gate 3 | https://forums.larian.com/ubbthreads.php?ubb=showflat&Number=955200 | 一手 | 抓取成功 | — |
| 7 | Larian 论坛 Modding Localization Help | https://forums.larian.com/ubbthreads.php?ubb=showflat&Number=870277 | 一手 | 抓取成功 | — |
| 8 | Larian 论坛 Wrong Mod Version while no mods | https://forums.larian.com/ubbthreads.php?ubb=showflat&Number=799210 | 一手 | 抓取成功 | — |
| 9 | bg3se Docs/API.md | https://github.com/Norbyte/bg3se/blob/main/Docs/API.md | 一手 | 抓取成功 | — |
| 10 | bg3se TranslatedString.h | https://github.com/Norbyte/bg3se/blob/main/BG3Extender/GameDefinitions/TranslatedString.h | 一手(源码) | 抓取成功 | — |
| 11 | bg3se Lua/Libs/Localization.inl | https://github.com/Norbyte/bg3se/blob/main/BG3Extender/Lua/Libs/Localization.inl | 一手(源码) | 抓取成功 | — |
| 12 | bg3se Extender/Shared/ExtensionState.cpp | https://github.com/Norbyte/bg3se/blob/main/BG3Extender/Extender/Shared/ExtensionState.cpp | 一手(源码) | 抓取成功 | — |
| 13 | bg3se Client/IMGUI/IMGUI.cpp | https://github.com/Norbyte/bg3se/blob/main/BG3Extender/Extender/Client/IMGUI/IMGUI.cpp | 一手(源码) | 抓取成功 | — |
| 14 | bg3se issue #427 Missing Chinese Characters | https://github.com/Norbyte/bg3se/issues/427 | 一手 | 抓取成功(gh) | 2024-07-31 |
| 15 | bg3se issue #422 Japanese font path | https://github.com/Norbyte/bg3se/issues/422 | 一手 | 抓取成功 | 2024-07-16 |
| 16 | bg3se issue #453 Chinese font abnormal | https://github.com/Norbyte/bg3se/issues/453 | 一手 | 抓取成功(gh) | 2024-09-19 |
| 17 | bg3se issue #406 IMGUI Localization | https://github.com/Norbyte/bg3se/issues/406 | 一手 | 抓取成功 | 2024-06-09 |
| 18 | bg3se Docs/ReleaseNotes.md (v32) | https://github.com/Norbyte/bg3se/blob/main/Docs/ReleaseNotes.md | 一手 | 抓取成功(gh) | — |
| 19 | bg3se IdeHelpers/ExtIdeHelpers.lua | https://github.com/Norbyte/bg3se/blob/main/BG3Extender/IdeHelpers/ExtIdeHelpers.lua | 一手 | 抓取成功(gh) | — |
| 20 | bg3se GlobalFixedStrings.inl (s_HandleUnknown) | https://github.com/Norbyte/bg3se/blob/main/BG3Extender/GameDefinitions/GlobalFixedStrings.inl | 一手 | 抓取成功(gh) | — |
| 21 | bg3se issue #145 dialogue NOT FOUND | https://github.com/Norbyte/bg3se/issues/145 | 一手 | 抓取成功 | 2023-11-04 |
| 22 | LSLib LS/Localization.cs | https://github.com/Norbyte/lslib/blob/master/LSLib/LS/Localization.cs | 一手(源码) | 抓取成功 | — |
| 23 | BG3-MCM wiki.md | https://github.com/AtilioA/BG3-MCM/blob/main/wiki.md | 一手 | 抓取成功 | — |
| 24 | BG3-MCM .vscode/schema.json | https://github.com/AtilioA/BG3-MCM/blob/main/.vscode/schema.json | 一手 | 抓取成功 | — |
| 25 | BG3-MCM 仓库目录 (Localization 语言) | https://github.com/AtilioA/BG3-MCM | 一手 | 抓取成功(gh) | — |
| 26 | BG3ModManager Changelog | https://github.com/LaughingLeader/BG3ModManager/wiki/Changelog | 一手 | 抓取成功 | — |
| 27 | BG3ModManager issue #364 Multiplayer mod mismatch | https://github.com/LaughingLeader/BG3ModManager/issues/364 | 一手 | 抓取成功 | 2024-09-11 |
| 28 | BG3ModManager issue #374 Modded multiplayer | https://github.com/LaughingLeader/BG3ModManager/issues/374 | 一手 | 抓取成功 | — |
| 29 | BG3ModManager issue #418（与 override 无关，被 [49] 误引） | https://github.com/LaughingLeader/BG3ModManager/issues/418 | 一手 | 抓取成功 | 2025-04-23 |
| 30 | ancestral/Murica README | https://github.com/ancestral/Murica | 一手 | 抓取成功 | — |
| 31 | Nettoge 【BG3】MODの日本語化 | https://nettoge.com/baldurs-gate-3-mod-japanese-localization/ | 一手(社区教程) | 抓取成功 | — |
| 32 | Nettoge MOD日本語化・翻訳作業補助ツール | https://nettoge.com/%E3%80%90baldurs-gate-3%E3%80%91mod%E6%97%A5%E6%9C%AC%E8%AA%9E%E5%8C%96%E3%83%BB%E7%BF%BB%E8%A8%B3%E4%BD%9C%E6%A5%AD%E8%A3%9C%E5%8A%A9%E3%83%84%E3%83%BC%E3%83%AB%E4%BD%9C%E3%81%A3%E3%81%9F/ | 一手 | 抓取成功 | — |
| 33 | dcinside 모드 한글화 하는법 | https://gall.dcinside.com/mgallery/board/view/?id=bg3&no=219875 | 一手(社区教程) | 抓取成功 | — |
| 34 | dcinside 한글화 모드 만드는 방법 | https://gall.dcinside.com/mgallery/board/view/?id=bg3&no=491643 | 一手(社区教程) | 抓取成功 | — |
| 35 | GameMale 非常简单的MOD汉化过程教学 | https://www.gamemale.com/thread-119405-1-1.html | 一手(社区教程) | 抓取成功 | — |
| 36 | DTF 俄语版缺 2 万行 | https://dtf.ru/games/2015508-v-russkoi-versii-baldurs-gate-3-ne-hvataet-20-000-strok | 二手(媒体转述官方) | 抓取成功 | — |
| 37 | Larian 官方文档 Adding Localisation | https://docs.baldursgate3.game/index.php?title=Adding_Localisation | 一手(官方) | 搜索摘要(403) | — |
| 38 | Nexus 文章 643 How to Translate these Mods | https://www.nexusmods.com/baldursgate3/articles/643 | 一手 | 搜索摘要(403) | — |
| 39 | Nexus mod 7288 How to Make Translation Mod (Advance) | https://www.nexusmods.com/baldursgate3/mods/7288 | 一手 | 搜索摘要(403) | — |
| 40 | Nexus mod 3023 How to Make Translation Mod | https://www.nexusmods.com/baldursgate3/mods/3023 | 一手 | 搜索摘要 | — |
| 41 | Nexus mod 8604 Game Text Compatibility Base Files | https://www.nexusmods.com/baldursgate3/mods/8604 | 一手 | 搜索摘要 | — |
| 42 | Nexus mod 9213 Nautiloid Nonsense（文本覆盖兼容指南） | https://www.nexusmods.com/baldursgate3/mods/9213 | 一手 | 搜索摘要 | — |
| 43 | Larian Support FAQ Official Mod Support | https://larian.com/support/faqs/official-mod-support_113 | 一手(官方) | 搜索摘要(403) | — |
| 44 | baldursgate3.game Patch 7 Now Live / Community Update 29 | https://baldursgate3.game/news/patch-7-now-live_121 | 一手(官方) | 搜索摘要(403) | 2024-09 |
| 45 | wiki.bg3.community General Load Order Guide | https://wiki.bg3.community/en/Tutorials/Mod-Use/general-load-order | 一手(社区wiki) | 搜索摘要(页面仅返回标题) | — |
| 46 | wiki.bg3.community Patch 7 Troubleshooting | https://wiki.bg3.community/en/Tutorials/patch7-troubleshooting | 一手(社区wiki) | 搜索摘要(仅标题) | — |
| 47 | wiki.bg3.community Dialogue Files Tutorial / New Voice Lines | https://wiki.bg3.community/en/Tutorials/dialogue-files-tutorial | 一手(社区wiki) | 搜索摘要 | — |
| 48 | bg3.wiki Modding:Items / bg3.community Basic-Class-Creation（DisplayName 示例） | https://bg3.wiki/wiki/Modding:Items | 一手(社区wiki) | 搜索摘要 | — |
| 49 | bg3modmanager.net Larian In-Game Mod Manager Guide | https://bg3modmanager.net/larian-in-game-mod-manager-guide/ | 二手(非官方 SEO 站，引证有误) | 抓取成功 | 2026 |
| 50 | Nexus mod 23274 BG3 Mod Translator | https://www.nexusmods.com/baldursgate3/mods/23274 | 一手 | 搜索摘要 | — |
| 51 | Steam 讨论 All text reading NOT FOUND | https://steamcommunity.com/app/1086940/discussions/3/4342103279870939033/ | 一手 | 搜索摘要(抓取仅得页头) | — |
| 52 | logu.jp 日本語化MODインストール手順 | https://logu.jp/bg3-mod-japanese-localization/ | 一手(社区教程) | 抓取成功(无相关内容) | — |
| 53 | Nexus 论坛 Localization mod Balder's Gate 3 | https://forums.nexusmods.com/topic/13505738-localization-mod-balders-gate-3/ | 一手 | 失败(403) | — |
| 54 | bg3.wiki Multiplayer | https://bg3.wiki/wiki/Multiplayer | 一手 | 抓取成功(无 mod 内容) | — |
| 55 | bg3.wiki Modding:Load_order / Modding:Pak_files | https://bg3.wiki/wiki/Modding:Load_order | — | 失败(404，页面不存在) | — |
| 56 | web.archive.org（docs/nexus/baldursgate3.game 存档） | https://web.archive.org/ | — | 失败(工具拦截) | — |

## 5. 抓取统计

- WebFetch 约 74 次：成功约 45 次；403 共 12 次（nexusmods ×3、docs.baldursgate3.game ×1、larian.com ×1、baldursgate3.game ×1、forums.nexusmods ×1、rpghq ×1、wiki.bg3.community 源码视图 ×2、gall.dcinside 首跳 ×2 后重试成功）；404 共 5 次（bg3.wiki 两个不存在页、bg3se IMGUI.md ×2、Multitool 仓库）；web.archive.org 被工具拒绝 4 次；wiki.bg3.community / bg3.community 正常路径 7 次均只返回标题（SPA）；Steam 讨论页 3 次只返回页头。
- WebSearch 约 53 次（英/中/日/韩/俄）。
- gh CLI（GitHub API/代码搜索/issue 评论）约 17 次，全部成功。
- 未使用任何浏览器类工具。
