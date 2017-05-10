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
#

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.common import constants
from octavia.common import data_models as o_data_models
from octavia.controller.worker.tasks import network_tasks
from octavia.network import base as net_base
from octavia.network import data_models
import octavia.tests.unit.base as base


AMPHORA_ID = 7
COMPUTE_ID = uuidutils.generate_uuid()
PORT_ID = uuidutils.generate_uuid()
SUBNET_ID = uuidutils.generate_uuid()
NETWORK_ID = uuidutils.generate_uuid()
IP_ADDRESS = "172.24.41.1"
VIP = o_data_models.Vip(port_id=PORT_ID, subnet_id=SUBNET_ID,
                        ip_address=IP_ADDRESS)
LB = o_data_models.LoadBalancer(vip=VIP)
FIRST_IP = {"ip_address": IP_ADDRESS, "subnet_id": SUBNET_ID}
FIXED_IPS = [FIRST_IP]
INTERFACE = data_models.Interface(id=uuidutils.generate_uuid(),
                                  compute_id=COMPUTE_ID, fixed_ips=FIXED_IPS,
                                  port_id=PORT_ID)


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
        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="controller_worker", amp_boot_network_list=['netid'])

        super(TestNetworkTasks, self).setUp()

    def test_calculate_delta(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        EMPTY = {}
        empty_deltas = {self.amphora_mock.id: data_models.Delta(
            amphora_id=self.amphora_mock.id,
            compute_id=self.amphora_mock.compute_id,
            add_nics=[],
            delete_nics=[])}

        def _interface(network_id):
            return [data_models.Interface(network_id=network_id)]

        net = network_tasks.CalculateDelta()

        self.assertEqual(EMPTY, net.execute(self.load_balancer_mock))

        self.amphora_mock.load_balancer = self.load_balancer_mock
        self.load_balancer_mock.amphorae = [self.amphora_mock]
        self.load_balancer_mock.pools = []

        self.assertEqual(empty_deltas, net.execute(self.load_balancer_mock))
        mock_driver.get_plugged_networks.assert_called_once_with(COMPUTE_ID)

        pool_mock = mock.MagicMock()
        self.load_balancer_mock.pools = [pool_mock]
        pool_mock.members = []
        self.assertEqual(empty_deltas, net.execute(self.load_balancer_mock))

        member_mock = mock.MagicMock()
        pool_mock.members = [member_mock]
        member_mock.subnet_id = 1

        mock_driver.get_subnet.reset_mock()
        mock_driver.get_subnet.return_value = data_models.Subnet(id=2,
                                                                 network_id=3)

        ndm = data_models.Delta(amphora_id=self.amphora_mock.id,
                                compute_id=self.amphora_mock.compute_id,
                                add_nics=_interface(2),
                                delete_nics=[])
        self.assertEqual({self.amphora_mock.id: ndm},
                         net.execute(self.load_balancer_mock))

        vrrp_port_call = mock.call(self.amphora_mock.vrrp_port_id)
        mock_driver.get_port.assert_has_calls([vrrp_port_call])
        # For some reason we call calculate_delta three times?
        self.assertEqual(3, mock_driver.get_port.call_count)

        member_subnet_call = mock.call(member_mock.subnet_id)
        mock_driver.get_subnet.assert_has_calls([member_subnet_call])
        self.assertEqual(1, mock_driver.get_subnet.call_count)

        mock_driver.get_plugged_networks.return_value = _interface(2)
        self.assertEqual(empty_deltas, net.execute(self.load_balancer_mock))

        mock_driver.get_plugged_networks.return_value = _interface(3)
        ndm = data_models.Delta(amphora_id=self.amphora_mock.id,
                                compute_id=self.amphora_mock.compute_id,
                                add_nics=_interface(2),
                                delete_nics=_interface(3))
        self.assertEqual({self.amphora_mock.id: ndm},
                         net.execute(self.load_balancer_mock))

        pool_mock.members = []
        mock_driver.get_plugged_networks.return_value = _interface(2)
        ndm = data_models.Delta(amphora_id=self.amphora_mock.id,
                                compute_id=self.amphora_mock.compute_id,
                                add_nics=[],
                                delete_nics=_interface(2))
        self.assertEqual({self.amphora_mock.id: ndm},
                         net.execute(self.load_balancer_mock))

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
        mock_driver.get_port.assert_called_once_with(PORT_ID)
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

    def test_get_amphorae_network_configs(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        lb = o_data_models.LoadBalancer()
        net_task = network_tasks.GetAmphoraeNetworkConfigs()
        net_task.execute(lb)
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

    def test_plug_vip_port(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        vrrp_port = mock.MagicMock()

        amphorae_network_config = mock.MagicMock()
        amphorae_network_config.get().vrrp_port = vrrp_port

        plugvipport = network_tasks.PlugVIPPort()
        plugvipport.execute(self.amphora_mock, amphorae_network_config)
        mock_driver.plug_port.assert_any_call(self.amphora_mock, vrrp_port)

        # test revert
        plugvipport.revert(None, self.amphora_mock, amphorae_network_config)
        mock_driver.unplug_port.assert_any_call(self.amphora_mock, vrrp_port)

    def test_wait_for_port_detach(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver

        amphora = o_data_models.Amphora(id=AMPHORA_ID,
                                        lb_network_ip=IP_ADDRESS)

        waitforportdetach = network_tasks.WaitForPortDetach()
        waitforportdetach.execute(amphora)

        mock_driver.wait_for_port_detach.assert_called_once_with(amphora)
