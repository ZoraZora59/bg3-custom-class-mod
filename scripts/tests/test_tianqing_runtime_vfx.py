"""Run production Lua against a deterministic BG3 boundary, not a client.

Effects, native casts, timers and AI-grid queries are recorded. These fixtures
prove scheduling/cancellation contracts; compiled-bank appearance, native event
delivery and real terrain still require game acceptance.
"""
import copy
import json
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts'))
sys.path.insert(0, str(REPO / 'build/test-tools'))
from lupa import LuaRuntime
from sword_cultivator_spec import FOLDER, guid

LUA = REPO / 'mods/EasternSwordCultivator/Source/Mods' / FOLDER / 'ScriptExtender/Lua'

BOUNDARY = r'''
Fixture.now=0;Fixture.clock={};Fixture.handlers={};Fixture.nextTimer=0;Fixture.nextAction=20000;Fixture.nativeCasts={};Fixture.outcomes={}
local F=Fixture
local function record(name,...)
    F.calls[#F.calls+1]={name=name,args={...},at=F.now}
end
local function timer(ms,callback,name,args)
    F.nextTimer=F.nextTimer+1;local handle=F.nextTimer
    F.clock[handle]={at=F.now+ms,callback=callback,name=name,args=args};return handle
end
function Ext.Timer.WaitFor(ms,callback) return timer(ms,callback) end
function Ext.Timer.WaitForPersistent(ms,name,args)
    assert(type(name)=='string' and type(args)=='table','Persistent timer requires serializable payload')
    return timer(ms,nil,name,args)
end
function Ext.Timer.RegisterPersistentHandler(name,callback) F.handlers[name]=callback end
function Ext.Timer.Cancel(handle) F.clock[handle]=nil end
function F.advance(untilMs)
    while true do
        local handle,nextTimer
        for h,t in pairs(F.clock) do
            if t.at<=untilMs and (not nextTimer or t.at<nextTimer.at or t.at==nextTimer.at and h<handle) then handle,nextTimer=h,t end
        end
        if not nextTimer then break end
        F.now=nextTimer.at;F.clock[handle]=nil
        if nextTimer.name then F.handlers[nextTimer.name](nextTimer.args,handle) else nextTimer.callback() end
    end
    F.now=untilMs
end
function F.reload()
    -- Emulate documented persistent freeze/restore with fresh timer handles.
    -- Ordinary Lua closures are discarded; SessionLoaded must recover them.
    local saved={}
    for _,t in pairs(F.clock) do if t.name then saved[#saved+1]={ms=t.at-F.now,name=t.name,args=t.args} end end
    F.clock={}
    for _,t in ipairs(saved) do timer(t.ms,nil,t.name,t.args) end
    F.event('SessionLoaded',{})
end
function Osi.PlayEffectAtPosition(...)
    assert(select('#',...)==5,'BG3 requires effect,X,Y,Z,scale')
    record('PlayEffectAtPosition',...)
end
function Osi.FindValidPosition(...)
    assert(select('#',...)==6,'BG3 AI-grid query takes six inputs')
    record('FindValidPosition',...)
    local x,y,z=...
    if F.ground then return F.ground(x,y,z) end
    return x,y,z
end
function F.completeNative(packet)
    assert(not packet.done,'Native fixture cast may finish only once');packet.done=true
    local source,spell,target,action=packet.source,packet.spell,packet.target,packet.action
    local outcome=packet.outcome or {}
    if outcome.failed then F.emit('CastSpellFailed',source,spell,'Target','',action);return end
    if F.finishBeforeHit then F.emit('CastedSpell',source,spell,'Target','',action) end
    if outcome.hit~=false then
        local success=F.stats[spell].SpellSuccess or ''
        if success:find('SavingThrow(Ability.Strength',1,true) then
            record('NativeStrengthSave',source,target,action,spell)
            if outcome.saveSucceeds==false then F.emit('StatusApplied',target,'ESC_SAVEFAIL_TIANQING_TIANDI',source,action) end
        end
        if success:find('ApplyStatus(ESC_HIT_MARKER',1,true) then F.emit('StatusApplied',target,'ESC_HIT_MARKER',source,action) end
    end
    if not F.finishBeforeHit then F.emit('CastedSpell',source,spell,'Target','',action) end
end
function Osi.UseSpell(source,spell,target,originator,withoutMove)
    record('UseSpell',source,spell,target,originator,withoutMove)
    assert(F.stats[spell] and (F.stats[spell].UseCosts or '')=='','Stage helper must be free')
    F.nextAction=F.nextAction+1;local action=F.nextAction
    F.emit('UsingSpellOnTarget',source,target,spell,'Target','',action)
    local packet={source=source,spell=spell,target=target,action=action,outcome=table.remove(F.outcomes,1)}
    F.nativeCasts[#F.nativeCasts+1]=packet
    if not F.deferNative then F.completeNative(packet) end
end
'''


class TianqingRuntimeVfx(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads((LUA / 'GeneratedSpec.json').read_text(encoding='utf-8'))
        # A configuration injection exercises compiled-enabled behavior even
        # while authoring/build receipts intentionally gate the production spec.
        self.spec = copy.deepcopy(self.spec)
        records = {key: {'effect': guid('vfx/tianqing/effect/' + key), 'hitTimeMs': 800}
                   for key in ('tianqing_wanjun', 'tianqing_lietian', 'tianqing_tianjian', 'tianqing_bafang', 'tianqing_tiandi')}
        self.spec['tianqingVfx'] = dict(enabled=True, records=records,
            tiandi=dict(effect=records['tianqing_tiandi']['effect'], hitTimeMs=800, intervalMs=1000, stageCount=3),
            bafang=dict(effect=guid('vfx/tianqing/effect/tianqing_bafang_column'), count=8, radius=8,
                        angleOffset=22.5, terrainSearchRadius=1))
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().GeneratedSpec = self.table(self.spec)
        self.lua.execute((Path(__file__).parent / 'esc_engine_fixture.lua').read_text(encoding='utf-8'))
        stats = {}
        for file in (LUA.parents[3] / 'Public' / FOLDER / 'Stats/Generated/Data').glob('*.txt'):
            for chunk in re.split(r'(?=new entry ")', file.read_text(encoding='utf-8')):
                name = re.search(r'new entry "([^"]+)"', chunk)
                if name:
                    stats[name.group(1)] = dict(re.findall(r'data "([^"]+)" "([^"]*)"', chunk))
        self.stats = stats
        self.lua.globals().Fixture.stats = self.table(stats)
        self.lua.execute(BOUNDARY)
        self.lua.execute('ESC={}')
        self.lua.globals().ESC.Rules = self.lua.execute((LUA / 'Rules.lua').read_text(encoding='utf-8'))
        self.lua.globals().ESC.Engine = self.lua.execute((LUA / 'Engine.lua').read_text(encoding='utf-8'))
        module_cache = {}
        def require(path):
            if path not in module_cache:
                module_cache[path] = self.lua.execute((LUA / path).read_text(encoding='utf-8'))
            return module_cache[path]
        self.lua.globals().Ext.Require = require
        self.lua.execute((LUA / 'Runtime.lua').read_text(encoding='utf-8'))
        self.F = self.lua.globals().Fixture
        self.F.actor('sword', 12, 'tianqing', 100, 100, 'players', 0)
        self.F.resource('sword').Amount = 50
        for index in range(3):
            self.F.actor('enemy' + str(index), 0, None, 100, 100, 'enemies', index + 1)

    def table(self, obj):
        return self.lua.table_from(obj, recursive=True)

    def spell(self, key, hand='main'):
        # The player casts one canonical root. Hand selection is real equipment,
        # never a restored selector or a forced runtime metadata hand.
        actor = self.F.entities['sword']
        actor._equipped['Melee Main Weapon'] = 'sword:sword' if hand == 'main' else None
        actor._equipped['Melee Offhand Weapon'] = 'sword:sword' if hand == 'off' else None
        self.F.event('EquipmentChanged', {'Character': 'sword'})
        return next(name for name, row in self.spec['aliases'].items()
                    if row.get('key') == key and row.get('hand') == 'auto'
                    and not row.get('internal') and not row.get('legacyMenu'))

    def calls(self, name):
        return [call for call in self.F.calls.values() if call.name == name]

    def begin(self, key='tianqing_tiandi', targets=('enemy0', 'enemy1'), action=100, center=(10, 2, 20), hand='main'):
        spell = self.spell(key, hand)
        self.F.emit('UsingSpell', 'sword', spell, 'Target', '', action)
        if center is not None:
            self.F.emit('UsingSpellAtPosition', 'sword', *center, spell, 'Target', '', action)
        for target in targets:
            self.F.emit('UsingSpellOnTarget', 'sword', target, spell, 'Target', '', action)
            if key == 'tianqing_tiandi':
                self.F.emit('StatusApplied', target, 'ESC_TIANDI_TARGET', 'sword', action)
        return spell

    def finish(self, spell, action=100):
        self.F.emit('CastedSpell', 'sword', spell, 'Target', '', action)

    def stage_calls(self):
        return [call for call in self.calls('UseSpell') if call.args[2].startswith('Target_ESC_TiandiStage')]

    def test_registration_waits_for_success_and_global_three_stage_clock(self):
        spell = self.begin()
        self.assertEqual(self.stage_calls(), [])
        self.assertEqual(self.calls('PlayEffectAtPosition'), [])
        # Native fee boundary: one paid root, six free helpers. Runtime must
        # never mutate either resource while it dispatches staged native casts.
        self.assertIn('ActionPoint:1', self.stats[spell]['UseCosts'])
        self.assertIn('ESC_SwordYuan:20', self.stats[spell]['UseCosts'])
        self.F.resource('sword').Amount = 30
        action = self.F.entities['sword'].ActionResources.Resources[self.lua.globals().ESC.Engine.action][1]
        action.Amount = 0
        self.F.clearCalls()
        self.finish(spell)
        self.F.advance(799)
        self.assertEqual(len(self.stage_calls()), 0)
        self.F.advance(2800)
        self.assertEqual([c.at for c in self.calls('PlayEffectAtPosition')], [0, 1000, 2000])
        self.assertEqual([c.at for c in self.stage_calls()], [800, 800, 1800, 1800, 2800, 2800])
        self.assertEqual(self.F.resource('sword').Amount, 30)
        self.assertEqual(action.Amount, 0)

    def test_fixed_area_and_target_snapshot(self):
        spell = self.begin()
        self.finish(spell)
        self.F.entities['sword'].Transform.Transform.Translate = self.table([99, 8, 99])
        self.F.entities['enemy0'].Transform.Transform.Translate = self.table([80, 9, 90])
        self.F.emit('StatusApplied', 'enemy2', 'ESC_TIANDI_TARGET', 'sword', 100)
        self.F.advance(2800)
        self.assertTrue(all(tuple(c.args[i] for i in (2, 3, 4)) == (10, 2, 20)
                            for c in self.calls('PlayEffectAtPosition')))
        self.assertEqual({c.args[3] for c in self.stage_calls()}, {'enemy0', 'enemy1'})

    def test_duplicate_cast_marker_and_timer_payload_cannot_repeat(self):
        spell = self.begin()
        self.F.emit('StatusApplied', 'enemy0', 'ESC_TIANDI_TARGET', 'sword', 100)
        self.finish(spell)
        self.finish(spell)
        handler = self.F.handlers['ESC_TianqingStage']
        handler(self.table(dict(id='sword', token='100', stage=1, kind='play')), 999)
        self.F.advance(800)
        handler(self.table(dict(id='sword', token='100', stage=1, kind='resolve')), 999)
        self.F.advance(2800)
        self.assertEqual(len(self.calls('PlayEffectAtPosition')), 3)
        self.assertEqual(len(self.stage_calls()), 6)
        self.F.reload()
        self.finish(spell)
        self.F.advance(5600)
        self.assertEqual(len(self.calls('PlayEffectAtPosition')), 3)

    def test_empty_area_still_has_three_swords(self):
        self.finish(self.begin(targets=()))
        self.F.advance(2800)
        self.assertEqual(len(self.calls('PlayEffectAtPosition')), 3)
        self.assertEqual(self.stage_calls(), [])

    def test_offhand_fallback_uses_canonical_root_and_only_free_offhand_helpers(self):
        self.finish(self.begin(hand='off'))
        self.F.advance(2800)
        self.assertEqual({c.args[2] for c in self.stage_calls()}, {'Target_ESC_TiandiStage_Off', 'Target_ESC_TiandiStage_NoControl_Off'})
        self.assertEqual(len(self.stage_calls()), 6)

    def test_failed_root_never_starts(self):
        spell = self.begin()
        self.F.emit('CastSpellFailed', 'sword', spell, 'Target', '', 100)
        self.finish(spell)
        self.F.advance(3000)
        self.assertEqual(self.calls('PlayEffectAtPosition'), [])
        self.assertEqual(self.stage_calls(), [])

    def test_source_leaving_combat_cancels_pending_contact(self):
        self.finish(self.begin())
        self.F.advance(400)
        self.F.emit('LeftCombat', 'sword', 'combat')
        self.F.reload()
        self.F.advance(3500)
        self.assertEqual(len(self.calls('PlayEffectAtPosition')), 1)
        self.assertEqual(self.stage_calls(), [])

    def test_source_death_and_failed_cast_cancel_remaining_stages(self):
        for event in ('dead', 'failed'):
            with self.subTest(event=event):
                self.setUp()
                spell = self.begin()
                self.finish(spell)
                self.F.advance(800)
                if event == 'dead':
                    self.F.entities['sword']._dead = True
                    self.F.emit('StatusApplied', 'sword', 'DEAD', 'enemy0', 101)
                else:
                    self.F.emit('CastSpellFailed', 'sword', spell, 'Target', '', 100)
                self.F.advance(3500)
                self.assertEqual(len(self.calls('PlayEffectAtPosition')), 1)
                self.assertEqual(len(self.stage_calls()), 2)

    def test_dead_or_removed_targets_skip_future_helpers(self):
        self.finish(self.begin())
        self.F.advance(800)
        self.F.entities['enemy0']._dead = True
        self.F.entities['enemy1'] = None
        self.F.advance(2800)
        self.assertEqual(len(self.stage_calls()), 2)
        self.assertEqual(len(self.calls('PlayEffectAtPosition')), 3)

    def test_persistent_reload_preserves_remaining_delay_and_no_replay(self):
        self.finish(self.begin())
        self.F.advance(500)
        self.F.reload()
        self.F.advance(800)
        self.assertEqual(len(self.stage_calls()), 2)
        self.F.advance(1200)
        self.F.reload()
        self.F.advance(2800)
        self.assertEqual([c.at for c in self.calls('PlayEffectAtPosition')], [0, 1000, 2000])
        self.assertEqual(len(self.stage_calls()), 6)

    def test_old_timer_api_checkpoint_resumes_pending_step_without_replay(self):
        self.lua.execute('Ext.Timer.WaitForPersistent=nil;Ext.Timer.RegisterPersistentHandler=nil')
        self.finish(self.begin())
        self.F.advance(500)
        self.F.reload()
        self.F.advance(1300)
        self.assertEqual(len(self.stage_calls()), 2)
        self.assertEqual(len(self.calls('PlayEffectAtPosition')), 1)
        self.F.advance(3300)
        self.assertEqual(len(self.calls('PlayEffectAtPosition')), 3)
        self.assertEqual(len(self.stage_calls()), 6)

    def test_wanjun_area_and_lietian_target_foot_play_once(self):
        for key, expected in (('tianqing_wanjun', (10, 2, 20)), ('tianqing_lietian', (1, 0, 0))):
            with self.subTest(key=key):
                self.setUp()
                spell = self.begin(key=key, targets=('enemy0',))
                self.finish(spell)
                self.finish(spell)
                calls = self.calls('PlayEffectAtPosition')
                self.assertEqual(len(calls), 1)
                self.assertEqual(tuple(calls[0].args[i] for i in (2, 3, 4)), expected)

    def test_bafang_queries_eight_ground_points_and_uses_full_returned_xyz(self):
        self.lua.execute('Fixture.ground=function(x,y,z) return x+.25,y+2,z-.25 end')
        self.finish(self.begin(key='tianqing_bafang', targets=(), center=None))
        queries, effects = self.calls('FindValidPosition'), self.calls('PlayEffectAtPosition')
        self.assertEqual(len(queries), 8)
        self.assertEqual(len(effects), 8)
        for query, effect in zip(queries, effects):
            self.assertAlmostEqual(effect.args[2], query.args[1] + .25)
            self.assertEqual(effect.args[3], 2)
            self.assertAlmostEqual(effect.args[4], query.args[3] - .25)
            self.assertAlmostEqual(query.args[1] ** 2 + query.args[3] ** 2, 64)
            self.assertEqual(query.args[4], 1)

    def test_bafang_invalid_query_falls_back_bounded_center_plane(self):
        self.lua.execute('Fixture.ground=function(x,y,z) return x+3,y+20,z end')
        self.finish(self.begin(key='tianqing_bafang', targets=(), center=None))
        queries, effects = self.calls('FindValidPosition'), self.calls('PlayEffectAtPosition')
        self.assertEqual(len(effects), 8)
        for query, effect in zip(queries, effects):
            self.assertEqual(tuple(effect.args[i] for i in (2, 3, 4)), tuple(query.args[i] for i in (1, 2, 3)))
        self.assertEqual(len([c for c in self.calls('Print') if 'ground query failed' in c.args[1]]), 8)

    def test_tianjian_plays_only_once_at_real_explosion_position(self):
        spell = self.begin(key='tianqing_tianjian', targets=(), center=(5, 0, 6))
        self.finish(spell)
        self.assertEqual(self.calls('PlayEffectAtPosition'), [])
        # Strict native proxy denies undocumented fields such as Params.Source
        # or Target in the AttackPosition union.
        event = self.table(dict(Functor=dict(FunctorList=[dict(TypeId='CreateExplosion', SpellId='Projectile_ESC_TianjianImpact')])))
        for context_type in ('AttackPosition', 2):
            event.Params = self.F.strictProxy(self.table(dict(Type=context_type, Caster='sword',
                                                             StoryActionId=100, Position=[5, 3, 6], PropertyContext={'GROUND': True})))
            self.F.event('ExecuteFunctor', event)
            self.F.event('AfterExecuteFunctor', event)
        self.F.emit('UsingSpellOnTarget', 'sword', 'enemy0', 'Projectile_ESC_TianjianImpact', 'Projectile', '', 102)
        self.F.emit('CastedSpell', 'sword', 'Projectile_ESC_TianjianImpact', 'Projectile', '', 102)
        self.assertEqual(len(self.calls('PlayEffectAtPosition')), 1)
        effect = self.calls('PlayEffectAtPosition')[0]
        self.assertEqual(tuple(effect.args[i] for i in (2, 3, 4)), (5, 3, 6))

    def test_compile_gate_retains_legacy_damage_contract_without_new_visual(self):
        self.lua.globals().GeneratedSpec.tianqingVfx.enabled = False
        spell = self.begin()
        self.finish(spell)
        self.F.advance(2800)
        self.assertEqual(self.calls('PlayEffectAtPosition'), [])
        # In legacy data the paid main owns attack one; marker dispatches the
        # existing two helpers. Disabled new banks must never add a third helper.
        self.assertEqual(len(self.stage_calls()), 4)

    def test_native_variants_keep_attacks_but_only_first_variant_has_save(self):
        for suffix in ('', '_Off'):
            first = self.stats['Target_ESC_TiandiStage' + suffix]
            plain = self.stats['Target_ESC_TiandiStage_NoControl' + suffix]
            self.assertEqual(first['SpellRoll'], plain['SpellRoll'])
            self.assertEqual(first['UseCosts'], plain['UseCosts'])
            self.assertEqual(re.findall(r'DealDamage\([^;]+', first['SpellSuccess']),
                             re.findall(r'DealDamage\([^;]+', plain['SpellSuccess']))
            self.assertIn('ExecuteWeaponFunctors(', plain['SpellSuccess'])
            self.assertIn('ApplyStatus(ESC_HIT_MARKER', plain['SpellSuccess'])
            self.assertIn('SavingThrow(Ability.Strength', first['SpellSuccess'])
            self.assertNotIn('SavingThrow(', plain['SpellSuccess'])
            self.assertNotIn('ESC_TIANDI_FIRSTHIT', first['SpellSuccess'])

    def test_overlapping_tokens_do_not_share_attempts_or_target_ledgers(self):
        self.finish(self.begin(targets=('enemy0', 'enemy1'), action=100), action=100)
        self.F.advance(1100)
        self.finish(self.begin(targets=('enemy0',), action=101), action=101)
        self.F.advance(3900)
        saves = self.calls('NativeStrengthSave')
        self.assertEqual(len(saves), 3)  # A: two targets; B: shared target gets its own first save.
        self.assertEqual([c.at for c in saves], [800, 800, 1900])
        self.assertEqual(len(self.stage_calls()), 9)
        self.assertEqual(len(self.calls('PlayEffectAtPosition')), 6)

    def test_miss_then_hit_attempts_save_once_even_when_save_succeeds(self):
        self.F.outcomes = self.table([dict(hit=False), dict(hit=True, saveSucceeds=True), dict(hit=True)])
        self.finish(self.begin(targets=('enemy0',)))
        self.F.advance(2800)
        self.assertEqual([c.args[2] for c in self.stage_calls()],
                         ['Target_ESC_TiandiStage', 'Target_ESC_TiandiStage', 'Target_ESC_TiandiStage_NoControl'])
        self.assertEqual([c.at for c in self.calls('NativeStrengthSave')], [1800])

    def test_adjacent_finish_before_hit_does_not_retry_successful_save(self):
        self.F.finishBeforeHit = True
        self.finish(self.begin(targets=('enemy0',)))
        self.F.advance(2800)
        self.assertEqual(len(self.calls('NativeStrengthSave')), 1)
        self.assertEqual([c.args[2] for c in self.stage_calls()],
                         ['Target_ESC_TiandiStage', 'Target_ESC_TiandiStage_NoControl', 'Target_ESC_TiandiStage_NoControl'])

    def test_pending_last_stage_queue_survives_reload_and_different_finish_order(self):
        self.F.deferNative = True
        self.finish(self.begin(targets=('enemy0', 'enemy1')))
        self.F.advance(2800)
        self.assertEqual(len(self.stage_calls()), 2)
        self.assertEqual(len(self.calls('PlayEffectAtPosition')), 3)
        state = self.F.entities['sword'].Vars.ESC_State
        entry = state.tianqingStages['100']
        self.assertIsNotNone(entry)
        self.assertEqual(entry.resolved, 3)
        self.assertEqual(len(entry.targetLedger['enemy0'].queue), 2)
        self.F.reload()
        # Different targets may finish in a different order. Each queues two
        # remaining native attacks behind its own first hit, with no new save.
        self.F.completeNative(self.F.nativeCasts[2])
        self.F.advance(2801)
        self.F.completeNative(self.F.nativeCasts[1])
        self.F.advance(2802)
        self.F.reload()
        self.F.completeNative(self.F.nativeCasts[4])
        self.F.advance(2803)
        self.F.completeNative(self.F.nativeCasts[3])
        self.F.advance(2804)
        self.F.completeNative(self.F.nativeCasts[5])
        self.F.completeNative(self.F.nativeCasts[6])
        self.F.advance(2805)
        self.assertEqual(len(self.stage_calls()), 6)
        self.assertEqual(len(self.calls('NativeStrengthSave')), 2)
        self.assertEqual(len(self.calls('PlayEffectAtPosition')), 3)
        self.assertIsNone(state.tianqingStages['100'])

    def test_failed_async_helper_allows_next_first_hit_attempt_without_extra_attack(self):
        self.F.deferNative = True
        self.F.outcomes = self.table([dict(failed=True), dict(hit=True, saveSucceeds=True), dict(hit=True)])
        self.finish(self.begin(targets=('enemy0',)))
        self.F.advance(2800)
        self.F.completeNative(self.F.nativeCasts[1])
        self.assertEqual(len(self.stage_calls()), 2)
        self.F.completeNative(self.F.nativeCasts[2])
        self.F.advance(2801)
        self.F.completeNative(self.F.nativeCasts[3])
        self.F.advance(2802)
        self.assertEqual(len(self.stage_calls()), 3)
        self.assertEqual(len(self.calls('NativeStrengthSave')), 1)

    def test_save_between_finish_callback_and_queue_release_keeps_success_attempt(self):
        self.F.deferNative = True
        self.finish(self.begin(targets=('enemy0',)))
        self.F.advance(1800)
        self.F.completeNative(self.F.nativeCasts[1])
        self.F.reload()  # Ordinary 1ms completion closure was lost.
        self.F.advance(1801)
        self.assertEqual(len(self.stage_calls()), 2)
        self.assertEqual(self.stage_calls()[1].args[2], 'Target_ESC_TiandiStage_NoControl')
        self.F.completeNative(self.F.nativeCasts[2])
        self.F.advance(2800)
        self.F.completeNative(self.F.nativeCasts[3])
        self.F.advance(2801)
        self.assertEqual(len(self.calls('NativeStrengthSave')), 1)


if __name__ == '__main__':
    unittest.main()
