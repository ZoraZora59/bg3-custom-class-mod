"""Behavior and operation-count regressions for long-running server sessions.

Uses the existing deterministic engine boundary, without game, save, package or
asset writes. Counts engine calls rather than timing a simulated Lua runtime;
these checks do not establish client frame-time or native VFX acceptance.
"""
import unittest

import test_esc_bridge as bridge

SPEC = bridge.SPEC


class RuntimePerformance(unittest.TestCase):
    def setUp(self):
        self.h = bridge.Bridge()
        self.h.setUp()
        self.lua, self.F = self.h.lua, self.h.F
        self.E, self.runtime = self.h.E, self.h.ESC.Runtime
        # Consume timers as a game event loop would. Keeping executed closures in
        # Fixture.timers would itself retain casts and invalidate the GC check.
        self.lua.execute('''
            Fixture.now=0;Fixture.timerSerial=0;Fixture.timers={}
            function Ext.Timer.WaitFor(ms,callback)
                Fixture.timerSerial=Fixture.timerSerial+1
                local id=Fixture.timerSerial
                Fixture.timers[id]={due=Fixture.now+ms,ms=ms,callback=callback}
                return id
            end
            function Ext.Timer.Cancel(id) Fixture.timers[id]=nil end
            function Fixture.advance(ms)
                local deadline=Fixture.now+ms
                while true do
                    local nextId,nextTime
                    for id,timer in pairs(Fixture.timers) do
                        if timer.due<=deadline and (not nextTime or timer.due<nextTime
                            or timer.due==nextTime and id<nextId) then
                            nextId,nextTime=id,timer.due
                        end
                    end
                    if not nextId then break end
                    local timer=Fixture.timers[nextId];Fixture.timers[nextId]=nil
                    Fixture.now=nextTime;timer.callback();Fixture.runNextTick()
                end
                Fixture.now=deadline
            end
            Fixture.reads={};Fixture.scans={}
            local get,scan=Ext.Entity.Get,Ext.Entity.GetAllEntitiesWithComponent
            function Ext.Entity.Get(id)
                if type(id)=='string' then Fixture.reads[id]=(Fixture.reads[id] or 0)+1 end
                return get(id)
            end
            function Ext.Entity.GetAllEntitiesWithComponent(component)
                Fixture.scans[component]=(Fixture.scans[component] or 0)+1
                return scan(component)
            end
            function Fixture.resetMetrics() Fixture.reads={};Fixture.scans={} end
            function Fixture.readCount(prefix)
                local count=0
                for id,n in pairs(Fixture.reads) do
                    if id:sub(1,#prefix)==prefix then count=count+n end
                end
                return count
            end
            Fixture.castReferences=setmetatable({}, {__mode='v'})
            function Fixture.liveCastReferences()
                collectgarbage('collect');collectgarbage('collect')
                local count=0;for _ in pairs(Fixture.castReferences) do count=count+1 end
                return count
            end
        ''')

    def load(self):
        self.F.event('SessionLoaded', self.h.table({}))

    def test_ordinary_turns_do_not_create_persistent_state_or_idle_work(self):
        self.h.actor()
        actors = [self.h.actor('ordinary-' + str(i), 0, None, party='enemies')
                  for i in range(100)]
        item = self.h.actor('ordinary-item', 0, None, party='neutral')
        item._isItem = True
        actors.append(item)
        for i in range(100):
            self.F.emit('TurnStarted', 'ordinary-' + str(i))
        self.F.emit('TurnStarted', 'ordinary-item')
        self.assertTrue(all(actor.Vars.ESC_State is None for actor in actors))
        self.F.resetMetrics()
        for _ in range(5):
            self.runtime.UpdateAuras()
        self.assertEqual(self.F.readCount('ordinary-'), 0)

    def test_unrelated_damage_keeps_native_damage_without_persistent_state(self):
        attacker = self.h.actor('ordinary-attacker', 0, None, party='enemies')
        victim = self.h.actor('ordinary-victim', 0, None, hp=1000,
                              maximum=1000, party='neutral')
        item = self.h.actor('ordinary-object', 0, None, hp=1000,
                            maximum=1000, party='neutral')
        item._isItem = True
        for i in range(100):
            target = 'ordinary-victim' if i % 2 else 'ordinary-object'
            hit = self.h.native_damage('ordinary-attacker', target, [1, 2],
                                       spell='Projectile_FireBolt', action=500 + i)
            self.assertEqual(hit.TotalDamageDone, 3)
        self.assertEqual((victim._hp, item._hp), (850, 850))
        self.assertTrue(all(actor.Vars.ESC_State is None
                            for actor in (attacker, victim, item)))
        self.F.resetMetrics()
        for _ in range(5):
            self.runtime.UpdateAuras()
        self.assertEqual(self.F.readCount('ordinary-'), 0)

    def test_idle_blood_character_has_zero_health_population_scans(self):
        self.h.actor()
        self.lua.execute('''
            for i=1,1000 do Fixture.actor('crowd-'..i,0,nil,100,100,'enemies',20+i) end
        ''')
        self.load()  # One-time saved beneficiary discovery is allowed.
        self.F.resetMetrics()
        self.F.advance(2000)
        self.assertEqual(self.F.scans.Health or 0, 0)
        self.assertEqual(self.F.readCount('crowd-'), 0)

    def test_saved_pollution_is_removed_but_nonclass_native_boost_is_restored(self):
        self.h.actor()
        self.lua.execute('''
            for i=1,100 do
                local actor=Fixture.actor('polluted-'..i,0,nil,100,100,'enemies',20+i)
                actor.Vars.ESC_State={turn=9,frenzy=0,shield=0,qiSword=false,
                    marks={},protections={},domains={},debuffs={},kills={},chains={},
                    boosts={aura='',chengfeng='',control_save_1=''}}
            end
            local ally=Fixture.actor('saved-beneficiary',0,nil,100,100,'players',20)
            ally.Vars.ESC_State={turn=2,boosts={fixture_saved='AC(1)'}}
        ''')
        self.load()
        self.assertTrue(all(self.F.entities['polluted-' + str(i)].Vars.ESC_State is None
                            for i in range(1, 101)))
        beneficiary = self.F.entities['saved-beneficiary']
        self.assertEqual(beneficiary.Vars.ESC_State.turn, 2)
        self.assertEqual(beneficiary._boosts.ESC_fixture_saved, 'AC(1)')
        self.F.resetMetrics()
        self.F.advance(1000)
        self.assertEqual(self.F.readCount('polluted-'), 0)
        self.assertEqual(beneficiary._boosts.ESC_fixture_saved, 'AC(1)')

    def test_saved_nonclass_records_work_until_owner_expiry_then_retire(self):
        self.h.actor()
        owner = self.h.ESC.State('sword')
        owner.turn = 7
        self.lua.execute('''
            local actor=Fixture.actor('saved-recipient',0,nil,100,100,'players',20)
            actor.Vars.ESC_State={turn=2,boosts={},
                marks={['weakpoint:sword']={expires=10,used={}}},
                protections={['chengfeng:sword']={owner='sword',kind='chengfeng',
                    movementExpires=8,expires=9,reduction=0}},
                debuffs={['sword:tianqing_lietian']={owner='sword',expires=9,ac=-3,attack=-2}}}
        ''')
        self.load()
        recipient = self.F.entities['saved-recipient']
        self.assertEqual(recipient.Vars.ESC_State.turn, 2)
        self.assertIsNotNone(recipient.Vars.ESC_State.marks['weakpoint:sword'])
        self.assertEqual(recipient._boosts.ESC_chengfeng_oa, 'IgnoreLeaveAttackRange()')
        self.assertEqual(recipient._boosts.ESC_chengfeng_movement, 'ActionResource(Movement,6,0)')
        self.assertIn('AC(-3)', recipient._boosts.ESC_aura)
        owner.turn = 8
        self.runtime.UpdateAuras()
        self.assertEqual(recipient._boosts.ESC_chengfeng_oa, 'IgnoreLeaveAttackRange()')
        self.assertIsNone(recipient._boosts.ESC_chengfeng_movement)
        owner.turn = 10
        self.runtime.UpdateAuras()
        self.runtime.UpdateAuras()  # Flush dependent native slot cleanup.
        self.assertIsNone(recipient.Vars.ESC_State)
        self.F.resetMetrics()
        self.F.advance(1000)
        self.assertEqual(self.F.readCount('saved-recipient'), 0)

    def test_actual_protection_and_debuff_still_affect_nonclass_characters(self):
        self.h.actor(branch='xingge')
        self.h.actor('protected', 0, None, party='players', x=10)
        self.h.actor('debuffed', 0, None, party='enemies', x=2)
        self.h.cast('sword', 'xingge_huifeng', 'protected', action=701)
        self.assertEqual(self.runtime.Defense('protected', 100, False, True)[0], 80)
        spell = SPEC['spells']['xingge_huifeng']['stat']
        self.runtime.BeginCast('sword', spell, 702, 'debuffed')
        self.F.emit('StatusApplied', 'debuffed', 'ESC_SAVEFAIL_XINGGE_HUIFENG', 'sword', 702)
        self.assertIn('RollBonus(Attack,-2)', self.F.entities.debuffed._boosts.ESC_aura)
        self.assertIn('ActionResourceMultiplier(Movement,50,0)', self.F.entities.debuffed._boosts.ESC_aura)
        self.F.protectionTurnStarted('sword')
        self.F.protectionTurnStarted('sword')
        self.assertEqual(self.runtime.Defense('protected', 100, False, True)[0], 100)
        self.assertIsNone(self.F.entities.debuffed._boosts.ESC_aura)

    def test_historical_kills_migrate_once_without_periodic_entity_reads(self):
        self.h.actor()
        self.h.ESC.State('sword')
        self.lua.execute('''
            for i=1,1000 do
                local id='historic-kill-'..i
                local actor=Fixture.actor(id,0,nil,0,100,'enemies',20+i);actor._dead=true
                Fixture.entities.sword.Vars.ESC_State.kills[id]=true
            end
        ''')
        self.load()
        self.F.resetMetrics()
        self.F.advance(2000)
        self.assertEqual(self.F.readCount('historic-kill-'), 0)
        # A migrated receipt still blocks a delayed duplicate from the old life.
        spell = SPEC['spells']['xueyan_luexue']['stat']
        self.runtime.BeginCast('sword', spell, 900, 'historic-kill-1000')
        before = (self.F.entities.sword._hp, self.F.resource('sword').Amount)
        self.F.emit('KilledBy', 'historic-kill-1000', 'sword', 'sword', 900)
        self.assertEqual((self.F.entities.sword._hp, self.F.resource('sword').Amount), before)

    def test_duplicate_kill_is_blocked_but_resurrection_allows_new_life_reward(self):
        self.h.actor()
        enemy = self.h.actor('enemy', 0, None, hp=0, party='enemies')
        enemy._dead = True
        spell = SPEC['spells']['xueyan_luexue']['stat']
        self.runtime.BeginCast('sword', spell, 901, 'enemy')
        self.F.emit('KilledBy', 'enemy', 'sword', 'sword', 901)
        self.F.emit('KilledBy', 'enemy', 'sword', 'sword', 901)
        self.assertEqual((self.F.entities.sword._hp, self.F.resource('sword').Amount), (40, 4))
        enemy._dead, enemy._hp = False, 100
        self.F.emit('Resurrected', 'enemy')
        enemy._dead, enemy._hp = True, 0
        self.runtime.BeginCast('sword', spell, 902, 'enemy')
        self.F.emit('KilledBy', 'enemy', 'sword', 'sword', 902)
        self.F.emit('KilledBy', 'enemy', 'sword', 'sword', 902)
        self.assertEqual((self.F.entities.sword._hp, self.F.resource('sword').Amount), (50, 8))

    def test_failed_cast_load_retires_contexts_and_recent_late_callbacks_are_inert(self):
        self.h.actor()
        self.h.actor('ordinary-caster', 0, None, party='enemies')
        self.lua.execute('''
            for action=10000,10999 do
                Fixture.castReferences[action]=ESC.Runtime.BeginCast(
                    'ordinary-caster','Shout_Thunderwave',action,'ordinary-caster')
                Fixture.emit('CastSpellFailed','ordinary-caster','Shout_Thunderwave','Shout','',action)
            end
        ''')
        domain = SPEC['spells']['xueyan_xuehai']['stat']
        cast = self.runtime.BeginCast('sword', domain, 11000, 'sword')
        self.F.castReferences[11000] = cast
        self.F.emit('CastSpellFailed', 'sword', domain, 'Shout', '', 11000)
        del cast
        self.F.runNextTick()
        self.F.advance(30001)
        self.assertEqual(self.F.liveCastReferences(), 0)
        self.F.clearCalls()
        self.F.emit('CastedSpell', 'sword', domain, 'Shout', '', 11000)
        self.F.emit('StatusApplied', 'sword', 'ESC_HIT_MARKER', 'sword', 11000)
        self.assertIsNone(self.F.entities.sword.Vars.ESC_State.domains.xueyan_xuehai)
        self.assertEqual(self.F.callCount('UseSpell'), 0)
        self.h.cast('sword', 'xueyan_xuehai', action=11001)
        self.assertIsNotNone(self.F.entities.sword.Vars.ESC_State.domains.xueyan_xuehai)

    def test_finished_cast_contexts_retire_without_rejecting_valid_delayed_damage(self):
        self.h.actor('ordinary-caster', 0, None, party='enemies')
        self.lua.execute('''
            for action=20000,20999 do
                Fixture.castReferences[action]=ESC.Runtime.BeginCast(
                    'ordinary-caster','Shout_Thunderwave',action,'ordinary-caster')
                Fixture.emit('CastedSpell','ordinary-caster','Shout_Thunderwave','Shout','',action)
            end
        ''')
        self.F.advance(30001)
        self.assertEqual(self.F.liveCastReferences(), 0)
        self.h.actor()
        self.h.actor('enemy', 0, None, hp=200, maximum=200, party='enemies')
        spell = SPEC['spells']['xueyan_luexue']['stat']
        cast = self.runtime.BeginCast('sword', spell, 22000, 'enemy')
        self.F.castReferences[22000] = cast
        self.F.emit('CastedSpell', 'sword', spell, 'Projectile', '', 22000)
        del cast
        self.F.advance(29999)
        hit = self.h.native_damage('sword', 'enemy', [10], spell=spell, action=22000)
        self.F.emit('StatusApplied', 'enemy', 'ESC_HIT_MARKER', 'sword', 22000)
        self.assertEqual(hit.TotalDamageDone, 10)
        self.assertGreater(self.F.resource('sword').Amount, 0)
        self.F.advance(2)
        self.assertEqual(self.F.liveCastReferences(), 0)


if __name__ == '__main__':
    unittest.main()
