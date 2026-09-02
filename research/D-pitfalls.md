# 子课题 D：BG3 职业类 mod 踩坑记录（pitfalls）+ 政策与法务风险

- 调研日期：2026-09-02
- 范围：面向"自创新职业 (class/subclass) mod"的症状 → 原因 → 解决/预防 清单；Larian / mod.io / Nexus 政策；WotC 内容授权（SRD 5.1 / 5.2 / 5.2.1）
- 引用规则：`[n]` 指向第 6 节来源列表；标注 `[背景知识—非本次检索]` 的内容来自训练记忆，未被本次检索证实，不计入来源统计。
- 重要限制：本次 WebFetch 对 larian.com、baldursgate3.game（含 Modding Terms PDF）、docs.baldursgate3.game、mod.io、nexusmods.com 新闻页均被 403/拦截；wiki.bg3.community 为 JS 渲染页，抓取只返回标题。这些页面的内容**只能依赖 WebSearch 返回的摘要片段**，引用时已尽量保留原文关键字，但无法核对全文。详见第 5、7 节。

---

## 1. TL;DR

1. **打包层面最常见的三个"静默失败"**：`meta.lsx` 的 `Folder` 属性与 PAK 内 `Mods/<Folder>/`、`Public/<Folder>/` 文件夹名不一致（"stuff in your mod will break"）；`UUID` 复制模板未改导致与他人 mod 互相覆盖；`Version64` 未重新生成导致更新不被识别。另有一个反直觉硬坑：`Name` 里不要出现 `-b` 这种"连字符后接 b"的组合，bg3.wiki 明确记录"can cause the mod not to load"。[1][2][42]
2. **Patch 7（2024-09）之后 `modsettings.lsx` 不再需要手动编辑**，路径仍是 `%LocalAppData%\Larian Studios\Baldur's Gate 3\PlayerProfiles\Public\modsettings.lsx`（Mac 为 `~/Documents/Larian Studios/Baldur's Gate 3/PlayerProfiles/Public/`）。游戏内 Mod Manager 与 BG3MM 写的是同一个文件，两者混用会互相覆盖；任何一个 mod 出错都会让游戏清空整个加载顺序；Steam Cloud 还会把它回滚并生成 `-conflict` 文件。[4][5][39][40]
3. **职业 mod 的核心冲突点是 `Progressions.lsx`**：子职业需要挂到父职业进阶表的 SubClasses 列表上，多个子职业 mod 静态覆盖同一条目就会"后加载者赢、其余消失"。Patch 8 的 12 个官方新子职业本身就是"经 Compatibility Framework 加入的，以免旧子职业 mod 无意中把它们删掉"；解决方案是让子职业通过 Compatibility Framework (CF) 在运行时注入——但 CF 依赖 Script Extender (SE)。**做"全新职业"而非"子职业"可以绕开这一整类冲突**。[26][27][29]
4. **图标与本地化是"看得见的坑"**：类/法术图标扩展名必须大写 `.DDS`、DXT5、不带 mipmap、路径 `Public\Game\GUI\Assets\<MODNAME>\ClassIcons`；本地化 handle 生成失败时 Toolkit 会直接写入 `ls::TranslatedStringRepository::s_HandleUnknown`，xml 未转 `.loca` 或语言文件夹名不对（要用 `English`、`German` 这类英文名）都会导致文本不显示。[20][21][31][32]
5. **SE 只服务最新游戏版本、自动更新、无 GitHub 发布**；Patch 8 版 SE 不能用于 Patch 7，反之亦然。每次大补丁后 SE 类 mod 会有一段失效期，社区普遍判断"最可能被 Patch 8 打坏的是非 mod.io 的 Nexus mod，尤其是基于 SE 的"。截至 2026-06-21 SE 仍有新版本 (v32) 发布，说明生态仍在维护。[9][10][43]
6. **平台限制决定技术选型**：主机 (PS5/Xbox) 只能通过 mod.io 官方目录、目录不含依赖 SE 的 mod；Mac 没有官方 SE；Linux/Steam Deck 需 `WINEDLLOVERRIDES="DWrite.dll=n,b" %command%`；联机要求"完全相同的 mod 且版本一致"；Toolkit 仅 PC。[12][23][24][44]
7. **政策/法务**：Larian Modding Terms（2024-05-30）要求 mod 内容"必须是你的原创或已获得必要许可"，禁止"为金钱或其他利益"出售/出租/许可 Toolkit 与 Mod；mod.io 游戏内管理器不允许 NSFW，并有"维护 D&D 世界观完整性"的额外准则。WotC 方面，SRD 5.2/5.2.1（2025-04/05）以 CC-BY-4.0 不可撤销发布，涵盖 12 个核心职业与 2024 PHB 的部分子职业/种族/专长，但**不含 Artificer、Aasimar、Beholder、Mind Flayer 等**；Tasha's/Xanathar's 子职业、Blood Hunter 等均不在 SRD 内。**完全自创职业**在法务上最安全，只要名称、图标、字体、音效都是自有或合规授权素材。[14][15][17][18]
8. **存档与 mod 生命周期**：mod 一旦被存档加载就"烤"进存档，移除会触发 missing mods 警告，内容类 mod（新法术/新职业）中途移除风险最高；Larian 官方建议大更新后先移除 mod 文件排查。发布者应在 mod 页面明确"不要在进行中的存档移除本 mod"并提供 Withers 重置建议。[13][35]

---

## 2. 分类坑清单（症状 → 原因 → 解决/预防 → 来源）

### 2.1 打包 / 元数据类（meta.lsx、PAK、转换）

| # | 症状 | 原因 | 解决 / 预防 | 来源 |
|---|------|------|-------------|------|
| A1 | BG3MM 导入 PAK 时报 "Mod Was Not Imported"；或 mod 不出现在加载顺序里，而是出现在 BG3MM 的 **Overrides** 区（橙色高亮） | PAK 内没有可解析的 `Mods/<Folder>/meta.lsx`（缺少 `ModuleShortDesc` 节点、XML 不合法、放错层级）。没有 meta.lsx 的包会被当作"基础游戏覆盖 (basegame override)" | 目录固定为 `Mods/<Folder>/meta.lsx`；保留 `<?xml version="1.0" encoding="UTF-8"?>` 声明与 `<version major="4" minor="0" revision="9" build="331"/>` 节点；**meta.lsx 保持 .lsx，不要转成 .lsf** | [1][4] |
| A2 | mod 被识别、能启用，但职业/法术/文本全部不生效（"stuff in your mod will break"） | `meta.lsx` 的 `Folder` 属性值与 PAK 内 `Mods/<Folder>` 及 `Public/<Folder>` 的实际文件夹名不一致（"parent folder of your meta.lsx is the same as the 'Folder' name"） | 三处名称逐字一致；改 mod 名时同步改文件夹、`Folder`、`Name`。"missing one little detail will make your mod not load & it's overall a tedious process to debug" | [1][2][42] |
| A3 | mod 莫名不加载，其他一切正常 | `Name` 属性含有"连字符后接 b"的组合。bg3.wiki 原文："Do not put - before a b, as we have found out lately that can cause the mod not to load"，并称这是 mod loader 的硬编码限制 | 命名避开 `-b`（如 `Foo-Bard` 改为 `Foo_Bard` 或 `FooBard`） | [1] |
| A4 | 装了你的 mod 后另一个 mod 消失 / 两个 mod 在管理器里互相"顶掉"；或你的 mod 更新后被当成另一个 mod | `UUID`（`FixedString`）复制自模板或他人 mod 未改；"must be unique unless you want it to override another mod" | 每个 mod 生成一次 RFC 4122 v4 UUID 并**终身不变**；只有明确要"覆盖/替代"别的 mod 时才复用其 UUID | [1][2] |
| A5 | 发布新版本后 BG3MM / 游戏内管理器 / 依赖方看不到"更新"；依赖版本校验异常 | `Version64`（`int64`）未重新生成。它把 Major.Minor.Revision.Build 编码成一个 64 位整数，模板值 `36028797018963968` 读作 `1.0.0.0` | 每次发版用 BG3MM、Modders Multitool 或 BG3 Mini Tool 重新生成；`PublishVersion` 节点可同步为当前版本 | [1][41] |
| A6 | 游戏/管理器提示缺少依赖；依赖框架的功能不生效 | `meta.lsx` 的 `<node id="Dependencies"/>` 缺失或写错（UUID/Folder/Name/Version64 与被依赖 mod 不一致）；"If missing or incorrectly configured, dependent mod features may fail" | 凡使用其他 mod 资源（Community Library、CF、SE 相关库）必须正确声明；声明的 `Version64` 不要高于用户实际安装版本 | [1] |
| A7 | 打包后 `.lsx` 数据不被读取；或本地化文本不显示 | 游戏读取的是二进制 `.lsf`（数据）与 `.loca`（本地化）。Multitool 只会自动转换命名为 `example.lsf.lsx` → `example.lsf`、`example.lsb.lsx` → `example.lsb`、`xxx.loca.xml` → `xxx.loca` 的文件；命名不符则原样打包 | 遵守 `*.lsf.lsx` / `*.loca.xml` 命名约定，或用 lslib (ConverterApp) 手动转换后再打包 | [21][22][41] |
| A8 | `MD5`、`Tags` 字段不知填什么 | 官方/社区模板中两者均 `value=""` 留空即可 | 留空；不要手填假 MD5 | [1] |
| A9 | PAK 内路径大小写导致 Linux/Proton 下资源找不到 | **未能检索到直接证据**。已知的相关硬性要求是图标扩展名必须大写 `.DDS`（见 C4） | `[背景知识—非本次检索]` 在 Windows 上路径大小写不敏感、在 Linux 原生/部分 Proton 配置下可能敏感；稳妥做法是与原版 PAK 中的路径大小写完全一致 | [31] |

### 2.2 加载 / 管理类（modsettings.lsx、加载顺序、管理器混用）

| # | 症状 | 原因 | 解决 / 预防 | 来源 |
|---|------|------|-------------|------|
| B1 | 不知道 Patch 7 之后 `modsettings.lsx` 在哪、还要不要改 | 位置未变：Windows `C:\Users\<YourUsername>\AppData\Local\Larian Studios\Baldur's Gate 3\PlayerProfiles\Public\modsettings.lsx`；Mac `/Users/<you>/Documents/Larian Studios/Baldur's Gate 3/PlayerProfiles/Public/`。"Prior to Patch 7, you needed to edit this file to correctly install mods and set the mod order, but this has now changed" | 不再手工编辑；由游戏内 Mod Manager 或 BG3MM 二选一来写 | [5] |
| B2 | 每次启动游戏后 `modsettings.lsx` 被重置、mod 被移除 / "game says mods disabled, but they are enabled in BG3MM" | 三种常见根因：(a) Patch 7 的游戏内 Mod Manager 与 BG3MM"写同一个 modsettings.lsx，两者会冲突，除非其中一个不用"；(b) "one or more of your mods are encountering an error, and the game is clearing the load order"；(c) 加载顺序里的某个 UUID 在 `Mods` 文件夹找不到对应 `.pak`，游戏视整个加载顺序为不一致 | 只用一个管理器；逐个二分排查出错 mod；保证列表里的每个 UUID 都有对应 PAK；BG3MM 用户重新 Export Order to Game | [4][39][40][49][50] |
| B3 | 换电脑 / 重启后加载顺序回滚；`PlayerProfiles/Public` 里出现带 `-conflict` 后缀的文件 | Steam Cloud 同步冲突：客户端把本地文件改名为 `-conflict`，再拉回云端旧版本；多 PC 之间、或上传超时回滚都会触发 | 在 Steam 库 → BG3 属性中关闭该游戏的云同步（或至少排除 Profile 文件夹） | [4]（三手） |
| B4 | 老教程叫装 "Mod Fixer"，不知 Patch 7 后是否还要 | "Modfixer is not broken and is not needed anymore in Patch 7, but it does not cause issues"；很多旧 mod 内置了 ModFixer，可以继续用 | 新 mod **不要**再捆绑 ModFixer；用户侧若出现异常，"remove the Mod Fixer .pak file from your mods folder" 是标准排查步骤之一 | [5] |
| B5 | 游戏大更新后启动崩溃 / 存档加载报错 | Larian 官方：应当"remove any existing mod files, especially after a major game update as some changes may create conflicts with how your mods work" | 补丁日先全部禁用 mod 验证原版可启动，再逐个恢复；作者应在补丁日主动测试并在 mod 页置顶说明 | [13] |
| B6 | 想找 Larian 官方帮忙解决 mod 问题 | Larian 把"third-party mods"定义为"mods created using a program other than the official Toolkit"，并说明"while you can still use these mods, troubleshooting may look a little different"；官方支持页对 mod 问题的处理流程与原版不同 | 报 bug 前先移除 mod 复现；Larian 官方 FAQ 是否有逐字的"modded saves are not supported"表述**本次未能核实**（页面被拦截） | [11][12] |
| B7 | 框架类 mod（Community Library / CF / ImprovedUI）应该放在加载顺序的哪里 | **未能检索到一手的顺序规则**。已确认的顺序规则只有：翻译补丁要"放在原 mod 之下" | 以各框架 Nexus/GitHub 页面的说明为准；建议子课题 A/B 补充 | [21][46] |

### 2.3 职业 mod 特有坑（角色创建、升级、图标、本地化、进阶表冲突）

| # | 症状 | 原因 | 解决 / 预防 | 来源 |
|---|------|------|-------------|------|
| C1 | 角色创建界面看不到新职业 / 子职业 | `ClassDescriptions.lsx` 与 `Progressions.lsx` 未通过 UUID 正确连接："The TableUUID is an UUID which essentially ties together everything for the progression, and the starting point is inside ClassDescriptions.lsx which associates a table with the general description for a class"。子职业还需要出现在父职业进阶表的 SubClasses 列表中 | 逐一核对：ClassDescriptions 的 `ProgressionTableUUID` = Progressions 里该职业各 Level 节点的 `TableUUID`；子职业 UUID 同时出现在 ClassDescriptions（`ParentGuid`）与父职业 Progressions 的 SubClasses 中 | [6][7][8] |
| C2 | 你的子职业与别人的子职业 mod 只能"二选一"显示；多职业异常；被动/法术重复解锁 | 多个 mod 静态覆盖了同一条基础职业 `Progressions` 记录（后加载者赢）。CF Patch 的描述直接列出了这类症状："subclasses not showing up at all, multiclassing being broken, duplicated unlocks and conflicts with other mods that alter the same base classes" | 使用 Compatibility Framework："API endpoints that Script-Extender Enabled mods can hook into to insert values into Progressions and Spell/Skill/PassiveLists at Runtime"，即运行时注入而非覆盖。代价：依赖 SE（PC only） | [26][29][46][45] |
| C3 | Patch 8 之后官方新子职业（Cleric/Paladin/Warlock/Sorcerer 等）在角色创建里消失 | "Patch 8's new subclasses were added via Compatibility Framework to prevent older subclass mods from deleting them unintentionally"——旧式（静态覆盖）子职业 mod 会把官方新增子职业从列表里挤掉。社区排查中，移除旧版 ImprovedUI (IMP-UI) 及其关联 mod 也解决过此问题 | 子职业 mod 一律走 CF；用户侧安装 "Compatibility Framework Patch for Modded Subclasses"；更新/移除 IMP-UI | [26][27][30] |
| C4 | 职业图标 / 法术图标空白或显示占位符 | 三个硬性要求：扩展名必须**全大写 `.DDS`**（"mandatory"）；保存为 `.DDS DTX5, No Mipmaps`（"Mipmaps ... will only make your icons blurry"）；路径为 `Public\Game\GUI\Assets\<MODNAME>\ClassIcons`。用户"安装方式不对导致图标路径与 mod 预期不符"也是常见原因 | 导出时检查扩展名大小写与 mipmap 选项；不要让用户手动拷贝零散文件，只发 PAK | [31][32][33] |
| C5 | 名称/描述显示成一串 handle、或 stats 文件里出现 `ls::TranslatedStringRepository::s_HandleUnknown` | 官方文档："the Editor will try to generate a TranslatedStringHandle. If it fails to create loca, instead of a TranslatedStringHandle in the file, it will just say 'ls::TranslatedStringRepository::s_HandleUnknown'"——即**先建本地化文件再填 DisplayName**。另外 xml 未转 `.loca`、或语言目录名不对也会导致不显示 | 先按官方 "Setting Up" 步骤创建 Localization 文件；目录为 `Localization/<LanguageName>/`，语言名用英文（"German" 而非 "Deutsch"）；handle 格式如 `h00a33f75ge607g4aa2ga34ag4e2849aa53f9`，节点形如 `<content contentuid="h…" version="1">Text</content>`；"Do not edit contentuid or version" | [20][21][22] |
| C6 | 别人做的翻译/补丁覆盖了你的文本，或你的文本覆盖了别人的 | 两个 mod 使用了相同 `contentuid`；翻译补丁需"Place translation patches below original mods" | `[背景知识—非本次检索]` 自己的 handle 一律新生成，不要复用原版或他人 handle（除非有意覆盖）；发布时把 English 之外的语言放在同一 PAK 的对应语言目录 | [21] |
| C7 | 新施法职业与原版职业多职业后法术位数量/等级异常 | **未检索到针对 mod 职业的一手资料**。本次只检索到原版本身的多职业法术 bug（Sorlock 法术位、容器法术多职业失效）及其修复 mod，说明该系统在原版就脆弱 | 上线前至少实测：新职业 1 级 + 各类全施法者/半施法者/术士；`[背景知识—非本次检索]` 自定义施法职业需在 ClassDescriptions 正确设置 `SpellCastingAbility`、`MustPrepareSpells`、`SpellList` 等，并检查多职业法术位表是否把你的职业按全/半施法者计算 | [36] |
| C8 | Withers 重置后职业丢失 / 存档中角色变成"无职业" | **未检索到证据**。 | `[背景知识—非本次检索]` 在用户移除职业 mod 之前，应先让所有使用该职业的角色到 Withers 重置为原版职业，再保存、再卸载；作者应把这条写进 mod 页面 | — |
| C9 | 职业专属对话选项不出现 / NPC 把你当成别的职业 | **未检索到证据**。 | `[背景知识—非本次检索]` 原版对话通过职业 Tag 判断；自创职业若不挂任何原版职业 Tag，就没有职业专属对话；若复用原版 Tag（如 WIZARD），NPC 会把你当作该职业。需自行权衡并在页面说明 | — |
| C10 | 升级界面空白、没有可选法术/被动 | **未检索到一手资料**。 | `[背景知识—非本次检索]` 常见于 Progressions 的 Selectors 引用了不存在的 SpellList/PassiveList UUID、或 `Level` 节点缺少 `ProgressionType`/`TableUUID`。建议用 Toolkit 直接校验而非手写 lsx | — |

### 2.4 补丁与生命周期（Patch 7 / Patch 8 / SE / 存档）

| # | 症状 | 原因 | 解决 / 预防 | 来源 |
|---|------|------|-------------|------|
| D1 | 游戏更新当天所有 SE 类 mod 失效或崩溃 | "Script Extender versions target a specific game build; an SE version built for Patch 8 won't work with Patch 7 (and vice versa)"；"New extender versions are only released for the latest game version ... the Script Extender auto-updates; there is no new release on Github when a Script Extender update happens, the game will download and apply it automatically when launching" | 补丁日等待 SE 自动更新；排查口径（作者原话）："check if the error also appears when you have no mods loaded (only the script extender). If the error disappears with no mods, then it is caused by one of the mods"；"the vast majority of the time this is either a vanilla game bug or caused by a specific mod / invalid combination of mods / not upgrading mods" | [9] |
| D2 | Patch 8（"The Final Patch"）后大量 mod 失效 | Patch 8 加入 12 个官方子职业（College of Glamour、Path of the Giant、Death Domain、Circle of Stars、Arcane Archer、Drunken Master、Oath of the Crown、Swarmkeeper、Swashbuckler、Shadow Magic、Hexblade、Bladesinger）、照片模式与跨平台联机；社区判断"the most likely mods to become incompatible with Patch 8 will be non-mod.io Nexus mods, especially those based on script extender" | 子职业 mod 若与官方同名（如 Hexblade、Bladesinger）需处理重名/去重；所有 SE mod 等待 SE 与框架更新 | [27][43][28] |
| D3 | 想知道 Patch 8 之后是否还有会打坏 mod 的更新 | GitHub 上 SE 仍有 v31 (2026-04-17)、v32 (2026-06-21) 发布，说明 2026 年生态仍在维护；但对应的游戏 hotfix 内容与对 mod 的具体影响**本次未能确认** | 订阅 SE Releases 与 Larian 官方新闻；每次 hotfix 后回归测试 | [10] |
| D4 | 玩家中途卸载你的 mod 后存档报 missing mods / 读档异常 | "If a save had mods on it, those mods are baked into that save"；能带警告继续读档的前提是 mod 没有实质改动游戏内容；社区经验："Cosmetic and/or UI mods are almost always safe to add ... anything that alters existing content or adds new assets is sketchy"、"Don't try to remove game editing files like spell mods that add new spells or approval mods" | 职业 mod 属于最难安全移除的一类：页面必须写明"请勿在进行中的存档移除"；建议用户先 Withers 重置、再用社区的 mod uninstaller 类工具、确认无错误后再保存 | [34][35] |
| D5 | Toolkit 工程在补丁后打不开 / 需要重新导出 | **未能检索到一手资料** | 建议子课题 A 补充；作者侧预防：源文件（lsx/xml/png）纳入版本管理，不要只保留 PAK | — |
| D6 | PC 与主机之间共享存档失败 | Larian："cross-saves will not be compatible if your PC save is on a different game version, and it's recommended to ensure installed mods are available on console if you intend to play across both PC and console" | 若目标用户会跨平台，mod 必须同时在 mod.io 主机目录可用（意味着不能依赖 SE） | [12] |

### 2.5 平台与联机

| # | 症状 | 原因 | 解决 / 预防 | 来源 |
|---|------|------|-------------|------|
| E1 | 多人联机进不了房间 / 队友看不到职业 | Larian："If you are playing Multiplayer with mods, both you and your party will need to have the exact same mods installed, and they must be on the same version" | 所有人同 mod、同版本；用管理器 Installed 页的 "Update" 按钮统一版本 | [12] |
| E2 | 主机玩家装不了你的 mod | 主机只能通过游戏内管理器访问 mod.io 官方目录（Larian 与 mod.io 联合审核后才上架）；"Consoles (PlayStation and Xbox) have no official support for Script Extender"；主机目录"doesn't include Script Extender-dependent mods"；Toolkit 仅 PC（"requires a 64-bit processor and operating system"） | 想覆盖主机就必须：用官方 Toolkit 制作、上传 mod.io、通过审核、**不依赖 SE/CF** | [4][12][24][44] |
| E3 | Mac 玩家装了 SE 没反应 | "Mac OS has no official support for Script Extender" | Mac 用户只能用非 SE mod；Mac 的 `modsettings.lsx` 路径见 B1 | [5][24] |
| E4 | Linux / Steam Deck 下 SE 不生效，BG3MM 显示红色感叹号 | 需要在启动参数加 `WINEDLLOVERRIDES="DWrite.dll=n,b" %command%`（Steam Deck 指南另加 `PROTON_NO_ESYNC=1`）；SE 安装方式是把 `DWrite.dll` 放到 `Baldurs Gate 3\bin`；"BG3MM will sometimes fail to recognize a Script Extender install on Linux/Steam Deck ... even though Script Extender is installed correctly" | 按上述参数配置；BG3MM 的误报可忽略，以游戏内 SE 控制台/日志为准 | [23][24][25] |
| E5 | 荣誉模式 / 成就是否会被 mod 关闭 | 本次检索到的 Steam 讨论称"If you run your game with mods enabled, whether they're third-party or installed through the Mod browser, your in-game achievements will automatically be disabled"，并提到 Achievement Enabler / SE 设置可重新开启。**但**`[背景知识—非本次检索]` 我的记忆是 Larian 在 Patch 7 官方 mod 支持上线时表示使用 mod 不会禁用成就，两者矛盾，**需以 Larian 官方 Patch 7 说明为准，本次未能核实** | 在 mod 页面不要对成就状态做承诺，引导用户看官方说明 | [37][38] |

---

## 3. 政策与法务小节

### 3.1 Larian 官方 Modding Terms（最后更新 2024-05-30）[14]

本次只拿到检索摘要中的原文片段（PDF 抓取 403）：

- 原创性："Any element of your Mod must be your own original work or you must have obtained the necessary permissions to use such element."
- 禁止商业化："You shall not sell, rent, lease, license, distribute or otherwise transfer or exploit the Baldur's Gate 3 Toolkit and/or Mods or any copies thereof, for money or other benefits."
- 责任归属："You are responsible for the content of any Mods which you create and publish in the Modding Library." / "You are solely responsible for your Mod and may be held liable for any Mod which you create and upload to the Modding Library."
- 下架权："LARIAN STUDIOS and mod.io reserve the right to remove any Mods from the Modding Library which violates these terms."

**未能核实**：条款对"捐赠 / Patreon 抢先体验"的具体口径、对 Nexus 等非 mod.io 渠道是否同样适用、以及对 WotC 内容的专门条款。

### 3.2 mod.io《Modding Guidelines & FAQ》[15][16]

检索摘要中的要点：

- "The in-game mod manager does not allow NSFW content."（摘要提示 PC 端 mod.io 网站与主机/游戏内目录的规则可能不同，未能核实细节）
- "You won't be allowed to upload anything copyrighted."
- "Baldur's Gate 3, as a Dungeons & Dragons game licensed by partners, has certain guidelines in place to ensure the integrity of the game's universe."——即除通用规则外还有一层"D&D 世界观完整性"准则，具体条文未能抓取。
- 主机目录由 Larian 与 mod.io 联合审核，通过者才在游戏内浏览器出现；目录不含依赖 SE 的 mod（见 E2）。[4][44]

### 3.3 Nexus Mods

本次只检索到 Nexus 的 Donation Points 权限机制（作者可设置"允许/需许可/不允许"他人用其素材赚取 DP）[48]，以及一例因版权问题被删除的音乐替换 mod 页面标题（"No Copyright Tracks - Music Replacer - DELETED"）。Nexus 关于付费墙、必须免费下载、素材授权的总则**本次未检索**；`[背景知识—非本次检索]` Nexus 要求上传内容免费可得，使用他人素材须在权限说明中获得许可，侵权投诉会导致下架。

### 3.4 Wizards of the Coast 内容授权 [17][18][19]

已从 D&D Beyond 官方 SRD 页面核实：

| 版本 | 许可 | 发布 | 说明 |
|---|---|---|---|
| SRD 5.1 | CC-BY-4.0 与 OGL 1.0a | — | 2014 规则版本 |
| SRD 5.2 | 仅 CC-BY-4.0 | 2025-04-22 | 2024 规则版本 |
| SRD 5.2.1 | 仅 CC-BY-4.0 | 2025-05-01 | 5.2 修订版 |

- 三个版本均"irrevocably available"，WotC 不能撤回或修改已发布的 CC 版本。
- **唯一义务是署名**："The only requirement is that the user must provide attribution"，署名文本按各版本前言 (preamble) 的要求写。
- 5.2/5.2.1 收录：全部核心职业（2024 规则与措辞）、种族 Dragonborn/Dwarf/Elf/Gnome/Goliath/Halfling/Human/Orc/Tiefling、背景 Acolyte/Criminal/Sage/Soldier、15 个新专长、20 个新增法术（如 Chromatic Orb、Hex）、若干怪物与魔法物品（部分商标名被改写，如 "Mysterious Deck" 替代 "Deck of Many Things"）。`[背景知识—非本次检索]` 每个职业只收录一个子职业（如 Berserker、Lore、Life、Land、Champion、Open Hand、Devotion、Hunter、Thief、Draconic、Fiend、Evoker）——本次抓取的页面未列出具体子职业名，需以 SRD 5.2.1 原文核对。
- **明确未收录**：Artificer、Aasimar，以及 Beholder、Mind Flayer、Strahd、Orcus、Tiamat 等——"excluded based on brand identity protection, licensing strategy, and intellectual property rights"。

由此推论（基于以上检索结果的分析，非法律意见）：

1. **Tasha's Cauldron / Xanathar's 的子职业、Artificer、Critical Role 的 Blood Hunter 都不在任何 SRD 里**。逐字复制其文本、特性名、图标进 mod 属于未授权使用（Larian 条款要求"原创或已获许可"、mod.io 禁止"anything copyrighted"）。`[背景知识—非本次检索]` Blood Hunter 的权利人是 Critical Role/Matthew Mercer 而非 WotC；游戏规则机制本身通常不受版权保护，但表达（文本、名称、美术）受保护——这是社区大量"非 SRD 子职业 mod"长期存在的灰色地带，被下架的风险取决于权利人是否主张。
2. **Patch 8 官方子职业**（Hexblade、Bladesinger、Swashbuckler 等）本身就是非 SRD 内容，Larian 能做是因为其与 WotC 有授权；mod 作者并不因此获得同等授权。
3. **完全自创职业相对安全的理由**：不复制任何 WotC/第三方文本与名称；若借用 SRD 的通用机制（法术位、熟练加值、SRD 法术）只需附 CC-BY-4.0 署名。**仍需注意**：(a) 职业/子职业/特性命名避开 WotC 已有产品名与 Product-Identity 式专名（Beholder、Mind Flayer 等）；(b) 图标、原画、字体、音效必须自绘或使用允许再分发的许可（CC0/OFL 等），不要从 D&D Beyond、其他游戏或画师作品裁切；(c) mod 标题里使用 "Baldur's Gate 3" 属社区惯例，但不要暗示官方出品；(d) 若接受捐赠，不要把 mod 或 Toolkit 产物作为付费/抢先体验对价（Larian 条款"for money or other benefits"）。

---

## 4. 对"自创职业 mod"项目的具体建议 / 决策点

1. **新职业 vs 子职业**：新职业拥有自己的 `ClassDescriptions` 与 `Progressions` 表，不需要改写任何原版职业条目，因此天然避开 C2/C3 这类"Progressions 覆盖战"，也不依赖 CF/SE，可上主机目录。代价是所有东西（图标、装备、本地化、Tag、多职业法术位）都要自己提供并测试。若你的职业还要带自定义子职业，它们挂在你自己的表下，同样不与他人冲突。[6][26][29]
2. **是否依赖 Script Extender** 应在第一天决定：依赖 SE = 仅 Windows/Linux(Proton)，无 Mac、无主机，每次补丁有失效期；不依赖 SE = 可上 mod.io 主机目录、跨平台联机友好。[9][12][24][44]
3. **发布渠道**：走官方 Toolkit → mod.io（可达主机与跨平台，但要过审、无 NSFW、受 Larian 条款约束）与 Nexus（可用 SE、更自由）可以并行，但要保证两边 **UUID 相同、Version64 同步**，否则玩家联机会因"版本不一致"失败。[1][12]
4. **版本纪律**：UUID 一经发布永不改变；每次发版重新生成 `Version64`；改动进阶表的版本在页面标注"需要新存档/需要 Withers 重置"。[1]
5. **本地化先行**：在 Toolkit 里先创建 Localization 文件再填任何 DisplayName，避免 `s_HandleUnknown`；语言目录用英文名；中文目录名`[背景知识—非本次检索]`通常为 `Chinese`（简体）与 `ChineseTraditional`，请以游戏 `Localization` 目录内实际文件夹名为准。[20][21]
6. **图标流水线固定化**：DXT5、无 mipmap、大写 `.DDS`、放 `Public\Game\GUI\Assets\<MODNAME>\ClassIcons`，写成脚本避免手工出错。[31][32]
7. **补丁日 SOP**：先禁用全部 mod 验证原版可启动 → 等 SE 自动更新 → 只开 SE 复现 → 逐个恢复；在 mod 页置顶当前兼容的游戏版本号。[9][13]
8. **法务清单**：只用自创文本；SRD 内容附 CC-BY-4.0 署名（把署名段落放进 mod 描述与 PAK 内 README）；素材来源与许可清单随源码保存；命名避开 WotC 专名。[14][15][17]
9. **给玩家的告示模板**（应写进 mod 页）：所有联机玩家须同版本；不要在进行中的存档移除；卸载前先 Withers 重置；Mac/主机不支持（若依赖 SE）。[12][35]

---

## 5. 未解决问题与信息缺口

1. **Larian 官方支持页原文**（mod-issues_112、official-mod-support_113、errors-or-crashes_82）与 **Modding Terms PDF** 抓取被拦截/403，本报告只引用了 WebSearch 摘要中的片段；"modded saves not supported"是否有逐字表述、成就是否被 mod 禁用（E5 存在矛盾）、捐赠口径——均未核实。
2. **mod.io 准则全文**（NSFW 定义、"D&D 世界观完整性"准则具体条文、审核时长、主机与 PC 目录的差异）未能抓取。
3. **官方 Toolkit 文档**（`docs.baldursgate3.game/Adding_Classes_and_Subclasses`）403，Selectors 语法、`ProgressionType`、多职业法术位对自定义职业的处理、Withers 重置行为、Tag 与对话的关系（C7–C10）缺少一手资料。
4. **wiki.bg3.community** 的 Patch 7 Troubleshooting、Creating meta.lsx、Basic Class Creation、Removing mods from a save、Compatibility Framework Usage 页面为 JS 渲染，只拿到标题；建议主流程用浏览器工具直接阅读这几页（链接见来源 [3][2][34][46]）。
5. **Patch 8 之后的 hotfix 时间线**及各次 hotfix 对 mod/SE 的具体影响未能确认；仅知 SE 在 2026-04 与 2026-06 仍有发布 [10]。
6. **框架类 mod 的加载顺序规则**（Community Library / CF / ImprovedUI 相对位置）未检索到一手说明（B7）。
7. **PAK 路径大小写敏感性**在 Linux/Proton 下的实际表现未检索到证据（A9）。
8. **Nexus 总则**（免费、素材授权、下架流程）未检索。
9. **SRD 5.2.1 具体收录哪些子职业**：抓取页面只说"a mix of ... subclasses ... from the 2024 Player's Handbook"，未列名单。
10. **Patch 7 / Patch 8 的确切发布日期**本次未从检索结果中取得；`[背景知识—非本次检索]` 分别为 2024-09-05 与 2025-04-15。

---

## 6. 来源列表

类型：一手 = 官方/作者本人；二手 = 社区 wiki、框架维护者、mod 作者页；三手 = 媒体/聚合站/论坛转述。访问日期均为 2026-09-02。"获取方式"说明该来源内容是完整抓取还是仅有搜索摘要。

| # | 标题 | URL | 类型 | 获取方式 |
|---|------|-----|------|----------|
| 1 | bg3.wiki — Modding:Meta.lsx（Creating meta.lsx） | https://bg3.wiki/wiki/Modding:Creating_meta.lsx | 二手 | WebFetch 成功 |
| 2 | BG3 Modding Community Wiki — Creating a meta.lsx file | https://wiki.bg3.community/Tutorials/General/creating_meta | 二手 | 仅搜索摘要（抓取仅返回标题） |
| 3 | BG3 Modding Community Wiki — Patch 7 Troubleshooting | https://wiki.bg3.community/en/Tutorials/patch7-troubleshooting | 二手 | 仅链接（抓取仅返回标题） |
| 4 | bg3modmanager.net — Troubleshooting / "Mod Was Not Imported" / modsettings.lsx Keeps Resetting / Larian In-Game Mod Manager Guide | https://bg3modmanager.net/troubleshooting/ ; https://bg3modmanager.net/bg3-mod-manager-mod-was-not-imported-fix/ ; https://bg3modmanager.net/modsettings-lsx-keeps-resetting-fix/ ; https://bg3modmanager.net/larian-in-game-mod-manager-guide/ | 三手 | 搜索摘要 |
| 5 | Nexus — modsettings.lsx and General Mod Troubleshooting for Mac Users (Patch 7)（mod 12356，Posts） | https://www.nexusmods.com/baldursgate3/mods/12356?tab=posts | 二手 | 搜索摘要 |
| 6 | Community Library Wiki — Building a Class Mod | https://github.com/BG3-Community-Library-Team/BG3-Community-Library/wiki/Building-a-Class-Mod | 二手 | 搜索摘要 |
| 7 | Larian 官方 Toolkit 文档 — Adding Classes and Subclasses | https://docs.baldursgate3.game/Adding_Classes_and_Subclasses | 一手 | 仅链接（抓取 403） |
| 8 | Community Library Wiki — Adding a Subclass to the Subclass Compatibility Framework | https://github.com/BG3-Community-Library-Team/BG3-Community-Library/wiki/Adding-a-Subclass-to-the-Subclass-Compatibility-Framework | 二手 | 搜索摘要（抓取仅返回首页） |
| 9 | Nexus — Baldur's Gate 3 Script Extender (BG3SE)（mod 2172，作者说明） | https://www.nexusmods.com/baldursgate3/mods/2172 | 一手 | 搜索摘要 |
| 10 | GitHub — Norbyte/bg3se Releases v31 (2026-04-17)、v32 (2026-06-21) | https://github.com/Norbyte/bg3se/releases/tag/v31 ; https://github.com/Norbyte/bg3se/releases/tag/v32 | 一手 | 仅标题 |
| 11 | Larian Support — Mod Issues | https://larian.com/support/faqs/mod-issues_112 | 一手 | 搜索摘要（抓取被拦截） |
| 12 | Larian Support — Official Mod Support | https://larian.com/support/faqs/official-mod-support_113 | 一手 | 搜索摘要（抓取 403） |
| 13 | Larian Support — Errors or Crashes When Loading Saves | https://larian.com/support/faqs/errors-or-crashes-when-loading-saves_82 | 一手 | 搜索摘要 |
| 14 | Larian — Baldur's Gate 3 Modding Terms（PDF，Last updated May 30, 2024） | https://baldursgate3.game/mods/Larian_BG3_Modding_Terms.pdf | 一手 | 搜索摘要（抓取 403） |
| 15 | mod.io — Modding Guidelines & FAQ guide for Baldur's Gate 3 | https://mod.io/g/baldursgate3/r/modding-guidelines | 一手 | 搜索摘要（抓取仅返回标题） |
| 16 | Larian — Community Update #27: Official Modding Support | https://baldursgate3.game/news/community-update-27-official-modding-support_118 | 一手 | 仅链接 |
| 17 | D&D Beyond — SRD v5.2.1 System Reference Document | https://www.dndbeyond.com/srd | 一手 | WebFetch 成功 |
| 18 | Screen Rant — Everything To Know About D&D 2024's New SRD 5.2 Creative Commons License | https://screenrant.com/dnd-2024-srd-52-creative-commons-license-explainer/ | 三手 | 搜索摘要 |
| 19 | D&D Beyond — You Can Now Publish Your Own Creations Using the New Core Rules | https://www.dndbeyond.com/posts/1949-you-can-now-publish-your-own-creations-using-the | 一手 | 仅链接 |
| 20 | Larian 官方 Toolkit 文档 — Adding Localisation | https://docs.baldursgate3.game/index.php?title=Adding_Localisation | 一手 | 搜索摘要 |
| 21 | bg3.wiki — Modding:Localization | https://bg3.wiki/wiki/Modding:Localization | 二手 | WebFetch 成功 |
| 22 | Nexus 文章 643 — How to Translate these Mods for your language | https://www.nexusmods.com/baldursgate3/articles/643 | 二手 | 搜索摘要 |
| 23 | Steam 指南 — Installing BG3 Mod Manager + Script Extender on Steam Deck | https://steamcommunity.com/sharedfiles/filedetails/?id=3545134209 | 二手 | 搜索摘要 |
| 24 | BG3 Modding Community Wiki — Installing Script Extender | https://wiki.bg3.community/en/Tutorials/Mod-Use/How-to-install-Script-Extender | 二手 | 搜索摘要 |
| 25 | GitHub — Norbyte/bg3se Issue #206: Steam Deck - Script Extender Mods not working | https://github.com/Norbyte/bg3se/issues/206 | 二手 | 搜索摘要 |
| 26 | Nexus — Compatibility Framework Patch for Modded Subclasses（mod 17062） | https://www.nexusmods.com/baldursgate3/mods/17062 | 二手 | 搜索摘要 |
| 27 | Larian — The Final Patch: New Subclasses, Photo Mode, and Cross-play | https://baldursgate3.game/news/the-final-patch-new-subclasses-photo-mode-and-cross-play_138 | 一手 | 搜索摘要 |
| 28 | Nexus News — Baldur's Gate 3 - Patch 8 | https://www.nexusmods.com/news/15251 | 二手 | 仅链接（抓取 403） |
| 29 | GitHub — BG3-Community-Library-Team/BG3-Compatibility-Framework Readme | https://github.com/BG3-Community-Library-Team/BG3-Compatibility-Framework/blob/main/Readme.md | 一手（框架作者） | 搜索摘要 |
| 30 | Screen Plays Mag — New Subclasses Not Showing Up Solution In BG3 After Patch 8 | https://screenplaysmag.com/blog/new-subclasses-not-showing-up-solution-in-bg3-baldurs-gate-3-after-patch-8/ | 三手 | 搜索摘要 |
| 31 | bg3.wiki — Modding:Class icons | https://bg3.wiki/wiki/Modding:Modding_class_icons | 二手 | 搜索摘要 |
| 32 | BG3 Modding Community Wiki — Icon Creation | https://wiki.bg3.community/Tutorials/Icons/Icon-Creation | 二手 | 搜索摘要 |
| 33 | Steam 讨论 — Modded class icons and resources not working | https://steamcommunity.com/app/1086940/discussions/0/5513030395223517345/ | 三手 | 搜索摘要 |
| 34 | BG3 Modding Community Wiki — Removing mods from a save | https://wiki.bg3.community/Tutorials/Mod-Use/Removing-mods-from-a-save | 二手 | 仅链接 |
| 35 | Steam 讨论 — BG3 not loading saves if mods were removed before Patch… | https://steamcommunity.com/app/1086940/discussions/0/4032473436326422915/ | 三手 | 搜索摘要 |
| 36 | Nexus — Warlock Multiclass (Sorlock) Bug Fix and Workaround（1122）/ Container Spells Multiclassing Fix（17949） | https://www.nexusmods.com/baldursgate3/mods/1122?tab=posts ; https://www.nexusmods.com/baldursgate3/mods/17949?tab=posts | 二手 | 搜索摘要 |
| 37 | Steam 讨论 — Mod support and Honor mode | https://steamcommunity.com/app/1086940/discussions/0/4848777893532107749/ | 三手 | 搜索摘要 |
| 38 | Nexus — Achievement Enabler（668，Posts） | https://www.nexusmods.com/baldursgate3/mods/668?tab=posts | 二手 | 仅链接 |
| 39 | GitHub — LaughingLeader/BG3ModManager Issue #22: modsettings.lsx removes mods when game is launched | https://github.com/LaughingLeader/BG3ModManager/issues/22 | 二手 | 仅标题 |
| 40 | GitHub — Norbyte/bg3se Issue #76: Scriptextender resets my modsettings.lsx | https://github.com/Norbyte/bg3se/issues/76 | 二手 | 仅标题 |
| 41 | bg3.wiki — Modding:LSX files / Modding:PAK files | https://bg3.wiki/wiki/Modding:LSX_files ; https://bg3.wiki/wiki/Modding:PAK_files | 二手 | 搜索摘要 |
| 42 | RPGHQ — [BG3] Modding BG3 - Getting Started | https://rpghq.org/forums/viewtopic.php?t=1617 | 三手 | 搜索摘要 |
| 43 | Steam 讨论（Patch 8 与 Nexus/mod.io mod 兼容性；search-4 结果集，具体楼层未定位） | https://steamcommunity.com/app/1086940/discussions/3/3823048658580701404 | 三手 | 搜索摘要 |
| 44 | thegamercodex — Baldur's Gate 3 Script Extender | https://thegamercodex.com/en/baldurs-gate-3/tools/bg3-script-extender | 三手 | 搜索摘要 |
| 45 | GitHub — FrederickEngelhardt/bg3-progressions-compatibility-patches | https://github.com/FrederickEngelhardt/bg3-progressions-compatibility-patches | 二手 | 仅链接 |
| 46 | BG3 Modding Community Wiki — Compatibility Framework Usage | https://wiki.bg3.community/Tutorials/Mod-Frameworks/compatibility-framework | 二手 | 仅链接 |
| 47 | GitHub — Norbyte/bg3se README（仅取得 ScriptExtenderSettings.json 配置表） | https://github.com/Norbyte/bg3se | 一手 | WebFetch 部分成功 |
| 48 | Nexus — Baldur's Gate 3 Community Library（1333，Donation Points 权限说明） | https://www.nexusmods.com/baldursgate3/mods/1333 | 二手 | 搜索摘要 |
| 49 | Larian 论坛 — modsettings.lsx keeps resetting | https://forums.larian.com/ubbthreads.php?ubb=showflat&Number=933789 | 三手 | 仅链接 |
| 50 | Nexus 论坛 — [SOLVED] Game says mods disabled, but they are enabled in BG3MM | https://forums.nexusmods.com/topic/13441922-solved-game-says-mods-disabled-but-they-are-enabled-in-bg3mm-please-help/ | 三手 | 仅链接 |

---

## 7. 审计

| 项目 | 数值 | 说明 |
|---|---|---|
| WebSearch 查询数 | 20 | 全部返回结果（0 次失败）；预算 20，已用尽 |
| WebFetch 抓取数 | 14 | 预算约 14，已用尽 |
| WebFetch 成功 | 3 完整 + 1 部分 | 成功：[1] bg3.wiki Meta.lsx、[17] D&D Beyond SRD、[21] bg3.wiki Localization；部分：[47] bg3se README（只拿到配置表） |
| WebFetch 失败 | 10 | 403：larian.com official-mod-support、docs.baldursgate3.game、nexusmods.com/news、baldursgate3.game Modding Terms PDF；域名被安全策略拦截：larian.com mod-issues；仅返回标题（JS 渲染）：wiki.bg3.community ×3（patch7-troubleshooting、creating_meta、Basic-Class-Creation）、mod.io guidelines、Community Library GitHub wiki |
| 连续失败停止 | 触发 | 最后 3 次抓取（docs.baldursgate3.game、Nexus news、Larian PDF）连续 403，按规则停止；预算亦已耗尽 |
| 重试情况 | 未执行"等 3 秒重试一次" | 原因：失败均为结构性（JS 渲染无正文 / 域名拦截 / 403），重试预期无效且预算有限。此为对纪律的偏离，如实记录 |
| 收到来源数（链接条目，含重复） | 约 200 | 20 次搜索共返回约 201 条链接，去重后约 90 个不同 URL |
| 引用来源数 | 50 | 见第 6 节；其中一手 15、二手 24、三手 11（回读核对后修正） |
| 背景知识标注 | 12 处 | 均以 `[背景知识—非本次检索]` 标出，不计入来源 |
