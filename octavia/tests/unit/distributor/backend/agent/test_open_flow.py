# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.

from unittest import mock

from octavia.distributor.backend.agent.api_server import open_flow
from octavia.tests.unit import base


class TestOpenFlow(base.TestCase):

    def test_register_rebuilds_persistent_group(self):
        state = {'vips': {}}
        commands = []

        def run(command, check=True):
            commands.append(command)
            if command[:3] == ['ovs-vsctl', 'port-to-br', 'eth1']:
                return mock.Mock(stdout='br-int\n')
            if command[:3] == ['ovs-vsctl', 'get', 'Interface']:
                return mock.Mock(stdout='7\n')
            if 'find' in command:
                return mock.Mock(stdout='tap-a,7\n')
            return mock.Mock(stdout='')

        with mock.patch.object(open_flow, 'STATE_PATH', '/tmp/state'), \
                mock.patch.object(open_flow, '_load_state',
                                  side_effect=[state, state, state]), \
                mock.patch.object(open_flow, '_save_state'), \
                mock.patch.object(open_flow, '_run', side_effect=run):
            result = open_flow.register_amphora(
                '10.0.0.10', 'aa:aa:aa:aa:aa:aa', 'eth1',
                '10.0.0.0/24', '10.0.0.1', 'bb:bb:bb:bb:bb:bb', 2)

        self.assertEqual(1, result['amphora_count'])
        group_commands = [command for command in commands
                          if command[:2] == ['ovs-ofctl', 'add-group']]
        self.assertTrue(group_commands)
        self.assertIn('set_field:bb:bb:bb:bb:bb:bb->eth_dst',
                      group_commands[0][-1])
        self.assertIn('set_field:aa:aa:aa:aa:aa:aa->eth_src',
                      group_commands[0][-1])
        self.assertTrue(any(command[:2] == ['ovs-ofctl', 'add-flow']
                            for command in commands))

    def test_runtime_needs_restore_when_bridge_is_missing(self):
        state = {
            'bridge': 'br-aa-test',
            'group_id': 1234,
            'amphora_macs': ['bb:bb:bb:bb:bb:bb'],
        }
        result = mock.Mock(returncode=2, stdout='')
        with mock.patch.object(open_flow, '_run', return_value=result):
            self.assertTrue(open_flow._runtime_needs_restore(state))

    def test_runtime_needs_restore_when_group_is_missing(self):
        state = {
            'bridge': 'br-aa-test',
            'group_id': 1234,
            'amphora_macs': ['bb:bb:bb:bb:bb:bb'],
        }
        bridge = mock.Mock(returncode=0, stdout='')
        groups = mock.Mock(returncode=0, stdout='NXST_GROUP_DESC reply')
        with mock.patch.object(open_flow, '_run', side_effect=[bridge, groups]):
            self.assertTrue(open_flow._runtime_needs_restore(state))

    def test_runtime_does_not_require_group_without_active_amphora(self):
        state = {
            'bridge': 'br-aa-test',
            'group_id': 1234,
            'amphora_macs': [],
        }
        bridge = mock.Mock(returncode=0, stdout='')
        with mock.patch.object(open_flow, '_run', return_value=bridge):
            self.assertFalse(open_flow._runtime_needs_restore(state))

    def test_runtime_needs_restore_when_vip_flow_is_missing(self):
        state = {
            'bridge': 'br-aa-test',
            'group_id': 1234,
            'vip': '10.0.0.10',
            'amphora_macs': ['bb:bb:bb:bb:bb:bb'],
        }
        bridge = mock.Mock(returncode=0, stdout='')
        groups = mock.Mock(returncode=0, stdout='group_id=1234')
        flows = mock.Mock(
            returncode=0,
            stdout='nw_dst=10.0.0.10 actions=group:1234')
        with mock.patch.object(open_flow, '_run',
                               side_effect=[bridge, groups, flows]):
            self.assertTrue(open_flow._runtime_needs_restore(state))
