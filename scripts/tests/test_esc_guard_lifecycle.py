"""Native guard clock contracts against the explicit simulated engine boundary.

These execute production Runtime and real generated status conditions. Passing
does not establish Toolkit parsing, engine timing, damage hooks or live VFX.
Run: python -m unittest discover -s scripts/tests -p 'test_esc_guard_lifecycle.py' -v
"""
from pathlib import Path
import re, unittest
import test_esc_bridge as bridge

stats={}
for file in (bridge.LUA.parents[3]/'Public'/bridge.FOLDER/'Stats/Generated/Data').glob('*.txt'):
    for name,chunk in re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)',file.read_text(encoding='utf-8'),re.S):
        stats[name]=dict(re.findall(r'^data "([^"]+)" "([^"]*)"$',chunk,re.M))

class GuardLifecycle(unittest.TestCase):
    # Do not inherit the unrelated baseline cases into this focused suite.
    def setUp(self):
        bridge.Bridge.setUp(self)
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
    def native_guard(self,key,action=1,finish=True):
        stat=bridge.SPEC['spells'][key]['stat']
        self.F.emit('UsingSpellOnTarget','sword','sword',stat,'Shout','',action)
        self.F.statusFunctors('sword',stat,'sword',action)
        if finish: self.F.emit('CastedSpell','sword',stat,'Shout','',action)
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
    def test_huifeng_owner_second_turn_ends_dr_even_when_native_status_remains(self):
        self.actor('sword',level=4,branch='xingge');self.actor('ally',level=0)
        self.native_status('ally','ESC_XINGGE_PROTECTION','sword')
        self.cast('sword','xingge_huifeng','ally')
        self.assertEqual(self.ESC.Runtime.Defense('ally',100,False,False,None,None)[0],72)
        self.F.emit('TurnStarted','sword')
        self.assertEqual(self.ESC.Runtime.Defense('ally',100,False,False,None,None)[0],72)
        # This fixture intentionally leaves the target's native status alive.
        # The caster-turn deadline is an independent GDD upper bound on DR.
        self.F.emit('TurnStarted','sword')
        self.assertTrue(self.E.hasStatus('ally','ESC_XINGGE_PROTECTION'))
        self.assertIsNone(self.ESC.State('ally').protections['huifeng:sword'])
        self.assertEqual(self.ESC.Runtime.Defense('ally',100,False,False,None,None)[0],90)

if __name__=='__main__': unittest.main(verbosity=2)
