"""Verify source invariants; these checks never write or compile an effect."""
import math
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import xueyan_visual_polish as visual

DATA = Path('E:/SteamLibrary/steamapps/common/Baldurs Gate 3/Data')


def prop(component, key):
    return component.find(f'./properties/property[@id="{key}"]')


def values(component, key):
    return [float(frame.get('value')) for frame in prop(component, key).findall('.//keyframe')]


class XueyanPolish(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (DATA / 'Editor/Config/AllSpark/ComponentDefinition.xcd').is_file():
            raise unittest.SkipTest('Installed native AllSpark authoring dictionaries are unavailable')
        dictionary = visual.fx.PropertyDictionary(DATA)
        cls.authored = {key: visual.author(DATA, key, dictionary) for key in visual.PROFILES}
        native = ET.parse(DATA / visual.fx.BLOOD).getroot()
        cls.smoke = next(c for c in native.findall('./trackgroups/trackgroup/track/component')
                         if c.get('instancename') == visual.SMOKE_INSTANCE)

    def test_profiles_cover_all_nine_skills_with_explicit_bindings(self):
        self.assertEqual({p['skill'] for p in visual.PROFILES.values()}, {
            'xueyan_luexue', 'xueyan_chuanshen', 'xueyan_ranxue', 'xueyan_liancheng',
            'xueyan_nixue', 'xueyan_xuehai', 'xueyan_wusheng', 'xueyan_huichao', 'xueyan_damage_mode'})
        for p in visual.PROFILES.values():
            self.assertIn(p['binding'], ('hit', 'cast', 'status'))
            self.assertTrue(p['presentation'])

    def test_native_smoke_colour_lifetime_and_flipbook_are_preserved(self):
        keys = [visual.fx.PARTICLE_COLOR, visual.fx.LIFESPAN,
                'b0a263d3-3d10-466d-8028-91be42b846e9', '346b8050-9a4e-49ad-8d58-f9c92585aaa7']
        for key, (root, origins, details) in self.authored.items():
            smoke = root.find('./trackgroups/trackgroup[@name="Native red mist"]')
            self.assertIsNotNone(smoke)
            for component in smoke.findall('./track/component'):
                for property_id in keys:
                    with self.subTest(key=key, property=property_id):
                        self.assertEqual(ET.tostring(prop(component, property_id)),
                                         ET.tostring(prop(self.smoke, property_id)))

    def test_combo_banks_have_one_sword_peak_and_no_repeated_attack_timeline(self):
        for key in ('xueyan_liancheng_hit', 'xueyan_wusheng_hit'):
            root, origins, details = self.authored[key]
            swords = root.findall('./trackgroups/trackgroup[@name="Short blood sword accents"]/track/component')
            self.assertEqual(len(swords), 1)
            self.assertEqual(list(root.find('phases')), [])
            self.assertEqual(details['bank_attack_stages'], 1)
            alpha = values(swords[0], visual.MODEL_ALPHA)
            self.assertEqual(sum(value == max(alpha) for value in alpha), 1)
            self.assertLess(float(swords[0].get('end')), .5)

    def test_impact_blade_starts_before_mist_and_all_source_bounds_cover_tails(self):
        for key, (root, origins, details) in self.authored.items():
            bounds = next(c for c in root.findall('./trackgroups/trackgroup/track/component')
                          if c.get('class') == 'BoundingSphere')
            self.assertEqual(float(bounds.get('end')), details['duration'])
            for component in root.findall('./trackgroups/trackgroup[@name="Native red mist"]/track/component'):
                self.assertGreaterEqual(float(bounds.get('end')), float(component.get('end')) + max(values(component, visual.fx.LIFESPAN)))
                if visual.PROFILES[key]['phase'] == 'impact':
                    self.assertGreater(float(component.get('start')), 0)
            self.assertFalse(details['compiled'])
            self.assertFalse(details['binding_enabled'])

    def test_domain_is_local_readable_low_ring_and_only_domain_loops(self):
        for key, (root, origins, details) in self.authored.items():
            loops = [phase for phase in root.findall('./phases/object/data') if phase.get('playcount') == '-1']
            self.assertEqual(bool(loops), key == 'xueyan_xuehai_status')
        root, origins, details = self.authored['xueyan_xuehai_status']
        smoke = root.findall('./trackgroups/trackgroup[@name="Native red mist"]/track/component')
        self.assertEqual(len(smoke), 12)
        for component in smoke:
            datum = prop(component, visual.PARTICLE_OFFSET).find('./data/datum')
            x, y, z = map(float, datum.get('value').split(','))
            self.assertAlmostEqual(math.hypot(x, z), 6, places=7)
            self.assertEqual(y, .15)
            self.assertEqual(prop(component, visual.SPACE).find('./data/datum').get('value'), '1')
            self.assertAlmostEqual(max(values(component, visual.PARTICLE_ALPHA)), .45)

    def test_domain_boundary_uses_existing_open_annulus_at_six_metre_radius(self):
        import xuehai_boundary_visual_polish as boundary
        root, origins, details = self.authored['xueyan_xuehai_status']
        models = root.findall('./trackgroups/trackgroup[@name="Persistent open bloodsea boundary"]/track/component')
        self.assertEqual(len(models), 1)
        model = models[0]
        self.assertIn(boundary.VISUAL,
                      prop(model, visual.fx.MESH).find('./data/datum').get('value'))
        self.assertEqual(values(model, visual.fx.MODEL_SCALE), [6, 6, 6, 6, 1, 1])
        self.assertEqual(values(model, visual.MODEL_ROTATION), [90, 90, 0, 0, 0, 0])
        self.assertEqual(values(model, visual.MODEL_POSITION), [0] * 6)
        self.assertEqual(prop(model, visual.fx.POSITION).find('./data/datum').get('value'), '0,0.4,0')
        # XY annulus rotated X90 stays in the owner's horizontal XZ plane.
        self.assertFalse(details.get('terrain_adaptation', False))

    def test_domain_boundary_holds_through_loop_and_fades_on_status_end(self):
        root, origins, details = self.authored['xueyan_xuehai_status']
        model = root.find('./trackgroups/trackgroup[@name="Persistent open bloodsea boundary"]/track/component')
        duration = float(model.get('end'))
        frames = prop(model, visual.MODEL_ALPHA).findall('.//keyframe')
        timeline = [(float(f.get('time')) * duration, float(f.get('value'))) for f in frames]
        self.assertEqual([round(t, 6) for t, a in timeline], [0, .1, 3.7, 5.8])
        self.assertEqual([a for t, a in timeline], [0, .45, .45, 0])
        self.assertEqual(values(model, visual.MODEL_BRIGHTNESS), [.8, .8])
        # Other blood skills keep their established one-shot composition.
        for key, (other, origins, details) in self.authored.items():
            if key != 'xueyan_xuehai_status':
                self.assertIsNone(other.find('./trackgroups/trackgroup[@name="Persistent open bloodsea boundary"]'))

    def test_inward_wisps_have_an_active_native_three_axis_position_module(self):
        for key in ('xueyan_huichao_cast', 'xueyan_ranxue_cast'):
            root, origins, details = self.authored[key]
            for component in root.findall('./trackgroups/trackgroup[@name="Native red mist"]/track/component'):
                channels = prop(component, visual.PARTICLE_POSITION).findall('./data/datum/rampchanneldata/rampchannel')
                self.assertEqual(len(channels), 3)
                self.assertTrue(any(m.get('id').lower() == '7a790ae7-3b1c-463e-bb1f-5cc14980b78c'
                                    and m.get('muted') == 'False' for m in component.findall('./modules/module')))
                offset = list(map(float, prop(component, visual.PARTICLE_OFFSET).find('./data/datum').get('value').split(',')))
                finish = [offset[i] + float(channels[i].findall('./keyframes/keyframe')[-1].get('value')) for i in range(3)]
                self.assertLess(math.hypot(finish[0], finish[2]), math.hypot(offset[0], offset[2]))

    def test_recovery_has_six_luminous_inward_threads_that_hold_at_chest(self):
        root, origins, details = self.authored['xueyan_huichao_cast']
        threads = root.findall('./trackgroups/trackgroup[@name="Converging recovery bloodlight"]/track/component')
        self.assertEqual(len(threads), 6)
        self.assertEqual(details['sword_count'], 0)
        for c in threads:
            offset = list(map(float, prop(c, visual.PARTICLE_OFFSET).find('./data/datum').get('value').split(',')))
            self.assertAlmostEqual(math.hypot(offset[0], offset[2]), 2.1, places=5)
            channels = prop(c, visual.PARTICLE_POSITION).findall('./data/datum/rampchanneldata/rampchannel')
            end = [offset[i] + float(channels[i].findall('./keyframes/keyframe')[-1].get('value')) for i in range(3)]
            self.assertAlmostEqual(math.hypot(end[0],end[2]), 0, places=5)
            self.assertAlmostEqual(end[1], 1.15, places=5)
            self.assertEqual(values(c, visual.PARTICLE_ALPHA), [0, .95, .95, .75, 0])
            self.assertEqual(values(c, visual.fx.LIFESPAN), [1.35]*4)

    def test_only_recovery_gains_threads_and_both_costs_share_its_cast_effect(self):
        for key,(r,origins,details) in self.authored.items():
            found=r.find('./trackgroups/trackgroup[@name="Converging recovery bloodlight"]')
            self.assertEqual(found is not None,key=='xueyan_huichao_cast')
        import re
        from sword_cultivator_spec import FOLDER
        source=SCRIPTS.parent/'mods/EasternSwordCultivator/Source/Public'/FOLDER/'Stats/Generated/Data/Spell_Target.txt'
        entries={}
        for chunk in re.split(r'(?=new entry ")',source.read_text('utf-8')):
            name=re.search(r'new entry "([^"]+)"',chunk)
            if name:entries[name.group(1)]=dict(re.findall(r'data "([^"]+)" "([^"]*)"',chunk))
        self.assertEqual(entries['Target_ESC_xueyan_huichao_Yuan']['CastEffect'],
                         entries['Target_ESC_xueyan_huichao_Frenzy']['CastEffect'])
        for suffix in ('Yuan', 'Frenzy'):
            self.assertEqual(entries['Target_ESC_xueyan_huichao_'+suffix]['PrepareEffect'], '')

    def test_recovery_axis_alignment_points_each_thread_at_the_chest(self):
        root, _, _ = self.authored['xueyan_huichao_cast']
        directions = set()
        for c in root.findall('./trackgroups/trackgroup[@name="Converging recovery bloodlight"]/track/component'):
            offset = list(map(float, prop(c, visual.PARTICLE_OFFSET).find('data/datum').get('value').split(',')))
            axis = tuple(map(float, prop(c, '917df2bc-bbb3-4205-8d28-2450ea069f00').find('data/datum').get('value').split(',')))
            to_chest = (-offset[0], 1.15-offset[1], -offset[2])
            length = math.sqrt(sum(x*x for x in to_chest))
            self.assertAlmostEqual(sum(x*x for x in axis), 1, places=6)
            self.assertAlmostEqual(sum(a*b for a,b in zip(axis,to_chest))/length, 1, places=6)
            self.assertEqual(prop(c,'c6f612f7-5a7a-4c31-88c3-e554a499cc12').find('data/datum').get('value'), '1')
            self.assertEqual(prop(c,'8918e423-678f-4a00-ba83-47ccbcf45048').find('data/datum').get('value'), '1')
            self.assertEqual(values(c,'79ab5e9c-2d87-496c-83bd-1b6c78cbd095'), [.01]*4)
            directions.add(axis)
        self.assertEqual(len(directions), 6)

    def test_recovery_has_one_opacity_curve_and_readable_bounded_red_threads(self):
        root, _, _ = self.authored['xueyan_huichao_cast']
        for c in root.findall('./trackgroups/trackgroup[@name="Converging recovery bloodlight"]/track/component'):
            for packed in values(c, visual.fx.PARTICLE_COLOR):
                argb = int(packed) & 0xffffffff
                self.assertEqual(argb>>24, 255)
                self.assertEqual((argb>>16)&255, 255)
                self.assertLess((argb>>8)&255, 32)
                self.assertLess(argb&255, 32)
            width = values(c,visual.fx.PARTICLE_SCALE)[0]*values(c,visual.fx.PARTICLE_AXES)[0]
            self.assertGreater(width, .6)
            self.assertLess(width, 1)
            light = values(c,visual.PARTICLE_BRIGHTNESS)
            self.assertGreater(max(light), 4)
            self.assertLessEqual(max(light), 8)
            self.assertLessEqual(max(light[2:]), 3)


if __name__ == '__main__':
    unittest.main()
