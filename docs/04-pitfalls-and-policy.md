# 04 · 踩坑清单（症状 → 原因 → 解决）与政策 / 法务

> 来源：`research/D-pitfalls.md`（D）、`research/G-official-docs-browser.md`（G）、`research/B-class-mod-anatomy.md`（B）。带 `[背景知识]` 的条目未经本次检索证实，需在 Windows 侧实测。

## 1. 打包 / 元数据

| # | 症状 | 原因 | 解决 / 预防 |
|---|---|---|---|
| A1 | BG3MM 报 "Mod Was Not Imported"；或 mod 出现在 Overrides 区（橙色）而不是加载顺序 | PAK 里没有可解析的 `Mods/<Folder>/meta.lsx`（缺 `ModuleShortDesc`、XML 不合法、层级错） | 固定路径 `Mods/<Folder>/meta.lsx`；保留 XML 声明与 `<version …/>` 节点；**meta.lsx 保持 .lsx 不要转 .lsf** D[1][4] |
| A2 | mod 能启用但职业/法术/文本全不生效 | `meta.lsx` 的 `Folder` 与 `Mods/<Folder>`、`Public/<Folder>` 目录名不一致 | 三处逐字一致；改名时同步改 D[1][2][42] |
| A3 | mod 莫名不加载 | `Name` 里出现"连字符后接 b"（`-b`），bg3.wiki 记录为 mod loader 硬编码限制 | 命名避开 `-b` D[1] |
| A4 | 装了你的 mod 后另一个 mod 消失 / 更新后被当成另一个 mod | `UUID` 复制自模板未改 | 每个 mod 一个 v4 UUID 且终身不变 D[1][2] |
| A5 | 发新版后管理器/依赖方看不到更新 | `Version64` 未重新生成 | 每次发版重算（`scripts/version64.py`）；Toolkit 的 Build 号会自动递增 G[G6] |
| A6 | 提示缺依赖 / 框架功能不生效 | `Dependencies` 缺失或 UUID/Folder/Name/Version64 与被依赖 mod 不一致 | 用其他 mod 资源必须正确声明；声明版本不要高于用户实际版本 D[1] |
| A7 | `.lsx` 数据不被读取 / 本地化不显示 | 游戏读二进制 `.lsf` 与 `.loca`；Multitool 只自动转换 `x.lsf.lsx`、`x.loca.xml` 命名的文件 | 遵守命名约定，或用 Divine 手动转换 D[21][22][41] |
| A8 | `MD5`、`Tags` 不知填什么 | 模板留空即可 | 留空 D[1] |
| A9 | Linux/Proton 下资源找不到 | `[背景知识]` 路径大小写敏感 | 与原版路径大小写完全一致；图标扩展名按官方/社区要求 D[31] |

## 2. 加载 / 管理

| # | 症状 | 原因 | 解决 / 预防 |
|---|---|---|---|
| B1 | Patch 7 后 `modsettings.lsx` 在哪、还改不改 | 位置未变：`%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\PlayerProfiles\Public\modsettings.lsx`（Mac：`~/Documents/Larian Studios/Baldur's Gate 3/PlayerProfiles/Public/`）；不再需要手改 | 由游戏内 Mod 管理器或 BG3MM 二选一来写 D[5] A[25] |
| B2 | 启动后 mod 被清空 / "游戏说 mod 已禁用但 BG3MM 里是启用的" | (a) 游戏内管理器与 BG3MM 同写一个文件互相覆盖；(b) 某个 mod 出错导致游戏清空整个加载顺序；(c) 列表里的 UUID 在 Mods 目录找不到对应 pak | 只用一个管理器；二分排查；保证每个 UUID 有 pak；BG3MM 记得 Export to Game D[4][39][40] A[30] |
| B3 | 换机/重启后加载顺序回滚，出现 `-conflict` 文件 | Steam Cloud 同步冲突 | 关闭该游戏云同步 D[4] |
| B4 | 老教程叫装 Mod Fixer | Patch 7 起不需要，但不致错 | 新 mod 不要捆绑 D[5] C[42] |
| B5 | 大更新后崩溃 / 读档报错 | Larian 官方建议大更新后先移除 mod 排查 | 补丁日 SOP（见 §6）D[13] |
| B6 | 想找官方支持 | Larian 把 Toolkit 之外做的 mod 定义为 "third-party"，排障流程不同 | 报 bug 前先移除 mod 复现 D[11][12] |
| B7 | 框架 mod 放哪 | 一手规则只找到"CF 放最底部"、"翻译补丁放原 mod 之下" | 以各框架页面为准 C[3] D[21][46] |

## 3. 职业 mod 特有

| # | 症状 | 原因 | 解决 / 预防 |
|---|---|---|---|
| C1 | 角色创建看不到新职业/子职业 | ClassDescriptions 与 Progressions 没通过 UUID 正确连接；没有 Level 1 节点；子职业不在父职业 `SubClasses` 里 | 核对 `ProgressionTableUUID` = 各级 `TableUUID`；子职业 UUID 同时出现在 ClassDescriptions（`ParentGuid`）与父职业 SubClasses D[6][7][8] B[5][13] |
| C2 | 你的子职业和别人的只能二选一；多职业坏；被动重复解锁 | 多个 mod 整节点覆盖同一条原版 Progression（后加载者赢） | Patch 7 合并节点（新 UUID + 原版 TableUUID + 同 Level）或 CF 注入 D[26][29] B[17] |
| C3 | Patch 8 后官方新子职业消失 | 旧式覆盖型子职业 mod 把它们挤掉；旧版 ImpUI 也会导致不显示 | 子职业一律走合并/CF；更新或移除 ImpUI D[26][27][30] |
| C4 | 职业/法术图标空白或占位符 | 类图标：文件名 ≠ `Name`、没走 Convert UI Assets、缺 AssetsLowRes；技能图标：atlas 名重复、mipmap、扩展名大小写（旧方法要求大写 `.DDS`、DXT5、无 mipmap） | 按 02 文档 §5 的官方路径与尺寸；保存后重启 Editor G[G8] D[31][32][33] |
| C5 | 名称显示成 handle 串 / stats 里出现 `ls::TranslatedStringRepository::s_HandleUnknown` | 先填了 DisplayName 后建本地化；xml 未转 loca；语言目录名不对（要 `English`、`Chinese`） | 先建 Localization 文件再填 DisplayName；目录用官方语言名；`reloadLoca` G[G7] D[20][21] |
| C6 | 你的文本被别人覆盖 / 覆盖别人 | 相同 `contentuid` | 自己的 handle 一律新生成；翻译补丁放原 mod 之下 D[21] |
| C7 | 多职业后法术位异常 | 原版多职业法术位系统本身脆弱（Sorlock、容器法术 bug 有专门修复 mod） | 上线前实测：新职业 1 级 + 各类全/半施法者/术士；正确设置 `SpellCastingAbility`、`MustPrepareSpells` D[36] |
| C8 | Withers 重置后职业丢失 / 卸载后角色无职业 | `[背景知识]` | 页面写明"卸载前先到 Withers 重置为原版职业再保存" |
| C9 | 职业专属对话不出现 / NPC 把你当别的职业 | `[背景知识]` 原版对话按职业 Tag 判断 | 决定是否复用原版 Tag，并在页面说明（见 02 §3.6） |
| C10 | 升级界面空白、没有可选法术/被动 | `[背景知识]` Selectors 引用了不存在的 List UUID；节点缺 `ProgressionType`/`TableUUID` | 用 `scripts/check_mod.py` 做引用校验；优先用 Toolkit 校验 |
| C11 | 12→13 级升级黑屏（玩家装了 UnlockLevelCurve） | 职业缺 13–20 级节点 | 补空节点或声明不兼容 B[28] |
| C12 | 自定义行动资源没有图标 / 反应界面红星 | 资源图标仍依赖 ImpUI（已停更），手动导出的 DDS 不显示 | 优先复用原版资源或隐藏资源；必须自定义时按 Djmr 指南 + Convert UI Assets B[18] |
| C13 | 升级界面不能即时显示新增法术位；物品联动只对原版施法者生效 | 引擎 UI 限制（Artificer 作者说明） | 页面写明"回到场景后生效" F[4] |

## 4. 补丁与生命周期

| # | 症状 | 原因 | 解决 / 预防 |
|---|---|---|---|
| D1 | 更新当天 SE 类 mod 全失效 | SE 只服务最新游戏版本，自动更新，GitHub 不一定发新 release | 等 SE 自动更新；排查口径：只开 SE 不开 mod 复现 D[9] |
| D2 | Patch 8 后大量 mod 失效 | 12 个官方子职业 + 数据变化；"最可能失效的是非 mod.io 的 SE 类 Nexus mod" | 同名子职业（Hexblade、Bladesinger…）处理重名；SE mod 等框架更新 D[27][43] |
| D3 | Patch 8 之后还有没有会打坏 mod 的更新 | SE 2026-04/06 仍在发版，说明有 hotfix；具体影响未确认 | 订阅 SE Releases 与 Larian 新闻；每次 hotfix 回归测试 D[10] |
| D4 | 玩家中途卸载 mod 后存档报 missing mods | "mod 一旦被存档加载就烤进存档"；内容类 mod（新职业/法术）最难安全移除 | 页面写明"不要在进行中的存档移除"；卸载前 Withers 重置 D[34][35] |
| D5 | Toolkit 工程补丁后打不开 | 未检索到一手资料 | 源文件入 git，不要只留 pak |
| D6 | PC 与主机存档不互通 | 版本或 mod 不一致 | 跨平台用户 → mod 必须在 mod.io 主机目录可用（不能依赖 SE）D[12] |

## 5. 平台与联机

| # | 症状 | 原因 / 规则 | 解决 |
|---|---|---|---|
| E1 | 联机进不了房间 | 所有人需相同 mod 且版本一致；加入大厅时会提示下载缺失/启停不匹配 mod G[G9] | 统一版本 |
| E2 | 主机玩家装不了 | 主机只能用 mod.io 官方目录，且排除 `.dll`/新种族/shader 等 G[G9] | Toolkit 制作 + mod.io + 不依赖 SE/CF |
| E3 | Mac 玩家装 SE 没反应 | Mac 原生版无官方 SE | Mac 用户只能用非 SE mod A[42] |
| E4 | Linux/Steam Deck SE 不生效、BG3MM 红色感叹号 | 需要 `WINEDLLOVERRIDES="DWrite.dll=n,b" %command%`；BG3MM 误报可忽略 | 按参数配置，以游戏内 SE 控制台为准 D[23][24][25] |
| E5 | 成就会不会被关 | **mod.io 官方准则页：启用任何 mod 后成就自动禁用**；SE 有重新开启成就的设置 | 页面不要对成就做承诺，引导看官方说明 G[G9] A[34] |

## 6. 补丁日 SOP（作者侧）
1. 先禁用全部 mod 验证原版可启动 → 2. 等 SE 自动更新（若有 SE 模块）→ 3. 只开 SE 复现 → 4. 逐个恢复框架 → 自己的 mod → 5. 跑 06 文档的测试矩阵 → 6. 在 mod 页置顶当前兼容的游戏版本，必要时标 "(Deprecated)"。建议 72 小时内完成烟测 F[表 B]。

## 7. 政策与法务

### 7.1 Larian Modding Terms（2024-05-30）与 mod.io 准则 D[14][15] G[G9]
- 任何元素（音频、代码、资源、视觉）必须原创或已获许可；不得与**可识别的第三方品牌、角色或人物相似**；未经许可不得含 Larian 其他游戏或第三方内容；不得含恶意代码。
- 不得为金钱或其他利益出售/出租/许可 Toolkit 或 Mod；不得只用 mod.io 给付费/第三方 mod 打广告；不得解锁付费或成就相关物品。
- 内容：不得歧视/淫秽/违法；缩略图不得裸露；主机不接受增加裸露/暴力的 mod。
- 署名：可署团队成员与灵感来源；**未获许可不得把他人 mod 扩展/翻译/重制后署原作者**。
- AI 生图：需遵守所用文生图服务的许可条款，并对其合法性负责。
- 多次违规或原样重传会被取消上传权限。

### 7.2 Wizards of the Coast 内容授权 D[17][18][19]
| 版本 | 许可 | 发布 |
|---|---|---|
| SRD 5.1 | CC-BY-4.0（另有 OGL 1.0a） | 2014 规则 |
| SRD 5.2 / 5.2.1 | 仅 CC-BY-4.0，不可撤销 | 2025-04-22 / 2025-05-01（2024 规则） |
- 唯一义务是**署名**（按各版本前言的要求写）。
- 5.2 收录全部核心职业（每职业一个子职业，具体名单需核对原文）、部分种族/背景/专长/法术。
- **明确未收录**：Artificer、Aasimar、Beholder、Mind Flayer、Strahd、Orcus、Tiamat 等。
- Tasha's / Xanathar's 子职业、Critical Role 的 Blood Hunter 都不在任何 SRD 内——逐字复制其文本/特性名/图标属未授权使用；社区大量此类 mod 长期存在属于灰色地带，风险取决于权利人是否主张。
- Patch 8 官方子职业（Hexblade、Bladesinger…）是 Larian 获授权才能做的，mod 作者不因此获得同等授权。

### 7.3 自创职业的法务清单
1. 只用自创文本与名称；借用 SRD 通用机制（法术位、熟练加值、SRD 法术）只需附 CC-BY-4.0 署名（放 mod 描述 + PAK 内 README）。
2. 职业/子职业/特性命名避开 WotC 产品名与 Product-Identity 专名（Beholder、Mind Flayer 等），也避开可识别的第三方 IP（其他游戏、影视、画师作品）。
3. 图标、原画、字体、音效自绘或用允许再分发的许可（CC0 / CC-BY / OFL）；不要从 D&D Beyond、其他游戏、画师作品裁切；AI 生图注意服务条款。
4. 标题里用 "Baldur's Gate 3" 属社区惯例，但不要暗示官方出品。
5. 接受捐赠可以，但不要把 mod 或抢先体验作为付费对价。
6. 素材来源与许可清单随源码保存（`ASSETS-LICENSE.md`）。
