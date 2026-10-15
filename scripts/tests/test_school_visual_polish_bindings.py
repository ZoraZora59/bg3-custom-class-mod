"""Guard against duplicate hits, helper-wide bursts and unsupported lifecycle bindings."""
import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts'))
import school_visual_polish as polish
from sword_cultivator_spec import FOLDER
from sword_spell_presentation import EFFECT_FIELDS, SOUND_FIELDS, SELF_UTILITY, present_spell
SOURCE = REPO / 'mods/EasternSwordCultivator/Source'


def sample(skill, role):
    return {'skill': skill, 'binding': role, 'phase': 'impact' if role == 'hit' else role,
            'mei': skill + '_' + role, 'offhandMei': skill + '_offhand_cast',
            'trajectories': skill + '_root,' + skill + '_pathfind'}


def stats():
    result = {}
    for path in (SOURCE / 'Public' / FOLDER / 'Stats/Generated/Data').glob('*.txt'):
        for name, body in re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)', path.read_text(encoding='utf-8'), re.S):
            result[name] = dict(re.findall(r'^data "([^"]+)" "([^"]*)"$', body, re.M))
    return result


class SchoolPolishBindingSafety(unittest.TestCase):
    def test_projectile_owns_impact_and_human_jump_trajectory_is_preserved(self):
        records = {'hit': sample('xueyan_liancheng', 'hit')}
        projectile = dict(SpellType='Projectile', SpellSuccess='DealDamage(2d6,Force)', Trajectories='old')
        binding = polish.spell_bindings('Projectile_ESC_liancheng_ContinueRanged', projectile, records)
        self.assertEqual(binding['Trajectories'], records['hit']['trajectories'])
        self.assertEqual(binding['HitEffect'], '')
        self.assertEqual(polish.spell_bindings('Projectile_ESC_ChainMove',
            dict(SpellType='Projectile', SpellFlags='IsJump', Trajectories='human'), records), {})

    def test_cast_offhand_matches_the_actual_animation_event(self):
        records = {'cast': sample('taixuan_zhaoxi', 'cast')}
        for hand, event, expected in [('Main', 'Cast', 'mei'), ('Off', 'CastOffhand', 'offhandMei')]:
            binding = polish.spell_bindings('Target_ESC_taixuan_zhaoxi_Melee' + hand,
                dict(SpellType='Target', CastTextEvent=event, SpellRoll='Attack(MeleeWeaponAttack)'), records)
            self.assertEqual(binding['CastEffect'], records['cast'][expected])
        editor, exported = polish._mei('taixuan_zhaoxi_cast', {'binding': 'cast'}, True)
        self.assertEqual(editor[0].get('TargetBone'), 'Dummy_Root')
        self.assertEqual(editor[0].get('StartTextKey'), 'CastOffhand')
        self.assertEqual(editor[0].get('Pivot'), 'Target')

    def test_recovery_cost_options_suppress_only_inherited_healing_preparation(self):
        records = {'cast': sample('xueyan_huichao', 'cast')}
        for suffix in ('Yuan','Frenzy'):
            result = polish.spell_bindings('Target_ESC_xueyan_huichao_'+suffix,
                dict(SpellType='Target', SpellProperties='ApplyStatus(ESC_CAST_XUEYAN_HUICHAO,100,0)'), records)
            self.assertIn('PrepareEffect', result)
            self.assertEqual(result['PrepareEffect'], '')
            self.assertEqual(result['CastEffect'], 'xueyan_huichao_cast')
            self.assertFalse(any(k in result for k in ('SpellProperties','UseCosts','SpellAnimation','SpellFlags')))
        other = {'cast': sample('tianqing_nixi','cast')}
        self.assertNotIn('PrepareEffect', polish.spell_bindings('Target_ESC_tianqing_nixi',
            dict(SpellType='Target'), other))

    def test_internal_stages_never_replay_full_cast_and_containers_remain_inert(self):
        records = {'hit': sample('taixuan_liuguang', 'hit'), 'cast': sample('taixuan_liuguang', 'cast')}
        binding = polish.spell_bindings('Target_ESC_LiuguangStage',
            dict(SpellType='Target', SpellSuccess='DealDamage(2d8,Force)'), records)
        self.assertEqual(binding['CastEffect'], '')
        self.assertEqual(binding['PrepareEffect'], '')
        self.assertEqual(binding['HitEffect'], records['hit']['mei'])
        self.assertEqual(polish.spell_bindings('Projectile_ESC_taixuan_liuguang',
            dict(ContainerSpells='child'), records), {})

    def test_two_counter_ranks_use_their_correct_taixuan_contact(self):
        records = {'a': sample('taixuan_qinghui', 'hit'), 'b': sample('taixuan_xinghe', 'hit')}
        for rank, skill in [(2, 'taixuan_qinghui'), (3, 'taixuan_xinghe')]:
            binding = polish.spell_bindings('Target_ESC_Counter' + str(rank),
                dict(SpellType='Target', SpellSuccess='DealDamage(3d8,Force)'), records)
            self.assertEqual(binding['HitEffect'], skill + '_hit')

    def test_blood_siphon_status_never_displays_domain_ring(self):
        records = {'ring': sample('xueyan_xuehai', 'status')}
        self.assertEqual(polish.status_bindings('ESC_BLOOD_ROBE', records), {})
        self.assertEqual(polish.status_bindings('ESC_VFX_BLOOD_DOMAIN', records), {'StatusEffect': 'xueyan_xuehai_status'})
        sword = {'ring': sample('taixuan_taiqing', 'status')}
        self.assertEqual(polish.status_bindings('ESC_SWORD_DOMAIN', sword), {})
        self.assertEqual(polish.status_bindings('ESC_VFX_SWORD_DOMAIN', sword), {'StatusEffect': 'taixuan_taiqing_status'})

    def test_xingge_assistance_attaches_to_selected_target_without_caster_burst(self):
        for skill in ('huifeng', 'fuchen', 'chengfeng', 'xiangfu'):
            key = 'xingge_' + skill
            records = {'target': sample(key, 'target')}
            result = polish.spell_bindings('Target_ESC_' + key,
                dict(SpellType='Target', SpellProperties='ApplyStatus(ESC_CAST_' + key.upper() + ',100,0)'), records)
            self.assertEqual(result['TargetEffect'], key + '_target')
            self.assertEqual(result['CastEffect'], '')
            self.assertEqual(result['PrepareEffect'], '')
            self.assertFalse(any(k in result for k in ('SpellProperties', 'UseCosts', 'SpellAnimation', 'SpellFlags')))
        editor, _ = polish._mei('xingge_xiangfu_target', {'binding': 'target'})
        self.assertEqual(editor[0].get('TargetBone'), 'Dummy_Root')
        self.assertEqual(editor[0].get('BindTargetTo'), 'TargetEntity')
        self.assertEqual(editor[0].get('DetachTarget'), 'false')
        self.assertNotIn('StartTextKey', editor[0].attrib)

    def test_xingge_event_cues_and_domain_markers_cannot_play_on_generic_cast(self):
        for key in ('xingge_wenlu', 'xingge_fengyu'):
            records = {'event': sample(key, 'target')}
            self.assertEqual(polish.spell_bindings('Target_ESC_' + key,
                dict(SpellType='Target'), records), {})
        for mechanism, visual, key in (
            ('ESC_DAMAGE_SHARE', 'ESC_VFX_DAMAGE_SHARE', 'xingge_fengyu'),
            ('ESC_TEAM_RESONANCE', 'ESC_VFX_TEAM_RESONANCE', 'xingge_zhangjian')):
            records = {'node': sample(key, 'status')}
            self.assertEqual(polish.status_bindings(mechanism, records), {})
            self.assertEqual(polish.status_bindings(visual, records), {'StatusEffect': key + '_status'})

    def test_xingge_domains_replace_action_surge_visuals_with_recipient_status_only(self):
        for key, visual, cost in (
            ('xingge_fengyu', 'ESC_VFX_DAMAGE_SHARE', 10),
            ('xingge_zhangjian', 'ESC_VFX_TEAM_RESONANCE', 20)):
            with self.subTest(skill=key):
                name = 'Shout_ESC_' + key
                records = {'node': sample(key, 'status')}
                # Match entry(): native presentation first, polish override last.
                native = present_spell(name, dict(SpellType='Shout', TargetConditions='Self()',
                    SpellProperties='ApplyStatus(ESC_CAST_' + key.upper() + ',100,0)',
                    UseCosts='ActionPoint:1;ESC_SwordYuan:' + str(cost)), 'Shout_SecondWind')
                self.assertEqual(native['PrepareEffect'], SELF_UTILITY['PrepareEffect'])
                self.assertEqual(native['CastEffect'], SELF_UTILITY['CastEffect'])
                binding = polish.spell_bindings(name, native, records)
                applied = {**native, **binding}
                self.assertEqual({field: applied[field] for field in EFFECT_FIELDS},
                                 {field: '' for field in EFFECT_FIELDS})
                self.assertEqual({field: value for field, value in applied.items() if field not in EFFECT_FIELDS},
                                 {field: value for field, value in native.items() if field not in EFFECT_FIELDS})
                self.assertEqual(applied['SpellAnimation'], SELF_UTILITY['SpellAnimation'])
                self.assertEqual({field: applied[field] for field in SOUND_FIELDS},
                                 {field: native[field] for field in SOUND_FIELDS})
                self.assertEqual(polish.status_bindings(visual, records), {'StatusEffect': key + '_status'})
                self.assertEqual(polish.spell_bindings(name, native, {}), {})

    def test_xingge_domain_cleanup_keeps_other_schools_and_real_resonance_hit(self):
        for key in ('taixuan_taiqing', 'xueyan_xuehai'):
            with self.subTest(skill=key):
                records = {'node': sample(key, 'status')}
                native = present_spell('Shout_ESC_' + key, dict(SpellType='Shout'), 'Shout_SecondWind')
                self.assertEqual(polish.spell_bindings('Shout_ESC_' + key, native, records), {})
        records = {'node': sample('xingge_zhangjian', 'status'),
                   'hit': sample('xingge_zhangjian', 'hit')}
        helper = polish.spell_bindings('Target_ESC_Resonance',
            dict(SpellType='Target', SpellSuccess='DealDamage(2d6,Force)'), records)
        self.assertEqual(helper['HitEffect'], 'xingge_zhangjian_hit')
        self.assertEqual(helper['CastEffect'], '')
        self.assertNotIn('SpellAnimation', helper)

    def test_invalid_compile_receipt_cannot_write_or_enable_bindings(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            receipt = source / polish.RECEIPT
            receipt.parent.mkdir(parents=True)
            receipt.write_text(json.dumps({'compiler': 'AllSpark.EffectCompiler.Compiler.Compile', 'records': []}), encoding='utf-8')
            with patch.object(polish, 'profiles', return_value={'new_hit': {'skill': 'taixuan_zhaoxi', 'binding': 'hit'}}), patch.object(polish, '_write_xml') as write:
                with self.assertRaisesRegex(ValueError, 'precisely'):
                    polish.generate_resources(source)
                write.assert_not_called()

    def test_registered_sources_receipts_and_status_bindings_are_current(self):
        receipt = json.loads((SOURCE / polish.RECEIPT).read_text(encoding='utf-8'))
        proof = {r['effect_name']: r for r in receipt['records']}
        spec = json.loads((REPO / 'mods/EasternSwordCultivator/implementation-spec.json').read_text(encoding='utf-8'))['schoolPolishVfx']
        self.assertTrue(spec['enabled'])
        self.assertEqual(set(spec['records']), set(polish.profiles()))
        for key, row in spec['records'].items():
            editor, binary = polish.paths(key)
            self.assertEqual(polish.digest(SOURCE / editor), proof[polish.effect_name(key)]['source_sha256'])
            self.assertEqual(polish.digest(SOURCE / binary), proof[polish.effect_name(key)]['compiled_sha256'])
        rows = stats()
        self.assertEqual(rows['ESC_IN_FLIGHT']['StatusEffect'],
                         polish.mei_guid('common_sword_flight_status'))
        self.assertNotIn('StatusEffect', rows['ESC_BLOOD_ROBE'])
        self.assertEqual(rows['ESC_VFX_BLOOD_DOMAIN']['StatusEffect'], polish.mei_guid('xueyan_xuehai_status'))
        self.assertNotIn('StatusEffect', rows['ESC_SWORD_DOMAIN'])
        self.assertEqual(rows['ESC_VFX_SWORD_DOMAIN']['StatusEffect'], polish.mei_guid('taixuan_taiqing_status'))
        for name, row in rows.items():
            if row.get('ContainerSpells'):
                self.assertNotIn(row.get('CastEffect'), {r['mei'] for r in spec['records'].values()})
            if name in ('Target_ESC_LiuguangStage', 'Target_ESC_BloodPulse'):
                self.assertEqual(row['CastEffect'], '')


if __name__ == '__main__':
    unittest.main()
