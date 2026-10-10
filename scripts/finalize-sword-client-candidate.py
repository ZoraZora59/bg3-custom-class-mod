"""Adopt an exact tested client PAK while retiring its temporary environment.

Prepare writes only a reviewed, hash-bound transaction under build. Apply never
writes the installed PAK or modsettings: it restores only the original SE JSON
and ESC_Test_01 directories. The original candidate manifest stays byte-exact;
an independent receipt records adoption. Rollback undoes this cleanup, retaining
the same PAK, and is also used automatically after a recoverable Apply failure.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
from datetime import datetime, timezone


SCRIPT = Path(__file__).resolve()
HELPER = SCRIPT.with_name('sword-client-candidate.py')
SPEC = importlib.util.spec_from_file_location('esc_candidate_for_finalization', HELPER)
env = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(env)
OPERATION = 'esc-client-candidate-finalize'


def base():
    return env.BUILD / 'client-candidate-finalize'


def raw_hash(value):
    return hashlib.sha256(value).hexdigest()


def ordinary(path):
    path = Path(path)
    if path.is_symlink() or (path.exists() and getattr(path.stat(), 'st_file_attributes', 0) & 0x400):
        env.fail('Reparse points are not supported: ' + str(path))
    return path


def save_path(name, root=None):
    if not isinstance(name, str) or '/' in name or '\\' in name or not env.TEST_NAME.match(name):
        env.fail('Only exact dedicated ESC_Test_01 directory names are allowed.')
    root = ordinary(root if root is not None else env.SAVES)
    path = ordinary(root / name)
    env.inside(path, root)
    return path


def test_snapshot():
    ordinary(env.SAVES)
    if not env.SAVES.is_dir():
        env.fail('Dedicated save root is missing.')
    return {p.name: env.tree_files(save_path(p.name)) for p in sorted(env.SAVES.iterdir())
            if env.TEST_NAME.match(p.name) and (p.is_dir() or p.is_symlink())}


def compare(expected, actual, label):
    env.assert_equal_snapshot(expected, actual, label)


def copy_file(source, destination):
    ordinary(source)
    destination = Path(destination)
    if destination.exists():
        env.fail('Backup already exists: ' + str(destination))
    shutil.copy2(source, destination)
    compare(env.digest(source), env.digest(destination), 'Copied file')


def copy_saves(source_root, destination_root, expected):
    destination_root.mkdir()
    for name, files in expected.items():
        source, target = save_path(name, source_root), save_path(name, destination_root)
        compare(files, env.tree_files(source), 'Save source')
        shutil.copytree(source, target)
        compare(files, env.tree_files(target), 'Save backup')


def preserved(manifest):
    return {'pak': env.file_sha(env.PACKAGE), 'settings': env.file_sha(env.SETTINGS),
            'source_manifest': env.file_sha(manifest)}


def source_inputs():
    return {str(p): env.digest(p) for p in (SCRIPT, HELPER)}


def prepare(manifest_path, expected_pak_sha):
    env.ready()
    manifest_path, original = env.load_manifest(manifest_path)
    pointer = env.BASE / 'state.json'
    state_bytes = pointer.read_bytes()
    state = json.loads(state_bytes)
    if (original['status'] != 'applied' or state.get('status') != 'applied'
            or state.get('active') is not True or Path(state.get('manifest', '')).resolve() != manifest_path):
        env.fail('Finalize requires the currently active applied candidate manifest.')
    if not env.SHA.fullmatch(expected_pak_sha) or original['candidate']['sha256'] != expected_pak_sha.lower():
        env.fail('Candidate differs from the explicitly expected tested PAK SHA.')
    env.verify_backups(manifest_path, original)
    wanted = {'pak': original['candidate']['sha256'],
              'settings': original['prepared']['settings']['sha256'],
              'se': original['prepared']['se']['sha256']}
    for key, record in original['records'].items():
        ordinary(record['target'])
        compare(wanted[key], env.file_sha(record['target']), 'Exact live candidate ' + key)
    compare(original['candidate']['metadata'], env.settings_metadata(env.SETTINGS.read_bytes()), 'Enabled metadata')
    tests = test_snapshot()
    unrelated = env.unrelated_snapshot()
    # Do not silently bless another PAK/extender replacement made during testing.
    for key in ('paks', 'dwrite'):
        compare(original['unrelated'][key], unrelated[key], 'Original unrelated ' + key)
    keep = preserved(manifest_path)
    root = env.inside(base() / ('run-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')), base())
    root.mkdir(parents=True)
    for source, name in ((env.PACKAGE, 'preserved.pak'), (env.SETTINGS, 'preserved.settings'),
                         (env.SESETTINGS, 'se.before'), (manifest_path, 'candidate-manifest.before.json'),
                         (pointer, 'candidate-state.before.json')):
        copy_file(source, root / name)
    se = original['records']['se']
    if se['existed']:
        copy_file(se['backup'], root / 'se.restore')
    copy_saves(env.SAVES, root / 'test-saves.before', tests)
    copy_saves(manifest_path.parent / 'test-saves.before', root / 'test-saves.restore', original['test_saves'])
    path = root / 'receipt.json'
    adopted_state = {'schema': 1, 'manifest': str(manifest_path), 'active': False,
                     'status': 'adopted', 'finalization_receipt': str(path)}
    env.write_json(root / 'candidate-state.adopted.json', adopted_state)
    receipt = {'schema': 1, 'operation': OPERATION, 'status': 'prepared', 'created_at': env.now(),
               'source_manifest': str(manifest_path), 'preserved': keep,
               'expected_pak_sha256': expected_pak_sha.lower(), 'source_inputs': source_inputs(),
               'state_before_sha256': raw_hash(state_bytes), 'adopted_state': adopted_state,
               'adopted_state_sha256': env.digest(root / 'candidate-state.adopted.json'),
               'se_before_sha256': wanted['se'], 'se_restore_sha256': se['sha256'],
               'se_restore_existed': se['existed'], 'test_saves_before': tests,
               'test_saves_restore': original['test_saves'], 'unrelated': unrelated,
               'retire_started': [], 'restore_started': [],
               'boundary': 'Exact tested PAK and enabled settings retained; original candidate manifest unchanged. '
                           'Only SE JSON and dedicated ESC_Test_01 saves restored. No publication or gameplay claim.'}
    receipt['backup_files'] = env.tree_files(root)
    compare(keep, preserved(manifest_path), 'Preserved files during Prepare')
    compare(wanted['se'], env.file_sha(env.SESETTINGS), 'SE during Prepare')
    compare(tests, test_snapshot(), 'Dedicated saves during Prepare')
    compare(unrelated, env.unrelated_snapshot(), 'Unrelated files during Prepare')
    compare(raw_hash(state_bytes), env.file_sha(pointer), 'Candidate state during Prepare')
    env.write_json(path, receipt)
    return path, receipt


def load_receipt(path):
    path = Path(path).resolve(strict=True)
    if path.name != 'receipt.json' or path.parent.parent != base().resolve() or not path.parent.name.startswith('run-'):
        env.fail('Use an exact finalization receipt under its owned directory.')
    ordinary(path)
    receipt = env.read_json(path)
    if receipt.get('schema') != 1 or receipt.get('operation') != OPERATION:
        env.fail('Invalid finalization receipt identity.')
    manifest_path, original = env.load_manifest(receipt['source_manifest'])
    compare(receipt['preserved']['source_manifest'], env.file_sha(manifest_path), 'Original candidate manifest')
    compare(receipt['expected_pak_sha256'], original['candidate']['sha256'], 'Expected package identity')
    for name in (*receipt['test_saves_before'], *receipt['test_saves_restore'],
                 *receipt['retire_started'], *receipt['restore_started']):
        save_path(name)
    compare(receipt['test_saves_restore'], original['test_saves'], 'Original dedicated save identity')
    return path, receipt, manifest_path, original


def verify_receipt(path, receipt, manifest_path, original, active=True):
    env.ready()
    compare(receipt['source_inputs'], source_inputs(), 'Finalizer code')
    env.verify_backups(manifest_path, original)
    compare(receipt['preserved'], preserved(manifest_path), 'Preserved PAK/settings/manifest')
    for relative, digest in receipt['backup_files'].items():
        p = env.inside(path.parent / relative, path.parent)
        ordinary(p)
        compare(digest, env.file_sha(p), 'Finalization backup')
    for subdir, expected in (('test-saves.before', receipt['test_saves_before']),
                             ('test-saves.restore', receipt['test_saves_restore'])):
        for name, files in expected.items():
            compare(files, env.tree_files(save_path(name, path.parent / subdir)), 'Finalization save backup')
    compare(receipt['unrelated'], env.unrelated_snapshot(), 'Unrelated files')
    pointer = env.BASE / 'state.json'
    if active:
        compare(receipt['state_before_sha256'], env.file_sha(pointer), 'Active candidate state')
        compare(receipt['se_before_sha256'], env.file_sha(env.SESETTINGS), 'Temporary SE')
        compare(receipt['test_saves_before'], test_snapshot(), 'Dedicated saves after Prepare')
    else:
        if env.file_sha(pointer) not in (receipt['state_before_sha256'], receipt['adopted_state_sha256']):
            env.fail('Unknown candidate state; refusing rollback.')


def move_save(source, destination):
    source, destination = ordinary(source), ordinary(destination)
    allowed = (env.SAVES.resolve(), base().resolve())
    for path in (source, destination):
        resolved = path.resolve()
        if not any(resolved != root and resolved.is_relative_to(root) for root in allowed):
            env.fail('Save move leaves the explicit owned roots.')
    if destination.exists():
        env.fail('Save move destination exists: ' + str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.rename(destination)


def rollback(path, receipt=None):
    path, loaded, manifest_path, original = load_receipt(path)
    receipt = receipt if receipt is not None else loaded
    if receipt['status'] not in ('applying', 'finalized', 'recovery-required', 'rolling-back'):
        env.fail('Rollback requires an applied or interrupted finalization.')
    verify_receipt(path, receipt, manifest_path, original, active=False)
    if env.file_sha(env.SESETTINGS) not in (receipt['se_before_sha256'], receipt['se_restore_sha256']):
        env.fail('Unknown SE file; refusing rollback.')
    current_saves = test_snapshot()
    if receipt['status'] == 'finalized':
        compare(receipt['test_saves_restore'], current_saves, 'Restored saves before rollback')
    elif set(current_saves) - (set(receipt['test_saves_before']) | set(receipt['restore_started'])):
        env.fail('Unknown dedicated save directory; refusing rollback.')
    # During recovery, only a directory whose restore was journaled may contain
    # an incomplete copy. Check untouched progress before moving anything.
    for name, files in current_saves.items():
        if name not in receipt['restore_started']:
            compare(receipt['test_saves_before'][name], files, 'Untouched saves before rollback')
    # Every attempted restored directory is retained, including an incomplete
    # copy after an I/O failure. Never recursively delete a save directory.
    archive_name = receipt.get('rollback_archive_name')
    if archive_name is None:
        archive_name = 'rollback-restored-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    if Path(archive_name).name != archive_name or not archive_name.startswith('rollback-restored-'):
        env.fail('Invalid rollback archive identity.')
    archived = env.inside(path.parent / archive_name, path.parent)
    receipt.update(status='rolling-back', rollback_archive_name=archive_name)
    env.write_json(path, receipt)
    for name in receipt['restore_started']:
        target = save_path(name)
        if target.exists():
            retired = save_path(name, path.parent / 'test-saves.retired')
            if (name in receipt['test_saves_before'] and not retired.exists()
                    and env.tree_files(target) == receipt['test_saves_before'][name]):
                continue  # An earlier interrupted rollback already restored this directory.
            move_save(target, save_path(name, archived))
    for name, files in receipt['test_saves_before'].items():
        retired = save_path(name, path.parent / 'test-saves.retired')
        target = save_path(name)
        if retired.exists():
            compare(files, env.tree_files(retired), 'Retired saves before rollback')
            move_save(retired, target)
        else:
            compare(files, env.tree_files(target), 'Untouched original test saves')
    if env.file_sha(env.SESETTINGS) != receipt['se_before_sha256']:
        env.replace_known(path.parent / 'se.before', env.SESETTINGS,
                          receipt['se_restore_sha256'], receipt['se_before_sha256'])
    pointer = env.BASE / 'state.json'
    if env.file_sha(pointer) != receipt['state_before_sha256']:
        env.replace_known(path.parent / 'candidate-state.before.json', pointer,
                          receipt['adopted_state_sha256'], receipt['state_before_sha256'])
    compare(receipt['test_saves_before'], test_snapshot(), 'Rolled-back dedicated saves')
    compare(receipt['preserved'], preserved(manifest_path), 'Preserved files after rollback')
    compare(receipt['unrelated'], env.unrelated_snapshot(), 'Unrelated files after rollback')
    receipt.update(status='rolled-back', rolled_back_at=env.now(), rollback_restored_archive=str(archived))
    env.write_json(path, receipt)
    return path, receipt


def apply(path):
    path, receipt, manifest_path, original = load_receipt(path)
    if receipt['status'] != 'prepared':
        env.fail('Apply requires a newly prepared finalization receipt.')
    verify_receipt(path, receipt, manifest_path, original)
    receipt.update(status='applying', apply_started_at=env.now())
    env.write_json(path, receipt)
    try:
        if receipt['se_restore_existed']:
            env.replace_known(path.parent / 'se.restore', env.SESETTINGS,
                              receipt['se_before_sha256'], receipt['se_restore_sha256'])
        else:
            compare(receipt['se_before_sha256'], env.file_sha(env.SESETTINGS), 'Owned temporary SE before removal')
            env.SESETTINGS.unlink()
        for name, files in receipt['test_saves_before'].items():
            target = save_path(name)
            compare(files, env.tree_files(target), 'Live dedicated save before retirement')
            receipt['retire_started'].append(name)
            env.write_json(path, receipt)
            move_save(target, save_path(name, path.parent / 'test-saves.retired'))
        for name, files in receipt['test_saves_restore'].items():
            target = save_path(name)
            if target.exists():
                env.fail('Dedicated destination reappeared during finalization.')
            receipt['restore_started'].append(name)
            env.write_json(path, receipt)
            shutil.copytree(save_path(name, path.parent / 'test-saves.restore'), target)
            compare(files, env.tree_files(target), 'Restored dedicated save')
        compare(receipt['test_saves_restore'], test_snapshot(), 'Restored dedicated saves')
        compare(receipt['se_restore_sha256'], env.file_sha(env.SESETTINGS), 'Restored SE')
        compare(receipt['preserved'], preserved(manifest_path), 'Retained PAK/settings/manifest')
        compare(receipt['unrelated'], env.unrelated_snapshot(), 'Unrelated files after finalization')
        compare(receipt['state_before_sha256'], env.file_sha(env.BASE / 'state.json'), 'State before adoption')
        env.replace_known(path.parent / 'candidate-state.adopted.json', env.BASE / 'state.json',
                          receipt['state_before_sha256'], receipt['adopted_state_sha256'])
        receipt.update(status='finalized', finalized_at=env.now(),
                       installed_pak_unchanged=True, enabled_settings_unchanged=True,
                       original_manifest_unchanged=True, unrelated_unchanged=True)
        env.write_json(path, receipt)
    except BaseException as exc:
        receipt.update(status='recovery-required', apply_error=str(exc))
        try:
            rollback(path, receipt)
        except BaseException as recovery:
            receipt['recovery_error'] = str(recovery)
            env.write_json(path, receipt)
        raise
    return path, receipt


def summary(path, receipt):
    return {'status': receipt['status'], 'receipt': str(path),
            'source_manifest': receipt['source_manifest'], 'kept_pak_sha256': receipt['expected_pak_sha256'],
            'live_pak_sha256': env.file_sha(env.PACKAGE),
            'live_settings_sha256': env.file_sha(env.SETTINGS), 'live_se_sha256': env.file_sha(env.SESETTINGS),
            'restored_test_directories': len(receipt['test_saves_restore']),
            'boundary': receipt['boundary']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    prepare_command = commands.add_parser('prepare')
    prepare_command.add_argument('--manifest', required=True, type=Path)
    prepare_command.add_argument('--expected-pak-sha', required=True)
    for action in ('apply', 'rollback', 'status'):
        commands.add_parser(action).add_argument('--receipt', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'prepare':
            path, receipt = prepare(args.manifest, args.expected_pak_sha)
        elif args.action == 'status':
            path, receipt, _, _ = load_receipt(args.receipt)
        else:
            path, receipt = globals()[args.action](args.receipt)
        print(json.dumps(summary(path, receipt), ensure_ascii=False))
    except Exception as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
