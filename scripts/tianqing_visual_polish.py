"""Author compact Tianqing hit accents and its golden recovery cast.

The existing spatial coordinator owns falling greatswords.  These banks contain
only nearby particle accents: one synchronized pulse per actual hit, without
damage, actor motion, repeated hits, camera shake, or a second falling sword.
AllSpark compilation and client playback are separate from source authoring.
"""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

from sword_cultivator_spec import guid


_spec = importlib.util.spec_from_file_location(
    'tianqing_polish_sword_fx', Path(__file__).with_name('generate-sword-vfx.py'))
fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fx)

SLASH = fx.BASE / 'Actions/Cast/WeaponAttack/VFX_Actions_Cast_WeaponAttack_Target_BladeFlourish_Slash_01.lsefx'
RECOVERY = fx.BASE / 'Spells/Cast/Fighter/VFX_Spells_Cast_Fighter_ShoutSelf_SecondWind_Root_01.lsefx'
GOLD = (255, 217, 145)
PARTICLE_ALPHA = 'd1892ce7-07f3-4d9c-9acb-6692b897a71b'
PARTICLE_BRIGHTNESS = '7b01f163-d329-4cd0-97f0-31115055b9c8'
SYSTEM_COLOR = 'bb1e9c04-b4b9-4407-af31-effec5a9d46a'
SYSTEM_BRIGHTNESS = '1dc673ff-bbe4-4852-9615-78cd6a835d19'
PARTICLE_OFFSET = '726ea55f-d0f9-4176-9a22-c5539199a83a'
KEYFRAMED_OFFSET = 'a14d2803-fec4-4015-9e37-eb67e1c2f1d8'
PIVOT_ROTATION = 'e63eabc6-eb9f-49c3-bdab-bd090fbd349e'

# Source location and component identities are checked before every copy.
NATIVE_TRACKS = {
    'bounds': (SLASH, 0, 2, 'f0aeab22-bb3e-419f-9cd7-b972c1411f7b', 'BoundingSphere'),
    'sweep': (SLASH, 1, 0, '2ad35eea-2311-4c35-a17a-6427a9d6d888', 'ParticleSystem'),
    'point': (fx.PIERCE, 4, 0, 'ae6913c4-8ffe-47b5-a1e8-66608961bc58', 'ParticleSystem'),
    'core': (fx.PIERCE, 8, 2, '0e27237d-3909-45be-8344-82dbedd98510', 'ParticleSystem'),
    'ring': (fx.SMITE, 2, 5, '920ec035-71e5-4d4e-bd5d-920dfde922c6', 'ParticleSystem'),
    'recovery': (RECOVERY, 4, 1, 'b55d2d91-c2ed-48c0-9675-e0b113323aca', 'ParticleSystem'),
}


def _hit(skill, label, presentation, primitive, axes, *, ring=1., life=.28, angle=0, paired=False):
    return dict(skill=skill, phase='impact', label=label, binding='hit',
                presentation=presentation, primitive=primitive, primary_axes=axes,
                ring_scale=ring, lifespan=life, angle=angle, paired=paired)


PROFILES = {
    'tianqing_nifeng_hit': _hit('tianqing_nifeng', '逆锋横扫',
        '宽阔金色刃弧瞬切，窄金边余光收束，保留横扫的清晰方向。',
        'sweep', (1.6, .8, 1), ring=.62, life=.22),
    'tianqing_tianbeng_hit': _hit('tianqing_tianbeng', '天崩',
        '两道同拍金色尖锋形成楔形破裂，中心短促震纹突出重劈。',
        'point', (.7, 1.3, 1), ring=.85, life=.24, angle=28, paired=True),
    'tianqing_tianfeng_hit': _hit('tianqing_tianfeng', '破阵',
        '锐窄金色穿刺芒集中于命中处，细小冲击圈迅速退去。',
        'point', (.24, 1.45, 1), ring=.48, life=.2),
    'tianqing_wanjun_hit': _hit('tianqing_wanjun', '万钧',
        '紧实金色破碎核心配局部厚震环，与整招一次的落剑同奏。',
        'core', (1, .8, 1), ring=1.25, life=.26),
    'tianqing_lietian_hit': _hit('tianqing_lietian', '裂天',
        '纵向金裂芒与小范围环纹强调切开目标的一击。',
        'point', (.32, 1.6, 1), ring=.7, life=.25),
    'tianqing_tianjian_hit': _hit('tianqing_tianjian', '天剑坠世',
        '温白金色压缩核心骤亮，重环在目标附近展开并留下清楚余光。',
        'core', (1.25, 1.25, 1), ring=1.4, life=.3),
    'tianqing_bafang_hit': _hit('tianqing_bafang', '八方灭阵',
        '双向短金芒同拍破裂，紧凑薄环点明每个受击目标。',
        'point', (.5, .95, 1), ring=.78, life=.23, angle=55, paired=True),
    'tianqing_tiandi_hit': _hit('tianqing_tiandi', '天地剑劫',
        '交错金裂芒与压缩震环统一短峰，每个真实阶段命中只亮一次。',
        'point', (.52, 1.2, 1), ring=1.1, life=.25, angle=45, paired=True),
    'tianqing_nixi_cast': dict(skill='tianqing_nixi', phase='cast', label='逆息回生',
        binding='cast', presentation='金色环纹向内收息，柔亮金芒向上回升，体现回生而非重击。',
        primitive='recovery', primary_axes=(.36, .5, 1), lifespan=.65),
}


def _metadata(dictionary, component, key):
    """Check engine built-ins against XMD; XCD has no definition for them."""
    kind = component.get('class')
    module = dictionary.membership.get((kind, key))
    if module is None or module.get('name') != 'Required' or module.get('required') != 'True':
        raise ValueError(f'Native Required XMD metadata changed: {kind}/{key}')
    if not component.findall(f'./properties/property[@id="{key}"]/data/datum'):
        raise ValueError(f'Native serialized metadata missing: {kind}/{key}')
    dictionary.used[f'{kind}/{key}'] = dict(
        component=kind, property=key, name='Name' if key == fx.NAME else 'Start / End Time',
        type='engine built-in', tooltip=None, channels=[], constraints=[],
        module=dict(module.attrib), verification='XMD Required membership and native serialized datum')


def _append(root, data, primitive, key, label, index, dictionary, origins):
    path, gi, ti, instance, kind = NATIVE_TRACKS[primitive]
    origin = data / path
    source = ET.parse(origin).getroot()
    groups = source.findall('./trackgroups/trackgroup')
    try:
        native = groups[gi].findall('track')[ti]
    except IndexError as exc:
        raise ValueError(f'Native template track changed: {origin} {gi}/{ti}') from exc
    original = native.find('component')
    if original is None or original.get('class') != kind or original.get('instancename') != instance:
        raise ValueError(f'Native template identity changed: {origin} {gi}/{ti}')
    _metadata(dictionary, original, fx.NAME)
    _metadata(dictionary, original, fx.TIME)
    track = copy.deepcopy(native)
    track.set('name', label)
    track.set('muted', 'False')
    track.set('mutestateoverride', 'Unmuted')
    component = track.find('component')
    component.set('instancename', guid(f'vfx/visual-polish/tianqing/{key}/{index}'))
    fx.set_value(component, fx.NAME, label)
    group = ET.SubElement(root.find('trackgroups'), 'trackgroup', name=label)
    ET.SubElement(ET.SubElement(group, 'ids'), 'id', value=str(index + 1))
    group.append(track)
    if origin not in origins:
        origins.append(origin)
    return component


def _constant(dictionary, component, key, values):
    fx.replace_ramp(dictionary, component, key, tuple([(0, v), (1, v)] for v in values))


def _scalar(dictionary, component, key, value):
    dictionary.property(component, key)
    fx.set_value(component, key, value)


def _particle(dictionary, component, *, life, alpha, axes, scale, offset=(0, 0, 0), recovery=False):
    # A zero continuous rate and a single initial particle prevent each bank
    # from accidentally making several attacks look like one long explosion.
    fx.timing(component, 0, .05)
    _scalar(dictionary, component, fx.INITIAL_COUNT, '1,1')
    _constant(dictionary, component, fx.EMIT_RATE, (0,))
    _constant(dictionary, component, fx.LIFESPAN, (life, life))
    _constant(dictionary, component, fx.PARTICLE_AXES, axes)
    fx.replace_ramp(dictionary, component, fx.PARTICLE_SCALE, (scale, scale))
    _scalar(dictionary, component, PARTICLE_OFFSET, ','.join(format(v, '.9g') for v in offset))
    packed = (0xff000000 | GOLD[0] << 16 | GOLD[1] << 8 | GOLD[2]) - 0x100000000
    _constant(dictionary, component, fx.PARTICLE_COLOR, (packed,))
    # Native particle and whole-effect color multiply. Neutralize the latter
    # explicitly so a dormant cyan ramp cannot tint the authored gold.
    _constant(dictionary, component, SYSTEM_COLOR, (-1,))
    _constant(dictionary, component, SYSTEM_BRIGHTNESS, (1,))
    peak = (.11 if recovery else .025) / life
    tail = (.22 if recovery else .09) / life
    fx.replace_ramp(dictionary, component, PARTICLE_ALPHA,
                    ([(0, 0), (peak, alpha), (tail, alpha * .45), (1, 0)],))
    fx.replace_ramp(dictionary, component, PARTICLE_BRIGHTNESS,
                    ([(0, .4), (peak, 1.6 if recovery else 2), (tail, .7), (1, 0)],))


def author(data: Path, key: str, dictionary):
    """Return independent editor XML, native origins, and source evidence."""
    profile = PROFILES[key]
    origin = data / SLASH
    root = ET.parse(origin).getroot()
    root.set('id', guid('vfx/visual-polish/tianqing/editor/' + key))
    root.find('phases').clear()
    root.find('trackgroups').clear()
    origins = []
    _append(root, data, 'bounds', key, 'Local Tianqing bounds', 0, dictionary, origins)
    recovery = profile['binding'] == 'cast'
    life = profile['lifespan']
    primary = _append(root, data, profile['primitive'], key,
                      'Golden recovery rise' if recovery else 'Golden heavy blade accent',
                      1, dictionary, origins)
    primary_scale = [(0, .65), (.12, .9), (1, .8)]
    _particle(dictionary, primary, life=life, alpha=.65 if recovery else .95,
              axes=profile['primary_axes'], scale=primary_scale, recovery=recovery)
    if recovery:
        # The installed XCD names this Keyframed Offset; this moves only the
        # particle accent. No character movement or gameplay healing is edited.
        fx.replace_ramp(dictionary, primary, KEYFRAMED_OFFSET, (
            [(0, 0), (1, 0)], [(0, .2), (1, 1.25)], [(0, 0), (1, 0)],
        ))
    else:
        _scalar(dictionary, primary, PIVOT_ROTATION, f'0,0,{profile["angle"]}')
        if profile['paired']:
            partner = _append(root, data, profile['primitive'], key,
                              'Matching golden fracture edge', 2, dictionary, origins)
            _particle(dictionary, partner, life=life, alpha=.78,
                      axes=profile['primary_axes'], scale=primary_scale)
            _scalar(dictionary, partner, PIVOT_ROTATION, f'0,0,{-profile["angle"]}')
    ring = _append(root, data, 'ring', key,
                   'Inward recovery ring' if recovery else 'Local heavy shock contour',
                   3, dictionary, origins)
    ring_life = .65 if recovery else life + .12
    ring_curve = ([(0, 1.15), (.4, .85), (1, .28)] if recovery else
                  [(0, .2 * profile['ring_scale']), (.18, .7 * profile['ring_scale']),
                   (1, 1.35 * profile['ring_scale'])])
    _particle(dictionary, ring, life=ring_life, alpha=.36 if recovery else .5,
              axes=(1, 1, 1), scale=ring_curve, recovery=recovery)
    duration = ring_life + .1
    fx.bounds(dictionary, root, 5, duration)
    details = dict(
        rgb=GOLD, shape=profile['presentation'], local_bounds_radius=5,
        particle_count=3 if profile.get('paired') else 2,
        emitter_duration=.05, continuous_emit_rate=0, particles_per_track=1,
        primary_particle_lifespan=life, contour_particle_lifespan=ring_life,
        opacity_peak_seconds=.11 if recovery else .025,
        bright_tail_seconds=.22 if recovery else .09,
        opacity_peak_basis='Synchronized serialized opacity/brightness ramps; rendered peak unverified',
        bank_repetitions=1, giant_sword_count=0, camera_shake_count=0,
        invocation_scope='one cast' if recovery else 'one actual hit',
        falling_swords='existing Tianqing spatial coordinator only',
        recovery_motion='local particle accent rises and ring shrinks' if recovery else None,
        remaining='AllSpark preview/compile, native material hue and orientation, client attachment, hit timing and low-quality playback',
    )
    return root, origins, details
