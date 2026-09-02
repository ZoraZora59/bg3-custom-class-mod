# 子课题 F：mod 团队职能分工与设计工作流（含 5e 自制职业设计方法论）

- 调研日期：2026-09-02
- 所属课题：《博德之门3 (Baldur's Gate 3, BG3) mod 开发调研》
- 目标读者：想制作自创职业/子职业 mod 的 BG3 玩家；需要明确"每个 mod 需要哪些职能参与、设计工作流怎么走"
- 证据标注约定：
  - `[n]` 指向第 5 节来源列表；只有本次会话里 WebSearch / WebFetch 实际返回的内容才会被编号引用。
  - `[背景知识—非本次检索]`：来自训练记忆、本次未能用检索验证的内容，不计入来源统计，使用时请自行核对。
  - "（推断）"：本报告基于来源做出的推论；"（草案/建议）"：本报告提出的方案，不是社区已有的公开规范。
  - 页面上没有的数据一律写"未公开"，不猜测人数、耗时。
- 抓取限制：Larian 官方文档站 `docs.baldursgate3.game`、Nexus 页面/文章直接抓取均返回 HTTP 403，`wiki.bg3.community` 与 mod.io 指南只返回标题（JS 渲染）；这些站点的信息只来自搜索引擎摘要，已在来源类型中注明"仅摘要"。

---

## 1. TL;DR

1. **头部 BG3 mod 的"团队"普遍很小、很松散，且没有任何一个案例公开过职能分工表或人数/工时。** Community Library 以 GitHub 组织 + Discord 招募运作（加入方式就是"Ask!"）[1][2]；ImprovedUI 由 4 位核心作者接力维护、后续贡献者按补丁加入 [6]；5e Spells 由单一作者 Celes 创建、由另一人（DiZ91891）上传维护 [7]；Artificer 自述为 "collaborative project"，用 GitHub Issues 当 TODO [4]。职能只能从 Credits、仓库结构和衍生 mod 生态反推。
2. **反复出现的职能**：设计/平衡、数据实现（stats / progressions）、脚本（Script Extender/Lua）、图标（可直接用 Game-Icons.net 的 CC 素材）[1]、VFX（以复用原版为主）[17]、本地化（第三方以独立翻译 mod 发布）[5][16]、测试（PR 前自测 + 团队复测）[2]、兼容性/框架维护 [3][24]、社区支持与文档。一人身兼数职是常态。
3. **协作工具的事实标准是 GitHub（仓库 + Issue 模板 + Wiki + Releases）和 Discord（官方 BG3 Discord 的 modding 区 #bg3-modding / #bg3-scripting）** [1][2][4]；本次没有检索到 Trello / GitHub Projects 看板的公开使用证据。
4. **5e 设计方法论的共识**：先职业幻想后机制（WotC："lean heavily into iconic fantasy stories"）[13]；每个特性都要与官方职业逐级比较并"justify"（Leuku）[8]；复杂度必须"opt-in"，区分建卡时的 crunch 与每回合要跟踪的 grit（KibblesTasty）[10]；WotC 自己靠公开 playtest + 问卷、按"强度/选择率"回炉迭代 [12][13]。
5. **BG3 把这套方法论的落点改了**：12 级上限 `[背景知识—非本次检索]`（佐证：Nexus 上有独立的 "Artificer - 12 Levels Option" mod [5]）；Patch 8 之后每个原版职业都新增了一条子职业，且 Larian 为每条都配了动画、VFX、专属召唤物 [18]，抬高了玩家对"完成度"的预期；升级界面无法即时显示部分多职业变化 [4]；依赖 Script Extender 的 mod 只能走 Nexus、进不了 mod.io/主机 [20]。
6. **工作流草案（8 阶段 + gate）见第 3 节。** 证据最扎实的 gate 是 Community Library 的 PR 流程："测试（可能需要一个辅助测试 mod）→ PR → 团队 review 并测试 → 合并，或给出不通过的理由与要改的点" [2]。
7. **最小团队（1–2 人）完全可行**——多个头部 mod 就是这样做的——前提是：图标用 CC 素材、VFX 复用原版或 VFX 库、本地化交给社区翻译者、兼容性交给 Community Library / Compatibility Framework。**理想团队（4–6 人）** 新增的价值主要在测试矩阵覆盖、自定义图标/VFX、多语言同步和补丁后的快速跟进。
8. **信息缺口**：开发耗时/工时未公开；Crowdin/Weblate 在 BG3 mod 圈的使用无检索证据；"Down by the River" Discord 与 modding 的关系未确认；类图标的精确像素尺寸在可读到的来源中未给出。

---

## 2. 分节详细发现

### 2.1 现有 mod 团队怎么组织

#### 案例概览

| mod | 类型 | 组织形态（来源可见部分） | 观察到的职能 | 协作/分发工具 | 来源 |
|---|---|---|---|---|---|
| BG3 Community Library / Compatibility Framework | 框架/资源库 | GitHub 组织 `BG3-Community-Library-Team`；有"团队"概念，加入方式是在官方 BG3 Discord 的 modding 区 ping @NellsRelo | 代码/数据贡献者、review+测试的团队、打包工具链（ShinyHobo）、mod 管理器展示图（Alana）、图标素材（Game-Icons.net） | GitHub 仓库 / Issues 模板 / Wiki / Releases；Discord | [1][2][3] |
| Artificer class and all subclasses（Kidel） | 职业类 | "collaborative project"，GitHub Issues 即 TODO，477 commits，MIT | 实现者（含 G-Vie 等贡献者）；翻译由第三方独立发布（JP、CHS）；规则变体由第三方独立发布 | GitHub；Nexus 主页 + 多个衍生 mod | [4][5] |
| ImprovedUI（ImpUI） | 框架/UI | 4 位核心作者接力：AlanaSP 首发 → ShinyHobo 接手并加 picture mode → Djmr 在 EA 期间维护、现独占所有权 → Zee 自 Patch 4 加入；Patch 8 期间 bibsan 补回 CC 功能；另有获 Djmr 授权、"open to contributions" 的 ImpUI_P8_Fork | UI 实现、所有权/维护权交接、授权 fork | GitHub（TheRealDjmr/BG3ImprovedUI）；Nexus / mod.io / Thunderstore | [6] |
| 5e Spells（Celes） | 内容库 | "created by Celes and uploaded by DiZ91891"；2020-11-20 首发，2026-05-24 仍在更新；数据全部开源到 GitHub | 作者 + 上传/维护者分离；开源仓库本身作为兼容性策略 | GitHub（Celestro/5eSpells，访问时 0 issues / 1 PR）；Nexus；mod.io 上有 "5e Spells: WIP" 与 "5.5e Spells" 条目 | [7] |

#### 案例细节

**Community Library / Compatibility Framework（BG3-Community-Library-Team）**

- README 给出三条参与路径：(1) 加入团队——"Ping @NellsRelo on the official Baldur's Gate 3 Discord's modding section, or via the Nexus release"，没有正式申请流程，就是 "Ask!"；(2) 独立贡献——fork、加改动并测试、提 PR，"We'll review it, and if all goes well, we'll either add your contribution, or provide reasoning as to why we won't"；(3) 建议——用 GitHub Issue 的 Bug Report / Feature Request 模板 [1]。
- Wiki "Making Contributions" 把流程写成五步：fork → 做改动 → "Test changes/additions (May require setting up a secondary testing mod to draw on your changes/additions)" → push 并发 PR → "The team will review the code, and test the changes/additions"；被拒时会说明"为什么不通过、需要什么改动、发现了哪些错误" [2]。
- 工具：GitHub（访问时 457 commits、29 open issues、2 open PRs）、GitHub Wiki（含 "Setting up a Development Environment"）、官方 BG3 Discord 的 #bg3-modding / #bg3-scripting 频道；开发工具链为 BG3 Modders Multitool、LSLib、Script Extender [1][2]。
- Credits 里的"非代码"职能：ShinyHobo（简化 .pak 打包流程）、Alana（Mod Manager 兼容图片）、Game-Icons.net（CC 3.0 图标）[1]——说明打包工具链、mod 管理器展示素材、图标素材都是独立的工作项，而且图标可以用 CC 素材而不必有专职美术。
- 内容按 classes / races / spells / passives / statuses / items / scripts / visual effects 分类，各有文档 [2]。
- Compatibility Framework 的 README 致谢 Larian、BG3 Modding Community、ShinyHobo；配套 CF-Sample-Patches、CF-Example-Mods 示例仓库 [3]；同一组织还提供 Sample-Template（"A Starting Point for your Own Mods"）[24]。第三方 FrederickEngelhardt 单独维护 "patches for mods that change progression files yet break when used together" [24]——Progressions 冲突是社区公认痛点，"兼容性"是一项贯穿生命周期的职能。

**Artificer class and all subclasses（Kidel）**

- GitHub README 自述为 "collaborative project"，对 5e 原版做 "mechanical adaptations to fit BG3's design constraints while maintaining the class's core identity"；TODO 就是仓库 Issues；477 commits；MIT 许可；README 没有按职能分列的 Credits [4]。Nexus 搜索摘要提到贡献者图里有 G-Vie 等人 [5]。
- 衍生生态：日文翻译（Akazonae36，独立 mod 23324）、简中翻译（独立 mod 15477）、"Artificer - 12 Levels Option"（独立 mod 3224）、"Artificer Feat Every Level"（独立 mod 5566）[5]——本地化和规则变体由社区"外包"、以独立 mod 发布，是职业 mod 的典型生态。
- 对 UI 约束的一手描述："New slots won't show up on levelup screen, but will be added once you return to the field. **Works only with core game spellcasters.**"；物品相关功能 "will only work for items of the core game" [4]。

**ImprovedUI（Djmr / AlanaSP / ShinyHobo / Zee）**

- Nexus 描述："made by Djmr, AlanaSP, ShinyHobo & Zee"；所有权与维护权有明确的接力链；Patch 8 期间 bibsan 补回部分 CC 功能；ImpUI_P8_Fork 是 Patch 8 专用、"authorized by Djmr and open to contributions" [6]。
- **来源分歧**：Thunderstore 的包名只列 `ShinyHobo_Djmr_AlanaSP`（无 Zee）[6]。不同分发站的署名不一致，应以 Nexus 页面 / GitHub 为准。
- 启示：长寿命框架 mod 靠"明确的所有权交接 + 授权 fork"存活过多次大补丁。

**5e Spells（Celes）**

- "created by Celes and uploaded by DiZ91891"；部分法术需要 Script Extender，可配置只启用部分法术 [7]。GitHub 仓库自述：把 mod 现有全部数据放出来，让其他 modder 使用这些资源 "without creating incompatibility issues" [7]。
- 启示：作者与上传/维护者可以是两个人；公开数据仓库本身就是一种兼容性与协作策略。

#### 小结：出现过的角色与工具

| 角色 | 证据 |
|---|---|
| 维护者 / 项目所有者（决定合并、交接、授权 fork） | [1][2][6] |
| 数据实现者（stats、progressions、lists） | [2][4][7] |
| 脚本（Script Extender / Lua） | 5e Spells 部分法术依赖 SE [7]；CL 内容分类含 scripts [2]；#bg3-scripting 频道 [1] |
| 图标 / 素材 | Game-Icons.net CC 素材 [1]；mod 管理器展示图（Alana）[1] |
| VFX | CL 内容分类含 visual effects [2]；VFX 库作为独立 mod 存在 [17] |
| 打包 / 工具链 | ShinyHobo 的 .pak 流程 [1][3] |
| 本地化 | 第三方独立翻译 mod（Artificer JP / CHS）[5] |
| 测试 / review | PR 前自测 + 团队复测 [2] |
| 兼容性 / 补丁 | Compatibility Framework、进阶补丁仓库 [3][24] |
| 上传 / 分发 / 社区支持 | 5e Spells 的上传者 DiZ91891 [7]；多站分发 [6][7] |

工具：GitHub（仓库 / Issue 模板 / Wiki / Releases）[1][2][4][7]、Discord（官方 BG3 服务器 modding 区）[1]、分发站 Nexus / mod.io / Thunderstore [5][6][7]、BG3 Mod Manager（LaughingLeader，"This is the only official source!"）与 Norbyte 的 bg3se [23]、Mod Change Tracker（用 SE 把所有已装 mod 对 stat 条目的修改导出为文本，便于排查冲突）[23]。未检索到 Trello / GitHub Projects 的公开使用证据。

### 2.2 5e 自制（homebrew）职业/子职业设计方法论

#### WotC 官方公开的设计思路

- **Designer Insights: Subclasses Update（Ben Petrisor）**：把老特性改成"随攻击次数缩放"以奖励不同 build（"scales with the number of attacks the Barbarian makes"）；把特性"broken up into multiple effects"以提高可读性；老子职业获得 "new designs and quality of life updates to bring them in line with the updated Player's Handbook"；问卷在文章发布时已关闭——即 playtest → 问卷 → 修订的固定节奏 [12]。这篇文章几乎没有显式的方法论陈述，只能从案例反推 [12]。
- **Designer Insights: Apocalyptic Subclasses（Wesley Schneider、Makenzie De Armas、Ben Petrisor）**：设计"lean heavily into iconic fantasy stories"，希望子职业 "really adept at fulfilling their narrative framework"（例：Circle of Preservation 围绕治疗与保护）；承认部分子职业 "on the lower end of power scaling and how often they were chosen/played"，并据此回炉；"it's not necessary that every subclass be balanced" 但值得给不受欢迎的子职业翻新 [13]。
- **r/UnearthedArcana wiki 的资源页**指出：UA 文章常附"how homebrewers may create their own content"的说明，尤其是 *Modifying Classes* 一文 "contains specific guidelines on the design parameters of each class and advice on how to modify them"；DMG 的 "Dungeon Master's Workshop"（pp. 273–289）有创建怪物、法术、魔法物品、种族、职业、子职业的章节 [9]。（本次尝试直接抓取 *Modifying Classes* PDF 失败，返回 404，未能核对原文。）

#### 社区权威指南

- **Leuku's Guide to Balancing (and Judging the Balance of) Homebrew Classes**：核心方法是与官方职业逐级比较——"the balance of any given feature does not exist in a vacuum, but in a continuum of all of the features combined"；尊重 "tiers of play"，职业要 "fulfill minimum average damage expectations"；"your class' features do not exist in a vacuum – they stack upon a foundation of basics"；从其他职业借来的特性 "You have to justify every single feature you take from another class"，口号是 "Justify, Justify, Justify!"；完整数值表在 GM Binder 版本，本次未能读取 [8]。
- **KibblesTasty "Opt In Complexity & 5e Design"**：复杂度应"局限在选择它的角色身上"（"you can play Bob the Barbarian, and sit next to Isaac the Inventor" 而不必关心对方职业多复杂）；区分 **crunch**（建卡时的选择，不拖慢桌面，"That's crunch, and you can add as much of it as you want"）与 **grit**（每回合要跟踪、会卡住游戏的效果，例 Conjure Animals）；页数会让 DM 反射性拒绝；要监控"横向能力选项"数量——50 页的 Inventor 提供的选择仍少于官方 Cleric/Wizard [10]。其 Compendium "318 pages of content all designed and extensively playtested" [11]。
- r/UA wiki 建议把作品拿到 r/UnearthedArcana / r/DnDHomebrew 请有经验的 DM 与玩家评审 [9]。

**来源分歧**：Leuku 强调"以官方为基线、每个偏离都要证明"[8]；Kibbles 认为第三方内容本就服务于"想要更多深度"的玩家，不必匹配 PHB 的复杂度基线 [10]。二者可以调和：**数值（power）对齐官方，复杂度（crunch）可以高于官方但必须 opt-in，且不能带来 grit**——这也是本报告在 BG3 语境下采用的立场。

#### 提炼：关键平衡维度（设计检查清单）

| 维度 | 检查什么 | 证据 / 标注 |
|---|---|---|
| 职业幻想与机制一致 | 一句话说清 fantasy；每个核心特性都在兑现它 | WotC "narrative framework" [13] |
| 伤害基线（DPR） | 按 tier 与最近的官方职业比较，满足"最低平均伤害预期" | Leuku "tiers of play" / "minimum average damage expectations" [8]；具体基线数值 `[背景知识—非本次检索]`，本次未取得原表 |
| 资源节奏 | 短休/长休资源的数量与回复方式是否与官方同类职业一致 | Leuku 把 spell slots / action economy 列为平衡考量 [8] |
| 特性密度与"基础层" | 特性是叠在职业基础（HP、熟练、Extra Attack 等）之上的，不要重复计算基础层的价值 | Leuku "foundation of basics" [8] |
| 借用特性的正当性 | 从其他职业搬来的特性逐条 justify | Leuku "Justify, Justify, Justify!" [8] |
| 子职业节点 | 与所属职业的官方子职业节点一致 | UA *Modifying Classes* 有各职业参数 [9]；具体等级表 `[背景知识—非本次检索]`（如 Cleric/Sorcerer/Warlock 1 级、Druid/Wizard 2 级、其余 3 级选择子职业） |
| 法术槽 | 全施法 / 半施法 / 三分之一施法只能三选一，不自创曲线 | `[背景知识—非本次检索]` |
| 动作经济 | 附赠动作 / 反应的占用与官方同类比较 | Leuku [8] |
| 复杂度 | crunch 可以多，grit 要少 | Kibbles [10] |
| 可读性 | 复合特性拆成多个效果；随攻击次数缩放而非固定数值 | WotC [12] |
| 迭代信号 | 强度偏低或"没人选"都是回炉信号 | WotC [13] |

### 2.3 BG3 特有的设计约束

- **12 级上限**：`[背景知识—非本次检索]` BG3 角色上限 12 级。检索到的佐证：Nexus 上存在独立的 "Artificer - 12 Levels Option" mod [5]，说明职业 mod 作者会为 12 级结构单独做压缩方案；Artificer 仓库也自述做了 "mechanical adaptations to fit BG3's design constraints" [4]。（草案）压缩原则：保留官方子职业的前三个节点（通常 3/6/10 或 1/6/10 等），把 14+ 级的特性要么舍弃、要么降级合并进 10–11 级，并把 12 级留给最后一次 ASI/专长 `[背景知识—非本次检索：ASI 在 4/8/12 级]`。
- **Patch 8 后的子职业分布**：Patch 8（2025-04-15，官方称最终大补丁）为 12 个原版职业各加一条子职业：College of Glamour Bard、Path of the Giant Barbarian、Death Domain Cleric、Circle of Stars Druid、Arcane Archer Fighter、Way of the Drunken Master Monk、Oath of the Crown Paladin、Swarmkeeper Ranger、Swashbuckler Rogue、Shadow Magic Sorcerer、Hexblade Warlock、Bladesinger Wizard；每条都带 "new abilities, animations, visual effects, unique summons, and powerful cantrips" [18]。设计含义：(a) 先核对你的概念是否已被 Patch 8 或现有 mod 覆盖（Artificer 已有多个版本与变体 [5]）；(b) Larian 的完成度标准（动画/VFX/召唤物）会成为玩家评价 mod 的参照。
- **"以原版职业为基线量化"**：Leuku 的逐级比较法在 BG3 更容易落地，因为原版职业的 Progressions / Stats 数据可以直接读取（推断，基于 toolkit 数据模型 [19]）。（草案）做法：为你的职业选一个"影子基线"原版职业，逐级（1–12）列出双方的攻击次数、主要资源、法术等级、被动数，并在设计单里对每一项写差异与理由。
- **多人合作与荣誉模式**：本次只检索到玩家侧信息——荣誉模式存档类 mod 在"新 HM 存档"与"旧存档加 mod"上的行为不同 [21]；Explorer 难度禁用 Add Class（多职业）[21]；Withers 重置 100 金 [21]。含义：测试矩阵必须把"新档 / 旧档 / 难度模式 / 多职业"作为独立维度。联机同步的 mod 特有约束未检索到一手描述；`[背景知识—非本次检索]` 联机时所有玩家需装同一套 mod 与相同版本。
- **UI 能承载的复杂度**：一手证据是 Artificer 的说明——升级界面不会即时显示新增的法术槽，且只对原版施法者生效 [4]；ImprovedUI 长期存在并随每个大补丁更新 [6]（`[背景知识—非本次检索]` 其作用之一是让自定义职业/种族在角色创建等界面正确显示，因此自定义职业 mod 通常把 ImpUI 列为依赖）。资源面板与反应弹窗的承载能力未检索到直接来源；`[背景知识—非本次检索]` 自定义资源需在 ActionResourceDefinitions 中声明才会有 UI 显示，反应（reaction）以弹窗形式呈现，过多的反应类特性会显著增加玩家的操作负担。
- **发布渠道约束**：Larian 在 Patch 7 引入与 mod.io 集成的游戏内 mod 管理器（支持主机与 PC）；"Complex mods that use Script Extender are only on Nexus"，玩家常同时使用两套管理器 [20]。设计阶段就要决定"纯数据实现"还是"允许 SE"，这直接决定主机玩家能否使用。

### 2.4 工作流与阶段门（gate）

**检索到的一手证据（工作流相关）**

- 贡献流程：fork → 改动 → 测试（可能需要一个辅助测试 mod）→ PR → 团队 review 并测试 → 合并或反馈 [2]；Issue 使用 Bug Report / Feature Request 模板 [1]。
- 任务管理：Artificer 直接用 GitHub Issues 作为 TODO 列表 [4]。
- 技术拆解的数据模型：Larian 文档的 "Adding Classes and Subclasses"——在 toolkit 中为 mod 新增 Progressions 表；`ProgressionType` 0 = Class、1 = Subclass、2 = Race；需要 ClassDescriptions 表（DisplayName / Description）才能在角色创建中出现 [19]。教程生态：Nexus "Full Tutorial - Making Your Own Class - Flowerborn"、"Full Tutorial. Make New Abilities for Your Subclass"、toolkit 视频教程、mod.io "Adding New Classes or Subclasses"、Community Library wiki 的 Subclass Compatibility Framework 文档 [19]。
- 发布：Nexus 与 mod.io 双轨；SE 依赖只能 Nexus [20]；ImpUI 等框架同时在 Nexus / mod.io / Thunderstore 分发 [6]。
- 维护：ImpUI 的 Patch 8 专用 fork、bibsan 补回功能 [6]；5e Spells 从 2020-11 持续更新到 2026-05 [7]。

**社区作者公开的耗时/工作量数据**：未公开。针对性搜索没有找到任何作者公开的开发时长 [审计：查询 #17 无相关结果]。可用的间接量级：Community Library 457 commits [1]、Artificer 477 commits [4]、5e Spells 约 5 年半持续维护 [7]——都说明"发布之后的维护"是主要工作量来源（推断）。

分阶段工作流草案（阶段、交付物、gate、职能）见第 3 节表 B。

### 2.5 本地化协作、图标/美术规格、VFX 与模型

**本地化**

- 文件与流程（来自 Nexus 教程文章与进阶教程的摘要）：mod 的 `Localization` 目录下按语言建文件夹，把 English 目录下的 `Mod_Name.xml` 或 `Mod_Name.loca` 复制到 "YourLanguage" 目录后翻译；`base_game_loca_xml` 里有 `english / russian / chinese / chinesetraditional .loca.xml`，可用 `contentuid` 对齐原版既有译文 [16]。Larian 官方文档另有 "Adding Localisation" 页面 [16]。
- 工具：BG3 script translator（跨平台，用 Google Translate 处理 .loca/XML）、XML TRANSLATOR（Python 脚本）、BG3 Mod Auto Translator、LarinStudios Localization Helper（本地化 XML 的 QOL 编辑器）[16]。
- 惯例：翻译由第三方以**独立 mod** 发布——Artificer 的日文版（Akazonae36）与简中版都是独立 Nexus 条目 [5]。
- 中文社区：只观察到 CHS 翻译 mod 的存在 [5]；没有检索到中文翻译组织的公开流程。Crowdin / Weblate：未检索到任何 BG3 mod 使用案例（信息缺口）。
- （建议）源 mod 作者的最低配合：把 `english.loca.xml` 源文件放进仓库、在 Nexus 权限里明确允许翻译、每次改文本时在 changelog 里列出新增/变更的 handle，方便翻译者增量更新。

**图标 / 美术规格**

| 项目 | 规格 | 来源 |
|---|---|---|
| 技能/法术/物品图标尺寸 | "Icon size should be kept to 64x64"，所有技能与物品图标都是 64×64 | Larian 文档 [14]（仅摘要） |
| 图集（atlas） | 边长只能是 2 的幂，32×32 到 4096×4096；512×512 = 8×8 = 64 个图标，1024×1024 = 16×16 = 256 个 | [14] |
| 格式 | ".DDS DTX5 format with no mipmaps, as mipmaps will only make icons blurry" | [14] |
| 绑定方式 | 在 Stats Editor 相关 stats 文件的 Icon 列填写 | [14] |
| 目录 | 图标 `MySweetMod\Public\Game\Assets\Tooltips\Icons`；图集 `MySweetMod\Public\MySweetMod\Assets\Textures\Icons` | [14] |
| 类/子职业图标 | 需要两版：标准版（角色创建右上角、角色面板/法术书）与 Hotbar 版（角色创建的职业选择、左侧热键栏）；目录 `Public\Game\GUI\Assets\ClassIcons`；文件名与 `classdescriptions.lsx` 中的类名一致；**扩展名必须大写 `.DDS`**；像素尺寸在该页面未给出 | bg3.wiki [15] |
| 工具 | Photoshop（商业）、NVIDIA Texture Tools Exporter（免费）、GIMP、Paint.net | [15]；Paint.net 导出设置以图片形式给出 [15] |
| 模板与素材 | mod.io 指南 "Making a Class Icon (with templates)"、"Custom Icon Visual Cheat Sheet"；Nexus "Bg3 Icon pack"；YouTube 自定义法术图标教程 | [14]（仅标题/摘要） |
| 免费素材 | Game-Icons.net（CC 3.0），Community Library 即采用 | [1] |

（建议）设计单里为每个主动技能、被动、状态、职业与子职业各预留一个图标条目，并在实现阶段先用 Game-Icons.net 占位，美术资源到位后替换——这与 Community Library 的做法一致 [1]。texconv 未在检索到的来源中出现，`[背景知识—非本次检索]` 它是 Microsoft 的命令行 DDS 转换工具，可替代图形软件插件做批量转换。

**VFX 与模型**

- 官方流程：法术/技能/状态特效用 Effect Editor "AllSpark" 制作；官方指南分四部分——Part 1 制作特效、Part 2 创建资源、Part 3 创建 MultiEffectInfo (MEI) 文件并把特效指派给法术、Part 4 投射物法术与角色的进阶信息 [17]。
- 复用原版：Nexus "Basic VFX Tutorial - Sample VFX Mod" 描述的步骤涉及转换文件、移动 MultiEffectInfo 目录、在合并的 effect banks 中查找 GUID、编辑 EffectBanks [17]。
- VFX 库：VFX Library by Shivero、Vlad's Codex - Enhanced VFX Library（提供原版 VFX 的 "true color" 版本），作为依赖放在 load order 最前，用于给新法术/mod 提供特效 [17]。
- 可行性判断（推断）：自定义 VFX 是一条独立的技能栈（编辑器 + 资源 + MEI 绑定），VFX 库与"复用原版"教程的存在本身说明社区默认走复用路线；1–2 人团队应把自定义 VFX 列为可选项，模型/动画不在职业 mod 的常规范围内（Patch 8 那种"新动画 + 专属召唤物"的完成度 [18] 是官方级投入）。

### 2.6 社区运营与反馈

- **页面写法惯例（从案例归纳）**：明确的作者/贡献者署名与接力说明 [6]；依赖说明（是否需要 Script Extender、ImpUI、Community Library）[7][20]；把翻译版与规则变体作为独立条目互链 [5]；开源仓库链接 [4][7]；已知限制写在正文（如 Artificer 的多职业法术槽说明 [4]）。
- **Bug 报告**：Community Library 用 GitHub Issue 模板（Bug Report / Feature Request）[1]；排查工具 Mod Change Tracker 可导出所有 mod 对 stat 条目的修改 [23]；BG3 Mod Manager 的官方源在 LaughingLeader 的 GitHub [23]。社区通用的 bug 报告模板未检索到公开版本（信息缺口）。（草案）模板：游戏版本 / 平台（PC-Steam、GOG、主机）/ mod 版本 / 是否 SE 及版本 / 完整 load order 导出 / 新档还是旧档 / 单机还是联机 / 难度模式 / 复现步骤 / 截图或 SE 控制台日志 / Mod Change Tracker 输出（若为数值异常）。
- **Discord**：Community Library 把官方 BG3 Discord 的 modding 区（#bg3-modding、#bg3-scripting）作为招募与讨论渠道 [1]。"Down by the River"：本次只确认到其 X 账号自述为 "#bg3 #baldursgate3 Discord community" [22]，未检索到它与 modding 支持的具体关系（信息缺口）。
- **版本发布说明**：案例中 GitHub Releases 是标准做法 [1][3]；BG3 Mod Manager 自身以 wiki Changelog 记录变更 [23]。（建议）每个版本的说明至少包含：兼容的游戏补丁、是否需要新档、依赖版本、文本变更清单（供翻译者）。

---

## 3. 角色矩阵、工作流草案、团队规模对比

### 表 A：每个职业 mod 需要哪些职能参与（角色矩阵，草案）

| 角色 | 必需性 | 可否由一人兼任 | 主要交付物 | 介入阶段 | 证据 |
|---|---|---|---|---|---|
| 项目所有者 / 维护者 | 必需 | 通常与设计或实现兼任 | Issues/TODO、里程碑、Releases、所有权与授权说明 | 全程 | [1][4][6] |
| 设计 / 平衡 | 必需 | 可兼任 | 职业设计单（GDD）、逐级对比表、平衡表 | 概念 → 设计 → 纸面平衡 → 测试反馈迭代 | 方法论 [8][10][12][13] |
| 数据实现（stats / progressions / lists） | 必需 | 可兼任 | ClassDescriptions、Progressions（type 0/1）、ProgressionDescriptions、SpellLists/PassiveLists 等、Stats 条目、meta.lsx、.pak | 技术拆解 → 实现 → 维护 | [2][19] |
| 脚本（Script Extender / Lua / Osiris） | 可选（动态机制、跨 mod API 时必需） | 可兼任，但是独立技能栈 | Lua 脚本、SE 配置、CF/CL 集成代码 | 技术拆解 → 实现 | [1][2][7][20] |
| 兼容性 / 框架集成 | 必需 | 通常由实现兼任 | 依赖声明（ImpUI/CL/CF）、CF 补丁、load order 说明 | 技术拆解 → 发布 → 维护 | [3][6][24] |
| 图标 / 2D 美术 | 必需（可用 CC 素材降级） | 可兼任 | 64×64 DDS 图集、类图标两版（标准 + Hotbar） | 实现（中后期） | [1][14][15] |
| VFX / 模型 | 可选 | 独立技能栈，小团队不建议自制 | MEI 文件、EffectBank 引用、VFX 库依赖 | 实现（后期） | [17] |
| 本地化 | 可选但强烈建议 | 作者提供英文 + 母语；其他语言交给社区 | `Localization/<lang>/*.loca(.xml)`、文本变更清单 | 实现末 → 发布 → 维护 | [5][16] |
| 测试 / QA | 必需 | 可由作者 + Discord testers 分担 | 测试矩阵结果、bug 列表、回归记录 | 内部测试 → 封闭测试 → 每次补丁后 | [2][21] |
| 社区运营 / 文档 | 必需 | 可兼任 | Nexus/mod.io 页面、README、changelog、FAQ、bug 模板、Discord 支持 | 发布 → 维护 | [1][6][7][23] |

### 表 B：分阶段工作流草案

| # | 阶段 | 交付物 | gate（可进入下一阶段的判据） | 参与职能 | 证据/依据 |
|---|---|---|---|---|---|
| 0 | 概念 | 一页概念：职业幻想一句话、最近的原版"影子基线"职业、与 Patch 8 及现有 mod 的差异、是否允许 SE 依赖 | 幻想能一句话说清；Nexus/mod.io 已有同类 mod 的差异明确；SE 决策已做（决定能否上 mod.io/主机） | 设计、所有者 | [13][18][20][5] |
| 1 | 职业设计单（GDD） | 1–12 级逐级特性表；子职业节点；资源定义；法术列表；每条特性的 justify 与影子基线的差异 | 每条特性都有 justify；子职业节点与影子基线一致；无 grit 型（每回合跟踪）特性 | 设计 | [8][9][10] |
| 2 | 纸面平衡 | 按 tier 的 DPR 表、资源节奏表、动作经济表；"横向选项"数量统计 | 数值落在影子基线附近（阈值由团队定）；每级都有变化或与基线一致；复杂度为 opt-in | 设计（+ 一名评审者） | [8][10] |
| 3 | 技术拆解 | 特性 → Progressions / Stats / Lists / Localization / Icons / (Lua) 的映射表；每项的风险等级；依赖清单（ImpUI/CL/CF/VFX 库） | 每条特性都有实现路径与风险等级；"纯数据 vs SE"结论与阶段 0 一致；图标与 VFX 需求已列成清单 | 实现、脚本、兼容性 | [2][19][17] |
| 4 | 实现 | 可运行的 .pak；先做 1–5 级纵切片再补 6–12；图标占位（CC 素材）；英文文本 | 新游戏可创建角色并升到 12 级不崩；无占位文本/丢失图标；多职业下不报错 | 实现、脚本、图标 | [1][4][19] |
| 5 | 内部测试矩阵 | 结果表：新档 / 旧档加 mod / 多职业（与原版施法者）/ Withers 重置 / 联机（host + client）/ 荣誉与各难度 / 与 ImpUI、5e Spells、CL/CF 的共存 / 当前游戏补丁 | 阻断级 0；每个矩阵格都有记录；已知限制写进 README | 测试、实现 | [2][4][21] |
| 6 | 封闭测试 | 测试版 + 反馈模板发给 Discord testers；数值反馈汇总 | 反馈收敛（同一问题不再重复出现）；平衡表据反馈更新 | 测试、设计、社区 | [1][2] |
| 7 | 发布 | Nexus 页面（+ GitHub 源码）；无 SE 依赖时同步 mod.io；页面含依赖、安装、已知问题、权限（含翻译权限）、Credits；Release 说明 | 页面清单完整；翻译源文件与文本变更清单已随包提供；bug 报告模板已发布 | 社区、所有者 | [5][6][7][16][20] |
| 8 | 维护 | 补丁跟进（如 Patch 8 专用 fork 的做法）；Issue 分流；翻译 mod 更新通知；交接/授权预案 | 每次游戏补丁后完成一次矩阵烟测（建议 72 小时内）；所有权与授权关系清晰 | 所有者、实现、社区 | [6][7][23] |

说明：阶段 0–3 是"纸面"阶段，成本低、可反复；阶段 4 以后每次返工都要重跑第 5 阶段矩阵，所以 gate 1–3 要严。

### 表 C：最小团队 vs 理想团队

| 维度 | 最小团队（1–2 人） | 理想团队（4–6 人） |
|---|---|---|
| 组成 | 1 人兼设计 + 实现 + 所有者；第 2 人做测试与图标/文本 | 设计/平衡 1、数据实现 1、脚本 1、图标/VFX 1、QA 负责人 1（+ Discord tester 池）、社区/本地化协调 1 |
| 现实对应 | 5e Spells（作者 + 上传者）[7]；Artificer 的核心贡献者规模未公开但以 Issues 驱动 [4] | ImpUI 的 4 位核心作者 + 补丁期贡献者 [6]；Community Library 的"团队 + 独立贡献者"模式 [1][2] |
| 图标 | 用 Game-Icons.net 等 CC 素材 [1] | 自制风格统一的图集与类图标两版 [15] |
| VFX | 复用原版或 VFX 库 [17] | 可做少量自定义 VFX（AllSpark 流程）[17] |
| 本地化 | 英文 + 作者母语；其余交社区翻译者独立发布 [5][16] | 内部维护 2–3 种语言并同步更新，其余仍交社区 |
| 测试 | 作者自测 + 少量 Discord 玩家；矩阵只覆盖新档/旧档/多职业/重置 | 完整矩阵含联机、荣誉、与主流框架共存；补丁后 72 小时烟测 |
| 兼容性 | 依赖 CL/CF/ImpUI，不自写 API | 可为其他 mod 提供 CF 补丁与 API |
| 建议 | 把阶段 0–3 做扎实，纯数据实现优先，SE 只在必须时引入；一开始就写好权限与翻译说明，把社区当作"外包团队" | 用 GitHub Issues 模板 + Releases 管理；明确所有权与授权 fork 规则，避免维护者离开后 mod 死亡 [6] |

---

## 4. 未解决问题与信息缺口

1. **耗时/工作量**：没有任何作者公开开发时长；只有 commit 数与维护年限作量级参考 [1][4][7]。
2. **官方文档原文**：`docs.baldursgate3.game` 直接抓取 403，图标/VFX/职业创建的规格只来自搜索摘要 [14][17][19]；建议用浏览器人工核对后再写进内部规范。
3. **UA *Modifying Classes* 原文**：PDF 抓取 404，各职业的"设计参数"未能核对，只保留 r/UA wiki 的转述 [9]。
4. **类图标像素尺寸**：bg3.wiki 页面没有给出数值 [15]；mod.io 的模板指南只能读到标题 [14]。
5. **Crowdin / Weblate**：未检索到任何 BG3 mod 使用案例；中文翻译社区的组织方式未检索到公开描述。
6. **"Down by the River" Discord**：只确认为 BG3 社区服务器的 X 账号 [22]，与 modding 支持的关系未确认。
7. **联机与荣誉模式下 mod 的技术约束**：只找到玩家侧的存档/难度描述 [21]，没有 modder 侧的一手说明。
8. **UI 承载能力**：除 Artificer 的升级界面说明 [4] 外，资源面板与反应弹窗的限制没有一手来源。
9. **重试未执行**：按纪律单次失败应等待 3 秒重试一次；本次 6 个抓取失败均为主机级拦截（403）、URL 错误（404）或 JS 渲染空页，且抓取预算已用尽，因此未重试，改用搜索摘要补位。

---

## 5. 来源列表

| 编号 | 标题 | URL | 类型 | 访问日期 |
|---|---|---|---|---|
| [1] | BG3-Community-Library-Team/BG3-Community-Library（README） | https://github.com/BG3-Community-Library-Team/BG3-Community-Library | 一手（全文抓取） | 2026-09-02 |
| [2] | BG3 Community Library Wiki – Making Contributions | https://github.com/BG3-Community-Library-Team/BG3-Community-Library/wiki/Making-Contributions | 一手（全文抓取） | 2026-09-02 |
| [3] | BG3-Community-Library-Team/BG3-Compatibility-Framework（README、CF-Sample-Patches、CF-Example-Mods） | https://github.com/BG3-Community-Library-Team/BG3-Compatibility-Framework | 一手（仅搜索摘要） | 2026-09-02 |
| [4] | Kidel/BG3_Artificer（README） | https://github.com/Kidel/BG3_Artificer | 一手（全文抓取） | 2026-09-02 |
| [5] | Nexus：Artificer class and all subclasses（mod 1779）及衍生条目 3224 / 5566 / 23324 / 15477 | https://www.nexusmods.com/baldursgate3/mods/1779 | 一手（仅搜索摘要） | 2026-09-02 |
| [6] | Nexus：ImpUI (ImprovedUI)（mod 366）、ImpUI_P8_Fork（mod 16649）；GitHub TheRealDjmr/BG3ImprovedUI；Thunderstore ImprovedUI | https://www.nexusmods.com/baldursgate3/mods/366 ；https://github.com/TheRealDjmr/BG3ImprovedUI ；https://thunderstore.io/c/baldurs-gate-3/p/ShinyHobo_Djmr_AlanaSP/ImprovedUI/ | 一手（仅搜索摘要） | 2026-09-02 |
| [7] | Nexus：5e Spells（mod 125）；GitHub Celestro/5eSpells；mod.io 5e Spells: WIP / 5.5e Spells | https://www.nexusmods.com/baldursgate3/mods/125 ；https://github.com/Celestro/5eSpells | 一手（GitHub 抓取 + Nexus 摘要） | 2026-09-02 |
| [8] | Leuku's Guide to Balancing (and Judging the Balance of) Homebrew Classes | https://leukudndhomebrew.wordpress.com/2020/03/09/leukus-guide-to-balancing/ | 一手（社区权威指南原文，部分抓取；GM Binder 完整版未读） | 2026-09-02 |
| [9] | r/UnearthedArcana wiki – resources（libredd.it 镜像） | https://libredd.it/r/UnearthedArcana/wiki/resources | 二手（仅搜索摘要） | 2026-09-02 |
| [10] | KibblesTasty – Opt In Complexity & 5e Design | https://www.kthomebrew.com/kibblesblog/opt-in-complexity-amp-5e-design | 一手（全文抓取） | 2026-09-02 |
| [11] | RPG.net – How balanced is Kibbles' homebrew content；kthomebrew.com 首页 | https://forum.rpg.net/threads/5e-how-balanced-is-kibbles-homebrew-content.901666/ ；https://www.kthomebrew.com/ | 二手（仅搜索摘要） | 2026-09-02 |
| [12] | D&D Beyond – Designer Insights from Unearthed Arcana: Subclasses Update | https://www.dndbeyond.com/posts/2092-designer-insights-from-unearthed-arcana-subclasses | 一手（WotC 官方，全文抓取） | 2026-09-02 |
| [13] | D&D Beyond – Designer Insights from Unearthed Arcana: Apocalyptic Subclasses（及 BoLS / EN World 报道） | https://www.dndbeyond.com/posts/2041-designer-insights-from-unearthed-arcana | 一手（仅搜索摘要） | 2026-09-02 |
| [14] | Larian 官方文档 – Adding Skill and Item Icons；mod.io "Making a Class Icon (with templates)"、"Custom Icon Visual Cheat Sheet"；Nexus Bg3 Icon pack（mod 3125） | https://docs.baldursgate3.game/Adding_Skill_and_Item_Icons ；https://mod.io/g/baldursgate3/r/making-a-class-icon-with-templates | 一手（仅搜索摘要；直接抓取 403 / 空页） | 2026-09-02 |
| [15] | bg3.wiki – Modding: Class icons | https://bg3.wiki/wiki/Modding:Modding_class_icons | 二手（社区 wiki，全文抓取） | 2026-09-02 |
| [16] | Nexus 文章 "How to Translate these Mods for your language"（articles/643）、"How to Make Translation Mod (Advance)"（mod 7288）、翻译工具 mod 23203 / 19280 / 15778 / 3136；Larian 文档 Adding Localisation | https://www.nexusmods.com/baldursgate3/articles/643 ；https://docs.baldursgate3.game/index.php?title=Adding_Localisation | 一手/二手（仅搜索摘要；直接抓取 403） | 2026-09-02 |
| [17] | Larian 文档 – VFX、VFX – Part 1: Making Effects；Nexus Basic VFX Tutorial - Sample VFX Mod（mod 4200）；VFX Library by Shivero（mod 3888）；Vlad's Codex - Enhanced VFX Library（mod 13797） | https://docs.baldursgate3.game/index.php?title=VFX ；https://www.nexusmods.com/baldursgate3/mods/4200 | 一手/二手（仅搜索摘要） | 2026-09-02 |
| [18] | Xbox Wire – Baldur's Gate 3: Patch 8 Now Live, Bringing 12 New Subclasses；bg3.wiki Patch 8；Screen Rant / TheGamer 报道 | https://news.xbox.com/en-us/2025/04/15/baldurs-gate-3-patch-8-new-subclasses/ ；https://bg3.wiki/wiki/Guide:Patch_8_preview | 一手/二手（仅搜索摘要） | 2026-09-02 |
| [19] | Larian 文档 – Adding Classes and Subclasses；Nexus Flowerborn 全教程（mod 4502）、Make New Abilities for Your Subclass（mod 5999）、toolkit 视频 976 / 923；mod.io Adding New Classes or Subclasses；wiki.bg3.community Basic Class Creation；CL wiki Tutorials | https://docs.baldursgate3.game/Adding_Classes_and_Subclasses ；https://www.nexusmods.com/baldursgate3/mods/4502 | 一手/二手（仅搜索摘要；wiki.bg3.community 抓取为空页） | 2026-09-02 |
| [20] | Screen Rant – How To Install (& Use) BG3 Mod Manager；thegamercodex BG3 Mod Manager；bg3modmanager.net；Nexus BG3SE（mod 2172） | https://screenrant.com/baldurs-gate-3-how-to-install-mods-manager/ ；https://thegamercodex.com/en/baldurs-gate-3/tools/bg3-mod-manager | 三手（仅搜索摘要） | 2026-09-02 |
| [21] | Nexus：Honourable Saves（5486）、Honour mode Save Files（5045）、Save in Honour Mode（4757）、Respec spell（2397）；Pixel Twelve Respec and Multiclass Guide | https://www.nexusmods.com/baldursgate3/mods/4757?tab=posts ；https://pixeltwelve.com/articles/baldurs-gate-3-respec-multiclass-guide | 二手/三手（仅搜索摘要） | 2026-09-02 |
| [22] | Larian 论坛 "Discord for BG3???"；X 账号 DownByTheRiverCommunity (@DBTRcommunity) | https://forums.larian.com/ubbthreads.php?ubb=showflat&Number=736978 ；https://x.com/dbtrcommunity?lang=en | 三手（仅搜索摘要） | 2026-09-02 |
| [23] | GitHub LaughingLeader/BG3ModManager（及 wiki Changelog）；GitHub Norbyte/bg3se；Nexus Mod Change Tracker - Modders Resource（mod 15172）；Steam 指南 BG3 2023 Modding Guide | https://github.com/LaughingLeader/BG3ModManager ；https://github.com/Norbyte/bg3se ；https://www.nexusmods.com/baldursgate3/mods/15172 | 一手/二手（仅搜索摘要） | 2026-09-02 |
| [24] | GitHub BG3-Community-Library-Team/Sample-Template；GitHub FrederickEngelhardt/bg3-progressions-compatibility-patches | https://github.com/BG3-Community-Library-Team/Sample-Template ；https://github.com/FrederickEngelhardt/bg3-progressions-compatibility-patches | 一手（仅搜索摘要） | 2026-09-02 |

未读取、仅在搜索结果中出现、本报告不作引用的条目：GM Binder "Leuku's Discussion on Innovative Homebrew Class Design"；D&D Beyond 论坛 "Home brew classes that are balanced"、"1DnD Design Philosophy"；vocal.media "How to Balance Your D&D Homebrew Class"；YouTube 自定义法术图标教程。

---

## 6. 审计

| 项目 | 数值 |
|---|---|
| WebSearch 调用数 | 18（预算约 18，已用满） |
| WebFetch 调用数 | 14（预算约 14，已用满） |
| 搜索结果返回的链接总数 | 约 145 条（含跨查询重复） |
| 实际打开的页面 | 14 个：成功 8（GitHub ×4、wordpress、kthomebrew、dndbeyond、bg3.wiki），失败 6 |
| 失败明细 | docs.baldursgate3.game 403；Nexus articles/643 403；media.wizards.com UA PDF 404；mod.io 指南、wiki.bg3.community ×2 仅返回标题（JS 渲染空页） |
| 重试 | 0 次（原因见第 4 节第 9 条：失败均为确定性拦截且预算已尽） |
| 无相关结果的查询 | 1（作者公开开发时长） |
| 引用来源数 | 24 个编号来源，其中全文抓取 8、仅搜索摘要 16 |
| 标注为 `[背景知识—非本次检索]` 的内容 | 12 级上限与 ASI 等级、5e 子职业节点表、法术槽三档、ImpUI 的作用、ActionResourceDefinitions/反应弹窗、联机需同套 mod、texconv 用途 |
