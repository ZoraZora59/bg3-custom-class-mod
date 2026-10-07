[CmdletBinding()]
param(
    [ValidateSet('Prepare', 'Apply', 'Rollback')][string]$Mode = 'Prepare',
    [string]$NewPakPath,
    [string]$MetaPath,
    [string]$ExpectedNewSha256,
    [string]$ExpectedVersion,
    [string]$ManifestPath,
    [string]$ExplicitToolkitEvidencePath
)

# Local installation only. Default Prepare writes solely to this repository's
# build directory. Apply and Rollback require explicit modes; there is no upload
# or publication operation. MD5 is ModuleInfo metadata, never a PAK checksum.
# Apply evidence JSON: schema=1, package_sha256, checked_asset_scope (array),
# source_continuity (array of {path, sha256}), boundary (actual scope/limitations).
# The helper verifies continuity and records the stated scope; it does not infer
# a full skill suite pass or replace the human's Toolkit observations.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$taskRepo = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskBuild = Join-Path $taskRepo 'build\sword-cultivator'
$taskLocal = Join-Path $env:LOCALAPPDATA "Larian Studios\Baldur's Gate 3"
$taskBin = 'E:\SteamLibrary\steamapps\common\Baldurs Gate 3\bin'
$taskUuid = '6560ea02-fe1e-5fdb-8631-b41a2e53af90'
$taskFolder = "EasternSwordCultivator_$taskUuid"
$taskPak = Join-Path $taskLocal "Mods\$taskFolder.pak"
$taskSettings = Join-Path $taskLocal 'PlayerProfiles\Public\modsettings.lsx'
$taskDivine = Join-Path $taskRepo 'build\tools\LSLib-1.20.4\Packed\Tools\Divine.exe'
$taskFields = @('Folder', 'MD5', 'Name', 'PublishHandle', 'UUID', 'Version64')

function Get-TaskSha([string]$Path) {
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Read-TaskXml([string]$Path) {
    $doc = [System.Xml.XmlDocument]::new()
    $doc.PreserveWhitespace = $true
    $doc.XmlResolver = $null
    $doc.Load($Path)
    return ,$doc
}
function Get-TaskEscRow([System.Xml.XmlDocument]$Document) {
    $rows = $Document.SelectNodes("//node[@id='ModuleShortDesc'][attribute[@id='UUID' and @value='$taskUuid']]")
    if ($rows.Count -ne 1) { throw 'Expected exactly one enabled ESC row; no load-order reconstruction is allowed.' }
    return ,$rows[0]
}
function Get-TaskAttrs([System.Xml.XmlElement]$Node) {
    $values = [ordered]@{}
    foreach ($field in $taskFields) {
        $matches = $Node.SelectNodes("attribute[@id='$field']")
        if ($matches.Count -ne 1) { throw "Missing or duplicated module metadata field: $field" }
        $values[$field] = $matches[0].GetAttribute('value')
    }
    $values
}
function Get-TaskModuleInfo([string]$Path) {
    $doc = Read-TaskXml $Path
    $rows = $doc.SelectNodes("//node[@id='ModuleInfo']")
    if ($rows.Count -ne 1) { throw "Expected exactly one ModuleInfo: $Path" }
    Get-TaskAttrs $rows[0]
}
function Get-TaskPackedVersion([string]$Value) {
    $packed = [long]0
    if ($Value -notmatch '^\d+$' -or -not [long]::TryParse($Value, [ref]$packed) -or $packed -le 0) {
        throw 'Version64 must be a positive signed Int64 decimal value.'
    }
    $packed
}
function Get-TaskVersion([long]$Packed) {
    # LSLib PackedVersion.FromInt64, LSLib/LS/Resource.cs.
    '{0}.{1}.{2}.{3}' -f (($Packed -shr 55) -band 0x7f), (($Packed -shr 47) -band 0xff), (($Packed -shr 31) -band 0xffff), ($Packed -band 0x7fffffff)
}
function Assert-TaskIdentity($Metadata) {
    if ($Metadata.UUID -ne $taskUuid -or $Metadata.Folder -ne $taskFolder -or $Metadata.Name -ne 'EasternSwordCultivator') {
        throw 'Module UUID, Folder or Name differs from EasternSwordCultivator.'
    }
    [void](Get-TaskPackedVersion ([string]$Metadata.Version64))
    $publish = [ulong]0
    if ([string]$Metadata.PublishHandle -notmatch '^\d+$' -or -not [ulong]::TryParse([string]$Metadata.PublishHandle, [ref]$publish)) {
        throw 'ModuleInfo PublishHandle must be a valid unsigned decimal value.'
    }
}
function Save-TaskJson($Data, [string]$Path) {
    $stage = $Path + '.' + [guid]::NewGuid().ToString('N') + '.tmp'
    try {
        [System.IO.File]::WriteAllText($stage, (($Data | ConvertTo-Json -Depth 20) + [Environment]::NewLine), [System.Text.UTF8Encoding]::new($false))
        [void](Get-Content -LiteralPath $stage -Raw -Encoding utf8 | ConvertFrom-Json)
        if (Test-Path -LiteralPath $Path) { [System.IO.File]::Replace($stage, $Path, ($Path + '.previous.json')) }
        else { [System.IO.File]::Move($stage, $Path) }
    } finally {
        if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage }
    }
}
function Assert-TaskInside([string]$Path, [string]$Root) {
    $full = [System.IO.Path]::GetFullPath($Path)
    $prefix = [System.IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    if (-not $full.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) { throw "Path is outside prepared workspace: $full" }
}
function Assert-TaskNoDuplicate {
    $extras = @(Get-ChildItem -LiteralPath (Join-Path $taskLocal 'Mods') -File -Filter '*.pak' |
        Where-Object { $_.FullName -ne $taskPak -and ($_.Name -match 'EasternSwordCultivator|6560ea02-fe1e-5fdb-8631-b41a2e53af90') })
    if ($extras.Count -gt 0) { throw 'Another ESC package exists. Resolve the duplicate before installing.' }
}
function Assert-TaskReady {
    if (@(Get-Process bg3,bg3_dx11,Glasses,BG3ModManager -ErrorAction SilentlyContinue).Count -gt 0) {
        throw 'Close BG3, Toolkit and the mod manager before changing installed files.'
    }
    foreach ($stateName in @('toolkit-environment', 'test-environment')) {
        $statePath = Join-Path $taskBuild "$stateName\state.json"
        if ((Test-Path -LiteralPath $statePath) -and (Get-Content -LiteralPath $statePath -Raw -Encoding utf8 | ConvertFrom-Json).active) {
            throw "Restore $stateName before changing the installed package."
        }
    }
    Assert-TaskNoDuplicate
}
function Get-TaskOtherFiles {
    $records = @(Get-ChildItem -LiteralPath (Join-Path $taskLocal 'Mods') -File -Filter '*.pak' |
        Where-Object { $_.FullName -ne $taskPak } | ForEach-Object {
            [ordered]@{ path = $_.FullName; kind = 'other-pak'; exists = $true; sha256 = Get-TaskSha $_.FullName }
        })
    foreach ($leaf in @('DWrite.dll', 'ScriptExtenderSettings.json')) {
        $path = Join-Path $taskBin $leaf
        $exists = Test-Path -LiteralPath $path -PathType Leaf
        $records += [ordered]@{ path = $path; kind = 'script-extender'; exists = $exists; sha256 = $(if ($exists) { Get-TaskSha $path } else { $null }) }
    }
    @($records | Sort-Object { $_.path })
}
function Get-TaskSaves {
    # Inventory only: this is not a byte-for-byte backup or hash of save contents.
    @(Get-ChildItem -LiteralPath (Join-Path $taskLocal 'PlayerProfiles\Public\Savegames') -Recurse -File -ErrorAction SilentlyContinue |
        Sort-Object FullName | ForEach-Object { [ordered]@{ path = $_.FullName; bytes = $_.Length; modified_ticks = $_.LastWriteTimeUtc.Ticks } })
}
function Assert-TaskUntouched($Snapshot) {
    if ((ConvertTo-Json -InputObject @(Get-TaskOtherFiles) -Depth 5 -Compress) -ne (ConvertTo-Json -InputObject @($Snapshot.other_files) -Depth 5 -Compress)) {
        throw 'Other installed PAK/SE files changed; the recorded snapshot is stale.'
    }
    if ((ConvertTo-Json -InputObject @(Get-TaskSaves) -Depth 5 -Compress) -ne (ConvertTo-Json -InputObject @($Snapshot.saves) -Depth 5 -Compress)) {
        throw 'Save inventory changed; the recorded snapshot is stale.'
    }
}
function Read-TaskToolkitEvidence([string]$Path, [string]$PackageSha) {
    if ([string]::IsNullOrWhiteSpace($Path)) { throw 'Apply requires ExplicitToolkitEvidencePath for this exact package and checked asset scope.' }
    $evidencePath = (Resolve-Path -LiteralPath $Path).Path
    $evidenceSha = Get-TaskSha $evidencePath
    $evidence = Get-Content -LiteralPath $evidencePath -Raw -Encoding utf8 | ConvertFrom-Json
    foreach ($field in @('schema', 'package_sha256', 'checked_asset_scope', 'source_continuity', 'boundary')) {
        if ($evidence.PSObject.Properties.Name -notcontains $field) { throw "Toolkit evidence is missing $field." }
    }
    if ($evidence.schema -ne 1 -or [string]$evidence.package_sha256 -notmatch '^[a-fA-F0-9]{64}$' -or
        ([string]$evidence.package_sha256).ToLowerInvariant() -ne $PackageSha -or
        $evidence.checked_asset_scope -isnot [array] -or @($evidence.checked_asset_scope).Count -eq 0 -or
        $evidence.source_continuity -isnot [array] -or @($evidence.source_continuity).Count -eq 0 -or
        [string]::IsNullOrWhiteSpace([string]$evidence.boundary)) {
        throw 'Toolkit evidence must identify this PAK SHA256, a nonempty asset scope, source continuity records and actual limitations.'
    }
    foreach ($scope in $evidence.checked_asset_scope) {
        if ($null -eq $scope -or [string]::IsNullOrWhiteSpace([string]$scope)) { throw 'Toolkit checked_asset_scope contains an empty item.' }
    }
    $verified = @()
    foreach ($item in $evidence.source_continuity) {
        if ($item.PSObject.Properties.Name -notcontains 'path' -or $item.PSObject.Properties.Name -notcontains 'sha256' -or
            [string]$item.sha256 -notmatch '^[a-fA-F0-9]{64}$') { throw 'Each source_continuity item requires path and SHA256.' }
        $filePath = (Resolve-Path -LiteralPath ([string]$item.path)).Path
        if (-not (Test-Path -LiteralPath $filePath -PathType Leaf) -or (Get-TaskSha $filePath) -ne ([string]$item.sha256).ToLowerInvariant()) {
            throw "Toolkit source continuity failed: $filePath"
        }
        $verified += [ordered]@{ path = $filePath; sha256 = ([string]$item.sha256).ToLowerInvariant() }
    }
    if ((Get-TaskSha $evidencePath) -ne $evidenceSha) { throw 'Toolkit evidence changed while being read.' }
    [ordered]@{ path = $evidencePath; sha256 = $evidenceSha; checked_asset_scope = @($evidence.checked_asset_scope); verified_source_files = $verified; boundary = [string]$evidence.boundary; content = $evidence }
}
function Assert-TaskEvidenceUnchanged($Evidence) {
    if ((Get-TaskSha $Evidence.path) -ne $Evidence.sha256) { throw 'Toolkit evidence changed during installation.' }
    foreach ($file in $Evidence.verified_source_files) {
        if ((Get-TaskSha $file.path) -ne $file.sha256) { throw "Toolkit source changed during installation: $($file.path)" }
    }
}
function Replace-TaskFile([string]$Source, [string]$Target, [string]$ExpectedTargetSha, [string]$ExpectedSourceSha) {
    if ((Get-TaskSha $Target) -ne $ExpectedTargetSha) { throw "Target changed before replacement: $Target" }
    if ((Get-TaskSha $Source) -ne $ExpectedSourceSha) { throw "Prepared source changed: $Source" }
    $stage = $Target + '.esc-update-' + [guid]::NewGuid().ToString('N') + '.tmp'
    $replaceBackup = $Target + '.esc-replaced-' + [guid]::NewGuid().ToString('N') + '.tmp'
    try {
        Copy-Item -LiteralPath $Source -Destination $stage
        if ((Get-TaskSha $stage) -ne $ExpectedSourceSha -or (Get-TaskSha $Target) -ne $ExpectedTargetSha) { throw 'Stage copy or pre-replacement verification failed.' }
        # Same-directory stage meets File.Replace's same-volume requirement.
        # https://learn.microsoft.com/en-us/dotnet/api/system.io.file.replace
        # Use an explicit backup path: PowerShell converts a null string to ''.
        [System.IO.File]::Replace($stage, $Target, $replaceBackup)
    } finally {
        if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage }
        if (Test-Path -LiteralPath $replaceBackup) { Remove-Item -LiteralPath $replaceBackup }
    }
    if ((Get-TaskSha $Target) -ne $ExpectedSourceSha) { throw "Replacement hash verification failed: $Target" }
}
function Restore-TaskPair($Prepared) {
    $entries = @(
        @{ target = $taskPak; backup = $Prepared.old_pak_path; old = $Prepared.old_pak_sha256; new = $Prepared.new_pak_sha256 },
        @{ target = $taskSettings; backup = $Prepared.old_settings_path; old = $Prepared.old_settings_sha256; new = $Prepared.new_settings_sha256 }
    )
    # Validate both before restoring either; refuse to overwrite external edits.
    foreach ($entry in $entries) {
        $actual = Get-TaskSha $entry.target
        if ($actual -ne $entry.old -and $actual -ne $entry.new) { throw "Refusing rollback of a file changed outside this operation: $($entry.target)" }
        if ((Get-TaskSha $entry.backup) -ne $entry.old) { throw 'Rollback backup no longer matches its recorded hash.' }
    }
    foreach ($entry in $entries) {
        if ((Get-TaskSha $entry.target) -eq $entry.old) { continue }
        Replace-TaskFile $entry.backup $entry.target $entry.new $entry.old
    }
}

if ($Mode -eq 'Prepare') {
    if ([string]::IsNullOrWhiteSpace($NewPakPath) -or [string]::IsNullOrWhiteSpace($MetaPath)) { throw 'Prepare requires NewPakPath and MetaPath from final PAK readback.' }
    if (-not [string]::IsNullOrWhiteSpace($ExpectedNewSha256) -and $ExpectedNewSha256 -notmatch '^[a-fA-F0-9]{64}$') { throw 'ExpectedNewSha256 must be a SHA256 digest.' }
    if (-not [string]::IsNullOrWhiteSpace($ExpectedVersion) -and $ExpectedVersion -notmatch '^\d+\.\d+\.\d+\.\d+$') { throw 'ExpectedVersion must contain four decimal parts.' }
    $sourcePak = (Resolve-Path -LiteralPath $NewPakPath).Path
    $readbackMeta = (Resolve-Path -LiteralPath $MetaPath).Path
    if ($sourcePak -eq $taskPak -or [System.IO.Path]::GetExtension($sourcePak) -ne '.pak') { throw 'Select a separate built PAK, not the installed package.' }
    $sourcePakSha = Get-TaskSha $sourcePak
    $readbackMetaSha = Get-TaskSha $readbackMeta
    if (-not [string]::IsNullOrWhiteSpace($ExpectedNewSha256) -and $sourcePakSha -ne $ExpectedNewSha256.ToLowerInvariant()) { throw 'Built PAK SHA256 does not match ExpectedNewSha256.' }
    $readbackValues = Get-TaskModuleInfo $readbackMeta
    Assert-TaskIdentity $readbackValues
    Assert-TaskNoDuplicate
    $oldPakSha = Get-TaskSha $taskPak
    $oldSettingsSha = Get-TaskSha $taskSettings
    $original = Read-TaskXml $taskSettings
    $originalRow = Get-TaskEscRow $original
    $oldMeta = Get-TaskAttrs $originalRow
    Assert-TaskIdentity $oldMeta
    $otherBefore = @(Get-TaskOtherFiles)
    $savesBefore = @(Get-TaskSaves)
    $run = Join-Path $taskBuild ('local-build-update-' + (Get-Date -Format 'yyyyMMdd-HHmmss-ffffff'))
    Assert-TaskInside $run $taskBuild
    New-Item -ItemType Directory -Path $run | Out-Null
    $copyPak = Join-Path $run 'new-local.pak'
    $oldPakCopy = Join-Path $run 'installed.before.pak'
    $oldSettingsCopy = Join-Path $run 'modsettings.before.lsx'
    $newSettingsCopy = Join-Path $run 'modsettings.prepared.lsx'
    $readbackMetaCopy = Join-Path $run 'readback-meta.lsx'
    Copy-Item -LiteralPath $sourcePak -Destination $copyPak
    Copy-Item -LiteralPath $taskPak -Destination $oldPakCopy
    Copy-Item -LiteralPath $taskSettings -Destination $oldSettingsCopy
    Copy-Item -LiteralPath $readbackMeta -Destination $readbackMetaCopy
    foreach ($pair in @(@{path=$copyPak; sha=$sourcePakSha}, @{path=$oldPakCopy; sha=$oldPakSha}, @{path=$oldSettingsCopy; sha=$oldSettingsSha}, @{path=$readbackMetaCopy; sha=$readbackMetaSha})) {
        if ((Get-TaskSha $pair.path) -ne $pair.sha) { throw 'Backup/source copy verification failed.' }
    }
    $unpacked = Join-Path $run 'new-local-unpacked'
    & $taskDivine -g bg3 -a extract-package -s $copyPak -d $unpacked | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Built PAK extraction failed.' }
    $nativeMeta = Join-Path $unpacked "Mods\$taskFolder\meta.lsx"
    $newMeta = Get-TaskModuleInfo $nativeMeta
    Assert-TaskIdentity $newMeta
    foreach ($field in $taskFields) {
        if ($newMeta[$field] -cne $readbackValues[$field]) { throw "PAK ModuleInfo differs from supplied readback meta: $field" }
    }
    $newPacked = Get-TaskPackedVersion ([string]$newMeta.Version64)
    $version = Get-TaskVersion $newPacked
    if ($newPacked -le (Get-TaskPackedVersion ([string]$oldMeta.Version64))) { throw 'Built Version64 must be newer than the existing enabled ESC row.' }
    if (-not [string]::IsNullOrWhiteSpace($ExpectedVersion) -and $version -ne $ExpectedVersion) { throw 'PAK Version64 does not encode ExpectedVersion.' }
    foreach ($field in $taskFields) { $originalRow.SelectSingleNode("attribute[@id='$field']").SetAttribute('value', $newMeta[$field]) }
    $options = [System.Xml.XmlWriterSettings]::new()
    $options.Encoding = [System.Text.UTF8Encoding]::new($false)
    # XmlWriter defaults to Replace (Windows CRLF); retain parsed whitespace.
    # https://learn.microsoft.com/en-us/dotnet/api/system.xml.xmlwritersettings.newlinehandling
    $options.NewLineHandling = [System.Xml.NewLineHandling]::None
    $writer = [System.Xml.XmlWriter]::Create($newSettingsCopy, $options)
    try { $original.WriteTo($writer) } finally { $writer.Dispose() }
    $before = Read-TaskXml $oldSettingsCopy
    $after = Read-TaskXml $newSettingsCopy
    $afterRow = Get-TaskEscRow $after
    foreach ($field in $taskFields) { $afterRow.SelectSingleNode("attribute[@id='$field']").SetAttribute('value', $oldMeta[$field]) }
    if ($before.OuterXml -cne $after.OuterXml) { throw 'Prepared settings changed more than the ESC row six metadata values.' }
    if ((Get-TaskSha $sourcePak) -ne $sourcePakSha -or (Get-TaskSha $readbackMeta) -ne $readbackMetaSha -or
        (Get-TaskSha $taskPak) -ne $oldPakSha -or (Get-TaskSha $taskSettings) -ne $oldSettingsSha) { throw 'An input or installed file changed while preparing; prepare again.' }
    $prepared = [ordered]@{
        schema = 1; operation = 'esc-local-build-install'; status = 'prepared'; created = (Get-Date -Format o); module_uuid = $taskUuid
        version = $version; new_metadata = $newMeta; old_metadata = $oldMeta
        target_pak = $taskPak; target_settings = $taskSettings; source_pak = $sourcePak; source_meta = $readbackMeta
        metadata_source = $nativeMeta; metadata_source_sha256 = Get-TaskSha $nativeMeta
        readback_meta_path = $readbackMetaCopy; readback_meta_sha256 = $readbackMetaSha
        new_pak_path = $copyPak; new_pak_sha256 = $sourcePakSha; old_pak_path = $oldPakCopy; old_pak_sha256 = $oldPakSha
        old_settings_path = $oldSettingsCopy; old_settings_sha256 = $oldSettingsSha
        new_settings_path = $newSettingsCopy; new_settings_sha256 = Get-TaskSha $newSettingsCopy
        other_files = $otherBefore; saves = $savesBefore; toolkit_evidence = $null; applied_at = $null; rolled_back_at = $null; apply_error = $null; rollback_error = $null
        boundary = 'Prepare copied/extracted only into build; six metadata fields verified against actual PAK and supplied readback. Apply only replaces UUID-named ESC PAK and existing same-UUID settings row. Other PAK/SE files are hashed; saves use path/size/mtime inventory. No publication or game test by this helper.'
        rollback_boundary = 'Exact PAK/settings present at Prepare are retained; saves are inventoried, not backed up. Rollback refuses unknown target hashes and preserves the other-file/save inventory present when Rollback starts.'
    }
    Assert-TaskUntouched $prepared
    $outPath = Join-Path $run 'manifest.json'
    Save-TaskJson $prepared $outPath
    [ordered]@{ status = 'prepared'; manifest = $outPath; version = $version; package_sha256 = $sourcePakSha; other_pak_count = @($otherBefore | Where-Object {$_.kind -eq 'other-pak'}).Count; se_records = 2; save_records = $savesBefore.Count; installed_files_changed = $false } | ConvertTo-Json -Compress
    return
}

if ([string]::IsNullOrWhiteSpace($ManifestPath)) { throw 'Apply/Rollback requires the exact prepared manifest path.' }
$manifest = (Resolve-Path -LiteralPath $ManifestPath).Path
Assert-TaskInside $manifest $taskBuild
$run = Split-Path -Parent $manifest
if ([System.IO.Path]::GetFileName($run) -notmatch '^local-build-update-\d{8}-\d{6}-\d{6}$' -or [System.IO.Path]::GetFileName($manifest) -ne 'manifest.json') { throw 'Use a manifest created by this local build installer.' }
$prepared = Get-Content -LiteralPath $manifest -Raw -Encoding utf8 | ConvertFrom-Json
if ($prepared.schema -ne 1 -or $prepared.operation -ne 'esc-local-build-install' -or $prepared.module_uuid -ne $taskUuid -or
    $prepared.target_pak -ne $taskPak -or $prepared.target_settings -ne $taskSettings) { throw 'Manifest target identity is invalid.' }
foreach ($path in @($prepared.old_pak_path, $prepared.new_pak_path, $prepared.old_settings_path, $prepared.new_settings_path, $prepared.metadata_source, $prepared.readback_meta_path)) { Assert-TaskInside $path $run }
$requiredCopies = @(@{path=$prepared.old_pak_path; sha=$prepared.old_pak_sha256}, @{path=$prepared.old_settings_path; sha=$prepared.old_settings_sha256})
if ($Mode -eq 'Apply') {
    $requiredCopies += @(@{path=$prepared.new_pak_path; sha=$prepared.new_pak_sha256}, @{path=$prepared.new_settings_path; sha=$prepared.new_settings_sha256},
        @{path=$prepared.metadata_source; sha=$prepared.metadata_source_sha256}, @{path=$prepared.readback_meta_path; sha=$prepared.readback_meta_sha256})
}
foreach ($pair in $requiredCopies) { if ($pair.sha -notmatch '^[a-f0-9]{64}$' -or (Get-TaskSha $pair.path) -ne $pair.sha) { throw 'Prepared file or backup no longer matches its manifest.' } }
Assert-TaskReady

if ($Mode -eq 'Rollback') {
    $rollbackSnapshot = [ordered]@{ other_files = @(Get-TaskOtherFiles); saves = @(Get-TaskSaves) }
    Restore-TaskPair $prepared
    Assert-TaskUntouched $rollbackSnapshot
    $prepared.status = 'rolled-back'
    $prepared.rolled_back_at = Get-Date -Format o
    Save-TaskJson $prepared $manifest
    [ordered]@{ status = $prepared.status; manifest = $manifest; installed_version = Get-TaskVersion ([long]$prepared.old_metadata.Version64); other_files_unchanged = $true; save_inventory_unchanged = $true } | ConvertTo-Json -Compress
    return
}

if ($prepared.status -ne 'prepared') { throw 'This manifest has already been applied or retired. Prepare a new update.' }
Assert-TaskUntouched $prepared
if ((Get-TaskSha $taskPak) -ne $prepared.old_pak_sha256 -or (Get-TaskSha $taskSettings) -ne $prepared.old_settings_sha256) { throw 'Installed files changed since preparation; prepare again.' }
$evidence = Read-TaskToolkitEvidence $ExplicitToolkitEvidencePath $prepared.new_pak_sha256
$prepared.toolkit_evidence = $evidence
Save-TaskJson $prepared $manifest
Assert-TaskEvidenceUnchanged $evidence
Assert-TaskReady
try {
    Replace-TaskFile $prepared.new_pak_path $taskPak $prepared.old_pak_sha256 $prepared.new_pak_sha256
    Replace-TaskFile $prepared.new_settings_path $taskSettings $prepared.old_settings_sha256 $prepared.new_settings_sha256
    Assert-TaskUntouched $prepared
    Assert-TaskEvidenceUnchanged $evidence
    $prepared.status = 'applied'
    $prepared.applied_at = Get-Date -Format o
    Save-TaskJson $prepared $manifest
} catch {
    $failure = $_.Exception.Message
    try { Restore-TaskPair $prepared; $prepared.status = 'rolled-back-after-error' }
    catch { $prepared.status = 'rollback-needs-review'; $prepared.rollback_error = $_.Exception.Message }
    $prepared.apply_error = $failure
    Save-TaskJson $prepared $manifest
    throw "Local install failed: $failure. Recovery status: $($prepared.status). See $manifest"
}
[ordered]@{ status = 'applied'; manifest = $manifest; version = $prepared.version; installed_sha256 = Get-TaskSha $taskPak; other_files_unchanged = $true; save_inventory_unchanged = $true; toolkit_scope = $evidence.checked_asset_scope; game_test = 'not-run-by-helper'; publication = 'none' } | ConvertTo-Json -Depth 8 -Compress
