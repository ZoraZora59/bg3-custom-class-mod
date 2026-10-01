# SkeletonSmokeTest

由仓库模板生成的独立测试骨架，不是东方剑修正式实现。

- Mod UUID：`6611021c-fdfa-4af8-a89a-4ff3201b2a00`
- 游戏中拟显示名称：示例职业；子职业：示例之道。
- `Source/` 保留可编辑 LSX 与本地化 XML。
- `scripts/build-smoke-test.ps1` 把非 meta LSX 转 LSF、XML 转 LOCA，再生成 `build/SkeletonSmokeTest.pak`。
- `scripts/pack-bg3.ps1` 为此次排查用 LSLib API 包装器；包标记调整尚未证明能解决加载问题。

构建需要 PowerShell 7 与 LSLib 1.20.4（默认工具路径 `build/tools/LSLib-1.20.4/Packed/Tools/Divine.exe`）：

```powershell
pwsh -NoProfile -File .\scripts\build-smoke-test.ps1
```

该命令只构建；`-Deploy` 会复制到当前用户的游戏 Mods 目录，不负责启用，部署前请关闭游戏并备份配置。

**状态：手工候选包已生成；游戏识别、角色创建和升级尚未通过验收。** 本轮已移除临时部署并恢复用户原配置。

详细证据、官方来源和下一轮流程见 [官方复核记录](../../research/L-official-skeleton-validation.md)。下一轮先用 Toolkit 建立可验证的基线。
