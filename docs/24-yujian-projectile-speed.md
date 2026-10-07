# 御剑术弹道提速

记录日期：2026-10-07。用户反馈基础御剑术弹道偏慢，本轮将其恒定飞行速度由 **20 m/s 调至 30 m/s**。主手和副手共用 Common Root 配置，本次 Toolkit 实测只覆盖主手；三派与行歌使用各自独立 Root。

依据 [Larian 官方 Projectiles 指南](https://docs.baldursgate3.game/Projectiles)：Constant 为全程恒速，单位 m/s。30 是本轮调优值，官方没有推荐速度；同路径的理论飞行时间减少约三分之一，尚未测量完整施展动作时长。

| 字段 | 原值 | 新值 |
|---|---:|---:|
| `Speed` | 20 | 30 |
| `InitialSpeed` | 20 | 30 |
| `VelocityMode` | 0 | 0 |

实际恒速由 `Speed` 控制；`InitialSpeed` 同步保留字段一致性。贝塞尔轨迹、动作事件、粒子时间线、伤害、射程与费用保持原值。Pathfind 子模板继续继承 Common Root，实际障碍回退行为未在本轮验证。

版本为 **1.0.0.7**。最小更新包由上一版本正式 PAK 回读构建，仅替换以下三个既有包路径，文件总数仍为 519：

- Common 主 Projectile Root 的编译 LSF。
- 模组 `meta.lsx` 的版本。
- `ScriptExtender/Lua/GeneratedSpec.json` 的版本。

[最小更新包](../build/sword-vfx/speed-tuning-20261007-095250-062160/EasternSwordCultivator-speed.pak) SHA256：`439B8828579CDEC8E12D6B00F329933BD0E664CF37EC923A9EA4EAA75D1F6CAB`。制作备份及[519 文件清单](../build/sword-vfx/speed-tuning-20261007-095250-062160/minimal-staging.json)保留在同一目录。

整体生成候选 `D1094396…` 有 520 个路径，还包含另一项成长说明注册，其 130 项检查结果不用于证明这个最小包；本轮实际安装的是上述 519 个路径的 `439B8828…` 包。

[独立最小包审计](../build/sword-vfx/speed-tuning-20261007-095250-062160/independent-minimal-speed-review.json)已通过：519 个同名文件中严格只有上述三个路径变化，其余 516 个与 v6 原包字节一致；Common Root 解码只有两个速度字段变化，两份元数据只有版本变化。staging、回读、清单及独立解包一致。该结果属于静态检查，不代替运行测试。

Toolkit Game Mode 已以影心卸盾、主手装备长剑，创建狼目标，在近距离启用保证命中进行复测。御剑术主手 `Projectile_ESC_yujian_Main` 实际对狼造成 4 点斩击伤害，目标生命由 11 降至 7，见[主手命中截图](../build/sword-vfx/speed-tuning-20261007-095250-062160/toolkit-ui/main-yujian-hit.png)。[独立施展日志报告](../build/sword-vfx/speed-tuning-20261007-095250-062160/independent-toolkit-speed-probe.json)确认动作 `1`：UsingSpell 行 68608 → OnTarget 行 68625 → CastSpell 行 68632 → 命中标记行 68716 → AttackedBy 行 68815（Slashing 4）→ CastedSpell 行 68967，未记录对应 `CastSpellFailed`。测试 Common Root 与最小包中的 Root 字节一致，速度配置为 30；[显式 Toolkit 安装证据](../build/sword-vfx/speed-tuning-20261007-095250-062160/explicit-toolkit-install-evidence.json)保留这一资源连续性与测试边界。

本次未测量飞行时长、完整施展时长或 FPS，也未确认所选实际路径是贝塞尔还是 Pathfind；不能把命中记录当作速度体感或性能的量化验收。副手只确认共用 Root 与绑定连续性，没有实际施放；障碍回退、自然命中率、正式客户端战斗与其他技能没有本轮复测记录。截图中的原生 TemplateId／Tag／layout／focus 警告保留，不作全视觉、无告警或性能通过结论。

本次原生控制台调试经验：单独授予 `Projectile_ESC_yujian_Main` 未出现可用栏位；使用 `addDebugSpell Projectile_ESC_yujian` 授予父容器后，能从容器选择主手并完成上述施放。这是本次 Toolkit 操作观察，不作为新技能机制或通用控制台规则。

测试结束已完成[关闭后捕获](../build/sword-cultivator/toolkit-environment/capture-20261007-101535-433332/capture.json)，Toolkit 关闭并恢复原环境，[环境状态](../build/sword-cultivator/toolkit-environment/state.json)为 `active=false`，恢复时间为 `10:16:04`，退役目录为 `retired-20261007-101603-846964`。

当前[本地安装清单](../build/sword-cultivator/local-build-update-20261007-101605-799766/manifest.json)已为 `applied`，应用时间 `10:19:07`，版本 `1.0.0.7`、安装 SHA 为上述 `439B8828…`。Apply 返回 `other_files_unchanged=true` 与 `save_inventory_unchanged=true`：13 个其他 PAK、2 个 SE 文件与 226 项存档路径／大小／修改时间清单保持不变；这是文件保留核查，不表示另外 13 个 Mod 已启用，也不是存档内容逐字节比较。原包与设置备份已保留。本轮未启动正式客户端进行新的战斗或技能测试，本地安装成功不扩大 Toolkit 单次主手施放的验收范围。

[安装后独立复核](../build/sword-vfx/speed-tuning-20261007-095250-062160/post-install-audit.json)的 14 项检查通过：正式 PAK 为 `439B8828…`，启用设置中仅 ESC 版本由 v6 改为 v7；其他文件、存档清单、备份与恢复状态均符合本轮安装记录。
