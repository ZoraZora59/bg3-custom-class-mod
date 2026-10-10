"""Guard local Tianqing accents against extra swords and repeated hit pulses."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import tianqing_visual_polish as polish


def ramps(component, key):
    return [[(float(k.get('time')), float(k.get('value')))
             for k in ch.findall('./keyframes/keyframe')]
            for ch in component.findall(f'./properties/property[@id="{key}"]/data/datum/rampchanneldata/rampchannel')]


class TianqingProfileContract(unittest.TestCase):
    def test_current_attacks_and_recovery_have_separate_profiles(self):
        attacks = {'nifeng', 'wanjun', 'lietian', 'tianbeng', 'tianfeng', 'tianjian', 'bafang', 'tiandi'}
        self.assertEqual(set(polish.PROFILES), {f'tianqing_{key}_hit' for key in attacks} | {'tianqing_nixi_cast'})
        for key, p in polish.PROFILES.items():
            self.assertTrue(p['label'])
            self.assertTrue(p['presentation'])
            self.assertEqual(p['skill'], key.rsplit('_', 1)[0])
            self.assertEqual((p['phase'], p['binding']), ('cast', 'cast') if key.endswith('_cast') else ('impact', 'hit'))
            self.assertFalse(any('damage' in name.lower() for name in p))


@unittest.skipUnless((polish.fx.DATA / 'Editor/Config/AllSpark/ComponentDefinition.xcd').is_file(),
                     'Installed editable native VFX dictionary is required')
class TianqingNativeAuthoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dictionary = polish.fx.PropertyDictionary(polish.fx.DATA)
        cls.authored = {key: polish.author(polish.fx.DATA, key, cls.dictionary) for key in polish.PROFILES}

    def test_particle_banks_never_copy_giant_swords_or_global_screen_effects(self):
        all_instances = []
        for key, (root, origins, details) in self.authored.items():
            with self.subTest(key=key):
                components = root.findall('./trackgroups/trackgroup/track/component')
                self.assertEqual({c.get('class') for c in components}, {'BoundingSphere', 'ParticleSystem'})
                self.assertEqual(len([c for c in components if c.get('class') == 'ParticleSystem']), details['particle_count'])
                self.assertFalse(root.findall('./phases/object'))
                self.assertEqual(details['giant_sword_count'], 0)
                self.assertEqual(details['bank_repetitions'], 1)
                self.assertTrue(all(p.is_file() for p in origins))
                for c in components:
                    all_instances.append(c.get('instancename'))
        self.assertEqual(len(all_instances), len(set(all_instances)))

    def test_each_actual_hit_has_one_synchronized_opacity_peak_and_bounded_tail(self):
        for key, (root, _, details) in self.authored.items():
            particles = [c for c in root.findall('./trackgroups/trackgroup/track/component') if c.get('class') == 'ParticleSystem']
            for c in particles:
                with self.subTest(key=key, instance=c.get('instancename')):
                    self.assertEqual(c.get('start'), '0')
                    self.assertAlmostEqual(float(c.get('end')), .05)
                    count = c.find(f'./properties/property[@id="{polish.fx.INITIAL_COUNT}"]/data/datum')
                    self.assertEqual(count.get('value'), '1,1')
                    self.assertTrue(all(v == 0 for ch in ramps(c, polish.fx.EMIT_RATE) for _, v in ch))
                    life = ramps(c, polish.fx.LIFESPAN)[0][0][1]
                    self.assertLessEqual(life, .65)
                    for ramp_key in (polish.PARTICLE_ALPHA, polish.PARTICLE_BRIGHTNESS):
                        ch, = ramps(c, ramp_key)
                        self.assertEqual(ch[-1][1], 0)
                        peak = max(v for _, v in ch)
                        self.assertEqual(sum(v == peak for _, v in ch), 1)
                        peak_time = next(t for t, v in ch if v == peak) * life
                        self.assertAlmostEqual(peak_time, details['opacity_peak_seconds'], places=7)
                        self.assertTrue(all(v <= peak for _, v in ch))

    def test_hit_size_is_local_and_recovery_moves_up_while_contour_shrinks(self):
        for key, (root, _, details) in self.authored.items():
            with self.subTest(key=key):
                bound = next(c for c in root.findall('./trackgroups/trackgroup/track/component') if c.get('class') == 'BoundingSphere')
                datum = bound.find(f'./properties/property[@id="{polish.fx.BOUND_RADIUS}"]/data/datum')
                self.assertLessEqual(float(datum.get('value')), 5)
                self.assertEqual(details['invocation_scope'], 'one cast' if key.endswith('_cast') else 'one actual hit')
        root, _, _ = self.authored['tianqing_nixi_cast']
        rise, ring = [c for c in root.findall('./trackgroups/trackgroup/track/component') if c.get('class') == 'ParticleSystem']
        y = ramps(rise, polish.KEYFRAMED_OFFSET)[1]
        self.assertGreater(y[-1][1], y[0][1])
        for ch in ramps(ring, polish.fx.PARTICLE_SCALE):
            self.assertTrue(all(a >= b for (_, a), (_, b) in zip(ch, ch[1:])))

    def test_native_identity_drift_fails_before_authoring(self):
        original_parse = ET.parse
        def changed_parse(path, *args, **kwargs):
            tree = original_parse(path, *args, **kwargs)
            if Path(path) == polish.fx.DATA / polish.SLASH:
                c = tree.getroot().findall('./trackgroups/trackgroup')[1].findall('track')[0].find('component')
                c.set('instancename', 'unexpected-native-component')
            return tree
        with patch.object(polish.ET, 'parse', side_effect=changed_parse):
            with self.assertRaisesRegex(ValueError, 'Native template identity changed'):
                polish.author(polish.fx.DATA, 'tianqing_nifeng_hit', polish.fx.PropertyDictionary(polish.fx.DATA))

    def test_missing_dictionary_property_fails_instead_of_using_guessed_property(self):
        dictionary = polish.fx.PropertyDictionary(polish.fx.DATA)
        dictionary.properties.pop(('ParticleSystem', polish.PARTICLE_ALPHA))
        with self.assertRaisesRegex(ValueError, 'AllSpark XCD does not define'):
            polish.author(polish.fx.DATA, 'tianqing_wanjun_hit', dictionary)

    def test_authoring_is_deterministic_and_original_templates_are_unmodified(self):
        source_hashes = {path: polish.fx.digest(path) for _, origins, _ in self.authored.values() for path in origins}
        key = 'tianqing_tiandi_hit'
        first = copy.deepcopy(self.authored[key][0])
        second, _, _ = polish.author(polish.fx.DATA, key, polish.fx.PropertyDictionary(polish.fx.DATA))
        self.assertEqual(ET.tostring(first), ET.tostring(second))
        self.assertEqual(source_hashes, {path: polish.fx.digest(path) for path in source_hashes})


if __name__ == '__main__':
    unittest.main()
