# Compile with the installed, IL-verified AllSpark API in a standalone .NET 4 host.
# Divine only serializes the native compiler's runtime XML into LSF, not .lsefx.
# All intermediate data stays in build; -InstallCompiled copies verified outputs.
param(
  [string]$Toolkit = 'E:/SteamLibrary/steamapps/common/Baldurs Gate 3 Toolkit',
  [string]$GameData = 'E:/SteamLibrary/steamapps/common/Baldurs Gate 3/Data',
  [string]$OutputDirectory,
  [string]$AuthoringManifest,
  [switch]$InstallCompiled
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$taskRepo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskFolder = 'EasternSwordCultivator_6560ea02-fe1e-5fdb-8631-b41a2e53af90'
$taskSourceRoot = Join-Path $taskRepo 'mods/EasternSwordCultivator/Source'
$taskSubdirectory = 'Tianqing'
$taskNames = @('Bafang_GroundColumn','Bafang_GroundRing','Lietian_GroundFall','TiandiStage_GroundFall','Tianjian_GroundFall','Wanjun_GroundFall') | ForEach-Object { 'VFX_ESC_Tianqing_' + $_ + '_01' }
if ($AuthoringManifest) {
  $taskPlanPath = [IO.Path]::GetFullPath($AuthoringManifest)
  $taskPlan = Get-Content -LiteralPath $taskPlanPath -Encoding utf8 -Raw | ConvertFrom-Json
  if ($taskPlan.subdirectory -notin @('Polish','Tianqing','Xueyan')) { throw 'Additional authoring must use a dedicated Polish, Tianqing or Xueyan directory.' }
  $taskSubdirectory = $taskPlan.subdirectory
  $taskNames = @($taskPlan.records | ForEach-Object { $_.effect_name })
  if ($taskNames.Count -eq 0 -or @($taskNames | Sort-Object -Unique).Count -ne $taskNames.Count) { throw 'Empty or duplicate effect names in authoring manifest.' }
  foreach ($taskEffectName in $taskNames) {
    if ($taskEffectName -cnotmatch ('^VFX_ESC_' + $taskSubdirectory + '_[A-Za-z0-9_]+_01$')) { throw 'Invalid authoring effect name.' }
  }
}
$taskEditor = Join-Path $taskSourceRoot ('Editor/Mods/' + $taskFolder + '/Assets/Effects/Sword/' + $taskSubdirectory)
$taskDestination = Join-Path $taskSourceRoot ('Public/' + $taskFolder + '/Assets/Effects/Effects_Banks/Sword/' + $taskSubdirectory)
$taskDivine = Join-Path $taskRepo 'build/tools/LSLib-1.20.4/Packed/Tools/Divine.exe'
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $taskRepo 'build/sword-vfx/tianqing-native-probe-20261007' }
$taskOutput = [IO.Path]::GetFullPath($OutputDirectory)
$taskBuildRoot = [IO.Path]::GetFullPath((Join-Path $taskRepo 'build/sword-vfx')) + [IO.Path]::DirectorySeparatorChar
if (-not $taskOutput.StartsWith($taskBuildRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Compilation outputs must remain in repository build/sword-vfx.' }
if ([Environment]::Version.Major -ne 4 -or [IntPtr]::Size -ne 8) {
  $taskLegacyHost = Join-Path $env:WINDIR 'System32/WindowsPowerShell/v1.0/powershell.exe'
  $taskArguments = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$PSCommandPath,'-Toolkit',$Toolkit,'-GameData',$GameData,'-OutputDirectory',$taskOutput)
  if ($AuthoringManifest) { $taskArguments += @('-AuthoringManifest',$taskPlanPath) }
  if ($InstallCompiled) { $taskArguments += '-InstallCompiled' }
  & $taskLegacyHost @taskArguments
  exit $LASTEXITCODE
}
[IO.Directory]::CreateDirectory($taskOutput) | Out-Null
Add-Type -AssemblyName System.Xml.Linq
# Compare every resource node, attribute type, and serialized value. Floating
# values are compared as the exact IEEE value actually stored by LSF; numeric
# type IDs and symbolic names are equivalent LSX representations.
Add-Type -ReferencedAssemblies @('System.Xml.Linq.dll','System.Xml.dll','System.Core.dll') -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Xml.Linq;
public static class TianqingLsfProof {
  static readonly Dictionary<string,string> Types = new Dictionary<string,string> {
    {"1","uint8"},{"4","int32"},{"5","uint32"},{"6","float"},
    {"7","double"},{"12","fvec3"},{"13","fvec4"},{"19","bool"},
    {"22","FixedString"},{"23","LSString"},{"31","guid"}
  };
  static string Text(XElement e, string n) { var a=e.Attribute(n); return a==null?null:a.Value; }
  static List<XElement> Elements(XElement e,string name) { return new List<XElement>(e.Elements(name)); }
  static string Type(XElement a) { string t=Text(a,"type"),v; return Types.TryGetValue(t,out v)?v:t; }
  static string Value(XElement a) {
    string t=Type(a),v=Text(a,"value");
    if(v==null) {
      var values=new List<string>();
      foreach(var e in a.Elements()) foreach(var f in e.Attributes()) values.Add(f.Value);
      v=String.Join(" ",values.ToArray());
    }
    if(t=="float"||t=="fvec3"||t=="fvec4") {
      var bits=new List<string>();
      foreach(var n in v.Split(new[]{' ','\t','\r','\n'},StringSplitOptions.RemoveEmptyEntries))
        bits.Add(Convert.ToBase64String(BitConverter.GetBytes(Single.Parse(n,CultureInfo.InvariantCulture))));
      return String.Join("|",bits.ToArray());
    }
    if(t=="double") return Convert.ToBase64String(BitConverter.GetBytes(Double.Parse(v,CultureInfo.InvariantCulture)));
    if(t=="bool") { if(v=="0") return "False"; if(v=="1") return "True"; return Boolean.Parse(v).ToString(); }
    if(t=="guid") return new Guid(v).ToString("D");
    if(t=="uint8"||t=="uint32"||t=="int32") return Int64.Parse(v,CultureInfo.InvariantCulture).ToString(CultureInfo.InvariantCulture);
    return v;
  }
  static void Same(string a,string b,string where) { if(a!=b) throw new Exception("LSF roundtrip mismatch at "+where+": "+a+" != "+b); }
  static void Node(XElement a,XElement b,string path) {
    Same(Text(a,"id"),Text(b,"id"),path+"/id");
    var xa=new Dictionary<string,string>();var xb=new Dictionary<string,string>();
    foreach(var f in a.Attributes()) xa.Add(f.Name.ToString(),f.Value);
    foreach(var f in b.Attributes()) xb.Add(f.Name.ToString(),f.Value);
    Same(xa.Count.ToString(),xb.Count.ToString(),path+"/node-attributes");
    foreach(var f in xa) { string v; if(!xb.TryGetValue(f.Key,out v)) throw new Exception("Missing node attribute "+path+"/"+f.Key); Same(f.Value,v,path+"/"+f.Key); }
    var aa=new Dictionary<string,XElement>();var ab=new Dictionary<string,XElement>();
    foreach(var f in a.Elements("attribute")) aa.Add(Text(f,"id"),f);
    foreach(var f in b.Elements("attribute")) ab.Add(Text(f,"id"),f);
    Same(aa.Count.ToString(),ab.Count.ToString(),path+"/attribute-count");
    foreach(var f in aa) {
      XElement v;if(!ab.TryGetValue(f.Key,out v)) throw new Exception("Missing attribute "+path+"/"+f.Key);
      Same(Type(f.Value),Type(v),path+"/"+f.Key+"/type");
      Same(Value(f.Value),Value(v),path+"/"+f.Key+"/value");
    }
    var ac=new List<XElement>();var bc=new List<XElement>();
    foreach(var c in a.Elements("children")) ac.AddRange(c.Elements("node"));
    foreach(var c in b.Elements("children")) bc.AddRange(c.Elements("node"));
    Same(ac.Count.ToString(),bc.Count.ToString(),path+"/child-count");
    for(int i=0;i<ac.Count;i++) Node(ac[i],bc[i],path+"/"+Text(ac[i],"id")+"["+i+"]");
  }
  public static void Validate(string expected,string actual) {
    var a=XDocument.Load(expected);var b=XDocument.Load(actual);
    Same(a.Root.Name.LocalName,b.Root.Name.LocalName,"root");
    var ar=new Dictionary<string,XElement>();var br=new Dictionary<string,XElement>();
    foreach(var r in a.Root.Elements("region")) ar.Add(Text(r,"id"),r);
    foreach(var r in b.Root.Elements("region")) br.Add(Text(r,"id"),r);
    Same(ar.Count.ToString(),br.Count.ToString(),"region-count");
    foreach(var r in ar) {
      XElement v;if(!br.TryGetValue(r.Key,out v)) throw new Exception("Missing region "+r.Key);
      var an=Elements(r.Value,"node");var bn=Elements(v,"node");
      Same(an.Count.ToString(),bn.Count.ToString(),r.Key+"/root-count");
      for(int i=0;i<an.Count;i++) Node(an[i],bn[i],r.Key);
    }
  }
}
'@
function Get-TaskHash([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Write-TaskJson($Data,[string]$Path) { [IO.File]::WriteAllText($Path,($Data | ConvertTo-Json -Depth 12) + [Environment]::NewLine,(New-Object Text.UTF8Encoding($false))) }
function Invoke-TaskConvert([string]$InputPath,[string]$DestinationPath) {
  $taskLog = & $taskDivine -g bg3 -a convert-resource -s $InputPath -d $DestinationPath 2>&1
  if ($LASTEXITCODE -ne 0 -or -not [IO.File]::Exists($DestinationPath)) { throw ('Divine failed: ' + ($taskLog -join [Environment]::NewLine)) }
}
$taskAssemblies = @{}
$taskDependencies = @()
foreach ($taskDll in @('LSCSharpCore.dll','AllSpark.DataLayer.dll','AllSpark.EffectCompiler.dll','AllSpark.EffectEditor.dll')) {
  $taskPath = Join-Path $Toolkit $taskDll
  $taskDependencies += @{path=$taskPath;sha256=(Get-TaskHash $taskPath)}
  $taskAssemblies[$taskDll] = [Reflection.Assembly]::LoadFrom($taskPath)
}
$taskXmdPath = Join-Path $GameData 'Editor/Config/AllSpark/ModuleDefinition.xmd'
$taskXcdPath = Join-Path $GameData 'Editor/Config/AllSpark/ComponentDefinition.xcd'
foreach ($taskPath in @($taskXmdPath,$taskXcdPath,$taskDivine)) { $taskDependencies += @{path=$taskPath;sha256=(Get-TaskHash $taskPath)} }
$taskModuleType = $taskAssemblies['AllSpark.DataLayer.dll'].GetType('AllSpark.DataLayer.Module.ModuleDefinition',$true)
$taskModule = [Activator]::CreateInstance($taskModuleType)
$taskModuleType.GetMethod('Load',[type[]]@([System.Xml.Linq.XElement])).Invoke($taskModule,[object[]]@(([System.Xml.Linq.XDocument]::Load($taskXmdPath)).Root)) | Out-Null
$taskComponentType = $taskAssemblies['AllSpark.DataLayer.dll'].GetType('AllSpark.DataLayer.ComponentDefinition',$true)
$taskComponent = [Activator]::CreateInstance($taskComponentType,[object[]]@($taskModule))
$taskComponentType.GetMethod('Load',[type[]]@([System.Xml.Linq.XElement])).Invoke($taskComponent,[object[]]@(([System.Xml.Linq.XDocument]::Load($taskXcdPath)).Root)) | Out-Null
$taskEffectType = $taskAssemblies['AllSpark.DataLayer.dll'].GetType('AllSpark.DataLayer.Effect',$true)
$taskTransformer = $taskAssemblies['AllSpark.EffectEditor.dll'].GetType('AllSpark.EffectEditor.EffectTransformer',$true)
$taskTransformMethod = $taskTransformer.GetMethod('ToNewFormat',[Reflection.BindingFlags]'Public,Static',$null,[type[]]@($taskEffectType),$null)
$taskCompilerType = $taskAssemblies['AllSpark.EffectCompiler.dll'].GetType('AllSpark.EffectCompiler.Compiler',$true)
$taskCompiler = [Activator]::CreateInstance($taskCompilerType)
$taskCompileMethod = $taskCompilerType.GetMethod('Compile',[type[]]@($taskEffectType))
$taskRecords = @()
foreach ($taskName in $taskNames) {
  $taskInputPath = Join-Path $taskEditor ($taskName + '.lsefx')
  $taskSourceHash = Get-TaskHash $taskInputPath
  $taskEffect = [Activator]::CreateInstance($taskEffectType,[object[]]@($taskComponent.PropertyDefinitionContainer,$taskModule))
  $taskEffectType.GetMethod('Load',[type[]]@([System.Xml.Linq.XElement])).Invoke($taskEffect,[object[]]@(([System.Xml.Linq.XDocument]::Load($taskInputPath)).Root)) | Out-Null
  $taskTransformMethod.Invoke($null,[object[]]@($taskEffect)) | Out-Null
  $taskCompiled = $taskCompileMethod.Invoke($taskCompiler,[object[]]@($taskEffect))
  if ($taskCompiled.GetType().FullName -ne 'System.Xml.Linq.XDocument' -or $taskCompiled.Root.Name.LocalName -ne 'save') { throw ('Unexpected compiler output for ' + $taskName) }
  $taskXmlPath = Join-Path $taskOutput ($taskName + '.compiled.lsx')
  $taskCompiled.Save($taskXmlPath)
  # Native MObjectVisitor writes top-level region IDs as LSF node names. LSLib
  # writes the XML node IDs instead. Normalize only the packaging copy; retaining
  # two 'root' node names makes LSF readers overwrite the Dependencies region.
  # Real prior AllSpark .lsfx readback has Dependencies/Dependencies, Effect/Effect.
  $taskPackaging = New-Object System.Xml.Linq.XDocument($taskCompiled)
  $taskRegionIds = @()
  foreach ($taskRegion in $taskPackaging.Root.Elements('region')) {
    $taskRegionId = $taskRegion.Attribute('id').Value
    $taskRegionIds += $taskRegionId
    $taskRegion.Element('node').SetAttributeValue('id',$taskRegionId)
  }
  if ((($taskRegionIds | Sort-Object) -join ',') -ne 'Dependencies,Effect') { throw ('Unexpected runtime regions: ' + ($taskRegionIds -join ',')) }
  $taskPackagingPath = Join-Path $taskOutput ($taskName + '.binary-input.lsx')
  $taskPackaging.Save($taskPackagingPath)
  $taskBinaryPath = Join-Path $taskOutput ($taskName + '.lsfx')
  $taskRoundtripPath = Join-Path $taskOutput ($taskName + '.roundtrip.lsx')
  Invoke-TaskConvert $taskPackagingPath $taskBinaryPath
  $taskBytes = [IO.File]::ReadAllBytes($taskBinaryPath)
  if ($taskBytes.Length -lt 8 -or [Text.Encoding]::ASCII.GetString($taskBytes,0,4) -ne 'LSOF' -or [BitConverter]::ToUInt32($taskBytes,4) -ne 7) { throw ('Invalid BG3 LSF binary: ' + $taskName) }
  Invoke-TaskConvert $taskBinaryPath $taskRoundtripPath
  [TianqingLsfProof]::Validate($taskPackagingPath,$taskRoundtripPath)
  if ((Get-TaskHash $taskInputPath) -ne $taskSourceHash) { throw ('Source changed while compiling: ' + $taskName) }
  $taskRecord = [ordered]@{
    effect_name=$taskName; source_sha256=$taskSourceHash; compiled_sha256=(Get-TaskHash $taskBinaryPath)
    compiled_xml_sha256=(Get-TaskHash $taskXmlPath); packaging_xml_sha256=(Get-TaskHash $taskPackagingPath)
    normalizeTopLevelNodeIds=$true; semantic_roundtrip_verified=$true; binary_magic='LSOF'; binary_version=7
    compiled_bytes=$taskBytes.Length; component_count=@($taskCompiled.Descendants('node') | Where-Object { $_.Attribute('id').Value -eq 'EffectComponent' }).Count
    source=$taskInputPath; compiled_xml=$taskXmlPath; packaging_xml=$taskPackagingPath; compiled_binary=$taskBinaryPath; roundtrip_xml=$taskRoundtripPath
  }
  Write-TaskJson $taskRecord (Join-Path $taskOutput ($taskName + '.compile-evidence.json'))
  $taskRecords += $taskRecord
  Write-Output ('Compiled and verified ' + $taskName + ' (' + $taskBytes.Length + ' bytes)')
}
$taskReceipt = [ordered]@{
  compiler='AllSpark.EffectCompiler.Compiler.Compile'; binary_wrapper='LSLib 1.20.4 Divine convert-resource'
  normalizeTopLevelNodeIds=$true; normalization_basis='LSLib LSFWriter serializes Node.Name; native AllSpark .lsfx readback has Dependencies/Dependencies and Effect/Effect.'
  preserved_native_xml=$true; standalone_process=$true; runtime=[Environment]::Version.ToString(); process_bitness=[IntPtr]::Size*8
  created_utc=[DateTime]::UtcNow.ToString('o'); dependencies=$taskDependencies; records=$taskRecords
  proof_scope='Native runtime XML compilation and exact typed per-region LSF roundtrip; no client rendering or gameplay validation.'
}
$taskReceiptPath = Join-Path $taskOutput 'native-compile.json'
Write-TaskJson $taskReceipt $taskReceiptPath
if ($InstallCompiled) {
  # Partial authoring compiles only the requested banks. Retain independently
  # verified receipts for untouched banks; never silently bless stale inputs.
  $taskPublicReceiptPath = Join-Path $taskDestination 'native-compile.json'
  $taskRetainedRecords = @()
  if (Test-Path -LiteralPath $taskPublicReceiptPath) {
    $taskPreviousReceipt = Get-Content -LiteralPath $taskPublicReceiptPath -Encoding utf8 -Raw | ConvertFrom-Json
    if ($taskPreviousReceipt.compiler -ne $taskReceipt.compiler) { throw 'Existing native compilation receipt uses a different compiler.' }
    foreach ($taskPreviousRecord in $taskPreviousReceipt.records) {
      if ($taskPreviousRecord.effect_name -in $taskNames) { continue }
      $taskPreviousEditor = Join-Path $taskEditor ($taskPreviousRecord.effect_name + '.lsefx')
      $taskPreviousBinary = Join-Path $taskDestination ($taskPreviousRecord.effect_name + '.lsfx')
      if ((Get-TaskHash $taskPreviousEditor) -ne $taskPreviousRecord.source_sha256 -or (Get-TaskHash $taskPreviousBinary) -ne $taskPreviousRecord.compiled_sha256) {
        throw ('Untouched compilation receipt is stale: ' + $taskPreviousRecord.effect_name)
      }
      $taskRetainedRecords += $taskPreviousRecord
    }
  }
  [IO.Directory]::CreateDirectory($taskDestination) | Out-Null
  foreach ($taskRecord in $taskRecords) {
    $taskCopy = Join-Path $taskDestination ($taskRecord.effect_name + '.lsfx')
    [IO.File]::Copy($taskRecord.compiled_binary,$taskCopy,$true)
    if ((Get-TaskHash $taskCopy) -ne $taskRecord.compiled_sha256) { throw ('Copied output hash mismatch: ' + $taskRecord.effect_name) }
  }
  $taskPublicRecords = @($taskRetainedRecords)
  foreach ($taskRecord in $taskRecords) {
    $taskPublicRecords += [ordered]@{
      effect_name=$taskRecord.effect_name; source_sha256=$taskRecord.source_sha256; compiled_sha256=$taskRecord.compiled_sha256
      source=('Editor/Mods/' + $taskFolder + '/Assets/Effects/Sword/' + $taskSubdirectory + '/' + $taskRecord.effect_name + '.lsefx')
      compiled_binary=('Public/' + $taskFolder + '/Assets/Effects/Effects_Banks/Sword/' + $taskSubdirectory + '/' + $taskRecord.effect_name + '.lsfx')
      compiled_xml_sha256=$taskRecord.compiled_xml_sha256; packaging_xml_sha256=$taskRecord.packaging_xml_sha256
      normalizeTopLevelNodeIds=$true; semantic_roundtrip_verified=$true; binary_version=7
    }
  }
  $taskPublicReceipt = [ordered]@{
    compiler=$taskReceipt.compiler; binary_wrapper=$taskReceipt.binary_wrapper; normalizeTopLevelNodeIds=$true
    packaging_proof='Native XML retained; only top-level node IDs normalized to region IDs, matching native AllSpark binary structure. Every region node and typed attribute value passed LSF readback comparison.'
    records=$taskPublicRecords
  }
  Write-TaskJson $taskPublicReceipt (Join-Path $taskDestination 'native-compile.json')
  Write-Output ('Verified binaries and receipt installed into repository Source: ' + $taskDestination)
}
