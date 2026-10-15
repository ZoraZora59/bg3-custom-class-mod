"""Native boost handles are separate from saved Vars; this is not client proof."""
from pathlib import Path
import unittest

import test_esc_bridge as bridge


class PersistentBoostRestore(unittest.TestCase):
    table = bridge.Bridge.table
    actor = bridge.Bridge.actor

    def setUp(self):
        bridge.Bridge.setUp(self)
        self.lua.execute((Path(__file__).parent / 'esc_native_boost_fixture.lua').read_text(encoding='utf-8'))
        self.owner = self.actor(branch='xingge', hp=112, maximum=112)
        self.actor('ally', level=0, hp=30, maximum=30, x=8)

    def saved(self, target, values):
        state = self.ESC.State(target)
        for key, value in values.items():
            state.boosts[key] = value
        return state

    def calls(self, name, cause):
        # The base fixture records RemoveBoosts without the unused native arg.
        return [call for call in self.F.calls.values()
                if call.name == name and call.args[3] == cause]

    def reload_lua(self):
        # SE reload resets Lua locals/listeners; persisted entity Vars survive.
        self.lua.execute('Fixture.listeners={};Fixture.events={};Fixture.timers={};Fixture.nextTicks={}')
        self.ESC.Engine = self.lua.execute(bridge.SNAPSHOT['Engine.lua'].decode('utf-8'))
        self.lua.execute(bridge.SNAPSHOT['Runtime.lua'].decode('utf-8'))
        self.E = self.ESC.Engine

    def test_removal_assertions_observe_recorded_cause(self):
        self.saved('sword', {'hp': 'IncreaseMaxHP(12)'})
        self.F.addNativeBoost('sword', 'ESC_hp', 'IncreaseMaxHP', '12')
        self.E.setBoosts('sword', 'hp', '')
        self.assertEqual(len(self.calls('RemoveBoosts', 'ESC_hp')), 1)
        self.assertEqual(self.F.nativeBoostCount('sword', 'ESC_hp'), 0)

    def test_clear_removes_false_only_and_shared_conditional_handles(self):
        self.saved('sword', {'weakpoint': "IF(HasStatus('ESC_WEAKPOINT')):RollBonus(Attack,2)"})
        self.F.addNativeBoost('sword', 'ESC_weakpoint', 'RollBonus', 'Attack,2', True)
        shared = self.F.addNativeBoost('sword', 'ESC_weakpoint', 'RollBonus', 'Attack,2')
        self.lua.globals().table.insert(self.owner.BoostConditionalState.States,
                                       self.table({'Boost': shared, 'ConditionResult': False}))
        self.F.addNativeBoost('sword', 'OTHER_MOD', 'RollBonus', 'Attack,3', True)
        self.E.setBoosts('sword', 'weakpoint', '')
        self.assertEqual(self.ESC.State('sword').boosts['weakpoint'], '')
        self.assertEqual(self.F.nativeBoostCount('sword', 'ESC_weakpoint'), 0)
        self.assertEqual(len(self.owner.BoostConditionalState.States), 1)
        self.assertEqual(self.F.nativeBoostCount('sword', 'OTHER_MOD'), 1)

    def test_native_hp_missing_saved_snapshot_is_restored_once_without_hp_assignment(self):
        self.saved('sword', {'hp': 'IncreaseMaxHP(12)'})
        self.F.event('SessionLoaded', self.table({}))
        self.assertEqual((self.owner._hp, self.owner._maxHp), (124, 124))
        self.assertEqual(len(self.calls('AddBoosts', 'ESC_hp')), 1)
        self.assertEqual(self.calls('RemoveBoosts', 'ESC_hp'), [])
        self.assertEqual(self.F.callCount('SetHitpoints'), 0)
        self.F.clearCalls()
        self.F.event('SessionLoaded', self.table({}))
        self.assertEqual((self.owner._hp, self.owner._maxHp), (124, 124))
        self.assertEqual(self.calls('AddBoosts', 'ESC_hp') + self.calls('RemoveBoosts', 'ESC_hp'), [])

    def test_existing_native_hp_and_other_slots_are_not_reapplied(self):
        self.saved('sword', {'hp': 'IncreaseMaxHP(12)', 'weakpoint': "IF(HasStatus('ESC_WEAKPOINT')):RollBonus(Attack,2)"})
        self.F.addNativeBoost('sword', 'ESC_hp', 'IncreaseMaxHP', '12')
        self.F.addNativeBoost('sword', 'ESC_weakpoint', 'RollBonus', 'Attack,2', True)
        self.F.event('SessionLoaded', self.table({}))
        self.assertEqual((self.owner._hp, self.owner._maxHp), (124, 124))
        self.assertEqual(self.calls('AddBoosts', 'ESC_hp') + self.calls('AddBoosts', 'ESC_weakpoint'), [])
        self.assertEqual(self.F.nativeBoostCount('sword', 'ESC_hp'), 1)
        self.assertEqual(self.F.nativeBoostCount('sword', 'ESC_weakpoint'), 1)

    def test_partly_missing_bundle_adds_only_missing_statement(self):
        self.saved('ally', {'saved_support': 'IgnoreLeaveAttackRange();ActionResource(Movement,6,0)'})
        self.F.entities['ally'].Classes = None
        self.F.addNativeBoost('ally', 'ESC_saved_support', 'IgnoreLeaveAttackRange', '')
        self.F.event('SessionLoaded', self.table({}))
        self.assertEqual([c.args[2] for c in self.calls('AddBoosts', 'ESC_saved_support')], ['ActionResource(Movement,6,0)'])
        self.assertEqual(self.calls('RemoveBoosts', 'ESC_saved_support'), [])
        self.assertEqual(self.F.nativeBoostCount('ally', 'ESC_saved_support'), 2)

    def test_all_committed_nonclass_slots_restore_but_expired_aura_and_transients_do_not(self):
        self.saved('ally', {'followup_sword': "IF(HasStatus('ESC_FOLLOWUP',context.Target,'sword')):RollBonus(Attack,2)",
                           'weakpoint': "IF(HasStatus('ESC_WEAKPOINT')):RollBonus(Attack,2)",
                           'aura': 'AC(2);RollBonus(Attack,2)',
                           'chengfeng': 'IgnoreLeaveAttackRange();ActionResource(Movement,6,0)',
                           'auto_release': 'StatusImmunity(STUNNED)',
                           'cast_snapshot_1': 'RollBonus(Attack,4)', 'cast_weapon_accuracy': 'RollBonus(Attack,1)'})
        self.ESC.State('ally').protections['chengfeng:sword'] = self.table(
            {'owner': 'sword', 'kind': 'chengfeng', 'expires': 0, 'reduction': 0})
        self.F.entities['ally'].Classes = None  # Health beneficiary, no Classes discovery.
        self.F.event('SessionLoaded', self.table({}))
        for slot in ('followup_sword', 'weakpoint'):
            self.assertEqual(self.F.nativeBoostCount('ally', 'ESC_' + slot), 1, slot)
        for slot in ('aura', 'chengfeng', 'auto_release', 'cast_snapshot_1', 'cast_weapon_accuracy'):
            self.assertEqual(self.F.nativeBoostCount('ally', 'ESC_' + slot), 0, slot)
            self.assertEqual(self.calls('AddBoosts', 'ESC_' + slot), [])

    def test_queued_initial_add_and_alias_restore_do_not_duplicate(self):
        self.F.entities['Hero_sword'] = self.owner
        self.F.deferNativeBoosts = True
        self.ESC.Refresh('Hero_sword')
        self.F.event('SessionLoaded', self.table({}))
        self.F.flushNativeBoosts()
        self.assertEqual(self.F.nativeBoostCount('sword', 'ESC_hp'), 1)
        self.assertEqual((self.owner._hp, self.owner._maxHp), (124, 124))
        self.assertEqual(len(self.calls('AddBoosts', 'ESC_hp')), 1)

    def test_cold_lua_reload_rebuilds_missing_native_boost_despite_prior_submission(self):
        self.ESC.Refresh('sword')
        self.assertEqual(self.owner._maxHp, 124)
        # Model the observed client load boundary: saved description remains,
        # native actor boosts are gone and max HP is back to class base.
        self.owner.BoostsContainer = self.table({'Boosts': []})
        self.owner.BoostConditionalState = None
        self.owner._hp, self.owner._maxHp = 112, 112
        self.reload_lua()
        self.F.clearCalls()
        self.F.event('SessionLoaded', self.table({}))
        self.assertEqual((self.owner._hp, self.owner._maxHp), (124, 124))
        self.assertEqual(len(self.calls('AddBoosts', 'ESC_hp')), 1)
        self.assertEqual(self.calls('RemoveBoosts', 'ESC_hp'), [])

    def test_partial_bundle_keeps_existing_hp_and_ignores_other_mod_cause(self):
        self.saved('sword', {'saved_bundle': 'IncreaseMaxHP(12);RollBonus(Attack,2)'})
        self.F.addNativeBoost('sword', 'ESC_saved_bundle', 'IncreaseMaxHP', '12')
        self.F.addNativeBoost('sword', 'OTHER_MOD', 'RollBonus', 'Attack,2')
        self.owner._hp = 60
        self.E.restoreBoosts('sword')
        self.E.restoreBoosts('sword')
        self.assertEqual((self.owner._hp, self.owner._maxHp), (60, 124))
        self.assertEqual([c.args[2] for c in self.calls('AddBoosts', 'ESC_saved_bundle')], ['RollBonus(Attack,2)'])
        self.assertEqual(self.calls('RemoveBoosts', 'ESC_saved_bundle'), [])
        self.assertEqual(self.F.nativeBoostCount('sword', 'OTHER_MOD'), 1)

    def test_repeated_description_counts_and_shared_conditional_handle_are_not_collapsed(self):
        self.saved('sword', {'saved_bundle': 'AC(1);AC(1);RollBonus(Attack,2)'})
        self.F.addNativeBoost('sword', 'ESC_saved_bundle', 'AC', '1')
        handle = self.F.addNativeBoost('sword', 'ESC_saved_bundle', 'RollBonus', 'Attack,2')
        self.owner.BoostConditionalState = self.table({'States': [{'Boost': handle, 'ConditionResult': False}]})
        self.E.restoreBoosts('sword')
        self.assertEqual([c.args[2] for c in self.calls('AddBoosts', 'ESC_saved_bundle')], ['AC(1)'])
        self.assertEqual(self.F.nativeBoostCount('sword', 'ESC_saved_bundle'), 3)

    def test_conditional_missing_statement_retains_condition_when_rebuilt(self):
        conditional = "IF((HasStatus('ESC_WEAKPOINT') or HasStatus('ESC_FOLLOWUP'))):RollBonus(Attack,2)"
        self.saved('sword', {'saved_bundle': conditional + ';SpellSaveDC(2)'})
        self.F.addNativeBoost('sword', 'ESC_saved_bundle', 'SpellSaveDC', '2')
        self.E.restoreBoosts('sword')
        self.assertEqual([c.args[2] for c in self.calls('AddBoosts', 'ESC_saved_bundle')], [conditional])


if __name__ == '__main__':
    unittest.main()
