"""Twelve-metre Tianqing sword light; native receipt gates registration.

Reuse the proven -Z world-beam mesh and owned luminous sword materials.
This module only authors/registers visuals; it never changes spell mechanics.
"""
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import yixiantian_vfx as beam
import sword_vfx_resources as resources
from sword_cultivator_spec import FOLDER, guid
from world_beam_materials import material_id

NAME = 'VFX_ESC_Tianqing_Nifeng_LongBlade_01'
VISUAL = guid('vfx/nifeng/line/core')
HALO_VISUAL = guid('vfx/nifeng/line/halo')
SOURCE_REL = Path('Editor/Mods') / FOLDER / 'Assets/Effects/Sword/Nifeng' / (NAME + '.lsefx')
BINARY_REL = Path('Public') / FOLDER / 'Assets/Effects/Effects_Banks/Sword/Nifeng' / (NAME + '.lsfx')
RESOURCE_REL = Path('Public') / FOLDER / 'Content/Assets/Effects/Effects/Sword/[PAK]_ESC_NifengLine/_merged.lsx'
VISUAL_REL = Path('Public') / FOLDER / 'Content/Assets/Effects/Models/[PAK]_ESC_NifengLine/_merged.lsx'
RECEIPT = BINARY_REL.parent / 'native-compile.json'


def author(data):
    root, donors, designs = beam.author(data)
    fx = beam.fx
    dictionary = fx.PropertyDictionary(Path(data))
    root.set('id', guid('vfx/editor/nifeng/long-blade'))
    for index, phase in enumerate(root.findall('./phases/object/data')):
        phase.set('id', guid(f'vfx/phase/nifeng/long-blade/{index}'))
    group = root.find('./trackgroups/trackgroup')
    group.set('name', 'One forward 12m golden sword light')
    widths = (.28, .8)
    colors = ((255, 244, 220), (255, 183, 35))
    for index, track in enumerate(group.findall('track')[:2]):
        component = track.find('component')
        design = designs[index]
        design.update(label=('Gold white 12m blade core' if index == 0 else 'Soft gold 12m blade halo'),
                      width=widths[index], rgb=colors[index], visual=(VISUAL, HALO_VISUAL)[index])
        track.set('name', design['label'])
        component.set('instancename', guid(f'vfx/component/nifeng/long-blade/model/{index}'))
        fx.set_value(component, fx.NAME, design['label'])
        fx.set_value(component, fx.MESH, f"ESC_Nifeng_Line_{index} <{design['visual']}>")
        scales = list(design['axis_scale'])
        scales[0] = design['width'] / (.3824824 - (-.3824822))
        scales[2] *= 12 / 30
        design['axis_scale'] = tuple(scales)
        beam.constant(dictionary, component, fx.MODEL_SCALE, scales)
        red, green, blue = design['rgb']
        color = (0xff000000 | red << 16 | green << 8 | blue) - 0x100000000
        beam.constant(dictionary, component, fx.MODEL_COLOR, (color,))
    bounds = group.findall('track')[2].find('component')
    bounds.set('instancename', guid('vfx/component/nifeng/long-blade/bounds'))
    fx.set_value(bounds, fx.BOUND_CENTER, '0,0,-6')
    fx.set_value(bounds, fx.BOUND_RADIUS, 6.15)
    return root, donors, designs


def visual_bank():
    root, parent = resources._document('VisualBank')
    children = ET.SubElement(parent, 'children')
    for index, (visual, shape) in enumerate(((VISUAL, 'sword'), (HALO_VISUAL, 'circle'))):
        node = copy.deepcopy(ET.parse(beam.BEAM_TEMPLATE).getroot())
        for key, value in [('ID', visual), ('Name', f'ESC_Nifeng_Line_{index}')]:
            node.find(f'./attribute[@id="{key}"]').set('value', value)
        for obj in node.findall('./children/node[@id="Objects"]'):
            obj.find('./attribute[@id="MaterialID"]').set('value', material_id('tianqing', shape))
        children.append(node)
    return root


def generate_resources(source):
    source = Path(source).resolve()
    if not (source / RECEIPT).is_file():
        return dict(enabled=False, remaining='native compiler receipt missing')
    proof = json.loads((source / RECEIPT).read_text(encoding='utf-8'))
    if proof.get('compiler') != 'AllSpark.EffectCompiler.Compiler.Compile' or len(proof.get('records', [])) != 1:
        raise ValueError('Nifeng requires exactly one native compiler record')
    record = proof['records'][0]
    if record.get('effect_name') != NAME or not record.get('semantic_roundtrip_verified') or record.get('binary_version') != 7:
        raise ValueError('Native Nifeng semantic roundtrip missing')
    for path, key in ((SOURCE_REL, 'source_sha256'), (BINARY_REL, 'compiled_sha256')):
        if not (source / path).is_file() or hashlib.sha256((source / path).read_bytes()).hexdigest() != record[key].lower():
            raise ValueError('Stale native Nifeng receipt')
    meta = resources._metadata(source / SOURCE_REL, 'cast')
    if meta['looping'] or set(meta['dependencies']) != {VISUAL, HALO_VISUAL}:
        raise ValueError('Unexpected Nifeng lifecycle or direct dependencies')
    resources._write_xml(source / VISUAL_REL, visual_bank())
    resources._convert(source / VISUAL_REL)
    meta['dependencies'] = sorted({VISUAL, HALO_VISUAL, material_id('tianqing'), material_id('tianqing', 'circle')})
    root, parent = resources._document('EffectBank')
    children = ET.SubElement(parent, 'children')
    resources._effect_resource(children, 'tianqing', 'cast', meta)
    values = dict(EffectName=NAME, Name=NAME, ID=guid('vfx/effect/nifeng/long-blade'), SourceFile=BINARY_REL.as_posix())
    for attribute in children.find('node').findall('attribute'):
        if attribute.get('id') in values:
            attribute.set('value', values[attribute.get('id')])
    resources._write_xml(source / RESOURCE_REL, root)
    resources._convert(source / RESOURCE_REL)
    return dict(enabled=True, effect=values['ID'], effectName=NAME, heightOffset=.8, range=12,
                sourceSHA256=record['source_sha256'], compiledSHA256=record['compiled_sha256'],
                orientationNativeVerified=False, orientationMode='continuousVanilla270MinusAngleX',
                nativeVisualAudioAcceptance='pending')
