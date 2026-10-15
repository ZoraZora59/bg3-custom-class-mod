"""Validate in-memory Taixuan authoring, without writing or compiling assets."""
import hashlib
import math
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import taixuan_visual_polish as tx
from sword_cultivator_spec import SPELLS

DATA = Path('E:/SteamLibrary/steamapps/common/Baldurs Gate 3/Data')


def components(root, kind):
    return [c for c in root.findall('./trackgroups/trackgroup/track/component')
            if c.get('class') == kind]


def scalar(component, key):
    return component.find(f'./properties/property[@id="{key}"]/data/datum').get('value')


def ramps(component, key):
    return [[(float(frame.get('time')), float(frame.get('value')))
             for frame in channel.findall('./keyframes/keyframe')]
            for channel in component.findall(
                f'./properties/property[@id="{key}"]/data/datum/rampchanneldata/rampchannel')]



# Verified native Visual resource GUIDs. EnergyRing is not a sword or a shell.
SPIRITUAL_SWORD = '3727a57a-e4be-44da-02b4-5061028fed5f'
ENERGY_RING = '36c6fe7b-25b9-19fe-a285-d750d070b6ff'
BLUE_CORE = '27169e30-e769-5199-2378-1cb3f2ad4f38'
NATIVE_CAST_KEYS = {'taixuan_jiuxiao_cast', 'taixuan_taiqing_cast'}
NATIVE_HIT_KEYS = {'taixuan_jiuxiao_hit', 'taixuan_taiqing_hit'}


def is_sword(model):
    return any(uid in scalar(model, tx.fx.MESH) for uid in (tx.LONGSWORD, SPIRITUAL_SWORD))


class TaixuanPolishPlan(unittest.TestCase):
    def test_every_taixuan_named_skill_has_a_cast_and_no_unknown_keys(self):
        skills = {key for key, value in SPELLS.items() if value['branch'] == 'taixuan'}
        self.assertEqual({p['skill'] for p in tx.PROFILES.values()}, skills)
        self.assertEqual({p['skill'] for p in tx.PROFILES.values() if p['binding'] == 'cast'}, skills)
        for key, profile in tx.PROFILES.items():
            with self.subTest(key=key):
                self.assertEqual(profile['binding'], 'hit' if profile['phase'] == 'impact' else profile['phase'])
                self.assertTrue(profile['presentation'])

    def test_healing_has_no_impact_and_actual_stages_are_not_repeated_in_banks(self):
        self.assertNotIn('taixuan_guiyuan_hit', tx.PROFILES)
        self.assertIn('taixuan_liuguang_hit', tx.PROFILES)
        self.assertIn('taixuan_taiqing_hit', tx.PROFILES)
        self.assertEqual(tx.PROFILES['taixuan_taiqing_status']['radius'], 6)
        self.assertEqual(tx.PROFILES['taixuan_taiqing_status']['shell_alpha'], 0)
        self.assertEqual(tx.PROFILES['taixuan_qinghui_status']['count'], 0)
        self.assertEqual(tx.PROFILES['taixuan_xinghe_status']['count'], 0)


@unittest.skipUnless((DATA / 'Editor/Config/AllSpark/ComponentDefinition.xcd').is_file(),
                     'Installed native AllSpark definitions are required for source authoring checks')
class TaixuanNativeAuthoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dictionary = tx.fx.PropertyDictionary(DATA)
        cls.authored = {key: tx.author(DATA, key, cls.dictionary) for key in tx.PROFILES}

    def test_identity_and_provenance_are_unique_and_no_asset_claims_activation(self):
        root_ids = []
        for key, (root, origins, details) in self.authored.items():
            with self.subTest(key=key):
                root_ids.append(root.get('id'))
                identities = [c.get('instancename') for c in root.findall('./trackgroups/trackgroup/track/component')]
                self.assertEqual(len(identities), len(set(identities)))
                self.assertTrue(origins)
                self.assertTrue(all(path.is_file() for path in origins))
                self.assertFalse(details['compiled'])
                self.assertFalse(details['binding_enabled'])
                self.assertTrue(components(root, 'BoundingSphere'))
        self.assertEqual(len(root_ids), len(set(root_ids)))

    def test_impacts_have_one_core_with_one_emission_and_simultaneous_glint_rays(self):
        for key, profile in tx.PROFILES.items():
            if profile['phase'] != 'impact':
                continue
            root, _, details = self.authored[key]
            particles = components(root, 'ParticleSystem')
            with self.subTest(key=key):
                self.assertEqual(len(particles), 1 + len(profile['angles']))
                self.assertEqual(details['central_peak_count'], 1)
                self.assertEqual(details['effect_repetitions'], 1)
                self.assertFalse(details['full_distance_beam'])
                for particle in particles:
                    self.assertEqual(float(particle.get('start')), 0)
                    self.assertEqual(scalar(particle, tx.fx.INITIAL_COUNT), '1,1')
                    self.assertTrue(all(value == 0 for channel in ramps(particle, tx.fx.EMIT_RATE)
                                        for _, value in channel))
                    self.assertLessEqual(max(value for channel in ramps(particle, tx.fx.LIFESPAN)
                                             for _, value in channel), .45)
                angles = [ramps(p, tx.PARTICLE_ANGLE)[0][0][1] for p in particles[1:]]
                self.assertEqual(angles, list(profile['angles']))

    def test_casts_have_exactly_their_sword_motif_no_loop_or_particle_damage_proxy(self):
        for key, profile in tx.PROFILES.items():
            if profile['phase'] != 'cast':
                continue
            root, _, details = self.authored[key]
            with self.subTest(key=key):
                models = components(root, 'Model')
                self.assertEqual(len(models), profile['count'])
                self.assertFalse(root.findall('./phases/object/data'))
                self.assertEqual(components(root, 'ParticleSystem'), [])
                self.assertFalse(details['produces_damage'])
                for model in models:
                    expected_visual = SPIRITUAL_SWORD if key in NATIVE_CAST_KEYS else tx.LONGSWORD
                    self.assertIn(expected_visual, scalar(model, tx.fx.MESH))
                    rotation = ramps(model, tx.MODEL_ROTATION)
                    self.assertEqual([[v for _, v in c] for c in rotation],
                                     [[0, 0], [0, 0], [0, 0]] if key in NATIVE_CAST_KEYS else [[90, 90], [0, 0], [0, 0]])
                    alpha = ramps(model, tx.MODEL_ALPHA)[0]
                    self.assertEqual(alpha[0][1], 0)
                    self.assertEqual(alpha[-1][1], 0)
                    for channel in ramps(model, tx.MODEL_ROTATION_RPM):
                        self.assertTrue(all(value == 0 for _, value in channel))

    def test_status_orbits_match_radius_have_closed_loop_seams_and_faint_alpha(self):
        for key, profile in tx.PROFILES.items():
            if profile['phase'] != 'status':
                continue
            root, _, details = self.authored[key]
            swords = [model for model in components(root, 'Model')
                      if is_sword(model)]
            with self.subTest(key=key):
                self.assertEqual(len(swords), profile['count'])
                self.assertTrue(any(phase.get('playcount') == '-1'
                                    for phase in root.findall('./phases/object/data')))
                for sword in swords:
                    native = key == 'taixuan_taiqing_status'
                    self.assertIn(tx.LONGSWORD, scalar(sword, tx.fx.MESH))
                    self.assertEqual([[v for _, v in c] for c in ramps(sword, tx.MODEL_ROTATION)],
                                     [[90, 90], [0, 0], [0, 0]])
                    channels = ramps(sword, tx.MODEL_OFFSET)
                    for channel in channels:
                        self.assertAlmostEqual(channel[0][1], channel[-1][1], places=7)
                    for (_, x), (_, z) in zip(channels[0], channels[2]):
                        self.assertAlmostEqual(math.hypot(x, z), profile['radius'], places=6)
                    self.assertTrue(all(value <= (.85 if native else .48) for _, value in ramps(sword, tx.MODEL_ALPHA)[0]))
                cores = [m for m in components(root, 'Model') if BLUE_CORE in scalar(m, tx.fx.MESH)]
                self.assertEqual(len(cores), profile['count'] if key == 'taixuan_taiqing_status' else 0)
                for sword, core in zip(swords, cores):
                    self.assertEqual(ramps(core,tx.MODEL_OFFSET),ramps(sword,tx.MODEL_OFFSET))
                    self.assertEqual(ramps(core,tx.MODEL_ALPHA),ramps(sword,tx.MODEL_ALPHA))
                shells = [model for model in components(root, 'Model')
                          if not is_sword(model) and ENERGY_RING not in scalar(model, tx.fx.MESH)
                          and BLUE_CORE not in scalar(model, tx.fx.MESH)]
                self.assertEqual(len(shells), 0 if profile['shell_alpha'] == 0 else 1)
                rings = [model for model in components(root, 'Model')
                         if ENERGY_RING in scalar(model, tx.fx.MESH)]
                self.assertEqual(len(rings), 1 if key == 'taixuan_taiqing_status' else 0)
                self.assertEqual(len(components(root, 'Model')), len(swords) + len(cores) + len(shells) + len(rings))
                self.assertEqual(len(components(root, 'ParticleSystem')), profile['wisps']+(1 if key=='taixuan_taiqing_status' else 0))
                self.assertFalse(details['common_guard_swords_duplicated'])
                self.assertFalse(details['terrain_adaptation'])


    def test_actual_hits_preserve_hit_glints_and_delegate_swords_to_world_rain(self):
        for key, profile in tx.PROFILES.items():
            if profile['phase'] != 'impact':
                continue
            root, _, details = self.authored[key]
            models = components(root, 'Model')
            with self.subTest(key=key):
                self.assertEqual(len(models), 2 if key == 'taixuan_liuguang_hit' else 0)
                if key == 'taixuan_liuguang_hit':
                    self.assertEqual(len([m for m in models if tx.LONGSWORD in scalar(m,tx.fx.MESH)]),1)
                    self.assertEqual(len([m for m in models if BLUE_CORE in scalar(m,tx.fx.MESH)]),1)
                    self.assertTrue(details['local_short_thrust'])
                    self.assertFalse(details['full_distance_beam'])
                if key not in NATIVE_HIT_KEYS:
                    continue
                self.assertEqual(details['world_rain_owner'], 'TaixuanRainVfx.lua')
                self.assertTrue(details['native_damage_timing_unchanged'])
                self.assertEqual(components(root, 'BoundingSphere')[0].get('end'), '1')
                self.assertFalse(root.findall('./phases/object/data'))
                self.assertEqual(details['central_peak_count'], 1)
                self.assertEqual(len(components(root, 'ParticleSystem')), 1 + len(profile['angles']))

    def test_taiqing_has_one_open_native_ring_with_original_status_lifecycle(self):
        root, _, _ = self.authored['taixuan_taiqing_status']
        rings = [m for m in components(root, 'Model') if ENERGY_RING in scalar(m, tx.fx.MESH)]
        ring, = rings
        self.assertEqual((float(ring.get('start')), float(ring.get('end'))), (0, 4.2))
        self.assertEqual(scalar(ring, tx.fx.POSITION), '0,0.45,0')
        self.assertEqual([[v for _, v in c] for c in ramps(ring, tx.fx.MODEL_SCALE)],
                         [[6, 6], [.12, .12], [6, 6]])
        self.assertEqual([[v for _, v in c] for c in ramps(ring, tx.MODEL_ROTATION)],
                         [[0, 0], [0, 0], [0, 0]])
        self.assertTrue(all(value == 0 for channel in ramps(ring, tx.MODEL_OFFSET) for _, value in channel))
        alpha = ramps(ring, tx.MODEL_ALPHA)[0]
        self.assertEqual(len(alpha), 4)
        for (time, value), (seconds, expected) in zip(alpha, [(0, 0), (.2, .75), (3.8, .75), (4.2, 0)]):
            self.assertAlmostEqual(time * 4.2, seconds, places=7)
            self.assertEqual(value, expected)
        bound, = components(root, 'BoundingSphere')
        self.assertEqual(float(bound.get('end')), 4.2)
        self.assertEqual(float(scalar(bound, tx.fx.BOUND_RADIUS)), 9)
        self.assertTrue(any(p.get('playcount') == '-1' for p in root.findall('./phases/object/data')))

    def test_reauthoring_is_deterministic_and_reads_native_sources_without_modifying_them(self):
        from xml.etree import ElementTree as ET
        origins = {path for _, paths, _ in self.authored.values() for path in paths}
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in origins}
        for key, (root, _, _) in self.authored.items():
            again, _, _ = tx.author(DATA, key, self.dictionary)
            self.assertEqual(ET.tostring(root), ET.tostring(again))
        self.assertEqual(before, {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in origins})


if __name__ == '__main__':
    unittest.main()
