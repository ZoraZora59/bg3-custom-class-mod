"""Generate the formal mod from the confirmed design and original art.

UTF-8 throughout; stable UUIDs; never writes into the user's game installation.
The game bridge is maintained separately under the module's ScriptExtender/Lua.
"""
import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image
from sword_spell_presentation import present_spell
from sword_vfx_bindings import PHASES, STYLES, effect_name, set_enabled_phases
from sword_vfx_resources import generate_resources as generate_vfx_resources
from sword_tooltips import LEVEL_MAPS, spell_tooltip
from sword_cultivator_spec import (
    BRANCHES, BRANCH_DESCRIPTIONS, CAPACITIES, CLASS_DESCRIPTION, FOLDER,
    HIT_CONTROLS, MOD, MODULE_UUID, PASSIVES, PUBLISH_HANDLE, SPELLS, VERSION64, guid, spells_at,
)

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / 'mods' / MOD
SOURCE = ROOT / 'Source'
PUBLIC = SOURCE / 'Public' / FOLDER
MODULE = SOURCE / 'Mods' / FOLDER
ART = REPO / 'art/static-v1'
manifest = json.loads((ART / 'manifest.json').read_text(encoding='utf-8'))
assets = {a['id']: a for a in manifest['assets']}
loca = {}
aliases = {}
PLAYER_TEXT = json.loads((REPO / 'scripts/sword_player_text.json').read_text(encoding='utf-8'))
QI_CONDITION = "HasStatus('ESC_QI_MODE',context.Source) and (HasPassive('ESC_P_Branch_taixuan',context.Source) or HasPassive('ESC_P_Branch_xueyan',context.Source))"
SWORD_PROFICIENCIES = 'Longswords|Shortswords|Greatswords|Rapiers|Scimitars'


def sword_condition(hand):
    # Shillelagh uses these fixed melee slots, independently of the active set.
    slot = 'MeleeMainHand' if hand == 'Main' else 'MeleeOffHand'
    return f"IsWeaponOfProficiencyGroup('{SWORD_PROFICIENCIES}', GetItemInEquipmentSlot(EquipmentSlot.{slot}, context.Source))"


def equipment_condition():
    # Native Bladesong helpers; only Taixuan and Xingge forbid medium/heavy armor.
    return ("not HasShieldEquipped(context.Source) and "
            "((not HasPassive('ESC_P_Branch_taixuan',context.Source) and "
            "not HasPassive('ESC_P_Branch_xingge',context.Source)) or "
            "(not HasHeavyArmor(context.Source) and not HasMediumArmor(context.Source)))")


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


def handle(key, chinese, english=None):
    h = 'h' + guid('loca/' + key).replace('-', 'g')
    loca[h] = (chinese, english or (loca[h][1] if h in loca else chinese))
    return h


def attr(node, name, typ, value):
    values = dict(id=name, type=typ)
    if typ == 'TranslatedString':
        values.update(handle=value, version='1')
    else:
        values['value'] = str(value).lower() if isinstance(value, bool) else str(value)
    ET.SubElement(node, 'attribute', **values)


def document(region):
    root = ET.Element('save')
    ET.SubElement(root, 'version', major='4', minor='8', revision='0', build='500')
    children = ET.SubElement(ET.SubElement(ET.SubElement(root, 'region', id=region), 'node', id='root'), 'children')
    return root, children


def xml(path, root):
    ET.indent(root, space='    ')
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def entry(name, typ, values, using=None):
    if typ == 'SpellData':
        conditions = values.get('RequirementConditions', '')
        events = values.get('RequirementEvents', '').split(';') if values.get('RequirementEvents') else []
        if any(condition in conditions for condition in (
                'IsWeaponOfProficiencyGroup(', 'HasShieldEquipped(', 'HasHeavyArmor(', 'HasMediumArmor(')):
            events.extend(('OnEquip', 'OnUnequip'))
        if 'HasStatus(' in conditions:
            # Native Target_Dig explicitly listens for both status transitions.
            events.extend(('OnStatusApplied', 'OnStatusRemoved'))
        if events:
            values = dict(values)
            values['RequirementEvents'] = ';'.join(dict.fromkeys(events))
        values = present_spell(name, values, using)
    lines = [f'new entry "{name}"', f'type "{typ}"']
    if using:
        lines.append(f'using "{using}"')
    for key, value in values.items():
        if len(str(value).encode('utf-8')) > 2048:
            raise ValueError(f'BG3 GSTNodeStorage limit exceeded: {name}.{key}')
        if '"' in str(value) or '\n' in str(value):
            raise ValueError((key, value))
        lines.append(f'data "{key}" "{value}"')
    return '\n'.join(lines) + '\n\n'


def icon(asset):
    return 'ESC_' + asset


def spellid(key):
    # All buttons are native spells; scripted effects can be tracked by this ID.
    kind = SPELLS[key]['kind']
    if key == 'sword_flight': return 'Shout_ESC_sword_flight'
    if key == 'xueyan_liancheng': return 'Shout_ESC_xueyan_liancheng'
    if key == 'tianqing_tianbeng': return 'Target_ESC_tianqing_tianbeng'
    if kind=='dash_attack': return f'Rush_ESC_{key}'
    if key=='tianqing_tianjian': return 'Projectile_ESC_tianqing_tianjian'
    prefix = ('Projectile' if kind in ('attack', 'chain_attack', 'cooperate', 'flight') and key != 'sword_strike'
              else 'Target' if kind in ('heal', 'protect', 'release', 'focus', 'rescue', 'recall') or key == 'sword_strike'
              else 'Target' if kind in ('area_attack', 'area_save', 'leap_area_save')
              else 'Zone' if kind in ('cone_attack', 'dash_attack', 'piercing_line')
              else 'Shout')
    return f'{prefix}_ESC_{key}'


def player_text(name):
    text = (REPO / 'docs/21-player-facing-skill-text-draft.md').read_text(encoding='utf-8')
    # Inline branch entries include their full rules in one paragraph.
    match = re.search(r'^\*\*' + re.escape(name) + r'[^\n]*\*\*：(.*)$', text, re.M)
    if match:
        return match.group(1).strip()
    match = re.search(r'^### ' + re.escape(name) + r'[^\n]*\n(.*?)(?=\n##|\Z)', text, re.M | re.S)
    if match:
        body = re.sub(r'^- ', '', match.group(1).strip(), flags=re.M)
        return re.sub(r'\n+', '<br>', body)
    return ''


def generate_meta():
    template = REPO / 'mods/SkeletonToolkitTest/Source/Mods/SkeletonToolkitTest_1226413d-5cb8-f80e-10bc-2fe4417c83a1/meta.lsx'
    root = ET.parse(template).getroot()
    info = root.find(".//node[@id='ModuleInfo']")
    values = dict(Folder=FOLDER, Name=MOD, UUID=MODULE_UUID, Version64=str(VERSION64),
                  PublishHandle=str(PUBLISH_HANDLE),
                  Author='Zora', Description='东方剑修：一脉四途，1—12级职业与原创静态美术。需要 BG3 Script Extender。',
                  MD5='')
    for a in info.findall('attribute'):
        if a.get('id') in values:
            a.set('value', values[a.get('id')])
    # Publishing metadata belongs to Toolkit; don't carry the test project's signature.
    for child in list(info):
        if child.tag == 'children':
            info.remove(child)
    xml(MODULE / 'meta.lsx', root)
    p, rows = document('MetaData')
    parent = p.find('.//node')
    for key, value in dict(GameProject='', Module=MODULE_UUID, Name=MOD, UUID=guid('project')).items():
        attr(parent, key, 'LSString', value)
    attr(parent, 'UpdatedDependencies', 'bool', True)
    xml(SOURCE / 'Projects' / FOLDER / 'meta.lsx', p)
    write(MODULE / 'ScriptExtender/Config.json', json.dumps(dict(RequiredVersion=32, ModTable='ESC', FeatureFlags=['Lua']), indent=2) + '\n')


def generate_classes():
    root, rows = document('ClassDescriptions')
    for key in ['common', *BRANCHES]:
        n = ET.SubElement(rows, 'node', id='ClassDescription')
        name = MOD if key == 'common' else 'ESC_' + BRANCHES[key]['english']
        display = '东方剑修' if key == 'common' else BRANCHES[key]['name']
        description = CLASS_DESCRIPTION if key == 'common' else BRANCH_DESCRIPTIONS[key]
        values = dict(Name=('FixedString', name), UUID=('guid', guid('class/' + key)),
                      ProgressionTableUUID=('guid', guid('table/' + key)),
                      DisplayName=('TranslatedString', handle('class/' + key, display, 'Eastern Sword Cultivator' if key == 'common' else BRANCHES[key]['english'])),
                      Description=('TranslatedString', handle('class/' + key + '/description', description)),
                      PrimaryAbility=('uint8', 5), SpellCastingAbility=('uint8', 5), LearningStrategy=('uint8', 1),
                      SoundClassType=('FixedString', 'Fighter'),
                      CharacterCreationPose=('guid', '0f07ec6e-4ef0-434e-9a51-1353260ccff8'))
        if key == 'common':
            values.update(BaseHp=('int32', 10), HpPerLevel=('int32', 6), ClassEquipment=('FixedString', 'EQP_CC_ESC'),
                          ClassHotbarColumns=('int32', 5), CommonHotbarColumns=('int32', 9), ItemsHotbarColumns=('int32', 2))
        else:
            values['ParentGuid'] = ('guid', guid('class/common'))
            values['ShortName'] = values['DisplayName']
        for field, (typ, value) in values.items():
            attr(n, field, typ, value)
    xml(PUBLIC / 'ClassDescriptions/ClassDescriptions.lsx', root)
    root, rows = document('AbilityDistributionPresets')
    for branch in ['common', *BRANCHES]:
        n = ET.SubElement(rows, 'node', id='AbilityDistributionPreset')
        attr(n, 'UUID', 'guid', guid('ability-preset/' + branch))
        attr(n, 'ClassUUID', 'guid', guid('class/' + branch))
        # A legal 27-point recommendation; racial bonuses remain native choices.
        for ability, score in dict(Strength=8,Dexterity=14,Constitution=15,Intelligence=8,Wisdom=15,Charisma=10).items():
            attr(n, ability, 'int32', score)
    xml(PUBLIC / 'CharacterCreationPresets/AbilityDistributionPresets.lsx', root)
    root, rows = document('DefaultValues')
    n = ET.SubElement(rows, 'node', id='DefaultValue')
    for field, typ, value in [('UUID','guid',guid('default-skills')),('TableUUID','guid',guid('table/common')),('Level','int32',1),('Add','LSString','Insight;Perception;Athletics;Acrobatics;Survival;Medicine;Intimidation')]:
        attr(n, field, typ, value)
    xml(PUBLIC / 'DefaultValues/Skills.lsx', root)


def generate_progression_descriptions():
    # Native classes register their name against the progression TABLE here.
    # Without this row, CC's ClassProgression omits weapon/armour details even
    # when the mechanical proficiency Boosts are present in Progressions.
    root, rows = document('ProgressionDescriptions')
    for key in ['common', *BRANCHES]:
        n = ET.SubElement(rows, 'node', id='ProgressionDescription')
        name = MOD if key == 'common' else 'ESC_' + BRANCHES[key]['english']
        display = '东方剑修' if key == 'common' else BRANCHES[key]['name']
        description = CLASS_DESCRIPTION if key == 'common' else BRANCH_DESCRIPTIONS[key]
        attr(n, 'UUID', 'guid', guid('progression-description/' + key))
        attr(n, 'Type', 'FixedString', name)
        attr(n, 'ProgressionTableId', 'guid', guid('table/' + key))
        attr(n, 'Hidden', 'bool', False)
        attr(n, 'DisplayName', 'TranslatedString', handle('class/' + key, display))
        attr(n, 'Description', 'TranslatedString', handle('class/' + key + '/description', description))
    xml(PUBLIC / 'Progressions/ProgressionDescriptions.lsx', root)


def generate_progressions():
    root, rows = document('Progressions')
    spell_root, spell_rows = document('SpellLists')
    for branch in ['common', *BRANCHES]:
        levels = range(1, 13) if branch == 'common' else range(3, 13)
        for level in levels:
            n = ET.SubElement(rows, 'node', id='Progression')
            for field, typ, value in [('UUID', 'guid', guid(f'progression/{branch}/{level}')),
                                      ('TableUUID', 'guid', guid('table/' + branch)),
                                      ('Name', 'LSString', MOD if branch == 'common' else 'ESC_' + BRANCHES[branch]['english']),
                                      ('Level', 'uint8', level), ('ProgressionType', 'uint8', 0 if branch == 'common' else 1)]:
                attr(n, field, typ, value)
            boosts = []
            if branch == 'common':
                if level == 1:
                    boosts += ['Proficiency(LightArmor)', *[f'Proficiency({weapon})' for weapon in ['Longswords', 'Shortswords', 'Greatswords', 'Rapiers', 'Scimitars']],
                               'ProficiencyBonus(SavingThrow,Wisdom)', 'ProficiencyBonus(SavingThrow,Constitution)']
                    attr(n, 'Selectors', 'LSString', f'SelectSkills({guid("skills")},2)')
                if level == 5:
                    boosts.append('ActionResource(ESC_SwordOpportunity,3,0)')
                if level >= 2:
                    delta = CAPACITIES[level - 1] - CAPACITIES[level - 2]
                    boosts.append(f'ActionResource(ESC_SwordYuan,{delta},0)')
                if level in (4, 8, 12):
                    attr(n, 'AllowImprovement', 'bool', True)
                if level == 3:
                    subrows = ET.SubElement(ET.SubElement(ET.SubElement(n, 'children'), 'node', id='SubClasses'), 'children')
                    for b in BRANCHES:
                        attr(ET.SubElement(subrows, 'node', id='SubClass'), 'Object', 'guid', guid('class/' + b))
            elif level == 3 and branch in ('tianqing', 'xueyan'):
                boosts.extend(['Proficiency(MediumArmor)', 'Proficiency(HeavyArmor)'])
            if branch in ('tianqing', 'xingge') and level == 4:
                key = 'tianqing_nixi' if branch == 'tianqing' else 'xingge_xiangfu'
                cost = 10 if branch == 'tianqing' else 6
                boosts.append(f"UnlockSpellVariant(SpellId('{spellid(key)}'),ModifyUseCosts(Replace,ESC_SwordYuan,{cost},0,ESC_SwordYuan))")
            new_spells=[spellid(key) for key in spells_at(branch,level) if key!='yujian']
            if branch=='common' and level==5:
                boosts += ['ActionResource(ESC_FlightMovement,24,0)','ActionResource(ESC_ChainMovement,6,0)']
            if new_spells:
                list_uuid=guid(f'spelllist/{branch}/{level}')
                spell_list=ET.SubElement(spell_rows,'node',id='SpellList')
                attr(spell_list,'Name','FixedString',f'ESC_SpellLists_{len(spell_rows)-1}')
                attr(spell_list,'UUID','guid',list_uuid)
                attr(spell_list,'Spells','LSString',';'.join(new_spells))
                selector=n.find("attribute[@id='Selectors']")
                addition=f'AddSpells({list_uuid},,,,AlwaysPrepared)'
                if selector is not None: selector.set('value',selector.get('value')+';'+addition)
                else: attr(n,'Selectors','LSString',addition)
            passives = [f'ESC_P_{key}' for key, (at, group) in PASSIVES.items()
                        if at == level and (group == branch or group == 'solo' and branch in ('taixuan', 'tianqing', 'xueyan'))]
            if branch == 'common' and level == 1:
                passives.extend(['ESC_P_StarterSword','ESC_P_StarterMelee'])
            if branch == 'common' and level == 2:
                passives.append('ESC_P_StarterGuard')
            if branch == 'taixuan' and level == 4:
                attr(n, 'PassivesRemoved', 'LSString', 'ESC_P_StarterGuard')
            if branch == 'common' and level in (5, 10, 11):
                passives.append(f'ESC_P_Level{level}')
            if branch != 'common' and level == 3:
                passives.append('ESC_P_Branch_' + branch)
                attr(n, 'PassivesRemoved', 'LSString', 'ESC_P_StarterSword;ESC_P_StarterMelee')
            if boosts:
                attr(n, 'Boosts', 'LSString', ';'.join(boosts))
            if passives:
                attr(n, 'PassivesAdded', 'LSString', ';'.join(passives))
    # A separate multiclass entry omits starting saving throws, equipment and skill picks.
    normal = rows.find("node/attribute[@id='Level'][@value='1']/..")
    multiclass = ET.fromstring(ET.tostring(normal))
    for a in multiclass.findall('attribute'):
        if a.get('id') == 'UUID':
            a.set('value', guid('progression/common/multiclass'))
        elif a.get('id') == 'Boosts':
            a.set('value', ';'.join(x for x in a.get('value').split(';') if 'SavingThrow' not in x))
        elif a.get('id') == 'Selectors':
            multiclass.remove(a)
    attr(multiclass, 'IsMulticlass', 'bool', True)
    rows.append(multiclass)
    xml(PUBLIC / 'Progressions/Progressions.lsx', root)
    xml(PUBLIC / 'Lists/SpellLists.lsx',spell_root)
    root, rows = document('SkillLists')
    n = ET.SubElement(rows, 'node', id='SkillList')
    attr(n, 'Name', 'FixedString', 'ESC_SkillLists_0')
    attr(n, 'UUID', 'guid', guid('skills'))
    attr(n, 'Skills', 'LSString', 'Athletics,Acrobatics,Insight,Perception,Survival,Medicine,Intimidation')
    xml(PUBLIC / 'Lists/SkillLists.lsx', root)
    root, rows = document('AbilityLists')
    n = ET.SubElement(rows, 'node', id='AbilityList')
    attr(n, 'Name', 'FixedString', 'ESC_AbilityLists_0')
    attr(n, 'UUID', 'guid', guid('abilities'))
    attr(n, 'Abilities', 'LSString', 'Strength,Dexterity,Constitution,Intelligence,Wisdom,Charisma')
    xml(PUBLIC / 'Lists/AbilityLists.lsx', root)


def generate_resource():
    root, rows = document('ActionResourceDefinitions')
    n = ET.SubElement(rows, 'node', id='ActionResourceDefinition')
    for field, typ, value in [('UUID', 'guid', guid('resource/sword_yuan')), ('Name', 'FixedString', 'ESC_SwordYuan'),
                              ('MaxLevel', 'uint32', 0), ('ReplenishType', 'FixedString', 'Rest'),
                              ('ShowOnActionResourcePanel', 'bool', True), ('IsSpellResource', 'bool', False),
                              ('DisplayName', 'TranslatedString', handle('resource/yuan/name', '剑元', 'Sword Yuan')),
                              ('Description', 'TranslatedString', handle('resource/yuan/description', '剑术的内在力量。常态剑招不消耗；调息、伤敌及分支特性恢复剑元。')),
                              ('Error', 'TranslatedString', handle('resource/yuan/error', '剑元不足。'))]:
        attr(n, field, typ, value)
    n = ET.SubElement(rows, 'node', id='ActionResourceDefinition')
    for field, typ, value in [('UUID','guid',guid('resource/sword_opportunity')),('Name','FixedString','ESC_SwordOpportunity'),('MaxLevel','uint32',0),('ReplenishType','FixedString','Turn'),('ShowOnActionResourcePanel','bool',False),('IsSpellResource','bool',False)]:
        attr(n,field,typ,value)
    for key,name,capacity in [('flight','ESC_FlightMovement',24),('chain_move','ESC_ChainMovement',6)]:
        n=ET.SubElement(rows,'node',id='ActionResourceDefinition')
        for field,typ,value in [('UUID','guid',guid('resource/'+key)),('Name','FixedString',name),('MaxLevel','uint32',0),('ReplenishType','FixedString','Turn'),('ShowOnActionResourcePanel','bool',False),('IsSpellResource','bool',False)]: attr(n,field,typ,value)
    xml(PUBLIC / 'ActionResourceDefinitions/ActionResourceDefinitions.lsx', root)


def generate_level_maps():
    # Native SneakAttack uses a class-bound map. These series only supply UI
    # parameters; combat continues to use the existing stats/Lua rules.
    root, rows = document('LevelMapValues')
    maps = {**PLAYER_TEXT.get('level_maps', {}), **LEVEL_MAPS}
    for name, ranks in maps.items():
        ranks = {int(level): value for level, value in ranks.items()}
        node = ET.SubElement(rows, 'node', id='LevelMapSeries')
        attr(node, 'UUID', 'guid', guid('tooltip-map/' + name))
        attr(node, 'Name', 'FixedString', name)
        attr(node, 'PreferredClassUUID', 'guid', guid('class/common'))
        attr(node, 'FallbackValue', 'LSString', ranks[min(ranks)])
        for level in range(1, 13):
            rank = max(key for key in ranks if key <= level)
            attr(node, 'Level' + str(level), 'LSString', ranks[rank])
    xml(PUBLIC / 'Levelmaps/LevelMapValues.lsx', root)


def apply_spell_tooltip(key, spec, values, suffix=''):
    fields = spell_tooltip(key, spec)
    text = fields.pop('extra_text')
    values.update(fields)
    values['ExtraDescription'] = (
        handle('spell/' + key + '/damage' + suffix, text) + ';1' if text else '')
    if key == 'taixuan_guiyuan' or key == 'xueyan_huichao':
        values['TooltipDamageList'] = 'RegainHitPoints(MaxHP*0.4)'
    if key == 'tianqing_nixi':
        values['TooltipDamageList'] = 'RegainHitPoints(MaxHP*LevelMapValue(ESC_NixiHealing)/100)'
    # Ally healing is a percentage of the TARGET's maximum HP. A static caster
    # HP preview before selecting the ally would be wrong; its description
    # therefore shows the current, class-bound percentage instead.


def generate_passives():
    text = ''
    descriptions = PLAYER_TEXT['passive_descriptions']
    for key in PASSIVES:
        name = assets['passive_' + key]['name']
        values = dict(DisplayName=handle('passive/' + key, name) + ';1',
                      Description=handle('passive/' + key + '/description', descriptions[key]) + ';1',
                      DescriptionParams=PLAYER_TEXT.get('passive_description_params', {}).get(key, ''),
                      Icon=icon('passive_' + key), Properties='Highlighted')
        if key == 'basic_defense':
            values.update(Boosts='AC(1)', BoostConditions=equipment_condition(),
                          BoostContext='OnEquip;OnCreate')
        if key == 'xueyan_unhindered':
            values['Boosts'] = 'IgnoreLeaveAttackRange()'
        text += entry('ESC_P_' + key, 'PassiveData', values)
    for branch, data in BRANCHES.items():
        text += entry('ESC_P_Branch_' + branch, 'PassiveData', dict(
            DisplayName=handle('class/' + branch, data['name']) + ';1',
            Description=handle('class/' + branch + '/description', BRANCH_DESCRIPTIONS[branch]) + ';1',
            Icon=icon('badge_' + branch), Properties='Highlighted'))
    text += entry('ESC_P_StarterSword', 'PassiveData', dict(Properties='IsHidden', Boosts=f'UnlockSpell({spellid("yujian")})'))
    text += entry('ESC_P_StarterMelee', 'PassiveData', dict(Properties='IsHidden', Boosts=f'UnlockSpell({spellid("sword_strike")})'))
    text += entry('ESC_P_StarterGuard', 'PassiveData', dict(Properties='IsHidden', Boosts=f'UnlockSpell({spellid("qi_guard")})'))
    for level in (5, 10, 11):
        text += entry(f'ESC_P_Level{level}', 'PassiveData', dict(Properties='IsHidden'))
    write(PUBLIC / 'Stats/Generated/Data/Passive.txt', text)


def generate_spells():
    files = {}
    for key, spec in SPELLS.items():
        sid = spellid(key)
        typ = sid.split('_')[0]
        name = assets['skill_' + key]['name']
        description = player_text(name)
        if not description:
            description = PLAYER_TEXT['fallback_descriptions'].get(key, name)
        values = dict(SpellType=typ, Level=0, SpellSchool='None',
                      DisplayName=handle('spell/' + key, name) + ';1',
                      Description=handle('spell/' + key + '/description', description) + ';1',
                      DescriptionParams=PLAYER_TEXT.get('spell_description_params', {}).get(key, ''),
                      Icon=icon('skill_' + key), SpellStyleGroup='Class',
                      Cooldown='',
                      TooltipUpcastDescription='', TooltipUpcastDescriptionParams='',
                      SpellProperties='', SpellRoll='', SpellSuccess='', SpellFail='',
                      TooltipDamageList='', TooltipStatusApply='', ConcentrationSpellID='',
                      Requirements='', TargetConditions='Character() and not Dead()',
                      TargetRadius=spec['range'] or 0, CycleConditions='Enemy() and not Dead()',
                      SpellFlags='IsSpell;RangeIgnoreVerticalThreshold',
                      AmountOfTargets=1, ProjectileCount=1)
        if spec['action'] == 'bonus':
            costs = ['BonusActionPoint:1']
        elif spec['action'] == 'sword':
            costs = ['ActionPoint:1']
        else:
            costs = []
        if spec['cost']:
            costs.append('ESC_SwordYuan:' + str(spec['cost']))
        values['UseCosts'] = ';'.join(costs)
        base = {'Projectile': 'Projectile_MagicMissile', 'Target': 'Target_HealingWord',
                'Zone': 'Zone_Thunderwave', 'Rush':'Rush_Rush', 'Shout': 'Shout_SecondWind'}[typ]
        if spec['kind'] == 'flight':
            base='Shout_SecondWind'
            values.update(TargetConditions='Self()',TargetRadius=0,SpellProperties='ApplyStatus(ESC_CAST_SWORD_FLIGHT,100,0)')
        elif spec['kind'] in ('attack', 'chain_attack', 'cooperate', 'cone_attack', 'dash_attack', 'area_attack', 'area_save', 'self_area_save', 'leap_area_save', 'piercing_line'):
            if key=='sword_strike': base='Target_MainHandAttack'
            values['TargetConditions'] = 'Character() and Enemy() and not Dead()'
            values['SpellFlags'] += ';IsHarmful'
            # Engine rolls each segment; Lua handles damage accounting and special boundaries.
            dtype = 'Necrotic' if spec['branch'] == 'xueyan' else 'Force'
            normal_dice = {
                'taixuan_zhaoxi':['2d8','3d8','4d8'], 'tianqing_nifeng':['3d8','4d8','5d8'],
                'xueyan_luexue':['2d6','3d6','4d6'], 'xingge_wenlu':['1d4','1d6','2d6'],
            }
            def damage_expression(divisor=1):
                parts=[]
                def add(expression,damage_type,conditions=()):
                    condition=' and '.join(conditions)
                    value=expression if divisor==1 else f'({expression})/{divisor}'
                    parts.append(('IF('+condition+'):' if condition else '')+f'DealDamage({value},{damage_type},Magical)')
                def elemental(expression,conditions=()):
                    if spec['branch']=='xueyan':
                        add(expression,'Necrotic',(*conditions,"not HasStatus('ESC_FORCE_MODE',context.Source)"))
                        add(expression,'Force',(*conditions,"HasStatus('ESC_FORCE_MODE',context.Source)"))
                    else: add(expression,'Force',conditions)
                if spec['base']=='Q': elemental('2d6+WisdomModifier')
                elif spec['base']=='WQ':
                    elemental('2d6+WisdomModifier',(QI_CONDITION,))
                    add('MainMeleeWeapon','MainMeleeWeaponDamageType',('not ('+QI_CONDITION+')',))
                else: add('MainMeleeWeapon','MainMeleeWeaponDamageType')
                if key in normal_dice:
                    for condition,dice in zip([
                        "not HasPassive('ESC_P_Level5',context.Source)",
                        "HasPassive('ESC_P_Level5',context.Source) and not HasPassive('ESC_P_Level10',context.Source)",
                        "HasPassive('ESC_P_Level10',context.Source)"],normal_dice[key]): elemental(dice,(condition,))
                elif spec['dice']: elemental('32d8' if key=='tianqing_tianbeng' else spec['dice'])
                return ';'.join(parts)
            damage=damage_expression()
            half=damage_expression(2)
            if key in ('tianqing_bafang','tianqing_tiandi'):
                values['TargetConditions']='Character() and not Self() and not Dead()'
                damage="IF(Enemy()):"+damage.replace(';',';IF(Enemy()):')+";IF(not Enemy()):"+damage_expression(4).replace(';',';IF(not Enemy()):')
                half="IF(Enemy()):"+half.replace(';',';IF(Enemy()):')+";IF(not Enemy()):"+damage_expression(8).replace(';',';IF(not Enemy()):')
            # Noesis tooltip damage parser rejects conditional IF functors.
            # Show the unmodified opening-rank, weapon-mode roll here; the real
            # SpellSuccess/SpellFail above retain mode, level, and save branches.
            preview_type='Necrotic' if spec['branch']=='xueyan' else 'Force'
            preview_base=('DealDamage(2d6+WisdomModifier,'+preview_type+',Magical)' if spec['base']=='Q'
                          else 'DealDamage(MainMeleeWeapon,MainMeleeWeaponDamageType,Magical)')
            preview_extra=normal_dice.get(key,[spec['dice']])[0]
            values['TooltipDamageList']=preview_base+(';DealDamage('+preview_extra+','+preview_type+',Magical)' if preview_extra else '')
            # A fixed opening-rank roll would mislead higher-level or Qi Sword
            # characters. Show these variable rolls in the localized rules text.
            if key in normal_dice or spec['base']=='WQ' or spec['branch']=='xueyan':
                values['TooltipDamageList']=''
            if 'save' in spec['kind']:
                values.update(SpellRoll='not SavingThrow(Ability.Dexterity,SourceSpellDC())', SpellSuccess=damage,
                              SpellFail=half)
            else:
                values.update(SpellRoll='Attack(AttackType.MeleeSpellAttack)' if key == 'sword_strike' else 'Attack(AttackType.RangedSpellAttack)', SpellSuccess=damage)
            if key=='tianqing_tiandi':
                values['SpellProperties']='RemoveStatus(ESC_TIANDI_FIRSTHIT);ApplyStatus(ESC_TIANDI_TARGET,100,0)'
            if key in HIT_CONTROLS:
                control=HIT_CONTROLS[key]
                failed=f";TARGET:IF(Enemy() and not SavingThrow(Ability.{control['ability']},SourceSpellDC())):ApplyStatus(ESC_SAVEFAIL_{key.upper()},100,0)"
                if key=='tianqing_tiandi': failed=failed.replace('Enemy() and','Enemy() and not HasStatus(\'ESC_TIANDI_FIRSTHIT\') and')
                values['SpellSuccess']+=failed
                if key=='tianqing_tiandi': values['SpellSuccess']+=';ApplyStatus(ESC_TIANDI_FIRSTHIT,100,1)'
                if 'save' in spec['kind']: values['SpellFail']+=failed
            if key=='tianqing_tiandi': values['AmountOfTargets']=1
            if spec['segments'] > 1 and key not in ('tianqing_tiandi','taixuan_liuguang'):
                values['AmountOfTargets'] = spec['segments']
            if key in ('tianqing_tianbeng','taixuan_liuguang'):
                values['AmountOfTargets']=1
                values['ProjectileCount']=1
                values['TooltipDamageList']=''
            if typ in ('Target', 'Shout') and spec['radius']:
                values['AreaRadius'] = spec['radius']
                if typ == 'Shout':
                    values['TargetRadius'] = spec['radius']
            if typ=='Rush':
                values.update(HitRadius=spec['radius']/2,MovementSpeed=40000,Requirements='!Immobile',RequirementConditions='',AIFlags='',WeaponTypes='')
            if typ == 'Zone':
                values.update(Shape='Cone' if spec['kind'] == 'cone_attack' else 'Line', Range=spec['range'],
                              Base=spec['radius'] or 12, Angle=90 if key == 'tianqing_tianbeng' else 60,
                              SurfaceType='Sentinel', SurfaceLifetime=0)
            # This status is an engine-confirmed hit marker, including fully absorbed hits.
            if key in ('taixuan_zhaoxi', 'xingge_wenlu'):
                values['SpellSuccess'] += ';ApplyStatus(ESC_' + ('WEAKPOINT' if key.startswith('taixuan') else 'FOLLOWUP') + ',100,3)'
            values['SpellSuccess'] += ';ApplyStatus(ESC_HIT_MARKER,100,0)'
            if spec['base'] in ('W','WQ'):
                weapon_functor=(';IF(not ('+QI_CONDITION+')):' if spec['base']=='WQ' else ';')+'ExecuteWeaponFunctors(MainHand)'
                values['SpellSuccess']+=weapon_functor
                if 'save' in spec['kind']: values['SpellFail']+=weapon_functor
            if key == 'taixuan_yixiantian':
                damage='DealDamage(2d6+WisdomModifier+36d8,Force,Magical)'
                values.update(SpellRoll='', SpellSuccess='', SpellProperties=damage, TooltipDamageList=damage,
                              SpellFlags=values['SpellFlags'] + ';IgnoreVisionBlock')
        else:
            if typ == 'Shout':
                values.update(TargetConditions='Self()', TargetRadius=0)
            # Callback marker spell has a real status, not a damaging placeholder.
            values['SpellProperties'] = f'ApplyStatus(ESC_CAST_{key.upper()},100,0)'
        values['SpellFlags'] += ';IgnoreSilence'
        values['RequirementConditions']=equipment_condition()
        if spec['base']=='W' and spec['action']=='sword': values['RequirementConditions']+=' and ('+sword_condition('Main')+' or '+sword_condition('Off')+')'
        if key=='recall_sword': values['TargetConditions']='Item()'
        if key in ('taixuan_guiyuan','tianqing_nixi','xueyan_huichao','control_release'):
            values['TargetConditions']='Self() and not Dead()'
        if key=='focus_target': values['TargetConditions']='Character() and Enemy() and not Dead()'
        if key in ('xingge_chengfeng','xingge_huifeng','xingge_xiangfu','xingge_fuchen'): values['TargetConditions']='Character() and (Self() or Ally()) and not Dead()'
        if key=='xueyan_wusheng': values['AmountOfTargets']=1
        if key=='xueyan_liancheng': values.update(AmountOfTargets=1,TargetRadius=18)
        apply_spell_tooltip(key, spec, values)
        if key in ('xueyan_nixue', 'xueyan_wusheng'):
            variants=[]
            for spent in range(16):
                variant=sid + '_F' + str(spent)
                variants.append(variant)
                variant_values=dict(values)
                variant_values['SpellContainerID']=sid
                variant_values['DisplayName']=handle('spell/'+key+'/spend/'+str(spent),name+(' · 不消耗癫狂' if spent==0 else ' · 消耗'+str(spent)+'层癫狂'))+';1'
                if spent:
                    variant_values['RequirementConditions']=f"not HasShieldEquipped(context.Source) and HasStatus('ESC_FRENZY_AT_LEAST_{spent}',context.Source)"
                files[typ]=files.get(typ,'')+entry(variant,'SpellData',variant_values,base)
                aliases[variant]=dict(key=key,spent=spent,**({'chain':'wusheng'} if key=='xueyan_wusheng' else {}))
            values.update(ContainerSpells=';'.join(variants),SpellProperties='',SpellSuccess='',SpellFail='',SpellRoll='',UseCosts='',SpellFlags=values['SpellFlags']+';IsLinkedSpellContainer')
        if key=='xueyan_huichao':
            choices=[]
            for suffix,cost in [('Yuan','BonusActionPoint:1;ESC_SwordYuan:6'),('Frenzy','BonusActionPoint:1')]:
                variant=sid+'_'+suffix;choices.append(variant);v=dict(values);v['UseCosts']=cost;v['SpellContainerID']=sid
                v['DisplayName']=handle('spell/huichao/'+suffix,name+(' · 6剑元' if suffix=='Yuan' else ' · 3层癫狂'))+';1'
                if suffix=='Frenzy':v['RequirementConditions']="not HasShieldEquipped(context.Source) and HasStatus('ESC_FRENZY_AT_LEAST_3',context.Source)"
                aliases[variant]=dict(key=key,**({'spent':3,'noYuan':True} if suffix=='Frenzy' else {}))
                files[typ]=files.get(typ,'')+entry(variant,'SpellData',v,base)
            values.update(ContainerSpells=';'.join(choices),SpellProperties='',UseCosts='',SpellFlags=values['SpellFlags']+';IsLinkedSpellContainer')
        if key in ('taixuan_zhaoxi','tianqing_nifeng','xueyan_luexue','xingge_wenlu'):
            variants=[]
            for melee in (True,False):
                for hand in ('Main','Off'):
                    variant_type='Zone' if key=='tianqing_nifeng' else ('Target' if melee else 'Projectile')
                    variant=variant_type+'_ESC_'+key+('_Melee' if melee else '_Ranged')+hand
                    v=dict(values);v['SpellType']=variant_type;v['TargetRadius']=3 if melee else 18
                    v['SpellRoll']=('Attack(AttackType.MeleeWeaponAttack)' if hand=='Main' else 'Attack(AttackType.MeleeOffHandWeaponAttack)') if melee else 'Attack(AttackType.RangedSpellAttack)'
                    if key=='tianqing_nifeng': v.update(Shape='Cone' if melee else 'Line',Range=6 if melee else 12,TargetRadius=6 if melee else 12,Base=6 if melee else 2,Angle=60)
                    form=('近战' if melee else '御剑')
                    v['DisplayName']=handle('spell/'+key+'/'+('Melee' if melee else 'Ranged')+hand,name+' · '+form+('' if hand=='Main' else '（副手）'))+';1'
                    v['SpellContainerID']=sid
                    for field in ('SpellSuccess','SpellFail','TooltipDamageList','SpellProperties','ExtraDescriptionParams'):
                        v[field]=v.get(field,'').replace('MainMeleeWeaponDamageType','OffhandMeleeWeaponDamageType').replace('MainMeleeWeapon','OffhandMeleeWeapon').replace('ExecuteWeaponFunctors(MainHand)','ExecuteWeaponFunctors(OffHand)') if hand=='Off' else v.get(field,'')
                    gate=equipment_condition()
                    if hand=='Off': v['RequirementConditions']=gate+' and '+sword_condition('Off')
                    else: v['RequirementConditions']=gate+(' and (('+QI_CONDITION+') or '+sword_condition('Main')+')' if spec['base']=='WQ' else ' and '+sword_condition('Main'))
                    files[variant_type]=files.get(variant_type,'')+entry(variant,'SpellData',v,'Zone_Thunderwave' if key=='tianqing_nifeng' else ('Target_MainHandAttack' if melee else 'Projectile_MagicMissile'))
                    aliases[variant]=dict(key=key,hand=hand.lower(),**({'chain':'liancheng'} if key=='xueyan_liancheng' else {}));variants.append(variant)
                    if hand=='Off' and key!='xueyan_liancheng':
                        bonus=variant+'_Bonus';bv=dict(v);bv['UseCosts']='BonusActionPoint:1';bv['SpellContainerID']=sid
                        bv['RequirementConditions']=gate+' and '+sword_condition('Main')+' and '+sword_condition('Off')
                        bv['DisplayName']=handle('spell/'+key+'/bonus/'+form,name+' · 副手追加（'+form+'）')+';1'
                        bv['Description']=handle('spell/'+key+'/bonus/'+form+'/description','用副手剑追加一次'+form+'攻击，触发'+name+'的效果。需要双持剑；不获得连贯出剑。')+';1'
                        files[variant_type]+=entry(bonus,'SpellData',bv,'Zone_Thunderwave' if key=='tianqing_nifeng' else ('Target_MainHandAttack' if melee else 'Projectile_MagicMissile'));variants.append(bonus)
                        aliases[bonus]=dict(key=key,hand='off',offhand=True,bonusOnly=True)
            values.update(ContainerSpells=';'.join(variants),SpellProperties='',SpellSuccess='',SpellFail='',SpellRoll='',UseCosts='',SpellFlags=values['SpellFlags']+';IsLinkedSpellContainer')
        if spec['base'] in ('W','WQ') and spec['action']=='sword' and key not in ('taixuan_zhaoxi','tianqing_nifeng','xueyan_luexue','xingge_wenlu','xueyan_liancheng','tianqing_tianjian'):
            choices=[]
            for hand in ('Main','Off'):
                variant=sid+'_'+hand;choices.append(variant);v=dict(values)
                v['SpellContainerID']=sid;v['DisplayName']=handle('spell/'+key+'/'+hand, name+' · '+('主手佩剑' if hand=='Main' else '副手佩剑'))+';1'
                gate=equipment_condition()
                v['RequirementConditions']=gate+(' and (('+QI_CONDITION+') or '+sword_condition('Main')+')' if hand=='Main' and spec['base']=='WQ' else ' and '+sword_condition(hand))
                if hand=='Off':
                    v['SpellRoll']=v.get('SpellRoll','').replace('AttackType.MeleeSpellAttack','AttackType.MeleeOffHandWeaponAttack').replace('AttackType.MeleeWeaponAttack','AttackType.MeleeOffHandWeaponAttack')
                    for field in ('SpellSuccess','SpellFail','SpellProperties','TooltipDamageList','ExtraDescriptionParams'):
                        v[field]=v.get(field,'').replace('MainMeleeWeaponDamageType','OffhandMeleeWeaponDamageType').replace('MainMeleeWeapon','OffhandMeleeWeapon').replace('ExecuteWeaponFunctors(MainHand)','ExecuteWeaponFunctors(OffHand)')
                files[typ]=files.get(typ,'')+entry(variant,'SpellData',v,base);aliases[variant]=dict(key=key,hand=hand.lower())
            values.update(ContainerSpells=';'.join(choices),SpellProperties='',SpellSuccess='',SpellFail='',SpellRoll='',UseCosts='',SpellFlags=values['SpellFlags']+';IsLinkedSpellContainer')
        if key=='xueyan_liancheng':
            values.update(SpellType='Shout',TargetRadius=0,TargetConditions='Self()',SpellRoll='',SpellSuccess='',SpellFail='',SpellProperties='ApplyStatus(ESC_CAST_XUEYAN_LIANCHENG,100,0)',TooltipDamageList='')
            base='Shout_SecondWind'
            aliases[sid]=dict(key=key,chain='liancheng',startChain=True)
        if key=='tianqing_tianjian':
            choices=[]
            for hand in ('Main','Off'):
                impact='Projectile_ESC_TianjianImpact'+('_Off' if hand=='Off' else '')
                iv=dict(values);iv.update(UseCosts='',TargetRadius=0,AreaRadius=9,ExplodeRadius=9,SpellProperties='',TargetConditions='Character() and Enemy() and not Dead()')
                if hand=='Off':
                    for field in ('SpellSuccess','SpellFail','TooltipDamageList','ExtraDescriptionParams'):
                        iv[field]=iv.get(field,'').replace('MainMeleeWeaponDamageType','OffhandMeleeWeaponDamageType').replace('MainMeleeWeapon','OffhandMeleeWeapon').replace('ExecuteWeaponFunctors(MainHand)','ExecuteWeaponFunctors(OffHand)')
                files['Projectile']=files.get('Projectile','')+entry(impact,'SpellData',iv,'Projectile_Jump_Bulette_Spawn');aliases[impact]=dict(key=key,internal=True,impact=True,hand=hand.lower())
                jump=sid+'_'+hand;choices.append(jump);v=dict(values)
                if hand=='Off':
                    for field in ('TooltipDamageList', 'ExtraDescriptionParams'):
                        v[field]=v.get(field,'').replace('MainMeleeWeaponDamageType','OffhandMeleeWeaponDamageType').replace('MainMeleeWeapon','OffhandMeleeWeapon')
                v.update(SpellContainerID=sid,DisplayName=handle('spell/'+key+'/'+hand,name+' · '+('主手佩剑' if hand=='Main' else '副手佩剑'))+';1',SpellRoll='',SpellSuccess='',SpellFail='',SpellProperties='GROUND:CreateExplosion('+impact+')',TargetRadius=24,AddRangeFromAbility='',TargetConditions="not Surface('SurfaceChasm')",SpellFlags='IsJump;RangeIgnoreVerticalThreshold;CannotTargetCharacter;CannotTargetItems;IgnoreSilence',SpellJumpType='Jump',RequirementConditions=equipment_condition()+' and '+sword_condition(hand))
                files['Projectile']+=entry(jump,'SpellData',v,'Projectile_Jump');aliases[jump]=dict(key=key,hand=hand.lower())
            values.update(ContainerSpells=';'.join(choices),SpellRoll='',SpellSuccess='',SpellFail='',SpellProperties='',UseCosts='',SpellFlags='IsLinkedSpellContainer;IgnoreSilence')
            base='Projectile_Jump'
        files[typ] = files.get(typ, '') + entry(sid, 'SpellData', values, base)
    helpers = {
        'TaiqingPulse': ('internal_taiqing_pulse','2d8','Force',True,0),
        'BloodPulse': ('internal_blood_pulse','2d6','Necrotic',True,0),
        'Counter2': ('internal_counter2','4d8','Force',True,2),
        'Counter3': ('internal_counter3','6d8','Force',True,3),
        'Resonance': ('internal_resonance','2d6','Force',True,0),
        'Aftershock': ('internal_aftershock','6d8','Force',False,0),
    }
    for suffix,(key,dice,dtype,attack,bonus) in helpers.items():
        sid='Target_ESC_'+suffix
        base_damage=('2d6+WisdomModifier' if suffix!='Aftershock' else '0')
        damage=(f'DealDamage({base_damage},{dtype},Magical);' if base_damage!='0' else '')+f'DealDamage({dice},{dtype},Magical)'
        if suffix=='BloodPulse':
            damage="IF(not HasStatus('ESC_FORCE_MODE',context.Source)):"+damage.replace(';',";IF(not HasStatus('ESC_FORCE_MODE',context.Source)):")+";IF(HasStatus('ESC_FORCE_MODE',context.Source)):"+damage.replace('Necrotic','Force').replace(';',";IF(HasStatus('ESC_FORCE_MODE',context.Source)):")
        values=dict(SpellType='Target',Level=0,UseCosts='',Cooldown='',SpellRoll='Attack(AttackType.RangedSpellAttack)' if attack else '',SpellProperties='' if attack else damage,SpellSuccess=damage+';ApplyStatus(ESC_HIT_MARKER,100,0)' if attack else '',SpellFail='',TargetRadius=30,TargetConditions='Character() and Enemy() and not Dead()',SpellFlags='IsSpell;IsHarmful;IgnoreSilence',Icon=icon('skill_xueyan_xuehai' if suffix=='BloodPulse' else 'skill_taixuan_taiqing'),AmountOfTargets=1)
        files['Target']=files.get('Target','')+entry(sid,'SpellData',values,'Target_HealingWord')
        aliases[sid]=dict(key=key,internal=True,attackBonus=bonus)
    tiandi_damage="IF(Enemy()):DealDamage(MainMeleeWeapon,MainMeleeWeaponDamageType,Magical);IF(Enemy()):DealDamage(14d8,Force,Magical);IF(not Enemy()):DealDamage((MainMeleeWeapon)/4,MainMeleeWeaponDamageType,Magical);IF(not Enemy()):DealDamage((14d8)/4,Force,Magical)"
    tiandi_control=";TARGET:IF(Enemy() and not HasStatus('ESC_TIANDI_FIRSTHIT') and not SavingThrow(Ability.Strength,SourceSpellDC())):ApplyStatus(ESC_SAVEFAIL_TIANQING_TIANDI,100,0);ApplyStatus(ESC_TIANDI_FIRSTHIT,100,1);ExecuteWeaponFunctors(MainHand)"
    files['Target']+=entry('Target_ESC_TiandiStage','SpellData',dict(SpellType='Target',UseCosts='',Cooldown='',SpellRoll='Attack(AttackType.RangedSpellAttack)',SpellSuccess=tiandi_damage+tiandi_control+';ApplyStatus(ESC_HIT_MARKER,100,0)',SpellProperties='',SpellFail='',TargetRadius=30,TargetConditions='Character() and not Self() and not Dead()',SpellFlags='IsSpell;IsHarmful;IgnoreSilence',AmountOfTargets=1,Icon=icon('skill_tianqing_tiandi')),'Target_HealingWord')
    aliases['Target_ESC_TiandiStage']=dict(key='internal_tiandi_stage',internal=True,parent='tianqing_tiandi')
    files['Target']+=entry('Target_ESC_TianbengMain','SpellData',dict(SpellType='Target',UseCosts='',Cooldown='',SpellRoll='',SpellSuccess='',SpellFail='',SpellProperties='DealDamage(14d8,Force,Magical);ApplyStatus(ESC_HIT_MARKER,100,0)',TargetRadius=30,TargetConditions='Character() and Enemy() and not Dead()',SpellFlags='IsSpell;IsHarmful;IgnoreSilence',AmountOfTargets=1,Icon=icon('skill_tianqing_tianbeng')),'Target_HealingWord')
    aliases['Target_ESC_TianbengMain']=dict(key='internal_tianbeng_main',internal=True,parent='tianqing_tianbeng')
    for suffix,key,parent,dice,weapon in [
        ('LiuguangStage','internal_liuguang_stage','taixuan_liuguang','4d8',False),
        ('TianbengCone','internal_tianbeng_cone','tianqing_tianbeng','18d8',True),
    ]:
        stage_damage=('DealDamage(MainMeleeWeapon,MainMeleeWeaponDamageType,Magical)' if weapon else 'DealDamage(2d6+WisdomModifier,Force,Magical)')+';DealDamage('+dice+',Force,Magical);ApplyStatus(ESC_HIT_MARKER,100,0)'
        if weapon:
            stage_damage+=";TARGET:IF(not SavingThrow(Ability.Strength,SourceSpellDC())):ApplyStatus(ESC_SAVEFAIL_TIANQING_TIANBENG,100,0);ExecuteWeaponFunctors(MainHand)"
        for hand in (('Main','Off') if weapon else ('Main',)):
            stage='Target_ESC_'+suffix+('_Off' if hand=='Off' else '')
            success=stage_damage
            if hand=='Off':
                success=success.replace('MainMeleeWeaponDamageType','OffhandMeleeWeaponDamageType').replace('MainMeleeWeapon','OffhandMeleeWeapon').replace('ExecuteWeaponFunctors(MainHand)','ExecuteWeaponFunctors(OffHand)')
            files['Target']+=entry(stage,'SpellData',dict(SpellType='Target',UseCosts='',Cooldown='',SpellRoll='Attack(AttackType.RangedSpellAttack)',SpellSuccess=success,SpellProperties='',SpellFail='',TargetRadius=18,TargetConditions='Character() and Enemy() and not Dead()',SpellFlags='IsSpell;IsHarmful;IgnoreSilence',AmountOfTargets=1,Icon=icon('skill_'+parent)),'Target_HealingWord')
            aliases[stage]=dict(key=key,internal=True,parent=parent,hand=hand.lower())
    for suffix,damage_key,roll,damage,fail in [
        ('ChengfengBurst','xingge_chengfeng','not SavingThrow(Ability.Dexterity,SourceSpellDC())','DealDamage(MainMeleeWeapon,MainMeleeWeaponDamageType,Magical);DealDamage(8d6,Force,Magical)','DealDamage((MainMeleeWeapon)/2,MainMeleeWeaponDamageType,Magical);DealDamage((8d6)/2,Force,Magical)'),
        ('HuifengControl','xingge_huifeng','not SavingThrow(Ability.Dexterity,SourceSpellDC())','',''),
    ]:
        control="ApplyStatus(ESC_SAVEFAIL_XINGGE_HUIFENG,100,0)" if suffix=='HuifengControl' else "TARGET:IF(not SavingThrow(Ability.Strength,SourceSpellDC())):ApplyStatus(ESC_SAVEFAIL_XINGGE_CHENGFENG,100,0)"
        marker='' if suffix=='HuifengControl' else ';ApplyStatus(ESC_HIT_MARKER,100,0)'
        success=damage+(';' if damage else '')+control+marker+(';ExecuteWeaponFunctors(MainHand)' if damage else '')
        fail=fail+(';' +control+marker+';ExecuteWeaponFunctors(MainHand)' if fail else '')
        for hand in (('Main','Off') if suffix=='ChengfengBurst' else ('Main',)):
            sid='Target_ESC_'+suffix+('_Off' if hand=='Off' else '')
            v=dict(SpellType='Target',UseCosts='',Cooldown='',SpellRoll=roll,SpellSuccess=success,SpellFail=fail,SpellProperties='',TargetRadius=30,TargetConditions='Character() and Enemy() and not Dead()',SpellFlags='IsSpell;IsHarmful;IgnoreSilence',AmountOfTargets=1,Icon=icon('skill_'+damage_key))
            if hand=='Off':
                for field in ('SpellSuccess','SpellFail'):v[field]=v[field].replace('MainMeleeWeaponDamageType','OffhandMeleeWeaponDamageType').replace('MainMeleeWeapon','OffhandMeleeWeapon').replace('ExecuteWeaponFunctors(MainHand)','ExecuteWeaponFunctors(OffHand)')
            files['Target']+=entry(sid,'SpellData',v,'Target_HealingWord');aliases[sid]=dict(key='internal_chengfeng_burst' if suffix=='ChengfengBurst' else 'internal_huifeng_control',internal=True,parent=damage_key,hand=hand.lower())
    # Native helper follow-up stages preserve the selected weapon hand of their parent cast.
    for original,key,parent in [('Target_ESC_TiandiStage','internal_tiandi_stage','tianqing_tiandi'),('Target_ESC_TianbengMain','internal_tianbeng_main','tianqing_tianbeng')]:
        native=re.search(r'new entry "'+original+r'"\n(.*?)(?=new entry |\Z)',files['Target'],re.S).group(1)
        values=dict(re.findall(r'data "([^"]+)" "([^"]*)"',native))
        for field in ('SpellSuccess','SpellFail','SpellProperties'):
            values[field]=values.get(field,'').replace('MainMeleeWeaponDamageType','OffhandMeleeWeaponDamageType').replace('MainMeleeWeapon','OffhandMeleeWeapon').replace('ExecuteWeaponFunctors(MainHand)','ExecuteWeaponFunctors(OffHand)')
        files['Target']+=entry(original+'_Off','SpellData',values,'Target_HealingWord');aliases[original+'_Off']=dict(key=key,internal=True,parent=parent,hand='off')
    for chain,count in [('liancheng',4),('wusheng',6)]:
        key='xueyan_'+chain
        for melee in (True,False):
            typ='Target' if melee else 'Projectile';sid=typ+'_ESC_'+chain+'_Continue'+('Melee' if melee else 'Ranged')
            damage="IF(not HasStatus('ESC_FORCE_MODE',context.Source)):DealDamage(2d6+WisdomModifier,Necrotic,Magical);IF(HasStatus('ESC_FORCE_MODE',context.Source)):DealDamage(2d6+WisdomModifier,Force,Magical)"
            if chain=='liancheng':damage+=";IF(not HasStatus('ESC_FORCE_MODE',context.Source)):DealDamage(1d6,Necrotic,Magical);IF(HasStatus('ESC_FORCE_MODE',context.Source)):DealDamage(1d6,Force,Magical)"
            continuation_text=PLAYER_TEXT['ui_descriptions'][chain+'_continuation_description']
            v=dict(SpellType=typ,UseCosts='',Cooldown='',SpellRoll='Attack(AttackType.MeleeSpellAttack)' if melee else 'Attack(AttackType.RangedSpellAttack)',SpellSuccess=damage+';ApplyStatus(ESC_HIT_MARKER,100,0)',SpellFail='',SpellProperties='',TargetRadius=3 if melee else (18 if chain=='liancheng' else 24),TargetConditions='Character() and Enemy() and not Dead()',RequirementConditions=f"HasStatus('ESC_CHAIN_{chain.upper()}',context.Source)",SpellFlags='IsSpell;IsHarmful;IgnoreSilence',AmountOfTargets=1,Icon=icon('skill_'+key),DisplayName=handle('spell/chain/'+chain+str(melee),assets['skill_'+key]['name']+' · 续剑'+('近战' if melee else '御剑'))+';1',Description=handle('spell/chain/'+chain+str(melee)+'/description',continuation_text)+';1')
            apply_spell_tooltip(key, {**SPELLS[key], 'segments': 1, 'continuation': True}, v, '/continuation')
            files[typ]=files.get(typ,'')+entry(sid,'SpellData',v,'Target_HealingWord' if melee else 'Projectile_MagicMissile');aliases[sid]=dict(key=key,chain=chain,continuation=True)
    for sid,key,resource,status,range_ in [('Projectile_ESC_FlightMove','internal_flight_move','ESC_FlightMovement','ESC_IN_FLIGHT',24),('Projectile_ESC_ChainMove','internal_chain_move','ESC_ChainMovement','ESC_CHAIN_LIANCHENG',6)]:
        v=dict(SpellType='Projectile',UseCosts=resource+':Distance',Cooldown='',TargetRadius=range_,AddRangeFromAbility='',TargetConditions="not Surface('SurfaceChasm')",RequirementConditions=f"HasStatus('{status}',context.Source)",SpellProperties='',SpellSuccess='',SpellFail='',SpellRoll='',AmountOfTargets=1,Icon=icon('skill_sword_flight' if key=='internal_flight_move' else 'skill_xueyan_liancheng'),DisplayName=handle('spell/move/'+key,'御剑飞移' if key=='internal_flight_move' else '连城移步')+';1',SpellFlags='IsJump;RangeIgnoreVerticalThreshold;CannotTargetCharacter;CannotTargetItems;NoAOEDamageOnLand;IgnoreSilence')
        v['Description']=handle('spell/move/'+key+'/description',PLAYER_TEXT['ui_descriptions']['flight_move_description' if key=='internal_flight_move' else 'chain_move_description'])+';1'
        files['Projectile']=files.get('Projectile','')+entry(sid,'SpellData',v,'Projectile_Fly' if key=='internal_flight_move' else 'Projectile_Jump');aliases[sid]=dict(key=key,internal=True)
    for typ, text in files.items():
        write(PUBLIC / f'Stats/Generated/Data/Spell_{typ}.txt', text)


def generate_statuses():
    text = ''
    for key, spec in SPELLS.items():
        text += entry('ESC_CAST_' + key.upper(), 'StatusData', dict(
            StatusType='BOOST', DisplayName=handle('spell/' + key, assets['skill_' + key]['name']) + ';1',
            Icon=icon('skill_' + key), StackId='ESC_CAST_' + key.upper(),
            StatusPropertyFlags='DisableCombatlog;DisablePortraitIndicator;DisableOverhead'))
    for aid, a in assets.items():
        if a['kind'] != 'status':
            continue
        key = aid.removeprefix('status_')
        text += entry('ESC_' + key.upper(), 'StatusData', dict(
            StatusType='BOOST', DisplayName=handle('status/' + key, a['name']) + ';1',
            Description=handle('status/' + key + '/description', PLAYER_TEXT['status_descriptions'].get(key, a['name'])) + ';1',
            DescriptionParams=PLAYER_TEXT.get('status_description_params', {}).get(key, ''), Icon=icon(aid),
            StackId='ESC_' + key.upper(), TickType='StartTurn', **({'Boosts':'AC(2)'} if key=='xingge_protection' else {})))
    for key in HIT_CONTROLS:
        text+=entry('ESC_SAVEFAIL_'+key.upper(),'StatusData',dict(StatusType='BOOST',StackId='ESC_SAVEFAIL_'+key.upper(),StatusPropertyFlags='DisableCombatlog;DisablePortraitIndicator;DisableOverhead',**({'OnApplyFunctors':f'Force({HIT_CONTROLS[key]["push"]})'} if HIT_CONTROLS[key].get('push') else {})))
    for name in ['HIT_MARKER', 'CHAIN', 'GUARD', 'BASELINE', 'WEAPON_WISDOM']:
        text += entry('ESC_' + name, 'StatusData', dict(StatusType='BOOST', StackId='ESC_' + name,
            StatusPropertyFlags='DisableCombatlog;DisablePortraitIndicator;DisableOverhead'))
    for number in range(1,16):
        text += entry('ESC_FRENZY_AT_LEAST_' + str(number), 'StatusData', dict(StatusType='BOOST',
            StackId='ESC_FRENZY_AT_LEAST_' + str(number),StatusPropertyFlags='DisableCombatlog;DisablePortraitIndicator;DisableOverhead'))
    for name in ['FORCE_MODE','QI_MODE']:
        text += entry('ESC_' + name, 'StatusData', dict(StatusType='BOOST',StackId='ESC_'+name,
            StatusPropertyFlags='DisableCombatlog;DisablePortraitIndicator;DisableOverhead'))
    sword_spells=[spellid(key) for key,spell in SPELLS.items() if spell['action']=='sword']
    sword_spells += [sid for sid,a in aliases.items() if not a.get('internal') and a.get('key') in SPELLS and SPELLS[a['key']]['action']=='sword' and not a.get('bonusOnly') and not a.get('continuation')]
    groups=[]
    for offset in range(0,len(sword_spells),12):
        group='ESC_EXTRA_ATTACK_'+str(offset//12);groups.append(group)
        condition=' or '.join("SpellId('"+sid+"')" for sid in sword_spells[offset:offset+12])
        text+=entry(group,'StatusData',dict(StatusType='BOOST',StackId=group,StatusPropertyFlags='DisableCombatlog;DisablePortraitIndicator;DisableOverhead',Boosts=f'UnlockSpellVariant({condition},ModifyUseCosts(Replace,ActionPoint,1,0,ESC_SwordOpportunity))'))
    text += entry('ESC_EXTRA_ATTACK','StatusData',dict(StatusType='BOOST',StackId='ESC_EXTRA_ATTACK',StatusPropertyFlags='DisableCombatlog;DisablePortraitIndicator;DisableOverhead',OnApplyFunctors=';'.join(f'ApplyStatus({group},100,-1)' for group in groups),OnRemoveFunctors=';'.join(f'RemoveStatus({group})' for group in groups)))
    for name,boosts in [
        ('IN_FLIGHT','UnlockSpell(Projectile_ESC_FlightMove)'),
        ('CHAIN_LIANCHENG','UnlockSpell(Target_ESC_liancheng_ContinueMelee);UnlockSpell(Projectile_ESC_liancheng_ContinueRanged);UnlockSpell(Projectile_ESC_ChainMove)'),
        ('CHAIN_WUSHENG','UnlockSpell(Target_ESC_wusheng_ContinueMelee);UnlockSpell(Projectile_ESC_wusheng_ContinueRanged)'),
        # Keep this inert legacy marker so old saves that chose a starter sword
        # can deserialize it; no new spell applies or consumes it.
        ('OFFHAND_SWORD',''),('MAIN_SWORD',''),('ARMOR_BLOCKED',''),('STARTING_SWORD_CHOSEN',''),('TIANDI_TARGET',''),('TIANDI_FIRSTHIT',''),
        ('COUNTER_RANK2',"UnlockInterrupt(Interrupt_ESC_Counter2);IF(SpellId('Target_ESC_Counter2')):RollBonus(Attack,2)"),
        ('COUNTER_RANK3',"UnlockInterrupt(Interrupt_ESC_Counter3);IF(SpellId('Target_ESC_Counter3')):RollBonus(Attack,3)"),
    ]:text+=entry('ESC_'+name,'StatusData',dict(StatusType='BOOST',StackId='ESC_'+name,Boosts=boosts,StatusPropertyFlags='DisableCombatlog;DisablePortraitIndicator;DisableOverhead'))
    write(PUBLIC / 'Stats/Generated/Data/Status_BOOST.txt', text)
    interrupts=''
    for rank in (2,3):
        interrupts+=entry(f'Interrupt_ESC_Counter{rank}','InterruptData',dict(DisplayName=handle('counter/'+str(rank),'清辉反击' if rank==2 else '星河反击')+';1',Description=handle('counter/'+str(rank)+'/description','攻击落空或被剑气护体化解时，可用剑气反击18米内的攻击者。反击不消耗动作、反应或剑元。')+';1',Icon=icon('skill_taixuan_qinghui' if rank==2 else 'skill_taixuan_xinghe'),InterruptContext='OnCastHit',InterruptContextScope='Self',Container='YesNoDecision',Conditions=f"HasStatus('ESC_COUNTER_RANK{rank}',context.Observer) and not HasShieldEquipped(context.Observer) and Enemy(context.Source,context.Observer) and HasFunctor(StatsFunctorType.DealDamage) and HasLastAttackTriggered() and not AnyEntityIsItem() and not HasAnyStatus({{'SG_Incapacitated','SG_Polymorph'}},context.Observer) and not SpellId('Target_ESC_Counter2') and not SpellId('Target_ESC_Counter3')",Properties=f'UseSpell(SWAP,Target_ESC_Counter{rank},true,true,true)',Cost='',Stack='ESC_Counter',InterruptDefaultValue='Enabled;Ask',EnableContext='OnStatusApplied;OnStatusRemoved'))
    write(PUBLIC/'Stats/Generated/Data/Interrupt.txt',interrupts)


def generate_equipment():
    lines = ['new equipment "EQP_CC_ESC"', 'add initialweaponset "Melee"']
    for name in ['WPN_Longsword', 'ARM_Leather_Body', 'ARM_Boots_Leather', 'OBJ_Potion_Healing',
                 'ARM_Camp_Body', 'ARM_Camp_Shoes', 'OBJ_Backpack_CampSupplies']:
        lines += ['add equipmentgroup', f'add equipment entry "{name}"']
    write(PUBLIC / 'Stats/Generated/Equipment.txt', '\n'.join(lines) + '\n')


def generate_art(texconv):
    root, rows = document('IconUVList')
    atlas = Image.new('RGBA', (1024, 1024))
    staging = REPO / 'build/sword-cultivator/icons'
    staging.mkdir(parents=True, exist_ok=True)
    index = []
    for aid, a in assets.items():
        if a['status'] != 'complete':
            raise ValueError('Unfinished art: ' + aid)
        if a['kind'] == 'illustration':
            dst = MODULE / 'GUI/Assets/Illustrations' / (icon(aid) + '.png')
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ART / a['master'], dst)
            index.append(dict(asset=aid, icon=icon(aid), illustration=str(dst.relative_to(SOURCE))))
            continue
        number = len(rows)
        x, y = (number % 16) * 64, (number // 16) * 64
        badge = a['kind'] == 'badge'
        selected_stem = Path(a['master']).stem
        hotbar = ART / 'exports' / ('class_hotbar_64' if badge else 'hotbar_64') / (selected_stem + '.png')
        with Image.open(hotbar) as img:
            atlas.paste(img.convert('RGBA'), (x, y))
        n = ET.SubElement(rows, 'node', id='IconUV')
        attr(n, 'MapKey', 'FixedString', icon(aid))
        for name, value in [('U1', (x + .5)/1024), ('U2', (x + 63.5)/1024), ('V1', (y + .5)/1024), ('V2', (y + 63.5)/1024)]:
            attr(n, name, 'float', value)
        outputs = {}
        if badge:
            branch = 'common' if aid == 'badge_sword_cultivator' else aid.removeprefix('badge_')
            class_name = MOD if branch == 'common' else 'ESC_' + BRANCHES[branch]['english']
            for size, subdir in [('class_300', 'ClassIcons'), ('class_hotbar_64', 'ClassIcons/hotbar')]:
                dst = MODULE / 'GUI/Assets' / subdir / (class_name + '.png')
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ART / 'exports' / size / (selected_stem + '.png'), dst)
                outputs[subdir] = str(dst.relative_to(SOURCE))
        else:
            for export, subdir in [('controller_144', 'ControllerUIIcons/skills_png'), ('tooltip_380', 'Tooltips/Icons')]:
                png = staging / (icon(aid) + '.png')
                shutil.copy2(ART / 'exports' / export / (selected_stem + '.png'), png)
                for quality in ('Assets', 'AssetsLowRes'):
                    dst = MODULE / 'GUI' / quality / subdir
                    dst.mkdir(parents=True, exist_ok=True)
                    subprocess.run([str(texconv), '-nologo', '-y', '-f', 'BC3_UNORM', '-m', '1', '-o', str(dst), str(png)], check=True, capture_output=True)
                outputs[export] = str((MODULE / 'GUI/Assets' / subdir / (icon(aid) + '.dds')).relative_to(SOURCE))
        index.append(dict(asset=aid, icon=icon(aid), selected=a['master'], sha256=hashlib.sha256((ART/a['master']).read_bytes()).hexdigest(), outputs=outputs))
    info = ET.SubElement(root, 'region', id='TextureAtlasInfo')
    info_rows = ET.SubElement(ET.SubElement(info, 'node', id='root'), 'children')
    for nodeid, fields in [('TextureAtlasIconSize', [('Height','int32',64),('Width','int32',64)]),
                           ('TextureAtlasTextureSize', [('Height','int32',1024),('Width','int32',1024)]),
                           ('TextureAtlasPath', [('Path','string','Assets/Textures/Icons/ESC_Icons.dds'),('UUID','FixedString',guid('atlas'))])]:
        n = ET.SubElement(info_rows, 'node', id=nodeid)
        for name, typ, value in fields:
            attr(n, name, typ, value)
    xml(PUBLIC / 'GUI/ESC_Icons.lsx', root)
    atlas.save(staging / 'ESC_Icons.png')
    dst = PUBLIC / 'Assets/Textures/Icons'
    dst.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(texconv), '-nologo', '-y', '-f', 'BC3_UNORM', '-m', '0', '-o', str(dst), str(staging / 'ESC_Icons.png')], check=True, capture_output=True)
    write(ROOT / 'asset-bindings.json', json.dumps(index, ensure_ascii=False, indent=2) + '\n')
    cover = next(a for a in assets.values() if a['id'] == 'cover_lineage')
    with Image.open(ART / cover['master']) as image:
        image.convert('RGB').resize((640, 360), Image.Resampling.LANCZOS).save(ROOT / 'thumbnail.png')


def generate_icon_registry():
    # PAK names must match the atlas and bank paths exactly, even on Windows.
    texture_dir = PUBLIC / 'Assets/Textures/Icons'
    texture = next(p for p in texture_dir.iterdir() if p.name.lower() == 'esc_icons.dds')
    if texture.name != 'ESC_Icons.dds':
        temporary = texture.with_name('ESC_Icons.rename-tmp')
        texture.replace(temporary)
        temporary.replace(texture_dir / 'ESC_Icons.dds')
    # Match the generated texture-resource format used by the installed
    # Witcher and Saber class mods, including dimensions and a standalone LSF.
    root, rows = document('TextureBank')
    root.find('.//node').set('id', 'TextureBank')
    n = ET.SubElement(rows, 'node', id='Resource')
    for field, typ, value in [('ID','FixedString',guid('atlas')),('Name','LSString','ESC_Icons'),
                              ('SourceFile','LSString',f'Public/{FOLDER}/Assets/Textures/Icons/ESC_Icons.dds')]:
        attr(n, field, typ, value)
    for field, typ, value in [('SRGB','bool',False), ('Streaming','bool',True),
                              ('Template','FixedString','ESC_Icons'), ('Type','int32',1),
                              ('Width','int32',1024), ('Height','int32',1024), ('Depth','int32',1)]:
        attr(n, field, typ, value)
    xml(PUBLIC / f'Content/[PAK]_Generated_{MODULE_UUID}/{guid("atlas")}.lsx', root)
    # Retire only the old ESC atlas bank to avoid registering the UUID twice.
    for extension in ('.lsx', '.lsf'):
        old = PUBLIC / ('Content/UI/[PAK]_ESC_UI/_merged' + extension)
        if old.is_file():
            old.unlink()


def generate_class_art(texconv):
    # The running Toolkit requests Class<Name>.DDS; official docs require DDS in both quality roots.
    staging=REPO/'build/sword-cultivator/class-icons';staging.mkdir(parents=True,exist_ok=True)
    binding_path=ROOT/'asset-bindings.json'
    bindings=json.loads(binding_path.read_text(encoding='utf-8')) if binding_path.exists() else []
    binding_map={row['asset']:row for row in bindings}
    for aid,a in assets.items():
        if a['kind']!='badge': continue
        branch='common' if aid=='badge_sword_cultivator' else aid.removeprefix('badge_')
        class_name=MOD if branch=='common' else 'ESC_'+BRANCHES[branch]['english']
        selected_stem=Path(a['master']).stem
        for export,subdir in [('class_300','ClassIcons'),('class_hotbar_64','ClassIcons/hotbar')]:
            for stem in [class_name,'Class'+class_name]:
                png=staging/(stem+'.png');shutil.copy2(ART/'exports'/export/(selected_stem+'.png'),png)
                for quality in ('Assets','AssetsLowRes'):
                    dest=MODULE/'GUI'/quality/subdir;dest.mkdir(parents=True,exist_ok=True)
                    # Noesis metadata indexes PNG paths; keep each alias beside its DDS.
                    shutil.copy2(png,dest/png.name)
                    subprocess.run([str(texconv),'-nologo','-y','-f','BC7_UNORM_SRGB','-m','1','-o',str(dest),str(png)],check=True,capture_output=True)
                    output=dest/(stem+'.dds')
                    output.replace(dest/(stem+'.DDS'))
                    if aid in binding_map and stem.startswith('Class'):
                        binding_map[aid].setdefault('outputs',{})[quality+'/'+subdir]=str((dest/(stem+'.DDS')).relative_to(SOURCE))
        # Passive and choice icons also request the regular tooltip/controller paths.
        for side,subdir in [(380,'Tooltips/Icons'),(144,'ControllerUIIcons/skills_png')]:
            png=staging/(icon(aid)+'.png')
            with Image.open(ART/'exports/class_300'/(selected_stem+'.png')) as source:
                source.resize((side,side),Image.Resampling.LANCZOS).save(png)
            for quality in ('Assets','AssetsLowRes'):
                dest=MODULE/'GUI'/quality/subdir;dest.mkdir(parents=True,exist_ok=True)
                shutil.copy2(png,dest/png.name)
                subprocess.run([str(texconv),'-nologo','-y','-f','BC3_UNORM','-m','1','-o',str(dest),str(png)],check=True,capture_output=True)
                if aid in binding_map:
                    binding_map[aid].setdefault('outputs',{})[quality+'/'+subdir]=str((dest/(icon(aid)+'.dds')).relative_to(SOURCE))
    if bindings: write(binding_path,json.dumps(bindings,ensure_ascii=False,indent=2)+'\n')


def generate_resource_art(texconv):
    # The resource panel resolves a hard-coded name in Shared/Resources.
    for aid, resource in [('resource_sword_yuan','ESC_SwordYuan'),('resource_frenzy','ESC_Frenzy')]:
        source=ART/'exports/hotbar_64'/(Path(assets[aid]['master']).stem+'.png')
        for quality in ('Assets','AssetsLowRes'):
            # Game.pak resolves all four resource states separately.
            for state in ('','Highlight','Missing','Used'):
                dest=MODULE/'GUI'/quality/'Shared/Resources'/state;dest.mkdir(parents=True,exist_ok=True)
                png=dest/(resource+'.png');shutil.copy2(source,png)
                subprocess.run([str(texconv),'-nologo','-y','-f','BC7_UNORM_SRGB','-m','1','-o',str(dest),str(png)],check=True,capture_output=True)
                (dest/(resource+'.dds')).replace(dest/(resource+'.DDS'))


def generate_gui_metadata():
    # Native schema is verified from Shared.pak Mods/Shared/GUI/metadata.lsf.
    root=ET.Element('save')
    ET.SubElement(root,'version',major='4',minor='8',revision='0',build='500')
    config=ET.SubElement(ET.SubElement(root,'region',id='config'),'node',id='config')
    rows=ET.SubElement(ET.SubElement(ET.SubElement(config,'children'),'node',id='entries'),'children')
    keys=set()
    for path in sorted((MODULE/'GUI').rglob('*')):
        if path.suffix.lower() not in ('.dds','.png'): continue
        with Image.open(path) as img: width,height=img.size
        key=path.relative_to(MODULE/'GUI').as_posix()
        for alias in [key]+([str(Path(key).with_suffix('.png')).replace('\\','/')] if path.suffix.lower()=='.dds' else []):
            if alias in keys: continue
            keys.add(alias)
            obj=ET.SubElement(rows,'node',id='Object');attr(obj,'MapKey','FixedString',alias)
            child=ET.SubElement(ET.SubElement(obj,'children'),'node',id='entries')
            for field,typ,value in [('h','int16',height),('w','int16',width),('mipcount','int8',1)]: attr(child,field,typ,value)
    xml(MODULE/'GUI/metadata.lsx',root)


def generate_localization():
    for language, offset in [('Chinese', 0), ('English', 1)]:
        root = ET.Element('contentList')
        for h, texts in sorted(loca.items()):
            ET.SubElement(root, 'content', contentuid=h, version='1').text = texts[offset]
        xml(MODULE / 'Localization' / language / (MOD + '.xml'), root)


def generate_condition_errors():
    descriptions = {
        ('ESC_ARMOR_BLOCKED', 'True'): ('装备盾牌或中甲、重甲时无法使用。', 'Unavailable while using a shield or medium or heavy armor.'),
        ('ESC_MAIN_SWORD', 'False'): ('需要装备主手剑。', 'Requires a main-hand sword.'),
        ('ESC_OFFHAND_SWORD', 'False'): ('需要装备副手剑。', 'Requires an off-hand sword.'),
        ('ESC_QI_MODE', 'False'): ('需要处于气剑状态。', 'Requires Qi Sword mode.'),
        ('ESC_IN_FLIGHT', 'False'): ('需要处于御剑飞行状态。', 'Requires Sword Flight.'),
        ('ESC_CHAIN_LIANCHENG', 'False'): ('需要先施展连城剑招。', 'Requires an active Liancheng sequence.'),
        ('ESC_CHAIN_WUSHENG', 'False'): ('需要先施展无生剑招。', 'Requires an active Wusheng sequence.'),
    }
    for stacks in range(1, 16):
        descriptions[(f'ESC_FRENZY_AT_LEAST_{stacks}', 'False')] = (
            f'需要至少 {stacks} 层癫狂。', f'Requires at least {stacks} Frenzy stacks.')
    for identifier, translations in PLAYER_TEXT['condition_descriptions'].items():
        status, polarity = identifier.rsplit('_',1)
        descriptions[(status,polarity)] = tuple(translations)
    required = set()
    for spell_file in sorted((PUBLIC / 'Stats/Generated/Data').glob('Spell_*.txt')):
        for conditions in re.findall(r'^data "RequirementConditions" "([^"]*)"$',
                                     spell_file.read_text(encoding='utf-8'), re.M):
            for match in re.finditer(r"(not )?HasStatus\('([^']+)'", conditions):
                required.add((match.group(2), 'True' if match.group(1) else 'False'))
    unknown = required - descriptions.keys()
    if unknown:
        raise ValueError(f'Missing condition error text: {sorted(unknown)}')
    root, children = document('ConditionErrors')
    for status, polarity in sorted(required):
        identifier = f'CE_Status_{status}_{polarity}'
        obj = ET.SubElement(children, 'node', id='ConditionErrors')
        attr(obj, 'UUID', 'guid', guid('condition-error/' + identifier))
        attr(obj, 'Identifier', 'FixedString', identifier)
        attr(obj, 'DisplayName', 'TranslatedString',
             handle('condition-error/' + identifier, *descriptions[(status, polarity)]))
        attr(obj, 'ErrorDescriptionType', 'uint8', 0)
    xml(PUBLIC / 'ErrorDescriptions/ConditionErrors.lsx', root)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--texconv', type=Path, default=Path('E:/SteamLibrary/steamapps/common/Baldurs Gate 3 Toolkit/texconv.exe'))
    parser.add_argument('--skip-art', action='store_true')
    args = parser.parse_args()
    compiled_vfx = PUBLIC / 'Assets/Effects/Effects_Banks/Sword'
    authored = {(style, phase) for style in STYLES for phase in PHASES
                if (compiled_vfx / (effect_name(style, phase) + '.lsfx')).is_file()}
    if authored:
        vfx = generate_vfx_resources(sorted({s for s, _ in authored}),
                                     sorted({p for _, p in authored}), SOURCE)
        enabled = {(style, phase) for style, phases in vfx['registered'].items()
                   for phase in phases}
        # A trajectory needs both a compiled trail and impact plus its template.
        enabled = {pair for pair in enabled
                   if pair[1] != 'projectile' or pair[0] in vfx['projectiles']}
    else:
        vfx, enabled = {'registered': {}, 'projectiles': {}}, set()
    set_enabled_phases(enabled)
    write(ROOT / 'vfx-bindings.json', json.dumps(vfx, ensure_ascii=False, indent=2) + '\n')
    for generate in [generate_meta, generate_classes, generate_progressions, generate_progression_descriptions, generate_resource, generate_level_maps, generate_passives,
                     generate_spells, generate_statuses, generate_equipment, generate_condition_errors]:
        generate()
    if not args.skip_art:
        generate_art(args.texconv)
    generate_icon_registry()
    generate_class_art(args.texconv)
    generate_resource_art(args.texconv)
    cover=ROOT/'thumbnail.png'
    if not cover.is_file():
        raise FileNotFoundError(f'Mod Manager cover art missing: {cover}')
    with Image.open(cover) as image:
        if image.format!='PNG' or image.width<1 or image.height<1:
            raise ValueError(f'Mod Manager cover art must be a valid PNG: {cover}')
        image.verify()
    for destination in [SOURCE/'Projects'/FOLDER/'thumbnail.png',MODULE/'mod_publish_logo.png']:
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(cover,destination)
    generate_gui_metadata()
    generate_localization()
    spec = dict(module=MODULE_UUID, folder=FOLDER, version64=VERSION64,
                publishHandle=PUBLISH_HANDLE, capacities=CAPACITIES,
                resource=guid('resource/sword_yuan'), flightResource=guid('resource/flight'), chainMoveResource=guid('resource/chain_move'), chainStatuses={'liancheng':'ESC_CHAIN_LIANCHENG','wusheng':'ESC_CHAIN_WUSHENG'},
                opportunityResource=guid('resource/sword_opportunity'), classes={b:guid('class/'+b) for b in ['common',*BRANCHES]},
                branches=BRANCHES, spells={key: {**value, 'stat': spellid(key)} for key,value in SPELLS.items()},
                aliases=aliases,
                design_sha256={name: hashlib.sha256((REPO/'docs'/name).read_bytes()).hexdigest()
                               for name in ['20-eastern-sword-cultivator-gdd.md', '21-player-facing-skill-text-draft.md']})
    write(ROOT / 'implementation-spec.json', json.dumps(spec, ensure_ascii=False, indent=2) + '\n')
    write(MODULE / 'ScriptExtender/Lua/GeneratedSpec.json', json.dumps(spec, ensure_ascii=False) + '\n')
    print(f'Generated {FOLDER}: 5 classes, 53 progression nodes, {len(SPELLS)} named techniques, {len(loca)} localization entries')


if __name__ == '__main__':
    main()
