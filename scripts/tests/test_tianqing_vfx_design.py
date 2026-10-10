"""Check authored falling-sword geometry, not compiled/gameplay behavior."""
import itertools
import json
import math
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
REPO = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
from sword_cultivator_spec import FOLDER
from tianqing_vfx_design import TIANQING_PROFILES, TIANQING_AUXILIARY_PROFILES, TIANQING_BINDING_PLAN, PRESERVED_ENTRIES
from sword_glow import visual_id

ASSET_PROFILES = {**TIANQING_PROFILES, **TIANQING_AUXILIARY_PROFILES}

SOURCE = REPO / 'mods/EasternSwordCultivator/Source'
MESH = '15864e49-e811-41aa-9f27-f2ca410a13cf'
POSITION = '47a42cb9-3508-427e-8a09-8d8cc74771b7'
OFFSET = '37b047c1-8fb7-4e7c-9319-58db9da44e77'
ROTATION = '4a72a815-57fb-4fcb-9a50-1024331ce66a'
SCALE = '2bea542b-790f-4ef8-877b-5a97335adb1f'
RADIUS = 'ba2ee0f9-d369-4d36-bd63-30d4c8c46a0a'
CENTER = 'c1115291-39d1-43a2-8259-31c2ef4dbd93'
GREAT_SWORD = '12f3193c-ce1a-5a69-1bf0-8537b9b606f9'
# Original resource bounds, not a claim about rendered vertices.
NATIVE_MIN = (-.16201761, -.032432493, -1.57971)
NATIVE_MAX = (.16201802, .05192164, .35004446)

SPIRITUAL_SWORD = '3727a57a-e4be-44da-02b4-5061028fed5f'
# Shared.pak / SharedDev Spiritual Weapons/GreatSword/[PAK]_Body Visual.
# Both visuals' resource AABBs are verified native data; they are not vertex
# readback or visible-output acceptance.
SWORD_GEOMETRY = {
    GREAT_SWORD: (NATIVE_MIN, NATIVE_MAX, (0, 0, -1), (-90, 0, 0)),
    SPIRITUAL_SWORD: ((-.1707061, -.00018119812, -.042987518),
                     (.17070608, 1.9629779, .043253355), (0, 1, 0), (180, 0, 0)),
}
SWORD_GEOMETRY[visual_id('tianqing')] = (
    *SWORD_GEOMETRY[SPIRITUAL_SWORD][:3], (-180, 0, 0))
FALL_KEYS = {'tianqing_wanjun', 'tianqing_lietian', 'tianqing_tianjian',
             'tianqing_bafang', 'tianqing_tiandi'}


def scalar(component, key):
    datum = component.find(f'./properties/property[@id="{key}"]/data/datum')
    if datum is None:
        raise AssertionError(f'Missing source property {key}')
    return datum.get('value')


def vector(component, key):
    return tuple(float(v) for v in scalar(component, key).split(','))


def ramps(component, key):
    prop = component.find(f'./properties/property[@id="{key}"]')
    if prop is None:
        raise AssertionError(f'Missing source ramp {key}')
    return [[(float(k.get('time')), float(k.get('value')))
             for k in c.findall('./keyframes/keyframe')]
            for c in prop.findall('./data/datum/rampchanneldata/rampchannel')]


def swords(root):
    result = []
    for track in root.findall('./trackgroups/trackgroup/track'):
        c = track.find('component')
        if (c is not None and c.get('class') == 'Model'
                and track.get('muted') != 'True'
                and track.get('mutestateoverride') != 'Muted'
                and any(uid in (scalar(c, MESH) or '') for uid in SWORD_GEOMETRY)):
            result.append(c)
    return result



def sword_geometry(component):
    mesh = scalar(component, MESH) or ''
    ids = [uid for uid in SWORD_GEOMETRY if uid in mesh]
    if len(ids) != 1:
        raise AssertionError(f'Expected one verified sword Visual: {mesh}')
    return SWORD_GEOMETRY[ids[0]]


def rotate_euler(point, degrees):
    """Right-handed X, then Y, then Z rotation; authored swords use only X."""
    x, y, z = point
    rx, ry, rz = map(math.radians, degrees)
    y, z = y*math.cos(rx)-z*math.sin(rx), y*math.sin(rx)+z*math.cos(rx)
    x, z = x*math.cos(ry)+z*math.sin(ry), -x*math.sin(ry)+z*math.cos(ry)
    x, y = x*math.cos(rz)-y*math.sin(rz), x*math.sin(rz)+y*math.cos(rz)
    return x, y, z


def world_mesh_corners(component, offset):
    low, high, _, _ = sword_geometry(component)
    scale = tuple(ch[0][1] for ch in ramps(component, SCALE))
    rotation = tuple(ch[0][1] for ch in ramps(component, ROTATION))
    position = vector(component, POSITION)
    for corner in itertools.product(*zip(low, high)):
        rotated = rotate_euler(tuple(v*s for v, s in zip(corner, scale)), rotation)
        yield tuple(position[i]+offset[i]+rotated[i] for i in range(3))


class TianqingVfxSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roots = {}
        for key in FALL_KEYS | set(TIANQING_AUXILIARY_PROFILES):
            name = ASSET_PROFILES[key]['effect_name']
            path = SOURCE / 'Editor/Mods' / FOLDER / 'Assets/Effects/Sword/Tianqing' / (name + '.lsefx')
            cls.roots[key] = ET.parse(path).getroot()

    def test_only_selected_attacks_receive_falling_sword_sources(self):
        self.assertEqual({k for k, p in TIANQING_PROFILES.items() if p.get('effect_name')}, FALL_KEYS)
        for key, root in self.roots.items():
            with self.subTest(key=key):
                self.assertEqual(len(swords(root)), 8 if key == 'tianqing_bafang' else 1)

    def test_serialized_swords_drop_without_horizontal_travel(self):
        for key, root in self.roots.items():
            for sword in swords(root):
                with self.subTest(key=key, sword=sword.get('instancename')):
                    offsets = ramps(sword, OFFSET)
                    self.assertEqual(len(offsets), 3)
                    for axis in (0, 2):
                        values = [v for _, v in offsets[axis]]
                        self.assertGreaterEqual(len(values), 2)
                        self.assertAlmostEqual(max(values), min(values), places=6)
                    heights = [v for _, v in offsets[1]]
                    self.assertGreater(heights[0] - heights[-1], 5)
                    self.assertTrue(all(a >= b for a, b in zip(heights, heights[1:])))

    def test_position_module_is_active_and_ground_contact_matches_planned_impact(self):
        for key, root in self.roots.items():
            profile = ASSET_PROFILES[key]
            for sword in swords(root):
                with self.subTest(key=key):
                    modules = sword.findall('./modules/module')
                    self.assertTrue(any(m.get('id', '').lower() == '7a790ae7-3b1c-463e-bb1f-5cc14980b78c'
                                        and m.get('muted') == 'False' for m in modules))
                    y = ramps(sword, OFFSET)[1]
                    end_value = y[-1][1]
                    contact = next(t for t, value in y if abs(value - end_value) < 1e-6)
                    seconds = contact * (float(sword.get('end')) - float(sword.get('start'))) + float(sword.get('start'))
                    self.assertAlmostEqual(seconds, profile['hit_time'], places=5)
                    self.assertEqual(profile['impact_start'], profile['hit_time'])

    def test_blade_points_down_and_resource_tip_bounds_reach_ground(self):
        for key, root in self.roots.items():
            for sword in swords(root):
                with self.subTest(key=key):
                    rotation = ramps(sword, ROTATION)
                    self.assertEqual(len(rotation), 3)
                    _, _, native_blade_axis, expected_rotation = sword_geometry(sword)
                    for axis, expected in enumerate(expected_rotation):
                        self.assertTrue(rotation[axis])
                        for _, value in rotation[axis]:
                            self.assertAlmostEqual((value-expected+180)%360-180, 0)
                    actual_rotation = tuple(channel[0][1] for channel in rotation)
                    direction = rotate_euler(native_blade_axis, actual_rotation)
                    for value, expected in zip(direction, (0, -1, 0)):
                        self.assertAlmostEqual(value, expected, places=7)
                    for keyframe_property in ('e5ece95a-a162-4a49-b029-cbc701fb00e4',
                                              'c57b1310-2df9-4339-bdf8-a97475e121ff'):
                        for channel in ramps(sword, keyframe_property):
                            self.assertTrue(channel)
                            self.assertTrue(all(abs(value) < 1e-8 for _, value in channel))
                    for transform_property in ('e2f48d17-b4f1-468d-87c5-0c9cf67e169e',
                                               '98d90be4-888a-4fd4-8d36-6a202e67d55b'):
                        self.assertEqual(vector(sword, transform_property), (0, 0, 0))
                    final_offset = tuple(ch[-1][1] for ch in ramps(sword, OFFSET))
                    tip_y = min(point[1] for point in world_mesh_corners(sword, final_offset))
                    self.assertAlmostEqual(tip_y, 0, places=4)

    def test_eight_swords_have_eight_distinct_evenly_spaced_landing_points(self):
        points = [vector(s, POSITION) for s in swords(self.roots['tianqing_bafang'])]
        self.assertEqual(len({(round(x, 5), round(z, 5)) for x, _, z in points}), 8)
        # The mesh origin moves while the original blade center stays fixed.
        # Verify this offset from the two resources' independently known bounds.
        cx=sum(p[0]for p in points)/8;cz=sum(p[2]for p in points)/8
        s=swords(self.roots['tianqing_bafang'])[0]
        scales=[r[0][1]for r in ramps(s,SCALE)]
        low,high,_,_=sword_geometry(s)
        old_x=scales[0]*(high[0]-low[0])/(NATIVE_MAX[0]-NATIVE_MIN[0])
        old_y=scales[2]*(high[2]-low[2])/(NATIVE_MAX[1]-NATIVE_MIN[1])
        self.assertAlmostEqual(cx,(NATIVE_MIN[0]+NATIVE_MAX[0])/2*old_x-(low[0]+high[0])/2*scales[0],places=6)
        self.assertAlmostEqual(cz,-(NATIVE_MIN[1]+NATIVE_MAX[1])/2*old_y+(low[2]+high[2])/2*scales[2],places=6)
        radii = [math.hypot(x-cx, z-cz) for x, _, z in points]
        self.assertGreater(min(radii), 0)
        self.assertAlmostEqual(min(radii), max(radii), places=5)
        angles = sorted(math.atan2(z-cz, x-cx) % (2 * math.pi) for x, _, z in points)
        for a, b in zip(angles, angles[1:] + [angles[0] + 2 * math.pi]):
            self.assertAlmostEqual(b - a, math.pi / 4, places=5)

    def test_each_column_emits_one_collision_burst_at_ground_contact(self):
        for key, root in self.roots.items():
            bursts = [c for c in root.findall('./trackgroups/trackgroup/track/component')
                      if c.get('class') == 'ParticleSystem']
            self.assertEqual(len(bursts), len(swords(root)))
            for burst in bursts:
                with self.subTest(key=key):
                    self.assertAlmostEqual(float(burst.get('start')), ASSET_PROFILES[key]['hit_time'])
                    self.assertGreaterEqual(float(burst.get('end')) - float(burst.get('start')), .099999)
                    self.assertEqual(vector(burst, '20d22bbd-2e85-41e1-bc13-00b2a72cdf9b'), (1, 1))
                    for channel in ramps(burst, 'b16512bc-8157-4c11-bfde-732ec940b841'):
                        self.assertTrue(all(value == 0 for _, value in channel))
                    lifespan = ramps(burst, '352fac77-0097-47ec-908c-7c0d334fc161')
                    self.assertEqual(len(lifespan), 2)
                    for channel in lifespan:
                        self.assertTrue(channel)
                        self.assertTrue(all(abs(value - .6) < 1e-8 for _, value in channel))
                    alpha = ramps(burst, 'd1892ce7-07f3-4d9c-9acb-6692b897a71b')[0]
                    self.assertEqual(alpha[0], (0, 1))
                    self.assertLessEqual(max(value for _, value in alpha), 1)
                    scale = ramps(burst, '02e6012f-51af-4f4c-8897-2b8421952fa1')
                    self.assertTrue(all(channel[0][1] > 0 for channel in scale))

    def test_bounds_cover_all_serialized_sword_positions_and_mesh_corners(self):
        for key, root in self.roots.items():
            bound = next(c for c in root.findall('./trackgroups/trackgroup/track/component')
                         if c.get('class') == 'BoundingSphere')
            center, radius = vector(bound, CENTER), float(scalar(bound, RADIUS))
            for sword in swords(root):
                pos, offsets, scales = vector(sword, POSITION), ramps(sword, OFFSET), ramps(sword, SCALE)
                scale = [r[0][1] for r in scales]
                for axis in scales:
                    self.assertAlmostEqual(min(v for _, v in axis), max(v for _, v in axis))
                for y in (offsets[1][0][1], offsets[1][-1][1]):
                    offset = (offsets[0][0][1], y, offsets[2][0][1])
                    for world in world_mesh_corners(sword, offset):
                        with self.subTest(key=key, point=world):
                            self.assertLessEqual(math.dist(world, center), radius + 1e-5)

    def test_authoring_never_claims_compilation_and_runtime_assets_have_receipts(self):
        names = []
        for key in FALL_KEYS:
            p = TIANQING_PROFILES[key]
            self.assertFalse(p['compiled'])
            self.assertFalse(p['binding_enabled'])
            names.append(p['effect_name'])
        public = SOURCE / 'Public' / FOLDER
        for path in (public / 'Stats/Generated/Data').glob('Spell_*.txt'):
            text = path.read_text(encoding='utf-8')
            for name in names:
                self.assertNotIn(name, text)
        binaries = [p for name in names for p in public.rglob(name + '.lsfx')]
        if binaries:
            from tianqing_vfx_resources import RECEIPT, generate_resources
            self.assertTrue((SOURCE / RECEIPT).is_file())
            # Inspect receipt hashes without regenerating resources in tests.
            from tianqing_vfx_resources import digest, paths, PROFILES
            receipt = json.loads((SOURCE / RECEIPT).read_text(encoding='utf-8'))
            rows = {r['effect_name']: r for r in receipt['records']}
            for key, profile in PROFILES.items():
                if profile['effect_name'] in rows:
                    editor, binary = paths(key)
                    self.assertEqual(digest(SOURCE / editor), rows[profile['effect_name']]['source_sha256'].lower())
                    self.assertEqual(digest(SOURCE / binary), rows[profile['effect_name']]['compiled_sha256'].lower())

    def test_unified_binding_plan_names_canonical_roots_and_landing_only(self):
        planned = {p['profile']: p['stats_names'] for p in TIANQING_BINDING_PLAN
                   if not p['helper_binding_forbidden']}
        self.assertEqual(planned, {
            'tianqing_wanjun': ['Target_ESC_tianqing_wanjun'],
            'tianqing_lietian': ['Target_ESC_tianqing_lietian'],
            'tianqing_tianjian': ['Projectile_ESC_TianjianImpact', 'Projectile_ESC_TianjianImpact_Off'],
            'tianqing_bafang': ['Shout_ESC_tianqing_bafang'],
            'tianqing_tiandi': ['Target_ESC_tianqing_tiandi'],
        })
        aliases = json.loads((SOURCE / 'Mods' / FOLDER / 'ScriptExtender/Lua/GeneratedSpec.json').read_text(encoding='utf-8'))['aliases']
        for key, entries in planned.items():
            for name in entries:
                self.assertEqual(aliases[name]['key'], key)
                self.assertFalse(aliases[name].get('legacyMenu', False))
        forbidden = next(p for p in TIANQING_BINDING_PLAN
                         if p['profile'] == 'tianqing_tiandi' and p['helper_binding_forbidden'])
        self.assertEqual(set(forbidden['stats_names']), {
            'Target_ESC_TiandiStage','Target_ESC_TiandiStage_Off',
            'Target_ESC_TiandiStage_NoControl','Target_ESC_TiandiStage_NoControl_Off'})
        rows = {}
        for file in (SOURCE / 'Public' / FOLDER / 'Stats/Generated/Data').glob('Spell_*.txt'):
            for name, body in re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)', file.read_text(encoding='utf-8'), re.S):
                rows[name] = dict(re.findall(r'^data "([^"]+)" "([^"]*)"$', body, re.M))
        giant_meis = {p['planned_mei_guid'] for p in TIANQING_BINDING_PLAN if p['planned_mei_guid']}
        for name in forbidden['stats_names'] + ['Target_ESC_Aftershock']:
            for field in ('CastEffect','PositionEffect','TargetEffect','HitEffect','TargetHitEffect'):
                self.assertNotIn(rows[name].get(field, ''), giant_meis, (name, field))

    def test_binding_plan_uses_existing_execution_entries_and_rejects_victim_helpers(self):
        names = set()
        for path in (SOURCE / 'Public' / FOLDER / 'Stats/Generated/Data').glob('Spell_*.txt'):
            names.update(re.findall(r'^new entry "([^"]+)"', path.read_text(encoding='utf-8'), re.M))
        for plan in TIANQING_BINDING_PLAN:
            self.assertTrue(plan['blocked_activation'])
            self.assertFalse(plan['binding_enabled'])
            self.assertNotEqual(plan['proposed_field'], 'HitEffect')
            for name in plan['stats_names']:
                self.assertIn(name, names)
            if plan['helper_binding_forbidden']:
                self.assertIsNone(plan['proposed_field'])
                self.assertEqual(plan['expected_bank_invocations_per_cast'], 0)
        for skill, entries in PRESERVED_ENTRIES.items():
            for name in entries:
                with self.subTest(key=skill, name=name):
                    self.assertIn(name, names)
        stages = [p for p in TIANQING_BINDING_PLAN if p['profile'] == 'tianqing_tiandi']
        self.assertTrue(stages)
        for p in stages:
            self.assertTrue(p['requires_runtime_stage_coordinator'])
            self.assertEqual(p['swords_per_bank'], 1)
        self.assertTrue(any(p['helper_binding_forbidden'] for p in stages))


if __name__ == '__main__':
    unittest.main()
