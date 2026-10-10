"""Register native-compiled falling banks for spatial Osiris playback.

No MEI is attached to an individual victim. PlayEffectAtPosition takes an
EffectResource UUID, using the verified EffectBank schema in sword_vfx_resources.
Each compilation receipt must match both current editor source and binary.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from sword_cultivator_spec import FOLDER, guid
from sword_vfx_resources import _attribute, _convert, _document, _metadata, _write_xml
from tianqing_vfx_design import TIANQING_PROFILES, TIANQING_AUXILIARY_PROFILES, TIANQING_TIMING_PROFILES, TIANQING_TIMING_PAIRS

PROFILES = {k: p for k, p in {**TIANQING_PROFILES, **TIANQING_AUXILIARY_PROFILES, **TIANQING_TIMING_PROFILES}.items()
            if p.get('authoring_enabled')}
BANK = Path('Public') / FOLDER / 'Content/Assets/Effects/Effects/Sword/[PAK]_ESC_TianqingFalls/_merged.lsx'
RECEIPT = Path('Public') / FOLDER / 'Assets/Effects/Effects_Banks/Sword/Tianqing/native-compile.json'
REQUIRED = set(PROFILES)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def paths(key):
    name = PROFILES[key]['effect_name']
    return (Path('Editor/Mods') / FOLDER / 'Assets/Effects/Sword/Tianqing' / (name + '.lsefx'),
            Path('Public') / FOLDER / 'Assets/Effects/Effects_Banks/Sword/Tianqing' / (name + '.lsfx'))


def generate_resources(source):
    source = Path(source).resolve()
    receipt = source / RECEIPT
    if not receipt.is_file():
        return {'enabled': False, 'records': {}, 'remaining': 'native compilation receipt missing'}
    proof = json.loads(receipt.read_text(encoding='utf-8'))
    if proof.get('compiler') != 'AllSpark.EffectCompiler.Compiler.Compile':
        raise ValueError('Tianqing compilation receipt must identify the native AllSpark compiler')
    by_name = {r['effect_name']: r for r in proof['records']}
    root, parent = _document('EffectBank')
    children = ET.SubElement(parent, 'children')
    records = {}
    for key, profile in PROFILES.items():
        editable, binary = paths(key)
        row = by_name.get(profile['effect_name'])
        if row is None:
            continue
        if (not (source / binary).is_file() or not (source / binary).stat().st_size
                or digest(source / editable) != row['source_sha256'].lower()
                or digest(source / binary) != row['compiled_sha256'].lower()):
            raise ValueError(f'Stale or missing native Tianqing compilation: {key}')
        meta = _metadata(source / editable, 'impact')
        node = ET.SubElement(children, 'node', id='Resource')
        for field in ('bounds_min', 'bounds_max', 'center'):
            _attribute(node, {'bounds_min': 'BoundsMin', 'bounds_max': 'BoundsMax', 'center': 'Center'}[field],
                       'fvec3', ' '.join(f'{v:g}' for v in meta[field]))
        effect = guid('vfx/tianqing/effect/' + key)
        for field, typ, value in (
            ('CullingDistance', 'float', 0), ('Duration', 'float', meta['duration']),
            ('EffectName', 'FixedString', profile['effect_name']), ('ID', 'FixedString', effect),
            ('Initialized', 'bool', True), ('InterruptionMode', 'uint32', 0),
            ('Localized', 'bool', False), ('Looping', 'bool', meta['looping']),
            ('Name', 'LSString', profile['effect_name']), ('Radius', 'float', meta['radius']),
            ('SourceFile', 'LSString', binary.as_posix()),
        ):
            _attribute(node, field, typ, value)
        deps = ET.SubElement(ET.SubElement(ET.SubElement(node, 'children'), 'node', id='Dependencies'), 'children')
        for dependency in meta['dependencies']:
            _attribute(ET.SubElement(deps, 'node', id='DependentResource'), 'Object', 'FixedString', dependency)
        records[key] = {'effect': effect, 'effectName': profile['effect_name'],
                        'hitTimeMs': round(profile['hit_time'] * 1000),
                        'sourceSHA256': row['source_sha256'].lower(),
                        'compiledSHA256': row['compiled_sha256'].lower(), 'path': binary.as_posix()}
    if not REQUIRED <= records.keys():
        raise ValueError(f'Incomplete Tianqing release compilation: {sorted(REQUIRED - records.keys())}')
    _write_xml(source / BANK, root)
    _convert(source / BANK)
    return {'enabled': True, 'records': records,
            'timing': {key: {
                'prepareEffect': records[pair['prepare']]['effect'],
                'impactEffect': records[pair['impact']]['effect'],
                'prepareDescentMs': round(PROFILES[pair['prepare']]['hit_time'] * 1000),
                'hoverHeight': PROFILES[pair['prepare']]['hover_height'],
                'stopFadeMs': round(PROFILES[pair['prepare']]['stop_fade'] * 1000),
                'impactHitTimeMs': 0,
            } for key, pair in TIANQING_TIMING_PAIRS.items()},
            'tiandi': {**records['tianqing_tiandi'], 'intervalMs': 1000, 'stageCount': 3},
            'bafang': {**records['tianqing_bafang_column'], 'count': 8, 'radius': 8,
                       'angleOffset': 22.5, 'terrainSearchRadius': 1}}
