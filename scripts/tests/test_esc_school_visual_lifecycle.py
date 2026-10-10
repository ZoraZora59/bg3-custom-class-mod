"""Dedicated school-domain VFX follows gameplay state in the simulated Lua engine.

The tests exercise production Runtime. They cannot prove native status events,
render attachment, loop cleanup or accurate game save timing.
"""
import copy
import unittest
from unittest.mock import patch

import test_esc_bridge as bridge

VISUAL = 'ESC_VFX_BLOOD_DOMAIN'
SWORD_VISUAL = 'ESC_VFX_SWORD_DOMAIN'


class SchoolVisualLifecycle(unittest.TestCase):
    def setUp(self):
        spec = copy.deepcopy(bridge.SPEC)
        spec['schoolPolishVfx'] = {'enabled': True}
        # Bridge caches its Lua snapshot at import. Capture the production file
        # here as well so a focused run cannot accidentally exercise old Lua.
        snapshot = dict(bridge.SNAPSHOT)
        snapshot['Runtime.lua'] = (bridge.LUA / 'Runtime.lua').read_bytes()
        with patch.object(bridge, 'SPEC', spec), patch.object(bridge, 'SNAPSHOT', snapshot):
            bridge.Bridge.setUp(self)
        for status in (VISUAL, SWORD_VISUAL):
            self.F.stats[status] = self.table({'StatusType': 'BOOST', 'Boosts': '',
                'StatusPropertyFlags': 'DisableCombatlog;DisablePortraitIndicator;DisableOverhead'})
        self.actor(level=11, branch='xueyan', hp=30)

    table = bridge.Bridge.table
    actor = bridge.Bridge.actor
    cast = bridge.Bridge.cast
    native_damage = bridge.Bridge.native_damage

    def active(self, status=VISUAL):
        return self.E.hasStatus('sword', status)

    def domain(self, action=101):
        self.cast('sword', 'xueyan_xuehai', action=action)

    def visual_calls(self, name, status=VISUAL):
        return [c for c in self.F.calls.values() if c.name == name and c.args[2] == status]

    def sword_domain(self, action=201):
        self.F.entities['sword'].Classes.Classes[1].SubClassUUID = bridge.SPEC['classes']['taixuan']
        self.cast('sword', 'taixuan_taiqing', action=action)

    def test_siphon_keeps_healing_yuan_shield_and_blood_robe_without_domain_ring(self):
        self.actor('enemy', level=0, party='enemies', hp=100)
        stat = bridge.SPEC['spells']['xueyan_luexue']['stat']
        self.native_damage('sword', 'enemy', [1], spell=stat, action=91)
        self.native_damage('sword', 'enemy', [1], spell=stat, action=91)
        self.F.emit('StatusApplied', 'enemy', 'ESC_HIT_MARKER', 'sword', 91)
        self.ESC.Runtime.UpdateAuras()
        self.assertEqual(self.F.entities['enemy']._hp, 98)
        self.assertEqual(self.F.entities['sword']._hp, 31)
        self.assertEqual(self.F.resource('sword').Amount, 2)
        self.assertEqual(self.ESC.State('sword').shield, 1)
        self.assertTrue(self.E.hasStatus('sword', 'ESC_BLOOD_ROBE'))
        self.assertFalse(self.active())
        self.assertEqual(self.visual_calls('ApplyStatus'), [])

    def test_open_domain_applies_one_visual_without_refreshing_on_updates(self):
        self.domain()
        self.assertTrue(self.active())
        applied = self.visual_calls('ApplyStatus')
        self.assertEqual(len(applied), 1)
        self.assertEqual(applied[0].args[3], -1)
        self.assertEqual(applied[0].args[5], 'sword')
        self.ESC.Runtime.UpdateAuras()
        self.ESC.Runtime.UpdateAuras()
        self.assertEqual(len(self.visual_calls('ApplyStatus')), 1)

    def test_four_owner_turns_expire_domain_visual_on_the_existing_domain_clock(self):
        self.domain()
        for _ in range(3):
            self.F.emit('TurnStarted', 'sword')
            self.assertTrue(self.active())
        self.F.emit('TurnStarted', 'sword')
        self.assertFalse(self.active())
        self.assertEqual(len(self.visual_calls('RemoveStatus')), 1)

    def test_visual_sync_never_changes_hp_yuan_or_siphon_shield(self):
        self.domain()
        state = self.ESC.State('sword')
        state.shield = 7
        state.shieldUntil = 100
        before_hp, before_yuan = self.F.entities['sword']._hp, self.F.resource('sword').Amount
        # Synchronizing a visual status cannot consume or reset gameplay pools.
        self.ESC.Runtime.UpdateAuras()
        self.assertEqual(state.shield, 7)
        self.assertEqual(self.F.entities['sword']._hp, before_hp)
        self.assertEqual(self.F.resource('sword').Amount, before_yuan)
        state.turn = 4
        self.ESC.Runtime.UpdateAuras()
        self.assertFalse(self.active())
        self.assertEqual(state.shield, 7)
        self.assertEqual(self.F.entities['sword']._hp, before_hp)
        self.assertEqual(self.F.resource('sword').Amount, before_yuan)

    def test_death_notification_removes_visual_with_existing_domain_cleanup(self):
        self.domain()
        self.F.entities['sword']._dead = True
        self.F.emit('StatusApplied', 'sword', 'DEAD', 'enemy', 103)
        self.assertFalse(self.active())
        self.assertIsNone(self.ESC.State('sword').domains['xueyan_xuehai'])

    def test_subclass_change_removes_ring_at_respec_event(self):
        self.domain()
        self.F.entities['sword'].Classes.Classes[1].SubClassUUID = bridge.SPEC['classes']['taixuan']
        self.F.emit('RespecCompleted', 'sword')
        self.assertFalse(self.active())
        # Existing gameplay state is unchanged by the presentation sync itself.
        self.assertIsNotNone(self.ESC.State('sword').domains['xueyan_xuehai'])

    def test_class_removal_removes_ring_at_respec_event(self):
        self.domain()
        self.F.entities['sword'].Classes.Classes = self.table([])
        self.F.emit('RespecCompleted', 'sword')
        self.assertFalse(self.active())

    def test_equipment_pause_hides_ring_and_resume_restores_only_active_domain(self):
        self.domain()
        self.F.entities['sword']._equipped.Shield = 'shield'
        self.F.emit('Equipped', 'shield', 'sword')
        self.assertFalse(self.active())
        self.F.entities['sword']._equipped.Shield = None
        self.F.emit('Unequipped', 'shield', 'sword')
        self.assertTrue(self.active())
        self.ESC.State('sword').turn = 4
        self.ESC.Runtime.UpdateAuras()
        self.assertFalse(self.active())

    def test_session_reload_restores_missing_visual_for_active_domain_once(self):
        self.domain()
        self.lua.globals().Osi.RemoveStatus('sword', VISUAL, 'sword')
        self.F.clearCalls()
        self.F.event('SessionLoaded', self.table({}))
        self.assertTrue(self.active())
        self.F.event('SessionLoaded', self.table({}))
        self.assertEqual(len(self.visual_calls('ApplyStatus')), 1)

    def test_session_reload_removes_stale_visual_after_domain_deadline(self):
        self.domain()
        self.ESC.State('sword').turn = 4
        self.F.event('SessionLoaded', self.table({}))
        self.assertFalse(self.active())

    def test_disabled_or_unregistered_visual_assets_never_apply_and_clear_stale_status(self):
        self.domain()
        self.lua.globals().GeneratedSpec.schoolPolishVfx.enabled = False
        self.F.clearCalls()
        self.ESC.Runtime.UpdateAuras()
        self.assertFalse(self.active())
        self.assertEqual(self.visual_calls('ApplyStatus'), [])
        self.lua.globals().GeneratedSpec.schoolPolishVfx.enabled = True
        self.F.stats[VISUAL] = None
        self.ESC.Runtime.UpdateAuras()
        self.assertFalse(self.active())
        self.assertEqual(self.visual_calls('ApplyStatus'), [])

    def test_taiqing_open_domain_applies_once_and_never_refreshes_its_visual(self):
        self.sword_domain()
        self.assertTrue(self.active(SWORD_VISUAL))
        self.assertFalse(self.active(VISUAL))
        self.ESC.Runtime.UpdateAuras()
        self.ESC.Runtime.UpdateAuras()
        calls = self.visual_calls('ApplyStatus', SWORD_VISUAL)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].args[3], -1)

    def test_taiqing_deadline_clears_visual_even_with_old_native_status_present(self):
        self.sword_domain()
        self.ESC.State('sword').turn = 4
        self.assertTrue(self.E.hasStatus('sword', 'ESC_SWORD_DOMAIN'))
        self.ESC.Runtime.UpdateAuras()
        self.assertFalse(self.active(SWORD_VISUAL))
        self.assertTrue(self.E.hasStatus('sword', 'ESC_SWORD_DOMAIN'))

    def test_taiqing_incapacitation_cleans_visual_while_preserving_native_status(self):
        for index, status in enumerate(('DOWNED', 'DYING', 'DEAD')):
            with self.subTest(status=status):
                self.setUp()
                self.sword_domain(action=202+index)
                if status == 'DEAD':
                    self.F.entities['sword']._dead = True
                self.F.emit('StatusApplied', 'sword', status, 'enemy', 211+index)
                self.assertFalse(self.active(SWORD_VISUAL))
                self.assertIsNone(self.ESC.State('sword').domains['taixuan_taiqing'])
                self.assertTrue(self.E.hasStatus('sword', 'ESC_SWORD_DOMAIN'))

    def test_taiqing_subclass_change_removes_visual_without_touching_old_status(self):
        self.sword_domain()
        self.F.entities['sword'].Classes.Classes[1].SubClassUUID = bridge.SPEC['classes']['xueyan']
        self.F.emit('RespecCompleted', 'sword')
        self.assertFalse(self.active(SWORD_VISUAL))
        self.assertTrue(self.E.hasStatus('sword', 'ESC_SWORD_DOMAIN'))
        self.assertIsNotNone(self.ESC.State('sword').domains['taixuan_taiqing'])

    def test_taiqing_class_removal_cleans_visual_at_respec_completion(self):
        self.sword_domain()
        self.F.entities['sword'].Classes.Classes = self.table([])
        self.F.emit('RespecCompleted', 'sword')
        self.assertFalse(self.active(SWORD_VISUAL))

    def test_taiqing_shield_and_medium_heavy_armor_pause_then_restore_active_visual(self):
        for equipment in ('Shield', 'MediumArmor', 'HeavyArmor'):
            with self.subTest(equipment=equipment):
                self.setUp()
                self.sword_domain()
                actor = self.F.entities['sword']
                if equipment == 'Shield':
                    actor._equipped.Shield = 'shield'
                else:
                    armor = self.actor('armor', level=0)
                    armor._proficiencies = self.table({equipment: True})
                    actor._equipped.Breast = 'armor'
                self.F.emit('Equipped', 'armor' if equipment != 'Shield' else 'shield', 'sword')
                self.assertFalse(self.active(SWORD_VISUAL))
                self.assertTrue(self.E.hasStatus('sword', 'ESC_SWORD_DOMAIN'))
                actor._equipped.Shield = None
                actor._equipped.Breast = None
                self.F.emit('Unequipped', 'armor', 'sword')
                self.assertTrue(self.active(SWORD_VISUAL))
                self.assertEqual(len(self.visual_calls('ApplyStatus', SWORD_VISUAL)), 2)

    def test_taiqing_reload_restores_active_visual_once_and_cleans_expired_visual(self):
        self.sword_domain()
        self.lua.globals().Osi.RemoveStatus('sword', SWORD_VISUAL, 'sword')
        self.F.clearCalls()
        self.F.event('SessionLoaded', self.table({}))
        self.assertTrue(self.active(SWORD_VISUAL))
        self.F.event('SessionLoaded', self.table({}))
        self.assertEqual(len(self.visual_calls('ApplyStatus', SWORD_VISUAL)), 1)
        self.ESC.State('sword').turn = 4
        self.F.event('SessionLoaded', self.table({}))
        self.assertFalse(self.active(SWORD_VISUAL))

    def test_native_realtime_expiry_ends_domain_and_visual_without_owner_turn(self):
        self.sword_domain()
        self.lua.globals().Osi.RemoveStatus('sword', 'ESC_SWORD_DOMAIN', 'sword')
        self.F.emit('StatusRemoved', 'sword', 'ESC_SWORD_DOMAIN', 'sword', 201)
        self.assertEqual(self.ESC.State('sword').turn, 0)
        self.assertIsNone(self.ESC.State('sword').domains.taixuan_taiqing)
        self.assertFalse(self.active(SWORD_VISUAL))
        self.ESC.Runtime.UpdateAuras()
        self.assertFalse(self.active(SWORD_VISUAL))

    def test_delayed_old_removal_does_not_end_live_recast(self):
        self.sword_domain()
        self.sword_domain(action=202)
        sequence = self.ESC.State('sword').domains.taixuan_taiqing.sequence
        self.F.emit('StatusRemoved', 'sword', 'ESC_SWORD_DOMAIN', 'sword', 201)
        self.assertEqual(self.ESC.State('sword').domains.taixuan_taiqing.sequence, sequence)
        self.assertTrue(self.active(SWORD_VISUAL))

    def test_reload_does_not_restore_domain_whose_native_status_is_absent(self):
        self.sword_domain()
        # A save can retain the old script snapshot after native realtime expiry.
        self.lua.globals().Osi.RemoveStatus('sword', 'ESC_SWORD_DOMAIN', 'sword')
        self.F.event('SessionLoaded', self.table({}))
        self.assertIsNone(self.ESC.State('sword').domains.taixuan_taiqing)
        self.assertFalse(self.active(SWORD_VISUAL))

    def test_blood_domain_expiry_preserves_siphon_shield(self):
        self.domain()
        self.ESC.State('sword').shield = 7
        self.ESC.State('sword').shieldUntil = 100
        self.lua.globals().Osi.RemoveStatus('sword', 'ESC_BLOOD_ROBE', 'sword')
        self.F.emit('StatusRemoved', 'sword', 'ESC_BLOOD_ROBE', 'sword', 101)
        self.assertIsNone(self.ESC.State('sword').domains.xueyan_xuehai)
        self.assertFalse(self.active())
        self.assertEqual(self.ESC.State('sword').shield, 7)

    def test_taiqing_assets_missing_or_disabled_cannot_apply_visual(self):
        self.sword_domain()
        self.lua.globals().GeneratedSpec.schoolPolishVfx.enabled = False
        self.ESC.Runtime.UpdateAuras()
        self.assertFalse(self.active(SWORD_VISUAL))
        self.lua.globals().GeneratedSpec.schoolPolishVfx.enabled = True
        self.F.stats[SWORD_VISUAL] = None
        self.F.clearCalls()
        self.ESC.Runtime.UpdateAuras()
        self.assertFalse(self.active(SWORD_VISUAL))
        self.assertEqual(self.visual_calls('ApplyStatus', SWORD_VISUAL), [])


if __name__ == '__main__':
    unittest.main()
