"""Read-only native authoring checks; rendering and event wiring stay separate."""
import copy
import hashlib
import itertools
import math
from pathlib import Path
import sys
import unittest
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import xingge_visual_polish as xg
from sword_cultivator_spec import SPELLS

DATA = Path('E:/SteamLibrary/steamapps/common/Baldurs Gate 3/Data')


def components(root, kind):
    return root.findall(f'./trackgroups/trackgroup/track/component[@class="{kind}"]')


def scalar(component, key):
    return component.find(f'./properties/property[@id="{key}"]/data/datum').get('value')


def ramps(component, key):
    return [[(float(k.get('time')), float(k.get('value')))
             for k in c.findall('./keyframes/keyframe')]
            for c in component.findall(
                f'./properties/property[@id="{key}"]/data/datum/rampchanneldata/rampchannel')]


class XinggePlan(unittest.TestCase):
    def test_eight_skills_and_unique_explicit_binding_roles(self):
        expected = {key for key, row in SPELLS.items() if row['branch'] == 'xingge'}
        self.assertEqual(len(expected), 8)
        self.assertEqual({p['skill'] for p in xg.PROFILES.values()}, expected)
        roles = [(p['skill'], p['binding']) for p in xg.PROFILES.values()]
        self.assertEqual(len(roles), len(set(roles)))
        for p in xg.PROFILES.values():
            self.assertEqual(p['binding'], 'hit' if p['phase'] == 'impact' else p['phase'])
            self.assertIn(p['binding'], ('cast', 'hit', 'target', 'status'))
            for field in ('trigger', 'recipient', 'lifecycle', 'presentation'):
                self.assertTrue(p[field])

    def test_target_and_event_roles_cannot_be_confused_with_caster_casts(self):
        expected = {'xingge_wenlu_mark', 'xingge_huifeng_target', 'xingge_fuchen_target',
                    'xingge_chengfeng_target', 'xingge_fengyu_transfer', 'xingge_xiangfu_target'}
        self.assertEqual({k for k, p in xg.PROFILES.items() if p['binding'] == 'target'}, expected)
        for key in expected:
            self.assertNotEqual(xg.PROFILES[key]['recipient'], 'caster')
        self.assertEqual(xg.PROFILES['xingge_tongzhou_cast']['recipient'], 'caster')
        self.assertIn('actual damage-share event', xg.PROFILES['xingge_fengyu_transfer']['trigger'])
        self.assertIn('actual resonance helper', xg.PROFILES['xingge_zhangjian_hit']['trigger'])
        self.assertIn('actual healing', xg.PROFILES['xingge_xiangfu_target']['trigger'])

    def test_support_nodes_do_not_author_a_six_metre_closed_ring(self):
        for key in ('xingge_fengyu_status', 'xingge_zhangjian_status'):
            p = xg.PROFILES[key]
            self.assertEqual(p['team_radius'], 6)
            self.assertLess(p['radius'], 1.5)
            self.assertEqual(p['alpha'], .38 if key == 'xingge_fengyu_status' else .42)
        angles = sorted(a % 360 for a in xg.ARC_ANGLES)
        gaps = [(angles[(i + 1) % len(angles)] - a) % 360 for i, a in enumerate(angles)]
        self.assertEqual(sorted(gaps)[-2:], [100, 100])


@unittest.skipUnless((DATA / 'Editor/Config/AllSpark/ComponentDefinition.xcd').is_file(),
                     'Installed native AllSpark definitions are required')
class XinggeNativeAuthoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dictionary = xg.fx.PropertyDictionary(DATA)
        cls.authored = {k: xg.author(DATA, k, cls.dictionary) for k in xg.PROFILES}

    def test_assets_have_stable_unique_ids_and_honest_activation_boundary(self):
        roots = set()
        for key, (root, origins, detail) in self.authored.items():
            with self.subTest(key=key):
                roots.add(root.get('id'))
                ids = [c.get('instancename') for c in root.findall('./trackgroups/trackgroup/track/component')]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertTrue(origins)
                self.assertTrue(all(p.is_file() for p in origins))
                self.assertFalse(detail['compiled'])
                self.assertFalse(detail['binding_enabled'])
                self.assertFalse(detail['produces_damage'])
                self.assertFalse(detail['gameplay_changed'])
                self.assertFalse(detail['automatic_event_replay'])
                self.assertTrue(components(root, 'BoundingSphere'))
        self.assertEqual(len(roots), len(self.authored))

    def test_damage_profiles_emit_one_simultaneous_peak_not_a_combo(self):
        for key, profile in xg.PROFILES.items():
            if profile['phase'] != 'impact':
                continue
            root, _, detail = self.authored[key]
            with self.subTest(key=key):
                self.assertEqual(detail['central_peak_count'], 1)
                self.assertEqual(detail['effect_repetitions'], 1)
                self.assertEqual(components(root, 'Model'), [])
                self.assertEqual(len(components(root, 'ParticleSystem')), 1 + len(profile['angles']))
                for c in components(root, 'ParticleSystem'):
                    self.assertEqual(float(c.get('start')), 0)
                    self.assertEqual(scalar(c, xg.fx.INITIAL_COUNT), '1,1')
                    self.assertTrue(all(v == 0 for ch in ramps(c, xg.fx.EMIT_RATE) for _, v in ch))
                    self.assertLessEqual(max(v for ch in ramps(c, xg.fx.LIFESPAN) for _, v in ch), .45)

    def test_support_composition_has_two_open_arcs_without_shells_or_ribbons(self):
        for key, profile in xg.PROFILES.items():
            if profile['phase'] == 'impact':
                continue
            root, _, detail = self.authored[key]
            with self.subTest(key=key):
                models = components(root, 'Model')
                self.assertEqual(len(models), 6)
                self.assertTrue(all(xg.tx.LONGSWORD in scalar(c, xg.fx.MESH) for c in models))
                self.assertEqual(components(root, 'Ribbon 2.0'), [])
                self.assertFalse(detail['sphere_shell'])
                self.assertFalse(detail['full_circle'])
                self.assertFalse(detail['cross_entity_beam'])
                self.assertEqual(detail['minimum_open_gap_degrees'], 100)
                # Tangential blades and nonrotating offsets keep both gaps
                # open instead of sweeping a hidden 360-degree guard loop.
                for c, angle in zip(models, xg.ARC_ANGLES):
                    self.assertTrue(all(v == -angle for _, v in ramps(c, xg.tx.MODEL_ROTATION)[1]))
                    for prop in (xg.tx.MODEL_ROTATION_RPM, xg.tx.MODEL_ROTATION_LIFE):
                        self.assertTrue(all(v == 0 for ch in ramps(c, prop) for _, v in ch))

    def test_finite_effects_clear_native_loop_and_fade_completely(self):
        for key, profile in xg.PROFILES.items():
            if profile['phase'] not in ('cast', 'target'):
                continue
            root, _, detail = self.authored[key]
            with self.subTest(key=key):
                self.assertEqual(list(root.find('phases')), [])
                self.assertFalse(detail['looping'])
                self.assertLessEqual(detail['duration'], 1.25)
                self.assertEqual(float(components(root, 'BoundingSphere')[0].get('end')), detail['duration'])
                for c in components(root, 'Model'):
                    alpha, = ramps(c, xg.tx.MODEL_ALPHA)
                    self.assertEqual(alpha[0][1], 0)
                    self.assertEqual(alpha[-1][1], 0)
                    self.assertLessEqual(max(v for _, v in alpha), .46)
                for c in components(root, 'ParticleSystem'):
                    life = max(v for ch in ramps(c, xg.fx.LIFESPAN) for _, v in ch)
                    self.assertLessEqual(float(c.get('end')) + life, detail['duration'])

    def test_status_loops_have_matching_seams_and_follow_the_recipient(self):
        def at(channel, time):
            actual, value = min(channel, key=lambda item: abs(item[0] - time))
            self.assertAlmostEqual(actual, time, places=7)
            return value

        for key in ('xingge_fengyu_status', 'xingge_zhangjian_status'):
            root, _, detail = self.authored[key]
            self.assertTrue(any(p.get('playcount') == '-1' for p in root.findall('./phases/object/data')))
            self.assertEqual(detail['attachment'], 'actual recipient root')
            self.assertEqual(detail['loop_seconds'], 3.6)
            for c in components(root, 'Model'):
                for channel in ramps(c, xg.tx.MODEL_OFFSET):
                    self.assertAlmostEqual(at(channel, .2 / 4.2), at(channel, 3.8 / 4.2))
                alpha, = ramps(c, xg.tx.MODEL_ALPHA)
                self.assertEqual(at(alpha, .2 / 4.2), at(alpha, 3.8 / 4.2))
            for c in components(root, 'ParticleSystem'):
                self.assertEqual(scalar(c, 'b13c2ffd-c94f-4d56-947e-07077287ec52'), '1')

    def test_wisps_preserve_one_active_native_colour_module_and_short_lifetimes(self):
        for key, profile in xg.PROFILES.items():
            if profile['phase'] == 'impact':
                continue
            root, _, detail = self.authored[key]
            particles = components(root, 'ParticleSystem')
            self.assertEqual(len(particles), 2 if profile['wisps'] else 0)
            for c in particles:
                active = [m for m in c.findall('./modules/module')
                          if m.get('id', '').lower() == 'b369fad0-cc26-42f3-bdc2-0b8f120c6081'
                          and m.get('muted', 'False') == 'False']
                self.assertEqual(len(active), 1)
                self.assertLessEqual(max(v for ch in ramps(c, xg.fx.LIFESPAN) for _, v in ch), .35)
                self.assertNotEqual(float(scalar(c, xg.tx.PARTICLE_OFFSET).split(',')[0]), 0)

    def test_model_paths_fit_declared_culling_bounds(self):
        from sword_glow import _rotation
        for key, (root, _, detail) in self.authored.items():
            radius = float(scalar(components(root, 'BoundingSphere')[0], xg.fx.BOUND_RADIUS))
            for c in components(root, 'Model'):
                offsets = ramps(c, xg.tx.MODEL_OFFSET)
                scale = [channel[0][1] for channel in ramps(c, xg.fx.MODEL_SCALE)]
                rotation = _rotation([channel[0][1] for channel in ramps(c, xg.tx.MODEL_ROTATION)])
                position = tuple(map(float, scalar(c, xg.fx.POSITION).split(',')))
                for point in zip(*offsets):
                    offset = [value for _, value in point]
                    for corner in itertools.product(*zip(*xg.tx.STEEL_SWORD_BOUNDS)):
                        world = [position[i] + offset[i] + sum(
                            rotation[i][j] * corner[j] * scale[j] for j in range(3)) for i in range(3)]
                        self.assertLessEqual(math.sqrt(sum(v * v for v in world)), radius)

    def test_existing_glow_conversion_preserves_paths_alpha_and_native_loop(self):
        from sword_glow import apply, visual_id, _rotation
        for key, (authored, _, detail) in self.authored.items():
            root = copy.deepcopy(authored)
            before = [(ramps(c, xg.tx.MODEL_OFFSET), ramps(c, xg.tx.MODEL_ALPHA))
                      for c in components(root, 'Model')]
            phases = ET.tostring(root.find('phases'))
            proof = apply(root, self.dictionary, 'xingge')
            self.assertEqual(proof['luminous_swords'], len(before))
            self.assertEqual(ET.tostring(root.find('phases')), phases)
            for c, (offset, alpha) in zip(components(root, 'Model'), before):
                self.assertIn(visual_id('xingge'), scalar(c, xg.fx.MESH))
                self.assertEqual(ramps(c, xg.tx.MODEL_OFFSET), offset)
                self.assertEqual(ramps(c, xg.tx.MODEL_ALPHA), alpha)
                if key in ('xingge_fengyu_status', 'xingge_zhangjian_status'):
                    rotation = _rotation([channel[0][1] for channel in ramps(c, xg.tx.MODEL_ROTATION)])
                    # Native +Y points to the tip: Fengyu raises a guard,
                    # Zhangjian holds a longer blade at a slight attack angle.
                    pitch = 20 if key == 'xingge_fengyu_status' else -12
                    self.assertAlmostEqual(rotation[1][1], math.sin(math.radians(pitch)), places=7)
                    width = (xg.tx.NATIVE_SWORD['maximum'][0] - xg.tx.NATIVE_SWORD['minimum'][0]) * ramps(c, xg.fx.MODEL_SCALE)[0][0][1]
                    self.assertAlmostEqual(width, .65 * (xg.tx.STEEL_SWORD_BOUNDS[1][0] - xg.tx.STEEL_SWORD_BOUNDS[0][0]), places=7)

    def test_reauthoring_is_deterministic_and_native_origins_are_untouched(self):
        origins = {p for _, paths, _ in self.authored.values() for p in paths}
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in origins}
        for key, (root, _, _) in self.authored.items():
            again, _, _ = xg.author(DATA, key, self.dictionary)
            self.assertEqual(ET.tostring(root), ET.tostring(again))
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in origins})


if __name__ == '__main__':
    unittest.main()
