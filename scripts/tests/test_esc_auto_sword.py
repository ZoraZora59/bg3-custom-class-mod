"""Automatic sword foundation contracts using the actual generated production spec.

These deterministic Lua regressions cannot establish native attack-roll or VFX acceptance.
The explicit retired leaf list is a frozen save-migration contract, not a build-file input.
"""
import unittest
import test_esc_bridge as bridge

LEGACY_MENU_LEAVES = (
    'Projectile_ESC_yujian_Main',
    'Projectile_ESC_yujian_Off',
    'Target_ESC_sword_strike_Main',
    'Target_ESC_sword_strike_Off',
    'Target_ESC_taixuan_zhaoxi_MeleeMain',
    'Target_ESC_taixuan_zhaoxi_MeleeOff',
    'Target_ESC_taixuan_zhaoxi_MeleeOff_Bonus',
    'Projectile_ESC_taixuan_zhaoxi_RangedMain',
    'Projectile_ESC_taixuan_zhaoxi_RangedOff',
    'Zone_ESC_tianqing_nifeng_MeleeMain',
    'Zone_ESC_tianqing_nifeng_MeleeOff',
    'Zone_ESC_tianqing_nifeng_MeleeOff_Bonus',
    'Zone_ESC_tianqing_nifeng_RangedMain',
    'Zone_ESC_tianqing_nifeng_RangedOff',
    'Target_ESC_tianqing_wanjun_Main',
    'Target_ESC_tianqing_wanjun_Off',
    'Target_ESC_tianqing_lietian_Main',
    'Target_ESC_tianqing_lietian_Off',
    'Target_ESC_tianqing_tianbeng_Main',
    'Target_ESC_tianqing_tianbeng_Off',
    'Rush_ESC_tianqing_tianfeng_Main',
    'Rush_ESC_tianqing_tianfeng_Off',
    'Projectile_ESC_tianqing_tianjian_Main',
    'Projectile_ESC_tianqing_tianjian_Off',
    'Shout_ESC_tianqing_bafang_Main',
    'Shout_ESC_tianqing_bafang_Off',
    'Target_ESC_tianqing_tiandi_Main',
    'Target_ESC_tianqing_tiandi_Off',
    'Target_ESC_xueyan_luexue_MeleeMain',
    'Target_ESC_xueyan_luexue_MeleeOff',
    'Target_ESC_xueyan_luexue_MeleeOff_Bonus',
    'Projectile_ESC_xueyan_luexue_RangedMain',
    'Projectile_ESC_xueyan_luexue_RangedOff',
    'Rush_ESC_xueyan_chuanshen_Main',
    'Rush_ESC_xueyan_chuanshen_Off',
    'Target_ESC_xingge_wenlu_MeleeMain',
    'Target_ESC_xingge_wenlu_MeleeOff',
    'Target_ESC_xingge_wenlu_MeleeOff_Bonus',
    'Projectile_ESC_xingge_wenlu_RangedMain',
    'Projectile_ESC_xingge_wenlu_RangedOff',
    'Target_ESC_xingge_chengfeng_Main',
    'Target_ESC_xingge_chengfeng_Off',
    'Projectile_ESC_xingge_tongzhou_Main',
    'Projectile_ESC_xingge_tongzhou_Off',
    'Target_ESC_liancheng_ContinueMelee',
    'Target_ESC_wusheng_ContinueMelee',
)

PRESERVED_BONUS = (
    'Projectile_ESC_taixuan_zhaoxi_RangedOff_Bonus',
    'Zone_ESC_tianqing_nifeng_RangedOff_Bonus',
    'Projectile_ESC_xueyan_luexue_RangedOff_Bonus',
    'Projectile_ESC_xingge_wenlu_RangedOff_Bonus',
)

class AutomaticSwordRuntime(unittest.TestCase):
    table = bridge.Bridge.table
    actor = bridge.Bridge.actor
    cast = bridge.Bridge.cast
    native_damage = bridge.Bridge.native_damage

    def setUp(self):
        bridge.Bridge.setUp(self)
        self.owner = self.actor(branch='taixuan')
        self.enemy = self.actor('enemy', 0, None, 10000, 10000, 'enemies', 2)
        self.owner._abilities['Wisdom'] = 14
        self.owner._abilities['Strength'] = 18
        self.owner._abilities['Dexterity'] = 22
        self.F.entities['off'] = self.table(dict(_isItem=True, _owner='sword', _boosts={},
                                               _proficiencies=dict(Rapiers=True), Weapon=dict(WeaponProperties=4)))
        self.F.resource('sword').Amount = 50
        self.alias = 'Projectile_ESC_taixuan_liuguang'
        self.helper = 'Target_ESC_LiuguangStage'
        self.contexts, self.pending = self.lua.execute('''
            local function upvalue(fn,wanted)
                for i=1,100 do local name,value=debug.getupvalue(fn,i)
                    if not name then break end;if name==wanted then return value end end
                error('Missing '..wanted)
            end
            return upvalue(ESC.Runtime.BeginCast,'casts'),upvalue(upvalue(ESC.Runtime.BeginCast,'bindPendingHelper'),'pendingHelpers')
        ''')

    def automatic_boost(self):
        return ';'.join(v for k, v in self.owner._boosts.items() if str(k).startswith('ESC_auto_weapon_accuracy_'))

    def test_main_sword_preferred_over_stronger_offhand(self):
        self.owner._equipped['Melee Offhand Weapon'] = 'off'
        self.assertEqual(self.E.preferredSword('sword'), ('sword:sword', 'main'))
        self.assertEqual(self.E.techniqueAttribute('sword'), (4, 'main'))

    def test_only_offhand_sword_uses_finesse_attribute(self):
        self.owner._equipped['Melee Main Weapon'] = None
        self.owner._equipped['Melee Offhand Weapon'] = 'off'
        self.assertEqual(self.E.preferredSword('sword'), ('off', 'off'))
        self.assertEqual(self.E.techniqueAttribute('sword'), (6, 'off'))

    def test_empty_or_non_sword_equipment_uses_only_wisdom(self):
        self.F.entities['dagger'] = self.table(dict(_isItem=True, _proficiencies=dict(Daggers=True)))
        for equip in (None, 'dagger'):
            with self.subTest(equip=equip):
                self.owner._equipped['Melee Main Weapon'] = equip
                self.owner._equipped['Melee Offhand Weapon'] = equip
                self.assertEqual(self.E.preferredSword('sword'), (None, 'qi'))
                self.assertEqual(self.E.techniqueAttribute('sword'), (2, 'qi'))

    def test_all_class_branches_allow_swordless_attack_but_outsider_does_not(self):
        for branch in ('tianqing', 'taixuan', 'xueyan', 'xingge'):
            actor = self.actor(branch, 12, branch)
            actor._equipped['Melee Main Weapon'] = None
            self.assertTrue(self.E.allowed(branch, branch, True))
        ordinary = self.actor('ordinary', 0, None)
        ordinary._equipped['Melee Main Weapon'] = None
        self.assertFalse(self.E.allowed('ordinary', None, True))

    def test_fallback_preserves_shield_and_branch_armor_constraints(self):
        self.owner._equipped['Melee Main Weapon'] = None
        self.owner._equipped.Shield = 'shield'
        self.assertFalse(self.E.allowed('sword', 'taixuan', True))
        self.owner._equipped.Shield = None
        self.F.entities['armor'] = self.table(dict(_proficiencies=dict(MediumArmor=True)))
        self.owner._equipped['Breast'] = 'armor'
        self.assertFalse(self.E.allowed('sword', 'taixuan', True))
        self.assertFalse(self.E.allowed('sword', 'xingge', True))
        self.assertTrue(self.E.allowed('sword', 'tianqing', True))

    def test_old_saved_qi_mode_and_grant_clear_without_touching_other_spell(self):
        self.owner._spells = self.table({'Shout_ESC_qi_sword': True, 'Shout_ESC_qi_guard': True, 'Projectile_FireBolt': True})
        self.ESC.State('sword').qiSword = True
        self.E.status('sword', 'ESC_QI_MODE', -1, 'sword')
        self.ESC.Refresh('sword')
        self.assertFalse(self.ESC.State('sword').qiSword)
        self.assertFalse(self.E.hasStatus('sword', 'ESC_QI_MODE'))
        self.assertIsNone(self.owner._spells['Shout_ESC_qi_sword'])
        self.assertTrue(self.owner._spells['Projectile_FireBolt'])
        calls = [c for c in self.F.calls.values() if c.name == 'RemoveSpell' and c.args[2] == 'Shout_ESC_qi_sword']
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].args[3], 0)
        self.ESC.Refresh('sword')
        self.assertEqual(len([c for c in self.F.calls.values() if c.name == 'RemoveSpell' and c.args[2] == 'Shout_ESC_qi_sword']), 1)

    def test_session_reload_clears_stale_qi_and_rebuilds_equipment_accuracy(self):
        self.ESC.State('sword').qiSword = True
        self.E.status('sword', 'ESC_QI_MODE', -1, 'sword')
        self.owner._spells = self.table({'Shout_ESC_qi_sword': True})
        self.F.event('SessionLoaded', self.table({}))
        self.assertFalse(self.ESC.State('sword').qiSword)
        self.assertFalse(self.E.hasStatus('sword', 'ESC_QI_MODE'))
        self.assertIn('RollBonus(Attack,2)', self.automatic_boost())

    def test_old_saved_toggle_callback_cannot_restore_manual_mode(self):
        self.F.emit('UsingSpell', 'sword', 'Shout_ESC_qi_sword', 'Shout', '', 110)
        self.F.emit('CastedSpell', 'sword', 'Shout_ESC_qi_sword', 'Shout', '', 110)
        self.assertFalse(self.ESC.State('sword').qiSword)
        self.assertFalse(self.E.hasStatus('sword', 'ESC_QI_MODE'))

    def test_automatic_accuracy_exists_before_using_and_does_not_create_cast(self):
        self.ESC.Refresh('sword')
        boost = self.automatic_boost()
        self.assertIn("SpellId('Target_ESC_LiuguangStage')", boost)
        self.assertIn("SpellId('Target_ESC_TaiqingPulse')", boost)
        self.assertIn('RollBonus(Attack,2)', boost)
        self.assertIsNone(self.contexts[111])
        self.assertEqual(self.native_damage('sword', 'enemy', [12], self.helper, 111).TotalDamageDone, 13)
        self.assertIsNone(self.contexts[111])

    def test_begin_auto_does_not_double_add_accuracy_or_mutate_shared_alias(self):
        self.ESC.Refresh('sword')
        before = self.automatic_boost()
        cast = self.ESC.Runtime.BeginCast('sword', self.alias, 112, 'enemy')
        self.assertEqual(cast.alias.hand, 'main')
        self.assertEqual(self.lua.globals().GeneratedSpec.aliases[self.alias].hand, 'auto')
        self.assertEqual(self.automatic_boost(), before)
        self.assertIsNone(self.owner._boosts['ESC_cast_weapon_accuracy'])

    def test_switch_equipment_updates_accuracy_and_fallback_removes_it(self):
        self.ESC.Refresh('sword')
        self.assertIn('RollBonus(Attack,2)', self.automatic_boost())
        self.owner._equipped['Melee Main Weapon'] = None
        self.owner._equipped['Melee Offhand Weapon'] = 'off'
        self.F.emit('Unequipped', 'sword:sword', 'sword')
        self.assertIn('RollBonus(Attack,4)', self.automatic_boost())
        self.owner._equipped['Melee Offhand Weapon'] = None
        self.F.emit('Unequipped', 'off', 'sword')
        self.assertEqual(self.automatic_boost(), '')

    def test_shield_and_class_removal_clear_scoped_accuracy(self):
        self.ESC.Refresh('sword')
        self.assertTrue(self.automatic_boost())
        self.owner._equipped.Shield = 'shield'
        self.ESC.Refresh('sword')
        self.assertEqual(self.automatic_boost(), '')
        self.owner._equipped.Shield = None
        self.ESC.Refresh('sword')
        self.owner._spells = self.table({'Shout_ESC_qi_sword': True, 'Projectile_FireBolt': True})
        self.ESC.State('sword').qiSword = True
        self.E.status('sword', 'ESC_QI_MODE', -1, 'sword')
        self.owner.Classes.Classes = self.table([])
        self.ESC.Refresh('sword')
        self.assertEqual(self.automatic_boost(), '')
        self.assertFalse(self.ESC.State('sword').qiSword)
        self.assertFalse(self.E.hasStatus('sword', 'ESC_QI_MODE'))
        self.assertIsNone(self.owner._spells['Shout_ESC_qi_sword'])
        self.assertTrue(self.owner._spells['Projectile_FireBolt'])

    def test_external_spell_bow_and_dice_only_aftershock_are_outside_auto_accuracy(self):
        self.ESC.Refresh('sword')
        boost = self.automatic_boost()
        for name in ('Projectile_FireBolt', 'Projectile_MainHandAttack', 'Target_ESC_Aftershock', 'Target_ESC_HuifengControl'):
            self.assertNotIn("SpellId('" + name + "')", boost)
        self.assertEqual(self.native_damage('sword', 'enemy', [12], 'Projectile_FireBolt', 113).TotalDamageDone, 12)
        self.assertEqual(self.native_damage('sword', 'enemy', [12], 'Projectile_MainHandAttack', 114).TotalDamageDone, 12)

    def test_external_pact_weapon_attribute_is_respected_once(self):
        self.owner._abilities['Charisma'] = 24
        self.F.entities['pact'] = self.table(dict(BoostInfo=dict(Cause=dict(Cause='PACT_OF_THE_BLADE')),
            WeaponAttackRollAbilityOverrideBoost=dict(Ability='Charisma')))
        self.F.entities['sword:sword'].BoostsContainer = self.table(dict(Boosts=[dict(Type='WeaponAttackRollAbilityOverride', Boosts=['pact'])]))
        self.assertEqual(self.E.techniqueAttribute('sword'), (7, 'main'))
        self.ESC.Refresh('sword')
        self.assertIn('RollBonus(Attack,5)', self.automatic_boost())

    def test_automatic_boost_chunks_respect_native_bound_and_never_add_dc(self):
        self.ESC.Refresh('sword')
        boosts = [v for k, v in self.owner._boosts.items() if str(k).startswith('ESC_auto_weapon_accuracy_')]
        self.assertTrue(boosts)
        self.assertTrue(all(len(value.encode('utf-8')) <= 2048 for value in boosts))
        self.assertTrue(all('SpellSaveDC' not in value for value in boosts))
        self.assertTrue(all('SpellId(' in value for value in boosts))

    def test_explicit_bonus_offhand_retains_its_hand_and_own_accuracy_once(self):
        self.owner._equipped['Melee Offhand Weapon'] = 'off'
        bonus = next(name for name, alias in bridge.SPEC['aliases'].items()
                     if alias.get('bonusOnly') and alias['key'] == 'taixuan_zhaoxi')
        self.ESC.Refresh('sword')
        preferred = self.automatic_boost()
        fixed = ';'.join(v for k, v in self.owner._boosts.items() if str(k).startswith('ESC_auto_offhand_accuracy_'))
        self.assertNotIn("SpellId('" + bonus + "')", preferred)
        self.assertIn("SpellId('" + bonus + "')", fixed)
        self.assertIn('RollBonus(Attack,4)', fixed)
        cast = self.ESC.Runtime.BeginCast('sword', bonus, 117, 'enemy')
        self.assertEqual(cast.alias.hand, 'off')
        self.assertTrue(cast.alias.bonusOnly)
        self.assertTrue(cast.alias.offhand)
        self.assertIsNone(self.owner._boosts['ESC_cast_weapon_accuracy'])
        self.owner._equipped['Melee Offhand Weapon'] = None
        self.F.emit('Unequipped', 'off', 'sword')
        self.assertFalse(any(v for k, v in self.owner._boosts.items() if str(k).startswith('ESC_auto_offhand_accuracy_')))

    def test_three_liuguang_helpers_keep_parent_and_captured_hand_with_empty_cost(self):
        self.owner._equipped['Melee Main Weapon'] = None
        self.owner._equipped['Melee Offhand Weapon'] = 'off'
        root = self.ESC.Runtime.BeginCast('sword', self.alias, 115, 'enemy')
        self.assertEqual(root.alias.hand, 'off')
        self.owner._equipped['Melee Main Weapon'] = 'sword:sword'
        self.F.emit('CastedSpell', 'sword', self.alias, 'Projectile', '', 115)
        self.assertEqual(len(self.pending['sword']), 3)
        for entry in self.pending['sword'].values():
            self.assertEqual(entry.meta.hand, 'off')
            self.assertEqual(entry.meta.parentAction, 115)
        self.assertEqual(self.F.stats[self.helper].UseCosts, '')
        self.assertEqual(self.F.resource('sword').Amount, 50)

    def line_packet(self, spell, target, action, raw, kind='Force', reduced=1, identity=None):
        identities = {'Force': '11111111-1111-4111-8111-111111111111',
                      'Slashing': '22222222-2222-4222-8222-222222222222',
                      'Fire': '33333333-3333-4333-8333-333333333333'}
        identity = identities.get(kind) if identity is None else identity
        hit = self.table(dict(DamageList=[dict(Amount=reduced, DamageType=kind)], TotalDamageDone=reduced,
                              Damage=dict(TotalDamage=raw), SpellId=spell))
        event = self.table(dict(Caster='sword', Target=target, StoryActionId=action, Hit=hit,
                                Functor=dict(FunctorUuid=identity)))
        self.F.event('DealDamage', event)
        self.F.event('BeforeDealDamage', self.table(dict(Hit=hit)))
        self.F.event('DealtDamage', event)
        return hit.TotalDamageDone

    def line_setup(self, action=116):
        self.enemy.Transform.Transform.Translate[1] = 4
        immune = self.actor('immune', 0, None, 10000, 10000, 'enemies', 1)
        immune.Resistances = self.table(dict(Resistances={14: 4}))
        self.actor('near', 0, None, 10000, 10000, 'enemies', 2)
        spell = bridge.SPEC['spells']['taixuan_yixiantian']['stat']
        self.ESC.Runtime.BeginCast('sword', spell, action, None, self.table([30, 0, 0]))
        return spell

    def test_line_combined_functor_retains_geometric_falloff_and_immunity(self):
        spell = self.line_setup()
        self.assertEqual(self.line_packet(spell, 'enemy', 116, 101), 50)
        self.assertEqual(self.line_packet(spell, 'immune', 116, 101), 0)
        self.assertEqual(self.line_packet(spell, 'near', 116, 999), 101)

    def test_line_weapon_and_force_components_are_both_preserved_and_rounded_once(self):
        spell = self.line_setup()
        far = [self.line_packet(spell, 'enemy', 116, 11, 'Slashing'), self.line_packet(spell, 'enemy', 116, 90)]
        near = [self.line_packet(spell, 'near', 116, 999, 'Slashing'), self.line_packet(spell, 'near', 116, 999)]
        self.assertEqual(far, [5, 45])
        self.assertEqual(near, [11, 90])
        self.assertEqual(sum(far), 50)

    def test_line_same_type_weapon_rider_functors_do_not_reuse_first_component(self):
        spell = self.line_setup()
        ids = ['11111111-1111-4111-8111-111111111111', '22222222-2222-4222-8222-222222222222',
               '33333333-3333-4333-8333-333333333333']
        far = [self.line_packet(spell, 'enemy', 116, raw, identity=identity) for raw, identity in zip((11, 9, 81), ids)]
        near = [self.line_packet(spell, 'near', 116, 999, identity=identity) for identity in ids]
        self.assertEqual(far, [5, 5, 40])
        self.assertEqual(near, [11, 9, 81])

    def test_line_conditional_same_type_rider_and_reordered_packets_use_uuid_not_ordinal(self):
        spell = self.line_setup()
        primary = '11111111-1111-4111-8111-111111111111'
        technique = '22222222-2222-4222-8222-222222222222'
        rider = '33333333-3333-4333-8333-333333333333'
        # Far lacks the rider; near receives its packets in a different order.
        far = [self.line_packet(spell, 'enemy', 116, 11, identity=primary),
               self.line_packet(spell, 'enemy', 116, 90, identity=technique)]
        near = [self.line_packet(spell, 'near', 116, 7, identity=rider),
                self.line_packet(spell, 'near', 116, 999, identity=technique),
                self.line_packet(spell, 'near', 116, 999, identity=primary)]
        self.assertEqual(far, [5, 45])
        self.assertEqual(near, [7, 90, 11])
        self.assertEqual(len(list(self.contexts[116].lineDamageParts.keys())), 3)

    def test_auto_line_missing_or_zero_identity_cannot_guess_or_reuse_another_component(self):
        spell = self.line_setup()
        self.assertEqual(self.line_packet(spell, 'near', 116, 11), 11)
        self.assertEqual(self.line_packet(spell, 'near', 116, 90, identity=''), 0)
        self.assertEqual(self.line_packet(spell, 'near', 116, 7,
            identity='00000000-0000-0000-0000-000000000000'), 0)
        self.assertTrue(self.contexts[116].lineIdentityMissing)
        self.assertEqual(len(list(self.contexts[116].lineDamageParts.keys())), 1)

    def test_legacy_menu_removes_exact_old_leaves_without_removing_roots_bonus_or_helpers(self):
        preserved = [bridge.SPEC['spells']['taixuan_zhaoxi']['stat'], *PRESERVED_BONUS,
                     'Target_ESC_LiuguangStage', 'Projectile_FireBolt']
        self.owner._spells = self.table({name: True for name in list(LEGACY_MENU_LEAVES) + preserved})
        self.ESC.Refresh('sword')
        self.assertTrue(all(self.owner._spells[name] is None for name in LEGACY_MENU_LEAVES))
        self.assertTrue(all(self.owner._spells[name] for name in preserved))
        removals = [c for c in self.F.calls.values() if c.name == 'RemoveSpell' and c.args[2] in LEGACY_MENU_LEAVES]
        self.assertEqual(len(removals), 46)
        self.assertTrue(all(c.args[3] == 0 for c in removals))
        self.ESC.Refresh('sword')
        self.assertEqual(len([c for c in self.F.calls.values() if c.name == 'RemoveSpell' and c.args[2] in LEGACY_MENU_LEAVES]), 46)

    def test_retired_melee_starter_cleans_at_level1_but_keeps_canonical_ranged_intro(self):
        self.owner.Classes.Classes[1].Level = 1
        self.owner._spells = self.table({'Target_ESC_sword_strike': True, 'Projectile_ESC_yujian': True})
        self.owner._passives = self.table({'ESC_P_StarterMelee': True, 'ESC_P_StarterSword': True})
        self.ESC.Refresh('sword')
        self.assertIsNone(self.owner._spells['Target_ESC_sword_strike'])
        self.assertIsNone(self.owner._passives['ESC_P_StarterMelee'])
        self.assertTrue(self.owner._spells['Projectile_ESC_yujian'])
        self.assertTrue(self.owner._passives['ESC_P_StarterSword'])

    def test_old_lietian_root_repair_requires_correct_branch_and_original_unlock(self):
        self.assertEqual(bridge.SPEC['spells']['tianqing_lietian']['level'], 8)
        for level, branch, repaired in ((5, 'tianqing', False), (7, 'tianqing', False),
                                        (8, 'tianqing', True), (12, 'tianqing', True), (12, 'taixuan', False)):
            with self.subTest(level=level, branch=branch):
                actor = self.actor('legacy', level, branch)
                actor._spells = self.table({'Projectile_ESC_tianqing_lietian': True})
                self.ESC.Refresh('legacy')
                self.assertIsNone(actor._spells['Projectile_ESC_tianqing_lietian'])
                self.assertEqual(bool(actor._spells['Target_ESC_tianqing_lietian']), repaired)
                calls_before = len([c for c in self.F.calls.values() if c.name == 'AddSpell'])
                self.ESC.Refresh('legacy')
                self.assertEqual(len([c for c in self.F.calls.values() if c.name == 'AddSpell']), calls_before)

    def test_force_immune_line_target_takes_zero_including_physical_weapon_and_riders(self):
        spell = self.line_setup()
        for kind, raw in (('Slashing', 11), ('Fire', 9), ('Force', 81)):
            self.assertEqual(self.line_packet(spell, 'immune', 116, raw, kind), 0)
        self.assertEqual(self.line_packet(spell, 'near', 116, 101), 101)
        self.assertIsNone(self.contexts[116].lineOrder['immune'])

    def set_target_mark(self, target, kind):
        owner = 'sword'
        if kind == 'followup':
            owner = 'followup_ally'
            self.actor(owner, 12, 'xingge', 100, 100, 'players', 20)
        self.ESC.Refresh(owner)
        self.ESC.State(target).marks[kind + ':' + owner] = self.table(dict(expires=self.ESC.State(owner).turn + 3, used={}))

    def test_line_near_only_weakpoint_after_far_packet_keeps_target_bonus_local(self):
        spell = self.line_setup()
        self.set_target_mark('near', 'weakpoint')
        self.assertEqual(self.line_packet(spell, 'enemy', 116, 100), 50)
        self.assertEqual(self.line_packet(spell, 'near', 116, 999), 120)
        self.assertEqual(self.contexts[116].lineDamageParts['11111111-1111-4111-8111-111111111111'], 100)

    def test_line_far_only_weakpoint_before_near_packet_does_not_spread(self):
        spell = self.line_setup()
        self.set_target_mark('enemy', 'weakpoint')
        self.assertEqual(self.line_packet(spell, 'enemy', 116, 100), 60)
        self.assertEqual(self.line_packet(spell, 'near', 116, 999), 100)

    def test_line_near_only_followup_after_far_packet_keeps_target_bonus_local(self):
        spell = self.line_setup()
        self.set_target_mark('near', 'followup')
        self.assertEqual(self.line_packet(spell, 'enemy', 116, 100), 50)
        self.assertEqual(self.line_packet(spell, 'near', 116, 999), 115)

    def test_line_far_only_followup_before_near_packet_does_not_spread(self):
        spell = self.line_setup()
        self.set_target_mark('enemy', 'followup')
        self.assertEqual(self.line_packet(spell, 'enemy', 116, 100), 57)
        self.assertEqual(self.line_packet(spell, 'near', 116, 999), 100)

    def bonus_grants(self, actor_id):
        return [call for call in self.F.calls.values()
                if call.name == 'AddSpell' and call.args[1] == actor_id and call.args[2] in PRESERVED_BONUS]

    def test_saved_linked_root_repairs_only_own_level3_bonus_once_for_each_branch(self):
        for branch, key, bonus in (('taixuan', 'taixuan_zhaoxi', PRESERVED_BONUS[0]),
                                   ('tianqing', 'tianqing_nifeng', PRESERVED_BONUS[1]),
                                   ('xueyan', 'xueyan_luexue', PRESERVED_BONUS[2]),
                                   ('xingge', 'xingge_wenlu', PRESERVED_BONUS[3])):
            for level in (3, 12):
                with self.subTest(branch=branch, level=level):
                    actor_id = branch + str(level)
                    actor = self.actor(actor_id, level, branch)
                    root = bridge.SPEC['spells'][key]['stat']
                    actor._spells = self.table({root: True, 'Projectile_FireBolt': True})
                    self.F.event('SessionLoaded', self.table({}))
                    self.F.event('SessionLoaded', self.table({}))
                    calls = self.bonus_grants(actor_id)
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(calls[0].args[2], bonus)
                    self.assertEqual((calls[0].args[3], calls[0].args[4]), (0, 0))
                    self.assertTrue(actor._spells[bonus])
                    self.assertTrue(actor._spells[root])
                    self.assertTrue(actor._spells['Projectile_FireBolt'])
                    self.assertTrue(all(actor._spells[name] is None for name in PRESERVED_BONUS if name != bonus))

    def test_bonus_migration_never_grants_below_unlock_unknown_branch_or_outsider(self):
        for actor_id, level, branch in (('level1', 1, 'taixuan'), ('level2', 2, 'tianqing'),
                                         ('common', 12, None), ('outsider', 0, None)):
            with self.subTest(actor_id=actor_id):
                actor = self.actor(actor_id, level, branch)
                actor._spells = self.table({'Projectile_FireBolt': True})
                self.F.event('SessionLoaded', self.table({}))
                self.assertEqual(self.bonus_grants(actor_id), [])
                self.assertTrue(actor._spells['Projectile_FireBolt'])

    def test_existing_known_bonus_is_preserved_without_add_or_child_removal(self):
        bonus = PRESERVED_BONUS[0]
        self.owner._spells = self.table({bonus: True, 'Target_ESC_taixuan_zhaoxi_MeleeOff_Bonus': True})
        self.ESC.Refresh('sword')
        self.assertTrue(self.owner._spells[bonus])
        self.assertIsNone(self.owner._spells['Target_ESC_taixuan_zhaoxi_MeleeOff_Bonus'])
        self.assertEqual(self.bonus_grants('sword'), [])
        self.assertTrue(all(call.args[2] != bonus for call in self.F.calls.values() if call.name == 'RemoveSpell'))

    def test_bonus_known_grant_does_not_depend_on_current_dual_wield_equipment(self):
        self.owner._equipped['Melee Main Weapon'] = None
        self.owner._equipped['Melee Offhand Weapon'] = None
        self.F.event('SessionLoaded', self.table({}))
        self.assertTrue(self.owner._spells[PRESERVED_BONUS[0]])
        self.assertEqual(len(self.bonus_grants('sword')), 1)
        self.owner._equipped['Melee Main Weapon'] = 'sword:sword'
        self.owner._equipped['Melee Offhand Weapon'] = 'off'
        self.ESC.Refresh('sword')
        self.assertEqual(len(self.bonus_grants('sword')), 1)

    def test_level_and_respec_do_not_preempt_native_bonus_grant(self):
        for branch, bonus in zip(('taixuan', 'tianqing', 'xueyan', 'xingge'), PRESERVED_BONUS):
            for event in ('LeveledUp', 'RespecCompleted'):
                with self.subTest(branch=branch, event=event):
                    actor_id = branch + event
                    actor = self.actor(actor_id, 12, branch)
                    actor._spells = self.table({'Projectile_FireBolt': True})
                    self.F.emit(event, actor_id)
                    self.ESC.Refresh(actor_id)  # A status/equipment refresh can intervene.
                    self.assertEqual(self.bonus_grants(actor_id), [])
                    self.assertIsNone(actor._spells[bonus])
                    # Native progression arrives later, retaining its own source.
                    actor._spells[bonus] = True
                    self.ESC.Refresh(actor_id)
                    self.F.event('SessionLoaded', self.table({}))
                    self.assertTrue(actor._spells[bonus])
                    self.assertEqual(self.bonus_grants(actor_id), [])

    def test_old_save_bonus_repair_waits_for_deferred_session_boundary(self):
        self.owner._spells = self.table({'Projectile_ESC_taixuan_zhaoxi': True})
        self.F.deferNextTicks = True
        self.F.event('SessionLoaded', self.table({}))
        self.assertEqual(self.bonus_grants('sword'), [])
        self.F.runNextTick()
        self.assertTrue(self.owner._spells[PRESERVED_BONUS[0]])
        self.assertEqual(len(self.bonus_grants('sword')), 1)

    def test_previously_watched_character_losing_class_cannot_repair_bonus(self):
        self.ESC.Refresh('sword')
        self.owner._spells = self.table({'Projectile_FireBolt': True})
        self.owner.Classes.Classes = self.table([])
        before = len(self.bonus_grants('sword'))
        self.ESC.Refresh('sword')
        self.assertEqual(len(self.bonus_grants('sword')), before)
        self.assertTrue(all(self.owner._spells[name] is None for name in PRESERVED_BONUS))

    def test_session_reload_repairs_level12_old_root_without_duplicate_bonus(self):
        self.owner._spells = self.table({'Projectile_ESC_taixuan_zhaoxi': True})
        self.F.event('SessionLoaded', self.table({}))
        self.F.event('SessionLoaded', self.table({}))
        self.assertTrue(self.owner._spells[PRESERVED_BONUS[0]])
        self.assertEqual(len(self.bonus_grants('sword')), 1)



if __name__ == '__main__':
    unittest.main(verbosity=2)
