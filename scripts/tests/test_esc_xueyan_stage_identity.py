"""Real Runtime/Engine stage settlement with captured native identity shapes.

Deterministic simulation; native H18 provided Name_GUID/UUID event evidence,
but the repaired Runtime still requires installed-client acceptance.
"""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts/tests'))
import test_esc_bridge as bridge

SOURCE = 'aa182d6a-22b9-5412-23ed-daa9d98b30bd'
NAMED_SOURCE = 'Elves_Female_High_Player_' + SOURCE
TARGET = '6fc3605a-a251-6170-f3b8-f276637ba1a6'
NAMED_TARGET = 'Goblins_Male_Guard_' + TARGET
OTHER = 'd764e091-3386-cd8e-70c5-7a3e067848d9'
NAMED_OTHER = 'Goblins_Male_Guard_' + OTHER
SPELL = 'Projectile_ESC_xueyan_luexue'


class XueyanStageIdentity(unittest.TestCase):
    def setUp(self):
        runtime = Path(os.environ.get('ESC_XUEYAN_RUNTIME_CANDIDATE', bridge.LUA / 'Runtime.lua'))
        snapshot = dict(bridge.SNAPSHOT)
        snapshot['Runtime.lua'] = runtime.read_bytes()
        with patch.object(bridge, 'SNAPSHOT', snapshot):
            bridge.Bridge.setUp(self)
        bridge.Bridge.actor(self, SOURCE, 12, 'xueyan', 162, 180, 'players')
        bridge.Bridge.actor(self, TARGET, 0, None, 10009, 10009, 'enemies', 2)
        bridge.Bridge.actor(self, OTHER, 0, None, 10009, 10009, 'enemies', 3)
        self.ESC.State(SOURCE).frenzy = 4
        self.F.resource(SOURCE).Amount = 0
        self.F.entityAliases = self.lua.table_from({
            NAMED_SOURCE: SOURCE, NAMED_TARGET: TARGET, NAMED_OTHER: OTHER})
        # Native Entity.Get and Osiris accept both identities. No Runtime
        # function, comparator, damage accounting or reward is mocked.
        self.lua.execute('''
            local originalGet=Ext.Entity.Get
            function Ext.Entity.Get(ref)
                return originalGet(Fixture.entityAliases[ref] or ref)
            end
            for name,fn in pairs(Osi) do
                local original=fn
                Osi[name]=function(...)
                    local args=table.pack(...)
                    for i=1,args.n do
                        if type(args[i])=='string' then args[i]=Fixture.entityAliases[args[i]] or args[i] end
                    end
                    return original(table.unpack(args,1,args.n))
                end
            end
        ''')

    def table(self, value):
        return bridge.Bridge.table(self, value)

    def begin(self, action=68, source=NAMED_SOURCE, target=NAMED_TARGET):
        self.F.emit('UsingSpell', source, SPELL, 'Projectile', '', action)
        self.F.emit('UsingSpellOnTarget', source, target, SPELL, 'Projectile', '', action)

    def damage(self, amounts=(10, 15), action=68, target=TARGET, spell=SPELL, status=None):
        emitted = []
        for index, amount in enumerate(amounts):
            # Captured native DealDamage/DealtDamage Hit lists are empty; the
            # populated BeforeDealDamage packet is a separate native structure.
            blank = self.table(dict(DamageList=[], TotalDamageDone=0, SpellId=spell, StatusId=status))
            event = self.table(dict(Caster=SOURCE, Target=target, StoryActionId=action,
                                   SpellId=spell, Hit=blank))
            self.F.event('DealDamage', event)
            hit = self.table(dict(DamageList=[dict(Amount=amount, DamageType='Slashing' if index == 0 else 'Necrotic')],
                                  TotalDamageDone=amount))
            self.F.event('BeforeDealDamage', self.table(dict(Hit=hit)))
            victim = self.F.entities[target]
            victim._hp = max(0, victim._hp - hit.TotalDamageDone)
            event.Result = self.table(dict(Hit=dict(DamageList=[], TotalDamageDone=0)))
            self.F.event('DealtDamage', event)
            emitted.append(hit.TotalDamageDone)
        return emitted

    def marker(self, action=68, source=SOURCE, target=NAMED_TARGET):
        self.F.emit('StatusApplied', target, 'ESC_HIT_MARKER', source, action)

    def finish(self, action=68, source=NAMED_SOURCE):
        self.F.emit('CastedSpell', source, SPELL, 'Projectile', '', action)

    def reward(self):
        return self.E.hp(SOURCE), self.ESC.State(SOURCE).shield, self.F.resource(SOURCE).Amount

    def test_captured_mixed_marker_settles_empty_result_packets(self):
        self.begin()
        self.assertEqual(self.damage(), [12, 18])
        self.assertEqual(self.reward(), (162, 0, 0))
        self.marker()
        self.assertEqual(self.reward(), (170, 3, 2))

    def test_named_cast_finish_settles_canonical_damage_without_marker(self):
        self.begin()
        self.damage()
        self.finish()
        self.assertEqual(self.reward(), (170, 3, 2))

    def test_named_source_and_bare_target_marker_use_same_stage(self):
        self.begin(source=SOURCE, target=TARGET)
        self.damage()
        self.marker(source=NAMED_SOURCE, target=TARGET)
        self.assertEqual(self.reward(), (170, 3, 2))

    def test_marker_and_finish_aliases_cannot_reward_twice(self):
        self.begin()
        self.damage()
        self.marker()
        self.assertEqual(self.reward(), (170, 3, 2))
        self.marker(source=NAMED_SOURCE, target=TARGET)
        self.finish()
        self.ESC.Runtime.FlushStage(SOURCE, 68, TARGET)
        self.assertEqual(self.reward(), (170, 3, 2))

    def test_separate_actions_keep_separate_settlements(self):
        for action in (68, 69):
            self.begin(action)
            self.damage(action=action)
        self.marker(68)
        self.assertEqual(self.reward(), (170, 3, 2))
        self.marker(69)
        self.assertEqual(self.reward(), (178, 6, 4))

    def test_separate_targets_keep_separate_settlements(self):
        self.begin()
        self.damage()
        self.damage(target=OTHER)
        self.marker()
        self.assertEqual(self.reward(), (170, 3, 2))
        self.marker(target=NAMED_OTHER)
        self.assertEqual(self.reward(), (178, 6, 4))

    def test_nonhostile_target_never_grants_siphon(self):
        self.F.entities[TARGET]._party = 'players'
        self.begin()
        self.damage()
        self.marker()
        self.finish()
        self.assertEqual(self.reward(), (162, 0, 0))

    def test_status_damage_never_grants_siphon(self):
        self.begin()
        self.damage(status='BURNING')
        self.marker()
        self.finish()
        self.assertEqual(self.reward(), (162, 0, 0))

    def test_bare_identity_behavior_is_preserved(self):
        self.begin(source=SOURCE, target=TARGET)
        self.damage()
        self.marker(source=SOURCE, target=TARGET)
        self.finish(source=SOURCE)
        self.assertEqual(self.reward(), (170, 3, 2))


if __name__ == '__main__':
    unittest.main(verbosity=2)
