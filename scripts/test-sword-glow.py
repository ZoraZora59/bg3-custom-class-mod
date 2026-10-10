"""Verify sword-tip direction, transform preservation and scoped VFX changes."""
import copy
import math
import unittest
import xml.etree.ElementTree as ET
import sword_glow as glow
import taixuan_visual_polish as tx


class SwordGlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dictionary=tx.fx.PropertyDictionary(tx.fx.DATA)

    def model(self,angles):
        root,_=tx.fx.projectile(tx.fx.DATA)
        c=next(c for c in root.findall('.//component[@class="Model"]'))
        for key,values in ((tx.MODEL_ROTATION,angles),(tx.fx.MODEL_SCALE,(1.7,.9,2.1))):
            tx.fx.replace_ramp(self.dictionary,c,key,tuple([(0,v),(1,v)]for v in values))
        return root,c

    def test_tip_direction_and_world_center(self):
        # Directions are independently specified for the actual cast/flight/
        # falling poses, including yaw and roll used by blood swords.
        cases=[((0,0,0),(0,0,-1)),((90,0,0),(0,1,0)),((-90,0,0),(0,-1,0)),
               ((0,90,0),(-1,0,0)),((0,-90,0),(1,0,0)),
               ((0,0,25),(0,0,-1))]
        for angles,expected in cases:
            with self.subTest(angles=angles):
                root,c=self.model(angles)
                old_position=tuple(map(float,c.find(f'./properties/property[@id="{tx.fx.POSITION}"]/data/datum').get('value').split(',')))
                old_center=tuple((a+b)*s/2 for a,b,s in zip(*tx.STEEL_SWORD_BOUNDS,(1.7,.9,2.1)))
                old_rotation=glow._rotation(angles)
                expected_center=tuple(old_position[i]+sum(old_rotation[i][k]*old_center[k]for k in range(3))for i in range(3))
                glow.apply(root,self.dictionary,'xueyan')
                r=glow._rotation(tx._native_constant_values(c,tx.MODEL_ROTATION))
                for actual,wanted in zip((r[0][1],r[1][1],r[2][1]),expected):self.assertAlmostEqual(actual,wanted,places=7)
                scale=tx._native_constant_values(c,tx.fx.MODEL_SCALE)
                center=tuple((a+b)*s/2 for a,b,s in zip(tx.NATIVE_SWORD['minimum'],tx.NATIVE_SWORD['maximum'],scale))
                pos=tuple(map(float,c.find(f'./properties/property[@id="{tx.fx.POSITION}"]/data/datum').get('value').split(',')))
                for i in range(3):self.assertAlmostEqual(pos[i]+sum(r[i][k]*center[k]for k in range(3)),expected_center[i],places=7)
                self.assertAlmostEqual((tx.NATIVE_SWORD['maximum'][1]-tx.NATIVE_SWORD['minimum'][1])*scale[1],(tx.STEEL_SWORD_BOUNDS[1][2]-tx.STEEL_SWORD_BOUNDS[0][2])*2.1,places=7)

    def test_paths_lifetimes_and_other_components_are_preserved(self):
        root,c=self.model((0,-90,0))
        def other():
            return [ET.tostring(x)for x in root.findall('.//component')if x.get('class')!='Model']
        before=other();phases=ET.tostring(root.find('phases'));timing=(c.get('start'),c.get('end'))
        glow.apply(root,self.dictionary,'taixuan')
        self.assertEqual(other(),before)
        self.assertEqual(ET.tostring(root.find('phases')),phases)
        self.assertEqual((c.get('start'),c.get('end')),timing)
        self.assertIn(glow.visual_id('taixuan'),c.find(f'./properties/property[@id="{tx.fx.MESH}"]/data/datum').get('value'))

    def test_owned_resources_are_distinct_and_cover_all_palettes(self):
        ids={glow.visual_id(s,shape)for s in glow.PALETTES for shape in ('sword','circle')}
        self.assertEqual(len(ids),10)
        self.assertEqual(ids,set(glow.dependencies()))
        self.assertNotIn(glow.SWORD,ids)
        self.assertNotIn(glow.CIRCLE,ids)


if __name__=='__main__':unittest.main(verbosity=2)
