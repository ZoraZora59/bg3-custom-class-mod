"""Damage presentation for the sword-cultivator's existing spell rules.

``spell_tooltip`` returns presentation fields only and never changes ``spec``.
The caller localizes ``extra_text`` into ``ExtraDescription`` and copies the
other fields to the spell.  Cloned off-hand variants must also replace the
weapon tokens in ``ExtraDescriptionParams`` (or call with ``hand='off'`` in
their spec).

``LEVEL_MAPS`` maps native series names to explicit level/value pairs.  Emit
these as LevelMapSeries with PreferredClassUUID bound to the MAIN sword-
cultivator class, so multiclass character level cannot advance these dice.
Only the designed levels 1-12 are emitted; these maps do not add class content.

Official references:
https://docs.baldursgate3.game/Making_a_Basic_Spell
https://docs.baldursgate3.game/index.php?title=Stats_Expressions
The installed Shared/Levelmaps/LevelMapValues.tbl's SneakAttack series is the
native class-bound level-map example.  Its editor field is PreferredClass;
the corresponding runtime LSX field is PreferredClassUUID.

The native tooltip parser does not accept our execution IF functors.  A
switchable weapon/Qi roll or Necrotic/Force type therefore gets clearly
labeled alternative damage in ExtraDescription, without a false fixed type.
Displayed values are BASE damage: Lua damage multipliers, Frenzy spending,
equipment riders, resistance and target-specific reduction resolve on hit.
"""

from __future__ import annotations

from collections.abc import Mapping


def _ranks(first: str, middle: str, final: str) -> dict[int, str]:
    return {
        level: first if level < 5 else middle if level < 10 else final
        for level in range(1, 13)
    }


LEVEL_MAPS = {
    'ESC_ZhaoxiDamage': _ranks('2d8', '3d8', '4d8'),
    'ESC_NifengDamage': _ranks('3d8', '4d8', '5d8'),
    'ESC_LuexueDamage': _ranks('2d6', '3d6', '4d6'),
    'ESC_WenluDamage': _ranks('1d4', '1d6', '2d6'),
}

_NORMAL_MAPS = {
    'taixuan_zhaoxi': 'ESC_ZhaoxiDamage',
    'tianqing_nifeng': 'ESC_NifengDamage',
    'xueyan_luexue': 'ESC_LuexueDamage',
    'xingge_wenlu': 'ESC_WenluDamage',
}

_QI_BASE = '2d6+WisdomModifier'


def _sum(*expressions: str) -> str:
    return '+'.join(expression for expression in expressions if expression)


def _damage(expression: str, damage_type: str = 'Force') -> str:
    # The official tooltip examples omit Magical from DealDamage parameters.
    return f'DealDamage({expression},{damage_type})'


def _result(
    native: str = '', extra: str = '', params: str = '',
) -> dict[str, str]:
    return {
        'TooltipDamageList': native,
        'extra_text': extra,
        'ExtraDescriptionParams': params,
    }


def spell_tooltip(key: str, spec: Mapping[str, object]) -> dict[str, str]:
    """Describe current damage without costs, ranges, or future upgrades.

    ``spec`` uses the generator's base/dice/branch/segments fields.  Optional
    ``hand`` accepts main/off and selects the corresponding weapon tokens.
    Empty values deliberately clear misleading inherited damage previews.
    """
    base = str(spec.get('base', ''))
    branch = str(spec.get('branch', key.split('_', 1)[0]))
    hand = str(spec.get('hand', 'main')).lower()
    weapon = 'OffhandMeleeWeapon' if hand in ('off', 'offhand') else 'MainMeleeWeapon'
    weapon_type = weapon + 'DamageType'
    weapon_damage = _damage(weapon, weapon_type)

    if key == 'taixuan_qinghui':
        return _result(
            extra='每次反击的基础伤害：[1]。',
            params=_damage(_sum(_QI_BASE, '4d8')),
        )

    if not base:
        return _result()

    # These entry-level buttons are replaced by branch sword arts before the
    # player obtains Qi Sword mode.  Do not preview a future mode on them.
    if key in ('yujian', 'sword_strike'):
        return _result(weapon_damage)

    bonus = (
        f'LevelMapValue({_NORMAL_MAPS[key]})' if key in _NORMAL_MAPS
        else '32d8' if key == 'tianqing_tianbeng'
        else str(spec.get('dice', ''))
    )

    if branch == 'xueyan':
        # Bare expressions retain dynamic dice/Wisdom values without claiming
        # that the currently selected damage type is always Necrotic or Force.
        qi_damage = _sum(_QI_BASE, bonus)
        if base == 'WQ':
            return _result(
                extra=('基础伤害：佩剑 [1]，另附 [2] 剑气伤害；'
                       '气剑 [3] 剑气伤害。剑气可选坏死或力场。'),
                params=';'.join((weapon_damage, bonus, qi_damage)),
            )
        if base == 'W':
            return _result(
                extra=('基础伤害：佩剑 [1]，另附 [2] 剑气伤害。'
                       '剑气可选坏死或力场。'),
                params=';'.join((weapon_damage, bonus)),
            )
        label = {
            'xueyan_liancheng': '四剑，每剑基础伤害',
            'xueyan_wusheng': '六剑，每剑基础伤害',
            'xueyan_xuehai': '每次落剑的基础伤害',
        }.get(key, '基础伤害')
        if spec.get('continuation'):
            label = '本次续剑的基础伤害'
        return _result(
            extra=f'{label}：[1] 剑气伤害（坏死或力场）。',
            params=qi_damage,
        )

    if base == 'WQ':
        # Both alternatives are displayed separately; the two rolls are not
        # summed as if the caster were using a weapon and a Qi sword together.
        return _result(
            extra='基础伤害：佩剑 [1]，另附 [2]；气剑 [3]。',
            params=';'.join((
                weapon_damage, _damage(bonus), _damage(_sum(_QI_BASE, bonus)),
            )),
        )

    native = (
        _damage(_sum(_QI_BASE, bonus)) if base == 'Q'
        else weapon_damage + (';' + _damage(bonus) if bonus else '')
    )

    if key == 'tianqing_tianbeng':
        return _result(
            native,
            '所示为主目标基础伤害；其他敌人：[1]，另附 [2]。',
            ';'.join((weapon_damage, _damage('18d8'))),
        )
    if key == 'taixuan_xinghe':
        return _result(
            native,
            '所示为剑雨基础伤害；每次反击造成 [1]。',
            _damage(_sum(_QI_BASE, '6d8')),
        )
    if key == 'tianqing_tianjian':
        return _result(
            native,
            '所示为落点基础伤害；余威每次造成 [1]。',
            _damage('6d8'),
        )
    labels = {
        'taixuan_liuguang': '四剑；所示为每剑基础伤害。',
        'taixuan_jiuxiao': '所示为每名敌人的基础伤害。',
        'taixuan_taiqing': '所示为每次落剑的基础伤害。',
        'taixuan_yixiantian': '所示为首名敌人的基础伤害。',
        'tianqing_tiandi': '三剑；所示为每剑基础伤害。',
        'xingge_chengfeng': '所示为每名敌人的基础伤害。',
        'xingge_zhangjian': '所示为每次御剑呼应的基础伤害。',
    }
    return _result(native, labels.get(key, '所示为基础伤害。'))
