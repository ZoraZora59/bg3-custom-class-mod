# 天倾特效编译与发布审计：2026-10-07

记录时区：Asia/Shanghai。初始审计快照：2026-10-07 16:14；最终候选及修复证据更新至 16:43。用户已要求完成编译、发布更新；本记录冻结操作接口、旧包备份和证据门槛。尚未取得的结果一律为 `pending`，不预写上传、上线、安装或客户端验收成功。此前设计与源审查见 [S](S-tianqing-vfx-redesign-20261007.md)，连续出剑修复证据见 [R](R-continuous-strikes-20261007.md)。

本轮发布 UI 阻塞由主代理报告：Sky `Chrome.get_window_state` 返回无法确定当前浏览器 URL，并要求停止本轮 Computer Use。当前发布状态为 `pending / blocked-by-computer-use-current-url`，本轮停止全部 UI 输入；CLI 编译、回收及包准备可继续，不能把这些工作称为上传完成。目前没有已文档化且已经验证可调用的原生 Publish CLI 替代，不读取或逆向认证储存绕过此限制。

## 1. 身份、版本与发布前备份

| 项目 | 本轮现场依据 |
|---|---|
| 既有 mod.io 项目 | Mod ID / `PublishHandle=6417135`；UUID `6560ea02-fe1e-5fdb-8631-b41a2e53af90`；Folder `EasternSwordCultivator_6560ea02-fe1e-5fdb-8631-b41a2e53af90`；Name `EasternSwordCultivator` |
| 发布前正式安装版本 | `1.0.0.9`，`Version64=36028797018963977`；本轮安装包审查详见 S |
| 新候选版本常量 | [sword_cultivator_spec.py](../scripts/sword_cultivator_spec.py) 已为 `(1 << 55) | 10`，即 `1.0.0.10`、`Version64=36028797018963978` |
| 当前生成状态 | 初始快照的生成产物仍为 9；最终已重新生成并冻结，Source `Mods/.../meta.lsx` 与 `implementation-spec.json` 均为 `1.0.0.10` / `36028797018963978`，`tianqingVfx.enabled=true`；626 个 SourceSHA256 输入当前无漂移 |
| Toolkit 最终版本 | `pending`。历史发布有 Build 自动增加的观察；本轮可能成为 `1.0.0.11`、`Version64=36028797018963979`，但不预先认定。最终版本、ModuleInfo MD5 和 PublishHandle 均从真正发布并下载的 PAK 回读 |
| GustavX 依赖 | 依赖节点 `PublishHandle=0`；不是本 Mod 的发布 ID，不改为 6417135 |

主代理在任何 Toolkit Publish / Publish Local 之前已保存正式安装旧包与所有现有 profile 的配置到 [pre-release](../build/sword-vfx/tianqing-release-20261007/pre-release)。现场现有 profile 只有 `Public`，该目录包含：

- `installed-1.0.0.9.pak`：23,071,258 字节，SHA256 `AB78E073313E93865AC8DDAAF1723FAB83A2521D15112E632D938B33B659E3B5`，本审计已重新计算核对。
- `Public/modsettings.lsx`：SHA256 `218A10CF825A8411C7A461802A93516E4F2992B23CF4A53AFEF304CE54F957B2`，本审计已重新计算核对。
- 发布前的 `sword_cultivator_spec.py`、`implementation-spec.json`、两个效果/职业生成器和 `tianqing_vfx_design.py`，用于追踪本轮变更。

Toolkit 数据环境备份只保护 Data 下本 Mod 的五组目录，不保护上述正式 LocalAppData PAK。Toolkit 发布可能先改写正式 PAK，所以下载包更新脚本的 Prepare 备份不一定仍是 1.0.0.9；真正恢复发布前版本的依据是此独立 pre-release 备份。不得把稍后 Prepare 的 `old_pak` 自动称为旧正式版本。

## 2. 编译、登记与发布接口

| 接口 | 用途与本轮门槛 |
|---|---|
| 原生效果编译 | 六份源已通过本机 `AllSpark.EffectCompiler.Compiler.Compile` 产出原生编译 XML；由 LSLib 1.20.4 Divine 封装为 LSOF v7 `.lsfx`。这是本轮调用原生 DLL 的实现，不声称官方文档已经提供 Publish CLI 或效果编译 CLI |
| 新落剑资源登记 | [tianqing_vfx_resources.py](../scripts/tianqing_vfx_resources.py) 校验 `Public/.../Assets/Effects/Effects_Banks/Sword/Tianqing/native-compile.json`，要求 compiler 标识匹配，当前 `.lsefx` 与 `.lsfx` 哈希均对应 receipt；登记空间播放的 EffectResource，不给逐敌 MEI 复制整招落剑 |
| 新 bank 实际产物 | 万钧、裂天、天剑坠世、八方单柄 GroundColumn、天地单阶段及八方 GroundRing 六份均已有 receipt 和 `.lsfx`；空间八方执行使用单柄 column，避免将八柄 bank 复制八次。源和二进制当前 SHA 全部与 receipt 一致 |
| 本地构建 | [build-sword-cultivator.ps1](../scripts/build-sword-cultivator.ps1) 生成、prepare、静态/回归、原生 Stats parser、封包、解包回读；它不会编译 `.lsefx`。须先取得并登记本轮原生效果产物，旧构建报告不能替代新包证据 |
| 正式发布 | 优先沿用既有官方 Toolkit Project Settings → Authenticate → Publish，更新项目 6417135；完成扫描与 Windows 平台核对后确认该文件是否实际生效及预期可见性 |
| 正式安装 | 沿用“发布后下载 PAK → 核对真实 FileID / 下载来源 → 比较实际上传包 → Prepare → Apply”的路径，不用脚本构建包冒充线上包 |

官方 [VFX Part 1](https://docs.baldursgate3.game/index.php?title=VFX_%E2%80%93_Part_1:_Making_Effects) 记录 AllSpark 的 Build → Compile Effect 流程；[Publishing a Mod](https://docs.baldursgate3.game/index.php?title=Getting_Started:_Publishing_a_Mod) 区分 Publish Local、认证上传、扫描和 Go Live。存在 DLL 或生成了 bank 不证明效果已编译成功或画面正确。

本轮原生编译接口与逐项证据保存在 [tianqing-native-probe-20261007](../build/sword-vfx/tianqing-native-probe-20261007)；游戏 Source 的 [native-compile.json](../mods/EasternSwordCultivator/Source/Public/EasternSwordCultivator_6560ea02-fe1e-5fdb-8631-b41a2e53af90/Assets/Effects/Effects_Banks/Sword/Tianqing/native-compile.json) SHA256 为 `0710BB0E59FAB44103D448CF4F00C924F06243BC5277EB8E8C60326C8878009F`。独立只读审计已逐项重新计算六份 `.lsefx` 和 `.lsfx` SHA，全部匹配 receipt。封装只将顶层 node ID 规范为 region ID，以匹配原生二进制结构；证据分别保存原生编译 XML、封装输入 XML 和二进制回读，记录 typed attribute / region node 的语义往返相等。此证据证明原生编译产物及封装连续性，不证明客户端呈现、锚点和触地效果已经通过。

通用 [mod.io REST 认证](https://docs.mod.io/restapi/introduction) 要求 OAuth2 才能写入；API key 的 GET 权限或浏览器登录不能代替已授权的上传接口。[Add Modfile](https://docs.mod.io/restapi/docs/add-modfile) 提供 ZIP 上传接口，但本轮尚未核实 BG3 项目的 Game ID、可调用写权限及项目特定上传门槛，不搜索或打印 token / credential store。[Manage Platform Status](https://docs.mod.io/restapi/docs/manage-platform-status) 还要求所属游戏团队权限，且平台批准与文件激活分开。当前未发现 mod.io 专用连接器；不得据通用 API 文档绕过 BG3 的扫描、平台或正式发布核对。

上次可复核的成功发布记录是 [modio-upload-20261007/release-result.json](../build/sword-cultivator/modio-upload-20261007/release-result.json)：官方 Toolkit、1.0.0.5、6417135，线上下载 PAK 与原生发布 PAK 字节相同；FileID 未取得、部分线上状态由用户确认。它只支持沿用流程，不证明当前线上版本、可见性或本轮成功。不得复用历史 FileID 8269084，也不使用固定旧 SHA / 旧版本的 `consolidate-modio.ps1`。

## 3. 顺序与执行命令

以下命令的工作目录均为仓库根目录。`pwsh` 已在本机找到；路径/占位值必须替换成这次操作取得的真实证据，命令不是本记录已经执行的声明。

1. 旧正式包与配置备份、六份原生编译和登记/生成已完成。Runtime 空间触发、天地统一三阶段与跨施展首次控制冲突已修复，最终源和候选包已冻结；具体检查结果见第 4 节。
2. 安装 Toolkit 项目目录，进行原生编译及本轮作用范围内的观察。若编译需要先安装 Editor 源，编译后回收 `.lsfx` 与 receipt，再生成登记并重新核对实际装载源的连续性。
3. 捕获本轮不可变快照与新日志，然后正常关闭 Toolkit/BG3，恢复原项目目录。
4. 运行本轮构建检查，取得新包回读、最终源连续性与编译证据；不能沿用 AB78 旧包报告。正式 Publish 所用源必须与本轮验过的源连续一致，若需再次安装则重复环境 install / capture / restore。
5. 官方 Toolkit 更新 6417135，读取真实最终版本、原生发布 PAK、上传成功状态、新 FileID、扫描和 Windows 平台状态。下载该发布文件，核对 ZIP/PAK 哈希和字节，确认其 PAK 与实际上传 PAK 一致；这些结果当前均 `pending`。
6. 关闭 Toolkit、BG3 与 Mod Manager，确认 Toolkit/test 环境均 inactive，使用下载包更新脚本 Prepare / Apply。只更新正式 ESC PAK 和 Public profile 的既有 ESC 元数据行，其余包、SE、保存清单保持脚本的连续性检查。
7. 回读正式安装包与配置，记录真实版本、SHA、关联 ID 与恢复状态。客户端巨剑画面、坡地高度、结算/费用/连续出剑和保存加载验收另列证据，不从发布成功推定。

环境命令无需额外参数：

```powershell
Set-Location -LiteralPath 'C:\Users\Zora\Documents\ChatGPT\博德之门3 mod\bg3-custom-class-mod'
$env:PYTHONUTF8 = '1'
python scripts/sword-toolkit-environment.py install
```

install 要求 BG3 和 Toolkit 已关闭且无 active 环境；它备份并覆盖 Data 下精确 UUID 的 Mods、Public、Projects、Editor/Mods、Generated/Public。它只给安装到 Toolkit 的 meta 描述使用 ASCII 回退；Source 中文描述保留。

```powershell
python scripts/sword-toolkit-environment.py capture
```

capture 可在观察/编译后捕获，输出本次 `capture-...` 路径，保存当前五组目录及本会话新日志；不自动回写 Source，也不把截图/文件快照推定为完整客户端验收。

```powershell
python scripts/sword-toolkit-environment.py restore
```

restore 要求先正常关闭 BG3/Toolkit；校验原目录完整恢复，将测试产物保留在 retired 目录并将 state 设为 inactive。本轮 test-environment 若另外激活，也须走其自身恢复流程，不能手改 state 绕过检查。

正式下载包 Prepare（已取得真实新 FileID 的首选路径）：

```powershell
pwsh -NoProfile -File build/sword-cultivator/update-installed-modio-release.ps1 `
  -Mode Prepare `
  -NewPakPath 'C:\本轮下载解压目录\EasternSwordCultivator_6560ea02-fe1e-5fdb-8631-b41a2e53af90.pak' `
  -ExpectedNewSha256 '本轮下载PAK的64位SHA256' `
  -NewFileId 真实新FileID `
  -PublishedVersion '真实四段版本'
```

下载 PAK 必须保留完整 UUID 文件名，路径不能是已安装 PAK；版本必须严格高于配置中已启用的 ESC Version64。PublishedVersion 采用回读结果，例如实际为 1.0.0.11 就填写 1.0.0.11，不能固定为候选 1.0.0.10。Prepare 自行解包取六个元数据字段，无 `MetaPath` 参数；只写 build，输出新的 `manifest` 路径。正式安装前仍须人工核对本轮线上状态/下载来源；提供 FileID 本身不等于完成扫描或验证原生发布包字节。

若 FileID 未取得，才使用同一 Prepare 的 `-NewFileId 0 -OnlineEvidencePath '本轮online-download-evidence.json'`；证据必须含 Mod6417135、`binary.modcdn.io`、实际 ZIP/PAK 路径/哈希/大小、`native_published_equal=true`，不得用上次证据代替。

```powershell
pwsh -NoProfile -File build/sword-cultivator/update-installed-modio-release.ps1 `
  -Mode Apply `
  -ManifestPath 'C:\本次Prepare输出目录\manifest.json'
```

Apply 只需确切本次 manifest，不能传历史 manifest。它检查文件/备份哈希、安装状态未变、其它 PAK/SE 与保存清单未变、两测试环境 inactive，并在失败时尝试恢复。Toolkit 若已改写当前 PAK，manifest 将忠实备份那一包，不能代替第 1 节旧正式包。若 Toolkit 也改写已启用配置使其版本等于新包，严格升级门槛会拒绝；先核对真实文件与配置状态，不伪造版本规避。

该下载路径不调用 `install-sword-local-build.ps1`；后者用于本地产物，另需实际解包的 `MetaPath`、`ExpectedVersion` 与显式 Toolkit evidence JSON，不能把两个安装流程的参数混用。

## 4. 本轮证据与 remaining

Runtime 使用持久化阶段 checkpoint 与 `ESC_TianqingStage` handler：固定落区和目标集合，play / resolve 在发原生调用之前先提交阶段状态；重复 CastedSpell、marker 和 timer payload 不重复派发，死亡/失败/离开战斗清理后续阶段。八方逐点查询 AI grid 并使用返回的完整 XYZ，失败或超出边界时退回中心平面并记日志；这不是实际地形 raycast 已通过的声明。最终 [Runtime fixture](../scripts/tests/test_tianqing_runtime_vfx.py) 23 项全部通过，包含初版 16 项及控制冲突、异步 helper 和保存恢复检查；它们是生产 Lua 在确定性边界上的模拟，不能代替真实客户端原生伤害、控制或时序验证。

只读审阅发现的 P1 已修复：异步多个天地施展原先共用目标上的 `ESC_TIANDI_FIRSTHIT`，导致施展之间互相干扰；首次 STR 豁免成功也未由 `controlApplied` 记录为已经尝试。最终实现按每次施展 token / 目标保存 `controlAttempted`；控制版 Stage 保留原 STR save，NoControl 版保持相同攻击/伤害/武器效果但不重复 STR save；同一 token / 目标一次只派发一个 pending 原生 helper，后续阶段排队，真正 HitMarker 标记已尝试，Casted / Failed 完成后再派发下一项。修复已通过上述 23 项专用 fixture 及完整回归；生成器 disabled 分支保留原 FIRSTHIT 行为，真实客户端验收仍 pending。

首轮离线候选 PAK SHA256 `5CDD6CDC0FF2A9289A15BED7669A0DCB3391CB6FEC1DB6DA81FFBDFFFC7A0E8E`，23,118,403 字节，已经因上述 P1 修复标为 **superseded**；不能作为最终候选。最终构建使用 `stage-20261007-163905-786`，版本 `1.0.0.10`，冻结 PAK SHA256 `222B0E1306E934A468B42840918F6D972AC42421E5774C33474C2F633ABABB6C`，23,119,546 字节、526 个包文件；本审计已重新计算构建 PAK SHA 核对一致。214 项完整回归全部通过，626 个 SourceSHA256 输入当前无漂移，静态错误 0、StatsParser diagnostics 0、PackageReadback pass；ToolkitTest 与 GameTest 仍 pending。冻结包与 [release-result.json](../build/sword-vfx/tianqing-release-20261007/release-result.json)、`build-report-final.json`、`regression-report-final.json`、`native-compile-final.json` 均保存在 [本轮 release 目录](../build/sword-vfx/tianqing-release-20261007)。

| 层次 | 状态与完成门槛 |
|---|---|
| 旧包/配置独立备份 | 已核对第 1 节两项 SHA；全部现有 profile 为 Public |
| 源版本统一与执行接入 | 候选 10 已统一并冻结，空间与阶段逻辑、控制冲突修复已通过 23 项专用 fixture 和完整回归。合法 Target 裂天子招保留原费用/检定/伤害/控制/武器字段，旧 Projectile 入口保留免费选择容器 |
| 新原生效果编译 | 六份已编译、封装和登记；独立 SHA 复核通过。语义往返证据见第 2 节，实际外观/锚点仍 `pending` |
| 完整回归 / parser / 最终新 PAK | 214 项全部通过，626 个 SourceSHA256 输入无漂移；静态错误 0、StatsParser diagnostics 0、526 文件 PackageReadback pass。最终候选为 222B SHA；首轮 5CDD 已 superseded |
| Toolkit 本轮观察与捕获 | `pending`；新 bank 的垂直朝向、触地、数量、释放锚点与实际载入版本分别留证；捕获日志不能扩大观察范围 |
| Publish / FileID / 扫描 / Windows / 生效 | `pending / blocked-by-computer-use-current-url`；本轮 Computer Use 已要求停止，CLI 准备不能代替上传。解除后采用本轮真实返回和页面状态，不照抄上次成功值 |
| 发布下载与实际上传包相等 | `pending`；记录本轮 ZIP/PAK SHA、大小、FileID、ModuleInfo 六字段及字节比较 |
| 正式下载包 Apply / 环境恢复 | `pending`；正式 PAK 重新计算仍为旧 AB78 SHA / 1.0.0.9，未替换；settings SHA 仍为第 1 节的 218A10。Toolkit 环境 active=false。最终安装须保存本次 manifest、回读新安装 SHA/配置，并检查其它 PAK、SE、保存清单连续性 |
| 客户端视觉与机制 | `pending`；数量/地形/取消/连续施展/多目标、天剑落地与余威、天地三次结算与首次控制、原伤害/费用/出剑机会/保存生命周期。编译和发布都不等同于此层通过 |

后续结果须附实际证据路径、版本和边界后再更新此记录。未经取得的成功、正式可见性或客户端视觉不得预先填写。

## 5. 2026-10-07 17:13 Toolkit 实际上传与恢复

以上 `blocked-by-computer-use-current-url` 是此前回合的历史快照。本轮已重新进入原生 Toolkit 并执行 Publish，Message Log 明确显示 `Mod published successfully`；当前状态为 **uploaded**。实际记录见 [toolkit-upload-result.json](../build/sword-vfx/tianqing-release-20261007/toolkit-upload-result.json)，这不等于线上扫描、平台生效或正式安装已经完成。

原生实际上传版为 `1.0.0.12`，Version64 `36028797018963980`，仍关联既有 PublishHandle `6417135`。上传 PAK 保存在 `build/sword-vfx/tianqing-release-20261007/toolkit-upload/`，SHA256 `79925CE0A5D188B8440567B9F5C0EC9B1B77E7CFE61EE3C3079DD3A91614BAF5`，23,103,868 字节、551 个包文件。它与已验证的原生本地版 11 仅 `Mods/EasternSwordCultivator_6560ea02-fe1e-5fdb-8631-b41a2e53af90/meta.lsx` 不同；8 个 Stats 文件 / 297 条记录、全部 ScriptExtender 文件、6 个天倾 LSFX 与编译 receipt 保持字节相等，6 个效果 UUID / SourceFile 引用及编译哈希核对通过，原生重新序列化的资源库属性语义相同。Source 冻结版本仍为 `1.0.0.10`，214 项回归与 626 个冻结输入连续性证据不变；不得把原生自增版本写回为已重新测试的 Source 版本。

Publish 自动打开 File Manager，新文件出现 Scan 时钟。目前 FileID 尚未取得，扫描结果、Windows 平台、生效状态以及线上下载与上述实际上传 PAK 的字节相等均为 `pending-verification` / `pending`。内置 browser 的 createBrowserTab 30 秒与 getState 20 秒请求超时，open_in_codex 浏览器导航为 queued，因此本轮尚无对应线上核验；不能据上传成功推定这些门槛通过。

Toolkit 已正常关闭，capture 保存在 `build/sword-cultivator/toolkit-environment/capture-20261007-170915-615983`；restore 于 `2026-10-07T17:12:50.62827` 完成，退役目录为 `build/sword-cultivator/toolkit-environment/retired-20261007-171250-283285`，环境 `active=false`。原生 Publish 曾改写正式 PAK，随后已用 pre-release 独立备份准确恢复；本审计重新读取正式 PAK 和 Public settings，SHA256 分别仍为 `AB78E073313E93865AC8DDAAF1723FAB83A2521D15112E632D938B33B659E3B5` 与 `218A10CF825A8411C7A461802A93516E4F2992B23CF4A53AFEF304CE54F957B2`。正式体验仍保留 `1.0.0.9`，等待已核验的 mod.io 下载包后再执行本次 Prepare / Apply。客户端视觉与机制 GameTest 仍 `pending`。

## 6. 2026-10-07 17:21 下载核验与正式安装完成

第 4、5 节保留各时点的历史状态；当前下载校验与正式 Apply 均已完成，正式安装为 **1.0.0.12**。用户提供的 `C:/Users/Zora/Downloads/easternswordcultivator_6560ea0-60ff.zip`，SHA256 `26BFFED3B8D75AE15D1BA9D864CDF73EC7A5F9CC9A4A501EC6A829B73E5DF0C2`，21,987,701 字节；本轮 ADS 来源已核对 `binary.modcdn.io` 与 `/mods/c828/6417135/easternswordcultivator_6560ea0-60ff.zip`，查询参数不记入此记录。解包 PAK 与第 5 节实际 Toolkit 上传 PAK 的 SHA256 / 大小一致，均为 `79925CE0A5D188B8440567B9F5C0EC9B1B77E7CFE61EE3C3079DD3A91614BAF5` / 23,103,868 字节。证据见 [online-download-evidence.json](../build/sword-vfx/tianqing-release-20261007/modio-download/online-download-evidence.json)，本审计已重新计算 ZIP、下载 PAK 与正式 PAK 的哈希和大小核对。

首次 Prepare 因 XmlWriter 默认将 LF 改为 CRLF，触发 ESC metadata 节点之外 XML 不变校验而拒绝，正式文件未写。主代理显式设置 `NewLineHandling=None` 保留换行，并以 `-cne` 保留大小写敏感的一致性校验后重试成功；未放宽仅更新 ESC 六个 metadata 字段的范围。成功 [manifest.json](../build/sword-cultivator/modio-local-update-20261007-172112-517080/manifest.json) 状态为 `applied`，时间 `2026-10-07T17:21:47.9922791+08:00`；安装 Version64 为 `36028797018963980`，正式 Public settings SHA256 为 `43EA9AE48B57E5D57C96DBF73133AFAA30F18FB4F6CA0870BB8681C4DF0E95A5`，已独立回读一致。manifest 内保留旧正式版 9 PAK / 配置的准确备份，SHA 分别为第 1 节 AB78 与 218A10；15 个其它 PAK / SE 文件及 236 个保存文件清单未变，Toolkit / test 两环境均 `active=false`。

FileID 未取得，manifest `file_id=null`，其依据是已核验下载来源、上传包字节相等与包内真实 ModuleInfo，不填造编号。线上扫描结果、Windows 平台状态、File Manager activation 仍未通过浏览器核验；下载存在不代替这些页面状态。正式包已安装也不代表客户端视觉或机制通过，GameTest 本轮未运行，仍 `pending`。
