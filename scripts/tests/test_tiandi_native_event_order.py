"""Replay H14 action 65's native callback order and Name_GUID aliases.

This is a deterministic regression, not client visual or cost acceptance.
"""
import unittest

import test_tianqing_runtime_vfx as staged


NATIVE_ORDER = r'''
local F=Fixture
F.entityAliases={Player_sword='sword',Goblin_enemy0='enemy0',Goblin_enemy1='enemy1'}
local originalGet=Ext.Entity.Get
function Ext.Entity.Get(ref) return originalGet(F.entityAliases[ref] or ref) end
for name,original in pairs(Osi) do
    if type(original)=='function' then
        Osi[name]=function(...)
            local args=table.pack(...)
            for i=1,args.n do args[i]=F.entityAliases[args[i]] or args[i] end
            return original(table.unpack(args,1,args.n))
        end
    end
end
function Osi.UseSpell(source,spell,target,originator,withoutMove)
    assert((F.stats[spell].UseCosts or '')=='','Stage helper must remain free')
    F.calls[#F.calls+1]={name='UseSpell',args={source,spell,target,originator,withoutMove},at=F.now}
    F.nextAction=F.nextAction+1;local action=F.nextAction
    local owner=ESC.Engine.uuid(ESC.Engine.entity(source))
    local victim=ESC.Engine.uuid(ESC.Engine.entity(target))
    local eventOwner='Player_'..owner
    local eventTarget=F.bareTarget and victim or 'Goblin_'..victim
    local outcome=table.remove(F.outcomes,1) or {}
    local packet={source=owner,spell=spell,target=victim,action=action}
    F.nativeCasts[#F.nativeCasts+1]=packet
    if outcome.raiseDispatch then error('Native dispatch fixture failure') end
    packet.complete=function()
    local function damageAndMarkers()
        if outcome.hit==false or outcome.failed then return end
        for _,amount in ipairs({7,61}) do
            local hit={DamageList={{Amount=amount,DamageType='Force'}},TotalDamageDone=amount,SpellId=spell}
            local evt={Caster=owner,Target=victim,StoryActionId=action,Hit=hit}
            F.event('DealDamage',evt);F.event('BeforeDealDamage',{Hit=hit})
            F.entities[victim]._hp=F.entities[victim]._hp-hit.TotalDamageDone
            evt.Result={Hit=hit};F.event('DealtDamage',evt)
        end
        if (F.stats[spell].SpellSuccess or ''):find('SavingThrow(Ability.Strength',1,true) then
            F.calls[#F.calls+1]={name='NativeStrengthSave',args={source,victim,action,spell},at=F.now}
            if outcome.saveSucceeds==false then
                F.emit('StatusApplied',victim,'ESC_SAVEFAIL_TIANQING_TIANDI',owner,action)
            end
        end
        F.emit('StatusApplied',victim,'ESC_HIT_MARKER',owner,action)
    end
    if not F.finishBeforeDamage then damageAndMarkers() end
    if outcome.failed then F.emit('CastSpellFailed',eventOwner,spell,'Target','',action)
    else F.emit('CastedSpell',eventOwner,spell,'Target','',action) end
    if F.finishBeforeDamage then damageAndMarkers() end
    F.emit('UsingSpell',eventOwner,spell,'Target','',action)
    if not outcome.noTarget then F.emit('UsingSpellOnTarget',eventOwner,eventTarget,spell,'Target','',action) end
    if F.duplicateNative and not outcome.noTarget then
        F.emit('UsingSpellOnTarget',owner,victim,spell,'Target','',action)
        F.emit('CastedSpell',owner,spell,'Target','',action)
    end
    end
    if not F.deferNative then packet.complete() end
end
function F.completeNative(packet)
    assert(not packet.done,'Native fixture cast may finish only once');packet.done=true
    packet.complete()
end
'''


class NativeTiandiOrder(unittest.TestCase):
    table = staged.TianqingRuntimeVfx.table
    spell = staged.TianqingRuntimeVfx.spell
    calls = staged.TianqingRuntimeVfx.calls
    begin = staged.TianqingRuntimeVfx.begin
    finish = staged.TianqingRuntimeVfx.finish
    stage_calls = staged.TianqingRuntimeVfx.stage_calls

    def setUp(self):
        staged.TianqingRuntimeVfx.setUp(self)
        self.lua.execute(NATIVE_ORDER)
        for target in ('enemy0', 'enemy1'):
            self.F.entities[target]._hp = 1000
            self.F.entities[target]._maxHp = 1000

    def run_three(self, outcomes=None):
        if outcomes:
            self.F.outcomes = self.table(outcomes)
        self.finish(self.begin(targets=('Goblin_enemy0',)))
        self.F.advance(3000)

    def assert_finished(self, hits=3):
        self.assertEqual(len(self.stage_calls()), 3)
        self.assertEqual(self.F.entities['enemy0']._hp, 1000-68*hits)
        self.assertIsNone(self.F.entities['sword'].Vars.ESC_State.tianqingStages['100'])
        self.assertEqual(len(self.calls('PlayEffectAtPosition')), 3)

    def test_damage_then_completion_before_target_releases_all_three(self):
        self.run_three()
        self.assert_finished()
        self.assertEqual(len(self.calls('NativeStrengthSave')), 1)

    def test_completion_before_damage_and_duplicate_aliases_do_not_repeat(self):
        self.F.finishBeforeDamage = True
        self.F.duplicateNative = True
        self.F.bareTarget = True
        self.run_three()
        self.assert_finished()
        self.assertEqual(len(self.calls('NativeStrengthSave')), 1)

    def test_miss_then_hit_waits_for_actual_target_and_attempts_control_once(self):
        self.run_three([dict(hit=False), dict(saveSucceeds=False), dict(hit=True)])
        self.assert_finished(hits=2)
        self.assertEqual(len(self.calls('NativeStrengthSave')), 1)

    def test_failed_targetless_completion_releases_queue_after_target_arrives(self):
        self.run_three([dict(failed=True), dict(hit=True), dict(hit=True)])
        self.assert_finished(hits=2)
        self.assertEqual(len(self.calls('NativeStrengthSave')), 1)

    def test_two_targets_keep_independent_three_hit_and_control_ledgers(self):
        self.F.duplicateNative = True
        self.finish(self.begin(targets=('Goblin_enemy0', 'Goblin_enemy1')))
        self.F.advance(3000)
        self.assertEqual(len(self.stage_calls()), 6)
        for target in ('enemy0', 'enemy1'):
            self.assertEqual(self.F.entities[target]._hp, 796)
        self.assertEqual(len(self.calls('NativeStrengthSave')), 2)
        self.assertIsNone(self.F.entities['sword'].Vars.ESC_State.tianqingStages['100'])

    def test_duplicate_root_target_aliases_do_not_double_damage(self):
        self.finish(self.begin(targets=('Goblin_enemy0', 'enemy0')))
        self.F.advance(3000)
        self.assert_finished()

    def test_legacy_named_target_queue_resolves_against_uuid_damage(self):
        self.finish(self.begin(targets=('Goblin_enemy0',)))
        # A saved pre-fix cast can still contain Name_GUID target/ledger keys.
        entry = self.F.entities['sword'].Vars.ESC_State.tianqingStages['100']
        entry.targets = self.table(['Goblin_enemy0'])
        self.F.advance(3000)
        self.assert_finished()

    def test_sync_failure_without_target_uses_exact_dispatch_and_keeps_paid_cost(self):
        self.F.resource('sword').Amount = 30
        action = self.F.entities['sword'].ActionResources.Resources[self.lua.globals().ESC.Engine.action][1]
        action.Amount = 0
        self.run_three([dict(failed=True, noTarget=True), dict(hit=True), dict(hit=True)])
        self.assert_finished(hits=2)
        self.assertEqual(len(self.calls('NativeStrengthSave')), 1)
        self.assertEqual(self.F.resource('sword').Amount, 30)
        self.assertEqual(action.Amount, 0)

    def test_two_target_sync_failure_releases_only_its_exact_dispatch(self):
        self.F.outcomes = self.table([dict(failed=True, noTarget=True)])
        self.finish(self.begin(targets=('Goblin_enemy0', 'Goblin_enemy1')))
        self.F.advance(3000)
        self.assertEqual(len(self.stage_calls()), 6)
        self.assertEqual(self.F.entities['enemy0']._hp, 864)
        self.assertEqual(self.F.entities['enemy1']._hp, 796)
        self.assertEqual(len(self.calls('NativeStrengthSave')), 2)
        self.assertIsNone(self.F.entities['sword'].Vars.ESC_State.tianqingStages['100'])

    def test_nested_dispatch_after_failed_second_stage_preserves_exact_binding(self):
        self.F.deferNative = True
        self.F.outcomes = self.table([dict(hit=True), dict(failed=True, noTarget=True), dict(hit=True)])
        self.finish(self.begin(targets=('Goblin_enemy0',)))
        self.F.advance(2800)
        self.F.deferNative = False
        self.F.completeNative(self.F.nativeCasts[1])
        self.F.advance(3000)  # Stage 3 dispatches inside stage 2's failure callback.
        self.assert_finished(hits=2)
        self.assertEqual(len(self.calls('NativeStrengthSave')), 1)

    def test_dispatch_exception_restores_context_and_never_retries_uncertain_stage(self):
        self.run_three([dict(raiseDispatch=True), dict(hit=True), dict(hit=True)])
        self.assert_finished(hits=2)
        self.assertEqual(len(self.calls('NativeStrengthSave')), 1)
        self.assertEqual(len([call for call in self.calls('Print') if 'native dispatch failed' in call.args[1]]), 1)

    def test_async_failure_without_target_cancels_without_replaying_damage(self):
        self.F.deferNative = True
        self.F.outcomes = self.table([dict(failed=True, noTarget=True)])
        self.finish(self.begin(targets=('Goblin_enemy0',)))
        self.F.advance(2800)
        self.F.completeNative(self.F.nativeCasts[1])
        self.F.runNextTick()
        self.F.advance(6000)
        self.assertEqual(len(self.stage_calls()), 1)
        self.assertEqual(self.F.entities['enemy0']._hp, 1000)
        self.assertIsNone(self.F.entities['sword'].Vars.ESC_State.tianqingStages['100'])

    def test_async_failure_does_not_cancel_another_already_bound_parent(self):
        self.F.deferNative = True
        self.F.outcomes = self.table([dict(failed=True, noTarget=True), dict(hit=True)])
        self.finish(self.begin(targets=('Goblin_enemy0',)))
        self.finish(self.begin(targets=('Goblin_enemy1',), action=101), action=101)
        self.F.advance(2800)
        bound = self.F.nativeCasts[2]
        self.F.emit('UsingSpellOnTarget', 'Player_sword', 'Goblin_enemy1', bound.spell, 'Target', '', bound.action)
        self.F.completeNative(self.F.nativeCasts[1])
        self.F.runNextTick()
        self.F.deferNative = False
        self.F.completeNative(bound)
        self.F.advance(3000)
        self.assertEqual(len(self.stage_calls()), 4)
        self.assertEqual(self.F.entities['enemy0']._hp, 1000)
        self.assertEqual(self.F.entities['enemy1']._hp, 796)
        self.assertEqual(len(self.calls('NativeStrengthSave')), 1)
        self.assertIsNone(self.F.entities['sword'].Vars.ESC_State.tianqingStages['100'])
        self.assertIsNone(self.F.entities['sword'].Vars.ESC_State.tianqingStages['101'])

    def test_ambiguous_async_failure_cancels_unbound_parents_without_guessing_target(self):
        self.F.deferNative = True
        self.F.outcomes = self.table([dict(failed=True, noTarget=True)])
        self.finish(self.begin(targets=('Goblin_enemy0',)))
        self.finish(self.begin(targets=('Goblin_enemy1',), action=101), action=101)
        self.F.advance(2800)
        self.F.completeNative(self.F.nativeCasts[1])
        self.F.runNextTick()
        self.F.advance(6000)
        self.assertEqual(len(self.stage_calls()), 2)
        self.assertEqual(self.F.entities['enemy0']._hp, 1000)
        self.assertEqual(self.F.entities['enemy1']._hp, 1000)
        self.assertIsNone(self.F.entities['sword'].Vars.ESC_State.tianqingStages['100'])
        self.assertIsNone(self.F.entities['sword'].Vars.ESC_State.tianqingStages['101'])

    def test_late_abandoned_failure_target_cannot_steal_a_new_dispatch(self):
        self.F.deferNative = True
        self.F.outcomes = self.table([dict(failed=True, noTarget=True)])
        self.finish(self.begin(targets=('Goblin_enemy0',)))
        self.F.advance(800)
        failed = self.F.nativeCasts[1]
        self.F.completeNative(failed)
        self.F.runNextTick()
        self.finish(self.begin(targets=('Goblin_enemy0',), action=200), action=200)
        self.F.advance(1600)
        self.F.emit('UsingSpellOnTarget', 'Player_sword', 'Goblin_enemy0', failed.spell, 'Target', '', failed.action)
        self.F.emit('CastedSpell', 'Player_sword', failed.spell, 'Target', '', failed.action)
        self.F.deferNative = False
        self.F.completeNative(self.F.nativeCasts[2])
        self.F.advance(4000)
        self.assertEqual(len(self.stage_calls()), 4)
        self.assertEqual(self.F.entities['enemy0']._hp, 796)
        self.assertEqual(len(self.calls('NativeStrengthSave')), 1)
        self.assertIsNone(self.F.entities['sword'].Vars.ESC_State.tianqingStages['100'])
        self.assertIsNone(self.F.entities['sword'].Vars.ESC_State.tianqingStages['200'])

    def test_async_failure_with_late_target_before_next_tick_keeps_remaining_stages(self):
        self.F.deferNative = True
        self.F.outcomes = self.table([dict(failed=True)])
        self.finish(self.begin(targets=('Goblin_enemy0',)))
        self.F.advance(800)
        self.F.completeNative(self.F.nativeCasts[1])
        self.F.runNextTick()
        self.F.deferNative = False
        self.F.advance(3000)
        self.assert_finished(hits=2)

    def test_old_orphaned_named_flight_is_cancelled_on_reload_without_any_replay(self):
        self.F.deferNative = True
        spell = self.begin(targets=('Goblin_enemy0',))
        self.finish(spell)
        self.F.advance(2800)
        state = self.F.entities['sword'].Vars.ESC_State
        entry = state.tianqingStages['100']
        ledger = entry.targetLedger['enemy0']
        self.assertIsNone(ledger.inFlight.action)
        self.assertEqual(len(ledger.queue), 2)
        # H14 has already dealt stage one's damage, but lost the action binding.
        entry.targets = self.table(['Goblin_enemy0'])
        entry.targetLedger['Goblin_enemy0'] = ledger
        entry.targetLedger['enemy0'] = None
        self.F.entities['enemy0']._hp = 932
        self.F.reload()
        self.F.advance(6000)
        self.F.reload()
        self.finish(spell)
        self.F.handlers['ESC_TianqingStage'](self.table(dict(id='sword', token='100', stage=3, kind='resolve')), 999)
        self.F.advance(9000)
        self.assertEqual(len(self.stage_calls()), 1)
        self.assertEqual(len(self.calls('PlayEffectAtPosition')), 3)
        self.assertEqual(self.F.entities['enemy0']._hp, 932)
        self.assertIsNone(state.tianqingStages['100'])
        self.assertIn('100', list(state.tianqingDone.values()))

    def test_bound_native_completion_still_survives_reload(self):
        self.finish(self.begin(targets=('Goblin_enemy0', 'Goblin_enemy1')))
        self.F.advance(800)
        self.F.reload()  # Lose the one millisecond queue-release closures.
        self.F.advance(3000)
        self.assertEqual(len(self.stage_calls()), 6)
        self.assertEqual(self.F.entities['enemy0']._hp, 796)
        self.assertEqual(self.F.entities['enemy1']._hp, 796)
        self.assertEqual(len(self.calls('NativeStrengthSave')), 2)
        self.assertIsNone(self.F.entities['sword'].Vars.ESC_State.tianqingStages['100'])


if __name__ == '__main__':
    unittest.main()
