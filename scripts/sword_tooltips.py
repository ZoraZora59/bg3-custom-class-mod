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

The native tooltip parser does not accept our execution IF functors.  An
automatically selected main/off/no-sword roll or Necrotic/Force type gets
clearly labeled conditional alternatives in ExtraDescription, without a false fixed type.
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



def _auto_tooltip(key: str, spec: Mapping[str, object], bonus: str = '') -> dict[str, str]:
    """Show conditional AUTO bases without unsupported native IF expressions."""
    blood = str(spec.get('branch', key.split('_', 1)[0])) == 'xueyan'
    label = {
        'taixuan_liuguang': '四剑，每剑',
        'taixuan_jiuxiao': '每名敌人',
        'taixuan_taiqing': '每次落剑',
        'taixuan_yixiantian': '首名可受伤敌人',
        'tianqing_tianbeng': '主目标',
        'tianqing_tiandi': '三剑，每剑',
        'xueyan_liancheng': '四剑，每剑',
        'xueyan_wusheng': '六剑，每剑',
        'xueyan_xuehai': '每次落剑',
        'xingge_chengfeng': '每名敌人',
        'xingge_zhangjian': '每次御剑呼应',
        'internal_counter2': '每次反击',
        'internal_counter3': '每次反击',
        'internal_resonance': '每次御剑呼应',
    }.get(key, '本次剑击')
    if spec.get('continuation'):
        label = '本次续剑'
    main = _damage('MainMeleeWeapon', 'MainMeleeWeaponDamageType')
    off = _damage('OffhandMeleeWeapon', 'OffhandMeleeWeaponDamageType')
    qi = _QI_BASE if blood else _damage(_QI_BASE)
    extra_damage = bonus if blood else _damage(bonus) if bonus else ''
    params = [main, off, qi]
    text = (f'{label}的基础伤害自动择一：主手剑 [1]；'
            '主手无剑时副手剑 [2]；两手无剑时气剑 [3]。')
    if bonus:
        params.append(extra_damage)
        text += '另附 [4] 剑气伤害。'
    if blood:
        text += '气剑与额外剑气可选坏死或力场，佩剑类型不变。'
    if key == 'tianqing_tianbeng':
        params.append(_damage('18d8'))
        text += f'其他敌人使用相同基础，另附 [{len(params)}]。'
    elif key == 'taixuan_xinghe':
        params.append(_damage('6d8'))
        text += f'每次反击使用相同基础，另附 [{len(params)}]。'
    elif key == 'tianqing_tianjian':
        params.append(_damage('6d8'))
        text += f'余威每次仅造成 [{len(params)}]，不另加基础剑击。'
    return _result(extra=text, params=';'.join(params))

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

    if base == 'AUTO' or key == 'taixuan_qinghui':
        bonus = (
            f'LevelMapValue({_NORMAL_MAPS[key]})' if key in _NORMAL_MAPS
            else '32d8' if key == 'tianqing_tianbeng'
            else '4d8' if key in ('taixuan_qinghui', 'internal_counter2')
            else '6d8' if key == 'internal_counter3'
            else '2d6' if key == 'internal_resonance'
            else str(spec.get('dice', ''))
        )
        if spec.get('bonusOnly') and hand in ('off', 'offhand'):
            if branch == 'xueyan':
                return _result(
                    weapon_damage,
                    '本次副手御剑另附 [1] 剑气伤害（坏死或力场）。',
                    bonus,
                )
            native = weapon_damage + (';' + _damage(bonus) if bonus else '')
            return _result(native, '所示为本次副手御剑基础伤害。')
        return _auto_tooltip(key, spec, bonus)

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
