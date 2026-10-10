"""Native overlay ownership and event pairing, not client rendering proof."""
import copy
import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'build/test-tools'))
from lupa import LuaRuntime
import xueyan_echo_visual_polish as echo

LUA=ROOT/'mods/EasternSwordCultivator/Source/Mods'/echo.FOLDER/'ScriptExtender/Lua'

def prop(c,key):return c.find(f'./properties/property[@id="{key}"]')
def value(c,key):return prop(c,key).find('./data/datum').get('value')


class NativeEchoSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d=echo.fx.PropertyDictionary(echo.fx.DATA)
        cls.banks={k:echo.author(echo.fx.DATA,k,d)[0] for k in echo.KEYS}
    def overlays(self,key):return self.banks[key].findall('.//component[@class="OverlayMaterial"]')
    def test_intro_has_three_separate_native_offsets_and_pairs_have_one_each(self):
        self.assertEqual(len(self.overlays('intro')),3)
        for i in range(1,4):
            self.assertEqual(len(self.overlays('echo'+str(i))),1)
            self.assertIn(echo.MATERIALS[i-1],value(self.overlays('intro')[i-1],echo.MATERIAL))
            self.assertIn(echo.MATERIALS[i-1],value(self.overlays('echo'+str(i))[0],echo.MATERIAL))
    def test_equipped_visual_binding_and_weapons_are_preserved_exactly(self):
        for k in echo.KEYS:
            for overlay in self.overlays(k):
                i=next(i for i,g in enumerate(echo.MATERIALS,1) if g in value(overlay,echo.MATERIAL))
                native=ET.parse(echo.fx.DATA/f'Editor/Mods/Shared/Assets/Effects/Status/VFX_Status_MirrorImage_{i:02}.lsefx').getroot()
                original=native.find('.//component[@class="OverlayMaterial"]')
                for key in (echo.TARGET,echo.WEAPON,echo.ARMOUR,echo.MATERIAL):
                    self.assertEqual(ET.tostring(prop(overlay,key)),ET.tostring(prop(original,key)))
                self.assertEqual(value(overlay,echo.WEAPON),'1')
                self.assertEqual(value(overlay,echo.ARMOUR),'1')
    def test_no_proxy_models_actor_spawn_or_looping_lifecycle(self):
        for k,r in self.banks.items():
            self.assertEqual({c.get('class') for c in r.findall('.//component')},{'BoundingSphere','OverlayMaterial'})
            self.assertEqual(list(r.find('phases')),[])
            self.assertLessEqual(max(float(c.get('end')) for c in r.findall('.//component')),1.8)
    def test_silhouettes_hold_before_they_fade_without_native_flash_peak(self):
        for k in echo.KEYS:
            for c in self.overlays(k):
                alpha=[float(f.get('value')) for f in prop(c,echo.ALPHA).findall('.//keyframe')]
                self.assertEqual(alpha[0],0);self.assertEqual(alpha[-1],0)
                self.assertEqual(alpha[1],alpha[2]);self.assertGreaterEqual(alpha[1],.7)
                self.assertLessEqual(max(float(f.get('value')) for f in prop(c,echo.BRIGHTNESS).findall('.//keyframe')),3.5)
    def test_receipt_and_registered_effects_resolve_all_four_banks(self):
        source=LUA.parents[3]
        receipt=json.loads((source/echo.RECEIPT).read_text('utf-8'))
        rows={r['effect_name']:r for r in receipt['records']}
        spec=json.loads((LUA/'GeneratedSpec.json').read_text('utf-8'))
        registry=ET.parse(source/echo.BANK).getroot()
        ids={a.get('value') for a in registry.findall('.//attribute[@id="ID"]')}
        for k in echo.KEYS:
            row=rows[echo.effect_name(k)];e,b=echo.paths(k)
            self.assertTrue(row['semantic_roundtrip_verified'])
            self.assertEqual(echo.digest(source/e),row['source_sha256'])
            self.assertEqual(echo.digest(source/b),row['compiled_sha256'])
            self.assertIn(echo.effect_guid(k),ids)
            self.assertEqual(spec['xueyanEchoVfx']['records'][k]['effect'],echo.effect_guid(k))


class NativeEchoEvents(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.spec=json.loads((LUA/'GeneratedSpec.json').read_text('utf-8'))
        self.lua.globals().Spec=self.table(copy.deepcopy(self.spec))
        self.lua.execute('''
        F={entities={},listeners={},effects={}}
        function F.actor(id)
            local entity={Uuid={EntityUuid=id},Vars={ESC_State={chains={wusheng={remaining=5}},frenzy=4,shield=7}},alive=true,branch='xueyan'}
            F.entities[id]=entity;return entity
        end
        F.actor('caster');F.entities['Name_caster']=F.entities.caster
        E={entity=function(id)return F.entities[id]end,
           uuid=function(e)return e and e.Uuid.EntityUuid end,
           spellName=function(s)return s end,
           class=function(id)return 12,F.entities[id] and F.entities[id].branch end,
           alive=function(id)return F.entities[id] and F.entities[id].alive end}
        Osi={PlayEffect=function(...)
            assert(select('#',...)==4,'Installed PlayEffect requires four inputs')
            F.effects[#F.effects+1]={...}
        end}
        Ext={Osiris={RegisterListener=function(name,count,when,fn)F.listeners[name]=fn end},
             Events={SessionLoaded={Subscribe=function(self,fn)F.reload=fn end}}}
        function F.emit(name,...)F.listeners[name](...)end
        ''')
        self.module=self.lua.execute((LUA/'XueyanEchoVfx.lua').read_text('utf-8'))
        self.module.Install(self.lua.globals().E,self.lua.globals().Spec)
        self.F=self.lua.globals().F
        self.root='Projectile_ESC_xueyan_wusheng_F4'
        self.cont='Projectile_ESC_wusheng_ContinueRanged'
    def table(self,v):
        if isinstance(v,dict):return self.lua.table_from({k:self.table(x) for k,x in v.items()})
        if isinstance(v,list):return self.lua.table_from([self.table(x) for x in v])
        return v
    def cast(self,spell=None,action=1,id='caster',target=False):
        spell=spell or self.root
        if target:self.F.emit('UsingSpellOnTarget',id,'enemy',spell,'Projectile','',action)
        else:self.F.emit('UsingSpell',id,spell,'Projectile','',action)
    def effects(self):return [self.F.effects[i] for i in range(1,len(self.F.effects)+1)]
    def test_six_real_casts_map_to_three_pairs_and_do_not_modify_chain(self):
        self.cast();state=self.F.entities.caster.Vars.ESC_State
        for n in (5,4,3,2,1):
            state.chains.wusheng.remaining=n;self.cast(self.cont,7-n)
            self.assertEqual(state.chains.wusheng.remaining,n)
        self.assertEqual([r[2] for r in self.effects()],[echo.effect_guid(k) for k in ('intro','echo1','echo2','echo2','echo3','echo3')])
        self.assertEqual(state.frenzy,4);self.assertEqual(state.shield,7)
    def test_using_and_target_notifications_are_deduplicated_per_canonical_owner(self):
        self.cast();self.cast(target=True,id='Name_caster');self.cast()
        self.assertEqual(len(self.effects()),1)
        self.assertEqual(tuple(self.effects()[0][i] for i in (3,4)),('Dummy_Root',1))
    def test_distinct_owners_and_actions_never_suppress_each_other(self):
        self.F.actor('other');self.cast();self.cast(id='other');self.cast(action=2)
        self.assertEqual(len(self.effects()),3)
    def test_unknown_nonblood_or_dead_casts_never_emit(self):
        self.cast('Target_ESC_BloodPulse');self.cast('Projectile_ESC_xueyan_luexue')
        self.F.entities.caster.branch='taixuan';self.cast()
        self.F.entities.caster.branch='xueyan';self.F.entities.caster.alive=False;self.cast()
        self.assertEqual(self.effects(),[])
    def test_missing_invalid_or_finished_chain_never_replays_intro(self):
        state=self.F.entities.caster.Vars.ESC_State
        for n in (0,-1,6,2.5,'invalid'):
            state.chains.wusheng.remaining=n;self.cast(self.cont)
        state.chains.wusheng=None;self.cast(self.cont)
        self.assertEqual(self.effects(),[])
    def test_no_next_shadow_without_next_actual_cast_and_reload_only_clears_dedupe(self):
        self.cast();self.assertEqual(len(self.effects()),1)
        self.F.reload();self.assertEqual(len(self.effects()),1)
        self.cast();self.assertEqual(len(self.effects()),2)
    def test_native_playback_failure_is_visual_only(self):
        self.lua.execute('Osi.PlayEffect=function()error("native unavailable")end')
        self.cast();self.assertEqual(self.F.entities.caster.Vars.ESC_State.chains.wusheng.remaining,5)
    def test_disabled_config_registers_no_listeners(self):
        self.lua.execute('F.listeners={};Spec.xueyanEchoVfx.enabled=false')
        self.module.Install(self.lua.globals().E,self.lua.globals().Spec)
        self.assertEqual(list(self.F.listeners.keys()),[])


class RuntimeEchoIntegration(unittest.TestCase):
    def test_runtime_owns_all_six_chain_transitions_with_visual_listener_loaded_after_it(self):
        # Exercise actual production Runtime listener ordering and alias/chain
        # shapes instead of only manufacturing the visual module's input.
        import importlib.util
        spec=importlib.util.spec_from_file_location('echo_runtime_fixture',Path(__file__).with_name('test_tianqing_runtime_vfx.py'))
        fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
        h=fixture.TianqingRuntimeVfx();h.setUp()
        h.F.actor('blood',12,'xueyan',100,100,'players',0)
        h.lua.execute('Fixture.echoes={};function Osi.PlayEffect(...) Fixture.echoes[#Fixture.echoes+1]={...} end')
        module=h.lua.execute((LUA/'XueyanEchoVfx.lua').read_text('utf-8'))
        module.Install(h.lua.globals().ESC.Engine,h.lua.globals().GeneratedSpec)
        root='Projectile_ESC_xueyan_wusheng_F4';cont='Projectile_ESC_wusheng_ContinueRanged'
        for i in range(6):
            spell=root if i==0 else cont
            h.F.emit('UsingSpell','blood',spell,'Projectile','',100+i)
            h.F.emit('UsingSpellOnTarget','blood','enemy0',spell,'Projectile','',100+i)
            h.F.emit('CastedSpell','blood',spell,'Projectile','',100+i)
            state=h.F.entities.blood.Vars.ESC_State
            if i<5:self.assertEqual(state.chains.wusheng.remaining,5-i)
            else:self.assertIsNone(state.chains.wusheng)
        self.assertEqual([h.F.echoes[i][2] for i in range(1,7)],
                         [echo.effect_guid(k) for k in ('intro','echo1','echo2','echo2','echo3','echo3')])
        self.assertEqual(h.calls('UseSpell'),[])


if __name__=='__main__':unittest.main()
