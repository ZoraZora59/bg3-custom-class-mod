"""Exercise real Runtime/Engine with native Name_GUID and bare UUID aliases.

Deterministic simulation only; native damage, gestures and VFX remain pending.
"""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

REPO = next(p for p in Path(__file__).resolve().parents
            if (p / 'scripts/tests/test_esc_bridge.py').is_file())
sys.path.insert(0, str(REPO / 'scripts/tests'))
import test_esc_bridge as bridge

MAIN = 'd764e091-3386-cd8e-70c5-7a3e067848d9'
NAMED_MAIN = 'Goblins_Male_Guard_' + MAIN
INSIDE = 'dfd44248-1212-4eb9-a6b4-8d7335ad57f7'
SPELL = 'Target_ESC_tianqing_tianbeng'
MARKER = 'ESC_SAVEFAIL_TIANQING_TIANBENG'


class TianbengEntityIdentity(unittest.TestCase):
    def setUp(self):
        runtime = Path(os.environ.get('ESC_IDENTITY_RUNTIME_CANDIDATE', bridge.LUA / 'Runtime.lua'))
        snapshot = dict(bridge.SNAPSHOT)
        snapshot['Runtime.lua'] = runtime.read_bytes()
        with patch.object(bridge, 'SNAPSHOT', snapshot):
            bridge.Bridge.setUp(self)
        source = bridge.Bridge.actor(self, level=10, branch='tianqing')
        source._equipped['Melee Main Weapon'] = None
        source._equipped['Melee Offhand Weapon'] = 'sword:sword'
        bridge.Bridge.actor(self, MAIN, 0, None, 1000, 1000, 'enemies', 8)
        bridge.Bridge.actor(self, INSIDE, 0, None, 1000, 1000, 'enemies', 4)
        bridge.Bridge.actor(self, 'ally', 0, None, 1000, 1000, 'players', 4)
        self.lua.globals().Fixture.entityAliases = self.lua.table_from({NAMED_MAIN: MAIN})
        # Entity.Get and native Osiris both resolve a Name_GUID to its one
        # canonical entity. No comparator, Runtime, or helper is mocked.
        self.lua.execute('''
            local originalGet=Ext.Entity.Get
            function Ext.Entity.Get(ref)
                return originalGet(Fixture.entityAliases[ref] or ref)
            end
            for name,fn in pairs(Osi) do
                local original=fn
                Osi[name]=function(...)
                    local args=table.pack(...)
                    for index=1,args.n do
                        if type(args[index])=='string' then
                            args[index]=Fixture.entityAliases[args[index]] or args[index]
                        end
                    end
                    return original(table.unpack(args,1,args.n))
                end
            end
        ''')

    def begin(self, target, action):
        self.F.emit('UsingSpellOnTarget', 'sword', target, SPELL, 'Target', '', action)
        self.assertEqual(self.E['class']('sword'), (10, 'tianqing'))
        self.F.clearCalls()

    def test_named_primary_is_excluded_from_followup_cone(self):
        self.begin(NAMED_MAIN, 901)
        self.ESC.Runtime.FinishCast('sword', SPELL, 901)
        calls = [call for call in self.F.calls.values() if call.name == 'UseSpell']
        self.assertEqual([(call.args[2], call.args[3]) for call in calls],
                         [('Target_ESC_TianbengCone_Off', INSIDE)])
        self.ESC.Runtime.FinishCast('sword', SPELL, 901)
        self.assertEqual(self.F.callCount('UseSpell'), 1)

    def test_bare_primary_keeps_single_cone_followup(self):
        self.begin(MAIN, 911)
        self.ESC.Runtime.FinishCast('sword', SPELL, 911)
        calls = [call for call in self.F.calls.values() if call.name == 'UseSpell']
        self.assertEqual([(call.args[2], call.args[3]) for call in calls],
                         [('Target_ESC_TianbengCone_Off', INSIDE)])

    def test_named_primary_save_bare_event_gets_armor_penalty(self):
        self.begin(NAMED_MAIN, 921)
        self.F.emit('StatusApplied', MAIN, MARKER, 'sword', 921)
        self.assertEqual(self.ESC.State(MAIN).debuffs['sword:tianqing_tianbeng'].ac, -3)
        self.ESC.Runtime.FinishCast('sword', SPELL, 921)
        self.F.emit('UsingSpellOnTarget', 'sword', INSIDE,
                    'Target_ESC_TianbengCone_Off', 'Target', '', 922)
        self.F.emit('StatusApplied', INSIDE, MARKER, 'sword', 922)
        self.assertIsNone(self.ESC.State(INSIDE).debuffs['sword:tianqing_tianbeng'].ac)

    def test_bare_primary_save_named_event_gets_armor_penalty(self):
        self.begin(MAIN, 931)
        self.F.emit('StatusApplied', NAMED_MAIN, MARKER, 'sword', 931)
        self.assertEqual(self.ESC.State(MAIN).debuffs['sword:tianqing_tianbeng'].ac, -3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
