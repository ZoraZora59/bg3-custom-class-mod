"""Replay production event handlers in the order observed for ImmediateCast helpers.

The B6F observation has no preceding UsingSpell for helper actions64-66. Two
DealDamage/BeforeDealDamage/DealtDamage packets happen before completion. This
fixture replay does not imply new native client verification.

Run: python -m unittest discover -s scripts/tests -p 'test_esc_helper_parent_attribution.py' -v
The normal test-sword-cultivator.py runner discovers this file automatically.
Tests load the current production Lua snapshot, never an isolated candidate.
"""
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'scripts/tests/test_esc_bridge.py').is_file())
sys.path.insert(0, str(ROOT / 'scripts/tests'))
import test_esc_bridge as bridge


class HelperParentAttribution(unittest.TestCase):
    table = bridge.Bridge.table
    actor = bridge.Bridge.actor
    cast = bridge.Bridge.cast
    native_damage = bridge.Bridge.native_damage

    def setUp(self):
        bridge.Bridge.setUp(self)
        self.actor(branch='taixuan', level=12, hp=112, maximum=112)
        self.actor('enemy', level=0, branch=None, hp=10009, maximum=10009, party='enemies', x=2)
        self.F.resource('sword').Amount = 50
        self.contexts, self.pending_helpers = self.lua.execute('''
            local function upvalue(fn,wanted)
                for i=1,100 do
                    local name,value=debug.getupvalue(fn,i)
                    if not name then break end
                    if name==wanted then return value end
                end
                error('Missing production upvalue '..wanted)
            end
            return upvalue(ESC.Runtime.BeginCast,'casts'),
                upvalue(upvalue(ESC.Runtime.BeginCast,'bindPendingHelper'),'pendingHelpers')
        ''')

    def packet_sequence(self, spell, action, parts):
        return [self.native_damage('sword', 'enemy', [amount], spell=spell, action=action).TotalDamageDone
                for amount in parts]

    def finish(self, spell, action):
        self.F.emit('StatusApplied', 'enemy', 'ESC_HIT_MARKER', 'sword', action)
        self.F.emit('CastedSpell', 'sword', spell, 'Target', '', action)

    def domain(self):
        self.cast('sword', 'taixuan_taiqing', action=501)

    def test_b6f_three_helpers_damage_before_completion_without_using_spell(self):
        root = 'Projectile_ESC_taixuan_liuguang'
        helper = 'Target_ESC_LiuguangStage'
        self.F.emit('UsingSpellOnTarget', 'sword', 'enemy', root, 'Projectile', '', 63)
        self.assertEqual(self.packet_sequence(root, 63, [12, 19]), [13, 22])
        # The fixture boundary sets the native paid-root state observed in B6F.
        self.E.resourceEntry('sword', '734cbcfb-8922-4b6d-8330-b2a7e4c14b6a').Amount = 0
        pool = self.E.resourceEntry('sword', bridge.SPEC['opportunityResource'])
        pool.Amount = 3
        self.F.resource('sword').Amount = 40
        self.E.status('sword', 'ESC_EXTRA_ATTACK', 1, 'sword')
        self.finish(root, 63)
        calls = [c for c in self.F.calls.values() if c.name == 'UseSpell' and c.args[2] == helper]
        self.assertEqual(len(calls), 3)
        for action, parts, expected in [(64, [12, 14], [13, 16]),
                                        (65, [7, 19], [8, 21]), (66, [13, 10], [14, 12])]:
            # Deliberately no UsingSpell or UsingSpellOnTarget for these helpers.
            self.assertIsNone(self.contexts[action])
            pending = len(self.pending_helpers['sword'])
            self.assertEqual(self.packet_sequence(helper, action, parts), expected)
            self.assertIsNone(self.contexts[action], 'Parent lookup cannot invent a cast context')
            self.assertEqual(len(self.pending_helpers['sword']), pending,
                             'Parent lookup cannot consume pending target metadata')
            self.finish(helper, action)
            self.assertEqual((pool.Amount, self.F.resource('sword').Amount), (3, 40))
        self.assertEqual(self.F.entities['enemy']._hp, 10009 - 119)
        self.assertEqual(self.F.callCount('UseSpell'), 3, 'Helper attribution cannot dispatch more swords')

    def test_completion_before_damage_retains_existing_parent_alias(self):
        spell = 'Target_ESC_LiuguangStage'
        self.F.emit('CastedSpell', 'sword', spell, 'Target', '', 601)
        self.assertEqual(self.packet_sequence(spell, 601, [12, 14]), [13, 16])

    def test_late_using_and_completion_do_not_replay_or_reset_split_rounding(self):
        spell = 'Target_ESC_LiuguangStage'
        first = self.packet_sequence(spell, 602, [12])
        self.F.emit('UsingSpellOnTarget', 'sword', 'enemy', spell, 'Target', '', 602)
        second = self.packet_sequence(spell, 602, [14])
        self.finish(spell, 602)
        self.assertEqual(first + second, [13, 16])
        self.assertEqual(self.F.callCount('UseSpell'), 0)

    def test_level9_helper_does_not_gain_level10_regular_bonus(self):
        self.F.entities['sword'].Classes.Classes[1].Level = 9
        self.assertEqual(self.packet_sequence('Target_ESC_LiuguangStage', 603, [12, 14]), [12, 14])

    def test_level10_helper_damage_without_any_cast_receives_parent_bonus(self):
        self.F.entities['sword'].Classes.Classes[1].Level = 10
        self.assertEqual(self.packet_sequence('Target_ESC_LiuguangStage', 604, [20]), [23])

    def test_domain_and_regular_add_without_inventing_cast_snapshot(self):
        self.domain()
        self.assertEqual(self.packet_sequence('Target_ESC_LiuguangStage', 605, [12, 14]), [16, 19])

    def test_domain_weakpoint_and_regular_add_for_damage_first_helper(self):
        self.domain()
        self.ESC.Runtime.State('enemy').marks['weakpoint:sword'] = self.table(dict(expires=3, used={}))
        self.assertEqual(self.packet_sequence('Target_ESC_LiuguangStage', 606, [12, 14]), [18, 22])

    def test_existing_started_cast_retains_snapshot_after_domain_expires(self):
        self.domain()
        spell = 'Target_ESC_LiuguangStage'
        self.F.emit('UsingSpellOnTarget', 'sword', 'enemy', spell, 'Target', '', 607)
        self.ESC.Runtime.State('sword').domains['taixuan_taiqing'] = None
        self.E.removeStatus('sword', 'ESC_SWORD_DOMAIN', 'sword')
        self.ESC.Runtime.UpdateAuras()
        self.assertEqual(self.packet_sequence(spell, 607, [20]), [27])

    def test_taiqing_damage_first_adds_domain20_and_regular15_once(self):
        self.domain()
        self.assertEqual(self.packet_sequence('Target_ESC_TaiqingPulse', 608, [11, 6]), [14, 8])

    def test_blood_damage_first_receives_regular_bonus(self):
        self.assertEqual(self.packet_sequence('Target_ESC_BloodPulse', 609, [20]), [23])

    def test_blood_h19_f4_native_packet_shape_adds_regular15(self):
        self.F.entities['sword'].Classes.Classes[1].SubClassUUID = bridge.SPEC['classes']['xueyan']
        self.ESC.State('sword').frenzy = 4
        self.assertEqual(self.packet_sequence('Target_ESC_BloodPulse', 621, [7, 6]), [9, 8])
        self.assertIsNone(self.contexts[621], 'Damage-first attribution must not invent a cast')

    def test_domain_parent_bonus_begins_at_level10_without_changing_level9(self):
        for i, (spell, branch) in enumerate((('Target_ESC_TaiqingPulse', 'taixuan'),
                                            ('Target_ESC_BloodPulse', 'xueyan'))):
            self.F.entities['sword'].Classes.Classes[1].SubClassUUID = bridge.SPEC['classes'][branch]
            self.F.entities['sword'].Classes.Classes[1].Level = 9
            self.assertEqual(self.packet_sequence(spell, 630 + i, [20]), [20])
            self.F.entities['sword'].Classes.Classes[1].Level = 10
            self.assertEqual(self.packet_sequence(spell, 640 + i, [20]), [23])

    def test_taiqing_opening_completion_before_damage_has_135_not_155_percent(self):
        self.domain()
        spell = 'Target_ESC_TaiqingPulse'
        self.F.emit('CastedSpell', 'sword', spell, 'Target', '', 650)
        self.assertEqual(self.packet_sequence(spell, 650, [20]), [27])
        self.F.emit('UsingSpellOnTarget', 'sword', 'enemy', spell, 'Target', '', 650)
        self.assertEqual(self.packet_sequence(spell, 650, [20]), [27])

    def test_only_two_domain_aliases_receive_new_parent_attribution(self):
        self.assertEqual(bridge.SPEC['aliases']['Target_ESC_TaiqingPulse'].get('parent'), 'taixuan_taiqing')
        self.assertEqual(bridge.SPEC['aliases']['Target_ESC_BloodPulse'].get('parent'), 'xueyan_xuehai')
        for name in ('Counter2', 'Counter3', 'Resonance', 'Aftershock'):
            self.assertNotIn('parent', bridge.SPEC['aliases']['Target_ESC_' + name])

    def test_external_direct_spell_does_not_inherit_regular_parent(self):
        self.assertEqual(self.packet_sequence('Projectile_MagicMissile', 610, [20]), [20])

    def test_offhand_known_parent_and_ultimate_parent_use_their_own_rows(self):
        self.F.entities['sword'].Classes.Classes[1].SubClassUUID = bridge.SPEC['classes']['tianqing']
        self.assertEqual(self.packet_sequence('Target_ESC_TianbengCone_Off', 611, [20]), [23])
        self.assertEqual(self.packet_sequence('Target_ESC_TiandiStage_Off', 612, [20]), [20])

    def test_all_declared_parent_aliases_use_actual_parent_level_and_cost(self):
        aliases = {spell: alias for spell, alias in bridge.SPEC['aliases'].items() if alias.get('parent')}
        self.assertGreater(len(aliases), 8)
        for i, (spell, alias) in enumerate(aliases.items()):
            with self.subTest(spell=spell):
                parent = bridge.SPEC['spells'][alias['parent']]
                branch = alias['parent'].split('_')[0]
                self.F.entities['sword'].Classes.Classes[1].SubClassUUID = bridge.SPEC['classes'][branch]
                expected = 23 if 6 <= parent['level'] <= 9 and parent['cost'] == 10 else 20
                self.assertEqual(self.packet_sequence(spell, 700+i, [20]), [expected])

    def test_two_owners_targets_same_action_have_separate_stage_rounding(self):
        self.actor('other', branch='taixuan', level=12)
        self.actor('other-enemy', level=0, branch=None, hp=1000, maximum=1000, party='enemies', x=3)
        spell = 'Target_ESC_LiuguangStage'
        self.assertEqual(self.packet_sequence(spell, 801, [12]), [13])
        other_hit = self.native_damage('other', 'other-enemy', [20], spell=spell, action=801)
        self.assertEqual(other_hit.TotalDamageDone, 23)
        self.assertEqual(self.packet_sequence(spell, 801, [14]), [16])
        self.assertIsNone(self.contexts[801])

    def test_miss_failed_or_duplicate_completion_does_not_dispatch_extra_swords(self):
        spell = 'Target_ESC_LiuguangStage'
        self.F.emit('CastedSpell', 'sword', spell, 'Target', '', 802)  # completed miss: no damage packet
        self.F.emit('CastedSpell', 'sword', spell, 'Target', '', 802)
        self.F.emit('CastSpellFailed', 'sword', spell, 'Target', '', 803)
        self.assertEqual(self.F.callCount('UseSpell'), 0)
        self.assertEqual(self.F.resource('sword').Amount, 50)
        self.assertEqual(self.F.entities['enemy']._hp, 10009)


if __name__ == '__main__':
    unittest.main(verbosity=2)
