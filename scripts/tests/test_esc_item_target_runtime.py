"""Item damage through production Lua; simulated hooks, not client acceptance."""
import unittest

import test_esc_bridge as bridge


class ItemTargets(unittest.TestCase):
    table = bridge.Bridge.table
    actor = bridge.Bridge.actor
    cast = bridge.Bridge.cast
    native_damage = bridge.Bridge.native_damage

    def setUp(self):
        bridge.Bridge.setUp(self)
        self.lua.execute('''
            -- The shared fixture predates destructible objects. Give this suite
            -- the documented CHARACTER/GUIDSTRING boundary instead of silently
            -- treating every UUID as a character.
            function Osi.IsCharacter(id)
                local e=Fixture.entities[id]
                return e and e.Uuid and not e._isItem and 1 or 0
            end
            for _,name in ipairs({'GetEquippedItem','GetAbility','IsDead','IsInCombat'}) do
                local original=Osi[name]
                Osi[name]=function(id,...)
                    assert(Osi.IsCharacter(id)==1,name..' requires CHARACTER')
                    return original(id,...)
                end
            end
            for _,name in ipairs({'IsEnemy','IsInPartyWith'}) do
                local original=Osi[name]
                Osi[name]=function(a,b)
                    assert(Osi.IsCharacter(a)==1 and Osi.IsCharacter(b)==1,name..' requires CHARACTERs')
                    return original(a,b)
                end
            end
        ''')

    def item(self, name='crate', hp=1000, x=2):
        value = self.table(dict(Uuid=dict(EntityUuid=name), Vars={}, Health=dict(TemporaryHp=0),
                               Transform=dict(Transform=dict(Translate=[x, 0, 0])),
                               StatusContainer=dict(Statuses={}), _isItem=True, _hp=hp, _maxHp=hp,
                               _boosts={}))
        self.F.entities[name] = value
        return value

    def next_tick(self):
        timers = [timer for timer in self.F.timers.values() if timer.ms == 1]
        self.F.timers = self.table({})
        for timer in timers:
            timer.callback()

    def test_item_damage_keeps_weapon_parts_rounding_and_never_siphons_or_rewards_kill(self):
        for hand in ('main', 'off', 'qi'):
            with self.subTest(hand=hand):
                self.setUp()
                source = self.actor(level=12, branch='xueyan', hp=30)
                if hand != 'main':
                    source._equipped['Melee Main Weapon'] = None
                if hand == 'off':
                    source._equipped['Melee Offhand Weapon'] = 'sword:sword'
                crate = self.item(hp=3)
                state = self.ESC.State('sword')
                state.frenzy = 15
                spell = bridge.SPEC['spells']['xueyan_luexue']['stat']
                self.ESC.Runtime.BeginCast('sword', spell, 1, 'crate')
                first = self.native_damage('sword', 'crate', [1], spell=spell, action=1, damage_types=['Slashing'])
                second = self.native_damage('sword', 'crate', [1], spell=spell, action=1, damage_types=['Fire'])
                self.assertEqual(first.TotalDamageDone + second.TotalDamageDone, 3)
                self.assertEqual((first.DamageList[1].DamageType, second.DamageList[1].DamageType), ('Slashing', 'Fire'))
                self.F.emit('StatusApplied', 'crate', 'ESC_HIT_MARKER', 'sword', 1)
                self.F.emit('KilledBy', 'crate', 'sword', 'sword', 1)
                self.F.emit('StatusApplied', 'crate', 'DEAD', 'sword', 1)
                self.ESC.Runtime.FinishCast('sword', spell, 1)
                self.assertEqual(crate._hp, 0)
                self.assertEqual((source._hp, self.F.resource('sword').Amount, state.frenzy, state.shield), (30, 0, 15, 0))
                self.assertIsNone(crate.Vars.ESC_State)
                # A subsequent real enemy still gets the normal hit reward;
                # item handling must not leave a damage context on the stack.
                self.actor('enemy', 0, None, 1000, 1000, 'enemies', 3)
                self.ESC.Runtime.BeginCast('sword', spell, 2, 'enemy')
                self.native_damage('sword', 'enemy', [20], spell=spell, action=2)
                self.F.emit('StatusApplied', 'enemy', 'ESC_HIT_MARKER', 'sword', 2)
                self.assertGreater(source._hp, 30)
                self.assertGreater(self.F.resource('sword').Amount, 0)

    def test_item_marks_focus_and_cooperation_are_skipped_but_wenlu_cast_recovery_remains(self):
        for branch, key in (('taixuan', 'taixuan_zhaoxi'), ('xingge', 'xingge_wenlu')):
            for bonus in (False, True):
                with self.subTest(key=key, bonus=bonus):
                    self.setUp()
                    source = self.actor(branch=branch)
                    source._equipped['Melee Offhand Weapon'] = 'sword:sword'
                    self.actor('ally', 0, None, 100, 100, 'players', 1)
                    self.actor('enemy', 0, None, 100, 100, 'enemies', 3)
                    crate = self.item()
                    self.ESC.State('sword').focus = 'enemy'
                    spell = bridge.SPEC['spells'][key]['stat'] + ('_RangedOff_Bonus' if bonus else '')
                    self.ESC.Runtime.BeginCast('sword', spell, 10, 'crate')
                    self.native_damage('sword', 'crate', [10], spell=spell, action=10)
                    self.F.emit('StatusApplied', 'crate', 'ESC_HIT_MARKER', 'sword', 10)
                    self.ESC.Runtime.FinishCast('sword', spell, 10)
                    self.ESC.Runtime.BeginCast('ally', 'Target_MainHandAttack', 11, 'crate')
                    self.ESC.Runtime.Hit('ally', 'crate', 11)
                    self.assertIsNone(crate.Vars.ESC_State)
                    self.assertFalse(self.E.hasStatus('crate', 'ESC_WEAKPOINT'))
                    self.assertFalse(self.E.hasStatus('crate', 'ESC_FOLLOWUP'))
                    self.assertEqual(self.ESC.State('sword').focus, 'enemy')
                    self.assertEqual(self.F.resource('sword').Amount, 2 if branch == 'xingge' else 0)

    def test_liuguang_item_miss_keeps_three_later_native_attacks_once(self):
        self.actor(level=10, branch='taixuan')
        crate = self.item()
        spell = bridge.SPEC['spells']['taixuan_liuguang']['stat']
        self.ESC.Runtime.BeginCast('sword', spell, 20, 'crate')
        pool = self.E.resourceEntry('sword', bridge.SPEC['opportunityResource'])
        pool.Amount = 3
        self.ESC.Runtime.FinishCast('sword', spell, 20)
        self.ESC.Runtime.FinishCast('sword', spell, 20)
        calls = [c for c in self.F.calls.values() if c.name == 'UseSpell']
        self.assertEqual([(c.args[2], c.args[3]) for c in calls], [('Target_ESC_LiuguangStage', 'crate')] * 3)
        for action in (21, 22, 23):
            self.F.emit('UsingSpellOnTarget', 'sword', 'crate', 'Target_ESC_LiuguangStage', 'Target', '', action)
            hit = self.native_damage('sword', 'crate', [20], spell='Target_ESC_LiuguangStage', action=action)
            self.assertEqual(hit.TotalDamageDone, 23)
            self.F.emit('StatusApplied', 'crate', 'ESC_HIT_MARKER', 'sword', action)
            self.F.emit('CastedSpell', 'sword', 'Target_ESC_LiuguangStage', 'Target', '', action)
        self.assertEqual((crate._hp, pool.Amount, self.F.callCount('UseSpell')), (931, 3, 3))
        self.assertIsNone(crate.Vars.ESC_State)

    def test_liuguang_keeps_nonhostile_character_restriction(self):
        self.actor(branch='taixuan')
        self.actor('friend', 0, None, 100, 100, 'players', 2)
        self.cast('sword', 'taixuan_liuguang', 'friend')
        self.assertEqual(self.F.callCount('UseSpell'), 0)

    def test_lietian_item_contact_keeps_native_damage_and_world_visual_anchor(self):
        self.lua.execute('''
            Fixture.itemImpacts={}
            function Osi.PlayLoopEffectAtPosition(...) return 1 end
            function Osi.StopLoopEffect(...) end
            function Osi.PlayEffectAtPosition(effect,x,y,z,scale)
                table.insert(Fixture.itemImpacts,{effect=effect,position={x,y,z}})
            end
        ''')
        self.actor(branch='tianqing')
        crate = self.item(x=8)
        spell = bridge.SPEC['spells']['tianqing_lietian']['stat']
        self.F.emit('UsingSpellOnTarget', 'sword', 'crate', spell, 'Target', '', 30)
        self.next_tick()
        hit = self.native_damage('sword', 'crate', [20], spell=spell, action=30)
        self.F.emit('StatusApplied', 'crate', 'ESC_HIT_MARKER', 'sword', 30)
        self.ESC.Runtime.FinishCast('sword', spell, 30)
        self.assertEqual(hit.TotalDamageDone, 20)
        effect = bridge.SPEC['tianqingVfx']['timing']['tianqing_lietian']['impactEffect']
        impacts = [c for c in self.F.itemImpacts.values() if c.effect == effect]
        self.assertEqual(len(impacts), 1)
        self.assertEqual(tuple(impacts[0].position.values()), (8, 0, 0))
        self.assertIsNone(crate.Vars.ESC_State)

    def test_item_never_consumes_echo_and_mixed_hit_uses_only_real_enemy(self):
        self.actor(branch='xingge')
        self.actor('ally', 0, None, 100, 100, 'players', 1)
        self.actor('enemy', 0, None, 100, 100, 'enemies', 3)
        self.item()
        self.cast('sword', 'xingge_zhangjian')
        self.F.clearCalls()
        self.ESC.Runtime.BeginCast('ally', 'Target_MainHandAttack', 40, 'crate')
        self.ESC.Runtime.Hit('ally', 'crate', 40)
        self.next_tick()
        self.assertIsNone(self.ESC.State('sword').domains.xingge_zhangjian.used['ally'])
        self.assertEqual(self.F.callCount('UseSpell'), 0)
        self.ESC.Runtime.BeginCast('ally', 'Shout_Thunderwave', 41, 'crate')
        self.ESC.Runtime.Hit('ally', 'crate', 41)
        self.ESC.Runtime.Hit('ally', 'enemy', 41)
        self.next_tick()
        echoes = [c for c in self.F.calls.values() if c.name == 'UseSpell' and c.args[2] == 'Target_ESC_Resonance']
        self.assertEqual([c.args[3] for c in echoes], ['enemy'])

    def test_item_keeps_manual_chain_counts_without_minting_opportunities(self):
        for chain, initial, count in (('liancheng', 'Shout_ESC_xueyan_liancheng', 4),
                                      ('wusheng', 'Projectile_ESC_xueyan_wusheng_F0', 5)):
            with self.subTest(chain=chain):
                self.setUp()
                self.actor(branch='xueyan')
                crate = self.item()
                pool = self.E.resourceEntry('sword', bridge.SPEC['opportunityResource'])
                self.ESC.Runtime.BeginCast('sword', initial, 50, 'sword' if chain == 'liancheng' else 'crate')
                pool.Amount = 3
                self.ESC.Runtime.FinishCast('sword', initial, 50)
                continuation = 'Projectile_ESC_' + chain + '_ContinueRanged'
                for i in range(count):
                    action = 51 + i
                    self.ESC.Runtime.BeginCast('sword', continuation, action, 'crate')
                    self.native_damage('sword', 'crate', [10], spell=continuation, action=action)
                    self.F.emit('StatusApplied', 'crate', 'ESC_HIT_MARKER', 'sword', action)
                    self.ESC.Runtime.FinishCast('sword', continuation, action)
                    entry = self.ESC.State('sword').chains[chain]
                    self.assertEqual(entry.remaining if entry else 0, count - i - 1)
                    self.assertEqual(pool.Amount, 3)
                self.assertIsNone(crate.Vars.ESC_State)
                self.assertLess(crate._hp, 1000)

    def test_item_source_damage_avoids_character_queries_and_auto_targeting_ignores_items(self):
        self.actor(branch='taixuan', hp=100)
        self.actor('enemy', 0, None, 100, 100, 'enemies', 4)
        crate = self.item(x=1)
        self.assertFalse(self.E.friend('sword', 'crate'))
        self.assertFalse(self.E.enemy('sword', 'crate'))
        self.native_damage('crate', 'sword', [10], spell='Projectile_Explosion', action=70)
        self.assertIsNone(crate.Vars.ESC_State)
        self.cast('sword', 'taixuan_taiqing', action=71)
        pulses = [c.args[3] for c in self.F.calls.values() if c.name == 'UseSpell' and c.args[2] == 'Target_ESC_TaiqingPulse']
        self.assertEqual(pulses, ['enemy'] * 3)
        self.assertEqual(self.ESC.State('sword').focus, 'enemy')


if __name__ == '__main__':
    unittest.main()
