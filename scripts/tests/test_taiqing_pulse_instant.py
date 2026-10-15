"""Verify generated Taiqing native attacks; these checks are not client proof."""
import ast
import itertools
import os
from pathlib import Path
import re
import unittest


REPO = next(p for p in Path(__file__).resolve().parents
            if (p / 'scripts/generate-sword-cultivator.py').is_file())
FOLDER = 'EasternSwordCultivator_6560ea02-fe1e-5fdb-8631-b41a2e53af90'
DATA = Path(os.environ['ESC_HELPER_STATS_CANDIDATE']) if os.environ.get('ESC_HELPER_STATS_CANDIDATE') else REPO / 'mods/EasternSwordCultivator/Source/Public' / FOLDER / 'Stats/Generated/Data'


def read_stats(path):
    text = path.read_text(encoding='utf-8')
    return {name: {
        'using': next(iter(re.findall(r'^using "([^"]+)"', body, re.M)), ''),
        'data': dict(re.findall(r'^data "([^"]+)" "([^"]*)"', body, re.M)),
    } for name, body in re.findall(
        r'^new entry "([^"]+)"\n(.*?)(?=^new entry |\Z)', text, re.M | re.S)}


# Presentation and gameplay contracts are explicit semantic checks, not hashes.
PRESENTATION_FIELDS = {
    'DisplayName','SpellAnimation','SpellFlags','PrepareEffect','CastEffect',
    'PrepareSound','PrepareLoopSound','CastSound','TargetSound','VocalComponentSound',
}
AUTO_HELPERS = {
    'Target_ESC_TaiqingPulse': ('2d8', 30, '219f1b14-5372-5071-9d28-c74a315b9fb9'),
    'Target_ESC_BloodPulse': ('2d6', 30, '77fc4b3d-4263-5503-8642-6ab0b3b7cad0'),
    'Target_ESC_Counter2': ('4d8', 18, 'b197b270-77a7-58a1-8a49-19d73183eabd'),
    'Target_ESC_Counter3': ('6d8', 18, 'daa31a1d-7d8a-5ddf-b33c-f23f130c7a79'),
    'Target_ESC_Resonance': ('2d6', 30, 'e78657ee-c90d-5367-9fcd-879f65440a45'),
}


def _boolean(node):
    if isinstance(node, ast.Expression): return _boolean(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, bool): return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not): return not _boolean(node.operand)
    if isinstance(node, ast.BoolOp):
        values = [_boolean(v) for v in node.values]
        if isinstance(node.op, ast.And): return all(values)
        if isinstance(node.op, ast.Or): return any(values)
    raise AssertionError('Unsupported native AUTO condition: ' + ast.dump(node))


def active_functors(expression, statuses):
    result = []
    for entry in expression.split(';'):
        conditional = re.fullmatch(r'IF\((.*)\):(.*)', entry)
        if conditional:
            condition, entry = conditional.groups()
            condition = re.sub(r"HasStatus\('([^']+)',context.Source\)",
                               lambda m: str(m[1] in statuses), condition)
            if not _boolean(ast.parse(condition, mode='eval')): continue
        if entry: result.append(entry)
    return result


HELPER_PARENTS = {'Target_ESC_BloodPulse': 'Shout_ESC_xueyan_xuehai', 'Target_ESC_Counter2': 'Shout_ESC_taixuan_qinghui', 'Target_ESC_Counter3': 'Shout_ESC_taixuan_xinghe', 'Target_ESC_Resonance': 'Shout_ESC_xingge_zhangjian', 'Target_ESC_Aftershock': 'Projectile_ESC_tianqing_tianjian'}


class TaiqingPulseInstant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.targets = read_stats(DATA / 'Spell_Target.txt')
        cls.shouts = read_stats(DATA / 'Spell_Shout.txt')
        cls.pulse = cls.targets['Target_ESC_TaiqingPulse']['data']

    def test_display_name_is_the_actual_taiqing_skill(self):
        root = self.shouts['Shout_ESC_taixuan_taiqing']['data']
        self.assertTrue(self.pulse.get('DisplayName'))
        self.assertEqual(self.pulse['DisplayName'], root['DisplayName'])
        self.assertNotEqual(self.pulse['DisplayName'], 'hb049d4afgac1cg4172gab68g5266b799b6f6;1')

    def test_periodic_attack_has_no_caster_gesture_or_cast_sounds(self):
        self.assertEqual(self.pulse['SpellAnimation'], '')
        self.assertEqual(self.pulse['CastTextEvent'], 'Cast')
        self.assertEqual(set(self.pulse['SpellFlags'].split(';')),
                         {'IsSpell', 'IsHarmful', 'IgnoreSilence', 'ImmediateCast'})
        for field in ('PrepareEffect', 'CastEffect', 'PrepareSound', 'PrepareLoopSound',
                      'CastSound', 'TargetSound', 'VocalComponentSound'):
            with self.subTest(field=field):
                self.assertEqual(self.pulse[field], '')

    def test_each_sword_keeps_native_attack_damage_target_and_zero_cost(self):
        self.assertEqual(self.pulse['SpellType'], 'Target')
        self.assertEqual(self.pulse['SpellRoll'], 'Attack(AttackType.RangedSpellAttack)')
        self.assertEqual(self.pulse['SpellProperties'], '')
        self.assert_auto_attack('Target_ESC_TaiqingPulse')
        self.assertEqual(self.pulse['SpellFail'], '')
        self.assertEqual(self.pulse['TargetConditions'], 'Character() and Enemy() and not Dead()')
        self.assertEqual(self.pulse['AmountOfTargets'], '1')
        self.assertEqual(self.pulse['UseCosts'], '')
        self.assertEqual(self.pulse['Cooldown'], '')
        self.assertEqual(self.pulse['DamageType'], 'None')
        self.assertEqual(self.pulse['HitEffect'], '219f1b14-5372-5071-9d28-c74a315b9fb9')
        for field in ('SpellProperties', 'SpellSuccess', 'SpellFail'):
            self.assertNotIn('RegainHitPoints', self.pulse[field])

    def assert_auto_attack(self, name):
        data = self.targets[name]['data']
        dice, radius, hit = AUTO_HELPERS[name]
        self.assertEqual(self.targets[name]['using'], 'Target_HealingWord')
        self.assertEqual(data['SpellType'], 'Target')
        self.assertEqual(data['SpellRoll'], 'Attack(AttackType.RangedSpellAttack)')
        self.assertEqual(data['TargetRadius'], str(radius))
        self.assertEqual(data['TargetConditions'], 'Character() and Enemy() and not Dead()')
        for field in ('UseCosts','Cooldown','DualWieldingUseCosts','ContainerSpells',
                      'SpellProperties','SpellFail','SpellAnimation','PrepareEffect','CastEffect',
                      'PrepareSound','PrepareLoopSound','CastSound','TargetSound','VocalComponentSound'):
            self.assertEqual(data[field], '', (name, field))
        self.assertEqual(data['AmountOfTargets'], '1')
        self.assertEqual(data['HitEffect'], hit)
        self.assertEqual(data['DamageType'], 'None')
        self.assertEqual(set(data['SpellFlags'].split(';')),
                         {'IsSpell','IsHarmful','IgnoreSilence','ImmediateCast'})
        for main, off, force in itertools.product((False, True), repeat=3):
            flags = {flag for active, flag in ((main,'ESC_MAIN_SWORD'),
                    (off,'ESC_OFFHAND_SWORD'),(force,'ESC_FORCE_MODE')) if active}
            damage_type = 'Force' if name != 'Target_ESC_BloodPulse' or force else 'Necrotic'
            if main:
                base, functors = 'MainMeleeWeapon,MainMeleeWeaponDamageType', ['ExecuteWeaponFunctors(MainHand)']
            elif off:
                base, functors = 'OffhandMeleeWeapon,OffhandMeleeWeaponDamageType', ['ExecuteWeaponFunctors(OffHand)']
            else:
                base, functors = '2d6+WisdomModifier,' + damage_type, []
            expected = ['DealDamage(' + base + ',Magical)',
                        'DealDamage(' + dice + ',' + damage_type + ',Magical)',
                        'ApplyStatus(ESC_HIT_MARKER,100,0)'] + functors
            with self.subTest(helper=name, main=main, off=off, force=force):
                self.assertEqual(active_functors(data['SpellSuccess'], flags), expected)
                self.assertNotIn('RegainHitPoints', data['SpellSuccess'])

    def test_other_five_native_helpers_keep_their_rules(self):
        for name in AUTO_HELPERS:
            self.assert_auto_attack(name)
        # Landing aftershock has one unchanged pure 6d8 packet; AUTO must not
        # add a weapon, Wisdom or a second foundation to this separate effect.
        shock = self.targets['Target_ESC_Aftershock']['data']
        self.assertEqual(shock['SpellProperties'], 'DealDamage(6d8,Force,Magical)')
        self.assertEqual(shock['SpellRoll'], '')
        self.assertEqual(shock['SpellSuccess'], '')
        self.assertEqual(shock['SpellFail'], '')
        self.assertEqual(shock['UseCosts'], '')
        self.assertEqual(shock['Cooldown'], '')
        self.assertEqual(shock['TargetRadius'], '30')
        self.assertEqual(shock['TargetConditions'], 'Character() and Enemy() and not Dead()')
        self.assertEqual(shock['AmountOfTargets'], '1')
        self.assertEqual(shock['DamageType'], 'Force')
        self.assertEqual(shock['HitEffect'], '56be48fe-b34b-51c8-a977-b9eb5bc89f6e')

    def test_automatic_helpers_use_parent_names_and_no_caster_gesture(self):
        all_spells={}
        for path in DATA.glob('Spell_*.txt'):all_spells.update(read_stats(path))
        for name,parent in HELPER_PARENTS.items():
            with self.subTest(helper=name):
                data=self.targets[name]['data']
                self.assertEqual(data['DisplayName'],all_spells[parent]['data']['DisplayName'])
                self.assertEqual(set(data['SpellFlags'].split(';')),{'IsSpell','IsHarmful','IgnoreSilence','ImmediateCast'})
                self.assertEqual(data['CastTextEvent'],'Cast')
                for field in PRESENTATION_FIELDS-{'DisplayName','SpellFlags'}:self.assertEqual(data[field],'')
