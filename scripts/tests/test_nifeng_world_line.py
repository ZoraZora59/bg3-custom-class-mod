"""Nifeng visual-only contracts in simulated BG3; not native event/visual QA."""
import copy
import importlib.util
import itertools
import math
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p / 'scripts/tests/test_esc_bridge.py').is_file())
sys.path.insert(0, str(REPO / 'scripts/tests'))
import test_esc_bridge as bridge

SOURCE_ROOT = HERE.parents[1]
RUNTIME_REL = Path('mods/EasternSwordCultivator/Source/Mods') / bridge.FOLDER / 'ScriptExtender/Lua/Runtime.lua'
CANDIDATE_RUNTIME = (SOURCE_ROOT / RUNTIME_REL).read_bytes()
author_loader = importlib.util.spec_from_file_location('nifeng_test_author', SOURCE_ROOT / 'scripts/nifeng_vfx.py')
author = importlib.util.module_from_spec(author_loader)
author_loader.loader.exec_module(author)
CONFIG = dict(enabled=True, effect=author.guid('vfx/effect/nifeng/long-blade'), heightOffset=.8, range=12)


def plain(value):
    if hasattr(value, 'items'):
        return {str(k): plain(v) for k, v in value.items()}
    return value


class NifengBridge(unittest.TestCase):
    table = bridge.Bridge.table
    actor = bridge.Bridge.actor

    def install(self, candidate=True, enabled=True):
        snapshot = dict(bridge.SNAPSHOT)
        if candidate:
            snapshot['Runtime.lua'] = CANDIDATE_RUNTIME
        spec = copy.deepcopy(bridge.SPEC)
        # After merge this remains a real visual-on/off comparison, rather
        # than accidentally comparing the same enabled Runtime to itself.
        spec['nifengLineVfx'] = dict(CONFIG, enabled=enabled and candidate)
        with patch.object(bridge, 'SNAPSHOT', snapshot), patch.object(bridge, 'SPEC', spec):
            bridge.Bridge.setUp(self)
        self.lua.execute('''
            Fixture.lineAttempts=0
            function Osi.PlayEffectAtPositionAndRotation(effect,x,y,z,yaw,scale)
                assert(type(effect)=='string' and type(x)=='number' and type(y)=='number'
                    and type(z)=='number' and type(yaw)=='number' and scale==1)
                Fixture.lineAttempts=Fixture.lineAttempts+1
                if Fixture.failLine then error('simulated unavailable effect') end
                Fixture.calls[#Fixture.calls+1]={name='PlayEffectAtPositionAndRotation',args={effect,x,y,z,yaw,scale}}
            end
        ''')
        self.actor(branch='tianqing')
        self.actor('enemy', 0, None, 500, 500, 'enemies', 4)
        self.native = 'Zone_ESC_tianqing_nifeng'
        self.offhand = 'Zone_ESC_tianqing_nifeng_RangedOff_Bonus'

    def setUp(self):
        self.install()

    def lines(self):
        return [call for call in self.F.calls.values()
                if call.name == 'PlayEffectAtPositionAndRotation' and call.args[1] == CONFIG['effect']]

    def select(self, point=(8, 0, 0), action=1001, stat=None):
        self.F.emit('UsingSpellAtPosition', 'sword', *point, stat or self.native, 'Zone', '', action)

    def finish(self, action=1001, stat=None):
        self.F.emit('CastedSpell', 'sword', stat or self.native, 'Zone', '', action)

    def fail(self, action=1001):
        self.F.emit('CastSpellFailed', 'sword', self.native, 'Zone', '', action)

    def miss(self, action=1001, owner='sword', attacker='sword'):
        self.F.emit('MissedBy', 'enemy', owner, attacker, action)

    def damage(self, target='enemy', action=1001):
        hit = self.table(dict(DamageList=[dict(Amount=1, DamageType='Force')], TotalDamageDone=1,
                              Damage=dict(TotalDamage=101), SpellId=self.native))
        event = self.table(dict(Caster='sword', Target=target, StoryActionId=action, Hit=hit,
                                Functor=dict(FunctorUuid='11111111-1111-1111-1111-111111111111')))
        self.F.event('DealDamage', event)
        self.F.event('BeforeDealDamage', self.table(dict(Hit=hit)))
        self.F.event('DealtDamage', event)
        return plain(hit)

    def test_hit_packets_targets_misses_and_completion_share_one_attempt(self):
        self.actor('far', 0, None, 500, 500, 'enemies', 9)
        self.select()
        self.damage(); self.damage(); self.damage('far')
        self.miss(); self.finish(); self.finish()
        self.assertEqual(self.F.lineAttempts, 1)
        self.assertEqual(len(self.lines()), 1)

    def test_native_miss_before_or_after_failed_has_one_visual_no_gameplay_completion(self):
        for order in (('miss', 'fail'), ('fail', 'miss')):
            with self.subTest(order=order):
                self.install(); self.select()
                for name in order:
                    getattr(self, name)()
                self.miss(); self.finish()
                self.assertEqual(self.F.lineAttempts, 1)
                # The existing failed flag still suppresses completion and opportunity grants.
                resources = self.F.entities['sword'].ActionResources.Resources
                opportunity = resources[bridge.SPEC['opportunityResource']]
                self.assertTrue(opportunity is None or opportunity[1].Amount == 0)

    def test_miss_casted_and_damage_ordering_never_duplicates(self):
        for order in itertools.permutations(('miss', 'finish', 'damage')):
            with self.subTest(order=order):
                self.install(); self.select()
                for name in order:
                    getattr(self, name)()
                self.assertEqual(self.F.lineAttempts, 1)

    def test_preview_failed_without_miss_never_plays(self):
        self.select(); self.fail(); self.finish()
        self.assertEqual(self.F.lineAttempts, 0)

    def test_empty_success_and_independent_main_offhand_actions_each_play_once(self):
        self.select(); self.finish(); self.finish()
        self.select((-2, 0, 0), 1002, self.offhand)
        self.finish(1002, self.offhand); self.miss(1002)
        self.assertEqual(self.F.lineAttempts, 2)

    def test_real_selected_direction_short_distance_and_fixed_endpoint(self):
        self.ESC.Runtime.StartDiagnostics()
        for action, (point, yaw) in enumerate((((2, 0, 0), 270), ((-2, 0, 0), 90),
                    ((0, 0, -2), 0), ((0, 0, 2), 180), ((2, 0, 2), 225)), 1001):
            self.select(point, action); self.finish(action)
            self.assertAlmostEqual(self.lines()[-1].args[5], yaw)
        traces = [row for row in self.ESC.Runtime.Diagnostics().values() if row.phase == 'NifengLine']
        self.assertEqual(len(traces), 5)
        for row in traces:
            self.assertAlmostEqual(math.hypot(row.finish[1] - row.start[1], row.finish[3] - row.start[3]), 12)

    def test_start_and_first_explicit_selection_survive_later_target_actor_motion(self):
        self.F.entities['sword'].Transform.Transform.Translate = self.table([10, 4, 20])
        self.select((12, 80, 20))
        self.F.entities['sword'].Transform.Transform.Translate = self.table([40, 7, 60])
        self.F.emit('UsingSpellOnTarget', 'sword', 'enemy', self.native, 'Zone', '', 1001)
        self.select((0, 0, -8))  # repeated position must not overwrite the first explicit anchor
        self.miss()
        call, = self.lines()
        self.assertEqual([call.args[i] for i in range(2, 6)], [10, 4.8, 20, 270])

    def test_other_owner_attacker_action_or_spell_cannot_emit_nifeng(self):
        self.actor('other', 12, 'tianqing')
        self.select()
        self.miss(owner='other'); self.miss(attacker='other'); self.miss(action=9999)
        self.select(action=1002, stat=bridge.SPEC['spells']['tianqing_wanjun']['stat'])
        self.miss(action=1002)
        self.assertEqual(self.F.lineAttempts, 0)

    def test_disabled_zero_missing_nonfinite_direction_and_preview_action_are_skipped(self):
        self.install(enabled=False); self.select(); self.miss(); self.finish()
        self.assertEqual(self.F.lineAttempts, 0)
        self.install()
        for action, point in enumerate(((0, 0, 0), (float('nan'), 0, 1), (float('inf'), 0, 1)), 1001):
            self.select(point, action); self.miss(action)
        self.F.emit('UsingSpell', 'sword', self.native, 'Zone', '', 1010); self.miss(1010)
        self.select(action=0); self.miss(0); self.finish(0)
        self.assertEqual(self.F.lineAttempts, 0)

    def test_visual_call_failure_is_one_attempt_and_does_not_abort_damage(self):
        self.select(); self.F.failLine = True
        first = self.damage(); self.damage(); self.miss(); self.finish()
        self.assertGreater(first['TotalDamageDone'], 0)
        self.assertEqual(self.F.lineAttempts, 1)
        self.assertEqual(self.lines(), [])

    def test_owner_and_session_invalidation_block_late_miss_and_finish(self):
        for kind in ('DEAD', 'DOWNED', 'DYING', 'LeftCombat', 'SessionLoaded'):
            with self.subTest(kind=kind):
                self.install(); self.select(); self.fail()
                if kind == 'SessionLoaded':
                    self.ESC.Runtime.SessionLoaded()
                elif kind == 'LeftCombat':
                    self.F.emit(kind, 'sword', 'fixture-combat')
                else:
                    self.F.emit('StatusApplied', 'sword', kind, 'sword', 900)
                self.miss(); self.finish()
                self.assertEqual(self.F.lineAttempts, 0)

    def test_missing_owner_blocks_late_miss(self):
        self.select(); self.F.entities['sword'] = None; self.miss()
        self.assertEqual(self.F.lineAttempts, 0)

    def test_baseline_candidate_mechanics_and_native_calls_match(self):
        def run(candidate, route, fail_visual=False):
            self.install(candidate=candidate); self.select(); self.F.failLine = fail_visual
            hits = []
            for event in route:
                if event == 'damage':
                    hits.append(self.damage())
                else:
                    getattr(self, event)()
            calls = [plain(call) for call in self.F.calls.values()
                     if call.name != 'PlayEffectAtPositionAndRotation'
                     and not (call.name == 'Print' and 'Nifeng line visual call failed' in str(call.args[1]))]
            return dict(hits=hits, calls=calls, state=plain(self.F.entities['sword'].Vars),
                        resources=plain(self.F.entities['sword'].ActionResources),
                        playerHP=self.F.entities['sword']._hp, targetHP=self.F.entities['enemy']._hp)
        for route in (('damage', 'damage', 'finish'), ('miss', 'finish'), ('fail', 'miss', 'finish'), ('fail', 'finish')):
            with self.subTest(route=route):
                baseline = run(False, route)
                self.assertEqual(run(True, route), baseline)
                self.assertEqual(run(True, route, True), baseline)


class NifengAuthor(unittest.TestCase):
    def test_authored_geometry_lifetime_owned_materials_and_no_audio(self):
        root, _, designs = author.author(author.beam.fx.DATA)
        components = [track.find('component') for track in root.findall('.//track')]
        self.assertEqual([c.get('class') for c in components], ['Model', 'Model', 'BoundingSphere'])
        self.assertTrue(all(p.get('playcount') == '1' for p in root.findall('./phases/object/data')))
        self.assertEqual([float(c.get('end')) for c in components], [.34, .42, .42])
        for design in designs:
            self.assertAlmostEqual(design['axis_scale'][2] * 10.000001, 12)
        bounds = components[-1]
        value = lambda key: bounds.find(f'./properties/property[@id="{key}"]/data/datum').get('value')
        self.assertEqual(value(author.beam.fx.BOUND_CENTER), '0,0,-6')
        self.assertGreaterEqual(float(value(author.beam.fx.BOUND_RADIUS)), math.hypot(6, .4))
        materials = {n.get('value') for n in author.visual_bank().findall('.//attribute[@id="MaterialID"]')}
        self.assertEqual(materials, {author.material_id('tianqing'), author.material_id('tianqing', 'circle')})

    def test_missing_native_receipt_never_enables_or_writes_resources(self):
        # An isolated empty Source keeps this gate active after real compilation.
        with TemporaryDirectory() as temporary_source:
            source = Path(temporary_source)
            with patch.object(author.resources, '_write_xml', side_effect=AssertionError('unexpected resource write')):
                self.assertFalse(author.generate_resources(source)['enabled'])
            self.assertEqual(list(source.rglob('*')), [])


if __name__ == '__main__':
    unittest.main()
