"""Tianfeng's visible sword must follow the Rush caster, never a damage target."""
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tianfeng_visual_polish as tf
import school_visual_polish as bindings
import sword_glow


def ramps(component, key):
    return [[(float(k.get('time')), float(k.get('value')))
             for k in ch.findall('./keyframes/keyframe')]
            for ch in component.findall(f'./properties/property[@id="{key}"]/data/datum/rampchanneldata/rampchannel')]


class TianfengCastBinding(unittest.TestCase):
    def test_native_cast_binding_follows_caster_rotation_and_position(self):
        editor, _ = bindings._mei(tf.KEY, tf.PROFILES[tf.KEY])
        item, = editor.findall('EffectInfo')
        self.assertEqual(item.get('TargetBone'), 'Dummy_Root')
        self.assertEqual(item.get('Pivot'), 'Target')
        for field in ('DetachTarget', 'DetachSource', 'KeepRotation', 'UseDistance'):
            self.assertEqual(item.get(field), 'false')
        self.assertEqual(item.get('StartTextKey'), 'Cast')

    def test_runtime_loop_owns_rush_sword_and_keeps_native_contact_and_mechanics(self):
        record = {**tf.PROFILES[tf.KEY], 'mei': 'owned-cast', 'offhandMei': 'owned-off'}
        hit = dict(skill='tianqing_tianfeng', binding='hit', mei='owned-hit')
        fields = dict(SpellType='Rush', SpellRoll='Attack(AttackType.RangedSpellAttack)',
                      SpellSuccess='DealDamage(22d8,Force)', CastTextEvent='Cast')
        result = bindings.spell_bindings('Rush_ESC_tianqing_tianfeng', fields,
                                        {tf.KEY: record, 'hit': hit})
        self.assertEqual(result['CastEffect'], '')
        self.assertEqual(result['HitEffect'], 'owned-hit')
        self.assertFalse(set(result) & {'SpellSuccess', 'SpellRoll', 'MovementSpeed', 'TargetRadius', 'UseCosts'})
        self.assertEqual(bindings.spell_bindings('Rush_ESC_xueyan_chuanshen', fields,
                                                {tf.KEY: record, 'hit': hit}), {})
        # A pre-loop compiled record must still use its finite native MEI.
        del record['lifecycle']
        self.assertEqual(bindings.spell_bindings('Rush_ESC_tianqing_tianfeng', fields,
                         {tf.KEY: record, 'hit': hit})['CastEffect'], 'owned-cast')
        self.assertFalse(bindings.attached_until_casted(dict(record, skill='taixuan_zhaoxi',
                         lifecycle='attached-until-casted')))


@unittest.skipUnless((tf.fx.DATA / 'Editor/Config/AllSpark/ComponentDefinition.xcd').is_file(),
                     'Installed native AllSpark components are required')
class TianfengSwordAuthoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dictionary = tf.fx.PropertyDictionary(tf.fx.DATA)
        cls.root, cls.origins, cls.details = tf.author(tf.fx.DATA, tf.KEY, cls.dictionary)
        cls.glow = sword_glow.apply(cls.root, cls.dictionary, 'tianqing')

    def test_one_recognizable_native_luminous_sword_and_two_dim_side_streams(self):
        components = self.root.findall('.//component')
        self.assertEqual({c.get('class') for c in components}, {'Model', 'BoundingSphere'})
        models = [c for c in components if c.get('class') == 'Model']
        self.assertEqual(len(models), 3)
        meshes = [c.find(f'./properties/property[@id="{tf.fx.MESH}"]/data/datum').get('value') for c in models]
        self.assertEqual(sum(sword_glow.visual_id('tianqing') in mesh for mesh in meshes), 1)
        self.assertEqual(sum(tf.RUSH_MESH in mesh for mesh in meshes), 2)
        self.assertEqual(self.glow['luminous_swords'], 1)
        self.assertGreater(self.details['sword_length'], 4.5)
        self.assertLess(self.details['sword_length'], 5.)
        for c, mesh in zip(models, meshes):
            if tf.RUSH_MESH in mesh:
                self.assertLessEqual(max(v for ch in ramps(c, tf.fall.ALPHA) for _, v in ch), .18)

    def test_sword_points_forward_without_world_motion_or_falling_path(self):
        sword = next(c for c in self.root.findall('.//component[@class="Model"]')
                     if sword_glow.visual_id('tianqing') in c.find(f'./properties/property[@id="{tf.fx.MESH}"]/data/datum').get('value'))
        angles = tuple(ch[0][1] for ch in ramps(sword, tf.fall.INITIAL_ROTATION))
        rotation = sword_glow._rotation(angles)
        # The real luminous GR2 tip is +Y. After mapping it must face -Z.
        tip_direction = tuple(rotation[i][1] for i in range(3))
        self.assertAlmostEqual(tip_direction[0], 0)
        self.assertAlmostEqual(tip_direction[1], 0)
        self.assertAlmostEqual(tip_direction[2], -1)
        for model in self.root.findall('.//component[@class="Model"]'):
            for key in (tf.fall.KEYFRAMED_OFFSET, tf.fall.ROTATION_RPM, tf.fall.ROTATION_LIFE):
                self.assertTrue(all(v == 0 for ch in ramps(model, key) for _, v in ch))

    def test_loop_holds_pose_and_brightness_until_short_transparent_exit(self):
        phases = self.root.findall('./phases/object/data')
        self.assertEqual([p.get('playcount') for p in phases], ['1', '-1', '1'])
        self.assertEqual([float(p.get('duration')) for p in phases],
                         [tf.LEAD_IN, tf.LOOP, tf.LEAD_OUT])
        loop_start = tf.LEAD_IN / tf.DURATION
        loop_end = (tf.LEAD_IN + tf.LOOP) / tf.DURATION
        for c in self.root.findall('.//component[@class="Model"]'):
            self.assertEqual(float(c.get('start')), 0)
            self.assertEqual(float(c.get('end')), tf.DURATION)
            ch, = ramps(c, tf.fall.ALPHA)
            self.assertEqual(ch[0][1], 0)
            self.assertEqual(ch[-1][1], 0)
            self.assertGreater(max(v for _, v in ch), 0)
            # The entire repeated interval lies between equal-valued keys.
            left = max((key for key in ch if key[0] <= loop_start), key=lambda key: key[0])
            right = min((key for key in ch if key[0] >= loop_end), key=lambda key: key[0])
            self.assertEqual(left[1], right[1])
            self.assertFalse(any(left[0] < t < right[0] for t, _ in ch))
        bound, = self.root.findall('.//component[@class="BoundingSphere"]')
        self.assertEqual(float(bound.get('end')), tf.DURATION)
        self.assertAlmostEqual(tf.DURATION - self.details['fade_start'], .3)

    def test_authoring_is_deterministic_and_native_inputs_unchanged(self):
        before = {p: tf.fx.digest(p) for p in self.origins}
        dictionary = tf.fx.PropertyDictionary(tf.fx.DATA)
        other, _, _ = tf.author(tf.fx.DATA, tf.KEY, dictionary)
        sword_glow.apply(other, dictionary, 'tianqing')
        self.assertEqual(ET.tostring(self.root), ET.tostring(other))
        self.assertEqual(before, {p: tf.fx.digest(p) for p in self.origins})


if __name__ == '__main__':
    unittest.main()
