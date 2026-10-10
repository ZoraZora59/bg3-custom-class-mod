"""Verify release banks and execution binding, separately from client VFX proof."""
import json
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts'))
from sword_cultivator_spec import FOLDER
from tianqing_vfx_resources import BANK, RECEIPT, PROFILES, paths, digest
from school_visual_polish import mei_guid as local_contact_mei

SOURCE = REPO / 'mods/EasternSwordCultivator/Source'
PUBLIC = SOURCE / 'Public' / FOLDER


def stats():
    result = {}
    for file in (PUBLIC / 'Stats/Generated/Data').glob('Spell_*.txt'):
        for name, body in re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)', file.read_text(encoding='utf-8'), re.S):
            result[name] = dict(re.findall(r'^data "([^"]+)" "([^"]*)"$', body, re.M))
            result[name]['_using'] = next(iter(re.findall(r'^using "([^"]+)"', body, re.M)), '')
    return result


class TianqingReleaseIntegration(unittest.TestCase):
    def test_compiled_banks_match_current_sources_and_registered_resource_paths(self):
        receipt = json.loads((SOURCE / RECEIPT).read_text(encoding='utf-8'))
        self.assertEqual(receipt['compiler'], 'AllSpark.EffectCompiler.Compiler.Compile')
        proof = {r['effect_name']: r for r in receipt['records']}
        bank = ET.parse(SOURCE / BANK)
        resources = [dict((a.get('id'), a.get('value')) for a in n.findall('attribute'))
                     for n in bank.findall('.//node[@id="Resource"]')]
        by_name = {r['EffectName']: r for r in resources}
        self.assertEqual(set(by_name), {p['effect_name'] for p in PROFILES.values()})
        for key, p in PROFILES.items():
            editor, binary = paths(key)
            self.assertEqual(digest(SOURCE / editor), proof[p['effect_name']]['source_sha256'].lower())
            self.assertEqual(digest(SOURCE / binary), proof[p['effect_name']]['compiled_sha256'].lower())
            self.assertEqual(by_name[p['effect_name']]['SourceFile'], binary.as_posix())
            self.assertEqual(by_name[p['effect_name']]['Looping'],
                             'True' if p.get('timing_phase') == 'prepare' else 'False')

    def test_runtime_config_has_three_area_stages_and_eight_single_columns(self):
        spec = json.loads((SOURCE / 'Mods' / FOLDER / 'ScriptExtender/Lua/GeneratedSpec.json').read_text(encoding='utf-8'))
        vfx = spec['tianqingVfx']
        self.assertTrue(vfx['enabled'])
        self.assertEqual(vfx['tiandi']['stageCount'], 3)
        self.assertGreaterEqual(vfx['tiandi']['intervalMs'], vfx['tiandi']['hitTimeMs'])
        self.assertEqual(vfx['bafang']['count'], 8)
        self.assertEqual(vfx['bafang']['effect'], vfx['records']['tianqing_bafang_column']['effect'])
        self.assertNotEqual(vfx['bafang']['effect'], vfx['records']['tianqing_bafang']['effect'])

    def test_lietian_canonical_target_keeps_cost_roll_damage_and_local_contact(self):
        rows = stats()
        row = rows['Target_ESC_tianqing_lietian']
        self.assertEqual(row['SpellType'], 'Target')
        self.assertEqual(row['TargetRadius'], '18')
        self.assertEqual(row['UseCosts'], 'ActionPoint:1;ESC_SwordYuan:4')
        self.assertEqual(row['SpellRoll'], 'Attack(AttackType.RangedSpellAttack)')
        self.assertIn('DealDamage(12d8,Force,Magical)', row['SpellSuccess'])
        self.assertIn('DealDamage(MainMeleeWeapon,MainMeleeWeaponDamageType,Magical)', row['SpellSuccess'])
        self.assertIn('DealDamage(OffhandMeleeWeapon,OffhandMeleeWeaponDamageType,Magical)', row['SpellSuccess'])
        self.assertIn('DealDamage(2d6+WisdomModifier,Force,Magical)', row['SpellSuccess'])
        self.assertEqual(row['ContainerSpells'], '')
        self.assertNotIn('IsLinkedSpellContainer', row['SpellFlags'])
        self.assertEqual(row.get('Trajectories', ''), '')
        self.assertEqual(row['HitEffect'], local_contact_mei('tianqing_lietian_hit'))
        for prefix in ('Projectile', 'Target'):
            for hand in ('Main','Off'):
                self.assertNotIn(prefix + '_ESC_tianqing_lietian_' + hand, rows)
        spec = json.loads((SOURCE / 'Mods' / FOLDER / 'ScriptExtender/Lua/GeneratedSpec.json').read_text(encoding='utf-8'))
        self.assertEqual(spec['aliases']['Target_ESC_tianqing_lietian']['hand'], 'auto')
        self.assertEqual(spec['spells']['tianqing_lietian']['base'], 'AUTO')

    def test_tiandi_paid_cast_only_collects_targets_and_helpers_keep_real_attack(self):
        rows = stats()
        for hand in ('Main', 'Off'):
            paid = rows['Target_ESC_tianqing_tiandi']
            self.assertEqual(paid['SpellRoll'], '')
            self.assertEqual(paid['SpellSuccess'], '')
            self.assertIn('ApplyStatus(ESC_TIANDI_TARGET', paid['SpellProperties'])
            self.assertIn('ESC_SwordYuan:20', paid['UseCosts'])
            from sword_spell_presentation import SWORD_SWEEP
            self.assertEqual(paid['SpellAnimation'], SWORD_SWEEP['SpellAnimation'])
            helper = rows['Target_ESC_TiandiStage' + ('_Off' if hand == 'Off' else '')]
            self.assertEqual(helper['UseCosts'], '')
            self.assertIn('Attack(', helper['SpellRoll'])
            self.assertIn('DealDamage(', helper['SpellSuccess'])
            self.assertIn('SavingThrow(Ability.Strength', helper['SpellSuccess'])
            self.assertNotIn('ESC_TIANDI_FIRSTHIT', helper['SpellSuccess'])
            # The scene-wide sword is still once per stage. This is only a
            # small gold contact at each real native attack's recipient.
            self.assertEqual(helper['HitEffect'], local_contact_mei('tianqing_tiandi_hit'))
            no_control = rows['Target_ESC_TiandiStage_NoControl' + ('_Off' if hand == 'Off' else '')]
            self.assertEqual(no_control['SpellRoll'], helper['SpellRoll'])
            self.assertEqual(no_control['UseCosts'], '')
            self.assertNotIn('SavingThrow(', no_control['SpellSuccess'])
            self.assertNotIn('ESC_SAVEFAIL_', no_control['SpellSuccess'])
            self.assertNotIn('ESC_TIANDI_FIRSTHIT', no_control['SpellSuccess'])
            self.assertIn('ESC_HIT_MARKER', no_control['SpellSuccess'])
            self.assertIn('14d8', no_control['SpellSuccess'])

    def test_native_editor_tables_compile_lietian_ids_with_correct_type_prefix(self):
        editor = SOURCE / 'Editor/Mods' / FOLDER / 'Stats/SpellData'
        target = {f.get('value') for f in ET.parse(editor / 'Target.stats').findall('.//field[@name="Name"]')}
        projectile = {f.get('value') for f in ET.parse(editor / 'Projectile.stats').findall('.//field[@name="Name"]')}
        self.assertIn('ESC_tianqing_lietian', target)
        self.assertNotIn('ESC_tianqing_lietian', projectile)
        for hand in ('Main', 'Off'):
            self.assertNotIn('ESC_tianqing_lietian_' + hand, target)
            self.assertNotIn('ESC_tianqing_lietian_' + hand, projectile)
        self.assertFalse(any(n.startswith('Projectile_') for n in target))
        self.assertFalse(any(n.startswith('Target_') for n in projectile))

    def test_tianjian_still_uses_human_jump_and_landing_explosion(self):
        rows = stats()
        root = 'Projectile_ESC_tianqing_tianjian'
        jump = rows[root]
        self.assertEqual(jump['_using'], 'Projectile_Jump')
        self.assertIn('IsJump', jump['SpellFlags'])
        self.assertNotIn('IsLinkedSpellContainer', jump['SpellFlags'])
        self.assertEqual(jump['SpellProperties'], 'GROUND:CreateExplosion(Projectile_ESC_TianjianImpact)')
        self.assertEqual(jump['SpellJumpType'], 'Jump')
        self.assertEqual(jump['UseCosts'], 'ActionPoint:1;ESC_SwordYuan:10')
        self.assertEqual(jump['ContainerSpells'], '')
        for hand in ('Main', 'Off'):
            old = rows[root + '_' + hand]
            self.assertEqual(old['ContainerSpells'], root)
            self.assertEqual(old['UseCosts'], '')
            self.assertEqual(old['SpellProperties'], '')
            self.assertEqual(old['SpellSuccess'], '')
        impact = rows['Projectile_ESC_TianjianImpact']
        self.assertIn('SavingThrow(Ability.Dexterity', impact['SpellRoll'])
        self.assertIn('DealDamage(26d8,Force,Magical)', impact['SpellSuccess'])
        self.assertIn('MainMeleeWeapon,MainMeleeWeaponDamageType', impact['SpellSuccess'])
        self.assertIn('OffhandMeleeWeapon,OffhandMeleeWeaponDamageType', impact['SpellSuccess'])
        self.assertIn('2d6+WisdomModifier,Force', impact['SpellSuccess'])
        self.assertEqual(impact['UseCosts'], '')


if __name__ == '__main__':
    unittest.main()
