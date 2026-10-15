"""Author Xingge's open jade support arcs from verified native components.

This module returns editable XML only. It does not compile, register, cast,
choose recipients, apply statuses or change damage/resources. Target profiles
must be attached to the actual recipient by the caller; they are not CastEffect
aliases. Event profiles never animate an unearned follow-up or damage transfer.

Native factories and their installed PropertyDictionary own every edited
property. In particular Ribbon material ramps are not treated as motion paths.
Official attachment reference:
https://docs.baldursgate3.game/index.php?title=VFX_%E2%80%93_Part_3:_Assigning_and_Testing_Effects
"""
from __future__ import annotations

import copy
import math
from pathlib import Path

import taixuan_visual_polish as tx
from sword_cultivator_spec import guid

fx = tx.fx
JADE = (90, 235, 167)
WARM_WHITE = (255, 241, 210)
ARC_ANGLES = (-40, 0, 40, 140, 180, 220)
LOOP_LEAD, LOOP_SECONDS, LOOP_OUT = .2, 3.6, .4


def _profile(skill, phase, label, presentation, *, trigger, recipient, **design):
    return dict(skill='xingge_' + skill, phase=phase, label=label,
                binding='hit' if phase == 'impact' else phase,
                presentation=presentation, trigger=trigger, recipient=recipient,
                lifecycle=('native status attachment and termination' if phase == 'status'
                           else 'finite one-event effect; no automatic repeats'), **design)


PROFILES = {
    'xingge_wenlu_hit': _profile('wenlu', 'impact', '问路：开路剑锋',
        '青绿窄锋落在真实命中处，一道暖白锐点标出开路瞬间。',
        trigger='actual damaging hit', recipient='actual hit target',
        angles=(-20, 20), axis=(.32, 1.25, 1), core_scale=.65, rgb=JADE),
    'xingge_wenlu_mark': _profile('wenlu', 'target', '问路：开放剑痕',
        '目标近身两侧留开口剑痕；同伴实际利用机会时可由事件再次短亮回应。',
        trigger='actual mark application or consumed follow-up opportunity',
        recipient='marked enemy, not the caster',
        radius=.85, height=.4, duration=1.0, motion='hold', alpha=.40, wisps=False),
    'xingge_huifeng_target': _profile('huifeng', 'target', '回风：护弧轻拨',
        '受援者两侧青绿护弧轻展，暖白风线沿开口离身，不形成封闭护罩。',
        trigger='successful assistance application', recipient='assisted ally or self',
        radius=1.3, height=.9, duration=1.2, motion='open', alpha=.44, wisps=True),
    'xingge_fuchen_target': _profile('fuchen', 'target', '拂尘：解缚开弧',
        '成对细锋从受援者近身向外解开，留下短促、开放的暖白护弧。',
        trigger='actual cleanse or protection application', recipient='cleansed ally or self',
        radius=1.15, height=1.0, duration=1.15, motion='release', alpha=.38, wisps=True),
    'xingge_chengfeng_target': _profile('chengfeng', 'target', '乘风：两侧破围',
        '受援者左右剑弧向三米外缘展开，前后始终留口；安全移动提示跟随受援者。',
        trigger='actual assistance and safe-movement application', recipient='assisted ally or self',
        radius=2.65, height=.45, duration=1.25, motion='open', alpha=.44, wisps=True),
    'xingge_chengfeng_hit': _profile('chengfeng', 'impact', '乘风：破围触点',
        '每个真实受伤目标只给一次侧向青白剑峰，击退位置由原生结果决定。',
        trigger='actual damaging burst hit', recipient='actual hit target',
        angles=(-65, 65), axis=(.35, 1.1, 1), core_scale=.7, rgb=JADE),
    'xingge_tongzhou_cast': _profile('tongzhou', 'cast', '同舟：交接剑路',
        '施法者左右两段开放剑路向前交接；落空也保留一次合击指令读点。',
        trigger='root action release including a miss', recipient='caster',
        radius=1.15, height=.9, duration=1.0, motion='handoff', alpha=.46, wisps=True),
    'xingge_tongzhou_hit': _profile('tongzhou', 'impact', '同舟：合击交点',
        '真实攻击交接处一对青绿细锋同时收成暖白交点，不预演队友攻击次数。',
        trigger='actual damaging root or ally follow-up hit', recipient='actual hit target',
        angles=(-35, 35), axis=(.3, 1.4, 1), core_scale=.7, rgb=JADE),
    'xingge_fengyu_status': _profile('fengyu', 'status', '风雨：护持节点',
        '实际受护队友近身维持低亮成对剑弧，六米团队范围不画成封闭大圆。',
        trigger='actual protected status lifetime', recipient='each protected ally; never caster by default',
        radius=.95, height=.7, motion='hold', alpha=.38, wisps=True, team_radius=6,
        model_scale=(.65, .40, .55), pitch_degrees=20),
    'xingge_fengyu_transfer': _profile('fengyu', 'target', '风雨：承伤接续',
        '分担真正发生后，行歌近身两侧短弧向身躯承接后消散；不伪造两人间直线。',
        trigger='actual damage-share event only', recipient='actual damage-share receiver (Xingge)',
        radius=1.1, height=.95, duration=.9, motion='receive', alpha=.42, wisps=True),
    'xingge_zhangjian_status': _profile('zhangjian', 'status', '仗剑：同行剑弧',
        '实际团队节点两侧开放剑弧稳定呼应，保持前后视野和脚下地面可读。',
        trigger='actual resonance status lifetime', recipient='each actual aura node recipient',
        radius=1.2, height=.9, motion='hold', alpha=.42, wisps=True, team_radius=6,
        model_scale=(.65, .40, .65), pitch_degrees=-12),
    'xingge_zhangjian_hit': _profile('zhangjian', 'impact', '仗剑：独立跟进',
        '符合本轮条件的真实飞剑跟进在目标上显一次青绿锐点，无虚构周期连闪。',
        trigger='actual resonance helper damaging hit only', recipient='actual hit target',
        angles=(0, 90), axis=(.28, 1.0, 1), core_scale=.6, rgb=JADE),
    'xingge_xiangfu_target': _profile('xiangfu', 'target', '相扶：接续护弧',
        '青绿两侧短弧向实际获治者接续，暖白微风轻亮后收净。',
        trigger='actual healing application', recipient='actually healed ally or self',
        radius=1.0, height=.9, duration=1.2, motion='receive', alpha=.40, wisps=True),
}


def _keep_bounds(root):
    for group in list(root.find('trackgroups')):
        for track in list(group.findall('track')):
            if track.find('component').get('class') != 'BoundingSphere':
                group.remove(track)
        if not group.findall('track'):
            root.find('trackgroups').remove(group)


def _arc_frames(profile, duration):
    if profile['phase'] == 'status':
        # Both loop boundaries have identical shape, position and alpha.
        return ((0, 1), (.2 / duration, 1), (2 / duration, 1.04),
                (3.8 / duration, 1), (1, 1))
    factors = {'hold': (1, 1, 1, 1), 'open': (.5, .65, 1, 1.06),
               'release': (.32, .55, 1, 1.14), 'handoff': (.65, .9, 1, .7),
               'receive': (1.12, 1, .6, .2)}[profile['motion']]
    return tuple(zip((0, .12, .55, 1), factors))


def _paired_arcs(data, key, profile, dictionary):
    looping = profile['phase'] == 'status'
    duration = LOOP_LEAD + LOOP_SECONDS + LOOP_OUT if looping else profile['duration']
    root, origins, _ = fx.guard_status(data, dictionary)
    models = root.findall('./trackgroups/trackgroup/track/component[@class="Model"]')
    sword = next(c for c in models if tx.LONGSWORD in c.find(
        f'./properties/property[@id="{fx.MESH}"]/data/datum').get('value', ''))
    template = copy.deepcopy(tx._track_for(root, sword.get('instancename')))
    wisp_template = copy.deepcopy(next(track for track, _ in fx.active_particles(root)))
    _keep_bounds(root)
    if not looping:
        root.find('phases').clear()
    frames = _arc_frames(profile, duration)
    alpha = ([(0, 0), (.2 / duration, profile['alpha']),
              (3.8 / duration, profile['alpha']), (1, 0)] if looping else
             [(0, 0), (.12, profile['alpha'] * .7), (.40, profile['alpha']),
              (.65, profile['alpha'] * .7), (1, 0)])
    arcs = tx._group(root, 'Two open sword arcs; front and back remain clear', 71)
    for index, angle in enumerate(ARC_ANGLES):
        track = copy.deepcopy(template)
        c = track.find('component')
        fx.timing(c, 0, duration)
        tx._scalar(dictionary, c, fx.POSITION, '0,0,0')
        # Keep scale/rotation constant for the existing SwordGlow steel-to-
        # luminous conversion. Only the verified Model offset ramp moves.
        tx._constant(dictionary, c, fx.MODEL_SCALE, profile.get('model_scale', (.28, .28, .44)))
        # The steel blade points along -Z; positive pitch raises its tip.
        # SwordGlow maps that direction to its native +Y blade without changing it.
        tx._constant(dictionary, c, tx.MODEL_ROTATION, (profile.get('pitch_degrees', 0), -angle, 0))
        tx._constant(dictionary, c, tx.MODEL_ROTATION_RPM, (0, 0, 0))
        tx._constant(dictionary, c, tx.MODEL_ROTATION_LIFE, (0, 0, 0))
        tx._constant(dictionary, c, tx.MODEL_BRIGHTNESS, (1,))
        fx.recolor(dictionary, c, fx.MODEL_COLOR, JADE)
        radians = math.radians(angle)
        fx.replace_ramp(dictionary, c, tx.MODEL_OFFSET, (
            [(t, profile['radius'] * f * math.cos(radians)) for t, f in frames],
            [(t, profile['height']) for t, _ in frames],
            [(t, profile['radius'] * f * math.sin(radians)
              - (.45 * t if profile['motion'] == 'handoff' else 0)) for t, f in frames],
        ))
        fx.replace_ramp(dictionary, c, tx.MODEL_ALPHA, (alpha,))
        tx._scalar(dictionary, c, '8771c2c7-091d-4d1f-b7cb-91f87f6a486a', .4 if looping else .2)
        arcs.append(track)
    if profile['wisps']:
        wisps = tx._group(root, 'Two native warm-white curved wisps', 72)
        for side in (-1, 1):
            track = copy.deepcopy(wisp_template)
            c = track.find('component')
            # Let the last particle die before the finite bank ends. Status
            # donor already has a .35s maximum life and a .4s exit phase.
            fx.timing(c, 0, duration - .4)
            tx._scalar(dictionary, c, tx.PARTICLE_OFFSET,
                       f"{side * profile['radius'] * .72},{profile['height']},0")
            color_states = [(m, m.get('muted', 'False')) for m in c.findall('./modules/module')
                            if m.get('id', '').lower() == 'b369fad0-cc26-42f3-bdc2-0b8f120c6081']
            fx.recolor(dictionary, c, fx.PARTICLE_COLOR, WARM_WHITE, .65)
            for module, state in color_states:
                module.set('muted', state)
            fx.ramp_edit(dictionary, c, fx.EMIT_RATE, lambda channel, value: 2 if looping else 5)
            wisps.append(track)
    fx.bounds(dictionary, root, profile['radius'] * 1.15 + 1.2, duration)
    return root, origins, dict(
        duration=duration, sword_count=6, paired_open_arcs=2,
        arc_angles_degrees=list(ARC_ANGLES), each_arc_span_degrees=80,
        minimum_open_gap_degrees=100, full_circle=False, sphere_shell=False,
        local_radius=profile['radius'], motion=profile['motion'], looping=looping,
        loop_seconds=LOOP_SECONDS if looping else None,
        loop_seam='identical offset and alpha at .2s and 3.8s' if looping else None,
        maximum_model_alpha=profile['alpha'], warm_white_wisp_count=2 if profile['wisps'] else 0,
        attachment='actual recipient root' if profile['binding'] != 'cast' else 'caster root',
        pair_count_is_not_attack_count=True, automatic_event_replay=False,
        produces_damage=False, gameplay_changed=False, cross_entity_beam=False)


def _impact(data, key, profile, dictionary):
    root, origins, detail = tx._impact(data, key, profile, dictionary)
    # One warm point inside jade rays gives a hand-off read without adding a
    # second emission peak or a timed sequence of imaginary ally attacks.
    core = root.find('./trackgroups/trackgroup[@name="One actual-stage impact core"]/track/component')
    fx.recolor(dictionary, core, fx.PARTICLE_COLOR, WARM_WHITE)
    detail.update(automatic_event_replay=False, produces_damage=False,
                  gameplay_changed=False, looping=False)
    return root, origins, detail


def author(data: Path, key: str, dictionary):
    """Return source, native provenance and design facts; activation is external."""
    profile = PROFILES[key]
    factory = _impact if profile['phase'] == 'impact' else _paired_arcs
    root, origins, details = factory(Path(data), key, profile, dictionary)
    root.set('id', guid('vfx/visual-polish/editor/' + key))
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
    details.update(skill=profile['skill'], phase=profile['phase'], binding=profile['binding'],
                   trigger=profile['trigger'], recipient=profile['recipient'],
                   lifecycle=profile['lifecycle'], presentation=profile['presentation'],
                   compiled=False, binding_enabled=False,
                   visual_validation='pending native compilation and rendered client observation')
    return root, list(dict.fromkeys(origins)), details
