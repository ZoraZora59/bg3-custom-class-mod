"""Toolkit log capture tests use temporary paths and never touch the game."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts'))
spec = importlib.util.spec_from_file_location(
    'esc_toolkit_log_capture', REPO / 'scripts/sword-toolkit-environment.py')
environment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(environment)


class ToolkitLogCapture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        original = {name: getattr(environment, name) for name in
                    ('DATA', 'TOOLKIT', 'BASE', 'STATE')}
        self.addCleanup(lambda: [setattr(environment, name, value)
                                 for name, value in original.items()])
        environment.DATA = root / 'game/Data'
        environment.TOOLKIT = root / 'toolkit'
        environment.BASE = root / 'snapshots'
        environment.STATE = environment.BASE / 'state.json'
        environment.TOOLKIT.mkdir(parents=True)
        environment.BASE.mkdir(parents=True)
        self.start = datetime.now() - timedelta(minutes=30)

    def state(self, **overrides):
        state = dict(active=True, installed_at=self.start.isoformat(),
                     backup=str(environment.BASE / ('backup-' + self.start.strftime('%Y%m%d-%H%M%S-%f'))))
        state.update(overrides)
        environment.STATE.write_text(json.dumps(state), encoding='utf-8')

    def log(self, prefix, when, suffix, contents=b'log', modified=None):
        path = environment.TOOLKIT / (
            prefix + '.' + when.strftime('%Y-%m-%dT%H-%M-%S-%f') + '.' + suffix)
        path.write_bytes(contents)
        if modified is not None:
            os.utime(path, (modified.timestamp(), modified.timestamp()))
        return path

    def captured(self):
        environment.capture()
        snapshot = sorted(environment.BASE.glob('capture-*'))[-1]
        report = json.loads((snapshot / 'capture.json').read_text(encoding='utf-8'))
        return snapshot, report['log_evidence']

    def test_stale_name_is_not_rescued_by_new_modification_time(self):
        self.state()
        old = self.log('log', self.start - timedelta(minutes=5), 'txt',
                       b'previous round', modified=datetime.now())
        fresh = self.log('osirislog', self.start + timedelta(minutes=2), 'log',
                         b'this round')
        snapshot, evidence = self.captured()
        self.assertFalse((snapshot / 'logs' / old.name).exists())
        self.assertEqual((snapshot / 'logs' / fresh.name).read_bytes(), b'this round')
        self.assertEqual(evidence['patterns']['log.*.txt']['status'], 'stale')
        self.assertEqual(evidence['patterns']['log.*.txt']['candidates'][0]['status'], 'stale')
        self.assertEqual(evidence['patterns']['osirislog.*.log']['status'], 'captured')
        self.assertEqual(evidence['patterns']['thothlog.*.txt']['status'], 'missing')
        self.assertEqual(evidence['time_source'], 'installed_at')
        self.assertFalse(evidence['launch_time_directly_observed'])

    def test_latest_fresh_log_selected_and_hashed(self):
        self.state()
        older_time = self.start + timedelta(minutes=1)
        newer_time = self.start + timedelta(minutes=2)
        older = self.log('log', older_time, 'txt', b'first', modified=older_time)
        newer = self.log('log', newer_time, 'txt', b'second', modified=newer_time)
        snapshot, evidence = self.captured()
        group = evidence['patterns']['log.*.txt']
        self.assertEqual(group['status'], 'captured')
        self.assertEqual(group['selected']['name'], newer.name)
        self.assertEqual(group['selected']['sha256'], environment.digest(newer))
        self.assertEqual(len(group['candidates']), 2)
        self.assertFalse((snapshot / 'logs' / older.name).exists())

    def test_legacy_state_uses_backup_name_and_unknown_state_fails_closed(self):
        self.state(installed_at=None)
        current = self.log('thothlog', self.start + timedelta(minutes=1), 'txt')
        snapshot, evidence = self.captured()
        self.assertEqual(evidence['time_source'], 'backup_directory_name')
        self.assertEqual(evidence['patterns']['thothlog.*.txt']['status'], 'captured')
        self.assertTrue((snapshot / 'logs' / current.name).exists())

        self.state(installed_at=None, backup=str(environment.BASE / 'unknown'))
        snapshot2, evidence2 = self.captured()
        self.assertEqual(evidence2['time_source'], 'unavailable')
        self.assertEqual(evidence2['patterns']['thothlog.*.txt']['status'], 'unverifiable')
        self.assertFalse((snapshot2 / 'logs' / current.name).exists())

    def test_unknown_filename_requires_both_fresh_creation_and_modification(self):
        self.state()
        unknown = environment.TOOLKIT / 'log.custom.txt'
        unknown.write_bytes(b'new session with nonstandard filename')
        snapshot, evidence = self.captured()
        self.assertEqual(evidence['patterns']['log.*.txt']['status'], 'captured')
        self.assertEqual((snapshot / 'logs' / unknown.name).read_bytes(), unknown.read_bytes())
        self.assertIsNone(evidence['patterns']['log.*.txt']['selected']['filename_time'])


if __name__ == '__main__':
    unittest.main()
