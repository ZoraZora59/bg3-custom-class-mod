"""Tianqing visual authoring plan; no record in this module enables a game binding.

The falling banks are independent effects at a fixed ground anchor. They do not
define projectiles, actor movement, damage, costs, or areas of effect. Native
field/attachment validation and AllSpark compilation are separate prerequisites.
"""
from __future__ import annotations

from sword_cultivator_spec import guid


GREAT_SWORD = {
    'name': 'WPN_HUM_Greatsword_A_0',
    'guid': '12f3193c-ce1a-5a69-1bf0-8537b9b606f9',
    'bounds_min': (-0.16201761, -0.032432493, -1.57971),
    'bounds_max': (0.16201802, 0.05192164, 0.35004446),
    'resource_evidence': 'build/vfx-reference-research/human-weapons.lsx',
    'source_file': 'Generated/Public/Shared/Assets/Weapons/Resources/WPN_HUM_Greatsword_A_0.GR2',
    'long_axis': 'Z',
    'blade_direction': '-Z',
    'blade_direction_evidence': 'Asymmetric native resource bounds; not a vertex-level tip or visual verification',
    'initial_rotation_degrees': (-90, 0, 0),
    'down_direction': '-Y',
}

NATIVE_REFERENCES = {
    'falling_model': {
        'source': 'Editor/Mods/SharedDev/Assets/Effects/Spells/Cast/Intent/Summon/VFX_Spells_Cast_Intent_Summon_TargetSummon_SpiritualWeapon_Root_01.lsefx',
        'component_instance': 'd1618392-8443-4be9-9808-8009a478625d',
        'native_time': (0, .5),
        'native_offset': (0, 13, 0),
        'native_keyframed_y': (0, -10),
        'offset_property': '37b047c1-8fb7-4e7c-9319-58db9da44e77',
        'offset_module': '7a790ae7-3b1c-463e-bb1f-5cc14980b78c',
    },
    'shockwave': {
        'source': 'Editor/Mods/Shared/Assets/Effects/Spells/Cast/Paladin/VFX_Spells_Cast_Paladin_Target_ThunderousSmite_Impact_BodyFX_01.lsefx',
        'component_instance': '920ec035-71e5-4d4e-bd5d-920dfde922c6',
        'native_lifespan_reference': {'min': .6, 'max': 0,
                                      'note': 'Native serialized channels only; the effective fallback lifetime is not established'},
    },
    'target_ground': {
        'spell': 'Target_CallLightning',
        'field': 'PositionEffect',
        'mei_guid': 'de5e4e60-e2b7-44f4-aca8-c11390b4cc48',
        'mei_source': 'Editor/Mods/Shared/MultiEffectInfos/de5e4e60-e2b7-44f4-aca8-c11390b4cc48.mei',
        'target_bones': [],
        'pivot': 'Target',
        'detach_source': True,
        'detach_target': True,
        'keep_rotation': True,
        'use_orient_direction': False,
        'keep_scale': False,
        'start_text_key': 'Cast',
    },
    'source_cast': {
        'spell': 'Shout_AspectOfTheElk',
        'field': 'CastEffect',
        'mei_guid': '95cfcd2b-fccb-4415-9b6a-c24208bd0f06',
        'mei_source': 'Editor/Mods/SharedDev/MultiEffectInfos/95cfcd2b-fccb-4415-9b6a-c24208bd0f06.mei',
        'target_bones': ['Dummy_Root'], 'pivot': 'Target',
        'detach_target': True, 'keep_rotation': False,
        'use_orient_direction': False, 'start_text_key': 'Cast',
        'remaining': 'Validate detached caster transform and fixed world center in the actual Shout execution',
    },
}


def _fall(label, effect, count, height, scale, hit, *, radius=0, area=0):
    return {
        'label': label, 'motion': 'vertical_fall', 'authoring_enabled': True,
        'effect_name': effect, 'planned_mei_guid': guid('vfx/tianqing-redesign/mei/' + effect),
        'sword_count': count, 'drop_height': height, 'model_axis_scale': scale,
        'hit_time': hit, 'impact_start': hit, 'impact_opacity_peak_time': hit,
        'duration': round(hit + .85, 3), 'lead_in': .1,
        'model_fade_start': round(hit + .2, 3), 'model_fade_end': round(hit + .45, 3),
        'layout': 'ring' if count > 1 else 'center', 'layout_radius': radius,
        'layout_angle_offset_degrees': 22.5 if count > 1 else 0,
        'shockwave_scale_factor': 1.2 if count > 1 else 2.4,
        'gameplay_area_radius_reference': area,
        'anchor': 'world_ground', 'target_bones': [],
        'collision_height': 0, 'continuous_model_rotation': False,
        'compiled': False, 'binding_enabled': False,
        'requires_allspark_preview': True, 'needs_native_validation': True,
    }


TIANQING_PROFILES = {
    'tianqing_nifeng': {'label': '逆锋横扫', 'motion': 'preserve_sweep', 'authoring_enabled': False, 'sword_count': 0},
    'tianqing_wanjun': _fall('万钧', 'VFX_ESC_Tianqing_Wanjun_GroundFall_01', 1, 10, (2.4, 2.4, 3.4), .6, area=6),
    'tianqing_lietian': _fall('裂天', 'VFX_ESC_Tianqing_Lietian_GroundFall_01', 1, 14, (2.8, 2.8, 4.8), .72),
    'tianqing_tianbeng': {'label': '天崩', 'motion': 'preserve_cone', 'authoring_enabled': False, 'sword_count': 0},
    'tianqing_tianfeng': {'label': '破阵', 'motion': 'preserve_rush', 'authoring_enabled': False, 'sword_count': 0},
    'tianqing_tianjian': _fall('天剑坠世', 'VFX_ESC_Tianqing_Tianjian_GroundFall_01', 1, 16, (3.6, 3.6, 6.6), .85, area=9),
    'tianqing_bafang': _fall('八方灭阵', 'VFX_ESC_Tianqing_Bafang_GroundRing_01', 8, 12, (2.2, 2.2, 3.2), .7, radius=8, area=18),
    'tianqing_tiandi': _fall('天地剑劫：单段', 'VFX_ESC_Tianqing_TiandiStage_GroundFall_01', 1, 16, (3.4, 3.4, 6), .8, area=9),
    'tianqing_xushi': {'label': '回元', 'motion': 'none', 'authoring_enabled': False, 'sword_count': 0},
    'tianqing_nixi': {'label': '回生', 'motion': 'none', 'authoring_enabled': False, 'sword_count': 0},
}
TIANQING_PROFILES['tianqing_tianjian']['followup_radius_reference'] = 6
TIANQING_PROFILES['tianqing_tianjian']['followup_giant_sword_count'] = 0
TIANQING_PROFILES['tianqing_bafang']['terrain_sampling'] = 'not_authored'
TIANQING_PROFILES['tianqing_bafang']['ground_contact_scope'] = 'flat plane at anchor Y'
TIANQING_PROFILES['tianqing_tiandi']['future_area_stage_count'] = 3
TIANQING_PROFILES['tianqing_tiandi']['bank_repetitions'] = 1

# Runtime plays this one-column bank at eight independently queried AI-grid
# anchors. Keep the original full-ring source as an editable flat-plane preview.
TIANQING_AUXILIARY_PROFILES = {
    'tianqing_bafang_column': _fall('八方灭阵：单柱', 'VFX_ESC_Tianqing_Bafang_GroundColumn_01',
                                  1, 12, (2.2, 2.2, 3.2), .7, area=18),
}
TIANQING_AUXILIARY_PROFILES['tianqing_bafang_column']['shockwave_scale_factor'] = 1.2

# Native damage timing is animation-dependent. These banks split the visible
# anticipation from the actual contact callback; no timing value here drives
# damage, costs or saves. The existing complete falls remain byte-for-byte
# independent, especially the coordinated Tiandi stage bank.
TIANQING_TIMING_PROFILES = {}
TIANQING_TIMING_PAIRS = {}
for _key, _base_key in (
    ('tianqing_wanjun', 'tianqing_wanjun'),
    ('tianqing_lietian', 'tianqing_lietian'),
    ('tianqing_tianjian', 'tianqing_tianjian'),
    ('tianqing_bafang', 'tianqing_bafang_column'),
):
    _base = {**TIANQING_PROFILES, **TIANQING_AUXILIARY_PROFILES}[_base_key]
    _stem = _base['effect_name'].removesuffix('_01')
    _pair = {}
    for _phase in ('prepare', 'impact'):
        _profile_key = _key + '_' + _phase
        TIANQING_TIMING_PROFILES[_profile_key] = {
            **_base, 'base_profile': _base_key, 'timing_phase': _phase,
            'effect_name': _stem + ('_PrepareHover_01' if _phase == 'prepare' else '_Contact_01'),
            'hit_time': 0 if _phase == 'impact' else _base['hit_time'],
            'duration': .85 if _phase == 'impact' else round(_base['hit_time'] + .2, 3),
            'hover_height': .6, 'loop_duration': .1, 'stop_fade': .1,
            'model_fade_start': .2, 'model_fade_end': .45,
            'motion': 'hover_prepare' if _phase == 'prepare' else 'instant_ground_contact',
        }
        _pair[_phase] = _profile_key
    TIANQING_TIMING_PAIRS[_key] = _pair


def _plan(key, stats, field, anchor, *, execution=False, forbidden=False, note=''):
    profile = TIANQING_PROFILES[key]
    return {
        'profile': key, 'stats_names': stats, 'current_spell_type': stats[0].split('_', 1)[0],
        'proposed_field': field, 'proposed_anchor': anchor,
        'planned_mei_guid': profile.get('planned_mei_guid'),
        'native_reference_mei_guid': NATIVE_REFERENCES['target_ground']['mei_guid'],
        'native_reference_scope': 'Target PositionEffect only; does not validate this other SpellType or helper context',
        'compiled': False, 'binding_enabled': False, 'blocked_activation': True,
        'needs_native_validation': True, 'requires_execution_redesign': execution,
        'helper_binding_forbidden': forbidden, 'note': note,
    }


TIANQING_BINDING_PLAN = [
    _plan('tianqing_wanjun', ['Target_ESC_tianqing_wanjun'],
          'PositionEffect', 'selected_target_ground',
          note='One bank per cast at the selected area center. Never attach the giant to per-victim HitEffect.'),
    _plan('tianqing_lietian', ['Target_ESC_tianqing_lietian'],
          'TargetEffect', 'selected_target_root_detached',
          note='Canonical Target execution is implemented; Runtime plays one detached bank at the selected target ground. This authoring plan alone does not enable the binding or prove native appearance. Preserve AUTO foundation, attack roll, range and costs.'),
    _plan('tianqing_tianjian', ['Projectile_ESC_TianjianImpact', 'Projectile_ESC_TianjianImpact_Off'],
          'PositionEffect', 'landing_explosion_ground',
          note='Only the landing helper is a candidate. Validate PositionEffect in CreateExplosion context and exactly one bank per landing. Preserve Projectile_Jump and actor trajectory.'),
    _plan('tianqing_bafang', ['Shout_ESC_tianqing_bafang'],
          'CastEffect', 'caster_self_ground_detached',
          note='One bank contains eight simultaneous vertical swords around self, independent of victim count. Native Shout CastEffect attachment/textkey still needs validation; PositionEffect is not assumed supported.'),
    _plan('tianqing_tiandi', ['Target_ESC_tianqing_tiandi'],
          'PositionEffect', 'selected_area_ground', execution=True,
          note='Single-sword bank is for a future area-wide stage coordinator. Three stages share one fixed 9m area center; bank itself never repeats.'),
    _plan('tianqing_tiandi', ['Target_ESC_TiandiStage', 'Target_ESC_TiandiStage_Off', 'Target_ESC_TiandiStage_NoControl', 'Target_ESC_TiandiStage_NoControl_Off'],
          None, 'future_area_stage_coordinator_only', execution=True, forbidden=True,
          note='Current Runtime invokes this helper twice per marked creature immediately. Never bind a giant to these per-target helpers; N targets would produce 2N extra swords.'),
    _plan('tianqing_tianjian', ['Target_ESC_Aftershock'], None, 'independent_followup_target', forbidden=True,
          note='6m aftershock uses independent later targets; keep a small local impact only. No second giant sword and no reuse of the landing bank per enemy.'),
]
for plan in TIANQING_BINDING_PLAN:
    plan['expected_bank_invocations_per_cast'] = (3 if plan['profile'] == 'tianqing_tiandi' else 1)
    if plan['helper_binding_forbidden']:
        plan['expected_bank_invocations_per_cast'] = 0
    plan['swords_per_bank'] = TIANQING_PROFILES[plan['profile']]['sword_count']
    plan['requires_runtime_stage_coordinator'] = plan['profile'] == 'tianqing_tiandi'
    plan['fields_to_review_before_activation'] = ['SpellAnimation', 'CastTextEvent', 'CastEffect', 'HitEffect', 'TargetEffect', 'TargetHitEffect', 'PositionEffect', 'Trajectories']
    if plan['profile'] == 'tianqing_bafang':
        plan['requires_per_column_ground_height_validation'] = True
        plan['native_reference_mei_guid'] = NATIVE_REFERENCES['source_cast']['mei_guid']
        plan['native_reference_scope'] = 'Native Shout CastEffect uses Dummy_Root with Cast textkey; detached transform/once-per-cast playback still requires validation'

PRESERVED_ENTRIES = {
    'tianqing_nifeng': ['Zone_ESC_tianqing_nifeng', 'Zone_ESC_tianqing_nifeng_RangedOff_Bonus'],
    'tianqing_tianbeng': ['Target_ESC_tianqing_tianbeng', 'Target_ESC_TianbengMain', 'Target_ESC_TianbengMain_Off', 'Target_ESC_TianbengCone', 'Target_ESC_TianbengCone_Off'],
    'tianqing_tianfeng': ['Rush_ESC_tianqing_tianfeng'],
    'tianqing_xushi': ['Shout_ESC_tianqing_xushi'],
    'tianqing_nixi': ['Target_ESC_tianqing_nixi'],
}
