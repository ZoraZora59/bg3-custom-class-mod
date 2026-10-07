# 剑修技能运行修复：2026-10-07

本批已实际应用源码并生成 **1.0.0.8 候选**：补齐三档护体的原生护甲状态、收敛状态到期后的脚本减伤残留、修正反击范围和条件，清理回风保护残留，并修正一线天的力场免疫判定。尚未完成游戏或 Toolkit 运行验收；候选未安装。

## 工作基线与并发保护

- 项目：`C:\Users\Zora\Documents\ChatGPT\博德之门3 mod\bg3-custom-class-mod`。
- 最初定位为 master 且有大量既有未提交改动；本批应用前另一个会话已提交并切换到 main，基线提交 `08c62a9b64b046f3803a86e320efc792e657ae32`。当前分支 `main`。未切换分支、重置、提交、推送或合并。
- 先保存61项源码/设计输入、旧构建报告和一个约23MB旧Mod包，再以SHA256核对8项直接修改。61项中只有安装脚本发生LF/CRLF转换，文本完全一致，已保留；所有修复输入完全匹配。CAS清单见本次工作区 `project-evidence/applied-source-manifest.json`。
- 依据仓库及父目录AGENTS、docs/19–24和只读本地项目记忆索引。docs/20第207行的施展者回合期限保留。未扫描无关私人目录，未修改记忆。

## 已实施的行为

| 技能/路径 | 改动 | 已有证据与边界 |
|---|---|---|
| 剑气护体 / 清辉返照 / 星河倒悬 | 原生ApplyStatus建立护体，分别AC＋2/3/5；原生同系取强，弱招不刷新强招；2轮状态与档位同步 | 不再只靠CastedSpell后的隐藏空标记；静态、模拟和原生parser通过，真实状态时序待测 |
| 护体减伤 | SE从实际Ready及rank读20%/30%/40%；移除、重载、装备暂停后不复活过期护体；Runtime不再重复加AC | 原生护甲可独立存在；减伤仍依赖BG3SE，本轮未验证真实HP提交顺序 |
| 护体刷新 | Ready移除回调不删除刚施加的新rank，覆盖前后两种通知顺序均有对抗回归 | 引擎真实同名覆盖通知顺序仍待运行观察 |
| 护体反击 | helper距离30m→18m；原生interrupt明确Ready、受击者本人、装备和距离条件，排除反击递归，保留可选/免费规则 | 条件解析与模拟通过，真实反击UI、命中与伤害待测 |
| 行歌·回风 | 原生施加保护AC＋2；原生状态移除及时清理对应来源减伤，旧来源回调不删除新来源；减伤仍在施展者第2个后续回合到期 | 原生AC与目标回合时钟的边界尚未统一验收，不能称完整caster-duration修复 |
| 太玄·一线天 | Engine读取v32 userdata的ImmuneToMagical，免疫目标不占衰减顺位且伤害为0 | 严格字段/类型代理反例：旧近101、免疫101、远25；候选近101、免疫0、远50。真实HP提交时序待测 |
| 护体可见表现 | Ready绑定已编译原生胸部循环护光MEI `87356553-5bed-4e2b-86eb-f0697e5ec648` | 只绑定StatusEffect；没有继承原技能AC/专注。有限绕身剑弧、来袭局部偏转尚未实现；未观察游戏画面 |

## 改动文件

直接实现：`scripts/generate-sword-cultivator.py`、`scripts/sword_cultivator_spec.py`（candidate版本7→8）、`scripts/sword_player_text.json`、模块Lua的`Runtime.lua`与`Engine.lua`。

测试：`scripts/tests/esc_engine_fixture.lua`、`test_esc_bridge.py`，新增`test_esc_guard_lifecycle.py`。新增15项护体/回风生命周期与3项免疫契约测试，共18项；其他测试随原生护体施加路径调整fixture。

原构建链已重生成原生Stats、Editor .stats镜像、双语玩家文本、版本meta、implementation-spec和Toolkit source report。完整路径/哈希清单见工作区verification-manifest；差异补丁基于上述main提交。原有职业详情注册和Common御剑速度30保留。21项VFX LSF因名称表序列化导致二进制SHA变化；42次精确解码对照证明21/21规范化XML语义相同（保留node/children顺序，版本/类型/值未忽略）。10/10已编译LSFX字节与SHA完全一致，未改变模型/材质编译内容。详情见工作区vfx-serialization-audit.json。

## 验证与产物

- 命令：`pwsh -NoProfile -File scripts/build-sword-cultivator.ps1 -SkipArt`，2026-10-07 02:53:15–02:53:54 UTC，退出0。
- **148/148测试通过，0失败、0错误、0跳过**，源码在测试期间未变化。层级为static-and-simulated-lua，fixture不能证明真实引擎事件时序。
- 静态错误/警告：0/0；StatParser诊断：0。双语LOCA、原生资源转换及PAK构建通过。
- **520文件**逐项路径及SHA256回读一致；封面、图集大小写/资源注册、UUID、依赖、PublishHandle均通过。
- 候选包：`C:\Users\Zora\Documents\Codex\2026-10-07\task\project-evidence\EasternSwordCultivator-1.0.0.8-815c1042.pak`，23,042,281字节，SHA256 `815c104253158485febe3b712b5e888398d55b25a67847748d4052a3207cc41c`。
- 构建通常输出：`C:\Users\Zora\Documents\ChatGPT\博德之门3 mod\bg3-custom-class-mod\build\sword-cultivator\EasternSwordCultivator.pak`；该路径可能被后续构建替换，交接优先使用上面的冻结副本与哈希。
- 构建报告、回归报告、完整CLI日志、空Stats诊断文件、CAS清单和验证manifest均在本次工作区 `project-evidence/`。
- 当前正式安装包SHA256仍为 `1a7e9c69980a8da8ce37e1109684e38f6870292e31efdde9f2f923da9235adba`（1.0.0.7），与本批前记录一致。本批没有改游戏包、modsettings、存档或SE设置，没有发布远程资源。

## 运行验收阻塞与剩余差距

当前工具没有可调用node_repl/sky原生窗口控制入口，统一CUA明确禁用native computer API。只读进程检查没有BG3/Glasses/AllSpark运行，SE调试端口9998没有监听。不能从该会话创建测试角色、实机施展、拍摄或操作AllSpark；没有用终端自制UI工具绕过限制。

因此 `ToolkitTest=pending`、`GameTest=pending`。旧1.0.0.6原型/1.0.0.7单次命中截图均不能作为本轮1.0.0.8护体或视觉验收，本轮没有新游戏截图。现有的SE live-probe及G01–G12运行清单可在游戏测试环境已打开后继续使用。

如未来恢复测试，需记录：三档AC与收到100点伤害的实际变化；弱招/同名刷新；2轮和脱战12秒到期；盾牌及分支中重甲暂停/恢复；18m边界与反击拒绝/接受；保存读取；失去职业及倒地/死亡；回风施展者与受保护者错开行动顺序；一线天免疫目标位于最前且命中通知远先近后的实际HP变化。每项附当前包SHA、状态/事件日志和画面。本轮按用户最新要求停止这些运行探索。

其他明确视觉差距仍为：护体有限绕身剑弧/来袭偏转、一线天30m完整长锋、天倾3–5倍人高巨剑与八向展开、血魇最终红雾的远程轨迹与消散。现有10项Projectile/Impact资产并不覆盖这些全部动作。设计描述明确，当前缺的是原生制作与运行工具，不需追加笼统视觉问题。

用户已明确要求停止扩展，仅收尾本地提交。护体剑弧调查只留下本次工作区 `guard-vfx-prototype/inspect_guard_vfx.py`、`inspect_ribbon.py`、`inspect_modules.py` 三个检查脚本，未生成LSEFX/LSFX/MEI新原型。这些半成品保留在工作区，不纳入生产仓库提交；没有删除任何已存在文件。

## 弹窗调查

用户曾看到未保留的错误弹窗；按要求暂停后，在用户授权继续后恢复。独立VFX候选检查的前两次StatParser遇到未处理.NET异常（缺Localization，随后缺模块meta）；第三次正确stage后通过。前两次最值得怀疑，但未观察弹窗，无法确认来源。之后本批完整构建已预检模块/基础包并由原build创建Localization，StatParser退出0、输出为空；没有重复失败调用。Application日志未找到匹配1000/1001/1026记录，这不证明弹窗不存在。
