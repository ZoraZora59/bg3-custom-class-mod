"""Real Runtime event/lifecycle contracts in a simulated engine, not VFX acceptance.

Only the four native PlayEffect arguments and visual-status lifecycle are
mocked here. Production Rules, Engine and Runtime retain damage/resource logic.
"""
import copy
import unittest
from unittest.mock import patch
from uuid import NAMESPACE_URL, uuid5

import test_esc_bridge as bridge

SHARE = 'ESC_VFX_DAMAGE_SHARE'
TEAM = 'ESC_VFX_TEAM_RESONANCE'
KEYS = ('xingge_wenlu_mark', 'xingge_fengyu_transfer',
        'xingge_fengyu_status', 'xingge_zhangjian_status')
EFFECTS = {key: str(uuid5(NAMESPACE_URL, 'esc-test:' + key)) for key in KEYS}


class XinggeVisualEvents(unittest.TestCase):
    table = bridge.Bridge.table
    actor = bridge.Bridge.actor
    cast = bridge.Bridge.cast
    native_damage = bridge.Bridge.native_damage
    cooperation_packet = bridge.Bridge.cooperation_packet
    cooperation_intent = bridge.Bridge.cooperation_intent

    def setUp(self):
        spec = copy.deepcopy(bridge.SPEC)
        spec['schoolPolishVfx'] = {'enabled': True,
            'records': {key: {'effect': effect} for key, effect in EFFECTS.items()}}
        snapshot = dict(bridge.SNAPSHOT)
        snapshot['Runtime.lua'] = (bridge.LUA / 'Runtime.lua').read_bytes()
        with patch.object(bridge, 'SPEC', spec), patch.object(bridge, 'SNAPSHOT', snapshot):
            bridge.Bridge.setUp(self)
        self.vfx = self.lua.globals().GeneratedSpec.schoolPolishVfx
        self.lua.execute('''function Osi.PlayEffect(...)
            assert(select('#',...)==4, 'native PlayEffect has four arguments')
            local target,effect,bone,scale=...
            assert(Fixture.entities[target] and bone=='Dummy_Root' and scale==1)
            Fixture.calls[#Fixture.calls+1]={name='PlayEffect',args={target,effect,bone,scale}}
        end''')
        for status in (SHARE, TEAM):
            self.F.stats[status] = self.table({'StatusType': 'BOOST', 'Boosts': '',
                'StatusPropertyFlags': 'DisableCombatlog;DisablePortraitIndicator;DisableOverhead'})
        self.actor(branch='xingge', hp=100)
        self.actor('ally', level=0, hp=100, x=5)
        self.actor('enemy', level=0, hp=100, party='enemies', x=2)

    def effects(self, key):
        return [call for call in self.F.calls.values()
                if call.name == 'PlayEffect' and call.args[2] == EFFECTS[key]]

    def status_calls(self, name, status):
        return [call for call in self.F.calls.values()
                if call.name == name and call.args[2] == status]

    def update(self):
        self.ESC.Runtime.UpdateAuras()

    def active(self, target, status):
        return self.E.hasStatus(target, status)

    def entity_alias(self, alias, target):
        # Osiris Name_GUID and ECS GUID resolve to one entity, but ECS discovery
        # enumerates that entity only once. Keep the alias out of pairs().
        self.lua.execute('''Fixture.entityAliases=Fixture.entityAliases or {}
            setmetatable(Fixture.entities,{__index=function(entities,key)
                local canonical=Fixture.entityAliases[key]
                return canonical and rawget(entities,canonical) or nil
            end})''')
        self.F.entityAliases[alias] = target

    def domain(self, key='xingge_fengyu', owner='sword', action=100):
        self.cast(owner, key, action=action)

    def hit(self, owner, action, key=None, target='enemy'):
        spell = bridge.SPEC['spells'][key]['stat'] if key else 'Target_MainHandAttack'
        self.ESC.Runtime.BeginCast(owner, spell, action, target)
        self.ESC.Runtime.Hit(owner, target, action)

    def run_new_short_timers(self, start):
        timers = list(self.F.timers.values())
        for timer in timers[start:]:
            if timer.ms == 1:
                timer.callback()
        return len(timers)

    def chengfeng_boost(self, target='ally'):
        values = [self.F.entities[target]._boosts['ESC_' + slot]
                  for slot in ('chengfeng', 'chengfeng_oa', 'chengfeng_movement')]
        return ';'.join(value for value in values if value) or None

    def delayed_chengfeng_removals(self):
        # story_header.div:1078-1079 identifies SourceID/Cause and the remove
        # description/all-matches flag. It does not guarantee synchronous removal.
        # Reproduce H31's native outcome by committing removals after newer adds.
        # Existing fixture creates native-shaped BoostInfo/BoostsContainer handles,
        # independently of saved Vars and the base fixture's _boosts strings.
        self.lua.execute((bridge.REPO / 'scripts/tests/esc_native_boost_fixture.lua').read_text('utf-8'))
        self.lua.execute('''
            local remove=Osi.RemoveBoosts
            Fixture.chengfengRemovals={}
            function Osi.RemoveBoosts(id,boost,first,sourceID,cause)
                if sourceID:find('ESC_chengfeng',1,true)==1 then
                    assert(first==0,'Production removes all matching descriptions')
                    table.insert(Fixture.chengfengRemovals,{id,boost,first,sourceID,cause})
                else remove(id,boost,first,sourceID,cause) end
            end
            function Fixture.flushChengfengRemovals()
                local pending=Fixture.chengfengRemovals;Fixture.chengfengRemovals={}
                for _,args in ipairs(pending) do remove(table.unpack(args)) end
            end
        ''')

    def native_chengfeng_handles(self, kind, target='ally'):
        entity = self.F.entities[target]
        result = []
        if entity.BoostsContainer is None:
            return result
        for group in entity.BoostsContainer.Boosts.values():
            if group.Type != kind:
                continue
            for handle in group.Boosts.values():
                info = self.F.entities[handle].BoostInfo
                if info.Cause.Cause.startswith('ESC_chengfeng'):
                    result.append(handle)
        return result

    def test_chengfeng_native_deferred_removal_keeps_original_oa_handle_next_round(self):
        self.delayed_chengfeng_removals()
        self.entity_alias('Hero_sword', 'sword')
        self.cast('Hero_sword', 'xingge_chengfeng', 'ally', action=321)
        initial = self.native_chengfeng_handles('IgnoreLeaveAttackRange')
        self.assertEqual(len(initial), 1)
        self.assertEqual(len(self.native_chengfeng_handles('ActionResource')), 1)
        self.F.emit('TurnStarted', 'sword')
        self.F.flushChengfengRemovals()
        self.assertEqual(self.native_chengfeng_handles('IgnoreLeaveAttackRange'), initial)
        self.assertEqual(self.native_chengfeng_handles('ActionResource'), [])
        self.F.emit('TurnStarted', 'ally')
        for _ in range(10):
            self.update()
        self.F.flushChengfengRemovals()
        self.assertEqual(self.native_chengfeng_handles('IgnoreLeaveAttackRange'), initial)
        self.F.emit('TurnStarted', 'Hero_sword')
        self.F.flushChengfengRemovals()
        self.assertEqual(self.native_chengfeng_handles('IgnoreLeaveAttackRange'), [])

    def test_chengfeng_native_self_recast_does_not_replace_live_oa_handle(self):
        self.delayed_chengfeng_removals()
        self.cast('sword', 'xingge_chengfeng', 'sword', action=322)
        initial = self.native_chengfeng_handles('IgnoreLeaveAttackRange', 'sword')
        self.F.emit('TurnStarted', 'sword')
        self.F.flushChengfengRemovals()
        self.cast('sword', 'xingge_chengfeng', 'sword', action=323)
        self.F.flushChengfengRemovals()
        self.assertEqual(self.native_chengfeng_handles('IgnoreLeaveAttackRange', 'sword'), initial)
        self.assertEqual(len(self.native_chengfeng_handles('ActionResource', 'sword')), 1)
        self.F.emit('TurnStarted', 'sword')
        self.F.flushChengfengRemovals()
        self.assertEqual(self.native_chengfeng_handles('IgnoreLeaveAttackRange', 'sword'), initial)
        self.assertEqual(self.native_chengfeng_handles('ActionResource', 'sword'), [])
        self.F.emit('TurnStarted', 'sword')
        self.F.flushChengfengRemovals()
        self.assertEqual(self.native_chengfeng_handles('IgnoreLeaveAttackRange', 'sword'), [])

    def test_chengfeng_native_legacy_bundle_migrates_without_deleting_new_slots(self):
        self.delayed_chengfeng_removals()
        self.ESC.State('ally').protections['chengfeng:sword'] = self.table(
            dict(owner='sword', kind='chengfeng', movementExpires=1, expires=2, reduction=0))
        self.E.setBoosts('ally', 'chengfeng',
                         'IgnoreLeaveAttackRange();ActionResource(Movement,6,0)')
        self.update()
        self.F.flushChengfengRemovals()
        self.assertEqual(self.F.nativeBoostCount('ally', 'ESC_chengfeng'), 0)
        self.assertEqual(len(self.native_chengfeng_handles('IgnoreLeaveAttackRange')), 1)
        self.assertEqual(len(self.native_chengfeng_handles('ActionResource')), 1)
        self.F.emit('TurnStarted', 'sword')
        self.F.flushChengfengRemovals()
        self.assertEqual(len(self.native_chengfeng_handles('IgnoreLeaveAttackRange')), 1)
        self.assertEqual(self.native_chengfeng_handles('ActionResource'), [])
        self.F.emit('TurnStarted', 'sword')
        self.F.flushChengfengRemovals()
        self.assertEqual(self.native_chengfeng_handles('IgnoreLeaveAttackRange'), [])

    def test_chengfeng_native_owners_overlap_without_removing_shared_immunity(self):
        self.delayed_chengfeng_removals()
        self.actor('other', branch='xingge', hp=100, x=4)
        self.cast('sword', 'xingge_chengfeng', 'ally', action=324)
        initial = self.native_chengfeng_handles('IgnoreLeaveAttackRange')
        self.F.emit('TurnStarted', 'sword')
        self.F.flushChengfengRemovals()
        self.cast('other', 'xingge_chengfeng', 'ally', action=325)
        self.F.emit('TurnStarted', 'sword')
        self.F.flushChengfengRemovals()
        self.assertEqual(self.native_chengfeng_handles('IgnoreLeaveAttackRange'), initial)
        self.assertEqual(len(self.native_chengfeng_handles('ActionResource')), 1)
        self.F.emit('TurnStarted', 'other')
        self.F.flushChengfengRemovals()
        self.assertEqual(self.native_chengfeng_handles('IgnoreLeaveAttackRange'), initial)
        self.assertEqual(self.native_chengfeng_handles('ActionResource'), [])
        self.F.emit('TurnStarted', 'other')
        self.F.flushChengfengRemovals()
        self.assertEqual(self.native_chengfeng_handles('IgnoreLeaveAttackRange'), [])

    def test_chengfeng_native_loaded_remaining_oa_does_not_restore_movement_or_extend_expiry(self):
        self.delayed_chengfeng_removals()
        self.ESC.State('sword').turn = 1
        state = self.ESC.State('ally')
        state.boosts['chengfeng'] = 'IgnoreLeaveAttackRange()'
        state.protections['chengfeng:sword'] = self.table(
            dict(owner='sword', kind='chengfeng', movementExpires=1, expires=2, reduction=0))
        self.F.entities['ally'].Classes = None
        self.F.event('SessionLoaded', self.table({}))
        self.F.flushChengfengRemovals()
        self.assertEqual(self.F.nativeBoostCount('ally', 'ESC_chengfeng'), 0)
        self.assertEqual(len(self.native_chengfeng_handles('IgnoreLeaveAttackRange')), 1)
        self.assertEqual(self.native_chengfeng_handles('ActionResource'), [])
        self.F.emit('TurnStarted', 'sword')
        self.F.flushChengfengRemovals()
        self.assertEqual(self.native_chengfeng_handles('IgnoreLeaveAttackRange'), [])
        self.F.event('SessionLoaded', self.table({}))
        self.F.flushChengfengRemovals()
        self.assertEqual(self.native_chengfeng_handles('IgnoreLeaveAttackRange'), [])
        self.assertEqual(self.native_chengfeng_handles('ActionResource'), [])

    def test_chengfeng_ally_movement_ends_before_next_round_oa_immunity(self):
        self.entity_alias('Hero_sword', 'sword')
        self.cast('Hero_sword', 'xingge_chengfeng', 'ally', action=301)
        self.assertEqual(self.chengfeng_boost(),
                         'IgnoreLeaveAttackRange();ActionResource(Movement,6,0)')
        self.F.emit('TurnStarted', 'ally')
        self.assertIn('Movement,6,0', self.chengfeng_boost())
        self.F.emit('TurnStarted', 'sword')
        self.assertEqual(self.chengfeng_boost(), 'IgnoreLeaveAttackRange()')
        self.F.clearCalls()
        for _ in range(10):
            self.update()
        self.assertEqual([c.name for c in self.F.calls.values()
                          if c.name in ('AddBoosts', 'RemoveBoosts')], [])
        self.F.emit('TurnStarted', 'Hero_sword')
        self.assertIsNone(self.chengfeng_boost())

    def test_chengfeng_self_keeps_next_round_oa_without_extra_movement(self):
        self.cast('sword', 'xingge_chengfeng', 'sword', action=302)
        self.F.emit('TurnStarted', 'sword')
        self.assertEqual(self.chengfeng_boost('sword'), 'IgnoreLeaveAttackRange()')
        self.F.emit('TurnStarted', 'sword')
        self.assertIsNone(self.chengfeng_boost('sword'))

    def test_chengfeng_recast_refreshes_both_deadlines_once(self):
        self.cast('sword', 'xingge_chengfeng', 'ally', action=303)
        self.F.emit('TurnStarted', 'sword')
        self.assertEqual(self.chengfeng_boost(), 'IgnoreLeaveAttackRange()')
        self.cast('sword', 'xingge_chengfeng', 'ally', action=304)
        self.assertIn('Movement,6,0', self.chengfeng_boost())
        self.F.emit('TurnStarted', 'sword')
        self.assertEqual(self.chengfeng_boost(), 'IgnoreLeaveAttackRange()')
        self.F.emit('TurnStarted', 'sword')
        self.assertIsNone(self.chengfeng_boost())

    def test_chengfeng_other_owner_does_not_lose_live_movement_or_immunity(self):
        self.actor('other', branch='xingge', hp=100, x=4)
        self.cast('sword', 'xingge_chengfeng', 'ally', action=305)
        self.F.emit('TurnStarted', 'sword')
        self.cast('other', 'xingge_chengfeng', 'ally', action=306)
        self.update()
        self.assertIn('Movement,6,0', self.chengfeng_boost())
        self.F.emit('TurnStarted', 'sword')
        self.assertIn('Movement,6,0', self.chengfeng_boost())
        self.F.emit('TurnStarted', 'other')
        self.assertEqual(self.chengfeng_boost(), 'IgnoreLeaveAttackRange()')
        self.F.emit('TurnStarted', 'other')
        self.assertIsNone(self.chengfeng_boost())

    def test_chengfeng_legacy_saved_deadline_is_not_extended_or_recreated(self):
        # Pre-H30 saved records have only expires. Keep their existing deadline;
        # a new cast is required to gain the corrected additional-round immunity.
        self.ESC.State('ally').protections['chengfeng:sword'] = self.table(
            dict(owner='sword', kind='chengfeng', expires=1, reduction=0))
        self.E.setBoosts('ally', 'chengfeng',
                         'IgnoreLeaveAttackRange();ActionResource(Movement,6,0)')
        self.update()
        self.assertIn('Movement,6,0', self.chengfeng_boost())
        self.F.emit('TurnStarted', 'sword')
        self.assertIsNone(self.chengfeng_boost())
        self.update()
        self.assertIsNone(self.chengfeng_boost())

    def control_save_boosts(self, target='ally'):
        return [value for key, value in self.F.entities[target]._boosts.items()
                if key.startswith('ESC_control_save_') and value]

    def test_fuchen_nonclass_ally_real_status_events_keep_then_remove_save_bonus(self):
        self.entity_alias('Companion_ally', 'ally')
        self.E.status('ally', 'SILENCED', 1, 'enemy')
        self.cast('sword', 'xingge_fuchen', 'ally', action=307)
        self.F.runNextTick()
        self.assertFalse(self.E.hasStatus('ally', 'SILENCED'))
        self.assertEqual(self.F.resource('sword').Amount, 3)
        # Native ApplyStatus is asynchronous in the client; deliver its actual
        # status callback separately, with the observed non-cast action -1.
        self.F.emit('StatusApplied', 'Companion_ally', 'ESC_CONTROL_RESISTANCE', 'sword', -1)
        values = self.control_save_boosts()
        self.assertTrue(values)
        self.assertTrue(all('RollBonus(SavingThrow,2)' in b and 'Advantage(' not in b for b in values))
        self.assertIn("StatusId('SILENCED')", ';'.join(values))
        self.F.emit('TurnStarted', 'ally')
        self.assertEqual(self.control_save_boosts(), values)
        self.E.removeStatus('ally', 'ESC_CONTROL_RESISTANCE', 'sword')
        self.F.emit('StatusRemoved', 'Companion_ally', 'ESC_CONTROL_RESISTANCE', 'sword', -1)
        self.assertEqual(self.control_save_boosts(), [])
        self.F.emit('TurnStarted', 'ally')
        self.assertEqual(self.control_save_boosts(), [])
        self.assertEqual(self.F.resource('sword').Amount, 3)

    def test_fuchen_status_can_buff_an_unwatched_nonclass_recipient_without_refund(self):
        self.actor('fresh', level=0, hp=100, x=3)
        self.E.status('fresh', 'ESC_CONTROL_RESISTANCE', 2, 'sword')
        self.F.emit('StatusApplied', 'fresh', 'ESC_CONTROL_RESISTANCE', 'sword', -1)
        self.assertTrue(self.control_save_boosts('fresh'))
        self.assertEqual(self.F.resource('sword').Amount, 0)

    def test_fuchen_nonclass_loaded_status_is_authority_for_saved_bonus(self):
        # Nonclass beneficiaries may only be enumerated by Health at load time.
        self.assertIsNone(self.F.entities['ally'].Vars.ESC_State)
        self.F.entities['ally'].Classes = None
        self.E.status('ally', 'ESC_CONTROL_RESISTANCE', 2, 'sword')
        self.F.event('SessionLoaded', self.table({}))
        self.assertTrue(self.control_save_boosts())
        # A native status which expired during/at loading must not have its
        # persisted boost restored merely because Lua still saved the string.
        self.E.removeStatus('ally', 'ESC_CONTROL_RESISTANCE', 'sword')
        self.F.event('SessionLoaded', self.table({}))
        self.assertEqual(self.control_save_boosts(), [])

    def test_fuchen_class_recipient_keeps_innate_resistance_and_advantage(self):
        self.actor('taixuan', branch='taixuan', hp=100, x=3)
        self.E.status('taixuan', 'ESC_CONTROL_RESISTANCE', 2, 'sword')
        self.F.emit('StatusApplied', 'taixuan', 'ESC_CONTROL_RESISTANCE', 'sword', -1)
        self.assertTrue(self.control_save_boosts('taixuan'))
        self.assertTrue(all('RollBonus(SavingThrow,6)' in b and 'Advantage(AllSavingThrows)' in b
                            for b in self.control_save_boosts('taixuan')))
        self.E.removeStatus('taixuan', 'ESC_CONTROL_RESISTANCE', 'sword')
        self.F.emit('StatusRemoved', 'taixuan', 'ESC_CONTROL_RESISTANCE', 'sword', -1)
        self.assertTrue(self.control_save_boosts('taixuan'))
        self.assertTrue(all('RollBonus(SavingThrow,4)' in b and 'Advantage(AllSavingThrows)' in b
                            for b in self.control_save_boosts('taixuan')))

    def test_alias_aura_mechanics_are_one_stable_row_per_entity(self):
        self.entity_alias('Hero_sword', 'sword')
        self.entity_alias('Companion_ally', 'ally')
        self.F.entities['ally'].Transform.Transform.Translate[1] = 1
        for actor in ('sword', 'Hero_sword', 'ally', 'Companion_ally'):
            self.ESC.State(actor)
        self.domain('xingge_zhangjian', owner='Hero_sword')
        self.update()
        self.F.clearCalls()
        for _ in range(20):
            self.update()
        for actor in ('sword', 'ally'):
            self.assertEqual(self.F.entities[actor]._boosts['ESC_aura'], 'AC(2);RollBonus(Attack,2)')
        self.assertEqual([c.name for c in self.F.calls.values()
                          if c.name in ('AddBoosts', 'RemoveBoosts')], [])
        # Alias damage events must read that same aura row.
        self.assertEqual(self.ESC.Runtime.Defense('ally', 20, False, True), (17, 17))
        self.assertEqual(self.ESC.Runtime.Defense('Companion_ally', 20, False, True), (17, 17))

    def test_resonance_uses_one_allowance_per_actual_ally_and_victim(self):
        self.entity_alias('Hero_sword', 'sword')
        self.entity_alias('Companion_ally', 'ally')
        self.entity_alias('Target_enemy', 'enemy')
        self.ESC.State('Hero_sword')
        self.domain('xingge_zhangjian')
        cursor = len(list(self.F.timers.values()))
        for who, action in (('ally', 81), ('ally', 82), ('Companion_ally', 83)):
            self.hit(who, action)
            self.ESC.Runtime.Hit(who, 'Target_enemy', action)
            cursor = self.run_new_short_timers(cursor)
        echoes = [c for c in self.F.calls.values()
                  if c.name == 'UseSpell' and c.args[2] == 'Target_ESC_Resonance']
        self.assertEqual([(c.args[1], c.args[3]) for c in echoes], [('sword', 'enemy')])

    def native_aoe_echo_requests(self, source='ally', action=401):
        """Build helper metadata via the real cast/damage/attack event chain."""
        self.actor('enemy_a', level=0, hp=100, party='enemies', x=1)
        self.actor('enemy_b', level=0, hp=100, party='enemies', x=2)
        self.actor('bystander', level=0, hp=100, party='enemies', x=2.5)
        cursor = len(list(self.F.timers.values()))
        self.F.emit('UsingSpell', source, 'Zone_Cleave', 'Zone', '', action)
        for target in ('enemy_a', 'enemy_b'):
            self.native_damage(source, target, [5], spell='Zone_Cleave', action=action)
            self.F.emit('AttackedBy', target, source, source, 'Slashing', 5, 'Attack', action)
        self.F.emit('CastedSpell', source, 'Zone_Cleave', 'Zone', '', action)
        self.run_new_short_timers(cursor)
        return [c.args[3] for c in self.F.calls.values()
                if c.name == 'UseSpell' and c.args[2] == 'Target_ESC_Resonance']

    def complete_native_echo(self, target, action, hit_before_target=False):
        spell = 'Target_ESC_Resonance'
        # H29 live actions 104/105: damage, CastedSpell, UsingSpell,
        # UsingSpellOnTarget, then ESC_HIT_MARKER. Do not inject helper metadata.
        self.native_damage('sword', target, [6], spell=spell, action=action)
        self.F.emit('CastedSpell', 'sword', spell, 'Target', '', action)
        if hit_before_target:
            self.F.emit('StatusApplied', target, 'ESC_HIT_MARKER', 'sword', action)
        self.F.emit('UsingSpell', 'sword', spell, 'Target', '', action)
        self.F.emit('UsingSpellOnTarget', 'sword', target, spell, 'Target', '', action)
        self.F.emit('StatusApplied', target, 'ESC_HIT_MARKER', 'sword', action)

    def test_resonance_casted_before_target_aoe_returns_one_shared_reward(self):
        self.domain('xingge_zhangjian')
        self.assertEqual(set(self.native_aoe_echo_requests()), {'enemy_a', 'enemy_b'})
        self.complete_native_echo('enemy_a', 402)
        self.assertEqual(self.F.resource('sword').Amount, 3)
        self.complete_native_echo('enemy_b', 403)
        self.assertEqual(self.F.resource('sword').Amount, 3)
        self.F.emit('StatusApplied', 'enemy_b', 'ESC_HIT_MARKER', 'sword', 403)
        self.assertEqual(self.F.resource('sword').Amount, 3)

    def test_resonance_early_hit_binds_actual_target_before_using_spell_target(self):
        self.domain('xingge_zhangjian')
        self.native_aoe_echo_requests()
        self.complete_native_echo('enemy_b', 402, hit_before_target=True)
        self.complete_native_echo('enemy_a', 403, hit_before_target=True)
        self.assertEqual(self.F.resource('sword').Amount, 3)

    def test_resonance_missed_first_helper_does_not_consume_group_reward(self):
        self.domain('xingge_zhangjian')
        self.native_aoe_echo_requests()
        spell = 'Target_ESC_Resonance'
        self.F.emit('CastedSpell', 'sword', spell, 'Target', '', 402)
        self.F.emit('UsingSpellOnTarget', 'sword', 'enemy_a', spell, 'Target', '', 402)
        self.assertEqual(self.F.resource('sword').Amount, 0)
        self.complete_native_echo('enemy_b', 403)
        self.assertEqual(self.F.resource('sword').Amount, 3)
        # A different actual ally has its own once-per-round echo and reward.
        self.actor('ally2', level=0, hp=100, x=4)
        self.F.clearCalls()
        self.assertEqual(set(self.native_aoe_echo_requests('ally2', 404)), {'enemy_a', 'enemy_b'})
        self.complete_native_echo('enemy_a', 405)
        self.complete_native_echo('enemy_b', 406)
        self.assertEqual(self.F.resource('sword').Amount, 6)

    def test_resonance_unbound_helper_cannot_mint_a_per_action_reward(self):
        self.domain('xingge_zhangjian')
        self.complete_native_echo('enemy', 407)
        self.assertEqual(self.F.resource('sword').Amount, 0)

    def test_wenlu_actor_and_duplicate_target_aliases_do_not_reset_consumption(self):
        self.entity_alias('Hero_sword', 'sword')
        self.entity_alias('Companion_ally', 'ally')
        self.entity_alias('Target_enemy', 'enemy')
        self.hit('sword', 80, 'xingge_wenlu')
        self.hit('ally', 81)
        self.ESC.Runtime.Hit('Hero_sword', 'Target_enemy', 80)
        self.hit('Companion_ally', 82)
        self.assertEqual(self.F.resource('sword').Amount, 3)
        self.assertEqual(len(self.effects(KEYS[0])), 2)
        # A real recast through the other alias still intentionally resets it.
        self.hit('Hero_sword', 83, 'xingge_wenlu', 'Target_enemy')
        self.hit('ally', 84)
        self.assertEqual(self.F.resource('sword').Amount, 6)

    def test_cooperation_native_helper_and_wenlu_reward_union_use_actual_owner(self):
        self.entity_alias('Hero_sword', 'sword')
        self.entity_alias('Companion_ally', 'ally')
        self.F.entities['ally'].Transform.Transform.Translate[1] = 1
        self.hit('sword', 80, 'xingge_wenlu')
        self.cast('Hero_sword', 'xingge_tongzhou', 'enemy', action=81)
        packet = self.cooperation_packet('ally')
        self.cooperation_intent('ally', packet.token, 'Target_MainHandAttack')
        free = [c for c in self.F.calls.values() if c.name == 'UseSpell'
                and c.args[2] == 'ESC_FREE_Target_MainHandAttack']
        self.assertEqual(len(free), 1)
        # Real native cast/hit notifications bind the pending helper metadata;
        # no injected casts or debug upvalue mutation is involved.
        self.F.emit('UsingSpellOnTarget', 'Companion_ally', 'enemy', free[0].args[2], 'Target', '', 82)
        self.F.emit('StatusApplied', 'enemy', 'ESC_HIT_MARKER', 'Companion_ally', 82)
        self.assertEqual(self.F.resource('sword').Amount, 3)
        self.F.emit('StatusApplied', 'enemy', 'ESC_HIT_MARKER', 'ally', 82)
        self.assertEqual(self.F.resource('sword').Amount, 3)

    def test_cooperation_queue_expires_across_owner_alias_and_next_request_works(self):
        self.entity_alias('Hero_sword', 'sword')
        self.entity_alias('Companion_ally', 'ally')
        self.F.entities['ally'].Transform.Transform.Translate[1] = 1
        self.cast('Hero_sword', 'xingge_tongzhou', 'enemy', action=81)
        old = self.cooperation_packet('ally')
        self.F.emit('TurnStarted', 'sword')
        self.assertFalse(self.cooperation_packet('ally').available)
        self.cast('sword', 'xingge_tongzhou', 'enemy', action=82)
        new = self.cooperation_packet('ally')
        self.assertNotEqual(new.token, old.token)
        self.cooperation_intent('Companion_ally', old.token, 'Target_MainHandAttack')
        self.assertEqual(self.F.callCount('UseSpell'), 0)
        self.cooperation_intent('Companion_ally', new.token, 'Target_MainHandAttack')
        self.assertEqual(self.F.callCount('UseSpell'), 1)
        self.assertFalse(self.cooperation_packet('ally').available)

    def test_loaded_alias_marks_and_used_maps_preserve_consumption_and_deadlines(self):
        self.entity_alias('Hero_sword', 'sword')
        self.entity_alias('Companion_ally', 'ally')
        self.domain('xingge_zhangjian')
        self.ESC.State('sword').domains.xingge_zhangjian.used['Companion_ally'] = True
        # A persisted pre-upgrade map has raw owner and beneficiary names.
        self.ESC.State('enemy').marks['followup:Hero_sword'] = self.table(
            {'expires': 3, 'used': {'Companion_ally': True}})
        cursor = len(list(self.F.timers.values()))
        self.hit('ally', 81)
        self.run_new_short_timers(cursor)
        self.assertEqual(self.F.resource('sword').Amount, 0)
        self.assertEqual([c for c in self.F.calls.values()
                          if c.name == 'UseSpell' and c.args[2] == 'Target_ESC_Resonance'], [])
        self.assertEqual(self.ESC.State('sword').domains.xingge_zhangjian.expires, 4)
        self.assertEqual(self.ESC.State('enemy').marks['followup:sword'].expires, 3)
        self.actor('ally2', level=0, hp=100, x=4)
        self.hit('ally2', 82)
        self.assertEqual(self.F.resource('sword').Amount, 3)

    def test_alias_four_turn_clock_and_damage_share_stay_single(self):
        self.entity_alias('Hero_sword', 'sword')
        self.entity_alias('Companion_ally', 'ally')
        for actor in ('sword', 'Hero_sword', 'ally', 'Companion_ally'):
            self.ESC.State(actor)
        self.domain(owner='Hero_sword')
        self.domain('xingge_zhangjian', owner='Hero_sword', action=101)
        self.assertEqual(self.ESC.Runtime.Defense('Companion_ally', 20, False, False), (11, 20))
        self.assertEqual(self.F.entities['sword']._hp, 94)
        self.assertEqual(len(self.effects(KEYS[1])), 1)
        for turn, actor in enumerate(('sword', 'Hero_sword', 'sword', 'Hero_sword'), 1):
            self.F.emit('TurnStarted', actor)
            self.assertEqual(self.ESC.State('sword').turn, turn)
            self.assertEqual(self.active('ally', TEAM), turn < 4)
            self.assertEqual(self.active('ally', SHARE), turn < 4)

    def test_loaded_followup_boost_aliases_merge_to_one_native_slot(self):
        self.entity_alias('Hero_sword', 'sword')
        for owner in ('Hero_sword', 'sword'):
            self.E.setBoosts('ally', 'followup_' + owner,
                "IF(HasStatus('ESC_FOLLOWUP',context.Target,'" + owner + "')):RollBonus(Attack,2)")
        self.ESC.State('ally')
        self.update()
        self.assertIsNone(self.F.entities['ally']._boosts['ESC_followup_Hero_sword'])
        self.assertEqual(self.F.entities['ally']._boosts['ESC_followup_sword'],
            "IF(HasStatus('ESC_FOLLOWUP',context.Target,'sword')):RollBonus(Attack,2)")
        self.F.clearCalls()
        self.update()
        self.assertEqual([c.name for c in self.F.calls.values()
                          if c.name in ('AddBoosts', 'RemoveBoosts')], [])

    def test_loaded_self_followup_slots_are_removed_for_both_owner_names(self):
        self.entity_alias('Hero_sword', 'sword')
        self.ESC.State('Hero_sword')
        for owner in ('Hero_sword', 'sword'):
            self.E.setBoosts('sword', 'followup_' + owner,
                "IF(HasStatus('ESC_FOLLOWUP',context.Target,'" + owner + "')):RollBonus(Attack,2)")
        self.update()
        for owner in ('Hero_sword', 'sword'):
            self.assertIsNone(self.F.entities['sword']._boosts['ESC_followup_' + owner])
        # A fresh real Wenlu cast still benefits the ally, never its owner.
        self.hit('Hero_sword', 80, 'xingge_wenlu')
        self.assertIsNotNone(self.F.entities['ally']._boosts['ESC_followup_sword'])
        for owner in ('Hero_sword', 'sword'):
            self.assertIsNone(self.F.entities['sword']._boosts['ESC_followup_' + owner])
        self.F.clearCalls()
        self.update()
        self.assertEqual([c.name for c in self.F.calls.values()
                          if c.name in ('AddBoosts', 'RemoveBoosts')], [])

    def test_loaded_protection_owner_alias_preserves_reduction_and_exact_expiry(self):
        self.entity_alias('Hero_sword', 'sword')
        self.entity_alias('Companion_ally', 'ally')
        self.ESC.State('ally').protections['huifeng:Hero_sword'] = self.table(
            {'owner': 'Hero_sword', 'kind': 'huifeng', 'expires': 2, 'reduction': .20})
        self.lua.globals().Osi.ApplyStatus('ally', 'ESC_XINGGE_PROTECTION', 12, 1, 'Hero_sword')
        self.ESC.State('Companion_ally')
        self.update()
        self.assertEqual(self.ESC.Runtime.Defense('Companion_ally', 20, False, True), (16, 16))
        self.assertEqual(self.ESC.State('ally').protections['huifeng:Hero_sword'].expires, 2)
        self.F.emit('TurnStarted', 'sword')
        self.assertEqual(self.ESC.Runtime.Defense('ally', 20, False, True), (16, 16))
        self.F.emit('TurnStarted', 'Hero_sword')
        self.assertIsNone(self.ESC.State('ally').protections['huifeng:Hero_sword'])
        self.assertEqual(self.ESC.Runtime.Defense('ally', 20, False, True), (20, 20))

    def test_alias_self_never_receives_own_wenlu_reward_or_damage_transfer(self):
        self.entity_alias('Hero_sword', 'sword')
        self.ESC.State('Hero_sword')
        self.hit('sword', 80, 'xingge_wenlu')
        self.hit('Hero_sword', 81)
        self.assertEqual(self.F.resource('sword').Amount, 0)
        self.domain()
        self.F.clearCalls()
        self.assertEqual(self.ESC.Runtime.Defense('Hero_sword', 20, False, False), (14, 14))
        self.assertEqual(self.F.callCount('ApplyDamage'), 0)

    def test_mark_and_first_real_ally_use_flash_marked_enemy_with_native_overload(self):
        self.hit('sword', 81, 'xingge_wenlu')
        self.assertIsNotNone(self.ESC.State('enemy').marks['followup:sword'])
        self.assertEqual([c.args[1] for c in self.effects(KEYS[0])], ['enemy'])
        self.hit('ally', 82)
        self.assertEqual([c.args[1] for c in self.effects(KEYS[0])], ['enemy', 'enemy'])
        self.assertEqual(self.F.resource('sword').Amount, 3)

    def test_duplicate_hits_do_not_flash_or_reset_consumption_but_recast_does(self):
        self.hit('sword', 81, 'xingge_wenlu')
        self.hit('ally', 82)
        self.F.emit('StatusApplied', 'enemy', 'ESC_HIT_MARKER', 'sword', 81)
        self.ESC.Runtime.Hit('ally', 'enemy', 82)
        self.hit('ally', 83)
        self.assertEqual(len(self.effects(KEYS[0])), 2)
        self.assertEqual(self.F.resource('sword').Amount, 3)
        self.hit('sword', 84, 'xingge_wenlu')
        self.hit('ally', 85)
        self.assertEqual(len(self.effects(KEYS[0])), 4)
        self.assertEqual(self.F.resource('sword').Amount, 6)

    def test_each_real_ally_gets_one_mark_response_and_enemy_self_do_not(self):
        self.actor('ally2', level=0, hp=100, x=4)
        self.hit('sword', 81, 'xingge_wenlu')
        self.hit('sword', 82)
        self.hit('enemy', 83)
        self.assertEqual(len(self.effects(KEYS[0])), 1)
        self.hit('ally', 84)
        self.hit('ally2', 85)
        self.hit('ally2', 86)
        self.assertEqual(len(self.effects(KEYS[0])), 3)
        self.assertEqual(self.F.resource('sword').Amount, 6)

    def test_no_mark_on_cast_without_hit_or_after_expiry_or_weakpoint(self):
        self.ESC.Runtime.BeginCast('sword', bridge.SPEC['spells']['xingge_wenlu']['stat'], 81, 'enemy')
        self.assertEqual(self.effects(KEYS[0]), [])
        self.ESC.Runtime.Hit('sword', 'enemy', 81)
        self.ESC.State('sword').turn = 3
        self.hit('ally', 82)
        self.assertEqual(len(self.effects(KEYS[0])), 1)
        self.F.entities['sword'].Classes.Classes[1].SubClassUUID = bridge.SPEC['classes']['taixuan']
        self.hit('sword', 83, 'taixuan_zhaoxi')
        self.assertEqual(len(self.effects(KEYS[0])), 1)

    def test_mixed_type_transfer_has_one_receipt_on_actual_receiver_after_damage(self):
        self.domain()
        self.assertEqual(self.effects(KEYS[1]), [])
        self.F.clearCalls()
        parts = self.table([{'Amount': 4, 'DamageType': 'Fire'}, {'Amount': 4, 'DamageType': 'Cold'}])
        final, credited = self.ESC.Runtime.Defense('ally', 8, False, False, parts)
        self.assertEqual((final, credited), (5, 8))
        damage = [c for c in self.F.calls.values() if c.name == 'ApplyDamage']
        self.assertEqual([(c.args[1], c.args[2], c.args[3]) for c in damage],
                         [('sword', 1, 'Fire'), ('sword', 2, 'Cold')])
        self.assertEqual(self.F.entities['sword']._hp, 98)
        self.assertEqual([c.args[1] for c in self.effects(KEYS[1])], ['sword'])
        calls = [c.name for c in self.F.calls.values()]
        self.assertGreater(calls.index('PlayEffect'), max(i for i, name in enumerate(calls) if name == 'ApplyDamage'))

    def test_zero_or_fully_absorbed_transfer_and_transfer_recursion_have_no_receipt(self):
        self.domain()
        self.ESC.Runtime.Defense('ally', 1, False, False)  # floor(.45) == 0
        self.ESC.State('ally').shield = 100
        self.ESC.Runtime.Defense('ally', 10, False, False)
        self.ESC.Runtime.Defense('ally', 10, False, True)
        self.assertEqual(self.effects(KEYS[1]), [])
        self.assertEqual(self.F.entities['sword']._hp, 100)

    def test_repeated_actual_transfers_each_get_one_receipt_without_changing_damage(self):
        self.domain()
        for _ in range(2):
            self.assertEqual(self.ESC.Runtime.Defense('ally', 10, False, False)[0], 6)
        self.assertEqual(self.F.entities['sword']._hp, 96)
        self.assertEqual(len(self.effects(KEYS[1])), 2)

    def test_missing_disabled_or_empty_event_records_suppress_visual_only(self):
        for mode in ('disabled', 'missing', 'empty'):
            with self.subTest(mode=mode):
                self.setUp()
                if mode == 'disabled':
                    self.vfx.enabled = False
                elif mode == 'missing':
                    self.vfx.records = None
                else:
                    for key in KEYS:
                        self.vfx.records[key].effect = ''
                self.hit('sword', 81, 'xingge_wenlu')
                self.hit('ally', 82)
                self.assertEqual(self.F.resource('sword').Amount, 3)
                self.domain()
                self.assertEqual(self.ESC.Runtime.Defense('ally', 10, False, False)[0], 6)
                self.assertEqual(self.F.entities['sword']._hp, 98)
                self.assertEqual(self.effects(KEYS[0]) + self.effects(KEYS[1]), [])

    def test_native_visual_failure_cannot_interrupt_mark_rewards_or_actual_transfer(self):
        self.lua.execute("function Osi.PlayEffect(...) error('simulated native VFX failure') end")
        self.hit('sword', 81, 'xingge_wenlu')
        self.hit('ally', 82)
        self.assertEqual(self.F.resource('sword').Amount, 3)
        self.domain()
        self.assertEqual(self.ESC.Runtime.Defense('ally', 10, False, False)[0], 6)
        self.assertEqual(self.F.entities['sword']._hp, 98)

    def test_only_actual_party_nodes_inside_six_meters_get_domain_visuals(self):
        self.actor('boundary', level=0, hp=100, x=6)
        self.actor('outside', level=0, hp=100, x=6.001)
        self.actor('summon', level=0, hp=100, x=1)._summon = True
        self.actor('dead', level=0, hp=100, x=1)._dead = True
        self.actor('zero', level=0, hp=0, x=1)
        self.actor('dying', level=0, hp=1, x=1)
        self.lua.globals().Osi.ApplyStatus('dying', 'DYING', -1, 1, 'dying')
        self.update()
        self.assertFalse(self.active('ally', SHARE))
        self.domain()
        self.domain('xingge_zhangjian', action=101)
        for target in ('ally', 'boundary'):
            self.assertTrue(self.active(target, SHARE))
            self.assertTrue(self.active(target, TEAM))
        self.assertFalse(self.active('sword', SHARE))
        self.assertTrue(self.active('sword', TEAM))
        for target in ('enemy', 'outside', 'summon', 'dead', 'zero', 'dying'):
            self.assertFalse(self.active(target, SHARE), target)
            self.assertFalse(self.active(target, TEAM), target)

    def test_visual_updates_are_idempotent_and_do_not_change_resources_or_deadlines(self):
        self.domain()
        self.domain('xingge_zhangjian', action=101)
        state = self.ESC.State('sword')
        state.shield = 7
        before = (self.F.entities['sword']._hp, self.F.resource('sword').Amount,
                  state.domains.xingge_fengyu.expires, state.domains.xingge_zhangjian.expires)
        self.F.clearCalls()
        for _ in range(20):
            self.update()
        self.assertEqual(self.status_calls('ApplyStatus', SHARE) + self.status_calls('ApplyStatus', TEAM), [])
        self.assertEqual(before, (self.F.entities['sword']._hp, self.F.resource('sword').Amount,
                                state.domains.xingge_fengyu.expires, state.domains.xingge_zhangjian.expires))
        self.assertEqual(state.shield, 7)

    def test_osiris_and_ecs_aliases_cannot_remove_the_same_active_visual(self):
        self.entity_alias('Hero_sword', 'sword')
        self.entity_alias('Companion_ally', 'ally')
        # Register both names through normal Runtime entry points, as native
        # story events and ECS discovery do in the actual client.
        for target in ('sword', 'Hero_sword', 'ally', 'Companion_ally'):
            self.ESC.State(target)
        self.F.clearCalls()
        self.domain()
        self.domain('xingge_zhangjian', action=101)
        state = self.ESC.State('sword')
        before = (self.F.entities['sword']._hp, self.F.resource('sword').Amount,
                  state.domains.xingge_fengyu.expires, state.domains.xingge_zhangjian.expires)
        for _ in range(20):
            self.update()
        for target, status in (('sword', TEAM), ('ally', TEAM), ('ally', SHARE)):
            self.assertTrue(self.active(target, status), (target, status))
            self.assertEqual(len([c for c in self.status_calls('ApplyStatus', status)
                                  if c.args[1] == target]), 1)
        self.assertFalse(self.active('sword', SHARE))
        self.assertEqual(self.status_calls('RemoveStatus', TEAM)
                         + self.status_calls('RemoveStatus', SHARE), [])
        self.assertEqual(before, (self.F.entities['sword']._hp, self.F.resource('sword').Amount,
                                state.domains.xingge_fengyu.expires, state.domains.xingge_zhangjian.expires))
        self.F.clearCalls()
        state.turn = 4
        self.update()
        self.update()
        self.assertEqual(sorted((c.args[1], c.args[2]) for c in self.F.calls.values()
                                if c.name == 'RemoveStatus' and c.args[2] in (TEAM, SHARE)),
                         [('ally', SHARE), ('ally', TEAM), ('sword', TEAM)])

    def test_alias_owner_is_self_even_when_native_party_relation_excludes_self(self):
        self.entity_alias('Hero_sword', 'sword')
        self.lua.execute('''local party=Osi.IsInPartyWith
            function Osi.IsInPartyWith(a,b)
                if Ext.Entity.Get(a)==Ext.Entity.Get(b) then return 0 end
                return party(a,b)
            end''')
        self.domain(owner='Hero_sword')
        self.domain('xingge_zhangjian', owner='Hero_sword', action=101)
        self.update()
        self.assertTrue(self.active('sword', TEAM))
        self.assertFalse(self.active('sword', SHARE))
        self.assertTrue(self.active('ally', SHARE))
        self.assertTrue(self.active('ally', TEAM))

    def test_leaving_reentering_or_changing_party_reconciles_recipient(self):
        self.domain()
        self.domain('xingge_zhangjian', action=101)
        self.F.entities['ally'].Transform.Transform.Translate[1] = 6.001
        self.update()
        self.assertFalse(self.active('ally', SHARE))
        self.assertFalse(self.active('ally', TEAM))
        self.F.entities['ally'].Transform.Transform.Translate[1] = 6
        self.update()
        self.assertTrue(self.active('ally', SHARE))
        self.F.entities['ally']._party = 'enemies'
        self.update()
        self.assertFalse(self.active('ally', SHARE))
        self.assertFalse(self.active('ally', TEAM))

    def test_owner_movement_and_recipient_downing_remove_visuals(self):
        self.domain()
        self.F.entities['sword'].Transform.Transform.Translate[1] = -2
        self.update()
        self.assertFalse(self.active('ally', SHARE))
        self.F.entities['sword'].Transform.Transform.Translate[1] = 0
        self.update()
        self.assertTrue(self.active('ally', SHARE))
        self.lua.globals().Osi.ApplyStatus('ally', 'DOWNED', -1, 1, 'enemy')
        self.F.emit('StatusApplied', 'ally', 'DOWNED', 'enemy', 200)
        self.assertFalse(self.active('ally', SHARE))

    def test_invalid_equipment_pauses_visual_and_does_not_revive_expired_domain(self):
        for equipment in ('Shield', 'MediumArmor', 'HeavyArmor'):
            with self.subTest(equipment=equipment):
                self.setUp()
                self.domain()
                self.domain('xingge_zhangjian', action=101)
                if equipment == 'Shield':
                    self.F.entities['sword']._equipped.Shield = 'shield'
                else:
                    self.actor('armor', level=0)._proficiencies = self.table({equipment: True})
                    self.F.entities['sword']._equipped.Breast = 'armor'
                self.F.emit('Equipped', 'shield' if equipment == 'Shield' else 'armor', 'sword')
                self.assertFalse(self.active('ally', SHARE))
                self.assertFalse(self.active('ally', TEAM))
                self.F.entities['sword']._equipped.Shield = None
                self.F.entities['sword']._equipped.Breast = None
                self.F.emit('Unequipped', 'shield' if equipment == 'Shield' else 'armor', 'sword')
                self.assertTrue(self.active('ally', SHARE))
                self.ESC.State('sword').turn = 4
                self.update()
                self.assertFalse(self.active('ally', SHARE))
                self.assertFalse(self.active('ally', TEAM))

    def test_owner_death_or_subclass_or_class_removal_cleans_party_visuals(self):
        for mode in ('dead', 'subclass', 'class'):
            with self.subTest(mode=mode):
                self.setUp()
                self.domain()
                self.domain('xingge_zhangjian', action=101)
                if mode == 'dead':
                    self.F.entities['sword']._dead = True
                    self.F.emit('StatusApplied', 'sword', 'DEAD', 'enemy', 200)
                else:
                    if mode == 'class':
                        self.F.entities['sword'].Classes.Classes = self.table([])
                    else:
                        self.F.entities['sword'].Classes.Classes[1].SubClassUUID = bridge.SPEC['classes']['taixuan']
                    self.F.emit('RespecCompleted', 'sword')
                self.assertFalse(self.active('ally', SHARE))
                self.assertFalse(self.active('ally', TEAM))
                self.assertFalse(self.active('sword', TEAM))

    def test_four_owner_turns_keep_three_then_expire_both_visuals(self):
        self.domain()
        self.domain('xingge_zhangjian', action=101)
        for _ in range(3):
            self.F.emit('TurnStarted', 'sword')
            self.assertTrue(self.active('ally', SHARE))
            self.assertTrue(self.active('ally', TEAM))
        self.F.emit('TurnStarted', 'sword')
        self.assertFalse(self.active('ally', SHARE))
        self.assertFalse(self.active('ally', TEAM))

    def test_overlapping_owners_keep_one_visual_until_last_domain_ends(self):
        self.actor('owner2', branch='xingge', hp=100, x=1)
        self.domain()
        self.domain(owner='owner2', action=101)
        self.assertEqual(len([c for c in self.status_calls('ApplyStatus', SHARE) if c.args[1] == 'ally']), 1)
        self.ESC.State('sword').turn = 4
        self.update()
        self.assertTrue(self.active('ally', SHARE))
        self.ESC.State('owner2').turn = 4
        self.update()
        self.assertFalse(self.active('ally', SHARE))

    def test_native_domain_removal_cleans_visuals(self):
        self.domain()
        self.lua.globals().Osi.RemoveStatus('sword', 'ESC_DAMAGE_SHARE', 'sword')
        self.F.emit('StatusRemoved', 'sword', 'ESC_DAMAGE_SHARE', 'sword', 100)
        self.assertFalse(self.active('ally', SHARE))

    def test_session_reload_removes_orphan_visual_on_previously_unwatched_non_sword_ally(self):
        self.lua.globals().Osi.ApplyStatus('ally', SHARE, -1, 1, 'ally')
        self.lua.globals().Osi.ApplyStatus('ally', TEAM, -1, 1, 'ally')
        self.F.event('SessionLoaded', self.table({}))
        self.assertFalse(self.active('ally', SHARE))
        self.assertFalse(self.active('ally', TEAM))

    def test_session_reload_restores_missing_visual_only_when_domain_is_real(self):
        self.domain()
        self.lua.globals().Osi.RemoveStatus('ally', SHARE, 'ally')
        self.F.event('SessionLoaded', self.table({}))
        self.assertTrue(self.active('ally', SHARE))
        self.lua.globals().Osi.RemoveStatus('sword', 'ESC_DAMAGE_SHARE', 'sword')
        self.F.event('SessionLoaded', self.table({}))
        self.assertFalse(self.active('ally', SHARE))

    def test_disabled_missing_record_or_missing_status_cleans_old_visual_without_domain_mutation(self):
        for mode in ('disabled', 'record', 'status'):
            with self.subTest(mode=mode):
                self.setUp()
                self.domain()
                if mode == 'disabled':
                    self.vfx.enabled = False
                elif mode == 'record':
                    self.vfx.records.xingge_fengyu_status = None
                else:
                    self.F.stats[SHARE] = None
                self.update()
                self.assertFalse(self.active('ally', SHARE))
                self.assertIsNotNone(self.ESC.State('sword').domains.xingge_fengyu)


if __name__ == '__main__':
    unittest.main()
