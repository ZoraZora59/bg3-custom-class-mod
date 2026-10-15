"""Candidate installation safety tests use only isolated temporary fixtures."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / 'sword-client-candidate.py'
SPEC = importlib.util.spec_from_file_location('sword_client_candidate', SCRIPT)
environment = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(environment)


class ClientCandidate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = {name: getattr(environment, name) for name in
                         ('REPO', 'BUILD', 'BASE', 'PACKAGE', 'SETTINGS', 'SESETTINGS',
                          'DWRITE', 'SAVES', 'check_closed', 'package_metadata')}
        self.addCleanup(lambda: [setattr(environment, name, value) for name, value in self.original.items()])
        environment.REPO = self.root
        environment.BUILD = self.root / 'build/sword-cultivator'
        environment.BASE = environment.BUILD / 'client-candidate'
        environment.PACKAGE = self.root / 'local/Mods' / (environment.FOLDER + '.pak')
        environment.SETTINGS = self.root / 'local/PlayerProfiles/Public/modsettings.lsx'
        environment.SESETTINGS = self.root / 'game/bin/ScriptExtenderSettings.json'
        environment.DWRITE = self.root / 'game/bin/DWrite.dll'
        environment.SAVES = self.root / 'local/PlayerProfiles/Public/Savegames/Story'
        environment.check_closed = lambda: None
        for path in (environment.PACKAGE, environment.SETTINGS, environment.SESETTINGS, environment.DWRITE):
            path.parent.mkdir(parents=True, exist_ok=True)
        self.official = b'published package v12'
        self.candidate = b'candidate package v10'
        self.replacement = b'updated candidate package v10'
        environment.PACKAGE.write_bytes(self.official)
        self.source = self.root / 'frozen-candidate.pak'
        self.source.write_bytes(self.candidate)
        self.replacement_source = self.root / 'updated-candidate.pak'
        self.replacement_source.write_bytes(self.replacement)
        self.other_pak = environment.PACKAGE.parent / 'other.pak'
        self.other_pak.write_bytes(b'other mod stays unchanged')
        environment.DWRITE.write_bytes(b'installed extender stays unchanged')
        self.se = b'{ "EnableLogging": false, "OtherSetting": 17 }\r\n'
        environment.SESETTINGS.write_bytes(self.se)
        self.official_meta = {
            'Folder': environment.FOLDER, 'MD5': 'official-md5', 'Name': 'EasternSwordCultivator',
            'PublishHandle': '6417135', 'UUID': environment.UUID, 'Version64': '36028797018963980'}
        self.candidate_meta = self.official_meta | {'MD5': '', 'Version64': '36028797018963978'}
        row = '<node id="ModuleShortDesc">\r\n' + ''.join(
            '  <attribute id="{}" type="LSString" value="{}"/>\r\n'.format(k, v)
            for k, v in self.official_meta.items()) + '</node>'
        self.prefix = b'\xef\xbb\xbf<?xml version="1.0" encoding="utf-8"?>\r\n<save><region id="Config"><node id="root"><children>\r\n'
        self.suffix = (b'\r\n<node id="ModuleShortDesc"><attribute id="UUID" value="other-uuid"/>'
                       b'<attribute id="Name" value="Other Mod &amp; Spaces"/></node>\r\n'
                       b'<node id="ModOrder"><children><node id="Module"><attribute id="UUID" value="other-uuid"/></node>'
                       b'<node id="Module"><attribute id="UUID" value="' + environment.UUID.encode() +
                       b'"/></node></children></node></children></node></region></save>\r\n')
        self.settings = self.prefix + row.encode('utf-8') + self.suffix
        environment.SETTINGS.write_bytes(self.settings)
        self.test_dir = environment.SAVES / 'ESC_Test_01-123__AutoSave_0'
        self.test_dir.mkdir(parents=True)
        (self.test_dir / 'AutoSave_0.lsv').write_bytes(b'original dedicated save')
        (self.test_dir / 'AutoSave_0.WebP').write_bytes(b'original dedicated preview')
        (self.test_dir / 'empty-original-directory').mkdir()
        self.campaign_dir = environment.SAVES / 'OtherCampaign'
        self.campaign_dir.mkdir()
        (self.campaign_dir / 'other.lsv').write_bytes(b'unrelated campaign save')
        self.similar_dir = environment.SAVES / 'ESC_Test_012-is-not-owned'
        self.similar_dir.mkdir()
        (self.similar_dir / 'other.lsv').write_bytes(b'not the dedicated character')
        def metadata(package, destination):
            return dict(self.candidate_meta if Path(package).read_bytes() in
                        (self.candidate, self.replacement) else self.official_meta)
        environment.package_metadata = metadata

    def prepare(self):
        return environment.prepare(self.source, environment.digest(self.source), '1.0.0.10')

    def prepare_replacement(self):
        return environment.prepare(self.replacement_source, environment.digest(self.replacement_source),
                                   '1.0.0.10', no_debug=True, replace_active=True)

    def activate(self):
        path, _ = self.prepare()
        environment.apply(path)
        return path, path.read_bytes(), (environment.BASE / 'state.json').read_bytes()

    def assert_originals(self):
        self.assertEqual(environment.PACKAGE.read_bytes(), self.official)
        self.assertEqual(environment.SETTINGS.read_bytes(), self.settings)
        self.assertEqual(environment.SESETTINGS.read_bytes(), self.se)
        self.assertEqual(self.other_pak.read_bytes(), b'other mod stays unchanged')
        self.assertEqual((self.campaign_dir / 'other.lsv').read_bytes(), b'unrelated campaign save')
        self.assertEqual((self.similar_dir / 'other.lsv').read_bytes(), b'not the dedicated character')

    def test_prepare_lower_version_backs_up_without_live_changes(self):
        path, manifest = self.prepare()
        self.assertEqual(manifest['official_version'], '1.0.0.12')
        self.assertEqual(manifest['candidate']['version'], '1.0.0.10')
        self.assertEqual(manifest['status'], 'prepared')
        self.assert_originals()
        self.assertEqual(Path(manifest['records']['pak']['backup']).read_bytes(), self.official)
        self.assertTrue((path.parent / 'test-saves.before' / self.test_dir.name / 'empty-original-directory').is_dir())
        self.assertEqual(len(manifest['test_saves']), 1)
        prepared = Path(manifest['prepared']['settings']['path']).read_bytes()
        self.assertTrue(prepared.startswith(self.prefix))
        self.assertTrue(prepared.endswith(self.suffix))
        self.assertEqual(environment.settings_metadata(prepared), self.candidate_meta)

    def test_apply_restore_keeps_other_mods_and_archives_new_test_saves(self):
        path, _ = self.prepare()
        environment.apply(path)
        self.assertEqual(environment.PACKAGE.read_bytes(), self.candidate)
        self.assertEqual(environment.settings_metadata(environment.SETTINGS.read_bytes()), self.candidate_meta)
        self.assertTrue(environment.SETTINGS.read_bytes().endswith(self.suffix))
        se = environment.read_json(environment.SESETTINGS)
        self.assertTrue(se['EnableLuaDebugger'])
        self.assertEqual(se['OtherSetting'], 17)
        (self.test_dir / 'AutoSave_0.lsv').write_bytes(b'new test progress')
        new_dir = environment.SAVES / 'ESC_Test_01-456__AutoSave_1'
        new_dir.mkdir()
        (new_dir / 'AutoSave_1.lsv').write_bytes(b'new dedicated autosave')
        _, restored = environment.restore(path)
        self.assert_originals()
        self.assertEqual((self.test_dir / 'AutoSave_0.lsv').read_bytes(), b'original dedicated save')
        self.assertFalse(new_dir.exists())
        retired = Path(restored['retired_test_saves'])
        self.assertEqual((retired / new_dir.name / 'AutoSave_1.lsv').read_bytes(), b'new dedicated autosave')
        self.assertEqual((retired / self.test_dir.name / 'AutoSave_0.lsv').read_bytes(), b'new test progress')
        self.assertTrue(restored['unrelated_unchanged_by_restore'])
        self.assertFalse(environment.read_json(environment.BASE / 'state.json')['active'])

    def test_wrong_explicit_sha_fails_before_backup_or_live_write(self):
        with self.assertRaisesRegex(RuntimeError, 'explicitly expected SHA'):
            environment.prepare(self.source, '0' * 64)
        self.assertFalse(environment.BASE.exists())
        self.assert_originals()

    def test_duplicate_esc_package_refused(self):
        (environment.PACKAGE.parent / 'EasternSwordCultivator.pak').write_bytes(b'duplicate')
        with self.assertRaisesRegex(RuntimeError, 'same-UUID'):
            self.prepare()
        self.assert_originals()

    def test_active_toolkit_or_process_refused(self):
        state = environment.BUILD / 'toolkit-environment/state.json'
        state.parent.mkdir(parents=True)
        state.write_text('{"active":true}', encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'active toolkit-environment'):
            self.prepare()
        state.write_text('{"active":false}', encoding='utf-8')
        with patch.object(environment, 'check_closed', side_effect=RuntimeError('Close BG3')):
            with self.assertRaisesRegex(RuntimeError, 'Close BG3'):
                self.prepare()
        self.assert_originals()

    def test_official_metadata_mismatch_refused(self):
        self.official_meta['MD5'] = 'mismatch'
        with self.assertRaisesRegex(RuntimeError, 'official PAK metadata differs'):
            self.prepare()
        self.assert_originals()

    def test_apply_refuses_stale_dedicated_save_and_other_pak(self):
        path, _ = self.prepare()
        (self.test_dir / 'AutoSave_0.lsv').write_bytes(b'external save change')
        with self.assertRaisesRegex(RuntimeError, 'Dedicated saves after Prepare'):
            environment.apply(path)
        (self.test_dir / 'AutoSave_0.lsv').write_bytes(b'original dedicated save')
        self.other_pak.write_bytes(b'external mod change')
        with self.assertRaisesRegex(RuntimeError, 'Unrelated files after Prepare'):
            environment.apply(path)
        self.assertEqual(environment.PACKAGE.read_bytes(), self.official)
        self.assertEqual(environment.SETTINGS.read_bytes(), self.settings)

    def test_restore_unknown_package_or_settings_rejects_before_any_restore(self):
        path, _ = self.prepare()
        environment.apply(path)
        environment.PACKAGE.write_bytes(b'unknown outside package')
        candidate_settings = environment.SETTINGS.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'unknown live file SHA: pak'):
            environment.restore(path)
        self.assertEqual(environment.SETTINGS.read_bytes(), candidate_settings)
        environment.PACKAGE.write_bytes(self.candidate)
        environment.SETTINGS.write_bytes(candidate_settings + b' ')
        with self.assertRaisesRegex(RuntimeError, 'unknown live file SHA: settings'):
            environment.restore(path)
        self.assertEqual(environment.PACKAGE.read_bytes(), self.candidate)

    def test_corrupt_backup_refused_and_manifest_path_escape_refused(self):
        path, manifest = self.prepare()
        environment.apply(path)
        Path(manifest['records']['pak']['backup']).write_bytes(b'bad backup')
        with self.assertRaisesRegex(RuntimeError, 'Original backup SHA256 differs'):
            environment.restore(path)
        self.assertEqual(environment.PACKAGE.read_bytes(), self.candidate)
        manifest['records']['pak']['target'] = str(self.other_pak)
        environment.write_json(path, manifest)
        with self.assertRaisesRegex(RuntimeError, 'exact owned path'):
            environment.load_manifest(path)

    def test_partial_apply_failure_automatically_restores_known_files(self):
        path, _ = self.prepare()
        replace = environment.os.replace
        def fail_settings(source, target):
            if Path(target) == environment.SETTINGS:
                raise OSError('simulated locked modsettings')
            return replace(source, target)
        with patch.object(environment.os, 'replace', side_effect=fail_settings):
            with self.assertRaisesRegex(OSError, 'locked modsettings'):
                environment.apply(path)
        self.assert_originals()
        self.assertEqual(environment.read_json(path)['status'], 'prepared')
        self.assertFalse(environment.read_json(environment.BASE / 'state.json')['active'])

    def test_missing_original_se_settings_is_removed_after_restore(self):
        environment.SESETTINGS.unlink()
        path, _ = self.prepare()
        environment.apply(path)
        self.assertTrue(environment.SESETTINGS.is_file())
        environment.restore(path)
        self.assertFalse(environment.SESETTINGS.exists())
        self.assertEqual(environment.PACKAGE.read_bytes(), self.official)

    def test_external_campaign_change_is_preserved_by_restore(self):
        path, _ = self.prepare()
        environment.apply(path)
        (self.campaign_dir / 'other.lsv').write_bytes(b'external campaign change')
        _, restored = environment.restore(path)
        self.assertEqual((self.campaign_dir / 'other.lsv').read_bytes(), b'external campaign change')
        self.assertFalse(restored['unrelated_matches_prepare'])
        self.assertTrue(restored['unrelated_unchanged_by_restore'])
        self.assertEqual(environment.PACKAGE.read_bytes(), self.official)

    def test_no_debug_disables_four_flags_preserves_other_settings_and_exact_restore(self):
        self.se = (b'{"EnableLogging":true,"LogRuntime":true,"LogFailedCompile":true,'
                   b'"EnableLuaDebugger":true,"CreateConsole":true,"LogDirectory":"original-logs",'
                   b'"LogCompile":true,"OtherSetting":17}\r\n')
        environment.SESETTINGS.write_bytes(self.se)
        path, manifest = environment.prepare(self.source, environment.digest(self.source), no_debug=True)
        self.assertFalse(manifest['debug_enabled'])
        self.assert_originals()
        environment.apply(path)
        se = environment.read_json(environment.SESETTINGS)
        for name in ('EnableLogging', 'LogRuntime', 'LogFailedCompile', 'EnableLuaDebugger'):
            self.assertIs(se[name], False)
        self.assertIs(se['CreateConsole'], True)
        self.assertIs(se['LogCompile'], True)
        self.assertEqual(se['LogDirectory'], 'original-logs')
        self.assertEqual(se['OtherSetting'], 17)
        environment.restore(path)
        self.assert_originals()

    def test_default_debug_mode_keeps_existing_diagnostic_behavior(self):
        _, manifest = self.prepare()
        se = environment.read_json(manifest['prepared']['se']['path'])
        self.assertTrue(manifest['debug_enabled'])
        for name in ('EnableLogging', 'LogRuntime', 'LogFailedCompile', 'EnableLuaDebugger'):
            self.assertIs(se[name], True)
        self.assertIs(se['CreateConsole'], False)
        self.assertTrue(se['LogDirectory'].endswith('client-logs'))

    def test_cli_accepts_no_debug_and_replace_active(self):
        old_path, old_manifest, old_state = self.activate()
        args = ['sword-client-candidate.py', 'prepare', '--candidate', str(self.replacement_source),
                '--expected-sha', environment.digest(self.replacement_source),
                '--expected-version', '1.0.0.10', '--no-debug', '--replace-active']
        with patch('sys.argv', args), patch('builtins.print') as output:
            self.assertEqual(environment.main(), 0)
        result = json.loads(output.call_args.args[0])
        self.assertFalse(result['debug_enabled'])
        self.assertEqual(result['supersedes_manifest'], str(old_path))
        self.assertEqual(old_path.read_bytes(), old_manifest)
        self.assertEqual((environment.BASE / 'state.json').read_bytes(), old_state)

    def test_replacement_prepare_apply_restore_preserves_progress_and_parent_chain(self):
        old_path, old_manifest, old_state = self.activate()
        old_se = environment.SESETTINGS.read_bytes()
        old_settings = environment.SETTINGS.read_bytes()
        (self.test_dir / 'AutoSave_0.lsv').write_bytes(b'current dedicated progress')
        current_tests = environment.test_snapshot()
        current_other = environment.unrelated_snapshot()
        path, manifest = self.prepare_replacement()
        self.assertEqual(environment.PACKAGE.read_bytes(), self.candidate)
        self.assertEqual(environment.SESETTINGS.read_bytes(), old_se)
        self.assertEqual(old_path.read_bytes(), old_manifest)
        self.assertEqual((environment.BASE / 'state.json').read_bytes(), old_state)
        self.assertEqual(manifest['supersedes']['manifest_sha256'], environment.digest(old_path))
        self.assertEqual(Path(manifest['records']['pak']['backup']).read_bytes(), self.candidate)
        environment.apply(path)
        self.assertEqual(environment.PACKAGE.read_bytes(), self.replacement)
        self.assertFalse(environment.read_json(environment.SESETTINGS)['EnableLuaDebugger'])
        self.assertEqual(environment.test_snapshot(), current_tests)
        self.assertEqual(environment.unrelated_snapshot(), current_other)
        (self.test_dir / 'AutoSave_0.lsv').write_bytes(b'newer dedicated progress')
        new_dir = environment.SAVES / 'ESC_Test_01-new-progress'
        new_dir.mkdir()
        (new_dir / 'progress.lsv').write_bytes(b'new dedicated save after update')
        (self.campaign_dir / 'other.lsv').write_bytes(b'new campaign progress')
        newer_tests = environment.test_snapshot()
        newer_other = environment.unrelated_snapshot()
        _, restored = environment.restore(path)
        self.assertTrue(restored['saves_unchanged_by_restore'])
        self.assertNotIn('retired_test_saves', restored)
        self.assertEqual(environment.PACKAGE.read_bytes(), self.candidate)
        self.assertEqual(environment.SETTINGS.read_bytes(), old_settings)
        self.assertEqual(environment.SESETTINGS.read_bytes(), old_se)
        self.assertEqual(environment.test_snapshot(), newer_tests)
        self.assertEqual(environment.unrelated_snapshot(), newer_other)
        self.assertEqual(old_path.read_bytes(), old_manifest)
        self.assertEqual((environment.BASE / 'state.json').read_bytes(), old_state)
        environment.verify_backups(old_path, environment.read_json(old_path))

    def test_replace_active_requires_applied_environment_and_owned_live_files(self):
        with self.assertRaisesRegex(RuntimeError, 'currently active applied'):
            self.prepare_replacement()
        self.assert_originals()
        old_path, old_manifest, old_state = self.activate()
        environment.SESETTINGS.write_bytes(b'{"outside_edit":true}')
        with self.assertRaisesRegex(RuntimeError, 'live file differs.*se'):
            self.prepare_replacement()
        self.assertEqual(old_path.read_bytes(), old_manifest)
        self.assertEqual((environment.BASE / 'state.json').read_bytes(), old_state)

    def test_replacement_apply_failure_restores_old_files_pointer_and_can_retry(self):
        old_path, old_manifest, old_state = self.activate()
        old_se = environment.SESETTINGS.read_bytes()
        path, _ = self.prepare_replacement()
        current_tests = environment.test_snapshot()
        replace = environment.os.replace
        def fail_se(source, target):
            if Path(target) == environment.SESETTINGS:
                raise OSError('simulated locked SE config')
            return replace(source, target)
        with patch.object(environment.os, 'replace', side_effect=fail_se):
            with self.assertRaisesRegex(OSError, 'locked SE config'):
                environment.apply(path)
        self.assertEqual(environment.PACKAGE.read_bytes(), self.candidate)
        self.assertEqual(environment.SESETTINGS.read_bytes(), old_se)
        self.assertEqual(environment.test_snapshot(), current_tests)
        self.assertEqual((environment.BASE / 'state.json').read_bytes(), old_state)
        self.assertEqual(old_path.read_bytes(), old_manifest)
        self.assertEqual(environment.read_json(path)['status'], 'prepared')
        environment.apply(path)
        self.assertEqual(environment.PACKAGE.read_bytes(), self.replacement)

    def test_replacement_apply_state_publication_failure_rolls_back(self):
        old_path, old_manifest, old_state = self.activate()
        old_se = environment.SESETTINGS.read_bytes()
        path, _ = self.prepare_replacement()
        replace = environment.os.replace
        failed = False
        def fail_applied_state(source, target):
            nonlocal failed
            if Path(target) == environment.BASE / 'state.json' and not failed:
                pending = environment.read_json(source)
                if pending == environment.candidate_state(path, 'applied'):
                    failed = True
                    raise OSError('simulated applied pointer failure')
            return replace(source, target)
        with patch.object(environment.os, 'replace', side_effect=fail_applied_state):
            with self.assertRaisesRegex(OSError, 'applied pointer failure'):
                environment.apply(path)
        self.assertTrue(failed)
        self.assertEqual(environment.PACKAGE.read_bytes(), self.candidate)
        self.assertEqual(environment.SESETTINGS.read_bytes(), old_se)
        self.assertEqual(old_path.read_bytes(), old_manifest)
        self.assertEqual((environment.BASE / 'state.json').read_bytes(), old_state)
        self.assertEqual(environment.read_json(path)['status'], 'prepared')

    def test_replacement_restore_recovers_interrupted_partial_apply_without_save_writes(self):
        _, _, old_state = self.activate()
        old_se = environment.SESETTINGS.read_bytes()
        path, manifest = self.prepare_replacement()
        manifest['status'] = 'applying'
        environment.save_manifest(path, manifest)
        environment.replace_known(manifest['candidate']['path'], environment.PACKAGE,
                                  manifest['records']['pak']['sha256'], manifest['candidate']['sha256'])
        (self.test_dir / 'AutoSave_0.lsv').write_bytes(b'keep interrupted transaction progress')
        current_tests = environment.test_snapshot()
        environment.restore(path)
        self.assertEqual(environment.PACKAGE.read_bytes(), self.candidate)
        self.assertEqual(environment.SESETTINGS.read_bytes(), old_se)
        self.assertEqual(environment.test_snapshot(), current_tests)
        self.assertEqual((environment.BASE / 'state.json').read_bytes(), old_state)

    def test_replacement_restore_failure_keeps_recoverable_pointer_and_retries(self):
        _, _, old_state = self.activate()
        old_se = environment.SESETTINGS.read_bytes()
        path, _ = self.prepare_replacement()
        environment.apply(path)
        current_tests = environment.test_snapshot()
        replace = environment.os.replace
        def fail_se(source, target):
            if Path(target) == environment.SESETTINGS:
                raise OSError('simulated restore SE failure')
            return replace(source, target)
        with patch.object(environment.os, 'replace', side_effect=fail_se):
            with self.assertRaisesRegex(OSError, 'restore SE failure'):
                environment.restore(path)
        self.assertEqual(environment.read_json(path)['status'], 'restore-recovery-required')
        self.assertEqual(environment.read_json(environment.BASE / 'state.json')['manifest'], str(path))
        self.assertEqual(environment.test_snapshot(), current_tests)
        environment.restore(path)
        self.assertEqual(environment.PACKAGE.read_bytes(), self.candidate)
        self.assertEqual(environment.SESETTINGS.read_bytes(), old_se)
        self.assertEqual((environment.BASE / 'state.json').read_bytes(), old_state)
        self.assertEqual(environment.test_snapshot(), current_tests)

    def test_replacement_refuses_stale_parent_state_before_any_live_write(self):
        self.activate()
        path, _ = self.prepare_replacement()
        pointer = environment.BASE / 'state.json'
        state = environment.read_json(pointer) | {'external_edit': True}
        environment.write_json(pointer, state)
        old_se = environment.SESETTINGS.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'Active candidate state changed'):
            environment.apply(path)
        self.assertEqual(environment.PACKAGE.read_bytes(), self.candidate)
        self.assertEqual(environment.SESETTINGS.read_bytes(), old_se)
        self.assertEqual(environment.read_json(pointer), state)

    def test_replacement_refuses_tampered_parent_and_prepared_settings(self):
        old_path, _, _ = self.activate()
        path, manifest = self.prepare_replacement()
        parent_bytes = old_path.read_bytes()
        old_path.write_bytes(parent_bytes + b' ')
        with self.assertRaisesRegex(RuntimeError, 'Superseded candidate manifest changed'):
            environment.apply(path)
        old_path.write_bytes(parent_bytes)
        Path(manifest['prepared']['se']['path']).write_bytes(b'{"EnableLuaDebugger":true}')
        with self.assertRaisesRegex(RuntimeError, 'Prepared configuration changed: se'):
            environment.apply(path)
        self.assertEqual(environment.PACKAGE.read_bytes(), self.candidate)

    def test_replacement_rollback_pointer_failure_can_recover_without_save_changes(self):
        _, _, old_state = self.activate()
        old_se = environment.SESETTINGS.read_bytes()
        path, _ = self.prepare_replacement()
        current_tests = environment.test_snapshot()
        replace = environment.os.replace
        def fail_se_and_parent_pointer(source, target):
            if Path(target) == environment.SESETTINGS:
                raise OSError('simulated apply SE failure')
            if Path(target) == environment.BASE / 'state.json' and Path(source).read_bytes() == old_state:
                raise OSError('simulated parent pointer failure')
            return replace(source, target)
        with patch.object(environment.os, 'replace', side_effect=fail_se_and_parent_pointer):
            with self.assertRaisesRegex(OSError, 'apply SE failure'):
                environment.apply(path)
        self.assertEqual(environment.read_json(path)['status'], 'apply-recovery-required')
        self.assertEqual(environment.PACKAGE.read_bytes(), self.candidate)
        self.assertEqual(environment.SESETTINGS.read_bytes(), old_se)
        self.assertEqual(environment.read_json(environment.BASE / 'state.json')['manifest'], str(path))
        environment.restore(path)
        self.assertEqual((environment.BASE / 'state.json').read_bytes(), old_state)
        self.assertEqual(environment.test_snapshot(), current_tests)

    def test_replacement_restore_refuses_foreign_pointer_before_any_live_write(self):
        self.activate()
        path, _ = self.prepare_replacement()
        environment.apply(path)
        pointer = environment.BASE / 'state.json'
        foreign = environment.read_json(pointer) | {'external_edit': True}
        environment.write_json(pointer, foreign)
        current_tests = environment.test_snapshot()
        current_se = environment.SESETTINGS.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'Active candidate state changed'):
            environment.restore(path)
        self.assertEqual(environment.read_json(pointer), foreign)
        self.assertEqual(environment.PACKAGE.read_bytes(), self.replacement)
        self.assertEqual(environment.SESETTINGS.read_bytes(), current_se)
        self.assertEqual(environment.test_snapshot(), current_tests)

    def test_two_prepared_replacements_cannot_overwrite_each_other(self):
        self.activate()
        first_path, _ = self.prepare_replacement()
        second_path, _ = self.prepare_replacement()
        environment.apply(first_path)
        with self.assertRaisesRegex(RuntimeError, 'Installed file changed|Active candidate state changed'):
            environment.apply(second_path)
        self.assertEqual(environment.read_json(environment.BASE / 'state.json')['manifest'], str(first_path))
        self.assertEqual(environment.PACKAGE.read_bytes(), self.replacement)

    def test_replacement_chain_can_restore_each_parent_and_original(self):
        old_path, old_manifest, old_state = self.activate()
        first_path, _ = self.prepare_replacement()
        environment.apply(first_path)
        first_manifest = first_path.read_bytes()
        first_state = (environment.BASE / 'state.json').read_bytes()
        second_path, _ = self.prepare_replacement()
        environment.apply(second_path)
        environment.restore(second_path)
        self.assertEqual(first_path.read_bytes(), first_manifest)
        self.assertEqual((environment.BASE / 'state.json').read_bytes(), first_state)
        environment.restore(first_path)
        self.assertEqual(old_path.read_bytes(), old_manifest)
        self.assertEqual((environment.BASE / 'state.json').read_bytes(), old_state)
        environment.restore(old_path)
        self.assert_originals()

    def test_replacement_preserves_new_other_mod_rows_as_byte_exact_settings_baseline(self):
        old_path, old_manifest, old_state = self.activate()
        parent_settings_sha = environment.read_json(old_path)['prepared']['settings']['sha256']
        extra_row = (b'<node id="ModuleShortDesc"><attribute id="UUID" value="new-other-mod"/>'
                     b'<attribute id="Name" value="New Other Mod &amp; Spaces"/></node>\r\n')
        current_settings = environment.SETTINGS.read_bytes().replace(self.suffix, extra_row + self.suffix)
        environment.SETTINGS.write_bytes(current_settings)
        current_sha = environment.digest(environment.SETTINGS)
        self.assertNotEqual(current_sha, parent_settings_sha)
        path, manifest = self.prepare_replacement()
        self.assertEqual(manifest['supersedes']['accepted_settings_sha256'], current_sha)
        self.assertEqual(manifest['records']['settings']['sha256'], current_sha)
        self.assertEqual(Path(manifest['records']['settings']['backup']).read_bytes(), current_settings)
        self.assertEqual(Path(manifest['prepared']['settings']['path']).read_bytes(), current_settings)
        self.assertEqual(environment.SETTINGS.read_bytes(), current_settings)
        self.assertEqual(old_path.read_bytes(), old_manifest)
        self.assertEqual((environment.BASE / 'state.json').read_bytes(), old_state)
        environment.apply(path)
        self.assertEqual(environment.SETTINGS.read_bytes(), current_settings)
        environment.restore(path)
        self.assertEqual(environment.SETTINGS.read_bytes(), current_settings)
        self.assertEqual(old_path.read_bytes(), old_manifest)
        self.assertEqual((environment.BASE / 'state.json').read_bytes(), old_state)
        # The legacy manifest cannot silently erase additions accepted by the replacement.
        with self.assertRaisesRegex(RuntimeError, 'unknown live file SHA: settings'):
            environment.restore(old_path)
        self.assertEqual(environment.SETTINGS.read_bytes(), current_settings)

    def test_replacement_refuses_esc_metadata_changes_even_when_other_rows_change(self):
        old_path, old_manifest, old_state = self.activate()
        changed = environment.SETTINGS.read_bytes().replace(
            b'value="36028797018963978"', b'value="36028797018963979"')
        environment.SETTINGS.write_bytes(changed)
        with self.assertRaisesRegex(RuntimeError, 'ESC settings metadata differs'):
            self.prepare_replacement()
        self.assertEqual(environment.SETTINGS.read_bytes(), changed)
        self.assertEqual(environment.PACKAGE.read_bytes(), self.candidate)
        self.assertEqual(old_path.read_bytes(), old_manifest)
        self.assertEqual((environment.BASE / 'state.json').read_bytes(), old_state)

    def test_replacement_refuses_unknown_esc_row_changes_with_same_six_values(self):
        self.activate()
        changed = environment.SETTINGS.read_bytes().replace(
            b'<attribute id="MD5" type="LSString"', b'<attribute id="MD5" type="FixedString"', 1)
        environment.SETTINGS.write_bytes(changed)
        self.assertEqual(environment.settings_metadata(changed), self.candidate_meta)
        with self.assertRaisesRegex(RuntimeError, 'ESC settings row changed'):
            self.prepare_replacement()
        self.assertEqual(environment.SETTINGS.read_bytes(), changed)
        self.assertEqual(environment.PACKAGE.read_bytes(), self.candidate)

    def test_replacement_rechecks_accepted_settings_hash_and_backup(self):
        self.activate()
        current = environment.SETTINGS.read_bytes() + b'\r\n<!-- other settings edit -->\r\n'
        environment.SETTINGS.write_bytes(current)
        path, manifest = self.prepare_replacement()
        manifest['supersedes']['accepted_settings_sha256'] = '0' * 64
        environment.write_json(path, manifest)
        with self.assertRaisesRegex(RuntimeError, 'rollback file differs.*settings'):
            environment.apply(path)
        manifest['supersedes']['accepted_settings_sha256'] = manifest['records']['settings']['sha256']
        environment.write_json(path, manifest)
        Path(manifest['records']['settings']['backup']).write_bytes(current + b' ')
        with self.assertRaisesRegex(RuntimeError, 'baseline settings backup changed'):
            environment.apply(path)
        self.assertEqual(environment.SETTINGS.read_bytes(), current)
        self.assertEqual(environment.PACKAGE.read_bytes(), self.candidate)


if __name__ == '__main__':
    unittest.main()
