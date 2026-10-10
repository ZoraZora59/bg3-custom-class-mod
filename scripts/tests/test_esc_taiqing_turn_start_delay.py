"""Candidate Runtime contracts at a deliberately simulated BG3 boundary.

Run from the repository with:
  python -m unittest discover -s <this directory> -p test_taiqing_turn_start_delay.py -v

The real candidate Engine/Runtime methods run in the existing Lupa fixture.
Only the event-loop/timer boundary is advanced explicitly. These assertions
establish callback scheduling and cancellation, never native hit acceptance.
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

CANDIDATE = Path(os.environ.get(
    'ESC_TAIQING_RUNTIME_CANDIDATE',
    str(bridge.LUA / 'Runtime.lua')))
PULSE = 'Target_ESC_TaiqingPulse'
BLOOD = 'Target_ESC_BloodPulse'


class TaiqingTurnStartDelay(unittest.TestCase):
    table = bridge.Bridge.table
    actor = bridge.Bridge.actor
    cast = bridge.Bridge.cast

    def setUp(self):
        snapshot = dict(bridge.SNAPSHOT)
        snapshot['Runtime.lua'] = CANDIDATE.read_bytes()
        with patch.object(bridge, 'SNAPSHOT', snapshot):
            bridge.Bridge.setUp(self)
        self.owner = self.actor(branch='taixuan', hp=100)
        self.enemy = self.actor('enemy', 0, None, 1000, 1000, 'enemies', 2)
        self.other = self.actor('other', 0, None, 1000, 1000, 'enemies', 3)
        self.ESC.State('sword').focus = 'enemy'
        self.runtime = self.ESC.Runtime

    def timers(self, ms=1):
        return [timer for timer in self.F.timers.values() if timer.ms == ms]

    def pulse_counts(self, spell=PULSE, source='sword'):
        counts = {}
        for call in self.F.calls.values():
            if call.name == 'UseSpell' and call.args[1] == source and call.args[2] == spell:
                counts[call.args[3]] = counts.get(call.args[3], 0) + 1
        return counts

    def open_domain(self):
        self.cast('sword', 'taixuan_taiqing', action=801)
        self.assertEqual(self.pulse_counts(), {'enemy': 3, 'other': 1})
        # Discard unrelated native cast retention/VFX timers from this fixture.
        self.F.timers = self.table([])
        self.F.clearCalls()

    def queue_turn(self):
        self.F.emit('TurnStarted', 'sword')
        self.assertEqual(self.pulse_counts(), {})
        timers = self.timers()
        self.assertTrue(timers, 'TurnStarted must queue one bounded 1 ms callback')
        return timers[-1]

    def assert_cancelled(self, timer):
        self.F.clearCalls()
        before = len(self.timers())
        timer.callback()
        self.assertEqual(self.pulse_counts(), {})
        self.assertEqual(len(self.timers()), before, 'Cancellation must not retry')

    def test_opening_stays_synchronous_with_domain_active_before_first_helper(self):
        self.F.clearCalls()
        self.cast('sword', 'taixuan_taiqing', action=802)
        self.assertEqual(self.pulse_counts(), {'enemy': 3, 'other': 1})
        self.assertEqual(self.timers(), [])
        calls = list(self.F.calls.values())
        status = next(i for i, call in enumerate(calls)
                      if call.name == 'ApplyStatus' and call.args[2] == 'ESC_SWORD_DOMAIN')
        first_pulse = next(i for i, call in enumerate(calls)
                           if call.name == 'UseSpell' and call.args[2] == PULSE)
        self.assertLess(status, first_pulse)
        self.assertEqual(self.ESC.State('sword').domains.taixuan_taiqing.expires, 4)

    def test_turn_emits_nothing_until_timer_then_three_focus_and_one_other(self):
        self.open_domain()
        timer = self.queue_turn()
        self.assertEqual(len(self.timers()), 1)
        self.F.clearCalls()
        yuan = self.F.resource('sword').Amount
        timer.callback()
        self.assertEqual(self.pulse_counts(), {'enemy': 3, 'other': 1})
        self.assertEqual(self.F.resource('sword').Amount, yuan)
        self.assertEqual(self.F.callCount('ApplyDamage'), 0)
        self.assertEqual(self.F.callCount('SetHitpoints'), 0)

    def test_same_timer_callback_is_consumed_once(self):
        self.open_domain()
        timer = self.queue_turn()
        timer.callback()
        timer.callback()
        self.assertEqual(self.pulse_counts(), {'enemy': 3, 'other': 1})

    def test_new_turn_supersedes_old_callback(self):
        self.open_domain()
        first = self.queue_turn()
        second = self.queue_turn()
        self.assert_cancelled(first)
        second.callback()
        self.assertEqual(self.pulse_counts(), {'enemy': 3, 'other': 1})

    def test_stale_callback_after_newest_callback_cannot_replay(self):
        self.open_domain()
        first = self.queue_turn()
        second = self.queue_turn()
        second.callback()
        first.callback()
        second.callback()
        self.assertEqual(self.pulse_counts(), {'enemy': 3, 'other': 1})

    def test_turn_advance_without_reschedule_invalidates_snapshot(self):
        self.open_domain()
        timer = self.queue_turn()
        self.ESC.State('sword').turn += 1
        self.assert_cancelled(timer)

    def test_domain_removed_before_callback(self):
        self.open_domain()
        timer = self.queue_turn()
        self.ESC.State('sword').domains.taixuan_taiqing = None
        self.assert_cancelled(timer)

    def test_native_expiry_cancels_queued_pulse_and_later_combat_turns(self):
        self.open_domain()
        timer = self.queue_turn()
        self.lua.globals().Osi.RemoveStatus('sword', 'ESC_SWORD_DOMAIN', 'sword')
        self.F.emit('StatusRemoved', 'sword', 'ESC_SWORD_DOMAIN', 'sword', 801)
        self.assert_cancelled(timer)
        self.F.clearCalls()
        timers_before = len(self.timers())
        self.F.emit('TurnStarted', 'sword')
        self.assertEqual(len(self.timers()), timers_before)
        self.assertEqual(self.pulse_counts(), {})

    def test_domain_expired_before_callback(self):
        self.open_domain()
        timer = self.queue_turn()
        state = self.ESC.State('sword')
        state.domains.taixuan_taiqing.expires = state.turn
        self.assert_cancelled(timer)

    def test_recast_changes_sequence_on_same_domain_table_and_cancels_old_timer(self):
        self.open_domain()
        timer = self.queue_turn()
        domain = self.ESC.State('sword').domains.taixuan_taiqing
        old_sequence = domain.sequence
        self.lua.globals().OldDomain = domain
        self.F.clearCalls()
        self.cast('sword', 'taixuan_taiqing', action=803)
        self.assertEqual(self.pulse_counts(), {'enemy': 3, 'other': 1})
        self.assertTrue(self.lua.execute('return OldDomain == ESC.State("sword").domains.taixuan_taiqing'))
        self.assertNotEqual(domain.sequence, old_sequence)
        self.assert_cancelled(timer)

    def test_session_reload_invalidates_callback_and_new_turn_can_schedule(self):
        self.open_domain()
        old_timer = self.queue_turn()
        self.runtime.SessionLoaded()
        self.assert_cancelled(old_timer)
        # Public SessionLoaded schedules 200/6000 ms maintenance, which this
        # focused boundary intentionally leaves pending.
        fresh_timer = self.queue_turn()
        fresh_timer.callback()
        self.assertEqual(self.pulse_counts(), {'enemy': 3, 'other': 1})

    def test_public_session_loaded_event_invalidates_old_callback(self):
        self.open_domain()
        timer = self.queue_turn()
        self.F.event('SessionLoaded', self.table({}))
        self.assert_cancelled(timer)

    def test_owner_removed_before_callback(self):
        self.open_domain()
        timer = self.queue_turn()
        self.F.entities.sword = None
        self.assert_cancelled(timer)

    def test_dead_owner_cancels_without_retry_or_resurrection_replay(self):
        self.open_domain()
        timer = self.queue_turn()
        self.owner._dead = True
        self.assert_cancelled(timer)
        self.owner._dead = False
        timer.callback()
        self.assertEqual(self.pulse_counts(), {})

    def test_downed_owner_cancels(self):
        self.open_domain()
        timer = self.queue_turn()
        self.lua.globals().Osi.ApplyStatus('sword', 'DOWNED', 6, 1, 'enemy')
        self.assert_cancelled(timer)

    def test_left_combat_cancels_without_reentry_replay(self):
        self.open_domain()
        timer = self.queue_turn()
        self.owner._combat = False
        self.assert_cancelled(timer)
        self.owner._combat = True
        timer.callback()
        self.assertEqual(self.pulse_counts(), {})

    def test_inactive_combat_turn_cancels(self):
        self.open_domain()
        timer = self.queue_turn()
        self.owner.TurnBased.IsActiveCombatTurn = False
        self.assert_cancelled(timer)

    def test_missing_turn_based_component_cancels(self):
        self.open_domain()
        timer = self.queue_turn()
        self.owner.TurnBased = None
        self.assert_cancelled(timer)

    def test_shield_equipped_during_delay_cancels(self):
        self.open_domain()
        timer = self.queue_turn()
        self.owner._equipped.Shield = 'shield'
        self.assertFalse(self.E.allowed('sword', 'taixuan', False))
        self.assert_cancelled(timer)

    def test_medium_or_heavy_armor_equipped_during_delay_cancels(self):
        for proficiency in ('MediumArmor', 'HeavyArmor'):
            with self.subTest(proficiency=proficiency):
                self.setUp()
                self.open_domain()
                timer = self.queue_turn()
                self.F.entities.armor = self.table({
                    '_isItem': True, '_boosts': {}, '_proficiencies': {proficiency: True}})
                self.owner._equipped.Breast = 'armor'
                self.assertFalse(self.E.allowed('sword', 'taixuan', False))
                self.assert_cancelled(timer)

    def test_class_removed_or_branch_changed_during_delay_cancels(self):
        for branch in (None, 'xueyan'):
            with self.subTest(branch=branch):
                self.setUp()
                self.open_domain()
                timer = self.queue_turn()
                if branch is None:
                    self.owner.Classes.Classes = self.table([])
                else:
                    self.owner.Classes.Classes[1].SubClassUUID = bridge.SPEC['classes'][branch]
                self.assert_cancelled(timer)

    def test_delay_uses_current_focus_and_targets(self):
        self.open_domain()
        timer = self.queue_turn()
        self.ESC.State('sword').focus = 'other'
        timer.callback()
        self.assertEqual(self.pulse_counts(), {'enemy': 1, 'other': 3})

    def test_target_leaves_radius_before_callback(self):
        self.open_domain()
        timer = self.queue_turn()
        self.enemy.Transform.Transform.Translate[1] = 20
        timer.callback()
        self.assertEqual(self.pulse_counts(), {'other': 1})

    def test_target_dies_before_callback(self):
        self.open_domain()
        timer = self.queue_turn()
        self.enemy._dead = True
        timer.callback()
        self.assertEqual(self.pulse_counts(), {'other': 1})

    def test_four_total_batches_then_expiry_has_no_timer_or_damage(self):
        self.open_domain()
        totals = {'enemy': 3, 'other': 1}
        for _ in range(3):
            self.F.clearCalls()
            timer = self.queue_turn()
            timer.callback()
            for target, count in self.pulse_counts().items():
                totals[target] += count
        self.assertEqual(totals, {'enemy': 12, 'other': 4})
        self.F.clearCalls()
        timers_before = len(self.timers())
        self.F.emit('TurnStarted', 'sword')
        self.assertIsNone(self.ESC.State('sword').domains.taixuan_taiqing)
        self.assertEqual(len(self.timers()), timers_before)
        self.assertEqual(self.pulse_counts(), {})

    def test_no_domain_turn_does_not_schedule(self):
        self.F.clearCalls()
        self.F.emit('TurnStarted', 'sword')
        self.assertEqual(self.timers(), [])
        self.assertEqual(self.pulse_counts(), {})

    def test_blood_domain_opening_is_synchronous_but_turn_uses_same_bounded_delay(self):
        blood = self.actor('blood', branch='xueyan', hp=100)
        self.cast('blood', 'xueyan_xuehai', action=804)
        self.assertEqual(self.pulse_counts(BLOOD, 'blood'), {'enemy': 1, 'other': 1})
        self.F.timers = self.table([])
        self.F.clearCalls()
        self.F.emit('TurnStarted', 'blood')
        self.assertEqual(self.pulse_counts(BLOOD, 'blood'), {})
        self.assertEqual(len(self.timers()), 1)
        self.timers()[0].callback()
        self.assertEqual(self.pulse_counts(BLOOD, 'blood'), {'enemy': 1, 'other': 1})
        self.assertTrue(blood.TurnBased.IsActiveCombatTurn)


if __name__ == '__main__':
    unittest.main(verbosity=2)
