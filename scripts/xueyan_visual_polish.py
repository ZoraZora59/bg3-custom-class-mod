"""Author blood-sword accents from verified native AllSpark components.

This module only returns editable XML. It never writes files, enables bindings,
changes attacks, or creates actors. A continuation bank represents one actual
attack, never a prerecorded four/six-hit sequence. Smoke keeps BloodPuff's
native white/grey colour, red material, flipbook and 1.5--2 second lifetime.
Compilation, owner attachment, ground contact and visual timing need separate
verification. Official authoring workflow:
https://docs.baldursgate3.game/VFX_%E2%80%93_Part_1:_Making_Effects
"""
from __future__ import annotations

import copy
import importlib.util
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from sword_cultivator_spec import guid

_spec = importlib.util.spec_from_file_location(
    'xueyan_native_authoring', Path(__file__).with_name('generate-sword-vfx.py'))
fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fx)

PARTICLE_POSITION = 'a14d2803-fec4-4015-9e37-eb67e1c2f1d8'
PARTICLE_OFFSET = '726ea55f-d0f9-4176-9a22-c5539199a83a'
PARTICLE_ALPHA = 'd1892ce7-07f3-4d9c-9acb-6692b897a71b'
SPACE = 'b13c2ffd-c94f-4d56-947e-07077287ec52'
MODEL_POSITION = '37b047c1-8fb7-4e7c-9319-58db9da44e77'
MODEL_ROTATION = '4a72a815-57fb-4fcb-9a50-1024331ce66a'
MODEL_ALPHA = '00910be4-aaa1-41a2-946f-735d33de387b'
PARTICLE_EFFECT_COLOR = 'bb1e9c04-b4b9-4407-af31-effec5a9d46a'
PARTICLE_BRIGHTNESS = '7b01f163-d329-4cd0-97f0-31115055b9c8'
PARTICLE_EFFECT_BRIGHTNESS = '1dc673ff-bbe4-4852-9615-78cd6a835d19'
MODEL_BRIGHTNESS = '6cbb9e51-0d17-4916-9666-30d8c7b47e81'
COLOR_LIFE_MODULE = 'bf4bb6b1-21ad-4f8b-adfb-581a277c8ccb'
CRIMSON_CORE_INSTANCE = 'ae6913c4-8ffe-47b5-a1e8-66608961bc58'
SMOKE_INSTANCE = 'dbcba590-de6e-495a-b8ec-1374569d8a7e'
BLADE = (255, 42, 62)
DEEP_RED = (214, 39, 61)


def _profile(skill, phase, label, presentation, **settings):
    return dict(skill=skill, phase=phase, label=label,
                binding='hit' if phase == 'impact' else phase,
                presentation=presentation, **settings)


PROFILES = {
    'xueyan_luexue_hit': _profile('xueyan_luexue', 'impact', '掠血·撕雾',
        'A narrow bright blood blade cuts first; a restrained red puff follows.',
        slash_scale=.8, slash_life=.45, mist_scale=.68, mist_alpha=1., sword_count=1, crimson_core_width=1.6),
    'xueyan_chuanshen_hit': _profile('xueyan_chuanshen', 'impact', '血影穿身·贯斩',
        'A stretched piercing blood blade and a small torn mist at each real victim.',
        slash_scale=1.05, slash_life=.42, mist_scale=.32, mist_alpha=.7, sword_count=1),
    'xueyan_liancheng_hit': _profile('xueyan_liancheng', 'impact', '血影连城·单段',
        'One sharp blade peak per real pursuit attack; no four-stage playback.',
        slash_scale=.92, slash_life=.4, mist_scale=.3, mist_alpha=.66, sword_count=1),
    'xueyan_wusheng_hit': _profile('xueyan_wusheng', 'impact', '血魇无生·单段',
        'One pale crimson blade through deep red mist per real attack; no six-stage playback.',
        slash_scale=1.15, slash_life=.38, mist_scale=.32, mist_alpha=.72, sword_count=1),
    'xueyan_nixue_cast': _profile('xueyan_nixue', 'cast', '逆血狂澜·放卷',
        'Eight short blood blades spread once toward the six-metre boundary and fold inward.',
        sword_count=8, radius=5.5, motion='out_return', mist_scale=.23, mist_alpha=.58,
        sword_model_scale=(.8, .65, 1.05), sword_seconds=1.0,
        sword_alpha_keys=((0, 0), (.09, .94), (.40, .90),
                          (.65, .80), (.90, 0), (1, 0))),
    'xueyan_xuehai_cast': _profile('xueyan_xuehai', 'cast', '血海噬灵·开域',
        'A low circle of blood blades opens once; no per-victim domain replay.',
        sword_count=8, radius=5.6, motion='out', mist_scale=.18, mist_alpha=.42,
        crimson_blade_light=False, sword_model_scale=(1.4, 1.0, .68)),
    'xueyan_xuehai_hit': _profile('xueyan_xuehai', 'impact', '血海噬灵·噬灵斩',
        'A small local blood cut for each actual BloodPulse hit.',
        slash_scale=.65, slash_life=.42, mist_scale=.25, mist_alpha=.6, sword_count=0),
    'xueyan_xuehai_status': _profile('xueyan_xuehai', 'status', '血海噬灵·赤环血雾',
        'An open luminous crimson ring and twelve low red wisps mark the six-metre owner-following boundary.',
        sword_count=0, radius=6, mist_scale=.24, mist_alpha=.45,
        boundary_alpha=.45, boundary_brightness=.8),
    'xueyan_ranxue_cast': _profile('xueyan_ranxue', 'cast', '燃血入狂·内聚',
        'Four short blood blades and wisps pull inward, then extinguish.',
        sword_count=4, radius=1.4, motion='in', mist_scale=.24, mist_alpha=.65,
        crimson_blade_light=False, sword_model_scale=(1.4, 1.0, .68)),
    'xueyan_huichao_cast': _profile('xueyan_huichao', 'cast', '回潮·回卷',
        'Six crimson wisps and luminous blood threads converge into the chest, hold briefly and fade for both costs.',
        sword_count=0, radius=2.1, motion='in', mist_scale=.42, mist_alpha=.88,
        mist_count=6, convergence_height=1.15, recovery_threads=6,
        recovery_thread_scale=.85, recovery_thread_width=.9, recovery_thread_brightness=8),
    'xueyan_damage_mode_cast': _profile('xueyan_damage_mode', 'cast', '血剑凝锋·切换',
        'One brief bright blood-blade accent; the red identity survives either damage mode.',
        sword_count=1, radius=.45, motion='in', mist_scale=.18, mist_alpha=.55),
}


def _constant(dictionary, component, key, values):
    fx.replace_ramp(dictionary, component, key,
                    tuple([(0, v), (1, v)] for v in values))


def _scalar(dictionary, component, key, value):
    dictionary.property(component, key)
    fx.set_value(component, key, value)


def _blood_particle_color(dictionary, component):
    """Edit the actual native active colour module, including its HDR multiplier.

    BladeFlourish's mesh swoosh has Color Over Effect Life enabled, a blue/purple
    colour ramp, and brightness 100 -> 20 -> 3. Ordinary Particle Color alone
    leaves that active presentation intact. Sparks and directional flares use
    ordinary Color instead. Both module/property IDs come from installed XCD/
    XMD; no shader or material override is fabricated.
    """
    effect_life = any(m.get('id', '').lower() == COLOR_LIFE_MODULE
                      and m.get('muted') == 'False'
                      for m in component.findall('./modules/module'))
    if effect_life:
        fx.recolor(dictionary, component, PARTICLE_EFFECT_COLOR, BLADE)
        # 1CA0's constant 2.3 was too dim in actual client review. Retain the
        # verified native HDR envelope while changing its active hue to red.
        fx.replace_ramp(dictionary, component, PARTICLE_EFFECT_BRIGHTNESS,
                        ([(0, 100), (.2726081, 20), (1, 3)],))
    else:
        fx.recolor(dictionary, component, fx.PARTICLE_COLOR, BLADE)
        # Preserve each donor's own particle brightness rather than applying
        # one low envelope to both sparks and directional emissive flares.


def _group(root, label):
    result = ET.SubElement(root.find('trackgroups'), 'trackgroup', name=label)
    ET.SubElement(ET.SubElement(result, 'ids'), 'id', value=str(len(root.find('trackgroups')) + 80))
    return result


def _clone(template, key, label, index):
    track = copy.deepcopy(template)
    track.set('muted', 'False')
    track.set('mutestateoverride', 'Unmuted')
    track.set('name', f'{label} {index + 1}')
    component = track.find('component')
    component.set('instancename', guid(f'vfx/xueyan-polish/{key}/{label}/{index}'))
    fx.set_value(component, fx.NAME, track.get('name'))
    return track, component


def _base(data, key):
    root, origin = fx.impact(data)
    root.set('id', guid('vfx/xueyan-polish/editor/' + key))
    root.find('phases').clear()
    for group in list(root.find('trackgroups')):
        for track in list(group.findall('track')):
            component = track.find('component')
            if component is None or component.get('class') != 'BoundingSphere':
                group.remove(track)
            else:
                component.set('instancename', guid('vfx/xueyan-polish/bounds/' + key))
        if not group.findall('track'):
            root.find('trackgroups').remove(group)
    return root, origin


def _mist(root, data, key, dictionary, profile, points, *, looping=False, inward=False):
    origin = data / fx.BLOOD
    source = ET.parse(origin).getroot()
    template = next(t for t in source.findall('./trackgroups/trackgroup/track')
                    if t.find('component') is not None
                    and t.find('component').get('instancename') == SMOKE_INSTANCE)
    group = _group(root, 'Native red mist')
    for index, point in enumerate(points):
        track, smoke = _clone(template, key, 'Native red mist', index)
        start, end = (.1, 3.7) if looping else ((.08, .58) if inward else (.075, .175))
        fx.timing(smoke, start, end)
        fx.multiply(dictionary, smoke, fx.PARTICLE_SCALE, profile['mist_scale'])
        fx.multiply(dictionary, smoke, PARTICLE_ALPHA, profile['mist_alpha'])
        initial = '1,1' if looping else ('4,4' if profile['phase'] == 'impact' else '2,2')
        _scalar(dictionary, smoke, fx.INITIAL_COUNT, initial)
        fx.ramp_edit(dictionary, smoke, fx.EMIT_RATE, lambda channel, value: .8 if looping else (6 if inward else 0))
        _scalar(dictionary, smoke, PARTICLE_OFFSET, ','.join(format(v, '.9g') for v in point))
        # Local = 1 in the installed XCD World|Local|World (Emit Local).
        # This lets a status perimeter follow its owner; a detached impact stays
        # local to its stationary MEI. Preserve BloodPuff's actual velocity and
        # orientation pair as well as life/color: the native smoke has camera
        # alignment and AlignToVelocity=1 with initial velocity .3. Zeroing the
        # velocity while retaining that axis alignment was not a verified pair.
        _scalar(dictionary, smoke, SPACE, 1)
        if inward:
            x, y, z = point
            fx.replace_ramp(dictionary, smoke, PARTICLE_POSITION, (
                [(0, 0), (.35, -x*.55), (1, -x*.9)],
                [(0, 0), (.65, profile.get('convergence_height', .35)-y),
                 (1, profile.get('convergence_height', .35)-y)] if profile.get('recovery_threads') else [(0, 0), (1, .35-y)],
                [(0, 0), (.35, -z*.55), (1, -z*.9)],
            ))
        group.append(track)
    return origin


def _recovery_threads(root, data, key, dictionary, profile, points):
    """Native unlit flares travel inward with blood mist, without impact flashes."""
    origin = data / fx.PIERCE
    native = ET.parse(origin).getroot()
    template = next(t for t in native.findall('./trackgroups/trackgroup/track')
                    if t.find('component') is not None
                    and t.find('component').get('instancename') == CRIMSON_CORE_INSTANCE)
    group = _group(root, 'Converging recovery bloodlight')
    for index, (x, y, z) in enumerate(points):
        track, light = _clone(template, key, 'Recovery bloodlight', index)
        fx.timing(light, .02, .12)
        # Own opacity once: the separate Alpha curve provides the fade. Keeping
        # the donor's transparent Color endpoints would multiply a second fade.
        crimson = (255 << 24 | 255 << 16 | 8 << 8 | 24) - 0x100000000
        _constant(dictionary, light, fx.PARTICLE_COLOR, (crimson,))
        _constant(dictionary, light, fx.LIFESPAN, (1.35, 1.35))
        # Reduce radiance as six threads overlap at the chest, so the hold
        # reads as recovered blood rather than a sixfold impact flash.
        brightness = profile['recovery_thread_brightness']
        fx.replace_ramp(dictionary, light, PARTICLE_BRIGHTNESS,
                        ([(0, brightness), (.55, brightness), (.65, 3), (.82, 2), (1, 1)],))
        _scalar(dictionary, light, fx.INITIAL_COUNT, '1,1')
        fx.ramp_edit(dictionary, light, fx.EMIT_RATE, lambda channel, value: 0)
        _scalar(dictionary, light, SPACE, 1)
        _scalar(dictionary, light, PARTICLE_OFFSET, f'{x:g},{y:g},{z:g}')
        scale = profile['recovery_thread_scale']
        _constant(dictionary, light, fx.PARTICLE_SCALE, (scale, scale))
        _constant(dictionary, light, fx.PARTICLE_AXES, (profile['recovery_thread_width'], 1.5, 1))
        # The native flare is Axis Aligned with Align To Velocity enabled.
        # Keyframed offset alone does not replace its inherited -Z velocity
        # axis. Aim each of the six native emitters into the actual chest point.
        direction = (-x, profile['convergence_height']-y, -z)
        length = math.sqrt(sum(v*v for v in direction))
        _scalar(dictionary, light, '917df2bc-bbb3-4205-8d28-2450ea069f00',
                ','.join(format(v/length, '.9g') for v in direction))
        _constant(dictionary, light, '79ab5e9c-2d87-496c-83bd-1b6c78cbd095', (.01, .01))
        fx.replace_ramp(dictionary, light, PARTICLE_POSITION, (
            [(0, 0), (.14, 0), (.65, -x*.94), (.82, -x*.97), (1, -x)],
            [(0, 0), (.65, profile['convergence_height']-y), (1, profile['convergence_height']-y)],
            [(0, 0), (.14, 0), (.65, -z*.94), (.82, -z*.97), (1, -z)],))
        fx.replace_ramp(dictionary, light, PARTICLE_ALPHA,
                        ([(0, 0), (.08, .95), (.65, .95), (.82, .75), (1, 0)],))
        group.append(track)
    return origin


def _swords(root, data, key, dictionary, profile, *, hit=False):
    source, origin = fx.projectile(data)
    template = next(t for t in source.findall('./trackgroups/trackgroup/track')
                    if t.find('component').get('class') == 'Model')
    group = _group(root, 'Short blood sword accents')
    # Preserve the optional native flare for existing profiles. Selected casts
    # use the actual luminous sword supplied by the SwordGlow postpass alone.
    core_origin = data / fx.PIERCE
    native_core = ET.parse(core_origin).getroot()
    core_template = next(t for t in native_core.findall('./trackgroups/trackgroup/track')
                         if t.find('component') is not None
                         and t.find('component').get('instancename') == CRIMSON_CORE_INSTANCE)
    cores = _group(root, 'Crimson blade light') if profile.get('crimson_blade_light', True) else None
    for index in range(profile['sword_count']):
        track, model = _clone(template, key, 'Short blood sword', index)
        seconds = .32 if hit else profile.get('sword_seconds', .72)
        fx.timing(model, 0, seconds)
        _scalar(dictionary, model, fx.POSITION, '0,0,0')
        _constant(dictionary, model, fx.MODEL_SCALE, (.8, .8, 1.1) if hit else profile.get('sword_model_scale', (.5, .5, .68)))
        fx.recolor(dictionary, model, fx.MODEL_COLOR, BLADE if hit else DEEP_RED)
        _constant(dictionary, model, MODEL_BRIGHTNESS, (2.5,))
        _constant(dictionary, model, 'e5ece95a-a162-4a49-b029-cbc701fb00e4', (0, 0, 0))
        _constant(dictionary, model, 'c57b1310-2df9-4339-bdf8-a97475e121ff', (0, 0, 0))
        fx.replace_ramp(dictionary, model, MODEL_ALPHA, (
            profile.get('sword_alpha_keys', [(0, 0), (.09, .94), (.35, .8), (.72, 0), (1, 0)]),
        ))
        if hit:
            _constant(dictionary, model, MODEL_ROTATION, (0, 0, 25 if key.endswith('wusheng_hit') else -12))
            reach = 1.7 if 'chuanshen' in key else .8
            fx.replace_ramp(dictionary, model, MODEL_POSITION, (
                [(0, 0), (1, 0)], [(0, 0), (1, 0)],
                [(0, reach), (.38, 0), (1, -reach*.6)],
            ))
        else:
            angle = 2*math.pi*index/max(1, profile['sword_count'])
            cosine, sine = math.cos(angle), math.sin(angle)
            radius, motion = profile.get('radius', 1), profile.get('motion', 'in')
            if motion == 'out_return':
                radial = [(0, .45), (.38, radius), (.55, radius), (1, .35)]
            elif motion == 'out':
                radial = [(0, .5), (.5, radius), (1, radius)]
            else:
                radial = [(0, radius), (.6, .3), (1, .15)]
            fx.replace_ramp(dictionary, model, MODEL_POSITION, (
                [(t, r*cosine) for t, r in radial],
                [(0, .5), (1, .5)],
                [(t, r*sine) for t, r in radial],
            ))
            yaw = -math.degrees(angle) + (90 if motion == 'in' else -90)
            _constant(dictionary, model, MODEL_ROTATION, (0, yaw, 0))
        group.append(track)
        if cores is None:
            continue
        light_track, light = _clone(core_template, key, 'Crimson blade light', index)
        fx.timing(light, 0, .1)
        _blood_particle_color(dictionary, light)
        _constant(dictionary, light, fx.LIFESPAN, (seconds, seconds))
        _scalar(dictionary, light, fx.INITIAL_COUNT, '1,1')
        fx.ramp_edit(dictionary, light, fx.EMIT_RATE, lambda channel, value: 0)
        fx.multiply(dictionary, light, fx.PARTICLE_SCALE, 1. if hit else .35)
        # The native piercing flare collapses its width at 30% of life. Keep
        # the red core readable through the outward/inward sword route, then
        # close it with the blade's existing single fade rather than a second
        # flash. X/Y/Z are the installed XCD Axis Scale channels.
        core_width = profile.get('crimson_core_width', 5)
        fx.replace_ramp(dictionary, light, fx.PARTICLE_AXES, (
            [(0, core_width), (.55, core_width), (.72, 0), (1, 0)],
            [(0, 1.05), (.3, 3.15), (.55, 3.15), (.72, 0), (1, 0)],
            [(0, 1), (1, 1)],
        ))
        _scalar(dictionary, light, PARTICLE_OFFSET, '0,0,0')
        # Matching normalized position keys keep the accent at the sword's
        # authored route. Screen-facing flare orientation remains native and
        # still needs scene inspection; this is not a new weapon shader.
        movement = model.find(f'./properties/property[@id="{MODEL_POSITION}"]')
        fx.replace_ramp(dictionary, light, PARTICLE_POSITION, tuple(
            [(float(frame.get('time')), float(frame.get('value')))
             for frame in channel.findall('./keyframes/keyframe')]
            for channel in movement.findall('./data/datum/rampchanneldata/rampchannel')))
        cores.append(light_track)
    return [origin, core_origin] if cores is not None else [origin]


def _domain_boundary(root, data, key, dictionary, profile, duration):
    # Keep the native open annulus; a dedicated world Model material avoids
    # the shared sword shader's character-local sphere/Fresnel opacity masks.
    from xuehai_boundary_visual_polish import VISUAL, NAME
    source, origin = fx.projectile(data)
    template = next(t for t in source.findall('./trackgroups/trackgroup/track')
                    if t.find('component').get('class') == 'Model')
    track, model = _clone(template, key, 'Crimson six-metre open boundary', 0)
    fx.timing(model, 0, duration)
    _scalar(dictionary, model, fx.MESH,
            f'{NAME} <{VISUAL}>')
    _scalar(dictionary, model, fx.POSITION, '0,0.4,0')
    _constant(dictionary, model, fx.MODEL_SCALE, (profile['radius'], profile['radius'], 1))
    _constant(dictionary, model, MODEL_ROTATION, (90, 0, 0))
    _constant(dictionary, model, MODEL_POSITION, (0, 0, 0))
    _constant(dictionary, model, 'e5ece95a-a162-4a49-b029-cbc701fb00e4', (0, 0, 0))
    _constant(dictionary, model, 'c57b1310-2df9-4339-bdf8-a97475e121ff', (0, 0, 0))
    fx.recolor(dictionary, model, fx.MODEL_COLOR, (255, 5, 10))
    _constant(dictionary, model, MODEL_BRIGHTNESS, (profile['boundary_brightness'],))
    # Constant across both endpoints of the native 0.1..3.7 second loop.
    # Only the status-owned opening and ending phases fade this boundary.
    fx.replace_ramp(dictionary, model, MODEL_ALPHA, (
        [(0, 0), (.1 / duration, profile['boundary_alpha']),
         (3.7 / duration, profile['boundary_alpha']), (1, 0)],))
    _group(root, 'Persistent open bloodsea boundary').append(track)
    return origin


def author(data: Path, key: str, dictionary):
    """Return a new XML root, native source paths and presentation-only details."""
    data = Path(data)
    profile = PROFILES[key]
    root, base_origin = _base(data, key)
    origins = [base_origin]
    looping = profile['phase'] == 'status'
    duration = 5.8 if looping else 2.8
    if looping:
        native = ET.parse(data / fx.BLOOD).getroot()
        root.find('phases').extend(copy.deepcopy(list(native.find('phases'))))
        for phase, seconds in zip(root.findall('./phases/object/data'), (.1, 3.6, 2.1)):
            phase.set('duration', format(seconds, '.9g'))
    if profile['phase'] == 'impact':
        native, _ = fx.impact(data)
        group = _group(root, 'Immediate blade cut')
        for index, (template, unused) in enumerate(fx.active_particles(native)):
            track, component = _clone(template, key, 'Immediate blade cut', index)
            fx.timing(component, 0, .1)
            _blood_particle_color(dictionary, component)
            fx.multiply(dictionary, component, fx.PARTICLE_SCALE, profile['slash_scale'])
            fx.multiply(dictionary, component, fx.LIFESPAN, profile['slash_life'])
            group.append(track)
        points = [(0, 0, 0)]
    else:
        count = 12 if looping else profile.get('mist_count', (max(4, profile['sword_count']) if key != 'xueyan_damage_mode_cast' else 1))
        radius = profile.get('radius', .6)
        points = [(radius*math.cos(2*math.pi*i/count), .15 if looping else .45,
                   radius*math.sin(2*math.pi*i/count)) for i in range(count)]
    origins.append(_mist(root, data, key, dictionary, profile, points,
                         looping=looping, inward=profile.get('motion') == 'in'))
    if profile.get('recovery_threads'):
        origins.append(_recovery_threads(root, data, key, dictionary, profile, points))
    if looping:
        origins.append(_domain_boundary(root, data, key, dictionary, profile, duration))
    if profile['sword_count']:
        origins.extend(_swords(root, data, key, dictionary, profile, hit=profile['phase'] == 'impact'))
    # Covers ring centres plus unchanged native 2..4.5 puff scale and particle
    # lifetime. This is a conservative source bound, not ground-contact proof.
    radius = max(4, profile.get('radius', 0) + 3)
    fx.bounds(dictionary, root, radius, duration)
    return root, list(dict.fromkeys(origins)), {
        **profile, 'duration': duration, 'looping': looping,
        'smoke_lifetime': 'native 1.5--2 seconds, unchanged',
        'smoke_color': 'native white/grey ramp; red comes from native material',
        'smoke_velocity_alignment': 'native .3 velocity/camera alignment retained',
        'active_slash_effect_life_color': 'crimson; native HDR brightness envelope retained after 1CA0 client rejection',
        'emissive_blade_accents': profile['sword_count'],
        'emissive_reference': 'native Directional_Flare material 97b12629-982f-c7b4-7807-1ca4cd35e0aa',
        'sword_peak_seconds': .0288 if profile['phase'] == 'impact' else .0648,
        'bank_attack_stages': 1, 'mist_emitters': len(points),
        'scope': 'authoring-source-only', 'compiled': False, 'binding_enabled': False,
        'remaining': 'Native compile; actual attachment, opacity, timing, cancellation, terrain and performance checks',
    }
