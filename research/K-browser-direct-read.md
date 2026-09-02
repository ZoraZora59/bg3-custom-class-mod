# K · 主控浏览器直读（汉化课题）

> 主控用内置浏览器直读的一手/二手页面，用于补子代理 WebFetch 打不开的站点。日期：2026-09-02。引用均为转述或 ≤15 词短引。

## 1. 结论摘要
1. **bg3.wiki《Modding:Localization》给出的社区标准做法就是"独立翻译补丁"**：只从原 mod 复制 `Localization/English`，把目录改名为目标语言（用英文名，如 `German` 而非 `Deutsch`），翻译 xml 里 `<content>` 的正文、**不动 `contentuid` 与 `version`**，自建 `meta.lsx`，打包后"放在原 mod 之下加载"，仍有问题再把原 mod 加为依赖 [K1]。
2. 同页开头就写：先问原作者是否同意翻译，"99% 的作者都乐意"，且**把原 mod 设为依赖并不会通知作者**，所以要主动告知 [K1]。
3. **mod.io（Larian 官方）准则**：未获许可"不得把他人 mod 扩展、翻译或重制后署名"（转述）；mod.io 没有翻译分区，只能用 `translation` tag + 语言 tag；联机所有人必须装相同 mod；两个 mod 改同一 ID 条目时"加载顺序获胜"；第三方（非 Toolkit）pak 会在游戏内被标为 third-party 且不能从游戏内更新 [K2]。
4. **3DM 中文社区教程（fuyunai13，2023-10/11）证实两条路线都存在**：第一版教程是"解包原 mod → 在 `Localization` 下新建 `Chinese` → 复制 English 的 xml 翻译 → 生成 loca → 重新打包成 CHS 版"（即直接改原 mod 的整合版）；第二版教程改为"独立汉化 mod"，成品只含 `Localization` + `Mods`（meta.lsx）两部分，用 BG3 LocaHelper 自动生成 meta.lsx、loca 并打包 [K3][K4]。
5. 3DM 教程明确的技术细节：游戏只识别 `.loca`，xml 可删；LocaHelper 能对比新旧版本 xml，**新增文本标蓝、只翻新增**；原 mod 更新时靠 `Previous XML` 对比；工具需要 Windows（.NET 4.8.1 / .NET 7 运行库）[K3][K4]。
6. **加载顺序的方向已核实**：bg3.wiki《Modding:Installing mods》要求在 BG3MM 里"把被依赖的 mod 放在依赖者之上"，`modsettings.lsx` 的 `ModOrder` 节点从上到下就是加载顺序、`GustavDev` 永远第一 [K6]——所以"翻译补丁放在原 mod 之下"= 比原 mod **更晚加载**。
7. **mod.io 官方渠道也走"独立翻译 mod"，且给出了转换流程**（社区作者 hawchangJA 写在 mod.io 指南区，约 2024-10）：用官方 Toolkit 新建空项目 → 只把 `Localization/<目标语言>/*.xml` 复制进 `{GameData}/Mods/<Project-UUID>/Localization/`（**Toolkit 管线读 xml、不读 .loca**）→ 在 Toolkit 里填 Name/Author/描述/缩略图、把被翻译 mod 加进 Dependencies → 发布后在 mod.io 再设一次依赖。作者推测的文本选取规则：按游戏语言目录找 handle → 找不到回退 English → 再找不到显示 "Not Found"；并提醒 Multitool 打包会把多个 xml 合并、同 handle 会在 mod 内部互相覆盖，而 Toolkit 不合并 [K7]。
8. **官方《Adding Localisation》再读（针对翻译场景）**：`version` 的官方定义是"字符串的版本，用于更新自己的行或更新游戏里已有的行"；xml 内可用 `&lt;`/`&gt;` 这类 HTML 实体；改完 xml 要重载模块/重启/`reloadLoca`；**官方页没有任何关于"缺失 handle 时回退英文"的说明**，回退行为仍只有 K7 作者的推测与报告 I 的社区证据 [K8]。
9. **Nexus 在内置浏览器里被 Cloudflare 人机验证拦下**（"正在进行安全验证"页面 11 秒未放行），未绕过，Nexus 文章 643 / mod 7288 / 各 CHS 汉化页只能依赖子代理的搜索摘要 [K5]。

## 2. 证据细节

### K1 bg3.wiki — Modding:Localization（抓取成功）
- 页面定位：本地化文件决定游戏显示的一切文本（字幕、物品名与描述、书籍、角色创建名称）。
- "Translating Mods to other Languages" 一节：另有 Nexus 上 bk0n9 的指南与 Padme4000 的模板作为替代。
- 步骤（转述）：
  1. 先征得作者同意；作者希望知道以便在页面互链；把主 mod 设为 requirement 不会通知作者。
  2. 新建工作目录（建议"原 mod 名 + 语言"）。
  3. 只复制原 mod 的 `Localization/English`（含 `.loca`；若用 Multitool 解包会是 `.loca.xml`，可保留该后缀，Multitool 重打包时会转回 `.loca`）；**其它目录都不需要**。
  4. 把 `English` 目录改名为目标语言的英文名。
  5. `.loca` 需用 LSLib 转成 xml 再编辑（Notepad++ / VS Code）。
  6. 只改 `>` 与 `<` 之间的文本，不改 `version` 与 `contentuid`。
  7. 按《Modding:Creating meta.lsx》自建 meta.lsx，打包测试；"为保险起见在加载顺序里放到原 mod 之下"；仍有问题就把原 mod 加为 Dependencies（链接到《Modding:Dependencies》）。
- 该页未说明：缺失 handle 的回退行为、多 pak 同 handle 的覆盖规则（留给报告 I）。

### K2 mod.io — Modding Guidelines & FAQ（抓取成功，页面显示"7 个月前更新"）
- Best Practices 表格 "Crediting Mod Authors"：署名团队成员与灵感来源；**未获许可不得把他人 mod 扩展/翻译/重制后署原作者**（原文为 "Do not attempt to credit a mod author if you have not obtained permission to expand, translate, or re-create an existing mod"，此句为本页唯一 ≥15 词引用，仅作准则原文留档）。
- ToS 摘要：mod 的任何元素必须是原创或已获必要许可。
- Third-Party Mods：在 mod.io 之外维护的 mod 会被读入并标为 "third-party"，玩家不能从该界面更新它们。
- Multiplayer：联机时所有人需安装相同 mod；加入大厅时会提示下载缺失 mod、启用/禁用不匹配项。
- FAQ："两个 mod 改同一个基于 ID 的条目 → 加载顺序获胜"（所有 mod 文件先加载再合并）。
- FAQ："mod.io 没有翻译分区"，建议 `translation` tag + 支持的语言 tag。
- 主机：Toolkit 不面向主机，主机 mod 需通过 Larian 内部策展；不支持 `.exe/.dll/.zip`、新增可玩种族等。

### K3 3DM — 第一版教程《mod 汉化教程 基于 BG3 Locahelper 2023.10.22》（抓取成功）
- 工具：LSLib Toolkit（楼主的汉化版 v1.18.7）+ BG3 LocaHelper 2.3（作者 tento0815，德国翻译者为提效自研；.NET 4.8.1；旧版 Win10 装不上）。
- 流程（改原 mod 的"整合版"路线）：LSLib 解包 pak → `Localization` 下新建 `Chinese` → 把 `English` 的 xml 复制进去 → LocaHelper 里以 Current XML（原文）/ Translated XML（Chinese 目录）双窗口对照逐句翻译（状态 origin=红、Translated=绿）→ `Save Source XML` 同时自动生成 `.loca` → 方案 A 回 LSLib 重新打包（版本选 BG3 V18，压缩可选）/ 方案 B 用 LocaHelper 的 Pack Mod 直接打包 → 文件名加 `CHS` 后缀区分。
- 更新维护：导入 Previous XML 与 Current XML 对比，新增文本标蓝，点击 Source 自动生成新译文骨架，只翻新增。
- 楼下讨论（果冻是你大爷）："做独立汉化包还得额外建 meta 和完整 mod 目录"——楼主回复 LocaHelper 2.4 起可自动生成独立 mod。

### K4 3DM — 第二版教程《制作独立汉化 mod 2023.11.5》（抓取成功）
- 独立汉化 mod 的结构：解包成品可见**只有 `Localization` 与 `Mods` 两部分**（示例为楼主自己发在 Nexus 的 "Chinese Patch Collection of Sharess and Loviatar"，一个汉化包覆盖同系列多个 mod）。
- LocaHelper 3.x 流程：设置独立汉化 mod 输出路径 → "将 pak 文件导入到新的模组中"关联原 mod（示例在原名后加 `CHS`）→ 新增 `Localization/Chinese` → 若原 mod 只有 `.loca` 没有 xml，用 LSLib 转换（转换时必须手改后缀名）→ 加载 xml 翻译（已译绿、未译橙、更新后新增蓝，带计数）→ 保存时自动生成 loca → 用 Notepad++ 改工具自动生成的 meta.lsx（只需改作者名与描述）→ 工具内"打包并压缩选定的模组"。
- "游戏只能识别 loca 格式"，打包前可删 xml。
- 建议：初学者先挑文本量小的 mod；非英语作者（俄/德/法/日）的 mod 难度高。
- 工具需 Win10 21H2+ 与 .NET 7 运行库；附件需回帖可见。

### K6 bg3.wiki — Modding:Installing mods（抓取成功）
- BG3MM 流程：pak 放进 `%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\Mods` → 右栏拖到左栏 → "被依赖的 mod 放在依赖它的 mod 之上" → 保存 Mod Order → Export 到游戏。
- 手动流程：`modsettings.lsx`（PlayerProfiles/Public）里 `ModOrder` 的 `Module` 节点顺序即加载顺序，Gustav/GustavDev 必须第一；Mac/Linux 用户没有 BG3MM 时尤其要手工排好；示例文件里每个 mod 对应一个 `ModuleShortDesc`（Folder/MD5/Name/UUID/Version64）。
- 该页写于 Patch 7 之前（仍提 Mod Fixer、手改 modsettings），Patch 7 后由游戏内管理器或 BG3MM 写该文件（见 docs/04 B1）。

### K7 mod.io — Translation MOD conversion guide（抓取成功；作者 hawchangJA，日文母语，"1y 11mo" 前更新，2 条评论）
- 前提：翻译 mod 已在 Nexus 发布、被翻译的 mod 已在 mod.io、装好 Toolkit 并完成 mod.io 发布准备；开篇提醒"别忘了向原作者取得许可"。
- Nexus 格式 mod 结构 vs mod.io/Toolkit 项目结构：Toolkit 项目分 `Editor/Mods/<Name-UUID>`、`Mods/<Name-UUID>/Localization/<Lang>/(Gender/Female|Neutral)/<Lang>.loca.xml + meta.lsx`、`Project/<Name-UUID>/meta.lsx`、`Public/<Name-UUID>/...`；翻译 mod 只有 Localization 目录重要，其余目录不需要（Toolkit 会自动重建一部分）。
- 步骤：① Toolkit 新建项目后关闭（只建不改，项目名用 PascalCase）；② 资源管理器里把 `ModName/Localization/<Lang>/*` 复制到 `{GameData}/Mods/<Name-UUID>/Localization/<Lang>/`，**注意 mod.io 格式似乎读不了 .loca，要复制未转换的 .xml**；③ Toolkit 打开项目填 Name（≤50 字符，显示在官方管理器）、Author、Description（非英文描述建议每次发布时重新粘贴，否则可能乱码）、缩略图（必填）、Dependencies（把被翻译 mod 加进去；只能选游戏里已安装的 mod）、Conflicts；建议先保存一次再发布以确保信息写入；④ 发布后在 mod.io 页面再设一次 dependencies，官方管理器据此自动启停依赖。
- 参考信息："How translation text is selected (my guess)"：按游戏语言目录查 handle（含 Gender 子目录）→ 找不到就查 English → 仍找不到显示 "Not Found"；官方支持 15 种语言（列表与 G7 一致）；想显示第 16 种语言只能顶替某个非英语语言目录；想保留英文的条目直接在目标语言里删掉该 handle 即可。
- Toolkit 版本号：Build 号每次发布（含本地发布）自增且不可减；不开 Toolkit 时可直接改 meta.lsx 的 Version64。
- 打包差异：Multitool 会把多个 xml 合并成一个再打包，跨目录同 handle 会互相覆盖；官方 Toolkit 不合并。
- 变体与翻译 mod 的取舍：mod.io 与 Toolkit 没有"变体"机制，只能作为独立 mod 并设置冲突；作者建议——文本多或会持续更新 ⇒ 主 mod + 独立翻译 mod；文本少且少更新 ⇒ 把译文交给原作者合并进主 mod。
- UUID 继承坑：若沿用原 mod 的 UUID 打开 Project Settings 会报"同一键已存在"，因为原 mod 已装在 Mods 目录；需用官方管理器删除（禁用无效，直接删 pak 可能让全部 mod 被禁用）。

### K8 Larian 官方文档 — Adding Localisation（再读，抓取成功）
- 与 G7 一致的部分不重复。翻译场景相关补充：
  - `.loca` 是原版数据库导出的二进制；mod 在自己目录放 xml 即可"修改已有字符串或新建字符串"（此为 Toolkit/Editor 管线视角，手工 pak 仍需 .loca，见 K3/K4）。
  - `<version>`："your string 的版本，用于更新自己的行或更新游戏里已有的行"；示例用原版 handle + `version="2"` 覆盖原版文本。
  - 字符串可嵌 HTML 字符实体（`&lt;`、`&gt;`）——翻译时 `<LSTag>`/`<br>` 之类标记在 xml 里就是以实体形式出现，必须原样保留。
  - 未提到回退（fallback）规则。

### K5 Nexus（失败）
- `https://www.nexusmods.com/baldursgate3/articles/643` 在内置浏览器停留在 Cloudflare 验证页（标题"请稍候…"），等待 11 秒未放行；按规则不做人机验证绕过。

## 3. 信息缺口
- Nexus 文章 643、mod 7288、各 CHS 汉化 mod 页面的原文（仅能靠搜索摘要，见报告 J）。
- bg3.wiki 未回答"缺失 handle 回退"与"同 handle 覆盖规则"（见报告 I）。
- BG3 LocaHelper 是否有 GitHub/Nexus 官方发布页与 2026 年现状（见报告 H）。

## 4. 来源表
| # | 标题 | URL | 一手/二手 | 抓取状态 | 日期 |
|---|---|---|---|---|---|
| K1 | bg3.wiki — Modding:Localization | https://bg3.wiki/wiki/Modding:Localization | 二手（社区 wiki） | 浏览器直读成功 | 2026-09-02 |
| K2 | mod.io — Baldur's Gate 3 Modding Guidelines & FAQ | https://mod.io/g/baldursgate3/r/modding-guidelines | 一手（Larian 官方） | 浏览器直读成功 | 2026-09-02 |
| K3 | 3DM — mod 汉化教程 基于 BG3 Locahelper（第一版） | https://bbs.3dmgame.com/thread-6461116-1-1.html | 二手（社区教程） | 浏览器直读成功 | 2026-09-02 |
| K4 | 3DM — 基于 BG3 LocaHelper 制作独立汉化 mod 教程（第二版） | https://bbs.3dmgame.com/thread-6464902-1-1.html | 二手（社区教程） | 浏览器直读成功 | 2026-09-02 |
| K5 | Nexus — 文章 643 How to Translate these Mods | https://www.nexusmods.com/baldursgate3/articles/643 | 二手 | 失败（Cloudflare 人机验证） | 2026-09-02 |
| K6 | bg3.wiki — Modding:Installing mods | https://bg3.wiki/wiki/Modding:Installing_mods | 二手（社区 wiki） | 浏览器直读成功 | 2026-09-02 |
| K7 | mod.io — Translation MOD conversion guide（hawchangJA） | https://mod.io/g/baldursgate3/r/translation-mod-conversion-guide | 二手（社区作者发布在官方平台指南区） | 浏览器直读成功 | 2026-09-02 |
| K8 | Larian 官方文档 — Adding Localisation | https://docs.baldursgate3.game/index.php?title=Adding_Localisation | 一手 | 浏览器直读成功 | 2026-09-02 |

## 5. 抓取统计
- 浏览器直读成功 7，失败 1（Nexus 人机验证，未绕过）。
