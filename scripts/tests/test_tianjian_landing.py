"""Actual Runtime/Engine simulation, with recorded native functor boundaries.

Does not emulate native saves, geometry, Force physics, or Toolkit execution.
"""
from pathlib import Path
import importlib.util
import re
from unittest.mock import patch
import sys
import unittest

REPO = next(p for p in Path(__file__).resolve().parents if (p/'scripts/tests/test_esc_bridge.py').is_file())
sys.path.insert(0, str(REPO/'scripts/tests'))
import test_esc_bridge as bridge

ROOT = 'Projectile_ESC_tianqing_tianjian_Main'
IMPACT = 'Projectile_ESC_TianjianImpact'
DOMAIN = 'tianqing_tianjian'
MARKER = 'ESC_SAVEFAIL_TIANQING_TIANJIAN'


class TianjianLanding(unittest.TestCase):
    table = bridge.Bridge.table
    native_damage = bridge.Bridge.native_damage

    def setUp(self):
        bridge.Bridge.setUp(self)
        self.lua.execute('''
            function Osi.PlayEffectAtPosition(...)
                assert(select('#',...)==5,'Native PlayEffectAtPosition requires five arguments')
                Fixture.calls[#Fixture.calls+1]={name='PlayEffectAtPosition',args={...}}
            end
        ''')
        self.F.actor('sword', 9, 'tianqing', 1000, 1000, 'players', 0)
        self.F.actor('enemy', 0, None, 1000, 1000, 'enemies', 5)
        self.F.actor('ally', 0, None, 1000, 1000, 'players', 5)
        self.F.actor('far', 0, None, 1000, 1000, 'enemies', 7)
        self.F.resource('sword').Amount = 40

    def begin(self, action=501):
        self.F.emit('UsingSpellAtPosition', 'sword', 0, 0, 0, ROOT, 'Projectile', '', action)

    def event(self, action=501, context_type='AttackPosition', impact=IMPACT, caster='sword', flags=None):
        values = dict(Type=context_type, Caster=caster, StoryActionId=action, Position=[0, 0, 0],
                      PropertyContext={'GROUND': True} if flags is None else flags)
        if context_type in ('AttackTarget', 1):
            values['Target'] = 'sword'
        params = self.F.strictProxy(self.table(values))
        return self.table(dict(Params=params, Functor=dict(FunctorList=[dict(TypeId='CreateExplosion', SpellId=impact)])))

    def landing(self, action=501):
        event = self.event(action)
        self.F.event('ExecuteFunctor', event)
        self.F.event('AfterExecuteFunctor', event)

    def domain(self):
        return self.ESC.State('sword').domains[DOMAIN]

    def domain_status_count(self):
        return sum(c.name == 'ApplyStatus' and c.args[2] == 'ESC_TIANQING_AFTERSHOCK' for c in self.F.calls.values())

    def aliases(self, mapping):
        self.lua.globals().Fixture.identityAliases=self.table(mapping)
        self.lua.execute('''
            local aliases=Fixture.identityAliases
            local originalGet=Ext.Entity.Get
            function Ext.Entity.Get(id) return originalGet(aliases[id] or id) end
            for name,original in pairs(Osi) do
                if type(original)=='function' then
                    Osi[name]=function(...)
                        local args={...}
                        for i=1,select('#',...) do args[i]=aliases[args[i]] or args[i] end
                        return original(table.unpack(args,1,select('#',...)))
                    end
                end
            end
        ''')

    def test_named_and_uuid_watched_owner_trigger_one_aftershock_per_enemy_turn(self):
        self.aliases({'Elves_Female_High_Player_sword':'sword'})
        # SessionLoaded refresh registers the canonical ECS UUID before Osiris
        # later supplies the same character as Name_GUID.
        self.ESC.State('sword')
        self.F.emit('UsingSpellAtPosition','Elves_Female_High_Player_sword',0,0,0,ROOT,'Projectile','',701)
        self.landing(701)
        self.F.clearCalls()
        self.F.emit('TurnStarted','enemy')
        calls=[c for c in self.F.calls.values() if c.name=='UseSpell' and c.args[2]=='Target_ESC_Aftershock']
        self.assertEqual(len(calls),1)
        self.assertTrue(self.E.sameEntity(calls[0].args[1],'sword'))
        self.assertEqual(calls[0].args[3],'enemy')
        self.F.emit('TurnStarted','enemy')
        self.assertEqual(sum(c.name=='UseSpell' and c.args[2]=='Target_ESC_Aftershock' for c in self.F.calls.values()),2)

    def test_two_real_aftershock_owners_with_aliases_each_trigger_once(self):
        self.F.actor('other',9,'tianqing',1000,1000,'players',3)
        self.aliases({'Elves_Female_High_Player_sword':'sword','Other_Named_other':'other'})
        self.ESC.State('sword');self.ESC.State('other')
        for name,canonical,action in [('Elves_Female_High_Player_sword','sword',701),('Other_Named_other','other',702)]:
            self.F.emit('UsingSpellAtPosition',name,0,0,0,ROOT,'Projectile','',action)
            event=self.event(action,caster=canonical)
            self.F.event('ExecuteFunctor',event);self.F.event('AfterExecuteFunctor',event)
        self.F.clearCalls()
        self.F.emit('TurnStarted','enemy')
        calls=[c for c in self.F.calls.values() if c.name=='UseSpell' and c.args[2]=='Target_ESC_Aftershock']
        self.assertEqual(len(calls),2)
        self.assertEqual({self.E.uuid(self.E.entity(c.args[1])) for c in calls},{'sword','other'})

    def test_native_entity_proxy_resolves_without_reading_nonexistent_handle(self):
        self.lua.execute('''
            Fixture.nativeCaster=Fixture.strictProxy({})
            local original=Ext.Entity.Get
            function Ext.Entity.Get(ref)
                if ref==Fixture.nativeCaster then return Fixture.entities.sword end
                return original(ref)
            end
        ''')
        self.assertIsNone(self.E.refUuid(self.F.nativeCaster))
        self.begin()
        event=self.event(caster=self.F.nativeCaster)
        self.F.event('ExecuteFunctor',event)
        self.assertIsNone(self.domain())
        self.F.event('AfterExecuteFunctor',event)
        self.assertEqual(self.domain_status_count(),1)

    def test_raw_entity_handle_and_wrapped_reference_keep_same_exact_root(self):
        for wrapped in (False, True):
            with self.subTest(wrapped=wrapped):
                self.setUp()
                self.lua.execute('''
                    local original=Ext.Entity.Get
                    function Ext.Entity.Get(ref)
                        if ref==321 then return Fixture.entities.sword end
                        return original(ref)
                    end
                ''')
                self.begin()
                event=self.event(caster=self.table({'Handle':321}) if wrapped else 321)
                self.F.event('ExecuteFunctor',event);self.F.event('AfterExecuteFunctor',event)
                self.assertEqual(self.domain_status_count(),1)

    def test_native_cast_phase_precedes_ground_but_cannot_trigger_landing(self):
        self.begin()
        cast_event=self.event(context_type='AttackTarget',flags={'CAST':True})
        self.F.event('ExecuteFunctor',cast_event);self.F.event('AfterExecuteFunctor',cast_event)
        self.assertIsNone(self.domain())
        self.assertEqual(self.F.callCount('PlayEffectAtPosition'),0)
        self.landing()
        self.assertEqual(self.domain_status_count(),1)

    def test_attack_position_requires_ground_property_context(self):
        self.begin()
        for flags in ({'CAST':True}, 4):
            event=self.event(flags=flags)
            self.F.event('ExecuteFunctor',event);self.F.event('AfterExecuteFunctor',event)
        self.assertIsNone(self.domain())
        event=self.event(flags=16)
        self.F.event('ExecuteFunctor',event);self.F.event('AfterExecuteFunctor',event)
        self.assertEqual(self.domain_status_count(),1)

    def test_landing_never_chooses_another_action_or_caster(self):
        self.F.actor('other',9,'tianqing',1000,1000,'players',5)
        self.begin()
        for event in (self.event(action=0),self.event(action=502),self.event(caster='other')):
            self.F.event('ExecuteFunctor',event);self.F.event('AfterExecuteFunctor',event)
        self.assertIsNone(self.domain())
        self.landing()
        self.assertEqual(self.domain_status_count(),1)

    def test_empty_landing_starts_only_after_native_explosion_once(self):
        self.begin()
        self.F.emit('CastedSpell', 'sword', ROOT, 'Projectile', '', 501)
        self.assertIsNone(self.domain())
        event = self.event()
        self.F.event('ExecuteFunctor', event)
        self.assertIsNone(self.domain())
        self.F.event('AfterExecuteFunctor', event)
        self.assertEqual(self.domain().expires, 4)
        self.assertEqual(self.domain_status_count(), 1)
        self.landing()
        self.assertEqual(self.domain_status_count(), 1)
        self.assertEqual(self.F.resource('sword').Amount, 40)
        self.assertEqual(self.F.callCount('UseSpell'), 0)

    def test_shared_story_action_impact_notification_is_not_required(self):
        self.begin()
        self.F.emit('UsingSpellOnTarget', 'sword', 'enemy', IMPACT, 'Projectile', '', 501)
        self.F.emit('CastedSpell', 'sword', IMPACT, 'Projectile', '', 501)
        self.landing()
        self.assertEqual(self.domain().expires, 4)
        self.assertEqual(self.domain_status_count(), 1)

    def test_separate_impact_action_does_not_double_start_or_start_early(self):
        self.begin()
        self.F.emit('UsingSpellOnTarget', 'sword', 'enemy', IMPACT, 'Projectile', '', 502)
        self.F.emit('CastedSpell', 'sword', IMPACT, 'Projectile', '', 502)
        self.assertIsNone(self.domain())
        self.landing()
        self.F.emit('CastedSpell', 'sword', IMPACT, 'Projectile', '', 502)
        self.assertEqual(self.domain_status_count(), 1)

    def test_failed_jump_does_not_start_domain(self):
        self.begin()
        self.F.emit('CastSpellFailed', 'sword', ROOT, 'Projectile', '', 501)
        self.landing()
        self.assertIsNone(self.domain())

    def test_dead_source_does_not_start_domain(self):
        self.begin()
        self.F.entities['sword']._dead = True
        self.landing()
        self.assertIsNone(self.domain())

    def test_wrong_explosion_and_unpaired_post_do_not_start_domain(self):
        self.begin()
        event = self.event(impact='Projectile_Fireball')
        self.F.event('ExecuteFunctor', event)
        self.F.event('AfterExecuteFunctor', event)
        self.F.event('AfterExecuteFunctor', event)
        self.assertIsNone(self.domain())

    def test_enemy_turn_aftershock_range_and_four_caster_turn_expiry(self):
        self.begin()
        self.landing()
        self.F.clearCalls()
        self.F.emit('TurnStarted', 'ally')
        self.F.emit('TurnStarted', 'far')
        self.assertEqual(self.F.callCount('UseSpell'), 0)
        self.F.emit('TurnStarted', 'enemy')
        calls = [c for c in self.F.calls.values() if c.name == 'UseSpell']
        self.assertEqual([(c.args[2], c.args[3]) for c in calls], [('Target_ESC_Aftershock', 'enemy')])
        for _ in range(3):
            self.F.emit('TurnStarted', 'sword')
            self.assertIsNotNone(self.domain())
        self.F.emit('TurnStarted', 'sword')
        self.assertIsNone(self.domain())
        self.F.clearCalls()
        self.F.emit('TurnStarted', 'enemy')
        self.assertEqual(self.F.callCount('UseSpell'), 0)

    def impact_control_in_context(self, spell=IMPACT, branch='SpellSuccess', context='AOE',
                                  source='sword', target='enemy', strength_failed=True):
        # Recorded native boundary: CreateExplosion delivers victim functors in
        # AOE context with action 0. We do not emulate native rolls or Force.
        body=self.F.stats[spell][branch]
        functors=[f for f in body.split(';') if MARKER in f]
        self.assertEqual(len(functors),1)
        functor=functors[0]
        scope,condition=functor.split('IF(',1)
        self.assertEqual(condition,"Enemy() and not SavingThrow(Ability.Strength,SourceSpellDC())):ApplyStatus("+MARKER+",100,0)")
        if context in scope.rstrip(':').split(':') and strength_failed and self.E.enemy(source,target):
            self.F.emit('StatusApplied',target,MARKER,source,0)
            return True
        return False

    def test_actual_aoe_context_reaches_control_for_both_impact_save_branches(self):
        for spell in (IMPACT,IMPACT+'_Off'):
            for branch in ('SpellSuccess','SpellFail'):
                with self.subTest(spell=spell,branch=branch):
                    self.setUp()
                    self.assertTrue(self.impact_control_in_context(spell=spell,branch=branch))
                    control=self.ESC.State('enemy').debuffs['sword:'+DOMAIN]
                    self.assertEqual((control.ac,control.slow,control.expires),(-4,.5,3))
                    self.assertTrue(self.E.hasStatus('enemy','PRONE'))
                    self.assertEqual(self.E.hp('enemy'),1000)
                    self.assertEqual(self.F.resource('sword').Amount,40)
                    self.assertEqual(self.F.callCount('UseSpell'),0)
                    self.assertEqual(self.domain_status_count(),0)

    def test_target_only_negative_control_is_filtered_out_of_real_aoe_context(self):
        original=self.F.stats[IMPACT].SpellSuccess
        self.F.stats[IMPACT].SpellSuccess=original.replace('TARGET:AOE:IF','TARGET:IF')
        self.assertFalse(self.impact_control_in_context())
        self.assertIsNone(self.ESC.State('enemy').debuffs['sword:'+DOMAIN])
        self.F.stats[IMPACT].SpellSuccess=original
        self.assertTrue(self.impact_control_in_context())
        self.assertTrue(self.E.hasStatus('enemy','PRONE'))

    def test_aoe_strength_success_and_friend_have_no_failed_marker_control(self):
        self.assertFalse(self.impact_control_in_context(strength_failed=False))
        self.assertFalse(self.impact_control_in_context(target='ally'))
        self.assertFalse(self.E.hasStatus('enemy','PRONE'))
        self.assertFalse(self.E.hasStatus('ally','PRONE'))
        # Even a stray explicit marker cannot bypass the runtime enemy guard.
        self.F.emit('StatusApplied','ally',MARKER,'sword',0)
        self.assertIsNone(self.ESC.State('ally').debuffs['sword:'+DOMAIN])

    def test_action_zero_control_ignores_stale_cast_and_keeps_owners_separate(self):
        self.F.actor('other',9,'tianqing',1000,1000,'players',3)
        self.F.emit('UsingSpellOnTarget','other','enemy','Target_ESC_tianqing_lietian','Target','',0)
        self.impact_control_in_context(source='sword')
        self.ESC.State('other').turn=4
        self.F.emit('TurnStarted','other')
        other_turn=self.ESC.State('other').turn
        self.impact_control_in_context(source='other')
        controls=self.ESC.State('enemy').debuffs
        self.assertEqual(controls['sword:'+DOMAIN].expires,3)
        self.assertEqual(controls['other:'+DOMAIN].expires,other_turn+3)
        self.assertEqual(controls['other:'+DOMAIN].ac,-4)
        self.assertIsNone(controls['other:tianqing_lietian'])

    def test_generator_preserves_aoe_control_and_native_force_contract(self):
        load=importlib.util.spec_from_file_location('tianjian_control_generator',REPO/'scripts/generate-sword-cultivator.py')
        generator=importlib.util.module_from_spec(load);load.loader.exec_module(generator)
        generated={}
        with patch.object(generator,'write',lambda path,text:generated.__setitem__(path.name,text)):
            generator.generate_spells();generator.generate_statuses()
        stats={}
        for filename in ('Spell_Projectile.txt','Status_BOOST.txt'):
            for name,body in re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)',generated[filename],re.S):
                stats[name]=dict(re.findall(r'^data "([^"]+)" "([^"]*)"$',body,re.M))
        for spell in (IMPACT,IMPACT+'_Off'):
            for field in ('SpellSuccess','SpellFail'):
                self.assertEqual(stats[spell][field],self.F.stats[spell][field])
        self.assertEqual(stats[MARKER]['OnApplyFunctors'],'Force(4)')

    def test_failed_marker_is_only_native_force_site_and_keeps_damage_definition(self):
        self.assertEqual(self.F.stats[MARKER].OnApplyFunctors,'Force(4)')
        for spell in (IMPACT,IMPACT+'_Off'):
            for branch,expression in (('SpellSuccess','DealDamage(26d8,Force,Magical)'),
                                      ('SpellFail','DealDamage((26d8)/2,Force,Magical)')):
                text=self.F.stats[spell][branch]
                self.assertIn(expression,text)
                self.assertNotIn('Force(',text)
                self.assertEqual(text.count('SavingThrow(Ability.Strength,'),1)
                self.assertIn('TARGET:AOE:IF(Enemy() and not SavingThrow(Ability.Strength,',text)

    def test_native_failed_strength_marker_keeps_prone_slow_ac_duration(self):
        self.begin()
        self.F.emit('StatusApplied', 'enemy', MARKER, 'sword', 501)
        debuff = self.ESC.State('enemy').debuffs['sword:'+DOMAIN]
        self.assertEqual((debuff.ac, debuff.slow, debuff.expires), (-4, .5, 3))
        self.assertTrue(self.E.hasStatus('enemy', 'PRONE'))
        self.assertIn('AC(-4)', self.ESC.State('enemy').boosts['aura'])
        self.assertIn('ActionResourceMultiplier(Movement,50,0)', self.ESC.State('enemy').boosts['aura'])
        self.F.emit('StatusApplied', 'ally', MARKER, 'sword', 501)
        self.assertIsNone(self.ESC.State('ally').debuffs['sword:'+DOMAIN])

    def test_strength_success_is_represented_by_no_failed_marker(self):
        self.begin()
        self.landing()
        self.assertIsNone(self.ESC.State('enemy').debuffs['sword:'+DOMAIN])
        self.assertFalse(self.E.hasStatus('enemy', 'PRONE'))

    def test_visual_api_failure_does_not_discard_actual_landing_buff(self):
        self.begin()
        self.lua.execute("function Osi.PlayEffectAtPosition(...) error('simulated native visual API failure') end")
        self.landing()
        self.assertEqual(self.domain().expires, 4)
        self.assertEqual(self.domain_status_count(), 1)

    def test_disabled_new_visual_resource_does_not_disable_landing_mechanics(self):
        self.lua.globals().GeneratedSpec.tianqingVfx.enabled = False
        self.begin()
        self.landing()
        self.assertEqual(self.domain().expires, 4)
        self.assertEqual(self.F.callCount('PlayEffectAtPosition'), 0)

    def test_existing_40_percent_damage_and_25_percent_reduction_activate_after_landing(self):
        self.begin()
        self.assertEqual(self.ESC.Runtime.Defense('sword', 100, False, False, None, None)[0], 65)
        self.landing()
        self.assertEqual(self.ESC.Runtime.Defense('sword', 100, False, False, None, None)[0], 48)
        self.F.emit('UsingSpellOnTarget', 'sword', 'enemy', IMPACT, 'Projectile', '', 512)
        hit = self.native_damage('sword', 'enemy', [100], spell=IMPACT, action=512)
        self.assertEqual(hit.TotalDamageDone, 140)
        for _ in range(4):
            self.F.emit('TurnStarted', 'sword')
        self.assertEqual(self.ESC.Runtime.Defense('sword', 100, False, False, None, None)[0], 65)


    def test_named_cast_bare_uuid_landing_starts_existing_domain_once(self):
        self.lua.execute('''
            local aliases={Elves_Female_High_Player_sword='sword'}
            local originalGet=Ext.Entity.Get
            function Ext.Entity.Get(id) return originalGet(aliases[id] or id) end
            for name,original in pairs(Osi) do
                if type(original)=='function' then
                    Osi[name]=function(...)
                        local args={...}
                        for i=1,select('#',...) do args[i]=aliases[args[i]] or args[i] end
                        return original(table.unpack(args,1,select('#',...)))
                    end
                end
            end
        ''')
        self.F.emit('UsingSpellAtPosition', 'Elves_Female_High_Player_sword', 0, 0, 0, ROOT, 'Projectile', '', 701)
        self.F.emit('CastedSpell', 'Elves_Female_High_Player_sword', ROOT, 'Projectile', '', 701)
        self.assertIsNone(self.domain())
        self.landing(701)
        self.assertIsNotNone(self.domain())
        self.assertEqual(self.domain().expires, 4)
        self.assertEqual(self.domain_status_count(), 1)
        self.landing(701)
        self.assertEqual(self.domain_status_count(), 1)
        self.assertEqual(self.F.resource('sword').Amount, 40)
        self.assertEqual(self.F.callCount('UseSpell'), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
