"""Nixue blade-width postpass after the existing SwordGlow conversion.

This factory edits the supplied XML only. It does not read candidate XML, write
files, compile, register resources, create shaders, or change any other profile.
"""
from __future__ import annotations

KEY = 'xueyan_nixue_cast'
BASELINE_PROFILE_SCALE = (.8, .65, 1.05)
WIDE_PROFILE_SCALE = (1.4, 1.0, 1.10)


def _constant(component, key):
    channels = component.findall(f'./properties/property[@id="{key}"]/data/datum/rampchanneldata/rampchannel')
    values = [[float(k.get('value')) for k in c.findall('./keyframes/keyframe')] for c in channels]
    if len(values) != 3 or any(len(row) != 2 or len(set(row)) != 1 for row in values):
        raise ValueError('Nixue v2 requires three constant native model channels')
    return tuple(row[0] for row in values)


def apply(root, dictionary, key):
    if key != KEY:
        return {}
    import sword_glow as glow
    import taixuan_visual_polish as tx
    fx = tx.fx
    native_min, native_max = tx.NATIVE_SWORD['minimum'], tx.NATIVE_SWORD['maximum']
    native_size = tuple(b-a for a, b in zip(native_min, native_max))
    native_center = tuple((a+b)/2 for a, b in zip(native_min, native_max))
    steel_size = tuple(b-a for a, b in zip(*tx.STEEL_SWORD_BOUNDS))

    def convert(profile):
        sizes = tuple(s*v for s, v in zip(steel_size, profile))
        # Steel -Z is the long axis; the luminous native sword points along +Y.
        return (sizes[0]/native_size[0], sizes[2]/native_size[1], sizes[1]/native_size[2])

    expected_old, new_scale = convert(BASELINE_PROFILE_SCALE), convert(WIDE_PROFILE_SCALE)
    models = root.findall('.//component[@class="Model"]')
    if len(models) != 8:
        raise ValueError('Nixue v2 requires exactly eight existing sword models')
    prepared = []
    for model in models:
        mesh = model.find(f'./properties/property[@id="{fx.MESH}"]/data/datum')
        if mesh is None or glow.visual_id('xueyan') not in mesh.get('value', ''):
            raise ValueError('Nixue v2 must follow the existing SwordGlow conversion')
        if (model.get('start'), model.get('end')) != ('0', '1'):
            raise ValueError('Nixue v2 requires the reviewed one-second baseline')
        old_scale = _constant(model, fx.MODEL_SCALE)
        if max(abs(a-b) for a, b in zip(old_scale, expected_old)) > 1e-8:
            raise ValueError('Unexpected Nixue baseline scale or duplicate v2 postpass')
        rotation = glow._rotation(_constant(model, tx.MODEL_ROTATION))
        position = model.find(f'./properties/property[@id="{fx.POSITION}"]/data/datum')
        old_position = tuple(map(float, position.get('value').split(',')))
        # Compensate the non-centred native mesh pivot so its centre follows
        # exactly the reviewed path. Animated position/rotation keys are intact.
        local_delta = tuple(native_center[i]*(old_scale[i]-new_scale[i]) for i in range(3))
        delta = tuple(sum(rotation[i][j]*local_delta[j] for j in range(3)) for i in range(3))
        prepared.append((model, position, tuple(old_position[i]+delta[i] for i in range(3))))
    # Validate every model before mutating the supplied tree.
    for model, position, new_position in prepared:
        channels = model.findall(f'./properties/property[@id="{fx.MODEL_SCALE}"]/data/datum/rampchanneldata/rampchannel')
        for channel, value in zip(channels, new_scale):
            for frame in channel.findall('./keyframes/keyframe'):
                frame.set('value', format(value, '.12g'))
        position.set('value', ','.join(format(v, '.12g') for v in new_position))
    return dict(nixue_v2=True, nixue_model_count=8, nixue_model_scale=new_scale,
                nixue_width_ratio=1.75, nixue_thickness_ratio=1/.65,
                nixue_length_ratio=1.10/1.05, nixue_centre_paths_preserved=True,
                sword_peak_seconds=.09, nixue_visual_acceptance='NOT_TESTED')
