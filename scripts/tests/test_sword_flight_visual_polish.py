"""Foot sword geometry and attachment cannot replace real native Fly mechanics."""
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import school_visual_polish as bindings
import sword_flight_visual_polish as flight
import sword_glow
from test_tianfeng_visual_polish import ramps


class SwordFlightBinding(unittest.TestCase):
    def test_existing_flight_status_owns_attachment_and_unrelated_statuses_do_not(self):
        record = {**flight.PROFILES[flight.KEY], 'mei': 'foot-sword'}
        self.assertEqual(bindings.status_bindings('ESC_IN_FLIGHT', {flight.KEY: record}),
                         {'StatusEffect': 'foot-sword'})
        for name in ('ESC_CHAIN_LIANCHENG', 'ESC_COUNTER_RANK2', 'ESC_VFX_DAMAGE_SHARE'):
            self.assertEqual(bindings.status_bindings(name, {flight.KEY: record}), {})
        editor, _ = bindings._mei(flight.KEY, record)
        effect, = editor.findall('EffectInfo')
        self.assertEqual(effect.get('TargetBone'), 'Dummy_Root')
        self.assertEqual(effect.get('Pivot'), 'Target')
        for field in ('DetachTarget', 'DetachSource', 'KeepRotation', 'UseDistance'):
            self.assertEqual(effect.get(field), 'false')
        self.assertNotIn('StartTextKey', effect.attrib)

    def test_human_fly_and_activation_retain_every_gameplay_and_animation_field(self):
        records = {flight.KEY: {**flight.PROFILES[flight.KEY], 'mei': 'foot-sword'}}
        fields = dict(SpellType='Projectile', SpellFlags='IsJump', Trajectories='native-fly',
                      UseCosts='ESC_FlightMovement:Distance', SpellJumpType='Flight',
                      SpellAnimation='native-fly-animation', CastEffect='native-fly-takeoff')
        self.assertEqual(bindings.spell_bindings('Projectile_ESC_FlightMove', fields, records), {})
        self.assertEqual(bindings.spell_bindings('Shout_ESC_sword_flight',
                         dict(SpellType='Shout', UseCosts='BonusActionPoint:1'), records), {})


@unittest.skipUnless((flight.fx.DATA / 'Editor/Config/AllSpark/ComponentDefinition.xcd').is_file(),
                     'Installed native AllSpark components are required')
class SwordFlightAuthoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dictionary = flight.fx.PropertyDictionary(flight.fx.DATA)
        cls.root, cls.origins, cls.details = flight.author(flight.fx.DATA, flight.KEY, cls.dictionary)
        sword_glow.apply(cls.root, cls.dictionary, 'common')

    def test_complete_broad_horizontal_blade_points_forward_and_wakes_backward(self):
        models = self.root.findall('.//component[@class="Model"]')
        self.assertEqual(len(models), 3)
        swords = [c for c in models if sword_glow.visual_id('common') in
                  c.find(f'./properties/property[@id="{flight.fx.MESH}"]/data/datum').get('value')]
        self.assertEqual(len(swords), 1)
        sword, = swords
        rotation = sword_glow._rotation(tuple(ch[0][1] for ch in ramps(sword, flight.fall.INITIAL_ROTATION)))
        # Luminous native mesh tip +Y maps into forward -Z, with no vertical tilt.
        for actual, expected in zip((rotation[i][1] for i in range(3)), (0, 0, -1)):
            self.assertAlmostEqual(actual, expected)
        self.assertGreater(self.details['sword_length'], 2.8)
        self.assertLess(self.details['sword_length'], 3.)
        self.assertGreater(self.details['sword_width'], .7)
        for model in models:
            for field in (flight.fall.KEYFRAMED_OFFSET, flight.fall.ROTATION_RPM, flight.fall.ROTATION_LIFE):
                self.assertTrue(all(v == 0 for ch in ramps(model, field) for _, v in ch))
            if model is not sword:
                r = sword_glow._rotation(tuple(ch[0][1] for ch in ramps(model, flight.fall.INITIAL_ROTATION)))
                for actual, expected in zip((-r[i][1] for i in range(3)), (0, 0, 1)):
                    self.assertAlmostEqual(actual, expected)
        # The actual reference bounds keep the blade below shin height.
        top = flight.GREAT_SWORD['bounds_max'][1] * flight.SWORD_SCALE[1] + flight.SWORD_POSITION[1]
        bottom = flight.GREAT_SWORD['bounds_min'][1] * flight.SWORD_SCALE[1] + flight.SWORD_POSITION[1]
        self.assertGreater(bottom, 0)
        self.assertLess(top, .13)

    def test_stable_loop_has_bounded_fade_without_implicit_timer_or_world_path(self):
        phases = self.root.findall('./phases/object/data')
        self.assertEqual([p.get('playcount') for p in phases], ['1', '-1', '1'])
        self.assertEqual([float(p.get('duration')) for p in phases],
                         [flight.LEAD_IN, flight.LOOP, flight.LEAD_OUT])
        for component in self.root.findall('.//component[@class="Model"]'):
            alpha, = ramps(component, flight.fall.ALPHA)
            self.assertEqual(alpha[0][1], 0)
            self.assertEqual(alpha[-1][1], 0)
            self.assertEqual(alpha[1][1], alpha[2][1])
            self.assertGreaterEqual(alpha[1][1], .65)
            self.assertAlmostEqual(float(component.get('end')), flight.DURATION)
        bound, = self.root.findall('.//component[@class="BoundingSphere"]')
        self.assertAlmostEqual(float(bound.get('end')), flight.DURATION)
        self.assertFalse(self.details['world_path'])

    def test_author_is_deterministic_and_preserves_all_native_donors(self):
        before = {p: flight.fx.digest(p) for p in self.origins}
        dictionary = flight.fx.PropertyDictionary(flight.fx.DATA)
        other, _, _ = flight.author(flight.fx.DATA, flight.KEY, dictionary)
        sword_glow.apply(other, dictionary, 'common')
        self.assertEqual(ET.tostring(other), ET.tostring(self.root))
        self.assertEqual(before, {p: flight.fx.digest(p) for p in self.origins})


if __name__ == '__main__':
    unittest.main()
