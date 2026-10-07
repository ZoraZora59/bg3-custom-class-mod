# 东方剑修：首批特效与动作原型验证

记录日期：2026-10-07（Asia/Shanghai）。首批 10 项飞行／命中原型、原生编译、局部 Toolkit 施展、最终包静态核查、本地安装与客户端主菜单／启用检查已完成；完整实时视觉、战斗、性能与职业 SE 行为尚未验收。完整设计见[技能特效与动作设计](22-skill-vfx-and-animation.md)。

## 制作范围

44 个命名技能共享 Common、Taixuan、Tianqing、Xueyan、Xingge 各两项 Projectile／Impact，共 10 项资产。它们复用原生模型、材质、粒子与轨迹组件进行重组和调参；本轮没有制作 44 套逐招原创特效。Prepare／Cast 与人物动作沿用配对 textkey 的完整原生 Animation 组，未制作新的 GR2；分支原创准备、释放、持续效果和复杂逐招构形仍待制作。

| 分支 | 设计优化方向 | 本轮实装原型 | 后续视觉验收 |
|---|---|---|---|
| 太玄 | 细长轴线、精准贯刺，出手短促、剑尖稳定 | 细长飞剑与窄尾迹；局部方向性贯刺 Impact | 轴向、剑尖、逐段命中；一线天全距离长锋尚未绑定 Beam |
| 天倾 | 硕大巨剑、承重收势与宏大冲击 | 原生巨剑模型、厚尾迹；扩大斩击并叠加冲击波 | 飞行体量与朝向、落剑重量、目标和真实范围可读性 |
| 血魇 | 红雾拖尾、锐剑撕雾，命中扩散后回卷 | 飞剑叠加原生红烟，独立两层血雾 Impact；飞行粒子尺度倍率 `0.40`、初始数 `4,4`、寿命 `1.5—2 秒`、发射 `6/s`、总时长 `2.3 秒` | 移动中的雾尾密度、刃口轮廓、末尾散尽及连击遮挡 |

行歌已具备较轻的青绿飞剑与成对护弧命中原型，本轮未取得其代表技能运行验收记录。三派的优化动作仍需在现有 Animation 组、主副手和不同 rig 上继续校准。

以下是 **AllSpark 预览**，不代表实时飞行或性能通过。

| 天倾巨剑 | 血魇红雾 |
|---|---|
| ![天倾巨剑 AllSpark 预览](../build/sword-vfx/toolkit-ui-20261007/04-tianqing-giant-sword-preview.jpg) | ![血魇红雾 AllSpark 预览](../build/sword-vfx/toolkit-ui-20261007/08-xueyan-blood-mist-preview.jpg) |

## 编译与版本证据

Toolkit 原生 Compile All 日志记录 `Compiled 10 effects` 和 `Effect banks reloaded`，见[编译截图 09](../build/sword-vfx/toolkit-ui-20261007/09-final-ten-effects-compiled.jpg)与[原生日志截图 10](../build/sword-vfx/toolkit-ui-20261007/10-final-native-compile-log.jpg)。最新血魇修订已重新编译。

10 项 `.lsfx` 已从 Toolkit 捕获至 Source：[捕获记录](../build/sword-cultivator/toolkit-environment/capture-20261007-044035-006009/capture.json)、[编译文件 SHA256 清单](../build/sword-vfx/final-compiled-capture.json)，已只读确认 Source 与清单 **10/10 一致**。第四轮结束后另有[捕获记录](../build/sword-cultivator/toolkit-environment/capture-20261007-050126-756935/capture.json)，40 项 Public 资产和 10 项 Editor 源与测试前冻结记录全部 SHA 一致；Toolkit 原环境于 `05:01:43` 精确恢复，[状态记录](../build/sword-cultivator/toolkit-environment/state.json)为 `active=false`。

| 最终包项目 | 核查结果 |
|---|---|
| PAK | `EasternSwordCultivator.pak`，版本 `1.0.0.6`，`23,040,142 字节` |
| SHA256 | `9B5DB5AA0DDE9B437EF008C1DD21BF171E8C02BE9176B55DD8FEAE5BED59D029` |
| 回读 | `stage-20261007-044113-780`，519 个文件与最终包清单零差异 |
| 检查 | 129 项回归检查通过；40 项 VFX 内容核查一致：10 个编译文件、10 个 Root、10 个 MEI、10 项 Effect 登记 |
| 血雾 bank | 最终 Duration `2.3 秒`；第四轮 live、Source 与 PAK 解码内容一致 |
| 本地正式安装 | Apply 已返回 `applied`，版本与上述 PAK SHA 一致；完成 PAK／启用元数据更新，未完成客户端完整验收 |
| 客户端启动与启用 | DX11 已到主菜单，`v4.1.1.7631656`，SE `v32` 已加载；东方剑修启用绿勾在同会话返回菜单、重入 Installed 后保持 |

依据为[独立最终包核查](../build/sword-vfx/final-review-20261007-044700/independent-final-package-review.json)。编译 `.lsfx` 使用精确字节／SHA 比较，Root／MEI／Effect bank 使用解码内容比较；序列化 SHA 不同不等于语义不一致。静态回读与检查通过也不等于客户端运行或视觉通过。

[本地安装清单](../build/sword-cultivator/local-build-update-20261007-044336-437904/manifest.json)为 `applied`，应用时间 `05:04:12`；工具返回 `other_files_unchanged=true`、`save_inventory_unchanged=true`、`publication=none`。本次更新 PAK 与启用元数据，其他文件和存档清单未变，未发布。另有[最终独立补记](../build/sword-vfx/final-review-20261007-044700/independent-final-review-addendum.json)及[安装用 Toolkit 证据包](../build/sword-vfx/final-review-20261007-044700/explicit-toolkit-install-evidence.json)记录静态与运行边界；本地安装成功不等于已在客户端完成特效、战斗与 SE 测试。

[客户端主菜单截图 22](../build/sword-vfx/toolkit-ui-20261007/22-client-installed-main-menu.jpg)记录 DX11 启动与 SE 本体加载。按 Larian [Installed 页勾选框启用指南](https://baldursgate3.game/news/community-update-29-playing-with-mods_124)仅切换东方剑修一次，[截图 24](../build/sword-vfx/toolkit-ui-20261007/24-client-mod-enabled.jpg)显示绿勾；返回主菜单再进入 Installed，[截图 25](../build/sword-vfx/toolkit-ui-20261007/25-client-enable-persisted.jpg)仍保持，其余可见项未勾选，未再次切换。该结果仅确认同会话启用保持，未验证重启后保持、客户端存档加载、战斗、升级、特效或职业 Lua 回调。

[退出后的独立核查](../build/sword-vfx/independent-post-client-audit-20261007-051335-277934/evidence.json)确认安装 PAK SHA 与最终包一致，客户端原生格式设置的规范化内容与准备文件一致、版本为 `1.0.0.6`；13 个其他 PAK 与 2 个 SE 文件 SHA 未变，220 项存档路径／大小／修改时间清单未变，4 份安装备份／准备副本完整。客户端已正常退出，核查时无 BG3／Glasses／AllSpark 进程；本轮未读取存档内容来作逐字节比较。

当前设置经客户端重新序列化，SHA 已不同于安装工具记录的旧／新值；`StrictRollback` 会拒绝当前状态，尚未执行回滚。原备份完整，后续回滚需复核设置，不能称为已验证的一键回滚。

## Toolkit 实际施展

Common 御剑主手已对狼命中 8 点伤害，[截图 07](../build/sword-vfx/toolkit-ui-20261007/07-yujian-cast-hit.jpg)与[独立日志记录](../build/sword-vfx/independent-toolkit-log-20261007-035949-862236/evidence.json)留存。三派代表子项的[独立报告](../build/sword-vfx/independent-three-style-probe-20261007-042758-251158/evidence.json)与[原始测试及追加暴击对照](../build/sword-vfx/independent-three-style-probe-20261007-042758-251158/requested-probes-and-message-evidence.json)记录如下：

| 子项 | StoryActionID | 实际伤害分量 | 结论 |
|---|---|---|---|
| 照隙 `Projectile_ESC_taixuan_zhaoxi_RangedMain` | `6` | 物理斩击 4＋力场 8 | 施展、命中、结束链完整，无对应 `CastSpellFailed` |
| 裂天一剑 `Projectile_ESC_tianqing_lietian_Main` | `8` | 物理斩击 9＋力场 115，暴击 | 同上 |
| 掠血 `Projectile_ESC_xueyan_luexue_RangedMain` | `10` | 物理斩击 7＋坏死 8 | 原始代表测试链完整，无对应施展失败 |
| 掠血，同一子项的远距强制暴击对照 | `12` | 物理斩击 10＋坏死 15 | 追加对照链完整，无对应施展失败 |

日志建立了对应动作的 `UsingSpell` → `UsingSpellOnTarget` → `CastSpell` → 命中标记／`AttackedBy` → `CastedSpell` 链。它证明这些子项可实际施展并产生伤害；不证明数值平衡、飞剑逐帧外观、性能、所有主副手和全部 44 招通过，也不证明 Toolkit 未加载的 SE 回调执行。

**第四轮血魇复测只确认近身成功。** [不可变第四轮证据](../build/sword-vfx/independent-fourth-blood-probe-20261007-050237-883665/evidence.json)与[真实截图 21](../build/sword-vfx/toolkit-ui-20261007/21-final-blood-retest.jpg)记录：

| 实际子项 | StoryActionID | 第四轮结果 |
|---|---|---|
| `Target_ESC_xueyan_luexue_MeleeMain` | `5` | 斩击 4＋坏死 6；UsingSpell 行 70723 → OnTarget 行 70745 → CastSpell 行 70756 → 命中标记行 70777 → AttackedBy 行 70876／71028 → CastedSpell 行 71185；对应近身链附近无施展失败 |
| `Projectile_ESC_xueyan_luexue_RangedMain` | `0` | 行 68144 为 `CastSpellFailed`；不计入成功记录 |

第三轮御剑成功记录对应此前血雾 bank Duration `1.2 秒`。第四轮资源配置与最终包一致、Duration 为 `2.3 秒`，但实际成功子项是近身；它不证明最终远程轨迹、烟雾寿命与消散的运行行为。两个会话的结果不能合并成“最终远程复测成功”。

## 告警与原生对照

自定义技能暴击测试有 RadialBlur 告警。原生 `Projectile_Dipped_Poison` 的固定 `roll 20` 双伤害暴击对照同样复现：动作 `22` 命中穿刺 15＋毒素 12，施放后出现 RadialBlur（含 `x126` 计数）与 `VfxGameObj null`，见[截图 20](../build/sword-vfx/toolkit-ui-20261007/20-native-poison-dual-damage-roll20.jpg)及[独立原生对照报告](../build/sword-vfx/independent-native-controls-20261007-044122-665153/evidence.json)。操作记录为施放前清零 Message Log，清零画面未单独留存。原生 Eldritch Blast 与主手暴击的已观察画面没有 RadialBlur；Eldritch Blast 有 `VfxGameObj null`。

本轮没有修改原生 CriticalHit 资源或技能机制。该对照在同一已加载本 Mod 的 Toolkit 环境进行，并非纯净无 Mod 客户端基线。原生双伤害技能也复现，不能据此宣称最终归因已解决，更不能称为无告警或性能通过；已有原生／操作系统警告亦未据此排除。

第四轮截图 21 仍出现声音事件加载失败及多条写入失败消息，未完成归因或修复；保留为运行告警，不作“原生音频与特效均无错误”的结论。

## 尚未验收

实时飞剑朝向、轨迹、尾迹、Impact、结束散尽及取消清理尚缺逐帧视觉验收；最终血雾 Duration `2.3 秒` 的远程子项在第四轮失败，成功近身子项不能代替它。连续出剑、多人同屏与领域叠加尚缺性能验收。多段、领域、反击、行歌合击、44 招逐项与客户端 SE 生命周期没有本轮通过记录。最终包已构建、完成静态核查并本地安装，客户端主菜单及同会话启用保持已确认；重启后保持、完整视觉、战斗与 SE 行为仍待验证。
