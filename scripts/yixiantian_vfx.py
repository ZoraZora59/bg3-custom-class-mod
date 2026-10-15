"""Fixed thirty-metre world beam, enabled only by matching native compilation."""
import copy,hashlib,importlib.util,json
from pathlib import Path
import xml.etree.ElementTree as ET
import sword_vfx_resources as resources
from sword_cultivator_spec import FOLDER,guid
from world_beam_materials import material_id
REPO=Path(__file__).resolve().parents[1]
loader=importlib.util.spec_from_file_location('yixiantian_fx_definitions',REPO/'scripts/generate-sword-vfx.py')
fx=importlib.util.module_from_spec(loader);loader.loader.exec_module(fx)
NAME='VFX_ESC_Taixuan_Yixiantian_LongBeam_01'
VISUAL=guid('vfx/yixiantian/beam/core')
HALO_VISUAL=guid('vfx/yixiantian/beam/halo')
BEAM_TEMPLATE=Path(__file__).parent/'resources/native-beam.lsx'
SOURCE_REL=Path('Editor/Mods')/FOLDER/'Assets/Effects/Sword/Yixiantian'/(NAME+'.lsefx')
BINARY_REL=Path('Public')/FOLDER/'Assets/Effects/Effects_Banks/Sword/Yixiantian'/(NAME+'.lsfx')
RESOURCE_REL=Path('Public')/FOLDER/'Content/Assets/Effects/Effects/Sword/[PAK]_ESC_YixiantianBeam/_merged.lsx'
RECEIPT=BINARY_REL.parent/'native-compile.json'
def constant(dictionary,component,key,values):
    fx.replace_ramp(dictionary,component,key,tuple([(0,v),(1,v)] for v in values))
SCALE_UNIFORM = 'f80eefa7-3ffe-4c08-b043-596ae48487f8'
OFFSET_RAMP = '37b047c1-8fb7-4e7c-9319-58db9da44e77'
ROTATION = '4a72a815-57fb-4fcb-9a50-1024331ce66a'
ROTATION_RATE = 'e5ece95a-a162-4a49-b029-cbc701fb00e4'
ROTATION_LIFE = 'c57b1310-2df9-4339-bdf8-a97475e121ff'
ALPHA = '00910be4-aaa1-41a2-946f-735d33de387b'
BRIGHTNESS = '6cbb9e51-0d17-4916-9666-30d8c7b47e81'
MODIFIERS = ('5b7fc64a-bf90-4085-9151-044aa275f590', 'de10ede1-b899-4565-8a4b-eaa258360ee9', 'f009ecca-fae4-49fd-aad3-3224e3ed7e21')

def author(data):
    NATIVE=Path(data)/'Editor/Mods/Shared/Assets/Effects/Beams/VFX_Beams_Debuff_TrueStrike_Beam_01.lsefx'
    dictionary=fx.PropertyDictionary(Path(data))
    # Exact native [PAK]_Static_Models Visual bounds and Objects material.
    evidence=dict(bounds_min=(-.3824822,-.3824274,-10.000001),bounds_max=(.3824824,.38242725,0),name='VFX_Static_Beam_01_Exterior_Default_01')
    root = ET.parse(NATIVE).getroot()
    donor, = [t for t in root.findall('./trackgroups/trackgroup/track')
              if t.find('component').get('instancename') == 'e55f84d1-b87c-48e3-8227-e7d2e34133aa']
    bound, = [t for t in root.findall('./trackgroups/trackgroup/track') if t.find('component').get('class') == 'BoundingSphere']
    if donor.get('muted') != 'False' or donor.find('component').get('class') != 'Model':
        raise ValueError('Verified native TrueStrike Model donor changed')
    root.set('id', guid('vfx/editor/yixiantian/long-beam'))
    for index, phase in enumerate(root.findall('./phases/object/data')):
        phase.set('id', guid(f'vfx/phase/yixiantian/long-beam/{index}'))
        phase.set('duration', '.42' if index == 0 else '0')
        phase.set('playcount', '1')
    groups = root.find('trackgroups');groups.clear()
    group = ET.SubElement(groups, 'trackgroup', name='One continuous 30m luminous sword edge')
    ET.SubElement(ET.SubElement(group, 'ids'), 'id', value='1')
    low, high = evidence['bounds_min'], evidence['bounds_max']
    length = high[2] - low[2]
    # Native Default material rendered as an opaque grey slab in H13b. Owned
    # visuals use the already rendered cyan unlit material and a softer halo.
    designs = [dict(label='White cyan narrow 30m core', width=.12, thickness=.12, duration=.34, rgb=(225, 248, 255), peak_alpha=.95, visual=VISUAL),
               dict(label='Low alpha cyan narrow halo', width=.6, thickness=.10, duration=.42, rgb=(120, 215, 255), peak_alpha=.17, visual=HALO_VISUAL)]
    for index, design in enumerate(designs):
        track = copy.deepcopy(donor);component = track.find('component')
        track.set('name', design['label']);track.set('muted', 'False');track.set('mutestateoverride', 'Unmuted')
        component.set('instancename', guid(f'vfx/component/yixiantian/long-beam/model/{index}'))
        fx.set_value(component, fx.NAME, design['label']);fx.timing(component, 0, design['duration'])
        dictionary.property(component, fx.MESH)
        fx.set_value(component, fx.MESH, f"ESC_Yixiantian_Beam_{index} <{design['visual']}>")
        scale = (design['width'] / (high[0] - low[0]), design['thickness'] / (high[1] - low[1]), 30 / length)
        constant(dictionary, component, fx.MODEL_SCALE, scale)
        constant(dictionary, component, SCALE_UNIFORM, (1,))
        for key in MODIFIERS:
            dictionary.property(component, key);fx.set_value(component, key, 1)
        for key in (ROTATION, ROTATION_RATE, ROTATION_LIFE, OFFSET_RAMP):
            constant(dictionary, component, key, (0, 0, 0))
        dictionary.property(component, fx.POSITION);fx.set_value(component, fx.POSITION, '0,0,0')
        rgb=design['rgb'];color=(0xff000000 | rgb[0] << 16 | rgb[1] << 8 | rgb[2])-0x100000000
        constant(dictionary, component, fx.MODEL_COLOR, (color,))
        constant(dictionary, component, BRIGHTNESS, (5,))
        duration=design['duration']
        fx.replace_ramp(dictionary, component, ALPHA, ([(0, 0), (.025/duration, design['peak_alpha']), (.10/duration, design['peak_alpha']), (1, 0)],))
        # Native dynamic material ramps retained; only transform/color/alpha changed.
        group.append(track);design['axis_scale']=scale
    track=copy.deepcopy(bound);component=track.find('component')
    track.set('name','Complete fixed beam culling sphere');track.set('muted','False');track.set('mutestateoverride','Unmuted')
    component.set('instancename',guid('vfx/component/yixiantian/long-beam/bounds'))
    fx.set_value(component,fx.NAME,track.get('name'));fx.timing(component,0,.42)
    dictionary.property(component,fx.BOUND_CENTER);fx.set_value(component,fx.BOUND_CENTER,'0,0,-15')
    dictionary.property(component,fx.BOUND_RADIUS);fx.set_value(component,fx.BOUND_RADIUS,15.15)
    group.append(track)

    return root,[NATIVE],designs

def generate_resources(source):
    source=Path(source).resolve()
    if not (source/RECEIPT).is_file():return dict(enabled=False,remaining='native compiler receipt missing')
    proof=json.loads((source/RECEIPT).read_text(encoding='utf-8'))
    if proof.get('compiler')!='AllSpark.EffectCompiler.Compiler.Compile' or len(proof.get('records',[]))!=1:
        raise ValueError('Beam requires exactly one native compiler record')
    r=proof['records'][0]
    if r.get('effect_name')!=NAME or not r.get('semantic_roundtrip_verified') or r.get('binary_version')!=7:
        raise ValueError('Native beam semantic roundtrip missing')
    for p,key in [(SOURCE_REL,'source_sha256'),(BINARY_REL,'compiled_sha256')]:
        if not (source/p).is_file() or hashlib.sha256((source/p).read_bytes()).hexdigest()!=r[key].lower():
            raise ValueError('Stale native beam receipt')
    meta=resources._metadata(source/SOURCE_REL,'cast')
    if meta['looping'] or set(meta['dependencies'])!={VISUAL,HALO_VISUAL}:raise ValueError('Unexpected beam lifecycle or direct dependencies')
    # Preserve the native mesh and -Z pivot; only replace its Objects material.
    visual_root,visual_parent=resources._document('VisualBank')
    visual_children=ET.SubElement(visual_parent,'children')
    for index,(visual,shape) in enumerate(((VISUAL,'sword'),(HALO_VISUAL,'circle'))):
        node=copy.deepcopy(ET.parse(BEAM_TEMPLATE).getroot())
        for key,value in [('ID',visual),('Name',f'ESC_Yixiantian_Beam_{index}')]:
            node.find(f'./attribute[@id="{key}"]').set('value',value)
        for obj in node.findall('./children/node[@id="Objects"]'):
            obj.find('./attribute[@id="MaterialID"]').set('value',material_id('taixuan',shape))
        visual_children.append(node)
    visual_path=source/Path('Public')/FOLDER/'Content/Assets/Effects/Models/[PAK]_ESC_YixiantianBeam/_merged.lsx'
    resources._write_xml(visual_path,visual_root);resources._convert(visual_path)
    meta['dependencies']=sorted({VISUAL,HALO_VISUAL,material_id('taixuan'),material_id('taixuan','circle')})
    root,parent=resources._document('EffectBank');children=ET.SubElement(parent,'children')
    resources._effect_resource(children,'taixuan','cast',meta)
    values=dict(EffectName=NAME,Name=NAME,ID=guid('vfx/effect/yixiantian/long-beam'),SourceFile=BINARY_REL.as_posix())
    for a in children.find('node').findall('attribute'):
        if a.get('id') in values:a.set('value',values[a.get('id')])
    resources._write_xml(source/RESOURCE_REL,root);resources._convert(source/RESOURCE_REL)
    return dict(enabled=True,effect=values['ID'],effectName=NAME,heightOffset=.8,range=30,
        sourceSHA256=r['source_sha256'],compiledSHA256=r['compiled_sha256'],
        orientationNativeVerified=False,orientationMode='continuousVanilla270MinusAngleX',nativeVisualAudioAcceptance='pending')
