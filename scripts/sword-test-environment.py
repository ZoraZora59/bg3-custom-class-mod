"""Deploy/restore only this mod and a temporary, backed-up test configuration.

Run with BG3/Toolkit closed. Existing PAKs and saved games are never modified.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from sword_cultivator_spec import FOLDER,MOD,MODULE_UUID,VERSION64

REPO=Path(__file__).resolve().parents[1]
GAME=Path('E:/SteamLibrary/steamapps/common/Baldurs Gate 3')
LOCAL=Path(os.environ['LOCALAPPDATA'])/'Larian Studios/Baldur\'s Gate 3'
SETTINGS=LOCAL/'PlayerProfiles/Public/modsettings.lsx'
PACKAGE=LOCAL/'Mods'/f'{MOD}.pak'
SESETTINGS=GAME/'bin/ScriptExtenderSettings.json'
BACKUP=REPO/'build/sword-cultivator/test-environment'
TOOLKIT_REPORT=REPO/'build/sword-cultivator/toolkit-validation.json'
BUILD=REPO/'build/sword-cultivator'
CAPTURES=BUILD/'toolkit-environment'
LEGACY_DEPLOY_ARCHIVE=BUILD/'prior-release-20261001-005752'
TOOLKIT_CASES={'project_load','class_and_subclasses','level_1_to_12','spells_and_icons','editor_log'}


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def check_closed():
    tasks=subprocess.check_output(['tasklist','/FO','CSV','/NH'],text=True,errors='replace').lower()
    if any('"'+process+'"' in tasks for process in ['bg3.exe','bg3_dx11.exe','glasses.exe']):
        raise SystemExit('Close BG3 and Toolkit normally before deployment/restoration.')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write_json_atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,
                                     prefix=path.name+'.',suffix='.tmp',delete=False) as stream:
        temporary=Path(stream.name)
        json.dump(value,stream,indent=2,ensure_ascii=False)
    try:os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)


def verified_toolkit_package(built,report_path,build_report_path):
    if not built.is_file() or not report_path.is_file() or not build_report_path.is_file():
        raise SystemExit('Toolkit package, validation, and build report are all required.')
    package_sha=digest(built)
    toolkit=read_json(report_path)
    cases=toolkit.get('Cases',{})
    if (toolkit.get('Status')!='pass' or
            any(cases.get(key,{}).get('Status')!='pass' or not cases[key].get('Evidence')
                for key in TOOLKIT_CASES)):
        raise SystemExit('The Toolkit report does not prove all five required editor checks.')
    if toolkit.get('PackageSHA256','').lower()!=package_sha:
        raise SystemExit('The package differs from the Toolkit-verified version; retest before deployment.')
    if read_json(build_report_path).get('SHA256','').lower()!=package_sha:
        raise SystemExit('The package differs from its build report.')
    return package_sha


def active_test_state():
    path=BACKUP/'state.json'
    if not path.is_file():raise SystemExit('No active ESC game-test deployment state exists.')
    state=read_json(path)
    if not state.get('active'):raise SystemExit('The ESC game-test environment is not active.')
    pak_records=[record for record in state.get('files',[]) if record.get('key')=='pak']
    if len(pak_records)!=1 or Path(pak_records[0].get('path',''))!=PACKAGE:
        raise SystemExit('The active state does not own this ESC PAK path.')
    return path,state


def last_deployed_sha(state,installed_sha):
    recorded=state.get('deployed_pak_sha256')
    if recorded:
        if not re.fullmatch(r'[0-9a-fA-F]{64}',recorded):
            raise SystemExit('The active deployment SHA is malformed.')
        return recorded.lower(),'state'
    # The first 629ADB deployment predates SHA tracking. Adopt it only from
    # the exact archived PAK and the original five-case Toolkit gate.
    archived=LEGACY_DEPLOY_ARCHIVE/f'{MOD}.pak'
    archived_sha=verified_toolkit_package(archived,LEGACY_DEPLOY_ARCHIVE/'toolkit-validation.json',
                                         LEGACY_DEPLOY_ARCHIVE/'build-report.json')
    if archived_sha!=installed_sha:
        raise SystemExit('Untracked installed PAK does not match the archived owned deployment.')
    return archived_sha,'prior-release-20261001-005752'


def refresh():
    """Replace only the currently owned test PAK after a new five-case gate."""
    check_closed()
    loose_state=REPO/'build/sword-cultivator/toolkit-environment/state.json'
    if loose_state.exists() and read_json(loose_state).get('active'):
        raise SystemExit('Capture and restore Toolkit loose source before refreshing the game PAK.')
    status,state=active_test_state()
    if state.get('pending_refresh'):
        raise SystemExit('A PAK refresh is pending; inspect state and restore/reconcile before retrying.')
    if not PACKAGE.is_file():raise SystemExit('The currently deployed ESC PAK is missing.')
    installed_sha=digest(PACKAGE)
    owned_sha,provenance=last_deployed_sha(state,installed_sha)
    if installed_sha!=owned_sha:
        raise SystemExit('Installed ESC PAK differs from the last state-owned deployment; refusing to overwrite it.')
    built=BUILD/f'{MOD}.pak'
    next_sha=verified_toolkit_package(built,TOOLKIT_REPORT,BUILD/'build-report.json')
    if next_sha==installed_sha:raise SystemExit('The Toolkit-verified PAK is already installed.')

    backup=BACKUP/'package-upgrades'/f'{installed_sha}.pak'
    backup.parent.mkdir(parents=True,exist_ok=True)
    if backup.exists():
        if digest(backup)!=installed_sha:raise SystemExit('Existing test PAK backup has the wrong SHA.')
    else:
        with tempfile.NamedTemporaryFile('wb',dir=backup.parent,prefix='pak.',suffix='.tmp',delete=False) as stream:
            temporary_backup=Path(stream.name)
        try:
            shutil.copy2(PACKAGE,temporary_backup)
            if digest(temporary_backup)!=installed_sha:raise SystemExit('Old test PAK backup verification failed.')
            os.replace(temporary_backup,backup)
        finally:temporary_backup.unlink(missing_ok=True)

    now=datetime.now(timezone.utc)
    record={'previous_sha256':installed_sha,'next_sha256':next_sha,
            'backup':str(backup),'toolkit_report':str(TOOLKIT_REPORT),
            'toolkit_report_sha256':digest(TOOLKIT_REPORT),
            'source':provenance,'at_utc':now.isoformat()}
    report=BACKUP/f'refresh-{now.strftime("%Y%m%dT%H%M%S%fZ")}-{next_sha[:12]}.json'
    record['report']=str(report)
    state['deployed_pak_sha256']=installed_sha
    state['pending_refresh']=record
    write_json_atomic(status,state)
    try:
        with tempfile.NamedTemporaryFile('wb',dir=PACKAGE.parent,prefix=MOD+'.',suffix='.tmp',delete=False) as stream:
            staged=Path(stream.name)
        try:
            shutil.copy2(built,staged)
            if digest(staged)!=next_sha:raise SystemExit('Staged PAK verification failed.')
            os.replace(staged,PACKAGE)
        finally:staged.unlink(missing_ok=True)
    except BaseException:
        if PACKAGE.is_file() and digest(PACKAGE)==installed_sha:
            state.pop('pending_refresh',None)
            write_json_atomic(status,state)
        raise
    if digest(PACKAGE)!=next_sha:
        raise SystemExit('Refreshed PAK readback failed; original remains in package-upgrades backup.')
    write_json_atomic(report,record)
    state['deployed_pak_sha256']=next_sha
    state.setdefault('refresh_history',[]).append(record)
    state.pop('pending_refresh',None)
    write_json_atomic(status,state)
    print('Test PAK refreshed: '+installed_sha+' -> '+next_sha+'; backup: '+str(backup))


def diagnostic_exit_override(capture_arg,analysis_arg,expected_package_sha,built):
    """Authorize a game *diagnostic* from immutable evidence, never Toolkit pass."""
    capture=Path(capture_arg).resolve(strict=True)
    analysis=Path(analysis_arg).resolve(strict=True)
    if capture.parent!=CAPTURES.resolve() or not capture.name.startswith('capture-'):
        raise SystemExit('Diagnostic override needs an immutable Toolkit capture under this build.')
    if not analysis.is_relative_to(BUILD.resolve()):
        raise SystemExit('Diagnostic analysis must be saved under this build directory.')
    package_sha=digest(built)
    if len(expected_package_sha)!=64 or expected_package_sha.lower()!=package_sha:
        raise SystemExit('Explicit diagnostic package SHA does not match the PAK.')
    build_report=json.loads((BUILD/'build-report.json').read_text(encoding='utf-8'))
    if build_report.get('SHA256','').lower()!=package_sha:
        raise SystemExit('The PAK does not match the recorded build report.')

    manifest_path=capture/'capture.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    files=manifest.get('files',{})
    if not all(isinstance(files.get(part),dict) and files[part] for part in ('Mods','Public')):
        raise SystemExit('Toolkit capture lacks module and public source evidence.')
    package_files={row['Path'].replace('\\','/').casefold():row['SHA256'].lower()
                   for row in build_report['Files']}
    derived={f'Mods/{FOLDER}/GUI/metadata.lsf'.casefold(),
             f'Public/{FOLDER}/Content/UI/[PAK]_ESC_UI/_merged.lsf'.casefold()}
    compared={'Mods':0,'Public':0}
    for part,entries in files.items():
        for relative,recorded_sha in entries.items():
            source=(capture/'Data'/part/FOLDER/relative).resolve()
            if not source.is_relative_to(capture) or not source.is_file() or digest(source)!=recorded_sha.lower():
                raise SystemExit('Toolkit capture file is missing or differs from its manifest: '+str(source))
            if part in compared:
                key=f'{part}/{FOLDER}/{relative}'.casefold()
                if key in package_files and key not in derived:
                    if package_files[key]!=recorded_sha.lower():
                        raise SystemExit('Toolkit capture and PAK build differ: '+key)
                    compared[part]+=1
    if not all(compared.values()):
        raise SystemExit('Toolkit capture and PAK build have no comparable module/public files.')

    saved=json.loads(analysis.read_text(encoding='utf-8'))
    log=Path(saved['Log']).resolve(strict=True)
    if not log.is_relative_to(capture/'logs'):
        raise SystemExit('Diagnostic analysis does not reference a log in the specified capture.')
    analyzer=REPO/'scripts/analyze-sword-toolkit-log.py'
    rerun=subprocess.run([sys.executable,str(analyzer),'--log',str(log)],
                         capture_output=True,text=True,encoding='utf-8',errors='replace')
    if rerun.returncode!=1 or json.loads(rerun.stdout)!=saved:
        raise SystemExit('Diagnostic analysis is stale or does not reproduce from the captured log.')
    crash=saved.get('NativeCrash',{})
    frames=' '.join(row['text'] for row in crash.get('RelevantStackFrames',[]))
    if (saved.get('ModuleIssues') or saved.get('ModuleErrorGate')!='no-attributable-errors-observed'
            or saved.get('ProcessExitGate')!='fail-native-crash'
            or saved.get('ToolkitLogGate')!='fail' or not crash.get('Detected')
            or 'Noesis::' not in frames or 'UninstallGameUI' not in frames):
        raise SystemExit('Diagnostic override applies only to clean module logs with a native UI-exit crash.')
    return {'mode':'diagnostic-only-toolkit-exit-override','toolkit_status':'fail-native-crash',
            'capture':str(capture),'capture_manifest_sha256':digest(manifest_path),
            'analysis':str(analysis),'analysis_sha256':digest(analysis),
            'log':str(log),'log_sha256':digest(log),'package_sha256':package_sha,
            'package_overlap_files':compared}


def deploy(override_args=None):
    check_closed()
    loose_state=REPO/'build/sword-cultivator/toolkit-environment/state.json'
    if loose_state.exists() and json.loads(loose_state.read_text(encoding='utf-8'))['active']:
        raise SystemExit('Capture and restore Toolkit loose source before testing the packaged game mod.')
    # The requested test order is a real gate, not merely a note in the report.
    built=REPO/'build/sword-cultivator/EasternSwordCultivator.pak'
    override=None
    if override_args:
        override=diagnostic_exit_override(*override_args,built)
    else:
        verified_toolkit_package(built,TOOLKIT_REPORT,BUILD/'build-report.json')
    status=BACKUP/'state.json'
    if status.exists():
        previous=json.loads(status.read_text(encoding='utf-8'))
        if previous['active']:raise SystemExit('A test environment is already active; restore it first.')
    BACKUP.mkdir(parents=True,exist_ok=True)
    records=[]
    for key,path in [('modsettings',SETTINGS),('pak',PACKAGE),('se_settings',SESETTINGS)]:
        record=dict(key=key,path=str(path),existed=path.exists())
        if path.exists():
            record['sha256']=digest(path)
            shutil.copy2(path,BACKUP/(key+'.backup'))
        records.append(record)
    state=dict(active=True,files=records,existing_paks={p.name:digest(p) for p in (LOCAL/'Mods').glob('*.pak')},
               saves=[str(p.relative_to(LOCAL)) for p in (LOCAL/'PlayerProfiles/Public/Savegames').rglob('*.lsv')])
    if override:state['diagnostic_toolkit_override']=override
    # Save the recovery state BEFORE touching any live files.
    status.write_text(json.dumps(state,indent=2),encoding='utf-8')
    root=ET.parse(SETTINGS).getroot()
    mods=root.find(".//node[@id='Mods']/children")
    for row in list(mods):
        fields={a.get('id'):a.get('value') for a in row.findall('attribute')}
        if fields.get('Folder')!='GustavX':mods.remove(row)
    row=ET.SubElement(mods,'node',id='ModuleShortDesc')
    for key,typ,value in [('Folder','LSString',FOLDER),('Name','LSString',MOD),('UUID','guid',MODULE_UUID),
                           ('Version64','int64',VERSION64),('MD5','LSString',''),('PublishHandle','uint64',0)]:
        ET.SubElement(row,'attribute',id=key,type=typ,value=str(value))
    order=root.find(".//node[@id='ModOrder']")
    if order is None:
        order=ET.SubElement(root.find('.//node[@id="root"]/children'),'node',id='ModOrder')
    for child in list(order):order.remove(child)
    children=ET.SubElement(order,'children')
    ET.SubElement(ET.SubElement(children,'node',id='Module'),'attribute',id='UUID',type='guid',value=MODULE_UUID)
    ET.indent(root)
    ET.ElementTree(root).write(SETTINGS,encoding='utf-8',xml_declaration=True)
    shutil.copy2(built,PACKAGE)
    state['deployed_pak_sha256']=digest(PACKAGE)
    write_json_atomic(status,state)
    log_directory=BACKUP/'logs';log_directory.mkdir(exist_ok=True)
    settings=json.loads(SESETTINGS.read_text(encoding='utf-8-sig')) if SESETTINGS.exists() else {}
    settings.update(EnableLogging=True,LogRuntime=True,LogFailedCompile=True,LogDirectory=str(log_directory),CreateConsole=False)
    SESETTINGS.write_text(json.dumps(settings,indent=2),encoding='utf-8')
    print('Test environment active. Original settings backup: '+str(BACKUP))
    if override:print('Diagnostic-only override active; Toolkit remains failed due to native exit crash.')


def restore():
    check_closed()
    status=BACKUP/'state.json'
    state=json.loads(status.read_text(encoding='utf-8'))
    if not state['active']:raise SystemExit('Test environment is already restored.')
    for record in state['files']:
        path=Path(record['path'])
        if record['existed']:
            shutil.copy2(BACKUP/(record['key']+'.backup'),path)
            assert digest(path)==record['sha256']
        elif path.exists():
            archived=BACKUP/('retired-'+record['key']+path.suffix)
            shutil.copy2(path,archived)
            path.unlink()
    # Other applications or manual mod management may change unrelated PAKs.
    # Never recreate or overwrite those files to force a clean audit.
    differences=[]
    for name,sha in state['existing_paks'].items():
        path=LOCAL/'Mods'/name
        if not path.exists():differences.append(dict(name=name,result='missing',original_sha256=sha))
        elif digest(path)!=sha:differences.append(dict(name=name,result='changed',original_sha256=sha,current_sha256=digest(path)))
    state['active']=False
    state['external_pak_differences']=differences
    state['restore']='original configuration restored; unrelated PAK audit '+('has differences' if differences else 'matches')
    status.write_text(json.dumps(state,indent=2),encoding='utf-8')
    print(state['restore'])
    for item in differences:print(item['result']+': '+item['name'])


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['deploy','refresh','restore'])
    parser.add_argument('--diagnostic-toolkit-exit-override',action='store_true',
                        help='Permit an isolated game diagnostic with a documented Toolkit UI-exit crash')
    parser.add_argument('--toolkit-capture',type=Path)
    parser.add_argument('--toolkit-analysis',type=Path)
    parser.add_argument('--diagnostic-package-sha')
    args=parser.parse_args()
    evidence=(args.toolkit_capture,args.toolkit_analysis,args.diagnostic_package_sha)
    if args.diagnostic_toolkit_exit_override:
        if args.action!='deploy' or not all(evidence):
            parser.error('Diagnostic override requires deploy, capture, analysis, and exact package SHA.')
    elif any(evidence):
        parser.error('Diagnostic evidence options require --diagnostic-toolkit-exit-override.')
    if args.action=='deploy':deploy(evidence if args.diagnostic_toolkit_exit_override else None)
    elif args.action=='refresh':refresh()
    else:restore()
