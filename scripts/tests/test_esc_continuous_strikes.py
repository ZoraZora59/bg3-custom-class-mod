"""Continuous-strike contracts from generated native data.

This independent, deliberately limited model reads spell costs, variant boosts,
passive conditions and functors. It does not call spells_at or production Lua.
The payment snapshot models the native contract being requested; these tests
establish generated-data behavior, never Toolkit or client event ordering.
"""
import ast
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET


REPO = Path(__file__).resolve().parents[2]
MOD = REPO / 'mods/EasternSwordCultivator'
SPEC = json.loads((MOD / 'implementation-spec.json').read_text(encoding='utf-8'))
PUBLIC = MOD / 'Source/Public' / SPEC['folder']
DATA = PUBLIC / 'Stats/Generated/Data'
EVIDENCE_LAYER = 'independent generated native data model; not client validation'


def read_stats(paths):
    result = {}
    for path in paths:
        text = path.read_text(encoding='utf-8')
        for name, body in re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)', text, re.S):
            result[name] = dict(re.findall(r'^data "([^"]+)" "([^"]*)"$', body, re.M))
    return result


SPELLS = read_stats(sorted(DATA.glob('Spell_*.txt')))
PASSIVES = read_stats([DATA / 'Passive.txt'])
STATUSES = read_stats([DATA / 'Status_BOOST.txt'])
NAMED_KEYS = {row['stat']: key for key, row in SPEC['spells'].items()}


def spell_key(name):
    return NAMED_KEYS.get(name) or SPEC['aliases'].get(name, {}).get('key')


def costs(text):
    result = {}
    for token in filter(None, text.split(';')):
        resource, amount = token.split(':', 1)
        # Distance costs belong to movement helpers outside this model's scope.
        result[resource] = float(amount) if amount != 'Distance' else amount
    return result


def eligible_spells():
    result = set()
    for name, row in SPELLS.items():
        key = spell_key(name)
        definition = SPEC['spells'].get(key, {})
        alias = SPEC['aliases'].get(name, {})
        excluded = definition.get('internal') or any(alias.get(flag) for flag in
            ('internal', 'bonusOnly', 'continuation'))
        if definition.get('action') == 'sword' and not excluded and costs(row.get('UseCosts', '')).get('ActionPoint') == 1:
            result.add(name)
    return result


ELIGIBLE = eligible_spells()
RESOURCE_DEFINITIONS = ET.parse(PUBLIC / 'ActionResourceDefinitions/ActionResourceDefinitions.lsx')
OPPORTUNITY_DEFINITION = next(node for node in RESOURCE_DEFINITIONS.findall('.//node[@id="ActionResourceDefinition"]')
    if node.find("attribute[@id='Name']").get('value') == 'ESC_SwordOpportunity')
OPPORTUNITY_REPLENISH = OPPORTUNITY_DEFINITION.find("attribute[@id='ReplenishType']").get('value')
CAST_PASSIVES = {name: row for name, row in PASSIVES.items()
    if name.startswith('ESC_P_ContinuousCast_') or
       name == 'ESC_P_continuous_strikes' and 'OnCast' in row.get('StatsFunctorContext', '')}


def split_arguments(text):
    depth = 0
    quote = None
    start = 0
    result = []
    for index, char in enumerate(text):
        if quote:
            if char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        elif char == ',' and depth == 0:
            result.append(text[start:index].strip())
            start = index + 1
    result.append(text[start:].strip())
    return result


@dataclass
class Actor:
    level: int
    branch: str
    actions: int = 1
    yuan: int = 100
    bonus: int = 1
    opportunity: int = 0
    opportunity_capacity: int = 3
    turn_based: bool = True
    shield: bool = False
    medium: bool = False
    heavy: bool = False
    blocked: bool = False
    statuses: set = field(default_factory=set)
    restores: list = field(default_factory=list)

    @property
    def passives(self):
        result = {'ESC_P_Branch_' + self.branch}
        result.update('ESC_P_Level' + str(level) for level in (5, 10, 11) if self.level >= level)
        if self.level >= 5:
            result.add('ESC_P_continuous_strikes')
            result.update(CAST_PASSIVES)
        return result

    def amount(self, resource):
        return {'ActionPoint': self.actions, 'BonusActionPoint': self.bonus,
                'ESC_SwordYuan': self.yuan, 'ESC_SwordOpportunity': self.opportunity}.get(resource, 0)


class NativeDataModel:
    """Only documented constructs used by the generated continuous-strike data."""
    def __init__(self, actor, opportunity_replenish=OPPORTUNITY_REPLENISH):
        self.actor = actor
        self.opportunity_replenish = opportunity_replenish
        self.spell = None
        self.base_costs = {}
        self.paid_costs = {}

    def condition(self, expression):
        expression = expression.replace('context.HasContextFlag', 'HasContextFlag')
        expression = expression.replace('StatsFunctorContext.OnCast', "'OnCast'")
        expression = expression.replace('context.Source', "'source'").replace('context.Target', "'source'")
        expression = re.sub(r'\btrue\b', 'True', expression)
        expression = re.sub(r'\bfalse\b', 'False', expression)
        functions = {
            'HasContextFlag': lambda flag: flag == 'OnCast',
            'SpellId': lambda name, *args: name == self.spell,
            'HasUseCosts': lambda resource, modified=False, *args:
                (self.paid_costs if modified else self.base_costs).get(resource, 0) != 0,
            'TurnBased': lambda *args: self.actor.turn_based,
            'Tagged': lambda tag, *args: tag == 'EXTRA_ATTACK_BLOCKED' and self.actor.blocked,
            'HasPassive': lambda name, *args: name in self.actor.passives,
            'HasStatus': lambda name, *args: name in self.actor.statuses,
            'HasShieldEquipped': lambda *args: self.actor.shield,
            'HasMediumArmor': lambda *args: self.actor.medium,
            'HasHeavyArmor': lambda *args: self.actor.heavy,
            'HasActionResource': lambda resource, amount, *args: self.actor.amount(resource) >= amount,
            'ClassLevel': lambda *args: self.actor.level,
        }
        tree = ast.parse(expression, mode='eval')
        allowed = (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not,
                   ast.Compare, ast.Eq, ast.NotEq, ast.Gt, ast.GtE, ast.Lt, ast.LtE,
                   ast.Call, ast.Name, ast.Load, ast.Constant)
        for node in ast.walk(tree):
            if not isinstance(node, allowed):
                raise AssertionError('Unsupported native condition construct: ' + ast.dump(node))
            if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id not in functions):
                raise AssertionError('Unsupported native condition function: ' + ast.dump(node))
        return bool(eval(compile(tree, '<generated native condition>', 'eval'), {'__builtins__': {}}, functions))

    def functors(self, text):
        for command in filter(None, (part.strip() for part in text.split(';'))):
            if command.startswith('IF('):
                match = re.fullmatch(r'IF\((.*)\):(\w+\(.*\))', command)
                if not match:
                    raise AssertionError('Unsupported conditional functor: ' + command)
                if not self.condition(match[1]):
                    continue
                command = match[2]
            match = re.fullmatch(r'(\w+)\((.*)\)', command)
            if not match:
                raise AssertionError('Unsupported native functor: ' + command)
            function, text_args = match.groups()
            args = split_arguments(text_args)
            if function == 'RestoreResource':
                if args[0] == 'SELF':
                    args = args[1:]
                if args[0] != 'ESC_SwordOpportunity' or args[2] != '0':
                    raise AssertionError('Unexpected resource restoration: ' + command)
                amount = int(args[1])
                # Official RestoreResource does not increase maximum. The
                # first live round passed with Never, but native costs reduced
                # its MaxAmount to zero and the next paid action restored none.
                self.actor.opportunity = min(self.actor.opportunity_capacity, self.actor.opportunity + amount)
                self.actor.restores.append(amount)
            elif function == 'UseActionResource':
                if args[0] == 'SELF':
                    args = args[1:]
                if args != ['ESC_SwordOpportunity', '100%', '0']:
                    raise AssertionError('Unexpected opportunity reset: ' + command)
                self.spend_opportunity(self.actor.opportunity)
            elif function == 'ApplyStatus':
                if args[0] == 'SELF':
                    args = args[1:]
                name = args[0]
                self.actor.statuses.add(name)
                self.functors(STATUSES[name].get('OnApplyFunctors', ''))
            elif function == 'RemoveStatus':
                self.remove_status(args[-1])
            else:
                raise AssertionError('Unsupported native functor: ' + command)

    def remove_status(self, name):
        if name in self.actor.statuses:
            self.actor.statuses.remove(name)
            self.functors(STATUSES[name].get('OnRemoveFunctors', ''))

    def spend_opportunity(self, amount):
        self.actor.opportunity -= amount
        if self.opportunity_replenish == 'Never':
            self.actor.opportunity_capacity = max(0, self.actor.opportunity_capacity - amount)

    def selected_costs(self, spell):
        self.spell = spell
        self.base_costs = costs(SPELLS[spell].get('UseCosts', ''))
        result = dict(self.base_costs)
        for name in sorted(self.actor.statuses):
            for boost in filter(None, STATUSES[name].get('Boosts', '').split(';')):
                if boost.startswith('IF('):
                    match=re.fullmatch(r'IF\((.*)\):(UnlockSpellVariant\(.*\))',boost)
                    if not match:
                        raise AssertionError('Unsupported conditional opportunity boost: '+boost)
                    if not self.condition(match[1]):
                        continue
                    boost=match[2]
                if not boost.startswith('UnlockSpellVariant('):
                    raise AssertionError('Unsupported opportunity boost: ' + boost)
                args = split_arguments(boost[len('UnlockSpellVariant('):-1])
                if not self.condition(args[0]):
                    continue
                for modifier in args[1:]:
                    if modifier == 'ModifyIconGlow()':
                        continue
                    match = re.fullmatch(r'ModifyUseCosts\((.*)\)', modifier)
                    if not match:
                        raise AssertionError('Unsupported native variant modifier: ' + modifier)
                    operation, new_resource, amount, level, old_resource = split_arguments(match[1])
                    if operation != 'Replace' or level != '0':
                        raise AssertionError('Unsupported cost operation: ' + modifier)
                    if old_resource in result:
                        result.pop(old_resource)
                        result[new_resource] = float(amount)
        return result

    def cast(self, spell, fail=False):
        # Capture selected, modified costs before payment and keep that snapshot
        # for OnCast, including after the last opportunity reaches zero.
        selected = self.selected_costs(spell)
        if fail or any(not isinstance(amount, (int, float)) or self.actor.amount(resource) < amount
                       for resource, amount in selected.items()):
            return False
        self.paid_costs = dict(selected)
        for resource, amount in selected.items():
            attribute = {'ActionPoint': 'actions', 'BonusActionPoint': 'bonus',
                         'ESC_SwordYuan': 'yuan', 'ESC_SwordOpportunity': 'opportunity'}[resource]
            if resource == 'ESC_SwordOpportunity':
                self.spend_opportunity(amount)
            else:
                setattr(self.actor, attribute, getattr(self.actor, attribute) - amount)
        if self.actor.level >= 5:
            for row in CAST_PASSIVES.values():
                if self.condition(row['Conditions']):
                    self.functors(row['StatsFunctors'])
        for name in sorted(self.actor.statuses.copy()):
            row = STATUSES[name]
            if 'OnSpellCast' in row.get('RemoveEvents', '').split(';') and self.condition(row['RemoveConditions']):
                self.remove_status(name)
        return True


class ContinuousStrikes(unittest.TestCase):
    def test_generator_uses_only_native_single_spell_variant_selectors_with_outer_actor_gate(self):
        # Exercise the pure generator helper without generating source assets.
        # Vanilla SpellId and outer IF forms are checked separately; this does
        # not substitute for Toolkit's full boost parser and event ordering.
        source=(REPO/'scripts/generate-sword-cultivator.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        names={'equipment_condition','continuous_variant_boost'}
        definitions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
        self.assertEqual({node.name for node in definitions},names)
        namespace={}
        exec(compile(ast.Module(body=definitions,type_ignores=[]),'<generator helpers>','exec'),namespace)
        spells=['Target_ESC_sword_strike_Main','Projectile_ESC_yujian_Main']
        boosts=namespace['continuous_variant_boost'](spells).split(';')
        self.assertEqual(len(boosts),len(spells))
        for spell,boost in zip(spells,boosts):
            gate,variant=re.fullmatch(r'IF\((.*)\):(UnlockSpellVariant\(.*\))',boost).groups()
            self.assertIn('TurnBased(context.Source)',gate)
            self.assertIn("Tagged('EXTRA_ATTACK_BLOCKED',context.Source)",gate)
            self.assertIn('HasShieldEquipped(context.Source)',gate)
            args=split_arguments(variant[len('UnlockSpellVariant('):-1])
            self.assertEqual(args,[f"SpellId('{spell}')",'ModifyUseCosts(Replace,ESC_SwordOpportunity,1,0,ActionPoint)','ModifyIconGlow()'])
        constants=[node for node in tree.body if isinstance(node,ast.Assign)
                   and any(isinstance(target,ast.Name) and target.id=='CONTINUOUS_VARIANT_GROUP_SIZE' for target in node.targets)]
        self.assertEqual(len(constants),1)
        group_size=ast.literal_eval(constants[0].value)
        for offset in range(0,len(ELIGIBLE),group_size):
            group=namespace['continuous_variant_boost'](sorted(ELIGIBLE)[offset:offset+group_size])
            self.assertLessEqual(len(group.encode('utf-8')),2048)

    def test_generator_cleanup_covers_all_single_spell_variant_groups_and_legacy_groups(self):
        tree=ast.parse((REPO/'scripts/generate-sword-cultivator.py').read_text(encoding='utf-8'))
        definitions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='opportunity_statuses']
        constant=next(node for node in tree.body if isinstance(node,ast.Assign)
                      and any(isinstance(target,ast.Name) and target.id=='CONTINUOUS_VARIANT_GROUP_SIZE' for target in node.targets))
        size=ast.literal_eval(constant.value)
        namespace={'math':math,'SPELLS':SPEC['spells'],'aliases':SPEC['aliases'],
                   'spellid':lambda key:SPEC['spells'][key]['stat'],
                   'sword_action_spells':lambda:sorted(ELIGIBLE),'CONTINUOUS_VARIANT_GROUP_SIZE':size}
        exec(compile(ast.Module(body=definitions,type_ignores=[]),'<generator cleanup>','exec'),namespace)
        statuses=namespace['opportunity_statuses']()
        groups=math.ceil(len(ELIGIBLE)/size)
        self.assertGreaterEqual(len(statuses),groups)
        self.assertEqual(statuses[:groups],[f'ESC_EXTRA_ATTACK_{index}' for index in range(groups)])
        # Groups created by older saved progression/variants must still be
        # cleared even when an earlier container-only group is now unused.
        self.assertTrue(set(SPEC['opportunityStatuses'])<=set(statuses))

    def spell(self, key):
        return next(name for name in sorted(ELIGIBLE) if spell_key(name) == key)

    def normal(self, branch):
        return self.spell({'taixuan': 'taixuan_zhaoxi', 'tianqing': 'tianqing_nifeng',
                           'xueyan': 'xueyan_luexue', 'xingge': 'xingge_wenlu'}[branch])

    def test_native_trigger_whitelist_matches_executable_action_costs(self):
        self.assertTrue(CAST_PASSIVES)
        actual = []
        for name, row in CAST_PASSIVES.items():
            group = re.findall(r"SpellId\('([^']+)'", row['Conditions'])
            self.assertGreater(len(group), 0, name)
            self.assertLessEqual(len(group), 12, name)
            actual.extend(group)
            self.assertIn('OnCast', row['StatsFunctorContext'], name)
            self.assertIn("HasUseCosts('ActionPoint',true)", row['Conditions'].replace(' ', ''), name)
            self.assertIn('TurnBased(', row['Conditions'], name)
            self.assertIn('EXTRA_ATTACK_BLOCKED', row['Conditions'], name)
            self.assertIn('HasShieldEquipped(', row['Conditions'], name)
        self.assertEqual(set(actual), ELIGIBLE)
        self.assertEqual(len(actual), len(set(actual)), 'A cast must match one grant group')
        self.assertNotIn('Target_MainHandAttack', actual)

    def test_counts_follow_class_level_and_branch_until_the_last_charge(self):
        for branch in ('taixuan', 'tianqing', 'xueyan', 'xingge'):
            for level, expected in ((4, 1), (5, 2 if branch == 'xingge' else 3),
                                    (9, 2 if branch == 'xingge' else 3),
                                    (10, 2 if branch == 'xingge' else 4),
                                    (12, 2 if branch == 'xingge' else 4)):
                with self.subTest(branch=branch, level=level):
                    actor = Actor(level, branch)
                    model = NativeDataModel(actor)
                    for _ in range(expected):
                        self.assertTrue(model.cast(self.normal(branch)))
                    self.assertEqual(actor.actions, 0)
                    self.assertEqual(actor.opportunity, 0)
                    self.assertFalse(model.cast(self.normal(branch)))
                    self.assertNotIn('ESC_EXTRA_ATTACK', actor.statuses)
                    self.assertEqual(actor.restores, [] if level < 5 else [expected - 1])

    def test_each_additional_complete_action_opens_one_additional_set(self):
        actor = Actor(10, 'taixuan', actions=2)
        model = NativeDataModel(actor)
        for _ in range(8):
            self.assertTrue(model.cast(self.normal('taixuan')))
        self.assertEqual((actor.actions, actor.opportunity), (0, 0))
        self.assertEqual(actor.restores, [3, 3])
        self.assertFalse(model.cast(self.normal('taixuan')))

    def test_exhausted_first_round_does_not_destroy_capacity_for_later_paid_rounds(self):
        actor = Actor(10, 'tianqing')
        model = NativeDataModel(actor)
        for _ in range(3):
            self.assertEqual((actor.opportunity, actor.opportunity_capacity), (0, 3))
            for _ in range(4):
                self.assertTrue(model.cast(self.normal('tianqing')))
            self.assertEqual((actor.actions, actor.opportunity, actor.opportunity_capacity), (0, 0, 3))
            self.assertFalse(model.cast(self.normal('tianqing')))
            # Next turn only replenishes the full action. Opportunity remains
            # empty until the generated OnCast sees that action actually paid.
            actor.actions = 1
        self.assertEqual(actor.restores, [3, 3, 3])

    def test_previous_never_definition_replays_observed_second_round_capacity_failure(self):
        # This replay records the actual candidate's native Never capacity
        # behavior. It documents the old model omission, not client acceptance.
        actor = Actor(10, 'tianqing')
        model = NativeDataModel(actor, opportunity_replenish='Never')
        for _ in range(4):
            self.assertTrue(model.cast(self.normal('tianqing')))
        self.assertEqual((actor.opportunity, actor.opportunity_capacity), (0, 0))
        actor.actions = 1
        self.assertTrue(model.cast(self.normal('tianqing')))
        self.assertEqual((actor.actions, actor.opportunity, actor.opportunity_capacity), (0, 0, 0))
        self.assertFalse(model.cast(self.normal('tianqing')))

    def test_rest_balance_does_not_unlock_free_first_cast_or_inflate_lower_rank_grant(self):
        for branch, level, count in (('xingge', 5, 2), ('taixuan', 5, 3), ('tianqing', 10, 4)):
            with self.subTest(branch=branch, level=level):
                actor = Actor(level, branch, opportunity=3)
                model = NativeDataModel(actor)
                # FullRest may fill the hidden resource. It grants no variant
                # status, and the paid action drains it before restoring rank.
                self.assertEqual(model.selected_costs(self.normal(branch)), {'ActionPoint': 1})
                self.assertTrue(model.cast(self.normal(branch)))
                self.assertEqual((actor.actions, actor.opportunity), (0, count - 1))
                self.assertEqual(actor.opportunity_capacity, 3)
                for _ in range(count - 1):
                    self.assertTrue(model.cast(self.normal(branch)))
                self.assertFalse(model.cast(self.normal(branch)))

    def test_opportunity_replacement_preserves_independent_yuan_cost(self):
        actor = Actor(6, 'xueyan', yuan=12)
        model = NativeDataModel(actor)
        spell = self.spell('xueyan_chuanshen')
        for expected_yuan in (8, 4, 0):
            self.assertTrue(model.cast(spell))
            self.assertEqual(actor.yuan, expected_yuan)
        self.assertEqual((actor.actions, actor.opportunity), (0, 0))
        self.assertFalse(model.cast(spell))
        self.assertEqual(actor.restores, [2])

    def test_failed_selection_and_insufficient_yuan_do_not_restore_opportunities(self):
        actor = Actor(6, 'xueyan', yuan=3)
        model = NativeDataModel(actor)
        self.assertFalse(model.cast(self.spell('xueyan_chuanshen')))
        self.assertFalse(model.cast(self.normal('xueyan'), fail=True))
        self.assertEqual((actor.actions, actor.opportunity, actor.yuan), (1, 0, 3))
        self.assertEqual(actor.restores, [])
        self.assertTrue(model.cast(self.normal('xueyan')))
        self.assertFalse(model.cast(self.normal('xueyan'), fail=True))
        self.assertEqual(actor.opportunity, 2)
        self.assertEqual(actor.restores, [2])

    def test_multistage_helpers_are_free_and_do_not_open_or_consume_a_set(self):
        actor = Actor(6, 'taixuan')
        model = NativeDataModel(actor)
        self.assertTrue(model.cast(self.spell('taixuan_liuguang')))
        self.assertEqual((actor.actions, actor.opportunity, actor.yuan), (0, 2, 90))
        for _ in range(3):
            self.assertTrue(model.cast('Target_ESC_LiuguangStage'))
        self.assertEqual((actor.actions, actor.opportunity, actor.yuan), (0, 2, 90))
        self.assertEqual(actor.restores, [2])

    def test_bonus_free_containers_and_continuations_never_start_a_set(self):
        excluded = [name for name, alias in SPEC['aliases'].items()
                    if alias.get('bonusOnly') or alias.get('continuation')]
        excluded += [name for name, row in SPELLS.items()
                     if row.get('ContainerSpells') and row.get('UseCosts', '') == '']
        self.assertTrue(excluded)
        for spell in excluded:
            with self.subTest(spell=spell):
                actor = Actor(12, 'xueyan')
                model = NativeDataModel(actor)
                self.assertTrue(model.cast(spell))
                self.assertEqual(actor.opportunity, 0)
                self.assertEqual(actor.restores, [])
                self.assertEqual(actor.actions, 1)

    def test_turn_equipment_and_native_block_gates_do_not_grant_a_set(self):
        for actor in (Actor(10, 'taixuan', turn_based=False), Actor(10, 'taixuan', shield=True),
                      Actor(10, 'taixuan', medium=True), Actor(10, 'xingge', heavy=True),
                      Actor(10, 'xueyan', blocked=True)):
            with self.subTest(actor=actor):
                model = NativeDataModel(actor)
                self.assertTrue(model.cast(self.normal(actor.branch)))
                self.assertEqual(actor.opportunity, 0)
                self.assertEqual(actor.restores, [])

    def test_native_status_lifetime_and_resource_do_not_replenish_each_turn(self):
        row = STATUSES['ESC_EXTRA_ATTACK']
        self.assertEqual(row['TickType'], 'StartTurn')
        self.assertIn('OnSpellCast', row['RemoveEvents'].split(';'))
        self.assertIn("HasActionResource('ESC_SwordOpportunity'", row['RemoveConditions'])
        self.assertIn('context.Target', row['RemoveConditions'])
        actor = Actor(10, 'taixuan')
        model = NativeDataModel(actor)
        self.assertTrue(model.cast(self.normal('taixuan')))
        groups = actor.statuses - {'ESC_EXTRA_ATTACK'}
        self.assertTrue(groups)
        for name in groups:
            boost = STATUSES[name]['Boosts']
            self.assertIn('ModifyUseCosts(Replace,ESC_SwordOpportunity,1,0,ActionPoint)', boost)
            self.assertIn('ModifyIconGlow()', boost)
            self.assertNotIn('HasActionResource', boost, 'Do not reselect costs when the final charge is spent')
        model.remove_status('ESC_EXTRA_ATTACK')
        self.assertFalse(groups & actor.statuses)
        definitions = ET.parse(PUBLIC / 'ActionResourceDefinitions/ActionResourceDefinitions.lsx')
        resource = next(node for node in definitions.findall('.//node[@id="ActionResourceDefinition"]')
                        if node.find("attribute[@id='Name']").get('value') == 'ESC_SwordOpportunity')
        self.assertEqual(resource.find("attribute[@id='ReplenishType']").get('value'), 'FullRest')
        for name, passive in CAST_PASSIVES.items():
            functors = passive['StatsFunctors'].split(';')
            self.assertEqual(functors[0], 'UseActionResource(SELF,ESC_SwordOpportunity,100%,0)', name)
            self.assertTrue(all('RestoreResource' in functor for functor in functors[1:-1]), name)
            self.assertEqual(functors[-1], 'ApplyStatus(SELF,ESC_EXTRA_ATTACK,100,1)', name)
        runtime = (MOD / 'Source/Mods' / SPEC['folder'] / 'ScriptExtender/Lua/Runtime.lua').read_text(encoding='utf-8')
        self.assertNotIn('usedOpportunity', runtime)
        self.assertNotIn('R.opportunities(', runtime)
        self.assertNotIn('E.setResource(id,spec.opportunityResource', runtime)


if __name__ == '__main__':
    print('Evidence layer:', EVIDENCE_LAYER)
    unittest.main(verbosity=2)
