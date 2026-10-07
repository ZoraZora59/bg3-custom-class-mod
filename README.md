# Baldur's Gate 3 自创职业 Mod —— 调研与开发准备

调研日期：2026-09-02。目标：为"把自己幻想中的新职业做成 BG3 mod"准备好知识、环境、模板与工作流。
开发机：Mac（编辑/设计/脚本）+ Windows（官方 Toolkit / Script Extender / 游戏内验证）双机分工。

## 主分支与当前工程

项目统一使用 **`main`**，本地 `main` 跟踪 `origin/main`，GitHub 默认分支也是 `main`。原 `master` 的提交历史已接入 `main`；`master` 仅保留历史引用，后续开发、合并和发布以 `main` 为准。功能分支从 `main` 创建，使用 `codex/` 前缀。

当前正式工程为 [东方剑修](mods/EasternSwordCultivator/README.md)，完整机制依赖 BG3 Script Extender。设计以 [职业总稿](docs/20-eastern-sword-cultivator-gdd.md) 为准；玩家说明、原型特效和御剑速度记录见 [技能说明](docs/21-player-facing-skill-text-draft.md)、[特效接入](docs/22-skill-vfx-and-animation.md)、[原型验证](docs/23-vfx-prototype-validation.md)及[速度调整](docs/24-yujian-projectile-speed.md)。静态检查、Toolkit 验证和正式游戏验收分别记录；本地已安装的职业细节描述修复仍待界面复测。

文档中的 `build/` 日志、截图、安装备份和 PAK 是本地验证证据，由 Git 忽略，远程仓库不包含这些文件。以下“一页结论”保留早期调研内容；当前实现和验证状态以正式工程文档及 [Toolkit 运行记录](research/N-eastern-sword-toolkit-runs.md) 为准。

## 一页结论
1. **官方明确支持自创职业/子职业**：Toolkit（Patch 7 起）有官方逐步教程，mod.io 准则把 "Classes and Subclasses" 列为支持类型。
2. **职业 mod 的主体不需要 Script Extender**：进阶表、被动、法术、资源、反应全部由纯数据（`.lsx` 表 + stats `.txt`）驱动；SE 留给运行时逻辑与 UI，拆成可选模块。这样核心包能上 mod.io/主机、补丁日风险最小。
3. **一个职业 mod 的骨架只有两个文件**：`ClassDescriptions.lsx` + `Progressions.lsx`（通过 TableUUID 关联），加上本地化 xml 与类图标；其余（Lists、Stats、DefaultValues、Equipment）按需。
4. **首个 mod 建议做"全新职业"**：零冲突、可上主机；给原版职业加子职业才需要合并节点 / Compatibility Framework。
5. **工具链现状（2026-09）**：Toolkit（仅 Windows，32 GB 内存/160 GB 磁盘门槛）、LSLib 1.20.4、Multitool 0.10.6、BG3MM 1.0.12.9、BG3SE v32（支持 Patch 8）；ModFixer 不再需要；类图标不再依赖 ImprovedUI；Vortex 不推荐。
6. **最容易踩的坑**：`meta.lsx` 的 Folder/Name/目录名不一致、UUID 复用、Version64 不更新、先填 DisplayName 后建本地化（`s_HandleUnknown`）、两个 mod 管理器混用、子职业整节点覆盖、Patch 8 与 UnlockLevelCurve 的 13 级黑屏。
7. **法务**：完全自创最安全；借用 SRD 机制附 CC-BY-4.0 署名；Artificer / Tasha's 子职业 / Blood Hunter 均不在 SRD；素材许可要留档；mod.io 官方准则页称启用 mod 后成就会被禁用。
8. **团队**：1–2 人即可跑通（头部 mod 多如此）；每个 mod 的必需职能是所有者、设计/平衡、数据实现、兼容性、图标（可用 CC 素材）、测试、社区/文档；脚本、VFX、多语言为可选。工作流按 8 个阶段与 gate 走（docs/06）。

## 文档地图
| 文件 | 内容 |
|---|---|
| [docs/01-modding-landscape.md](docs/01-modding-landscape.md) | 三条开发路线、工具链现状、文件格式、发布渠道与规则、时间线 |
| [docs/02-class-mod-anatomy.md](docs/02-class-mod-anatomy.md) | 职业 mod 数据结构：官方 Toolkit 流程、字段速查、Selectors/Boosts/Functors、本地化、图标、子职业 vs 新职业、MVP 文件树 |
| [docs/03-case-studies.md](docs/03-case-studies.md) | 职业类 mod 案例、基础框架、可学习的开源仓库、中文社区资源、成功做法 |
| [docs/04-pitfalls-and-policy.md](docs/04-pitfalls-and-policy.md) | 踩坑清单（症状→原因→解决）、补丁日 SOP、Larian/mod.io 政策、WotC SRD 授权 |
| [docs/05-dev-environment.md](docs/05-dev-environment.md) | Mac + Windows 双机闭环、安装清单、仓库布局、打包/校验/测试/发布 |
| [docs/06-roles-and-workflow.md](docs/06-roles-and-workflow.md) | 职能矩阵、8 阶段工作流与 gate、团队规模、5e 设计方法论与 BG3 约束 |
| [docs/07-open-questions-and-next-steps.md](docs/07-open-questions-and-next-steps.md) | 待拍板决策 D1–D7、Windows 首周验证清单 V1–V12、信息缺口 |
| [docs/08-localization-plan.md](docs/08-localization-plan.md) | 多语言支持方案：官方 15 种语言目录、社区做法、随包发布 + 机翻初稿 + 社区校对的流程与工具 |
| [docs/09-translating-existing-mods.md](docs/09-translating-existing-mods.md) | 给别人的 mod 做汉化：独立汉化 mod vs 直接改原 mod 的对比、引擎回退/覆盖规则、Mac+Windows 流程、许可与发布、坑清单 |
| [docs/10-eastern-sword-cultivator-design.md](docs/10-eastern-sword-cultivator-design.md) | 2026-09-28 职业设计记录：东方剑修背景；四支定位、持剑／御剑、共同资源、回气主循环、癫狂机制与待讨论细节 |
| [docs/11-signature-techniques-draft.md](docs/11-signature-techniques-draft.md) | 招式记录：启蒙御剑术、分支常态、4／8级两门分支强化、癫狂即时增益与5级连贯／飞行；主要方向已确认，招名与细则待定 |
| [docs/12-survival-and-teamwork-draft.md](docs/12-survival-and-teamwork-draft.md) | 生存与协作草案：四支护身、生命恢复、抗控与解控；无鲜血目标、团队恢复的关键选择与确认记录 |
| [docs/13-attributes-and-equipment-draft.md](docs/13-attributes-and-equipment-draft.md) | 属性与装备记录：统一感知主属性、分支护甲方向、剑型范围、气剑／实体佩剑分工与待讨论细节 |
| [docs/14-level-progression-draft.md](docs/14-level-progression-draft.md) | 成长记录：1—12级主要节点已确认；5级连贯出剑与御剑飞行、4／8级分支强化、6／7／9级常规绝技、10级绝技进阶与前三支四次出手、11级基础深化、12级终极 |
| [docs/15-ultimate-techniques-expansion-draft.md](docs/15-ultimate-techniques-expansion-draft.md) | 绝技扩展记录：太玄／血魇／行歌各四门、天倾五门，共17门；6／7／9级常规、12级终极；四支分工已确认，记录主要效果与待定细则 |
| [docs/16-actions-and-resources-draft.md](docs/16-actions-and-resources-draft.md) | 动作与资源记录：连贯出手、费用与容量；血魇结算、太玄反击／破绽、行歌跟进／合击／呼应、持续剑域，以及广泛抗控／反应保障／受控自救，附计数示例 |
| [docs/18-numerical-framework-draft.md](docs/18-numerical-framework-draft.md) | 数值框架：已确认的逐级剑元容量、费用标准与回气；生命、防护、疗伤等后续初稿分别标明确认状态 |
| [docs/19-skill-specifications-draft.md](docs/19-skill-specifications-draft.md) | 招式规格：已确认4／8级强化与17门绝技的数值、10级进阶；招名与共通结算记录见总稿 |
| [docs/20-eastern-sword-cultivator-gdd.md](docs/20-eastern-sword-cultivator-gdd.md) | 职业设计总稿：当前阅读入口，汇总四支定位、1—12级成长、构筑与共通规则、正式招名及17门绝技，附出招示例与纸面伤害对照 |
| [docs/21-player-facing-skill-text-draft.md](docs/21-player-facing-skill-text-draft.md) | 玩家技能说明草稿：按招名解释用途、费用、伤害与关键效果，方便审阅玩家实际读到的文字 |
| `research/` | 11 份原始研究报告（A–G 职业 mod 调研；H–K 汉化他人 mod 调研），每条结论带来源、抓取方式与审计；`manifest.json` 记录扇出与对账 |
| `templates/` | 职业设计单、测试矩阵、bug 报告模板、`mod-skeleton/`（结构骨架，**未在游戏内验证**） |
| `scripts/` | `gen_ids.py`（UUID/handle 生成与占位替换）、`version64.py`（版本号互转）、`check_mod.py`（静态校验）、`loca_sync.py`（多语言同步/完成度/变更清单）、`loca_convert.py`（纯 Python `.loca`↔`.xml`，未在真实文件验证）、`build.ps1`（Windows 打包示意） |

引用约定：文档中的 `A[15]`、`G[G4]` 指向对应研究报告的来源表。研究报告区分"浏览器/抓取直读"与"仅搜索摘要"，后者需在浏览器人工复核。

## 快速开始
```bash
# 校验骨架（Mac）
python3 scripts/check_mod.py templates/mod-skeleton/Source
# 从骨架起一个新 mod 并替换全部占位 UUID / handle / 名称
cp -R templates/mod-skeleton mods/MyClass
python3 scripts/gen_ids.py --rewrite-placeholders mods/MyClass/Source --rename ExampleClass MyClass
# 版本号
python3 scripts/version64.py encode 1.0.0.0
```
Windows 侧打包与部署见 [docs/05](docs/05-dev-environment.md) §6（`scripts/build.ps1` 为示意，首次运行后请把真实输出记回 docs/07）。

## 当前状态与注意
- 2026-10-01 东方剑修已通过官方 Toolkit 上传至 [mod.io 私有测试页](https://mod.io/g/baldursgate3/m/easternswordcultivator)，列表封面与图库封面均已补齐，线上文件版本为1.0.0.2，仅Windows，完整机制需要Script Extender。后续构建已固化真实发布ID `6417135`；新版关联包111/111静态／模拟检查通过，但新版Toolkit与正式游戏验证仍待完成。已安装冻结6DD包保持不变，正式游戏实测由用户进行。证据边界及上传记录见[Toolkit实际记录](research/N-eastern-sword-toolkit-runs.md)。
- 2026-09-29 用户已授权将确认设计和静态图片完整接入 Mod，并允许安装使用 Script Extender；正式工程为 [EasternSwordCultivator](mods/EasternSwordCultivator/README.md)。当前实现与验收进行中，顺序为源码/脚本验证、当前版本 Toolkit、正式客户端；[验证矩阵](research/M-eastern-sword-validation.md) 与 [Toolkit 实际记录](research/N-eastern-sword-toolkit-runs.md) 区分通过、失败和待检。
- 2026-09-29 “东方剑修”的四支定位、1—12级成长、动作与资源循环、常态／强化及17门绝技数值初稿、10—11级进阶、装备与构筑、正式招名及背景基调已确认，本轮纸面审阅完成；用户决定后续在其他 session 细化。当前阅读入口为 [职业设计总稿](docs/20-eastern-sword-cultivator-gdd.md)，附[玩家技能说明草稿](docs/21-player-facing-skill-text-draft.md)；详细依据见 [数值框架](docs/18-numerical-framework-draft.md) 与 [招式规格](docs/19-skill-specifications-draft.md)。较早设计记录保留讨论过程；MVP 实现及游戏验证由另一个 session 进行。
- 仓库已初始化，`.gitignore` / `.gitattributes` 按 docs/05 §4 配置（构建产物、`*.pak`、版权素材目录均不入库）。
- 所有"游戏内行为"类结论均来自文档与社区资料，**尚未在游戏内验证**；docs/07 的 V1–V16 是第一批要在 Windows 上做的验证（V13–V16 来自汉化调研）。
- 研究阶段的抓取限制：Nexus 页面 403 且内置浏览器也被人机验证拦下（只能靠搜索摘要）、mod.io 与社区 wiki 为 JS 渲染；官方文档、mod.io 准则/指南、bg3.wiki、3DM 教程已用内置浏览器直读（research/G、K）。
