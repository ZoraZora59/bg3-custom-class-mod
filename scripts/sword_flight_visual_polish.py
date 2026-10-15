"""One foot sword attached for the existing Sword Flight readiness status.

The status owns its lifetime; native Projectile_Fly still owns all movement.
This borrows the compiled/proven sword and Rush contour component schemas,
not the Rush lifecycle, trajectories, animation, or gameplay.
"""
from __future__ import annotations

from sword_cultivator_spec import guid
from tianqing_vfx_design import GREAT_SWORD
import tianfeng_visual_polish as donor

fx, fall = donor.fx, donor.fall
KEY = 'common_sword_flight_status'
LEAD_IN, LOOP, LEAD_OUT = .15, .40, .30
DURATION = LEAD_IN + LOOP + LEAD_OUT
SWORD_SCALE = (2.2, 1.3, 1.5)
SWORD_POSITION = (0., .05, .90)
TAIL_SCALE = (.11, 1.3, .035)
TAIL_POSITIONS = ((-.16, .08, .45), (.16, .08, .45))
PROFILES = {
    KEY: dict(skill='sword_flight', phase='status', label='踏剑而行：青锋托身',
              binding='status', motion='root_attached_horizontal_foot_sword',
              presentation='御剑就绪时脚下浮现完整青色横剑，双束青白剑尾向后流动，随真实飞行升降与转向；状态结束时淡出。',
              sword_count=1, lifecycle='existing-flight-status'),
}


def author(data, key, dictionary):
    if key != KEY:
        raise KeyError(key)
    root, origins, _ = donor.author(data, donor.KEY, dictionary)
    root.set('id', guid('vfx/polish/editor/' + key))
    phases = root.findall('./phases/object/data')
    for index, (phase, duration) in enumerate(zip(phases, (LEAD_IN, LOOP, LEAD_OUT))):
        phase.set('id', guid(f'vfx/sword-flight/phase/{index}'))
        phase.set('duration', format(duration, '.9g'))
    sword_count = tail_count = 0
    for index, component in enumerate(root.findall('.//component')):
        component.set('instancename', guid(f'vfx/sword-flight/component/{index}'))
        if component.get('class') != 'Model':
            continue
        mesh = component.find(f'./properties/property[@id="{fx.MESH}"]/data/datum').get('value')
        if GREAT_SWORD['guid'] in mesh:
            sword_count += 1
            label, position, scale, rotation, alpha = (
                'Sword Flight horizontal foot blade', SWORD_POSITION, SWORD_SCALE, (0, 0, 0), 1.)
        elif donor.RUSH_MESH in mesh:
            label = f'Sword Flight blue-white wake {tail_count + 1}'
            position, scale, rotation, alpha = TAIL_POSITIONS[tail_count], TAIL_SCALE, (-90, 0, 0), .65
            tail_count += 1
            # Native ogive tip is -Y; -90 degrees points it behind the actor
            # (+Z). Flatten its cross-section so it cannot form a vertical hood.
            cyan_white = (0xff000000 | 190 << 16 | 235 << 8 | 255) - 0x100000000
            fall.constants(dictionary, component, fx.MODEL_COLOR, (cyan_white,))
            fall.constants(dictionary, component, fall.MODEL_BRIGHTNESS, (2.,))
        else:
            raise ValueError('Unexpected Sword Flight donor model')
        fx.set_value(component, fx.NAME, label)
        fx.timing(component, 0, DURATION)
        fall.scalar(dictionary, component, fx.POSITION, ','.join(map(str, position)))
        fall.constants(dictionary, component, fx.MODEL_SCALE, scale)
        fall.constants(dictionary, component, fall.INITIAL_ROTATION, rotation)
        for field in (fall.KEYFRAMED_OFFSET, fall.ROTATION_RPM, fall.ROTATION_LIFE):
            fall.constants(dictionary, component, field, (0, 0, 0))
        fx.replace_ramp(dictionary, component, fall.ALPHA, (
            [(0, 0), (LEAD_IN / DURATION, alpha),
             ((LEAD_IN + LOOP) / DURATION, alpha), (1, 0)],))
    if (sword_count, tail_count) != (1, 2):
        raise ValueError('Sword Flight requires one whole sword and two wakes')
    for group in root.findall('./trackgroups/trackgroup'):
        group.set('name', group.get('name', '').replace('Tianfeng', 'Sword Flight'))
        for track in group.findall('track'):
            component = track.find('component')
            name = component.find(f'./properties/property[@id="{fx.NAME}"]/data/datum')
            if name is not None:
                track.set('name', name.get('value'))
    fx.bounds(dictionary, root, 4, DURATION)
    return root, origins, dict(
        sword_count=1, steel_reference_scale=SWORD_SCALE, steel_reference_position=SWORD_POSITION,
        sword_length=(GREAT_SWORD['bounds_max'][2] - GREAT_SWORD['bounds_min'][2]) * SWORD_SCALE[2],
        sword_width=(GREAT_SWORD['bounds_max'][0] - GREAT_SWORD['bounds_min'][0]) * SWORD_SCALE[0],
        direction='blade caster local -Z; wakes +Z; blade lies in horizontal XZ plane',
        tail_count=2, tail_scale=TAIL_SCALE, tail_positions=TAIL_POSITIONS,
        lead_in=LEAD_IN, loop_duration=LOOP, stop_fade=LEAD_OUT, duration=DURATION,
        caster_attachment='ESC_IN_FLIGHT StatusEffect; TargetBone Dummy_Root; DetachTarget=false',
        ready_on_ground_visible=True, world_path=False, gameplay_changed=False,
        remaining='AllSpark preview and native Fly ascent/turn/landing/status-expiry rendered acceptance')
