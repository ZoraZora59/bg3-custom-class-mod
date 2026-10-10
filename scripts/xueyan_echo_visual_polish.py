"""Three native MirrorImage overlays, without actors or combat state writes.

The installed MirrorImage 01/02/03 banks use OverlayMaterial on TargetVisual,
including armour and weapons. Their native Illusion 04/05/06 material instances
provide three distinct WPO offsets. Keep those native bindings and geometry;
only change colour, opacity, brightness and bounded one-shot timing.
"""
from pathlib import Path
import copy
import hashlib
import json
import xml.etree.ElementTree as ET

import xueyan_visual_polish as blood
from sword_cultivator_spec import FOLDER, guid
from sword_vfx_resources import _attribute, _convert, _document, _metadata, _write_xml

fx = blood.fx
COLOR = '3237a2f2-de49-49e9-939f-2224ee8413a9'
ALPHA = '0deac224-14e2-4d21-9e9b-d70dd9ccff2a'
BRIGHTNESS = '18f82423-f5a6-47bc-8e35-3731038b5bb3'
MATERIAL = 'c4298659-2875-4dca-bd1c-6eb147c17032'
WEAPON = 'ded89a18-8bba-4b36-a81f-a822efa2d4fb'
ARMOUR = '2222b911-fd92-47f1-850a-4e22f839779d'
TARGET = 'c264cdea-ce1b-4bf3-a5d0-8575d9f656fc'
EDITOR = Path('Editor/Mods') / FOLDER / 'Assets/Effects/Sword/Xueyan'
COMPILED = Path('Public') / FOLDER / 'Assets/Effects/Effects_Banks/Sword/Xueyan'
RECEIPT = COMPILED / 'native-compile.json'
BANK = Path('Public') / FOLDER / 'Content/Assets/Effects/Effects/Sword/[PAK]_ESC_XueyanEchoes/_merged.lsx'
KEYS = ('intro', 'echo1', 'echo2', 'echo3')
MATERIALS = ('6dc3c781-802c-dbe3-03fb-8349f07fb906',
             '429f4b3f-14ab-4e1d-b9b2-502b75c6cd16',
             '3a233c44-d5fd-1208-a9fe-e96072d04255')


def effect_name(key): return 'VFX_ESC_Xueyan_Wusheng_' + key.title() + '_01'
def effect_guid(key): return guid('vfx/xueyan/echo/' + key)
def paths(key): return EDITOR / (effect_name(key)+'.lsefx'), COMPILED / (effect_name(key)+'.lsfx')
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def author(data, key, dictionary):
    if key not in KEYS: raise ValueError(key)
    data = Path(data)
    root, base = blood._base(data, 'wusheng_'+key)
    root.set('id', guid('vfx/xueyan/echo/editor/'+key))
    group = blood._group(root, 'Native equipped blood echoes')
    origins = [base]
    selected = (1, 2, 3) if key == 'intro' else (int(key[-1]),)
    duration = 1.8 if key == 'intro' else 1.35
    for index in selected:
        origin = data / f'Editor/Mods/Shared/Assets/Effects/Status/VFX_Status_MirrorImage_{index:02}.lsefx'
        native = ET.parse(origin).getroot()
        template = next(t for t in native.findall('./trackgroups/trackgroup/track')
                        if t.get('muted') == 'False' and t.find('component') is not None
                        and t.find('component').get('class') == 'OverlayMaterial')
        track, overlay = blood._clone(template, 'wusheng_'+key, 'Equipped blood echo', index-1)
        material = overlay.find(f'./properties/property[@id="{MATERIAL}"]/data/datum').get('value')
        if MATERIALS[index-1] not in material: raise ValueError('Native MirrorImage material drift')
        fx.timing(overlay, 0, duration)
        fx.recolor(dictionary, overlay, COLOR, (255, 14, 35))
        alpha = .88 if key != 'intro' or index == 1 else .72
        fx.replace_ramp(dictionary, overlay, ALPHA,
                        ([(0, 0), (.07, alpha), (.62, alpha), (.9, .2), (1, 0)],))
        # Native startup brightness spikes obscure the silhouette. Hold a
        # readable crimson rim; retain native Dynamic Value/Fresnel motion.
        blood._constant(dictionary, overlay, BRIGHTNESS, (3.5 if index == 1 or key != 'intro' else 2.7,))
        group.append(track)
        origins.append(origin)
    fx.bounds(dictionary, root, 5, duration)
    return root, origins, dict(shadows=list(selected), duration=duration,
        nativeMaterials=[MATERIALS[i-1] for i in selected],
        binding='native equipped TargetVisual via PlayEffect at Dummy_Root',
        attackPlayback='none; one bank per actual cast event', gameplayActors=0,
        clientVisualTest='pending')


def generate_resources(source):
    source = Path(source)
    if not (source / RECEIPT).is_file(): return {'enabled': False, 'records': {}}
    receipt = json.loads((source / RECEIPT).read_text('utf-8'))
    assert receipt['compiler'] == 'AllSpark.EffectCompiler.Compiler.Compile'
    rows = {r['effect_name']: r for r in receipt['records']}
    assert set(rows) == {effect_name(k) for k in KEYS}, 'Incomplete blood echo native receipt'
    verified = []
    for key in KEYS:
        editor, binary = paths(key); row = rows[effect_name(key)]
        assert row['semantic_roundtrip_verified'] and row['binary_version'] == 7
        assert digest(source/editor) == row['source_sha256'].lower(), key
        assert digest(source/binary) == row['compiled_sha256'].lower(), key
        meta = _metadata(source/editor, 'cast')
        assert not meta['looping'], 'Blood echoes must end without gameplay cleanup'
        verified.append((key, editor, binary, row, meta))
    root, parent = _document('EffectBank'); children = ET.SubElement(parent, 'children')
    records = {}
    for key, editor, binary, row, meta in verified:
        node = ET.SubElement(children, 'node', id='Resource')
        for field, attr in (('bounds_min','BoundsMin'), ('bounds_max','BoundsMax'), ('center','Center')):
            _attribute(node, attr, 'fvec3', ' '.join(f'{v:g}' for v in meta[field]))
        for field, typ, value in (
            ('CullingDistance','float',0), ('Duration','float',meta['duration']),
            ('EffectName','FixedString',effect_name(key)), ('ID','FixedString',effect_guid(key)),
            ('Initialized','bool',True), ('InterruptionMode','uint32',0), ('Localized','bool',False),
            ('Looping','bool',False), ('Name','LSString',effect_name(key)), ('Radius','float',meta['radius']),
            ('SourceFile','LSString',binary.as_posix())):
            _attribute(node, field, typ, value)
        deps = ET.SubElement(ET.SubElement(ET.SubElement(node,'children'),'node',id='Dependencies'),'children')
        for dependency in meta['dependencies']:
            _attribute(ET.SubElement(deps,'node',id='DependentResource'),'Object','FixedString',dependency)
        records[key] = dict(effect=effect_guid(key), effectName=effect_name(key), duration=meta['duration'],
                            sourceSHA256=row['source_sha256'].lower(), compiledSHA256=row['compiled_sha256'].lower())
    path = source/BANK
    old = path.read_bytes() if path.is_file() else None
    _write_xml(path, root)
    if old != path.read_bytes() or not path.with_suffix('.lsf').is_file(): _convert(path)
    return dict(enabled=True, records=records, clientVisualTest='pending',
                semantics='three native equipped overlays; actual casts grouped into three pairs')
