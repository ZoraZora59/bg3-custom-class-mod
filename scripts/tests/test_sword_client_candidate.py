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
        environment.PACKAGE.write_bytes(self.official)
        self.source = self.root / 'frozen-candidate.pak'
        self.source.write_bytes(self.candidate)
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
            return dict(self.candidate_meta if Path(package).read_bytes() == self.candidate else self.official_meta)
        environment.package_metadata = metadata

    def prepare(self):
        return environment.prepare(self.source, environment.digest(self.source), '1.0.0.10')

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


if __name__ == '__main__':
    unittest.main()
