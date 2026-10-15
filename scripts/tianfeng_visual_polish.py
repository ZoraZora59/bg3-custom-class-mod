"""A caster-attached greatsword held for Tianfeng's whole native Rush action.

TianqingCastVfx owns one Dummy_Root loop until CastedSpell or cancellation.
The effect has no world path, damage, projectile, or gameplay status.
Its luminous sword uses the same native GR2/material proven by the H18 falls.
"""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

from sword_cultivator_spec import guid
from tianqing_vfx_design import GREAT_SWORD
from sword_glow import visual_id

_spec = importlib.util.spec_from_file_location(
    'tianfeng_fall_authoring', Path(__file__).with_name('generate-tianqing-vfx.py'))
fall = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fall)
fx = fall.fx

KEY = 'tianqing_tianfeng_cast'
LEAD_IN, LOOP, LEAD_OUT = .10, .10, .30
DURATION = LEAD_IN + LOOP + LEAD_OUT
SWORD_SCALE = (4.8, 4., 2.45)
SWORD_POSITION = (0., 1.1, .1)
RUSH = fx.BASE / 'Actions/Cast/WeaponAttack/VFX_Actions_Cast_WeaponAttack_Rush_Rush_Root_01.lsefx'
RUSH_TRACK = '9c9b1439-0117-4033-a4f6-025a5ebe47d4'
RUSH_MESH = '2d26f787-71aa-cdc3-b93e-482a40fe7ad6'
PROFILES = {
    KEY: dict(skill='tianqing_tianfeng', phase='cast', label='天锋破阵：巨剑锋楔',
              binding='cast', presentation='金色巨剑随角色沿冲阵方向前推，两侧低亮气流分开，停步后迅速退亮。',
              motion='caster_attached_forward_wedge', sword_count=1,
              lifecycle='attached-until-casted'),
}


def author(data: Path, key: str, dictionary):
    if key != KEY:
        raise KeyError(key)
    # Reuse the verified static sword component, then remove its entire falling
    # path, floor burst and auxiliary glow shell before attaching it to a Rush.
    root, origins, _ = fall.author(data, 'tianqing_lietian', dictionary)
    root.set('id', guid('vfx/visual-polish/tianfeng/editor/' + key))
    sword = None
    for group in list(root.find('trackgroups')):
        for track in list(group.findall('track')):
            component = track.find('component')
            mesh = component.find(f'./properties/property[@id="{fx.MESH}"]/data/datum')
            if component.get('class') == 'Model' and mesh is not None and visual_id('tianqing') in mesh.get('value', ''):
                if sword is not None:
                    raise ValueError('Tianfeng requires precisely one sword donor')
                sword = component
                track.set('name', 'Tianfeng forward greatsword')
                component.set('instancename', guid('vfx/tianfeng/component/sword'))
                fx.set_value(component, fx.NAME, track.get('name'))
            elif component.get('class') == 'BoundingSphere':
                component.set('instancename', guid('vfx/tianfeng/component/bounds'))
            else:
                group.remove(track)
        if not group.findall('track'):
            root.find('trackgroups').remove(group)
    if sword is None:
        raise ValueError('Verified native greatsword donor missing')
    donor, phase_origin = fx.projectile(data)
    phases = copy.deepcopy(donor.find('phases'))
    phase_data = phases.findall('./object/data')
    expected = ('fc34bad5-e4a8-4855-bdd1-ece88d327719',
                '2d6a16c1-4632-4f7f-8097-4717dc65d7bd',
                'fc8e9f77-827a-433f-a58d-ad1007605399')
    if tuple(p.get('definitionid') for p in phase_data) != expected:
        raise ValueError('Verified native LeadIn/Loop/LeadOut schema changed')
    for index, (phase, seconds) in enumerate(zip(phase_data, (LEAD_IN, LOOP, LEAD_OUT))):
        phase.set('id', guid(f'vfx/tianfeng/phase/{index}'))
        phase.set('duration', format(seconds, '.9g'))
        phase.set('playcount', '-1' if index == 1 else '1')
    root.remove(root.find('phases'))
    root.insert(0, phases)
    origins.append(phase_origin)
    # Define this horizontal pose in the original steel coordinate frame;
    # the shared glow pass then maps it to the proven native luminous GR2.
    fall.scalar(dictionary, sword, fx.MESH, f"{GREAT_SWORD['name']} <{GREAT_SWORD['guid']}>")
    fx.timing(sword, 0, DURATION)
    fall.scalar(dictionary, sword, fx.POSITION, ','.join(map(str, SWORD_POSITION)))
    fall.constants(dictionary, sword, fx.MODEL_SCALE, SWORD_SCALE)
    fall.constants(dictionary, sword, fall.INITIAL_ROTATION, (0, 0, 0))
    fall.constants(dictionary, sword, fall.KEYFRAMED_OFFSET, (0, 0, 0))
    fx.replace_ramp(dictionary, sword, fall.ALPHA, (
        [(0, 0), (.035 / DURATION, 1), ((LEAD_IN + LOOP) / DURATION, 1), (1, 0)],))

    # The native Rush's forward ogive meshes supply two faint side contours.
    # Their zero local path means they cannot outrun a blocked/stopped actor.
    rush_path = data / RUSH
    rush_root = ET.parse(rush_path).getroot()
    donor = fall.native_track(rush_root, RUSH_TRACK)
    native = donor.find('component')
    mesh = native.find(f'./properties/property[@id="{fx.MESH}"]/data/datum')
    if native.get('class') != 'Model' or mesh is None or RUSH_MESH not in mesh.get('value', ''):
        raise ValueError('Verified native Rush contour changed')
    contours = fall.group(root, 'Tianfeng low-brightness side streams', 3)
    packed_gold = (0xff000000 | 255 << 16 | 183 << 8 | 35) - 0x100000000
    for index, side in enumerate((-1, 1)):
        track = copy.deepcopy(donor)
        track.set('muted', 'False'); track.set('mutestateoverride', 'Unmuted')
        track.set('name', f'Tianfeng side stream {index + 1}')
        component = track.find('component')
        component.set('instancename', guid(f'vfx/tianfeng/component/side/{index}'))
        fx.set_value(component, fx.NAME, track.get('name'))
        fx.timing(component, 0, DURATION)
        fall.scalar(dictionary, component, fx.POSITION, f'{side * .62},.85,-1.5')
        fall.constants(dictionary, component, fx.MODEL_SCALE, (.38, .55, .55))
        fall.constants(dictionary, component, fall.KEYFRAMED_OFFSET, (0, 0, 0))
        fall.constants(dictionary, component, fall.ROTATION_RPM, (0, 0, 0))
        fall.constants(dictionary, component, fall.ROTATION_LIFE, (0, 0, 0))
        fall.constants(dictionary, component, fx.MODEL_COLOR, (packed_gold,))
        fall.constants(dictionary, component, fall.MODEL_BRIGHTNESS, (1.,))
        fx.replace_ramp(dictionary, component, fall.ALPHA, (
            [(0, 0), (.06 / DURATION, .18), ((LEAD_IN + LOOP) / DURATION, .18), (1, 0)],))
        contours.append(track)
    fx.bounds(dictionary, root, 6, DURATION)
    origins.append(rush_path)
    details = dict(
        sword_count=1, steel_reference_scale=SWORD_SCALE,
        steel_reference_position=SWORD_POSITION,
        sword_length=(GREAT_SWORD['bounds_max'][2] - GREAT_SWORD['bounds_min'][2]) * SWORD_SCALE[2],
        direction='caster local -Z', duration=DURATION, fade_in=.035,
        fade_start=LEAD_IN + LOOP, fade_end=DURATION, loop=True,
        lead_in=LEAD_IN, loop_duration=LOOP, stop_fade=LEAD_OUT,
        side_stream_count=2, side_stream_max_alpha=.18,
        caster_attachment='PlayLoopEffect(caster, effect, Dummy_Root, 1); stop on CastedSpell/cancel',
        world_path=False, gameplay_changed=False, giant_sword_count=1,
        expected_motion='Follows actual Rush root transform, including collision stops; bounded fade after release',
        remaining='Native rendered direction, actor attachment, full/blocked rush and end fade acceptance',
    )
    return root, origins, details
