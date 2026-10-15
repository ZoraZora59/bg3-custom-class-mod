"""H38 native Target dispatch contracts in the simulated bridge, not wall-passage QA."""
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
import test_esc_bridge as bridge
from test_esc_continuous_strikes import Actor, NativeDataModel, SPELLS, ELIGIBLE

ROOT = bridge.SPEC['spells']['taixuan_yixiantian']['stat']
CHILD = 'Target_ESC_YixiantianHit'


class NativeLine(unittest.TestCase):
    table = bridge.Bridge.table
    actor = bridge.Bridge.actor

    def setUp(self):
        bridge.Bridge.setUp(self)
        self.actor(branch='taixuan')
        self.seq=500;self.order=[];self.packets=[];self.cast_first=True
        self.pause=False;self.fail_target=None;self.damage_first=False
        self.original=self.lua.globals().Osi.UseSpell
        self.lua.globals().Osi.UseSpell=self.native
        self.lua.execute("""
            function Osi.PlayEffectAtPositionAndRotation(...)
                Fixture.calls[#Fixture.calls+1]={name='Beam',args={...}}
            end
        """)

    def layout(self):
        self.actor('A',0,None,10009,10009,'enemies',4)
        self.actor('B',0,None,10009,10009,'enemies',16).Resistances=self.table(dict(Resistances={14:4}))
        self.actor('C',0,None,10009,10009,'enemies',24)
        self.actor('friend',0,None,100,100,'players',5)
        self.actor('outside',0,None,100,100,'enemies',31)
        self.F.entities['C']._canSee=False  # Native LOS is not implemented by this fixture.

    def begin(self, action=100):
        self.F.emit('UsingSpellAtPosition','sword',30,0,0,ROOT,'Zone','',action)

    def finish(self, action=100):
        self.F.emit('CastedSpell','sword',ROOT,'Zone','',action)

    def drain(self):
        for _ in range(20):
            if not len(self.F.nextTicks):return
            self.F.runNextTick()
        self.fail('unbounded native helper dispatch')

    def native(self, source, spell, target, originator, without_move):
        self.original(source,spell,target,originator,without_move)
        if spell!=CHILD:return
        self.seq+=1;action=self.seq;self.order.append(target)
        if self.pause:return
        if self.fail_target==target:
            self.F.emit('CastSpellFailed',source,spell,'Target','',action);return
        if not self.damage_first:
            if self.cast_first:self.F.emit('CastedSpell',source,spell,'Target','',action)
            else:self.F.emit('UsingSpellOnTarget',source,target,spell,'Target','',action)
        # Different later raw rolls must not replace the root's first component rolls.
        amounts=(7,165) if target=='A' else (15,154) if target=='B' else (80,300)
        for index,amount in enumerate(amounts):
            self.damage(source,target,action,amount,index)
        self.F.emit('UsingSpellOnTarget',source,target,spell,'Target','',action)
        self.F.emit('StatusApplied',target,'ESC_HIT_MARKER',source,action)
        self.F.emit('CastedSpell',source,spell,'Target','',action)
        # Duplicates must not dispatch or settle a second root reward.
        self.F.emit('StatusApplied',target,'ESC_HIT_MARKER',source,action)
        self.F.emit('CastedSpell',source,spell,'Target','',action)

    def damage(self, source, target, action, amount, index, spell=CHILD):
        hit=self.table(dict(DamageList=[dict(Amount=amount,DamageType='Slashing' if index==0 else 'Force')],
                            TotalDamageDone=amount,Damage=dict(TotalDamage=amount),SpellId=spell))
        event=self.table(dict(Caster=source,Target=target,StoryActionId=action,Hit=hit,
                             Functor=dict(FunctorUuid=f'11111111-1111-1111-1111-{index+1:012d}')))
        self.F.event('DealDamage',event)
        self.F.event('BeforeDealDamage',self.table(dict(Hit=hit)))
        self.F.entities[target]._hp-=hit.TotalDamageDone
        self.F.event('DealtDamage',event)
        self.packets.append((target,index,hit.TotalDamageDone))
        return hit.TotalDamageDone

    def test_native_target_sequence_shared_roll_immune_skip_and_single_beam(self):
        self.layout();self.begin();self.assertEqual(self.order,[])
        self.finish();self.drain();self.finish();self.drain()
        self.assertEqual(self.order,['A','B','C'])
        self.assertEqual(self.packets,[('A',0,7),('A',1,165),('B',0,0),('B',1,0),('C',0,3),('C',1,83)])
        self.assertEqual(self.F.entities['friend']._hp,100)
        self.assertEqual(self.F.callCount('Beam'),1)
        self.assertEqual(self.F.callCount('SetHitpoints'),0)

    def test_normal_callback_order_matches_casted_first(self):
        self.cast_first=False;self.layout();self.begin();self.finish();self.drain()
        self.assertEqual(self.order,['A','B','C']);self.assertEqual(self.F.entities['C']._hp,9923)

    def test_damage_before_both_cast_callbacks_binds_exact_dispatch(self):
        self.damage_first=True;self.layout();self.begin();self.finish();self.drain()
        self.assertEqual(self.order,['A','B','C']);self.assertEqual(self.F.entities['C']._hp,9923)

    def test_overlapping_unbound_same_target_cannot_steal_another_root(self):
        self.layout();self.pause=True
        self.begin(100);self.finish(100);self.begin(101);self.finish(101)
        self.assertEqual(self.order,['A','A'])
        self.assertEqual(self.damage('sword','A',600,100,0),0)
        self.assertEqual(self.F.entities['A']._hp,10009)
        self.lua.execute('local ts=Fixture.timers;Fixture.timers={};for _,t in ipairs(ts) do if t.ms==30000 then t.callback() end end')
        self.drain();self.assertEqual(self.order,['A','A'])

    def test_unbound_helper_has_zero_damage_and_no_award(self):
        self.actor('A',0,None,100,100,'enemies',4)
        self.assertEqual(self.damage('sword','A',444,100,0),0)
        self.assertEqual(self.F.entities['A']._hp,100)
        self.assertEqual(self.F.resource('sword').Amount,0)

    def test_failure_cancels_remaining_queue_without_fabricated_damage(self):
        self.layout();self.fail_target='B';self.begin();self.finish();self.drain()
        self.assertEqual(self.order,['A','B']);self.assertEqual(self.F.entities['C']._hp,10009)
        self.assertEqual(self.F.callCount('SetHitpoints'),0)

    def test_unbound_async_failure_settles_only_prior_hits_once_and_stops_queue(self):
        self.layout()
        self.actor('xingge',12,'xingge',100,100,'players',0)
        self.ESC.Runtime.State('xingge').domains['xingge_zhangjian']=self.table(dict(expires=10,sequence=1,used={}))
        native=self.native
        def pending_b(source,spell,target,originator,without_move):
            self.pause=spell==CHILD and target=='B'
            native(source,spell,target,originator,without_move)
            self.pause=False
        self.lua.globals().Osi.UseSpell=pending_b
        self.begin();self.finish();self.drain()
        self.assertEqual(self.order,['A','B'])
        self.assertEqual(self.F.entities['A']._hp,9837)
        self.assertEqual(self.F.entities['B']._hp,10009)
        failed_action=self.seq
        # UseSpell already returned; neither target callback nor damage bound B.
        self.F.emit('CastSpellFailed','sword',CHILD,'Target','',failed_action)
        self.F.emit('CastSpellFailed','sword',CHILD,'Target','',failed_action)
        self.drain()
        self.assertEqual(self.order,['A','B'])
        self.assertEqual(self.F.entities['C']._hp,10009)
        self.lua.execute('local ts=Fixture.timers;Fixture.timers={};for _,t in ipairs(ts) do if t.ms==1 then t.callback() else table.insert(Fixture.timers,t) end end')
        echoes=[c for c in self.F.calls.values() if c.name=='UseSpell' and c.args[2]=='Target_ESC_Resonance']
        self.assertEqual([c.args[3] for c in echoes],['A'])
        self.F.emit('UsingSpellOnTarget','xingge','A','Target_ESC_Resonance','Target','',700)
        self.F.emit('StatusApplied','A','ESC_HIT_MARKER','xingge',700)
        self.F.emit('StatusApplied','A','ESC_HIT_MARKER','xingge',700)
        self.assertEqual(self.F.resource('xingge').Amount,3)
        self.assertEqual(self.F.callCount('SetHitpoints'),0)

    def test_root_cancel_and_session_reload_do_not_dispatch_pending_hits(self):
        for cancel in ('failed','dead','reload'):
            with self.subTest(cancel=cancel):
                self.setUp();self.layout();self.begin()
                if cancel=='failed':self.F.emit('CastSpellFailed','sword',ROOT,'Zone','',100)
                elif cancel=='dead':self.F.emit('StatusApplied','sword','DEAD','sword',99)
                else:self.ESC.Runtime.SessionLoaded()
                self.finish();self.drain();self.assertEqual(self.order,[])

    def test_reload_between_native_targets_cancels_queue(self):
        self.layout();self.begin();self.finish()
        self.assertEqual(self.order,['A'])
        self.ESC.Runtime.SessionLoaded();self.drain();self.assertEqual(self.order,['A'])
        self.assertEqual(self.F.entities['C']._hp,10009)

    def test_captured_target_set_excludes_later_arrivals(self):
        self.layout();self.begin();self.finish()
        self.actor('late',0,None,100,100,'enemies',8)
        self.drain();self.assertEqual(self.order,['A','B','C']);self.assertEqual(self.F.entities['late']._hp,100)

    def test_echo_uses_complete_root_hitset_and_single_root_reward(self):
        self.actor('A',0,None,10009,10009,'enemies',4)
        self.actor('C',0,None,10009,10009,'enemies',6)
        self.actor('xingge',12,'xingge',100,100,'players',0)
        self.ESC.Runtime.State('xingge').domains['xingge_zhangjian']=self.table(dict(expires=10,sequence=1,used={}))
        self.begin();self.finish();self.drain()
        self.lua.execute('local ts=Fixture.timers;Fixture.timers={};for _,t in ipairs(ts) do if t.ms==1 then t.callback() else table.insert(Fixture.timers,t) end end')
        echoes=[c for c in self.F.calls.values() if c.name=='UseSpell' and c.args[2]=='Target_ESC_Resonance']
        self.assertEqual({c.args[3] for c in echoes},{'A','C'})
        self.assertEqual(len(echoes),2)
        # Both native echo actions bind the shared original root token.
        for action,target in ((700,'A'),(701,'C')):
            self.F.emit('UsingSpellOnTarget','xingge',target,'Target_ESC_Resonance','Target','',action)
            self.F.emit('StatusApplied',target,'ESC_HIT_MARKER','xingge',action)
        self.assertEqual(self.F.resource('xingge').Amount,3)


class GeneratedLine(unittest.TestCase):
    def test_public_cost_and_native_target_contract(self):
        root,child=SPELLS[ROOT],SPELLS[CHILD]
        self.assertEqual(root['SpellProperties'],'')
        self.assertEqual(root['VerbalIntent'],'Damage')
        self.assertEqual(root['HitAnimationType'],'MagicalDamage_External')
        self.assertTrue(root['SpellAnimation'].startswith('3ff87abf-1ea1-4c32-aadf-c822d74c7dc0'))
        self.assertEqual(root['UseCosts'],'ActionPoint:1;ESC_SwordYuan:20')
        self.assertEqual((root['Shape'],root['Range'],root['Base']),('Square','30','2'))
        self.assertEqual(child['UseCosts'],'');self.assertEqual(child['SpellRoll'],'')
        self.assertIn('DealDamage(36d8,Force,Magical)',child['SpellProperties'])
        self.assertIn('DealDamage(MainMeleeWeapon,',child['SpellProperties'])
        self.assertIn('DealDamage(OffhandMeleeWeapon,',child['SpellProperties'])
        self.assertIn('DealDamage(2d6+WisdomModifier,',child['SpellProperties'])
        self.assertTrue({'ImmediateCast','IgnoreVisionBlock'}<=set(child['SpellFlags'].split(';')))
        self.assertNotIn(CHILD,ELIGIBLE)
        for field in ('PrepareEffect','CastEffect','HitEffect','TargetEffect','TargetSound','SpellAnimation','CastSound'):
            self.assertEqual(child[field],'',field)
        for initial_actions,initial_opportunity,want in ((1,0,(0,30,3)),(0,2,(0,30,1))):
            actor=Actor(12,'taixuan',actions=initial_actions,yuan=50,opportunity=initial_opportunity)
            if initial_opportunity:actor.statuses.update(bridge.SPEC['opportunityStatuses'])
            model=NativeDataModel(actor);model.cast(ROOT)
            before=(actor.actions,actor.yuan,actor.opportunity)
            self.assertEqual(before,want)
            model.cast(CHILD);model.cast(CHILD);model.cast(CHILD)
            self.assertEqual((actor.actions,actor.yuan,actor.opportunity),before)

    def test_editor_public_and_alias_registry_agree(self):
        folder=bridge.SPEC['folder'];source=bridge.LUA.parents[3]
        path=source/'Editor/Mods'/folder/'Stats/SpellData/Target.stats'
        obj=next(x for x in ET.parse(path).getroot().findall('./stat_objects/stat_object')
                 if any(f.get('name')=='Name' and f.get('value')=='ESC_YixiantianHit' for f in x.findall('./fields/field')))
        fields={f.get('name'):f.get('value','') for f in obj.findall('./fields/field')}
        for key in ('SpellProperties','UseCosts','SpellFlags','SpellAnimation','HitEffect','TargetConditions'):
            self.assertEqual(fields[key],SPELLS[CHILD][key])
        self.assertEqual(bridge.SPEC['aliases'][CHILD],dict(key='internal_yixiantian_hit',internal=True,parent='taixuan_yixiantian',hand='auto'))


if __name__=='__main__':unittest.main()
