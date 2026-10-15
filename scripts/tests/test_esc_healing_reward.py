"""Real Engine/Runtime with native OnHeal marker and observed asynchronous timing.

The fixture reproduces H28 action84/86: AfterExecuteFunctor precedes HP, while
OnHeal is after HP and reports rolled healing even for a full-health target.
"""
import unittest
import test_esc_bridge as bridge


class HealingReward(unittest.TestCase):
    table = bridge.Bridge.table
    actor = bridge.Bridge.actor

    def setUp(self):
        bridge.Bridge.setUp(self)
        self.actor(branch='xingge', hp=100)
        self.actor('ally', level=0, hp=15, maximum=20, x=3)
        self.F.resource('sword').Amount = 15
        self.F.deferNextTicks = True
        self.lua.execute("""
        Fixture.pendingHP={}
        Osi.SetHitpoints=function(id,hp,kind) Fixture.pendingHP[id]=hp end
        """)

    def begin(self, action=501, target='ally', caster='sword'):
        spell=bridge.SPEC['spells']['xingge_xiangfu']['stat']
        self.F.emit('UsingSpellOnTarget',caster,target,spell,'Target','',action)
        return spell

    def finish(self, action=501, spell=None):
        self.F.emit('CastedSpell','sword',spell or bridge.SPEC['spells']['xingge_xiangfu']['stat'],'Target','',action)

    def result(self, action=501, caster='sword', target='ally', amount=5,
               spell='Target_ESC_xingge_xiangfu', apply=True):
        return self.F.nativeHeal(caster,spell,target,action,amount,not apply)

    def test_native_passive_contract_uses_positive_heal_and_exact_eligible_spell(self):
        passive=self.F.stats.ESC_P_xingge_cooperation
        self.assertEqual(passive.StatsFunctorContext,'OnHeal')
        self.assertEqual(passive.Conditions,
            "HealDoneGreaterThan(0) and SpellId('Target_ESC_xingge_xiangfu') and not Self() and Party() and not IsSummon()")
        self.assertEqual(passive.StatsFunctors,'ApplyStatus(ESC_XIANGFU_HEALED,100,0)')

    def test_live_h27_zero_functor_result_and_later_four_hp_gain_refund_once_after_payment(self):
        self.actor('ally',level=0,hp=5,maximum=12,x=3)
        self.F.resource('sword').Amount=50
        self.begin(action=72)
        self.result(action=72,amount=4)  # Before/After expose HP5 and zero; native completes to9.
        self.assertEqual(self.F.entities['ally']._hp,9)
        self.assertEqual(self.F.resource('sword').Amount,50)
        self.F.resource('sword').Amount=44
        self.finish(action=72);self.F.runNextTick()
        self.assertEqual(self.F.resource('sword').Amount,47)

    def test_partial_overheal_awards_once_and_full_health_control_does_not(self):
        self.actor('ally',level=0,hp=9,maximum=12,x=3)
        self.begin(action=73);self.result(action=73,amount=4)
        self.assertEqual(self.F.entities['ally']._hp,12)
        self.finish(action=73);self.F.runNextTick()
        self.assertEqual(self.F.resource('sword').Amount,18)
        self.begin(action=74);self.result(action=74,amount=4);self.finish(action=74);self.F.runNextTick()
        self.assertEqual(self.F.resource('sword').Amount,18)

    def test_native_heal_replaces_queued_sethp_and_refunds_after_paid_root(self):
        spell=self.begin()
        self.assertIn('RegainHitPoints((Target.MaxHP*LevelMapValue(ESC_XiangfuHealing)+99)/100,Guaranteed)',self.F.stats[spell].SpellProperties)
        self.F.resource('sword').Amount=9  # Native level-4+ variant costs 6.
        self.result()
        self.finish()
        self.F.runNextTick()
        self.assertEqual(self.F.entities['ally']._hp,20)
        self.assertEqual(self.F.resource('sword').Amount,12)
        self.assertEqual(len(list(self.F.pendingHP.items())),0)

    def test_one_actual_point_counts_but_full_overheal_or_blocked_does_not(self):
        for actual in (0,1,5):
            with self.subTest(actual=actual):
                self.setUp();self.begin();self.result(amount=actual);self.finish();self.F.runNextTick()
                self.assertEqual(self.F.resource('sword').Amount,15+(3 if actual else 0))

    def test_unrelated_source_action_spell_target_cannot_award(self):
        self.actor('other',branch='xingge');self.actor('otherally',level=0,hp=1,maximum=20,x=3)
        for overrides in (dict(action=502),dict(caster='other'),dict(spell='Target_HealingWord'),dict(target='otherally')):
            with self.subTest(overrides=overrides):
                self.begin();self.result(**overrides);self.finish();self.F.runNextTick()
                self.assertEqual(self.F.resource('sword').Amount,15)

    def test_other_heal_and_damage_between_completion_and_tick_do_not_change_receipt(self):
        self.begin();self.result(amount=2);self.finish()
        self.F.entities['ally']._hp=3  # Later damage must not erase earned support.
        self.F.runNextTick();self.assertEqual(self.F.resource('sword').Amount,18)
        self.setUp();self.begin();self.result(amount=0);self.finish()
        self.F.entities['ally']._hp=20  # An unrelated heal must not create it.
        self.F.runNextTick();self.assertEqual(self.F.resource('sword').Amount,15)

    def test_duplicate_native_receipts_and_canonical_alias_award_once(self):
        self.F.entities['Hero_sword']=self.F.entities['sword']
        self.F.entities['Companion_ally']=self.F.entities['ally']
        self.begin(caster='Hero_sword',target='Companion_ally');self.result(amount=1)
        self.result(amount=1);self.finish();self.finish();self.F.runNextTick()
        self.assertEqual(self.F.resource('sword').Amount,18)

    def test_receipt_after_casted_uses_same_root_and_settles_once(self):
        self.begin();self.finish();self.result();self.F.runNextTick()
        self.assertEqual(self.F.resource('sword').Amount,18)

    def test_rolled_positive_without_actual_gain_or_other_gain_without_receipt_is_not_support(self):
        for native,apply in ((5,False),(0,True)):
            with self.subTest(native=native):
                self.setUp();self.begin()
                self.result(amount=native,apply=apply)
                self.finish();self.F.runNextTick()
                self.assertEqual(self.F.resource('sword').Amount,15)

    def test_actual_native_heal_on_self_keeps_healing_but_never_refunds(self):
        self.F.entities['sword']._hp=50
        spell=self.begin(target='sword')
        self.F.statusFunctors('sword',spell,'sword',501)
        self.finish();self.F.runNextTick()
        self.assertEqual(self.F.entities['sword']._hp,80)
        self.assertEqual(self.F.resource('sword').Amount,15)
        self.assertEqual(len(list(self.F.pendingHP.items())),0)

    def test_native_formula_ranks_and_summon_filter_are_preserved(self):
        for level,expected in ((3,18),(4,20),(12,20)):
            with self.subTest(level=level):
                self.setUp();self.actor(level=level,branch='xingge')
                spell=self.begin();self.F.statusFunctors('sword',spell,'ally',501)
                self.assertEqual(self.F.entities['ally']._hp,expected)
        self.setUp();self.F.entities['ally']._summon=True
        spell=self.begin();self.F.statusFunctors('sword',spell,'ally',501)
        self.assertEqual(self.F.entities['ally']._hp,15)

    def test_fractional_percentage_rounds_up_for_both_healing_ranks(self):
        # Sufficient missing HP avoids cap/zero-HP effects hiding rounding.
        for level,expected in ((3,{21:4,23:4,124:19}),(12,{21:7,23:7,124:38})):
            for maximum,healed in expected.items():
                with self.subTest(level=level,maximum=maximum):
                    self.setUp();self.actor(level=level,branch='xingge')
                    self.actor('ally',level=0,hp=1,maximum=maximum,x=3)
                    spell=self.begin();self.F.statusFunctors('sword',spell,'ally',501)
                    self.assertEqual(self.F.entities['ally']._hp,1+healed)

    def test_failed_or_invalid_cast_and_nonparty_target_never_refund(self):
        for mode in ('failed','invalid','neutral','self'):
            with self.subTest(mode=mode):
                self.setUp();target='sword' if mode=='self' else 'ally';spell=self.begin(target=target)
                if mode=='failed':self.F.emit('CastSpellFailed','sword',spell,'Target','',501)
                elif mode=='invalid':self.ESC.Runtime.BeginCast('sword',spell,501,'ally').invalid=True
                elif mode=='neutral':self.F.entities['ally']._party='neutral'
                self.result(target=target);self.finish();self.F.runNextTick()
                self.assertEqual(self.F.resource('sword').Amount,15)

    def test_one_point_missing_at_large_maximum_survives_rounded_native_percent(self):
        self.actor('ally',level=0,hp=123,maximum=124,x=3)
        self.begin();self.result(amount=38);self.finish();self.F.runNextTick()
        self.assertEqual(self.F.entities['ally']._hp,124)
        self.assertEqual(self.F.resource('sword').Amount,18)

    def test_heal_between_using_and_native_execution_does_not_leave_stale_missing_hp(self):
        self.begin()
        self.F.entities['ally']._hp=20
        self.result(amount=5);self.finish();self.F.runNextTick()
        self.assertEqual(self.F.resource('sword').Amount,15)

    def test_other_native_heal_during_pending_receipt_is_not_misattributed(self):
        self.actor('other',branch='xingge')
        self.begin()
        self.lua.execute("""
        Fixture.beforeNativeHeal=function()
            Fixture.nativeHeal('other','Target_HealingWord','ally',600,5,false)
        end
        """)
        self.result(amount=5);self.finish();self.F.runNextTick()
        self.assertEqual(self.F.entities['ally']._hp,20)
        self.assertEqual(self.F.resource('sword').Amount,15)

    def test_scripted_heal_or_damage_interference_cannot_award_from_net_delta(self):
        for operation in ('heal','damage'):
            with self.subTest(operation=operation):
                self.setUp();self.begin()
                if operation=='heal':
                    self.lua.execute("""
                    Fixture.beforeNativeHeal=function()
                        ESC.Engine.heal('ally',5)
                        Fixture.entities.ally._hp=20
                    end
                    """)
                else:
                    self.lua.execute("""
                    Fixture.beforeNativeHeal=function()
                        Fixture.event('DealDamage',{Caster='sword',Target='ally',StoryActionId=700,
                            Hit={TotalDamageDone=2,DamageList={}}})
                        Fixture.entities.ally._hp=13
                        Fixture.event('DealtDamage',{Target='ally',Hit={TotalDamageDone=2,DamageList={}}})
                    end
                    """)
                self.result(amount=5);self.finish();self.F.runNextTick()
                self.assertEqual(self.F.resource('sword').Amount,15)

    def test_read_load_or_failure_clears_pending_native_receipt(self):
        for operation in ('load','failed'):
            with self.subTest(operation=operation):
                self.setUp();self.begin()
                if operation=='load':
                    self.lua.execute("Fixture.beforeNativeHeal=function() ESC.Runtime.SessionLoaded() end")
                else:
                    self.lua.execute("Fixture.beforeNativeHeal=function() Fixture.emit('CastSpellFailed','sword','Target_ESC_xingge_xiangfu','Target','',501) end")
                self.result();self.finish();self.F.runNextTick()
                self.assertEqual(self.F.resource('sword').Amount,15)

    def wind(self, level=12, hp=30):
        self.actor(level=level,branch='xingge',hp=hp,maximum=124)
        self.F.resource('sword').Amount=30
        bridge.Bridge.cast(self,'sword','xingge_fengyu',action=880)

    def test_native_wind_healing_waits_for_receipt_and_applies_rounded_extra(self):
        for level,multiplier in ((9,1.5),(12,1.75)):
            with self.subTest(level=level):
                self.setUp();self.wind(level=level)
                self.F.nativeHeal('sword','Target_ESC_xingge_xiangfu','sword',881,38,False)
                self.assertEqual(self.F.entities['sword']._hp,68)
                self.assertIsNone(self.F.pendingHP['sword'])
                self.F.runNextTick()
                self.assertEqual(self.F.pendingHP['sword'],30+__import__('math').ceil(38*multiplier))

    def test_wind_receipt_respects_expiry_and_duplicate_native_delivery(self):
        self.wind(hp=68)
        self.F.nativeHeal('sword','Target_ESC_xingge_xiangfu','sword',881,38,False)
        self.F.runNextTick()
        self.assertEqual(self.F.pendingHP['sword'],124)
        self.F.pendingHP['sword']=None
        self.lua.execute("""
        local entity=Fixture.entities.sword
        entity._nativeHealStatus={Started=true,HealAmount=38,StoryActionID=881,StatusSource='sword'}
        Fixture.entityCreated('ServerStatusApplyEvent',{Target='sword',StatusId='HEAL'})
        entity._nativeHealStatus=nil
        """)
        self.assertIsNone(self.F.pendingHP['sword'])
        self.setUp();self.wind()
        self.lua.execute("Fixture.beforeNativeHeal=function() Osi.RemoveStatus('sword','ESC_DAMAGE_SHARE','sword') end")
        self.F.nativeHeal('sword','Target_ESC_xingge_xiangfu','sword',881,38,False)
        self.assertIsNone(self.F.pendingHP['sword'])

    def test_scripted_wind_heal_and_regeneration_do_not_get_second_multiplier(self):
        self.wind()
        self.E.heal('sword',38)
        self.assertEqual(self.F.pendingHP['sword'],97)
        self.E.heal('sword',10,True)
        self.assertEqual(self.F.pendingHP['sword'],40)
        self.assertIsNone(self.F.entities['sword']['_nativeHealStatus'])

    def test_same_frame_native_wind_bonus_receipts_coalesce_without_losing_healing(self):
        self.wind()
        self.F.nativeHeal('sword','Target_HealingWord','sword',881,10,False)
        self.F.nativeHeal('sword','Target_HealingWord','sword',882,10,False)
        self.assertEqual(self.F.entities['sword']._hp,50)
        self.assertIsNone(self.F.pendingHP['sword'])
        self.F.runNextTick()
        self.assertEqual(self.F.pendingHP['sword'],66)  # Two ceil(10*1.75)-10 bonuses.

    def test_wind_bonus_is_owner_only_and_cancelled_on_session_reload(self):
        self.wind()
        self.F.nativeHeal('sword','Target_HealingWord','ally',881,2,False)
        self.F.runNextTick();self.assertIsNone(self.F.pendingHP['ally'])
        self.F.nativeHeal('sword','Target_HealingWord','sword',882,38,False)
        self.ESC.Runtime.SessionLoaded();self.F.runNextTick()
        self.assertIsNone(self.F.pendingHP['sword'])

    def test_native_self_cast_context_is_amplified_without_needing_target_flag(self):
        self.wind()
        self.F.nativeHealContext=self.table(dict(CAST=True))
        self.F.nativeHeal('sword','Shout_WholenessOfBody','sword',883,10,False)
        self.F.runNextTick();self.assertEqual(self.F.pendingHP['sword'],48)

    def test_scripted_heal_interference_does_not_consume_native_credentials_for_wind(self):
        self.wind()
        self.lua.execute("""
        Fixture.beforeNativeHeal=function()
            ESC.Engine.heal('sword',10)
            Fixture.pendingHP.sword=nil
            -- A foreign script may carry the same action/source into HEAL.
            local entity=Fixture.entities.sword
            entity._nativeHealStatus={Started=true,HealAmount=10,StoryActionID=881,StatusSource='sword'}
            entity.ServerCharacter={GetStatus=function() return entity._nativeHealStatus end}
            Fixture.entityCreated('ServerStatusApplyEvent',{Target='sword',StatusId='HEAL'})
            entity._nativeHealStatus=nil
        end
        """)
        self.F.nativeHeal('sword','Target_HealingWord','sword',881,38,False)
        self.F.runNextTick();self.assertIsNone(self.F.pendingHP['sword'])


if __name__=='__main__':unittest.main()
