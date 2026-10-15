"""Receipt-gated, per-technique VFX; gameplay and animation stay with the generator.

Whole Tianqing falling swords remain spatial, once-per-cast effects. These
bindings supply only local contact, caster release, and native status loops.
Projectile children inherit the existing style's trail and motion, changing
only their contact effect. Human Jump/Fly trajectories are never replaced.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from sword_cultivator_spec import FOLDER, MODULE_UUID, guid
from sword_vfx_bindings import classify_spell, projectile_guid
from sword_vfx_resources import _attribute, _convert, _document, _effect_info_attribute, _metadata, _write_xml


SUBDIRECTORY = 'Polish'
EDITOR = Path('Editor/Mods') / FOLDER / 'Assets/Effects/Sword' / SUBDIRECTORY
PUBLIC = Path('Public') / FOLDER
COMPILED = PUBLIC / 'Assets/Effects/Effects_Banks/Sword' / SUBDIRECTORY
RECEIPT = COMPILED / 'native-compile.json'
BANK = PUBLIC / 'Content/Assets/Effects/Effects/Sword/[PAK]_ESC_SchoolPolish/_merged.lsx'
GROUP = guid('vfx/polish/mei/group')
STATUS_SKILLS = {'ESC_COUNTER_RANK2': 'taixuan_qinghui',
                 'ESC_IN_FLIGHT': 'sword_flight',
                 'ESC_COUNTER_RANK3': 'taixuan_xinghe',
                 'ESC_VFX_SWORD_DOMAIN': 'taixuan_taiqing',
                 'ESC_VFX_BLOOD_DOMAIN': 'xueyan_xuehai',
                 'ESC_VFX_DAMAGE_SHARE': 'xingge_fengyu',
                 'ESC_VFX_TEAM_RESONANCE': 'xingge_zhangjian'}
_enabled = {}


def authoring_modules():
    import taixuan_visual_polish
    import tianqing_visual_polish
    import xueyan_visual_polish
    import tianfeng_visual_polish
    import xingge_visual_polish
    import sword_flight_visual_polish
    return (taixuan_visual_polish, tianqing_visual_polish, xueyan_visual_polish,
            tianfeng_visual_polish, xingge_visual_polish, sword_flight_visual_polish)


def profiles():
    result = {}
    roles = set()
    for module in authoring_modules():
        for key, value in module.PROFILES.items():
            role = (value['skill'], value['binding'])
            if key in result or role in roles:
                raise ValueError(f'Duplicate per-technique VFX role: {key}')
            roles.add(role)
            result[key] = value
    # Exactly four target effects; all other profile records remain unchanged.
    from xingge_support_v2 import DESIGNS, CORE_SCALE
    for key, design in DESIGNS.items():
        result[key] = {**result[key], 'duration': design['duration'],
                       'model_scale': CORE_SCALE, 'pitch_degrees': design['pitch'],
                       'presentation': design['motif']}
    return result


def author_profile(module, data, key, dictionary):
    from xingge_support_v2 import DESIGNS, author as author_support
    if key in DESIGNS:
        # This factory already performs the steel-to-luminous conversion once.
        return author_support(data, key, dictionary)
    from sword_glow import apply as apply_glow
    root, origins, details = module.author(data, key, dictionary)
    details.update(apply_glow(root, dictionary, key.split('_')[0]))
    from nixue_v2 import apply as apply_nixue_v2
    details.update(apply_nixue_v2(root, dictionary, key))
    return root, origins, details


def effect_name(key):
    return 'VFX_ESC_Polish_' + '_'.join(word.title() for word in key.split('_')) + '_01'


def effect_guid(key):
    return guid('vfx/polish/effect/' + key)


def mei_guid(key, offhand=False):
    return guid('vfx/polish/mei/' + key + ('/offhand' if offhand else ''))


def paths(key):
    name = effect_name(key)
    return EDITOR / (name + '.lsefx'), COMPILED / (name + '.lsfx')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def attached_until_casted(profile):
    # This is an explicit single-technique runtime lifecycle, not permission
    # for ordinary cast effects to loop indefinitely through native MEIs.
    return (profile.get('skill') == 'tianqing_tianfeng' and profile.get('binding') == 'cast'
            and profile.get('lifecycle') == 'attached-until-casted')


def _mei(key, profile, offhand=False):
    status = profile['binding'] == 'status'
    cast = profile['binding'] == 'cast'
    target = profile['binding'] == 'target'
    # Native CastEffect's TargetEntity context is the caster. Part 3 and
    # ActionSurge use TargetBone, Pivot=Target for prepare/cast/status.
    bone_key = 'TargetBone'
    bone = 'Dummy_Root' if cast or status or target else 'Dummy_BodyFX'
    fields = dict(UUID=guid('vfx/polish/mei/' + key + ('/offhand' if offhand else '') + '/item'),
                  EffectResourceGuid=effect_guid(key), DetachSource=not status and not cast and not target,
                  DetachTarget=not status and not cast and not target, KeepRotation=False, UseOrientDirection=False,
                  UseDistance=False, UseScaleOverride=False, KeepScale=True,
                  MainHand=False, OffHand=False, MinDistance=0, MaxDistance=0,
                  BindSourceTo='SourceEntity', BindTargetTo='TargetEntity',
                  Pivot='Target', Enabled=True)
    if cast:
        fields['StartTextKey'] = 'CastOffhand' if offhand else 'Cast'
    name = effect_name(key) + ('_Offhand' if offhand else '')
    editor = ET.Element('MultiEffectInfos', UUID=mei_guid(key, offhand), OwnerUUID=GROUP, Name=name)
    ET.SubElement(editor, 'EffectInfo',
                  **{k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in fields.items()},
                  **{bone_key: bone}, DamageType='None', VerbalIntent='None')
    exported, parent = _document('MultiEffectInfos')
    _attribute(parent, 'UUID', 'guid', mei_guid(key, offhand))
    _attribute(parent, 'Name', 'LSString', name)
    item = ET.SubElement(ET.SubElement(parent, 'children'), 'node', id='EffectInfo')
    for field, value in fields.items():
        _effect_info_attribute(item, field, value)
    _effect_info_attribute(item, 'DamageType', 0)
    _effect_info_attribute(item, 'VerbalIntent', 0)
    _attribute(ET.SubElement(ET.SubElement(item, 'children'), 'node', id=bone_key), 'Value', 'LSString', bone)
    return editor, exported


def _projectile(key, parent_id, pathfind=False):
    root, parent = _document('Templates')
    node = ET.SubElement(ET.SubElement(parent, 'children'), 'node', id='GameObjects')
    uuid = guid('vfx/polish/projectile/' + key + ('/pathfind' if pathfind else ''))
    fields = [('LevelName', 'FixedString', ''), ('MapKey', 'FixedString', uuid),
              ('Name', 'LSString', effect_name(key) + ('_Pathfind' if pathfind else '_Projectile')),
              ('ParentTemplateId', 'FixedString', parent_id), ('Type', 'FixedString', 'projectile')]
    fields.append(('TrajectoryType', 'uint8', 2 if pathfind else 0))
    if not pathfind:
        fields.append(('ImpactFX', 'FixedString', effect_name(key)))
    for field, typ, value in fields:
        _attribute(node, field, typ, value)
    return root, uuid


def generate_resources(source):
    """Fail on stale/partial native receipts, preserving the previous good assets."""
    source = Path(source).resolve()
    if not (source / RECEIPT).is_file():
        return {'enabled': False, 'records': {}, 'remaining': 'native compilation receipt missing'}
    proof = json.loads((source / RECEIPT).read_text(encoding='utf-8'))
    if proof.get('compiler') != 'AllSpark.EffectCompiler.Compiler.Compile':
        raise ValueError('School polish requires actual native AllSpark compilation')
    planned = profiles()
    by_name = {r['effect_name']: r for r in proof['records']}
    if set(by_name) != {effect_name(k) for k in planned}:
        raise ValueError('School polish receipt must cover precisely the current authoring plan')
    prepared = {}
    # Validate ALL assets before writing registrations.
    for key, profile in planned.items():
        editor, binary = paths(key)
        row = by_name[effect_name(key)]
        if (not row.get('semantic_roundtrip_verified') or row.get('binary_version') != 7
                or not (source / editor).is_file() or not (source / binary).is_file()
                or digest(source / editor) != row['source_sha256'].lower()
                or digest(source / binary) != row['compiled_sha256'].lower()):
            raise ValueError(f'Stale or unverified school polish compilation: {key}')
        meta = _metadata(source / editor, profile['phase'])
        if meta['looping'] != (profile['binding'] == 'status' or attached_until_casted(profile)):
            raise ValueError(f'Unexpected looping lifecycle: {key}')
        prepared[key] = (profile, row, meta, binary)
    root, parent = _document('EffectBank')
    children = ET.SubElement(parent, 'children')
    records = {}
    for key, (profile, row, meta, binary) in prepared.items():
        node = ET.SubElement(children, 'node', id='Resource')
        for field, attr in (('bounds_min', 'BoundsMin'), ('bounds_max', 'BoundsMax'), ('center', 'Center')):
            _attribute(node, attr, 'fvec3', ' '.join(f'{v:g}' for v in meta[field]))
        for field, typ, value in (
            ('CullingDistance', 'float', 0), ('Duration', 'float', meta['duration']),
            ('EffectName', 'FixedString', effect_name(key)), ('ID', 'FixedString', effect_guid(key)),
            ('Initialized', 'bool', True), ('InterruptionMode', 'uint32', 0),
            ('Localized', 'bool', False), ('Looping', 'bool', meta['looping']),
            ('Name', 'LSString', effect_name(key)), ('Radius', 'float', meta['radius']),
            ('SourceFile', 'LSString', binary.as_posix())):
            _attribute(node, field, typ, value)
        if meta['dependencies']:
            deps = ET.SubElement(ET.SubElement(ET.SubElement(node, 'children'), 'node', id='Dependencies'), 'children')
            for dependency in meta['dependencies']:
                _attribute(ET.SubElement(deps, 'node', id='DependentResource'), 'Object', 'FixedString', dependency)
        for offhand in ((False, True) if profile['binding'] == 'cast' else (False,)):
            editor, exported = _mei(key, profile, offhand)
            _write_xml(source / 'Editor/Mods' / FOLDER / 'MultiEffectInfos' / (mei_guid(key, offhand) + '.mei'), editor)
            mei = source / PUBLIC / 'MultiEffectInfos' / (mei_guid(key, offhand) + '.lsx')
            _write_xml(mei, exported)
            _convert(mei)
        record = {**profile, 'effect': effect_guid(key), 'mei': mei_guid(key),
                  'effectName': effect_name(key), 'sourceSHA256': row['source_sha256'].lower(),
                  'compiledSHA256': row['compiled_sha256'].lower(), 'duration': meta['duration']}
        if profile['binding'] == 'cast':
            record['offhandMei'] = mei_guid(key, True)
        if profile['binding'] == 'hit':
            projectile, uuid = _projectile(key, projectile_guid(profile['skill'].split('_')[0]))
            fallback, fallback_uuid = _projectile(key, uuid, pathfind=True)
            for value, identifier in ((projectile, uuid), (fallback, fallback_uuid)):
                path = source / PUBLIC / 'RootTemplates' / (identifier + '.lsx')
                _write_xml(path, value)
                _convert(path)
            record['trajectories'] = uuid + ',' + fallback_uuid
        records[key] = record
    _write_xml(source / BANK, root)
    _convert(source / BANK)
    _write_xml(source / 'Editor/Mods' / FOLDER / 'MultiEffectInfos/Groups' / (GROUP + '.group'),
               ET.Element('Group', UUID=GROUP, OwnerUUID=MODULE_UUID, Name='ESC_SchoolPolish'))
    return {'enabled': True, 'records': records, 'evidenceLayer': 'native-compiled-and-bound',
            'clientVisualTest': 'pending'}


def set_enabled(records):
    global _enabled
    _enabled = dict(records)


def spell_bindings(name, values, records=None):
    available = _enabled if records is None else records
    if not available:
        return {}
    presentation = classify_spell(name, values)
    if presentation.container or presentation.form == 'movement':
        return {}
    key = presentation.key
    token = name.split('_ESC_', 1)[1].removesuffix('_Off')
    if token in ('Counter2', 'Counter3'):
        key = 'taixuan_qinghui' if token == 'Counter2' else 'taixuan_xinghe'
    roles = {r['binding']: r for r in available.values() if r['skill'] == key}
    result = {}
    if not presentation.internal and 'cast' in roles:
        if attached_until_casted(roles['cast']):
            result['CastEffect'] = ''  # One runtime handle owns the whole Rush.
        else:
            result['CastEffect'] = roles['cast']['offhandMei'] if values.get('CastTextEvent') == 'CastOffhand' else roles['cast']['mei']
        if key == 'xueyan_huichao':
            # Both cost options inherit HealingWord. Its blue preparation spiral
            # obscures the authored red recovery flow and is not this skill's cue.
            result['PrepareEffect'] = ''
        # Self support has one branch release instead of inherited foreign effects.
        if 'hit' not in roles or 'DealDamage(' not in ';'.join(str(values.get(f, '')) for f in ('SpellSuccess', 'SpellProperties')):
            result.update(TargetEffect='', TargetHitEffect='', HitEffect='')
    execution = ';'.join(str(values.get(f, '')) for f in ('SpellSuccess', 'SpellProperties', 'SpellFail'))
    if 'hit' in roles and 'DealDamage(' in execution:
        if presentation.internal:
            # Native helper animation parents also carry prepare/cast effects.
            # Explicit empties prevent a full release per segment or victim.
            result.update(PrepareEffect='', CastEffect='')
        if presentation.form == 'ranged':
            result['Trajectories'] = roles['hit']['trajectories']
            result.update(HitEffect='', TargetEffect='', TargetHitEffect='')
        else:
            result.update(HitEffect=roles['hit']['mei'], TargetEffect='', TargetHitEffect='')
    # Assistance belongs to its selected recipient. Event-only marks/transfers
    # are played by Runtime after the real event, never by a generic cast.
    if (not presentation.internal and key in ('xingge_huifeng', 'xingge_fuchen',
            'xingge_chengfeng', 'xingge_xiangfu') and 'target' in roles):
        result.update(PrepareEffect='', CastEffect='', HitEffect='', TargetHitEffect='',
                      TargetEffect=roles['target']['mei'])
    if (not presentation.internal and key in ('xingge_fengyu', 'xingge_zhangjian')
            and 'status' in roles):
        # Their actual recipients own the persistent sword nodes. SELF_UTILITY
        # supplies ActionSurge effects before this override; its release burst
        # and screen effects obscure those nodes. Keep the gesture and sounds.
        result.update(PrepareEffect='', CastEffect='', TargetEffect='', TargetHitEffect='',
                      TargetGroundEffect='', PositionEffect='', HitEffect='', ImpactEffect='',
                      PreviewEffect='', BeamEffect='', SpellEffect='')
    return result


def status_bindings(name, records=None):
    available = _enabled if records is None else records
    key = STATUS_SKILLS.get(name)
    row = next((r for r in available.values() if r['skill'] == key and r['binding'] == 'status'), None)
    return {'StatusEffect': row['mei']} if row else {}
