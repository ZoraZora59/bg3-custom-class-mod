"""Actual candidate Lua in simulated engine; never native gameplay acceptance."""
from pathlib import Path
import copy
import os
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p / 'build/test-tools').is_dir() and (p / 'scripts/tests/esc_engine_fixture.lua').is_file())
sys.path.insert(0, str(REPO / 'scripts/tests'))
import test_esc_bridge as bridge

FOLDER = 'EasternSwordCultivator_6560ea02-fe1e-5fdb-8631-b41a2e53af90'
RUNTIME = Path(os.environ.get('ESC_AUTO_FOCUS_RUNTIME_CANDIDATE', bridge.LUA / 'Runtime.lua'))
FIXTURE = Path(os.environ.get('ESC_AUTO_FOCUS_FIXTURE_CANDIDATE', REPO / 'scripts/tests/esc_engine_fixture.lua'))
ORIGINAL_FIXTURE = REPO / 'scripts/tests/esc_engine_fixture.lua'
ZHAOXI = 'Projectile_ESC_taixuan_zhaoxi'
PULSE = 'Target_ESC_TaiqingPulse'
original_setup = bridge.Bridge.setUp
original_read = Path.read_text

def read_candidate_fixture(path, *args, **kwargs):
    if path.resolve() == ORIGINAL_FIXTURE.resolve():
        return original_read(FIXTURE, *args, **kwargs)
    return original_read(path, *args, **kwargs)

def setup_candidate(self):
    snapshot = dict(bridge.SNAPSHOT)
    snapshot['Runtime.lua'] = RUNTIME.read_bytes()
    spec = copy.deepcopy(bridge.SPEC)
    spec['spells']['focus_target']['retired'] = True
    with patch.object(bridge, 'SNAPSHOT', snapshot), patch.object(bridge, 'SPEC', spec), patch.object(Path, 'read_text', read_candidate_fixture):
        original_setup(self)

class AutoFocus(unittest.TestCase):
    table = bridge.Bridge.table
    actor = bridge.Bridge.actor
    cast = bridge.Bridge.cast

    def setUp(self):
        setup_candidate(self)
        self.actor(branch='taixuan', hp=100, maximum=100)
        self.actor('enemy', level=0, party='enemies', x=2)
        self.actor('other', level=0, party='enemies', x=3)
        self.actor('ally', level=0, party='players', x=1)

    def finish(self, spell=ZHAOXI, target='other', action=11):
        self.ESC.Runtime.BeginCast('sword', spell, action, target)
        self.ESC.Runtime.FinishCast('sword', spell, action)

    def counts(self):
        result = {}
        for call in self.F.calls.values():
            if call.name == 'UseSpell' and call.args[2] == PULSE:
                result[call.args[3]] = result.get(call.args[3], 0) + 1
        return result

    def test_paid_attack_updates_only_when_root_completes_and_miss_still_selects(self):
        self.ESC.State('sword').focus = 'enemy'
        self.ESC.Runtime.BeginCast('sword', ZHAOXI, 11, 'other')
        self.assertEqual(self.ESC.State('sword').focus, 'enemy')
        # No hit event: a missed native attack still expresses player intent.
        self.ESC.Runtime.FinishCast('sword', ZHAOXI, 11)
        self.assertEqual(self.ESC.State('sword').focus, 'other')
        self.ESC.State('sword').focus = 'enemy'
        self.ESC.Runtime.FinishCast('sword', ZHAOXI, 11)
        self.assertEqual(self.ESC.State('sword').focus, 'enemy', 'Duplicate finish must not reselect')

    def test_failed_cast_does_not_reselect_even_after_late_finish(self):
        self.ESC.State('sword').focus = 'enemy'
        self.F.emit('UsingSpellOnTarget', 'sword', 'other', ZHAOXI, 'Projectile', '', 12)
        self.F.emit('CastSpellFailed', 'sword', ZHAOXI, 'Projectile', '', 12)
        self.F.emit('CastedSpell', 'sword', ZHAOXI, 'Projectile', '', 12)
        self.assertEqual(self.ESC.State('sword').focus, 'enemy')

    def test_nearest_fallback_is_stable_with_uuid_tie_break_and_keeps_first_buff_order(self):
        self.F.entities['other'].Transform.Transform.Translate = self.table([2, 0, 0])
        self.cast('sword', 'taixuan_taiqing', action=13)
        self.assertEqual(self.ESC.State('sword').focus, 'enemy')
        self.assertEqual(self.counts(), {'enemy': 3, 'other': 1})
        calls = list(self.F.calls.values())
        aura = [i for i, c in enumerate(calls) if c.name == 'AddBoosts' and c.args[1] == 'sword' and c.args[3] == 'ESC_aura']
        pulses = [i for i, c in enumerate(calls) if c.name == 'UseSpell' and c.args[2] == PULSE]
        self.assertLess(aura[0], pulses[0])

    def test_targeted_attack_switches_next_pulse_without_refreshing_domain_or_casting_extra(self):
        self.cast('sword', 'taixuan_taiqing', action=14)
        expires = self.ESC.State('sword').domains.taixuan_taiqing.expires
        self.F.clearCalls()
        self.finish(action=15)
        self.assertEqual(self.counts(), {})
        self.assertEqual(self.ESC.State('sword').domains.taixuan_taiqing.expires, expires)
        self.ESC.Runtime.Pulse('sword', 'taixuan_taiqing')
        self.assertEqual(self.counts(), {'enemy': 1, 'other': 3})

    def test_ordinary_paid_main_sword_attack_selects_target(self):
        self.finish('Target_MainHandAttack', action=16)
        self.assertEqual(self.ESC.State('sword').focus, 'other')

    def test_native_name_guid_attack_records_canonical_focus(self):
        self.lua.execute('''
            local original=Ext.Entity.Get
            function Ext.Entity.Get(ref)
                return original(ref=='Goblins_Male_Guard_other' and 'other' or ref)
            end
        ''')
        self.finish(target='Goblins_Male_Guard_other', action=17)
        self.assertEqual(self.ESC.State('sword').focus, 'other')

    def test_opportunity_paid_root_is_allowed_but_selection_container_and_bonus_child_are_not(self):
        self.F.stats[ZHAOXI].UseCosts = 'ESC_SwordOpportunity:1'
        self.finish(action=18)
        self.assertEqual(self.ESC.State('sword').focus, 'other')
        self.ESC.State('sword').focus = 'enemy'
        # A selector must never update focus, even if a saved row has a paid cost.
        self.F.stats[ZHAOXI].ContainerSpells = 'Projectile_ESC_taixuan_zhaoxi_RangedOff_Bonus'
        self.finish(ZHAOXI, action=19)
        self.F.stats[ZHAOXI].ContainerSpells = ''
        self.F.entities['sword']._equipped['Melee Offhand Weapon'] = 'sword:sword'
        self.finish('Projectile_ESC_taixuan_zhaoxi_RangedOff_Bonus', action=119)
        self.assertEqual(self.ESC.State('sword').focus, 'enemy')

    def test_automatic_helpers_and_aoe_victims_cannot_hijack_focus(self):
        self.ESC.State('sword').focus = 'enemy'
        for action, spell in enumerate(('Target_ESC_TaiqingPulse', 'Target_ESC_Counter2', 'Target_ESC_Counter3',
                                        'Target_ESC_LiuguangStage', 'Target_ESC_Resonance',
                                        'Target_ESC_taixuan_jiuxiao', 'Shout_ESC_taixuan_xinghe',
                                        'Zone_ESC_taixuan_yixiantian'), start=20):
            self.finish(spell, action=action)
            self.assertEqual(self.ESC.State('sword').focus, 'enemy', spell)

    def test_paid_single_target_callback_with_multiple_distinct_targets_is_rejected(self):
        self.ESC.State('sword').focus = 'enemy'
        self.F.emit('UsingSpellOnTarget', 'sword', 'other', ZHAOXI, 'Projectile', '', 30)
        self.F.emit('UsingSpellOnTarget', 'sword', 'enemy', ZHAOXI, 'Projectile', '', 30)
        self.F.emit('CastedSpell', 'sword', ZHAOXI, 'Projectile', '', 30)
        self.assertEqual(self.ESC.State('sword').focus, 'enemy')

    def test_free_cooperation_and_nonplayer_casts_cannot_select_focus(self):
        self.ESC.State('sword').focus = 'enemy'
        cast = self.ESC.Runtime.BeginCast('sword', 'Target_MainHandAttack', 31, 'other')
        cast.meta = self.table({'cooperator': 'ally', 'originalSpell': 'Target_MainHandAttack'})
        self.ESC.Runtime.FinishCast('sword', 'Target_MainHandAttack', 31)
        self.assertEqual(self.ESC.State('sword').focus, 'enemy')
        self.F.entities['sword']._player = False
        self.finish(action=32)
        self.assertEqual(self.ESC.State('sword').focus, 'enemy')

    def test_legacy_free_button_has_no_effect(self):
        self.ESC.State('sword').focus = 'enemy'
        self.cast('sword', 'focus_target', 'other', action=33)
        self.assertEqual(self.ESC.State('sword').focus, 'enemy')

    def test_friend_dead_dying_missing_and_invulnerable_targets_cannot_select(self):
        self.ESC.State('sword').focus = 'enemy'
        self.finish(target='ally', action=40)
        self.F.entities['other']._dead = True
        self.finish(action=41)
        self.F.entities['other']._dead = False
        self.F.entities['other']._hp = 0
        self.finish(action=42)
        self.F.entities['other']._hp = 100
        self.F.entities['other'].StatusContainer.Statuses = self.table({'dying': 'DYING'})
        self.finish(action=43)
        self.F.entities['other'].StatusContainer.Statuses = self.table({})
        self.F.entities['other'].BoostsContainer = self.table({'Boosts': [{'Type': 'Invulnerable', 'Boosts': ['dummy-handle']}]})
        self.finish(action=44)
        self.F.entities['other'].BoostsContainer = None
        self.F.stats['INVULNERABLE'] = self.table({'Boosts': 'Invulnerable()'})
        self.F.entities['other'].StatusContainer.Statuses = self.table({'native': 'INVULNERABLE'})
        self.finish(action=45)
        self.finish(target='gone', action=46)
        self.assertEqual(self.ESC.State('sword').focus, 'enemy')

    def test_invalid_saved_focus_falls_back_but_live_out_of_range_focus_stays(self):
        self.ESC.State('sword').focus = 'gone'
        self.cast('sword', 'taixuan_taiqing', action=50)
        self.assertEqual(self.ESC.State('sword').focus, 'enemy')
        self.F.entities['enemy'].Transform.Transform.Translate = self.table([10, 0, 0])
        self.F.clearCalls()
        self.cast('sword', 'taixuan_taiqing', action=51)
        self.assertEqual(self.ESC.State('sword').focus, 'enemy')
        self.assertEqual(self.counts(), {'other': 1})

    def test_invulnerable_existing_focus_gets_no_extra_swords(self):
        self.cast('sword', 'taixuan_taiqing', action=52)
        self.F.entities['enemy'].BoostsContainer = self.table({'Boosts': [{'Type': 'Invulnerable', 'Boosts': ['dummy-handle']}]})
        self.F.clearCalls()
        self.ESC.Runtime.Pulse('sword', 'taixuan_taiqing')
        self.assertEqual(self.counts(), {'enemy': 1, 'other': 1})

    def test_no_enemies_open_safely_and_four_round_duration_unchanged(self):
        self.F.entities['enemy']._dead = self.F.entities['other']._dead = True
        self.cast('sword', 'taixuan_taiqing', action=53)
        self.assertIsNone(self.ESC.State('sword').focus)
        self.assertEqual(self.counts(), {})
        for _ in range(3):
            self.F.emit('TurnStarted', 'sword')
        self.assertIsNotNone(self.ESC.State('sword').domains.taixuan_taiqing)
        self.F.emit('TurnStarted', 'sword')
        self.assertIsNone(self.ESC.State('sword').domains.taixuan_taiqing)

    def test_saved_button_removed_once_on_load_and_regranted_button_on_level_respec(self):
        actor = self.F.entities['sword']
        kept = ('Shout_ESC_taixuan_taiqing', ZHAOXI, 'Projectile_FireBolt')
        actor._spells = self.table({spell: True for spell in (*kept, 'Target_ESC_focus_target')})
        self.F.event('SessionLoaded', self.table({}))
        self.assertIsNone(actor._spells['Target_ESC_focus_target'])
        self.assertTrue(all(actor._spells[spell] for spell in kept))
        removed = [c for c in self.F.calls.values() if c.name == 'RemoveSpell' and c.args[2] == 'Target_ESC_focus_target']
        self.assertEqual(len(removed), 1)
        self.assertEqual(removed[0].args[3], 0)
        self.F.event('SessionLoaded', self.table({}))
        self.assertEqual(len([c for c in self.F.calls.values() if c.name == 'RemoveSpell' and c.args[2] == 'Target_ESC_focus_target']), 1)
        for event in ('LeveledUp', 'RespecCompleted'):
            actor._spells['Target_ESC_focus_target'] = True
            self.F.emit(event, 'sword')
            self.assertIsNone(actor._spells['Target_ESC_focus_target'])

    def test_nonclass_characters_saved_spell_grants_are_not_mutated(self):
        ordinary = self.actor('ordinary', level=0, party='players')
        ordinary._spells = self.table({'Target_ESC_focus_target': True})
        self.F.event('SessionLoaded', self.table({}))
        self.assertTrue(ordinary._spells['Target_ESC_focus_target'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
