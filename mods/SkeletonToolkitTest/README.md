# Toolkit 职业骨架验证工程

这是独立的技术验证工程，不是正式东方剑修实现。

- Steam Toolkit 创建的工程：`SkeletonToolkitTest`。
- 模块 UUID：`1226413d-5cb8-f80e-10bc-2fe4417c83a1`。
- 工程目录：`SkeletonToolkitTest_1226413d-5cb8-f80e-10bc-2fe4417c83a1`。
- `Source` 保留 Projects、Editor、Mods、Public 四部分；Editor 下的 `.tbl` 是可编辑源表，不应直接替代游戏资源打包。
- 来源：本仓库 `SkeletonSmokeTest`，字段类型对照本机官方 Shared 表；由 `scripts/prepare-toolkit-test.py` 准备。
- 主职业 12 个等级节点，子职业 3、6、10 级节点，以及多职业 1 级节点。当前 Editor、Public 和新版本地包均包含 16 行进阶。
- 示例效果：1 级移动倍率 125%，2 级近战命中附加 1d4 力场伤害。文本与图标为技术占位。

## 重建源文件

先在 Toolkit 创建独立工程，再关闭编辑器。运行：

```powershell
python scripts/prepare-toolkit-test.py --data 'E:\SteamLibrary\steamapps\common\Baldurs Gate 3\Data' --folder SkeletonToolkitTest_1226413d-5cb8-f80e-10bc-2fe4417c83a1
```

脚本只写入上述指定测试工程并在本仓库保存副本。运行会重新生成测试源表，不能用于已有正式职业工程。

如需官方快速测试教程的 Add Class 入口，增加 `--include-multiclass`，然后在 Toolkit 重新打开并导出 Progressions。该字段来自本机官方 `SharedDev/Progressions/Progressions.tbl`，不是 ClassDescriptions。

## 验收状态

已完成 Toolkit 安装、配置游戏 Data 路径、新建工程、首次载入 `Basic_Level_A`、准备并重载职业源文件、四张 UUID 表导出和 Publish Local。

正式游戏 v4.1.1.7398727 的 Mod 管理器已列出并成功启用 `SkeletonToolkitTest`，配置文件也写入该模块 UUID。首包 12,980 字节，SHA256 `57B570869CFC6404CE691CD8164BD547D49C7C1BD1F7510AE740E5FCEF8E74BB`。

2026-09-29 的新版 Publish Local 包为 13,173 字节，Version64 `36028797018963971`，SHA256 `D917201F2B5FC6302741E670786338DC90371709A232642661831EF56C4593C5`。解包回读确认 16 个进阶节点，其中 1 个多职业节点。

| 验收项目 | 结果 |
|---|---|
| Toolkit Basic_Level_A 添加职业 | 通过；滚动到职业列表底部可见 ExampleClass |
| 示例职业 1→2→3 级 | 通过；测试角色为 Wyll，保留邪术师 1 级，再取得示例职业 3 级 |
| 3 级子职业 | 通过；选择 ExamplePath 并确认升级后返回测试场景 |
| 静态数据检查 | 0 个错误，0 个警告 |
| 正式客户端新建角色 | 通过；选择示例职业，完成属性加值、两项技能熟练和守护者步骤，进入鹦鹉螺场景 |
| 正式客户端升级 | 未验证 |
| 图标、伤害效果、完整 12 级成长 | 未验收；职业图标当前缺失 |

Toolkit 内首次只看到原版职业不能视为本职业不存在：未导出资源、缓存旧表和列表尚未滚到底部均影响观察。最终重启并载入 16 行资源后确认添加和升级成功。

正式客户端复测时，将临时 modsettings 中测试模块的旧 Version64 `36028797018963969` 更新为当前包的 `36028797018963971`，随后重启。恢复界面操作时已经显示并选中“示例职业”；继续完成敏捷 +2、感知 +1、运动/体操两项熟练选择，并创建高精灵角色。进入鹦鹉螺后生命值为 12/12，快捷栏显示“示例职业”分类。包版本、重启及现场短暂手动操作没有被分别隔离，不能据此认定版本号是此前未显示的唯一原因。

本次没有在正式客户端获取足够经验并升级；1→2→3 级和子职业的通过结论仍限定于 Toolkit 多职业测试。

测试结束后已正常退出客户端，逐字节恢复原 modsettings（SHA256 `4621819A07E594C035EBDB3FB91E4FC7C23138AADEA200776CD7EEC860AD8F2F`）；原 14 个用户 PAK 保留，测试 PAK 已移出游戏 Mods。此次新建角色的 AutoSave_0 移到忽略目录 `build/toolkit-test/retired-20260929/` 留作验证备份，没有载入或改写既有存档。Toolkit 工程及可重建源文件保留。

升级验证后一次 Publish Local 在 PackCurrentMod / PackedFile 阶段发生访问异常并退出，旧包未改变。关闭正式客户端，重新打开工程且不加载关卡后再次发布成功。这是可复现记录，不足以认定游戏文件占用是唯一根因。

空工程首次加载已有缺失 DiceSet 元数据、AI_IGNORE Boost 解析和部分 Tag/模板等警告；后续诊断需要区分基线警告与本工程新增错误。
