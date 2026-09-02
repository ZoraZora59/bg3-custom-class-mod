# 子课题 E：脚本能力边界与研发基建（编辑器 / 调试 / 打包自动化 / 仓库结构）

- 调研日期：2026-09-02
- 目标项目：自创新职业 / 子职业 mod（Baldur's Gate 3）
- 开发环境：Apple Silicon Mac（编辑 / 设计 / 脚本）+ Windows PC（官方 Toolkit、Script Extender、游戏内验证）
- 引用规则：正文中 `[n]` 指向第 5 节来源列表，只包含本会话 WebSearch / WebFetch 实际返回的内容；凡标注 `[背景知识—非本次检索]` 的内容来自训练记忆，未在本次会话中核实，不计入来源统计；标注 `[本机核查]` 的内容来自在这台 Mac 上对 LSLib 上游仓库的浅克隆检查（commit `6f5f698`, 2026-03-31）与环境检查，不计入来源统计。
- 抓取受阻说明：Larian 官方文档站 `docs.baldursgate3.game` 对本工具两次返回 403，因此官方 Functors / Osiris 页面只能引用搜索摘要；bg3.wiki 上并不存在 `Modding:Boosts` / `Modding:Functors` / `Modding:Conditions` 这三个页面名（均 404），bg3.wiki 的相关内容散落在 `Modding:Coding_An_Item`、`Modding:Items` 等页面；wiki.bg3.community 为 JS 渲染站点，直接抓取只返回标题。

---

## 1. TL;DR

1. **不用 Script Extender（SE）就能做的事比想象中多。** 职业 mod 的核心机制——等级表、被动、法术、动作资源、状态、反应——全部由纯文本 Stats DSL（Boosts / Functors / Conditions）+ `.lsx` 数据表驱动。官方文档对 Functors 的定义是 "immediate changes to game state that fire and forget, used by passives, spells, statuses and interrupts" [9]。检索到的职业教程与官方 "Adding Classes and Subclasses" 页面均不涉及 Lua 或 Osiris [15][20]。
2. **权威参考在 Larian 官方文档站，但机器可读性差。** `Functors`、`Functors:UseActionResource`、`Stats Expressions`、`Adding Classes and Subclasses` 等页面存在于 `docs.baldursgate3.game`（并镜像到 mod.io 指南区）[9][13][14][15][16]，本次抓取被 403 拦截。bg3.wiki 没有独立的 Boosts/Functors/Conditions 参考页，但 `Modding:Coding_An_Item` 有可直接复用的真实片段 [8]。
3. **Osiris 对职业 mod 几乎不需要。** Osiris 是 Toolkit 的 Story Editor 里按 goal（INIT/KB/EXIT）编写、编译成 `story.div` 的事件脚本 [10][11]；职业机制不经过它。反而要注意 Patch 8 后 Osiris 脚本冲突是已知崩溃源，社区有专门修复 mod 与调试指南 [37][38]。
4. **BG3SE 现状（截至 2026-06）：v32（2026-06-21）"Supports patch 8"，自动更新，不支持 Patch 5 之前的游戏版本；v31 已内嵌进启动器作为在线更新失败时的回退** [4]。结构固定：`Mods/<Mod>/ScriptExtender/Config.json` + `Lua/BootstrapServer.lua` / `BootstrapClient.lua`；控制台、`reset` 热重置、VS Code 调试器（`EnableLuaDebugger`）、`ExtIdeHelpers.lua` 类型定义齐全 [2][3]。
5. **"SE 与否"的分界线很清楚：** 需要游戏内配置界面（IMGUI/MCM）、运行时改 stats、跨回合/跨存档的自定义状态、客户端-服务端自定义同步、定时器逻辑 → 必须 SE；标准职业特性 → 不必。IMGUI 与 MCM 需要 SE v18+ / MCM v1.9+ [46]；MCM 的非拉丁字符显示问题要靠 SE 上游扩展字体 glyph 范围 [46]——中文 UI 是明确风险点。
6. **打包与发布链路：** LSLib `Divine` 的 CLI 参数已从源码核实（`-a create-package|extract-package|convert-resource|convert-loca …`，默认压缩 `lz4hc`）[7]；Nexus 有官方 GitHub Action（基于 v3 API，输入 api key / file id / zip / version）且 Upload API 仍是 beta、"focused on updating existing mods" [18][19]；mod.io 的官方路径是在 Toolkit 编辑器内直接发布并接受审核，或本地打包后传到第三方站 [12]。`Version64` 是 int64，`1.0.0.0 = 36028797018963968`，位布局 `Major<<55 | Minor<<47 | Revision<<31 | Build` [23][本机核查]。
7. **Mac 上打包不是"开箱即用"。** `Divine.csproj` 目标框架是跨平台的 `net8.0`，但 `LSLib.csproj` 无条件引用 C++/CLI 原生项目 `LSLibNative.vcxproj`（仅被 GR2 解压路径使用），且构建前事件依赖 Windows 版 GpLex/Gppg 二进制 [本机核查]；社区在 Linux 上的做法是 Wine/Bottles + .NET 8 安装器运行 Windows 版工具 [39]。**双机分工下，默认在 Windows 侧打包（ConverterApp / Divine.exe / BG3MM），Mac 只负责源码。**
8. **编辑器：** VS Code 上有 `bg3-mod-helper`（UUID/handle 生成、实例查找、打包/loca/DDS 转换、悬停函数信息）[41][27]、`bg3txt-formatter`（stats .txt 高亮/格式化）[42]、`BG3-SE-Snippets`（SE 事件监听片段）[43]、`vscode-bg3-modding`（UUID/Handle/`Ext.Osiris.RegisterListener()`/meta.lsx 等片段）[44]；Lua 补全靠 SE 仓库的 `ExtIdeHelpers.lua` [2][25]。

---

## 2. 分节详细发现

### 2.1 不需要 Script Extender 的能力边界：Stats 文本 DSL

#### 2.1.1 三类原语的分工

| 原语 | 作用 | 出现位置（本次检索证实的） |
|---|---|---|
| **Boosts** | 声明式"加成"，给角色/物品持续性能力（解锁法术、熟练项、动作资源、法术位等） | 物品 `data "Boosts"`（"Boosts are used to force items to give specific abilities, such as unlocking spells"）[31]；Progressions 表的 Boosts 列（"In progression data, Boosts contain values like proficiencies and other character abilities"）[31]，例如 `ActionResource(Rage,2,0)`、`UnlockedSpellSlotLevel1` [21] |
| **Functors** | 即时、一次性的状态改变："immediate changes to game state that fire and forget, used by passives, spells, statuses and interrupts" [9] | 被动的 `StatsFunctors`、法术的成功/失败段、状态、反应（interrupt）[9][8] |
| **Conditions** | 布尔表达式，决定 functor 是否执行 / 目标是否合法；Khonsu 脚本也能用同一套："Conditions and functors that are usable in Stats are also available in Khonsu, with a list of hardcoded Thoth conditions available" [17] | `IF(...)` 前缀、`Conditions` 字段、`TargetConditions` 等 [8] |

> 文件位置 `[背景知识—非本次检索]`：Stats 文本一般放在 `Public/<ModFolder>/Stats/Generated/Data/*.txt`（`Passive.txt`、`Spell_*.txt`、`Status_*.txt`、`Interrupt.txt`…），条目格式为 `new entry "NAME"` / `type "PassiveData"` / `data "Key" "Value"`。bg3.wiki 的示例页确实按 `Armor.txt` / `Passive.txt` 分节 [8]，与此一致。

#### 2.1.2 权威参考页面（可达性说明）

| 页面 | 地位 | 本次状态 |
|---|---|---|
| Larian 官方 `Functors` | 一手，定义 + 列表 | 搜索命中 [9]，抓取 403 |
| Larian 官方 `Functors:UseActionResource` | 一手，单个 functor 页（说明官方文档按 functor 分页） | 仅标题 [13] |
| Larian 官方 `Stats Expressions` | 一手，表达式/骰子语法 | 仅标题 [14] |
| Larian 官方 `Adding Classes and Subclasses` | 一手，职业专题 | 仅标题 [15] |
| mod.io 指南 `Restore Your Custom Class Action Resource` | 官方指南镜像，专讲自定义资源恢复 | 搜索摘要 [16] |
| mod.io 指南 `Adding Khonsu (.khn) condition scripts` | 官方指南镜像 | 搜索摘要 [17] |
| bg3.wiki `Modding:Coding_An_Item` | 二手，但有逐字游戏数据示例 | 抓取成功 [8] |
| bg3.wiki `Modding:Items` | 二手 | 搜索摘要 [31] |
| wiki.bg3.community `Basic Class Creation` / `Progressions` | 二手，职业教程 | 搜索摘要 [20][21] |

**分歧/缺口：** 用户提问里点名的 `Ability()`、`Proficiency()`、`Advantage()`、`StatusImmunity()`、`IncreaseMaxHP()`、`SpellSaveDC()`（Boosts），`Summon`、`SurfaceChange`、`RegainHitPoints`、`ExecuteWeaponFunctors`、`UseSpell`（Functors），`IsMeleeAttack()`、`Tagged()`、`TurnBased()`、`DistanceToTargetGreaterThan()`（Conditions）在本次检索返回的内容中**没有逐字出现**，这些名称属于 `[背景知识—非本次检索]`；确认它们的准确签名需要在 Windows 上打开官方文档站，或直接解包 `Shared.pak` / `Gustav.pak` 里的 Stats 文本对照（见 2.4.5 的 `extract-package` 用法）。

#### 2.1.3 真实示例片段（逐字引自检索页面）

**示例 1 — 物品通过 Boosts 解锁法术、挂载被动**（`Armor.txt`）[8]：

```
data "Boosts" "UnlockSpell(Target_MAG_HealingWord);UnlockSpell(Shout_MAG_HealingWord_Mass)"
data "PassivesOnEquip" "MAG_Radiant_Radiating_Helmet_Passive;CUSTOMPASSIVEIMADE"
```

**示例 2 — 被动：触发上下文 + 条件 + functor**（`Passive.txt`）[8]：

```
data "StatsFunctorContext" "OnAttacked"
data "StatsFunctors" "IF(context.HasContextFlag(StatsFunctorContext.OnAttacked) and HasStatus('MAGE_ARMOR') and IsLastConditionRollSuccess(ConditionRollType.ConditionSavingThrow) and not Self() and IsSavingThrow()):DealDamage(SWAP, 1d4, Radiant,Magical)"
```

可以读出的语法事实：`IF(<条件>):<functor>` 的冒号结构；条件里用 `and` / `not` 组合；`context.HasContextFlag(StatsFunctorContext.X)` 用来在同一个被动上区分多种触发；`DealDamage(SWAP, 1d4, Radiant,Magical)` 第一个参数是目标选择符（`SWAP`），随后是骰子表达式、伤害类型、标记。

**示例 3 — 职业资源与恢复**：
- Progressions 的 Boosts 列写法 `ActionResource(Rage,2,0)`；法术位要出现在 UI 上，需要 `UnlockedSpellSlotLevel1` 之类的 boost [21]。
- 自定义资源恢复的 functor 写法："RestoreResource(YOUR_CUSTOM_RESOURCE, Percent%OrNumber, 0 is the first level of the resource)" [16]——第三个参数是资源等级索引（0 为第一级）。
- 状态施加：`ApplyStatus(SHOCKING_GRASP, 100, 2)`（状态名、成功率、持续回合）[8][20][31]（该片段来自同一批检索结果的摘要）。

#### 2.1.4 StatsFunctorContext 与被动的触发上下文

- 定义："StatsFunctorContext specifies what the passive is waiting for to activate, and when it triggers, conditions are checked to determine if the passive will work. To use StatsFunctorContext, you check what parameter was called (e.g., if triggered from OnCast), then use a colon to specify what happens." [20]
- 本次检索证实出现过的取值：`OnAttacked`、`OnCast`、`OnStatusRemoved`、`OnStatusApplied`、`OnHealed`、`OnDamage` [8][20]。
- 实务含义：一个被动可以声明多个上下文（分号分隔，`[背景知识—非本次检索]`），再在 `StatsFunctors` 里用 `context.HasContextFlag(...)` 分流 [8]。这是"不用 SE 做事件驱动逻辑"的主要手段。

#### 2.1.5 Interrupt（反应）机制

- 官方定义把 interrupt 与 passives / spells / statuses 并列为 functor 的宿主 [9]，即反应也是 Stats 条目（`[背景知识—非本次检索]`：类型 `InterruptData`，字段包括 `InterruptContext`、`InterruptContextScope`、`Conditions`、`Roll`、`Success`、`Failure`、`Cost` 等）。
- 已知硬限制（检索摘要）："OnPostRoll reactions can trigger on SavingThrow() calls in passive feature StatsFunctors but not in their Conditions. This is an inherent limitation of InterruptContext flags OnPostRoll and OnPreDamage." [30]（该句出自首轮检索结果集，最可能来自 bg3.wiki 的被动特性模板文档页，归属不完全确定。）
- 结论：反应可以纯 Stats 实现，但"在哪个时机能看到哪些信息"由 `InterruptContext` 的引擎实现决定，超出其表达力的反应逻辑（例如依赖多回合历史、依赖其他单位的隐藏计数）只能上 SE。

#### 2.1.6 无 SE 的能力边界小结

能做（证据见上）：新职业/子职业进阶表、被动（含事件式触发）、法术、状态、自定义动作资源及其恢复、反应、物品联动。
做不到 / 做不好（推断 + 2.3 的 SE 能力对照）：游戏内配置菜单、运行时按配置改数值、跨回合/跨存档的自定义计数与状态机、客户端-服务端自定义数据同步、每 tick/定时逻辑、依赖其他 mod 的动态注入（bg3.wiki 有 `Modding:Compatibility Framework` 专页 [58]，其实现依赖 SE，`[背景知识—非本次检索]`）。

### 2.2 Osiris story 脚本

- **是什么：** Toolkit 的 Story Editor 用来"create and modify story goals"；左侧是 goal 层级，展示游戏内全部 goal；右侧三段：INIT（goal 激活时只跑一次，如设置角色）、KB（"where the bulk of the script goes"，goal 活跃期间持续评估）、EXIT（仅在 `GoalCompleted` 调用时执行）[11]。
- **编译产物：** "The story.div file includes all the current Osiris goals, compiled in one single file"，可通过 `File > Open Story.div` 打开，或在 `...\Data\Mods\<YourMod>\Story` 下找到 [11]。官方还有 `Osiris: Introduction to Debugging` 页面 [56]。
- **职业 mod 是否需要：** 检索到的职业教程（`Basic Class Creation`、`Progressions`）只涉及 Stats / Progressions / 资源定义 [20][21]，官方 `Adding Classes and Subclasses` 亦为独立专题 [15]，均未出现 Osiris；据此判断**标准职业 mod 不需要 Osiris**（推断，基于教程覆盖面）。需要 Osiris 的典型场景是世界事件、对话/任务、场景触发（`[背景知识—非本次检索]`）。
- **风险：** Patch 8 之后 Osiris 脚本错误与崩溃是社区热点——Nexus 上有专门的 "Fix for Patch 8 Osiris Scripts Error and Crash (formerly known as Script Fix)" mod 与 "How to Debug and Fix Osiris in Baldur's Gate 3 (works in patch 8)" 指南 [37][38]。对职业 mod 的启示：**不要为了"顺手"引入 story goal**，避免把自己卷入 story 合并冲突。
- **与 BG3SE `Ext.Osiris` 的关系：** SE 的 `Ext.Osiris` 可 "Call Osiris functions, queries, events, PROCs, user queries, and databases from Lua" [2]，并用 `Ext.Osiris.RegisterListener(name, arity, event, handler)` 监听（`event` 取 `"before"` / `"after"` / `"beforeDelete"` / `"afterDelete"`）[2]：

```lua
Ext.Osiris.RegisterListener("TurnEnded", 1, "after",
    function (characterGuid)
        _P("TurnEnded- " .. characterGuid)
    end)
```

即：**用 SE 的 Lua 去"听"引擎已有的 Osiris 事件，而不必自己写 goal**——这是职业 mod 想做回合级逻辑时最省事的路径。SE 的 `ScriptExtenderSettings.json` 还提供 Osiris 活动日志、story 编译日志与编译错误日志开关 [1]。

### 2.3 BG3SE Lua

#### 2.3.1 现状与版本（截至 2026-09 能确认的）

- README："The Script Extender adds Lua/Osiris scripting support to the game." 组件包含 Lua（带调试器接口）、Osiris（带编译日志）、控制台、崩溃上报、成就兼容 [1]。
- 发布页：`Script Extender (2026 Jun 21) - v32`——"Supports patch 8"，扩展器自动更新，GitHub 新 release 通常只代表更新器变化；"Game versions older than patch 5 are not supported"。`v31 (2026 Apr 17)`："SE v31 is now embedded into the launcher as a fallback if online update fails." 安装方式仍是把 `DWrite.dll` 放进 `Baldurs Gate 3\bin` [4]。
- 问题追踪：Issue #496 "Patch 8 compatible?"（2025-04-15）报告 Patch 8 后创建角色即卡死崩溃，页面上未见维护者回复 [5]；Nexus 讨论区同期认为"Non-mod.io Nexus mods based on script extender are most likely to become incompatible with Patch 8"，需等 Norbyte 更新 [51]。
- **未能确认：** Patch 8 之后各 hotfix 的逐个兼容状态、Ext.UI(Noesis) 与 Ext.IMGUI 在最新版本的稳定性。

#### 2.3.2 目录与配置（逐字引自 API.md）[2]

`Mods\YourMod\ScriptExtender\Config.json`：

```json
{
    "RequiredVersion": 29,
    "ModTable": "YOUR_MOD_NAME_HERE",
    "FeatureFlags": ["Lua"]
}
```

| 键 | 含义（原文） |
|---|---|
| `RequiredVersion` | "Osiris Extender version required to run the mod" |
| `ModTable` | "Name of the mod in the global mod table (`Mods`) when using Lua; must be unique" |
| `FeatureFlags` | "List of features that the mod is using; currently accepts `Lua`" |

入口脚本位于 `Mods\<YOURMOD>\ScriptExtender\Lua\`："The extender will attempt to load `BootstrapServer.lua` on the server side, and `BootstrapClient.lua` on the client side." 其它文件用 `Ext.Require()` 加载；`Ext.Require` 会检查 `Mods/<ModuleUUID>/ScriptExtender/Lua/<path>` 是否已加载并缓存返回值；"`Ext.Require` should only be called during module startup … Loading Lua files after module startup is deprecated." [2]

#### 2.3.3 Server / Client 分层与常用模块 [2]

| 模块 | API.md 描述 | 对职业 mod 的用途 |
|---|---|---|
| `Ext.Osiris` | 从 Lua 调用/监听 Osiris 函数、查询、事件、PROC、数据库 | 监听 `TurnEnded` 等回合事件做跨回合逻辑 |
| `Ext.Stats` | 读取与修改 stat 条目（spells/statuses/passives/equipment…） | 运行时按配置改数值、动态生成变体 |
| `Ext.Events` | 引擎生命周期事件（GameStateChanged、SessionLoaded…） | 初始化时机 |
| `Ext.Timer` | "Schedule code execution at a future point in time or on each game loop tick" | 延时/定时；每 tick 回调需注意性能 |
| `Ext.Vars` | 用户变量/模组变量，带网络同步与持久化 | 跨存档的自定义计数、状态机 |
| `Ext.Entity` | "Query, create, and modify game entities and their components (ECS system)" | 读取角色组件（资源、状态） |
| `Ext.Net` | NetChannel API，服务端/客户端通信 | 自定义数据同步 |
| `Ext.UI` | "Create and modify Noesis viewmodels; bind to UI elements" | 改原生 UI |
| `Ext.IO` / `Ext.Json` / `Ext.Math` / `Ext.Loca` | 文件、JSON、数学、本地化 | 配置读写、动态文本 |

`Ext.IMGUI` 未出现在 API.md 的抓取摘要中，但社区教程指出通过 `Ext_ClientIMGUI` 的 `NewWindow()` 创建窗口并返回 `ImguiHandle` 对象，且第一步是去 SE 仓库找 `ExtIdeHelpers.lua` [25]。可见 IMGUI 是**客户端**能力，配合 `Ext.Net` 才能驱动服务端逻辑。

#### 2.3.4 控制台、日志与热重载

- 开启：在游戏 `bin` 目录创建 `ScriptExtenderSettings.json`，内容 `{ "CreateConsole": true }`，启动后会多开一个控制台窗口 [34]；载入存档后按一次 Enter 进入输入模式 [24]。
- 用法（API.md 原文）："Press `<enter>` to enter console mode; in this mode the normal log output is disabled to avoid log spam." 输入 `client` / `server` 切换执行环境；`!<command>` 触发 `RegisterConsoleCommand` 注册的回调；可直接执行 Lua（如 `_P(1234)`）；`reset` "Reinitializes server and client Lua VM"；`exit` 回到日志模式；多行模式以 `--[[` 开始、`]]--` 结束 [2]。
- **热重载：** 本次检索未见文件级热重载 API；可用的是 `reset` 重建 Lua VM [2]（加载 Lua 文件的操作被限定在启动阶段 [2]，所以"改文件 → `reset`"是实际的迭代方式，推断）。
- 日志：`ScriptExtenderSettings.json` 可把控制台与脚本输出写入日志文件，并可指定 Osiris 日志目录、开启运行时/编译日志 [1]。**具体默认日志路径本次未能确认。**

#### 2.3.5 调试器（VS Code）[3]

- 前置：安装 "BG3 Lua Debugger extension"（发布于 bg3se-updates 仓库）；`bin\ScriptExtenderSettings.json` 加 `"EnableLuaDebugger": true`；单独下载并解压 `DebugAdapter.zip`。README 另提到调试端口可配置（Osiris 9999、Lua 9998）[1]。
- `launch.json` 需把占位路径换成实际适配器路径，反斜杠要转义：`"program": "C:\\Whatever\\DebugAdapter\\LuaDebugger.exe"`；可选用 `preLaunchTask` / `postDebugTask` 让 VS Code 托管游戏启停。
- 顺序：先启动游戏，再按 F5；否则报 "Could not connect to Lua debugger backend: No connection could be made [...]"。
- 能力：单步（break/continue/step over/into/out）、调用栈、局部变量与 upvalue、监视、异常断点、普通断点、控制台求值；限制："Conditional breakpoints and logpoints are not supported"。
- 结论：**调试器只能在运行游戏的 Windows 机器上跑**（适配器是 `.exe`，且要连接本机游戏进程）。

#### 2.3.6 IDE 类型定义

- API.md："Please refer to the ExtIdeHelpers … for a more comprehensive and systematic definition/reference of the API."，文件为 SE 仓库 `BG3Extender/IdeHelpers/ExtIdeHelpers.lua` [2]。社区 IMGUI 教程同样以定位该文件为起点 [25]。
- 用法（`[背景知识—非本次检索]`）：在 VS Code 装 Lua 语言服务器（sumneko/LuaLS）后把该文件加入 workspace library，即可获得 `Ext.*` 补全与类型提示；此文件与平台无关，**Mac 上可用**。

#### 2.3.7 IMGUI / MCM 与中文显示风险

- "Script Extender (v18+) powers the IMGUI UI in-game and works with Mod Configuration Menu (v1.9+)" [46]；MCM 有社区 wiki 文档页 [26]，也曾出现 SE 更新干扰 MCM 的问题单 [47]。
- 字符显示："Character display issues need to be addressed upstream in BG3SE by adding Latin extended characters to its default font glyph range, and once SE exposes those glyphs, MCM should be able to display them normally. This affects any mod that uses IMGUI." [46]——连拉丁扩展字符都依赖上游字体范围，**中文在 IMGUI 中能否正常显示未能确认，应视为高风险**。

### 2.4 研发基建

#### 2.4.1 源码仓库布局

社区 git 教程给出的约定：`Source/` 下分 `Localization/`、`Mods/`、`Public/`；"Localization: Requires a subfolder for the language you're localizing in, and a .xml file of any name"；"Mods: Contains a folder with the name of your mod, within which you'll need a meta.lsx file, which defines the metadata, including the UUID, Name, and expected folder"；此外常见 `Assets/` 与 `Releases/`，"exist to store artifacts relating to publishing your mods - zipped up .pak files, images for your nexus page, etc." [22]。SE 部分固定在 `Mods/<Mod>/ScriptExtender/` [2]。

据此推荐（`Public/` 子目录名称为 `[背景知识—非本次检索]`）：

```
<repo>/
  Source/                      # Divine create-package 的 --source 根目录
    Mods/<ModFolder>/
      meta.lsx
      ScriptExtender/          # 仅在需要 SE 时存在
        Config.json
        Lua/BootstrapServer.lua
        Lua/BootstrapClient.lua
    Public/<ModFolder>/
      Stats/Generated/Data/*.txt
      Progressions/Progressions.lsx
      ClassDescriptions/ClassDescriptions.lsx
      ActionResourceDefinitions/ActionResourceDefinitions.lsx
      GUI/  Assets/  ...        # 图标 atlas、DDS
    Localization/English/<Mod>_English.xml
  Assets/                      # 源图 PNG、PSD、Nexus 页面素材
  Releases/                    # 若坚持提交产物；否则改用 GitHub Releases
  scripts/                     # 打包脚本、UUID/Version64 小工具
  .github/workflows/           # 可选 CI
```

#### 2.4.2 二进制资产与 PAK 是否入库

- 社区惯例允许把 zip 后的 `.pak` 放在 `Releases/` [22]，但这是"存放发布物"，不是构建输入。
- 建议（一般工程实践，非检索结论）：`.pak` 不入 git，交给 GitHub Releases / Nexus；`.dds`、`.gr2`、`.loca` 这类生成物若必须入库，用 Git LFS 跟踪；本次**未检索到 BG3 mod 社区关于 LFS 的专门指引**。

#### 2.4.3 UUID / handle / Version64

- UUID 与本地化 handle 的生成与去重：`bg3-mod-helper` 扩展"streamlining the creation and management of UUIDs and handles"，带 Instance Finder（悬停显示某 UUID/handle 在项目中的使用处）与右键 Quick Navigation [41][27]；`vscode-bg3-modding` 提供 `BG3 UUID`、`BG3 Handle` 片段 [44]；`BG3ModdingTools` 是一组 Python 脚本（部分功能需要 LSLib）[45]。
- `Version64`：社区 wiki 说明它是 Int64，`"36028797018963968"` 在 BG3 Mod Manager 里显示为 `1.0.0.0`，可用 BG3MM / Multitool / Padme 的 Mini Tool 生成 [23][54]；SE 的 `Ext.Mod` 在 meta.lsx 用了 `Version` 而非 `Version64` 时会误报 `0.0.0.0` [47]。
- 位布局 `[本机核查]`（LSLib `LSLib/LS/Resource.cs`）：`Major = (packed >> 55) & 0x7f`，`Minor = (packed >> 47) & 0xff`，`Revision = (packed >> 31) & 0xffff`，`Build = packed & 0x7fffffff`；本机验证 `1 << 55 == 36028797018963968`，与 [23] 一致。可写成脚本（依据上述源码改写）：

```python
def version64(major, minor, revision, build):
    return ((major & 0x7f) << 55) | ((minor & 0xff) << 47) \
         | ((revision & 0xffff) << 31) | (build & 0x7fffffff)
# version64(1, 0, 0, 0) == 36028797018963968
```

#### 2.4.4 lsx 校验手段

本次**未检索到**社区维护的 lsx XML Schema / XSD。可用的替代：`bg3-mod-helper` 的实例查找可发现悬空 UUID/handle [27]；bg3.wiki 有 `Modding:Working with LSX files` / `Modding:LSX files` 页面（仅标题）[59]；LSLib 能在 `lsx`↔`lsf` 间转换 [6][7]，一次 `convert-resource` 往返即可当作"能否被引擎解析"的粗校验（推断）。

#### 2.4.5 LSLib / Divine 命令行

LSLib 自述为 "Tools for manipulating Divinity Original Sin and Baldur's Gate 3 files"，支持 PAK、LSV 存档包、LSB/LSF/LSX/LSJ 资源转换、GR2 网格/动画转换、story (OSI) 数据库编辑；构建依赖 GPLex、GPPG、Protocol Buffers 编译器 [6]。`Divine` 的全部选项（逐字来自 `Divine/CLI/CommandLineArguments.cs`）[7]：

| 选项 | 说明（原文） | 取值 / 默认 |
|---|---|---|
| `-l, --loglevel` | "Set verbosity level of log output" | off/fatal/error/warn/info/debug/trace/all，默认 info |
| `-g, --game` | "Set target game when generating output" | dos/dosee/dos2/dos2de/**bg3** |
| `-s, --source` | "Set source file path or directory" | |
| `-d, --destination` | "Set destination file path or directory" | |
| `-f, --packaged-path` | "File to extract from package" | |
| `-i, --input-format` / `-o, --output-format` | 批处理输入/输出格式 | dae/glb/gltf/gr2/lsv/pak/lsj/lsx/lsb/lsf |
| `-a, --action` | "Set action to execute" | create-package, list-package, extract-single-file, extract-package, extract-packages, convert-model, convert-models, convert-resource, convert-resources, **convert-loca**, build-vt；默认 extract-package |
| `-c, --compression-method` | "Set compression method" | zlib/zlibfast/lz4/lz4hc/none，默认 lz4hc |
| `-x, --expression` | "Set glob expression for extract and list actions" | 默认 `*`；配 `--use-regex` 改为正则 |
| `--package-priority` | "Set a custom package priority" | 默认 0 |
| `--use-package-name` | "Use package name for destination folder" | |
| `--legacy-guids` | "Use legacy GUID serialization format when serializing LSX/LSJ files" | |
| `-e, --gr2-options` | GR2/DAE 转换选项 | export-normals … conform-copy |
| `--vt-root` / `--fast-build` / `--vt-validate` | 虚拟纹理构建 | |

检索到的实际命令行（原样）：

```
Divine.exe --action create-package --game bg3 --source "mod_files/" --destination "MyMod.pak" --compression-method zlib
```
（来自社区 CLI 指南 [32]）

```
divine -g dos2de -a extract-package -s "{path_to_pak_file}" -d "{destination_directory}"
```
（来自 Divine 原作者分叉的 README [33]；换成 `-g bg3` 即可）

由上述已核实参数**拼接的示意命令（本次未运行）**：

```
# 打包（默认 lz4hc）
Divine.exe -g bg3 -a create-package -s ".\Source" -d ".\build\MyClass.pak"
# 解包官方数据用于对照，仅取进阶表
Divine.exe -g bg3 -a extract-package -s "<Game>\Data\Shared.pak" -d ".\dump\Shared" -x "*/Progressions/*"
# lsf -> lsx（单文件 / 批量）
Divine.exe -g bg3 -a convert-resource  -s in.lsf -d out.lsx
Divine.exe -g bg3 -a convert-resources -s .\dump -d .\dump_lsx -i lsf -o lsx
# 本地化 xml -> loca
Divine.exe -g bg3 -a convert-loca -s .\Source\Localization\English\MyClass_English.xml -d .\build\MyClass_English.loca
```

GUI 替代：ConverterApp 的 "PAK / LSV Tools" 页填源目录与包路径后点 Create Package [29]；BG3 Mod Manager 内部也调用 LSLib 读 pak/lsb [52]。

#### 2.4.6 CI（GitHub Actions）

- **未找到**一个可核实的、用 Divine 打包 BG3 mod 的公开完整 workflow。`jinghaihan/bg3-mod-collection` 有 Actions 页面但内容未抓取 [48]；搜索摘要提到一个"AI 驱动简中本地化 + XML/LOCA 校验 + 仅本地化 PAK 生成"的工作流仓库，但结果中未给出可引用 URL。
- 可行做法（示意，未验证）：`windows-latest` runner → 下载 LSLib release zip → `Divine.exe -g bg3 -a create-package …` → 打 zip → 用 Nexus 官方 action 上传（见 2.4.7）。LSLib release 资产命名与解压路径本次未核实。

#### 2.4.7 发布自动化

- **Nexus：** 官方 `Nexus-Mods/upload-action` "uploads a new version of a file to NexusMods using the NexusMods v3 API"，输入为 API key、目标 file ID、zip 文件名、版本字符串 [18]；官方新闻称 Upload API 为 beta，"the first beta is focused on updating existing mods"，完整创建流程视反馈再定 [19]。即：**首次建页仍手动，后续版本可自动化。**
- **mod.io：** 官方发布指南——Toolkit 可直接上传到 mod.io；"publish your mod via the editor where it will be moderated and made visible in the in-game browser, or pack your mod locally to upload to a third-party site"；需要 Larian 账号与 mod.io 账号并完成绑定 [12]；mod.io 提供跨 PC/主机的下载、审核与指南托管 [53]。**mod.io 网页端能否绕开 Toolkit 直传、以及直传后是否进入游戏内浏览器——未能确认。**

### 2.5 编辑器支持

| 工具 | 类型 | 功能（检索摘要） | Mac 可用性 |
|---|---|---|---|
| `bg3-mod-helper`（VS Code） | Nexus 发布 + 社区 wiki 有专页 | UUID/handle 创建管理、打包、转 loca、图标进 atlas、png/dds 互转、悬停函数信息、Instance Finder、Quick Navigation [41][27] | 编辑类功能应可用；打包/loca/DDS 等依赖 LSLib/Windows 工具链的功能在 Mac 上**未验证** |
| `bg3txt-formatter`（Marketplace） | 一手 | "syntax highlighting and format for Baldur's Gate 3 text files" [42] | 纯语法扩展，可用 |
| `BG3-SE-Snippets`（Marketplace） | 一手 | "code snippets for the Baldur's Gate 3 Script Extender, mainly event listeners" [43] | 可用 |
| `Shresht7/vscode-bg3-modding` | 一手 | 片段：BG3 UUID、BG3 Handle、`Ext.Utils.Print()`、`Ext.Osiris.RegisterListener()`、Override Stat Entry、Script-Extender Config、meta.lsx 模板 [44] | 可用 |
| `ExtIdeHelpers.lua` | SE 仓库 | Lua API 完整类型定义 [2][25] | 可用 |
| `LaughingLeader/BG3ModdingTools` | GitHub | 杂项 Python 脚本，部分需 LSLib [45] | 部分可用 |
| BG3 Community Library | GitHub | 公共法术/脚本/物品/状态/被动集合，可作参考语料 [50] | 只读参考 |
| Multitool 搜索索引 | — | **本次未检索到**其索引功能说明（`[背景知识—非本次检索]`：Multitool 可对解包数据建索引搜索） | Windows |
| bg3.wiki 数据检索 | — | 可查 `Modding:*` 页面与游戏机制页面（如 `Conditions`）[60] | 浏览器即可 |
| 社区 wiki `Dev Environment Set-up` / `Tools` | wiki.bg3.community | 页面存在但抓取只返回标题 [28][61] | — |

### 2.6 测试与调试

- **控制台开启与使用：** 见 2.3.4；`bin\ScriptExtenderSettings.json` 加 `"CreateConsole": true` [34]；载入存档后 Enter 进入输入 [24]；`reset` 重建 VM [2]。
- **快速测试职业：** 社区 SE 命令集页面指出"You don't need to visit Withers at camp to change your class—executing a command triggers the level-one character creation screen immediately. Osi (Osiris) functions allow for complex world state changes." [36]；另有在线 "Script Extender Console Cheat Sheet" 用于生成控制台命令 [35]。具体的加经验 / 升级 / 重置命令名（如 `Osi.AddExperience` 之类）**本次未逐字核实**，`[背景知识—非本次检索]`。稳妥替代：准备"营地 + Withers 可用 + 各关键等级"的测试存档集，用重新分配职业来验证进阶表。
- **日志：** SE 可将控制台/脚本输出写日志、指定 Osiris 日志目录、开启 story 编译与错误日志 [1]；Toolkit 侧有官方 Osiris 调试文档 [56] 与社区 Patch 8 Osiris 调试指南 [37]。**崩溃日志与 SE 默认日志的具体路径未能确认。**
- **本地化预览：** `convert-loca` 可把 xml 转成 loca [7]；SE 的 `Ext.Loca` 可在运行时读写本地化 [2]。游戏内预览必须在 Windows 侧完成。
- **性能注意点（推断自 API 描述）：** `Ext.Timer` 支持"on each game loop tick"回调 [2]，每 tick 逻辑应尽量避免；Osiris 监听器与 `Ext.Vars` 同步都发生在服务端，客户端 IMGUI 只做展示。

### 2.7 "Mac 编辑 + Windows 验证"的双机闭环

#### 2.7.1 角色分工（依据证据）

| 环节 | 机器 | 依据 |
|---|---|---|
| 编辑 stats `.txt`、`.lsx`、loca `.xml`、Lua、meta.lsx、图标源图 | Mac | 纯文本/图片，VS Code 扩展多为语法/片段类 [42][43][44]；`ExtIdeHelpers.lua` 与平台无关 [2] |
| UUID / handle / Version64 生成 | Mac | 扩展片段 [44]、自写脚本（2.4.3） |
| 打包 `.pak`、xml→loca、png→dds | **Windows（默认）** | ConverterApp / Divine.exe 是 Windows 构建；Mac 侧 .NET 直跑证据不足（见 2.7.2） |
| 官方 Toolkit（若需 Osiris / 官方 mod.io 发布） | Windows | Toolkit 与 mod.io 发布走编辑器 [12] |
| 部署到游戏、SE 控制台/日志、VS Code 调试器、游戏内验证 | Windows | 调试适配器是 `.exe` 且需连接本机游戏 [3] |
| 发布（Nexus 自动化） | 任一机器 / CI | Nexus action 基于 HTTP API [18] |

#### 2.7.2 Mac 上跑 Divine 的证据（`[本机核查]` + [39][40]）

- `Divine/Divine.csproj`：`<TargetFramework>net8.0</TargetFramework>`（跨平台 TFM），引用 `LSLib.csproj`。
- `LSLib/LSLib.csproj`：`net8.0`，但**无条件** `<ProjectReference Include="..\LSLibNative\LSLibNative.vcxproj" />`；该 vcxproj 为 C++/CLI（`<CLRSupport>true</CLRSupport>`），包含 `granny2wrapper.cpp`、`fastlz.c`、`lz4wrapper.cpp`——C++/CLI 只能用 Windows 的 MSVC 构建。
- 原生库的唯一调用点是 `LSLib/Granny/GR2/Reader.cs`（`Granny2Compressor.Decompress/Decompress4`，即 GR2 解压）；PAK 的 LZ4 走托管包 `K4os.Compression.LZ4`（`LSLib/LS/Compression.cs`）。**因此打包/lsx/loca 路径在运行时并不需要原生库，但工程文件层面仍会阻止在 macOS 上 `dotnet build`。**
- `LSLib.csproj` 的 `PreBuildEvent` 调用 `$(SolutionDir)\external\gppg\binaries\GpLex` / `Gppg` 生成 `Goal.lex.cs` 等解析器源码；浅克隆中 `external/gppg` 不存在，生成文件也未提交。
- README 没有任何 Linux/macOS/mono 说明 [6]；本机未安装 `dotnet`（有 Homebrew 与 git 2.50.1，arm64）。
- 社区经验：Linux 指南通过 Wine/Bottles + ".NET 8.0 installer" 运行 LSLib 工具，Toolkit 在 Linux 下"no ability to render… graphical glitches" [39]；macOS CrossOver 用户曾尝试把 `lslib.dll` 标为 native 以运行 BG3MM，仍有 UI/库兼容问题 [40]。
- **结论：** 在 Mac 上用 .NET 原生构建/运行 Divine "理论上可修改工程后实现，但未经验证"；用 CrossOver/Wine 跑 Windows 版 Divine.exe 有社区先例但同样未在本会话验证。**双机分工下不值得投入，打包放 Windows。**

#### 2.7.3 最小闭环流程草案

```
[Mac]                                   [GitHub 私有仓库]                 [Windows]
VS Code 编辑                              git push  ─────────────▶        git pull
  Source/Public/.../Stats/*.txt                                            scripts\build.ps1 (示意)
  Source/Public/.../Progressions.lsx                                         ├ Divine.exe -g bg3 -a convert-loca …
  Source/Localization/English/*.xml                                          ├ Divine.exe -g bg3 -a create-package -s Source -d build\MyClass.pak
  Source/Mods/<Mod>/ScriptExtender/Lua/*.lua                                 └ copy build\MyClass.pak → 游戏 Mods 目录*
  Assets/icons/*.png                                                      BG3MM / 游戏内管理器启用 → 启动游戏
UUID / handle / Version64 脚本                                            SE 控制台 (CreateConsole) → reset / !cmd / Osi 事件
                                                                          VS Code + Lua Debugger (EnableLuaDebugger, F5)
                                         ◀──────── 反馈回流 ────────      控制台/日志文本、截图 → issue 或直接 commit 修正
```

`*` 游戏 Mods 目录路径为 `[背景知识—非本次检索]`（Windows 下通常在 `%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\Mods`），请在 Windows 侧核对。

要点：
1. **仓库即唯一事实源。** Windows 侧只做 `pull → 打包 → 部署 → 验证`，所有修改（包括在 Windows 上临时改的）都 commit 回仓库；`build/` 与 `.pak` 加入 `.gitignore`。
2. **Windows 侧的 `build.ps1`（示意，参数来自 [7]，未运行）：** 顺序执行 `convert-loca` → `create-package` → 复制到 Mods 目录；生成物用 `Version64` 与 git tag 对齐（2.4.3 脚本）。
3. **验证清单固定化：** 测试存档集（1 级 / 3 级 / 5 级 / 12 级）+ 一页"验收步骤"文档（职业出现在创建界面、每级特性、资源恢复时机、反应触发、本地化文本无 handle 裸露）。
4. **调试信息回流：** SE 控制台输出、`ScriptExtenderSettings.json` 打开的日志文件 [1]、崩溃时的复现步骤，粘贴到仓库 issue；Mac 侧据此修改再 push。
5. **发布：** 首次上架 Nexus 手动；之后可用 `Nexus-Mods/upload-action` 从 CI 或 Windows 侧更新版本 [18][19]。若目标是游戏内 mod.io 浏览器，则必须在 Windows 的 Toolkit 里走官方发布 [12]。

---

## 3. 对"自创职业 mod"项目的具体建议与决策点

### 3.1 "SE 与否"决策矩阵

| 需求 | 无 SE 可否 | 依据 / 备注 |
|---|---|---|
| 新职业/子职业、进阶表、被动、法术、动作资源 | **可** | Progressions Boosts（`ActionResource(...)`、`UnlockedSpellSlotLevelN`）[21]；Stats DSL [8][9] |
| 事件式被动（被攻击/施法/受伤/治疗时触发） | **可** | `StatsFunctorContext` + `context.HasContextFlag` [8][20] |
| 自定义资源在短休/长休/特定时机恢复 | **多数可** | `RestoreResource(...)` [16]、`UseActionResource` [13]；时机若超出内置定义则需 SE |
| 反应（Interrupt） | **可，有引擎限制** | `OnPostRoll` / `OnPreDamage` 的可见性限制 [30] |
| 跨回合计数、状态机、依赖历史的逻辑 | **需 SE** | `Ext.Osiris.RegisterListener` + `Ext.Vars` 持久化 [2] |
| 游戏内配置菜单 / 自定义 UI | **需 SE** | IMGUI（`NewWindow` → `ImguiHandle`）[25]，MCM 需 SE v18+ [46]；中文显示风险 [46] |
| 运行时按配置改数值 | **需 SE** | `Ext.Stats` [2] |
| 客户端-服务端自定义数据同步 | **需 SE** | `Ext.Net` / `Ext.Vars` [2] |
| 定时 / 每 tick 逻辑 | **需 SE** | `Ext.Timer` [2] |
| 与其他 mod 的动态兼容注入 | **通常需 SE** | Compatibility Framework 专页 [58]（细节未抓取） |
| 世界事件 / 对话 / 任务 | Osiris（Toolkit）或 SE | Story Editor [11]；职业 mod 不建议触碰（2.2） |

### 3.2 推荐技术路线

1. **v1 纯数据版（无 SE、无 Osiris）：** 用 Stats + Progressions + ClassDescriptions + ActionResourceDefinitions + Localization 完成职业主体。优点：兼容 Patch 8 及后续 hotfix 的风险最小（SE 曾在 Patch 8 期间大面积失效 [5][51]），可上 mod.io 走官方审核 [12]，主机玩家可用（推断自 mod.io 跨平台定位 [53]）。
2. **v2 可选 SE 增强层：** 把需要 SE 的功能做成独立的第二个 mod 或同一 mod 的可选模块（`ScriptExtender/Config.json` 只在该模块存在）[2]，主体不依赖 SE。这样 SE 失效时职业仍可玩。
3. **反应与资源恢复优先用引擎内置时机；** 只有当验证表明 `InterruptContext` 或恢复时机无法表达时，再引入 `Ext.Osiris` 监听 [2][30]。
4. **本地化：** 从第一天就用 handle 而不是硬编码文本；用扩展生成 handle [41][44]；Windows 侧 `convert-loca` [7]。
5. **中文 UI：** 若做 IMGUI/MCM 配置界面，先在 Windows 上验证中文字形能否显示 [46]；不能则配置项退化为纯英文或改用 JSON 配置文件（`Ext.IO` [2]）。

### 3.3 仓库与流程决策点

- 仓库布局按 2.4.1；`.pak`/`build/` 不入库；DDS/GR2 若入库走 LFS（一般实践）。
- 版本号：git tag `vX.Y.Z` ↔ `Version64`（脚本自动写入 meta.lsx，2.4.3）。
- 打包：Windows 侧 Divine.exe（2.4.5 参数已核实），Mac 不做打包。
- CI：先不做；若做，用 `windows-latest` + LSLib release + Nexus action（示意，2.4.6）。
- 发布：Nexus（后续版本可自动化 [18][19]）+ mod.io（Toolkit 内发布 [12]）双渠道；二者都从同一份 `.pak` 出。

---

## 4. 未解决问题与信息缺口

1. **官方 Stats 参考的逐字内容**（Boosts / Functors / Conditions 完整列表与签名）：官方站 403，未能核实用户点名的大部分函数名；需在 Windows 浏览器上打开 `docs.baldursgate3.game` 的 `Functors`、`Stats Expressions`、`Adding Classes and Subclasses` 页面 [9][14][15]，或解包 `Shared.pak` 对照。
2. **InterruptData 字段与各 `InterruptContext` 的确切语义**：只拿到一条限制说明 [30]。
3. **BG3SE 对 Patch 8 之后各 hotfix 的逐个兼容性、`Ext.IMGUI` / `Ext.UI` 的当前稳定性、IMGUI 中文字形**：仅有 v32 "Supports patch 8" 与字体 glyph 讨论 [4][46]。
4. **SE 默认日志与游戏崩溃日志的具体路径**：未核实。
5. **快速升级/加经验/重置的控制台命令名**：只有"命令可直接触发 1 级角色创建界面"的描述 [36]。
6. **Mac 上原生 .NET 构建 Divine**：静态分析表明需要修改工程（去掉 `LSLibNative` 引用、预生成解析器源码），未实测；CrossOver 路线未实测 [39][40]。
7. **可核实的 BG3 mod CI 示例仓库**：未找到完整 workflow 文件 [48]。
8. **mod.io 网页直传是否可行、是否进入游戏内浏览器**：未确认 [12]。
9. **lsx 校验的 schema**：未找到。
10. **社区 `Dev Environment Set-up` / `Tools` 页面正文**：JS 渲染，未抓到 [28][61]。
11. 来源 [30] 的归属（bg3.wiki 模板文档页 vs Nexus 讨论帖）不完全确定。

---

## 5. 来源列表

| # | 标题 | URL | 类型 | 获取方式 / 访问日期 |
|---|---|---|---|---|
| 1 | Norbyte/bg3se — README | https://github.com/Norbyte/bg3se | 一手 | WebFetch 成功，2026-09-02 |
| 2 | bg3se Docs/API.md | https://github.com/Norbyte/bg3se/blob/main/Docs/API.md | 一手 | WebFetch 成功，2026-09-02 |
| 3 | bg3se Docs/Debugger.md | https://github.com/Norbyte/bg3se/blob/main/Docs/Debugger.md | 一手 | WebFetch 成功，2026-09-02 |
| 4 | bg3se Releases | https://github.com/Norbyte/bg3se/releases | 一手 | WebFetch 成功，2026-09-02 |
| 5 | bg3se Issue #496 "Patch 8 compatible?" | https://github.com/Norbyte/bg3se/issues/496 | 一手（问题追踪） | WebFetch 成功，2026-09-02 |
| 6 | Norbyte/lslib — README | https://github.com/Norbyte/lslib | 一手 | WebFetch 成功，2026-09-02 |
| 7 | lslib Divine/CLI/CommandLineArguments.cs | https://github.com/Norbyte/lslib/blob/master/Divine/CLI/CommandLineArguments.cs | 一手 | WebFetch 成功，2026-09-02 |
| 8 | bg3.wiki Modding:Coding_An_Item | https://bg3.wiki/wiki/Modding:Coding_An_Item | 二手 | WebFetch 成功，2026-09-02 |
| 9 | Larian 官方文档 Functors | https://docs.baldursgate3.game/index.php?title=Functors | 一手 | WebSearch 摘要（WebFetch 403），2026-09-02 |
| 10 | Larian 官方文档 Scripting: Introduction to Osiris | https://docs.baldursgate3.game/Scripting:_Introduction_to_Osiris | 一手 | WebSearch 摘要（WebFetch 403），2026-09-02 |
| 11 | Larian 官方文档 Osiris: Using the Story Editor | https://docs.baldursgate3.game/index.php?title=Osiris%3A_Using_the_Story_Editor | 一手 | WebSearch 摘要，2026-09-02 |
| 12 | Larian 官方文档 Getting Started: Publishing a Mod（mod.io 镜像 publishing-a-mod） | https://docs.baldursgate3.game/Getting_Started:_Publishing_a_Mod ；https://mod.io/g/baldursgate3/r/publishing-a-mod | 一手 | WebSearch 摘要，2026-09-02 |
| 13 | Larian 官方文档 Functors:UseActionResource | https://docs.baldursgate3.game/index.php?title=Functors:UseActionResource | 一手 | WebSearch 仅标题，2026-09-02 |
| 14 | Larian 官方文档 Stats Expressions | https://docs.baldursgate3.game/index.php?title=Stats_Expressions | 一手 | WebSearch 仅标题，2026-09-02 |
| 15 | Larian 官方文档 Adding Classes and Subclasses | https://docs.baldursgate3.game/Adding_Classes_and_Subclasses | 一手 | WebSearch 仅标题，2026-09-02 |
| 16 | mod.io 指南 Restore Your Custom Class Action Resource | https://mod.io/g/baldursgate3/r/restore-your-custom-class-resource | 一手（官方指南区） | WebSearch 摘要，2026-09-02 |
| 17 | mod.io 指南 Adding Khonsu (.khn) condition scripts | https://mod.io/g/baldursgate3/r/adding-khonsu-khn-condition-scripts | 一手（官方指南区） | WebSearch 摘要，2026-09-02 |
| 18 | Nexus-Mods/upload-action | https://github.com/Nexus-Mods/upload-action | 一手 | WebSearch 摘要，2026-09-02 |
| 19 | Nexus 新闻 Upload API Open Beta Now Live! | https://www.nexusmods.com/news/15454 | 一手 | WebSearch 摘要，2026-09-02 |
| 20 | wiki.bg3.community Basic Class Creation | https://wiki.bg3.community/Tutorials/Classes/Basic-Class-Creation | 二手 | WebSearch 摘要，2026-09-02 |
| 21 | wiki.bg3.community Progressions | https://wiki.bg3.community/en/Information/Progression/Progressions | 二手 | WebSearch 摘要，2026-09-02 |
| 22 | wiki.bg3.community Modders guide to git: Working with Repositories | https://wiki.bg3.community/Tutorials/General/modders-guide-to-git/working-with-repositories | 二手 | WebSearch 摘要，2026-09-02 |
| 23 | wiki.bg3.community Creating a meta.lsx file | https://wiki.bg3.community/Tutorials/General/creating_meta | 二手 | WebSearch 摘要，2026-09-02 |
| 24 | wiki.bg3.community Getting Started with Script Extender | https://wiki.bg3.community/en/Tutorials/ScriptExtender/GettingStarted | 二手 | WebSearch 摘要，2026-09-02 |
| 25 | wiki.bg3.community Dear ImGui | https://wiki.bg3.community/Tutorials/ScriptExtender/ImGui-and-You/Dear-ImGui | 二手 | WebSearch 摘要，2026-09-02 |
| 26 | wiki.bg3.community Mod Configuration Menu documentation | https://wiki.bg3.community/Tutorials/Mod-Frameworks/mod-configuration-menu | 二手 | WebSearch 仅标题，2026-09-02 |
| 27 | wiki.bg3.community VSCod(e/ium) Extension (bg3-mod-helper) | https://wiki.bg3.community/Tools/bg3-mod-helper | 二手 | WebSearch 摘要，2026-09-02 |
| 28 | wiki.bg3.community Dev Environment Set-up | https://wiki.bg3.community/Tutorials/General/setting-up-a-dev-environment | 二手 | WebFetch 仅得标题（JS 渲染），2026-09-02 |
| 29 | bg3.wiki Modding:Packaging mods | https://bg3.wiki/wiki/Modding:Packaging_mods | 二手 | WebSearch 摘要，2026-09-02 |
| 30 | bg3.wiki Template:Passive_feature_page/doc（Interrupt 限制说明，归属不完全确定） | https://bg3.wiki/wiki/Template:Passive_feature_page/doc | 二手 | WebSearch 摘要，2026-09-02 |
| 31 | bg3.wiki Modding:Items | https://bg3.wiki/wiki/Modding:Items | 二手 | WebSearch 摘要，2026-09-02 |
| 32 | loregamer/bg3-modding-docs — lslib/cli-guide.md | https://github.com/loregamer/bg3-modding-docs/blob/main/lslib/cli-guide.md | 三手 | WebSearch 摘要，2026-09-02 |
| 33 | fireundubh/divine — README | https://github.com/fireundubh/divine | 二手（Divine 原作者分叉） | WebSearch 摘要，2026-09-02 |
| 34 | Nexus 文章 Enabling the Script Extender Console | https://www.nexusmods.com/baldursgate3/articles/169 | 二手 | WebSearch 摘要，2026-09-02 |
| 35 | Script Extender Console Cheat Sheet | https://bg3se.netlify.app/ | 二手 | WebSearch 摘要，2026-09-02 |
| 36 | Nexus BG3SE Console Commands and Item UUIDs | https://www.nexusmods.com/baldursgate3/mods/3090 | 二手 | WebSearch 摘要，2026-09-02 |
| 37 | Nexus 文章 Guide: How to Debug and Fix Osiris in Baldur's Gate 3 (works in patch 8) | https://www.nexusmods.com/baldursgate3/articles/1463 | 二手 | WebSearch 仅标题，2026-09-02 |
| 38 | Nexus mod Fix for Patch 8 Osiris Scripts Error and Crash | https://www.nexusmods.com/baldursgate3/mods/16664 | 二手 | WebSearch 仅标题，2026-09-02 |
| 39 | Steam 指南 Linux Guide for BG3, Script Extender, Modding Toolkit, WIP | https://steamcommunity.com/sharedfiles/filedetails/?id=3477750360 | 二手 | WebSearch 摘要，2026-09-02 |
| 40 | BG3ModManager Issue #140 UI issue with Crossover | https://github.com/LaughingLeader/BG3ModManager/issues/140 | 二手 | WebSearch 摘要，2026-09-02 |
| 41 | Nexus BG3 Mod Helper – A Visual Studio Code Extension | https://www.nexusmods.com/baldursgate3/mods/6574 | 一手（作者发布页） | WebSearch 摘要，2026-09-02 |
| 42 | VS Marketplace bg3txt-formatter | https://marketplace.visualstudio.com/items?itemName=FierroF.bg3txt-formatter | 一手 | WebSearch 摘要，2026-09-02 |
| 43 | VS Marketplace BG3-SE-Snippets | https://marketplace.visualstudio.com/items?itemName=FallenStar.bg3-se-snippets | 一手 | WebSearch 摘要，2026-09-02 |
| 44 | Shresht7/vscode-bg3-modding | https://github.com/Shresht7/vscode-bg3-modding | 一手 | WebSearch 摘要，2026-09-02 |
| 45 | LaughingLeader/BG3ModdingTools | https://github.com/LaughingLeader/BG3ModdingTools | 一手 | WebSearch 摘要，2026-09-02 |
| 46 | Nexus Mod Configuration Menu (MCM) 讨论区 | https://www.nexusmods.com/baldursgate3/mods/9162?tab=posts | 二手 | WebSearch 摘要，2026-09-02 |
| 47 | bg3se Issue #444（Version vs Version64）；Issue #462（SE interfering with BG3MCM） | https://github.com/Norbyte/bg3se/issues/444 ；https://github.com/Norbyte/bg3se/issues/462 | 一手（问题追踪） | WebSearch 摘要/标题，2026-09-02 |
| 48 | jinghaihan/bg3-mod-collection — Actions | https://github.com/jinghaihan/bg3-mod-collection/actions | 二手 | WebSearch 仅标题，2026-09-02 |
| 49 | tdimino/bg3se-macos（"A replication of the BG3 Script Extender for MacOS"，未核实） | https://github.com/tdimino/bg3se-macos | 二手 | WebSearch 仅标题，2026-09-02 |
| 50 | BG3-Community-Library | https://github.com/BG3-Community-Library-Team/BG3-Community-Library | 一手（库） | WebSearch 摘要，2026-09-02 |
| 51 | Nexus BG3SE 页面讨论区 | https://www.nexusmods.com/baldursgate3/mods/2172?tab=posts | 二手 | WebSearch 摘要，2026-09-02 |
| 52 | LaughingLeader/BG3ModManager | https://github.com/LaughingLeader/BG3ModManager | 一手 | WebSearch 摘要，2026-09-02 |
| 53 | Larian Community Update 27: Official Modding Support | https://baldursgate3.game/news/community-update-27-official-modding-support_118 | 一手 | WebSearch 摘要，2026-09-02 |
| 54 | Padme4000/BG3-Mini-Tool | https://github.com/Padme4000/BG3-Mini-Tool | 一手 | WebSearch 仅标题，2026-09-02 |
| 55 | bg3.wiki Modding:Creating_meta.lsx | https://bg3.wiki/wiki/Modding:Creating_meta.lsx | 二手 | WebSearch 仅标题，2026-09-02 |
| 56 | Larian 官方文档 Osiris: Introduction to Debugging | https://docs.baldursgate3.game/index.php?title=Osiris%3A_Introduction_to_Debugging | 一手 | WebSearch 仅标题，2026-09-02 |
| 57 | Larian 官方文档 Getting Started: Installing the Toolkit | https://docs.baldursgate3.game/index.php?title=Getting_Started%3A_Installing_the_Toolkit | 一手 | WebSearch 仅标题，2026-09-02 |
| 58 | bg3.wiki Modding:Compatibility Framework | https://bg3.wiki/wiki/Modding:Compatibility_Framework | 二手 | WebSearch 仅标题，2026-09-02 |
| 59 | bg3.wiki Modding:Working with LSX files；Modding:LSX files | https://bg3.wiki/wiki/Modding:Working_with_LSX_files ；https://bg3.wiki/wiki/Modding:LSX_files | 二手 | WebSearch 仅标题，2026-09-02 |
| 60 | bg3.wiki Conditions（游戏机制页） | https://bg3.wiki/wiki/Conditions | 二手 | WebSearch 仅标题，2026-09-02 |
| 61 | wiki.bg3.community Tools | https://wiki.bg3.community/Tools | 二手 | WebSearch 仅标题，2026-09-02 |

本机核查（不计入来源）：`git clone --depth 1 https://github.com/Norbyte/lslib.git`（HEAD `6f5f6987`, 2026-03-31）后检查 `Divine/Divine.csproj`、`LSLib/LSLib.csproj`、`LSLibNative/LSLibNative.vcxproj`、`LSLib/Granny/GR2/Reader.cs`、`LSLib/LS/Compression.cs`、`LSLib/LS/Resource.cs`；环境：macOS 26.6.2 arm64，git 2.50.1，Homebrew 可用，`dotnet` 未安装；`python3 -c "print(1<<55)"` → `36028797018963968`。

---

## 6. 审计

| 项目 | 数值 |
|---|---|
| WebSearch 查询数 | 18（预算 18） |
| WebFetch 调用数 | 14（预算 14），成功 8，失败 6 |
| 失败明细 | bg3.wiki `Modding:Boosts` / `Modding:Functors` / `Modding:Conditions` 404 ×3（页面名不存在，改为搜索定位，未重试同名 URL）；`docs.baldursgate3.game` 403 ×2（`Scripting:_Introduction_to_Osiris`、`index.php?title=Functors`，第二次即为对该站的重试）；wiki.bg3.community `setting-up-a-dev-environment` 抓取只返回标题（JS 渲染）×1 |
| 搜索返回链接数 | 154 条（含重复），去重约 110 条 |
| 收到来源数（进入本报告候选） | 约 70 条 |
| 引用来源数 | 61 条（第 5 节），其中 WebFetch 成功直读 8 条、WebSearch 摘要 36 条、仅标题 17 条 |
| 标注 `[背景知识—非本次检索]` 的断言 | 12 处（文件路径、未核实的函数名、InterruptData 字段、Mods 目录路径、LuaLS 用法、Multitool 索引、控制台升级命令、Compatibility Framework 依赖 SE 等） |
| 标注 `[本机核查]` 的断言 | LSLib 工程结构与 Version64 位布局、本机环境 |
| 连续失败停止 | 未触发（无同一目标连续 3 次失败） |
