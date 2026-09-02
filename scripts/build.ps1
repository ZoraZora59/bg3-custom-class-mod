# 示意脚本（尚未在 Windows 上运行）：Mac 上 git push 后，在 Windows 侧执行。
# 参数名来自 LSLib Divine/CLI/CommandLineArguments.cs（research/E-scripting-infra.md §2.4.5）。
param(
  [string]$Mod = "ExampleClass",
  [string]$Source = ".\mods\$Mod\Source",
  [string]$Divine = "C:\Tools\ExportTool\Divine.exe",
  [string]$GameMods = "$env:LOCALAPPDATA\Larian Studios\Baldur's Gate 3\Mods"   # 社区惯例路径，请核对
)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path ".\build" | Out-Null

# 1) 本地化 xml -> loca（每个语言目录）
Get-ChildItem "$Source\Mods\$Mod\Localization" -Directory | ForEach-Object {
  Get-ChildItem $_.FullName -Filter *.xml | ForEach-Object {
    $loca = [System.IO.Path]::ChangeExtension($_.FullName, ".loca")
    & $Divine -g bg3 -a convert-loca -s $_.FullName -d $loca
  }
}
# 2) 打包
& $Divine -g bg3 -a create-package -s $Source -d ".\build\$Mod.pak"
# 3) 部署
Copy-Item ".\build\$Mod.pak" $GameMods -Force
Write-Host "Deployed .\build\$Mod.pak -> $GameMods"
