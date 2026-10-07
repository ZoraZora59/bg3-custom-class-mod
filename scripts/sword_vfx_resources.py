"""Register compiled sword effects with the verified native BG3 resource schemas.

This module has no import-time writes and never compiles .lsefx files. AllSpark
must produce a non-empty .lsfx before that effect can receive a bank entry or MEI.
An optional installed Data directory is read-only: compiled effects found there
are copied into source_root before registration. XML schemas are embedded here;
ignored build/reference files are not required to reproduce these resources.

Schemas checked against the installed Shared.pak on 2026-10-07:
  Content/Assets/Effects/Effects/[PAK]_Projectiles/_merged.lsf (EffectBank),
  MultiEffectInfos/1d808499-eac9-408a-b5c8-219bb4f52bdc.lsf (exported MEI),
  RootTemplates/_merged.lsf / 348013df-7958-4ca9-ac9f-80337e054bee.
Editor MEI/group schemas were checked against the matching Toolkit Data files.

Official workflow and constraints:
https://docs.baldursgate3.game/VFX_%E2%80%93_Part_1:_Making_Effects
https://docs.baldursgate3.game/VFX_%E2%80%93_Part_2:_Creating_Resources
https://docs.baldursgate3.game/VFX_%E2%80%93_Part_3:_Assigning_and_Testing_Effects
https://docs.baldursgate3.game/index.php?title=VFX_%E2%80%93_Part_4:_Advanced_Information

Cast MEIs deliberately omit StartTextKey. Native MEIs contain such immediate
items, and a specific VFX_Slash_Cast_01 key would exclude generic cast animations.
Projectile spawning is still controlled by each spell's matching CastTextEvent.
Projectile motion copies Magic Missile's explicit base parameters, including
its omitted/default RotateMode. Confirm Follow and sword orientation in Toolkit
before claiming visual validation. A fixed mesh is not the equipped sword.
Each primary trajectory also has a Pathfind child, preserving Magic Missile's
native fallback when the primary Bezier3 path cannot reach the target.
Root templates are exported to LSF as well as retaining editable LSX. The first
Toolkit GameMode probe rejected an LSX-only primary as an invalid trajectory;
successful resource conversion alone does not prove runtime template loading.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from collections.abc import Iterable

from sword_cultivator_spec import FOLDER, MODULE_UUID, guid
from sword_vfx_bindings import projectile_pathfind_guid, projectile_trajectories

STYLES = ('common', 'taixuan', 'tianqing', 'xueyan', 'xingge')
PHASES = ('prepare', 'cast', 'impact', 'status', 'projectile')
REPO = Path(__file__).resolve().parents[1]
REFERENCE_PROJECTILE = '348013df-7958-4ca9-ac9f-80337e054bee'
BANK_RELATIVE = Path('Public') / FOLDER / 'Content/Assets/Effects/Effects/Sword/[PAK]_ESC_SwordEffects/_merged'
GROUP_UUID = guid('vfx/mei/group')
ZERO = '00000000-0000-0000-0000-000000000000'
_GUID_REFERENCE = re.compile(r'<([0-9a-fA-F-]{36})>')
_SPHERE_CENTER = 'c1115291-39d1-43a2-8259-31c2ef4dbd93'
_SPHERE_RADIUS = 'ba2ee0f9-d369-4d36-bd63-30d4c8c46a0a'


def effect_name(style: str, phase: str) -> str:
    return f'VFX_ESC_{style.title()}_{phase.title()}_01'


def effect_path(style: str, phase: str) -> Path:
    return Path('Public') / FOLDER / 'Assets/Effects/Effects_Banks/Sword' / (effect_name(style, phase) + '.lsfx')


def editor_path(style: str, phase: str) -> Path:
    return Path('Editor/Mods') / FOLDER / 'Assets/Effects/Sword' / (effect_name(style, phase) + '.lsefx')


def _attribute(node: ET.Element, name: str, typ: str, value: object) -> None:
    value = str(value).title() if isinstance(value, bool) else str(value)
    ET.SubElement(node, 'attribute', id=name, type=typ, value=value)


def _document(region: str) -> tuple[ET.Element, ET.Element]:
    root = ET.Element('save')
    ET.SubElement(root, 'version', major='4', minor='0', revision='9', build='0')
    node = ET.SubElement(ET.SubElement(root, 'region', id=region), 'node', id=region)
    return root, node


def _write_xml(path: Path, root: ET.Element) -> None:
    ET.indent(root, space='    ')
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = ET.tostring(root, encoding='unicode', xml_declaration=False)
    path.write_text('<?xml version="1.0" encoding="utf-8"?>\n' + payload + '\n', encoding='utf-8', newline='\n')


def _convert(path: Path) -> Path:
    bundled = REPO / 'build/tools/LSLib-1.20.4/Packed/Tools/Divine.exe'
    executable = str(bundled) if bundled.is_file() else shutil.which('Divine.exe')
    if not executable:
        raise FileNotFoundError('Divine.exe is required to export native VFX resource LSF files.')
    output = path.with_suffix('.lsf')
    result = subprocess.run(
        [executable, '-g', 'bg3', '-a', 'convert-resource', '-s', str(path.resolve()), '-d', str(output.resolve())],
        capture_output=True, text=True, encoding='utf-8', errors='replace', check=False,
    )
    if result.returncode or not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f'VFX export failed for {path}: {result.stdout}\n{result.stderr}')
    return output


def _metadata(source: Path | None, phase: str) -> dict:
    # Conservative registration bounds are explicitly reported when the editable
    # source is unavailable. They do not replace its AllSpark bounding component.
    result = dict(duration=1.2, looping=phase in ('prepare', 'status', 'projectile'),
                  bounds_min=(-6.0, -6.0, -6.0), bounds_max=(6.0, 6.0, 6.0),
                  center=(0.0, 0.0, 0.0), radius=math.sqrt(108), dependencies=[],
                  metadata_source='conservative-defaults')
    if source is None:
        return result
    root = ET.parse(source).getroot()
    tracks = root.findall('.//track')
    active = [t.find('component') for t in tracks if t.get('muted', 'False').lower() != 'true']
    active = [c for c in active if c is not None]
    phases = root.findall('phases/object/data')
    duration = max([0.1, sum(float(p.get('duration', '0')) for p in phases)] +
                   [float(c.get('end', '0')) for c in active])
    spheres = []
    dependencies = set()
    for component in active:
        for datum in component.findall('.//datum'):
            dependencies.update(_GUID_REFERENCE.findall(datum.get('value', '')))
        if component.get('class') != 'BoundingSphere':
            continue
        values = {p.get('id'): p.find('data/datum').get('value')
                  for p in component.findall('properties/property')
                  if p.find('data/datum') is not None and p.find('data/datum').get('value') is not None}
        if _SPHERE_RADIUS not in values or _SPHERE_CENTER not in values:
            continue
        radius = float(values[_SPHERE_RADIUS])
        center = tuple(float(v) for v in values[_SPHERE_CENTER].split(','))
        if len(center) != 3 or not math.isfinite(radius) or radius <= 0:
            raise ValueError(f'Invalid effect bounding sphere in {source}')
        if float(component.get('start', '0')) > 1e-6 or float(component.get('end', '0')) + 1e-6 < duration:
            raise ValueError(f'BoundingSphere does not cover the effect lifecycle: {source}')
        spheres.append((center, radius))
    result.update(duration=duration, looping=any(p.get('playcount') == '-1' for p in phases),
                  dependencies=sorted(dependencies - {ZERO}))
    if spheres:
        low = tuple(min(c[i] - r for c, r in spheres) for i in range(3))
        high = tuple(max(c[i] + r for c, r in spheres) for i in range(3))
        center = tuple((lo + hi) / 2 for lo, hi in zip(low, high))
        result.update(bounds_min=low, bounds_max=high, center=center,
                      radius=math.sqrt(sum(((hi - lo) / 2) ** 2 for lo, hi in zip(low, high))),
                      metadata_source='editor-source')
    elif not any(c.get('class') == 'BoundingBox' for c in active):
        raise ValueError(f'Effect has no unmuted BoundingSphere or BoundingBox: {source}')
    return result


def _effect_resource(children: ET.Element, style: str, phase: str, meta: dict) -> None:
    node = ET.SubElement(children, 'node', id='Resource')
    for key, values in (('BoundsMin', meta['bounds_min']), ('BoundsMax', meta['bounds_max']), ('Center', meta['center'])):
        _attribute(node, key, 'fvec3', ' '.join(f'{v:g}' for v in values))
    for key, typ, value in (
        ('CullingDistance', 'float', 0), ('Duration', 'float', meta['duration']),
        ('EffectName', 'FixedString', effect_name(style, phase)),
        ('ID', 'FixedString', guid(f'vfx/effect/{style}/{phase}')),
        ('Initialized', 'bool', True), ('InterruptionMode', 'uint32', 0),
        ('Localized', 'bool', False), ('Looping', 'bool', meta['looping']),
        ('Name', 'LSString', effect_name(style, phase)), ('Radius', 'float', meta['radius']),
        ('SourceFile', 'LSString', effect_path(style, phase).as_posix()),
    ):
        _attribute(node, key, typ, value)
    if meta['dependencies']:
        deps = ET.SubElement(ET.SubElement(ET.SubElement(node, 'children'), 'node', id='Dependencies'), 'children')
        for dependency in meta['dependencies']:
            _attribute(ET.SubElement(deps, 'node', id='DependentResource'), 'Object', 'FixedString', dependency)


def _mei(style: str, phase: str) -> tuple[ET.Element, ET.Element]:
    name = f'ESC_{style.title()}_{phase.title()}'
    bone = 'Dummy_BodyFX' if phase == 'impact' else 'Dummy_Root'
    fields = dict(UUID=guid(f'vfx/mei/{style}/{phase}/item'),
                  EffectResourceGuid=guid(f'vfx/effect/{style}/{phase}'),
                  DetachSource=phase == 'impact', DetachTarget=phase == 'impact',
                  KeepRotation=False, UseOrientDirection=False, UseDistance=False,
                  UseScaleOverride=False, KeepScale=True, MainHand=False, OffHand=False,
                  MinDistance=0, MaxDistance=0, BindSourceTo='SourceEntity',
                  BindTargetTo='TargetEntity', Pivot='Target', Enabled=True)
    editor = ET.Element('MultiEffectInfos', UUID=guid(f'vfx/mei/{style}/{phase}'), OwnerUUID=GROUP_UUID, Name=name)
    ET.SubElement(editor, 'EffectInfo', **{k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in fields.items()},
                  DamageType='None', VerbalIntent='None', TargetBone=bone)
    exported, parent = _document('MultiEffectInfos')
    _attribute(parent, 'UUID', 'guid', editor.get('UUID'))
    _attribute(parent, 'Name', 'LSString', name)
    item = ET.SubElement(ET.SubElement(parent, 'children'), 'node', id='EffectInfo')
    for key, value in fields.items():
        typ = 'guid' if key in ('UUID', 'EffectResourceGuid') else 'bool' if isinstance(value, bool) else 'float' if key in ('MinDistance', 'MaxDistance') else 'FixedString'
        _attribute(item, key, typ, value)
    _attribute(item, 'DamageType', 'uint32', 0)
    _attribute(item, 'VerbalIntent', 'uint32', 0)
    _attribute(ET.SubElement(ET.SubElement(item, 'children'), 'node', id='TargetBone'), 'Value', 'LSString', bone)
    return editor, exported


def _projectile(style: str, trail_style: str, impact_style: str) -> ET.Element:
    root, parent = _document('Templates')
    node = ET.SubElement(ET.SubElement(parent, 'children'), 'node', id='GameObjects')
    # Preserve Magic Missile's motion schema. Constant velocity is in m/s:
    # https://docs.baldursgate3.game/Projectiles . The common sword projectile
    # deliberately uses 30 instead of the native 20 after flight-speed feedback.
    # RotateMode was omitted in the native base; Follow still needs UI review.
    speed = 30 if style == 'common' else 20
    values = (
        ('CameraOffset', 'fvec3', '0 0 0'), ('CastBone', 'FixedString', 'Dummy_CastFX'),
        ('Flag', 'int32', 0), ('GroundImpactFX', 'LSString', ''), ('GroupID', 'uint32', 0),
        ('HasGameplayValue', 'bool', False), ('ImpactFX', 'FixedString', effect_name(impact_style, 'impact')),
        ('InitialSpeed', 'float', speed), ('LevelName', 'FixedString', ''),
        ('MapKey', 'FixedString', guid(f'vfx/projectile/{style}')),
        ('Name', 'LSString', effect_name(style, 'projectile') + '_Template'),
        ('OffsetMin_Bezier3', 'fvec2', '0 1.5'), ('ParentTemplateId', 'FixedString', ''),
        ('PathRadius', 'float', 1.5), ('PathShift', 'float', 0.55),
        ('PhysicsOpenTemplate', 'FixedString', ''), ('PhysicsTemplate', 'FixedString', ''),
        ('PreviewPathImpactFX', 'FixedString', 'VFX_UI_DestinationBeam_Projectile_01'),
        ('PreviewPathMaterial', 'FixedString', '312a1494-a0e2-c215-cf51-bda58a6b2341'),
        ('ProjectilePath', 'uint8', 1), ('RotateImpact', 'bool', False), ('Scale', 'float', 1),
        ('ShiftMin_Bezier3', 'float', 0.55), ('Speed', 'float', speed),
        ('TrailFX', 'FixedString', effect_name(trail_style, 'projectile')),
        ('TrajectoryType', 'uint8', 0), ('Type', 'FixedString', 'projectile'),
        ('VelocityMode', 'uint8', 0), ('VisualTemplate', 'FixedString', ZERO),
    )
    for key, typ, value in values:
        _attribute(node, key, typ, value)
    bounds = ET.SubElement(ET.SubElement(ET.SubElement(node, 'children'), 'node', id='Bounds'), 'children')
    for bound_type in (1, 2, 0):
        bound = ET.SubElement(bounds, 'node', id='Bound')
        for key, typ, value in (('Height', 'float', 0), ('IsIgnoringScale', 'bool', False),
                                ('Max', 'fvec3', '0 0 0'), ('Min', 'fvec3', '0 0 0'),
                                ('Radius', 'float', 0), ('Shape', 'uint8', 0), ('Type', 'uint8', bound_type)):
            _attribute(bound, key, typ, value)
    return root


def _pathfind_projectile(style: str) -> ET.Element:
    """Use the native Magic Missile Pathfind child's minimal inheritance schema.

    Native UUID 7bff57fa-fd21-4ab3-9384-83fb14237690 sets TrajectoryType=2
    and inherits its Bezier3 parent 348013df-7958-4ca9-ac9f-80337e054bee.
    The custom child inherits its style's sword trail, impact, and motion.
    """
    root, parent = _document('Templates')
    node = ET.SubElement(ET.SubElement(parent, 'children'), 'node', id='GameObjects')
    for key, typ, value in (
        ('LevelName', 'FixedString', ''),
        ('MapKey', 'FixedString', projectile_pathfind_guid(style)),
        ('Name', 'LSString', effect_name(style, 'projectile') + '_Pathfind_Template'),
        ('ParentTemplateId', 'FixedString', guid(f'vfx/projectile/{style}')),
        ('TrajectoryType', 'uint8', 2), ('Type', 'FixedString', 'projectile'),
    ):
        _attribute(node, key, typ, value)
    return root


def generate_resources(styles: Iterable[str], phases: Iterable[str], source_root: Path | str,
                       data: Path | str | None = None) -> dict:
    """Emit only resources whose compiled effects exist; return binding evidence.

    styles/phases may be sequences or dictionaries (their keys are used).
    All requested styles get distinct Bezier3 and Pathfind Projectile templates
    when both a trail and impact exist. Each may use a compiled common effect;
    the manifest records the actual styles used. Uncompiled phases are skipped.
    Generated bank/MEI/template files from prior calls are removed only within
    this module's known UUID/name set when they are no longer registered.
    """
    styles, phases = tuple(dict.fromkeys(styles)), tuple(dict.fromkeys(phases))
    if not styles or not phases or set(styles) - set(STYLES) or set(phases) - set(PHASES):
        raise ValueError(f'Use styles from {STYLES} and phases from {PHASES}.')
    source_root = Path(source_root).resolve()
    data = Path(data).resolve() if data is not None else None
    if data is not None and source_root == data:
        raise ValueError('data is read-only; source_root must be a separate staging/source directory.')
    manifest = dict(registered={}, projectiles={}, missing_compiled=[], files=[],
                    reference_projectile=REFERENCE_PROJECTILE, rotation_validation='pending Toolkit Follow/orientation review')
    bank, bank_node = _document('EffectBank')
    bank_children = ET.SubElement(bank_node, 'children')
    for style in styles:
        manifest['registered'][style] = {}
        for phase in phases:
            relative = effect_path(style, phase)
            compiled = source_root / relative
            if data is not None:
                candidate = data / relative
                if candidate.is_file() and candidate.stat().st_size and (
                    not compiled.is_file() or compiled.stat().st_size == 0
                    or candidate.stat().st_mtime_ns > compiled.stat().st_mtime_ns
                ):
                    compiled.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(candidate, compiled)
            if not compiled.is_file() or compiled.stat().st_size == 0:
                manifest['missing_compiled'].append(dict(style=style, phase=phase, path=relative.as_posix()))
                continue
            editable = source_root / editor_path(style, phase)
            if data is not None:
                candidate = data / editor_path(style, phase)
                if candidate.is_file() and (
                    not editable.is_file() or candidate.stat().st_mtime_ns > editable.stat().st_mtime_ns
                ):
                    editable.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(candidate, editable)
            meta = _metadata(editable if editable.is_file() else None, phase)
            _effect_resource(bank_children, style, phase, meta)
            editor, exported = _mei(style, phase)
            mei_uuid = guid(f'vfx/mei/{style}/{phase}')
            editor_mei = source_root / 'Editor/Mods' / FOLDER / 'MultiEffectInfos' / (mei_uuid + '.mei')
            public_mei = source_root / 'Public' / FOLDER / 'MultiEffectInfos' / (mei_uuid + '.lsx')
            _write_xml(editor_mei, editor)
            _write_xml(public_mei, exported)
            exported_lsf = _convert(public_mei)
            manifest['files'].extend(str(p.relative_to(source_root).as_posix()) for p in (compiled, editor_mei, public_mei, exported_lsf))
            manifest['registered'][style][phase] = dict(effect=guid(f'vfx/effect/{style}/{phase}'), mei=mei_uuid,
                                                       name=effect_name(style, phase), **meta)
    if any(manifest['registered'].values()):
        group = ET.Element('Group', UUID=GROUP_UUID, OwnerUUID=MODULE_UUID, Name='ESC_Sword')
        group_path = source_root / 'Editor/Mods' / FOLDER / 'MultiEffectInfos/Groups' / (GROUP_UUID + '.group')
        _write_xml(group_path, group)
        bank_path = (source_root / BANK_RELATIVE).with_suffix('.lsx')
        _write_xml(bank_path, bank)
        manifest['files'].extend(p.relative_to(source_root).as_posix() for p in (group_path, bank_path, _convert(bank_path)))
    for style in styles:
        choices = {}
        for phase in ('projectile', 'impact'):
            choices[phase] = next((s for s in (style, 'common') if phase in manifest['registered'].get(s, {})), None)
        if all(choices.values()):
            template = source_root / 'Public' / FOLDER / 'RootTemplates' / (guid(f'vfx/projectile/{style}') + '.lsx')
            _write_xml(template, _projectile(style, choices['projectile'], choices['impact']))
            pathfind = template.with_name(projectile_pathfind_guid(style) + '.lsx')
            _write_xml(pathfind, _pathfind_projectile(style))
            template_lsf, pathfind_lsf = _convert(template), _convert(pathfind)
            manifest['files'].extend(p.relative_to(source_root).as_posix()
                                     for p in (template, template_lsf, pathfind, pathfind_lsf))
            manifest['projectiles'][style] = dict(uuid=guid(f'vfx/projectile/{style}'),
                                                 pathfind_uuid=projectile_pathfind_guid(style),
                                                 trajectories=projectile_trajectories(style), **choices)
    # Remove only this generator's own stale registrations, never effects or
    # editable files. Other mods and arbitrary UUIDs are outside this list.
    retained = set(manifest['files'])
    managed = [(source_root / BANK_RELATIVE).with_suffix(ext) for ext in ('.lsx', '.lsf')]
    managed += [source_root / 'Editor/Mods' / FOLDER / 'MultiEffectInfos/Groups' / (GROUP_UUID + '.group')]
    for style in STYLES:
        for root_uuid in (guid(f'vfx/projectile/{style}'), projectile_pathfind_guid(style)):
            managed.extend(source_root / 'Public' / FOLDER / 'RootTemplates' / (root_uuid + ext)
                           for ext in ('.lsx', '.lsf'))
        for phase in PHASES:
            mei_uuid = guid(f'vfx/mei/{style}/{phase}')
            managed.append(source_root / 'Editor/Mods' / FOLDER / 'MultiEffectInfos' / (mei_uuid + '.mei'))
            managed.extend(source_root / 'Public' / FOLDER / 'MultiEffectInfos' / (mei_uuid + ext) for ext in ('.lsx', '.lsf'))
    for path in managed:
        if path.relative_to(source_root).as_posix() not in retained and path.is_file():
            path.unlink()
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--styles', nargs='+', choices=STYLES, default=list(STYLES))
    parser.add_argument('--phases', nargs='+', choices=PHASES, default=list(PHASES))
    parser.add_argument('--source', type=Path, required=True, help='Separate Source/staging root; never the installed Data root.')
    parser.add_argument('--data', type=Path, help='Read-only installed Data root containing AllSpark compiled effects.')
    args = parser.parse_args()
    result = generate_resources(args.styles, args.phases, args.source, args.data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
