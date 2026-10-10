"""Finalization guards execute solely against isolated temporary installations."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_sword_client_candidate as fixture_module

environment = fixture_module.environment


SCRIPT = Path(__file__).resolve().parents[1] / 'finalize-sword-client-candidate.py'
SPEC = importlib.util.spec_from_file_location('esc_candidate_finalizer_test', SCRIPT)
finalizer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(finalizer)


class ClientFinalization(unittest.TestCase):
    def setUp(self):
        # Compose the pre-existing fixture; do not inherit/re-run its test suite.
        self.fixture = fixture_module.ClientCandidate(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.patch_env = patch.object(finalizer, 'env', environment)
        self.patch_env.start()
        self.addCleanup(self.patch_env.stop)
        self.manifest, _ = self.fixture.prepare()
        environment.apply(self.manifest)
        (self.fixture.test_dir / 'AutoSave_0.lsv').write_bytes(b'accepted new test progress')
        self.extra = environment.SAVES / 'ESC_Test_01-456__ManualSave'
        self.extra.mkdir()
        (self.extra / 'ManualSave.lsv').write_bytes(b'new test-only save')
        self.initial = self.snapshot()

    def snapshot(self):
        return dict(pak=environment.PACKAGE.read_bytes(), settings=environment.SETTINGS.read_bytes(),
                    se=environment.SESETTINGS.read_bytes() if environment.SESETTINGS.exists() else None,
                    manifest=self.manifest.read_bytes(),
                    state=(environment.BASE / 'state.json').read_bytes(),
                    saves=finalizer.test_snapshot(), unrelated=environment.unrelated_snapshot())

    def prepare(self):
        return finalizer.prepare(self.manifest, environment.digest(environment.PACKAGE))

    def test_prepare_is_read_only_to_live_installation_and_copies_all_inputs(self):
        path, receipt = self.prepare()
        self.assertEqual(self.initial, self.snapshot())
        self.assertEqual(receipt['status'], 'prepared')
        self.assertEqual((path.parent / 'preserved.pak').read_bytes(), self.fixture.candidate)
        self.assertEqual((path.parent / 'candidate-manifest.before.json').read_bytes(), self.initial['manifest'])
        self.assertTrue((path.parent / 'test-saves.before' / self.extra.name / 'ManualSave.lsv').is_file())
        self.assertTrue((path.parent / 'test-saves.restore' / self.fixture.test_dir.name / 'empty-original-directory').is_dir())

    def test_finalize_keeps_exact_pak_settings_manifest_and_restores_only_owned_data(self):
        path, _ = self.prepare()
        replace = environment.replace_known
        def narrow_replace(source, target, *args):
            self.assertNotIn(Path(target), (environment.PACKAGE, environment.SETTINGS))
            return replace(source, target, *args)
        with patch.object(environment, 'replace_known', side_effect=narrow_replace):
            _, receipt = finalizer.apply(path)
        after = self.snapshot()
        for key in ('pak', 'settings', 'manifest', 'unrelated'):
            self.assertEqual(after[key], self.initial[key])
        self.assertEqual(after['se'], self.fixture.se)
        self.assertEqual((self.fixture.test_dir / 'AutoSave_0.lsv').read_bytes(), b'original dedicated save')
        self.assertFalse(self.extra.exists())
        self.assertEqual((path.parent / 'test-saves.retired' / self.extra.name / 'ManualSave.lsv').read_bytes(), b'new test-only save')
        self.assertEqual(json.loads(after['manifest'])['status'], 'applied')
        self.assertEqual(receipt['status'], 'finalized')
        self.assertEqual(json.loads(after['state'])['status'], 'adopted')
        self.assertFalse(json.loads(after['state'])['active'])

    def test_explicit_rollback_returns_pre_cleanup_state_without_rolling_back_pak(self):
        path, _ = self.prepare()
        finalizer.apply(path)
        _, receipt = finalizer.rollback(path)
        self.assertEqual(receipt['status'], 'rolled-back')
        self.assertEqual(self.initial, self.snapshot())
        with self.assertRaisesRegex(RuntimeError, 'newly prepared'):
            finalizer.apply(path)

    def test_bad_expected_pak_refused_before_any_backups(self):
        with self.assertRaisesRegex(RuntimeError, 'explicitly expected'):
            finalizer.prepare(self.manifest, '0' * 64)
        self.assertFalse(finalizer.base().exists())
        self.assertEqual(self.initial, self.snapshot())

    def test_interrupted_explicit_rollback_can_resume_after_archiving_or_restoring(self):
        for stop_name in (self.fixture.test_dir.name, self.extra.name):
            with self.subTest(stop_name=stop_name):
                path, _ = self.prepare()
                finalizer.apply(path)
                move = finalizer.move_save
                def stop_rollback(source, target):
                    if Path(source).parent.name == 'test-saves.retired' and Path(source).name == stop_name:
                        raise OSError('simulated interrupted explicit rollback')
                    return move(source, target)
                with patch.object(finalizer, 'move_save', side_effect=stop_rollback):
                    with self.assertRaisesRegex(OSError, 'interrupted explicit rollback'):
                        finalizer.rollback(path)
                self.assertEqual(environment.read_json(path)['status'], 'rolling-back')
                _, receipt = finalizer.rollback(path)
                self.assertEqual(receipt['status'], 'rolled-back')
                self.assertEqual(self.initial, self.snapshot())

    def test_finalized_rollback_refuses_later_save_progress_before_any_live_write(self):
        path, _ = self.prepare()
        finalizer.apply(path)
        (self.fixture.test_dir / 'AutoSave_0.lsv').write_bytes(b'later accepted test progress')
        after = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, 'Restored saves before rollback'):
            finalizer.rollback(path)
        self.assertEqual(after, self.snapshot())

    def test_interrupted_rollback_refuses_unknown_save_directory_before_any_live_write(self):
        path, receipt = self.prepare()
        receipt['status'] = 'applying'
        environment.write_json(path, receipt)
        unknown = environment.SAVES / 'ESC_Test_01-999__NewOutsideProgress'
        unknown.mkdir()
        (unknown / 'Save.lsv').write_bytes(b'later outside test progress')
        after = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, 'Unknown dedicated save directory'):
            finalizer.rollback(path)
        self.assertEqual(after, self.snapshot())

    def test_prepare_rejects_running_game_and_wrong_active_manifest(self):
        with patch.object(environment, 'check_closed', side_effect=RuntimeError('Close BG3')):
            with self.assertRaisesRegex(RuntimeError, 'Close BG3'):
                self.prepare()
        pointer = environment.BASE / 'state.json'
        state = environment.read_json(pointer)
        state['active'] = False
        environment.write_json(pointer, state)
        with self.assertRaisesRegex(RuntimeError, 'currently active'):
            self.prepare()

    def test_prepare_rejects_mod_or_extender_change_since_candidate_apply(self):
        for target in (self.fixture.other_pak, environment.DWRITE):
            original = target.read_bytes()
            target.write_bytes(b'changed externally')
            with self.assertRaisesRegex(RuntimeError, 'Original unrelated'):
                self.prepare()
            target.write_bytes(original)
        self.assertEqual(self.initial, self.snapshot())

    def test_apply_refuses_unknown_pak_settings_or_se_before_any_cleanup(self):
        path, _ = self.prepare()
        for target in (environment.PACKAGE, environment.SETTINGS, environment.SESETTINGS):
            before = target.read_bytes()
            target.write_bytes(before + b'changed')
            with self.assertRaises(RuntimeError):
                finalizer.apply(path)
            self.assertEqual(finalizer.test_snapshot(), self.initial['saves'])
            target.write_bytes(before)
        self.assertEqual(self.initial, self.snapshot())

    def test_apply_refuses_changes_to_saves_mods_campaign_or_state(self):
        path, _ = self.prepare()
        targets = [self.fixture.test_dir / 'AutoSave_0.lsv', self.fixture.other_pak,
                   self.fixture.campaign_dir / 'other.lsv', environment.BASE / 'state.json']
        for target in targets:
            before = target.read_bytes()
            target.write_bytes(before + b'outside change')
            with self.assertRaises(RuntimeError):
                finalizer.apply(path)
            self.assertEqual(environment.SESETTINGS.read_bytes(), self.initial['se'])
            target.write_bytes(before)
        self.assertEqual(self.initial, self.snapshot())

    def test_apply_rechecks_closed_process_and_finalizer_code(self):
        path, _ = self.prepare()
        with patch.object(environment, 'check_closed', side_effect=RuntimeError('Close BG3')):
            with self.assertRaisesRegex(RuntimeError, 'Close BG3'):
                finalizer.apply(path)
        with patch.object(finalizer, 'source_inputs', return_value={'changed': 'code'}):
            with self.assertRaisesRegex(RuntimeError, 'Finalizer code'):
                finalizer.apply(path)
        self.assertEqual(self.initial, self.snapshot())

    def test_corrupt_backup_or_changed_original_manifest_refused(self):
        path, _ = self.prepare()
        backup = path.parent / 'se.restore'
        original = backup.read_bytes()
        backup.write_bytes(b'corrupt')
        with self.assertRaisesRegex(RuntimeError, 'Finalization backup'):
            finalizer.apply(path)
        backup.write_bytes(original)
        original = self.manifest.read_bytes()
        self.manifest.write_bytes(original + b' ')
        with self.assertRaisesRegex(RuntimeError, 'Original candidate manifest'):
            finalizer.apply(path)
        self.manifest.write_bytes(original)
        self.assertEqual(self.initial, self.snapshot())

    def test_receipt_and_save_path_escape_are_rejected(self):
        path, _ = self.prepare()
        wrong = self.fixture.root / 'receipt.json'
        wrong.write_bytes(path.read_bytes())
        with self.assertRaisesRegex(RuntimeError, 'exact finalization receipt'):
            finalizer.apply(wrong)
        for name in ('OtherCampaign', 'ESC_Test_012-similar', 'ESC_Test_01-../../OtherCampaign', 'ESC_Test_01-\\escape'):
            with self.assertRaises(RuntimeError):
                finalizer.save_path(name)
        self.assertEqual(self.initial, self.snapshot())

    def test_reparse_point_is_rejected_before_live_writes(self):
        original = Path.is_symlink
        def fake_link(path):
            return path == self.fixture.test_dir or original(path)
        with patch.object(Path, 'is_symlink', fake_link):
            with self.assertRaisesRegex(RuntimeError, 'Reparse points'):
                self.prepare()
        self.assertEqual(self.initial, self.snapshot())

    def test_missing_original_se_is_removed_and_rollback_recovers_temporary_file(self):
        # Start a separate, legitimate candidate transaction with an absent SE baseline.
        environment.restore(self.manifest)
        environment.SESETTINGS.unlink()
        self.manifest, _ = self.fixture.prepare()
        environment.apply(self.manifest)
        self.initial = self.snapshot()
        path, _ = self.prepare()
        finalizer.apply(path)
        self.assertFalse(environment.SESETTINGS.exists())
        self.assertEqual(environment.PACKAGE.read_bytes(), self.fixture.candidate)
        finalizer.rollback(path)
        self.assertEqual(self.initial, self.snapshot())

    def test_partial_save_copy_failure_rolls_back_and_preserves_incomplete_copy(self):
        path, _ = self.prepare()
        original_copy = finalizer.shutil.copytree
        def fail_restore(source, target, *args, **kwargs):
            if Path(target) == self.fixture.test_dir:
                Path(target).mkdir()
                (Path(target) / 'partial').write_bytes(b'preserved failed copy')
                raise OSError('simulated interrupted save copy')
            return original_copy(source, target, *args, **kwargs)
        with patch.object(finalizer.shutil, 'copytree', side_effect=fail_restore):
            with self.assertRaisesRegex(OSError, 'interrupted save copy'):
                finalizer.apply(path)
        self.assertEqual(self.initial, self.snapshot())
        receipt = environment.read_json(path)
        self.assertEqual(receipt['status'], 'rolled-back')
        self.assertEqual((Path(receipt['rollback_restored_archive']) / self.fixture.test_dir.name / 'partial').read_bytes(), b'preserved failed copy')

    def test_state_write_failure_rolls_back_without_marking_original_manifest_restored(self):
        path, _ = self.prepare()
        replace = environment.replace_known
        def fail_state(source, target, *args):
            if Path(target) == environment.BASE / 'state.json':
                raise OSError('simulated state lock')
            return replace(source, target, *args)
        with patch.object(environment, 'replace_known', side_effect=fail_state):
            with self.assertRaisesRegex(OSError, 'state lock'):
                finalizer.apply(path)
        self.assertEqual(self.initial, self.snapshot())
        self.assertEqual(environment.read_json(path)['status'], 'rolled-back')

    def test_partial_save_retirement_failure_restores_moved_and_untouched_directories(self):
        path, _ = self.prepare()
        move = finalizer.move_save
        def fail_second_retirement(source, target):
            if Path(source) == self.extra and Path(target).parent.name == 'test-saves.retired':
                raise OSError('simulated second save lock')
            return move(source, target)
        with patch.object(finalizer, 'move_save', side_effect=fail_second_retirement):
            with self.assertRaisesRegex(OSError, 'second save lock'):
                finalizer.apply(path)
        self.assertEqual(self.initial, self.snapshot())
        self.assertEqual(environment.read_json(path)['status'], 'rolled-back')

    def test_final_receipt_write_failure_rolls_back_already_adopted_state(self):
        path, _ = self.prepare()
        write = environment.write_json
        def fail_final_receipt(target, value):
            if Path(target) == path and value.get('status') == 'finalized':
                raise OSError('simulated final receipt lock')
            return write(target, value)
        with patch.object(environment, 'write_json', side_effect=fail_final_receipt):
            with self.assertRaisesRegex(OSError, 'final receipt lock'):
                finalizer.apply(path)
        self.assertEqual(self.initial, self.snapshot())
        self.assertEqual(environment.read_json(path)['status'], 'rolled-back')

    def test_partial_receipt_temp_write_keeps_valid_journal_and_rolls_back(self):
        path, _ = self.prepare()
        dump = environment.json.dump
        def fail_final_dump(value, stream, *args, **kwargs):
            if value.get('operation') == finalizer.OPERATION and value.get('status') == 'finalized':
                stream.write('{"partial":')
                raise OSError('simulated disk full during receipt write')
            return dump(value, stream, *args, **kwargs)
        with patch.object(environment.json, 'dump', side_effect=fail_final_dump):
            with self.assertRaisesRegex(OSError, 'disk full'):
                finalizer.apply(path)
        self.assertEqual(self.initial, self.snapshot())
        self.assertEqual(environment.read_json(path)['status'], 'rolled-back')

    def test_receipt_atomic_replace_failure_keeps_valid_journal_and_rolls_back(self):
        path, _ = self.prepare()
        replace = environment.os.replace
        def fail_final_replace(source, target):
            if Path(target) == path and environment.read_json(source).get('status') == 'finalized':
                raise OSError('simulated receipt atomic replacement failure')
            return replace(source, target)
        with patch.object(environment.os, 'replace', side_effect=fail_final_replace):
            with self.assertRaisesRegex(OSError, 'atomic replacement failure'):
                finalizer.apply(path)
        self.assertEqual(self.initial, self.snapshot())
        self.assertEqual(environment.read_json(path)['status'], 'rolled-back')

    def test_existing_campaign_progress_is_kept_and_future_candidates_remain_possible(self):
        campaign = self.fixture.campaign_dir / 'other.lsv'
        campaign.write_bytes(b'legitimate campaign progress during testing')
        path, _ = self.prepare()
        finalizer.apply(path)
        self.assertEqual(campaign.read_bytes(), b'legitimate campaign progress during testing')
        next_path, next_manifest = self.fixture.prepare()
        self.assertNotEqual(next_path, self.manifest)
        self.assertEqual(next_manifest['official_version'], '1.0.0.10')


if __name__ == '__main__':
    unittest.main()
