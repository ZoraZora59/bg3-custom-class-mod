"""Production beam visual lifecycle and unchanged damage in simulated BG3; no native QA."""
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p/'scripts/tests/test_esc_bridge.py').is_file())
sys.path.insert(0,str(REPO/'scripts/tests'))
import test_esc_bridge as bridge

CONFIG = bridge.SPEC['yixiantianVfx']


class CandidateBridge(unittest.TestCase):
    table=bridge.Bridge.table
    actor=bridge.Bridge.actor

    def install(self, enabled=True):
        snapshot=dict(bridge.SNAPSHOT)
        spec=copy.deepcopy(bridge.SPEC)
        spec['yixiantianVfx']=dict(CONFIG,enabled=enabled)
        with patch.object(bridge,'SNAPSHOT',snapshot),patch.object(bridge,'SPEC',spec):
            bridge.Bridge.setUp(self)
        self.lua.execute('''
            function Osi.PlayEffectAtPositionAndRotation(effect,x,y,z,yaw,scale)
                assert(type(effect)=='string' and type(x)=='number' and type(y)=='number'
                    and type(z)=='number' and type(yaw)=='number' and scale==1)
                if Fixture.failBeam then error('simulated unavailable effect call') end
                Fixture.calls[#Fixture.calls+1]={name='PlayEffectAtPositionAndRotation',args={effect,x,y,z,yaw,scale}}
            end
        ''')
        self.actor(branch='taixuan')
        self.native=bridge.SPEC['spells']['taixuan_yixiantian']['stat']

    def setUp(self):self.install()

    def beam_calls(self):
        return [c for c in self.F.calls.values() if c.name=='PlayEffectAtPositionAndRotation']

    def select(self,point,action=1001,stat=None):
        self.F.emit('UsingSpellAtPosition','sword',*point,stat or self.native,'Zone','',action)

    def finish(self,action=1001,stat=None):
        self.F.emit('CastedSpell','sword',stat or self.native,'Zone','',action)

    def damage(self,target,action=1001):
        hit=self.table(dict(DamageList=[dict(Amount=1,DamageType='Force')],TotalDamageDone=1,
                            Damage=dict(TotalDamage=101),SpellId=self.native))
        event=self.table(dict(Caster='sword',Target=target,StoryActionId=action,Hit=hit,
                              Functor=dict(FunctorUuid='11111111-1111-1111-1111-111111111111')))
        self.F.event('DealDamage',event)
        self.F.event('BeforeDealDamage',self.table(dict(Hit=hit)))
        self.F.event('DealtDamage',event)
        return hit.TotalDamageDone

    def test_actual_selected_direction_not_actor_facing_or_selected_distance(self):
        expected=[([2,0,0],270),([-2,0,0],90),([0,0,-2],0),([0,0,2],180),([2,0,2],225)]
        for i,(point,yaw) in enumerate(expected):
            self.select(point,1001+i);self.finish(1001+i)
            call=self.beam_calls()[-1]
            self.assertAlmostEqual(call.args[5],yaw)
            self.assertEqual([call.args[2],call.args[3],call.args[4]],[0,.8,0])
        self.assertEqual(len(self.beam_calls()),5)

    def test_cast_start_snapshot_and_xz_plane_survive_actor_motion_target_elevation(self):
        self.F.entities['sword'].Transform.Transform.Translate=self.table([10,4,20])
        self.select([15,80,20])
        self.F.entities['sword'].Transform.Transform.Translate=self.table([30,7,50])
        self.finish()
        call,=self.beam_calls()
        self.assertEqual([call.args[2],call.args[3],call.args[4]],[10,4.8,20])
        self.assertEqual(call.args[5],270)

    def test_first_damage_and_finish_multiple_targets_play_exactly_once(self):
        self.actor('near',0,None,500,500,'enemies',2)
        self.actor('far',0,None,500,500,'enemies',4)
        self.select([8,0,0]);self.damage('far');self.damage('near');self.finish();self.finish()
        self.assertEqual(len(self.beam_calls()),1)

    def test_empty_ground_and_casted_first_get_one_fallback_effect(self):
        self.select([1,0,0]);self.finish()
        self.assertEqual(len(self.beam_calls()),1)
        self.actor('near',0,None,500,500,'enemies',2)
        self.damage('near')
        self.assertEqual(len(self.beam_calls()),1)

    def test_disabled_other_key_failure_zero_and_missing_direction_skip(self):
        self.install(enabled=False);self.select([1,0,0]);self.finish()
        self.assertEqual(self.beam_calls(),[])
        self.install();other=bridge.SPEC['spells']['taixuan_liuguang']['stat']
        self.select([1,0,0],1002,other);self.finish(1002,other)
        self.select([0,0,0],1003);self.finish(1003)
        self.select([1,0,0],1004);self.F.emit('CastSpellFailed','sword',self.native,'Zone','',1004);self.finish(1004)
        self.F.emit('UsingSpellOnTarget','sword','sword',self.native,'Zone','',1005);self.finish(1005)
        self.assertEqual(self.beam_calls(),[])

    def test_visual_api_error_does_not_abort_native_damage(self):
        self.actor('near',0,None,500,500,'enemies',2)
        self.F.failBeam=True;self.select([2,0,0])
        self.assertEqual(self.damage('near'),101)
        self.assertEqual(self.beam_calls(),[])

    def test_force_immunity_does_not_consume_rank_and_damage_sorts_near_before_far(self):
        self.actor('immune',0,None,500,500,'enemies',1).Resistances=self.table(dict(Resistances={14:4}))
        self.actor('near',0,None,500,500,'enemies',2)
        self.actor('far',0,None,500,500,'enemies',4)
        self.select([30,0,0])
        outcome={target:self.damage(target) for target in ('far','immune','near')}
        self.assertEqual(outcome,dict(far=50,immune=0,near=101))
        self.assertEqual(len(self.beam_calls()),1)

    def test_owner_death_or_left_combat_cancels_unreleased_beam(self):
        for kind in ('DEAD','DOWNED','LeftCombat'):
            self.install();self.select([8,0,0])
            if kind=='LeftCombat':self.F.emit(kind,'sword','fixture-combat')
            else:self.F.emit('StatusApplied','sword',kind,'sword',900)
            self.finish();self.assertEqual(self.beam_calls(),[])

    def test_session_loaded_cancels_unreleased_beam(self):
        self.select([8,0,0]);self.ESC.Runtime.SessionLoaded()
        self.finish();self.assertEqual(self.beam_calls(),[])

    def test_missing_owner_does_not_emit_late_visual(self):
        self.select([8,0,0]);self.F.entities['sword']=None
        # Direct event callback still receives a cached native cast. Existing
        # finish paths may inspect owner, so evaluate only the pre-damage route.
        self.actor('near',0,None,500,500,'enemies',2)
        self.assertEqual(self.damage('near'),101)
        self.assertEqual(self.beam_calls(),[])

if __name__=='__main__':
    unittest.main()
