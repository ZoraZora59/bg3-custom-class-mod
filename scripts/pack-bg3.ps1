# Run with PowerShell 7: LSLib 1.20.4 targets modern .NET.
param(
    [Parameter(Mandatory)][string]$Source,
    [Parameter(Mandatory)][string]$Output,
    [Parameter(Mandatory)][string]$LibraryDirectory
)
$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'Use pwsh (PowerShell 7) for LSLib.' }
$LibraryDirectory = (Resolve-Path -LiteralPath $LibraryDirectory).Path
foreach ($assembly in @('K4os.Compression.LZ4.dll', 'K4os.Hash.xxHash.dll', 'K4os.Compression.LZ4.Streams.dll', 'LSLib.dll')) {
    Add-Type -Path (Join-Path $LibraryDirectory $assembly)
}
$packageBuild = [LSLib.LS.PackageBuildData]::new()
$packageBuild.Version = [LSLib.LS.Enums.PackageVersion]::V18
$packageBuild.Flags = [LSLib.LS.PackageFlags]::AllowMemoryMapping
$packageBuild.Hash = $true
$packageBuild.Compression = [LSLib.LS.CompressionMethod]::LZ4
$packager = [LSLib.LS.Packager]::new()
$null = $packager.CreatePackage([IO.Path]::GetFullPath($Output), (Resolve-Path -LiteralPath $Source).Path, $packageBuild).GetAwaiter().GetResult()
Write-Output "Created BG3 package with memory mapping and archive checksum: $Output"
