"""Explicit presentation fields for the sword-cultivator's native spells.

The spell generator owns rolls, damage, costs, targets, and containers.  This
module prevents its vanilla animation parents from also supplying unrelated
tooltips, healing/thunder effects, AI substitutions, or dual-wield costs.

Native animation profiles below retain complete rig mappings and paired cast
events.  Original VFX bindings are explicit and phase-limited in
sword_vfx_bindings; unfinished phases retain the existing native placeholders.

Official references consulted before copying the native fields:
https://docs.baldursgate3.game/Making_a_Basic_Spell
https://docs.baldursgate3.game/Making_a_Projectile_Spell
https://docs.baldursgate3.game/VFX_%E2%80%93_Part_3%3A_Assigning_and_Testing_Effects
SpellAnimation and its CastTextEvent must remain a matching, complete pair.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from sword_vfx_bindings import SpellPresentation, classify_spell, spell_vfx_bindings


# Exact fields copied from the locally extracted vanilla Stats.  No profile
# copies damage, costs, flags, target conditions, requirements, or trajectories.
# Paths are relative to build/sword-reference/Public/; resource IDs are native.
# Shared/Stats/Generated/Data/Spell_Projectile.txt: Projectile_MagicMissile.
MAGIC_MISSILE = {
    'SpellAnimation': (
        '3ff87abf-1ea1-4c32-aadf-c822d74c7dc0,,;,,;'
        '38cdb41c-2eec-4e03-bb31-83cff0346c35,,;'
        '85414f5f-b448-4dda-9370-1b6c4b38b561,,;'
        'd8925ce4-d6d9-400c-92f5-ad772ef7f178,,;,,;'
        'eadedcce-d01b-4fbb-a1ae-d218f13aa5d6,,;,,;,,'
    ),
    'CastTextEvent': 'Cast',
    'PrepareEffect': 'f9785481-e126-4499-b00e-f36fa02cd196',
    'CastEffect': '655f8b6b-f392-4c5d-8d74-d2a9df5f8f9d',
    'PrepareSound': 'Spell_Prepare_Damage_Force_Gen_L1to3',
    'PrepareLoopSound': 'Spell_Prepare_Damage_Force_Gen_L1to3_Loop',
    'CastSound': 'Spell_Cast_Damage_Force_MagicMissile_L1to3',
}

# SharedDev/Stats/Generated/Data/Spell_Target.txt:
# Target_BladeFlourish_Defensive.  Its BardicInspiration HitCosts and defensive
# status are intentionally not copied; this is only the single-sword movement.
MELEE_SWORD = {
    'SpellAnimation': (
        'a09de2c8-ec46-4c27-a502-bc92cf293fe5,,;'
        '9583ecee-cf6c-4735-86db-7ebf1df15eae,'
        '366693ee-d97f-4294-a4dd-a2145ddc4e6a,'
        '9f2d32b9-529a-4b75-b3df-6e1ae1395280;'
        'de006e3f-70fb-4eb7-a98d-d845d15b20e8,'
        '479ee5da-2967-41e1-b7d1-a94e864a5f25,'
        '79323098-edb3-4993-ba50-9b5f705e9878;'
        '50696db7-d931-4734-915d-32d038ba99a5,'
        'b5cb923d-0c08-4c20-89a9-44b9bf98c6cb,'
        '6282d127-0c06-4365-9d53-6f32ef350127;'
        '244b53cb-dc0f-4932-afd0-ab19c6df1b34,,;'
        'c36ed247-2272-492b-99c2-2ca10b014670,'
        'ecbf9949-3b33-432c-b735-e47aaed0924a,'
        'e71a7c08-fdc1-4a0b-9a90-1c793c58553c;'
        '0b07883a-08b8-43b6-ac18-84dc9e84ff50,,;,,;,,'
    ),
    # The inherited MainHandAttack has Cast; the native flourish explicitly
    # clears AlternativeCastTextEvents and DualWieldingUseCosts.
    'CastTextEvent': 'Cast',
    'PrepareEffect': '9b55a45f-1859-4f55-8fd4-44a27d3fcba1',
    'CastEffect': 'f573afc5-f018-4a87-a3a9-d1c0fe4e5b0d',
    'PrepareSound': 'Action_Prepare_Bard_Flourish',
    'PrepareLoopSound': 'Action_Loop_Bard_Flourish',
    'CastSound': 'Action_Cast_Bard_DefensiveFlourishMelee',
    'Sheathing': 'Melee',
}

# Shared/Stats/Generated/Data/Spell_Target.txt: Target_OffhandAttack.
# This is a SINGLE offhand attack event, not the main-hand dual-wield sequence.
OFFHAND_SWORD = {
    'SpellAnimation': (
        '8b8bb757-21ce-4e02-a2f3-97d55cf2f90b,,;'
        'c1df9aea-8be9-4de3-bcbc-4e4c1e44dc37,,;'
        '722df2d7-7898-4b0b-b930-5a850b55ccf0,,;'
        'a693a7c3-e7e7-4edb-98dd-db5fd700663f,,;'
        '7bb52cd4-0b1c-4926-9165-fa92b75876a3,,;'
        '35f5cba8-3706-46d5-9a1e-2def9ba22473,,;'
        '0b07883a-08b8-43b6-ac18-84dc9e84ff50,,;,,;,,'
    ),
    'CastTextEvent': 'CastOffhand',
    'CastEffect': '6b1751f5-a275-44de-bfde-352fc949162e',
    'Sheathing': 'Melee',
}

# Shared/Stats/Generated/Data/Spell_Zone.txt: Zone_Cleave.
# Its MaximumTargets=3, weapon restrictions, and short-rest cooldown are NOT
# copied: the generator's own sword skills retain their existing rules.
SWORD_SWEEP = {
    'SpellAnimation': (
        '79e47203-3855-4837-8673-ddb708d86962,,;'
        '711781fb-5f5a-4b9a-bd8b-e0b4ff9dec46,,;'
        'a17a7bf3-7381-4191-83f4-304d37c738e0,,;'
        '1172e0b6-08d1-4f28-a651-a01681b84ee6,,;'
        '863fabe7-d990-42a3-8961-7898c207bcb1,,;'
        '0002afee-5ad9-4109-ae64-9b2571601226,,;'
        '0b07883a-08b8-43b6-ac18-84dc9e84ff50,,;,,;,,'
    ),
    'CastTextEvent': 'Cast',
    'PrepareEffect': '9342eaf4-6a20-44c6-a740-863b0f9c2475',
    'CastEffect': '1d808499-eac9-408a-b5c8-219bb4f52bdc',
    'TargetEffect': '0444f9b9-f4a9-4c0e-8671-3bfc3e883447',
    'CastSound': 'Action_Cast_Sweep',
    'TargetSound': 'Action_Impact_SweepingAttack',
    'Sheathing': 'Melee',
}

# Shared/Stats/Generated/Data/Spell_Rush.txt: Rush_Rush.  Its complete native
# movement animation uses Cast; a Magic Missile casting gesture is not a Rush
# animation.  Damage, movement speed, requirements, weapon restrictions, costs,
# flags, and cooldown remain exclusively owned by the spell generator.
RUSH_SWORD = {
    'SpellAnimation': (
        'eae21eb0-bde7-4c86-a197-12a2a0c3ecac,,;'
        '7bfeb9dd-1348-45c7-bff9-ed42f8cd43a1,,;'
        'b780092c-cc12-43d5-b60e-acbac3fdceed,,;'
        'abbeb7de-2128-4b16-95e5-7b9d7b1af2f9,,;'
        'e6a25c4b-816c-41e1-888a-50215d994b23,,;,,;'
        '0b07883a-08b8-43b6-ac18-84dc9e84ff50,,;,,;,,'
    ),
    'CastTextEvent': 'Cast',
    'PrepareEffect': '82154992-95d0-4323-8e2e-35f06976736e',
    'CastEffect': '6137834a-4e00-466d-beef-3e9a515c8d60',
    'HitEffect': '9a19e7d0-92e8-4a40-909c-10b657135051',
    'PreviewEffect': '1615a7f7-21d9-4dd0-849b-d3c79a57c5ff',
    'CastSound': 'Action_Cast_Rush',
    'Sheathing': 'DontChange',
}

# Shared/Stats/Generated/Data/Spell_Shout.txt: Shout_ActionSurge.
# Only its non-healing gesture/effects/sounds; never the Combat requirement,
# ACTION_SURGE status, cooldown, AIFlags, or any resources.
SELF_UTILITY = {
    'SpellAnimation': (
        '5e57443f-284e-47b2-915e-5b6417db269c,,;'
        '925779e7-8bf6-4d56-8c4d-42c3bc01c60c,,;'
        '50398f4e-dd82-4d6a-ad43-aedd578543d9,,;'
        '1c343e00-7e6c-4f53-b588-074a3cdb9c7d,,;'
        '5bcdefbb-2194-46c2-ac77-0b2d8472a5f7,,;,,;'
        '5fdb66be-7506-411a-a7ea-c4783288aac8,,;,,;,,'
    ),
    'CastTextEvent': 'Cast',
    'PrepareEffect': '49dd385f-fd25-4372-8628-30b775af7c79',
    'CastEffect': '2550e2bb-c9f9-4440-9cd4-146a03f2e9bc',
    'CastSound': 'Action_Cast_Surge',
    'TargetSound': 'Action_Impact_Surge',
    'Sheathing': 'DontChange',
}

# Shared/Stats/Generated/Data/Spell_Target.txt: Target_TrueStrike.  This target
# gesture replaces HealingWord's gesture for non-healing utility spells.  Its
# hostile mark, debuff SFX, concentration and TRUE_STRIKE status are NOT copied.
TARGET_UTILITY = {
    'SpellAnimation': (
        '9313094a-bae2-454f-9701-f920d0e8e98d,,;,,;'
        '3e441d3f-11f9-432d-877c-c0ba4d92c74a,,;'
        '8b7ae969-2a04-4720-9685-3bde54c18ffe,,;'
        '808fdfab-2e6c-472e-b3c4-19ce4a719d9d,,;,,;'
        'ea745d30-eb87-447f-b190-c81298e27d9c,,;,,;,,'
    ),
    'CastTextEvent': 'Cast',
}

# A callback marker has no native RegainHitPoints functor, so the actual
# healing skills must be recognized by their stable design keys.
HEAL_KEYS = (
    'taixuan_guiyuan', 'tianqing_nixi', 'xueyan_huichao', 'xingge_xiangfu',
)

# Field names must also exist in the installed Toolkit's Shared/SharedDev
# Editor/Mods/*/Stats/SpellData/*.stats union.  The broader runtime Modifiers.txt
# includes unsupported editor fields such as ShortDescription and
# AiCalculationSpellOverride; do not emit them here.  SpellAnimationIntentType
# likewise has a different Toolkit table name and is deliberately not copied.
TOOLTIP_DEFAULTS = {
    'Description': '',
    'DescriptionParams': '',
    'ExtraDescription': '',
    'ExtraDescriptionParams': '',
    'ShortDescriptionParams': '',
    'TooltipDamageList': '',
    'TooltipStatusApply': '',
    'TooltipOnMiss': '',
    'TooltipOnSave': '',
    'TooltipPermanentWarnings': '',
    'TooltipUpcastDescription': '',
    'TooltipUpcastDescriptionParams': '',
    'CombatAIOverrideSpell': '',
    'DualWieldingUseCosts': '',
    'DualWieldingSpellAnimation': '',
    'AlternativeCastTextEvents': '',
    'SpellContainerID': '',
    'ContainerSpells': '',
}

# MEI and optional SFX fields verified in Shared/.../Structure/Modifiers.txt.
# Explicit empty values block an unrelated animation parent's inherited effect.
EFFECT_FIELDS = (
    'PrepareEffect', 'CastEffect', 'TargetEffect', 'TargetHitEffect',
    'TargetGroundEffect', 'PositionEffect', 'HitEffect', 'ImpactEffect',
    'PreviewEffect', 'BeamEffect', 'SpellEffect',
)
SOUND_FIELDS = (
    'PrepareSound', 'PrepareLoopSound', 'CastSound', 'TargetSound',
    'VocalComponentSound',
)

# These enum values are verified in Shared/.../Structure/Base/ValueLists.txt.
DAMAGE_TYPES = (
    'Slashing', 'Piercing', 'Bludgeoning', 'Acid', 'Thunder', 'Necrotic',
    'Fire', 'Lightning', 'Cold', 'Psychic', 'Poison', 'Radiant', 'Force',
)


def _damage_type(execution: str) -> str:
    """Use a single known type only when the functors have one fixed type."""
    if 'DealDamage(' not in execution:
        return 'None'
    if re.search(r'\b(?:Main|Offhand)(?:Melee)?WeaponDamageType\b', execution):
        # Weapon + Force damage and mode-dependent Necrotic/Force damage do not
        # have one honest static type.  The actual damage functors are untouched.
        return 'None'
    types = set(re.findall(
        r',\s*(' + '|'.join(DAMAGE_TYPES) + r')\s*(?:,|\))', execution,
    ))
    return next(iter(types)) if len(types) == 1 else 'None'


def _tooltip_roll(roll: str) -> str:
    # Derive the MAIN roll only; secondary control saves belong in the skill's
    # description.  Never inherit Thunderwave's Constitution save for an attack.
    attack = re.search(r'Attack\(AttackType\.([A-Za-z]+)\)', roll)
    if attack:
        return attack.group(1)
    save = re.search(r'SavingThrow\(Ability\.([A-Za-z]+)\s*,', roll)
    return save.group(1) if save else ''


def _animation_profile(
    presentation: SpellPresentation, roll: str, damage: bool, spell_type: str,
) -> Mapping[str, str]:
    """Choose a native, complete action independently of the VFX phase assets."""
    if presentation.form == 'rush' or spell_type == 'Rush':
        return RUSH_SWORD
    if presentation.form == 'zone' and presentation.key == 'tianqing_nifeng':
        return SWORD_SWEEP
    if presentation.form == 'melee':
        return OFFHAND_SWORD if 'MeleeOffHandWeaponAttack' in roll else MELEE_SWORD
    if damage:
        # Physical sword command/slash animations still use the paired Cast
        # event to launch a Projectile.  Copy only presentation, never the
        # native flourish's attack rules or Bardic Inspiration costs.
        if presentation.style in ('common', 'tianqing', 'xingge') and not (
            presentation.internal and presentation.key == 'qi_guard'
        ):
            if presentation.family in ('area_swords', 'self_burst'):
                return SWORD_SWEEP
            return OFFHAND_SWORD if presentation.hand == 'off' else MELEE_SWORD
        return MAGIC_MISSILE
    return SELF_UTILITY if spell_type == 'Shout' else TARGET_UTILITY


def _apply_vfx(
    result: dict[str, object], values: Mapping[str, object],
    presentation: SpellPresentation,
) -> dict[str, object]:
    # Enabled bindings replace profile defaults.  Explicit generator fields
    # still win, including a future per-skill effect or movement trajectory.
    for field, value in spell_vfx_bindings(presentation, values).items():
        if field not in values:
            result[field] = value
    return result


def present_spell(
    name: str, values: Mapping[str, object], using: str | None = None,
) -> dict[str, object]:
    """Return explicit presentation without changing any spell gameplay fields.

    Explicit generator fields win over defaults, including container links and
    future per-skill effects.  Every named/variant/helper spell is classified.
    Movement spells keep native trajectories, animations, and sounds.  Enabled
    custom phases are applied independently; inactive phases remain native.
    """
    result = dict(values)
    for field, value in TOOLTIP_DEFAULTS.items():
        result.setdefault(field, value)

    roll = str(values.get('SpellRoll', ''))
    execution = ';'.join(str(values.get(field, '')) for field in (
        'SpellProperties', 'SpellSuccess', 'SpellFail',
    ))
    damage = 'DealDamage(' in execution
    if 'ESC_FORCE_MODE' in execution and 'Necrotic' in str(result['TooltipDamageList']):
        # A fixed Necrotic preview contradicts the player's Force selection.
        # The explicit damage supplement describes both selectable types.
        raise ValueError(f'Mode-dependent skill has a fixed Necrotic preview: {name}')
    healing = not damage and (
        'RegainHitPoints(' in execution
        or any(re.search(r'_ESC_' + key + r'(?:_|$)', name) for key in HEAL_KEYS)
    )
    movement = 'IsJump' in str(values.get('SpellFlags', '')).split(';')
    spell_type = str(values.get('SpellType', name.split('_', 1)[0]))
    parent = using or ''
    container = bool(result['ContainerSpells'])
    presentation = classify_spell(name, values)
    result['TooltipAttackSave'] = _tooltip_roll(roll)
    result['DamageType'] = _damage_type(execution)
    result['VerbalIntent'] = 'Damage' if damage else 'Healing' if healing else (
        'Utility' if movement or container else 'Buff'
    )
    result['HitAnimationType'] = (
        'PhysicalDamage' if damage and 'Melee' in roll
        else 'MagicalDamage_External' if damage
        else 'MagicalNonDamage' if healing
        else 'None'
    )

    if movement:
        # These are human Jump/Fly children, not attacks.  The animation and
        # trajectory are part of movement execution and must remain inherited.
        return _apply_vfx(result, values, presentation)

    if healing and not container and parent in ('Target_HealingWord', 'Shout_SecondWind'):
        # Only intentional healing may retain the healing parent's presentation.
        return _apply_vfx(result, values, presentation)

    profile = _animation_profile(presentation, roll, damage, spell_type)

    for field, value in profile.items():
        if not container or field not in EFFECT_FIELDS + SOUND_FIELDS:
            result.setdefault(field, value)
    for field in EFFECT_FIELDS + SOUND_FIELDS:
        result.setdefault(field, '')
    # Every selected native animation above uses its paired primary event.
    result.setdefault('CastTextEvent', 'Cast')
    return _apply_vfx(result, values, presentation)
