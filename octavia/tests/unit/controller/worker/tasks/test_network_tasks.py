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

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils
import six

from octavia.common import data_models as o_data_models
from octavia.controller.worker.tasks import network_tasks
from octavia.network import base as net_base
from octavia.network import data_models
import octavia.tests.unit.base as base

if six.PY2:
    import mock
else:
    import unittest.mock as mock


AMPHORA_ID = 7
COMPUTE_ID = uuidutils.generate_uuid()
PORT_ID = uuidutils.generate_uuid()
SUBNET_ID = uuidutils.generate_uuid()
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


@mock.patch('stevedore.driver.DriverManager.driver')
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
        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="controller_worker", amp_network='netid')

        super(TestNetworkTasks, self).setUp()

    def test_calculate_delta(self,
                             mock_driver):
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
        self.load_balancer_mock.listeners = None
        self.assertEqual({self.amphora_mock.id: None},
                         net.execute(self.load_balancer_mock))

        listener_mock = mock.MagicMock()
        self.load_balancer_mock.listeners = [listener_mock]
        listener_mock.default_pool = None
        self.assertEqual(empty_deltas, net.execute(self.load_balancer_mock))
        mock_driver.get_plugged_networks.assert_called_once_with(COMPUTE_ID)

        pool_mock = mock.MagicMock()
        listener_mock.default_pool = pool_mock
        pool_mock.members = None
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

        vip_subnet_call = mock.call(self.vip_mock.subnet_id)
        member_subnet_call = mock.call(member_mock.subnet_id)
        mock_driver.get_subnet.assert_has_calls([vip_subnet_call,
                                                 member_subnet_call])
        self.assertEqual(2, mock_driver.get_subnet.call_count)

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

    def test_get_plumbed_networks(self,
                                  mock_driver):
        mock_driver.get_plugged_networks.side_effect = [['blah']]
        net = network_tasks.GetPlumbedNetworks()

        self.assertEqual(['blah'], net.execute(self.amphora_mock))
        mock_driver.get_plugged_networks.assert_called_once_with(
            COMPUTE_ID)

    def test_plug_networks(self,
                           mock_driver):

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

    def test_unplug_networks(self, mock_driver):
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

    def test_handle_network_delta(self, mock_driver):
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

    def test_plug_vip(self,
                      mock_driver):
        net = network_tasks.PlugVIP()

        mock_driver.plug_vip.return_value = ["vip"]

        data = net.execute(LB)
        mock_driver.plug_vip.assert_called_once_with(LB, LB.vip)
        self.assertEqual(["vip"], data)

        # revert
        net.revert(["vip"], LB)
        mock_driver.unplug_vip.assert_called_once_with(LB, LB.vip)

    def test_unplug_vip(self, mock_driver):
        net = network_tasks.UnplugVIP()

        net.execute(LB)
        mock_driver.unplug_vip.assert_called_once_with(LB, LB.vip)

    def test_allocate_vip(self, mock_driver):
        net = network_tasks.AllocateVIP()

        mock_driver.allocate_vip.return_value = LB.vip

        mock_driver.reset_mock()
        self.assertEqual(LB.vip, net.execute(LB))
        mock_driver.allocate_vip.assert_called_once_with(LB)
        # revert
        vip_mock = mock.MagicMock()
        net.revert(vip_mock, LB)
        mock_driver.deallocate_vip.assert_called_once_with(vip_mock)

    def test_deallocate_vip(self, mock_driver):
        net = network_tasks.DeallocateVIP()
        vip = o_data_models.Vip()
        lb = o_data_models.LoadBalancer(vip=vip)
        net.execute(lb)
        mock_driver.deallocate_vip.assert_called_once_with(lb.vip)

    def test_failover_preparation_for_amphora(self, mock_driver):
        failover = network_tasks.FailoverPreparationForAmphora()
        amphora = o_data_models.Amphora(id=AMPHORA_ID,
                                        lb_network_ip=IP_ADDRESS)
        failover.execute(amphora)
        mock_driver.failover_preparation.assert_called_once_with(amphora)
