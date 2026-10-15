"""Generated direct-strike item selection and native child propagation contracts.

Evaluates the exported boolean selectors with entity facts; this cannot establish
native picking, damage immunity, animation or client visual acceptance.
"""
import ast
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

from test_taiqing_pulse_instant import _boolean, read_stats

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / 'mods/EasternSwordCultivator/Source'
FOLDER = 'EasternSwordCultivator_6560ea02-fe1e-5fdb-8631-b41a2e53af90'
DIRECT = {
    'Projectile_ESC_yujian': (18, 'ActionPoint:1'),
    'Projectile_ESC_taixuan_zhaoxi': (18, 'ActionPoint:1'),
    'Projectile_ESC_taixuan_liuguang': (18, 'ActionPoint:1;ESC_SwordYuan:10'),
    'Target_ESC_tianqing_lietian': (18, 'ActionPoint:1;ESC_SwordYuan:4'),
    'Projectile_ESC_xueyan_luexue': (18, 'ActionPoint:1'),
    'Projectile_ESC_xingge_wenlu': (18, 'ActionPoint:1'),
    **{f'Projectile_ESC_xueyan_wusheng_F{spent}': (24, 'ActionPoint:1;ESC_SwordYuan:20')
       for spent in range(16)},
    **{f'Projectile_ESC_{key}_RangedOff_Bonus': (18, 'BonusActionPoint:1')
       for key in ('taixuan_zhaoxi', 'xueyan_luexue', 'xingge_wenlu')},
    'Projectile_ESC_liancheng_ContinueRanged': (18, ''),
    'Projectile_ESC_wusheng_ContinueRanged': (24, ''),
    'Target_ESC_LiuguangStage': (18, ''),
}


def accepts(condition, **facts):
    expression = re.sub(r'(Character|Item|Enemy|IsEquipped|Self|Dead)\(\)',
                        lambda m: str(facts.get(m[1], False)), condition)
    return _boolean(ast.parse(expression, mode='eval'))


class DirectSwordItemTargets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stats = {}
        for path in (SOURCE / 'Public' / FOLDER / 'Stats/Generated/Data').glob('Spell_*.txt'):
            cls.stats.update({name: row['data'] for name, row in read_stats(path).items()})
        cls.editor = {}
        for path in (SOURCE / 'Editor/Mods' / FOLDER / 'Stats/SpellData').glob('*.stats'):
            for obj in ET.parse(path).getroot().findall('./stat_objects/stat_object'):
                row = {field.get('name'): field.get('value') for field in obj.findall('./fields/field')}
                cls.editor[path.stem + '_' + row['Name']] = row

    def test_all_executable_children_admit_environment_items_but_reject_invalid_targets(self):
        for sid in DIRECT:
            condition = self.stats[sid]['TargetConditions']
            for facts, expected in (
                ({'Item': True}, True),  # Fixed doors need not be movable.
                ({'Item': True, 'Dead': True}, False),
                ({'Item': True, 'IsEquipped': True}, False),
                ({'Character': True, 'Enemy': True}, True),
                ({'Character': True}, False),  # Ally or neutral creature.
                ({'Character': True, 'Enemy': True, 'Dead': True}, False),
                ({'Character': True, 'Enemy': True, 'Self': True}, False),
                ({}, False),  # Terrain is not an attackable Item entity.
            ):
                with self.subTest(spell=sid, facts=facts):
                    self.assertEqual(accepts(condition, **facts), expected)

    def test_item_support_preserves_native_attacks_costs_and_ranges(self):
        for sid, (distance, costs) in DIRECT.items():
            row = self.stats[sid]
            with self.subTest(spell=sid):
                self.assertEqual(row['SpellRoll'], 'Attack(AttackType.RangedSpellAttack)')
                self.assertEqual(row['TargetRadius'], str(distance))
                self.assertEqual(row['UseCosts'], costs)
                self.assertIn('DealDamage(', row['SpellSuccess'])
                self.assertIn('ExecuteWeaponFunctors(', row['SpellSuccess'])
                self.assertNotIn('CannotTargetItems', row['SpellFlags'].split(';'))
                self.assertNotIn('InventorySelection', row['SpellFlags'].split(';'))

    def test_toolkit_and_runtime_selectors_agree(self):
        for sid in DIRECT:
            with self.subTest(spell=sid):
                self.assertEqual(self.editor[sid]['TargetConditions'], self.stats[sid]['TargetConditions'])

    def test_native_character_marks_do_not_attach_to_items(self):
        for key, mark in (('taixuan_zhaoxi', 'WEAKPOINT'), ('xingge_wenlu', 'FOLLOWUP')):
            for suffix in ('', '_RangedOff_Bonus'):
                row = self.stats[f'Projectile_ESC_{key}{suffix}']
                functors = [part for part in row['SpellSuccess'].split(';')
                            if f'ApplyStatus(ESC_{mark},' in part]
                self.assertEqual(len(functors), 1)
                condition = re.fullmatch(r'IF\((.*)\):ApplyStatus\(.*', functors[0])[1]
                self.assertFalse(accepts(condition, Item=True))
                self.assertTrue(accepts(condition, Character=True, Enemy=True))

    def test_domains_reactions_support_and_chain_activation_keep_original_targets(self):
        for sid in ('Target_ESC_TaiqingPulse', 'Target_ESC_BloodPulse',
                    'Target_ESC_Counter2', 'Target_ESC_Counter3', 'Target_ESC_Resonance',
                    'Projectile_ESC_xingge_tongzhou'):
            self.assertFalse(accepts(self.stats[sid]['TargetConditions'], Item=True), sid)
        self.assertEqual(self.stats['Shout_ESC_xueyan_liancheng']['TargetConditions'], 'Self()')
        self.assertEqual(self.stats['Shout_ESC_taixuan_taiqing']['TargetConditions'], 'Self()')


if __name__ == '__main__':
    unittest.main()
