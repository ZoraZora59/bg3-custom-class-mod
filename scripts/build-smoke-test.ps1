param(
    [string]$Mod = 'SkeletonSmokeTest',
    [string]$Divine = '',
    [switch]$Deploy
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $Divine) {
    $Divine = Join-Path $repoRoot 'build\tools\LSLib-1.20.4\Packed\Tools\Divine.exe'
}
$Divine = (Resolve-Path -LiteralPath $Divine).Path
$sourceRoot = (Resolve-Path -LiteralPath (Join-Path $repoRoot "mods\$Mod\Source")).Path
$buildRoot = Join-Path $repoRoot 'build'
$stageRoot = Join-Path $buildRoot ("staging\$Mod-" + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $stageRoot -Force | Out-Null

# Package a fresh staging copy; source XML and documentation stay out of the PAK.
Get-ChildItem -LiteralPath $sourceRoot -Recurse -File | ForEach-Object {
    $relativePath = $_.FullName.Substring($sourceRoot.Length + 1)
    if ($_.Extension -in @('.md', '.xml')) { return }
    if ($_.Extension -eq '.lsx' -and $_.Name -ne 'meta.lsx') { return }
    $stagePath = Join-Path $stageRoot $relativePath
    New-Item -ItemType Directory -Path (Split-Path -Parent $stagePath) -Force | Out-Null
    Copy-Item -LiteralPath $_.FullName -Destination $stagePath
}
Get-ChildItem -LiteralPath (Join-Path $sourceRoot "Public\$Mod") -Recurse -Filter '*.lsx' | ForEach-Object {
    $relativePath = [IO.Path]::ChangeExtension($_.FullName.Substring($sourceRoot.Length + 1), '.lsf')
    $stagePath = Join-Path $stageRoot $relativePath
    New-Item -ItemType Directory -Path (Split-Path -Parent $stagePath) -Force | Out-Null
    & $Divine -g bg3 -a convert-resource -s $_.FullName -d $stagePath
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $stagePath)) {
        throw "Resource conversion failed: $($_.FullName)"
    }
}
Get-ChildItem -LiteralPath (Join-Path $sourceRoot "Mods\$Mod\Localization") -Recurse -Filter '*.xml' | ForEach-Object {
    $relativePath = [IO.Path]::ChangeExtension($_.FullName.Substring($sourceRoot.Length + 1), '.loca')
    $stagePath = Join-Path $stageRoot $relativePath
    New-Item -ItemType Directory -Path (Split-Path -Parent $stagePath) -Force | Out-Null
    & $Divine -g bg3 -a convert-loca -s $_.FullName -d $stagePath
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $stagePath)) {
        throw "Localization conversion failed: $($_.FullName)"
    }
}
$packagePath = Join-Path $buildRoot "$Mod.pak"
# Divine's CLI leaves the package flags and archive hash at their defaults.
# Use LSLib's API to match the flags of installed BG3 packages.
& pwsh -NoProfile -File (Join-Path $PSScriptRoot 'pack-bg3.ps1') -Source $stageRoot -Output $packagePath -LibraryDirectory (Split-Path -Parent $Divine)
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $packagePath)) {
    throw 'Package creation failed'
}
Get-FileHash -LiteralPath $packagePath -Algorithm SHA256
if ($Deploy) {
    $gameMods = Join-Path $env:LOCALAPPDATA "Larian Studios\Baldur's Gate 3\Mods"
    New-Item -ItemType Directory -Path $gameMods -Force | Out-Null
    Copy-Item -LiteralPath $packagePath -Destination (Join-Path $gameMods "$Mod.pak") -Force
    Write-Output "Deployed: $gameMods\$Mod.pak"
}
