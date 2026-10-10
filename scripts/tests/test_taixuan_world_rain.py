"""Production world-rain event/lifecycle regressions; simulated engine, no native QA."""
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import unittest

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'scripts'))
sys.path.insert(0,str(REPO/'build/test-tools'))
from lupa import LuaRuntime
FOLDER='EasternSwordCultivator_6560ea02-fe1e-5fdb-8631-b41a2e53af90'
LUA=REPO/'mods/EasternSwordCultivator/Source/Mods'/FOLDER/'ScriptExtender/Lua'
SPEC=json.loads((LUA/'GeneratedSpec.json').read_text(encoding='utf-8'))
module_spec=importlib.util.spec_from_file_location('native_fixture_boundary',REPO/'scripts/tests/test_tianqing_runtime_vfx.py')
native=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(native)
MODULE=(LUA/'TaixuanRainVfx.lua').read_text(encoding='utf-8')
RUNTIME=(LUA/'Runtime.lua').read_text(encoding='utf-8')
FIXTURE=(REPO/'scripts/tests/esc_engine_fixture.lua').read_text(encoding='utf-8')

def fixture(enabled=True):
    spec=copy.deepcopy(SPEC)
    spec['taixuanWorldRainVfx']={'enabled':enabled,'records':{'jiuxiao':{'effect':'fixture-jiuxiao'},'taiqing':{'effect':'fixture-taiqing'},'jiuxiao_background':{'effect':'fixture-jiuxiao-background'}}}
    lua=LuaRuntime(unpack_returned_tuples=True)
    lua.globals().GeneratedSpec=lua.table_from(spec,recursive=True)
    lua.execute(FIXTURE)
    stats={}
    for file in (REPO/'mods/EasternSwordCultivator/Source/Public'/FOLDER/'Stats/Generated/Data').glob('*.txt'):
        for chunk in re.split(r'(?=new entry ")',file.read_text(encoding='utf-8')):
            name=re.search(r'new entry "([^"]+)"',chunk)
            if name:stats[name[1]]=dict(re.findall(r'data "([^"]+)" "([^"]*)"',chunk))
    lua.globals().Fixture.stats=lua.table_from(stats,recursive=True)
    lua.execute(native.BOUNDARY)
    lua.execute('ESC={}')
    lua.globals().ESC.Rules=lua.execute((LUA/'Rules.lua').read_text(encoding='utf-8'))
    lua.globals().ESC.Engine=lua.execute((LUA/'Engine.lua').read_text(encoding='utf-8'))
    rain=lua.execute(MODULE)
    modules={'TaixuanRainVfx.lua':rain}
    def require(path):
        if path not in modules: modules[path]=lua.execute((LUA/path).read_text(encoding='utf-8'))
        return modules[path]
    lua.globals().Ext.Require=require
    lua.execute(RUNTIME)
    f=lua.globals().Fixture
    for owner,x in [('sword',0),('other',100)]:
        f.actor(owner,12,'taixuan',100,100,'players',x)
    for target,x in [('enemy',2),('otherEnemy',102)]:f.actor(target,0,None,100,100,'enemies',x)
    return lua,f,rain

def calls(f,name):return [c for c in f.calls.values() if c.name==name]
def pos(c):return tuple(c.args[i] for i in (2,3,4))
def plain(value):
    if hasattr(value,'items'):
        return tuple(sorted(((plain(k),plain(v)) for k,v in value.items()),key=lambda item:str(item[0])))
    return value
def open_domain(lua,f,owner='sword',focus='enemy',action=100):
    lua.globals().ESC.Runtime.State(owner).focus=focus
    spell=SPEC['spells']['taixuan_taiqing']['stat']
    f.emit('UsingSpell',owner,spell,'Shout','',action)
    f.emit('CastedSpell',owner,spell,'Shout','',action)

class WorldRainBehavior(unittest.TestCase):
    def test_three_native_roll_requests_stay_immediate_and_helpers_do_not_spend_resources(self):
        lua,f,_=fixture()
        open_domain(lua,f)
        helpers=calls(f,'UseSpell')
        self.assertEqual([c.args[2] for c in helpers],['Target_ESC_TaiqingPulse']*3)
        self.assertEqual([c.at for c in helpers],[0,0,0])
        self.assertEqual(len(f.nativeCasts),3)
        self.assertEqual(f.stats['Target_ESC_TaiqingPulse']['UseCosts'],'')

    def test_focus_three_world_anchors_are_separate_and_repeat_finish_cannot_replay(self):
        lua,f,_=fixture();open_domain(lua,f)
        effects=calls(f,'PlayEffectAtPosition')
        self.assertEqual(len(effects),3)
        points=[pos(c) for c in effects]
        self.assertEqual(len(set(points)),3)
        self.assertGreater(min(math.dist(a,b) for i,a in enumerate(points) for b in points[i+1:]),.79)
        for packet in f.nativeCasts.values():f.emit('CastedSpell',packet.source,packet.spell,'Target','',packet.action)
        self.assertEqual(len(calls(f,'PlayEffectAtPosition')),3)

    def test_miss_has_one_attempt_sword_failed_native_cast_has_none(self):
        lua,f,_=fixture()
        f.outcomes=lua.table_from([{'hit':False},{'failed':True},{'hit':True}],recursive=True)
        open_domain(lua,f)
        self.assertEqual(len(f.nativeCasts),3)
        self.assertEqual(len(calls(f,'PlayEffectAtPosition')),2)

    def test_missing_target_before_native_finish_discards_world_effect(self):
        lua,f,_=fixture();f.deferNative=True;open_domain(lua,f)
        self.assertEqual(len(calls(f,'PlayEffectAtPosition')),0)
        f.entities['enemy']=None
        # Complete the native event only: this fixture is not an attack engine.
        for packet in f.nativeCasts.values():f.emit('CastedSpell',packet.source,packet.spell,'Target','',packet.action)
        self.assertEqual(len(calls(f,'PlayEffectAtPosition')),0)

    def test_two_owners_do_not_share_positions_or_dedupe(self):
        lua,f,_=fixture();open_domain(lua,f,action=100);open_domain(lua,f,'other','otherEnemy',200)
        effects=calls(f,'PlayEffectAtPosition')
        self.assertEqual(len(effects),6)
        self.assertEqual(len([c for c in effects if c.args[2]<10]),3)
        self.assertEqual(len([c for c in effects if c.args[2]>90]),3)

    def test_jiuxiao_full_radius_and_target_anchor_snapshot_on_two_targets(self):
        lua,f,_=fixture();spell=SPEC['spells']['taixuan_jiuxiao']['stat'];action=300
        f.entities['enemy'].Transform.Transform.Translate=lua.table_from([10,2,20])
        f.entities['otherEnemy'].Transform.Transform.Translate=lua.table_from([13,2,20])
        f.emit('UsingSpell','sword',spell,'Target','',action)
        f.emit('UsingSpellAtPosition','sword',10,2,20,spell,'Target','',action)
        for target in ('enemy','otherEnemy'):f.emit('UsingSpellOnTarget','sword',target,spell,'Target','',action)
        f.entities['enemy'].Transform.Transform.Translate=lua.table_from([99,3,99])
        f.emit('CastedSpell','sword',spell,'Target','',action)
        effects=calls(f,'PlayEffectAtPosition')
        self.assertEqual(len(effects),20)
        background=effects[:18]
        self.assertTrue(all(math.hypot(c.args[2]-10,c.args[4]-20)<=5.600001 for c in background))
        self.assertAlmostEqual(max(math.hypot(c.args[2]-10,c.args[4]-20) for c in background),5.6)
        # Every world-effect scalar is 1; no gameplay call occurred in this VFX stage.
        self.assertTrue(all(c.args[5]==1 for c in effects))
        self.assertIn((10,2,20),[pos(c) for c in effects])
        self.assertNotIn((99,3,99),[pos(c) for c in effects])
        self.assertEqual(calls(f,'UseSpell'),[])

    def test_disabled_native_receipt_config_emits_no_world_queries_or_effects(self):
        lua,f,_=fixture(enabled=False);open_domain(lua,f)
        self.assertEqual(len(f.nativeCasts),3)
        self.assertEqual(calls(f,'FindValidPosition'),[])
        self.assertEqual(calls(f,'PlayEffectAtPosition'),[])

    def test_actual_area_half_damage_victim_after_finish_adds_one_sword_without_replay(self):
        lua,f,_=fixture();spell=SPEC['spells']['taixuan_jiuxiao']['stat'];action=350
        f.emit('UsingSpell','sword',spell,'Target','',action)
        f.emit('UsingSpellOnTarget','sword','enemy',spell,'Target','',action)
        f.emit('CastedSpell','sword',spell,'Target','',action)
        self.assertEqual(len(calls(f,'PlayEffectAtPosition')),19)
        context=lua.table_from(dict(source='sword',target='otherEnemy',action=action,key='taixuan_jiuxiao',
            hp=100,level=12,branch='taixuan',eligible=True,credited=8,final=8),recursive=True)
        event=lua.table_from({'Result':{'Hit':{'TotalDamageDone':8}}},recursive=True)
        # Half damage on a successful save has no ESC_HIT_MARKER. Capture the
        # existing DealtDamage path, never manufacture another attack or roll.
        lua.globals().ESC.Runtime.AfterDamage(event,context)
        self.assertEqual(len(calls(f,'PlayEffectAtPosition')),20)
        lua.globals().ESC.Runtime.AfterDamage(event,context)
        self.assertEqual(len(calls(f,'PlayEffectAtPosition')),20)
        self.assertEqual(calls(f,'UseSpell'),[])

    def test_large_ai_grid_jump_is_rejected_without_collapsing_three_swords(self):
        lua,f,_=fixture()
        f.ground=lua.eval('function(x,y,z) return 0,y+5,0 end')
        open_domain(lua,f)
        points=[pos(c) for c in calls(f,'PlayEffectAtPosition')]
        self.assertEqual(len(set(points)),3)
        self.assertTrue(all(p[1]==0 for p in points))
        self.assertTrue(all(p[0]>1 for p in points))

    def test_session_and_owner_cleanup_cancel_deferred_visual_only(self):
        for event in ('SessionLoaded','LeftCombat'):
            lua,f,_=fixture();f.deferNative=True;open_domain(lua,f)
            if event=='SessionLoaded':lua.globals().ESC.Runtime.SessionLoaded()
            else:f.emit('LeftCombat','sword','fixture-combat')
            for packet in f.nativeCasts.values():f.emit('CastedSpell',packet.source,packet.spell,'Target','',packet.action)
            self.assertEqual(len(f.nativeCasts),3)
            self.assertEqual(calls(f,'PlayEffectAtPosition'),[])

    def test_transfer_damage_recipient_does_not_acquire_a_rain_sword(self):
        lua,f,_=fixture();spell=SPEC['spells']['taixuan_jiuxiao']['stat'];action=400
        f.emit('UsingSpellOnTarget','sword','enemy',spell,'Target','',action)
        f.emit('CastedSpell','sword',spell,'Target','',action)
        count=len(calls(f,'PlayEffectAtPosition'))
        context=lua.table_from(dict(source='sword',target='otherEnemy',action=action,
            key='taixuan_jiuxiao',hp=100,level=12,branch='taixuan',eligible=False,
            credited=8,final=8,transfer=True),recursive=True)
        event=lua.table_from({'Result':{'Hit':{'TotalDamageDone':8}}},recursive=True)
        lua.globals().ESC.Runtime.AfterDamage(event,context)
        self.assertEqual(len(calls(f,'PlayEffectAtPosition')),count)

    def test_owner_death_cancels_deferred_swords_without_extra_casts(self):
        lua,f,_=fixture();f.deferNative=True;open_domain(lua,f)
        f.emit('StatusApplied','sword','DEAD','sword',500)
        for packet in f.nativeCasts.values():
            f.emit('CastedSpell',packet.source,packet.spell,'Target','',packet.action)
        self.assertEqual(len(f.nativeCasts),3)
        self.assertEqual(calls(f,'PlayEffectAtPosition'),[])

if __name__=='__main__':
    unittest.main()
