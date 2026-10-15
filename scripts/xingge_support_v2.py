"""Four build-only support VFX candidates; no compiler, binding or installation.

Reuse xingge's native Model/ParticleSystem donors, SwordGlow's proven transform
conversion, and the existing owned jade sword/circle materials unchanged.
The additional halo Visual uses the same native Spiritual Weapon mesh. Its
combination with the softer circle material is a proposal, not rendered proof.
"""
from __future__ import annotations

import copy
import itertools
import math
import xml.etree.ElementTree as ET

import sword_glow as glow
import sword_vfx_resources as resources
import xingge_visual_polish as xg
from sword_cultivator_spec import guid

fx, tx = xg.fx, xg.tx
HALO_VISUAL = guid('vfx/xingge/support-v2/halo')
HALO_NAME = 'ESC_Xingge_Support_SwordHalo'
CORE_SCALE = (1.25, .85, .9)
HALO_AXIS_MULTIPLIERS = (1.85, 1.08, 2.0)  # native +Y is the blade axis

# Samples are (seconds, radius metres, height metres, rotation of the open arcs).
# Only the existing Model Offset ramp moves. Blade orientation stays constant,
# preserving the proven luminous conversion and avoiding new Euler spin logic.
DESIGNS = {
    'xingge_huifeng_target': dict(
        motif='two protective arcs sweep into a stable guard',
        duration=1.8, core_end=1.5, pitch=10, direction='tangent',
        orientation_angle_offset=25,
        path=((0, 1.2, .85, 0), (.18, 1.4, .95, 8),
              (.6, 1.6, 1.05, 32), (1.05, 1.5, 1.05, 50),
              (1.5, 1.5, 1.05, 50), (1.8, 1.5, 1.05, 50)),
        alpha=((0, 0), (.08, .62), (.30, .92), (1.05, .82), (1.5, 0)),
        halo_alpha=((0, 0), (.10, .60), (.35, .72), (1.35, .46), (1.8, 0))),
    'xingge_chengfeng_target': dict(
        motif='six outward blades open a clear escape corridor',
        duration=1.65, core_end=1.35, pitch=8, direction='outward',
        orientation_angle_offset=0,
        path=((0, .55, .55, 0), (.10, .85, .60, 0),
              (.42, 2.35, .70, 0), (.68, 2.70, .75, 0),
              (1.35, 2.70, .75, 0), (1.65, 2.70, .75, 0)),
        alpha=((0, 0), (.06, .68), (.30, .94), (.70, .80), (1.35, 0)),
        halo_alpha=((0, 0), (.09, .64), (.32, .74), (1.12, .44), (1.65, 0))),
    'xingge_fuchen_target': dict(
        motif='raised blades lift a cleansing wave from feet to above shoulders',
        duration=1.75, core_end=1.45, pitch=60, direction='tangent',
        orientation_angle_offset=10,
        path=((0, 1.1, .25, 0), (.18, 1.2, .60, 3),
              (.65, 1.25, 1.50, 10), (1.15, 1.1, 2.45, 20),
              (1.45, 1.0, 2.55, 20), (1.75, 1.0, 2.55, 20)),
        alpha=((0, 0), (.10, .66), (.40, .90), (.95, .84), (1.45, 0)),
        halo_alpha=((0, 0), (.12, .60), (.45, .72), (1.20, .48), (1.75, 0))),
    'xingge_xiangfu_target': dict(
        motif='six inward blades gather into a brief healing cradle',
        duration=1.7, core_end=1.4, pitch=15, direction='inward',
        orientation_angle_offset=0,
        path=((0, 1.8, .55, 0), (.15, 1.60, .75, 0),
              (.55, .90, 1.00, 0), (.85, .55, 1.05, 0),
              (1.40, .55, 1.05, 0), (1.70, .55, 1.05, 0)),
        alpha=((0, 0), (.08, .56), (.55, .84), (.85, .94), (1.10, .84), (1.4, 0)),
        halo_alpha=((0, 0), (.10, .48), (.55, .66), (.85, .76), (1.35, .48), (1.7, 0))),
}


def _constant(c, key, values, dictionary):
    tx._constant(dictionary, c, key, values)


def _centered_transform(c, steel_angles, scale_multiplier, dictionary):
    """Rotate/resize the already-converted sword about its actual mesh centre."""
    before_scale = tx._native_constant_values(c, fx.MODEL_SCALE)
    before_rotation = glow._rotation(tx._native_constant_values(c, tx.MODEL_ROTATION))
    after_rotation = glow._mul(glow._rotation(steel_angles), glow._rotation((-90, 0, 0)))
    after_scale = tuple(a * b for a, b in zip(before_scale, scale_multiplier))
    centre = tuple((a + b) / 2 for a, b in zip(tx.NATIVE_SWORD['minimum'], tx.NATIVE_SWORD['maximum']))
    prop = c.find(f'./properties/property[@id="{fx.POSITION}"]/data/datum')
    position = tuple(map(float, prop.get('value').split(',')))
    delta = tuple(sum(before_rotation[i][j] * centre[j] * before_scale[j]
                      - after_rotation[i][j] * centre[j] * after_scale[j]
                      for j in range(3)) for i in range(3))
    tx._scalar(dictionary, c, fx.POSITION, ','.join(format(position[i] + delta[i], '.12g') for i in range(3)))
    _constant(c, fx.MODEL_SCALE, after_scale, dictionary)
    _constant(c, tx.MODEL_ROTATION, glow._euler(after_rotation), dictionary)


def _offsets(design, angle):
    points = []
    for seconds, radius, height, turn in design['path']:
        a = math.radians(angle + turn)
        points.append((seconds / design['duration'], radius * math.cos(a), height, radius * math.sin(a)))
    return tuple([(p[0], p[axis + 1]) for p in points] for axis in range(3))


def _alpha(c, keys, duration, dictionary):
    points = [(seconds / duration, value) for seconds, value in keys]
    if points[-1][0] < 1:
        points.append((1, 0))
    fx.replace_ramp(dictionary, c, tx.MODEL_ALPHA, (points,))


def _model_extent(c):
    scale = tx._native_constant_values(c, fx.MODEL_SCALE)
    rotation = glow._rotation(tx._native_constant_values(c, tx.MODEL_ROTATION))
    position = tuple(map(float, c.find(f'./properties/property[@id="{fx.POSITION}"]/data/datum').get('value').split(',')))
    channels = c.findall(f'./properties/property[@id="{tx.MODEL_OFFSET}"]/data/datum/rampchanneldata/rampchannel')
    offsets = [tuple(float(k.get('value')) for k in channel.findall('./keyframes/keyframe')) for channel in channels]
    return max(math.sqrt(sum((position[i] + offset[i] + sum(rotation[i][j] * corner[j] * scale[j] for j in range(3))) ** 2 for i in range(3)))
               for offset in zip(*offsets) for corner in itertools.product(*zip(tx.NATIVE_SWORD['minimum'], tx.NATIVE_SWORD['maximum'])))


def author(data, key, dictionary):
    design = DESIGNS[key]
    profile = copy.deepcopy(xg.PROFILES[key])
    profile.update(model_scale=CORE_SCALE, duration=design['duration'])
    root, origins, details = xg._paired_arcs(data, key, profile, dictionary)
    glow_proof = glow.apply(root, dictionary, 'xingge')
    cores = root.findall('./trackgroups/trackgroup/track/component[@class="Model"]')
    assert len(cores) == 6 and glow_proof['luminous_swords'] == 6
    halo_group = tx._group(root, 'Six soft owned jade sword halos; no extra attacks', 73)
    for index, (core, angle) in enumerate(zip(cores, xg.ARC_ANGLES)):
        turn = design['orientation_angle_offset']
        yaw = -angle - turn + {'tangent': 0, 'outward': -90, 'inward': 90}[design['direction']]
        steel_angles = (design['pitch'], yaw, 0)
        _centered_transform(core, steel_angles, (1, 1, 1), dictionary)
        _constant(core, tx.MODEL_BRIGHTNESS, (1.6,), dictionary)
        fx.replace_ramp(dictionary, core, tx.MODEL_OFFSET, _offsets(design, angle))
        _alpha(core, design['alpha'], design['duration'], dictionary)
        # Keep the identical lifetime scale for offset ramps. Core alpha reaches
        # zero first; the same-path halo remains briefly, never a second event.
        original_track = next(t for t in root.findall('./trackgroups/trackgroup/track')
                              if t.find('component') is core)
        track = copy.deepcopy(original_track)
        halo = track.find('component')
        _centered_transform(halo, steel_angles, HALO_AXIS_MULTIPLIERS, dictionary)
        fx.set_value(halo, fx.MESH, f'{HALO_NAME} <{HALO_VISUAL}>')
        _constant(halo, tx.MODEL_BRIGHTNESS, (2.5,), dictionary)
        _alpha(halo, design['halo_alpha'], design['duration'], dictionary)
        halo_group.append(track)
    for index, track in enumerate(root.findall('./trackgroups/trackgroup/track')):
        c = track.find('component')
        layer = 'soft halo' if track in halo_group.findall('track') else 'core/native detail'
        label = f'{key} v2 {layer} {index + 1}'
        track.set('name', label)
        track.set('muted', 'False')
        track.set('mutestateoverride', 'Unmuted')
        c.set('instancename', guid(f'vfx/visual-polish/support-v2/{key}/{index}'))
        fx.set_value(c, fx.NAME, label)
    models = root.findall('./trackgroups/trackgroup/track/component[@class="Model"]')
    radius = max(_model_extent(c) for c in models) + .5
    fx.bounds(dictionary, root, round(radius, 6), design['duration'])
    root.set('id', guid('vfx/polish/editor/' + key))
    details.update(design=copy.deepcopy(design), duration=design['duration'],
                   sword_count=6, halo_model_count=6, core_scale=CORE_SCALE,
                   motion=design['motif'], local_radius=max(p[1] for p in design['path']),
                   maximum_model_alpha=max(a for _, a in design['alpha']),
                   halo_peak_alpha=max(a for _, a in design['halo_alpha']),
                   core_brightness=1.6, halo_brightness=2.5, bound_radius=round(radius, 6),
                   additional_visual=HALO_VISUAL, existing_material=glow.material_id('xingge', 'circle'),
                   material_parameters_changed=False, looping=False, compiled=False,
                   produces_damage=False, gameplay_changed=False, automatic_event_replay=False,
                   recipient=profile['recipient'], trigger=profile['trigger'],
                   core_end=design['core_end'], halo_end=design['duration'],
                   native_visual_acceptance='NOT_TESTED')
    return root, origins, details


def visual_bank():
    """One source-only Visual registration; existing materials remain byte-identical."""
    root, parent = resources._document('VisualBank')
    child = ET.SubElement(parent, 'children')
    node = copy.deepcopy(ET.parse(glow.TEMPLATES).getroot().find('Sword/node'))
    for key, value in [('ID', HALO_VISUAL), ('Name', HALO_NAME)]:
        node.find(f'./attribute[@id="{key}"]').set('value', value)
    for obj in node.findall('./children/node[@id="Objects"]'):
        obj.find('./attribute[@id="MaterialID"]').set('value', glow.material_id('xingge', 'circle'))
    child.append(node)
    return root
