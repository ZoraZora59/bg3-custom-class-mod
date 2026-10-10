"""Replay H19's Bloodsea turn boundary with the actual production Runtime.

The fixture may reject ImmediateCast during TurnStarted; timers advance only
when explicitly invoked. This is regression evidence, not native acceptance.
"""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts/tests'))
import test_esc_bridge as bridge

BLOOD = 'Target_ESC_BloodPulse'
KEY = 'xueyan_xuehai'


class BloodseaTurnStartDelay(unittest.TestCase):
    table = bridge.Bridge.table
    actor = bridge.Bridge.actor
    cast = bridge.Bridge.cast
    native_damage = bridge.Bridge.native_damage

    def setUp(self):
        snapshot = dict(bridge.SNAPSHOT)
        candidate = Path(os.environ.get('ESC_BLOODSEA_RUNTIME_CANDIDATE', bridge.LUA / 'Runtime.lua'))
        snapshot['Runtime.lua'] = candidate.read_bytes()
        with patch.object(bridge, 'SNAPSHOT', snapshot):
            bridge.Bridge.setUp(self)
        self.owner = self.actor(branch='xueyan', hp=100)
        self.enemy = self.actor('enemy', 0, None, 1000, 1000, 'enemies', 1.4)
        self.other = self.actor('other', 0, None, 1000, 1000, 'enemies', 3)
        self.F.resource('sword').Amount = 30

    def timers(self):
        return [t for t in self.F.timers.values() if t.ms == 1]

    def pulses(self, source='sword'):
        return [c.args[3] for c in self.F.calls.values()
                if c.name == 'UseSpell' and c.args[1] == source and c.args[2] == BLOOD]

    def open(self):
        self.cast('sword', KEY, action=71)
        self.assertCountEqual(self.pulses(), ['enemy', 'other'])
        self.F.timers = self.table([])
        self.F.clearCalls()

    def queue(self):
        self.F.emit('TurnStarted', 'sword')
        self.assertEqual(self.pulses(), [])
        self.assertTrue(self.timers(), 'Bloodsea must leave the native turn event')
        return self.timers()[-1]

    def test_native_boundary_rejects_inline_dispatch_but_accepts_delayed_helper(self):
        self.open()
        self.lua.execute('''
            Fixture.inlineRejected=0
            local native=Osi.UseSpell
            function Osi.UseSpell(...)
                if Fixture.inTurnEvent then Fixture.inlineRejected=Fixture.inlineRejected+1;return end
                return native(...)
            end
            Fixture.inTurnEvent=true
        ''')
        timer = self.queue()
        self.lua.execute('Fixture.inTurnEvent=false')
        self.assertEqual(self.F.inlineRejected, 0)
        timer.callback()
        self.assertCountEqual(self.pulses(), ['enemy', 'other'])
        self.assertEqual(self.F.resource('sword').Amount, 30)
        self.assertEqual(self.F.callCount('ApplyDamage'), 0)
        self.assertEqual(self.F.callCount('SetHitpoints'), 0)

    def test_opening_plus_three_turn_batches_then_fourth_turn_expires(self):
        self.open()
        total = 2
        for _ in range(3):
            self.F.clearCalls()
            timer = self.queue()
            timer.callback()
            self.assertCountEqual(self.pulses(), ['enemy', 'other'])
            total += len(self.pulses())
        self.F.clearCalls()
        before = len(self.timers())
        self.F.emit('TurnStarted', 'sword')
        self.assertIsNone(self.ESC.State('sword').domains[KEY])
        self.assertEqual(len(self.timers()), before)
        self.assertEqual(self.pulses(), [])
        self.assertEqual(total, 8)

    def test_duplicate_callback_is_consumed_without_retry(self):
        self.open()
        timer = self.queue()
        timer.callback()
        timer.callback()
        self.assertCountEqual(self.pulses(), ['enemy', 'other'])
        self.assertEqual(len(self.timers()), 1)

    def test_next_turn_supersedes_old_pending_callback(self):
        self.open()
        old = self.queue()
        current = self.queue()
        old.callback()
        self.assertEqual(self.pulses(), [])
        current.callback()
        self.assertCountEqual(self.pulses(), ['enemy', 'other'])

    def test_same_turn_recast_cancels_old_domain_sequence(self):
        self.open()
        old = self.queue()
        sequence = self.ESC.State('sword').domains[KEY].sequence
        self.cast('sword', KEY, action=72)
        self.assertNotEqual(self.ESC.State('sword').domains[KEY].sequence, sequence)
        self.F.clearCalls()
        old.callback()
        self.assertEqual(self.pulses(), [])

    def test_cancellation_checks_live_owner_domain_turn_and_equipment(self):
        invalidations = (
            "ESC.State('sword').domains.xueyan_xuehai=nil",
            "ESC.State('sword').domains.xueyan_xuehai.expires=ESC.State('sword').turn",
            "ESC.State('sword').turn=ESC.State('sword').turn+1",
            "Fixture.entities.sword._dead=true",
            "Fixture.entities.sword._combat=false",
            "Fixture.entities.sword.TurnBased.IsActiveCombatTurn=false",
            "Fixture.entities.sword.TurnBased=nil",
            "Fixture.entities.sword.Classes.Classes[1].SubClassUUID=GeneratedSpec.classes.taixuan",
            "Fixture.entities.sword._equipped.Shield='shield'",
            "Fixture.entities.sword=nil",
        )
        for code in invalidations:
            with self.subTest(code=code):
                self.setUp()
                self.open()
                timer = self.queue()
                self.lua.execute(code)
                before = len(self.timers())
                timer.callback()
                self.assertEqual(self.pulses(), [])
                self.assertEqual(len(self.timers()), before)

    def test_native_status_removal_cancels_pending_and_future_pulses(self):
        self.open()
        timer = self.queue()
        self.lua.globals().Osi.RemoveStatus('sword', 'ESC_BLOOD_ROBE', 'sword')
        self.F.emit('StatusRemoved', 'sword', 'ESC_BLOOD_ROBE', 'sword', 71)
        timer.callback()
        self.assertEqual(self.pulses(), [])
        before = len(self.timers())
        self.F.emit('TurnStarted', 'sword')
        self.assertEqual(len(self.timers()), before)

    def test_delayed_query_uses_actual_radius_and_living_hostile_targets(self):
        self.open()
        timer = self.queue()
        self.enemy.Transform.Transform.Translate[1] = 6.1
        self.other._dead = True
        self.actor('friend', 0, None, 100, 100, 'players', 1)
        self.actor('entered', 0, None, 100, 100, 'enemies', 5.9)
        timer.callback()
        self.assertEqual(self.pulses(), ['entered'])

    def test_native_damage_after_delayed_dispatch_uses_current_frenzy(self):
        self.ESC.State('sword').frenzy = 4
        self.open()
        timer = self.queue()
        self.ESC.State('sword').frenzy = 0
        timer.callback()
        hit = self.native_damage('sword', 'enemy', [20], spell=BLOOD, action=82)
        self.assertEqual(hit.TotalDamageDone, 23)
        self.assertEqual(len(self.pulses()), 2)

    def test_two_owners_keep_independent_pending_turns(self):
        self.open()
        first = self.queue()
        self.actor('blood2', branch='xueyan', hp=100)
        self.cast('blood2', KEY, action=73)
        self.F.clearCalls()
        self.F.emit('TurnStarted', 'blood2')
        second = self.timers()[-1]
        second.callback()
        first.callback()
        self.assertCountEqual(self.pulses(), ['enemy', 'other'])
        self.assertCountEqual(self.pulses('blood2'), ['enemy', 'other'])

    def test_session_reload_invalidates_old_timer(self):
        self.open()
        old = self.queue()
        self.ESC.Runtime.SessionLoaded()
        old.callback()
        self.assertEqual(self.pulses(), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
