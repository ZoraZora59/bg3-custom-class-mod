"""Visual timing/lifecycle boundaries; no native playback or gameplay proof."""
import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('tianqing_boundary',HERE/'test_tianqing_runtime_vfx.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
KEYS=('tianqing_wanjun','tianqing_lietian','tianqing_bafang','tianqing_tianjian')

class CastVisual(unittest.TestCase):
    def setUp(self):
        self.h=native.TianqingRuntimeVfx();self.h.setUp()
        self.lua,self.F=self.h.lua,self.h.F
        self.lua.globals().GeneratedSpec.tianqingVfx.timing=self.h.table({
            key:dict(prepareEffect=key+'-prepare',impactEffect=key+'-impact') for key in KEYS})
        self.lua.execute("""
        Fixture.nextFx=0;Fixture.fx={}
        function Osi.PlayLoopEffectAtPosition(...)
            assert(select('#',...)==5,'PlayLoopEffectAtPosition: five inputs, one return')
            local F=Fixture;F.nextFx=F.nextFx+1;local h=F.nextFx
            F.calls[#F.calls+1]={name='PlayLoopEffectAtPosition',args={...},at=F.now,handle=h}
            if F.noFxHandle then return nil end
            F.fx[h]={...};return h
        end
        function Osi.StopLoopEffect(...)
            assert(select('#',...)==1,'StopLoopEffect: one input')
            local h=...;Fixture.fx[h]=nil
            Fixture.calls[#Fixture.calls+1]={name='StopLoopEffect',args={h},at=Fixture.now}
        end
        """)
    def calls(self,name):return self.h.calls(name)
    def begin(self,key='tianqing_wanjun',**kw):return self.h.begin(key=key,**kw)
    def hit(self,target='enemy0',action=100):
        self.F.emit('StatusApplied',target,'ESC_HIT_MARKER','sword',action)
    def finish(self,spell,action=100):self.h.finish(spell,action)
    def test_start_precedes_native_hit_and_hit_switches_once_without_native_casts(self):
        spell=self.begin();self.F.advance(1)
        self.assertEqual(len(self.calls('PlayLoopEffectAtPosition')),1)
        self.assertEqual(self.calls('PlayEffectAtPosition'),[])
        self.F.advance(1189);self.hit();self.hit('enemy1');self.finish(spell);self.finish(spell)
        self.assertEqual([c.at for c in self.calls('PlayEffectAtPosition')],[1189])
        self.assertEqual(len(self.calls('StopLoopEffect')),1)
        self.assertEqual(self.calls('UseSpell'),[])
        self.assertEqual(self.F.resource('sword').Amount,50)
    def test_native_damage_callback_switches_before_markers_and_multiple_damage_types(self):
        spell=self.begin();self.F.advance(1);self.F.advance(1189)
        event=self.h.table(dict(Caster='sword',Target='enemy0',SpellId=spell,StoryActionId=100,HitWith='Spell',Hit={}))
        self.F.event('DealDamage',event);self.F.event('DealDamage',event);self.hit()
        self.assertEqual([c.at for c in self.calls('PlayEffectAtPosition')],[1189])
        self.assertEqual(len(self.calls('StopLoopEffect')),1)
    def test_invalid_position_cannot_emit_effects_and_only_visual_timer_expires(self):
        spell=self.begin(targets=(),center=(float('nan'),2,20));self.F.advance(1)
        self.finish(spell);self.F.advance(9000)
        self.assertEqual(self.calls('PlayLoopEffectAtPosition'),[])
        self.assertEqual(self.calls('PlayEffectAtPosition'),[])
        self.assertEqual(self.calls('UseSpell'),[])
    def test_position_event_in_same_batch_wins_over_first_victim(self):
        spell=self.h.spell('tianqing_wanjun')
        self.F.emit('UsingSpellOnTarget','sword','enemy0',spell,'Target','',100)
        self.F.emit('UsingSpellOnTarget','sword','enemy1',spell,'Target','',100)
        self.F.emit('UsingSpellAtPosition','sword',10,2,20,spell,'Target','',100)
        self.F.advance(1);self.hit('enemy1')
        for name in ('PlayLoopEffectAtPosition','PlayEffectAtPosition'):
            call=self.calls(name)[0]
            self.assertEqual(tuple(call.args[i] for i in (2,3,4)),(10,2,20))
    def test_target_snapshot_does_not_follow_later_victim_movement(self):
        self.begin(key='tianqing_lietian',targets=('enemy0',),center=None)
        self.F.advance(1)
        self.F.entities['enemy0'].Transform.Transform.Translate=self.h.table([99,5,99])
        self.hit();c=self.calls('PlayEffectAtPosition')[0]
        self.assertEqual(tuple(c.args[i] for i in (2,3,4)),(1,0,0))
    def test_miss_and_empty_area_stop_without_success_impact(self):
        for targets in (('enemy0',),()):
            with self.subTest(targets=targets):
                self.setUp();spell=self.begin(targets=targets);self.F.advance(1)
                self.finish(spell);self.F.advance(2)
                self.assertEqual(len(self.calls('StopLoopEffect')),1)
                self.assertEqual(self.calls('PlayEffectAtPosition'),[])
    def test_failed_cast_before_and_after_prepare_never_impacts_or_replays(self):
        for advance in (0,1):
            with self.subTest(advance=advance):
                self.setUp();spell=self.begin();self.F.advance(advance)
                self.F.emit('CastSpellFailed','sword',spell,'Target','',100)
                self.hit();self.finish(spell);self.F.advance(9000)
                self.assertEqual(self.calls('PlayEffectAtPosition'),[])
                self.assertEqual(len(self.calls('StopLoopEffect')),advance)
                self.assertEqual(len(list(self.F.fx.values())),0)
    def test_early_damage_no_late_prepare_and_same_batch_finish_before_hit(self):
        spell=self.begin();self.finish(spell);self.hit();self.F.advance(1)
        self.assertEqual(self.calls('PlayLoopEffectAtPosition'),[])
        self.assertEqual(len(self.calls('PlayEffectAtPosition')),1)
    def test_cancel_owner_does_not_stop_another_owner(self):
        self.F.actor('other',12,'tianqing',100,100,'players',50)
        spell=self.begin();self.F.emit('UsingSpellOnTarget','other','enemy1',spell,'Target','',200)
        self.F.advance(1);self.F.emit('LeftCombat','sword','combat')
        self.assertEqual(len(self.calls('StopLoopEffect')),1)
        self.assertEqual(len(list(self.F.fx.values())),1)
        self.hit();self.F.emit('StatusApplied','enemy1','ESC_HIT_MARKER','other',200)
        self.assertEqual(len(self.calls('PlayEffectAtPosition')),1)
    def test_death_and_session_reset_stop_handles_without_replaying(self):
        for reason in ('death','reload'):
            with self.subTest(reason=reason):
                self.setUp();self.begin();self.F.advance(1)
                if reason=='death':self.F.emit('StatusApplied','sword','DEAD','sword',0)
                else:self.F.event('SessionLoaded',{})
                self.F.advance(9000);self.hit()
                self.assertEqual(len(self.calls('StopLoopEffect')),1)
                self.assertEqual(self.calls('PlayEffectAtPosition'),[])
    def test_timeout_only_cleans_visual_and_does_not_issue_native_casts(self):
        self.begin();self.F.advance(8000)
        self.assertEqual(len(self.calls('StopLoopEffect')),1)
        self.assertEqual(self.calls('UseSpell'),[])
        self.assertEqual(self.F.resource('sword').Amount,50)
    def test_bafang_uses_one_set_of_eight_bounded_anchors_for_prepare_and_contact(self):
        self.lua.execute('Fixture.ground=function(x,y,z) return x+.25,y+2,z-.25 end')
        spell=self.begin(key='tianqing_bafang',center=None,targets=('enemy0','enemy1'))
        self.F.advance(1);self.hit();self.hit('enemy1');self.finish(spell)
        self.assertEqual(len(self.calls('FindValidPosition')),8)
        prepare,impact=self.calls('PlayLoopEffectAtPosition'),self.calls('PlayEffectAtPosition')
        self.assertEqual(len(prepare),8);self.assertEqual(len(impact),8)
        self.assertEqual([tuple(c.args[i] for i in (2,3,4)) for c in prepare],
                         [tuple(c.args[i] for i in (2,3,4)) for c in impact])
    def test_tianjian_waits_for_real_landing_and_uses_actual_position_once(self):
        spell=self.begin(key='tianqing_tianjian',targets=(),center=(5,0,6))
        self.F.advance(1);self.finish(spell);self.F.advance(1000)
        self.assertEqual(self.calls('PlayEffectAtPosition'),[])
        event=self.h.table(dict(Functor=dict(FunctorList=[dict(TypeId='CreateExplosion',SpellId='Projectile_ESC_TianjianImpact')])))
        event.Params=self.F.strictProxy(self.h.table(dict(Type='AttackPosition',Caster='sword',StoryActionId=100,Position=[5,3,6],PropertyContext={'GROUND':True})))
        self.F.event('ExecuteFunctor',event);self.F.event('AfterExecuteFunctor',event)
        self.F.event('ExecuteFunctor',event);self.F.event('AfterExecuteFunctor',event)
        effects=self.calls('PlayEffectAtPosition');self.assertEqual(len(effects),1)
        self.assertEqual(tuple(effects[0].args[i] for i in (2,3,4)),(5,3,6))
        self.assertEqual(len(self.calls('StopLoopEffect')),1)
    def test_missing_effect_handle_has_no_unstoppable_prepare_fallback(self):
        self.F.noFxHandle=True;self.begin();self.F.advance(1)
        self.assertEqual(self.calls('PlayEffectAtPosition'),[])
        self.hit();self.assertEqual(len(self.calls('PlayEffectAtPosition')),1)
        self.assertEqual(self.calls('StopLoopEffect'),[])
    def test_disabled_split_keeps_existing_non_timing_path(self):
        self.lua.globals().GeneratedSpec.tianqingVfx.timing=None
        spell=self.begin();self.F.advance(1);self.finish(spell)
        self.assertEqual(self.calls('PlayLoopEffectAtPosition'),[])
        self.assertEqual(len(self.calls('PlayEffectAtPosition')),1)

if __name__=='__main__':unittest.main()
