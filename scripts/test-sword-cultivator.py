"""Run the actual Lua rules and verify all generated references and selected art."""
import ast
import hashlib
import itertools
import importlib.util
import json
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image
from sword_cultivator_spec import BRANCHES, CAPACITIES, FOLDER, MOD, MODULE_UUID, PUBLISH_HANDLE, SPELLS, VERSION64, guid

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'build/test-tools'))
from lupa import LuaRuntime

SOURCE = REPO / 'mods' / MOD / 'Source'
LUA = SOURCE / 'Mods' / FOLDER / 'ScriptExtender/Lua'


class RulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = LuaRuntime(unpack_returned_tuples=True)
        cls.rules = cls.lua.execute((LUA / 'Rules.lua').read_text(encoding='utf-8'))

    def table(self, obj):
        return self.lua.table_from(obj, recursive=True)

    def test_level_specific_progression(self):
        for level, capacity in enumerate([0,6,10,14,18,24,26,28,30,40,44,50], 1):
            self.assertEqual(self.rules.capacity(level), capacity)
        self.assertEqual(self.rules.hitpoints(12,3,'taixuan'),202)
        self.assertEqual(self.rules.hitpoints(12,3,'tianqing'),280)
        self.assertEqual(self.rules.hitpoints(12,3,'xueyan'),180)
        self.assertEqual(self.rules.hitpoints(12,3,'xingge'),124)
        self.assertEqual(self.rules.hitpoints(2,3,'tianqing'),22)
        self.assertEqual(self.rules.opportunities(5,'taixuan'),3)
        self.assertEqual(self.rules.opportunities(10,'taixuan'),4)
        self.assertEqual(self.rules.opportunities(12,'xingge'),2)

    def test_rounding_and_capacity(self):
        self.assertEqual(self.rules.breath(7,'taixuan',True,True),11)
        self.assertEqual(self.rules.breath(12,'tianqing',True,True),35)
        self.assertEqual(self.rules.breath(12,'taixuan',False,True),13)
        self.assertEqual(self.rules.breath(12,'xingge',True,False),50)
        self.assertEqual(self.rules.recover(48,50,9),(50,2))
        self.assertEqual(self.rules.reduce(99,.2,self.table([.3])),55)

    def test_frenzy_snapshot_and_blood_cost(self):
        snapshot=self.rules.spendFrenzy(15,15)
        self.assertEqual(snapshot.attack,7)
        self.assertEqual(snapshot.remaining,0)
        self.assertEqual(snapshot.bonus,2.25)
        self.assertEqual(self.rules.frenzyGained(10,100,False),3)
        self.assertEqual(self.rules.frenzyGained(9,100,False),1)
        self.assertEqual(self.rules.frenzyGained(10,100,True),0)
        self.assertEqual(self.rules.bloodCost(10,100,3),(None,3))
        self.assertEqual(self.rules.bloodCost(11,100,14),(1,15))

    def test_siphon_combines_final_stage_damage(self):
        self.assertEqual(self.rules.siphon(3,51,100,0),(11,1,6))
        self.assertEqual(self.rules.siphon(11,51,100,18),(13,2,20))
        self.assertEqual(self.rules.siphon(11,0,100,18),(0,0,18))
        self.assertEqual(self.rules.shieldAbsorb(12,15),(0,3))
        self.assertEqual(self.rules.frenzyGained(0,100,False),0)

    def test_additive_damage_and_multiplicative_defense(self):
        multiplier=self.rules.damageMultiplier(self.table(dict(held=15,spent=15,regular=False,level=12)))
        self.assertAlmostEqual(multiplier,3.25)
        self.assertEqual(72*multiplier,234)
        self.assertAlmostEqual(self.rules.damageMultiplier(self.table(dict(weakpoint=True,domain=True,regular=True,level=12))),1.55)
        self.assertAlmostEqual(self.rules.baseReduction(12,'xueyan',15),.55)
        self.assertEqual(self.rules.reduce(100,.55,self.table([.2])),36)

    def test_damage_share_after_friend_defenses(self):
        self.assertEqual(self.rules.share(101,.45,.2,self.table([.30])),(56,25,45))
        best=self.rules.chooseShare(self.table([dict(percent=.4,sequence=9),dict(percent=.45,sequence=1),dict(percent=.45,sequence=2)]))
        self.assertEqual(best.sequence,2)

    def test_domain_expires_before_fifth_hit(self):
        domain=self.rules.applyDuration(None,10,4)
        hits=1
        for turn in range(11,15):
            hits+=int(self.rules.tickDuration(domain,turn))
        self.assertEqual(hits,4)
        domain.used['friend']=True
        refreshed=self.rules.applyDuration(domain,12,4)
        self.assertTrue(refreshed.used['friend'])

    def test_guard_weaker_cast_does_not_refresh(self):
        strong=self.table(dict(rank=3,ac=5,reduction=.4,dice='6d8',attack=3))
        weak=self.table(dict(rank=1,ac=2,reduction=.2))
        current,changed=self.rules.guard(None,strong,10)
        self.assertTrue(changed)
        current,changed=self.rules.guard(current,weak,11)
        self.assertFalse(changed)
        self.assertEqual(current.expires,12)

    def test_team_reward_gates_and_refresh_exception(self):
        mark=self.rules.recastFollowup(1)
        self.assertTrue(self.rules.followup(mark,'A'))
        self.assertFalse(self.rules.followup(mark,'A'))
        self.assertTrue(self.rules.followup(mark,'B'))
        refreshed=self.rules.recastFollowup(2)
        self.assertTrue(self.rules.followup(refreshed,'A'))
        kills=self.table({})
        self.assertTrue(self.rules.once(kills,'enemy'))
        self.assertFalse(self.rules.once(kills,'enemy'))

    def test_immunity_does_not_consume_line_position(self):
        damage=self.rules.falloff(174,self.table([True,False,True,False,False]))
        self.assertEqual(list(damage.values()),[0,174,0,87,43])

    def test_line_and_takeoff_geometry(self):
        self.assertEqual(self.rules.inLine(self.table([15,0,.5]),self.table([0,0,0]),self.table([30,0,0]),2),(True,.5))
        self.assertFalse(self.rules.inLine(self.table([31,0,0]),self.table([0,0,0]),self.table([30,0,0]),2))
        self.assertFalse(self.rules.canFly(self.table([[3,0,0]]),self.table([0,0,0])))
        self.assertTrue(self.rules.canFly(self.table([[3.01,0,0]]),self.table([0,0,0])))


class GeneratedDataTest(unittest.TestCase):
    @staticmethod
    def _native_spell_rows():
        text='\n'.join(p.read_text(encoding='utf-8') for p in
            (SOURCE/'Public'/FOLDER/'Stats/Generated/Data').glob('Spell_*.txt'))
        return {name:dict(re.findall(r'^data "([^"]+)" "([^"]*)"$',body,re.M))
            for name,body in re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)',text,re.S)}

    def _active_sword_basis(self,body,main,off,force=False,enemy=True):
        # Evaluate actual generated Boolean gates, not generator helper output.
        # This does not prove native query refresh, weapon riders or VFX.
        status={'ESC_MAIN_SWORD':main,'ESC_OFFHAND_SWORD':off,'ESC_FORCE_MODE':force}
        basis=[];procs=[]
        for clause in body.split(';'):
            found=re.fullmatch(r'IF\((.+)\):(DealDamage|ExecuteWeaponFunctors)\((.*)\)',clause)
            if not found: continue
            condition,functor,arguments=found.groups()
            if functor=='DealDamage' and not any(value in arguments.split(',')[0]
                for value in ('MainMeleeWeapon','OffhandMeleeWeapon','2d6+WisdomModifier')): continue
            condition=re.sub(r"HasStatus\('([^']+)',context.Source\)",
                lambda m:str(status[m[1]]),condition).replace('Enemy()',str(enemy))
            expression=ast.parse(condition,mode='eval')
            self.assertTrue(all(isinstance(n,(ast.Expression,ast.BoolOp,ast.UnaryOp,
                ast.Constant,ast.And,ast.Or,ast.Not)) for n in ast.walk(expression)),condition)
            if eval(compile(expression,'<native Boolean fixture>','eval'),{'__builtins__':{}}):
                if functor=='DealDamage': basis.append(tuple(arguments.split(',')[:2]))
                else: procs.append(arguments)
        return basis,procs

    def _assert_sword_basis(self,name,row,alias,fields=('SpellSuccess',)):
        fixed_off=alias.get('hand')=='off' or alias.get('bonusOnly',False)
        checked=0
        for field in fields:
            body=row.get(field,'')
            if not any(value in body for value in ('MainMeleeWeapon','OffhandMeleeWeapon','2d6+WisdomModifier')):
                continue
            for main,off,force,enemy in itertools.product((False,True),repeat=4):
                basis,procs=self._active_sword_basis(body,main,off,force,enemy)
                hand=('off' if off else 'qi') if fixed_off else ('main' if main else 'off' if off else 'qi')
                expected={'main':'MainMeleeWeapon','off':'OffhandMeleeWeapon','qi':'2d6+WisdomModifier'}[hand]
                self.assertEqual(len(basis),1,(name,field,main,off,force,enemy,basis))
                self.assertIn(expected,basis[0][0],(name,field,basis))
                self.assertEqual(procs,[] if hand=='qi' else ['MainHand' if hand=='main' else 'OffHand'],
                    (name,field,main,off,procs))
                if hand=='qi':
                    self.assertEqual(basis[0][1],'Force' if force or 'ESC_FORCE_MODE' not in body else 'Necrotic',name)
                if name.startswith('Target_ESC_TiandiStage') or name=='Target_ESC_tianqing_tiandi':
                    self.assertEqual('/4' in basis[0][0],not enemy,(name,field,enemy,basis))
                checked+=1
        self.assertGreater(checked,0,name)
        return checked

    def test_class_details_register_the_progression_table(self):
        public = SOURCE/'Public'/FOLDER
        classes = ET.parse(public/'ClassDescriptions/ClassDescriptions.lsx')
        descriptions = ET.parse(public/'Progressions/ProgressionDescriptions.lsx')
        registrations = descriptions.findall('.//node[@id="ProgressionDescription"]')
        class_rows = classes.findall('.//node[@id="ClassDescription"]')
        self.assertEqual(len(registrations), len(class_rows))
        for main in class_rows:
            name = main.find('attribute[@id="Name"]').get('value')
            matches = [row for row in registrations if row.find('attribute[@id="Type"]').get('value') == name]
            self.assertEqual(len(matches), 1, name)
            registration = matches[0]
            table = main.find('attribute[@id="ProgressionTableUUID"]').get('value')
            self.assertEqual(registration.find('attribute[@id="ProgressionTableId"]').get('value'), table)
            self.assertNotEqual(table, main.find('attribute[@id="UUID"]').get('value'))
            self.assertIsNone(registration.find('attribute[@id="ExactMatch"]'))
            hidden = registration.find('attribute[@id="Hidden"]')
            self.assertNotEqual(hidden.get('value').lower() if hidden is not None else 'false', 'true')
            for field in ('DisplayName', 'Description'):
                self.assertEqual(registration.find(f'attribute[@id="{field}"]').get('handle'),
                                 main.find(f'attribute[@id="{field}"]').get('handle'))

    def test_published_module_identity_and_dependency_handle(self):
        meta=ET.parse(SOURCE/'Mods'/FOLDER/'meta.lsx')
        def value(node,key):
            attr=node.find(f"attribute[@id='{key}']")
            self.assertIsNotNone(attr,key)
            return attr.get('value')
        own=meta.find(".//node[@id='ModuleInfo']")
        dependency=meta.find(".//node[@id='Dependencies']/children/node[@id='ModuleShortDesc']")
        self.assertIsNotNone(own)
        self.assertIsNotNone(dependency)
        self.assertEqual(value(own,'UUID'),MODULE_UUID)
        self.assertEqual(value(own,'Folder'),FOLDER)
        self.assertEqual(value(own,'PublishHandle'),str(PUBLISH_HANDLE))
        self.assertEqual(value(own,'Version64'),str(VERSION64))
        self.assertEqual(value(dependency,'Name'),'GustavX')
        self.assertEqual(value(dependency,'PublishHandle'),'0')
        generated=json.loads((LUA/'GeneratedSpec.json').read_text(encoding='utf-8'))
        self.assertEqual(generated['version64'],VERSION64)
        self.assertEqual(generated['publishHandle'],PUBLISH_HANDLE)

    def test_native_spell_lists_grant_only_gdd_branch_and_level(self):
        generated=json.loads((LUA/'GeneratedSpec.json').read_text(encoding='utf-8'))
        keys={row['stat']:key for key,row in generated['spells'].items()}
        keys.update({stat:value['key'] for stat,value in generated.get('aliases',{}).items()})
        lists={}
        for node in ET.parse(SOURCE/'Public'/FOLDER/'Lists/SpellLists.lsx').findall('.//node[@id="SpellList"]'):
            attrs={a.get('id'):a.get('value') for a in node.findall('attribute')}
            lists[attrs['UUID']]=set(filter(None,attrs.get('Spells','').split(';')))
        # Independent GDD-derived grant expectations. Do not call spells_at:
        # the generator's grant mapping itself is the behavior under test.
        expected={
            'common':{2:'tiaoxi',5:'sword_flight'},
            'taixuan':{3:'taixuan_zhaoxi',4:'taixuan_qinghui taixuan_guiyuan',5:'control_release',
                6:'taixuan_liuguang',7:'taixuan_xinghe',8:'taixuan_jiuxiao',9:'taixuan_taiqing',12:'taixuan_yixiantian'},
            'tianqing':{3:'tianqing_nifeng tianqing_nixi',4:'tianqing_wanjun',5:'control_release',
                6:'tianqing_tianbeng',7:'tianqing_tianfeng',8:'tianqing_lietian',9:'tianqing_tianjian',12:'tianqing_bafang tianqing_tiandi'},
            'xueyan':{3:'xueyan_luexue xueyan_damage_mode',4:'xueyan_chuanshen xueyan_huichao',5:'control_release',
                6:'xueyan_liancheng',7:'xueyan_nixue',8:'xueyan_ranxue',9:'xueyan_xuehai',12:'xueyan_wusheng'},
            'xingge':{3:'xingge_wenlu xingge_xiangfu',4:'xingge_huifeng',6:'xingge_chengfeng',
                7:'xingge_tongzhou',8:'xingge_fuchen',9:'xingge_fengyu',12:'xingge_zhangjian'}}
        tables={guid('table/'+branch):branch for branch in expected}
        for node in ET.parse(SOURCE/'Public'/FOLDER/'Progressions/Progressions.lsx').findall('.//node[@id="Progression"]'):
            attrs={a.get('id'):a.get('value') for a in node.findall('attribute')}
            if attrs.get('IsMulticlass')=='true': continue
            branch=tables[attrs['TableUUID']];level=int(attrs['Level']);actual=set();actual_stats=set()
            if branch=='common' and level==1:
                self.assertNotIn('SelectAbilityBonus(',attrs.get('Selectors',''),
                    'The GDD does not grant additional class ability scores at creation')
            for list_uuid in re.findall(r'AddSpells\(([0-9a-f-]{36})',attrs.get('Selectors','')):
                self.assertIn(list_uuid,lists)
                for stat in lists[list_uuid]:
                    self.assertIn(stat,keys)
                    actual.add(keys[stat]);actual_stats.add(stat)
                    self.assertFalse(generated['spells'][keys[stat]].get('retired',False),stat)
                    self.assertFalse(generated.get('aliases',{}).get(stat,{}).get('internal',False),stat)
            self.assertEqual(actual,set(expected[branch].get(level,'').split()),f'{branch} level {level}')
            regular={'taixuan':'taixuan_zhaoxi','tianqing':'tianqing_nifeng','xueyan':'xueyan_luexue','xingge':'xingge_wenlu'}
            if branch in regular and level==3:
                key=regular[branch];root=generated['spells'][key]['stat'];bonus=root+'_RangedOff_Bonus'
                self.assertTrue({root,bonus}<=actual_stats,(branch,actual_stats))
                self.assertEqual({n for n in actual_stats if n.endswith('_Bonus')},{bonus},branch)
        passive=(SOURCE/'Public'/FOLDER/'Stats/Generated/Data/Passive.txt').read_text(encoding='utf-8')
        self.assertIn('UnlockSpell('+generated['spells']['yujian']['stat']+')',passive)

    def test_introductory_grants_expire_at_branch_upgrades_without_obsolete_spell_lists(self):
        source=SOURCE/'Public'/FOLDER
        generated=json.loads((LUA/'GeneratedSpec.json').read_text(encoding='utf-8'))
        text=(source/'Stats/Generated/Data/Passive.txt').read_text(encoding='utf-8')
        passives={name:dict(re.findall(r'^data "([^"]+)" "([^"]*)"$',body,re.M))
            for name,body in re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)',text,re.S)}
        for passive,key in (('ESC_P_StarterSword','yujian'),
                            ('ESC_P_StarterGuard','qi_guard')):
            self.assertEqual(passives[passive]['Properties'],'IsHidden',passive)
            self.assertEqual(passives[passive]['Boosts'],'UnlockSpell('+generated['spells'][key]['stat']+')',passive)
        self.assertEqual(passives['ESC_P_StarterMelee']['Properties'],'IsHidden')
        self.assertEqual(passives['ESC_P_StarterMelee']['Boosts'],'')
        rows=[{a.get('id'):a.get('value') for a in node.findall('attribute')}
              for node in ET.parse(source/'Progressions/Progressions.lsx').findall('.//node[@id="Progression"]')]
        for row in rows:
            if row['TableUUID']==guid('table/common') and row['Level']=='1':
                self.assertIn('ESC_P_StarterSword',row['PassivesAdded'].split(';'))
                self.assertNotIn('ESC_P_StarterMelee',row['PassivesAdded'].split(';'))
                self.assertNotIn('AddSpells(',row.get('Selectors',''))
            elif row['TableUUID']==guid('table/common') and row['Level']=='2':
                self.assertIn('ESC_P_StarterGuard',row['PassivesAdded'].split(';'))
            elif row['TableUUID'] in {guid('table/'+branch) for branch in BRANCHES} and row['Level']=='3':
                self.assertEqual(set(row['PassivesRemoved'].split(';')),{'ESC_P_StarterSword','ESC_P_StarterMelee'})
            elif row['TableUUID']==guid('table/taixuan') and row['Level']=='4':
                self.assertIn('ESC_P_StarterGuard',row['PassivesRemoved'].split(';'))
        granted={spell for node in ET.parse(source/'Lists/SpellLists.lsx').findall('.//node[@id="SpellList"]')
                 for a in node.findall('attribute') if a.get('id')=='Spells' for spell in a.get('value','').split(';')}
        self.assertFalse(any(spell.startswith('Shout_ESC_Offhand_') for spell in granted))
        for key in ('yujian','sword_strike','qi_guard','tianqing_xushi','qi_sword','focus_target'):
            self.assertNotIn(generated['spells'][key]['stat'],granted,key)

    def test_regular_sword_containers_keep_bonus_offhand_children_and_pay_only_selected_action(self):
        stats=self._native_spell_rows()
        generated=json.loads((LUA/'GeneratedSpec.json').read_text(encoding='utf-8'))
        translations={a.get('contentuid'):a.text for a in ET.parse(SOURCE/'Mods'/FOLDER/'Localization/Chinese'/(MOD+'.xml')).getroot()}
        expected={'taixuan_zhaoxi':'Projectile_ESC_taixuan_zhaoxi_RangedOff_Bonus',
            'tianqing_nifeng':'Zone_ESC_tianqing_nifeng_RangedOff_Bonus',
            'xueyan_luexue':'Projectile_ESC_xueyan_luexue_RangedOff_Bonus',
            'xingge_wenlu':'Projectile_ESC_xingge_wenlu_RangedOff_Bonus'}
        self.assertEqual({n for n in stats if n.endswith('_Bonus')},set(expected.values()))
        for key,bonus in expected.items():
            name=generated['spells'][key]['stat'];root=stats[name];row=stats[bonus]
            self.assertEqual(root['UseCosts'],'ActionPoint:1',name)
            self.assertEqual(root['SpellRoll'],'Attack(AttackType.RangedSpellAttack)',name)
            self.assertEqual(generated['aliases'][name]['hand'],'auto',name)
            for spell in (root,row):
                self.assertEqual(spell['ContainerSpells'],'')
                self.assertEqual(spell['SpellContainerID'],'')
            self.assertEqual(row['UseCosts'],'BonusActionPoint:1',bonus)
            alias=generated['aliases'][bonus]
            self.assertEqual(alias['key'],key);self.assertTrue(alias['offhand'])
            self.assertTrue(alias['bonusOnly']);self.assertEqual(alias['hand'],'off')
            self.assertIn('副手追加',translations[row['DisplayName'].split(';')[0]],bonus)
            description=translations[row['Description'].split(';')[0]]
            self.assertIn('不获得连贯出剑',description,bonus)
            self.assertIn('追加一次远程飞剑攻击',description,bonus)
            self._assert_sword_basis(name,root,generated['aliases'][name])
            self._assert_sword_basis(bonus,row,alias)
            self.assertNotIn('Shout_ESC_Offhand_'+key,stats)
        for prefix,distance in (('wusheng',24),('liancheng',18)):
            spell='Projectile_ESC_'+prefix+'_ContinueRanged'
            self.assertNotIn('Target_ESC_'+prefix+'_ContinueMelee',stats)
            self.assertEqual(float(stats[spell]['TargetRadius']),distance,spell)
            self.assertNotRegex(translations[stats[spell]['Description'].split(';')[0]],r'\d+米',spell)
            self.assertTrue(stats[spell]['ExtraDescriptionParams'],spell)
        self.assertEqual(stats['Projectile_ESC_ChainMove']['TargetRadius'],'6')

    def test_native_spell_inheritance_cannot_add_offhand_costs_healing_text_or_foreign_container_children(self):
        text='\n'.join(path.read_text(encoding='utf-8') for path in (SOURCE/'Public'/FOLDER/'Stats/Generated/Data').glob('Spell_*.txt'))
        stats={name:dict(re.findall(r'^data "([^"]+)" "([^"]*)"$',body,re.M))
            for name,body in re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)',text,re.S)}
        damage_targets=save_spells=0;containers=set()
        for name,row in stats.items():
            # Explicit empty overrides are required: omitting these fields
            # inherits the native parent's offhand cost and animation events.
            for field in ('DualWieldingUseCosts','AlternativeCastTextEvents'):
                self.assertIn(field,row,name+'.'+field)
                self.assertEqual(row[field],'',name+'.'+field)
            damage=';'.join(row.get(field,'') for field in ('SpellSuccess','SpellFail','SpellProperties'))
            if row['SpellType']=='Target' and 'DealDamage(' in damage:
                damage_targets+=1
                self.assertEqual(row.get('TooltipPermanentWarnings'),'',name)
                self.assertEqual(row.get('VerbalIntent'),'Damage',name)
            ability=re.search(r'SavingThrow\(Ability\.([A-Za-z]+),',row.get('SpellRoll',''))
            if ability:
                save_spells+=1
                self.assertEqual(row.get('TooltipAttackSave'),ability.group(1),name)
            self.assertIn('ContainerSpells',row,name)
            children=row['ContainerSpells']
            if children:
                containers.add(name)
                self.assertIn('IsLinkedSpellContainer',row['SpellFlags'],name)
                for child in children.split(';'):
                    self.assertIn(child,stats,name+' child '+child)
                    self.assertRegex(child,r'^[A-Za-z]+_ESC_',name)
            else:
                self.assertNotIn('IsLinkedSpellContainer',row['SpellFlags'],name)
        self.assertGreater(damage_targets,10)
        self.assertGreater(save_spells,5)
        self.assertEqual(containers,{'Shout_ESC_xueyan_nixue','Projectile_ESC_xueyan_wusheng',
            'Target_ESC_xueyan_huichao','Projectile_ESC_tianqing_tianjian_Main','Projectile_ESC_tianqing_tianjian_Off'})

    def test_native_stats_values_fit_observed_toolkit_2048_byte_limit(self):
        failures=[]
        for file in (SOURCE/'Public'/FOLDER/'Stats/Generated/Data').glob('*.txt'):
            entry=''
            for line in file.read_text(encoding='utf-8').splitlines():
                match=re.match(r'new entry "([^"]+)"',line)
                if match: entry=match.group(1)
                match=re.match(r'data "([^"]+)" "(.*)"$',line)
                if match and len(match.group(2).encode('utf-8'))>2048:
                    failures.append(f'{file.name}:{entry}.{match.group(1)}={len(match.group(2).encode("utf-8"))} bytes')
        self.assertEqual(failures,[], '\n'.join(failures))

    def test_status_requirements_have_localized_native_condition_errors(self):
        required=set()
        for file in (SOURCE/'Public'/FOLDER/'Stats/Generated/Data').glob('Spell_*.txt'):
            for conditions in re.findall(r'^data "RequirementConditions" "([^"]*)"$',
                                         file.read_text(encoding='utf-8'),re.M):
                for match in re.finditer(r"(not )?HasStatus\('([^']+)'",conditions):
                    required.add(f'CE_Status_{match.group(2)}_{"True" if match.group(1) else "False"}')
        self.assertEqual(required,{'CE_Status_ESC_CHAIN_LIANCHENG_False','CE_Status_ESC_CHAIN_WUSHENG_False',
            'CE_Status_ESC_IN_FLIGHT_False'} | {'CE_Status_ESC_FRENZY_AT_LEAST_'+str(i)+'_False' for i in range(1,16)})
        for status in ('ESC_MAIN_SWORD','ESC_OFFHAND_SWORD','ESC_ARMOR_BLOCKED'):
            self.assertFalse(any(status in identifier for identifier in required),status)
        self.assertNotIn('CE_Status_ESC_QI_MODE_False',required)
        relative='ErrorDescriptions/ConditionErrors'
        native={}
        for node in ET.parse(SOURCE/'Public'/FOLDER/(relative+'.lsx')).findall('./region/node/children/node'):
            attrs={a.get('id'):a for a in node.findall('attribute')}
            identifier=attrs['Identifier'].get('value')
            self.assertNotIn(identifier,native)
            self.assertEqual(attrs['ErrorDescriptionType'].get('value'),'0')
            native[identifier]=attrs
        self.assertEqual(set(native),required)
        self.assertEqual(len({attrs['UUID'].get('value') for attrs in native.values()}),len(required))
        editor={}
        for node in ET.parse(SOURCE/'Editor/Mods'/FOLDER/(relative+'.tbl')).findall('./stat_objects/stat_object'):
            fields={field.get('name'):field for field in node.findall('./fields/field')}
            identifier=fields['Identifier'].get('value')
            self.assertNotIn(identifier,editor)
            editor[identifier]=fields
        self.assertEqual(set(editor),required)
        translations={language:{entry.get('contentuid'):entry.text for entry in ET.parse(
            SOURCE/'Mods'/FOLDER/'Localization'/language/(MOD+'.xml')).getroot()}
            for language in ('Chinese','English')}
        for identifier,attrs in native.items():
            fields=editor[identifier]
            self.assertEqual(fields['UUID'].get('value'),attrs['UUID'].get('value'))
            self.assertEqual(fields['DisplayName'].get('handle'),attrs['DisplayName'].get('handle'))
            self.assertEqual(fields['ErrorDescriptionType'].get('value'),'0')
            for language in translations:
                self.assertTrue(translations[language].get(attrs['DisplayName'].get('handle')),
                                f'{language}: {identifier}')
        for identifier,skill in (('CE_Status_ESC_CHAIN_LIANCHENG_False','血影连城'),
            ('CE_Status_ESC_CHAIN_WUSHENG_False','血魇·无生')):
            handle=native[identifier]['DisplayName'].get('handle')
            self.assertIn(skill,translations['Chinese'][handle])

    def test_equipment_requirements_use_native_slots_and_refresh_for_equipment_and_statuses(self):
        text='\n'.join(path.read_text(encoding='utf-8') for path in
            (SOURCE/'Public'/FOLDER/'Stats/Generated/Data').glob('Spell_*.txt'))
        stats={name:dict(re.findall(r'^data "([^"]+)" "([^"]*)"$',body,re.M))
            for name,body in re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)',text,re.S)}
        native_weapon_checks=0;checked_slots={}
        for name,row in stats.items():
            condition=row.get('RequirementConditions','')
            for status in ('ESC_MAIN_SWORD','ESC_OFFHAND_SWORD','ESC_ARMOR_BLOCKED'):
                self.assertNotIn(status,condition,name)
            self.assertNotIn('ConditionResult(',condition,name)
            self.assertNotIn('ConditionError(',condition,name)
            events=set(row.get('RequirementEvents','').split(';'))
            if any(fn+'(' in condition for fn in ('IsWeaponOfProficiencyGroup','HasShieldEquipped','HasHeavyArmor','HasMediumArmor')):
                self.assertTrue({'OnEquip','OnUnequip'}<=events,name)
            if 'HasStatus(' in condition:
                self.assertTrue({'OnStatusApplied','OnStatusRemoved'}<=events,name)
            for groups,slot in re.findall(r"IsWeaponOfProficiencyGroup\('([^']+)', GetItemInEquipmentSlot\(EquipmentSlot\.(\w+), context.Source\)\)",condition):
                native_weapon_checks+=1
                checked_slots.setdefault(name,set()).add(slot)
                self.assertEqual(set(groups.split('|')),{'Longswords','Shortswords','Greatswords','Rapiers','Scimitars'},name)
                self.assertIn(slot,('MeleeMainHand','MeleeOffHand'),name)
            if 'IsWeaponOfProficiencyGroup(' in condition:
                self.assertNotIn('GetActiveWeapon(',condition,name)
        self.assertEqual(native_weapon_checks,8)
        self.assertEqual(set(checked_slots),{'Projectile_ESC_taixuan_zhaoxi_RangedOff_Bonus',
            'Zone_ESC_tianqing_nifeng_RangedOff_Bonus','Projectile_ESC_xueyan_luexue_RangedOff_Bonus',
            'Projectile_ESC_xingge_wenlu_RangedOff_Bonus'})
        for slots in checked_slots.values(): self.assertEqual(slots,{'MeleeMainHand','MeleeOffHand'})
        passive=(SOURCE/'Public'/FOLDER/'Stats/Generated/Data/Passive.txt').read_text(encoding='utf-8')
        basic=dict(re.findall(r'^data "([^"]+)" "([^"]*)"$',re.search(
            r'new entry "ESC_P_basic_defense"\n(.*?)(?=new entry |\Z)',passive,re.S).group(1),re.M))
        self.assertNotIn('ESC_ARMOR_BLOCKED',passive)
        self.assertEqual(basic['Boosts'],'AC(1)')
        self.assertEqual(basic['BoostContext'],'OnEquip;OnCreate')
        for armor in ('HasHeavyArmor(context.Source)','HasMediumArmor(context.Source)'):
            self.assertIn(armor,basic['BoostConditions'])

    def test_native_equipment_condition_truth_table_preserves_hands_qi_and_branch_armor_rules(self):
        # Boolean native-query stand-ins exercise generated expression logic.
        # This does not establish the Toolkit parser or engine query behavior.
        text='\n'.join(path.read_text(encoding='utf-8') for path in
            (SOURCE/'Public'/FOLDER/'Stats/Generated/Data').glob('Spell_*.txt'))
        stats={name:dict(re.findall(r'^data "([^"]+)" "([^"]*)"$',body,re.M))
            for name,body in re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)',text,re.S)}
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute("context={Source='source',Target='enemy'}; EquipmentSlot={MeleeMainHand='main',MeleeOffHand='off'}")
        state={}
        def source_only(actor):
            self.assertEqual(actor,'source')
        def item(slot,actor):
            source_only(actor)
            return state[slot]
        def armor(kind,actor):
            source_only(actor)
            return state['armor']==kind
        def passive(name,actor):
            source_only(actor)
            return name=='ESC_P_Branch_'+state['branch']
        def shield(actor):
            source_only(actor)
            return state['shield']
        def status(name,actor):
            source_only(actor)
            self.assertEqual(name,'ESC_QI_MODE')
            return state['qi']
        lua.globals().GetItemInEquipmentSlot=item
        lua.globals().IsWeaponOfProficiencyGroup=lambda groups,weapon: bool(weapon and weapon in groups.split('|'))
        lua.globals().HasShieldEquipped=shield
        lua.globals().HasMediumArmor=lambda actor: armor('MediumArmor',actor)
        lua.globals().HasHeavyArmor=lambda actor: armor('HeavyArmor',actor)
        lua.globals().HasPassive=passive
        lua.globals().HasStatus=status
        generated=json.loads((LUA/'GeneratedSpec.json').read_text(encoding='utf-8'))
        roots=[generated['spells'][key]['stat'] for key in
            ('yujian','sword_strike','taixuan_zhaoxi','tianqing_nifeng','xueyan_luexue','xingge_wenlu')]
        names=roots+[name for name,alias in generated['aliases'].items() if alias.get('bonusOnly')]
        evaluate={name:lua.eval('function() return '+stats[name]['RequirementConditions']+' end') for name in names}
        swords={'Longswords','Shortswords','Greatswords','Rapiers','Scimitars'}
        for branch in ('','taixuan','tianqing','xueyan','xingge'):
            for armor_kind in ('','LightArmor','MediumArmor','HeavyArmor'):
                for main in (*sorted(swords),'Daggers','Longbows',''):
                    for off in ('Shortswords','Daggers',''):
                        for qi in (False,True):
                            for has_shield in (False,True):
                                state.update(branch=branch,armor=armor_kind,main=main,off=off,qi=qi,shield=has_shield)
                                equipment_ok=not has_shield and not (branch in ('taixuan','xingge') and armor_kind in ('MediumArmor','HeavyArmor'))
                                for name,fn in evaluate.items():
                                    if name.endswith('_Bonus'):
                                        hand_ok=main in swords and off in swords
                                    else: hand_ok=True
                                    self.assertEqual(fn(),equipment_ok and hand_ok,(name,dict(state)))

    def test_starting_longsword_is_equipped_without_a_choice_button(self):
        class_file=SOURCE/'Public'/FOLDER/'ClassDescriptions/ClassDescriptions.lsx'
        classes=ET.parse(class_file).findall('.//node[@id="ClassDescription"]')
        main=next(node for node in classes if any(
            a.get('id')=='Name' and a.get('value')==MOD for a in node.findall('attribute')))
        self.assertEqual(next(a.get('value') for a in main.findall('attribute')
            if a.get('id')=='ClassEquipment'),'EQP_CC_ESC')
        equipment=(SOURCE/'Public'/FOLDER/'Stats/Generated/Equipment.txt').read_text(encoding='utf-8')
        self.assertIn('new equipment "EQP_CC_ESC"',equipment)
        self.assertIn('add initialweaponset "Melee"',equipment)
        self.assertIn('add equipment entry "WPN_Longsword"',equipment)
        generated=json.loads((LUA/'GeneratedSpec.json').read_text(encoding='utf-8'))
        self.assertNotIn('startingSpells',generated)
        self.assertNotIn('startingWeapons',generated)
        self.assertFalse(any('starting_sword_' in row.get('key','') for row in generated['aliases'].values()))
        shout=(SOURCE/'Public'/FOLDER/'Stats/Generated/Data/Spell_Shout.txt').read_text(encoding='utf-8')
        status=(SOURCE/'Public'/FOLDER/'Stats/Generated/Data/Status_BOOST.txt').read_text(encoding='utf-8')
        self.assertNotIn('StartingSword',shout)
        self.assertNotIn('ESC_CAST_STARTING_SWORD',status)
        self.assertIn('new entry "ESC_STARTING_SWORD_CHOSEN"',status,
            'Keep the inert permanent marker prototype for existing saved characters')

    def test_native_skill_and_ability_lists_use_real_comma_enum_schema(self):
        expected={'SkillLists':('Skills',{'Athletics','Acrobatics','Insight','Perception','Survival','Medicine','Intimidation'}),
            'AbilityLists':('Abilities',{'Strength','Dexterity','Constitution','Intelligence','Wisdom','Charisma'})}
        for filename,(field,values) in expected.items():
            node=ET.parse(SOURCE/'Public'/FOLDER/'Lists'/(filename+'.lsx')).find('.//attribute[@id="'+field+'"]')
            parsed={s.strip() for s in node.get('value').split(',')}
            self.assertEqual(parsed,values,filename)

    def test_multiclass_entry_keeps_shared_sword_without_starting_equipment_or_save_bonuses(self):
        source=SOURCE/'Public'/FOLDER
        lists={}
        for node in ET.parse(source/'Lists/SpellLists.lsx').findall('.//node[@id="SpellList"]'):
            attrs={a.get('id'):a.get('value') for a in node.findall('attribute')}
            lists[attrs['UUID']]=set(filter(None,attrs.get('Spells','').split(';')))
        rows=[]
        for node in ET.parse(source/'Progressions/Progressions.lsx').findall('.//node[@id="Progression"]'):
            attrs={a.get('id'):a.get('value') for a in node.findall('attribute')}
            if attrs.get('IsMulticlass')=='true': rows.append(attrs)
        self.assertEqual(len(rows),1)
        row=rows[0];spells=set()
        for list_uuid in re.findall(r'AddSpells\(([0-9a-f-]{36})',row.get('Selectors','')): spells.update(lists[list_uuid])
        generated=json.loads((LUA/'GeneratedSpec.json').read_text(encoding='utf-8'))
        self.assertEqual(spells,set())
        self.assertIn('ESC_P_StarterSword',row['PassivesAdded'].split(';'))
        self.assertNotIn('ESC_P_StarterMelee',row['PassivesAdded'].split(';'))
        self.assertNotIn('SelectSkills(',row.get('Selectors',''))
        self.assertNotIn('SelectAbilityBonus(',row.get('Selectors',''))
        self.assertNotIn('SavingThrow',row.get('Boosts',''))

    def test_four_custom_resource_definitions_are_separate_pools(self):
        rows=[]
        for node in ET.parse(SOURCE/'Public'/FOLDER/'ActionResourceDefinitions/ActionResourceDefinitions.lsx').findall('./region/node/children/node'):
            rows.append({a.get('id'):a.get('value') for a in node.findall('attribute')})
        self.assertEqual({row['Name'] for row in rows},{'ESC_SwordYuan','ESC_SwordOpportunity','ESC_FlightMovement','ESC_ChainMovement'})
        self.assertEqual(len({row['UUID'] for row in rows}),4)
        yuan=next(row for row in rows if row['Name']=='ESC_SwordYuan')
        self.assertEqual(yuan['ShowOnActionResourcePanel'],'true')

    def test_editor_tables_preserve_all_formal_lsx_fields(self):
        editor=SOURCE/'Editor/Mods'/FOLDER
        for relative in ('ClassDescriptions/ClassDescriptions','Progressions/Progressions','Progressions/ProgressionDescriptions',
            'Lists/SkillLists','Lists/AbilityLists','Lists/SpellLists','ActionResourceDefinitions/ActionResourceDefinitions',
            'CharacterCreationPresets/AbilityDistributionPresets'):
            rows={}
            for row in ET.parse(editor/(relative+'.tbl')).findall('./stat_objects/stat_object'):
                fields={f.get('name'):f for f in row.findall('./fields/field')}
                uuid=fields['UUID'].get('value')
                self.assertNotIn(uuid,rows)
                rows[uuid]=fields
            native=ET.parse(SOURCE/'Public'/FOLDER/(relative+'.lsx')).findall('./region/node/children/node')
            self.assertEqual(len(rows),len(native),relative)
            for row in native:
                uuid=row.find('attribute[@id="UUID"]').get('value');fields=rows[uuid]
                for attr in row.findall('attribute'):
                    key=attr.get('id')
                    if key=='Name':
                        if relative.startswith(('ClassDescriptions','ActionResourceDefinitions')): key='NameFS'
                        elif not relative.startswith('Lists/'): key='FSName'
                    if key=='ParentGuid': key='ParentUUID'
                    self.assertIn(key,fields,f'{relative}:{uuid}:{key}')
                    for property in ('value','handle','version'):
                        if attr.get(property) is not None:
                            expected,actual=attr.get(property),fields[key].get(property)
                            if attr.get('type')=='bool': expected,actual=expected.lower(),actual.lower()
                            self.assertEqual(actual,expected,f'{relative}:{uuid}:{key}.{property}')
                subclasses=[a.get('value') for a in row.findall('./children/node[@id="SubClasses"]/children/node/attribute[@id="Object"]')]
                if subclasses: self.assertEqual(fields['SubClasses'].get('value').split(';'),subclasses)

    def test_editor_stats_preserve_formal_stats_and_safe_strings(self):
        for file in (SOURCE/'Public'/FOLDER/'Stats/Generated/Data').glob('*.txt'):
            prefix=''
            if file.stem.startswith('Spell_'):
                kind=file.stem.removeprefix('Spell_');relative='Stats/SpellData/'+kind+'.stats';prefix=kind+'_'
            elif file.stem in ('Passive','Interrupt'): relative='Stats/Stats/'+file.stem+'.stats'
            else: relative='Stats/StatusData/'+file.stem+'.stats'
            editor={}
            for node in ET.parse(SOURCE/'Editor/Mods'/FOLDER/relative).findall('./stat_objects/stat_object'):
                fields={f.get('name'):f for f in node.findall('./fields/field')}
                name=prefix+fields['Name'].get('value')
                self.assertNotIn(name,editor);editor[name]=fields
            blocks=re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)',file.read_text(encoding='utf-8'),re.S)
            self.assertEqual(set(editor),{name for name,_ in blocks})
            for name,body in blocks:
                for key,value in re.findall(r'^data "([^"]+)" "([^"]*)"$',body,re.M):
                    if key in ('SpellType','StatusType'): continue
                    key='WeaponType' if key=='WeaponTypes' else key
                    self.assertIn(key,editor[name],f'{name}.{key}')
                    field=editor[name][key]
                    actual=field.get('value')
                    if field.get('type')=='TranslatedStringTableFieldDefinition':
                        if value=='':
                            self.assertEqual(field.get('clear_inherited_value'),'true',f'{name}.{key}')
                            self.assertIn(field.get('handle'),(None,''),f'{name}.{key}')
                            actual=field.get('value','')
                        else:
                            actual=field.get('handle')+';'+field.get('version')
                    self.assertEqual(actual,value,f'{name}.{key}')
                    self.assertLessEqual(len((actual or '').encode('utf-8')),2048,f'{name}.{key}')

    def test_native_counter_is_optional_free_and_excludes_counter_recursion(self):
        stats=SOURCE/'Public'/FOLDER/'Stats/Generated/Data'
        interrupts={name:dict(re.findall(r'^data "([^"]+)" "([^"]*)"$',body,re.M))
            for name,body in re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)',(stats/'Interrupt.txt').read_text(encoding='utf-8'),re.S)}
        spells={name:dict(re.findall(r'^data "([^"]+)" "([^"]*)"$',body,re.M))
            for name,body in re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)',(stats/'Spell_Target.txt').read_text(encoding='utf-8'),re.S)}
        for rank in (2,3):
            interrupt=interrupts['Interrupt_ESC_Counter'+str(rank)]
            spell=spells['Target_ESC_Counter'+str(rank)]
            self.assertEqual(interrupt['Cost'],'')
            self.assertEqual(spell['UseCosts'],'')
            self.assertEqual(interrupt['Container'],'YesNoDecision')
            self.assertIn('Ask',interrupt['InterruptDefaultValue'])
            for suffix in (2,3):
                self.assertIn("not SpellId('Target_ESC_Counter"+str(suffix)+"')",interrupt['Conditions'])

    def test_native_recommended_attributes_are_valid_twenty_seven_point_buy(self):
        source=SOURCE/'Public'/FOLDER
        generated=json.loads((LUA/'GeneratedSpec.json').read_text(encoding='utf-8'))
        points={8:0,9:1,10:2,11:3,12:4,13:5,14:7,15:9}
        rows=[{a.get('id'):a.get('value') for a in node.findall('attribute')}
              for node in ET.parse(source/'CharacterCreationPresets/AbilityDistributionPresets.lsx').findall('.//node[@id="AbilityDistributionPreset"]')]
        self.assertEqual({row['ClassUUID'] for row in rows},set(generated['classes'].values()))
        self.assertEqual(len(rows),5)
        for row in rows:
            abilities=[int(row[name]) for name in ('Strength','Dexterity','Constitution','Intelligence','Wisdom','Charisma')]
            self.assertTrue(all(value in points for value in abilities))
            self.assertEqual(sum(points[value] for value in abilities),27)
            self.assertEqual(abilities,[8,14,15,8,15,10])
        default=ET.parse(source/'DefaultValues/Skills.lsx').find('.//node[@id="DefaultValue"]')
        attrs={a.get('id'):a.get('value') for a in default.findall('attribute')}
        self.assertEqual(attrs['Add'].split(';')[:2],['Insight','Perception'])
        fields={a.get('name'):a.get('value') for a in ET.parse(SOURCE/'Editor/Mods'/FOLDER/'DefaultValues/Skills.tbl').findall('.//field')}
        self.assertEqual(fields['DefaultValues'],attrs['Add'])
        self.assertEqual(fields['ProgressionUUID'],attrs['TableUUID'])

    def test_native_tianjian_jump_subspells_pay_once_and_impacts_keep_damage(self):
        spells=self._native_spell_rows()
        generated=json.loads((LUA/'GeneratedSpec.json').read_text(encoding='utf-8'))
        root=spells['Projectile_ESC_tianqing_tianjian']
        self.assertEqual(root['UseCosts'],'ActionPoint:1;ESC_SwordYuan:10')
        self.assertEqual(root['ContainerSpells'],'');self.assertEqual(root['SpellContainerID'],'')
        self.assertIn('IsJump',root['SpellFlags'])
        self.assertEqual(root['TargetRadius'],'24')
        self.assertEqual(root['SpellProperties'],'GROUND:CreateExplosion(Projectile_ESC_TianjianImpact)')
        self.assertNotIn('DealDamage(',root['SpellSuccess']+root['SpellProperties'])
        for suffix in ('Main','Off'):
            legacy='Projectile_ESC_tianqing_tianjian_'+suffix
            self.assertEqual(spells[legacy]['UseCosts'],'')
            self.assertEqual(spells[legacy]['ContainerSpells'],'Projectile_ESC_tianqing_tianjian')
            self.assertTrue(generated['aliases'][legacy]['legacy'])
        for name in ('Projectile_ESC_TianjianImpact','Projectile_ESC_TianjianImpact_Off'):
            impact=spells[name]
            self.assertEqual(impact['UseCosts'],'')
            self.assertEqual(impact['SpellRoll'],'not SavingThrow(Ability.Dexterity,SourceSpellDC())')
            self.assertIn('DealDamage(26d8,Force,Magical)',impact['SpellSuccess'])
            self.assertIn('DealDamage((26d8)/2,Force,Magical)',impact['SpellFail'])
            self.assertEqual(generated['aliases'][name]['hand'],'auto')
            self._assert_sword_basis(name,impact,generated['aliases'][name],('SpellSuccess','SpellFail'))
            for main,off in itertools.product((False,True),repeat=2):
                basis,_=self._active_sword_basis(impact['SpellFail'],main,off)
                self.assertIn('/2',basis[0][0],name)

    def test_native_weapon_functors_follow_selected_hand_and_exclude_pure_qi(self):
        spells=self._native_spell_rows()
        generated=json.loads((LUA/'GeneratedSpec.json').read_text(encoding='utf-8'))
        checked=0
        for name,row in spells.items():
            body=';'.join(row.get(field,'') for field in ('SpellSuccess','SpellFail','SpellProperties'))
            self.assertNotIn('MeleeOffHandWeaponRange',body,name)
            if any(value in body for value in ('MainMeleeWeapon','OffhandMeleeWeapon','2d6+WisdomModifier')):
                checked+=1
                self._assert_sword_basis(name,row,generated['aliases'].get(name,{}),
                    ('SpellSuccess','SpellFail','SpellProperties'))
                if 'Attack(' in row['SpellRoll']:
                    self.assertEqual(row['SpellRoll'],'Attack(AttackType.RangedSpellAttack)',name)
            elif 'DealDamage(' in body:
                self.assertNotIn('ExecuteWeaponFunctors(',body,name)
        self.assertGreater(checked,20)

    def test_native_liuguang_and_tianbeng_stages_are_independent_single_target_attacks_with_one_root_cost(self):
        spells=self._native_spell_rows()
        generated=json.loads((LUA/'GeneratedSpec.json').read_text(encoding='utf-8'))
        liuguang=spells[generated['spells']['taixuan_liuguang']['stat']]
        self.assertEqual((liuguang['AmountOfTargets'],liuguang['ProjectileCount']),('1','1'))
        self.assertEqual(liuguang['UseCosts'],'ActionPoint:1;ESC_SwordYuan:10')
        for name in (generated['spells']['taixuan_liuguang']['stat'],'Target_ESC_LiuguangStage'):
            row=spells[name]
            self.assertEqual(row['SpellRoll'],'Attack(AttackType.RangedSpellAttack)')
            self.assertIn('DealDamage(4d8,Force,Magical)',row['SpellSuccess'])
            self.assertIn('ApplyStatus(ESC_HIT_MARKER,100,0)',row['SpellSuccess'])
            self._assert_sword_basis(name,row,generated['aliases'][name])
        tianbeng=generated['spells']['tianqing_tianbeng']['stat']
        self.assertEqual(tianbeng,'Target_ESC_tianqing_tianbeng')
        self.assertEqual(spells[tianbeng]['ContainerSpells'],'')
        self.assertEqual(spells[tianbeng]['UseCosts'],'ActionPoint:1;ESC_SwordYuan:10')
        self.assertNotIn(tianbeng+'_Main',spells);self.assertNotIn(tianbeng+'_Off',spells)
        helpers={'Target_ESC_LiuguangStage':'taixuan_liuguang',
            'Target_ESC_TianbengCone':'tianqing_tianbeng','Target_ESC_TianbengCone_Off':'tianqing_tianbeng'}
        for name,dice in ((tianbeng,'32d8'),('Target_ESC_TianbengCone','18d8'),('Target_ESC_TianbengCone_Off','18d8')):
            row=spells[name]
            self.assertEqual(row['SpellType'],'Target');self.assertEqual(row['AmountOfTargets'],'1')
            self.assertEqual(row['SpellRoll'],'Attack(AttackType.RangedSpellAttack)')
            self.assertIn('DealDamage('+dice+',Force,Magical)',row['SpellSuccess'])
            self.assertIn('SavingThrow(Ability.Strength,SourceSpellDC())',row['SpellSuccess'])
            self.assertIn('ApplyStatus(ESC_SAVEFAIL_TIANQING_TIANBENG,100,0)',row['SpellSuccess'])
            self._assert_sword_basis(name,row,generated['aliases'][name])
        grants={spell for attr in ET.parse(SOURCE/'Public'/FOLDER/'Lists/SpellLists.lsx').findall('.//attribute[@id="Spells"]')
                for spell in attr.get('value','').split(';')}
        for name,parent in helpers.items():
            for field in ('UseCosts','Cooldown','ContainerSpells'):
                self.assertEqual(spells[name][field],'',name+'.'+field)
            self.assertTrue(generated['aliases'][name]['internal'],name)
            self.assertEqual(generated['aliases'][name]['parent'],parent,name)
            self.assertNotIn(name,grants)
        self.assertFalse(any(name.startswith('Zone_ESC_tianqing_tianbeng') for name in spells))

    def test_shared_sword_strike_native_variants_have_attack_damage_marker_and_weapon_functor(self):
        spells=self._native_spell_rows()
        generated=json.loads((LUA/'GeneratedSpec.json').read_text(encoding='utf-8'))
        grants={spell for attr in ET.parse(SOURCE/'Public'/FOLDER/'Lists/SpellLists.lsx').findall('.//attribute[@id="Spells"]')
                for spell in attr.get('value','').split(';')}
        self.assertTrue(generated['spells']['sword_strike']['retired'])
        for key,distance in (('yujian',18),('sword_strike',3)):
            name=generated['spells'][key]['stat'];row=spells[name]
            self.assertNotIn(name+'_Main',spells);self.assertNotIn(name+'_Off',spells)
            self.assertEqual(row['SpellRoll'],'Attack(AttackType.RangedSpellAttack)',name)
            self.assertIn('ApplyStatus(ESC_HIT_MARKER,100,0)',row['SpellSuccess'],name)
            self.assertEqual(row['UseCosts'],'ActionPoint:1',name)
            self.assertEqual(row['TargetRadius'],str(distance),name)
            self._assert_sword_basis(name,row,generated['aliases'][name])
            self.assertNotIn(name,grants)

    def test_all_techniques_have_stats_icons_and_text(self):
        stats='\n'.join(p.read_text(encoding='utf-8') for p in (SOURCE/'Public'/FOLDER/'Stats/Generated/Data').glob('*.txt'))
        names=re.findall(r'new entry "([^\"]+)"',stats)
        self.assertEqual(len(names),len(set(names)))
        generated=json.loads((LUA/'GeneratedSpec.json').read_text(encoding='utf-8'))
        for row in generated['spells'].values():
            self.assertIn(row['stat'],names)
        for alias in generated.get('aliases',{}):
            self.assertIn(alias,names)
        atlas=ET.parse(SOURCE/'Public'/FOLDER/'GUI/ESC_Icons.lsx')
        icons={a.get('value') for a in atlas.findall('.//attribute[@id="MapKey"]')}
        self.assertEqual(len(icons),79)
        for value in re.findall(r'data "Icon" "([^\"]+)"',stats):
            self.assertIn(value,icons)
        for language in ('English','Chinese'):
            translations={a.get('contentuid'):a.text for a in ET.parse(SOURCE/'Mods'/FOLDER/'Localization'/language/(MOD+'.xml')).getroot()}
            for h in re.findall(r'h[0-9a-fg]{36}',stats):
                self.assertTrue(translations.get(h),h)

    def test_four_branches_level_chain_and_feats(self):
        root=ET.parse(SOURCE/'Public'/FOLDER/'Progressions/Progressions.lsx')
        tables={}
        for n in root.findall('.//node[@id="Progression"]'):
            a={a.get('id'):a.get('value') for a in n.findall('attribute')}
            if a.get('IsMulticlass')=='true': continue
            tables.setdefault(a['TableUUID'],{})[int(a['Level'])]=a
        for branch in BRANCHES:
            self.assertEqual(sorted(tables[guid('table/'+branch)]),list(range(3,13)))
        main=tables[guid('table/common')]
        self.assertEqual(sorted(main),list(range(1,13)))
        self.assertEqual([k for k,v in main.items() if v.get('AllowImprovement')=='true'],[4,8,12])
        total=0
        for level in range(2,13):
            total+=int(re.search(r'ActionResource\(ESC_SwordYuan,(\d+),0\)',main[level]['Boosts']).group(1))
            self.assertEqual(total,CAPACITIES[level-1])

    def test_resource_states_and_badges_have_real_png_dds_and_noesis_metadata(self):
        gui=SOURCE/'Mods'/FOLDER/'GUI'
        metadata=ET.parse(gui/'metadata.lsx')
        keys={a.get('value') for a in metadata.findall('.//attribute[@id="MapKey"]')}
        required=[]
        for quality in ('Assets','AssetsLowRes'):
            for name in ('ESC_SwordYuan','ESC_Frenzy'):
                for state in ('','Highlight/','Used/','Missing/'):
                    for ext in ('.png','.DDS'):
                        required.append(f'{quality}/Shared/Resources/{state}{name}{ext}')
            for name in ('sword_cultivator','taixuan','tianqing','xueyan','xingge'):
                for placement in ('Tooltips/Icons','ControllerUIIcons/skills_png'):
                    for ext in ('.png','.DDS'):
                        required.append(f'{quality}/{placement}/ESC_badge_{name}{ext}')
        self.assertEqual(len(required),72)
        for relative in required:
            with self.subTest(asset=relative):
                path=gui/relative
                self.assertTrue(path.is_file(),relative)
                self.assertIn(relative,keys,relative)
                magic=b'\x89PNG\r\n\x1a\n' if relative.endswith('.png') else b'DDS '
                self.assertEqual(path.read_bytes()[:len(magic)],magic,relative)

    def test_class_icon_metadata_keys_resolve_to_physical_png_and_dds(self):
        gui=SOURCE/'Mods'/FOLDER/'GUI'
        keys={a.get('value') for a in ET.parse(gui/'metadata.lsx').findall('.//attribute[@id="MapKey"]')}
        names=['Class'+MOD]+['ClassESC_'+branch['english'] for branch in BRANCHES.values()]
        for quality in ('Assets','AssetsLowRes'):
            for placement,side in (('ClassIcons',300),('ClassIcons/hotbar',64)):
                for name in names:
                    for ext,magic in (('.png',b'\x89PNG\r\n\x1a\n'),('.DDS',b'DDS ')):
                        relative=f'{quality}/{placement}/{name}{ext}'
                        with self.subTest(asset=relative):
                            self.assertIn(relative,keys)
                            path=gui/relative
                            self.assertTrue(path.is_file(),relative)
                            self.assertEqual(path.read_bytes()[:len(magic)],magic)
                            with Image.open(path) as image:
                                self.assertEqual(image.size,(side,side))

    def test_mod_manager_cover_has_both_toolkit_and_package_bindings(self):
        cover=REPO/'mods'/MOD/'thumbnail.png'
        toolkit=SOURCE/'Projects'/FOLDER/'thumbnail.png'
        package=SOURCE/'Mods'/FOLDER/'mod_publish_logo.png'
        self.assertTrue(cover.is_file())
        self.assertEqual(toolkit.read_bytes(),cover.read_bytes())
        self.assertEqual(package.read_bytes(),cover.read_bytes())
        with Image.open(package) as image:
            self.assertEqual(image.format,'PNG')
            self.assertGreater(image.width,0)
            self.assertGreater(image.height,0)
            image.verify()

    def test_toolkit_install_meta_english_fallback_preserves_source_chinese(self):
        installer=REPO/'scripts/sword-toolkit-environment.py'
        spec=importlib.util.spec_from_file_location('sword_toolkit_environment_test',installer)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source=SOURCE/'Mods'/FOLDER/'meta.lsx'
        original=source.read_bytes()
        converted=module.toolkit_editor_meta_bytes(original)
        get_description=lambda data: ET.fromstring(data).find(
            ".//node[@id='ModuleInfo']/attribute[@id='Description']").get('value')
        self.assertIn('东方剑修',get_description(original))
        self.assertTrue(converted.isascii())
        self.assertEqual(get_description(converted),module.EDITOR_DESCRIPTION)
        self.assertEqual(converted,original.replace(get_description(original).encode('utf-8'),
                                                    module.EDITOR_DESCRIPTION.encode('ascii'),1))
        self.assertEqual(source.read_bytes(),original)

    def test_native_tooltip_damage_preview_has_no_conditional_functors(self):
        stats=SOURCE/'Public'/FOLDER/'Stats/Generated/Data'
        previews={};rows={}
        generated=json.loads((LUA/'GeneratedSpec.json').read_text(encoding='utf-8'))
        for file in stats.glob('Spell_*.txt'):
            for name,body in re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)',file.read_text(encoding='utf-8'),re.S):
                row=dict(re.findall(r'^data "([^"]+)" "([^"]*)"$',body,re.M))
                preview=row.get('TooltipDamageList','')
                previews[name]=preview;rows[name]=row
                self.assertNotIn('IF(',preview,name)
                execution=';'.join(row.get(field,'') for field in ('SpellSuccess','SpellFail','SpellProperties'))
                if 'ESC_FORCE_MODE' in execution and not generated.get('aliases',{}).get(name,{}).get('bonusOnly'):
                    self.assertEqual(preview,'',name)
        generated=json.loads((LUA/'GeneratedSpec.json').read_text(encoding='utf-8'))
        self.assertTrue({row['stat'] for row in generated['spells'].values()}<=set(rows))
        self.assertTrue(set(generated['aliases'])<=set(rows))
        self.assertTrue(any(previews.values()))
        for key in ('xueyan_nixue','xueyan_wusheng'):
            names=[generated['spells'][key]['stat']]+[name for name,alias in generated['aliases'].items() if alias['key']==key]
            for name in names: self.assertEqual(previews[name],'',name)
        translations={a.get('contentuid'):a.text for a in ET.parse(SOURCE/'Mods'/FOLDER/'Localization/Chinese'/(MOD+'.xml')).getroot()}
        for key,spell in generated['spells'].items():
            row=rows[spell['stat']]
            description=translations[row['Description'].split(';')[0]]
            self.assertNotRegex(description,r'\d+级|后期提高|后期恢复',key)
            if spell['base'] or key=='taixuan_qinghui':
                self.assertTrue(row['TooltipDamageList'] or row['ExtraDescriptionParams'],key)
            for field in ('DescriptionParams','ExtraDescriptionParams','TooltipDamageList'):
                self.assertNotIn('IF(',row.get(field,''),(key,field))
            if spell['branch']=='xueyan':
                self.assertNotIn('Necrotic',row['TooltipDamageList'],key)
        for key in ('yujian','sword_strike'):
            self.assertEqual(rows[generated['spells'][key]['stat']]['TooltipDamageList'],'',key)
        for name,alias in generated['aliases'].items():
            key=alias['key'];fixed_bonus=alias.get('bonusOnly',False)
            if fixed_bonus:
                self.assertEqual(alias['hand'],'off',name)
                self.assertIn('DealDamage(OffhandMeleeWeapon,OffhandMeleeWeaponDamageType)',previews[name],name)
                self.assertNotIn('MainMeleeWeapon',previews[name],name)
                if key=='xueyan_luexue':
                    self.assertEqual(previews[name],'DealDamage(OffhandMeleeWeapon,OffhandMeleeWeaponDamageType)')
            elif generated['spells'].get(key,{}).get('base')=='AUTO' or alias.get('hand')=='auto':
                self.assertEqual(previews[name],'',name)
        maps=ET.parse(SOURCE/'Public'/FOLDER/'Levelmaps/LevelMapValues.lsx')
        series={node.find("attribute[@id='Name']").get('value'):node for node in maps.findall('.//node[@id="LevelMapSeries"]')}
        expected={'ESC_ZhaoxiDamage':('2d8','3d8','4d8'),
                  'ESC_NifengDamage':('3d8','4d8','5d8'),
                  'ESC_LuexueDamage':('2d6','3d6','4d6'),
                  'ESC_WenluDamage':('1d4','1d6','2d6')}
        for name,ranks in expected.items():
            node=series[name]
            self.assertEqual(node.find("attribute[@id='PreferredClassUUID']").get('value'),guid('class/common'),name)
            for level,dice in zip((3,5,10),ranks):
                self.assertEqual(node.find(f"attribute[@id='Level{level}']").get('value'),dice,(name,level))

    def test_art_revision_and_source_integrity(self):
        bindings=json.loads((REPO/'mods'/MOD/'asset-bindings.json').read_text(encoding='utf-8'))
        self.assertEqual(len(bindings),81)
        self.assertNotIn('skill_recall_sword',{row['asset'] for row in bindings})
        for binding in bindings:
            if 'selected' in binding:
                source=REPO/'art/static-v1'/binding['selected']
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),binding['sha256'])
                for relative in binding['outputs'].values():
                    self.assertTrue((SOURCE/relative).is_file(),relative)
        selected=next(b for b in bindings if b['asset']=='skill_xueyan_liancheng')
        self.assertTrue(selected['selected'].endswith('-v2.png'))
        atlas=SOURCE/'Public'/FOLDER/'Assets/Textures/Icons/ESC_Icons.dds'
        with Image.open(atlas) as image:
            self.assertEqual(image.size,(1024,1024))
            self.assertEqual(image.convert('RGBA').getchannel('A').getextrema(),(0,255))
        gui=SOURCE/'Mods'/FOLDER/'GUI'
        metadata=ET.parse(gui/'metadata.lsx')
        self.assertFalse(any('ESC_skill_recall_sword' in a.get('value','')
                             for a in metadata.findall('.//attribute[@id="MapKey"]')))
        self.assertFalse(any(p.stem=='ESC_skill_recall_sword' for p in gui.rglob('*')))

    def test_hotbar_atlas_resource_resolves_with_exact_pak_case(self):
        public=SOURCE/'Public'/FOLDER
        atlas=ET.parse(public/'GUI/ESC_Icons.lsx')
        path_node=atlas.find('.//node[@id="TextureAtlasPath"]')
        fields={a.get('id'):a.get('value') for a in path_node.findall('attribute')}
        # is_file() alone masks this regression on Windows; resolve exact names.
        texture=public
        for part in fields['Path'].split('/'):
            self.assertIn(part,{p.name for p in texture.iterdir()})
            texture=texture/part
        bank_path=public/f'Content/[PAK]_Generated_{MODULE_UUID}/{fields["UUID"]}.lsx'
        bank=ET.parse(bank_path).find('.//node[@id="Resource"]')
        resource={a.get('id'):a.get('value') for a in bank.findall('attribute')}
        self.assertEqual(resource['ID'],fields['UUID'])
        self.assertEqual(resource['SourceFile'],texture.relative_to(SOURCE).as_posix())
        # The standalone generated resource must carry its DDS dimensions.
        self.assertEqual((resource['Type'],resource['SRGB'],resource['Streaming']),('1','false','true'))
        with Image.open(texture) as image:
            self.assertEqual((int(resource['Width']),int(resource['Height'])),image.size)
            self.assertEqual(resource['Depth'],'1')
            rgba=image.convert('RGBA')
            for node in atlas.findall('.//node[@id="IconUV"]'):
                uv={a.get('id'):a.get('value') for a in node.findall('attribute')}
                bounds=tuple(int(float(uv[key])*image.size[i%2]) for i,key in enumerate(('U1','V1','U2','V2')))
                self.assertIsNotNone(rgba.crop(bounds).getbbox(),uv['MapKey'])
        header=texture.read_bytes()[:128]
        self.assertEqual(header[:4],b'DDS ')
        self.assertEqual(int.from_bytes(header[28:32],'little'),11)
        old=public/'Content/UI/[PAK]_ESC_UI'
        self.assertFalse((old/'_merged.lsx').exists())
        self.assertFalse((old/'_merged.lsf').exists())

    def test_lua_syntax_all_files(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        compile_lua=lua.eval('function(text,name) local fn,err=load(text,name); if not fn then error(err) end; return true end')
        for path in LUA.glob('*.lua'):
            self.assertTrue(compile_lua(path.read_text(encoding='utf-8'),path.name))


def case_ids(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite): yield from case_ids(item)
        else: yield item.id()


if __name__=='__main__':
    # Bridge tests execute the production listeners against a deterministic test
    # boundary. A pass establishes Lua behavior, never Toolkit/game acceptance.
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    suite.addTests(unittest.defaultTestLoader.discover(str(REPO/'scripts/tests'),pattern='test_*.py'))
    ids=list(case_ids(suite))
    source_extensions={'.lua','.json','.lsx','.lsf','.lsfx','.lsefx','.mei','.group','.xml','.txt','.tbl','.stats','.png','.dds'}
    def source_hashes():
        source_paths=[p for p in SOURCE.rglob('*') if p.is_file() and p.suffix.lower() in source_extensions]
        source_paths.extend([Path(__file__),REPO/'scripts/sword_cultivator_spec.py',
            REPO/'scripts/generate-sword-cultivator.py',REPO/'scripts/sword_spell_presentation.py',REPO/'scripts/sword_tooltips.py',
            REPO/'scripts/generate-sword-vfx.py',REPO/'scripts/sword_vfx_bindings.py',REPO/'scripts/sword_vfx_resources.py',
            REPO/'scripts/tianqing_vfx_design.py',REPO/'scripts/generate-tianqing-vfx.py',
            REPO/'scripts/tianqing_vfx_resources.py',
            REPO/'scripts/compile-tianqing-vfx.ps1',
            REPO/'scripts/tests/test_tianqing_vfx_design.py',
            REPO/'scripts/tests/test_tianqing_vfx_integration.py',
            REPO/'scripts/tests/test_tianqing_runtime_vfx.py',
            REPO/'scripts/tests/test_tianqing_cast_vfx.py',
            REPO/'scripts/tests/test_tianqing_timing_assets.py',
            REPO/'scripts/tests/test_taixuan_world_rain.py',
            REPO/'scripts/tests/test_tiandi_native_event_order.py',
            REPO/'scripts/prepare-sword-toolkit.py',
            REPO/'docs/20-eastern-sword-cultivator-gdd.md',REPO/'docs/21-player-facing-skill-text-draft.md',
            REPO/'scripts/tests/esc_engine_fixture.lua',REPO/'scripts/tests/test_esc_bridge.py',
            REPO/'scripts/tests/test_esc_continuous_strikes.py',
            REPO/'scripts/tests/test_esc_guard_lifecycle.py',REPO/'scripts/tests/test_guard_vfx_binding.py',
            REPO/'scripts/tests/test_toolkit_log_analyzer.py',REPO/'scripts/analyze-sword-toolkit-log.py',
            REPO/'scripts/sword_player_text.json'])
        source_paths.extend((REPO/'scripts').glob('*visual*polish*.py'))
        source_paths.extend((REPO/'scripts/tests').glob('test_*visual*polish*.py'))
        source_paths.append(REPO/'scripts/tests/test_esc_school_visual_lifecycle.py')
        source_paths.extend([REPO/'scripts/sword_projectile_readability.py',
            REPO/'scripts/tests/test_esc_auto_focus.py',
            REPO/'scripts/tests/test_taixuan_native_event_order.py',
            REPO/'scripts/tests/test_tianjian_landing.py',
            REPO/'scripts/tests/test_esc_xueyan_stage_identity.py',
            REPO/'scripts/tests/test_esc_helper_parent_attribution.py',
            REPO/'scripts/tests/test_esc_taiqing_turn_start_delay.py',
            REPO/'scripts/tests/test_esc_bloodsea_turn_start_delay.py',
            REPO/'scripts/tests/test_esc_auto_sword.py',
            REPO/'scripts/tests/test_esc_shield_equipment.py'])
        return {str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else 'missing'
            for p in source_paths}
    hashes=source_hashes()
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    after=source_hashes()
    bridge_module=sys.modules.get('test_esc_bridge')
    bridge_hashes={str((LUA/name).relative_to(REPO)):hashlib.sha256(data).hexdigest()
        for name,data in getattr(bridge_module,'SNAPSHOT',{}).items()}
    changed=hashes!=after or any(hashes.get(name)!=value for name,value in bridge_hashes.items())
    report={'Date':datetime.now(timezone.utc).isoformat(),'EvidenceLayer':'static-and-simulated-lua',
        'TestsRun':result.testsRun,'Failures':len(result.failures),'Errors':len(result.errors),
        'Skipped':len(result.skipped),'Success':result.wasSuccessful() and not changed,
        'Cases':ids,'SourceSHA256':hashes,'BridgeSnapshotSHA256':bridge_hashes,'SourceChangedDuringTests':changed,
        'FailedCases':[case.id() for case,_ in result.failures],
        'ErrorCases':[case.id() for case,_ in result.errors],'ToolkitTest':'not-established',
        'GameTest':'not-established'}
    destination=REPO/'build/sword-cultivator/regression-report.json'
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if changed: print('Source changed during testing; rerun on a stable source snapshot.',file=sys.stderr)
    sys.exit(0 if report['Success'] else 1)
