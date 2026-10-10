"""Author Taixuan's local sword, star and domain motifs from native components.

Factories return editable XML only. They do not compile, register, bind, install
or change gameplay. Native glint lifetimes/materials are retained; a four-stage
attack gets one local glint per actual stage, never four bursts in one bank.

Official binding/attachment reference:
https://docs.baldursgate3.game/index.php?title=VFX_%E2%80%93_Part_3:_Assigning_and_Testing_Effects
"""
from __future__ import annotations

import copy
import importlib.util
import math
from pathlib import Path

from sword_cultivator_spec import guid


_spec = importlib.util.spec_from_file_location(
    'taixuan_native_fx_authoring', Path(__file__).with_name('generate-sword-vfx.py'))
fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fx)

CYAN = (170, 230, 255)
JADE = (195, 244, 230)
WHITE = (228, 250, 255)
LONGSWORD = 'c1319fce-3d47-ac75-e502-a3e965500038'
MODEL_OFFSET = '37b047c1-8fb7-4e7c-9319-58db9da44e77'
MODEL_ROTATION = '4a72a815-57fb-4fcb-9a50-1024331ce66a'
MODEL_ROTATION_RPM = 'e5ece95a-a162-4a49-b029-cbc701fb00e4'
MODEL_ROTATION_LIFE = 'c57b1310-2df9-4339-bdf8-a97475e121ff'
MODEL_ALPHA = '00910be4-aaa1-41a2-946f-735d33de387b'
PARTICLE_OFFSET = '726ea55f-d0f9-4176-9a22-c5539199a83a'
PARTICLE_ANGLE = '8ac28820-26ab-4bbe-bded-41597208ba05'
CORE = 'e64c7f54-ecd3-4983-902d-dd180f93a0ce'
FLARE = 'ae6913c4-8ffe-47b5-a1e8-66608961bc58'


def _profile(skill, phase, label, presentation, **design):
    return dict(skill=skill, phase=phase, label=label,
                binding='hit' if phase == 'impact' else phase,
                presentation=presentation, **design)


# Counts refer to visual composition, never extra attacks or targets. All
# impact profiles contain exactly one central core and a simultaneous glint.
PROFILES = {
    'taixuan_zhaoxi_hit': _profile('taixuan_zhaoxi', 'impact', '照隙：锐点',
        '玉白剑尖贯入，极窄青白剑痕与一个局部亮点迅速消散。',
        angles=(0,), axis=(.55, 1.2, 1), core_scale=.75, rgb=CYAN),
    'taixuan_qinghui_hit': _profile('taixuan_qinghui', 'impact', '清辉反击：交锋',
        '返照反击在真实命中处显出两道交错细锋，同一瞬间收成玉白亮点。',
        angles=(-40, 40), axis=(.45, 1.0, 1), core_scale=.85, rgb=JADE),
    'taixuan_jiuxiao_hit': _profile('taixuan_jiuxiao', 'impact', '九霄：落星',
        '每名实际被剑雨击中的目标只出现一个四芒落星，剑雨构形不复制伤害。',
        angles=(0, 90), axis=(.5, 1.2, 1), core_scale=1.05, rgb=WHITE),
    'taixuan_liuguang_hit': _profile('taixuan_liuguang', 'impact', '追星：单段星芒',
        '每个实际攻击段各显一个短促四芒贯刺，单个效果不自行连闪四次。',
        angles=(-45, 45), axis=(.4, 1.35, 1), core_scale=.8, rgb=WHITE),
    'taixuan_xinghe_hit': _profile('taixuan_xinghe', 'impact', '星河：六芒',
        '向外剑势在实际目标上收为六芒星，护身与反击各有清楚读点。',
        angles=(0, 60, 120), axis=(.5, 1.3, 1), core_scale=1.05, rgb=JADE),
    'taixuan_taiqing_hit': _profile('taixuan_taiqing', 'impact', '太清：域中细锋',
        '领域每次真实剑击一个克制的十字亮峰，重点目标加剑沿用真实 helper。',
        angles=(0, 90), axis=(.35, .85, 1), core_scale=.65, rgb=CYAN),
    'taixuan_yixiantian_hit': _profile('taixuan_yixiantian', 'impact', '一线天：贯穿读点',
        '实际受伤目标留一道长而极窄的局部剑痕；本资产不承担三十米整条长锋。',
        angles=(0,), axis=(.32, 2.0, 1), core_scale=1.15, rgb=WHITE),
    'taixuan_zhaoxi_cast': _profile('taixuan_zhaoxi', 'cast', '照隙：凝锋',
        '一柄青白气剑在身前短促凝锋，稳定剑尖后迅速收束。',
        count=1, radius=.55, motion='gather', rgb=CYAN),
    'taixuan_qinghui_cast': _profile('taixuan_qinghui', 'cast', '清辉：护弧初展',
        '三柄细剑围身展开半弧，返照护体随后维持疏朗循环。',
        count=3, radius=1.05, motion='expand', rgb=JADE),
    'taixuan_jiuxiao_cast': _profile('taixuan_jiuxiao', 'cast', '九霄：剑冠',
        '六柄细长气剑在身周上方排成剑冠，短促下压收束，目标各有落星读点。',
        count=6, radius=1.45, motion='gather', rgb=WHITE),
    'taixuan_liuguang_cast': _profile('taixuan_liuguang', 'cast', '追星：四锋',
        '四柄窄锋构成起招轮廓；后续四个实际攻击段分别给出命中峰。',
        count=4, radius=1.0, motion='gather', rgb=WHITE),
    'taixuan_xinghe_cast': _profile('taixuan_xinghe', 'cast', '星河：外推剑环',
        '八柄细剑由内向外推出一道低密度剑环，释放后快速退亮。',
        count=8, radius=2.2, motion='expand', rgb=JADE),
    'taixuan_taiqing_cast': _profile('taixuan_taiqing', 'cast', '太清：开域',
        '六柄细剑从近身向外轻展，接入六米随身剑域的稀疏边界。',
        count=6, radius=1.7, motion='expand', rgb=CYAN),
    'taixuan_yixiantian_cast': _profile('taixuan_yixiantian', 'cast', '一线天：多锋归一',
        '三柄窄剑从两侧与身前汇成一锋，最亮点集中在收束时。',
        count=3, radius=1.6, motion='gather', rgb=WHITE),
    'taixuan_guiyuan_cast': _profile('taixuan_guiyuan', 'cast', '归元：气息回流',
        '三柄玉白气剑与微风向自身归拢，淡光完成一次恢复读点。',
        count=3, radius=1.1, motion='gather', rgb=JADE),
    'taixuan_qinghui_status': _profile('taixuan_qinghui', 'status', '清辉：返照微光',
        '共同护体的绕剑之外，仅叠加一缕玉白弧光与低亮护壳。',
        count=0, wisps=1, radius=1.15, height=.95, shell_alpha=.10, rgb=JADE),
    'taixuan_xinghe_status': _profile('taixuan_xinghe', 'status', '星河：双弧微光',
        '共同护体的绕剑之外，青白双弧与极淡护壳提供更强返照读点。',
        count=0, wisps=2, radius=1.4, height=1.05, shell_alpha=.07, rgb=WHITE),
    'taixuan_taiqing_status': _profile('taixuan_taiqing', 'status', '太清：六米剑域',
        '六柄低亮气剑沿六米随身边界环行，周期攻击之间保持稀疏。',
        count=6, wisps=1, radius=6.0, height=.3, shell_alpha=0, rgb=CYAN),
}


def _constant(dictionary, component, key, values):
    fx.replace_ramp(dictionary, component, key,
                    tuple([(0, value), (1, value)] for value in values))


def _scalar(dictionary, component, key, value):
    dictionary.property(component, key)
    fx.set_value(component, key, value)


def _group(root, label, index):
    from xml.etree import ElementTree as ET
    group = ET.SubElement(root.find('trackgroups'), 'trackgroup', name=label)
    ET.SubElement(ET.SubElement(group, 'ids'), 'id', value=str(index))
    return group


def _track_for(root, instance):
    return next(track for track in root.findall('./trackgroups/trackgroup/track')
                if track.find('component') is not None
                and track.find('component').get('instancename') == instance)


def _impact(data, key, profile, dictionary):
    root, origins, _ = fx.branch_impact(data, 'taixuan', dictionary)
    template = copy.deepcopy(_track_for(root, FLARE))
    core_track = copy.deepcopy(_track_for(root, CORE))
    for group in list(root.find('trackgroups')):
        for track in list(group.findall('track')):
            if track.find('component').get('class') != 'BoundingSphere':
                group.remove(track)
        if not group.findall('track'):
            root.find('trackgroups').remove(group)
    # The native Pierce components emit their initial particles once with
    # EmitRate=0. Keep their .3-.45s lifespan ramps and flipbook/material intact.
    core = core_track.find('component')
    fx.multiply(dictionary, core, fx.PARTICLE_SCALE, profile['core_scale'])
    fx.recolor(dictionary, core, fx.PARTICLE_COLOR, profile['rgb'])
    _scalar(dictionary, core, fx.INITIAL_COUNT, '1,1')
    fx.timing(core, 0, .45)
    _group(root, 'One actual-stage impact core', 61).append(core_track)
    rays = _group(root, 'Simultaneous narrow glint rays', 62)
    for angle in profile['angles']:
        track = copy.deepcopy(template)
        component = track.find('component')
        fx.multiply(dictionary, component, fx.PARTICLE_AXES, profile['axis'])
        fx.recolor(dictionary, component, fx.PARTICLE_COLOR, profile['rgb'])
        _constant(dictionary, component, PARTICLE_ANGLE, (angle, angle))
        _scalar(dictionary, component, fx.INITIAL_COUNT, '1,1')
        fx.timing(component, 0, .45)
        rays.append(track)
    fx.bounds(dictionary, root, 8, 1.0)
    return root, origins, dict(
        central_peak_count=1, ray_angles_degrees=list(profile['angles']),
        all_rays_start_together=True, continuous_emission=0,
        native_particle_lifetimes_preserved=True, effect_repetitions=1,
        full_distance_beam=False, duration=1.0)


def _cast(data, key, profile, dictionary):
    root, origin = fx.projectile(data)
    template = copy.deepcopy(next(track for track in root.findall('./trackgroups/trackgroup/track')
                                  if track.find('component').get('class') == 'Model'))
    root.find('phases').clear()
    for group in list(root.find('trackgroups')):
        for track in list(group.findall('track')):
            if track.find('component').get('class') != 'BoundingSphere':
                group.remove(track)
        if not group.findall('track'):
            root.find('trackgroups').remove(group)
    duration = 1.1
    swords = _group(root, 'One cast sword motif', 63)
    for index in range(profile['count']):
        track = copy.deepcopy(template)
        component = track.find('component')
        fx.timing(component, 0, duration)
        _scalar(dictionary, component, fx.POSITION, '0,0,0')
        fx.multiply(dictionary, component, fx.MODEL_SCALE, (.35, .35, .85))
        fx.recolor(dictionary, component, fx.MODEL_COLOR, profile['rgb'])
        angle = -math.pi / 2 + index * 2 * math.pi / profile['count']
        radius = profile['radius']
        factors = (1, 1, .65, .08) if profile['motion'] == 'gather' else (.22, .3, 1, 1.12)
        times = (0, .10 / duration, .55 / duration, 1)
        _constant(dictionary, component, MODEL_ROTATION, (90, 0, 0))
        _constant(dictionary, component, MODEL_ROTATION_RPM, (0, 0, 0))
        _constant(dictionary, component, MODEL_ROTATION_LIFE, (0, 0, 0))
        fx.replace_ramp(dictionary, component, MODEL_OFFSET, (
            [(t, radius * factor * math.cos(angle)) for t, factor in zip(times, factors)],
            [(0, 1.05), (.5, 1.25), (1, 1.05)],
            [(t, radius * factor * math.sin(angle)) for t, factor in zip(times, factors)],
        ))
        fx.replace_ramp(dictionary, component, MODEL_ALPHA, (
            [(0, 0), (.10 / duration, .55), (.45 / duration, .85), (.7 / duration, .35), (1, 0)],
        ))
        # This Model transition ends with the non-looping cast; the native
        # material and mesh are kept. No independently moving projectile exists.
        _scalar(dictionary, component, '8771c2c7-091d-4d1f-b7cb-91f87f6a486a', .25)
        swords.append(track)
    fx.bounds(dictionary, root, max(5, profile['radius'] + 3), duration)
    return root, [origin], dict(
        sword_count=profile['count'], motif=profile['motion'], local_radius=profile['radius'],
        duration=duration, repetitions=1, looping=False, produces_damage=False,
        target_area_rain=False, full_distance_beam=False)


def _status(data, key, profile, dictionary):
    root, origins, _ = fx.guard_status(data, dictionary)
    groups = root.find('trackgroups')
    model_tracks = [track for track in root.findall('./trackgroups/trackgroup/track')
                    if track.find('component') is not None
                    and track.find('component').get('class') == 'Model'
                    and LONGSWORD in track.find('component').find(
                        f'./properties/property[@id="{fx.MESH}"]/data/datum').get('value', '')]
    template = copy.deepcopy(model_tracks[0])
    # One torso shell is suitable for the personal guards, but a 6m opaque
    # sphere would obscure the domain. The domain uses only its sword perimeter.
    for group in list(groups):
        for track in list(group.findall('track')):
            component = track.find('component')
            if track in model_tracks or (profile['shell_alpha'] == 0 and component.get('class') == 'Model'):
                group.remove(track)
        if not group.findall('track'):
            groups.remove(group)
    duration, lead, loop = 4.2, .2, 3.6
    swords = _group(root, 'Taixuan sparse looping sword perimeter', 64) if profile['count'] else None
    for index in range(profile['count']):
        track = copy.deepcopy(template)
        component = track.find('component')
        fx.recolor(dictionary, component, fx.MODEL_COLOR, profile['rgb'])
        fx.multiply(dictionary, component, fx.MODEL_SCALE, (.60, .60, .9))
        offset = index * 2 * math.pi / profile['count']
        times = [0] + [lead + loop * step / 48 for step in range(49)] + [duration]
        angles = [offset] + [offset + 2 * math.pi * step / 48 for step in range(49)] + [offset + 2 * math.pi]
        fx.replace_ramp(dictionary, component, MODEL_OFFSET, (
            [(t / duration, profile['radius'] * math.cos(angle)) for t, angle in zip(times, angles)],
            [(t / duration, profile['height']) for t in times],
            [(t / duration, profile['radius'] * math.sin(angle)) for t, angle in zip(times, angles)],
        ))
        fx.replace_ramp(dictionary, component, MODEL_ALPHA, (
            [(0, 0), (lead / duration, .48), ((lead + loop) / duration, .48), (1, 0)],
        ))
        swords.append(track)
    # Keep the native short-lived wisp's selected Color module. Activating a
    # dormant duplicate Color module would change the rendered interpretation.
    for track, component in list(fx.active_particles(root)):
        color_states = [(module, module.get('muted', 'False'))
                        for module in component.findall('./modules/module')
                        if module.get('id', '').lower() == 'b369fad0-cc26-42f3-bdc2-0b8f120c6081']
        fx.recolor(dictionary, component, fx.PARTICLE_COLOR, profile['rgb'], .5)
        for module, muted in color_states:
            module.set('muted', muted)
        fx.ramp_edit(dictionary, component, fx.EMIT_RATE, lambda channel, value: 2)
        _scalar(dictionary, component, PARTICLE_OFFSET, f"0,{profile['height']},0")
        if profile['wisps'] == 2:
            # A second small wind curl differentiates the stronger guard. It
            # adds no sword Model beside ESC_COUNTER_READY's common three.
            twin = copy.deepcopy(track)
            twin_component = twin.find('component')
            _scalar(dictionary, twin_component, PARTICLE_OFFSET, f"0.45,{profile['height']},0.45")
            fx.multiply(dictionary, twin_component, fx.PARTICLE_SCALE, .85)
            _group(root, 'Second faint star-river guard curl', 65).append(twin)
    for component in root.findall('./trackgroups/trackgroup/track/component'):
        if component.get('class') == 'Model' and LONGSWORD not in component.find(
                f'./properties/property[@id="{fx.MESH}"]/data/datum').get('value', ''):
            fx.recolor(dictionary, component, fx.MODEL_COLOR, profile['rgb'])
            fx.replace_ramp(dictionary, component, MODEL_ALPHA, (
                [(0, 0), (lead / duration, profile['shell_alpha']),
                 ((lead + loop) / duration, profile['shell_alpha']), (1, 0)],
            ))
    fx.bounds(dictionary, root, profile['radius'] + 3, duration)
    return root, origins, dict(
        sword_count=profile['count'], orbit_radius=profile['radius'] if profile['count'] else None,
        orbit_height=profile['height'] if profile['count'] else None, wisp_count=profile['wisps'],
        common_guard_swords_duplicated=False,
        loop_seconds=loop, loop_seam='same position and rotation', shell_alpha=profile['shell_alpha'],
        owner_attachment='Dummy_Root', terrain_adaptation=False, gameplay_radius_changed=False,
        loop_lifecycle='StatusEffect owns attachment and termination')



# Native resource-bank bounds, not a gameplay radius or client visibility claim.
# SpiritualWeapon Objects MaterialID 897a51e0-39fb-7d08-0437-03ec27637571
# and EnergyRing Objects MaterialID 0284789c-9a82-6af1-1af7-b75dfb5a4e16
# are retained by sword_vfx_resources._metadata's verified dependency mapping.
NATIVE_SWORD = {
    'name': 'SPRW_Greatsword', 'guid': '3727a57a-e4be-44da-02b4-5061028fed5f',
    'minimum': (-.1707061, -.00018119812, -.042987518),
    'maximum': (.17070608, 1.9629779, .043253355),
}
STEEL_SWORD_BOUNDS = ((-.11930772, -.06461757, -1.1560508),
                      (.11930772, .08212577, .36261004))
NATIVE_RING = '36c6fe7b-25b9-19fe-a285-d750d070b6ff'
MODEL_BRIGHTNESS = '6cbb9e51-0d17-4916-9666-30d8c7b47e81'
NATIVE_MOTIF_KEYS = frozenset(('taixuan_jiuxiao_cast', 'taixuan_jiuxiao_hit',
                             'taixuan_taiqing_cast', 'taixuan_taiqing_hit',
                             'taixuan_taiqing_status'))


def _native_prop(component, key):
    prop = component.find(f'./properties/property[@id="{key}"]')
    if prop is None:
        raise ValueError(f'Expected existing Model property {key}')
    return prop


def _native_constant_values(component, key):
    channels = _native_prop(component, key).findall('./data/datum/rampchanneldata/rampchannel')
    values = [[float(k.get('value')) for k in c.findall('./keyframes/keyframe')] for c in channels]
    if not values or any(not row or len(set(row)) != 1 for row in values):
        raise ValueError('Expected constant native Model channels')
    return tuple(row[0] for row in values)


def _native_replace_constants(component, key, values):
    channels = _native_prop(component, key).findall('./data/datum/rampchanneldata/rampchannel')
    if len(channels) != len(values):
        raise ValueError('Native Model channel count changed')
    for channel, value in zip(channels, values):
        for frame in channel.findall('./keyframes/keyframe'):
            frame.set('value', format(value, '.17g'))


def _native_up_bounds(minimum, maximum, scale, offset, steel):
    import itertools
    corners = []
    for x, y, z in itertools.product(*zip(minimum, maximum)):
        local = (x * scale[0], -z * scale[2], y * scale[1]) if steel else (x * scale[0], y * scale[1], z * scale[2])
        corners.append(tuple(local[i] + offset[i] for i in range(3)))
    return tuple(min(p[i] for p in corners) for i in range(3)), tuple(max(p[i] for p in corners) for i in range(3))


def _native_upgrade_swords(components, expected_count):
    """Map X90 steel to X0 native +Y, retaining world AABB and all orbit/alpha."""
    if len(components) != expected_count:
        raise ValueError('Expected existing sparse sword Model count')
    minimum, maximum = NATIVE_SWORD['minimum'], NATIVE_SWORD['maximum']
    for component in components:
        mesh = _native_prop(component, fx.MESH).find('data/datum')
        if LONGSWORD not in mesh.get('value', '') or _native_constant_values(component, MODEL_ROTATION) != (90, 0, 0):
            raise ValueError('Expected the verified upward steel sword baseline')
        old_scale = _native_constant_values(component, fx.MODEL_SCALE)
        offset = tuple(float(v) for v in _native_prop(component, fx.POSITION).find('data/datum').get('value').split(','))
        low, high = _native_up_bounds(*STEEL_SWORD_BOUNDS, old_scale, offset, True)
        scale = tuple((high[i] - low[i]) / (maximum[i] - minimum[i]) for i in range(3))
        zero_low, _ = _native_up_bounds(minimum, maximum, scale, (0, 0, 0), False)
        pivot = tuple(low[i] - zero_low[i] for i in range(3))
        mesh.set('value', f"{NATIVE_SWORD['name']} <{NATIVE_SWORD['guid']}>")
        _native_prop(component, fx.POSITION).find('data/datum').set('value', ','.join(format(v, '.17g') for v in pivot))
        _native_replace_constants(component, fx.MODEL_SCALE, scale)
        _native_replace_constants(component, MODEL_ROTATION, (0, 0, 0))
        mapped_low, mapped_high = _native_up_bounds(minimum, maximum, scale, pivot, False)
        if max(abs(a - b) for before, after in ((low, mapped_low), (high, mapped_high)) for a, b in zip(before, after)) > 1e-12:
            raise AssertionError('Native sword adaptation changed the original world AABB')


def _native_sword_template(data, dictionary):
    # Use the original guard factory's native Model, not a candidate file or
    # a generated-source dependency. This also works before Common is authored.
    guard, origins, _ = fx.guard_status(data, dictionary)
    template = copy.deepcopy(guard.find('./trackgroups/trackgroup[@name="Three sword guard"]/track'))
    _native_upgrade_swords([template.find('component')], 1)
    return template, origins[0]


def _native_added_model(root, label, uid, template, duration):
    group = _group(root, label, 1001)
    track = copy.deepcopy(template)
    track.set('name', label)
    track.set('muted', 'False')
    track.set('mutestateoverride', 'Unmuted')
    component = track.find('component')
    # Preserve the already-reviewed candidate identity during regeneration.
    component.set('instancename', guid('vfx/candidate/taixuan-native-rain-domain/' + uid))
    fx.set_value(component, fx.NAME, label)
    fx.timing(component, 0, duration)
    group.append(track)
    return component


def _native_motifs(data, key, root, dictionary):
    """Only five reviewed motifs; existing phases/bounds/glints remain intact."""
    extra_origins = []
    detail = dict(native_sword_visual=NATIVE_SWORD['guid'], native_client_picture='pending')
    if key in ('taixuan_jiuxiao_hit','taixuan_taiqing_hit'):
        detail.update(local_swords_per_actual_hit=0, world_rain_owner='TaixuanRainVfx.lua',
                      existing_glint_peak_unchanged=True, native_damage_timing_unchanged=True)
        return [],detail
    if key.endswith('_cast') or key.endswith('_status'):
        swords = [c for c in root.findall('./trackgroups/trackgroup/track/component[@class="Model"]')
                  if LONGSWORD in _native_prop(c, fx.MESH).find('data/datum').get('value', '')]
        _native_upgrade_swords(swords, 6)
        detail.update(native_sword_count=6, original_sword_world_aabb_preserved=True,
                      original_orbit_alpha_and_timing_preserved=True)
    if key.endswith('_hit') or key.endswith('_status'):
        template, origin = _native_sword_template(data, dictionary)
        extra_origins.append(origin)
        if key.endswith('_hit'):
            component = _native_added_model(root, 'One native luminous sword at actual hit', key, template, .42)
            low, high = NATIVE_SWORD['minimum'], NATIVE_SWORD['maximum']
            scale = (.14 / (high[0] - low[0]), 1.30 / (high[1] - low[1]), .07 / (high[2] - low[2]))
            _native_replace_constants(component, fx.MODEL_SCALE, scale)
            _native_replace_constants(component, MODEL_ROTATION, (180, 0, 0))
            _native_prop(component, fx.POSITION).find('data/datum').set('value', f'0,{high[1] * scale[1]:.17g},0')
            fx.replace_ramp(dictionary, component, MODEL_OFFSET, (
                [(0, 0), (1, 0)], [(0, 2.4), (.02 / .42, 2.4), (.10 / .42, .85), (.14 / .42, 0), (1, 0)], [(0, 0), (1, 0)]))
            fx.replace_ramp(dictionary, component, MODEL_ALPHA, (
                [(0, 0), (.02 / .42, 1), (.19 / .42, 1), (.34 / .42, 0), (1, 0)],))
            rgb = WHITE if key == 'taixuan_jiuxiao_hit' else CYAN
            _native_replace_constants(component, fx.MODEL_COLOR, (((255 << 24) | (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]) - 0x100000000,))
            _native_replace_constants(component, MODEL_BRIGHTNESS, (1,))
            detail.update(local_swords_per_actual_hit=1, local_sword_size_xyz_m=(.14, 1.3, .07),
                          bodyfx_contact_time=.14, local_sword_lifetime=.42,
                          native_damage_timing_unchanged=True, existing_glint_peak_unchanged=True,
                          empty_ground_rain=False, produces_extra_damage=False)
        else:
            component = _native_added_model(root, 'Low open R6 native emissive domain perimeter', key + '/ring', template, 4.2)
            _native_prop(component, fx.MESH).find('data/datum').set('value', f'VFX_Static_Capless_Cylinder_01_Energy_Ring_01 <{NATIVE_RING}>')
            _native_replace_constants(component, fx.MODEL_SCALE, (6, .06, 6))
            _native_replace_constants(component, MODEL_ROTATION, (0, 0, 0))
            _native_prop(component, fx.POSITION).find('data/datum').set('value', '0,0.18,0')
            fx.replace_ramp(dictionary, component, MODEL_OFFSET, tuple([(0, 0), (1, 0)] for _ in range(3)))
            fx.replace_ramp(dictionary, component, MODEL_ALPHA, ([(0, 0), (.2 / 4.2, .5), (3.8 / 4.2, .5), (1, 0)],))
            _native_replace_constants(component, MODEL_BRIGHTNESS, (1,))
            detail.update(native_open_ring_visual=NATIVE_RING, native_ring_scale=(6, .06, 6),
                          ring_y_range=(.12, .24), ring_alpha_hold=.5,
                          gameplay_radius_unchanged=True, terrain_adaptation=False)
    return extra_origins, detail


def author(data: Path, key: str, dictionary):
    """Return in-memory source, native origins and honest authoring evidence."""
    profile = PROFILES[key]
    factory = {'impact': _impact, 'cast': _cast, 'status': _status}[profile['phase']]
    root, origins, details = factory(Path(data), key, profile, dictionary)
    root.set('id', guid('vfx/visual-polish/editor/' + key))
    # Clones receive stable unique identities and descriptive names. Native
    # references are provenance only, never reused as our component UUIDs.
    for index, track in enumerate(root.findall('./trackgroups/trackgroup/track')):
        component = track.find('component')
        if component is None:
            continue
        label = f"{profile['label']} {component.get('class')} {index + 1}"
        track.set('name', label)
        track.set('muted', 'False')
        track.set('mutestateoverride', 'Unmuted')
        component.set('instancename', guid(f'vfx/visual-polish/component/{key}/{index}'))
        fx.set_value(component, fx.NAME, label)
    if key in NATIVE_MOTIF_KEYS:
        extra_origins, native_details = _native_motifs(Path(data), key, root, dictionary)
        origins = list(dict.fromkeys([*origins, *extra_origins]))
        details.update(native_details)
    from sword_visible_blade import improve_polish
    blade_origins, blade_details = improve_polish(Path(data), key, root, dictionary)
    origins = list(dict.fromkeys([*origins, *blade_origins]))
    details.update(blade_details)
    details.update(skill=profile['skill'], phase=profile['phase'],
                   presentation=profile['presentation'], compiled=False, binding_enabled=False,
                   visual_validation='pending native compilation and rendered client observation')
    return root, origins, details
