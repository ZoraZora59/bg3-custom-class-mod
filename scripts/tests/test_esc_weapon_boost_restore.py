"""Regress the native H2 save with tracked Wisdom but no item boost."""
import unittest
import test_esc_bridge as bridge


class WeaponBoostRestore(bridge.Bridge):
    def test_saved_tracking_without_native_boost_reinstates_override(self):
        owner=self.actor(branch='taixuan')
        self.ESC.Refresh('sword')
        self.F.runNextTick()
        sword=self.F.entities['sword:sword']
        sword.BoostsContainer=self.table(dict(Boosts=[]));sword._boosts=self.table({})
        self.assertTrue(self.ESC.State('sword').weaponWisdom['sword:sword'])
        self.ESC.Refresh('sword')
        self.assertTrue(self.E.hasWeaponWisdom('sword:sword','ESC_WEAPON_WISDOM_sword'))
        self.assertEqual(sword._boosts['ESC_WEAPON_WISDOM_sword'],'WeaponAttackRollAbilityOverride(Wisdom)')

    def test_missing_effect_is_added_without_a_deferred_native_removal(self):
        self.actor(branch='taixuan');self.ESC.Refresh('sword');self.F.runNextTick()
        self.F.entities['sword:sword'].BoostsContainer=self.table(dict(Boosts=[]))
        self.F.clearCalls();self.ESC.Refresh('sword')
        weapon_calls=[call.name for call in self.F.calls.values()
            if call.name in ('AddBoosts','RemoveBoosts') and call.args[2]=='WeaponAttackRollAbilityOverride(Wisdom)']
        self.assertEqual(weapon_calls,['AddBoosts'])

    def test_pending_add_is_shared_by_prefixed_and_uuid_owner_events(self):
        owner=self.actor(branch='taixuan')
        self.F.entities['Player_sword']=owner
        self.lua.execute('Fixture.nativeAddBoosts=Osi.AddBoosts;Osi.AddBoosts=function(id,boost,slot,source) if boost=="WeaponAttackRollAbilityOverride(Wisdom)" then Fixture.queuedWisdomAdds=(Fixture.queuedWisdomAdds or 0)+1 else Fixture.nativeAddBoosts(id,boost,slot,source) end end')
        self.ESC.Refresh('Player_sword');self.ESC.Refresh('sword');self.ESC.Refresh('Player_sword')
        self.assertEqual(self.F.queuedWisdomAdds,1)

    def test_legacy_prefixed_own_cause_is_recognized_and_removed(self):
        owner=self.actor(branch='taixuan');self.F.entities['Player_sword']=owner
        self.lua.globals().Osi.AddBoosts('sword:sword','WeaponAttackRollAbilityOverride(Wisdom)','ESC_WEAPON_WISDOM_Player_sword','Player_sword')
        self.F.clearCalls();self.ESC.Refresh('sword')
        self.assertFalse(any(call.name=='AddBoosts' and call.args[2]=='WeaponAttackRollAbilityOverride(Wisdom)' for call in self.F.calls.values()))
        self.assertTrue(self.E.hasWeaponWisdom('sword:sword','ESC_WEAPON_WISDOM_sword'))
        owner._equipped.Shield='shield';self.ESC.Refresh('sword')
        self.assertFalse(self.E.hasWeaponWisdom('sword:sword','ESC_WEAPON_WISDOM_sword'))

    def test_repeated_refresh_does_not_stack_native_boost(self):
        self.actor(branch='taixuan');self.ESC.Refresh('sword')
        self.F.clearCalls()
        for _ in range(3):self.ESC.Refresh('sword')
        self.assertEqual(self.F.callCount('AddBoosts'),0)

    def test_removed_effect_is_repaired_without_touching_external_pact(self):
        owner=self.actor(branch='taixuan');owner._abilities.Charisma=14
        sword=self.F.entities['sword:sword']
        self.F.entities['pact']=self.table(dict(BoostInfo=dict(Cause=dict(Cause='PACT_WEAPON')),
            WeaponAttackRollAbilityOverrideBoost=dict(Ability='Charisma')))
        sword.BoostsContainer=self.table(dict(Boosts=[dict(Type='WeaponAttackRollAbilityOverride',Boosts=['pact'])]))
        self.ESC.State('sword').weaponWisdom=self.table({'sword:sword':True})
        self.ESC.Refresh('sword')
        handles=list(sword.BoostsContainer.Boosts[1].Boosts.values())
        self.assertIn('pact',handles)
        self.assertEqual(len(handles),2)

    def test_missing_effect_is_not_reinstated_with_shield(self):
        owner=self.actor(branch='taixuan');self.ESC.Refresh('sword')
        sword=self.F.entities['sword:sword']
        sword.BoostsContainer=self.table(dict(Boosts=[]));sword._boosts=self.table({})
        owner._equipped.Shield='shield';self.ESC.Refresh('sword')
        self.assertFalse(self.E.hasWeaponWisdom('sword:sword','ESC_WEAPON_WISDOM_sword'))

    def test_untracked_native_override_is_removed_when_shield_blocks_class(self):
        owner=self.actor(branch='taixuan');self.ESC.Refresh('sword')
        self.ESC.State('sword').weaponWisdom=self.table({})
        owner._equipped.Shield='shield';self.ESC.Refresh('sword')
        self.assertFalse(self.E.hasWeaponWisdom('sword:sword','ESC_WEAPON_WISDOM_sword'))


# Keep only these regression methods; the base module is collected separately.
for _name in dir(bridge.Bridge):
    if _name.startswith('test_') and _name not in WeaponBoostRestore.__dict__:
        setattr(WeaponBoostRestore,_name,None)

if __name__=='__main__':unittest.main()
