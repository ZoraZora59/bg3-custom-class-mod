"""Read-only BG3 effect/MEI/animation catalogue and source binding audit.

No Toolkit automation, game writes, package extraction, or runtime claims.
Only the requested output JSON files are written. Packed vanilla resources are
reported as unverified when no exported LSX was supplied, never as absent.

Examples (run with ``python -X utf8`` on Windows)::

    python scripts/sword-vfx-catalog.py build
    python scripts/sword-vfx-catalog.py query BladeFlourish --kind sources
    python scripts/sword-vfx-catalog.py inspect VFX_Projectiles_Force_MagicMissile_Projectile_01
    python scripts/sword-vfx-catalog.py check

Official references consulted before implementing the observed XML readers:
https://docs.baldursgate3.game/VFX_%E2%80%93_Part_1:_Making_Effects
https://docs.baldursgate3.game/VFX_%E2%80%93_Part_2:_Creating_Resources
https://docs.baldursgate3.game/VFX_%E2%80%93_Part_3:_Assigning_and_Testing_Effects
https://docs.baldursgate3.game/VFX_%E2%80%93_Part_4:_Advanced_Information
https://docs.baldursgate3.game/Projectiles
https://docs.baldursgate3.game/Creating_Shortnames

The source ``effect/@id`` is NOT its Resource Manager GUID. Properties and
modules in .lsefx use opaque GUIDs; this tool intentionally does not guess
their color/shape/timing meanings. ``inspect`` exposes exact XML values and
curves for comparison with AllSpark, including muted preview-only tracks.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


REPO = Path(__file__).resolve().parents[1]
DEFAULT_DATA = Path('E:/SteamLibrary/steamapps/common/Baldurs Gate 3/Data')
DEFAULT_SOURCE = REPO / 'mods/EasternSwordCultivator/Source'
DEFAULT_OUTPUT = REPO / 'build/sword-cultivator/vfx/catalog.json'
GUID = re.compile(r'[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}')
RESOURCE_LABEL = re.compile(r'^(.*?)\s*<(' + GUID.pattern + r')>$')
ZERO = '00000000-0000-0000-0000-000000000000'
MEI_FIELDS = {
    'UUID', 'EffectResourceGuid', 'Enabled', 'StartTextKey', 'EndTextKey',
    'SourceBone', 'TargetBone', 'SourceBones', 'TargetBones', 'Pivot',
    'DetachSource', 'DetachTarget', 'UseDistance', 'HardAttach',
    'MainHand', 'OffHand', 'SourceSkeletonSlot', 'TargetSkeletonSlot',
}
EFFECT_FIELDS = {
    'PrepareEffect', 'CastEffect', 'TargetEffect', 'TargetHitEffect',
    'TargetGroundEffect', 'PositionEffect', 'HitEffect', 'ImpactEffect',
    'PreviewEffect', 'BeamEffect', 'SpellEffect', 'StatusEffect',
    'ApplyEffect', 'EndEffect',
}
STAT_FIELDS = EFFECT_FIELDS | {
    'SpellAnimation', 'DualWieldingSpellAnimation', 'CastTextEvent',
    'AlternativeCastTextEvents', 'Trajectories', 'SpellType',
}
PROJECTILE_EFFECT_FIELDS = {
    'TrailEffect', 'ImpactEffect', 'GroundImpactEffect', 'BeamEffect',
    'TrailEffectID', 'ImpactEffectID', 'GroundImpactEffectID', 'BeamEffectID',
}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n',
                    encoding='utf-8')


def print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def paths(root: Path, pattern: str):
    return sorted(root.rglob(pattern)) if root.is_dir() else []


def attrs(node: ET.Element) -> dict[str, str]:
    return {a.get('id', ''): a.get('value', '') for a in node.findall('attribute')}


def number(value: str | None) -> float:
    try:
        return float(value or 0)
    except ValueError:
        return 0.0


def is_muted(track: ET.Element) -> bool:
    # mutestateoverride controls preview visualization. The persisted muted
    # boolean controls export, per Part 1. Do not mistake Unmuted for export.
    return track.get('muted', '').lower() == 'true'


def source_summary(path: Path) -> dict:
    root = ET.parse(path).getroot()
    if root.tag != 'effect':
        raise ValueError('Expected <effect>, found <' + root.tag + '>.')
    live = [c for t in root.findall('.//track') if not is_muted(t)
            for c in t.findall('component')]
    phases = root.findall('./phases/object/data')
    bounds = [c for c in live if c.get('class') in {'BoundingSphere', 'BoundingBox'}]
    begin = min((number(c.get('start')) for c in live), default=0)
    end = max((number(c.get('end')) for c in live), default=0)
    # Timeline interval coverage is structural only. It cannot establish that
    # radius/box dimensions encompass emitted particles or their tails.
    covered_until = begin
    for component in sorted(bounds, key=lambda c: number(c.get('start'))):
        if number(component.get('start')) > covered_until + 0.0001:
            break
        covered_until = max(covered_until, number(component.get('end')))
    return {
        'name': path.stem, 'bytes': path.stat().st_size, 'format': 'xml',
        'classes': dict(sorted(Counter(c.get('class', '') for c in live).items())),
        'muted_tracks': sum(is_muted(t) for t in root.findall('.//track')),
        'duration': round(end - begin, 6),
        'phase_durations': [number(p.get('duration')) for p in phases],
        'loop': any(p.get('playcount') == '-1' for p in phases),
        'bounding_timeline_covered': bool(bounds) and covered_until + 0.0001 >= end,
    }


def mei_summary(path: Path) -> dict:
    root = ET.parse(path).getroot()
    if root.tag != 'MultiEffectInfos':
        raise ValueError('Expected <MultiEffectInfos>.')
    return {
        'name': root.get('Name', path.stem), 'uuid': root.get('UUID', ''),
        'effects': [{k: v for k, v in item.attrib.items() if k in MEI_FIELDS}
                    for item in root.findall('EffectInfo')],
    }


def shortnames(path: Path) -> list[dict]:
    root = ET.parse(path).getroot()
    result = []
    for node in root.findall('.//stat_object'):
        row = {a.get('name'): a.get('value') for a in node.findall('fields/field')}
        if row.get('UUID') and row.get('Name'):
            result.append({'uuid': row['UUID'], 'name': row['Name'],
                           'category': row.get('Category', '')})
    return result


def stats(path: Path) -> list[dict]:
    result = []
    row = None
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        entry = re.fullmatch(r'\s*new entry "([^"]+)"\s*', line)
        if entry:
            row = {'name': entry[1], 'fields': {}}
            result.append(row)
        elif row is not None:
            parent = re.fullmatch(r'\s*using "([^"]+)"\s*', line)
            data = re.fullmatch(r'\s*data "([^"]+)" "(.*)"\s*', line)
            if parent:
                row['parent'] = parent[1]
            elif data and data[1] in STAT_FIELDS:
                row['fields'][data[1]] = data[2]
    return result


def read_lsx(path: Path) -> tuple[list[dict], list[dict]]:
    root = ET.parse(path).getroot()
    resources, templates = [], []
    for region in root.findall('region'):
        bank = region.get('id', '')
        for node in region.findall('.//node'):
            values = attrs(node)
            if node.get('id') == 'Resource' and values.get('ID'):
                resources.append({'uuid': values['ID'], 'name': values.get('Name', ''),
                                  'bank': bank, 'source_file': values.get('SourceFile', ''),
                                  'attributes': {k: v for k, v in values.items()
                                                 if k in {'AnimationName', 'AnimationType'}}})
            elif values.get('MapKey') and (values.get('Type') or values.get('Name')):
                # Projectile settings may be stored in a child node rather
                # than on GameObjects itself. Read only the relevant fields.
                values.update({a.get('id'): a.get('value', '') for a in node.findall('.//attribute')
                               if a.get('id') in PROJECTILE_EFFECT_FIELDS | {
                                   'CastBone', 'CastBoneName', 'TrajectoryType',
                                   'RotationMode', 'VelocityMode', 'InitialSpeed', 'Acceleration'}})
                templates.append({'uuid': values['MapKey'], 'name': values.get('Name', ''),
                                  'type': values.get('Type', ''), 'attributes': values})
    return resources, templates


def make_catalog(args) -> dict:
    data = args.data_root.resolve()
    mod = args.mod_source.resolve()
    roots = {'data': str(data), 'mod_source': str(mod)}
    public_roots = [data / 'Public', mod / 'Public'] + args.public_root
    reference = REPO / 'build/sword-reference/Public'
    if reference.is_dir() and reference not in public_roots:
        public_roots.append(reference)
    sources, meis, names, resources, templates, own_stats, external_stats = [], [], [], [], [], [], {}
    errors, unsupported = [], []

    def tagged(item: dict, path: Path, location: str, module: str) -> dict:
        return dict(item, location=location, module=module,
                    path=path.relative_to(Path(roots[location])).as_posix())

    def read(reader, path: Path, location: str, module: str, destination: list):
        try:
            result = reader(path)
            result = result if isinstance(result, list) else [result]
            destination.extend(tagged(item, path, location, module) for item in result)
        except (OSError, ET.ParseError, ValueError) as exc:
            errors.append({'path': str(path), 'error': str(exc)})

    modules = [(data / 'Editor/Mods' / m, 'data', m) for m in args.modules]
    modules += [(p, 'mod_source', p.name) for p in sorted((mod / 'Editor/Mods').glob('*'))
                if p.is_dir()]
    for module_path, location, module in modules:
        for path in paths(module_path / 'Assets/Effects', '*.lsefx'):
            read(source_summary, path, location, module, sources)
        for path in paths(module_path / 'MultiEffectInfos', '*.mei'):
            read(mei_summary, path, location, module, meis)
        for path in paths(module_path / 'Animation', 'ShortNames.tbl'):
            read(shortnames, path, location, module, names)

    for index, public in enumerate(dict.fromkeys(p.resolve() for p in public_roots)):
        location = 'public' + str(index)
        roots[location] = str(public)
        if not public.is_dir():
            continue
        module_paths = [p for p in public.iterdir() if p.is_dir()]
        # --public-root also accepts a single module directory.
        if (public / 'Content').is_dir() or (public / 'RootTemplates').is_dir():
            module_paths = [public]
        for module_path in sorted(module_paths):
            module = module_path.name
            own = module_path.is_relative_to(mod)
            for folder in ('Content', 'RootTemplates'):
                for path in paths(module_path / folder, '*.lsx'):
                    try:
                        r, t = read_lsx(path)
                        resources.extend(tagged(v, path, location, module) for v in r)
                        templates.extend(tagged(v, path, location, module) for v in t)
                    except (OSError, ET.ParseError, ValueError) as exc:
                        errors.append({'path': str(path), 'error': str(exc)})
                for pattern in ('*.lsf', '*.lsb'):
                    unsupported.extend(str(p) for p in paths(module_path / folder, pattern))
            # Public MEI exports, when present, are LSX wrappers and are not
            # inferred to use the editor .mei schema. Scan editor .mei instead.
            for path in paths(module_path / 'Stats/Generated/Data', '*.txt'):
                if not (own or path.name.startswith(('Spell_', 'Status_'))):
                    continue
                records = []
                read(stats, path, location, module, records)
                if own:
                    own_stats.extend(records)
                else:
                    external_stats.update((r['name'], r) for r in records)

    # Keep only reference parent chains needed by the mod, not all vanilla stats.
    parent_names = {r.get('parent') for r in own_stats}
    reference_stats = []
    visited = {r['name'] for r in own_stats}
    while parent_names:
        name = parent_names.pop()
        if not name or name in visited:
            continue
        visited.add(name)
        if name in external_stats:
            row = external_stats[name]
            reference_stats.append(row)
            parent_names.add(row.get('parent'))
    catalog = {
        'schema_version': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'read_only_static_catalog; no compilation or runtime verification',
        'roots': roots, 'sources': sources, 'meis': meis, 'shortnames': names,
        'resources': resources, 'templates': templates, 'stats': own_stats,
        'reference_stats': sorted(reference_stats, key=lambda r: r['name']),
        'parse_errors': errors, 'unread_binary_metadata': unsupported,
        'packed_resource_boundary': 'PAK contents are not read. Supply extracted Content/RootTemplates LSX via --public-root.',
    }
    return catalog


def item_path(catalog: dict, item: dict) -> Path:
    return Path(catalog['roots'][item['location']]) / item['path']


def check_catalog(catalog: dict) -> dict:
    own = Path(catalog['roots']['mod_source'])
    data = Path(catalog['roots']['data'])
    meis = {r['uuid'].lower(): r for r in catalog['meis']}
    resources = {r['uuid'].lower(): r for r in catalog['resources']}
    templates = {r['uuid'].lower(): r for r in catalog['templates']}
    shorts = {r['uuid'].lower(): r for r in catalog['shortnames']}
    stat_map = {r['name']: r for r in catalog['reference_stats'] + catalog['stats']}
    issues, bindings, compiles = [], [], []

    def issue(level, code, **values):
        issues.append(dict(level=level, code=code, **values))

    def effective(name: str, chain=()):
        if name in chain:
            issue('error', 'stats_parent_cycle', name=name, chain=list(chain))
            return {}, {}
        row = stat_map.get(name)
        if not row:
            return {}, {}
        values, owners = effective(row.get('parent', ''), chain + (name,)) if row.get('parent') else ({}, {})
        values.update(row['fields'])
        owners.update({k: name for k in row['fields']})
        return values, owners

    def binding(owner, field, value, target, inherited_from=None):
        ids = GUID.findall(value)
        if value and not ids:
            issue('warning', 'non_guid_binding', owner=owner, field=field, value=value)
        for uid in ids:
            found = target.get(uid.lower())
            bindings.append({'owner': owner, 'field': field, 'uuid': uid,
                             'resolved': bool(found), 'target_name': found.get('name') if found else None,
                             'inherited_from': inherited_from})
            if not found:
                issue('unverified', 'not_in_scanned_' + ('meis' if target is meis else 'templates' if target is templates else 'shortnames'),
                      owner=owner, field=field, uuid=uid)

    for row in catalog['stats']:
        values, owners = effective(row['name'])
        for field in EFFECT_FIELDS:
            if values.get(field):
                binding(row['name'], field, values[field], meis, owners[field])
        if values.get('Trajectories'):
            if 'rules:' in values['Trajectories']:
                issue('unverified', 'trajectory_rules_not_indexed', owner=row['name'], value=values['Trajectories'])
            else:
                binding(row['name'], 'Trajectories', values['Trajectories'], templates, owners['Trajectories'])
        for field in ('SpellAnimation', 'DualWieldingSpellAnimation'):
            if values.get(field):
                binding(row['name'], field, values[field], shorts, owners[field])
        if values.get('SpellAnimation') and not values.get('CastTextEvent') and values.get('SpellType') in {'Projectile', 'Target', 'Zone', 'Rush'}:
            issue('warning', 'animation_without_cast_text_event', owner=row['name'])

    used_meis = {r['uuid'].lower() for r in bindings if r['field'] in EFFECT_FIELDS}
    for mei in catalog['meis']:
        if mei['uuid'].lower() not in used_meis and mei['location'] != 'mod_source':
            continue
        if mei['location'] == 'mod_source' and not mei['effects']:
            issue('warning', 'empty_mod_mei', name=mei['name'], uuid=mei['uuid'])
        for item in mei['effects']:
            if item.get('Enabled', 'true').lower() == 'false':
                continue
            uid = item.get('EffectResourceGuid', '')
            if not GUID.fullmatch(uid) or uid == ZERO:
                issue('error', 'invalid_mei_effect_resource_guid', mei=mei['name'], value=uid)
            elif uid.lower() not in resources:
                issue('unverified', 'effect_resource_not_in_exported_lsx', mei=mei['name'], uuid=uid,
                      boundary='May be inside vanilla PAK; this does not establish absence.')

    source_files = {}
    for resource in catalog['resources']:
        if resource['bank'] != 'EffectBank':
            continue
        source = resource['source_file'].replace('\\', '/')
        source_files.setdefault(source.casefold(), []).append(resource)
        if resource['name'] != Path(source).stem:
            issue('error', 'effect_resource_name_file_mismatch', resource=resource['name'], source_file=source)
        if item_path(catalog, resource).is_relative_to(own):
            alternatives = [own / source, data / source]
            if not any(p.is_file() for p in alternatives):
                issue('error', 'mod_effect_compiled_file_missing', resource=resource['name'], source_file=source)
    for source, records in source_files.items():
        if len({r['uuid'] for r in records}) > 1:
            issue('error', 'multiple_effect_resources_same_source', source_file=source,
                  uuids=sorted({r['uuid'] for r in records}))

    for source in catalog['sources']:
        if source['location'] != 'mod_source':
            continue
        path = item_path(catalog, source)
        effect_root = own / 'Editor/Mods' / source['module'] / 'Assets/Effects'
        relative = path.relative_to(effect_root).with_suffix('.lsfx')
        expected = Path('Public') / source['module'] / 'Assets/Effects/Effects_Banks' / relative
        candidates = [own / expected, data / expected]
        compiled = next((p for p in candidates if p.is_file()), None)
        status = 'missing' if compiled is None else ('source_newer_than_binary' if path.stat().st_mtime_ns > compiled.stat().st_mtime_ns else 'present_unverified')
        registrations = [r['uuid'] for r in catalog['resources']
                         if r['bank'] == 'EffectBank' and r['name'] == source['name']]
        compiles.append({'source': str(path), 'expected_compiled': expected.as_posix(),
                         'compiled': str(compiled) if compiled else None, 'status': status,
                         'registered_resource_uuids': sorted(set(registrations))})
        if compiled is None:
            issue('error', 'mod_source_not_compiled', name=source['name'], expected=expected.as_posix())
        elif status == 'source_newer_than_binary':
            issue('warning', 'compile_may_be_stale', name=source['name'])
        if not registrations:
            issue('unverified', 'mod_source_without_readable_effect_resource_registration',
                  name=source['name'], boundary='Registration may be stored in binary LSF metadata; supply exported LSX.')
        if not source['bounding_timeline_covered']:
            issue('warning', 'mod_bounding_timeline_not_covered', name=source['name'],
                  boundary='Structural interval only; inspect emitter tails and volume in AllSpark.')

    for template in catalog['templates']:
        if not item_path(catalog, template).is_relative_to(own):
            continue
        for field in PROJECTILE_EFFECT_FIELDS:
            uid = template['attributes'].get(field)
            if uid and uid != ZERO and uid.lower() not in resources:
                issue('unverified', 'projectile_effect_resource_not_in_exported_lsx',
                      template=template['name'], field=field, uuid=uid)
    for parse_error in catalog['parse_errors']:
        if Path(parse_error['path']).is_relative_to(own):
            issue('error', 'mod_xml_parse_error', **parse_error)
    return {
        'scope': 'static only; presence does not verify compilation or playback',
        'counts': {k: len(catalog[k]) for k in ('sources', 'meis', 'shortnames', 'resources', 'templates', 'stats', 'reference_stats')},
        'issue_counts': dict(Counter(i['level'] for i in issues)),
        'source_compile_correspondence': compiles, 'bindings': bindings, 'issues': issues,
        'parse_errors': catalog['parse_errors'],
    }


def inspect_source(path: Path) -> dict:
    root = ET.parse(path).getroot()
    components = []
    for track in root.findall('.//track'):
        for component in track.findall('component'):
            properties, referenced = [], []
            for prop in component.findall('properties/property'):
                values = [d.get('value') for d in prop.findall('data/datum') if d.get('value') is not None]
                curves = [{'type': channel.get('type'), 'selected': channel.get('selected'),
                           'keys': [k.attrib for k in channel.findall('keyframes/keyframe')]}
                          for channel in prop.findall('.//rampchannel')]
                for value in values:
                    match = RESOURCE_LABEL.fullmatch(value)
                    if match:
                        referenced.append({'name': match[1], 'uuid': match[2], 'property_guid': prop.get('id')})
                properties.append({'guid': prop.get('id'), 'values': values, 'curves': curves})
            components.append(dict(component.attrib, track_name=track.get('name'),
                                   export_muted=is_muted(track), properties=properties,
                                   resource_references=referenced,
                                   modules=[m.attrib for m in component.findall('modules/module')]))
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'root_attributes': root.attrib, 'summary': source_summary(path),
            'components': components}


def load(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit('Catalogue is missing; run build first: ' + str(path))
    return json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    build = sub.add_parser('build', help='Index readable local sources and write catalogue + audit JSON.')
    build.add_argument('--data-root', type=Path, default=DEFAULT_DATA)
    build.add_argument('--mod-source', type=Path, default=DEFAULT_SOURCE)
    build.add_argument('--modules', nargs='+', default=['Shared', 'SharedDev'])
    build.add_argument('--public-root', type=Path, action='append', default=[], help='Optional unpacked Public or single module directory containing LSX.')
    build.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    query = sub.add_parser('query', help='Search names, GUIDs, paths, bones, and events.')
    query.add_argument('text')
    query.add_argument('--kind', choices=['sources', 'meis', 'shortnames', 'resources', 'templates', 'stats', 'all'], default='all')
    query.add_argument('--limit', type=int, default=20)
    query.add_argument('--catalog', type=Path, default=DEFAULT_OUTPUT)
    inspect = sub.add_parser('inspect', help='Read one exact source name/GUID; emit full source properties/curves.')
    inspect.add_argument('identifier')
    inspect.add_argument('--catalog', type=Path, default=DEFAULT_OUTPUT)
    inspect.add_argument('--output', type=Path, help='Write detailed JSON rather than printing it.')
    check = sub.add_parser('check', help='Refresh current mod sources/stats using the indexed external catalogue.')
    check.add_argument('--catalog', type=Path, default=DEFAULT_OUTPUT)
    check.add_argument('--public-root', type=Path, action='append', default=[],
                       help='Add exported Content/RootTemplates LSX without rescanning vanilla effect sources.')
    check.add_argument('--output', type=Path, help='Defaults to catalogue-adjacent audit.json.')
    args = parser.parse_args()
    if args.command == 'build':
        catalog = make_catalog(args)
        audit = check_catalog(catalog)
        write_json(args.output, catalog)
        write_json(args.output.with_name('audit.json'), audit)
        print_json({'catalog': str(args.output.resolve()), 'audit': str(args.output.with_name('audit.json').resolve()),
                    'counts': audit['counts'], 'issue_counts': audit['issue_counts'],
                    'parse_errors': len(catalog['parse_errors']), 'runtime_verified': False})
        return 1 if audit['issue_counts'].get('error') else 0
    catalog = load(args.catalog)
    if args.command == 'query':
        found = []
        for kind in (['sources', 'meis', 'shortnames', 'resources', 'templates', 'stats'] if args.kind == 'all' else [args.kind]):
            for record in catalog[kind]:
                if args.text.casefold() in json.dumps(record, ensure_ascii=False).casefold():
                    found.append(dict(kind=kind, **record))
        print_json({'matches': len(found), 'results': found[:max(0, args.limit)]})
        return 0
    if args.command == 'inspect':
        found = [r for k in ('sources', 'meis', 'shortnames', 'resources', 'templates') for r in catalog[k]
                 if args.identifier.casefold() in {r.get('uuid', '').casefold(), r['name'].casefold()}]
        if len(found) != 1:
            raise SystemExit('Expected one exact match; found ' + str(len(found)) + '. Use query with name or GUID first.')
        item = found[0]
        result = inspect_source(item_path(catalog, item)) if item['path'].endswith('.lsefx') else item
        if args.output:
            write_json(args.output, result)
            print_json({'output': str(args.output.resolve())})
        else:
            print_json(result)
        return 0
    # Refresh only the mod here. Do not pay for another 11,000-source vanilla scan.
    own = Path(catalog['roots']['mod_source'])
    data = Path(catalog['roots']['data'])
    extra_public = [Path(value) for key, value in catalog['roots'].items()
                    if key.startswith('public') and Path(value) not in {data / 'Public', own / 'Public'}]
    extra_public.extend(args.public_root)
    temp_args = argparse.Namespace(data_root=data, mod_source=own,
                                   modules=[], public_root=extra_public)
    refreshed = make_catalog(temp_args)
    for key in ('sources', 'meis', 'shortnames'):
        catalog[key] = [r for r in catalog[key] if r['location'] != 'mod_source'] + refreshed[key]
    for key in ('resources', 'templates'):
        catalog[key] = refreshed[key]
    catalog['stats'] = refreshed['stats']
    catalog['reference_stats'] = refreshed['reference_stats']
    catalog['roots'].update(refreshed['roots'])
    catalog['parse_errors'] = [e for e in catalog['parse_errors'] if not Path(e['path']).is_relative_to(own)] + refreshed['parse_errors']
    audit = check_catalog(catalog)
    output = args.output or args.catalog.with_name('audit.json')
    catalog['refreshed_utc'] = datetime.now(timezone.utc).isoformat()
    write_json(args.catalog, catalog)
    write_json(output, audit)
    print_json({'audit': str(output.resolve()), 'counts': audit['counts'],
                'issue_counts': audit['issue_counts'], 'runtime_verified': False})
    return 1 if audit['issue_counts'].get('error') else 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
