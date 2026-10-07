"""Author sword FX from installed, editable vanilla components.

Compile the resulting .lsefx in Toolkit AllSpark before registering resources.
The model and ribbon materials are vanilla; composition is specific to this mod.
Official workflow: https://docs.baldursgate3.game/VFX_%E2%80%93_Part_1:_Making_Effects
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from sword_cultivator_spec import FOLDER, MOD, guid

REPO = Path(__file__).resolve().parents[1]
DATA = Path('E:/SteamLibrary/steamapps/common/Baldurs Gate 3/Data')
SOURCE = REPO / 'mods' / MOD / 'Source'
BASE = Path('Editor/Mods/Shared/Assets/Effects')
MESH = '15864e49-e811-41aa-9f27-f2ca410a13cf'
NAME = 'ef1d7d1e-02b6-4548-80d9-5ef2fbcda237'
TIME = '035b5248-d0ca-44b7-853f-3acb84110e67'
POSITION = '47a42cb9-3508-427e-8a09-8d8cc74771b7'
STYLES = ('common', 'taixuan', 'tianqing', 'xueyan', 'xingge')
MODEL_SCALE = '2bea542b-790f-4ef8-877b-5a97335adb1f'
MODEL_COLOR = '4dd77ddd-853f-4f44-9c4d-83f8493dd54a'
RIBBON_COLOR = '6b57c0bd-4010-431e-a968-76adfcd550e7'
RIBBON_SCALE = 'af11a01c-c586-4b7a-a148-ed28d952086d'
PARTICLE_COLOR = '93b34a52-eef2-4f88-80f6-19e3126188ca'
PARTICLE_SCALE = '02e6012f-51af-4f4c-8897-2b8421952fa1'
PARTICLE_AXES = '3ab58b27-d41b-4221-b714-cb35fd213ce7'
LIFESPAN = '352fac77-0097-47ec-908c-7c0d334fc161'
EMIT_RATE = 'b16512bc-8157-4c11-bfde-732ec940b841'
INITIAL_COUNT = '20d22bbd-2e85-41e1-bc13-00b2a72cdf9b'
BOUND_RADIUS = 'ba2ee0f9-d369-4d36-bd63-30d4c8c46a0a'
BOUND_CENTER = 'c1115291-39d1-43a2-8259-31c2ef4dbd93'
COLORS = {'taixuan': (170, 230, 255), 'tianqing': (255, 217, 145),
          'xueyan': (230, 65, 60), 'xingge': (100, 235, 190)}
PIERCE = BASE / 'Actions/Cast/WeaponAttack/VFX_Actions_Cast_WeaponAttack_Target_BladeFlourish_Pierce_01.lsefx'
BLOOD = Path('Editor/Mods/SharedDev/Assets/Effects/Cinematic/VFX_Cinematic_BloodPuff_01.lsefx')
SMITE = BASE / 'Spells/Cast/Paladin/VFX_Spells_Cast_Paladin_Target_ThunderousSmite_Impact_BodyFX_01.lsefx'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PropertyDictionary:
    """Resolve component properties and module membership from installed AllSpark XML.

    Native sources often serialize dormant property ramps. Activating their XMD
    module matters as much as changing the ramp. Missing sibling properties use
    XCD defaults; no enum ordinals or module identities are invented here.
    """
    def __init__(self, data):
        folder = data / 'Editor/Config/AllSpark'
        self.paths = [folder / 'ComponentDefinition.xcd', folder / 'ModuleDefinition.xmd']
        xcd, xmd = (ET.parse(p).getroot() for p in self.paths)
        self.properties = {(c.get('name'), p.get('id')): p
                           for c in xcd.iter('component')
                           for p in c.findall('./properties/property')}
        self.membership = {(p.get('component'), p.get('id')): m
                           for m in xmd.iter('module')
                           for p in m.findall('./properties/property')}
        self.used = {}

    def _property(self, component, key):
        kind = component.get('class')
        definition = self.properties.get((kind, key))
        if definition is None:
            raise ValueError(f'AllSpark XCD does not define {kind}/{key}')
        prop = component.find(f'./properties/property[@id="{key}"]')
        if prop is None:
            prop = ET.SubElement(component.find('properties'), 'property', id=key)
            for child in definition.find('definition'):
                if child.tag == 'data':
                    prop.append(copy.deepcopy(child))
            for datum in prop.findall('./data/datum'):
                datum.set('lod', '00000000-0000-0000-0000-000000000000')
        return prop, definition

    def property(self, component, key):
        prop, definition = self._property(component, key)
        kind = component.get('class')
        module = self.membership.get((kind, key))
        if module is not None:
            modules = component.find('modules')
            if modules is None:
                modules = ET.SubElement(component, 'modules')
            target = next((m for m in modules if m.get('id', '').lower() == module.get('id').lower()), None)
            if target is None:
                target = ET.SubElement(modules, 'module', id=module.get('id').lower(),
                                       muted='False', index=str(len(modules)))
            target.set('muted', 'False')
            for sibling in module.findall('./properties/property'):
                if (sibling.get('component') == kind
                        and component.find(f'./properties/property[@id="{sibling.get("id")}"]') is None):
                    self._property(component, sibling.get('id'))
        spec = definition.find('definition')
        self.used[f'{kind}/{key}'] = dict(component=kind, property=key,
                                         name=definition.get('name'), type=spec.get('type'),
                                         tooltip=spec.get('tooltip'),
                                         channels=[dict(c.attrib) for c in spec.findall('./channels/channel')],
                                         constraints=[dict(c.attrib) for c in spec.findall('./constraints/constraint')],
                                         module=None if module is None else dict(module.attrib))
        return prop

    def evidence(self):
        return dict(files=[dict(path=str(p), sha256=digest(p)) for p in self.paths],
                    properties=list(self.used.values()),
                    color_encoding='Signed ARGB (AARRGGBB), matching XCD red/green/blue channel colors',
                    official_workflow='https://docs.baldursgate3.game/VFX_%E2%80%93_Part_1:_Making_Effects')


def ramp_edit(dictionary, component, key, transform):
    prop = dictionary.property(component, key)
    channels = prop.findall('./data/datum/rampchanneldata/rampchannel')
    if not channels:
        raise ValueError(f'Expected native ramp for {component.get("class")}/{key}')
    for channel in channels:
        for frame in channel.findall('./keyframes/keyframe'):
            # Control points are keyframes too: transform values but retain their
            # times and spline types so the native fade/shape does not jump.
            frame.set('value', str(transform(channel.get('id'), frame.get('value'))))


def multiply(dictionary, component, key, factors):
    channels = dictionary.properties[(component.get('class'), key)].findall('./definition/channels/channel')
    mapping = {c.get('id'): factor for c, factor in zip(channels, factors)} if isinstance(factors, tuple) else None
    if mapping is not None and len(mapping) != len(channels):
        raise ValueError('Axis factors must match the exact XCD channel count')
    ramp_edit(dictionary, component, key,
              lambda channel, value: format(float(value) * (mapping[channel] if mapping else factors), '.9g'))


def recolor(dictionary, component, key, rgb, alpha=1.0):
    def transform(channel, value):
        argb = int(value) & 0xffffffff
        a = min(255, max(0, round((argb >> 24) * alpha)))
        # Retain native black/white density contrast while changing its hue.
        brightness = max((argb >> 16) & 255, (argb >> 8) & 255, argb & 255) / 255
        r, g, b = (round(v * brightness) for v in rgb)
        packed = (a << 24) | (r << 16) | (g << 8) | b
        return packed - 0x100000000 if packed >= 0x80000000 else packed
    ramp_edit(dictionary, component, key, transform)


def timing(component, start, end):
    component.set('start', format(start, '.9g'))
    component.set('end', format(end, '.9g'))
    set_value(component, TIME, f'{start:.9g},{end:.9g}')


def active_particles(root):
    for track in root.findall('./trackgroups/trackgroup/track'):
        component = track.find('component')
        if (component is not None and component.get('class') == 'ParticleSystem'
                and track.get('muted') != 'True' and track.get('mutestateoverride') != 'Muted'):
            yield track, component


def copy_tracks(root, origin, selections, style, label):
    source = ET.parse(origin).getroot()
    group = ET.SubElement(root.find('trackgroups'), 'trackgroup', name=label)
    ET.SubElement(ET.SubElement(group, 'ids'), 'id', value=str(len(root.find('trackgroups')) + 20))
    copied = []
    groups = source.findall('./trackgroups/trackgroup')
    for gi, ti, expected_instance in selections:
        track = copy.deepcopy(groups[gi].findall('track')[ti])
        component = track.find('component')
        if component is None or component.get('instancename') != expected_instance:
            raise ValueError(f'Native template changed: {origin} track {gi}/{ti}')
        track.set('muted', 'False')
        track.set('mutestateoverride', 'Unmuted')
        track.set('name', f'{label} {len(copied) + 1}')
        component.set('instancename', guid(f'vfx/component/{style}/{label}/{gi}/{ti}'))
        set_value(component, NAME, track.get('name'))
        group.append(track)
        copied.append(component)
    return copied


def bounds(dictionary, root, radius, duration):
    found = False
    for component in root.findall('./trackgroups/trackgroup/track/component'):
        if component.get('class') == 'BoundingSphere':
            found = True
            dictionary.property(component, BOUND_RADIUS)
            dictionary.property(component, BOUND_CENTER)
            set_value(component, BOUND_RADIUS, radius)
            set_value(component, BOUND_CENTER, '0,0,0')
            timing(component, 0, duration)
    if not found:
        raise ValueError('Native template must provide its BoundingSphere')


def branch_projectile(data, style, dictionary):
    root, origin = projectile(data)
    axes = {'taixuan': (.5, .5, 1.8), 'tianqing': (2.4, 2.4, 3.0),
            'xueyan': (.8, .8, 1.2), 'xingge': (.8, .8, 1.15)}[style]
    wake = {'taixuan': .55, 'tianqing': 3.0, 'xueyan': 1.1, 'xingge': .8}[style]
    for component in root.findall('./trackgroups/trackgroup/track/component'):
        if component.get('class') == 'Model':
            multiply(dictionary, component, MODEL_SCALE, axes)
            recolor(dictionary, component, MODEL_COLOR, COLORS[style])
            if style == 'tianqing':
                set_value(component, MESH, 'WPN_HUM_Greatsword_A_0 <12f3193c-ce1a-5a69-1bf0-8537b9b606f9>')
        elif component.get('class') == 'Ribbon 2.0':
            multiply(dictionary, component, RIBBON_SCALE, wake)
            recolor(dictionary, component, RIBBON_COLOR, COLORS[style])
    origins = [origin]
    if style == 'xueyan':
        blood_origin = data / BLOOD
        smoke, = copy_tracks(root, blood_origin, [(1, 0, 'dbcba590-de6e-495a-b8ec-1374569d8a7e')],
                             style, 'Blood mist wake')
        # Native 2..4.5 scale becomes .8..1.8. This changes only puff size;
        # emission, alpha, flipbook, lifetime and native red material stay fixed.
        multiply(dictionary, smoke, PARTICLE_SCALE, .40)
        # Keep BloodPuff's native white/gray Color ramp and 1.5..2s
        # lifespan. The material already has SmokeColor=(.4590799,0,0).
        # Its 8x8 flipbook advances at 24 fps: shortening the life to .3s
        # also truncated the texture animation before its mature smoke frames.
        dictionary.property(smoke, PARTICLE_COLOR)
        dictionary.property(smoke, LIFESPAN)
        ramp_edit(dictionary, smoke, EMIT_RATE, lambda channel, value: 6)
        dictionary.property(smoke, INITIAL_COUNT)
        # Native initial 4,4 guarantees the original burst independently of
        # continuous emission accumulation in the projectile's .1s loop.
        # Retain the previously authored 6/s rate as a separate variable.
        timing(smoke, 0, .2)
        lead_out = root.findall('./phases/object/data')[-1]
        if lead_out.get('definitionid') != 'fc8e9f77-827a-433f-a58d-ad1007605399':
            raise ValueError('Native projectile LeadOut phase changed')
        lead_out.set('duration', '2.1')
        origins.append(blood_origin)
    bounds(dictionary, root, 9 if style == 'tianqing' else 3, 2.3 if style == 'xueyan' else 1.2)
    return root, origins, dict(rgb=COLORS[style], model_axis_factors=axes, wake_scale_factor=wake,
                               blood_mist=style == 'xueyan',
                               blood_mist_particle_scale_factor=.40 if style == 'xueyan' else None,
                               blood_mist_native_color_lifetime_initial_count=style == 'xueyan',
                               blood_mist_emit_rate=6 if style == 'xueyan' else None,
                               lead_out=2.1 if style == 'xueyan' else 1,
                               orientation='Projectile Follow requires Toolkit verification')


def branch_impact(data, style, dictionary):
    if style == 'taixuan':
        origin = data / PIERCE
        root = ET.parse(origin).getroot()
        keep = {'ae6913c4-8ffe-47b5-a1e8-66608961bc58', 'ad52571a-627e-4019-bfd5-e1b5c4375846',
                'e64c7f54-ecd3-4983-902d-dd180f93a0ce'}
        for group in list(root.find('trackgroups')):
            for track in list(group.findall('track')):
                component = track.find('component')
                if (component is None or (component.get('class') != 'BoundingSphere'
                                          and component.get('instancename') not in keep)):
                    group.remove(track)
            if not group.findall('track'):
                root.find('trackgroups').remove(group)
        for track, component in active_particles(root):
            recolor(dictionary, component, PARTICLE_COLOR, COLORS[style])
            if component.get('instancename') == 'e64c7f54-ecd3-4983-902d-dd180f93a0ce':
                multiply(dictionary, component, PARTICLE_SCALE, .4)
            else:
                multiply(dictionary, component, PARTICLE_AXES, (.2, 1.35, 1.0))
        bounds(dictionary, root, 5, 2)
        return root, [origin], dict(rgb=COLORS[style], directional_flare_axis_factors=(.2, 1.35, 1),
                                    core_scale_factor=.4, note='Local piercing flare; full-distance Beam is not bound')

    root, origin = impact(data)
    origins = [origin]
    particles = list(active_particles(root))
    for track, component in particles:
        recolor(dictionary, component, PARTICLE_COLOR, COLORS[style])
        multiply(dictionary, component, PARTICLE_SCALE, {'tianqing': 2.5, 'xueyan': 1, 'xingge': .85}[style])
        if style == 'xueyan':
            multiply(dictionary, component, LIFESPAN, .65)
            timing(component, float(component.get('start')) * .65, float(component.get('end')) * .65)

    if style == 'tianqing':
        shock_origin = data / SMITE
        shock, = copy_tracks(root, shock_origin, [(2, 5, '920ec035-71e5-4d4e-bd5d-920dfde922c6')],
                             style, 'Heavy sword shockwave')
        multiply(dictionary, shock, PARTICLE_SCALE, 2)
        recolor(dictionary, shock, PARTICLE_COLOR, COLORS[style])
        origins.append(shock_origin)
    elif style == 'xueyan':
        blood_origin = data / BLOOD
        smoke = copy_tracks(root, blood_origin,
                            [(1, 0, 'dbcba590-de6e-495a-b8ec-1374569d8a7e'),
                             (1, 1, 'ebfa09d7-65ab-4cd1-904c-28863dbd890e')], style, 'Blood mist impact')
        for component, scale in zip(smoke, (.35, .25)):
            multiply(dictionary, component, PARTICLE_SCALE, scale)
            multiply(dictionary, component, LIFESPAN, .65)
            recolor(dictionary, component, PARTICLE_COLOR, COLORS[style], .85)
        origins.append(blood_origin)
    elif style == 'xingge':
        # A second native swoosh makes a paired protective arc. This is visual
        # presentation only; no gameplay protection is inferred from the effect.
        arc = copy.deepcopy(particles[0][0])
        component = arc.find('component')
        component.set('instancename', guid('vfx/component/xingge/guard-arc'))
        arc.set('name', 'Returning guard arc')
        set_value(component, NAME, 'Returning guard arc')
        multiply(dictionary, component, PARTICLE_SCALE, 1.15)
        recolor(dictionary, component, PARTICLE_COLOR, COLORS[style], .55)
        timing(component, float(component.get('start')) + .08, float(component.get('end')) + .08)
        root.findall('./trackgroups/trackgroup')[1].append(arc)
    bounds(dictionary, root, 10 if style == 'tianqing' else 5, 2)
    return root, origins, dict(rgb=COLORS[style], native_slash_scale_factor={'tianqing': 2.5, 'xueyan': 1, 'xingge': .85}[style],
                               shockwave_scale_factor=2 if style == 'tianqing' else None,
                               slash_lifespan_factor=.65 if style == 'xueyan' else 1,
                               blood_mist_scales=(.35, .25) if style == 'xueyan' else None,
                               paired_arc=style == 'xingge')


def set_value(component, key, value):
    values = component.findall(f'./properties/property[@id="{key}"]/data/datum')
    if not values:
        raise ValueError(f'Missing verified component property: {key}')
    for datum in values:
        datum.set('value', str(value))


def write(path, root):
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root, space='  ')
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def projectile(data):
    origin = data / BASE / 'Projectiles/VFX_Projectiles_Force_MagicMissile_Projectile_01.lsefx'
    root = ET.parse(origin).getroot()
    groups = root.find('trackgroups')
    model_kept = False
    for group in list(groups):
        group.set('name', 'Sword and wake')
        for track in list(group.findall('track')):
            component = track.find('component')
            kind = component.get('class')
            if kind == 'Model' and not model_kept:
                model_kept = True
                track.set('muted', 'False')
                track.set('mutestateoverride', 'Unmuted')
                track.set('name', 'Sword body')
                set_value(component, NAME, 'Sword body')
                set_value(component, MESH, 'WPN_HUM_Longsword_A_0 <c1319fce-3d47-ac75-e502-a3e965500038>')
                set_value(component, POSITION, '0,0,0')
            elif kind not in ('BoundingSphere', 'Ribbon 2.0'):
                group.remove(track)
            if kind == 'Ribbon 2.0':
                track.set('name', 'Narrow sword wake')
        if not group.findall('track'):
            groups.remove(group)
    if not model_kept:
        raise ValueError('Vanilla source lacks expected Model component')
    return root, origin


def impact(data):
    origin = data / BASE / 'Actions/Cast/WeaponAttack/VFX_Actions_Cast_WeaponAttack_Target_BladeFlourish_Slash_01.lsefx'
    root = ET.parse(origin).getroot()
    # Reference characters/floors stay muted; the native slash remains visible.
    # Registration will bind this to the impact point rather than a caster hand.
    return root, origin


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=DATA)
    parser.add_argument('--styles', nargs='+', choices=STYLES, default=['common'],
                        help='Author only these styles; default preserves the common factory')
    parser.add_argument('--phases', nargs='+', choices=('projectile', 'impact'), default=['projectile', 'impact'])
    parser.add_argument('--install-new', action='store_true', help='Copy only these new authored files into the active Toolkit project')
    args = parser.parse_args()
    styles = list(dict.fromkeys(args.styles))
    dictionary = PropertyDictionary(args.data) if any(s != 'common' for s in styles) else None
    records = []
    for style in styles:
        for phase in dict.fromkeys(args.phases):
            if style == 'common':
                root, origin = {'projectile': projectile, 'impact': impact}[phase](args.data)
                origins, design = [origin], None
            else:
                factory = {'projectile': branch_projectile, 'impact': branch_impact}[phase]
                root, origins, design = factory(args.data, style, dictionary)
            name = f'VFX_ESC_{style.title()}_{phase.title()}_01'
            # This editor id is not an EffectBank resource GUID.
            root.set('id', guid(f'vfx/editor/{style}/{phase}'))
            path = SOURCE / 'Editor/Mods' / FOLDER / 'Assets/Effects/Sword' / (name + '.lsefx')
            write(path, root)
            if args.install_new:
                target = args.data / path.relative_to(SOURCE)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
            record = dict(style=style, phase=phase, name=name, source=str(path.relative_to(REPO)),
                          sha256=digest(path), origin=str(origins[0]), origin_sha256=digest(origins[0]),
                          compiled=False, toolkit_test='not-run')
            if design is not None:
                record.update(design=design,
                              origins=[dict(path=str(p), sha256=digest(p)) for p in origins],
                              property_dictionary=dictionary.evidence(),
                              audit='build/sword-vfx/branch-template-audit.json')
            records.append(record)
    out = REPO / 'build/sword-vfx/authored-effects.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    previous = json.loads(out.read_text(encoding='utf-8')) if out.exists() else []
    merged = {(r['style'], r['phase']): r for r in previous}
    merged.update({(r['style'], r['phase']): r for r in records})
    out.write_text(json.dumps(list(merged.values()), ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Authored {len(records)} sources; AllSpark compilation and visual validation required.')


if __name__ == '__main__':
    main()
