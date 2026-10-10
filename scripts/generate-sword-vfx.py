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
import math
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

from sword_cultivator_spec import FOLDER, MOD, guid
from sword_projectile_readability import improve_projectile

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


def replace_ramp(dictionary, component, key, frames):
    """Replace verified ramp channels, activating their native XMD module."""
    prop = dictionary.property(component, key)
    channels = prop.findall('./data/datum/rampchanneldata/rampchannel')
    if len(channels) != len(frames):
        raise ValueError(f'Unexpected channel count for {component.get("class")}/{key}')
    for channel, values in zip(channels, frames):
        channel.set('type', 'Linear')
        keyframes = channel.find('keyframes')
        if keyframes is None:
            keyframes = ET.SubElement(channel, 'keyframes')
        keyframes.clear()
        for time, value in values:
            ET.SubElement(keyframes, 'keyframe', time=format(time, '.9g'), value=format(value, '.9g'))


def guard_emissive_cores(data, root, swords, dictionary):
    """Add three complete native Exterior models; preserve every steel track.

    Native Exterior bounds are +/-0.38248 on X/Y and -10.000001..0 on Z.
    X+90 turns its -Z long axis upward, matching the existing steel sword.
    Its 0.9m core is centered inside the native longsword's 0.987m height;
    copied orbit curves remain byte-identical, with only a static Y inset.
    """
    origin = data / BASE / 'Beams/VFX_Beams_Debuff_TrueStrike_Beam_01.lsefx'
    native = ET.parse(origin).getroot()
    donor, = [t for t in native.findall('./trackgroups/trackgroup/track')
              if t.find('component').get('instancename') == 'e55f84d1-b87c-48e3-8227-e7d2e34133aa']
    template = donor.find('component')
    def prop(c, key):
        return c.find(f'./properties/property[@id="{key}"]')
    if donor.get('muted') != 'False' or '27169e30-e769-5199-2378-1cb3f2ad4f38' not in prop(template, MESH).find('data/datum').get('value'):
        raise ValueError('Verified native TrueStrike Exterior donor changed')
    steel_tracks = swords.findall('track')
    if len(steel_tracks) != 3:
        raise ValueError('Expected three existing guard steel swords')
    group = ET.SubElement(root.find('trackgroups'), 'trackgroup', name='Three cyan emissive sword cores')
    ids = [int(n.get('value')) for n in root.findall('./trackgroups/trackgroup/ids/id')]
    ET.SubElement(ET.SubElement(group, 'ids'), 'id', value=str(max(ids) + 1))
    half_width, length = .14, .9
    scale = (half_width / .3824824, half_width / .3824274, length / 10.000001)
    # Steel visual bank Z bounds -1.1560508..0.36261004, rotated X+90 at .65.
    inset_y = .65 * (1.1560508 - .36261004) / 2 - length / 2
    cyan = (0xff000000 | 170 << 16 | 230 << 8 | 255) - 0x100000000
    for index, steel_track in enumerate(steel_tracks):
        steel = steel_track.find('component')
        track = copy.deepcopy(donor)
        core = track.find('component')
        label = f'Guard emissive sword core {index + 1}'
        track.set('name', label)
        track.set('muted', 'False')
        track.set('mutestateoverride', 'Unmuted')
        core.set('instancename', guid(f'vfx/component/common/status/emissive-core/{index}'))
        set_value(core, NAME, label)
        timing(core, float(steel.get('start')), float(steel.get('end')))
        for key in ('37b047c1-8fb7-4e7c-9319-58db9da44e77',
                    '00910be4-aaa1-41a2-946f-735d33de387b',
                    '8771c2c7-091d-4d1f-b7cb-91f87f6a486a'):
            dictionary.property(core, key)
            target = prop(core, key)
            position = list(core.find('properties')).index(target)
            core.find('properties').remove(target)
            core.find('properties').insert(position, copy.deepcopy(prop(steel, key)))
        replace_ramp(dictionary, core, MODEL_SCALE, tuple([(0, v), (1, v)] for v in scale))
        replace_ramp(dictionary, core, '4a72a815-57fb-4fcb-9a50-1024331ce66a',
                     ([(0, 90), (1, 90)], [(0, 0), (1, 0)], [(0, 0), (1, 0)]))
        dictionary.property(core, POSITION)
        set_value(core, POSITION, f'0,{inset_y:.9g},0')
        replace_ramp(dictionary, core, MODEL_COLOR, ([(0, cyan), (1, cyan)],))
        # Native DynamicParameters, Brightness=5 and all other donor properties
        # stay intact. The status owns the same phases and termination.
        group.append(track)
    return origin, dict(emissive_core_count=3, emissive_core_length=length,
                        emissive_core_diameter=2 * half_width, emissive_core_rgb=(170, 230, 255),
                        emissive_core_axis_scale=scale, emissive_core_static_inset=(0, inset_y, 0),
                        emissive_core_native_dynamic_retained=True, emissive_core_native_brightness=5)



# Native SharedDev SPRW_Greatsword Visual; verified Objects MaterialID is
# 897a51e0-39fb-7d08-0437-03ec27637571 (registered by _metadata).
# These author constants reproduce the reviewed transformed steel AABB exactly;
# native +Y becomes world +Y with X=0. No cache or installed material edit is used.
COMMON_SPIRITUAL_SWORD = {
    'name': 'SPRW_Greatsword', 'guid': '3727a57a-e4be-44da-02b4-5061028fed5f',
    'axis_scale': (.4542896975731798, .5028270744563265, 1.1060088758609856),
    'offset': (4.542896975268107e-9, -.23560541467942342, .005543155959233881),
    'rotation': (0, 0, 0),
}


def guard_native_spiritual_swords(root):
    """Change only three existing sword Mesh/Axis Scale/Rotation/Offset properties."""
    swords = root.findall('./trackgroups/trackgroup[@name="Three sword guard"]/track/component')
    if len(swords) != 3:
        raise ValueError('Expected three existing Common guard swords')
    design = COMMON_SPIRITUAL_SWORD
    for sword in swords:
        mesh = sword.find(f'./properties/property[@id="{MESH}"]/data/datum')
        if sword.get('class') != 'Model' or mesh.get('value') != 'WPN_HUM_Longsword_A_0 <c1319fce-3d47-ac75-e502-a3e965500038>':
            raise ValueError('Common native visual replacement expects the verified steel baseline')
        mesh.set('value', f"{design['name']} <{design['guid']}>")
        set_value(sword, POSITION, ','.join(format(v, '.17g') for v in design['offset']))
        for key, values in ((MODEL_SCALE, design['axis_scale']),
                            ('4a72a815-57fb-4fcb-9a50-1024331ce66a', design['rotation'])):
            channels = sword.findall(f'./properties/property[@id="{key}"]/data/datum/rampchanneldata/rampchannel')
            if len(channels) != 3:
                raise ValueError('Expected three existing Model transform channels')
            for channel, value in zip(channels, values):
                for frame in channel.findall('./keyframes/keyframe'):
                    frame.set('value', format(value, '.17g'))
    return dict(native_spiritual_swords=3, native_sword_visual=design['guid'],
                native_sword_axis_scale=design['axis_scale'], native_sword_offset=design['offset'],
                native_sword_rotation=design['rotation'], native_transformed_aabb_preserved=True)


def guard_status(data, dictionary, *, emissive_cores=False, native_swords=False):
    """Three local orbiting swords, native curved wisps and a faint sphere.

    Status MEI attaches this at Dummy_Root; explicit model Y=0.95 puts the
    orbit at waist/chest height. The lead-in and lead-out hold the loop seam,
    so the start/end positions of every loop agree. This source is a visual
    prototype until AllSpark compilation and in-game attachment are checked.
    Ribbon 2.0 has no keyframed emitter position in the installed XCD: its
    four-channel Value ramp is a material parameter, never a position track.
    The short curved wisps therefore reuse Cloud of Daggers' wind mesh.
    """
    root, origin = projectile(data)
    lead, loop, out = .2, 3.6, .4
    duration = lead + loop + out
    for phase, seconds in zip(root.findall('./phases/object/data'), (lead, loop, out)):
        phase.set('duration', format(seconds, '.9g'))
    groups = root.find('trackgroups')
    template = next(t for t in root.findall('./trackgroups/trackgroup/track')
                    if t.find('component').get('class') == 'Model')
    template = copy.deepcopy(template)
    for group in list(groups):
        for track in list(group.findall('track')):
            if track.find('component').get('class') != 'BoundingSphere':
                group.remove(track)
        if not group.findall('track'):
            groups.remove(group)
    swords = ET.SubElement(groups, 'trackgroup', name='Three sword guard')
    ET.SubElement(ET.SubElement(swords, 'ids'), 'id', value='41')
    rgb, radius, height = (175, 235, 225), 1.05, .95
    for index in range(3):
        track = copy.deepcopy(template)
        track.set('name', f'Guard sword {index + 1}')
        component = track.find('component')
        component.set('instancename', guid(f'vfx/component/common/status/sword/{index}'))
        set_value(component, NAME, track.get('name'))
        timing(component, 0, duration)
        multiply(dictionary, component, MODEL_SCALE, .65)
        recolor(dictionary, component, MODEL_COLOR, rgb)
        offset = index * 2 * math.pi / 3
        times = [0] + [lead + loop * step / 48 for step in range(49)] + [duration]
        angles = [offset] + [offset + 2 * math.pi * step / 48 for step in range(49)] + [offset + 2 * math.pi]
        replace_ramp(dictionary, component, '37b047c1-8fb7-4e7c-9319-58db9da44e77', (
            [(t / duration, radius * math.cos(a)) for t, a in zip(times, angles)],
            [(t / duration, height) for t in times],
            [(t / duration, radius * math.sin(a)) for t, a in zip(times, angles)],
        ))
        # The native longsword's blade follows -Z. Pitching +90 degrees
        # points it upward (+Y); only its position circles the owner. Fixed
        # rotation avoids composing lifetime yaw in the tilted local frame.
        replace_ramp(dictionary, component, '4a72a815-57fb-4fcb-9a50-1024331ce66a', (
            [(0, 90), (1, 90)], [(0, 0), (1, 0)], [(0, 0), (1, 0)],
        ))
        replace_ramp(dictionary, component, 'c57b1310-2df9-4339-bdf8-a97475e121ff', (
            [(0, 0), (1, 0)],
            [(0, 0), (1, 0)],
            [(0, 0), (1, 0)],
        ))
        replace_ramp(dictionary, component, '00910be4-aaa1-41a2-946f-735d33de387b', (
            [(0, 0), (lead / duration, .85), ((lead + loop) / duration, .85), (1, 0)],
        ))
        dictionary.property(component, '8771c2c7-091d-4d1f-b7cb-91f87f6a486a')
        set_value(component, '8771c2c7-091d-4d1f-b7cb-91f87f6a486a', out)
        swords.append(track)

    curve_origin = data / BASE / 'Status/VFX_Status_CloudOfDaggers_Aura_Dummy_01.lsefx'
    curve, = copy_tracks(root, curve_origin, [(4, 0, 'f91a0268-aed1-45db-8d2a-61a8f3ffa5ca')],
                        'common', 'Short guard wisp')
    timing(curve, 0, lead + loop)
    dictionary.property(curve, '726ea55f-d0f9-4176-9a22-c5539199a83a')
    set_value(curve, '726ea55f-d0f9-4176-9a22-c5539199a83a', f'0,{height},0')
    # Local particles follow the status owner. The installed XCD dropdown is
    # World|Local|World (Emit Local), so Local is exactly value 1.
    dictionary.property(curve, 'b13c2ffd-c94f-4d56-947e-07077287ec52')
    set_value(curve, 'b13c2ffd-c94f-4d56-947e-07077287ec52', 1)
    ramp_edit(dictionary, curve, EMIT_RATE, lambda channel, value: 3)
    replace_ramp(dictionary, curve, LIFESPAN, ([(0, .25), (1, .25)], [(0, .35), (1, .35)]))
    replace_ramp(dictionary, curve, PARTICLE_SCALE, ([(0, .25), (1, .4)], [(0, .35), (1, .5)]))
    # This native wisp stores a dormant Color override before its active Color
    # module. Recolor the shared ramp but preserve the native module selection:
    # PropertyDictionary.property() otherwise activates that dormant override.
    color_states = [(module, module.get('muted', 'False'))
                    for module in curve.findall('./modules/module')
                    if module.get('id', '').lower() == 'b369fad0-cc26-42f3-bdc2-0b8f120c6081']
    if sum(muted == 'False' for _, muted in color_states) != 1:
        raise ValueError('Native guard-wisp template must have exactly one active Color module')
    recolor(dictionary, curve, PARTICLE_COLOR, rgb, .7)
    for module, muted in color_states:
        module.set('muted', muted)
    ramp_edit(dictionary, curve, '79ab5e9c-2d87-496c-83bd-1b6c78cbd095', lambda channel, value: 0)
    # Edit only the native active Cylinder Emitter. Activating the dormant
    # Sphere/Circle property ramps would add competing emitter modules.
    for key in ('b0e13a65-91f5-4382-a507-748c257b36c8', '5f042807-09d5-4841-846e-2b13f7a3d80d'):
        ramp_edit(dictionary, curve, key, lambda channel, value: .05)

    # Reuse only the filled sphere from the native single-person status,
    # including its VAT mesh/material. The visual bank has approximately
    # +/-10m bounds, and this Medium template uses .15 axis modifiers.
    # A constant .8 uniform scale therefore gives an approximately 1.2m
    # radius. Remove the native burst/growth ramps and hold a faint shell
    # through the existing loop seam; no new shader or render mode is used.
    sphere_origin = data / 'Editor/Mods/SharedDev/Assets/Effects/Status/VFX_Status_ResilientSphere_Medium_RootFX_01.lsefx'
    shell, = copy_tracks(root, sphere_origin, [(1, 1, '36a94c62-d817-4021-8a85-22f65b4f9fea')],
                        'common', 'Faint guard sphere')
    timing(shell, 0, duration)
    for key in ('5b7fc64a-bf90-4085-9151-044aa275f590',
                'de10ede1-b899-4565-8a4b-eaa258360ee9',
                'f009ecca-fae4-49fd-aad3-3224e3ed7e21'):
        prop = dictionary.property(shell, key)
        if any(float(d.get('value')) != .15 for d in prop.findall('./data/datum')):
            raise ValueError('Native Medium sphere axis modifiers changed')
    dictionary.property(shell, MESH)
    dictionary.property(shell, POSITION)
    set_value(shell, POSITION, '0,1,0')
    replace_ramp(dictionary, shell, 'f80eefa7-3ffe-4c08-b043-596ae48487f8', ([(0, .8), (1, .8)],))
    shell_rgb, shell_alpha = (190, 235, 245), .18
    shell_color = (0xff000000 | shell_rgb[0] << 16 | shell_rgb[1] << 8 | shell_rgb[2]) - 0x100000000
    replace_ramp(dictionary, shell, MODEL_COLOR, ([(0, shell_color), (1, shell_color)],))
    replace_ramp(dictionary, shell, '6cbb9e51-0d17-4916-9666-30d8c7b47e81', ([(0, 1), (1, 1)],))
    replace_ramp(dictionary, shell, '00910be4-aaa1-41a2-946f-735d33de387b', (
        [(0, 0), (lead / duration, shell_alpha), ((lead + loop) / duration, shell_alpha), (1, 0)],
    ))
    zero_axes = ([(0, 0), (1, 0)],) * 3
    replace_ramp(dictionary, shell, 'e5ece95a-a162-4a49-b029-cbc701fb00e4', zero_axes)
    replace_ramp(dictionary, shell, 'c57b1310-2df9-4339-bdf8-a97475e121ff', zero_axes)
    dictionary.property(shell, '8771c2c7-091d-4d1f-b7cb-91f87f6a486a')
    set_value(shell, '8771c2c7-091d-4d1f-b7cb-91f87f6a486a', out)
    origins = [origin, curve_origin, sphere_origin]
    core_design = {}
    if emissive_cores:
        core_origin, core_design = guard_emissive_cores(data, root, swords, dictionary)
        origins.append(core_origin)
    native_design = guard_native_spiritual_swords(root) if native_swords else {}
    bounds(dictionary, root, 3, duration)
    return root, origins, dict(
        rgb=rgb, sword_count=3, sword_scale=.65, orbit_radius=radius, orbit_height=height,
        orbit_seconds=loop, lead_in=lead, lead_out=out, sword_loop_seam='matching position and rotation',
        wisp_lifetime=(.25, .35), wisp_emit_rate=3, status_mei_target_bone='Dummy_Root',
        shell_mesh='1658900e-c604-1548-ce0b-5c9d2545feae', shell_radius_approx=1.2,
        shell_center=(0, 1, 0), shell_rgb=shell_rgb, shell_alpha=shell_alpha,
        shell_native_axis_modifier=.15, shell_uniform_scale=.8, shell_brightness=1,
        remaining='AllSpark preview/compile, owner attachment/movement, expiration and low-quality validation; hit deflection is not authored',
        **core_design,
        **native_design,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=DATA)
    parser.add_argument('--styles', nargs='+', choices=STYLES, default=['common'],
                        help='Author only these styles; default preserves the common factory')
    parser.add_argument('--phases', nargs='+', choices=('projectile', 'impact', 'status'), default=['projectile', 'impact'])
    parser.add_argument('--install-new', action='store_true', help='Copy only these new authored files into the active Toolkit project')
    args = parser.parse_args()
    styles = list(dict.fromkeys(args.styles))
    if 'status' in args.phases and styles != ['common']:
        parser.error('The status prototype is authored only for --styles common.')
    dictionary = PropertyDictionary(args.data)
    records = []
    for style in styles:
        for phase in dict.fromkeys(args.phases):
            if phase == 'status':
                root, origins, design = guard_status(args.data, dictionary, emissive_cores=True, native_swords=True)
            elif style == 'common':
                root, origin = {'projectile': projectile, 'impact': impact}[phase](args.data)
                origins, design = [origin], None
            else:
                factory = {'projectile': branch_projectile, 'impact': branch_impact}[phase]
                root, origins, design = factory(args.data, style, dictionary)
            if phase == 'projectile':
                extra_origins, readability = improve_projectile(args.data, style, root, dictionary,
                                                               SimpleNamespace(**globals()))
                origins = list(dict.fromkeys(origins + extra_origins))
                design = {**(design or {}), **readability}
            name = f'VFX_ESC_{style.title()}_{phase.title()}_01'
            from sword_glow import apply as apply_glow
            design = {**(design or {}), **apply_glow(root, dictionary, style)}
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
                              audit=('build/sword-vfx/guard-status-source-validation.json'
                                     if phase == 'status' else 'build/sword-vfx/branch-template-audit.json'))
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
