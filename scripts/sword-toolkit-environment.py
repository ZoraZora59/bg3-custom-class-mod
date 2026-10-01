"""Install/capture/restore this project's Toolkit source without touching other mods.

Installation and restoration require both editor and game to be closed. Captures
are immutable evidence snapshots; they never overwrite the repository source.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from sword_cultivator_spec import FOLDER, MOD

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / 'mods' / MOD / 'Source'
DATA = Path('E:/SteamLibrary/steamapps/common/Baldurs Gate 3/Data').resolve()
TOOLKIT = Path('E:/SteamLibrary/steamapps/common/Baldurs Gate 3 Toolkit')
BASE = REPO / 'build/sword-cultivator/toolkit-environment'
STATE = BASE / 'state.json'
PARTS = ('Mods', 'Public', 'Projects', 'Editor/Mods', 'Generated/Public')
EDITOR_DESCRIPTION = ('Eastern Sword Cultivator: four paths, levels 1-12, and original static artwork. '
                      'Requires BG3 Script Extender.')
LOG_PATTERNS = ('log.*.txt', 'osirislog.*.log', 'thothlog.*.txt')
LOG_NAME_TIME = re.compile(r'^[^.]+\.(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{6})\.(?:txt|log)$')
BACKUP_NAME_TIME = re.compile(r'^backup-(\d{8}-\d{6}-\d{6})$')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def closed():
    tasks = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True, errors='replace').lower()
    if any('"' + p + '"' in tasks for p in ('bg3.exe', 'bg3_dx11.exe', 'glasses.exe')):
        raise SystemExit('Close BG3 and Toolkit normally before changing their source directories.')


def owned(part):
    path = (DATA / part / FOLDER).resolve()
    if not path.is_relative_to(DATA) or path.name != FOLDER:
        raise ValueError('Target is outside the exact project directory: ' + str(path))
    return path


def write_state(state):
    BASE.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix('.pending.json')
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(STATE)


def files(root):
    return {p.relative_to(root).as_posix(): digest(p) for p in sorted(root.rglob('*')) if p.is_file()}


def toolkit_editor_meta_bytes(source_bytes):
    """Use an ASCII description only in the Toolkit's installed module meta."""
    original = ET.fromstring(source_bytes)
    original_description = original.find(".//node[@id='ModuleInfo']/attribute[@id='Description']")
    if original_description is None or '东方剑修' not in original_description.get('value', ''):
        raise ValueError('Toolkit module meta lost its authored Chinese description.')
    authored = original_description.get('value').encode('utf-8')
    if source_bytes.count(authored) != 1:
        raise ValueError('Expected exactly one literal authored description in module meta.')
    converted = source_bytes.replace(authored, EDITOR_DESCRIPTION.encode('ascii'), 1)
    if not converted.isascii():
        raise ValueError('Toolkit module meta still contains non-ASCII text.')
    loaded_description = ET.fromstring(converted).find(".//node[@id='ModuleInfo']/attribute[@id='Description']")
    if loaded_description is None or loaded_description.get('value') != EDITOR_DESCRIPTION:
        raise ValueError('Toolkit module meta does not contain the editor description.')
    return converted


def log_start_time(state):
    """Find this installation's earliest possible Toolkit launch, including old states."""
    raw = state.get('installed_at')
    if raw:
        try:
            value = datetime.fromisoformat(raw)
            return value.astimezone().replace(tzinfo=None) if value.tzinfo else value, 'installed_at'
        except (TypeError, ValueError):
            pass
    match = BACKUP_NAME_TIME.fullmatch(Path(state.get('backup') or '').name)
    if match:
        return datetime.strptime(match.group(1), '%Y%m%d-%H%M%S-%f'), 'backup_directory_name'
    return None, 'unavailable'


def collect_logs(snapshot, state):
    """Copy only logs whose own session timestamp is newer than this install."""
    start, start_source = log_start_time(state)
    logs = snapshot / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    inventory = {}
    for pattern in LOG_PATTERNS:
        candidates = []
        fresh = []
        for path in sorted(TOOLKIT.glob(pattern)):
            stat = path.stat()
            match = LOG_NAME_TIME.fullmatch(path.name)
            name_time = datetime.strptime(match.group(1), '%Y-%m-%dT%H-%M-%S-%f') if match else None
            modified = datetime.fromtimestamp(stat.st_mtime)
            created = datetime.fromtimestamp(stat.st_ctime)
            # An old session filename stays old even if the file was later copied
            # or touched. Fall back to filesystem times only for unknown names.
            if start is None:
                status = 'unverifiable'
            elif name_time is not None:
                status = 'fresh' if name_time >= start else 'stale'
            else:
                status = 'fresh' if created >= start and modified >= start else 'stale'
            item = dict(name=path.name, size=stat.st_size,
                        filename_time=name_time.isoformat() if name_time else None,
                        created_at=created.isoformat(), modified_at=modified.isoformat(),
                        status=status)
            candidates.append(item)
            if status == 'fresh':
                fresh.append((path, item, stat.st_mtime_ns))
        selected = None
        if fresh:
            path, selected, _ = max(fresh, key=lambda entry: entry[2])
            shutil.copy2(path, logs / path.name)
            selected['sha256'] = digest(logs / path.name)
            group_status = 'captured'
        elif not candidates:
            group_status = 'missing'
        elif start is None:
            group_status = 'unverifiable'
        else:
            group_status = 'stale'
        reason = {
            'captured': 'Selected log began during this Toolkit installation.',
            'missing': 'No matching log file exists in the Toolkit directory.',
            'stale': 'Matching logs exist, but none can be attributed to this installation.',
            'unverifiable': 'Installation time is unavailable in the current or legacy state.',
        }[group_status]
        inventory[pattern] = dict(status=group_status, reason=reason,
                                  selected=selected, candidates=candidates)
    return dict(earliest_launch_at=start.isoformat() if start else None,
                time_source=start_source, launch_time_directly_observed=False,
                patterns=inventory)


def install():
    closed()
    if STATE.exists() and json.loads(STATE.read_text(encoding='utf-8'))['active']:
        raise SystemExit('Toolkit environment already active; capture and restore before another install.')
    if not (SOURCE / 'Editor/Mods' / FOLDER).is_dir():
        raise SystemExit('Generate the real Toolkit Editor source tables first.')
    for part in ('Mods', 'Projects'):
        if not (SOURCE / part / FOLDER / 'meta.lsx').is_file():
            raise SystemExit('Missing project metadata: ' + part)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = BASE / ('backup-' + stamp)
    records = []
    for part in PARTS:
        target = owned(part)
        record = dict(part=part, path=str(target), existed=target.exists())
        if target.exists():
            shutil.copytree(target, backup / part / FOLDER)
            record['original_files'] = files(target)
        records.append(record)
    state = dict(active=True, installed_at=datetime.now().isoformat(), backup=str(backup), directories=records)
    # Recovery record exists before the first live write.
    write_state(state)
    for record in records:
        origin = SOURCE / record['part'] / FOLDER
        if origin.is_dir():
            shutil.copytree(origin, owned(record['part']), dirs_exist_ok=True)
            record['installed_files'] = files(origin)
    # Toolkit Project Settings corrupted the authored Chinese description even
    # with a UTF-8 BOM or numeric XML references. Keep the source/game PAK's
    # Chinese text, but give only the editor's installed copy an ASCII fallback.
    toolkit_meta = owned('Mods') / 'meta.lsx'
    toolkit_meta.write_bytes(toolkit_editor_meta_bytes(toolkit_meta.read_bytes()))
    state['editor_meta_fallback'] = dict(path=str(toolkit_meta.relative_to(DATA)),
                                         description=EDITOR_DESCRIPTION,
                                         sha256=digest(toolkit_meta))
    for record in records:
        if record['part'] == 'Mods':
            record['installed_files'] = files(owned('Mods'))
    divine = REPO / 'build/tools/LSLib-1.20.4/Packed/Tools/Divine.exe'
    # The native resource manager reads compiled banks and GUI metadata. Keep
    # editable LSX in the repository, but install the same binary format as Toolkit.
    converted = []
    for part in ('Mods', 'Public'):
        path = owned(part)
        if not path.exists():
            continue
        for resource in sorted(path.rglob('*.lsx')):
            relative=resource.relative_to(path)
            is_content_bank=part=='Public' and relative.parts[0]=='Content'
            if resource.name not in ('_merged.lsx', 'metadata.lsx') and not is_content_bank:
                continue
            destination = resource.with_suffix('.lsf')
            subprocess.run([str(divine), '-g', 'bg3', '-a', 'convert-resource', '-s', str(resource),
                            '-d', str(destination)], check=True, capture_output=True, text=True)
            converted.append(dict(path=str(destination.relative_to(DATA)), sha256=digest(destination)))
    state['compiled_resources'] = converted
    write_state(state)
    print('Toolkit source installed: ' + FOLDER)
    print('Recovery state: ' + str(STATE))


def capture():
    if not STATE.exists():
        raise SystemExit('No Toolkit installation record.')
    state = json.loads(STATE.read_text(encoding='utf-8'))
    if not state['active']:
        raise SystemExit('Toolkit source is already restored.')
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    snapshot = BASE / ('capture-' + stamp)
    captured = {}
    for part in PARTS:
        path = owned(part)
        if path.exists():
            destination = snapshot / 'Data' / part / FOLDER
            shutil.copytree(path, destination)
            captured[part] = files(destination)
    log_evidence = collect_logs(snapshot, state)
    report = dict(captured_at=datetime.now().isoformat(), files=captured,
                  log_evidence=log_evidence,
                  evidence_boundary='File snapshot only; this does not prove editor gameplay or UI validation.')
    (snapshot / 'capture.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Immutable Toolkit evidence: ' + str(snapshot))


def restore():
    closed()
    state = json.loads(STATE.read_text(encoding='utf-8'))
    if not state['active']:
        raise SystemExit('Toolkit environment already restored.')
    backup = Path(state['backup']).resolve()
    if not backup.is_relative_to(BASE.resolve()):
        raise ValueError('Backup is outside this task directory.')
    retired = BASE / ('retired-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    # Move only the exact UUID directories aside; retain every editor-produced file.
    for record in state['directories']:
        target = owned(record['part'])
        destination = (retired / record['part'] / FOLDER).resolve()
        if not destination.is_relative_to(BASE.resolve()):
            raise ValueError('Retirement path is outside this task directory.')
        if target.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), str(destination))
        if record['existed']:
            shutil.copytree(backup / record['part'] / FOLDER, target)
            if files(target) != record['original_files']:
                raise RuntimeError('Original project files did not restore: ' + record['part'])
    state.update(active=False, restored_at=datetime.now().isoformat(), retired=str(retired))
    write_state(state)
    print('Original Toolkit directories restored; test outputs retained at ' + str(retired))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('install', 'capture', 'restore'))
    action = parser.parse_args().action
    {'install': install, 'capture': capture, 'restore': restore}[action]()
