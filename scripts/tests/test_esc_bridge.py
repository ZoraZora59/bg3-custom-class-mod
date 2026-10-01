"""Production Lua bridge contracts in a deterministic, explicitly simulated engine.

Run: python -m unittest discover -s scripts/tests -p 'test_esc_bridge.py' -v
These tests cannot establish Toolkit acceptance or in-game event compatibility.
"""
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'scripts'))
sys.path.insert(0,str(REPO/'build/test-tools'))
from lupa import LuaRuntime
from sword_cultivator_spec import FOLDER

LUA=REPO/'mods/EasternSwordCultivator/Source/Mods'/FOLDER/'ScriptExtender/Lua'
SNAPSHOT={p.name:p.read_bytes() for p in LUA.glob('*.lua')}
SPEC=json.loads((LUA/'GeneratedSpec.json').read_text(encoding='utf-8'))


class Bridge(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().GeneratedSpec=self.lua.table_from(SPEC,recursive=True)
        self.lua.execute((Path(__file__).parent/'esc_engine_fixture.lua').read_text(encoding='utf-8'))
        stats={}
        for file in (LUA.parents[3]/'Public'/FOLDER/'Stats/Generated/Data').glob('*.txt'):
            for chunk in re.split(r'(?=new entry ")',file.read_text(encoding='utf-8')):
                name=re.search(r'new entry "([^"]+)"',chunk)
                if name: stats[name.group(1)]=dict(re.findall(r'data "([^"]+)" "([^"]*)"',chunk))
        stats['Target_MainHandAttack']={'UseCosts':'ActionPoint:1','Cooldown':'','Level':0,'SpellType':'Target',
            'SpellRoll':'Attack(AttackType.MeleeWeaponAttack)','SpellProperties':'DealDamage(MainMeleeWeapon,MainWeaponDamageType)'}
        self.lua.globals().Fixture.stats=self.lua.table_from(stats,recursive=True)
        self.lua.execute('ESC={}')
        self.lua.globals().ESC.Rules=self.lua.execute(SNAPSHOT['Rules.lua'].decode('utf-8'))
        self.lua.globals().ESC.Engine=self.lua.execute(SNAPSHOT['Engine.lua'].decode('utf-8'))
        self.lua.execute(SNAPSHOT['Runtime.lua'].decode('utf-8'))
        self.F=self.lua.globals().Fixture
        self.E=self.lua.globals().ESC.Engine
        self.ESC=self.lua.globals().ESC

    def table(self,obj): return self.lua.table_from(obj,recursive=True)
    def actor(self,id='sword',level=12,branch='xueyan',hp=30,maximum=100,party='players',x=0):
        return self.F.actor(id,level,branch,hp,maximum,party,x)

    def cast(self,id,key,target=None,action=1):
        stat=SPEC['spells'][key]['stat']
        self.F.emit('UsingSpellOnTarget',id,target or id,stat,'Target','',action)
        self.F.emit('CastedSpell',id,stat,'Target','',action)

    def rescue_ready(self,branch='taixuan',level=5):
        entity=self.actor(branch=branch,level=level)
        self.F.resource('sword').Amount=10
        self.lua.globals().Osi.ApplyStatus('sword','STUNNED',12,1,'enemy')
        self.lua.globals().Osi.ApplyStatus('sword','BLINDED',12,1,'enemy')
        self.ESC.Runtime.UpdateRescue('sword')
        packets=[self.F.jsonPackets[call.args[3]] for call in self.F.calls.values() if call.name=='PostMessageToClient']
        token=next((packet.token for packet in packets if packet.available),None)
        return entity,token

    def rescue_intent(self,id,token,peer=0x10000):
        payload=self.lua.globals().Ext.Json.Stringify(self.table(dict(id=id,token=token)))
        self.F.event('NetMessage',self.table(dict(Channel='ESC_ControlRescueIntent',Payload=payload,UserID=peer)))

    def bonus(self,id='sword'):
        return self.F.entities[id].ActionResources.Resources['420c8df5-45c2-4253-93c2-7ec44e127930'][1]

    def cooperation_packet(self,id):
        packets=[self.F.jsonPackets[call.args[3]] for call in self.F.calls.values()
                 if call.name=='PostMessageToClient' and call.args[1]==id and call.args[2]=='ESC_CooperationState']
        return packets[-1]

    def cooperation_intent(self,id,token,spell,peer=0x10000):
        payload=self.lua.globals().Ext.Json.Stringify(self.table(dict(id=id,token=token,spell=spell)))
        self.F.event('NetMessage',self.table(dict(Channel='ESC_CooperationIntent',Payload=payload,UserID=peer)))

    def cooperation_ready(self):
        self.actor(branch='xingge');self.actor('ally',3,'taixuan',100,100,'players',1)
        self.actor('enemy',0,None,100,100,'enemies',2)
        self.cast('sword','xingge_tongzhou','enemy',action=201)
        return self.cooperation_packet('ally')

    def install_client(self):
        self.lua.execute('''Ext.IMGUI={};Fixture.windows={}
            function Ext.IMGUI.NewWindow(name)
                local window={name=name,buttons={}}
                function window:RemoveAllChildren() self.buttons={};self.text=nil end
                function window:AddText(text) self.text=text end
                function window:AddButton(text)
                    self.button={text=text};self.buttons[#self.buttons+1]=self.button;return self.button
                end
                Fixture.windows[#Fixture.windows+1]=window;return window
            end''')
        self.lua.execute(SNAPSHOT['BootstrapClient.lua'].decode('utf-8'))

    def native_damage(self,source,target,parts,spell=None,action=1,status=None):
        hit=self.table(dict(DamageList=[dict(Amount=p,DamageType='Force') for p in parts],TotalDamageDone=sum(parts),SpellId=spell,StatusId=status))
        event=self.table(dict(Caster=source,Target=target,StoryActionId=action,Hit=hit))
        event.Hit=hit
        self.F.event('DealDamage',event)
        self.F.event('BeforeDealDamage',self.table(dict(Hit=hit)))
        # Native engine is simulated only here, after production BeforeDealDamage.
        victim=self.F.entities[target]
        victim._hp=max(0,victim._hp-hit.TotalDamageDone)
        result=self.table(dict(Hit=hit))
        event.Result=result
        self.F.event('DealtDamage',event)
        return hit

    def test_actual_engine_resource_rounding_caps_and_missing_row(self):
        self.actor();row=self.F.resource('sword');row.Amount=48
        self.assertEqual(self.E.restore('sword',2.1),2)
        self.assertEqual(row.Amount,50)
        self.assertFalse(self.E.spendResource('sword',self.E.resource,51))
        self.assertEqual(row.Amount,50)
        self.assertTrue(self.E.spendResource('sword',self.E.resource,6))
        self.assertEqual(row.Amount,44)
        self.actor('ordinary',0,None)
        self.assertEqual(self.E.restore('ordinary',10),0)

    def test_registered_osiris_signatures_exist_in_installed_game(self):
        header=Path('E:/SteamLibrary/steamapps/common/Baldurs Gate 3/Data/Mods/SharedDev/Story/RawFiles/story_header.div')
        if not header.is_file(): self.skipTest('Installed BG3 story_header.div is unavailable')
        signatures={}
        for kind,name,args in re.findall(r'^(event|call|query) (\w+)\((.*)\) \(',header.read_text(encoding='utf-8'),re.M):
            signatures[name]=len(re.findall(r'\([A-Z0-9]+\)_',args))
        for listener in self.F.listenerSignatures.values():
            self.assertIn(listener.name,signatures)
            self.assertEqual(listener.arity,signatures[listener.name],listener.name)

    def test_multiclass_hp_uses_class_level_and_respec_removes_boosts(self):
        entity=self.actor(branch='taixuan',level=3)
        self.ESC.Refresh('sword')
        self.assertIn('IncreaseMaxHP(25)',entity._boosts['ESC_hp'])
        entity.Classes.Classes=self.table([dict(ClassUUID='other',Level=12)])
        self.F.emit('RespecCompleted','sword')
        self.assertIsNone(entity._boosts['ESC_hp'])
        self.assertEqual(self.ESC.State('sword').frenzy,0)

    def test_equipment_gate_differentiates_support_and_attack(self):
        entity=self.actor(branch='tianqing')
        entity._equipped['Melee Main Weapon']=None
        self.assertTrue(self.E.allowed('sword','tianqing',False))
        self.assertFalse(self.E.allowed('sword','tianqing',True))
        self.assertTrue(self.E.allowed('sword','taixuan',True))
        entity._equipped.Shield='shield'
        self.assertFalse(self.E.allowed('sword','taixuan',False))

    def test_sword_attribute_compares_wisdom_to_real_weapon_attribute(self):
        entity=self.actor(branch='taixuan')
        entity._abilities.Strength=10;entity._abilities.Dexterity=20;entity._abilities.Wisdom=18
        # A longsword does not use Dexterity. Its higher legal stat is Wisdom +4.
        self.assertEqual(self.E.swordAttribute('sword'),(4,0))
        self.ESC.Refresh('sword')
        self.assertIsNone(entity._boosts['ESC_wisdom'])
        self.assertEqual(self.F.entities['sword:sword']._boosts['ESC_WEAPON_WISDOM_sword'],'WeaponAttackRollAbilityOverride(Wisdom)')
        # A finesse sword can use Dexterity +5, so Wisdom must not lower it.
        # Installed BG3SE WeaponComponent exposes WeaponProperties as uint32;
        # native Finesse is bit 4, rather than a text flag list.
        self.F.entities['sword:sword'].Weapon=self.table(dict(WeaponProperties=4))
        self.assertEqual(self.E.swordAttribute('sword'),(5,5))
        self.ESC.Refresh('sword')
        self.assertIsNone(entity._boosts['ESC_wisdom'])
        self.assertIsNone(self.F.entities['sword:sword']._boosts['ESC_WEAPON_WISDOM_sword'])

    def test_wisdom_override_compares_each_hand_without_polluting_other_attacks(self):
        entity=self.actor(branch='taixuan')
        entity._abilities.Strength=10;entity._abilities.Dexterity=20;entity._abilities.Wisdom=18
        entity._equipped['Melee Offhand Weapon']='finesse'
        self.F.entities['finesse']=self.table(dict(_proficiencies=dict(Shortswords=True),Weapon=dict(WeaponProperties=4),_boosts={}))
        self.ESC.Refresh('sword')
        self.assertIsNone(entity._boosts['ESC_wisdom'])
        self.assertEqual(self.F.entities['sword:sword']._boosts['ESC_WEAPON_WISDOM_sword'],'WeaponAttackRollAbilityOverride(Wisdom)')
        self.assertIsNone(self.F.entities['finesse']._boosts['ESC_WEAPON_WISDOM_sword'])
        entity._equipped['Melee Main Weapon']='finesse'
        entity._equipped['Melee Offhand Weapon']='sword:sword'
        self.ESC.Refresh('sword')
        self.assertIsNone(entity._boosts['ESC_wisdom'])
        self.assertEqual(self.F.entities['sword:sword']._boosts['ESC_WEAPON_WISDOM_sword'],'WeaponAttackRollAbilityOverride(Wisdom)')
        entity._equipped.Shield='shield'
        self.ESC.Refresh('sword')
        self.assertIsNone(self.F.entities['sword:sword']._boosts['ESC_WEAPON_WISDOM_sword'])
        entity._equipped.Shield=None
        self.ESC.Refresh('sword')
        self.assertEqual(self.F.entities['sword:sword']._boosts['ESC_WEAPON_WISDOM_sword'],'WeaponAttackRollAbilityOverride(Wisdom)')
        entity._equipped['Melee Offhand Weapon']=None
        self.ESC.Refresh('sword')
        self.assertIsNone(self.F.entities['sword:sword']._boosts['ESC_WEAPON_WISDOM_sword'])

    def test_external_pact_attribute_is_preserved_and_own_weapon_override_is_not_original(self):
        actor=self.actor(branch='taixuan');actor._abilities.Wisdom=18;actor._abilities.Charisma=22
        actor.Stats=self.table(dict(SpellCastingAbility=6))
        weapon=self.F.entities['sword:sword'];weapon.Item=self.table({});weapon._owner='sword'
        self.F.entities['pact']=self.table(dict(BoostInfo=dict(Cause=dict(Cause='PACT_WEAPON')),
            WeaponAttackRollAbilityOverrideBoost=dict(Ability='Charisma')))
        self.F.entities['own']=self.table(dict(BoostInfo=dict(Cause=dict(Cause='ESC_WEAPON_WISDOM_sword')),
            WeaponAttackRollAbilityOverrideBoost=dict(Ability='Wisdom')))
        weapon.BoostsContainer=self.table(dict(Boosts=[dict(Type='WeaponAttackRollAbilityOverride',Boosts=['pact','own'])]))
        self.assertEqual(self.E.swordAttribute('sword'),(6,6))
        self.ESC.Refresh('sword')
        self.assertIsNone(weapon._boosts['ESC_WEAPON_WISDOM_sword'])
        actor._abilities.Wisdom=26
        self.ESC.Refresh('sword')
        self.assertEqual(self.E.swordAttribute('sword'),(8,6))
        self.assertEqual(weapon._boosts['ESC_WEAPON_WISDOM_sword'],'WeaponAttackRollAbilityOverride(Wisdom)')
        self.F.entities['pact'].WeaponAttackRollAbilityOverrideBoost.Ability='SpellCastingAbility'
        self.assertEqual(self.E.swordAttribute('sword'),(8,6))
        actor._abilities.Wisdom=18
        self.F.emit('StatusApplied','sword:sword','PACT_WEAPON','sword',260)
        self.assertIsNone(weapon._boosts['ESC_WEAPON_WISDOM_sword'])
        weapon.BoostsContainer=self.table(dict(Boosts=[dict(Type='WeaponAttackRollAbilityOverride',Boosts=['own'])]))
        self.F.emit('StatusRemoved','sword:sword','PACT_WEAPON','sword',261)
        self.assertEqual(self.E.swordAttribute('sword'),(4,3))
        self.assertEqual(weapon._boosts['ESC_WEAPON_WISDOM_sword'],'WeaponAttackRollAbilityOverride(Wisdom)')
        self.assertIsNone(self.E.sword(None))

    def test_strict_functor_context_variants_read_only_declared_recipient_fields(self):
        healed=self.actor('healed',0,None,30,100,'players',0)
        self.F.entities[42]=healed  # The official EntityRef field is a numeric handle.
        self.lua.execute("ESC.Runtime.HealingMultiplier=function(id) return id=='healed' and 1.5 or 1 end")
        functors=self.table(dict(FunctorList=[dict(TypeId='RegainHitPoints',HealingType='Living')]))
        for values in (
            dict(Type='AttackTarget',Target=42,Caster=1),
            dict(Type='Target',Source=42),
            dict(Type='Source',Source=42),
            dict(Type=1,Target=42,Caster=1),
        ):
            healed._hp=30
            event=self.table(dict(Functor=functors))
            event.Params=self.F.strictProxy(self.table(values))
            self.F.event('ExecuteFunctor',event)
            healed._hp=40  # Only the native healing result is simulated.
            self.F.event('AfterExecuteFunctor',self.table({}))
            self.assertEqual(healed._hp,45,values)
        healed._hp=30
        event=self.table(dict(Functor=functors))
        event.Params=self.F.strictProxy(self.table(dict(Type='Interrupt')))
        self.F.event('ExecuteFunctor',event)
        healed._hp=40
        self.F.event('AfterExecuteFunctor',self.table({}))
        self.assertEqual(healed._hp,40)

    def test_strict_entity_proxy_item_detection_for_status_and_recall(self):
        self.actor(branch='taixuan',level=5)
        self.actor('enemy',0,None,100,100,'enemies',2)
        self.F.strictEntity('enemy')
        self.F.emit('StatusApplied','enemy','BLINDED','sword',301)
        self.F.emit('StatusRemoved','enemy','BLINDED','sword',301)
        loose=self.table(dict(_isItem=True,_owner='sword',_equipped=False,
            Uuid=dict(EntityUuid='loose'),Transform=dict(Transform=dict(Translate=[1,0,0]))))
        self.F.entities['loose']=loose
        self.F.strictEntity('loose')
        self.F.emit('StatusApplied','loose','PACT_WEAPON','sword',302)
        self.F.emit('StatusRemoved','loose','PACT_WEAPON','sword',302)
        self.cast('sword','recall_sword','loose',action=303)
        equips=[call for call in self.F.calls.values() if call.name=='Equip']
        self.assertEqual(len(equips),1)
        self.assertEqual((equips[0].args[1],equips[0].args[2]),('sword','loose'))

    def test_one_full_sword_action_opportunities_never_refill_bonus_offhand_or_internal_hits(self):
        self.actor();self.actor('enemy',0,None,1000,1000,'enemies',2)
        pool=self.E.resourceEntry('sword',SPEC['opportunityResource'])
        spell=SPEC['spells']['xueyan_luexue']['stat']
        self.ESC.Runtime.BeginCast('sword',spell,21,'enemy')
        self.ESC.Runtime.FinishCast('sword',spell,21)
        self.assertEqual(pool.Amount,3)
        self.ESC.Runtime.BeginCast('sword',spell,22,'enemy')
        # The engine's native use-cost rewrite is outside this fixture; model its
        # one opportunity charge explicitly, then verify production finish logic.
        self.assertTrue(self.E.spendResource('sword',SPEC['opportunityResource'],1))
        self.ESC.Runtime.FinishCast('sword',spell,22)
        self.assertEqual(pool.Amount,2)
        bonus=next(name for name,row in SPEC['aliases'].items() if row['key']=='xueyan_luexue' and row.get('bonusOnly'))
        self.ESC.Runtime.BeginCast('sword',bonus,23,'enemy');self.ESC.Runtime.FinishCast('sword',bonus,23)
        self.assertEqual(pool.Amount,2)
        internal='Target_ESC_BloodPulse'
        self.ESC.Runtime.BeginCast('sword',internal,24,'enemy');self.ESC.Runtime.FinishCast('sword',internal,24)
        self.assertEqual(pool.Amount,2)
        pool.Amount=0;self.E.removeStatus('sword','ESC_EXTRA_ATTACK','sword')
        self.ESC.Runtime.BeginCast('sword',spell,25,'enemy');self.ESC.Runtime.FinishCast('sword',spell,25)
        self.assertEqual(pool.Amount,3)

    def test_branch_passive_does_not_mutate_other_class(self):
        entity=self.actor('ordinary',0,None)
        self.ESC.Refresh('ordinary')
        self.assertEqual(self.F.callCount('AddBoosts'),0)
        self.assertEqual(entity._hp,30)

    def test_reapplying_weaker_guard_preserves_strong_expiration(self):
        self.actor(branch='taixuan')
        self.cast('sword','taixuan_xinghe')
        self.F.emit('TurnStarted','sword')
        self.cast('sword','qi_guard',action=2)
        self.assertEqual(self.ESC.State('sword').guard.rank,3)
        self.assertEqual(self.ESC.State('sword').guard.expires,2)
        self.F.emit('TurnStarted','sword')
        self.assertIsNone(self.ESC.State('sword').guard)

    def test_equipment_pause_removes_native_counter_gate_without_extending_guard(self):
        entity=self.actor(branch='taixuan');self.cast('sword','taixuan_qinghui')
        self.assertTrue(self.E.hasStatus('sword','ESC_COUNTER_RANK2'))
        entity._equipped.Shield='shield';self.F.emit('Equipped','shield','sword')
        self.assertFalse(self.E.hasStatus('sword','ESC_COUNTER_RANK2'))
        self.F.emit('TurnStarted','sword')
        entity._equipped.Shield=None;self.F.emit('Unequipped','shield','sword')
        self.assertTrue(self.E.hasStatus('sword','ESC_COUNTER_RANK2'))
        self.assertEqual(self.ESC.State('sword').guard.expires,2)
        self.F.emit('TurnStarted','sword')
        self.assertIsNone(self.ESC.State('sword').guard)

    def test_blood_price_is_nonlethal_and_not_received_damage(self):
        entity=self.actor(hp=10)
        self.cast('sword','xueyan_ranxue')
        self.assertEqual(entity._hp,10)
        self.assertEqual(self.ESC.State('sword').frenzy,0)
        entity._hp=11
        self.cast('sword','xueyan_ranxue',action=2)
        self.assertEqual(entity._hp,1)
        self.assertEqual(self.ESC.State('sword').frenzy,4)

    def test_self_healing_never_rewards_cooperation(self):
        self.actor(branch='xingge',hp=20)
        self.cast('sword','xingge_xiangfu')
        self.assertEqual(self.F.entities['sword']._hp,50)
        self.assertEqual(self.F.resource('sword').Amount,0)

    def test_domain_clock_expires_on_owner_fourth_subsequent_turn(self):
        self.actor(branch='xueyan')
        self.cast('sword','xueyan_xuehai')
        for _ in range(3): self.F.emit('TurnStarted','sword')
        self.assertIsNotNone(self.ESC.State('sword').domains.xueyan_xuehai)
        self.F.emit('TurnStarted','sword')
        self.assertIsNone(self.ESC.State('sword').domains.xueyan_xuehai)

    def test_blood_domain_calls_four_actual_pulses_not_five(self):
        self.actor(branch='xueyan');self.actor('enemy',0,None,100,100,'enemies',2)
        self.cast('sword','xueyan_xuehai')
        for _ in range(4): self.F.emit('TurnStarted','sword')
        pulses=[call for call in self.F.calls.values() if call.name=='UseSpell' and call.args[2]=='Target_ESC_BloodPulse']
        self.assertEqual(len(pulses),4)
        self.assertTrue(all(call.args[3]=='enemy' for call in pulses))

    def test_taiqing_opening_buff_precedes_first_pulse_and_focus_has_three_hits(self):
        self.actor(branch='taixuan');self.actor('enemy',0,None,100,100,'enemies',2)
        self.cast('sword','focus_target','enemy')
        self.F.clearCalls();self.cast('sword','taixuan_taiqing',action=2)
        calls=list(self.F.calls.values())
        pulse_indexes=[i for i,call in enumerate(calls) if call.name=='UseSpell' and call.args[2]=='Target_ESC_TaiqingPulse']
        aura_indexes=[i for i,call in enumerate(calls) if call.name=='AddBoosts' and call.args[1]=='sword' and call.args[3]=='ESC_aura']
        self.assertEqual(len(pulse_indexes),3)
        self.assertTrue(aura_indexes and aura_indexes[0]<pulse_indexes[0])

    def test_frenzy_spending_keeps_precast_snapshot_and_changes_subsequent_defense(self):
        self.actor();self.ESC.State('sword').frenzy=15
        alias=next(name for name,row in SPEC['aliases'].items() if row['key']=='xueyan_wusheng' and row.get('spent')==15)
        cast=self.ESC.Runtime.BeginCast('sword',alias,71,'enemy')
        self.assertEqual((cast.snapshot.held,cast.snapshot.spent,cast.snapshot.attack),(15,15,7))
        self.assertEqual(self.ESC.State('sword').frenzy,0)
        self.assertEqual(self.ESC.Runtime.Defense('sword',100,False,True)[0],75)
        self.actor('enemy',0,None,1000,1000,'enemies')
        hit=self.native_damage('sword','enemy',[72],spell=alias,action=71)
        self.assertEqual(hit.TotalDamageDone,234)

    def test_damage_share_applies_after_custom_shield_and_never_recurses(self):
        self.actor('protector',12,'xingge',100,100,'players',5)
        self.actor('ally',0,None,100,100,'players',0)
        self.actor('neutral',0,None,100,100,'neutral',0)
        self.cast('protector','xingge_fengyu')
        self.ESC.State('ally').shield=20
        # No side-by-side aura at 5m. 100-20 shield =>80;45%=>36 transferred.
        result=self.ESC.Runtime.Defense('ally',100,False,False)
        self.assertEqual(result[0],44)
        self.assertEqual(self.F.entities['protector']._hp,75) # floor(36*.7)=25.
        self.assertEqual(self.ESC.Runtime.Defense('neutral',100,False,False)[0],100)
        self.assertEqual(self.F.entities['protector']._hp,75)
        self.assertEqual(self.ESC.Runtime.Defense('ally',100,False,True)[0],100)
        self.assertEqual(self.F.entities['protector']._hp,75)

    def test_free_cooperation_calls_each_party_member_without_consuming_native_resources(self):
        self.actor(branch='xingge');self.actor('enemy',0,None,100,100,'enemies',2)
        for id in ('a','b','c'): self.actor(id,0,None,100,100,'players',1)
        self.actor('neutral',0,None,100,100,'neutral',1)
        self.cast('sword','xingge_tongzhou','enemy')
        self.assertEqual(self.F.callCount('UseSpell'),0) # Choice is required before any attack.
        for id in ('a','b','c'):
            packet=self.cooperation_packet(id)
            self.cooperation_intent(id,packet.token,'Target_MainHandAttack')
        attacks=[call for call in self.F.calls.values() if call.name=='UseSpell' and call.args[2]=='ESC_FREE_Target_MainHandAttack']
        self.assertEqual({call.args[1] for call in attacks},{'a','b','c'})
        self.assertEqual(self.F.stats['ESC_FREE_Target_MainHandAttack'].UseCosts,'')
        self.assertEqual(self.F.stats['Target_MainHandAttack'].UseCosts,'ActionPoint:1')
        self.assertEqual(self.F.callCount('SetHitpoints'),0)

    def test_cooperation_cantrip_choice_client_click_is_free_once(self):
        packet=self.cooperation_ready()
        ally=self.F.entities['ally']
        ally.SpellBook=self.table(dict(Spells=[dict(Id='Projectile_FireBolt')]))
        self.F.stats['Projectile_FireBolt']=self.table(dict(Level=0,SpellType='Projectile',SpellRoll='Attack(AttackType.RangedSpellAttack)',
            SpellProperties='DealDamage(1d10,Fire)',AmountOfTargets=1,TargetRadius=18,UseCosts='ActionPoint:1',Cooldown='OncePerTurn'))
        # Refresh current native choices through a second queued request, consume first by decline.
        self.cast('sword','xingge_tongzhou','enemy',action=202)
        self.cooperation_intent('ally',packet.token,'decline')
        packet=self.cooperation_packet('ally')
        self.install_client()
        payload=self.lua.globals().Ext.Json.Stringify(packet)
        self.F.event('NetMessage',self.table(dict(Channel='ESC_CooperationState',Payload=payload)))
        window=self.F.windows[1]
        spells=[option.spell for option in packet.options.values()]
        button=window.buttons[spells.index('Projectile_FireBolt')+1]
        button.OnClick()
        intent=next(call for call in reversed(list(self.F.calls.values())) if call.name=='PostMessageToServer')
        self.assertEqual(intent.args[1],'ESC_CooperationIntent')
        self.F.event('NetMessage',self.table(dict(Channel=intent.args[1],Payload=intent.args[2],UserID=0x10000)))
        self.F.event('NetMessage',self.table(dict(Channel=intent.args[1],Payload=intent.args[2],UserID=0x10000)))
        attacks=[call for call in self.F.calls.values() if call.name=='UseSpell']
        self.assertEqual([(call.args[1],call.args[2],call.args[3]) for call in attacks],[('ally','ESC_FREE_Projectile_FireBolt','enemy')])
        self.assertEqual(self.F.stats['ESC_FREE_Projectile_FireBolt'].UseCosts,'')
        self.assertEqual(self.F.stats['ESC_FREE_Projectile_FireBolt'].Cooldown,'')
        self.assertEqual(self.F.stats['Projectile_FireBolt'].UseCosts,'ActionPoint:1')
        self.assertEqual(self.bonus('ally').Amount,1)
        revoke=self.cooperation_packet('ally')
        self.F.event('NetMessage',self.table(dict(Channel='ESC_CooperationState',Payload=self.lua.globals().Ext.Json.Stringify(revoke))))
        self.assertFalse(window.Visible)

    def test_cooperation_rejects_forged_unknown_multitarget_control_and_expired_choice(self):
        packet=self.cooperation_ready()
        self.cooperation_intent('ally',packet.token+1,'Target_MainHandAttack')
        self.cooperation_intent('ally',packet.token,'Target_MainHandAttack',peer=0x20000)
        self.cooperation_intent('ally',packet.token,'Unknown')
        ally=self.F.entities['ally'];ally.SpellBook=self.table(dict(Spells=[dict(Id='Unsafe')]))
        self.F.stats['Unsafe']=self.table(dict(Level=0,SpellType='Projectile',SpellRoll='Attack(AttackType.RangedSpellAttack)',
            SpellProperties='DealDamage(1d10,Fire)',AmountOfTargets=2,TargetRadius=18))
        self.cooperation_intent('ally',packet.token,'Unsafe')
        self.lua.globals().Osi.ApplyStatus('ally','STUNNED',12,1,'enemy')
        self.cooperation_intent('ally',packet.token,'Target_MainHandAttack')
        self.lua.globals().Osi.RemoveStatus('ally','STUNNED','enemy')
        self.F.emit('TurnStarted','sword')
        self.cooperation_intent('ally',packet.token,'Target_MainHandAttack')
        self.assertEqual(self.F.callCount('UseSpell'),0)
        self.cast('sword','xingge_tongzhou','enemy',action=203)
        new=self.cooperation_packet('ally')
        self.assertNotEqual(packet.token,new.token)
        self.cooperation_intent('ally',new.token,'Target_MainHandAttack')
        self.assertEqual(self.F.callCount('UseSpell'),1)

    def test_cooperation_free_options_exclude_surface_extra_projectiles_and_out_of_range(self):
        self.actor('ally',3,'taixuan');self.actor('enemy',0,None,100,100,'enemies',4)
        technical=SPEC['spells']['taixuan_liuguang']['stat']
        self.F.entities['ally'].SpellBook=self.table(dict(Spells=[dict(Id=name) for name in ('Surface','Explosion','Extra','Short','Valid',technical)]))
        for name,props,radius in (('Surface','DealDamage(1d10,Fire);CreateSurface(1)',18),
            ('Explosion','DealDamage(1d10,Fire);CreateExplosion(TEST)',18),
            ('Extra','DealDamage(1d10,Fire);SpawnExtraProjectiles(1)',18),('Short','DealDamage(1d10,Fire)',3),
            ('Valid','DealDamage(1d10,Fire)',18)):
            self.F.stats[name]=self.table(dict(Level=0,SpellType='Projectile',SpellRoll='Attack(AttackType.RangedSpellAttack)',
                SpellProperties=props,AmountOfTargets=1,TargetRadius=radius))
        # Our native techniques use Level=0 for engine routing; that must never
        # turn a known 10-yuan class technique into a free cantrip option.
        self.F.stats[technical]=self.table(dict(Level=0,SpellType='Projectile',SpellRoll='Attack(AttackType.RangedSpellAttack)',
            SpellProperties='DealDamage(4d8,Force)',AmountOfTargets=1,TargetRadius=18,UseCosts='ActionPoint:1;ESC_SwordYuan:10'))
        self.assertEqual([option.spell for option in self.E.freeOptions('ally','enemy').values()],['Valid'])

    def test_cooperation_rechecks_actual_party_enemy_alive_and_malformed_messages(self):
        for change in ('party','enemy','owner_dead','target_dead','blocked'):
            with self.subTest(change=change):
                self.setUp();packet=self.cooperation_ready()
                if change=='party': self.F.entities['ally']._party='neutral'
                elif change=='enemy': self.F.entities['enemy']._party='players'
                elif change=='owner_dead': self.F.entities['sword']._dead=True
                elif change=='target_dead': self.F.entities['enemy']._dead=True
                else: self.F.entities['ally']._blocked='enemy'
                self.F.event('NetMessage',self.table(dict(Channel='ESC_CooperationIntent',Payload='{bad',UserID=0x10000)))
                self.cooperation_intent('ally',packet.token,'Target_MainHandAttack')
                self.assertEqual(self.F.callCount('UseSpell'),0)

    def test_partial_persistent_state_can_start_cast_and_owner_turn(self):
        entity=self.actor();entity.Vars.ESC_State=self.table(dict(boosts={}))
        self.cast('sword','xueyan_xuehai')
        self.F.emit('TurnStarted','sword')
        state=self.ESC.State('sword')
        self.assertEqual((state.turn,state.frenzy,state.shield),(1,0,0))

    def test_chain_snapshot_accuracy_does_not_add_newly_gained_frenzy(self):
        self.actor();self.ESC.State('sword').frenzy=15
        alias=next(name for name,row in SPEC['aliases'].items() if row['key']=='xueyan_wusheng' and row.get('spent')==15)
        self.ESC.Runtime.BeginCast('sword',alias,221,'enemy')
        self.F.emit('CastedSpell','sword',alias,'Projectile','',221)
        self.ESC.State('sword').frenzy=2;self.ESC.Refresh('sword')
        continuation='Target_ESC_wusheng_ContinueMelee'
        cast=self.ESC.Runtime.BeginCast('sword',continuation,222,'enemy')
        self.assertEqual(cast.snapshot.attack,7)
        boosts=self.F.entities['sword']._boosts
        self.assertIn('RollBonus(Attack,1)',boosts['ESC_frenzy_stats_1'])
        self.assertIn('RollBonus(Attack,6)',boosts['ESC_cast_snapshot_1'])

    def test_failed_cast_and_reload_remove_temporary_accuracy_without_granting_actions(self):
        self.actor();self.ESC.State('sword').frenzy=15
        alias=next(name for name,row in SPEC['aliases'].items() if row['key']=='xueyan_wusheng' and row.get('spent')==15)
        self.ESC.Runtime.BeginCast('sword',alias,223,'enemy')
        self.assertIsNotNone(self.F.entities['sword']._boosts['ESC_cast_snapshot_1'])
        self.F.emit('CastSpellFailed','sword',alias,'Projectile','',223)
        self.assertIsNone(self.F.entities['sword']._boosts['ESC_cast_snapshot_1'])
        self.F.emit('CastedSpell','sword',alias,'Projectile','',223)
        self.assertEqual(self.E.resourceEntry('sword',SPEC['opportunityResource']).Amount,0)
        self.ESC.State('sword').frenzy=15
        self.ESC.Runtime.BeginCast('sword',alias,224,'enemy')
        self.assertIsNotNone(self.F.entities['sword']._boosts['ESC_cast_snapshot_1'])
        self.F.event('SessionLoaded',self.table({}))
        self.assertIsNone(self.F.entities['sword']._boosts['ESC_cast_snapshot_1'])

    def test_sword_in_melee_slot_does_not_reward_bow_attack_or_bow_kill(self):
        self.actor(level=11,hp=30);self.actor('enemy',0,None,100,100,'enemies',2)
        self.ESC.Runtime.BeginCast('sword','Projectile_MainHandAttack',231,'enemy')
        self.native_damage('sword','enemy',[10],spell='Projectile_MainHandAttack',action=231)
        self.F.emit('StatusApplied','enemy','ESC_HIT_MARKER','sword',231)
        self.F.emit('KilledBy','enemy','sword','sword',231)
        self.assertEqual((self.F.resource('sword').Amount,self.F.entities['sword']._hp,self.ESC.State('sword').frenzy),(0,30,0))
        self.actor('enemy2',0,None,100,100,'enemies',2)
        native=SPEC['spells']['yujian']['stat']
        self.ESC.Runtime.BeginCast('sword',native,232,'enemy2')
        self.native_damage('sword','enemy2',[10],spell=native,action=232)
        self.F.emit('StatusApplied','enemy2','ESC_HIT_MARKER','sword',232)
        self.assertGreater(self.F.resource('sword').Amount,0)

    def test_xingge_basic_sword_miss_and_free_cooperation_each_recover_once(self):
        entity=self.actor(branch='xingge');self.actor('enemy',0,None,100,100,'enemies',2)
        self.ESC.Runtime.BeginCast('sword','Target_MainHandAttack',235,'enemy')
        self.F.emit('CastedSpell','sword','Target_MainHandAttack','Target','',235)
        self.F.emit('CastedSpell','sword','Target_MainHandAttack','Target','',235)
        self.assertEqual(self.F.resource('sword').Amount,2)
        entity._equipped.Shield='shield'
        self.ESC.Runtime.BeginCast('sword','Target_MainHandAttack',236,'enemy')
        self.F.emit('CastedSpell','sword','Target_MainHandAttack','Target','',236)
        self.assertEqual(self.F.resource('sword').Amount,2)
        entity._equipped.Shield=None
        self.actor('ally',11,'xingge',100,100,'players',1)
        self.cast('sword','xingge_tongzhou','enemy',action=237)
        packet=self.cooperation_packet('ally')
        self.cooperation_intent('ally',packet.token,'Target_MainHandAttack')
        self.ESC.Runtime.BeginCast('ally','ESC_FREE_Target_MainHandAttack',238,'enemy')
        self.F.emit('CastedSpell','ally','ESC_FREE_Target_MainHandAttack','Target','',238)
        self.F.emit('CastedSpell','ally','ESC_FREE_Target_MainHandAttack','Target','',238)
        self.assertEqual(self.F.resource('ally').Amount,2)

    def test_external_domain_and_team_buffs_apply_to_firebolt_without_own_frenzy_or_siphon(self):
        self.actor('domain',12,'taixuan',100,100,'players',0)
        self.actor('team',12,'xingge',100,100,'players',0)
        self.actor(level=11,hp=30,x=1);self.ESC.State('sword').frenzy=15
        self.actor('enemy',0,None,1000,1000,'enemies',2)
        self.cast('domain','taixuan_taiqing',action=241)
        self.cast('team','xingge_zhangjian',action=242)
        hit=self.native_damage('sword','enemy',[100],spell='Projectile_FireBolt',action=243)
        self.assertEqual(hit.TotalDamageDone,150) # external20%+30%; own15-layer75% is excluded.
        self.assertEqual((self.F.resource('sword').Amount,self.F.entities['sword']._hp),(0,30))

    def test_equipment_pauses_domain_without_restarting_clock_and_sword_rewards(self):
        self.actor('domain',12,'taixuan',100,100,'players',0)
        self.actor('ally',0,None,100,100,'players',1)
        self.actor('enemy',0,None,1000,1000,'enemies',2)
        self.cast('domain','taixuan_taiqing',action=245)
        expires=self.ESC.State('domain').domains['taixuan_taiqing'].expires
        self.F.entities['domain']._equipped.Shield='shield'
        self.F.emit('Equipped','shield','domain')
        self.assertEqual(self.native_damage('ally','enemy',[100],spell='Projectile_FireBolt',action=246).TotalDamageDone,100)
        self.F.emit('TurnStarted','domain')
        self.F.entities['domain']._equipped.Shield=None
        self.F.emit('Unequipped','shield','domain')
        self.assertEqual(self.ESC.State('domain').domains['taixuan_taiqing'].expires,expires)
        self.assertEqual(self.native_damage('ally','enemy',[100],spell='Projectile_FireBolt',action=247).TotalDamageDone,120)
        self.setUp();entity=self.actor(level=11,hp=30);entity._equipped.Shield='shield'
        self.actor('enemy',0,None,100,100,'enemies',2)
        self.ESC.Runtime.BeginCast('sword','Target_MainHandAttack',248,'enemy')
        self.native_damage('sword','enemy',[10],spell='Target_MainHandAttack',action=248)
        self.F.emit('StatusApplied','enemy','ESC_HIT_MARKER','sword',248)
        self.F.emit('KilledBy','enemy','sword','sword',248)
        self.assertEqual((self.F.resource('sword').Amount,entity._hp,self.ESC.State('sword').frenzy),(0,30,0))

    def test_nested_native_transfer_damage_events_cannot_reward_or_add_cast_targets(self):
        self.actor('attacker',11,'xueyan',30,100,'enemies',0)
        self.actor('protector',12,'xingge',100,100,'players',5)
        self.actor('ally',0,None,100,100,'players',0)
        self.cast('protector','xingge_fengyu',action=250)
        cast=self.ESC.Runtime.BeginCast('attacker','Target_MainHandAttack',251,'ally')
        self.F.transferHooks=True;self.F.transferAction=251
        self.native_damage('attacker','ally',[10],spell='Target_MainHandAttack',action=251)
        self.F.emit('StatusApplied','ally','ESC_HIT_MARKER','attacker',251)
        self.assertEqual(self.F.entities['ally']._hp,94)
        self.assertEqual(self.F.entities['protector']._hp,98)
        self.assertEqual((self.F.resource('attacker').Amount,self.F.entities['attacker']._hp),(2,33)) # ceil(10*.25)=3, once.
        self.assertEqual(set(cast.targets.keys()),{'ally'})

    def test_shared_native_damage_keeps_types_and_rounds_receiver_total_once(self):
        self.actor('protector',12,'xingge',100,100,'players',5)
        self.actor('ally',0,None,100,100,'players',0)
        self.cast('protector','xingge_fengyu')
        self.F.clearCalls()
        parts=self.table([dict(Amount=4,DamageType='Fire'),dict(Amount=4,DamageType='Cold')])
        result=self.ESC.Runtime.Defense('ally',8,False,False,parts)
        self.assertEqual(result[0],5) # floor(8*.45)=3 transferred.
        calls=[call for call in self.F.calls.values() if call.name=='ApplyDamage']
        self.assertEqual([(call.args[1],call.args[2],call.args[3],call.args[4]) for call in calls],
                         [('protector',1,'Fire','ally'),('protector',2,'Cold','ally')])
        self.assertEqual(self.F.entities['protector']._hp,98) # floor((1+2)*.7)=2, not floor(.7)+floor(1.4)=1.
        self.assertEqual(self.F.callCount('SetHitpoints'),0)

    def test_incoming_two_functors_round_class_reduction_once_per_stage(self):
        self.actor('attacker',12,'taixuan',100,100,'enemies',2)
        self.actor(level=11,hp=100)
        for _ in range(2):
            self.native_damage('attacker','sword',[1],spell='Target_MainHandAttack',action=175)
        self.F.emit('StatusApplied','sword','ESC_HIT_MARKER','attacker',175)
        self.assertEqual(self.F.entities['sword']._hp,99) # floor((1+1)*.75)=1.

    def test_actual_offhand_spell_ids_require_sword_in_the_hand_that_attacks(self):
        for spell in ('Target_OffhandAttack','Projectile_OffhandAttack'):
            with self.subTest(spell=spell):
                self.setUp()
                entity=self.actor(level=11,hp=30)
                entity._equipped['Melee Main Weapon']='club'
                entity._equipped['Melee Offhand Weapon']='sword:sword'
                self.F.entities['club']=self.table(dict(_proficiencies=dict(Clubs=True)))
                self.actor('enemy',0,None,100,100,'enemies',2)
                self.native_damage('sword','enemy',[10],spell=spell,action=176)
                self.F.emit('StatusApplied','enemy','ESC_HIT_MARKER','sword',176)
                if spell=='Target_OffhandAttack': self.assertGreater(self.F.resource('sword').Amount,0)
                else: self.assertEqual(self.F.resource('sword').Amount,0) # This native projectile is a bow attack.
                earned=self.F.resource('sword').Amount
                self.native_damage('sword','enemy',[10],spell='Target_MainHandAttack',action=177)
                self.F.emit('StatusApplied','enemy','ESC_HIT_MARKER','sword',177)
                self.assertEqual(self.F.resource('sword').Amount,earned)

    def test_equipment_pauses_automatic_control_release_and_rescue_authority(self):
        for kind in ('shield','medium','heavy'):
            with self.subTest(kind=kind):
                entity,token=self.rescue_ready()
                if kind=='shield': entity._equipped.Shield='shield'
                else:
                    entity._equipped.Breast='armor'
                    self.F.entities['armor']=self.table(dict(_proficiencies={kind.title()+'Armor':True}))
                reaction=entity.ActionResources.Resources[self.E.reaction][1]
                self.F.emit('StatusAttempt','sword','STUNNED','enemy',178)
                self.assertEqual(reaction.Amount,1)
                self.assertIsNone(entity._boosts['ESC_auto_release'])
                self.rescue_intent('sword',token)
                self.assertIsNotNone(entity.StatusContainer.Statuses.STUNNED)
                self.assertEqual((self.F.resource('sword').Amount,self.bonus().Amount),(10,1))

    def test_malformed_rescue_network_json_is_rejected_without_exception(self):
        entity,token=self.rescue_ready()
        self.F.event('NetMessage',self.table(dict(Channel='ESC_ControlRescueIntent',Payload='{invalid',UserID=0x10000)))
        self.assertEqual((self.F.resource('sword').Amount,self.bonus().Amount),(10,1))
        self.assertIsNotNone(entity.StatusContainer.Statuses.STUNNED)

    def test_diagnostics_are_opt_in_ordered_bounded_and_saved_then_disabled(self):
        self.actor();self.actor('enemy',0,None,500,500,'enemies',2)
        self.native_damage('sword','enemy',[2],spell='Target_MainHandAttack',action=180)
        self.assertEqual(len(self.ESC.Runtime.Diagnostics()),0)
        self.ESC.Runtime.StartDiagnostics()
        self.native_damage('sword','enemy',[2],spell='Target_MainHandAttack',action=181)
        rows=list(self.ESC.Runtime.Diagnostics().values())
        self.assertEqual([row.phase for row in rows],['DealDamage','BeforeDealDamage','DealtDamage'])
        self.assertEqual([row.sequence for row in rows],[1,2,3])
        self.assertEqual(rows[0].hp,498)
        self.assertEqual(rows[2].hp,496)
        self.F.emit('StatusAttempt','enemy','STUNNED','sword',182)
        self.F.emit('StatusApplied','enemy','STUNNED','sword',182)
        self.assertEqual([row.phase for row in self.ESC.Runtime.Diagnostics().values()][-2:],['StatusAttempt','StatusApplied'])
        for _ in range(1001): self.F.event('BeforeDealDamage',self.table(dict(Hit=dict(DamageList=[],TotalDamageDone=0))))
        self.assertEqual(len(self.ESC.Runtime.Diagnostics()),1000)
        self.assertEqual(self.ESC.Runtime.Diagnostics()[1000].sequence,1000)
        self.assertTrue(self.ESC.Runtime.WriteDiagnostics('test/runtime.json'))
        saved=next(call for call in self.F.calls.values() if call.name=='SaveFile')
        self.assertEqual(saved.args[1],'test/runtime.json')
        self.assertEqual(len(self.F.jsonPackets[saved.args[2]]),1000)
        self.F.emit('StatusApplied','enemy','BLINDED','sword',183)
        self.assertEqual(len(self.ESC.Runtime.Diagnostics()),1000)
        self.ESC.Runtime.StartDiagnostics()
        self.ESC.Runtime.WriteDiagnostics('test/empty.json')
        self.F.emit('StatusApplied','enemy','BLINDED','sword',184)
        self.assertEqual(len(self.ESC.Runtime.Diagnostics()),0)

    def test_one_line_sorts_geometry_skips_force_immune_and_uses_pre_reduction_total(self):
        self.actor(branch='taixuan')
        self.actor('immune',0,None,500,500,'enemies',1).Resistances=self.table(dict(Resistances={14:4}))
        self.actor('near',0,None,500,500,'enemies',2)
        self.actor('far',0,None,500,500,'enemies',4)
        native=SPEC['spells']['taixuan_yixiantian']['stat']
        self.ESC.Runtime.BeginCast('sword',native,191,None,self.table([30,0,0]))
        outcomes={}
        # Deliver far first to ensure event order does not set falloff order.
        for target in ('far','immune','near'):
            hit=self.table(dict(DamageList=[dict(Amount=1,DamageType='Force')],TotalDamageDone=1,
                                Damage=dict(TotalDamage=101),SpellId=native))
            event=self.table(dict(Caster='sword',Target=target,StoryActionId=191,Hit=hit))
            self.F.event('DealDamage',event)
            self.F.event('BeforeDealDamage',self.table(dict(Hit=hit)))
            outcomes[target]=hit.TotalDamageDone
            self.F.event('DealtDamage',event)
        self.assertEqual(outcomes,dict(far=50,immune=0,near=101))

    def test_support_bursts_use_friend_center_three_metres_and_selected_offhand(self):
        for key,helper,spell in (
            ('xingge_chengfeng','Target_ESC_ChengfengBurst_Off','Target_ESC_xingge_chengfeng_Off'),
            ('xingge_huifeng','Target_ESC_HuifengControl',SPEC['spells']['xingge_huifeng']['stat'])):
            with self.subTest(key=key):
                self.setUp()
                entity=self.actor(branch='xingge')
                entity._equipped['Melee Offhand Weapon']='sword:sword'
                self.actor('friend',0,None,100,100,'players',10)
                self.actor('otherfriend',0,None,100,100,'players',11)
                for name,x in (('nearfriend',12),('boundary',13),('outside',14),('nearcaster',2)):
                    self.actor(name,0,None,100,100,'enemies',x)
                self.F.clearCalls()
                self.ESC.Runtime.BeginCast('sword',spell,195,'friend')
                self.F.emit('CastedSpell','sword',spell,'Target','',195)
                calls=[call for call in self.F.calls.values() if call.name=='UseSpell']
                self.assertEqual({(call.args[1],call.args[2],call.args[3]) for call in calls},
                                 {('sword',helper,'nearfriend'),('sword',helper,'boundary')})
                self.assertEqual(self.F.resource('sword').Amount,3)
                self.F.emit('CastedSpell','sword',spell,'Target','',195)
                self.assertEqual(self.F.resource('sword').Amount,3)
                self.assertEqual(self.F.callCount('UseSpell'),2)

    def test_zero_damage_hit_still_marks_and_duplicate_hit_does_not_reset_followup(self):
        self.actor(branch='xingge');self.actor('ally',0,None,100,100,'players',1)
        self.actor('enemy',0,None,100,100,'enemies',2)
        native=SPEC['spells']['xingge_wenlu']['stat']
        self.ESC.Runtime.BeginCast('sword',native,81,'enemy')
        self.F.emit('StatusApplied','enemy','ESC_HIT_MARKER','sword',81)
        self.assertIsNotNone(self.ESC.State('enemy').marks['followup:sword'])
        self.ESC.Runtime.BeginCast('ally','Target_MainHandAttack',82,'enemy')
        self.ESC.Runtime.Hit('ally','enemy',82)
        self.assertEqual(self.F.resource('sword').Amount,3)
        # A duplicate delivery of the already resolved initial hit is not a recast.
        self.F.emit('StatusApplied','enemy','ESC_HIT_MARKER','sword',81)
        self.ESC.Runtime.BeginCast('ally','Target_MainHandAttack',83,'enemy')
        self.ESC.Runtime.Hit('ally','enemy',83)
        self.assertEqual(self.F.resource('sword').Amount,3)
        # A new use of Wenlu is the GDD's explicit eligibility-reset exception.
        self.ESC.Runtime.BeginCast('sword',native,84,'enemy')
        self.ESC.Runtime.Hit('sword','enemy',84)
        self.ESC.Runtime.BeginCast('ally','Target_MainHandAttack',85,'enemy')
        self.ESC.Runtime.Hit('ally','enemy',85)
        self.assertEqual(self.F.resource('sword').Amount,6)

    def test_resonance_multi_target_aoe_only_once_but_includes_all_original_victims(self):
        self.actor(branch='xingge');self.actor('ally',0,None,100,100,'players',0)
        for id,x in [('enemy_a',1),('enemy_b',2),('bystander',2.5)]:
            self.actor(id,0,None,100,100,'enemies',x)
        self.cast('sword','xingge_zhangjian')
        self.F.clearCalls()
        self.ESC.Runtime.BeginCast('ally','Shout_Thunderwave',91,'enemy_a')
        self.ESC.Runtime.Hit('ally','enemy_a',91)
        self.ESC.Runtime.Hit('ally','enemy_b',91)
        self.ESC.Runtime.FinishCast('ally','Shout_Thunderwave',91)
        timers=[timer for timer in self.F.timers.values() if timer.ms==1]
        for timer in timers: timer.callback()
        echoes=[call for call in self.F.calls.values() if call.name=='UseSpell' and call.args[2]=='Target_ESC_Resonance']
        self.assertEqual({call.args[3] for call in echoes},{'enemy_a','enemy_b'})
        self.assertEqual(len(echoes),2)
        # Recasting the four-round domain cannot give the ally another same-round echo.
        self.cast('sword','xingge_zhangjian',action=92)
        self.ESC.Runtime.BeginCast('ally','Target_MainHandAttack',93,'enemy_a')
        self.ESC.Runtime.Hit('ally','enemy_a',93)
        timers=[timer for timer in self.F.timers.values() if timer.ms==1]
        for timer in timers: timer.callback()
        after=[call for call in self.F.calls.values() if call.name=='UseSpell' and call.args[2]=='Target_ESC_Resonance']
        self.assertEqual(len(after),2)

    def test_fully_absorbed_received_damage_never_gains_frenzy(self):
        self.actor();self.actor('enemy',0,None,100,100,'enemies')
        self.ESC.State('sword').shield=30
        hit=self.native_damage('enemy','sword',[20])
        self.assertEqual(hit.TotalDamageDone,0)
        self.assertEqual(self.F.entities['sword']._hp,30)
        self.assertEqual(self.ESC.State('sword').frenzy,0)

    def test_damage_rounds_once_per_stage_not_per_damage_type(self):
        self.actor(level=11,hp=100);self.actor('enemy',0,None,100,100,'enemies')
        hit=self.native_damage('enemy','sword',[1,1])
        # Two incoming damage types total 2; 25% class defense gives floor(1.5)=1.
        self.assertEqual(hit.TotalDamageDone,1)
        self.assertEqual(self.F.entities['sword']._hp,99)
        self.assertEqual(self.ESC.State('sword').frenzy,1)

    def test_regular_nonclass_damage_cannot_siphon(self):
        self.actor();self.actor('enemy',0,None,100,100,'enemies')
        self.native_damage('sword','enemy',[20],spell='Projectile_FireBolt',status='BURNING')
        self.assertEqual(self.F.entities['sword']._hp,30)
        self.assertEqual(self.F.resource('sword').Amount,0)

    def test_holding_sword_does_not_convert_other_class_spell_into_sword_hit(self):
        self.actor();self.actor('enemy',0,None,100,100,'enemies')
        self.native_damage('sword','enemy',[20],spell='Projectile_FireBolt',action=62)
        self.ESC.Runtime.FlushStage('sword',62,'enemy')
        self.assertEqual(self.F.entities['sword']._hp,30)
        self.assertEqual(self.F.resource('sword').Amount,0)

    def test_one_sword_stage_merges_native_damage_functors_before_rewards(self):
        self.actor(level=11);self.actor('enemy',0,None,100,100,'enemies')
        stat=SPEC['spells']['xueyan_luexue']['stat']
        self.native_damage('sword','enemy',[1],spell=stat,action=61)
        self.native_damage('sword','enemy',[1],spell=stat,action=61)
        self.F.emit('StatusApplied','enemy','ESC_HIT_MARKER','sword',61)
        self.assertEqual(self.F.resource('sword').Amount,2)
        self.assertEqual(self.F.entities['sword']._hp,31)
        self.assertEqual(self.ESC.State('sword').shield,1)

    def test_outgoing_percent_rounds_combined_functors_once_and_resets_per_stage(self):
        self.actor();self.actor('enemy',0,None,100,100,'enemies')
        self.ESC.State('sword').frenzy=15
        spell=SPEC['spells']['xueyan_luexue']['stat']
        self.ESC.Runtime.BeginCast('sword',spell,63,'enemy')
        for stage in range(2):
            self.native_damage('sword','enemy',[1],spell=spell,action=63)
            self.native_damage('sword','enemy',[1],spell=spell,action=63)
            self.F.emit('StatusApplied','enemy','ESC_HIT_MARKER','sword',63)
            self.assertEqual(self.F.entities['enemy']._hp,100-(stage+1)*3)
            self.assertEqual(self.F.resource('sword').Amount,(stage+1)*2)

    def test_kill_event_duplicate_cannot_repeat_heal_yuan_or_frenzy(self):
        self.actor();self.actor('enemy',0,None,0,100,'enemies')
        spell=SPEC['spells']['xueyan_luexue']['stat']
        self.ESC.Runtime.BeginCast('sword',spell,72,'enemy')
        for _ in range(2): self.F.emit('KilledBy','enemy','sword','sword',72)
        self.assertEqual(self.F.entities['sword']._hp,40)
        self.assertEqual(self.F.resource('sword').Amount,4)
        self.assertEqual(self.ESC.State('sword').frenzy,2)

    def test_support_targets_must_be_actual_party_members(self):
        self.actor(branch='xingge',hp=20)
        self.actor('neutral',0,None,20,100,'neutral')
        self.cast('sword','xingge_xiangfu','neutral')
        self.assertEqual(self.F.entities['neutral']._hp,20)
        self.assertEqual(self.F.resource('sword').Amount,0)

    def test_sword_bonuses_never_apply_to_unrelated_spell(self):
        entity=self.actor(branch='taixuan')
        self.ESC.Refresh('sword')
        checked=0
        for value in entity._boosts.values():
            for boost in value.split(';'):
                if 'RollBonus(Attack,' in boost or 'SpellSaveDC(' in boost:
                    checked+=1
                    self.assertTrue(boost.startswith('IF('),boost)
                    self.assertIn("SpellId('",boost)
                    self.assertNotIn("SpellId('Projectile_FireBolt')",boost)
        self.assertGreater(checked,0)

    def test_native_boost_strings_fit_observed_toolkit_intern_limit(self):
        self.actor(branch='taixuan');self.ESC.Refresh('sword')
        oversized=[len(call.args[2].encode('utf-8')) for call in self.F.calls.values()
            if call.name=='AddBoosts' and len(call.args[2].encode('utf-8'))>2048]
        self.assertEqual(oversized,[],f'Native AddBoosts strings exceed observed 2048-byte storage limit: {oversized}')

    def test_reload_does_not_duplicate_decay_timer(self):
        entity=self.actor();entity._combat=False
        self.ESC.State('sword').frenzy=5
        self.F.event('SessionLoaded',self.table({}))
        self.F.event('SessionLoaded',self.table({}))
        elapsed=[timer for timer in self.F.timers.values() if timer.ms==6000]
        for timer in elapsed: timer.callback()
        self.assertEqual(self.ESC.State('sword').frenzy,4)

    def test_reload_removes_only_old_starting_sword_spells_once(self):
        entity=self.actor()
        obsolete=('Shout_ESC_StartingSword','Shout_ESC_StartingSword_longsword',
            'Shout_ESC_StartingSword_greatsword','Shout_ESC_StartingSword_dualshorts')
        entity.Vars.ESC_State=self.table({'startingSword':'greatsword'})
        entity.StatusContainer.Statuses['ESC_STARTING_SWORD_CHOSEN']=self.table({'StatusId':'ESC_STARTING_SWORD_CHOSEN'})
        entity._spells=self.table({spell:True for spell in (*obsolete,'Target_ESC_sword_strike')})
        self.F.event('SessionLoaded',self.table({}))
        removed=[call for call in self.F.calls.values() if call.name=='RemoveSpell']
        self.assertEqual({call.args[2] for call in removed},set(obsolete))
        self.assertTrue(all(call.args[3]==1 for call in removed))
        self.assertTrue(entity._spells['Target_ESC_sword_strike'])
        self.assertEqual(entity.Vars.ESC_State.startingSword,'greatsword')
        self.assertIsNotNone(entity.StatusContainer.Statuses['ESC_STARTING_SWORD_CHOSEN'])
        self.assertFalse(any(call.name=='TemplateAddTo' for call in self.F.calls.values()))
        self.F.event('SessionLoaded',self.table({}))
        self.assertEqual(len([call for call in self.F.calls.values() if call.name=='RemoveSpell']),4)

    def test_rescue_network_intent_spends_once_and_clears_all_covered_controls(self):
        entity,token=self.rescue_ready()
        self.assertIsNotNone(token)
        self.rescue_intent('sword',token)
        self.assertFalse(self.E.hasStatus('sword','STUNNED'))
        self.assertFalse(self.E.hasStatus('sword','BLINDED'))
        self.assertTrue(self.E.hasStatus('sword','ESC_CONTROL_RESISTANCE'))
        self.assertEqual((self.F.resource('sword').Amount,self.bonus().Amount),(6,0))
        self.rescue_intent('sword',token)
        self.assertEqual((self.F.resource('sword').Amount,self.bonus().Amount),(6,0))

    def test_rescue_network_rejects_forged_token_and_other_player(self):
        _,token=self.rescue_ready()
        self.rescue_intent('sword',token+100)
        self.rescue_intent('sword',token,peer=0x20000)
        self.assertTrue(self.E.hasStatus('sword','STUNNED'))
        self.assertEqual((self.F.resource('sword').Amount,self.bonus().Amount),(10,1))

    def test_rescue_insufficient_yuan_or_bonus_spends_neither(self):
        _,token=self.rescue_ready()
        self.F.resource('sword').Amount=3
        self.rescue_intent('sword',token)
        self.assertEqual((self.F.resource('sword').Amount,self.bonus().Amount),(3,1))
        self.F.resource('sword').Amount=10;self.bonus().Amount=0
        self.rescue_intent('sword',token)
        self.assertEqual((self.F.resource('sword').Amount,self.bonus().Amount),(10,0))
        self.assertTrue(self.E.hasStatus('sword','STUNNED'))

    def test_rescue_in_combat_requires_own_turn_but_outside_combat_can_act(self):
        entity,token=self.rescue_ready();entity.TurnBased.IsActiveCombatTurn=False
        self.rescue_intent('sword',token)
        self.assertTrue(self.E.hasStatus('sword','STUNNED'))
        self.assertEqual((self.F.resource('sword').Amount,self.bonus().Amount),(10,1))
        entity._combat=False
        self.rescue_intent('sword',token)
        self.assertFalse(self.E.hasStatus('sword','STUNNED'))
        self.assertEqual((self.F.resource('sword').Amount,self.bonus().Amount),(6,0))

    def test_rescue_level_gate_does_not_offer_xingge_before_eight(self):
        _,token=self.rescue_ready(branch='xingge',level=7)
        self.assertIsNone(token)
        self.assertTrue(self.E.hasStatus('sword','STUNNED'))

    def test_rescue_client_button_emits_intent_then_hides_when_server_revokes(self):
        self.install_client()
        payload=self.lua.globals().Ext.Json.Stringify(self.table(dict(id='sword',available=True,token=19)))
        self.F.event('NetMessage',self.table(dict(Channel='ESC_ControlRescueState',Payload=payload)))
        window=self.F.windows[1]
        self.assertTrue(window.Visible)
        window.button.OnClick()
        calls=[call for call in self.F.calls.values() if call.name=='PostMessageToServer']
        self.assertEqual(calls[-1].args[1],'ESC_ControlRescueIntent')
        packet=self.F.jsonPackets[calls[-1].args[2]]
        self.assertEqual((packet.id,packet.token),('sword',19))
        payload=self.lua.globals().Ext.Json.Stringify(self.table(dict(id='sword',available=False)))
        self.F.event('NetMessage',self.table(dict(Channel='ESC_ControlRescueState',Payload=payload)))
        self.assertFalse(window.Visible)


if __name__=='__main__':
    print('Evidence layer: simulated BG3 boundary; production Lua SHA256 snapshot:')
    print(json.dumps({name:hashlib.sha256(data).hexdigest() for name,data in SNAPSHOT.items()},indent=2))
    unittest.main(verbosity=2)
