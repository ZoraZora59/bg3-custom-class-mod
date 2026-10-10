"""Native guard clock contracts against the explicit simulated engine boundary.

These execute production Runtime and real generated status conditions. Passing
does not establish Toolkit parsing, engine timing, damage hooks or live VFX.
Run: python -m unittest discover -s scripts/tests -p 'test_esc_guard_lifecycle.py' -v
"""
from pathlib import Path
import importlib.util
import re, unittest
from unittest.mock import patch
import test_esc_bridge as bridge

stats={}
for file in (bridge.LUA.parents[3]/'Public'/bridge.FOLDER/'Stats/Generated/Data').glob('*.txt'):
    for name,chunk in re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)',file.read_text(encoding='utf-8'),re.S):
        stats[name]=dict(re.findall(r'^data "([^"]+)" "([^"]*)"$',chunk,re.M))

# Capture native spell/status contracts in memory; do not regenerate files.
# Guard spells use the current generator even before Source has been refreshed.
generator_spec=importlib.util.spec_from_file_location('esc_guard_status_generator',bridge.REPO/'scripts/generate-sword-cultivator.py')
generator=importlib.util.module_from_spec(generator_spec)
generator_spec.loader.exec_module(generator)
generated_files={}
with patch.object(generator,'write',lambda path,value: generated_files.__setitem__(path.name,value)):
    generator.generate_spells()
    generator.generate_statuses()
generated_spells={}
for filename,text in generated_files.items():
    if filename.startswith('Spell_'):
        for name,chunk in re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)',text,re.S):
            generated_spells[name]=dict(re.findall(r'^data "([^"]+)" "([^"]*)"$',chunk,re.M))
generated_statuses={name:dict(re.findall(r'^data "([^"]+)" "([^"]*)"$',chunk,re.M))
    for name,chunk in re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)',generated_files['Status_BOOST.txt'],re.S)}

class GuardLifecycle(unittest.TestCase):
    # Do not inherit the unrelated baseline cases into this focused suite.
    def setUp(self):
        bridge.Bridge.setUp(self)
        self.F.stats['ESC_XINGGE_PROTECTION']=self.table(generated_statuses['ESC_XINGGE_PROTECTION'])
        for key in ('qi_guard','taixuan_qinghui','taixuan_xinghe'):
            stat=bridge.SPEC['spells'][key]['stat']
            self.F.stats[stat]=self.table(generated_spells[stat])
        self.lua.execute("""
            context={Source='sword',Observer='sword'}
            function HasStatus(name,id) return Osi.HasActiveStatus(id or context.Source,name)==1 end
            function HasPassive(name,id) return Osi.HasPassive(id or context.Source,name)==1 end
            function HasShieldEquipped(id) return Osi.GetEquippedShield(id)~=nil end
            function HasHeavyArmor(id) local a=Osi.GetEquippedItem(id,'Breast');return a and Osi.IsEquipmentWithProficiency(a,'HeavyArmor')==1 or false end
            function HasMediumArmor(id) local a=Osi.GetEquippedItem(id,'Breast');return a and Osi.IsEquipmentWithProficiency(a,'MediumArmor')==1 or false end
        """)
    table=bridge.Bridge.table
    actor=bridge.Bridge.actor
    cast=bridge.Bridge.cast
    def native_status(self,id,name,source=None):
        source=source or id
        self.lua.globals().Osi.ApplyStatus(id,name,12,1,source)
        self.F.emit('StatusApplied',id,name,source,900)
    def expire(self,id,name,source=None):
        self.lua.globals().Osi.RemoveStatus(id,name,source or id)
        self.F.emit('StatusRemoved',id,name,source or id,901)
    def native_guard(self,key,action=1,finish=True,target='sword'):
        stat=bridge.SPEC['spells'][key]['stat']
        self.F.emit('UsingSpellOnTarget','sword',target,stat,'Shout','',action)
        self.F.statusFunctors('sword',stat,target,action)
        if finish: self.F.emit('CastedSpell','sword',stat,'Shout','',action)
    def test_native_self_argument_and_default_target_are_distinct_for_apply_and_remove(self):
        # A mixed contract independently tests the recipient boundary. Do not
        # infer every functor recipient from the caster or the spell's key.
        self.actor(level=7,branch='taixuan');self.actor('enemy',level=0,party='enemy',x=5)
        osi=self.lua.globals().Osi
        for actor,status in (('sword','ESC_COUNTER_RANK2'),('enemy','ESC_COUNTER_RANK2'),('enemy','ESC_COUNTER_RANK3')):
            osi.ApplyStatus(actor,status,12,1,actor)
        self.F.stats['NativeRecipientProbe']=self.table(dict(SpellProperties=
            'RemoveStatus(SELF,ESC_COUNTER_RANK2);RemoveStatus(ESC_COUNTER_RANK3);'
            'ApplyStatus(SELF,ESC_COUNTER_READY,100,2);ApplyStatus(ESC_XINGGE_PROTECTION,100,2)'))
        self.F.clearCalls();self.F.statusFunctors('sword','NativeRecipientProbe','enemy',910)
        self.assertFalse(self.E.hasStatus('sword','ESC_COUNTER_RANK2'))
        self.assertTrue(self.E.hasStatus('enemy','ESC_COUNTER_RANK2'))
        self.assertFalse(self.E.hasStatus('enemy','ESC_COUNTER_RANK3'))
        self.assertTrue(self.E.hasStatus('sword','ESC_COUNTER_READY'))
        self.assertFalse(self.E.hasStatus('enemy','ESC_COUNTER_READY'))
        self.assertTrue(self.E.hasStatus('enemy','ESC_XINGGE_PROTECTION'))
        self.assertFalse(self.E.hasStatus('sword','ESC_XINGGE_PROTECTION'))
        self.assertEqual([(c.name,c.args[1],c.args[2]) for c in self.F.calls.values()
            if c.name in ('ApplyStatus','RemoveStatus') and
               (str(c.args[2]).startswith('ESC_COUNTER_') or c.args[2]=='ESC_XINGGE_PROTECTION')], [
                ('RemoveStatus','sword','ESC_COUNTER_RANK2'),('RemoveStatus','enemy','ESC_COUNTER_RANK3'),
                ('ApplyStatus','sword','ESC_COUNTER_READY'),('ApplyStatus','enemy','ESC_XINGGE_PROTECTION')])
    def test_fixture_rejects_invented_self_prefix_instead_of_granting_guard(self):
        self.actor(level=7,branch='taixuan');self.actor('enemy',level=0,party='enemy',x=5)
        self.F.stats['LegacySelfProbe']=self.table(dict(SpellProperties='SELF:ApplyStatus(ESC_COUNTER_READY,100,2)'))
        with self.assertRaisesRegex(Exception,'Unsupported SELF: prefix'):
            self.F.statusFunctors('sword','LegacySelfProbe','enemy',911)
        self.assertFalse(self.E.hasStatus('sword','ESC_COUNTER_READY'))
        self.assertFalse(self.E.hasStatus('enemy','ESC_COUNTER_READY'))
    def test_xinghe_enemy_target_upgrades_only_caster_guard(self):
        # Reproduce the real AoE recipient case that self-target tests masked.
        self.actor(level=12,branch='taixuan');self.actor('enemy',level=0,party='enemy',x=5)
        self.native_guard('taixuan_qinghui',action=912)
        self.lua.globals().Osi.ApplyStatus('enemy','ESC_COUNTER_RANK2',12,1,'enemy')
        self.F.clearCalls();self.native_guard('taixuan_xinghe',action=913,target='enemy')
        self.assertTrue(self.E.hasStatus('sword','ESC_COUNTER_READY'))
        self.assertTrue(self.E.hasStatus('sword','ESC_COUNTER_RANK3'))
        self.assertFalse(self.E.hasStatus('sword','ESC_COUNTER_RANK2'))
        self.assertTrue(self.E.hasStatus('enemy','ESC_COUNTER_RANK2'))
        self.assertFalse(self.E.hasStatus('enemy','ESC_COUNTER_READY'))
        self.assertFalse(self.E.hasStatus('enemy','ESC_COUNTER_RANK3'))
        self.assertEqual(self.ESC.State('sword').guard.rank,3)
        guard_calls=[c for c in self.F.calls.values() if c.name in ('ApplyStatus','RemoveStatus')
                     and str(c.args[2]).startswith('ESC_COUNTER_')]
        self.assertTrue(guard_calls)
        self.assertTrue(all(c.args[1]=='sword' for c in guard_calls))
    def test_guard_native_expiry_clears_dr_and_reaction_without_owner_turn(self):
        self.actor(level=4,branch='taixuan');self.actor('enemy',level=0,party='enemy',x=5)
        self.native_guard('taixuan_qinghui')
        self.assertEqual(self.ESC.Runtime.Defense('sword',100,False,False,None,None)[0],56)
        self.expire('sword','ESC_COUNTER_READY')
        self.assertEqual(self.ESC.Runtime.Defense('sword',100,False,False,None,None)[0],80)
        self.assertIsNone(self.ESC.State('sword').guard)
        self.assertFalse(self.ESC.Runtime.CounterEligible('sword','enemy',50))
    def test_native_status_starts_defense_before_castedspell(self):
        self.actor(level=4,branch='taixuan')
        self.native_guard('taixuan_qinghui',finish=False)
        self.assertEqual(self.ESC.Runtime.Defense('sword',100,False,False,None,None)[0],56)
    def test_guard_native_ac_is_not_duplicated_by_runtime(self):
        self.actor(level=4,branch='taixuan');self.native_guard('taixuan_qinghui')
        self.assertEqual(self.F.entities['sword']._boosts['ESC_combat'],'AC(5)')
    def test_weaker_cast_does_not_refresh_strong_native_clock(self):
        self.actor(level=7,branch='taixuan');self.native_guard('taixuan_xinghe')
        before=self.ESC.State('sword').guard.expires
        self.F.clearCalls();self.native_guard('qi_guard',action=2);self.native_guard('taixuan_qinghui',action=3)
        guard_calls=[call for call in self.F.calls.values() if call.name=='ApplyStatus' and call.args[2]=='ESC_COUNTER_READY']
        self.assertEqual(guard_calls,[])
        self.assertEqual((self.ESC.State('sword').guard.rank,self.ESC.State('sword').guard.expires),(3,before))
        self.native_guard('taixuan_xinghe',action=4)
        guard_calls=[call for call in self.F.calls.values() if call.name=='ApplyStatus' and call.args[2]=='ESC_COUNTER_READY']
        self.assertEqual(len(guard_calls),1)
    def test_removing_old_rank_during_upgrade_does_not_clear_new_guard(self):
        self.actor(level=7,branch='taixuan');self.native_guard('taixuan_qinghui')
        self.native_guard('taixuan_xinghe',action=2)
        self.expire('sword','ESC_COUNTER_RANK2')
        self.assertEqual(self.ESC.State('sword').guard.rank,3)
        self.assertTrue(self.E.hasStatus('sword','ESC_COUNTER_READY'))
    def test_pause_keeps_native_clock_and_resume_cannot_reapply(self):
        entity=self.actor(level=4,branch='taixuan');self.native_guard('taixuan_qinghui')
        self.F.clearCalls();entity._equipped.Shield='shield';self.F.emit('Equipped','shield','sword')
        self.assertEqual(self.ESC.Runtime.Defense('sword',100,False,False,None,None)[0],100)
        entity._equipped.Shield=None;self.F.emit('Unequipped','shield','sword')
        self.assertEqual(self.ESC.Runtime.Defense('sword',100,False,False,None,None)[0],56)
        self.assertEqual([c for c in self.F.calls.values() if c.name=='ApplyStatus' and c.args[2]=='ESC_COUNTER_READY'],[])
        self.expire('sword','ESC_COUNTER_READY');self.F.emit('Unequipped','shield','sword')
        self.assertEqual(self.ESC.Runtime.Defense('sword',100,False,False,None,None)[0],80)
    def test_huifeng_native_expiry_clears_dr_without_source_turn(self):
        self.actor('sword',level=4,branch='xingge');self.actor('ally',level=0)
        self.native_status('ally','ESC_XINGGE_PROTECTION','sword')
        self.cast('sword','xingge_huifeng','ally')
        self.assertEqual(self.ESC.Runtime.Defense('ally',100,False,False,None,None)[0],72) # 20% active + 10% side-by-side
        self.expire('ally','ESC_XINGGE_PROTECTION','sword')
        self.assertEqual(self.ESC.Runtime.Defense('ally',100,False,False,None,None)[0],90)
    def test_huifeng_generated_status_uses_source_start_turn_clock(self):
        protection=generated_statuses['ESC_XINGGE_PROTECTION']
        self.assertEqual(protection['TickType'],'StartTurn')
        self.assertIn('TickingWithSource',protection.get('StatusPropertyFlags','').split(';'))
        self.assertEqual(protection['Boosts'],'AC(2)')
    def test_huifeng_target_turns_cannot_expire_source_clock(self):
        self.actor('sword',level=4,branch='xingge');self.actor('ally',level=0)
        self.cast('sword','xingge_huifeng','ally')
        for _ in range(3): self.F.protectionTurnStarted('ally')
        self.assertTrue(self.E.hasStatus('ally','ESC_XINGGE_PROTECTION'))
        self.assertEqual(self.ESC.Runtime.Defense('ally',100,False,False,None,None)[0],72)
        self.F.protectionTurnStarted('sword');self.F.protectionTurnStarted('ally')
        self.assertTrue(self.E.hasStatus('ally','ESC_XINGGE_PROTECTION'))
        self.assertEqual(self.ESC.Runtime.Defense('ally',100,False,False,None,None)[0],72)
        self.F.protectionTurnStarted('sword')
        self.assertFalse(self.E.hasStatus('ally','ESC_XINGGE_PROTECTION'))
        self.assertEqual(self.ESC.Runtime.Defense('ally',100,False,False,None,None)[0],90)
    def test_huifeng_source_before_target_still_expires_at_second_source_start(self):
        self.actor('sword',level=4,branch='xingge');self.actor('ally',level=0)
        self.cast('sword','xingge_huifeng','ally')
        self.F.protectionTurnStarted('sword');self.F.protectionTurnStarted('ally')
        self.assertTrue(self.E.hasStatus('ally','ESC_XINGGE_PROTECTION'))
        self.F.protectionTurnStarted('sword')
        self.assertFalse(self.E.hasStatus('ally','ESC_XINGGE_PROTECTION'))
        self.assertEqual(self.ESC.Runtime.Defense('ally',100,False,False,None,None)[0],90)
    def test_ready_boost_truth_table_has_one_rank_and_equipment_pause(self):
        entity=self.actor(level=4,branch='taixuan')
        entity._passives=self.table({'ESC_P_Branch_taixuan':True})
        boosts=stats['ESC_COUNTER_READY']['Boosts']
        for rank in (1,2,3):
            entity.StatusContainer.Statuses['ESC_COUNTER_RANK2']=self.table({'StatusId':'ESC_COUNTER_RANK2'}) if rank==2 else None
            entity.StatusContainer.Statuses['ESC_COUNTER_RANK3']=self.table({'StatusId':'ESC_COUNTER_RANK3'}) if rank==3 else None
            for shield in (False,True):
                entity._equipped.Shield='shield' if shield else None
                total=sum(int(value) for condition,value in re.findall(r'IF\((.*?)\):AC\((\d+)\)',boosts) if self.lua.eval(condition))
                self.assertEqual(total,0 if shield else {1:2,2:3,3:5}[rank])
    def test_ready_boost_armor_pause_is_branch_specific(self):
        entity=self.actor(level=4,branch='taixuan')
        self.native_guard('taixuan_qinghui')
        boosts=stats['ESC_COUNTER_READY']['Boosts']
        for branch in ('taixuan','xingge','tianqing','xueyan'):
            entity._passives=self.table({'ESC_P_Branch_'+branch:True})
            for armor in ('MediumArmor','HeavyArmor'):
                item=self.actor('armor',level=0);item._proficiencies=self.table({armor:True})
                entity._equipped.Breast='armor'
                total=sum(int(v) for c,v in re.findall(r'IF\((.*?)\):AC\((\d+)\)',boosts) if self.lua.eval(c))
                self.assertEqual(total,0 if branch in ('taixuan','xingge') else 3)
    def test_huifeng_old_source_removal_preserves_new_source_protection(self):
        self.actor('sword',level=4,branch='xingge');self.actor('second',level=4,branch='xingge');self.actor('ally',level=0)
        self.native_status('ally','ESC_XINGGE_PROTECTION','sword');self.cast('sword','xingge_huifeng','ally')
        self.native_status('ally','ESC_XINGGE_PROTECTION','second');self.cast('second','xingge_huifeng','ally',action=2)
        self.F.emit('StatusRemoved','ally','ESC_XINGGE_PROTECTION','sword',903)
        self.assertIsNone(self.ESC.State('ally').protections['huifeng:sword'])
        self.assertIsNotNone(self.ESC.State('ally').protections['huifeng:second'])
        self.assertEqual(self.ESC.Runtime.Defense('ally',100,False,False,None,None)[0],72)
        self.expire('ally','ESC_XINGGE_PROTECTION','second')
        self.assertIsNone(self.ESC.State('ally').protections['huifeng:second'])
        self.assertEqual(self.ESC.Runtime.Defense('ally',100,False,False,None,None)[0],90)
    def test_native_clock_contract_is_explicit_in_all_guard_stats(self):
        ready=stats['ESC_COUNTER_READY']
        self.assertEqual(ready['TickType'],'StartTurn')
        for rank in (2,3):
            self.assertEqual(stats['ESC_COUNTER_RANK'+str(rank)]['TickType'],ready['TickType'])
            condition=stats['Interrupt_ESC_Counter'+str(rank)]['Conditions']
            self.assertIn("HasStatus('ESC_COUNTER_READY',context.Observer)",condition)
            self.assertIn('Self(context.Target,context.Observer)',condition)
            self.assertIn('DistanceToEntityGreaterThan(18,context.ObserverPosition,context.Source)',condition)
            self.assertEqual(stats['Target_ESC_Counter'+str(rank)]['TargetRadius'],'18')
        for key in ('qi_guard','taixuan_qinghui'):
            properties=stats[bridge.SPEC['spells'][key]['stat']]['SpellProperties']
            self.assertIn("IF(not (HasStatus('ESC_COUNTER_READY',context.Source) and",properties)
    def test_orphan_rank_cannot_block_new_guard_or_enable_expired_counter(self):
        self.actor(level=4,branch='taixuan');self.actor('enemy',level=0,party='enemy',x=5)
        self.native_status('sword','ESC_COUNTER_RANK3')
        self.assertFalse(self.ESC.Runtime.CounterEligible('sword','enemy',19))
        self.native_guard('qi_guard')
        self.assertEqual(self.ESC.State('sword').guard.rank,1)
        self.assertFalse(self.E.hasStatus('sword','ESC_COUNTER_RANK3'))
    def test_refresh_old_ready_removed_before_new_application_preserves_new_rank(self):
        self.actor(level=4,branch='taixuan');self.native_guard('taixuan_qinghui')
        self.expire('sword','ESC_COUNTER_RANK2');self.native_status('sword','ESC_COUNTER_RANK3')
        self.F.clearCalls()
        self.expire('sword','ESC_COUNTER_READY')
        self.assertTrue(self.E.hasStatus('sword','ESC_COUNTER_RANK3'))
        self.assertIsNone(self.ESC.State('sword').guard)
        self.native_status('sword','ESC_COUNTER_READY')
        self.assertEqual(self.ESC.State('sword').guard.rank,3)
        self.assertEqual(self.ESC.Runtime.Defense('sword',100,False,False,None,None)[0],48)
        erased=[c for c in self.F.calls.values() if c.name=='RemoveStatus' and c.args[2]=='ESC_COUNTER_RANK3']
        self.assertEqual(erased,[])
    def test_refresh_old_ready_removed_after_new_application_preserves_new_rank(self):
        self.actor(level=4,branch='taixuan');self.native_guard('taixuan_qinghui')
        self.expire('sword','ESC_COUNTER_RANK2');self.native_status('sword','ESC_COUNTER_RANK3')
        self.native_status('sword','ESC_COUNTER_READY')
        self.F.clearCalls()
        # A late removal notification refers to the old instance while the new
        # Ready is already active; do not remove the new status from the fixture.
        self.F.emit('StatusRemoved','sword','ESC_COUNTER_READY','sword',903)
        self.assertTrue(self.E.hasStatus('sword','ESC_COUNTER_RANK3'))
        self.assertEqual(self.ESC.State('sword').guard.rank,3)
        self.assertEqual(self.ESC.Runtime.Defense('sword',100,False,False,None,None)[0],48)
        erased=[c for c in self.F.calls.values() if c.name=='RemoveStatus' and c.args[2]=='ESC_COUNTER_RANK3']
        self.assertEqual(erased,[])
    def test_huifeng_owner_second_turn_ends_both_dr_and_native_ac(self):
        self.actor('sword',level=4,branch='xingge');self.actor('ally',level=0)
        self.native_status('ally','ESC_XINGGE_PROTECTION','sword')
        self.cast('sword','xingge_huifeng','ally')
        self.assertEqual(self.ESC.Runtime.Defense('ally',100,False,False,None,None)[0],72)
        self.F.emit('TurnStarted','sword')
        self.assertEqual(self.ESC.Runtime.Defense('ally',100,False,False,None,None)[0],72)
        # Target turns have not advanced; the caster deadline must also remove
        # the native AC rather than leaving a different clock for half the buff.
        self.F.emit('TurnStarted','sword')
        self.assertFalse(self.E.hasStatus('ally','ESC_XINGGE_PROTECTION'))
        self.assertIsNone(self.ESC.State('ally').protections['huifeng:sword'])
        self.assertEqual(self.ESC.Runtime.Defense('ally',100,False,False,None,None)[0],90)

    def test_huifeng_expired_old_owner_cannot_remove_new_owner_native_ac(self):
        self.actor('sword',level=4,branch='xingge');self.actor('second',level=4,branch='xingge');self.actor('ally',level=0)
        self.cast('sword','xingge_huifeng','ally',action=320)
        self.F.emit('TurnStarted','sword')
        self.cast('second','xingge_huifeng','ally',action=321)
        self.F.clearCalls()
        self.F.emit('TurnStarted','sword')
        self.assertTrue(self.E.hasStatus('ally','ESC_XINGGE_PROTECTION'))
        self.assertIsNotNone(self.ESC.State('ally').protections['huifeng:second'])
        self.assertEqual([c for c in self.F.calls.values() if c.name=='RemoveStatus' and c.args[2]=='ESC_XINGGE_PROTECTION'],[])
        self.F.emit('TurnStarted','second');self.F.emit('TurnStarted','second')
        self.assertFalse(self.E.hasStatus('ally','ESC_XINGGE_PROTECTION'))

    def test_huifeng_late_same_owner_removal_cannot_erase_refreshed_dr(self):
        self.actor('sword',level=4,branch='xingge');self.actor('ally',level=0)
        self.cast('sword','xingge_huifeng','ally',action=322)
        self.F.emit('TurnStarted','sword')
        self.cast('sword','xingge_huifeng','ally',action=323)
        self.F.emit('StatusRemoved','ally','ESC_XINGGE_PROTECTION','sword',322)
        self.assertIsNotNone(self.ESC.State('ally').protections['huifeng:sword'])
        self.assertEqual(self.ESC.State('ally').protections['huifeng:sword'].expires,3)
        self.assertEqual(self.ESC.Runtime.Defense('ally',100,False,False,None,None)[0],72)

    def test_huifeng_deadline_uses_documented_ecs_status_cause_map(self):
        self.actor('sword',level=4,branch='xingge');self.actor('second',level=4,branch='xingge');ally=self.actor('ally',level=0)
        self.cast('sword','xingge_huifeng','ally',action=324)
        self.F.emit('TurnStarted','sword')
        self.cast('second','xingge_huifeng','ally',action=325)
        # Official BG3SE StatusContainerComponent is EntityHandle -> FixedString;
        # source belongs to that status entity's StatusCauseComponent.
        self.F.entities[901]=self.F.strictProxy(self.table(dict(Uuid=False,ServerStatusCause=False,StatusCause=self.F.strictProxy(self.table(dict(Cause='second'))))))
        ally.StatusContainer.Statuses=self.table({901:'ESC_XINGGE_PROTECTION'})
        self.F.clearCalls();self.F.emit('TurnStarted','sword')
        self.assertTrue(self.E.hasStatus('ally','ESC_XINGGE_PROTECTION'))
        self.F.emit('TurnStarted','second');self.F.emit('TurnStarted','second')
        self.assertFalse(self.E.hasStatus('ally','ESC_XINGGE_PROTECTION'))
        removals=[c for c in self.F.calls.values() if c.name=='RemoveStatus' and c.args[2]=='ESC_XINGGE_PROTECTION']
        self.assertEqual([(c.args[1],c.args[3]) for c in removals],[('ally','second')])

    def test_huifeng_expired_snapshot_cannot_remove_same_source_new_native_cast(self):
        self.actor('sword',level=4,branch='xingge');ally=self.actor('ally',level=0)
        self.cast('sword','xingge_huifeng','ally',action=326)
        # A newly applied native status may precede its CastedSpell callback.
        # Its documented ServerStatusCause action distinguishes the new cast.
        self.F.entities[902]=self.F.strictProxy(self.table(dict(Uuid=False,ServerStatusCause=self.F.strictProxy(self.table(dict(Cause='sword',StoryActionId=327))))))
        ally.StatusContainer.Statuses=self.table({902:'ESC_XINGGE_PROTECTION'})
        self.F.clearCalls();self.F.emit('TurnStarted','sword');self.F.emit('TurnStarted','sword')
        self.assertTrue(self.E.hasStatus('ally','ESC_XINGGE_PROTECTION'))
        self.assertEqual([c for c in self.F.calls.values() if c.name=='RemoveStatus' and c.args[2]=='ESC_XINGGE_PROTECTION'],[])

    def test_huifeng_same_owner_accepts_guid_named_guid_and_entity_handle(self):
        owner='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
        named='S_Player_'+owner
        for source_kind in ('guid','handle','legacy_handle'):
            with self.subTest(source_kind=source_kind):
                self.setUp()
                self.actor(owner,level=4,branch='xingge');ally=self.actor('ally',level=0)
                self.lua.globals().ActorAliases=self.table({named:owner,701:owner})
                self.lua.execute('setmetatable(Fixture.entities,{__index=function(rows,key) local id=ActorAliases[key];return id and rawget(rows,id) or nil end})')
                self.cast(named,'xingge_huifeng','ally',action=330)
                if source_kind=='guid':
                    self.F.entities[901]=self.F.strictProxy(self.table(dict(Uuid=False,ServerStatusCause=self.F.strictProxy(self.table(dict(Cause=owner,StoryActionId=330))))))
                    ally.StatusContainer.Statuses=self.table({901:'ESC_XINGGE_PROTECTION'})
                elif source_kind=='handle':
                    self.F.entities[901]=self.F.strictProxy(self.table(dict(Uuid=False,ServerStatusCause=False,StatusCause=self.F.strictProxy(self.table(dict(Cause=701))))))
                    ally.StatusContainer.Statuses=self.table({901:'ESC_XINGGE_PROTECTION'})
                else:
                    ally.StatusContainer.Statuses['ESC_XINGGE_PROTECTION'].StatusSource=701
                self.ESC.Runtime.UpdateAuras()
                self.assertIsNotNone(self.ESC.State('ally').protections['huifeng:'+named])
                self.assertEqual(self.ESC.Runtime.Defense('ally',100,False,False,None,None)[0],72)
                self.F.emit('TurnStarted',named)
                self.assertTrue(self.E.hasStatus('ally','ESC_XINGGE_PROTECTION'))
                self.F.emit('TurnStarted',named)
                self.assertFalse(self.E.hasStatus('ally','ESC_XINGGE_PROTECTION'))

    def test_huifeng_mixed_actor_ids_cannot_remove_another_owners_status(self):
        first='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';second='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
        first_named='S_First_'+first;second_named='S_Second_'+second
        self.actor(first,level=4,branch='xingge');self.actor(second,level=4,branch='xingge');ally=self.actor('ally',level=0)
        self.lua.globals().ActorAliases=self.table({first_named:first,second_named:second,701:first,702:second})
        self.lua.execute('setmetatable(Fixture.entities,{__index=function(rows,key) local id=ActorAliases[key];return id and rawget(rows,id) or nil end})')
        self.cast(first_named,'xingge_huifeng','ally',action=331)
        self.F.emit('TurnStarted',first_named)
        self.cast(second_named,'xingge_huifeng','ally',action=332)
        self.F.entities[903]=self.F.strictProxy(self.table(dict(Uuid=False,ServerStatusCause=self.F.strictProxy(self.table(dict(Cause=second,StoryActionId=332))))))
        ally.StatusContainer.Statuses=self.table({903:'ESC_XINGGE_PROTECTION'})
        self.F.clearCalls();self.F.emit('TurnStarted',701)
        self.F.emit('StatusRemoved','ally','ESC_XINGGE_PROTECTION',first,331)
        self.assertTrue(self.E.hasStatus('ally','ESC_XINGGE_PROTECTION'))
        self.assertIsNotNone(self.ESC.State('ally').protections['huifeng:'+second_named])
        self.assertEqual([c for c in self.F.calls.values() if c.name=='RemoveStatus' and c.args[2]=='ESC_XINGGE_PROTECTION'],[])
        self.F.emit('TurnStarted',702);self.F.emit('TurnStarted',second_named)
        self.assertFalse(self.E.hasStatus('ally','ESC_XINGGE_PROTECTION'))

if __name__=='__main__': unittest.main(verbosity=2)
