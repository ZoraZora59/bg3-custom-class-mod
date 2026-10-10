"""Author new ground-falling Tianqing sources without compiling or enabling them.

Only the dedicated Source/Editor/.../Sword/Tianqing directory and the dedicated
authoring manifest are written. No .lsfx, resource, MEI, Stats, installation, or
existing branch source is modified. This CLI deliberately has no install flag.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from sword_cultivator_spec import FOLDER, MOD, guid
from tianqing_vfx_design import GREAT_SWORD, NATIVE_REFERENCES, PRESERVED_ENTRIES, TIANQING_BINDING_PLAN, TIANQING_PROFILES, TIANQING_AUXILIARY_PROFILES, TIANQING_TIMING_PROFILES


REPO = Path(__file__).resolve().parents[1]
DATA = Path('E:/SteamLibrary/steamapps/common/Baldurs Gate 3/Data')
SOURCE = REPO / 'mods' / MOD / 'Source'
OUTPUT = SOURCE / 'Editor/Mods' / FOLDER / 'Assets/Effects/Sword/Tianqing'
MANIFEST = REPO / 'build/sword-vfx/tianqing-redesign-20261007/authoring-manifest.json'
AUTHORING_PROFILES = {**TIANQING_PROFILES, **TIANQING_AUXILIARY_PROFILES}
AUTHORING_PROFILES.update(TIANQING_TIMING_PROFILES)

# Resolve the existing dictionary/helpers; importing does not run its main().
_spec = importlib.util.spec_from_file_location('sword_fx_authoring', REPO / 'scripts/generate-sword-vfx.py')
fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fx)

KEYFRAMED_OFFSET = '37b047c1-8fb7-4e7c-9319-58db9da44e77'
INITIAL_ROTATION = '4a72a815-57fb-4fcb-9a50-1024331ce66a'
ROTATION_RPM = 'e5ece95a-a162-4a49-b029-cbc701fb00e4'
ROTATION_LIFE = 'c57b1310-2df9-4339-bdf8-a97475e121ff'
UNIFORM_SCALE = 'f80eefa7-3ffe-4c08-b043-596ae48487f8'
ALPHA = '00910be4-aaa1-41a2-946f-735d33de387b'
PARTICLE_OFFSET = '726ea55f-d0f9-4176-9a22-c5539199a83a'
PARTICLE_ALPHA = 'd1892ce7-07f3-4d9c-9acb-6692b897a71b'
GOLD = (255, 217, 145)
MODEL_BRIGHTNESS = '6cbb9e51-0d17-4916-9666-30d8c7b47e81'

# Client review of the 38E candidate found a thin, dark edge while the descent
# and impact ring played correctly. A tint does not turn a lit weapon material
# into an emissive one. Keep the original downward pitch and longitudinal size;
# enlarge the two cross-section axes rather than guess a camera-dependent yaw.
SWORD_VISIBILITY_AXIS_FACTORS = (1.5, 4., 1.)
GOLD_CORE = {
    'name': 'VFX_Static_Capless_Cylinder_Downward_Energy_03',
    'guid': '5c7d2d15-21b6-d474-6f28-4b81be12c701',
    'bounds_min': (-1.0000005, -1., -.99452215),
    'bounds_max': (1., 1., .9945227),
    'material_guid': '0fef55b0-b22b-9167-1b61-e2ab8b31195f',
    'material_source': 'Public/Shared/Assets/Materials/Effects/Model/VFX_Model_AlphaBlend_Unlit_Emissive_Panning_UVDistortion_01.lsf',
    'resource_evidence': 'build/vfx-reference-research/static-models.lsx',
    'length_fraction': .8,
    'radial_clearance': .10,
    'radial_scale_quantum': .05,
    'tip_clearance': .08,
    'brightness': 2.25,
}

MODEL_DYNAMIC = '1a2e7309-8ae0-4931-998d-f0fee54ecee0'
WANJUN_EXTERIOR_CORE = {
    'source': 'Editor/Mods/Shared/Assets/Effects/Beams/VFX_Beams_Debuff_TrueStrike_Beam_01.lsefx',
    'component_instance': 'e55f84d1-b87c-48e3-8227-e7d2e34133aa',
    'name': 'VFX_Static_Beam_01_Exterior_02',
    'guid': '27169e30-e769-5199-2378-1cb3f2ad4f38',
    'bounds_min': (-.3824822, -.3824274, -10.000001),
    'bounds_max': (.3824824, .38242725, 0.),
    'material_guid': '016f3188-f19f-334e-f8d3-4d661a52755b',
    'material_source': 'Public/Shared/Assets/Materials/Effects/Model/VFX_Model_AlphaBlend_Unlit_Emissive_NoDepthWrite_Beam_01_Exterior.lsf',
    'brightness': 5,
}


def native_track(root, instance):
    matches = [t for t in root.findall('./trackgroups/trackgroup/track')
               if t.find('component') is not None and t.find('component').get('instancename') == instance]
    if len(matches) != 1:
        raise ValueError(f'Expected exactly one verified native component {instance}')
    return matches[0]


def constants(dictionary, component, key, values):
    fx.replace_ramp(dictionary, component, key,
                    tuple([(0, v), (1, v)] for v in values))


def scalar(dictionary, component, key, value):
    dictionary.property(component, key)
    fx.set_value(component, key, value)


def clone_track(template, key, label, index):
    track = copy.deepcopy(template)
    track.set('muted', 'False')
    track.set('mutestateoverride', 'Unmuted')
    track.set('name', f'{label} {index + 1}')
    component = track.find('component')
    component.set('instancename', guid(f'vfx/tianqing-redesign/component/{key}/{label}/{index}'))
    fx.set_value(component, fx.NAME, track.get('name'))
    return track, component


def group(root, label, index):
    value = ET.SubElement(root.find('trackgroups'), 'trackgroup', name=label)
    ET.SubElement(ET.SubElement(value, 'ids'), 'id', value=str(index))
    return value


def sword_layout(profile):
    if profile['sword_count'] == 1:
        return [(0., 0.)]
    return [(profile['layout_radius'] * math.cos(math.radians(profile['layout_angle_offset_degrees']) + 2 * math.pi * i / profile['sword_count']),
             profile['layout_radius'] * math.sin(math.radians(profile['layout_angle_offset_degrees']) + 2 * math.pi * i / profile['sword_count']))
            for i in range(profile['sword_count'])]


def falling_motion(dictionary, model, profile):
    """Use the same authored timeline for the metal body and emissive spine."""
    duration, hit, height = profile['duration'], profile['hit_time'], profile['drop_height']
    fx.replace_ramp(dictionary, model, KEYFRAMED_OFFSET, (
        [(0, 0), (1, 0)],
        [(0, height), (profile['lead_in'] / duration, height),
         ((profile['lead_in'] + (hit - profile['lead_in']) * .35) / duration, height * .85),
         ((profile['lead_in'] + (hit - profile['lead_in']) * .75) / duration, height * .45),
         (hit / duration, 0), (1, 0)],
        [(0, 0), (1, 0)],
    ))
    fx.replace_ramp(dictionary, model, ALPHA, (
        [(0, 0), (profile['lead_in'] / duration, 1),
         (profile['model_fade_start'] / duration, 1),
         (profile['model_fade_end'] / duration, 0), (1, 0)],
    ))


def wanjun_exterior_core(data, root, dictionary):
    """Swap only Wanjun's gold Model; retain its existing envelope and motion."""
    origin = data / WANJUN_EXTERIOR_CORE['source']
    donor = native_track(ET.parse(origin).getroot(), WANJUN_EXTERIOR_CORE['component_instance'])
    template = donor.find('component')
    def value(component, key):
        return component.find(f'./properties/property[@id="{key}"]/data/datum').get('value')
    if donor.get('muted') != 'False' or template.get('class') != 'Model' or WANJUN_EXTERIOR_CORE['guid'] not in value(template, fx.MESH):
        raise ValueError('Verified TrueStrike Exterior_02 donor changed')
    gold = root.find('./trackgroups/trackgroup[@name="Gold emissive sword spines"]')
    if gold is None or len(gold.findall('track')) != 1:
        raise ValueError('Expected one Wanjun gold component')
    track = gold.find('track')
    old = track.find('component')
    if old.get('class') != 'Model' or GOLD_CORE['guid'] not in value(old, fx.MESH):
        raise ValueError('Expected Wanjun cylinder envelope')
    channels = old.findall(f'./properties/property[@id="{fx.MODEL_SCALE}"]/data/datum/rampchanneldata/rampchannel')
    old_scale = tuple(float(c.find('./keyframes/keyframe').get('value')) for c in channels)
    old_pos = tuple(float(v) for v in value(old, fx.POSITION).split(','))
    length = old_scale[1] * 2.
    tip_y = old_pos[1] - length / 2.
    minimum, maximum = WANJUN_EXTERIOR_CORE['bounds_min'], WANJUN_EXTERIOR_CORE['bounds_max']
    scale = (old_scale[0] / max(abs(minimum[0]), abs(maximum[0])),
             old_scale[2] / max(abs(minimum[1]), abs(maximum[1])),
             length / (maximum[2] - minimum[2]))
    position = (old_pos[0], tip_y + length, old_pos[2])
    core = copy.deepcopy(template)
    core.set('instancename', old.get('instancename'))
    fx.timing(core, float(old.get('start')), float(old.get('end')))
    fx.set_value(core, fx.NAME, value(old, fx.NAME))
    constants(dictionary, core, fx.MODEL_SCALE, scale)
    constants(dictionary, core, INITIAL_ROTATION, (-90, 0, 0))
    scalar(dictionary, core, fx.POSITION, ','.join(f'{v:.9g}' for v in position))
    for key in (fx.MODEL_COLOR, ALPHA, KEYFRAMED_OFFSET):
        dictionary.property(core, key)
        props = core.find('properties')
        previous = props.find(f'property[@id="{key}"]')
        index = list(props).index(previous)
        props.remove(previous)
        props.insert(index, copy.deepcopy(old.find(f'./properties/property[@id="{key}"]')))
    # The native beam material requires the complete X/W ramps. Keep them
    # and Brightness 5 intact, including their active native module entries.
    for key in (MODEL_DYNAMIC, MODEL_BRIGHTNESS):
        dictionary.property(core, key)
        path = f'./properties/property[@id="{key}"]'
        if ET.tostring(core.find(path)) != ET.tostring(template.find(path)):
            raise AssertionError('Native beam dynamic parameters or brightness changed')
    track.remove(old)
    track.append(core)
    return origin, {**WANJUN_EXTERIOR_CORE, 'mapped_axis_scale': scale,
                    'mapped_offset': position, 'pivot_y': position[1],
                    'vertical_interval_at_contact': (tip_y, tip_y + length),
                    'native_dynamic_ramps_retained': True,
                    'replaced_core': dict(GOLD_CORE)}



# The native +Y SpiritualWeapon body is rotated X180 downward. This exact
# scale/pivot mapping preserves the reviewed giant steel body's world AABB;
# the independent Exterior Model and its native X/W/Brightness remain intact.
WANJUN_SPIRITUAL_SWORD = {
    'name': 'SPRW_Greatsword', 'guid': '3727a57a-e4be-44da-02b4-5061028fed5f',
    'axis_scale': (3.4167740237035478, 3.3421464262795793, 9.389975409919609),
    'offset': (7.721677401928417e-7, 6.560559573350793, -.0922998041534766),
    'rotation': (180, 0, 0),
}


def wanjun_native_spiritual_body(root):
    """Adapt only Wanjun's one existing body to the verified native emissive sword."""
    models = root.findall('./trackgroups/trackgroup[@name="Fixed world-ground sword columns"]/track/component')
    if len(models) != 1:
        raise ValueError('Expected one existing Wanjun falling sword body')
    body = models[0]
    mesh = body.find(f'./properties/property[@id="{fx.MESH}"]/data/datum')
    if body.get('class') != 'Model' or mesh.get('value') != f"{GREAT_SWORD['name']} <{GREAT_SWORD['guid']}>":
        raise ValueError('Wanjun native visual replacement expects the verified steel baseline')
    design = WANJUN_SPIRITUAL_SWORD
    mesh.set('value', f"{design['name']} <{design['guid']}>")
    fx.set_value(body, fx.POSITION, ','.join(format(v, '.17g') for v in design['offset']))
    for key, values in ((fx.MODEL_SCALE, design['axis_scale']), (INITIAL_ROTATION, design['rotation'])):
        channels = body.findall(f'./properties/property[@id="{key}"]/data/datum/rampchanneldata/rampchannel')
        if len(channels) != 3:
            raise ValueError('Expected three existing Model transform channels')
        for channel, value in zip(channels, values):
            for frame in channel.findall('./keyframes/keyframe'):
                frame.set('value', format(value, '.17g'))
    return dict(native_spiritual_body=dict(design), native_body_transformed_aabb_preserved=True)


def author_timing_split(data, key, dictionary):
    """Use a one-time lead-in and a stationary loop; contact never falls twice.

    Native phases come from the existing verified Magic Missile donor. Official
    AllSpark documentation assigns the loop its own time interval; all motion
    and opacity are constant in that interval, including both seam endpoints.
    StopLoopEffect transitions the prepare into its 100ms transparent lead-out.
    """
    profile = AUTHORING_PROFILES[key]
    root, origins, design = author(data, profile['base_profile'], dictionary)
    root.set('id', guid('vfx/tianqing-redesign/editor/' + key))
    duration = profile['duration']
    prepare = profile['timing_phase'] == 'prepare'
    if prepare:
        donor, phase_origin = fx.projectile(data)
        phases = copy.deepcopy(donor.find('phases'))
        phase_data = phases.findall('./object/data')
        expected = ('fc34bad5-e4a8-4855-bdd1-ece88d327719',
                    '2d6a16c1-4632-4f7f-8097-4717dc65d7bd',
                    'fc8e9f77-827a-433f-a58d-ad1007605399')
        if tuple(p.get('definitionid') for p in phase_data) != expected:
            raise ValueError('Verified native LeadIn/Loop/LeadOut schema changed')
        for index, (phase, seconds) in enumerate(zip(phase_data, (profile['hit_time'], profile['loop_duration'], profile['stop_fade']))):
            phase.set('id', guid(f'vfx/tianqing-redesign/phase/{key}/{index}'))
            phase.set('duration', format(seconds, '.9g'))
            phase.set('playcount', '-1' if index == 1 else '1')
        root.remove(root.find('phases'))
        root.insert(0, phases)
        origins.append(phase_origin)
    for group_node in list(root.find('trackgroups')):
        for index, track in enumerate(list(group_node.findall('track'))):
            component = track.find('component')
            component.set('instancename', guid(f'vfx/tianqing-redesign/component/{key}/{group_node.get("name")}/{index}'))
            kind = component.get('class')
            if kind == 'ParticleSystem':
                if prepare:
                    group_node.remove(track)
                else:
                    fx.timing(component, 0, .1)
            elif kind == 'Model':
                fx.timing(component, 0, duration)
                if prepare:
                    hit, lead, height, hover = profile['hit_time'], profile['lead_in'], profile['drop_height'], profile['hover_height']
                    fx.replace_ramp(dictionary, component, KEYFRAMED_OFFSET, (
                        [(0, 0), (1, 0)],
                        [(0, height), (lead / duration, height),
                         ((lead + (hit-lead) * .35) / duration, hover + (height-hover) * .85),
                         ((lead + (hit-lead) * .75) / duration, hover + (height-hover) * .45),
                         (hit / duration, hover), ((hit + profile['loop_duration']) / duration, hover), (1, hover)],
                        [(0, 0), (1, 0)],
                    ))
                    fx.replace_ramp(dictionary, component, ALPHA, (
                        [(0, 0), (lead / duration, 1), (hit / duration, 1),
                         ((hit + profile['loop_duration']) / duration, 1), (1, 0)],
                    ))
                else:
                    constants(dictionary, component, KEYFRAMED_OFFSET, (0, 0, 0))
                    fx.replace_ramp(dictionary, component, ALPHA, (
                        [(0, 1), (.2 / duration, 1), (.45 / duration, 0), (1, 0)],
                    ))
            elif kind == 'BoundingSphere':
                fx.timing(component, 0, duration)
            else:
                raise ValueError(f'Unexpected component in timing split: {kind}')
        if not group_node.findall('track'):
            root.find('trackgroups').remove(group_node)
    design.update(timing_phase=profile['timing_phase'], base_profile=profile['base_profile'],
                  has_loop_phase=prepare, descent_in_lead_in_only=prepare,
                  loop_repeats_descent=False, hover_height=profile['hover_height'] if prepare else 0,
                  collision_emitter_start=None if prepare else 0,
                  impact_opacity_peak_time=None if prepare else 0,
                  preview='Not yet visually validated in the client',
                  official_phase_reference='https://docs.baldursgate3.game/VFX_%E2%80%93_Part_1:_Making_Effects')
    return root, origins, design


def author(data, key, dictionary):
    profile = AUTHORING_PROFILES[key]
    if profile.get('timing_phase'):
        return author_timing_split(data, key, dictionary)
    origin = data / NATIVE_REFERENCES['falling_model']['source']
    source = ET.parse(origin).getroot()
    model_template = native_track(source, NATIVE_REFERENCES['falling_model']['component_instance'])
    native_model = model_template.find('component')
    if native_model.get('class') != 'Model' or (float(native_model.get('start')), float(native_model.get('end'))) != (0, .5):
        raise ValueError('SpiritualWeapon downward Model template changed')
    native_offset = native_model.find(f'./properties/property[@id="{fx.POSITION}"]/data/datum').get('value')
    if native_offset != '0,13,0':
        raise ValueError('SpiritualWeapon native downward Offset changed')
    native_mesh = native_model.find(f'./properties/property[@id="{fx.MESH}"]/data/datum').get('value')
    if GOLD_CORE['guid'] not in (native_mesh or ''):
        raise ValueError('SpiritualWeapon native emissive cylinder identity changed')

    root = copy.deepcopy(source)
    root.set('id', guid('vfx/tianqing-redesign/editor/' + key))
    root.find('phases').clear()  # Native non-looping cast/impact timeline, no projectile phases.
    root.find('trackgroups').clear()
    bounding = [t for t in source.findall('./trackgroups/trackgroup/track')
                if t.find('component') is not None and t.find('component').get('class') == 'BoundingSphere']
    if not bounding:
        raise ValueError('Native effect must provide a BoundingSphere')
    bound_track, bound = clone_track(bounding[0], key, 'Ground fall bounds', 0)
    group(root, 'Whole falling effect bounds', 1).append(bound_track)

    duration, hit, height = profile['duration'], profile['hit_time'], profile['drop_height']
    scale = tuple(a * b for a, b in zip(profile['model_axis_scale'], SWORD_VISIBILITY_AXIS_FACTORS))
    # -90 degrees about X sends the native blade's -Z length down -Y.
    # Resource BoundsMin gives a conservative tip-height origin; verify the
    # actual blade tip/material and ground contact in AllSpark before activation.
    tip_height = -GREAT_SWORD['bounds_min'][2] * scale[2]
    layout = sword_layout(profile)
    models = group(root, 'Fixed world-ground sword columns', 2)
    for index, (x, z) in enumerate(layout):
        track, model = clone_track(model_template, key, 'Falling greatsword', index)
        fx.timing(model, 0, duration)
        scalar(dictionary, model, fx.MESH, f"{GREAT_SWORD['name']} <{GREAT_SWORD['guid']}>")
        scalar(dictionary, model, fx.POSITION, f'{x:.9g},{tip_height:.9g},{z:.9g}')
        constants(dictionary, model, fx.MODEL_SCALE, scale)
        constants(dictionary, model, UNIFORM_SCALE, (1,))
        constants(dictionary, model, INITIAL_ROTATION, GREAT_SWORD['initial_rotation_degrees'])
        constants(dictionary, model, ROTATION_RPM, (0, 0, 0))
        constants(dictionary, model, ROTATION_LIFE, (0, 0, 0))
        for prop in ('e2f48d17-b4f1-468d-87c5-0c9cf67e169e', '98d90be4-888a-4fd4-8d36-6a202e67d55b'):
            scalar(dictionary, model, prop, '0,0,0')
        for prop in ('5b7fc64a-bf90-4085-9151-044aa275f590', 'de10ede1-b899-4565-8a4b-eaa258360ee9', 'f009ecca-fae4-49fd-aad3-3224e3ed7e21',
                     '7787b338-8cea-4396-b4d2-fdcf11166dae', '94689e2e-9150-424b-84df-66d79ec5296f', '8c59c30a-e959-4696-8812-cdf69a5d0d2a'):
            scalar(dictionary, model, prop, 1)
        scalar(dictionary, model, 'ccdcf9a0-c9c4-43d1-ae12-1d5950b7d04a', 0)  # SnapToGround must not clamp the descent.
        scalar(dictionary, model, '8771c2c7-091d-4d1f-b7cb-91f87f6a486a', 0)
        constants(dictionary, model, 'ce8b26c1-f96f-4644-914e-ba2ed398654e', (0, 0))
        constants(dictionary, model, MODEL_BRIGHTNESS, (1,))
        packed_gold = (0xff000000 | GOLD[0] << 16 | GOLD[1] << 8 | GOLD[2]) - 0x100000000
        constants(dictionary, model, fx.MODEL_COLOR, (packed_gold,))
        falling_motion(dictionary, model, profile)
        models.append(track)

    # Actual 1CA0 client review found the centered emissive surface hidden by
    # the opaque metal. Expose the same native cylinder outside the rotated
    # cross-section while retaining its length, material and falling motion.
    if tuple(GREAT_SWORD['initial_rotation_degrees']) != (-90, 0, 0):
        raise ValueError('Emissive-shell bounds require the verified -90 degree X pitch')
    sword_length = (GREAT_SWORD['bounds_max'][2] - GREAT_SWORD['bounds_min'][2]) * scale[2]
    metal_half_xz = (
        max(abs(GREAT_SWORD['bounds_min'][0]), abs(GREAT_SWORD['bounds_max'][0])) * scale[0],
        max(abs(GREAT_SWORD['bounds_min'][1]), abs(GREAT_SWORD['bounds_max'][1])) * scale[1],
    )
    shell_minimum_radius = math.hypot(*metal_half_xz) + GOLD_CORE['radial_clearance']
    donor_radial_extent = min(
        max(abs(GOLD_CORE['bounds_min'][0]), abs(GOLD_CORE['bounds_max'][0])),
        max(abs(GOLD_CORE['bounds_min'][2]), abs(GOLD_CORE['bounds_max'][2])),
    )
    quantum = GOLD_CORE['radial_scale_quantum']
    core_radius = math.ceil(shell_minimum_radius / donor_radial_extent / quantum) * quantum
    core_length = sword_length * GOLD_CORE['length_fraction']
    core_pivot_y = GOLD_CORE['tip_clearance'] + core_length / 2
    cores = group(root, 'Gold emissive sword spines', 4)
    for index, (x, z) in enumerate(layout):
        track, core = clone_track(model_template, key, 'Gold emissive sword spine', index)
        fx.timing(core, 0, duration)
        scalar(dictionary, core, fx.MESH, f"{GOLD_CORE['name']} <{GOLD_CORE['guid']}>")
        scalar(dictionary, core, fx.POSITION, f'{x:.9g},{core_pivot_y:.9g},{z:.9g}')
        constants(dictionary, core, fx.MODEL_SCALE, (core_radius, core_length / 2, core_radius))
        constants(dictionary, core, UNIFORM_SCALE, (1,))
        constants(dictionary, core, INITIAL_ROTATION, (0, 0, 0))
        constants(dictionary, core, ROTATION_RPM, (0, 0, 0))
        constants(dictionary, core, ROTATION_LIFE, (0, 0, 0))
        for prop in ('e2f48d17-b4f1-468d-87c5-0c9cf67e169e', '98d90be4-888a-4fd4-8d36-6a202e67d55b'):
            scalar(dictionary, core, prop, '0,0,0')
        for prop in ('5b7fc64a-bf90-4085-9151-044aa275f590', 'de10ede1-b899-4565-8a4b-eaa258360ee9', 'f009ecca-fae4-49fd-aad3-3224e3ed7e21',
                     '7787b338-8cea-4396-b4d2-fdcf11166dae', '94689e2e-9150-424b-84df-66d79ec5296f', '8c59c30a-e959-4696-8812-cdf69a5d0d2a'):
            scalar(dictionary, core, prop, 1)
        scalar(dictionary, core, 'ccdcf9a0-c9c4-43d1-ae12-1d5950b7d04a', 0)
        scalar(dictionary, core, '8771c2c7-091d-4d1f-b7cb-91f87f6a486a', 0)
        constants(dictionary, core, 'ce8b26c1-f96f-4644-914e-ba2ed398654e', (0, 0))
        constants(dictionary, core, fx.MODEL_COLOR, (packed_gold,))
        constants(dictionary, core, MODEL_BRIGHTNESS, (GOLD_CORE['brightness'],))
        falling_motion(dictionary, core, profile)
        cores.append(track)

    shock_origin = data / NATIVE_REFERENCES['shockwave']['source']
    shock_source = ET.parse(shock_origin).getroot()
    shock_template = native_track(shock_source, NATIVE_REFERENCES['shockwave']['component_instance'])
    shocks = group(root, 'Ground collision shockwaves', 3)
    for index, (x, z) in enumerate(layout):
        track, shock = clone_track(shock_template, key, 'Ground collision burst', index)
        # Emit once at contact. Override the native delayed opacity rise so
        # serialized opacity is maximal at hit_time; expansion follows contact.
        # The ring uses a fixed authored .6s lifespan after this .1s emitter window.
        fx.timing(shock, hit, hit + .1)
        scalar(dictionary, shock, PARTICLE_OFFSET, f'{x:.9g},0,{z:.9g}')
        scalar(dictionary, shock, fx.INITIAL_COUNT, '1,1')
        fx.ramp_edit(dictionary, shock, fx.EMIT_RATE, lambda channel, value: 0)
        constants(dictionary, shock, fx.LIFESPAN, (.6, .6))
        wave_scale = profile['shockwave_scale_factor']
        # XCD identifies these as Min Scale / Max Scale. Equal curves keep
        # particle size deterministic rather than retaining the native max=0.
        wave_curve = [(0, .45 * wave_scale), (.2, 2 * wave_scale), (1, 3 * wave_scale)]
        fx.replace_ramp(dictionary, shock, fx.PARTICLE_SCALE, (
            wave_curve, wave_curve,
        ))
        fx.replace_ramp(dictionary, shock, PARTICLE_ALPHA, (
            [(0, 1), (.05, 1), (.4, .4), (1, 0)],
        ))
        fx.recolor(dictionary, shock, fx.PARTICLE_COLOR, GOLD)
        shocks.append(track)

    # Conservatively cover the highest hilt, all ring columns, and native burst
    # expansion from world-ground origin. No small actor-body culling sphere.
    highest = height + sword_length
    radial = profile['layout_radius'] + math.hypot(
        max(abs(GREAT_SWORD['bounds_min'][0]), abs(GREAT_SWORD['bounds_max'][0])) * scale[0],
        max(abs(GREAT_SWORD['bounds_min'][1]), abs(GREAT_SWORD['bounds_max'][1])) * scale[1])
    bound_radius = max(math.hypot(highest, radial), profile['layout_radius'] + 3 * profile['shockwave_scale_factor']) + 3
    fx.bounds(dictionary, root, bound_radius, duration)
    origins = [origin, shock_origin]
    exterior_design = {}
    native_body_design = {}
    if key == 'tianqing_wanjun':
        exterior_origin, exterior_design = wanjun_exterior_core(data, root, dictionary)
        origins.append(exterior_origin)
        native_body_design = wanjun_native_spiritual_body(root)
    from sword_glow import apply as apply_glow
    glow_design = apply_glow(root,dictionary,'tianqing')
    return root, origins, {
        **glow_design,
        'model_pivot_y': (WANJUN_SPIRITUAL_SWORD['offset'][1] if native_body_design else tip_height), 'layout_positions_xz': layout,
        'bounds_center': (0, 0, 0), 'bounds_radius': bound_radius,
        'top_of_model_at_start': highest, 'particle_emit_duration': .1,
        'authored_particle_lifespan': .6,
        'native_lifespan_reference': NATIVE_REFERENCES['shockwave']['native_lifespan_reference'],
        'collision_emitter_start': hit, 'impact_opacity_peak_time': hit,
        'impact_opacity_peak_basis': 'Serialized particle opacity is maximal at hit_time; this is not the overall visual peak',
        'visual_peak_validation': 'Not run: expanding ring and retained native Brightness curve peak after contact; client timing and combined rendered peak are unverified',
        'has_loop_phase': False, 'bank_repetitions': 1,
        'mesh_axis_verification': ('SPRW_Greatsword native +Y long axis, X180 maps the blade toward world -Y; transformed AABB matches the reviewed steel body' if native_body_design else GREAT_SWORD['blade_direction_evidence']),
        'rendered_model_axis_scale': (WANJUN_SPIRITUAL_SWORD['axis_scale'] if native_body_design else scale),
        'visibility_axis_factors': SWORD_VISIBILITY_AXIS_FACTORS,
        'gold_core': {**GOLD_CORE, 'count': len(layout), 'length': core_length,
                      'radius': core_radius, 'pivot_y': core_pivot_y,
                      'metal_half_extents_xz': metal_half_xz,
                      'minimum_shell_radius': shell_minimum_radius,
                      'color_rgba': (*GOLD, 255), 'motion_matches_body': True, **exterior_design},
        'visibility_reason': ('F80C Wanjun cylinder shell remained invisible; use the native Exterior_02 beam with its required dynamic ramps' if exterior_design else '1CA0 client replay showed a readable opaque sword but no gold spine; expose the same native emissive cylinder beyond the metal cross-section'),
        **native_body_design,
        'visibility_validation': ('Candidate authoring only; normal-speed client review is required for blade silhouette, native hue, and bloom' if native_body_design else 'Candidate authoring only; normal-speed client review is required for blade silhouette, gold tint, and bloom'),
    }


def verify_stats_names():
    names = set()
    import re
    for path in (SOURCE / 'Public' / FOLDER / 'Stats/Generated/Data').glob('Spell_*.txt'):
        names.update(re.findall(r'^new entry "([^"]+)"', path.read_text(encoding='utf-8'), re.M))
    planned = [name for plan in TIANQING_BINDING_PLAN for name in plan['stats_names']]
    planned += [name for values in PRESERVED_ENTRIES.values() for name in values]
    missing = sorted(set(planned) - names)
    if missing:
        raise ValueError(f'Binding plan contains unknown generated Stats names: {missing}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=DATA)
    parser.add_argument('--profiles', nargs='+', choices=[key for key, p in AUTHORING_PROFILES.items() if p['authoring_enabled']])
    args = parser.parse_args()
    verify_stats_names()
    dictionary = fx.PropertyDictionary(args.data)
    selected = list(dict.fromkeys(args.profiles or [key for key, p in AUTHORING_PROFILES.items() if p['authoring_enabled']]))
    records = []
    for key in selected:
        root, origins, design = author(args.data, key, dictionary)
        profile = AUTHORING_PROFILES[key]
        path = OUTPUT / (profile['effect_name'] + '.lsefx')
        fx.write(path, root)
        records.append({
            'profile': key, 'effect_name': profile['effect_name'],
            'source': str(path.relative_to(REPO)).replace('\\', '/'), 'sha256': fx.digest(path),
            'compiled': False, 'binding_enabled': False, 'resource_registered': False,
            'mei_written': False, 'toolkit_preview': 'not-run', 'game_test': 'not-run',
            'profile_design': profile, 'serialized_design': design,
            'origins': [{'path': str(p), 'sha256': fx.digest(p)} for p in origins],
        })
    reference_evidence = []
    for reference in ('target_ground', 'source_cast'):
        path = args.data / NATIVE_REFERENCES[reference]['mei_source']
        mei = ET.parse(path).getroot()
        if mei.get('UUID') != NATIVE_REFERENCES[reference]['mei_guid']:
            raise ValueError(f'Native MEI identity changed: {path}')
        reference_evidence.append({'role': reference, 'path': str(path), 'sha256': fx.digest(path),
                                   'effect_infos': [dict(item.attrib) for item in mei.findall('EffectInfo')]})
    manifest = {
        'schema_version': 1, 'date': '2026-10-07', 'scope': 'authoring-source-and-plan-only',
        'subdirectory': 'Tianqing',
        'compiled': False, 'binding_enabled': False,
        'source_output_directory': str(OUTPUT.relative_to(REPO)).replace('\\', '/'),
        'records': records, 'binding_plan': TIANQING_BINDING_PLAN, 'preserved_entries': PRESERVED_ENTRIES,
        'native_references': NATIVE_REFERENCES, 'native_mei_evidence': reference_evidence,
        'mesh_evidence': {**GREAT_SWORD, 'resource_cache_sha256': fx.digest(REPO / GREAT_SWORD['resource_evidence'])},
        'property_dictionary': dictionary.evidence(),
        'official_docs': [
            'https://docs.baldursgate3.game/VFX_%E2%80%93_Part_1:_Making_Effects',
            'https://docs.baldursgate3.game/Projectiles',
            'https://docs.baldursgate3.game/index.php?title=VFX_%E2%80%93_Part_3:_Assigning_and_Testing_Effects',
        ],
        'remaining': [
            'AllSpark preview: confirm greatsword blade direction, materials, impact contact, low-quality visibility, and full bounds',
            'Compile new .lsefx to real .lsfx using Toolkit; only then create matching effect resources and MEIs',
            'Validate field support, attachment transforms, textkeys, hit timing, and once-per-cast behavior for every execution context',
            'Resolve Lietian projectile execution and Tiandi area-wide visual stage coordinator before enabling either binding',
            'Tianjian landing/aftershock and Bafang Shout field behavior require native/client validation',
            'Bafang currently shares the anchor Y flat plane across eight columns; individual ground heights on slopes or stairs are not sampled. Resolve per-column sampling or a verified native ground-contact method before activation; do not clamp the entire animated descent with SnapToGround',
            'Preview the retained native shockwave camera/velocity alignment flags and verify the expanding ring faces the ground',
        ],
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Authored {len(records)} new Tianqing .lsefx sources; compiled=false, binding_enabled=false.')


if __name__ == '__main__':
    main()
