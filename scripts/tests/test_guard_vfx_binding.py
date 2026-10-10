"""Verify guard visuals only use registered, compiled effect phases."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sword_vfx_bindings import guard_status_effect, mei_guid


class GuardVfxBinding(unittest.TestCase):
    def test_uncompiled_status_keeps_native_fallback(self):
        self.assertEqual(guard_status_effect({('common', 'projectile'), ('common', 'impact')}),
                         '87356553-5bed-4e2b-86eb-f0697e5ec648')

    def test_other_branch_status_does_not_enable_common_guard(self):
        self.assertEqual(guard_status_effect({('taixuan', 'status')}), guard_status_effect(set()))

    def test_compiled_common_status_uses_mei(self):
        self.assertEqual(guard_status_effect({('common', 'status')}), mei_guid('common', 'status'))


if __name__ == '__main__':
    unittest.main()
