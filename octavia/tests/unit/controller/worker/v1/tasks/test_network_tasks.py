# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils
from taskflow.types import failure
import tenacity

from octavia.common import constants
from octavia.common import data_models as o_data_models
from octavia.common import exceptions
from octavia.controller.worker.v1.tasks import network_tasks
from octavia.network import base as net_base
from octavia.network import data_models
from octavia.tests.common import constants as t_constants
import octavia.tests.unit.base as base


AMPHORA_ID = 7
COMPUTE_ID = uuidutils.generate_uuid()
PORT_ID = uuidutils.generate_uuid()
SUBNET_ID = uuidutils.generate_uuid()
NETWORK_ID = uuidutils.generate_uuid()
SG_ID = uuidutils.generate_uuid()
IP_ADDRESS = "172.24.41.1"
VIP = o_data_models.Vip(port_id=t_constants.MOCK_PORT_ID,
                        subnet_id=t_constants.MOCK_SUBNET_ID,
                        qos_policy_id=t_constants.MOCK_QOS_POLICY_ID1)
VIP2 = o_data_models.Vip(port_id=t_constants.MOCK_PORT_ID2,
                         subnet_id=t_constants.MOCK_SUBNET_ID2,
                         qos_policy_id=t_constants.MOCK_QOS_POLICY_ID2)
LB = o_data_models.LoadBalancer(vip=VIP)
LB2 = o_data_models.LoadBalancer(vip=VIP2)
FIRST_IP = {"ip_address": IP_ADDRESS, "subnet_id": SUBNET_ID}
FIXED_IPS = [FIRST_IP]
INTERFACE = data_models.Interface(id=uuidutils.generate_uuid(),
                                  compute_id=COMPUTE_ID, fixed_ips=FIXED_IPS,
                                  port_id=PORT_ID)
AMPS_DATA = [o_data_models.Amphora(id=t_constants.MOCK_AMP_ID1,
                                   vrrp_port_id=t_constants.MOCK_VRRP_PORT_ID1,
                                   vrrp_ip=t_constants.MOCK_VRRP_IP1),
             o_data_models.Amphora(id=t_constants.MOCK_AMP_ID2,
                                   vrrp_port_id=t_constants.MOCK_VRRP_PORT_ID2,
                                   vrrp_ip=t_constants.MOCK_VRRP_IP2)
             ]
UPDATE_DICT = {constants.TOPOLOGY: None}


class TestException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


@mock.patch('octavia.common.utils.get_network_driver')
class TestNetworkTasks(base.TestCase):
    def setUp(self):
        network_tasks.LOG = mock.MagicMock()
        self.amphora_mock = mock.MagicMock()
        self.load_balancer_mock = mock.MagicMock()
        self.vip_mock = mock.MagicMock()
        self.vip_mock.subnet_id = SUBNET_ID
        self.load_balancer_mock.vip = self.vip_mock
        self.load_balancer_mock.amphorae = []
        self.amphora_mock.id = AMPHORA_ID
        self.amphora_mock.compute_id = COMPUTE_ID
        self.amphora_mock.status = constants.AMPHORA_ALLOCATED
        self.boot_net_id = NETWORK_ID
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group="controller_worker",
                    amp_boot_network_list=[self.boot_net_id])
        conf.config(group="networking", max_retries=1)
        super().setUp()

    def test_calculate_amphora_delta(self, mock_get_net_driver):
        DELETE_NETWORK_ID = uuidutils.generate_uuid()
        MEMBER_NETWORK_ID = uuidutils.generate_uuid()
        MEMBER_SUBNET_ID = uuidutils.generate_uuid()
        VRRP_PORT_ID = uuidutils.generate_uuid()
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        member_mock = mock.MagicMock()
        member_mock.subnet_id = MEMBER_SUBNET_ID
        pool_mock = mock.MagicMock()
        pool_mock.members = [member_mock]
        lb_mock = mock.MagicMock()
        lb_mock.pools = [pool_mock]
        amphora_mock = mock.MagicMock()
        amphora_mock.id = AMPHORA_ID
        amphora_mock.compute_id = COMPUTE_ID
        amphora_mock.vrrp_port_id = VRRP_PORT_ID
        vrrp_port_mock = mock.MagicMock()
        vrrp_port_mock.network_id = self.boot_net_id
        mock_subnet = mock.MagicMock()
        mock_subnet.network_id = MEMBER_NETWORK_ID
        nic1_delete_mock = mock.MagicMock()
        nic1_delete_mock.network_id = DELETE_NETWORK_ID
        nic2_keep_mock = mock.MagicMock()
        nic2_keep_mock.network_id = self.boot_net_id

        mock_driver.get_port.return_value = vrrp_port_mock
        mock_driver.get_subnet.return_value = mock_subnet
        mock_driver.get_plugged_networks.return_value = [nic1_delete_mock,
                                                         nic2_keep_mock]

        calc_amp_delta = network_tasks.CalculateAmphoraDelta()

        # Test vrrp_port_id is None
        result = calc_amp_delta.execute(lb_mock, amphora_mock, {})

        self.assertEqual(AMPHORA_ID, result.amphora_id)
        self.assertEqual(COMPUTE_ID, result.compute_id)
        self.assertEqual(1, len(result.add_nics))
        self.assertEqual(MEMBER_NETWORK_ID, result.add_nics[0].network_id)
        self.assertEqual(1, len(result.delete_nics))
        self.assertEqual(DELETE_NETWORK_ID, result.delete_nics[0].network_id)
        mock_driver.get_port.assert_called_once_with(VRRP_PORT_ID)
        mock_driver.get_subnet.assert_called_once_with(MEMBER_SUBNET_ID)
        mock_driver.get_plugged_networks.assert_called_once_with(COMPUTE_ID)

        # Test with vrrp_port_id
        mock_driver.reset_mock()

        result = calc_amp_delta.execute(lb_mock, amphora_mock, {},
                                        vrrp_port=vrrp_port_mock)

        self.assertEqual(AMPHORA_ID, result.amphora_id)
        self.assertEqual(COMPUTE_ID, result.compute_id)
        self.assertEqual(1, len(result.add_nics))
        self.assertEqual(MEMBER_NETWORK_ID, result.add_nics[0].network_id)
        self.assertEqual(1, len(result.delete_nics))
        self.assertEqual(DELETE_NETWORK_ID, result.delete_nics[0].network_id)
        mock_driver.get_port.assert_not_called()
        mock_driver.get_subnet.assert_called_once_with(MEMBER_SUBNET_ID)
        mock_driver.get_plugged_networks.assert_called_once_with(COMPUTE_ID)

    def test_calculate_delta(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        EMPTY = {}
        empty_deltas = {self.amphora_mock.id: data_models.Delta(
            amphora_id=self.amphora_mock.id,
            compute_id=self.amphora_mock.compute_id,
            add_nics=[],
            delete_nics=[])}

        calc_delta = network_tasks.CalculateDelta()

        self.assertEqual(EMPTY,
                         calc_delta.execute(self.load_balancer_mock, {}))

        # Test with one amp and no pools, nothing plugged
        # Delta should be empty
        mock_driver.reset_mock()

        self.amphora_mock.load_balancer = self.load_balancer_mock
        self.load_balancer_mock.amphorae = [self.amphora_mock]
        self.load_balancer_mock.pools = []

        self.assertEqual(empty_deltas,
                         calc_delta.execute(self.load_balancer_mock, {}))
        mock_driver.get_plugged_networks.assert_called_once_with(COMPUTE_ID)

        # Pool mock should be configured explicitly for each test
        pool_mock = mock.MagicMock()
        self.load_balancer_mock.pools = [pool_mock]

        # Test with one amp and one pool but no members, nothing plugged
        # Delta should be empty
        pool_mock.members = []
        self.assertEqual(empty_deltas,
                         calc_delta.execute(self.load_balancer_mock, {}))

        # Test with one amp and one pool and one member, nothing plugged
        # Delta should be one additional subnet to plug
        mock_driver.reset_mock()
        member_mock = mock.MagicMock()
        member_mock.subnet_id = 1
        pool_mock.members = [member_mock]
        mock_driver.get_subnet.return_value = data_models.Subnet(id=2,
                                                                 network_id=3)

        ndm = data_models.Delta(amphora_id=self.amphora_mock.id,
                                compute_id=self.amphora_mock.compute_id,
                                add_nics=[
                                    data_models.Interface(network_id=2)],
                                delete_nics=[])
        self.assertEqual({self.amphora_mock.id: ndm},
                         calc_delta.execute(self.load_balancer_mock, {}))

        vrrp_port_call = mock.call(self.amphora_mock.vrrp_port_id)
        mock_driver.get_port.assert_has_calls([vrrp_port_call])
        self.assertEqual(1, mock_driver.get_port.call_count)

        member_subnet_call = mock.call(member_mock.subnet_id)
        mock_driver.get_subnet.assert_has_calls([member_subnet_call])
        self.assertEqual(1, mock_driver.get_subnet.call_count)

        # Test with one amp and one pool and one member, already plugged
        # Delta should be empty
        mock_driver.reset_mock()
        member_mock = mock.MagicMock()
        member_mock.subnet_id = 1
        pool_mock.members = [member_mock]
        mock_driver.get_plugged_networks.return_value = [
            data_models.Interface(network_id=2)]

        self.assertEqual(empty_deltas,
                         calc_delta.execute(self.load_balancer_mock, {}))

        # Test with one amp and one pool and one member, wrong network plugged
        # Delta should be one network to add and one to remove
        mock_driver.reset_mock()
        member_mock = mock.MagicMock()
        member_mock.subnet_id = 1
        pool_mock.members = [member_mock]
        mock_driver.get_plugged_networks.return_value = [
            data_models.Interface(network_id=3)]

        ndm = data_models.Delta(amphora_id=self.amphora_mock.id,
                                compute_id=self.amphora_mock.compute_id,
                                add_nics=[
                                    data_models.Interface(network_id=2)],
                                delete_nics=[
                                    data_models.Interface(network_id=3)])
        self.assertEqual({self.amphora_mock.id: ndm},
                         calc_delta.execute(self.load_balancer_mock, {}))

        # Test with one amp and one pool and no members, one network plugged
        # Delta should be one network to remove
        mock_driver.reset_mock()
        pool_mock.members = []
        mock_driver.get_plugged_networks.return_value = [
            data_models.Interface(network_id=2)]

        ndm = data_models.Delta(amphora_id=self.amphora_mock.id,
                                compute_id=self.amphora_mock.compute_id,
                                add_nics=[],
                                delete_nics=[
                                    data_models.Interface(network_id=2)])
        self.assertEqual({self.amphora_mock.id: ndm},
                         calc_delta.execute(self.load_balancer_mock, {}))

    def test_get_plumbed_networks(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        mock_driver.get_plugged_networks.side_effect = [['blah']]
        net = network_tasks.GetPlumbedNetworks()

        self.assertEqual(['blah'], net.execute(self.amphora_mock))
        mock_driver.get_plugged_networks.assert_called_once_with(
            COMPUTE_ID)

    def test_plug_networks(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver

        def _interface(network_id):
            return [data_models.Interface(network_id=network_id)]

        net = network_tasks.PlugNetworks()

        net.execute(self.amphora_mock, None)
        self.assertFalse(mock_driver.plug_network.called)

        delta = data_models.Delta(amphora_id=self.amphora_mock.id,
                                  compute_id=self.amphora_mock.compute_id,
                                  add_nics=[],
                                  delete_nics=[])
        net.execute(self.amphora_mock, delta)
        self.assertFalse(mock_driver.plug_network.called)

        delta = data_models.Delta(amphora_id=self.amphora_mock.id,
                                  compute_id=self.amphora_mock.compute_id,
                                  add_nics=_interface(1),
                                  delete_nics=[])
        net.execute(self.amphora_mock, delta)
        mock_driver.plug_network.assert_called_once_with(COMPUTE_ID, 1)

        # revert
        net.revert(self.amphora_mock, None)
        self.assertFalse(mock_driver.unplug_network.called)

        delta = data_models.Delta(amphora_id=self.amphora_mock.id,
                                  compute_id=self.amphora_mock.compute_id,
                                  add_nics=[],
                                  delete_nics=[])
        net.revert(self.amphora_mock, delta)
        self.assertFalse(mock_driver.unplug_network.called)

        delta = data_models.Delta(amphora_id=self.amphora_mock.id,
                                  compute_id=self.amphora_mock.compute_id,
                                  add_nics=_interface(1),
                                  delete_nics=[])
        net.revert(self.amphora_mock, delta)
        mock_driver.unplug_network.assert_called_once_with(COMPUTE_ID, 1)

        mock_driver.reset_mock()
        mock_driver.unplug_network.side_effect = net_base.NetworkNotFound
        net.revert(self.amphora_mock, delta)  # No exception
        mock_driver.unplug_network.assert_called_once_with(COMPUTE_ID, 1)

        mock_driver.reset_mock()
        mock_driver.unplug_network.side_effect = TestException('test')
        self.assertRaises(TestException,
                          net.revert,
                          self.amphora_mock,
                          delta)
        mock_driver.unplug_network.assert_called_once_with(COMPUTE_ID, 1)

    def test_unplug_networks(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver

        def _interface(network_id):
            return [data_models.Interface(network_id=network_id)]

        net = network_tasks.UnPlugNetworks()

        net.execute(self.amphora_mock, None)
        self.assertFalse(mock_driver.unplug_network.called)

        delta = data_models.Delta(amphora_id=self.amphora_mock.id,
                                  compute_id=self.amphora_mock.compute_id,
                                  add_nics=[],
                                  delete_nics=[])
        net.execute(self.amphora_mock, delta)
        self.assertFalse(mock_driver.unplug_network.called)

        delta = data_models.Delta(amphora_id=self.amphora_mock.id,
                                  compute_id=self.amphora_mock.compute_id,
                                  add_nics=[],
                                  delete_nics=_interface(1))
        net.execute(self.amphora_mock, delta)
        mock_driver.unplug_network.assert_called_once_with(COMPUTE_ID, 1)

        mock_driver.reset_mock()
        mock_driver.unplug_network.side_effect = net_base.NetworkNotFound
        net.execute(self.amphora_mock, delta)  # No exception
        mock_driver.unplug_network.assert_called_once_with(COMPUTE_ID, 1)

        # Do a test with a general exception in case behavior changes
        mock_driver.reset_mock()
        mock_driver.unplug_network.side_effect = Exception()
        net.execute(self.amphora_mock, delta)  # No exception
        mock_driver.unplug_network.assert_called_once_with(COMPUTE_ID, 1)

    def test_get_member_ports(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver

        def _interface(port_id):
            return [data_models.Interface(port_id=port_id)]

        net_task = network_tasks.GetMemberPorts()
        net_task.execute(LB, self.amphora_mock)
        mock_driver.get_port.assert_called_once_with(t_constants.MOCK_PORT_ID)
        mock_driver.get_plugged_networks.assert_called_once_with(COMPUTE_ID)

        mock_driver.reset_mock()
        net_task = network_tasks.GetMemberPorts()
        mock_driver.get_plugged_networks.return_value = _interface(1)
        mock_driver.get_port.side_effect = [
            data_models.Port(network_id=NETWORK_ID),
            data_models.Port(network_id=NETWORK_ID)]
        net_task.execute(self.load_balancer_mock, self.amphora_mock)
        self.assertEqual(2, mock_driver.get_port.call_count)
        self.assertFalse(mock_driver.get_network.called)

        mock_driver.reset_mock()
        port_mock = mock.MagicMock()
        fixed_ip_mock = mock.MagicMock()
        fixed_ip_mock.subnet_id = 1
        port_mock.fixed_ips = [fixed_ip_mock]
        net_task = network_tasks.GetMemberPorts()
        mock_driver.get_plugged_networks.return_value = _interface(1)
        mock_driver.get_port.side_effect = [
            data_models.Port(network_id=NETWORK_ID), port_mock]
        ports = net_task.execute(self.load_balancer_mock, self.amphora_mock)
        mock_driver.get_subnet.assert_called_once_with(1)
        self.assertEqual([port_mock], ports)

    def test_handle_network_delta(self, mock_get_net_driver):
        mock_net_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_net_driver

        nic1 = mock.MagicMock()
        nic1.network_id = uuidutils.generate_uuid()
        nic2 = mock.MagicMock()
        nic2.network_id = uuidutils.generate_uuid()
        interface1 = mock.MagicMock()
        interface1.port_id = uuidutils.generate_uuid()
        port1 = mock.MagicMock()
        port1.network_id = uuidutils.generate_uuid()
        fixed_ip = mock.MagicMock()
        fixed_ip.subnet_id = uuidutils.generate_uuid()
        port1.fixed_ips = [fixed_ip]
        subnet = mock.MagicMock()
        network = mock.MagicMock()

        delta = data_models.Delta(amphora_id=self.amphora_mock.id,
                                  compute_id=self.amphora_mock.compute_id,
                                  add_nics=[nic1],
                                  delete_nics=[nic2, nic2, nic2])

        mock_net_driver.plug_network.return_value = interface1
        mock_net_driver.get_port.return_value = port1
        mock_net_driver.get_network.return_value = network
        mock_net_driver.get_subnet.return_value = subnet

        mock_net_driver.unplug_network.side_effect = [
            None, net_base.NetworkNotFound, Exception]

        handle_net_delta_obj = network_tasks.HandleNetworkDelta()
        result = handle_net_delta_obj.execute(self.amphora_mock, delta)

        mock_net_driver.plug_network.assert_called_once_with(
            self.amphora_mock.compute_id, nic1.network_id)
        mock_net_driver.get_port.assert_called_once_with(interface1.port_id)
        mock_net_driver.get_network.assert_called_once_with(port1.network_id)
        mock_net_driver.get_subnet.assert_called_once_with(fixed_ip.subnet_id)

        self.assertEqual({self.amphora_mock.id: [port1]}, result)

        mock_net_driver.unplug_network.assert_called_with(
            self.amphora_mock.compute_id, nic2.network_id)

        # Revert
        delta2 = data_models.Delta(amphora_id=self.amphora_mock.id,
                                   compute_id=self.amphora_mock.compute_id,
                                   add_nics=[nic1, nic1],
                                   delete_nics=[nic2, nic2, nic2])

        mock_net_driver.unplug_network.reset_mock()
        handle_net_delta_obj.revert(
            failure.Failure.from_exception(Exception('boom')), None, None)
        mock_net_driver.unplug_network.assert_not_called()

        mock_net_driver.unplug_network.reset_mock()
        handle_net_delta_obj.revert(None, None, None)
        mock_net_driver.unplug_network.assert_not_called()

        mock_net_driver.unplug_network.reset_mock()
        handle_net_delta_obj.revert(None, None, delta2)

    def test_handle_network_deltas(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver

        def _interface(network_id):
            return [data_models.Interface(network_id=network_id)]

        net = network_tasks.HandleNetworkDeltas()

        net.execute({})
        self.assertFalse(mock_driver.plug_network.called)

        delta = data_models.Delta(amphora_id=self.amphora_mock.id,
                                  compute_id=self.amphora_mock.compute_id,
                                  add_nics=[],
                                  delete_nics=[])
        net.execute({self.amphora_mock.id: delta})
        self.assertFalse(mock_driver.plug_network.called)

        delta = data_models.Delta(amphora_id=self.amphora_mock.id,
                                  compute_id=self.amphora_mock.compute_id,
                                  add_nics=_interface(1),
                                  delete_nics=[])
        net.execute({self.amphora_mock.id: delta})
        mock_driver.plug_network.assert_called_once_with(COMPUTE_ID, 1)

        # revert
        net.execute({self.amphora_mock.id: delta})
        self.assertFalse(mock_driver.unplug_network.called)

        delta = data_models.Delta(amphora_id=self.amphora_mock.id,
                                  compute_id=self.amphora_mock.compute_id,
                                  add_nics=[],
                                  delete_nics=[])
        net.execute({self.amphora_mock.id: delta})
        self.assertFalse(mock_driver.unplug_network.called)

        delta = data_models.Delta(amphora_id=self.amphora_mock.id,
                                  compute_id=self.amphora_mock.compute_id,
                                  add_nics=_interface(1),
                                  delete_nics=[])

        mock_driver.reset_mock()
        mock_driver.unplug_network.side_effect = net_base.NetworkNotFound

        mock_driver.reset_mock()
        mock_driver.unplug_network.side_effect = TestException('test')
        self.assertRaises(TestException, net.revert, mock.ANY,
                          {self.amphora_mock.id: delta})
        mock_driver.unplug_network.assert_called_once_with(COMPUTE_ID, 1)

        mock_driver.reset_mock()
        net.execute({})
        self.assertFalse(mock_driver.unplug_network.called)

        delta = data_models.Delta(amphora_id=self.amphora_mock.id,
                                  compute_id=self.amphora_mock.compute_id,
                                  add_nics=[],
                                  delete_nics=[])
        net.execute({self.amphora_mock.id: delta})
        self.assertFalse(mock_driver.unplug_network.called)

        delta = data_models.Delta(amphora_id=self.amphora_mock.id,
                                  compute_id=self.amphora_mock.compute_id,
                                  add_nics=[],
                                  delete_nics=_interface(1))
        net.execute({self.amphora_mock.id: delta})
        mock_driver.unplug_network.assert_called_once_with(COMPUTE_ID, 1)

        mock_driver.reset_mock()
        mock_driver.unplug_network.side_effect = net_base.NetworkNotFound
        net.execute({self.amphora_mock.id: delta})
        mock_driver.unplug_network.assert_called_once_with(COMPUTE_ID, 1)

        # Do a test with a general exception in case behavior changes
        mock_driver.reset_mock()
        mock_driver.unplug_network.side_effect = Exception()
        net.execute({self.amphora_mock.id: delta})
        mock_driver.unplug_network.assert_called_once_with(COMPUTE_ID, 1)

    def test_plug_vip(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.PlugVIP()

        mock_driver.plug_vip.return_value = ["vip"]

        data = net.execute(LB)
        mock_driver.plug_vip.assert_called_once_with(LB, LB.vip)
        self.assertEqual(["vip"], data)

        # revert
        net.revert(["vip"], LB)
        mock_driver.unplug_vip.assert_called_once_with(LB, LB.vip)

        # revert with exception
        mock_driver.reset_mock()
        mock_driver.unplug_vip.side_effect = Exception('UnplugVipException')
        net.revert(["vip"], LB)
        mock_driver.unplug_vip.assert_called_once_with(LB, LB.vip)

    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'get_current_loadbalancer_from_db')
    def test_apply_qos_on_creation(self, mock_get_lb_db, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.ApplyQos()
        mock_get_lb_db.return_value = LB

        # execute
        UPDATE_DICT[constants.TOPOLOGY] = constants.TOPOLOGY_SINGLE
        update_dict = UPDATE_DICT
        net.execute(LB, [AMPS_DATA[0]], update_dict)
        mock_driver.apply_qos_on_port.assert_called_once_with(
            VIP.qos_policy_id, AMPS_DATA[0].vrrp_port_id)
        self.assertEqual(1, mock_driver.apply_qos_on_port.call_count)
        standby_topology = constants.TOPOLOGY_ACTIVE_STANDBY
        mock_driver.reset_mock()
        update_dict[constants.TOPOLOGY] = standby_topology
        net.execute(LB, AMPS_DATA, update_dict)
        mock_driver.apply_qos_on_port.assert_called_with(
            t_constants.MOCK_QOS_POLICY_ID1, mock.ANY)
        self.assertEqual(2, mock_driver.apply_qos_on_port.call_count)

        # revert
        mock_driver.reset_mock()
        update_dict = UPDATE_DICT
        net.revert(None, LB, [AMPS_DATA[0]], update_dict)
        self.assertEqual(0, mock_driver.apply_qos_on_port.call_count)
        mock_driver.reset_mock()
        update_dict[constants.TOPOLOGY] = standby_topology
        net.revert(None, LB, AMPS_DATA, update_dict)
        self.assertEqual(0, mock_driver.apply_qos_on_port.call_count)

    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'get_current_loadbalancer_from_db')
    def test_apply_qos_on_update(self, mock_get_lb_db, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.ApplyQos()
        null_qos_vip = o_data_models.Vip(qos_policy_id=None)
        null_qos_lb = o_data_models.LoadBalancer(
            vip=null_qos_vip, topology=constants.TOPOLOGY_SINGLE,
            amphorae=[AMPS_DATA[0]])

        tmp_vip_object = o_data_models.Vip(
            qos_policy_id=t_constants.MOCK_QOS_POLICY_ID1)
        tmp_lb = o_data_models.LoadBalancer(
            vip=tmp_vip_object, topology=constants.TOPOLOGY_SINGLE,
            amphorae=[AMPS_DATA[0]])

        # execute
        update_dict = {'description': 'fool'}
        net.execute(tmp_lb, update_dict=update_dict)
        mock_driver.apply_qos_on_port.assert_called_once_with(
            t_constants.MOCK_QOS_POLICY_ID1, AMPS_DATA[0].vrrp_port_id)
        self.assertEqual(1, mock_driver.apply_qos_on_port.call_count)

        mock_driver.reset_mock()
        update_dict = {'vip': {'qos_policy_id': None}}
        net.execute(null_qos_lb, update_dict=update_dict)
        mock_driver.apply_qos_on_port.assert_called_once_with(
            None, AMPS_DATA[0].vrrp_port_id)
        self.assertEqual(1, mock_driver.apply_qos_on_port.call_count)

        mock_driver.reset_mock()
        update_dict = {'name': '123'}
        net.execute(null_qos_lb, update_dict=update_dict)
        self.assertEqual(0, mock_driver.apply_qos_on_port.call_count)

        mock_driver.reset_mock()
        update_dict = {'description': 'fool'}
        tmp_lb.amphorae = AMPS_DATA
        tmp_lb.topology = constants.TOPOLOGY_ACTIVE_STANDBY
        net.execute(tmp_lb, update_dict=update_dict)
        mock_driver.apply_qos_on_port.assert_called_with(
            t_constants.MOCK_QOS_POLICY_ID1, mock.ANY)
        self.assertEqual(2, mock_driver.apply_qos_on_port.call_count)

        mock_driver.reset_mock()
        update_dict = {'description': 'fool',
                       'vip': {
                           'qos_policy_id': t_constants.MOCK_QOS_POLICY_ID1}}
        tmp_lb.amphorae = AMPS_DATA
        tmp_lb.topology = constants.TOPOLOGY_ACTIVE_STANDBY
        net.execute(tmp_lb, update_dict=update_dict)
        mock_driver.apply_qos_on_port.assert_called_with(
            t_constants.MOCK_QOS_POLICY_ID1, mock.ANY)
        self.assertEqual(2, mock_driver.apply_qos_on_port.call_count)

        mock_driver.reset_mock()
        update_dict = {}
        net.execute(null_qos_lb, update_dict=update_dict)
        self.assertEqual(0, mock_driver.apply_qos_on_port.call_count)

        # revert
        mock_driver.reset_mock()
        tmp_lb.amphorae = [AMPS_DATA[0]]
        tmp_lb.topology = constants.TOPOLOGY_SINGLE
        update_dict = {'description': 'fool'}
        mock_get_lb_db.return_value = tmp_lb
        net.revert(None, tmp_lb, update_dict=update_dict)
        self.assertEqual(0, mock_driver.apply_qos_on_port.call_count)

        mock_driver.reset_mock()
        update_dict = {'vip': {'qos_policy_id': None}}
        ori_lb_db = LB2
        ori_lb_db.amphorae = [AMPS_DATA[0]]
        mock_get_lb_db.return_value = ori_lb_db
        net.revert(None, null_qos_lb, update_dict=update_dict)
        mock_driver.apply_qos_on_port.assert_called_once_with(
            t_constants.MOCK_QOS_POLICY_ID2, AMPS_DATA[0].vrrp_port_id)
        self.assertEqual(1, mock_driver.apply_qos_on_port.call_count)

        mock_driver.reset_mock()
        update_dict = {'vip': {
            'qos_policy_id': t_constants.MOCK_QOS_POLICY_ID2}}
        tmp_lb.amphorae = AMPS_DATA
        tmp_lb.topology = constants.TOPOLOGY_ACTIVE_STANDBY
        ori_lb_db = LB2
        ori_lb_db.amphorae = [AMPS_DATA[0]]
        mock_get_lb_db.return_value = ori_lb_db
        net.revert(None, tmp_lb, update_dict=update_dict)
        mock_driver.apply_qos_on_port.assert_called_with(
            t_constants.MOCK_QOS_POLICY_ID2, mock.ANY)
        self.assertEqual(2, mock_driver.apply_qos_on_port.call_count)

    def test_unplug_vip(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.UnplugVIP()

        net.execute(LB)
        mock_driver.unplug_vip.assert_called_once_with(LB, LB.vip)

    def test_allocate_vip(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.AllocateVIP()

        mock_driver.allocate_vip.return_value = LB.vip

        mock_driver.reset_mock()
        self.assertEqual(LB.vip, net.execute(LB))
        mock_driver.allocate_vip.assert_called_once_with(LB)

        # revert
        vip_mock = mock.MagicMock()
        net.revert(vip_mock, LB)
        mock_driver.deallocate_vip.assert_called_once_with(vip_mock)

        # revert exception
        mock_driver.reset_mock()
        mock_driver.deallocate_vip.side_effect = Exception('DeallVipException')
        vip_mock = mock.MagicMock()
        net.revert(vip_mock, LB)
        mock_driver.deallocate_vip.assert_called_once_with(vip_mock)

    def test_allocate_vip_for_failover(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.AllocateVIPforFailover()

        mock_driver.allocate_vip.return_value = LB.vip

        mock_driver.reset_mock()
        self.assertEqual(LB.vip, net.execute(LB))
        mock_driver.allocate_vip.assert_called_once_with(LB)

        # revert
        vip_mock = mock.MagicMock()
        net.revert(vip_mock, LB)
        mock_driver.deallocate_vip.assert_not_called()

    def test_deallocate_vip(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.DeallocateVIP()
        vip = o_data_models.Vip()
        lb = o_data_models.LoadBalancer(vip=vip)
        net.execute(lb)
        mock_driver.deallocate_vip.assert_called_once_with(lb.vip)

    def test_update_vip(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        vip = o_data_models.Vip()
        lb = o_data_models.LoadBalancer(vip=vip)
        net_task = network_tasks.UpdateVIP()
        net_task.execute(lb)
        mock_driver.update_vip.assert_called_once_with(lb)

    def test_update_vip_for_delete(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        vip = o_data_models.Vip()
        lb = o_data_models.LoadBalancer(vip=vip)
        net_task = network_tasks.UpdateVIPForDelete()
        net_task.execute(lb)
        mock_driver.update_vip.assert_called_once_with(lb, for_delete=True)

    @mock.patch('octavia.db.api.get_session', return_value='TEST')
    @mock.patch('octavia.db.repositories.AmphoraRepository.get')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_get_amphora_network_configs_by_id(
            self, mock_lb_get, mock_amp_get,
            mock_get_session, mock_get_net_driver):
        LB_ID = uuidutils.generate_uuid()
        AMP_ID = uuidutils.generate_uuid()
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        mock_amp_get.return_value = 'mock amphora'
        mock_lb_get.return_value = 'mock load balancer'

        net_task = network_tasks.GetAmphoraNetworkConfigsByID()

        net_task.execute(LB_ID, AMP_ID)

        mock_driver.get_network_configs.assert_called_once_with(
            'mock load balancer', amphora='mock amphora')
        mock_amp_get.assert_called_once_with('TEST', id=AMP_ID)
        mock_lb_get.assert_called_once_with('TEST', id=LB_ID)

    @mock.patch('octavia.db.api.get_session', return_value='TEST')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_get_amphorae_network_configs(self, mock_lb_get, mock_get_session,
                                          mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        lb = o_data_models.LoadBalancer()
        mock_lb_get.return_value = lb
        net_task = network_tasks.GetAmphoraeNetworkConfigs()
        net_task.execute(lb.id)
        mock_lb_get.assert_called_once_with('TEST', id=lb.id)
        mock_driver.get_network_configs.assert_called_once_with(lb)

    def test_failover_preparation_for_amphora(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        failover = network_tasks.FailoverPreparationForAmphora()
        amphora = o_data_models.Amphora(id=AMPHORA_ID,
                                        lb_network_ip=IP_ADDRESS)
        failover.execute(amphora)
        mock_driver.failover_preparation.assert_called_once_with(amphora)

    def test_retrieve_portids_on_amphora_except_lb_network(
            self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver

        def _interface(port_id):
            return [data_models.Interface(port_id=port_id)]

        net_task = network_tasks.RetrievePortIDsOnAmphoraExceptLBNetwork()
        amphora = o_data_models.Amphora(id=AMPHORA_ID, compute_id=COMPUTE_ID,
                                        lb_network_ip=IP_ADDRESS)

        mock_driver.get_plugged_networks.return_value = []
        net_task.execute(amphora)
        mock_driver.get_plugged_networks.assert_called_once_with(
            compute_id=COMPUTE_ID)
        self.assertFalse(mock_driver.get_port.called)

        mock_driver.reset_mock()
        net_task = network_tasks.RetrievePortIDsOnAmphoraExceptLBNetwork()
        mock_driver.get_plugged_networks.return_value = _interface(1)
        net_task.execute(amphora)
        mock_driver.get_port.assert_called_once_with(port_id=1)

        mock_driver.reset_mock()
        net_task = network_tasks.RetrievePortIDsOnAmphoraExceptLBNetwork()
        port_mock = mock.MagicMock()
        fixed_ip_mock = mock.MagicMock()
        fixed_ip_mock.ip_address = IP_ADDRESS
        port_mock.fixed_ips = [fixed_ip_mock]
        mock_driver.get_plugged_networks.return_value = _interface(1)
        mock_driver.get_port.return_value = port_mock
        ports = net_task.execute(amphora)
        self.assertEqual([], ports)

        mock_driver.reset_mock()
        net_task = network_tasks.RetrievePortIDsOnAmphoraExceptLBNetwork()
        port_mock = mock.MagicMock()
        fixed_ip_mock = mock.MagicMock()
        fixed_ip_mock.ip_address = "172.17.17.17"
        port_mock.fixed_ips = [fixed_ip_mock]
        mock_driver.get_plugged_networks.return_value = _interface(1)
        mock_driver.get_port.return_value = port_mock
        ports = net_task.execute(amphora)
        self.assertEqual(1, len(ports))

    def test_plug_ports(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver

        amphora = mock.MagicMock()
        port1 = mock.MagicMock()
        port2 = mock.MagicMock()

        plugports = network_tasks.PlugPorts()
        plugports.execute(amphora, [port1, port2])

        mock_driver.plug_port.assert_any_call(amphora, port1)
        mock_driver.plug_port.assert_any_call(amphora, port2)

    @mock.patch('octavia.db.api.get_session', return_value='TEST')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_update_vip_sg(self, mock_lb_get, mock_get_session,
                           mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_driver.update_vip_sg.return_value = SG_ID
        mock_get_net_driver.return_value = mock_driver
        mock_lb_get.return_value = self.load_balancer_mock
        net = network_tasks.UpdateVIPSecurityGroup()

        sg_id = net.execute(self.load_balancer_mock.id)
        mock_lb_get.assert_called_once_with('TEST',
                                            id=self.load_balancer_mock.id)
        mock_driver.update_vip_sg.assert_called_once_with(
            self.load_balancer_mock, self.load_balancer_mock.vip)
        self.assertEqual(sg_id, SG_ID)

    def test_get_subnet_from_vip(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.GetSubnetFromVIP()

        net.execute(LB)
        mock_driver.get_subnet.assert_called_once_with(LB.vip.subnet_id)

    def test_plug_vip_amphora(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.PlugVIPAmpphora()
        mockSubnet = mock.MagicMock()
        net.execute(LB, self.amphora_mock, mockSubnet)
        mock_driver.plug_aap_port.assert_called_once_with(
            LB, LB.vip, self.amphora_mock, mockSubnet)

    def test_revert_plug_vip_amphora(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.PlugVIPAmpphora()
        mockSubnet = mock.MagicMock()
        net.revert(AMPS_DATA[0], LB, self.amphora_mock, mockSubnet)
        mock_driver.unplug_aap_port.assert_called_once_with(
            LB.vip, self.amphora_mock, mockSubnet)

    @mock.patch('octavia.controller.worker.v1.tasks.network_tasks.DeletePort.'
                'update_progress')
    def test_delete_port(self, mock_update_progress, mock_get_net_driver):
        PORT_ID = uuidutils.generate_uuid()
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        mock_driver.delete_port.side_effect = [
            mock.DEFAULT, exceptions.OctaviaException('boom'), mock.DEFAULT,
            exceptions.OctaviaException('boom'),
            exceptions.OctaviaException('boom'),
            exceptions.OctaviaException('boom'),
            exceptions.OctaviaException('boom'),
            exceptions.OctaviaException('boom'),
            exceptions.OctaviaException('boom')]
        mock_driver.admin_down_port.side_effect = [
            mock.DEFAULT, exceptions.OctaviaException('boom')]

        net_task = network_tasks.DeletePort()

        # Limit the retry attempts for the test run to save time
        net_task.execute.retry.stop = tenacity.stop_after_attempt(2)

        # Test port ID is None (no-op)
        net_task.execute(None)

        mock_update_progress.assert_not_called()
        mock_driver.delete_port.assert_not_called()

        # Test successful delete
        mock_update_progress.reset_mock()
        mock_driver.reset_mock()

        net_task.execute(PORT_ID)

        mock_update_progress.assert_called_once_with(0.5)
        mock_driver.delete_port.assert_called_once_with(PORT_ID)

        # Test exception and successful retry
        mock_update_progress.reset_mock()
        mock_driver.reset_mock()

        net_task.execute(PORT_ID)

        mock_update_progress.assert_has_calls([mock.call(0.5), mock.call(1.0)])
        mock_driver.delete_port.assert_has_calls([mock.call(PORT_ID),
                                                  mock.call(PORT_ID)])

        # Test passive failure
        mock_update_progress.reset_mock()
        mock_driver.reset_mock()

        net_task.execute(PORT_ID, passive_failure=True)

        mock_update_progress.assert_has_calls([mock.call(0.5), mock.call(1.0)])
        mock_driver.delete_port.assert_has_calls([mock.call(PORT_ID),
                                                  mock.call(PORT_ID)])
        mock_driver.admin_down_port.assert_called_once_with(PORT_ID)

        # Test passive failure admin down failure
        mock_update_progress.reset_mock()
        mock_driver.reset_mock()
        mock_driver.admin_down_port.reset_mock()

        net_task.execute(PORT_ID, passive_failure=True)

        mock_update_progress.assert_has_calls([mock.call(0.5), mock.call(1.0)])
        mock_driver.delete_port.assert_has_calls([mock.call(PORT_ID),
                                                  mock.call(PORT_ID)])
        mock_driver.admin_down_port.assert_called_once_with(PORT_ID)

        # Test non-passive failure
        mock_update_progress.reset_mock()
        mock_driver.reset_mock()
        mock_driver.admin_down_port.reset_mock()

        mock_driver.admin_down_port.side_effect = [
            exceptions.OctaviaException('boom')]

        self.assertRaises(exceptions.OctaviaException, net_task.execute,
                          PORT_ID)

        mock_update_progress.assert_has_calls([mock.call(0.5), mock.call(1.0)])
        mock_driver.delete_port.assert_has_calls([mock.call(PORT_ID),
                                                  mock.call(PORT_ID)])
        mock_driver.admin_down_port.assert_not_called()

    def test_create_vip_base_port(self, mock_get_net_driver):
        AMP_ID = uuidutils.generate_uuid()
        PORT_ID = uuidutils.generate_uuid()
        VIP_NETWORK_ID = uuidutils.generate_uuid()
        VIP_QOS_ID = uuidutils.generate_uuid()
        VIP_SG_ID = uuidutils.generate_uuid()
        VIP_SUBNET_ID = uuidutils.generate_uuid()
        VIP_IP_ADDRESS = '203.0.113.81'
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        vip_mock = mock.MagicMock()
        vip_mock.ip_address = VIP_IP_ADDRESS
        vip_mock.network_id = VIP_NETWORK_ID
        vip_mock.qos_policy_id = VIP_QOS_ID
        vip_mock.subnet_id = VIP_SUBNET_ID
        port_mock = mock.MagicMock()
        port_mock.id = PORT_ID

        mock_driver.create_port.side_effect = [
            port_mock, exceptions.OctaviaException('boom'),
            exceptions.OctaviaException('boom'),
            exceptions.OctaviaException('boom')]
        mock_driver.delete_port.side_effect = [mock.DEFAULT, Exception('boom')]

        net_task = network_tasks.CreateVIPBasePort()

        # Limit the retry attempts for the test run to save time
        net_task.execute.retry.stop = tenacity.stop_after_attempt(2)

        # Test execute
        result = net_task.execute(vip_mock, VIP_SG_ID, AMP_ID)

        self.assertEqual(port_mock, result)
        mock_driver.create_port.assert_called_once_with(
            VIP_NETWORK_ID, name=constants.AMP_BASE_PORT_PREFIX + AMP_ID,
            fixed_ips=[{constants.SUBNET_ID: VIP_SUBNET_ID}],
            secondary_ips=[VIP_IP_ADDRESS], security_group_ids=[VIP_SG_ID],
            qos_policy_id=VIP_QOS_ID)

        # Test execute exception
        mock_driver.reset_mock()

        self.assertRaises(exceptions.OctaviaException, net_task.execute,
                          vip_mock, None, AMP_ID)

        # Test revert when this task failed
        mock_driver.reset_mock()

        net_task.revert(failure.Failure.from_exception(Exception('boom')),
                        vip_mock, VIP_SG_ID, AMP_ID)

        mock_driver.delete_port.assert_not_called()

        # Test revert
        mock_driver.reset_mock()

        net_task.revert([port_mock], vip_mock, VIP_SG_ID, AMP_ID)

        mock_driver.delete_port.assert_called_once_with(PORT_ID)

        # Test revert exception
        mock_driver.reset_mock()

        net_task.revert([port_mock], vip_mock, VIP_SG_ID, AMP_ID)

        mock_driver.delete_port.assert_called_once_with(PORT_ID)

    @mock.patch('time.sleep')
    def test_admin_down_port(self, mock_sleep, mock_get_net_driver):
        PORT_ID = uuidutils.generate_uuid()
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        port_down_mock = mock.MagicMock()
        port_down_mock.status = constants.DOWN
        port_up_mock = mock.MagicMock()
        port_up_mock.status = constants.UP
        mock_driver.set_port_admin_state_up.side_effect = [
            mock.DEFAULT, net_base.PortNotFound, mock.DEFAULT, mock.DEFAULT,
            Exception('boom')]
        mock_driver.get_port.side_effect = [port_down_mock, port_up_mock]

        net_task = network_tasks.AdminDownPort()

        # Test execute
        net_task.execute(PORT_ID)

        mock_driver.set_port_admin_state_up.assert_called_once_with(PORT_ID,
                                                                    False)
        mock_driver.get_port.assert_called_once_with(PORT_ID)

        # Test passive fail on port not found
        mock_driver.reset_mock()

        net_task.execute(PORT_ID)

        mock_driver.set_port_admin_state_up.assert_called_once_with(PORT_ID,
                                                                    False)
        mock_driver.get_port.assert_not_called()

        # Test passive fail on port stays up
        mock_driver.reset_mock()

        net_task.execute(PORT_ID)

        mock_driver.set_port_admin_state_up.assert_called_once_with(PORT_ID,
                                                                    False)
        mock_driver.get_port.assert_called_once_with(PORT_ID)

        # Test revert when this task failed
        mock_driver.reset_mock()

        net_task.revert(failure.Failure.from_exception(Exception('boom')),
                        PORT_ID)

        mock_driver.set_port_admin_state_up.assert_not_called()

        # Test revert
        mock_driver.reset_mock()

        net_task.revert(None, PORT_ID)

        mock_driver.set_port_admin_state_up.assert_called_once_with(PORT_ID,
                                                                    True)

        # Test revert exception passive failure
        mock_driver.reset_mock()

        net_task.revert(None, PORT_ID)

        mock_driver.set_port_admin_state_up.assert_called_once_with(PORT_ID,
                                                                    True)

    @mock.patch('octavia.common.utils.get_vip_security_group_name')
    def test_get_vip_security_group_id(self, mock_get_sg_name,
                                       mock_get_net_driver):
        LB_ID = uuidutils.generate_uuid()
        SG_ID = uuidutils.generate_uuid()
        SG_NAME = 'fake_SG_name'
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        mock_get_sg_name.return_value = SG_NAME
        sg_mock = mock.MagicMock()
        sg_mock.id = SG_ID
        mock_driver.get_security_group.side_effect = [
            sg_mock, None, net_base.SecurityGroupNotFound,
            net_base.SecurityGroupNotFound]

        net_task = network_tasks.GetVIPSecurityGroupID()

        # Test execute
        result = net_task.execute(LB_ID)

        mock_driver.get_security_group.assert_called_once_with(SG_NAME)
        mock_get_sg_name.assert_called_once_with(LB_ID)

        # Test execute with empty get subnet response
        mock_driver.reset_mock()
        mock_get_sg_name.reset_mock()

        result = net_task.execute(LB_ID)

        self.assertIsNone(result)
        mock_get_sg_name.assert_called_once_with(LB_ID)

        # Test execute no security group found, security groups enabled
        mock_driver.reset_mock()
        mock_get_sg_name.reset_mock()
        mock_driver.sec_grp_enabled = True

        self.assertRaises(net_base.SecurityGroupNotFound, net_task.execute,
                          LB_ID)
        mock_driver.get_security_group.assert_called_once_with(SG_NAME)
        mock_get_sg_name.assert_called_once_with(LB_ID)

        # Test execute no security group found, security groups disabled
        mock_driver.reset_mock()
        mock_get_sg_name.reset_mock()
        mock_driver.sec_grp_enabled = False

        result = net_task.execute(LB_ID)

        self.assertIsNone(result)
        mock_driver.get_security_group.assert_called_once_with(SG_NAME)
        mock_get_sg_name.assert_called_once_with(LB_ID)
