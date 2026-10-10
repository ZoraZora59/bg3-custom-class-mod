"""Isolated flight-readability candidate; native compilation/acceptance pending.

Called after the existing projectile factory. No stats, trajectory, speed,
damage, runtime listener or projectile responsibilities are changed here.
The complete native MagicMissile particle donors retain their native materials
and modules; XCD/XMD lookup activates every property modified below.
"""
from pathlib import Path

BODY_FACTORS = dict(common=1.5, taixuan=1.5, tianqing=1.2, xueyan=1.5, xingge=1.5)
WAKE_FACTORS = dict(common=1.5, taixuan=2.0, tianqing=1.5, xueyan=1.5, xingge=1.5)
COLORS = dict(common=(170, 230, 255), taixuan=(170, 230, 255),
              tianqing=(255, 217, 145), xueyan=(230, 65, 60), xingge=(100, 235, 190))
PARTICLE_SPACE = 'b13c2ffd-c94f-4d56-947e-07077287ec52'
PARTICLE_BRIGHTNESS = '7b01f163-d329-4cd0-97f0-31115055b9c8'
PARTICLE_ALPHA = 'd1892ce7-07f3-4d9c-9acb-6692b897a71b'
PARTICLE_AXIS_SCALE = '3ab58b27-d41b-4221-b714-cb35fd213ce7'
PARTICLE_MAX_COUNT = '21176254-19ca-43e0-a890-b20fd264cca3'
RIBBON_SPACE = 'c79c53ae-a659-4570-88d0-11bbcb142327'
RIBBON_LIFE = 'edfa1f19-e70e-453a-a5af-310875d04854'
TAIL_SECONDS = .35


def _constant(fx, dictionary, component, key, values):
    fx.replace_ramp(dictionary, component, key,
                    tuple([(0, value), (1, value)] for value in values))


def _scalar(fx, dictionary, component, key, value):
    dictionary.property(component, key)
    fx.set_value(component, key, value)


def _native_particle(fx, dictionary, component, rgb, *, space, lifespan,
                     scale, emit_rate, initial_count, brightness, fade):
    _scalar(fx, dictionary, component, PARTICLE_SPACE, space)
    _scalar(fx, dictionary, component, fx.INITIAL_COUNT,
            f'{initial_count},{initial_count}')
    _constant(fx, dictionary, component, fx.LIFESPAN, (lifespan, lifespan))
    _constant(fx, dictionary, component, fx.PARTICLE_SCALE, scale)
    _constant(fx, dictionary, component, fx.EMIT_RATE, (emit_rate,))
    _constant(fx, dictionary, component, PARTICLE_BRIGHTNESS, (brightness,))
    packed = 0xff000000 | rgb[0] << 16 | rgb[1] << 8 | rgb[2]
    argb = packed - 0x100000000
    _constant(fx, dictionary, component, fx.PARTICLE_COLOR, (argb,))
    fx.replace_ramp(dictionary, component, PARTICLE_ALPHA, (fade,))
    # Preserve native orientation, particle axis shape, UV animation, material,
    # emitter shape and all other donor properties. This is not a mesh shader
    # override and does not rely on the SPRW preskinned sword being visible.
    fx.timing(component, 0, .2)


def improve_projectile(data, style, root, dictionary, fx):
    """Return origins/design after changing only visual composition in root."""
    if style not in BODY_FACTORS:
        raise ValueError(f'Unsupported sword visual style {style}')
    components = root.findall('./trackgroups/trackgroup/track/component')
    bodies = [c for c in components if c.get('class') == 'Model']
    ribbons = [c for c in components if c.get('class') == 'Ribbon 2.0']
    if len(bodies) != 1 or len(ribbons) != 1:
        raise ValueError('Readability candidate expects one sword and one native ribbon')
    fx.multiply(dictionary, bodies[0], fx.MODEL_SCALE, BODY_FACTORS[style])
    fx.multiply(dictionary, ribbons[0], fx.RIBBON_SCALE, WAKE_FACTORS[style])
    _scalar(fx, dictionary, ribbons[0], RIBBON_SPACE, 0)
    _scalar(fx, dictionary, ribbons[0], RIBBON_LIFE, TAIL_SECONDS)
    donor = Path(data) / fx.BASE / 'Projectiles/VFX_Projectiles_Force_MagicMissile_Projectile_01.lsefx'
    core, = fx.copy_tracks(root, donor,
                          [(1, 1, 'b9487f22-535a-443d-a873-aef354c9a1b3')],
                          style, 'Native luminous flight core')
    wake, = fx.copy_tracks(root, donor,
                          [(1, 2, '2dd9c85b-43ee-4124-806a-640c9c3cf76e')],
                          style, 'Native luminous flight afterglow')
    rgb = COLORS[style]
    _native_particle(fx, dictionary, core, rgb, space=1, lifespan=.25,
                     scale=(1.5, 2.0), emit_rate=30, initial_count=1, brightness=8,
                     fade=[(0, .7), (.15, 1), (.8, .8), (1, 0)])
    _native_particle(fx, dictionary, wake, rgb, space=0, lifespan=TAIL_SECONDS,
                     scale=(.2, .28), emit_rate=44, initial_count=2, brightness=6,
                     fade=[(0, .75), (.6, .55), (1, 0)])
    # Keep native trail length; increase its visible thickness and capacity.
    fx.multiply(dictionary, wake, PARTICLE_AXIS_SCALE, (1, 4, 1))
    _scalar(fx, dictionary, wake, PARTICLE_MAX_COUNT, 24)
    # H visibility candidate: broaden single common/Taixuan sword silhouette.
    # Keep native materials, RGB, brightness, count, lifetime and motion intact.
    if style in ('common', 'taixuan'):
        fx.multiply(dictionary, bodies[0], fx.MODEL_SCALE, (1.75, 1.75, 1.1))
        fx.multiply(dictionary, ribbons[0], fx.RIBBON_SCALE, 1.8)
        fx.multiply(dictionary, core, PARTICLE_AXIS_SCALE, (1.6, 1, 1))
        fx.multiply(dictionary, wake, PARTICLE_AXIS_SCALE, (1, 2, 1))
    bound, = [c for c in components if c.get('class') == 'BoundingSphere']
    fx.bounds(dictionary, root, 12, float(bound.get('end')))
    from sword_visible_blade import improve_projectile as visible_blade
    extra_origins, blade_detail = visible_blade(data, style, root, dictionary)
    return [donor, *extra_origins], dict(**blade_detail, readability_candidate=True,
                         sword_size_multiplier=BODY_FACTORS[style],
                         ribbon_width_multiplier=WAKE_FACTORS[style],
                         native_local_core=True, native_world_afterglow=True,
                         native_particle_systems_added=2,
                         tail_seconds=.50 if style in ('common','taixuan') else TAIL_SECONDS,
                         core_uniform_scale=(1.5, 2.0), core_brightness=8,
                         afterglow_thickness_multiplier=4, afterglow_brightness=6,
                         afterglow_max_particle_count=24,
                         rgb=rgb, culling_radius=12,
                         visual_acceptance='pending native compilation and unobstructed client frames',
                         projectile_stop_lifecycle='pending: finite particle life alone does not prove survival after impact')
