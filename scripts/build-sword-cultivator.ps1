param([switch]$SkipArt)
$ErrorActionPreference = 'Stop'
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONUTF8 = '1'
$repoRoot = Split-Path -Parent $PSScriptRoot
$sourceRoot = Join-Path $repoRoot 'mods\EasternSwordCultivator\Source'
$buildRoot = Join-Path $repoRoot 'build\sword-cultivator'
$toolRoot = Join-Path $repoRoot 'build\tools\LSLib-1.20.4\Packed\Tools'
$divine = Join-Path $toolRoot 'Divine.exe'
$stageRoot = Join-Path $buildRoot ('stage-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
Push-Location $repoRoot
try {
    $generationArgs = @('scripts/generate-sword-cultivator.py')
    if ($SkipArt) { $generationArgs += '--skip-art' }
    & python @generationArgs
    if ($LASTEXITCODE -ne 0) { throw 'Source generation failed' }
    & python scripts/prepare-sword-toolkit.py
    if ($LASTEXITCODE -ne 0) { throw 'Toolkit editor source preparation failed' }
    & python scripts/check_mod.py $sourceRoot
    if ($LASTEXITCODE -ne 0) { throw 'Source check failed' }
    & python scripts/test-sword-cultivator.py
    if ($LASTEXITCODE -ne 0) { throw 'Regression tests failed' }
    $regressionPath = Join-Path $buildRoot 'regression-report.json'
    if (-not (Test-Path -LiteralPath $regressionPath)) { throw 'Regression test evidence is missing' }
    $regression = Get-Content -LiteralPath $regressionPath -Encoding utf8 -Raw | ConvertFrom-Json
    if (-not $regression.Success -or $regression.Failures -ne 0 -or $regression.Errors -ne 0) { throw 'Regression test report failed' }
    New-Item -ItemType Directory -Force -Path $stageRoot,(Join-Path $stageRoot 'Localization') | Out-Null
    foreach ($part in @('Mods','Public')) {
        Copy-Item -LiteralPath (Join-Path $sourceRoot $part) -Destination $stageRoot -Recurse
    }
    foreach ($verified in $regression.SourceSHA256.PSObject.Properties) {
        $relativeVerified = $verified.Name.Replace('/','\')
        $sourcePrefix = 'mods\EasternSwordCultivator\Source\'
        $verifiedFile = Join-Path $repoRoot $relativeVerified
        if ($relativeVerified.StartsWith($sourcePrefix)) {
            $relativeSource = $relativeVerified.Substring($sourcePrefix.Length)
            if ($relativeSource.StartsWith('Mods\') -or $relativeSource.StartsWith('Public\')) {
                $verifiedFile = Join-Path $stageRoot $relativeSource
            }
        }
        if (-not (Test-Path -LiteralPath $verifiedFile) -or (Get-FileHash -LiteralPath $verifiedFile).Hash.ToLowerInvariant() -ne $verified.Value) {
            throw "Source changed after regression tests: $relativeVerified"
        }
    }
    $spec = Get-Content -LiteralPath (Join-Path $repoRoot 'mods\EasternSwordCultivator\implementation-spec.json') -Encoding utf8 -Raw | ConvertFrom-Json
    $parseLog = Join-Path $stageRoot 'stats-check.txt'
    Push-Location $toolRoot
    try {
        & ./StatParser.exe --mod $spec.folder --game-data-path $stageRoot --package-paths 'E:\SteamLibrary\steamapps\common\Baldurs Gate 3\Data\Shared.pak' --package-paths 'E:\SteamLibrary\steamapps\common\Baldurs Gate 3\Data\Engine.pak' --dependency Shared --dependency SharedDev *> $parseLog
        if ($LASTEXITCODE -ne 0) { throw 'Stats parser failed' }
    } finally { Pop-Location }
    $diagnostics = Get-Content -LiteralPath $parseLog -Encoding utf8 -Raw
    if ($diagnostics -match 'WARN|ERR|Unhandled exception') { throw "Stats diagnostics: $parseLog" }
    $packRoot = Join-Path $stageRoot 'package'
    New-Item -ItemType Directory -Path $packRoot | Out-Null
    foreach ($part in @('Mods','Public')) {
        Get-ChildItem -LiteralPath (Join-Path $stageRoot $part) -Recurse -File | ForEach-Object {
            $relativePath = $_.FullName.Substring($stageRoot.Length + 1)
            if ($_.Extension -eq '.md') { return }
            if ($_.Extension -eq '.lsx' -and
                $relativePath -match '^Public\\[^\\]+\\(MultiEffectInfos|RootTemplates)\\' -and
                (Test-Path -LiteralPath ([IO.Path]::ChangeExtension($_.FullName,'.lsf')))) { return }
            $target = Join-Path $packRoot $relativePath
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
            if ($_.Extension -eq '.xml') {
                if ($relativePath -notmatch '^Mods\\[^\\]+\\Localization\\(.+)\.xml$') {
                    throw "Unexpected XML outside module localization: $relativePath"
                }
                $target = Join-Path $packRoot ('Localization\' + $Matches[1] + '.loca')
                New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
                & $divine -g bg3 -a convert-loca -s $_.FullName -d $target
                if ($LASTEXITCODE -ne 0) { throw "Localization conversion failed: $relativePath" }
            } elseif ($_.Name -in @('_merged.lsx','metadata.lsx') -or
                ($_.Extension -eq '.lsx' -and $relativePath -match '^Public\\[^\\]+\\Content\\')) {
                $target = [IO.Path]::ChangeExtension($target,'.lsf')
                & $divine -g bg3 -a convert-resource -s $_.FullName -d $target
                if ($LASTEXITCODE -ne 0) { throw "Resource conversion failed: $relativePath" }
            } else { Copy-Item -LiteralPath $_.FullName -Destination $target }
        }
    }
    $packagePath = Join-Path $buildRoot 'EasternSwordCultivator.pak'
    & pwsh -NoProfile -File (Join-Path $PSScriptRoot 'pack-bg3.ps1') -Source $packRoot -Output $packagePath -LibraryDirectory $toolRoot
    if ($LASTEXITCODE -ne 0) { throw 'Package creation failed' }
    $extractRoot = Join-Path $stageRoot 'readback'
    & $divine -g bg3 -a extract-package -s $packagePath -d $extractRoot
    if ($LASTEXITCODE -ne 0) { throw 'Package readback failed' }
    $files = @(Get-ChildItem -LiteralPath $packRoot -Recurse -File | ForEach-Object {
        $relativePath = $_.FullName.Substring($packRoot.Length+1)
        $hash = (Get-FileHash -LiteralPath $_.FullName).Hash
        $readbackPath = Join-Path $extractRoot $relativePath
        if (-not (Test-Path -LiteralPath $readbackPath) -or (Get-FileHash -LiteralPath $readbackPath).Hash -ne $hash) {
            throw "Package differs from staging: $relativePath"
        }
        [PSCustomObject]@{Path=$relativePath;SHA256=$hash;Bytes=$_.Length}
    })
    $extraFiles = @(Get-ChildItem -LiteralPath $extractRoot -Recurse -File)
    if ($extraFiles.Count -ne $files.Count) { throw 'Package contains unexpected files' }
    [xml]$packedMeta = Get-Content -LiteralPath (Join-Path $extractRoot "Mods\$($spec.folder)\meta.lsx") -Encoding utf8 -Raw
    $ownMeta = $packedMeta.SelectSingleNode('//node[@id="ModuleInfo"]')
    $dependencyMeta = $packedMeta.SelectSingleNode('//node[@id="Dependencies"]/children/node[@id="ModuleShortDesc"]')
    if ($null -eq $ownMeta -or $null -eq $dependencyMeta) { throw 'Packaged module or dependency metadata is missing' }
    if ($ownMeta.SelectSingleNode('attribute[@id="UUID"]').value -cne $spec.module -or
        $ownMeta.SelectSingleNode('attribute[@id="PublishHandle"]').value -cne [string]$spec.publishHandle -or
        $ownMeta.SelectSingleNode('attribute[@id="Version64"]').value -cne [string]$spec.version64 -or
        $dependencyMeta.SelectSingleNode('attribute[@id="Name"]').value -cne 'GustavX' -or
        $dependencyMeta.SelectSingleNode('attribute[@id="PublishHandle"]').value -cne '0') {
        throw 'Packaged publication identity or dependency handle differs from the generated specification'
    }
    foreach ($language in @('Chinese','English')) {
        $compiled = Join-Path $extractRoot ("Localization\$language\EasternSwordCultivator.loca")
        if (-not (Test-Path -LiteralPath $compiled)) { throw "Packaged localization missing: $language" }
    }
    $coverMaster = Join-Path $repoRoot 'mods\EasternSwordCultivator\thumbnail.png'
    $coverInPak = Join-Path $extractRoot ("Mods\$($spec.folder)\mod_publish_logo.png")
    if (-not (Test-Path -LiteralPath $coverInPak) -or
        (Get-FileHash -LiteralPath $coverInPak).Hash -ne (Get-FileHash -LiteralPath $coverMaster).Hash) {
        throw 'Packaged Mod Manager cover is missing or differs from the selected thumbnail'
    }
    # Compare PAK entry names with ordinal case; NTFS Test-Path hides .DDS/.dds mismatches.
    [xml]$atlasXml = Get-Content -LiteralPath (Join-Path $sourceRoot "Public\$($spec.folder)\GUI\ESC_Icons.lsx") -Encoding utf8 -Raw
    $atlasNode = $atlasXml.SelectSingleNode('//node[@id="TextureAtlasPath"]')
    $atlasId = $atlasNode.SelectSingleNode('attribute[@id="UUID"]').value
    $atlasPath = $atlasNode.SelectSingleNode('attribute[@id="Path"]').value
    $textureEntry = "Public/$($spec.folder)/$atlasPath"
    $resourceEntry = "Public/$($spec.folder)/Content/[PAK]_Generated_$($spec.module)/$atlasId.lsf"
    $packedNames = @($files | ForEach-Object { $_.Path.Replace('\','/') })
    if (-not ($packedNames -ccontains $textureEntry) -or -not ($packedNames -ccontains $resourceEntry)) {
        throw 'Packaged hotbar atlas DDS/resource names differ from the registered paths'
    }
    $bankReadback = Join-Path $stageRoot 'atlas-resource-readback.lsx'
    & $divine -g bg3 -a convert-resource -s (Join-Path $extractRoot $resourceEntry) -d $bankReadback
    if ($LASTEXITCODE -ne 0) { throw 'Packaged atlas resource cannot be decoded' }
    [xml]$bankXml = Get-Content -LiteralPath $bankReadback -Encoding utf8 -Raw
    $bank = $bankXml.SelectSingleNode('//node[@id="Resource"]')
    foreach ($check in @{ID=$atlasId;SourceFile=$textureEntry;Type='1';Width='1024';Height='1024';Depth='1'}.GetEnumerator()) {
        if ($bank.SelectSingleNode("attribute[@id='$($check.Key)']").value -cne $check.Value) {
            throw "Packaged atlas resource field differs: $($check.Key)"
        }
    }
    $report = [PSCustomObject]@{
        Date=(Get-Date -Format o);Stage=$stageRoot;Package=$packagePath;SHA256=(Get-FileHash -LiteralPath $packagePath).Hash
        Bytes=(Get-Item -LiteralPath $packagePath).Length;Files=$files;StaticErrors=0;StaticWarnings=0
        StatsParserDiagnostics=0;RegressionTests=$regression.TestsRun;RegressionSkipped=$regression.Skipped
        PackageReadback='pass';CoverReadback='pass';AtlasReadback='pass';ToolkitTest='pending';GameTest='pending'
    }
    $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $buildRoot 'build-report.json') -Encoding utf8
    $report | Select-Object Date,Package,SHA256,Bytes,StaticErrors,StatsParserDiagnostics,PackageReadback,ToolkitTest,GameTest
} finally { Pop-Location }
