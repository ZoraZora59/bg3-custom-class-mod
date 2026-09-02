# 07 · 未解决问题、待做决策与下一步验证清单

## 1. 需要你拍板的决策（阶段 0 之前）

| # | 决策 | 选项与影响 | 建议 |
|---|---|---|---|
| D1 | **全新职业 vs 原版职业的子职业** | 全新职业：工作量大、零冲突、可上主机；子职业：工作量小、需合并节点/CF、非 1 级解锁 + 多职业有已知 bug | 首个 mod 做**全新职业**（你的目标就是"幻想里的新职业"）；子职业包作为后续扩展 |
| D2 | **是否依赖 Script Extender** | 依赖：仅 Windows/Linux、无主机、无 Mac 原生、补丁日失效期、只能 Nexus；不依赖：可 mod.io + 主机 + 跨平台联机 | 核心包**纯数据**；需要 SE 的功能拆成可选模块 |
| D3 | **目标平台与渠道** | PC only（Nexus）/ PC + 主机（mod.io，需过审、无 NSFW、不含 .dll/新种族） | 双轨发布，核心包按 mod.io 规则设计 |
| D4 | **是否支持 13–20 级** | 支持：多 8 级设计与测试；不支持：页面声明不兼容 UnlockLevelCurve | v1 只做 12 级并声明；v2 视反馈补 |
| D5 | **许可证** | MIT（社区主流）/ 其它；素材许可清单 | 代码与数据 MIT；素材单独列许可 |
| D6 | **语言** | 用户已明确：mod 要支持各种语言 | 英 + 简 + 繁人工维护；其余 12 种官方语言随包发布（`loca_sync.py` 生成占位 → 机翻初稿 → 社区校对），"无裸 handle" 作为发布门槛（见 docs/08） |
| D7 | **团队与分工** | 1–2 人 vs 4–6 人（见 06 文档） | 先按最小团队跑通一个纵切片，再扩人 |

## 2. Windows 侧首周验证清单（把"未确认"变成事实）

| # | 验证项 | 为什么 | 记录到 |
|---|---|---|---|
| V1 | Windows 机硬件是否达 Toolkit 门槛（32 GB 内存 / 8 GB 显存 / 160 GB 磁盘）；Toolkit + BG3 Toolkit Data DLC 安装并能加载 `WLD_Crashsite_D` | 决定走 Toolkit 主线还是纯文本主线 | 05 文档 §2 |
| V2 | 按官方 Battlemage 教程做一遍职业，Game Mode 内 `Ctrl+Shift+L` 能选到并升级 | 打通官方回路，核对本文所有字段 | 02 文档 |
| V3 | 用 `templates/mod-skeleton/` + Multitool 或 Divine 打包，游戏内管理器能识别、角色创建能看到职业 | 验证"纯文本 + 打包"路线与 `check_mod.py` 的假设 | README |
| V4 | `PrimaryAbility`/`SpellCastingAbility` 枚举、`LearningStrategy`、`ProgressionType` 种族值、Lists 分隔符、`AbilityDistributionPresets` 目录名 —— 用 Toolkit 下拉与解包的 Shared.pak 核对 | 研究报告中的 6 处来源分歧 | 02 文档 §3 |
| V5 | 类图标：300×300 + hotbar 尺寸（112×112 待证）经 Convert UI Assets 后在 CC/热键栏显示 | 官方只给 300×300 | 02 文档 §5 |
| V6 | 本地化：`Chinese`/`ChineseTraditional` 目录 + 自定义 handle 格式在游戏内显示正常；语言缺失时的回退行为（2026-09-02 汉化调研：引擎有回退池，缺失时回退英文或显示 "Not Found"，不会显示裸 handle——高置信推断，见 docs/09 §2，由 V14 封口） | 中文交付 | 02 文档 §4、09 文档 |
| V7 | Divine 在 Mac（.NET 8）上的 `create-package` / `convert-loca` 是否可用 | 决定 Mac 能否独立出 pak | 05 文档 §3 |
| V8 | `modsettings.lsx`、Mods 目录、SE 日志与崩溃日志的真实路径 | 05 文档中的路径来自社区/背景知识 | 05 文档 §6/§8 |
| V9 | mod.io：网页能否直传 `.pak`；审核时长；"Third Party" 标签行为；成就是否真被禁用 | 发布策略 | 01 文档 §4 |
| V10 | 自定义 Action Resource 不用 ImpUI 时的面板/图标表现（评论两说） | 决定是否允许自定义资源 | 02 文档 §3.7 |
| V11 | Patch 8 之后各 hotfix 对 SE / Toolkit 的影响；当前游戏版本号 | 时间线 | 01 文档 §5 |
| V12 | Withers 重置、职业 Tag 与对话、多职业法术位在自定义职业上的实际行为 | D 报告 C7–C10 均为背景知识 | 04 文档 §3 |
| V13 | `scripts/loca_convert.py` 转出的 `.loca` 与 LSLib 输出字节一致、游戏能读；`.loca`→xml 能无损还原 | Mac 独立做汉化文本层的前提 | 09 文档 §3 |
| V14 | 只带 `English` 目录的 mod 在简中客户端显示英文还是 "Not Found" | 决定"汉化是否必需"与 V6 的最终答案 | 09 文档 §2 |
| V15 | 汉化 pak 排在原 mod 之后能否逐条覆盖其自带的 `Chinese` 目录；排在之前是否被覆盖 | 加载顺序规则的一手证据 | 09 文档 §2 |
| V16 | `maclarian` / `bg3-forge` 在 Mac 上解/打包的 pak 能否被游戏加载 | 若可行，Mac 可独立跑完整条汉化流水线 | 09 文档 §5 |

## 3. 研究阶段遗留的信息缺口（按报告）
- **H/I/J/K（汉化他人 mod，2026-09-02）**：Nexus 全站（含文章 643、mod 7288、各 CHS 条目正文）只有搜索摘要；英文-only mod 的实际回退行为无一手明文；跨 pak 时加载顺序与 loca 文件名字母序谁优先未核实；mod.io 网页直传第三方 pak 是否开放、主机上是否已有过审的中文翻译 mod 未核实；Mac 原生工具（maclarian/bg3-forge）未实测。
- **A（工具链）**：官方 Toolkit 文档已由 G 补齐；仍缺 Toolkit 在 Linux/Proton 的可用性、Vortex 2026 现状、Patch 8 后原版 pak 新命名。
- **B（结构）**：`ProgressionDescriptions` 的 `ExactMatch`/`PassivePrototype` 未见于任何来源；`ActionResourceDefinitions.DiceType` 未见；`ReplenishType` 完整枚举未知；`MergedInto` 合并机制细节；两部视频教程未评估。
- **C（案例）**：Nexus 页面 403 导致推荐数/依赖/Credits 多为"页面未显示"；Artificer 之外的头部职业 mod 无源码；中文 QQ 群号未核实。
- **D（踩坑）**：Larian 支持页与 Modding Terms PDF 原文未读到（只有摘要）；框架 mod 加载顺序一手规则；PAK 路径大小写在 Linux 的表现；SRD 5.2.1 收录的具体子职业名单。
- **E（脚本/基建）**：Boosts/Conditions 完整签名（官方站无此页，已用 AllPages 核查）；InterruptData 字段语义；SE 对各 hotfix 的逐个兼容；IMGUI 中文字形；可核实的 BG3 mod CI 示例仓库；lsx schema。
- **F（团队）**：任何作者的开发耗时均未公开；Crowdin/Weblate 无案例；"Down by the River" Discord 与 modding 的关系未确认。

## 4. 建议的下一步（按顺序）
1. 拍板 D1–D7（尤其 D1/D2/D3）。
2. Windows 侧完成 V1–V3（一到两个晚上），把结果写回 docs。
3. 用 `templates/class-design-doc.md` 写第一个职业的设计单，走完阶段 0–3 的 gate。
4. 在 `mods/<ModName>/Source` 起项目（可从 `templates/mod-skeleton/` 复制并用 `scripts/gen_ids.py` 换掉全部占位 UUID/handle），做 1–5 级纵切片。
5. 跑 `templates/test-matrix.md`，通过后再扩到 12 级、子职业、图标、中文。
