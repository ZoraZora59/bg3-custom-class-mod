"""Support rewards with independently scheduled native UseCosts writes.

These tests reproduce client-observed CastedSpell-before-payment ordering;
they do not establish the live engine's event timing by themselves.
"""
import re
import unittest

import test_esc_bridge as bridge


class SupportRewardTiming(unittest.TestCase):
    table = bridge.Bridge.table
    actor = bridge.Bridge.actor

    def setUp(self):
        bridge.Bridge.setUp(self)
        self.actor(branch='xingge', hp=100)
        self.actor('ally', level=0, hp=50, maximum=100, x=5)
        self.F.resource('sword').Amount = 50

    def begin(self, key='xingge_fengyu', target='sword', action=301, owner='sword'):
        spell = bridge.SPEC['spells'][key]['stat']
        self.F.emit('UsingSpellOnTarget', owner, target, spell, 'Target', '', action)
        self.F.statusFunctors(owner, spell, target, action)
        return spell

    def pay(self, spell, owner='sword'):
        cost = re.search(r'ESC_SwordYuan:([\d.]+)', self.F.stats[spell]['UseCosts'] or '')
        self.F.resource(owner).Amount -= float(cost.group(1)) if cost else 0

    def finish(self, spell, action=301, owner='sword'):
        self.F.emit('CastedSpell', owner, spell, 'Target', '', action)

    def cast_and_pay(self, key='xingge_fengyu', target='sword', action=301, before=False):
        spell = self.begin(key, target, action)
        if before:
            self.pay(spell)
        self.finish(spell, action)
        if not before:
            self.pay(spell)
        self.F.runNextTick()
        return spell

    def test_full_and_near_full_wind_refund_survives_native_cost_after_casted(self):
        for initial in (50, 49, 40, 10):
            with self.subTest(initial=initial):
                self.setUp()
                self.F.resource('sword').Amount = initial
                self.cast_and_pay()
                self.assertEqual(self.F.resource('sword').Amount, initial - 10 + 3)

    def test_cost_already_paid_before_casted_is_not_charged_again(self):
        self.cast_and_pay(before=True)
        self.assertEqual(self.F.resource('sword').Amount, 43)

    def test_multiple_allies_reward_each_once_after_cost_then_clamp(self):
        for index in range(2, 6):
            self.actor('ally' + str(index), level=0, hp=100, x=5)
        self.cast_and_pay()
        self.assertEqual(self.F.resource('sword').Amount, 50)
        self.assertIsNotNone(self.ESC.State('sword').domains.xingge_fengyu)

    def test_no_allies_and_resonance_opening_do_not_refund(self):
        self.F.entities['ally']._party = 'neutral'
        self.cast_and_pay()
        self.assertEqual(self.F.resource('sword').Amount, 40)
        self.cast_and_pay('xingge_zhangjian', action=302)
        self.assertEqual(self.F.resource('sword').Amount, 20)

    def test_each_actual_support_kind_returns_three_after_its_native_cost(self):
        for key in ('xingge_xiangfu', 'xingge_fuchen', 'xingge_huifeng', 'xingge_chengfeng'):
            with self.subTest(key=key):
                self.setUp()
                if key == 'xingge_fuchen':
                    self.lua.globals().Osi.ApplyStatus('ally', 'STUNNED', 12, 1, 'enemy')
                spell = self.cast_and_pay(key, 'ally')
                cost = float(re.search(r'ESC_SwordYuan:([\d.]+)', self.F.stats[spell]['UseCosts']).group(1))
                self.assertEqual(self.F.resource('sword').Amount, 50 - cost + 3)

    def test_no_actual_heal_cleanse_or_self_support_does_not_refund(self):
        for key, target in (('xingge_xiangfu', 'ally'), ('xingge_fuchen', 'ally'),
                            ('xingge_huifeng', 'sword'), ('xingge_chengfeng', 'sword')):
            with self.subTest(key=key, target=target):
                self.setUp()
                self.F.entities['ally']._hp = 100
                spell = self.cast_and_pay(key, target)
                cost = float(re.search(r'ESC_SwordYuan:([\d.]+)', self.F.stats[spell]['UseCosts']).group(1))
                self.assertEqual(self.F.resource('sword').Amount, 50 - cost)

    def test_duplicate_casted_and_next_ticks_never_duplicate_refund(self):
        spell = self.begin()
        self.finish(spell)
        self.finish(spell)
        self.pay(spell)
        for _ in range(3):
            self.F.runNextTick()
        self.finish(spell)
        self.F.runNextTick()
        self.assertEqual(self.F.resource('sword').Amount, 43)

    def test_native_failure_cannot_reward_a_later_casted_notification(self):
        spell = self.begin()
        self.F.emit('CastSpellFailed', 'sword', spell, 'Target', '', 301)
        self.finish(spell)
        self.F.runNextTick()
        self.assertEqual(self.F.resource('sword').Amount, 50)
        self.assertIsNone(self.ESC.State('sword').domains.xingge_fengyu)

    def test_session_loaded_invalidates_old_reward_before_deferred_reload_runs(self):
        spell = self.begin()
        self.finish(spell)
        self.pay(spell)
        self.F.deferNextTicks = True
        self.F.event('SessionLoaded', self.table({}))
        self.F.runNextTick()
        self.assertEqual(self.F.resource('sword').Amount, 40)

    def test_owner_alias_and_two_successive_actions_keep_separate_rewards(self):
        self.F.entities['Hero_sword'] = self.F.entities['sword']
        spell = self.begin(owner='Hero_sword')
        self.finish(spell, owner='sword')
        self.pay(spell)
        self.F.runNextTick()
        self.assertEqual(self.F.resource('sword').Amount, 43)
        self.cast_and_pay(action=302)
        self.assertEqual(self.F.resource('sword').Amount, 36)

    def test_two_completed_actions_in_one_tick_do_not_overwrite_rewards(self):
        for action in (301, 302):
            spell = self.begin(action=action)
            self.finish(spell, action)
            self.pay(spell)
        self.F.runNextTick()
        self.assertEqual(self.F.resource('sword').Amount, 36)

    def test_earned_protection_reward_keeps_cast_time_recipient(self):
        spell = self.begin()
        self.finish(spell)
        self.pay(spell)
        self.F.entities['ally'].Transform.Transform.Translate[1] = 30
        self.F.runNextTick()
        self.assertEqual(self.F.resource('sword').Amount, 43)


if __name__ == '__main__':
    unittest.main()
