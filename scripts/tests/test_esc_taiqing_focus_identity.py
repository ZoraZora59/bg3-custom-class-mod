"""Taiqing focus resolves native Name_GUID and ECS GUID references to one entity.

This runs the real Engine/Runtime against the existing simulated boundary. The
lookup aliases reproduce the read-only native snapshot; these are not game tests.
"""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


REPO = next(p for p in Path(__file__).resolve().parents
            if (p / 'scripts/tests/test_esc_bridge.py').is_file())
sys.path.insert(0, str(REPO / 'scripts/tests'))
import test_esc_bridge as bridge


# Native snapshot 20261008T044419490036Z-B5B-focus-verified-before-taiqing-dap:
# Name_GUID and bare GUID both resolved to this entity; raw equality was false.
GOBLIN = 'd764e091-3386-cd8e-70c5-7a3e067848d9'
NAMED_GOBLIN = 'Goblins_Male_Guard_' + GOBLIN
OTHER = 'dfd44248-1212-4eb9-a6b4-8d7335ad57f7'
NAMED_OTHER = 'S_TUT_Helm_BackUpCambion_001_' + OTHER
PULSE = 'Target_ESC_TaiqingPulse'


class TaiqingFocusIdentity(unittest.TestCase):
    def setUp(self):
        runtime = Path(os.environ.get('ESC_TAIQING_RUNTIME_CANDIDATE', bridge.LUA / 'Runtime.lua'))
        snapshot = dict(bridge.SNAPSHOT)
        snapshot['Runtime.lua'] = runtime.read_bytes()
        with patch.object(bridge, 'SNAPSHOT', snapshot):
            bridge.Bridge.setUp(self)
        self.actor(branch='taixuan')
        self.actor(GOBLIN, level=0, party='enemies', hp=1000, maximum=1000, x=2)
        self.actor(OTHER, level=0, party='enemies', hp=1000, maximum=1000, x=3)
        # Only reproduce the documented Entity.Get reference lookup. Keep one
        # canonical entity per UUID in the fixture so nearby enumeration is real.
        # Do not mock E.sameEntity, Runtime.Pulse, or inspect source text.
        self.lua.globals().Fixture.entityAliases = self.table({
            NAMED_GOBLIN: GOBLIN, NAMED_OTHER: OTHER,
        })
        self.lua.execute('''
            local originalGet = Ext.Entity.Get
            function Ext.Entity.Get(ref)
                local alias = type(ref)=='string' and Fixture.entityAliases[ref]
                return originalGet(alias or ref)
            end
        ''')

    table = bridge.Bridge.table
    actor = bridge.Bridge.actor
    cast = bridge.Bridge.cast

    def pulse_counts(self):
        counts = {}
        for call in self.F.calls.values():
            if call.name == 'UseSpell' and call.args[2] == PULSE:
                self.assertEqual(call.args[1], 'sword')
                counts[call.args[3]] = counts.get(call.args[3], 0) + 1
        return counts

    def test_opening_named_focus_gets_three_native_attacks_other_enemy_gets_one(self):
        self.ESC.State('sword').focus = NAMED_GOBLIN  # Legacy saved focus.
        self.assertEqual(self.ESC.State('sword').focus, NAMED_GOBLIN)
        self.assertNotEqual(NAMED_GOBLIN, GOBLIN)
        # Check actual Entity.Get identities, not a hand-coded suffix comparator.
        self.assertEqual(self.E.uuid(self.E.entity(NAMED_GOBLIN)), GOBLIN)
        self.F.clearCalls()
        self.cast('sword', 'taixuan_taiqing', action=502)
        self.assertEqual(self.pulse_counts(), {GOBLIN: 3, OTHER: 1})

    def test_bare_guid_focus_keeps_existing_three_attack_behavior(self):
        self.ESC.State('sword').focus = GOBLIN
        self.F.clearCalls()
        self.cast('sword', 'taixuan_taiqing', action=512)
        self.assertEqual(self.pulse_counts(), {GOBLIN: 3, OTHER: 1})

    def test_paid_named_attack_switch_changes_only_next_pulse_target(self):
        self.ESC.State('sword').focus = NAMED_GOBLIN
        self.cast('sword', 'taixuan_taiqing', action=522)
        expires = self.ESC.State('sword').domains.taixuan_taiqing.expires
        self.ESC.Runtime.BeginCast('sword', 'Projectile_ESC_taixuan_zhaoxi', 523, NAMED_OTHER)
        self.ESC.Runtime.FinishCast('sword', 'Projectile_ESC_taixuan_zhaoxi', 523)
        self.F.clearCalls()
        self.ESC.Runtime.Pulse('sword', 'taixuan_taiqing')
        self.assertEqual(self.pulse_counts(), {GOBLIN: 1, OTHER: 3})
        self.assertEqual(self.ESC.State('sword').domains.taixuan_taiqing.expires, expires)

    def test_named_focus_gets_four_pulses_then_expires_before_fifth(self):
        self.ESC.State('sword').focus = NAMED_GOBLIN
        self.F.clearCalls()
        self.cast('sword', 'taixuan_taiqing', action=532)
        for _ in range(3):
            self.F.emit('TurnStarted', 'sword')
            # Advance the queued event boundary before the following turn.
            timer = [t for t in self.F.timers.values() if t.ms == 1][-1]
            timer.callback()
        self.assertEqual(self.pulse_counts(), {GOBLIN: 12, OTHER: 4})
        self.assertIsNotNone(self.ESC.State('sword').domains.taixuan_taiqing)
        self.F.emit('TurnStarted', 'sword')
        self.assertIsNone(self.ESC.State('sword').domains.taixuan_taiqing)
        self.assertEqual(self.pulse_counts(), {GOBLIN: 12, OTHER: 4})

    def test_unresolved_named_focus_selects_nearest_live_enemy_on_open(self):
        # A stale saved focus now falls back to the nearest valid enemy on open.
        self.ESC.State('sword').focus = 'gone'
        self.F.clearCalls()
        self.cast('sword', 'taixuan_taiqing', action=542)
        self.assertEqual(self.pulse_counts(), {GOBLIN: 3, OTHER: 1})
