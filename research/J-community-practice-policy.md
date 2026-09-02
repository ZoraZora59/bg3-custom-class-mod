# J. 社区惯例、平台政策与中文社区做法（BG3 mod 汉化：改原 mod vs 独立汉化 mod）

调研日期：2026-09-02。抓取约束：nexusmods.com / mod.io / docs.baldursgate3.game / baldursgate3.game / larian.com（主域）均 403 或只返回标题，相关结论依赖搜索摘要；forums.larian.com、help.nexusmods.com、bg3.wiki、3DM、贴吧、GameMale、Steam 社区可直接抓取。标注含义：**已核实**＝抓到原文；**仅搜索摘要**＝只见到搜索引擎摘要；**推断**＝由多条证据综合得出；`[背景知识—非本次检索]`＝先验知识。

## 1. 结论摘要

1. **Nexus 上中文汉化 mod 的主流形态是"只含本地化文件的独立补丁"，要求玩家另装原 mod、并把汉化放在原 mod 之下/之后加载。** 抽样到的描述明确写着"仅含翻译文件、原 mod 需另行下载、需加载于原 mod 之下"[9]、"语言包，需与原 mod 一起使用"[8]、"汉化包，需要原 mod"[3]、"需原 mod 才能运行"[12]、"独立汉化 mod"[10]。贴吧求助帖楼主最初上传"整合包"，学会后改为"仅含汉化的独立补丁"并隐藏了一体包[48]。——仅搜索摘要（Nexus 页面）+ 已核实（贴吧）。
2. **任务指定的 7 个样本页面（15477/16818/15581/12935/14301/13131/13838）都能确认存在且是 CHS/CHT 版本**，但除 Mystic 系列（"汉化包，需要原 mod，杨杨人工翻译"，版本号 4.2.0.1 与原版同步）外，其余页面的描述正文搜索引擎未收录，**无法逐一判定是补丁还是整合重打包**[1][2][3][4][5][6][7]。——仅搜索摘要。
3. **命名惯例**：标题后缀 `CHS` / `CH` / `_CHT` / `(CHT)`，或 `XXX - CHS and CHT Translation Pack(s)`、`XXX - Chinese Translation`、`XXX - Mandarin - Simplified Chinese Translation`、`XXX Simple Chinese translation`；版本号常直接沿用原 mod 版本（"翻译版本号与主 mod 同步"[11]；俄译标题直接带 `(4.2.0.2)`[13]）。Nexus 语言下拉里中文标签叫 **"Mandarin"**，社区 2025 年还在提议改名为 "Chinese"[26]。——仅搜索摘要。
4. **Nexus 官方规则**（已核实[21]）：翻译"只能作为与原文件配合使用的附加文件"提交，并须链接原文件；含原 mod 内容而未获许可的翻译"可被处理，原作者要求即删除"；"仅署名不能替代明确许可"。上传时需选择"Translation of a file/mod that already exists"并选语言，且只允许翻译 Nexus 上已有的 mod[22]（仅搜索摘要）。
5. **Nexus 的 Permissions 区块没有单独的 "Translation permission" 下拉项**：标准项为 Upload / Modification / Conversion / Asset use（含收费与 DP 两个子项），措辞分三档："You are allowed…" / "You must get permission from me before…" / "You are not allowed… under any circumstances"，作者可另写自由文本 "Permission notes"（翻译政策通常写在这里）[24]。——仅搜索摘要 + `[背景知识—非本次检索]`；社区共识是"一律先问作者，作者失联也不能自我授权"[25]（已核实）。
6. **mod.io（Larian 官方渠道）**：Larian 的 Guidelines & FAQ 要求在扩展、翻译或重制他人 mod 前必须取得许可[27]（已核实）；Modding Terms 要求 mod 的每个元素"要么原创、要么已获必要许可"[33]（仅搜索摘要）。mod.io 没有专门的翻译分类，用 `translation` 标签 + 语言标签（列表里有 "Chinese (Simplified)"）提高可发现性[27][37]。
7. **主机可用性**：mod 上主机需经 Larian 额外内部测试与审核；第三方（非 Toolkit）mod "仍是一个选项"，但 Community Update #27 表明第三方 mod 基本不具备跨平台/主机支持，游戏内浏览器虽能识别却无内置更新检查[27][28]（已核实）。mod.io 提供官方《Translation MOD conversion guide》把非 mod.io 翻译 mod 转成 mod.io 翻译 mod[35]（仅搜索摘要，内容未抓到）。是否必须经 Toolkit 上传：Larian 论坛回复称 mod 需通过 Toolkit 提交至 mod.io[30]，Steam 摘要亦称"唯一途径是官方 Toolkit"[32]，但 Guidelines 又说第三方 mod 仍可选——**判定为：Toolkit 是官方/主机通道，网页直传第三方 pak 是否开放未核实**（推断）。
8. **中文社区教程分两派**：早期（2023-09/10）GameMale、3DM 第一版教程教"解包原 pak → 改 Localization → 重新打包"[49][44]；2023-11 起 3DM 第二版教程与贴吧回复转向"用 BG3 LocaHelper 生成只含 Localization + meta 的独立汉化 mod"[43][48]（已核实）。Nexus 上 "Mod Translation Tutorial for Chinese"（Null993，2023-10-08）与英文教程 3023/7288 同样教独立翻译 mod[16][17][18]（仅搜索摘要）。
9. **工具链**：LSLib/ExportTool（fuyunai13 汉化版 V1.18.7）解包/loca↔xml/打包；BG3 LocaHelper（Juij 编译汉化版 v3.3.1）"导入 pak → 生成新翻译 mod"、标色进度、机器翻译；Multitool 可自动 xml→loca；2025 年出现基于 AI 的"全自动 mod 汉化工具"[43][44][45][46][47][59]（已核实/部分）。
10. **常见坑**：简中目录名必须是 `Localization/Chinese`（官方 Chinese.pak 内即此名）[44][53]；loca/xml 互转要改后缀[43]；只能改 `><` 之间文本，动到 contentuid/version 会显示 "Not Found"[49][39]；汉化 mod 与原 mod 同名会生成同名 pak 导致崩溃[17]；需要 meta.lsx（可用示例改）[17][39]。——已核实。
11. **发布渠道**：N 网（主渠道，大量 CHS/CHT 条目）、3DM 论坛"正式版MOD/补丁/修改"分区、3DM Mod 站、游侠"汉化补丁合集"、贴吧、B 站（视频与"官方中文 mod 整理"动态）；mod.io 上的中文条目很少[47][50][51][52][37]。——仅搜索摘要。
12. **术语一致性**：未找到中文社区维护的 BG3 mod 汉化术语表；可用参考为 VG 百科（与"龙与地下城 5E 翻译馆"联合出品的法术大全）[54]、B 站 BWIKI（wiki.biligame.com/bg3）[55]；Steam 指南演示了解包官方 `Chinese.pak` 获取官方简中文本[53]；mod.io 官方指南《Using Origin Localisation》建议直接复用原版本地化 handle 以减少翻译工作[36]。——仅搜索摘要/已核实（[53]）。
13. **原 mod 更新后的跟进**：翻译者把版本号写进标题或与原 mod 同步；LocaHelper 会把新增文本标蓝以做增量翻译[43]；Nexus 教程指出"原 mod 未新增字符串则翻译 mod 无需更新"[17]；MO2 插件 LWizard 能把翻译 mod 标为 "Outdated"[19]；过时表现为新增文本显示英文或 "NOT FOUND"/裸 handle[15][20][49]。——已核实/仅搜索摘要混合。

## 2. 证据细节

### 2.1 Nexus 上中文汉化 mod 的结构

| 页面 | 标题（搜索摘要） | 能确认的结构信息 |
|---|---|---|
| mods/15477 [1] | Artificer class and all subclassesCHS | 摘要仅称"简中版，翻译更准确可读"；未见"需原 mod"字样，**补丁/整合待定** |
| mods/16818 [2] | Blood Hunter CH | 仅标题；另有 2909 "Blood Hunter Chinese"、15377/15378 "…CHS" 同题多版 [60] |
| mods/15581 [3] | Mystic Class and Mystic Expansion CHS | "秘术师及扩展包的汉化包，**需要原 mod**，杨杨人工翻译"；2025-04 更新 |
| mods/14301 [4] | Mystic Class CHS and Mystic Expansions CHS | 版本 4.2.0.1（与原 mod 版本号一致） |
| mods/12935 [5] | Mystic Class expansion CHS | 文件已归档（archived） |
| mods/13131 [6] | 5e Way of the Astral Self - Monk Subclass CHS | 仅标题；同一原 mod 另有 PTBR 版 15303 |
| mods/13838 [7] | Death Knight Class - Champion of the Lich King_CHT | 仅标题；同原 mod 另有 KOR/ES/FR/ITA/PTBR/RU 版，均为独立页面 |

其他抽样（仅搜索摘要）：
- Cleric Subclasses (CHT) [9]："只包含翻译文件，原 mod 需另行下载，**本 mod 需加载于原 mod 之下**；依赖 5e Spells 或其中文版。" ——这是抓到的最明确的加载顺序表述。
- Alternate Monk - CHS and CHT Translation Packs [8]："Translation of MOD …，语言包，需与原 mod 一起使用，支持繁/简。"
- Dragon Ball Warrior (DBZ)-Chinese translation [12]："需原 mod 才能正常运行。"
- BG3 Community Library CH Version [10]："独立的中文翻译 mod。"
- Many More Monsters_CHT(with CHS) [11]："翻译版本号与主 mod 同步；新增文本先机翻待校。"
- Chinese Localization pack beautification for hotfix 10 [14]：v1.51 "更新对 hotfix 10 的兼容，无新内容"——原版汉化美化包按游戏热修版本号标注。
- 贴吧求助帖 [48]（已核实）：楼主想汉化 N 网两个 mod，"不知道如何把只含语言文件的汉化打包成补丁"；回复"汉化只需要改 mod 名字的 loca 文件"、推荐 BG3LocaHelper "可以直接制作完整的汉化包，仅有汉化"；楼主 9 楼称已学会做独立补丁，隐藏原一体包。→ 说明中文社区也存在"整合包"做法，但被视为过渡形态。
- 命名与语言标签：Nexus 上传表单的语言下拉把中文标为 "Mandarin"[22][26]；BG3 板块存在 "…- Mandarin - Simplified Chinese Translation" 这类标题[26]。
- bg3.wiki Modding:Localization [39]（已核实）：翻译 mod 应"加载在原 mod 下方"，"可考虑把原 mod 加为依赖（meta.lsx Dependencies）"。

### 2.2 Nexus 的翻译机制与权限

- **File Submission Guidelines**（help.nexusmods.com，已核实[21]，"Usage and Accreditation" 小节）：翻译应仅作为与原文件协同运作的附加文件提交；须在描述中链接原文件；含原 mod 内容而未获许可的翻译可被处理并按原作者请求移除；仅署名不足以替代明确许可。
- **上传流程**（Nexus 新闻 12285，仅搜索摘要[22]）：上传第 2 步顶部需选择 "Normal file/mod" 或 "Translation of a file/mod that already exists"，随后选语言（无则选 "Other" 并写在文件名里）；Nexus 只允许翻译站内已有 mod；此机制用于把翻译从常规 mod 列表中分离并可按语言过滤。`[背景知识—非本次检索]`：被关联的原 mod 页面会出现 "Translations" 折叠区块，列出各语言翻译及作者。
- **Permissions 档位**（wiki.nexusmods.com 403，仅搜索摘要[24]）：标准下拉项 Upload permission / Modification permission / Conversion permission / Asset use permission（及"用于收费 mod""获取 DP"两个子项），示例措辞 "You are not allowed to upload this file to other sites under any circumstances"、"You must get permission from me before you are allowed to modify my files…"；可勾选"忽略下拉、仅用自定义 Permission notes"。**未搜到任何名为 "Translation permission" 的标准条目**——翻译一般落在 Modification permission 或 Permission notes 自由文本里（推断）。
- **社区实践**（Steam 讨论，已核实[25]）："一律先问作者"；描述里写明原 mod 链接、作者、"已获许可"；作者失联/被封也不能自行授权，可去论坛征求或在原页面上传；否则可能被举报为"盗用 mod"影响信誉。Nexus 论坛两个权限讨论帖均 403[23]。
- Nexus 英文教程 7288 摘要[18]："翻译作者应提前与原作者沟通……99% 的 modder 都不介意被翻译。"

### 2.3 mod.io（Larian 官方渠道）

- **许可**：Larian 论坛《Modding: Guidelines & FAQ》[27]（已核实）：未获许可不得扩展、翻译或重制既有 mod（原文措辞是关于署名的反向表述，核心是先取得许可）。《Larian BG3 Modding Terms》PDF（403，仅搜索摘要[33]）：mod 的任何元素须为原创或已获必要许可，上传者对内容负责。
- **标签**：Guidelines 明确 mod.io 上"没有专门的翻译分类"，建议用 `translation` 标签 + 支持语言标签[27]；mod.io 标签筛选有 "Languages" 组，含 "Chinese (Simplified)"[37]。mod.io 上已有翻译类条目示例：Translation Supplement JP、Fixed Japanese、Fixed Russian translation[37]。
- **主机**：Guidelines：mod 不必须由 Toolkit 制作，第三方 mod 也可获得主机支持，但需通过 Larian 额外内部测试与审核；含 .exe/.dll、成人/暴力内容等类型被排除[27]。Community Update #27（论坛打印版，已核实[28]）：官方通道 mod 经 mod.io 审核后获得跨平台支持与更新检查；第三方 mod 为本地打包，"游戏浏览器仍会识别"但无内置更新检查，且不便利跨平台，基本无法上主机；主机 mod 两层审核（PC 端稳定性与 ToS 检查 → 额外审核确定跨平台）。Larian 支持 FAQ 摘要[32]：第三方 mod = 非 Toolkit 制作，Larian 无法管理/修复；主机玩家须确认所装 mod "主机可用"。
- **上传方式**：Larian 论坛回复"mod 需通过 BG3 Toolkit 提交至 mod.io"，并给出官方本地化指南链接 `baldursgate3.game/mods#/r/adding-localisation`[29][30]（已核实）；Steam 摘要称"唯一上传方式是官方 Toolkit"[32]；与 Guidelines "第三方 mod 仍是选项" 存在张力。mod.io 官方《Translation MOD conversion guide》"帮助把现有非 mod.io 翻译 mod 转为 mod.io 翻译 mod"[35]——暗示翻译 mod 走官方通道需用 Toolkit 重新组织（推断）。mod.io 指南页本身与 support.mod.io 均不可抓[34][38]。
- **对翻译 mod 的具体做法**：Larian 论坛两帖[29][30] 的社区回复均建议"做独立翻译 mod（Localization/<语言>/*.loca），不要改原 pak"，并"联系原作者请其把翻译整合进原 mod"；另一帖[31]（荷兰语，改的是原版游戏而非 mod）显示改官方语言 pak 的做法会随补丁失效。

### 2.4 中文社区的汉化教程与做法

| 来源 | 日期 | 教的是 | 工具 | 关键步骤/踩坑 |
|---|---|---|---|---|
| GameMale《非常简单的MOD汉化过程教学》[49]（已核实） | 2023-09-12 | **直接改原 pak 重打包** | LSLib ConverterApp | Extract Package → 只动 Localization/English 的 xml → 文本编辑器改 `><` 之间 → xml 转 loca → Create Package；"只修改 >< 中间的文本，否则对不上显示 Not Found"；备份原 pak |
| 3DM 第一版教程（fuyunai13）[44]（已核实） | 2023-10-22 | **改原 mod 后重新打包**（A：LocaHelper 翻译+LSLib 封包；B：LocaHelper 一站式） | LSLib 汉化版、LocaHelper 2.3 | 解包 → Localization 下**新建 Chinese 文件夹**并复制 English 的 xml → LocaHelper 加载翻译（红 origin/绿 Translated）→ 自动 xml→loca → 重打包；.NET 4.8.1、Win10 22H2+、工具需加白名单 |
| 3DM 第二版教程（同作者）[43]（已核实） | 2023-11-05 | **独立汉化 mod**（只含 Localization + Mods/meta） | LSLib V1.18.7 汉化版、LocaHelper 3.x、Notepad++ | 设工作路径 → "将 pak 文件导入到新的模组中" → 建 Localization/Chinese → loca/xml 互转"一定要改后缀名" → 翻译（绿已译/橙未译）→ 保存自动生成 loca → 编辑 meta（作者/描述）→ "打包并压缩选定的模组"；**mod 更新时新增文本标蓝**便于增量翻译；发布前可删 xml 只留 loca；建议从文本量小的 mod 练手；成品发论坛或 N 网 |
| 贴吧《关于MOD汉化过程的求助》[48]（已核实） | — | 从整合包转为**独立补丁** | BG3LocaHelper | "汉化只需要改 mod 名字的 loca 文件"；源文件是 `__MT_GEN_LOCA+uuid` 的 loca.xml 不知如何命名 |
| B 站《最简单的博德之门3MOD汉化教程》[50]（抓取被拦，仅搜索摘要） | — | 未知 | ExportTool-v1.18.7CHS-修复版、LSLib Toolkit-fuyunai13、BG3MOD管理器-Juij汉化版 | — |
| Nexus《Mod Translation Tutorial for Chinese》(Null993)[16]（403，仅摘要） | 2023-10-08 | "这是一个模组翻译教程" | — | — |
| Nexus 3023/7288 英文教程[17][18]（仅摘要） | — | 独立翻译 mod | LSLib Export Tool | 与原 mod 同名会生成同名 pak 而崩溃；Localization 下按官方语言名建文件夹；xml 翻译后转 loca；meta.lsx 用示例 mod 改 |
| 3DM《全自动mod汉化工具》[47]（已核实，部分） | 2025-08-07 | AI 全自动翻译 | 自研 AI 工具（教程在 B 站视频） | 帖内未说明输出为独立包还是覆盖 |
| 3DM LocaHelper Juij 编译汉化版 v3.3.1 [45]（帖文被屏蔽，仅见回帖） | 2023-11-06 | — | LocaHelper | v3.0 后打不开的兼容问题由该版解决 |

工具背景（仅搜索摘要[59][46]）：Bg3LocaHelper 是"Larian 游戏本地化编辑器"，支持"导入 mod pak 并转换为新的翻译 mod"、微软/MyMemory 机翻，基于 Norbyte 的 LSLib；LSLib 汉化版由 3DM 版主 fuyunai13 维护。
发布渠道（仅搜索摘要）：3DM 论坛（正式版MOD / 补丁 / 修改 分区，含从 N 网搬运的资源）[47]、3DM Mod 站（含 Iceriny 的《翻译者的快速本地化实用工具》V1.0.0.6）[51]、游侠《博德之门3 mod 汉化补丁下载大全》[52]、N 网 CHS/CHT 条目、B 站"官方中文 mod 整理"动态[55]；未搜到公开的 QQ 群信息（信息缺口）。

### 2.5 术语一致性

- 官方文本提取：Steam 指南《中文版对话解包教程》[53]（已核实）用 Multitool 解包 `Chinese.pak`，"中文版本位于 Chinese 文件夹下的 Localization 目录"，`.loca` 改后缀转 xml；目的为查看官方对话，未明说用于 mod 术语参考。→ 简中目录名 **Chinese** 由此与 3DM 教程互相印证。
- mod.io 官方指南《Using Origin Localisation》[36]（仅摘要）：在 Toolkit 中复用原版本地化（如覆盖 Find Familiar 的 DisplayName），"可解决本地化问题，也能减少本地化工作"——即对与原版同名的法术/物品直接引用官方 handle 即可自动获得官方中文。
- 中文对照资源：VG 百科《博德之门3法术》与"龙与地下城 5E 翻译馆"联合出品，995 个文档[54]（抓取 SSL 失败，仅摘要）；B 站 BWIKI `wiki.biligame.com/bg3`（108 页）[55]；游民/3DM 的全法术中文攻略页。
- 官方简中本身有争议：N 网存在"Chinese translation fixes"（2000+ 处修正）与"Improved Chinese Translation Patch"[56]，说明社区并不完全以官方译名为准。
- **未找到**任何中文社区维护的 mod 汉化术语表/译名表。

### 2.6 原 mod 更新后的跟进

- 版本标注：翻译页版本号与原 mod 同步[11][4]；俄译标题直接写 `Mystic Class (4.2.0.2) and Mystic Expansion (1.5.0.2)`[13]；原版汉化美化包按 "hotfix 10" 标注[14]。**未搜到 "for v1.14" 这种中文页面写法的直接例证**。
- 增量翻译：LocaHelper 第二版教程"mod 更新时新增文本标注为蓝色"[43]；Nexus 3023 摘要"原 mod 未新增字符串则翻译 mod 无需更新"[17]；Many More Monsters_CHT 新增文本"先机翻待校"[11]；低质量聚合页描述通用做法为"重新解包新版、对比找出新增条目"[57]。
- 过时症状：5e Spells CH 2.3.0.0 更新日志"修复所有已知 NOT FOUND"[15]；GameMale 教程指出 handle 对不上即显示 "Not Found"[49]；官方文档描述缺 handle 时出现 `ls::TranslatedStringRepository::s_HandleUnknown`[20]；BG3 Crafting Update CHS 评论区反映 mod 管理器记不住已更新的翻译版本[58]。
- 工具：LWizard（MO2 插件）可把翻译 mod 状态标为 "Outdated"[19]。

## 3. 信息缺口 / 未核实

1. 7 个指定样本页的描述正文（是否"仅含翻译"、加载顺序、对应原版版本）只有 Mystic 系列被摘要覆盖；其余需在浏览器里人工打开确认。
2. Nexus mod 页 "Translations" 区块的显示形式、以及 Permissions 是否存在独立翻译档位——论坛与 wiki 均 403，仅有下拉项清单摘要；结论"无 Translation permission 项"属推断。
3. mod.io 是否允许网页直传第三方 pak、翻译 mod 必需的确切标签名、《Translation MOD conversion guide》具体步骤——mod.io 全站不可抓，摘要只给出用途。
4. 主机（PS5/Xbox）上是否已有任何通过审核的中文翻译 mod：未找到实例。
5. B 站视频与动态、bilibili 专栏（cv25749829 返回验证码）内容未读到；GameMale 与 3DM 帖文回复区技术含量低。
6. 中文社区 QQ 群/汉化组组织形式、术语表：无公开检索结果。
7. 繁体目录名（`ChineseTraditional`）本次未从抓取到的原文中核实，仅为 `[背景知识—非本次检索]`。

## 4. 来源表

| # | 标题 | URL | 一手/二手 | 抓取状态 | 日期 |
|---|---|---|---|---|---|
| 1 | Artificer class and all subclassesCHS | https://www.nexusmods.com/baldursgate3/mods/15477 | 一手 | 搜索摘要 | — |
| 2 | Blood Hunter CH | https://www.nexusmods.com/baldursgate3/mods/16818 | 一手 | 搜索摘要（仅标题） | — |
| 3 | Mystic Class and Mystic Expansion CHS | https://www.nexusmods.com/baldursgate3/mods/15581 | 一手 | 搜索摘要 | 2025-04 更新 |
| 4 | Mystic Class CHS and Mystic Expansions CHS | https://www.nexusmods.com/baldursgate3/mods/14301 | 一手 | 搜索摘要 | — |
| 5 | Mystic Class expansion CHS | https://www.nexusmods.com/baldursgate3/mods/12935 | 一手 | 搜索摘要（仅标题） | — |
| 6 | 5e Way of the Astral Self - Monk Subclass CHS | https://www.nexusmods.com/baldursgate3/mods/13131 | 一手 | 搜索摘要（仅标题） | — |
| 7 | Death Knight Class - Champion of the Lich King_CHT | https://www.nexusmods.com/baldursgate3/mods/13838 | 一手 | 搜索摘要（仅标题） | — |
| 8 | Alternate Monk - CHS and CHT Translation Packs | https://www.nexusmods.com/baldursgate3/mods/4538 | 一手 | 搜索摘要 | — |
| 9 | Cleric Subclasses (CHT) Traditional Chinese Translation | https://www.nexusmods.com/baldursgate3/mods/1570 | 一手 | 搜索摘要 | — |
| 10 | Baldur's Gate 3 Community Library CH Version | https://www.nexusmods.com/baldursgate3/mods/15226 | 一手 | 搜索摘要 | — |
| 11 | Many More Monsters_CHT(with CHS) | https://www.nexusmods.com/baldursgate3/mods/13372 | 一手 | 搜索摘要 | — |
| 12 | Dragon Ball Warrior (DBZ)-Chinese translation | https://www.nexusmods.com/baldursgate3/mods/4157 | 一手 | 搜索摘要 | — |
| 13 | Mystic Class (4.2.0.2) and Mystic Expansion (1.5.0.2) - Russian | https://www.nexusmods.com/baldursgate3/mods/13989 | 一手 | 搜索摘要（仅标题） | — |
| 14 | Chinese Localization pack beautification for hotfix 10 | https://www.nexusmods.com/baldursgate3/mods/4025 | 一手 | 搜索摘要 | — |
| 15 | 5e Spells CH | https://www.nexusmods.com/baldursgate3/mods/15637 | 一手 | 搜索摘要 | — |
| 16 | Mod Translation Tutorial for Chinese (Null993) | https://www.nexusmods.com/baldursgate3/mods/3073 | 一手 | 失败(403)→搜索摘要 | 2023-10-08 |
| 17 | How to Make Translation Mod | https://www.nexusmods.com/baldursgate3/mods/3023 | 一手 | 搜索摘要 | — |
| 18 | How to Make Translation Mod (Advance) | https://www.nexusmods.com/baldursgate3/mods/7288 | 一手 | 搜索摘要 | — |
| 19 | LWizard - BG3 Translation Toolkit for MO2 | https://www.nexusmods.com/baldursgate3/mods/22349 | 一手 | 搜索摘要 | — |
| 20 | Game Text Compatibility Base Files（评论区） | https://www.nexusmods.com/baldursgate3/mods/8604 | 一手 | 搜索摘要 | — |
| 21 | Nexus File Submission Guidelines | https://help.nexusmods.com/article/28-file-submission-guidelines | 一手 | 抓取成功 | — |
| 22 | Nexus 新闻：Integrated support and separation for translation mods | https://www.nexusmods.com/news/12285 | 一手 | 搜索摘要 | — |
| 23 | Nexus 论坛：How do Permissions Work with Translations? | https://forums.nexusmods.com/topic/9219853-how-do-permissions-work-with-translations/ | 二手 | 失败(403) | — |
| 24 | Nexus Wiki：How to Manage Mod Permissions, Credits, and Files | https://wiki.nexusmods.com/index.php/How_to_Manage_Mod_Permissions,_Credits,_and_Files_on_NexusMods | 一手 | 失败(403)→搜索摘要 | — |
| 25 | Steam 讨论：Translating Nexus mods - permission or something to upload? | https://steamcommunity.com/app/377160/discussions/0/2575445991837227064/ | 二手 | 抓取成功 | — |
| 26 | Nexus 论坛建议：Change language label "Mandarin" to "Chinese" | https://forums.nexusmods.com/topic/13542978-suggestion-change-language-label-mandarin-to-chinese | 二手 | 搜索摘要 | 2025 |
| 27 | Larian 论坛：Modding: Guidelines & FAQ | https://forums.larian.com/ubbthreads.php?ubb=showflat&Number=948625 | 一手 | 抓取成功 | — |
| 28 | Larian 论坛：Community Update #27 Official Modding Support（打印版） | https://forums.larian.com/ubbthreads.php?ubb=printthread&Board=86&main=118005&type=thread | 一手 | 抓取成功 | 2024 |
| 29 | Larian 论坛：Any way to translate an already created mod? (953645) | https://forums.larian.com/ubbthreads.php?ubb=showflat&Number=953645 | 二手 | 抓取成功 | — |
| 30 | Larian 论坛：Any way to translate an already created mod? (952596) | https://forums.larian.com/ubbthreads.php?ubb=showflat&Number=952596 | 二手 | 抓取成功 | — |
| 31 | Larian 论坛：Localization mod Balder's Gate 3 | https://forums.larian.com/ubbthreads.php?ubb=showflat&Number=955200 | 二手 | 抓取成功 | — |
| 32 | Larian 支持 FAQ：Official Mod Support / Mod Information；Steam 讨论摘要 | https://larian.com/support/faqs/official-mod-support_113 | 一手 | 搜索摘要 | — |
| 33 | Larian BG3 Modding Terms (PDF) | https://baldursgate3.game/mods/Larian_BG3_Modding_Terms.pdf | 一手 | 失败(403)→搜索摘要 | 2024-05-30 |
| 34 | mod.io：Modding Guidelines & FAQ | https://mod.io/g/baldursgate3/r/modding-guidelines | 一手 | 失败(仅标题) | — |
| 35 | mod.io：Translation MOD conversion guide | https://mod.io/g/baldursgate3/r/translation-mod-conversion-guide | 一手 | 搜索摘要 | — |
| 36 | mod.io：Using Origin Localisation guide | https://mod.io/g/baldursgate3/r/using-origin-localisation | 一手 | 搜索摘要 | — |
| 37 | mod.io：Languages 标签筛选 / Translation Supplement JP / Fixed Russian translation | https://mod.io/g/baldursgate3?tags=Languages | 一手 | 搜索摘要 | — |
| 38 | mod.io Support：Baldur's Gate 3 分区 | https://support.mod.io/hc/en-us/sections/10634930958607-Baldur-s-Gate-3 | 一手 | 失败(403) | — |
| 39 | bg3.wiki：Modding:Localization | https://bg3.wiki/wiki/Modding:Localization | 二手 | 抓取成功 | — |
| 40 | 官方文档：Adding Localisation | https://docs.baldursgate3.game/index.php?title=Adding_Localisation | 一手 | 搜索摘要（未抓） | — |
| 41 | BG3 Modding Community Wiki：Mod Types | https://wiki.bg3.community/en/Tutorials/Mod-Use/BG3-Mod-Types-and-how-to-install-them | 二手 | 失败(仅标题) | — |
| 42 | bg3modmanager.net：Larian In-Game Mod Manager Guide | https://bg3modmanager.net/larian-in-game-mod-manager-guide/ | 二手 | 抓取成功（无翻译相关内容） | 2026 |
| 43 | 3DM：基于 BG3 LocaHelper 制作独立汉化mod 教程（第二版，含第 4 页） | https://bbs.3dmgame.com/thread-6464902-1-1.html | 一手 | 抓取成功 | 2023-11-05 |
| 44 | 3DM：基于 BG3 Locahelper 的 mod 汉化教程（第一版，含第 8 页） | https://bbs.3dmgame.com/thread-6461116-1-1.html | 一手 | 抓取成功 | 2023-10-22 |
| 45 | 3DM：模组本地化助手 Bg3LocaHelper v3.3.1 Juij 编译汉化版 | https://bbs.3dmgame.com/thread-6464459-1-1.html | 一手 | 抓取成功（正文被屏蔽） | 2023-11-06 |
| 46 | 3DM：LSLib Toolkit 汉化版 V1.18.7（fuyunai13） | https://bbs.3dmgame.com/thread-6459981-1-1.html | 一手 | 搜索摘要 | 2023-10-19 |
| 47 | 3DM：全自动 mod 汉化工具 | https://bbs.3dmgame.com/thread-6611944-1-1.html | 一手 | 抓取成功（部分） | 2025-08-07 |
| 48 | 贴吧：关于MOD汉化过程的求助 | https://tieba.baidu.com/p/9320998751 | 一手 | 抓取成功 | — |
| 49 | GameMale：非常简单的MOD汉化过程教学（Kenttt） | https://www.gamemale.com/thread-119405-1-1.html | 一手 | 抓取成功 | 2023-09-12 |
| 50 | B 站：最简单的博德之门3MOD汉化教程 | https://www.bilibili.com/video/BV1CJaweSEr4/ | 一手 | 失败(域名拦截)→搜索摘要 | — |
| 51 | 3DM Mod 站：翻译者的快速本地化实用工具（Iceriny）/ 中英双语显示 | https://mod.3dmgame.com/mod/201549 | 一手 | 搜索摘要（201989 抓取为空） | — |
| 52 | 游侠：博德之门3 mod 汉化补丁下载大全 | https://patch.ali213.net/z/8446/17067/ | 二手 | 搜索摘要 | 2025 |
| 53 | Steam 指南：中文版对话解包教程 | https://steamcommunity.com/sharedfiles/filedetails/?id=3158539487 | 一手 | 抓取成功 | — |
| 54 | VG 百科：博德之门3法术（与 5E 翻译馆联合） | https://www.vgbaike.com/baldurs_gate_3/baike1211 | 二手 | 失败(SSL)→搜索摘要 | 2023-07-29 更新 |
| 55 | B 站 BWIKI：博德之门3WIKI；B 站动态"官方中文mod整理" | https://wiki.biligame.com/bg3/ | 二手 | 搜索摘要 | — |
| 56 | Nexus：Chinese translation fixes / Improved Chinese Translation Patch | https://www.nexusmods.com/baldursgate3/mods/8892 | 一手 | 搜索摘要 | — |
| 57 | cangjggame：博德之门3 汉化mod怎么制作（AI 聚合页，低可信） | https://cangjggame.com/s?id=e06ebb63-5b4b-4063-a668-b88b629aad35 | 二手 | 搜索摘要 | — |
| 58 | Nexus：BG3 Crafting Update CHS（评论区） | https://www.nexusmods.com/baldursgate3/mods/17329?tab=posts | 一手 | 搜索摘要 | — |
| 59 | Bg3LocaHelper / LarinStudios Localization Helper（Nexus 3136 & GitHub） | https://www.nexusmods.com/baldursgate3/mods/3136 | 一手 | 搜索摘要 | — |
| 60 | Nexus：Blood Hunter Chinese (2909) / Blood Hunter Class … CHS (15377) / Expanded CHS (15378) | https://www.nexusmods.com/baldursgate3/mods/2909 | 一手 | 搜索摘要（仅标题） | — |

## 5. 抓取统计

- WebSearch：49 次，全部返回结果。
- WebFetch：25 次——成功 14（help.nexusmods.com ×1、forums.larian.com ×5、bg3.wiki ×1、3DM ×5、贴吧 ×1、GameMale ×1、Steam ×2，其中 3DM 有 2 次正文被屏蔽/灌水）；403 或仅标题 9（nexusmods.com、forums.nexusmods.com、wiki.nexusmods.com、mod.io ×1、support.mod.io、baldursgate3.game、wiki.bg3.community、mod.3dmgame.com 返回空）；域名拦截/SSL 失败 2（bilibili、vgbaike）。
- 未使用任何浏览器类工具。
