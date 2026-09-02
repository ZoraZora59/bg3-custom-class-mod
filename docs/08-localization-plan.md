# 08 · 多语言支持方案（汇总本次调研的本地化结论）

> 用户要求：mod 要支持各种语言。本文把散落在 docs/02 §4、docs/03 §4–5、docs/04 §3、docs/06 §5、docs/07 D6 以及研究报告 B §2.3、F §2.5、G §7 的本地化结论集中起来，并给出落地方案。

## 1. 游戏支持什么（官方，已直读核实）G[G7]
- 语言目录名固定 15 个：`BrazilianPortuguese`、`Chinese`（简体）、`ChineseTraditional`、`English`、`French`、`German`、`Italian`、`Japanese`、`Korean`、`LatinSpanish`、`Polish`、`Russian`、`Spanish`、`Turkish`、`Ukrainian`。
- 结构：`Mods/<Mod>/Localization/<Language>/<任意名>.xml`，目录内所有 xml 都会被处理；每行 `<content contentuid="<handle>" version="1">文本</content>`。
- **同一个 handle 在所有语言里复用**，所以"支持一种新语言 = 多一个目录 + 一份同 handle 的 xml"，数据文件（lsx/txt）不需要任何改动。
- 自定义 handle 可以是任意无空格字母数字串；复用原版 handle 并提高 version 可覆盖原版文本。
- 性别语法（法语、德语等有阴阳性的语言）：`Localization/<Lang>/Gender/Female|Neutral/`，文件名后缀 `_to_F`、`_to_X`（说话者/听者性别组合）。
- 改动后需重载模块或 `reloadLoca`。
- 缺失 handle 的回退行为：2026-09-02 的汉化调研确认引擎带回退池，缺失时回退英文或显示 "Not Found"，不会显示裸 handle（高置信推断，一手明文缺失，见 docs/09 §2 与 docs/07 V14）。这不改变 D6 的发布门槛：任何语言都不得出现英文回退或 "Not Found"。

## 2. 社区怎么做 C[2.4][2.5] F[2.5]
| 做法 | 例子 | 优缺点 |
|---|---|---|
| **社区独立翻译 mod**（最常见） | Artificer CHS/JP、Mystic CHS×3、Blood Hunter PTBR/ES/FR/CH、DK CotLK 六语 | 作者零成本；但版本容易脱节，玩家要多装一个 mod，翻译补丁必须放在原 mod 之下加载 |
| **作者自带多语言** | Blood Hunter Expanded 自带 FR/UK/RU；RAW 仓库内 `Localization/Chinese`、`ChineseTraditional`… | 一包到位、版本同步、主机玩家可用（mod.io 无翻译分区，只能靠 'translation' + 语言 tag）；需要维护 |
| **数据全部开源 + 翻译者 PR** | 5e Spells、Community Library | 社区可直接提交翻译；需要 GitHub 协作 |
| **机器翻译初稿工具** | BG3 script translator（跨平台，Google Translate 处理 .loca/XML）、XML TRANSLATOR、BG3 Mod Auto Translator、LarinStudios Localization Helper（本地化 XML 编辑器）、LocaHelper（3DM 中文教程）、BG3LocalizationMerger | 出初稿快；质量需人工校对 |

Crowdin / Weblate 这类平台在 BG3 mod 圈没有检索到使用案例；中文翻译者群体活跃（Nexus 上大量 CHS/CHT 独立翻译）。

## 3. 本项目方案（"支持各种语言"落地）
1. **架构上一开始就按 15 语言设计**：所有玩家可见文本只经 handle 引用（lsx 的 `TranslatedString`、txt 的 `"<handle>;<version>"`），不在数据文件里写死文本；handle 一经发布不改（改文本只升 version）。
2. **English 是源语言，仓库内维护 `Localization/English/<Mod>.xml` 为唯一事实源**；Chinese / ChineseTraditional 由我们自己翻译并随包发布。
3. **其余 12 种语言"随包发布 + 分级质量"**：用 `scripts/loca_sync.py` 从英文生成/同步各语言 xml（缺失条目先以英文占位并加 `[TODO]` 标记，便于翻译者搜索），再用机器翻译工具出初稿，最后招募社区校对；未经校对的语言在页面标注"机翻/待校对"。这样任何语言的玩家都不会看到裸 handle。
4. **翻译者友好**：仓库开源，Nexus 权限明确允许翻译；每个版本的 changelog 列出新增/修改的 handle（`loca_sync.py --diff` 生成）；接受翻译 PR 或独立翻译 mod 两种方式。
5. **主机与 mod.io**：多语言打进同一个 pak，mod.io 页面加 'translation' 与语言 tag；主机玩家无法另装翻译 mod，所以随包是唯一途径。
6. **性别语法**：法语/德语/西语/俄语等若需要阴阳性版本，按 `Gender/Female|Neutral` 与 `_to_F/_to_X` 规则补文件；v1 先不做，页面声明。
7. **UI 层的例外**：若做 SE 的 IMGUI/MCM 配置界面，中文等非拉丁字形显示依赖 SE 上游字体范围（不确定）E[46]；配置界面文本先用英文或改用 JSON 配置。游戏本体 UI 显示的 stats/lsx 文本不受此限制。
8. **测试矩阵**加一行：切换游戏语言到每种已提供语言，检查职业名/描述/被动/法术无裸 handle、无截断（长文本在 tooltip 的折行）。
9. **静态校验**：`scripts/check_mod.py` 的 W4 会列出每种语言缺失的 handle；`loca_sync.py --check` 可在 CI 里把"缺失或仍带 [TODO]"的条目数量当作发布门槛。

## 4. 工具与脚本
- `scripts/loca_convert.py`：纯 Python 的 `.loca`↔`.xml` 转换/批量/校验（按 LSLib 源码实现，未在真实文件验证，docs/07 V13）；Mac 上可替代 Divine 的 `convert-loca`。
- 给别人的 mod 做汉化（独立汉化 mod 的完整流程、许可、发布、维护）见 [docs/09](09-translating-existing-mods.md)。
- `scripts/loca_sync.py`：从 English xml 同步到指定语言（新增缺失条目、保留已译文本、标记 `[TODO]`）；`--diff <旧English.xml>` 输出 handle 变更清单供 changelog；`--check` 统计各语言完成度。
- 机器翻译初稿：BG3 Mod Auto Translator / BG3 script translator（Nexus，见 F[16]）；中文校对流程参考 3DM LocaHelper 教程 C[65]。
- Windows 侧：Toolkit 或 Divine `convert-loca` 把每个语言目录的 xml 转成 `.loca`（`build.ps1` 已按目录遍历）。

## 5. 与决策 D6 的关系
docs/07 的 D6 原写"英 + 简 + 繁自维护，其余交社区"；按用户要求改为：**英 + 简 + 繁人工维护，其余 12 种语言随包发布（机翻初稿 + 社区校对）**，并把"无裸 handle"作为每个版本的发布门槛。
