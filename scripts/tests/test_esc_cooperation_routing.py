"""Native message routing distinguishes active UserID from reserved controller.

H26 Lae has ServerCharacter.UserID = unsigned(-65536), while Osiris and
UserReservedFor identify controller 65537. PostMessageToClient rejects her.
"""
import unittest

import test_esc_bridge as bridge


class CooperationRouting(unittest.TestCase):
    table = bridge.Bridge.table
    actor = bridge.Bridge.actor
    cast = bridge.Bridge.cast
    install_client = bridge.Bridge.install_client
    cooperation_intent = bridge.Bridge.cooperation_intent

    def setUp(self):
        bridge.Bridge.setUp(self)
        self.actor(branch='xingge')
        self.actor('ally', level=0, x=1)
        self.actor('enemy', level=0, party='enemies', x=2)
        self.F.entities['sword']._activeUser = 0x10001
        self.F.entities['ally']._activeUser = 0xffff0000
        self.F.entities['ally']._user = 0x10001
        self.lua.execute('''Fixture.deliveries={};Fixture.rejected={}
            local function deliver(user,channel,payload)
                if user==-65536 or user==0xffff0000 then
                    Fixture.rejected[#Fixture.rejected+1]={user=user,channel=channel};return
                end
                Fixture.deliveries[#Fixture.deliveries+1]={user=user,channel=channel,payload=payload}
            end
            function Ext.ServerNet.PostMessageToClient(id,channel,payload)
                deliver(Fixture.entities[id]._activeUser or 0xffff0000,channel,payload)
            end
            function Ext.ServerNet.PostMessageToUser(user,channel,payload)
                assert(type(user)=='number','Native PostMessageToUser requires an integer UserID')
                deliver(user,channel,payload)
            end''')

    def offer(self, action=301):
        self.cast('sword', 'xingge_tongzhou', 'enemy', action)
        rows = [r for r in self.F.deliveries.values() if r.channel == 'ESC_CooperationState']
        self.assertTrue(rows, 'Native transport rejected the assigned companion offer')
        delivery = rows[-1]
        return delivery, self.F.jsonPackets[delivery.payload]

    def test_inactive_assigned_companion_gets_offer_and_real_client_choice(self):
        delivery, packet = self.offer()
        self.assertEqual(delivery.user, 0x10001)
        self.assertEqual(packet.id, 'ally')
        self.assertTrue(packet.available)
        self.assertEqual(len(list(self.F.rejected.values())), 0)
        self.install_client()
        self.F.event('NetMessage', self.table({'Channel': delivery.channel, 'Payload': delivery.payload}))
        window = self.F.windows[1]
        self.assertTrue(window.Visible)
        window.buttons[1].OnClick()
        intent = next(c for c in reversed(list(self.F.calls.values())) if c.name == 'PostMessageToServer')
        self.F.event('NetMessage', self.table({'Channel': intent.args[1], 'Payload': intent.args[2], 'UserID': 0x10000}))
        attacks = [c for c in self.F.calls.values() if c.name == 'UseSpell']
        self.assertEqual([(c.args[1], c.args[2], c.args[3]) for c in attacks],
                         [('ally', 'ESC_FREE_Target_MainHandAttack', 'enemy')])
        revoke = list(self.F.deliveries.values())[-1]
        self.assertEqual(revoke.user, 0x10001)
        self.assertFalse(self.F.jsonPackets[revoke.payload].available)

    def test_remote_controller_gets_own_offer_without_host_fallback(self):
        self.F.entities['ally']._user = 0x20001
        delivery, packet = self.offer()
        self.assertEqual(delivery.user, 0x20001)
        self.cooperation_intent('ally', packet.token, 'Target_MainHandAttack', peer=0x10000)
        self.assertEqual(self.F.callCount('UseSpell'), 0)
        self.cooperation_intent('ally', packet.token, 'Target_MainHandAttack', peer=0x20000)
        self.assertEqual(self.F.callCount('UseSpell'), 1)

    def test_controller_change_rechecks_authority_before_executing_choice(self):
        _, packet = self.offer()
        self.F.entities['ally']._user = 0x20001
        self.cooperation_intent('ally', packet.token, 'Target_MainHandAttack', peer=0x10000)
        self.assertEqual(self.F.callCount('UseSpell'), 0)
        self.cooperation_intent('ally', packet.token, 'Target_MainHandAttack', peer=0x20000)
        self.assertEqual(self.F.callCount('UseSpell'), 1)

    def test_unassigned_companion_never_sends_to_reserved_or_arbitrary_user(self):
        for invalid in (-65536, 0xffff0000, None):
            with self.subTest(invalid=invalid):
                self.setUp()
                self.F.entities['ally']._user = invalid
                self.cast('sword', 'xingge_tongzhou', 'enemy', 301)
                self.assertEqual(len(list(self.F.deliveries.values())), 0)
                self.assertEqual(len(list(self.F.rejected.values())), 0)
                self.assertEqual(self.F.callCount('UseSpell'), 0)

    def test_duplicate_forged_and_expired_choices_remain_rejected(self):
        _, packet = self.offer()
        self.cooperation_intent('ally', packet.token + 1, 'Target_MainHandAttack')
        self.cooperation_intent('ally', packet.token, 'Target_MainHandAttack', peer=0x20000)
        self.assertEqual(self.F.callCount('UseSpell'), 0)
        self.cooperation_intent('ally', packet.token, 'Target_MainHandAttack')
        self.cooperation_intent('ally', packet.token, 'Target_MainHandAttack')
        self.assertEqual(self.F.callCount('UseSpell'), 1)
        _, packet = self.offer(action=302)
        self.F.emit('TurnStarted', 'sword')
        self.cooperation_intent('ally', packet.token, 'Target_MainHandAttack')
        self.assertEqual(self.F.callCount('UseSpell'), 1)


if __name__ == '__main__':
    unittest.main()
