"""Production Runtime/Engine + native callback order regression simulation.

The callback order comes from native action 117-121 captures. This is not
render, audio, native damage or Toolkit acceptance.
"""
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p / 'scripts/tests/test_taixuan_world_rain.py').is_file())
sys.path.insert(0, str(REPO / 'scripts/tests'))
import test_taixuan_world_rain as world

HOST = 'sword'
NAMED_HOST = 'Elves_Female_High_Player_sword'
ENEMY = 'enemy'
NAMED_ENEMY = 'Goblins_Male_Guard_enemy'

NATIVE_ORDER = r'''
local F=Fixture
F.entityAliases={Elves_Female_High_Player_sword='sword',Goblins_Male_Guard_enemy='enemy'}
local originalGet=Ext.Entity.Get
function Ext.Entity.Get(ref)
    return originalGet(type(ref)=='string' and F.entityAliases[ref] or ref)
end
for name,original in pairs(Osi) do
    if type(original)=='function' then
        Osi[name]=function(...)
            local args={...}
            for i=1,select('#',...) do args[i]=F.entityAliases[args[i]] or args[i] end
            return original(table.unpack(args,1,select('#',...)))
        end
    end
end
function Osi.UseSpell(source,spell,target,originator,withoutMove)
    assert((F.stats[spell].UseCosts or '')=='','Actual helper definition must be free')
    F.calls[#F.calls+1]={name='UseSpell',args={source,spell,target,originator,withoutMove},at=F.now}
    F.nextAction=F.nextAction+1;local action=F.nextAction
    local ownerUuid=ESC.Engine.uuid(ESC.Engine.entity(source))
    local targetUuid=ESC.Engine.uuid(ESC.Engine.entity(target))
    local eventOwner=ownerUuid=='sword' and 'Elves_Female_High_Player_sword' or ownerUuid
    local eventTarget=targetUuid=='enemy' and 'Goblins_Male_Guard_enemy' or targetUuid
    local packet={source=eventOwner,spell=spell,target=eventTarget,action=action}
    F.nativeCasts[#F.nativeCasts+1]=packet
    local outcome=table.remove(F.outcomes,1) or {}
    packet.outcome=outcome
    -- Native 117-119: both native damage functors precede CastedSpell.
    -- Native 120-121: no damage, but CastedSpell still precedes UsingSpell.
    local function nativeDamage()
      if outcome.hit~=false and not outcome.failed then
        for _,amount in ipairs({13,9}) do
            local hit={DamageList={{Amount=amount,DamageType='Force'}},TotalDamageDone=amount,SpellId=spell}
            local evt={Caster=ownerUuid,Target=targetUuid,StoryActionId=action,Hit=hit}
            F.event('DealDamage',evt);F.event('BeforeDealDamage',{Hit=hit})
            F.entities[targetUuid]._hp=math.max(0,F.entities[targetUuid]._hp-hit.TotalDamageDone)
            evt.Result={Hit=hit};F.event('DealtDamage',evt)
        end
      end
    end
    if not F.finishBeforeDamage then nativeDamage() end
    if outcome.failed then F.emit('CastSpellFailed',eventOwner,spell,'Target','',action)
    else F.emit('CastedSpell',eventOwner,spell,'Target','',action) end
    if F.finishBeforeDamage then nativeDamage() end
    if outcome.killOwner then
        F.entities[ownerUuid]._dead=true;F.emit('StatusApplied',eventOwner,'DEAD',eventOwner,action)
    elseif outcome.leftCombat then F.emit('LeftCombat',eventOwner,'fixture-combat')
    elseif outcome.lateFailed then F.emit('CastSpellFailed',eventOwner,spell,'Target','',action) end
    if outcome.removeTarget then F.entities[targetUuid]=nil end
    F.emit('UsingSpell',eventOwner,spell,'Target','',action)
    F.emit('UsingSpellOnTarget',eventOwner,eventTarget,spell,'Target','',action)
    if outcome.duplicate then
        F.emit('UsingSpellOnTarget',ownerUuid,targetUuid,spell,'Target','',action)
        F.emit('CastedSpell',ownerUuid,spell,'Target','',action)
    end
end
'''


def fixture():
    # Uses the current production Runtime/Engine/Rain via the shared fixture.
    # Native casts, geometry and resource engine behavior remain simulated.
    lua, f, rain = world.fixture()
    lua.execute(NATIVE_ORDER)
    f.entities['enemy']._hp = 1000
    f.entities['enemy']._maxHp = 1000
    return lua, f, rain


class NativeEventOrder(unittest.TestCase):
    def run_domain(self, outcomes=None):
        lua, f, rain = fixture()
        if outcomes:
            f.outcomes = lua.table_from(outcomes, recursive=True)
        world.open_domain(lua, f)
        return lua, f, rain

    def test_real_order_late_target_restores_three_distinct_focus_swords(self):
        _, f, _ = self.run_domain()
        points = [world.pos(c) for c in world.calls(f, 'PlayEffectAtPosition')]
        self.assertEqual(len(points), 3)
        self.assertEqual(len(set(points)), 3)
        self.assertEqual(set(points), {(1.6, 0, -.23), (2.4, 0, -.23), (2, 0, .46)})

    def test_three_native_requests_keep_damage_cost_and_no_manual_damage_contract(self):
        _, f, _ = self.run_domain()
        # Each 13+9 native attack receives additive domain20 + regular15:
        # floor(22 * 1.35)=29, three actual helper attacks total 87.
        self.assertEqual(f.entities['enemy']._hp, 913)
        self.assertEqual(len(world.calls(f, 'UseSpell')), 3)
        self.assertEqual(f.stats['Target_ESC_TaiqingPulse']['UseCosts'], '')
        self.assertEqual(f.entities['sword'].ActionResources.Resources[world.SPEC['resource']][1].Amount, 0)
        self.assertEqual(len(world.calls(f, 'ApplyDamage')), 0)

    def test_miss_attempt_has_sword_failed_attempt_has_none(self):
        _, f, _ = self.run_domain(outcomes=[{'hit': False}, {'failed': True}, {'hit': True}])
        effects = world.calls(f, 'PlayEffectAtPosition')
        self.assertEqual(len(effects), 2)
        self.assertEqual(set(world.pos(c) for c in effects), {(1.6, 0, -.23), (2, 0, .46)})

    def test_uuid_alias_duplicate_events_do_not_reset_or_replay_finished_cast(self):
        _, f, _ = self.run_domain(outcomes=[{'duplicate': True} for _ in range(3)])
        self.assertEqual(len(world.calls(f, 'PlayEffectAtPosition')), 3)
        self.assertEqual(len(world.calls(f, 'UseSpell')), 3)

    def test_late_actual_damage_target_keeps_three_focus_offsets_before_using_target(self):
        lua, f, _ = fixture()
        f.finishBeforeDamage = True
        world.open_domain(lua, f)
        points = [world.pos(c) for c in world.calls(f, 'PlayEffectAtPosition')]
        self.assertEqual(len(points), 3)
        self.assertEqual(set(points), {(1.6, 0, -.23), (2.4, 0, -.23), (2, 0, .46)})
        self.assertEqual(f.entities['enemy']._hp, 913)

    def test_late_failure_cancels_target_arrival(self):
        _, f, _ = self.run_domain(outcomes=[{'lateFailed': True} for _ in range(3)])
        self.assertEqual(len(world.calls(f, 'PlayEffectAtPosition')), 0)

    def test_owner_death_before_actual_target_arrival_cancels_world_only(self):
        _, f, _ = self.run_domain(outcomes=[{'killOwner': True} for _ in range(3)])
        self.assertEqual(len(world.calls(f, 'PlayEffectAtPosition')), 0)
        self.assertEqual(len(world.calls(f, 'UseSpell')), 3)

    def test_other_owner_preserves_its_own_focus_and_offsets(self):
        lua, f, _ = fixture()
        world.open_domain(lua, f)
        world.open_domain(lua, f, 'other', 'otherEnemy', 200)
        effects = world.calls(f, 'PlayEffectAtPosition')
        self.assertEqual(len(effects), 6)
        self.assertEqual(len({world.pos(c) for c in effects}), 6)
        self.assertEqual(len([c for c in effects if c.args[2] > 90]), 3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
