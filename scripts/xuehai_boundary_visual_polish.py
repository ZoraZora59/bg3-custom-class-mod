"""Bloodsea-only world-model material; reuse the shipped two-sided shader.

The H20 annulus inherited a character-local sphere mask and Fresnel opacity.
This preset uses the native Model graph's vertex RGBA and its UV0.y gradient
to show only the outer rim of the shipped annulus. Geometry and the status
loop are unchanged; the final colour power and intensity are explicitly unity.
Official workflow: https://docs.baldursgate3.game/index.php?title=Reusing_Base_Game_Shaders
"""
from pathlib import Path
import copy
import xml.etree.ElementTree as ET

from sword_cultivator_spec import FOLDER, guid

NAME = 'ESC_Xuehai_WorldBoundary'
VISUAL = guid('vfx/xueyan/xuehai/world-boundary/visual')
MATERIAL = guid('vfx/xueyan/xuehai/world-boundary/material')
# Engine.pak TextureBank: Engine_White, an opaque 16x16 RGBA texture.
WHITE_TEXTURE = '3d644f03-35d9-4819-bb56-dea978a3e975'
SHADER = ('Public/Shared/Assets/Materials/Effects/Model/'
          'VFX_Model_AlphaBlend_Unlit_Emissive_Panning_UVDistortion_TwoSided_01.lsf')
TEMPLATE = Path(__file__).parent / 'resources/native-xuehai-world-material.lsx'
VISUAL_TEMPLATE = Path(__file__).parent / 'resources/native-sword-glow.lsx'
BANKS = {kind: Path('Public') / FOLDER / 'Content/Assets/Effects' / folder
         / '[PAK]_ESC_XuehaiBoundary/_merged.lsx'
         for kind, folder in (('Material', 'Materials'), ('Visual', 'Models'))}

# These native graph switches make the annulus independent of character
# bones, camera angle, UV motion, and a changing dynamic-parameter input.
SCALARS = {
    'Distortion_Mult': 0, 'Use_DistortionOnMaskTexture': 0,
    'Use_DistortionOnMainTexture': 0, '_Use_DynXForMaskPowerMult': 0,
    'Use_MaskTexture': 0, '_Use_ProceduralGradientForMask': 1,
    '_Use_FresnelOpacity': 0, 'UseNearCameraFade': 0,
    'Use_ColorRamp': 0, 'TextureToEmissiveColor': 0,
    'Switch_UseEntireOpacityForContrast': 0,
    'MainTexture_Power': 1, 'MainTexture_Mult': 1,
    'EmissivePower': 1, 'OpacityPower': 1, 'Opacity_Mult': 1,
    # These run AFTER the ColorRamp switch in the native graph. Leaving the
    # donor's power 5 / intensity 50 overexposes even with Use_ColorRamp=0.
    'Colour_Ramp_Pow': 1, 'Colour_Ramp_Intensity': 1,
    'DepthDifferenceBlendDistance': .025, 'ClipTest': .001,
    'FogAmount': 0,
}
VECTORS = {
    'MainTexture_PanningSpeed': (0, 0), 'MaskTexture_PanningSpeed': (0, 0),
    'Distortion_PanningSpeed': (0, 0), 'MainTexture_UVMult': (1, 1),
    # Native GR2: radius .90218 at V=0/1, radius 1 at V=.5. The graph uses
    # smoothstep(top,V) * smoothstep(bottom,1-V), giving .176m soft width at
    # scale 6 while keeping the actual outer boundary at six metres.
    'ProceduralMask_Top_SmoothStep': (.35, .45),
    'ProceduralMask_Bottom_SmoothStep': (.35, .45),
}


def dependencies():
    return {VISUAL: (MATERIAL,)}


def documents():
    """Create only this material/visual pair, never shared sword resources."""
    from sword_vfx_resources import _attribute, _document
    material = copy.deepcopy(ET.parse(TEMPLATE).getroot())
    visual = copy.deepcopy(ET.parse(VISUAL_TEMPLATE).find('Circle/node'))

    def attr(node, name, value):
        node.find(f'./attribute[@id="{name}"]').set('value', str(value))

    assert material.find('./attribute[@id="SourceFile"]').get('value') == SHADER
    attr(material, 'ID', MATERIAL); attr(material, 'Name', NAME)
    for name in ('MainTexture_Map', 'MaskTexture_Map'):
        node = next(n for n in material.findall('./children/node')
                    if n.find(f'./attribute[@id="ParameterName"][@value="{name}"]') is not None)
        attr(node, 'Enabled', 'True'); attr(node, 'ID', WHITE_TEXTURE)
    for kind, values, typ in (('ScalarParameters', SCALARS, 'float'),
                              ('Vector2Parameters', VECTORS, 'fvec2')):
        for name, value in values.items():
            node = next((n for n in material.findall('./children/node')
                         if n.find(f'./attribute[@id="ParameterName"][@value="{name}"]') is not None), None)
            if node is None:
                node = ET.SubElement(material.find('children'), 'node', id=kind)
                _attribute(node, 'ParameterName', 'FixedString', name)
                _attribute(node, 'Enabled', 'bool', True)
                _attribute(node, 'Value', typ, '')
            attr(node, 'Enabled', 'True')
            attr(node, 'Value', ' '.join(map(str, value)) if isinstance(value, tuple) else value)
    attr(visual, 'ID', VISUAL); attr(visual, 'Name', NAME)
    for obj in visual.findall('./children/node[@id="Objects"]'):
        attr(obj, 'MaterialID', MATERIAL)
    docs = {}
    for kind, node in (('Material', material), ('Visual', visual)):
        root, bank = _document(kind + 'Bank')
        ET.SubElement(bank, 'children').append(node)
        docs[kind] = root
    return docs


def generate_resources(source):
    from sword_vfx_resources import _convert, _write_xml
    paths = []
    for kind, root in documents().items():
        path = Path(source) / BANKS[kind]
        previous = path.read_bytes() if path.is_file() else None
        _write_xml(path, root)
        if previous != path.read_bytes() or not path.with_suffix('.lsf').is_file():
            _convert(path)
        paths.extend((path, path.with_suffix('.lsf')))
    return paths
