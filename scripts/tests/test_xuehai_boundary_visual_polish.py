"""Guard the bloodsea material against the invisible character-overlay path."""
from pathlib import Path
import copy
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import xuehai_boundary_visual_polish as boundary


def attrs(node):
    return {a.get('id'): a.get('value') for a in node.findall('attribute')}


def resource(kind):
    return boundary.documents()[kind].find('.//node[@id="Resource"]')


class BloodseaWorldBoundary(unittest.TestCase):
    def test_material_is_a_world_model_and_keeps_the_native_vertex_rgba_input(self):
        material = resource('Material')
        self.assertEqual(attrs(material)['SourceFile'], boundary.SHADER)
        self.assertIn('/Model/', boundary.SHADER)
        self.assertIn('TwoSided', boundary.SHADER)
        self.assertNotIn('OverlayMaterial', boundary.SHADER)
        params = {attrs(n).get('ParameterName'): attrs(n) for n in material.findall('./children/node')}
        self.assertEqual(params['_MeshVertexColor']['Enabled'], 'False')
        self.assertEqual(params['DynamicParameter']['Enabled'], 'False')
        self.assertFalse(any('SphereMask' in name or 'BonePosition' in name for name in params if name))

    def test_opacity_uses_uniform_texture_without_view_or_distortion_masking(self):
        material = resource('Material')
        params = {attrs(n).get('ParameterName'): attrs(n) for n in material.findall('./children/node')}
        for key in ('_Use_FresnelOpacity',
                    'Use_MaskTexture', 'UseNearCameraFade', 'Distortion_Mult',
                    'Use_ColorRamp', '_Use_DynXForMaskPowerMult'):
            with self.subTest(key=key):
                self.assertEqual(params[key]['Enabled'], 'True')
                self.assertEqual(float(params[key]['Value']), 0)
        self.assertEqual(float(params['Opacity_Mult']['Value']), 1)
        self.assertEqual(params['MainTexture_Map']['ID'], boundary.WHITE_TEXTURE)
        for key in ('MainTexture_PanningSpeed', 'MaskTexture_PanningSpeed', 'Distortion_PanningSpeed'):
            self.assertEqual(list(map(float, params[key]['Value'].split())), [0, 0])

    def test_post_color_ramp_power_and_intensity_cannot_inherit_hdr_donor_values(self):
        params = {attrs(n).get('ParameterName'): attrs(n)
                  for n in resource('Material').findall('./children/node')}
        # Native graph applies these even when Use_ColorRamp is zero.
        for key in ('Colour_Ramp_Pow', 'Colour_Ramp_Intensity'):
            self.assertEqual(params[key]['Enabled'], 'True')
            self.assertEqual(float(params[key]['Value']), 1)
        import xueyan_visual_polish as blood
        vertex_red = blood.PROFILES['xueyan_xuehai_status']['boundary_brightness']
        emissive = vertex_red ** float(params['Colour_Ramp_Pow']['Value'])
        emissive *= float(params['Colour_Ramp_Intensity']['Value'])
        self.assertGreater(emissive, .5)
        self.assertLessEqual(emissive, 1)

    def test_native_uv_gradient_keeps_six_metre_edge_and_softens_a_narrow_rim(self):
        params = {attrs(n).get('ParameterName'): attrs(n)
                  for n in resource('Material').findall('./children/node')}
        self.assertEqual(float(params['_Use_ProceduralGradientForMask']['Value']), 1)
        top = tuple(map(float, params['ProceduralMask_Top_SmoothStep']['Value'].split()))
        bottom = tuple(map(float, params['ProceduralMask_Bottom_SmoothStep']['Value'].split()))
        def step(pair, v):
            t = min(1, max(0, (v-pair[0])/(pair[1]-pair[0])))
            return t*t*(3-2*t)
        def opacity(v): return step(top, v)*step(bottom, 1-v)
        self.assertEqual(opacity(.5), 1)
        self.assertEqual(opacity(0), 0)
        self.assertEqual(opacity(1), 0)
        self.assertGreater(opacity(.4), 0)
        self.assertLess(opacity(.4), 1)
        self.assertEqual(top, bottom)
        # Native GR2 outer radius is at V=.5, inner at V=0 and V=1.
        # Do not change scale/range to hide a thick rim.
        visible_width = (1-.90218)*6*(1-2*top[0])
        self.assertGreater(visible_width, .1)
        self.assertLess(visible_width, .2)

    def test_visual_retains_the_native_open_annulus_without_changing_its_geometry(self):
        original = copy.deepcopy(ET.parse(boundary.VISUAL_TEMPLATE).find('Circle/node'))
        actual = resource('Visual')
        for name in ('ID', 'Name'):
            original.find(f'./attribute[@id="{name}"]').set('value', attrs(actual)[name])
        for obj in original.findall('./children/node[@id="Objects"]'):
            obj.find('./attribute[@id="MaterialID"]').set('value', boundary.MATERIAL)
        self.assertEqual(ET.tostring(original), ET.tostring(actual))
        for key, expected in (('BoundsMin', (-1, -1, -.05)), ('BoundsMax', (1, 1, .05))):
            for value, target in zip(map(float, attrs(actual)[key].split()), expected):
                self.assertAlmostEqual(value, target, places=7)

    def test_only_bloodsea_has_the_new_visual_and_explicit_material_dependency(self):
        import xueyan_visual_polish as blood
        from sword_vfx_resources import _metadata
        if not (blood.fx.DATA / 'Editor/Config/AllSpark/ComponentDefinition.xcd').is_file():
            self.skipTest('Native AllSpark dictionaries unavailable')
        dictionary = blood.fx.PropertyDictionary(blood.fx.DATA)
        with tempfile.TemporaryDirectory() as tmp:
            for key in blood.PROFILES:
                root, origins, details = blood.author(blood.fx.DATA, key, dictionary)
                references = ET.tostring(root, encoding='unicode')
                self.assertEqual(boundary.VISUAL in references, key == 'xueyan_xuehai_status')
                if key != 'xueyan_xuehai_status':
                    continue
                path = Path(tmp) / 'bloodsea.lsefx'; blood.fx.write(path, root)
                meta = _metadata(path, 'status')
                self.assertIn(boundary.VISUAL, meta['dependencies'])
                self.assertIn(boundary.MATERIAL, meta['dependencies'])
                self.assertTrue(meta['looping'])
                self.assertEqual(meta['duration'], 5.8)

    def test_resource_generation_is_isolated_and_does_not_reexport_unchanged_binaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            unrelated = Path(tmp) / 'untouched.lsf'; unrelated.write_bytes(b'original')
            def convert(path):
                path.with_suffix('.lsf').write_bytes(b'compiled')
                return path.with_suffix('.lsf')
            with patch('sword_vfx_resources._convert', side_effect=convert) as export:
                paths = boundary.generate_resources(tmp)
                self.assertEqual(export.call_count, 2)
                boundary.generate_resources(tmp)
                self.assertEqual(export.call_count, 2)
            self.assertEqual(unrelated.read_bytes(), b'original')
            self.assertEqual(len(paths), 4)
            for p in paths:
                self.assertIn('[PAK]_ESC_XuehaiBoundary', p.as_posix())


if __name__ == '__main__':
    unittest.main()
