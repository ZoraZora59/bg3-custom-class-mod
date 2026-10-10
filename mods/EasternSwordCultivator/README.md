# 东方剑修正式工程

设计依据为 [职业总稿](../../docs/20-eastern-sword-cultivator-gdd.md)、[逐招规格](../../docs/19-skill-specifications-draft.md) 和 [玩家技能说明](../../docs/21-player-facing-skill-text-draft.md)。模块 UUID 为 `6560ea02-fe1e-5fdb-8631-b41a2e53af90`，使用独立命名空间，与 Skeleton 示例工程分离。

当前正在实现和验证完整的 1–12 级设计：太玄、天倾、血魇、行歌四支；职业表、原生 Stats、资源、中文说明及静态图接入 Toolkit 工程，复杂结算使用用户已授权的 Script Extender。尚未完成全部编辑器及正式游戏验收，不能作为已验证发布版。

## 源文件与构建

- `Source/Projects` 保存 Toolkit 项目；`Source/Editor/Mods` 保存真正的 UUID `.tbl` 和 Stats `.stats`，不采用 PAK 导入恢复表的方式。
- `Source/Public` 保存游戏读取的职业、进阶、列表、资源、Stats、图集和纹理库。
- `Source/Mods` 保存模块信息、本地化、UI 图像与 Script Extender 的生产 Lua。
- `implementation-spec.json` 保存稳定 UUID、资源与技能映射以及设计文件 SHA256；它是生成接口，规则以设计稿为准。
- 静态图绑定表对应已选中的 81 张图片；已移除召剑的活动绑定，其原始画稿保留在历史美术清单。连城诀使用已选定的 v2 图。地图人物动作和动态 VFX 不属于这批静态图片。

在仓库根目录使用 PowerShell 7，先生成并验证源码：

```powershell
$env:PYTHONUTF8 = '1'
python scripts/generate-sword-cultivator.py
python scripts/prepare-sword-toolkit.py
python scripts/test-sword-cultivator.py
```

构建脚本 `scripts/build-sword-cultivator.ps1` 再执行原生 StatsParser、LOCA/资源编译、打包和逐文件解包哈希回读。`-SkipArt` 可以复用已生成的 DDS，但仍生成数据与元数据。产物留在被 Git 忽略的 `build/sword-cultivator/`。

## 验证和本地测试

验证顺序为：静态和生产 Lua 模拟契约 → **当前版本 Toolkit** → 正式游戏客户端。旧 Skeleton 的验证不能替代本工程。具体覆盖与未检行为见 [独立验证矩阵](../../research/M-eastern-sword-validation.md)，实际编辑器载入记录见 [Toolkit 运行记录](../../research/N-eastern-sword-toolkit-runs.md)。

编辑器与游戏均正常关闭时，`scripts/sword-toolkit-environment.py install` 安装本工程的确切 UUID 目录，并备份原目录；`capture` 保留不可变文件证据，只采集可证明在本轮安装后产生的日志，并记录陈旧／缺失日志；`restore` 保留编辑器产物并恢复安装前目录。安装时编译原生纹理库和 GUI metadata。

`scripts/sword-test-environment.py deploy` 只允许部署对应包 SHA 的完整 Toolkit 放行版本，且要求先回收 Toolkit 松散源码，防止游戏测试读到另一份数据。它备份本地 Mod 配置，仅临时启用本模块；活动测试环境可用 `refresh` 在新包同SHA门禁通过后仅更新本模块PAK并备份旧包，保持其他配置和PAK不变；`restore` 恢复配置并核对原有 PAK 哈希。既有存档不载入、不改写。若外部操作改变了其他 PAK，只记录差异，不自行补装或覆盖。

## 已作出的实现决策

- 以已确认的 1–12 级设计为本轮交付范围，不把占位升级当作 13–20 级完整实现。
- 开局沿用职业装备表的一把普通长剑，移除一次性的“选择初始配剑”动作；巨剑或双短剑通过正常装备更换。旧档加载时只清理废弃选择技能，不额外赠送武器。
- 移除未完成的召剑技能及天倾、行歌3级授予；御剑攻击后佩剑自动归手，旧剑修角色加载或刷新时清理原有召剑按钮。
- 小图集引用与PAK文件名按大小写一致检查，独立编译纹理资源并保留完整mip链；大Tooltip图与小图分别验证。
- 原生条件提示提供22条独立UUID映射及中英文本，覆盖持剑、气剑模式与癫狂投入条件；源码和Editor表交叉校验，日志只采用本轮新文件。
- 完整机制依赖 Script Extender，不再把脚本部分作为可选功能。使用官方 Norbyte 更新器，保留安装来源和文件哈希。
- 复用本机官方 Toolkit schema 和原版素材入口，使用真正可编辑源表；静态解析、模拟测试和打包成功分别记证据层级。
- 多段、领域、癫狂快照、协同和分担按设计分别计数；保留模拟负契约，防止把全局加值或逐附伤重复奖励当成正常结果。
- 连贯出剑按原版额外攻击的费用替换方式修复：原生 `OnCast` 仅在本职业执行技能的生效费用仍为动作时填入剩余机会，后续将动作费用替换为 `ESC_SwordOpportunity`；Lua 只处理生命周期清理。太玄／天倾／血魇5级每动作3次、10级4次，行歌5级起2次；详见[连贯出剑修复记录](../../research/R-continuous-strikes-20261007.md)。本轮 Toolkit 与客户端流程尚未验证。
- 所有正式客户端测试都在 Toolkit 放行之后；存在引擎断言、崩溃或设计缺口时继续修复，保留目标，暂不宣称完成。

历史冻结包 `6DD25F0A...`：106/106静态／模拟契约通过，Toolkit五项门禁通过，已仅更新安装PAK供用户游戏复测。当时包UI直接覆盖1–3级及四支三级入口；4–12级仅有未变核心成长表的历史UI证据。游戏模组列表封面、客户端小图、SE战斗和存档尚未验收。

2026-10-01 已通过官方Toolkit上传到 [mod.io私有测试页](https://mod.io/g/baldursgate3/m/easternswordcultivator)，模组ID `6417135`，文件ID `8269084`，线上版本1.0.0.2，仅Windows，列表与图库封面已直接核验。正式游戏内封面由用户复测。构建器已持久化PublishHandle，新本地关联包Version64为 `36028797018963971`、SHA256为 `1BD21169D0BFCEBFAAD3927979BE2EB481F57B1ED85C0BF7D9E34C33A00AA117`，111/111检查及包内回读通过；该新版尚未安装或上传，Toolkit与游戏验证均pending，旧6DD门禁不转移到新包。详细过程见[第十七轮记录](../../research/N-eastern-sword-toolkit-runs.md)。

2026-10-07 冻结候选源为 `1.0.0.10`，包含召剑移除、原生连贯出剑修正及天倾落剑接入。六个落剑资源已由 Toolkit 原生编译 DLL 生成并通过二进制回读；天地三段由 Runtime 统一协调，八方逐点选落区，裂天改为 Target 执行并保留旧入口。Toolkit 实际上传版本为 `1.0.0.12`；用户提供的 mod.io 下载包与原生上传包 SHA256 和大小完全一致，正式安装及配置已更新至该版本，安装 SHA256 为 `79925CE0A5D188B8440567B9F5C0EC9B1B77E7CFE61EE3C3079DD3A91614BAF5`。旧包与配置保留备份，其他 Mod／扩展文件及存档清单未变。完整发布、下载和安装证据见 [T](../../research/T-tianqing-release-20261007.md)。FileID、扫描、Windows 平台及网页生效状态未直接核验；实际客户端画面、战斗和存档验收仍待进行。后续构建应以实际发布的 `1.0.0.12` 为版本下限，不直接复用候选源的版本号。
