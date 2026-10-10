"""Shield guards under the native failed query's truthy NULL GUID result.

Uses actual production SPEC/SNAPSHOT via bridge; no build artifacts at test runtime.
These are simulated callbacks, not proof of native API or damage compatibility.
"""
import unittest
import test_esc_bridge as bridge

class ShieldEquipmentGuard(unittest.TestCase):
    table=bridge.Bridge.table
    actor=bridge.Bridge.actor

    def setUp(self):
        bridge.Bridge.setUp(self)
        self.owner=self.actor(branch='taixuan')
        self.actor('enemy',0,None,10000,10000,'enemies',2)
        self.F.entities['off']=self.table(dict(_isItem=True,_owner='sword',_boosts={},_proficiencies=dict(Shortswords=True)))
        self.F.entities['dagger']=self.table(dict(_isItem=True,_owner='sword',_boosts={},_proficiencies=dict(Daggers=True)))
        self.F.entities['shield']=self.table(dict(_isItem=True,_boosts={},_proficiencies=dict(Shields=True),Armor=dict(Shield=True)))
        # Reproduce H native guard proof: failed query returns a truthy NULL GUID.
        # Explicit Shield slot remains independently absent/present.
        self.lua.execute("function Osi.GetEquippedShield(id) return Fixture.entities[id]._equipped.Shield or 'NULL_00000000-0000-0000-0000-000000000000' end")
        self.owner._equipped['Melee Offhand Weapon']='off'
        self.ESC.Refresh('sword')

    def pool(self,amount=3,active=True):
        row=self.E.resourceEntry('sword',bridge.SPEC['opportunityResource'])
        row.Amount=amount;row.MaxAmount=3
        for status in ['ESC_EXTRA_ATTACK',*bridge.SPEC['opportunityStatuses']]:
            if active:self.E.status('sword',status,-1,'sword')
            else:self.E.removeStatus('sword',status,'sword')
        return row

    def test_dual_short_swords_ignore_truthy_null_guid_from_shield_query(self):
        self.assertEqual(self.lua.globals().Osi.GetEquippedShield('sword'),'NULL_00000000-0000-0000-0000-000000000000')
        self.assertIsNone(self.E.shield('sword'))
        self.assertTrue(self.E.allowed('sword','taixuan',False))
        self.assertFalse(self.E.hasStatus('sword','ESC_ARMOR_BLOCKED'))

    def test_all_four_branches_accept_only_offhand_sword_and_swordless(self):
        for branch in ['taixuan','tianqing','xueyan','xingge']:
            for main,off in [('dagger','off'),(None,'off'),(None,None),('sword:sword',None)]:
                with self.subTest(branch=branch,main=main,off=off):
                    self.owner._equipped['Melee Main Weapon']=main
                    self.owner._equipped['Melee Offhand Weapon']=off
                    self.assertTrue(self.E.allowed('sword',branch,True))

    def test_real_shield_proficiency_blocks_and_clears_pool(self):
        pool=self.pool();self.owner._equipped.Shield='shield'
        self.F.emit('Equipped','shield','sword')
        self.assertEqual(self.E.shield('sword'),'shield')
        self.assertFalse(self.E.allowed('sword','taixuan',False))
        self.assertEqual(pool.Amount,0)
        self.assertFalse(self.E.hasStatus('sword','ESC_EXTRA_ATTACK'))
        self.assertFalse(self.E.hasStatus('sword','ESC_ARMOR_BLOCKED'))

    def test_shield_entity_flag_blocks_without_proficiency_or_name_hint(self):
        item='66000000-0000-4000-8000-000000000001'
        self.F.entities[item]=self.table(dict(_isItem=True,_boosts={},Armor=dict(Shield=True)))
        self.owner._equipped.Shield=item
        self.assertEqual(self.E.shield('sword'),item)
        self.assertFalse(self.E.allowed('sword','tianqing',True))

    def test_nonshield_or_null_item_in_shield_query_cannot_block(self):
        for item in ['off','00000000-0000-0000-0000-000000000000']:
            with self.subTest(item=item):
                self.owner._equipped.Shield=item
                self.assertIsNone(self.E.shield('sword'))
                self.assertTrue(self.E.allowed('sword','taixuan',False))

    def test_branch_armor_policy_and_armor_icon_remain_exact(self):
        for group in ['MediumArmor','HeavyArmor']:
            self.F.entities['armor']=self.table(dict(_isItem=True,_proficiencies={group:True}))
            self.owner._equipped.Breast='armor'
            for branch,allowed in [('taixuan',False),('xingge',False),('tianqing',True),('xueyan',True)]:
                with self.subTest(group=group,branch=branch):
                    actor=self.actor(branch,12,branch)
                    actor._equipped['Melee Offhand Weapon']='off';actor._equipped.Breast='armor'
                    self.ESC.Refresh(branch)
                    self.assertEqual(bool(self.E.allowed(branch,branch,False)),allowed)
                    self.assertEqual(bool(self.E.hasStatus(branch,'ESC_ARMOR_BLOCKED')),not allowed)

    def test_valid_equipment_events_keep_existing_pool_and_twenty_permissions(self):
        pool=self.pool()
        for slot,item,event in [('Melee Main Weapon','dagger','Equipped'),('Melee Main Weapon',None,'Unequipped'),
                                ('Melee Offhand Weapon',None,'Unequipped'),('Melee Offhand Weapon','off','Equipped'),
                                ('Melee Main Weapon','sword:sword','Equipped')]:
            with self.subTest(slot=slot,item=item):
                self.owner._equipped[slot]=item;self.F.emit(event,item or 'dagger','sword')
                self.assertEqual((pool.Amount,pool.MaxAmount),(3,3))
                self.assertTrue(self.E.hasStatus('sword','ESC_EXTRA_ATTACK'))
                self.assertTrue(all(self.E.hasStatus('sword',sid) for sid in bridge.SPEC['opportunityStatuses']))

    def test_production_bonus_using_callback_keeps_parent_group_and_balance(self):
        pool=self.pool()
        spell='Projectile_ESC_taixuan_zhaoxi_RangedOff_Bonus'
        self.F.emit('UsingSpellOnTarget','sword','enemy',spell,'Projectile','',901)
        self.F.emit('CastedSpell','sword',spell,'Projectile','',901)
        self.assertEqual(pool.Amount,3)
        self.assertTrue(self.E.hasStatus('sword','ESC_EXTRA_ATTACK'))
        self.assertTrue(all(self.E.hasStatus('sword',sid) for sid in bridge.SPEC['opportunityStatuses']))

    def test_valid_refresh_cannot_refill_exhausted_balance(self):
        pool=self.pool(0)
        self.F.emit('Equipped','off','sword')
        self.F.emit('UsingSpellOnTarget','sword','enemy','Projectile_ESC_taixuan_zhaoxi_RangedOff_Bonus','Projectile','',902)
        self.assertEqual(pool.Amount,0)

    def test_existing_weapon_wisdom_and_two_swords_refresh_restore_native_boosts(self):
        self.assertEqual(self.owner._boosts['ESC_two_swords'],'TwoWeaponFighting()')
        sword=self.F.entities['sword:sword'];off=self.F.entities['off']
        self.assertTrue(any('WeaponAttackRollAbilityOverride(Wisdom)' in v for v in sword._boosts.values()))
        self.assertTrue(any('WeaponAttackRollAbilityOverride(Wisdom)' in v for v in off._boosts.values()))

    def test_real_shield_removes_weapon_wisdom_and_two_swords(self):
        self.owner._equipped.Shield='shield';self.F.emit('Equipped','shield','sword')
        self.assertFalse(self.owner._boosts['ESC_two_swords'])
        for item in ['sword:sword','off']:
            self.assertFalse(any('WeaponAttackRollAbilityOverride(Wisdom)' in v for v in self.F.entities[item]._boosts.values()))

    def test_offhand_sword_keeps_ability_damage_without_a_main_hand_sword(self):
        for main in ['dagger',None]:
            with self.subTest(main=main):
                self.owner._equipped['Melee Main Weapon']=main
                self.F.emit('Equipped','off','sword')
                self.assertEqual(self.owner._boosts['ESC_two_swords'],'TwoWeaponFighting()')
                self.assertEqual(self.E.preferredSword('sword'),('off','off'))
        self.owner._equipped['Melee Offhand Weapon']=None
        self.F.emit('Unequipped','off','sword')
        self.assertFalse(self.owner._boosts['ESC_two_swords'])

    def test_turn_start_and_left_combat_still_clear_opportunities(self):
        for event in ['TurnStarted','LeftCombat']:
            with self.subTest(event=event):
                pool=self.pool();self.F.emit(event,'sword')
                self.assertEqual(pool.Amount,0)

    def test_old_save_migration_still_clears_old_pool_once(self):
        pool=self.pool();self.ESC.State('sword').nativeContinuous=None
        self.ESC.Refresh('sword');self.assertEqual(pool.Amount,0)
        self.assertFalse(self.E.hasStatus('sword','ESC_EXTRA_ATTACK'))

    def test_below_level5_and_death_still_clear_pool(self):
        for level,dead in [(4,False),(12,True)]:
            with self.subTest(level=level,dead=dead):
                pool=self.pool();self.owner.Classes.Classes[1].Level=level;self.owner._dead=dead
                self.ESC.Refresh('sword');self.assertEqual(pool.Amount,0)
