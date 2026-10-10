"""Check native MEI field types, separately from VFX binary and visual proof.

Native references: Shared Cleave_CastEffect
1d808499-eac9-408a-b5c8-219bb4f52bdc and MagicMissile_PrepareEffect
f9785481-e126-4499-b00e-f36fa02cd196. Toolkit's 2026-10-07 load explicitly
requires StartTextKey LSString (23), rejecting FixedString (22).
"""
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts'))
import school_visual_polish as polish
import sword_vfx_resources as base
from sword_cultivator_spec import FOLDER

SOURCE = REPO / 'mods/EasternSwordCultivator/Source'
# This is the native resource contract, deliberately independent of the
# production type mapping. Keep string events distinct from binding enums.
NATIVE_TYPES = {
    'UUID': 'guid', 'EffectResourceGuid': 'guid',
    'DetachSource': 'bool', 'DetachTarget': 'bool', 'KeepRotation': 'bool',
    'UseOrientDirection': 'bool', 'UseDistance': 'bool', 'UseScaleOverride': 'bool',
    'KeepScale': 'bool', 'MainHand': 'bool', 'OffHand': 'bool', 'Enabled': 'bool',
    'MinDistance': 'float', 'MaxDistance': 'float',
    'BindSourceTo': 'FixedString', 'BindTargetTo': 'FixedString', 'Pivot': 'FixedString',
    'DamageType': 'uint32', 'VerbalIntent': 'uint32',
    'StartTextKey': 'LSString', 'EndTextKey': 'LSString',
}


class NativeMeiAttributeTypes(unittest.TestCase):
    def assert_native_types(self, root):
        parent = root.find('.//node[@id="MultiEffectInfos"]')
        self.assertIsNotNone(parent)
        self.assertEqual(parent.find('attribute[@id="UUID"]').get('type'), 'guid')
        self.assertEqual(parent.find('attribute[@id="Name"]').get('type'), 'LSString')
        items = parent.findall('children/node[@id="EffectInfo"]')
        self.assertTrue(items)
        for item in items:
            for attribute in item.findall('attribute'):
                self.assertIn(attribute.get('id'), NATIVE_TYPES)
                self.assertEqual(attribute.get('type'), NATIVE_TYPES[attribute.get('id')],
                                 ET.tostring(attribute, encoding='unicode'))
            bones = item.findall('children/node')
            self.assertTrue(bones)
            for bone in bones:
                self.assertIn(bone.get('id'), ('SourceBone', 'TargetBone'))
                self.assertEqual(bone.find('attribute[@id="Value"]').get('type'), 'LSString')

    def test_polish_cast_main_and_offhand_export_the_animation_key_as_lsstring(self):
        for key, profile in polish.profiles().items():
            hands = (False, True) if profile['binding'] == 'cast' else (False,)
            for offhand in hands:
                with self.subTest(key=key, offhand=offhand):
                    editor, exported = polish._mei(key, profile, offhand)
                    self.assert_native_types(exported)
                    event = exported.find('.//node[@id="EffectInfo"]/attribute[@id="StartTextKey"]')
                    if profile['binding'] == 'cast':
                        expected = 'CastOffhand' if offhand else 'Cast'
                        self.assertEqual(event.get('type'), 'LSString')
                        self.assertEqual(event.get('value'), expected)
                        self.assertEqual(editor.find('EffectInfo').get('StartTextKey'), expected)
                    else:
                        self.assertIsNone(event)
                        self.assertNotIn('StartTextKey', editor.find('EffectInfo').attrib)

    def test_base_mei_schema_retains_immediate_events(self):
        for style in base.STYLES:
            for phase in base.PHASES:
                if phase == 'projectile':
                    continue
                with self.subTest(style=style, phase=phase):
                    _, exported = base._mei(style, phase)
                    self.assert_native_types(exported)
                    self.assertIsNone(exported.find('.//attribute[@id="StartTextKey"]'))
                    self.assertIsNone(exported.find('.//attribute[@id="EndTextKey"]'))

    def test_both_start_and_end_events_use_native_lsstring_even_when_empty(self):
        node = ET.Element('node', id='EffectInfo')
        base._effect_info_attribute(node, 'StartTextKey', 'CastOffhand')
        base._effect_info_attribute(node, 'EndTextKey', '')
        self.assertEqual([(a.get('id'), a.get('type'), a.get('value')) for a in node],
                         [('StartTextKey', 'LSString', 'CastOffhand'),
                          ('EndTextKey', 'LSString', '')])
        with self.assertRaisesRegex(ValueError, 'Unverified native EffectInfo'):
            base._effect_info_attribute(node, 'UnverifiedTextKey', 'Cast')

    def test_all_registered_source_meis_follow_the_native_type_contract(self):
        paths = sorted((SOURCE / 'Public' / FOLDER / 'MultiEffectInfos').glob('*.lsx'))
        self.assertTrue(paths)
        expected_polish_ids = {polish.mei_guid(key, offhand)
                              for key, profile in polish.profiles().items()
                              for offhand in ((False, True) if profile['binding'] == 'cast' else (False,))}
        self.assertLessEqual(expected_polish_ids, {path.stem for path in paths})
        for path in paths:
            with self.subTest(path=path.name):
                root = ET.parse(path).getroot()
                self.assert_native_types(root)
                editor_path = SOURCE / 'Editor/Mods' / FOLDER / 'MultiEffectInfos' / (path.stem + '.mei')
                editor = ET.parse(editor_path).getroot()
                exported_items = root.findall('.//node[@id="EffectInfo"]')
                self.assertEqual(len(exported_items), len(editor.findall('EffectInfo')))
                for exported_item, editor_item in zip(exported_items, editor.findall('EffectInfo')):
                    for field in ('StartTextKey', 'EndTextKey'):
                        event = exported_item.find('attribute[@id="' + field + '"]')
                        self.assertEqual(None if event is None else event.get('value'), editor_item.get(field))


if __name__ == '__main__':
    unittest.main()
