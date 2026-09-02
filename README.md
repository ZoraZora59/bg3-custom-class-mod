# Baldur's Gate 3 自创职业 Mod —— 调研与开发准备

调研日期：2026-09-02。目标：为"把自己幻想中的新职业做成 BG3 mod"准备好知识、环境、模板与工作流。
开发机：Mac（编辑/设计/脚本）+ Windows（官方 Toolkit / Script Extender / 游戏内验证）双机分工。

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
- 仓库已初始化，`.gitignore` / `.gitattributes` 按 docs/05 §4 配置（构建产物、`*.pak`、版权素材目录均不入库）。
- 所有"游戏内行为"类结论均来自文档与社区资料，**尚未在游戏内验证**；docs/07 的 V1–V16 是第一批要在 Windows 上做的验证（V13–V16 来自汉化调研）。
- 研究阶段的抓取限制：Nexus 页面 403 且内置浏览器也被人机验证拦下（只能靠搜索摘要）、mod.io 与社区 wiki 为 JS 渲染；官方文档、mod.io 准则/指南、bg3.wiki、3DM 教程已用内置浏览器直读（research/G、K）。
