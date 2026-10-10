"""Geometry and phase contracts for native-contact Tianqing visual banks.

These verify what AllSpark receives; rendered timing still requires the client.
"""
import json
import math
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts'))
from tianqing_vfx_design import TIANQING_TIMING_PROFILES, TIANQING_TIMING_PAIRS
from tianqing_vfx_resources import paths, PROFILES, RECEIPT, digest, BANK
from test_tianqing_vfx_design import (
    ramps, scalar, vector, swords, world_mesh_corners, OFFSET, RADIUS, CENTER,
)

SOURCE = REPO / 'mods/EasternSwordCultivator/Source'
ALPHA = '00910be4-aaa1-41a2-946f-735d33de387b'


def interpolate(channel, time):
    for (a, va), (b, vb) in zip(channel, channel[1:]):
        if a <= time <= b:
            return va if a == b else va + (vb-va) * (time-a) / (b-a)
    raise AssertionError(f'Time not covered: {time}')


class TianqingContactAssets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roots = {key: ET.parse(SOURCE / paths(key)[0]).getroot()
                     for key in TIANQING_TIMING_PROFILES}

    def test_only_four_native_timing_skills_are_split(self):
        self.assertEqual(set(TIANQING_TIMING_PAIRS), {
            'tianqing_wanjun', 'tianqing_lietian', 'tianqing_tianjian', 'tianqing_bafang'})
        self.assertEqual(len(self.roots), 8)
        for pair in TIANQING_TIMING_PAIRS.values():
            self.assertNotEqual(pair['prepare'], pair['impact'])
        self.assertEqual(PROFILES['tianqing_tiandi']['hit_time'], .8)

    def test_prepare_falls_once_and_holds_above_ground_through_loop(self):
        for key, profile in TIANQING_TIMING_PROFILES.items():
            if profile['timing_phase'] != 'prepare':
                continue
            with self.subTest(key=key):
                root = self.roots[key]
                phases = root.findall('./phases/object/data')
                self.assertEqual([p.get('playcount') for p in phases], ['1', '-1', '1'])
                self.assertEqual([p.get('definitionid') for p in phases], [
                    'fc34bad5-e4a8-4855-bdd1-ece88d327719',
                    '2d6a16c1-4632-4f7f-8097-4717dc65d7bd',
                    'fc8e9f77-827a-433f-a58d-ad1007605399'])
                self.assertFalse(root.findall('./trackgroups/trackgroup/track/component[@class="ParticleSystem"]'))
                duration = sum(float(p.get('duration')) for p in phases)
                start = float(phases[0].get('duration')) / duration
                end = (float(phases[0].get('duration')) + float(phases[1].get('duration'))) / duration
                self.assertEqual(len(swords(root)), 1)
                for model in root.findall('./trackgroups/trackgroup/track/component[@class="Model"]'):
                    ys = ramps(model, OFFSET)[1]
                    self.assertAlmostEqual(ys[0][1], profile['drop_height'])
                    self.assertTrue(all(a[1] >= b[1] for a,b in zip(ys, ys[1:])))
                    for time in (start, (start + end) / 2, end):
                        self.assertAlmostEqual(interpolate(ys, time), .6, places=6)
                        self.assertAlmostEqual(interpolate(ramps(model, ALPHA)[0], time), 1, places=6)
                    self.assertEqual(ramps(model, ALPHA)[0][-1], (1, 0))
                sword = swords(root)[0]
                self.assertAlmostEqual(min(p[1] for p in world_mesh_corners(sword, (0,.6,0))), .6, places=4)

    def test_contact_has_no_descent_and_emits_once_at_zero(self):
        for key, profile in TIANQING_TIMING_PROFILES.items():
            if profile['timing_phase'] != 'impact':
                continue
            with self.subTest(key=key):
                root = self.roots[key]
                self.assertEqual(root.findall('./phases/object'), [])
                self.assertEqual(len(swords(root)), 1)
                for model in root.findall('./trackgroups/trackgroup/track/component[@class="Model"]'):
                    for channel in ramps(model, OFFSET):
                        self.assertTrue(all(value == 0 for _, value in channel))
                    self.assertEqual(ramps(model, ALPHA)[0][0], (0, 1))
                    self.assertEqual(ramps(model, ALPHA)[0][-1], (1, 0))
                self.assertAlmostEqual(min(p[1] for p in world_mesh_corners(swords(root)[0], (0,0,0))), 0, places=4)
                bursts = root.findall('./trackgroups/trackgroup/track/component[@class="ParticleSystem"]')
                self.assertEqual(len(bursts), 1)
                self.assertEqual((float(bursts[0].get('start')), float(bursts[0].get('end'))), (0, .1))
                self.assertEqual(vector(bursts[0], '20d22bbd-2e85-41e1-bc13-00b2a72cdf9b'), (1,1))
                self.assertEqual(ramps(bursts[0], 'd1892ce7-07f3-4d9c-9acb-6692b897a71b')[0][0], (0,1))

    def test_bounds_cover_models_and_complete_authored_lifecycle(self):
        for key, root in self.roots.items():
            with self.subTest(key=key):
                bound = root.find('./trackgroups/trackgroup/track/component[@class="BoundingSphere"]')
                duration = TIANQING_TIMING_PROFILES[key]['duration']
                self.assertAlmostEqual(float(bound.get('start')), 0)
                self.assertAlmostEqual(float(bound.get('end')), duration)
                center, radius = vector(bound, CENTER), float(scalar(bound, RADIUS))
                for sword in swords(root):
                    for _, y in ramps(sword, OFFSET)[1]:
                        for point in world_mesh_corners(sword, (0,y,0)):
                            self.assertLessEqual(math.dist(point, center), radius + 1e-5)

    def test_all_eight_compiled_hashes_and_loop_resource_flags_match(self):
        receipt = json.loads((SOURCE / RECEIPT).read_text(encoding='utf-8'))
        rows = {r['effect_name']: r for r in receipt['records']}
        bank = ET.parse(SOURCE / BANK)
        resources = {n.find('./attribute[@id="EffectName"]').get('value'): n
                     for n in bank.findall('.//node[@id="Resource"]')}
        for key, profile in TIANQING_TIMING_PROFILES.items():
            with self.subTest(key=key):
                row = rows[profile['effect_name']]
                editor, binary = paths(key)
                self.assertEqual(digest(SOURCE/editor), row['source_sha256'].lower())
                self.assertEqual(digest(SOURCE/binary), row['compiled_sha256'].lower())
                self.assertTrue(row['semantic_roundtrip_verified'])
                looping = resources[profile['effect_name']].find('./attribute[@id="Looping"]').get('value')
                self.assertEqual(looping, 'True' if profile['timing_phase'] == 'prepare' else 'False')


if __name__ == '__main__':
    unittest.main()
