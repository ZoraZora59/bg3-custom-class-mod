"""Prepare/apply/restore one temporary ESC client candidate, without publishing.

Only the UUID-named installed PAK, its existing modsettings row, temporary SE
settings, and the dedicated ESC_Test_01 save directories are owned here. Other
PAKs, load-order entries and campaign saves are never written. A candidate may
have a lower version than the published package: this is a reversible test.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from xml.sax.saxutils import escape


REPO = Path(__file__).resolve().parents[1]
BUILD = REPO / 'build/sword-cultivator'
BASE = BUILD / 'client-candidate'
LOCAL = Path(os.environ['LOCALAPPDATA']) / "Larian Studios/Baldur's Gate 3"
GAME = Path('E:/SteamLibrary/steamapps/common/Baldurs Gate 3')
UUID = '6560ea02-fe1e-5fdb-8631-b41a2e53af90'
FOLDER = 'EasternSwordCultivator_' + UUID
FIELDS = ('Folder', 'MD5', 'Name', 'PublishHandle', 'UUID', 'Version64')
PACKAGE = LOCAL / 'Mods' / (FOLDER + '.pak')
SETTINGS = LOCAL / 'PlayerProfiles/Public/modsettings.lsx'
SESETTINGS = GAME / 'bin/ScriptExtenderSettings.json'
DWRITE = GAME / 'bin/DWrite.dll'
SAVES = LOCAL / 'PlayerProfiles/Public/Savegames/Story'
DIVINE = REPO / 'build/tools/LSLib-1.20.4/Packed/Tools/Divine.exe'
TEST_NAME = re.compile(r'^ESC_Test_01(?:-|$)')
SHA = re.compile(r'^[0-9a-fA-F]{64}$')
PROCESS_NAMES = {'bg3.exe', 'bg3_dx11.exe', 'glasses.exe', 'bg3modmanager.exe'}


def fail(message):
    raise RuntimeError(message)


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def file_sha(path):
    return digest(path) if Path(path).is_file() else None


def inside(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    if path == root or not path.is_relative_to(root):
        fail('Path is outside its owned directory: ' + str(path))
    return path


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                     prefix=path.name + '.', suffix='.tmp', delete=False) as stream:
        pending = Path(stream.name)
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    try:
        os.replace(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def now():
    return datetime.now(timezone.utc).isoformat()


def check_closed():
    raw = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'])
    encoding = 'mbcs' if os.name == 'nt' else 'utf-8'
    rows = csv.reader(raw.decode(encoding, errors='replace').splitlines())
    running = sorted({row[0].casefold() for row in rows if row and row[0].casefold() in PROCESS_NAMES})
    if running:
        fail('Close BG3, Toolkit and BG3ModManager normally before this operation: ' + ', '.join(running))


def ready():
    check_closed()
    for name in ('toolkit-environment', 'test-environment'):
        state = BUILD / name / 'state.json'
        if state.is_file() and read_json(state).get('active'):
            fail('Restore the active ' + name + ' before candidate client testing.')
    duplicates = [p for p in PACKAGE.parent.glob('*.pak')
                  if p.resolve() != PACKAGE.resolve() and
                  ('easternswordcultivator' in p.name.casefold() or UUID in p.name.casefold())]
    if duplicates:
        fail('Another ESC PAK exists; refusing a same-UUID deployment.')


def attrs(node):
    values = {}
    for field in FIELDS:
        items = node.findall("attribute[@id='" + field + "']")
        if len(items) != 1 or items[0].get('value') is None:
            fail('Missing or duplicated module metadata field: ' + field)
        values[field] = items[0].get('value')
    if values['UUID'].casefold() != UUID or values['Folder'] != FOLDER or values['Name'] != 'EasternSwordCultivator':
        fail('Package/settings identity differs from the exact ESC module.')
    if not re.fullmatch(r'\d+', values['Version64']) or not 0 < int(values['Version64']) < 2 ** 63:
        fail('Version64 must be a positive signed Int64.')
    if values['PublishHandle'] != '6417135':
        fail('Expected the existing ESC PublishHandle 6417135.')
    return values


def version(value):
    packed = int(value)
    return '{}.{}.{}.{}'.format((packed >> 55) & 0x7f, (packed >> 47) & 0xff,
                               (packed >> 31) & 0xffff, packed & 0x7fffffff)


def package_metadata(package, destination):
    if not DIVINE.is_file():
        fail('Missing existing LSLib Divine.exe: ' + str(DIVINE))
    subprocess.run([str(DIVINE), '-g', 'bg3', '-a', 'extract-package', '-s', str(package),
                    '-d', str(destination)], check=True, capture_output=True)
    meta = Path(destination) / 'Mods' / FOLDER / 'meta.lsx'
    nodes = ET.parse(meta).getroot().findall(".//node[@id='ModuleInfo']")
    if len(nodes) != 1:
        fail('Expected exactly one ModuleInfo in extracted PAK.')
    return attrs(nodes[0])


def settings_metadata(data):
    rows = []
    for node in ET.fromstring(data).findall(".//node[@id='ModuleShortDesc']"):
        if any(a.get('id') == 'UUID' and (a.get('value') or '').casefold() == UUID
               for a in node.findall('attribute')):
            rows.append(node)
    if len(rows) != 1:
        fail('Expected exactly one enabled ESC modsettings row; no load-order reconstruction is allowed.')
    return attrs(rows[0])


def candidate_settings(data, metadata):
    """Patch only six values inside the existing row, preserving all other bytes."""
    settings_metadata(data)
    bom = data.startswith(b'\xef\xbb\xbf')
    text = data.decode('utf-8-sig')
    matches = []
    for match in re.finditer(r'<node\b[^>]*\bid\s*=\s*[\"\']ModuleShortDesc[\"\'][^>]*>[\s\S]*?</node>', text):
        row = ET.fromstring(match.group())
        if any(a.get('id') == 'UUID' and (a.get('value') or '').casefold() == UUID
               for a in row.findall('attribute')):
            matches.append(match)
    if len(matches) != 1:
        fail('Cannot locate the exact existing ESC row for a byte-preserving patch.')
    match = matches[0]
    block = match.group()
    seen = set()
    def replace_attribute(element):
        fragment = element.group()
        field = ET.fromstring(fragment).get('id')
        if field not in FIELDS:
            return fragment
        if field in seen:
            fail('Duplicated ESC row metadata attribute: ' + field)
        seen.add(field)
        value = escape(metadata[field], {'"': '&quot;', "'": '&apos;'})
        return re.sub(r'(\bvalue\s*=\s*)([\"\'])(.*?)(\2)',
                      lambda m: m.group(1) + m.group(2) + value + m.group(4), fragment, count=1)
    block = re.sub(r'<attribute\b[^>]*?/\s*>', replace_attribute, block)
    if seen != set(FIELDS):
        fail('Could not patch every ESC metadata value.')
    prepared = ((b'\xef\xbb\xbf' if bom else b'') +
                (text[:match.start()] + block + text[match.end():]).encode('utf-8'))
    if settings_metadata(prepared) != metadata:
        fail('Prepared settings metadata verification failed.')
    return prepared


def test_directories():
    if not SAVES.is_dir():
        fail('The dedicated ESC_Test_01 Story save location does not exist.')
    return sorted(inside(p, SAVES) for p in SAVES.iterdir() if p.is_dir() and TEST_NAME.match(p.name))


def tree_files(root):
    root = Path(root)
    if not root.exists():
        return {}
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or (getattr(path.stat(), 'st_file_attributes', 0) & 0x400):
            fail('Reparse points are not supported in a backup scope: ' + str(path))
        inside(path, root)
        if path.is_file():
            result[path.relative_to(root).as_posix()] = digest(path)
    return result


def test_snapshot():
    return {p.name: tree_files(p) for p in test_directories()}


def unrelated_snapshot():
    saves_root = SAVES.parent
    excluded = test_directories()
    files = {}
    if saves_root.exists():
        for path in sorted(saves_root.rglob('*')):
            inside(path, saves_root)
            if path.is_file() and not any(path.is_relative_to(p) for p in excluded):
                files[path.relative_to(saves_root).as_posix()] = digest(path)
    return {'paks': {p.name: digest(p) for p in sorted(PACKAGE.parent.glob('*.pak'))
                     if p.resolve() != PACKAGE.resolve()},
            'campaign_files': files, 'dwrite': file_sha(DWRITE)}


def assert_equal_snapshot(expected, actual, label):
    if expected != actual:
        fail(label + ' changed; refusing to overwrite the prepared snapshot.')


def save_manifest(path, manifest):
    write_json(path, manifest)
    write_json(BASE / 'state.json', {'schema': 1, 'manifest': str(path),
                                    'active': manifest['status'] not in ('prepared', 'restored'),
                                    'status': manifest['status']})


def prepare(candidate, expected_sha, expected_version=None):
    ready()
    pointer = BASE / 'state.json'
    if pointer.is_file() and read_json(pointer).get('active'):
        fail('A candidate environment is active; restore its recorded manifest first.')
    candidate = Path(candidate).resolve(strict=True)
    if not SHA.fullmatch(expected_sha) or digest(candidate) != expected_sha.lower():
        fail('Candidate SHA256 differs from the explicitly expected SHA.')
    if candidate.suffix.casefold() != '.pak' or candidate == PACKAGE.resolve():
        fail('Select a separate frozen candidate PAK.')
    if not PACKAGE.is_file() or not SETTINGS.is_file():
        fail('The official installed ESC PAK and existing modsettings are required.')
    before_files = {'pak': file_sha(PACKAGE), 'settings': file_sha(SETTINGS), 'se': file_sha(SESETTINGS)}
    before_tests = test_snapshot()
    if not before_tests:
        fail('No dedicated ESC_Test_01 save directories exist to back up.')
    before_other = unrelated_snapshot()
    run = inside(BASE / ('run-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')), BASE)
    run.mkdir(parents=True)
    frozen = run / 'candidate.pak'
    shutil.copy2(candidate, frozen)
    if digest(frozen) != expected_sha.lower():
        fail('Frozen candidate copy SHA256 verification failed.')
    records = {}
    for key, target in (('pak', PACKAGE), ('settings', SETTINGS), ('se', SESETTINGS)):
        backup = run / (key + '.before')
        existed = target.is_file()
        if existed:
            shutil.copy2(target, backup)
            if digest(backup) != before_files[key]:
                fail('Original-file backup verification failed: ' + key)
        records[key] = {'target': str(target.resolve()), 'backup': str(backup),
                        'existed': existed, 'sha256': before_files[key]}
    for directory in test_directories():
        destination = run / 'test-saves.before' / directory.name
        shutil.copytree(directory, destination)
        assert_equal_snapshot(before_tests[directory.name], tree_files(destination), 'Test-save backup')
    official_meta = package_metadata(run / 'pak.before', run / 'official-readback')
    candidate_meta = package_metadata(frozen, run / 'candidate-readback')
    if settings_metadata((run / 'settings.before').read_bytes()) != official_meta:
        fail('Installed official PAK metadata differs from its enabled modsettings row.')
    if expected_version and version(candidate_meta['Version64']) != expected_version:
        fail('Candidate package metadata differs from the expected version.')
    prepared_settings = run / 'settings.candidate'
    prepared_settings.write_bytes(candidate_settings((run / 'settings.before').read_bytes(), candidate_meta))
    se = read_json(run / 'se.before') if records['se']['existed'] else {}
    if not isinstance(se, dict):
        fail('ScriptExtenderSettings must be a JSON object.')
    se.update(EnableLogging=True, LogRuntime=True, LogFailedCompile=True, EnableLuaDebugger=True,
              CreateConsole=False, LogDirectory=str(run / 'client-logs'))
    prepared_se = run / 'se.candidate'
    write_json(prepared_se, se)
    assert_equal_snapshot(before_files, {'pak': file_sha(PACKAGE), 'settings': file_sha(SETTINGS),
                                        'se': file_sha(SESETTINGS)}, 'Installed files during Prepare')
    assert_equal_snapshot(before_tests, test_snapshot(), 'Dedicated saves during Prepare')
    assert_equal_snapshot(before_other, unrelated_snapshot(), 'Unrelated files during Prepare')
    manifest = {'schema': 1, 'operation': 'esc-temporary-client-candidate', 'status': 'prepared',
                'created_at': now(), 'module_uuid': UUID, 'records': records,
                'candidate': {'path': str(frozen), 'sha256': expected_sha.lower(), 'metadata': candidate_meta,
                              'version': version(candidate_meta['Version64'])},
                'official_metadata': official_meta, 'official_version': version(official_meta['Version64']),
                'prepared': {'settings': {'path': str(prepared_settings), 'sha256': digest(prepared_settings)},
                             'se': {'path': str(prepared_se), 'sha256': digest(prepared_se)}},
                'test_saves': before_tests, 'unrelated': before_other,
                'scope': 'Temporary client diagnostic only. No publication or automatic visual/gameplay pass. '
                         'Only the exact UUID PAK, six values in its existing settings row, SE settings, and '
                         'ESC_Test_01 dedicated saves are owned. Other PAKs/order rows/campaign saves are never written.'}
    path = run / 'manifest.json'
    save_manifest(path, manifest)
    return path, manifest


def load_manifest(path):
    path = inside(Path(path).resolve(strict=True), BASE)
    if path.name != 'manifest.json' or path.parent.parent != BASE.resolve() or not path.parent.name.startswith('run-'):
        fail('Use an exact manifest produced by this candidate helper.')
    manifest = read_json(path)
    if manifest.get('schema') != 1 or manifest.get('operation') != 'esc-temporary-client-candidate' or manifest.get('module_uuid') != UUID:
        fail('Invalid candidate manifest identity.')
    for key, target in (('pak', PACKAGE), ('settings', SETTINGS), ('se', SESETTINGS)):
        if Path(manifest['records'][key]['target']).resolve() != target.resolve():
            fail('Manifest target differs from the exact owned path: ' + key)
        inside(manifest['records'][key]['backup'], path.parent)
    if Path(manifest['candidate']['path']).resolve() != path.parent / 'candidate.pak':
        fail('Manifest frozen candidate path is invalid.')
    for key in ('settings', 'se'):
        if Path(manifest['prepared'][key]['path']).resolve() != path.parent / (key + '.candidate'):
            fail('Manifest prepared configuration path is invalid.')
    for name in manifest['test_saves']:
        if Path(name).name != name or not TEST_NAME.match(name):
            fail('Manifest contains a non-dedicated save path.')
        inside(path.parent / 'test-saves.before' / name, path.parent)
    return path, manifest


def verify_backups(path, manifest, include_candidate=True):
    for key, record in manifest['records'].items():
        if record['existed'] and file_sha(record['backup']) != record['sha256']:
            fail('Original backup SHA256 differs: ' + key)
    for name, files in manifest['test_saves'].items():
        backup = path.parent / 'test-saves.before' / name
        if not backup.is_dir():
            fail('Dedicated save backup directory is missing.')
        assert_equal_snapshot(files, tree_files(backup), 'Dedicated save backup')
    if include_candidate:
        if digest(manifest['candidate']['path']) != manifest['candidate']['sha256']:
            fail('Frozen candidate PAK changed.')
        for key, record in manifest['prepared'].items():
            if digest(record['path']) != record['sha256']:
                fail('Prepared configuration changed: ' + key)
        if settings_metadata(Path(manifest['prepared']['settings']['path']).read_bytes()) != manifest['candidate']['metadata']:
            fail('Prepared candidate metadata changed.')


def replace_known(source, target, expected_current, expected_source):
    target = Path(target)
    if file_sha(target) != expected_current or digest(source) != expected_source:
        fail('Target/source SHA changed before replacement: ' + str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('wb', dir=target.parent, prefix=target.name + '.esc-', suffix='.tmp', delete=False) as stream:
        stage = Path(stream.name)
    try:
        shutil.copy2(source, stage)
        if digest(stage) != expected_source or file_sha(target) != expected_current:
            fail('Staged copy or current target changed.')
        os.replace(stage, target)
    finally:
        stage.unlink(missing_ok=True)
    if digest(target) != expected_source:
        fail('Replacement readback SHA256 failed.')


def restore_files(manifest):
    allowed = {'pak': manifest['candidate']['sha256'],
               'settings': manifest['prepared']['settings']['sha256'], 'se': manifest['prepared']['se']['sha256']}
    # Check every owned live file before restoring any; never overwrite unknown edits.
    for key, record in manifest['records'].items():
        if file_sha(record['target']) not in (record['sha256'], allowed[key]):
            fail('Refusing restore of an unknown live file SHA: ' + key)
    for key, record in manifest['records'].items():
        current = file_sha(record['target'])
        if current == record['sha256']:
            continue
        if record['existed']:
            replace_known(record['backup'], record['target'], current, record['sha256'])
        else:
            # Only the exact newly created, hash-owned SE file can reach this branch.
            if key != 'se' or current != allowed[key]:
                fail('Unexpected absent-original file in restore.')
            Path(record['target']).unlink()


def apply(path):
    ready()
    path, manifest = load_manifest(path)
    if manifest['status'] != 'prepared':
        fail('Apply requires a newly prepared manifest.')
    verify_backups(path, manifest)
    for key, record in manifest['records'].items():
        if file_sha(record['target']) != record['sha256']:
            fail('Installed file changed after Prepare: ' + key)
    assert_equal_snapshot(manifest['test_saves'], test_snapshot(), 'Dedicated saves after Prepare')
    assert_equal_snapshot(manifest['unrelated'], unrelated_snapshot(), 'Unrelated files after Prepare')
    pointer = BASE / 'state.json'
    if pointer.is_file() and read_json(pointer).get('active'):
        fail('Another candidate environment is active.')
    manifest.update(status='applying', apply_started_at=now())
    save_manifest(path, manifest)  # Recovery ownership recorded before any live write.
    try:
        replace_known(manifest['candidate']['path'], PACKAGE, manifest['records']['pak']['sha256'], manifest['candidate']['sha256'])
        for key, target in (('settings', SETTINGS), ('se', SESETTINGS)):
            replace_known(manifest['prepared'][key]['path'], target, manifest['records'][key]['sha256'], manifest['prepared'][key]['sha256'])
        assert_equal_snapshot(manifest['test_saves'], test_snapshot(), 'Dedicated saves during Apply')
        assert_equal_snapshot(manifest['unrelated'], unrelated_snapshot(), 'Unrelated files during Apply')
        manifest.update(status='applied', applied_at=now())
        save_manifest(path, manifest)
    except BaseException as exc:
        manifest['apply_error'] = str(exc)
        try:
            restore_files(manifest)
            manifest['status'] = 'prepared'
        except BaseException as rollback:
            manifest.update(status='apply-recovery-required', recovery_error=str(rollback))
        save_manifest(path, manifest)
        raise
    return path, manifest


def restore(path):
    ready()
    path, manifest = load_manifest(path)
    if manifest['status'] == 'restored':
        fail('This candidate environment is already restored.')
    if manifest['status'] == 'prepared':
        fail('This prepared candidate has not been applied.')
    verify_backups(path, manifest, include_candidate=False)
    before_other = unrelated_snapshot()
    # Preflight all known-hash file checks before touching files or dedicated saves.
    allowed = {'pak': manifest['candidate']['sha256'], 'settings': manifest['prepared']['settings']['sha256'],
               'se': manifest['prepared']['se']['sha256']}
    for key, record in manifest['records'].items():
        if file_sha(record['target']) not in (record['sha256'], allowed[key]):
            fail('Refusing restore of an unknown live file SHA: ' + key)
    current_tests = test_directories()
    retired = inside(path.parent / ('test-saves.retired-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')), path.parent)
    manifest.update(status='restoring', restore_started_at=now(), retired_test_saves=str(retired))
    manifest.setdefault('retired_test_saves_history', []).append(str(retired))
    save_manifest(path, manifest)
    try:
        restore_files(manifest)
        retired.mkdir()
        for source in current_tests:
            source = inside(source, SAVES)
            if not TEST_NAME.match(source.name):
                fail('Refusing to retire a non-dedicated save directory.')
            destination = inside(retired / source.name, retired)
            shutil.move(str(source), str(destination))
        for name in manifest['test_saves']:
            destination = inside(SAVES / name, SAVES)
            if destination.exists():
                fail('A dedicated save path reappeared during Restore.')
            shutil.copytree(path.parent / 'test-saves.before' / name, destination)
        assert_equal_snapshot(manifest['test_saves'], test_snapshot(), 'Restored dedicated saves')
        assert_equal_snapshot(before_other, unrelated_snapshot(), 'Unrelated files during Restore')
        manifest.update(status='restored', restored_at=now(),
                        unrelated_unchanged_by_restore=True,
                        unrelated_matches_prepare=before_other == manifest['unrelated'])
        save_manifest(path, manifest)
    except BaseException as exc:
        manifest.update(status='restore-recovery-required', restore_error=str(exc))
        save_manifest(path, manifest)
        raise
    return path, manifest


def status(path=None):
    if path is None:
        pointer = BASE / 'state.json'
        if not pointer.is_file():
            return {'status': 'no-candidate-environment'}
        path = read_json(pointer)['manifest']
    path, manifest = load_manifest(path)
    return summary(path, manifest) | {'live_pak_sha256': file_sha(PACKAGE),
                                     'live_settings_sha256': file_sha(SETTINGS),
                                     'live_se_sha256': file_sha(SESETTINGS)}


def summary(path, manifest):
    return {'status': manifest['status'], 'manifest': str(path),
            'official_version': manifest['official_version'], 'candidate_version': manifest['candidate']['version'],
            'candidate_sha256': manifest['candidate']['sha256'], 'test_save_directories': len(manifest['test_saves']),
            'other_paks': len(manifest['unrelated']['paks']),
            'publication': 'none', 'visual_gameplay_result': 'not-determined-by-installer'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    prepare_parser = commands.add_parser('prepare', help='Back up and verify; writes only inside this repository build.')
    prepare_parser.add_argument('--candidate', type=Path, required=True)
    prepare_parser.add_argument('--expected-sha', required=True)
    prepare_parser.add_argument('--expected-version')
    for action in ('apply', 'restore', 'status'):
        command = commands.add_parser(action)
        command.add_argument('--manifest', type=Path, required=action != 'status')
    args = parser.parse_args()
    try:
        if args.action == 'status':
            result = status(args.manifest)
        else:
            path, manifest = (prepare(args.candidate, args.expected_sha, args.expected_version)
                              if args.action == 'prepare' else globals()[args.action](args.manifest))
            result = summary(path, manifest)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (RuntimeError, OSError, ValueError, KeyError, ET.ParseError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
