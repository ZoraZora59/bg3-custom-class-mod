"""Stable, explicitly enabled VFX registrations for the sword cultivator.

This module describes bindings; it never writes assets, Stats, or game files.
An enabled phase means that its compiled effect and resource have been made.
The projectile phase is the Trail Effect resource of a Projectile template,
not a MultiEffectInfo.  Its impact is also an Effect resource on that template.

Official resource and binding references:
https://docs.baldursgate3.game/index.php?title=VFX_%E2%80%93_Part_2:_Creating_Resources
https://docs.baldursgate3.game/index.php?title=VFX_%E2%80%93_Part_4:_Advanced_Information
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from sword_cultivator_spec import SPELLS, guid


STYLES = ('common', 'taixuan', 'tianqing', 'xueyan', 'xingge')
PHASES = ('prepare', 'cast', 'impact', 'status', 'projectile')
DEFAULT_ENABLED_PHASES = frozenset({('common', 'projectile'), ('common', 'impact')})
_enabled_phases = DEFAULT_ENABLED_PHASES

# Each named design entry has an explicit primary family.  Variants preserve
# that family; they do not become unrelated spells because their Stats type,
# weapon hand, resource choice, or frenzy contribution differs.
FAMILY_KEYS = {
    'single_sword': (
        'yujian', 'sword_strike', 'taixuan_zhaoxi', 'tianqing_nifeng',
        'xueyan_luexue', 'xingge_wenlu',
    ),
    'strike_line': (
        'tianqing_lietian', 'tianqing_tianfeng', 'xueyan_chuanshen',
        'taixuan_yixiantian',
    ),
    'multi_stage': ('taixuan_liuguang', 'xueyan_liancheng', 'xueyan_wusheng'),
    'area_swords': (
        'taixuan_jiuxiao', 'tianqing_wanjun', 'tianqing_tianbeng',
        'tianqing_tianjian', 'tianqing_bafang', 'tianqing_tiandi',
    ),
    'self_burst': ('taixuan_xinghe', 'xueyan_nixue'),
    'domain': ('taixuan_taiqing', 'xueyan_xuehai'),
    'team_support': (
        'xingge_huifeng', 'xingge_chengfeng', 'xingge_tongzhou',
        'xingge_fengyu', 'xingge_zhangjian',
    ),
    'guard': ('qi_guard', 'taixuan_qinghui'),
    'restoration': (
        'tiaoxi', 'tianqing_xushi', 'xueyan_ranxue', 'taixuan_guiyuan',
        'tianqing_nixi', 'xueyan_huichao', 'xingge_xiangfu',
    ),
    'utility': (
        'qi_sword', 'xueyan_damage_mode', 'control_release', 'xingge_fuchen',
        'focus_target',
    ),
    'movement': ('sword_flight',),
}
KEY_FAMILIES = {key: family for family, keys in FAMILY_KEYS.items() for key in keys}
if set(KEY_FAMILIES) != set(SPELLS):
    raise ValueError('Sword VFX families must cover every named skill exactly')
if sum(map(len, FAMILY_KEYS.values())) != len(KEY_FAMILIES):
    raise ValueError('A named skill appears in more than one Sword VFX family')

# Internal native damage/control stages are not additional player skills.
# Map their visual origin explicitly rather than inferring it from damage type.
INTERNAL_KEYS = {
    'YixiantianHit': 'taixuan_yixiantian',
    'TianjianImpact': 'tianqing_tianjian',
    'TaiqingPulse': 'taixuan_taiqing',
    'BloodPulse': 'xueyan_xuehai',
    'Counter2': 'qi_guard',
    'Counter3': 'taixuan_qinghui',
    'Resonance': 'xingge_zhangjian',
    'Aftershock': 'tianqing_tianjian',
    'TiandiStage': 'tianqing_tiandi',
    'TiandiStage_NoControl': 'tianqing_tiandi',
    'TianbengMain': 'tianqing_tianbeng',
    'LiuguangStage': 'taixuan_liuguang',
    'TianbengCone': 'tianqing_tianbeng',
    'ChengfengBurst': 'xingge_chengfeng',
    'HuifengControl': 'xingge_huifeng',
}
_VARIANT = re.compile(
    r'(?:_(?:Main|Off|MeleeMain|MeleeOff|RangedMain|RangedOff)(?:_Bonus)?'
    r'|_F(?:[0-9]|1[0-5])|_Yuan|_Frenzy)?\Z'
)


def _validate(style: str, phase: str | None = None) -> None:
    if style not in STYLES:
        raise ValueError(f'Unknown Sword VFX style: {style}')
    if phase is not None and phase not in PHASES:
        raise ValueError(f'Unknown Sword VFX phase: {phase}')


def effect_guid(style: str, phase: str) -> str:
    """EffectResource GUID; used directly by projectile Trail/Impact fields."""
    _validate(style, phase)
    return guid(f'vfx/effect/{style}/{phase}')


def mei_guid(style: str, phase: str) -> str:
    """MultiEffectInfo GUID; used by Spell/Status effect fields."""
    _validate(style, phase)
    if phase == 'projectile':
        raise ValueError('Projectile trails bind an EffectResource, not an MEI')
    return guid(f'vfx/mei/{style}/{phase}')


def projectile_guid(style: str) -> str:
    """Primary Bezier3 Projectile RootTemplate GUID."""
    _validate(style)
    return guid(f'vfx/projectile/{style}')


def projectile_pathfind_guid(style: str) -> str:
    """Fallback Pathfind RootTemplate GUID, inheriting the primary template."""
    _validate(style)
    return guid(f'vfx/projectile/{style}/pathfind')


def projectile_trajectories(style: str) -> str:
    """Preserve Magic Missile's Bezier3-then-Pathfind trajectory waterfall."""
    return projectile_guid(style) + ',' + projectile_pathfind_guid(style)


def effect_name(style: str, phase: str) -> str:
    _validate(style, phase)
    return f'VFX_ESC_{style.title()}_{phase.title()}_01'


def mei_name(style: str, phase: str) -> str:
    # Validate the resource kind as well as its spelling.
    mei_guid(style, phase)
    return f'ESC_{style}_{phase}'


def projectile_name(style: str) -> str:
    _validate(style)
    return f'ESC_{style}_SwordProjectile'


def _allowlist(enabled: Iterable[tuple[str, str]] | None) -> frozenset[tuple[str, str]]:
    result = _enabled_phases if enabled is None else frozenset(enabled)
    for style, phase in result:
        _validate(style, phase)
    return result


def set_enabled_phases(enabled: Iterable[tuple[str, str]]) -> frozenset[tuple[str, str]]:
    """Replace the process-local allowlist after actual assets are available.

    Callers may pass an empty iterable to retain all existing visuals.  The
    change is in memory only; no asset is generated or installed by this API.
    """
    global _enabled_phases
    _enabled_phases = _allowlist(enabled)
    return _enabled_phases


def enabled_phases() -> frozenset[tuple[str, str]]:
    return _enabled_phases


def guard_status_effect(enabled: Iterable[tuple[str, str]] | None = None) -> str:
    """Use the compiled orbiting-sword status, retaining a native fallback."""
    if ('common', 'status') in _allowlist(enabled):
        return mei_guid('common', 'status')
    return '87356553-5bed-4e2b-86eb-f0697e5ec648'


def asset_registry(enabled: Iterable[tuple[str, str]] | None = None) -> dict[str, object]:
    """Describe stable registrations without claiming unmade phases exist."""
    allowed = _allowlist(enabled)
    effects = []
    meis = []
    projectiles = []
    for style in STYLES:
        for phase in PHASES:
            active = (style, phase) in allowed
            effects.append(dict(style=style, phase=phase, name=effect_name(style, phase),
                                uuid=effect_guid(style, phase), enabled=active))
            if phase != 'projectile':
                meis.append(dict(style=style, phase=phase, name=mei_name(style, phase),
                                 uuid=mei_guid(style, phase),
                                 effect=effect_guid(style, phase), enabled=active))
        projectiles.append(dict(
            style=style, name=projectile_name(style), uuid=projectile_guid(style),
            pathfind_uuid=projectile_pathfind_guid(style),
            trajectories=projectile_trajectories(style),
            trail=effect_guid(style, 'projectile'),
            impact=effect_guid(style, 'impact') if (style, 'impact') in allowed else '',
            enabled=(style, 'projectile') in allowed,
        ))
    return dict(effects=effects, meis=meis, projectiles=projectiles)


@dataclass(frozen=True)
class SpellPresentation:
    key: str
    style: str
    family: str
    form: str
    hand: str
    variant: str
    container: bool
    internal: bool


def classify_spell(name: str, values: Mapping[str, object]) -> SpellPresentation:
    """Classify all named, variant, continuation, and internal native rows.

    Unknown ESC rows fail here so adding a skill cannot silently give it an
    unrelated Magic Missile profile.  Classification changes no gameplay data.
    """
    if '_ESC_' not in name:
        raise ValueError(f'Not a Sword Cultivator spell: {name}')
    spell_type, token = name.split('_ESC_', 1)
    spell_type = str(values.get('SpellType', spell_type))
    container = bool(values.get('ContainerSpells', ''))
    internal = False
    variant = ''
    key = ''

    if token in ('FlightMove', 'ChainMove'):
        key = 'sword_flight' if token == 'FlightMove' else 'xueyan_liancheng'
        internal, variant = True, token
    else:
        continuation = re.fullmatch(r'(liancheng|wusheng)_Continue(Melee|Ranged)', token)
        if continuation:
            key = 'xueyan_' + continuation.group(1)
            variant = 'Continue' + continuation.group(2)
        else:
            helper = token.removesuffix('_Off')
            if helper in INTERNAL_KEYS:
                key, internal = INTERNAL_KEYS[helper], True
                variant = token
            else:
                for candidate in sorted(SPELLS, key=len, reverse=True):
                    if token == candidate or token.startswith(candidate + '_'):
                        suffix = token[len(candidate):]
                        if _VARIANT.fullmatch(suffix):
                            key, variant = candidate, suffix.removeprefix('_')
                            break
    if not key:
        raise ValueError(f'Unclassified Sword Cultivator spell or variant: {name}')

    roll = str(values.get('SpellRoll', ''))
    flags = str(values.get('SpellFlags', '')).split(';')
    hand = 'off' if ('Off' in variant or 'OffHand' in roll) else 'main'
    if container:
        form = 'container'
    elif 'IsJump' in flags:
        form = 'movement'
    elif internal and token.startswith('TianjianImpact'):
        form = 'impact'
    elif spell_type == 'Rush':
        form = 'rush'
    elif spell_type == 'Zone':
        form = 'zone'
    elif spell_type == 'Projectile':
        form = 'ranged'
    elif 'Melee' in roll:
        form = 'melee'
    elif internal:
        form = 'internal'
    elif spell_type == 'Shout':
        form = 'self'
    else:
        form = 'target'
    return SpellPresentation(key, SPELLS[key]['branch'], KEY_FAMILIES[key],
                             form, hand, variant, container, internal)


def spell_vfx_bindings(
    presentation: SpellPresentation,
    values: Mapping[str, object],
    enabled: Iterable[tuple[str, str]] | None = None,
) -> dict[str, str]:
    """Return only phase bindings whose assets have explicitly been enabled."""
    if presentation.container:
        return {}
    allowed = _allowlist(enabled)
    style = presentation.style
    result = {}
    for phase, field in (('prepare', 'PrepareEffect'), ('cast', 'CastEffect')):
        if (style, phase) in allowed:
            result[field] = mei_guid(style, phase)

    # Human Jump/Fly trajectories are execution data.  Never replace them with
    # a flying-sword projectile merely because their table type is Projectile.
    if presentation.form == 'movement':
        return result
    if presentation.form == 'ranged':
        if (style, 'projectile') in allowed:
            result['Trajectories'] = projectile_trajectories(style)
        # Projectile templates own their Impact Effect; also attaching the same
        # impact MEI to the spell would play it twice.
        return result

    execution = ';'.join(str(values.get(field, '')) for field in (
        'SpellProperties', 'SpellSuccess', 'SpellFail',
    ))
    if (style, 'impact') in allowed and 'DealDamage(' in execution:
        result['HitEffect'] = mei_guid(style, 'impact')
        # Replace the prior native hit/target visual as a unit; in particular,
        # do not leave Cleave's TargetEffect next to the new sword impact.
        result['TargetEffect'] = ''
        result['TargetHitEffect'] = ''
    return result
