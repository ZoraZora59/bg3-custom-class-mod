"""Isolated refresh tests; never access the real BG3 profile or installation."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'scripts'))
spec=importlib.util.spec_from_file_location('esc_test_environment',REPO/'scripts/sword-test-environment.py')
environment=importlib.util.module_from_spec(spec)
spec.loader.exec_module(environment)


class Refresh(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.original={name:getattr(environment,name) for name in
            ('REPO','BUILD','BACKUP','PACKAGE','TOOLKIT_REPORT','LEGACY_DEPLOY_ARCHIVE','check_closed')}
        self.addCleanup(lambda:[setattr(environment,name,value) for name,value in self.original.items()])
        environment.REPO=root
        environment.BUILD=root/'build/sword-cultivator'
        environment.BACKUP=environment.BUILD/'test-environment'
        environment.PACKAGE=root/'local/Mods/EasternSwordCultivator.pak'
        environment.TOOLKIT_REPORT=environment.BUILD/'toolkit-validation.json'
        environment.LEGACY_DEPLOY_ARCHIVE=environment.BUILD/'prior-release-20261001-005752'
        environment.check_closed=lambda:None
        environment.PACKAGE.parent.mkdir(parents=True)
        environment.BACKUP.mkdir(parents=True)
        environment.LEGACY_DEPLOY_ARCHIVE.mkdir(parents=True)
        self.old=b'previous toolkit-verified ESC PAK'
        self.new=b'new toolkit-verified ESC PAK'
        environment.PACKAGE.write_bytes(self.old)
        self.other=root/'local/Mods/unrelated.pak';self.other.write_bytes(b'keep unrelated PAK')
        self.settings=root/'local/modsettings.lsx';self.settings.write_bytes(b'keep modsettings')
        self.se=root/'game/bin/ScriptExtenderSettings.json';self.se.parent.mkdir(parents=True)
        self.se.write_bytes(b'keep extender settings')
        self.write_package(environment.LEGACY_DEPLOY_ARCHIVE,self.old)
        self.write_package(environment.BUILD,self.new)
        state={'active':True,'files':[{'key':'pak','path':str(environment.PACKAGE),'existed':False}],
               'existing_paks':{'unrelated.pak':environment.digest(self.other)}}
        (environment.BACKUP/'state.json').write_text(json.dumps(state),encoding='utf-8')
        loose=environment.REPO/'build/sword-cultivator/toolkit-environment/state.json'
        loose.parent.mkdir(parents=True);loose.write_text('{"active":false}',encoding='utf-8')

    def write_package(self,directory,contents,failed=None):
        directory.mkdir(parents=True,exist_ok=True)
        package=directory/'EasternSwordCultivator.pak';package.write_bytes(contents)
        sha=environment.digest(package)
        cases={name:{'Status':'fail' if name==failed else 'pass','Evidence':['real editor evidence']}
               for name in environment.TOOLKIT_CASES}
        (directory/'toolkit-validation.json').write_text(json.dumps(
            {'Status':'pass','PackageSHA256':sha,'Cases':cases}),encoding='utf-8')
        (directory/'build-report.json').write_text(json.dumps({'SHA256':sha}),encoding='utf-8')
        return sha

    def state(self):
        return json.loads((environment.BACKUP/'state.json').read_text(encoding='utf-8'))

    def test_legacy_owned_package_refreshes_only_esc_pak_and_keeps_rollback(self):
        old_sha=environment.digest(environment.PACKAGE)
        new_sha=environment.digest(environment.BUILD/'EasternSwordCultivator.pak')
        environment.refresh()
        self.assertEqual(environment.PACKAGE.read_bytes(),self.new)
        self.assertEqual(self.other.read_bytes(),b'keep unrelated PAK')
        self.assertEqual(self.settings.read_bytes(),b'keep modsettings')
        self.assertEqual(self.se.read_bytes(),b'keep extender settings')
        state=self.state()
        self.assertEqual(state['deployed_pak_sha256'],new_sha)
        self.assertNotIn('pending_refresh',state)
        self.assertEqual(len(state['refresh_history']),1)
        self.assertEqual(state['refresh_history'][0]['source'],'prior-release-20261001-005752')
        self.assertEqual(Path(state['refresh_history'][0]['backup']).read_bytes(),self.old)
        self.assertTrue(Path(state['refresh_history'][0]['report']).is_file())
        self.assertEqual(json.loads(Path(state['refresh_history'][0]['report']).read_text(encoding='utf-8'))['next_sha256'],new_sha)
        self.assertEqual(environment.digest(Path(state['refresh_history'][0]['backup'])),old_sha)

    def test_user_swapped_package_is_rejected_before_any_write(self):
        environment.PACKAGE.write_bytes(b'user replacement')
        before=(environment.BACKUP/'state.json').read_bytes()
        with self.assertRaisesRegex(SystemExit,'Untracked installed PAK'):
            environment.refresh()
        self.assertEqual(environment.PACKAGE.read_bytes(),b'user replacement')
        self.assertEqual((environment.BACKUP/'state.json').read_bytes(),before)
        self.assertFalse((environment.BACKUP/'package-upgrades').exists())

    def test_new_package_requires_all_five_toolkit_cases(self):
        self.write_package(environment.BUILD,self.new,failed='spells_and_icons')
        with self.assertRaisesRegex(SystemExit,'five required editor checks'):
            environment.refresh()
        self.assertEqual(environment.PACKAGE.read_bytes(),self.old)
        self.assertNotIn('pending_refresh',self.state())

    def test_loose_toolkit_environment_blocks_refresh(self):
        loose=environment.REPO/'build/sword-cultivator/toolkit-environment/state.json'
        loose.write_text('{"active":true}',encoding='utf-8')
        with self.assertRaisesRegex(SystemExit,'loose source'):
            environment.refresh()
        self.assertEqual(environment.PACKAGE.read_bytes(),self.old)

    def test_next_refresh_uses_recorded_last_deployed_sha(self):
        environment.refresh()
        second=b'second approved ESC PAK'
        second_sha=self.write_package(environment.BUILD,second)
        environment.refresh()
        self.assertEqual(environment.PACKAGE.read_bytes(),second)
        state=self.state()
        self.assertEqual(state['deployed_pak_sha256'],second_sha)
        self.assertEqual(len(state['refresh_history']),2)
        self.assertEqual(state['refresh_history'][1]['source'],'state')
        self.assertEqual(Path(state['refresh_history'][1]['backup']).read_bytes(),self.new)

    def test_replace_failure_keeps_installed_pak_and_clears_pending_state(self):
        original_replace=environment.os.replace
        def fail_package_replace(source,target):
            if Path(target)==environment.PACKAGE:raise OSError('simulated locked PAK')
            return original_replace(source,target)
        with patch.object(environment.os,'replace',side_effect=fail_package_replace):
            with self.assertRaisesRegex(OSError,'simulated locked PAK'):
                environment.refresh()
        self.assertEqual(environment.PACKAGE.read_bytes(),self.old)
        self.assertNotIn('pending_refresh',self.state())
        self.assertEqual(self.state()['deployed_pak_sha256'],environment.digest(environment.PACKAGE))
        self.assertEqual(len(list((environment.BACKUP/'package-upgrades').glob('*.pak'))),1)


if __name__=='__main__':unittest.main()
