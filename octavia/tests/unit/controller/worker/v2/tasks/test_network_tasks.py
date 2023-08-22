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
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils
from taskflow.types import failure
import tenacity

from octavia.api.drivers import utils as provider_utils
from octavia.common import constants
from octavia.common import data_models as o_data_models
from octavia.common import exceptions
from octavia.controller.worker.v2.tasks import network_tasks
from octavia.network import base as net_base
from octavia.network import data_models
from octavia.tests.common import constants as t_constants
import octavia.tests.unit.base as base


AMPHORA_ID = 7
COMPUTE_ID = uuidutils.generate_uuid()
PORT_ID = uuidutils.generate_uuid()
SUBNET_ID = uuidutils.generate_uuid()
NETWORK_ID = uuidutils.generate_uuid()
MGMT_NETWORK_ID = uuidutils.generate_uuid()
MGMT_SUBNET_ID = uuidutils.generate_uuid()
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
                                   status=constants.AMPHORA_ALLOCATED,
                                   vrrp_port_id=t_constants.MOCK_VRRP_PORT_ID1,
                                   vrrp_ip=t_constants.MOCK_VRRP_IP1),
             o_data_models.Amphora(id=t_constants.MOCK_AMP_ID2,
                                   status=constants.AMPHORA_ALLOCATED,
                                   vrrp_port_id=t_constants.MOCK_VRRP_PORT_ID2,
                                   vrrp_ip=t_constants.MOCK_VRRP_IP2),
             o_data_models.Amphora(id=t_constants.MOCK_AMP_ID3,
                                   status=constants.DELETED,
                                   vrrp_port_id=t_constants.MOCK_VRRP_PORT_ID3,
                                   vrrp_ip=t_constants.MOCK_VRRP_IP3)
             ]
UPDATE_DICT = {constants.TOPOLOGY: None}
_session_mock = mock.MagicMock()


class TestException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


@mock.patch('octavia.common.utils.get_network_driver')
class TestNetworkTasks(base.TestCase):
    def setUp(self):
        network_tasks.LOG = mock.MagicMock()
        self.db_amphora_mock = mock.MagicMock()
        self.db_load_balancer_mock = mock.MagicMock()
        self.vip_mock = mock.MagicMock()
        self.vip_mock.subnet_id = SUBNET_ID
        self.vip_mock.network_id = NETWORK_ID
        self.db_load_balancer_mock.vip = self.vip_mock
        self.db_load_balancer_mock.amphorae = []
        self.db_amphora_mock.id = AMPHORA_ID
        self.db_amphora_mock.compute_id = COMPUTE_ID
        self.db_amphora_mock.status = constants.AMPHORA_ALLOCATED
        self.mgmt_net_id = MGMT_NETWORK_ID
        self.mgmt_subnet_id = MGMT_SUBNET_ID
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group="controller_worker",
                    amp_boot_network_list=[self.mgmt_net_id])
        conf.config(group="networking", max_retries=1)
        self.amphora_mock = {constants.ID: AMPHORA_ID,
                             constants.COMPUTE_ID: COMPUTE_ID,
                             constants.LB_NETWORK_IP: IP_ADDRESS,
                             }
        self.load_balancer_mock = {
            constants.LOADBALANCER_ID: uuidutils.generate_uuid(),
            constants.VIP_SUBNET_ID: SUBNET_ID,
            constants.VIP_NETWORK_ID: NETWORK_ID,
            constants.VIP_PORT_ID: VIP.port_id,
            constants.VIP_ADDRESS: VIP.ip_address,
            constants.VIP_QOS_POLICY_ID: t_constants.MOCK_QOS_POLICY_ID1
        }

        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="controller_worker",
                    amp_boot_network_list=[self.mgmt_net_id])

        super().setUp()

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=_session_mock)
    def test_calculate_amphora_delta(self, mock_get_session, mock_lb_repo_get,
                                     mock_get_net_driver):
        LB_ID = uuidutils.generate_uuid()
        VRRP_PORT_ID = uuidutils.generate_uuid()
        VIP_NETWORK_ID = uuidutils.generate_uuid()
        VIP_SUBNET_ID = uuidutils.generate_uuid()
        DELETE_NETWORK_ID = uuidutils.generate_uuid()
        MEMBER_NETWORK_ID = uuidutils.generate_uuid()
        MEMBER_SUBNET_ID = uuidutils.generate_uuid()
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        member_mock = mock.MagicMock()
        member_mock.subnet_id = MEMBER_SUBNET_ID
        pool_mock = mock.MagicMock()
        pool_mock.members = [member_mock]
        lb_mock = mock.MagicMock()
        lb_mock.pools = [pool_mock]
        lb_mock.vip.subnet.network_id = VIP_NETWORK_ID
        lb_dict = {
            constants.LOADBALANCER_ID: LB_ID,
            constants.VIP_SUBNET_ID: VIP_SUBNET_ID,
            constants.VIP_NETWORK_ID: VIP_NETWORK_ID
        }

        amphora_dict = {constants.ID: AMPHORA_ID,
                        constants.COMPUTE_ID: COMPUTE_ID,
                        constants.VRRP_PORT_ID: VRRP_PORT_ID}

        mgmt_subnet = data_models.Subnet(
            id=self.mgmt_subnet_id,
            network_id=self.mgmt_net_id)
        mgmt_net = data_models.Network(
            id=self.mgmt_net_id,
            subnets=[mgmt_subnet.id])
        mgmt_interface = data_models.Interface(
            network_id=mgmt_net.id,
            fixed_ips=[
                data_models.FixedIP(
                    subnet_id=mgmt_subnet.id)])

        vrrp_subnet = data_models.Subnet(
            id=VIP_SUBNET_ID,
            network_id=VIP_NETWORK_ID)
        vrrp_port = data_models.Port(
            id=VRRP_PORT_ID,
            network_id=VIP_NETWORK_ID,
            fixed_ips=[
                data_models.FixedIP(
                    subnet=vrrp_subnet,
                    subnet_id=vrrp_subnet.id)])
        vrrp_interface = data_models.Interface(
            network_id=VIP_NETWORK_ID,
            fixed_ips=vrrp_port.fixed_ips)

        member_subnet = data_models.Subnet(
            id=MEMBER_SUBNET_ID,
            network_id=MEMBER_NETWORK_ID)

        to_be_deleted_interface = data_models.Interface(
            id=mock.Mock(),
            network_id=DELETE_NETWORK_ID)

        mock_lb_repo_get.return_value = lb_mock
        mock_driver.get_port.return_value = vrrp_port
        mock_driver.get_subnet.return_value = member_subnet
        mock_driver.get_plugged_networks.return_value = [
            mgmt_interface,
            vrrp_interface,
            to_be_deleted_interface]

        calc_amp_delta = network_tasks.CalculateAmphoraDelta()

        # Test vrrp_port_id is None
        result = calc_amp_delta.execute(lb_dict, amphora_dict, {})

        self.assertEqual(AMPHORA_ID, result[constants.AMPHORA_ID])
        self.assertEqual(COMPUTE_ID, result[constants.COMPUTE_ID])
        self.assertEqual(1, len(result[constants.ADD_NICS]))
        self.assertEqual(MEMBER_NETWORK_ID,
                         result[constants.ADD_NICS][0][constants.NETWORK_ID])
        self.assertEqual(1, len(result[constants.DELETE_NICS]))
        self.assertEqual(
            DELETE_NETWORK_ID,
            result[constants.DELETE_NICS][0][constants.NETWORK_ID])
        mock_driver.get_subnet.assert_called_once_with(
            MEMBER_SUBNET_ID)
        mock_driver.get_plugged_networks.assert_called_once_with(COMPUTE_ID)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=_session_mock)
    def test_calculate_delta(self, mock_get_session, mock_get_lb,
                             mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_lb.return_value = self.db_load_balancer_mock

        self.db_amphora_mock.to_dict.return_value = {
            constants.ID: AMPHORA_ID, constants.COMPUTE_ID: COMPUTE_ID,
            constants.VRRP_PORT_ID: PORT_ID}
        mock_get_net_driver.return_value = mock_driver
        empty_deltas = {self.db_amphora_mock.id: data_models.Delta(
            amphora_id=AMPHORA_ID,
            compute_id=COMPUTE_ID,
            add_nics=[],
            delete_nics=[],
            add_subnets=[],
            delete_subnets=[],
        ).to_dict()}

        mgmt_subnet = data_models.Subnet(
            id=self.mgmt_subnet_id, network_id=self.mgmt_net_id)
        mgmt_ip_address = mock.MagicMock()
        mgmt_interface = data_models.Interface(
            network_id=self.mgmt_net_id,
            fixed_ips=[
                data_models.FixedIP(
                    subnet=mgmt_subnet,
                    subnet_id=self.mgmt_subnet_id,
                    ip_address=mgmt_ip_address
                )
            ])
        vrrp_subnet = data_models.Subnet(
            id=self.vip_mock.subnet_id, network_id=self.vip_mock.network_id,
            name='vrrp_subnet')
        member_vip_subnet = data_models.Subnet(
            id=uuidutils.generate_uuid(), network_id=self.vip_mock.network_id,
            name='member_vip_subnet')
        vip_net = data_models.Network(
            id=self.vip_mock.network_id,
            subnets=[member_vip_subnet, vrrp_subnet],
            name='flat_network')
        vrrp_port = data_models.Port(
            id=uuidutils.generate_uuid(),
            network_id=vip_net.id, network=vip_net,
            fixed_ips=[
                data_models.FixedIP(
                    subnet=vrrp_subnet, subnet_id=vrrp_subnet.id,
                    ip_address=t_constants.MOCK_IP_ADDRESS)
            ],
            name='vrrp_port')

        member_private_net_id = uuidutils.generate_uuid()
        member_private_subnet = data_models.Subnet(
            id=uuidutils.generate_uuid(), network_id=member_private_net_id,
            name='member_private_subnet')
        member_private_subnet2 = data_models.Subnet(
            id=uuidutils.generate_uuid(), network_id=member_private_net_id,
            name='member_private_subnet2')
        member_private_net = data_models.Network(
            id=member_private_subnet.network_id,
            subnets=[member_private_subnet, member_private_subnet2],
            name='member_private_net')
        member_private_subnet_port = data_models.Port(
            id=uuidutils.generate_uuid(),
            network_id=member_private_net.id, network=member_private_net,
            fixed_ips=[
                data_models.FixedIP(
                    subnet=member_private_subnet,
                    subnet_id=member_private_subnet.id,
                    ip_address=t_constants.MOCK_IP_ADDRESS2)
            ],
            name='member_private_net_port')
        member_private_subnet2_port = data_models.Port(
            id=uuidutils.generate_uuid(),
            network_id=member_private_net.id, network=member_private_net,
            fixed_ips=[
                data_models.FixedIP(
                    subnet=member_private_subnet2,
                    subnet_id=member_private_subnet2.id,
                    ip_address=t_constants.MOCK_IP_ADDRESS2)
            ],
            name='member_private_net_port')

        # Pretend the VIP is on the member network, so already plugged
        mock_driver.get_plugged_networks.return_value = [
            mgmt_interface,
            data_models.Interface(
                network_id=vip_net.id, port_id=vrrp_port.id,
                fixed_ips=vrrp_port.fixed_ips)]
        mock_driver.get_port.return_value = vrrp_port
        mock_driver.get_subnet.return_value = vrrp_subnet

        calc_delta = network_tasks.CalculateDelta()

        # Test with no amps or anything at all
        self.assertEqual({}, calc_delta.execute(
            self.load_balancer_mock, {}))

        # Test with one amp and no pools, only the base network plugged
        # Delta should be empty
        mock_driver.reset_mock()

        self.db_amphora_mock.load_balancer = self.db_load_balancer_mock
        self.db_load_balancer_mock.amphorae = [self.db_amphora_mock]
        self.db_load_balancer_mock.pools = []
        self.assertEqual(empty_deltas,
                         calc_delta.execute(self.load_balancer_mock, {}))
        mock_driver.get_plugged_networks.assert_called_once_with(COMPUTE_ID)

        # Test with one amp and one pool but no members, nothing plugged
        # Delta should be empty
        mock_driver.reset_mock()
        pool_mock = mock.MagicMock()
        pool_mock.members = []
        self.db_load_balancer_mock.pools = [pool_mock]
        self.assertEqual(empty_deltas,
                         calc_delta.execute(self.load_balancer_mock, {}))

        # Test with one amp/pool and one member (on a distinct member subnet)
        # Dummy AZ is provided
        # Only the base network is already plugged
        # Delta should be one additional network/subnet to plug
        mock_driver.reset_mock()
        member_mock = mock.MagicMock()
        member_mock.subnet_id = member_private_subnet.id
        member2_mock = mock.MagicMock()
        member2_mock.subnet_id = member_private_subnet2.id
        pool_mock.members = [member_mock]
        az = {
            constants.COMPUTE_ZONE: 'foo'
        }
        mock_driver.get_subnet.return_value = data_models.Subnet(
            id=2, network_id=3)

        ndm = data_models.Delta(
            amphora_id=self.db_amphora_mock.id,
            compute_id=self.db_amphora_mock.compute_id,
            add_nics=[
                data_models.Interface(
                    network_id=3,
                    fixed_ips=[
                        data_models.FixedIP(
                            subnet_id=member_private_subnet.id)])],
            delete_nics=[],
            add_subnets=[{
                'subnet_id': member_private_subnet.id,
                'network_id': 3,
                'port_id': None}],
            delete_subnets=[]).to_dict(recurse=True)
        self.assertEqual({self.db_amphora_mock.id: ndm},
                         calc_delta.execute(self.load_balancer_mock, az))

        mock_driver.get_subnet.assert_called_once_with(
            member_mock.subnet_id)

        # Test with one amp/pool and one member (not plugged) that is being
        # deleted
        # Only the base network is already plugged
        # Delta should be empty
        mock_driver.reset_mock()
        member_mock = mock.MagicMock()
        member_mock.subnet_id = member_private_subnet.id
        member_mock.provisioning_status = constants.PENDING_DELETE
        pool_mock.members = [member_mock]

        self.assertEqual(empty_deltas,
                         calc_delta.execute(self.load_balancer_mock, {}))

        # Test with one amp/pool and one member (without any subnets)
        # Only the base network is already plugged
        # No delta
        mock_driver.reset_mock()
        member_mock = mock.MagicMock()
        member_mock.subnet_id = None
        pool_mock.members = [member_mock]

        self.assertEqual(empty_deltas,
                         calc_delta.execute(self.load_balancer_mock, {}))

        # Test with one amp and one pool and one member
        # Management network is defined in AZ metadata
        # Base network AND member network/subnet already plugged
        # Delta should be empty
        mock_driver.reset_mock()
        member_mock = mock.MagicMock()
        member_mock.subnet_id = member_private_subnet.id
        pool_mock.members = [member_mock]

        mgmt2_subnet_id = uuidutils.generate_uuid()
        mgmt2_net_id = uuidutils.generate_uuid()
        mgmt2_subnet = data_models.Subnet(
            id=mgmt2_subnet_id,
            network_id=mgmt2_net_id)
        mgmt2_interface = data_models.Interface(
            network_id=mgmt2_net_id,
            fixed_ips=[
                data_models.FixedIP(
                    subnet=mgmt2_subnet,
                    subnet_id=mgmt2_subnet_id,
                )
            ])
        az = {
            constants.MANAGEMENT_NETWORK: mgmt2_net_id,
        }
        mock_driver.get_subnet.return_value = member_private_subnet
        mock_driver.get_plugged_networks.return_value = [
            mgmt2_interface,
            data_models.Interface(
                network_id=vrrp_subnet.network_id,
                fixed_ips=vrrp_port.fixed_ips),
            data_models.Interface(
                network_id=member_private_subnet.network_id,
                fixed_ips=member_private_subnet_port.fixed_ips)]

        self.assertEqual(empty_deltas,
                         calc_delta.execute(self.load_balancer_mock, az))

        # Test with one amp and one pool and one member, wrong network plugged
        # Delta should be one network/subnet to add and one to remove
        mock_driver.reset_mock()
        member_mock = mock.MagicMock()
        member_mock.subnet_id = member_private_subnet.id
        pool_mock.members = [member_mock]
        az = {
            constants.COMPUTE_ZONE: 'foo'
        }
        mock_driver.get_subnet.return_value = member_private_subnet
        mock_driver.get_plugged_networks.return_value = [
            mgmt_interface,
            data_models.Interface(
                network_id=vrrp_subnet.network_id,
                fixed_ips=vrrp_port.fixed_ips),
            data_models.Interface(
                network_id='bad_net',
                fixed_ips=[data_models.FixedIP(subnet_id='bad_subnet')])]

        ndm = data_models.Delta(
            amphora_id=self.db_amphora_mock.id,
            compute_id=self.db_amphora_mock.compute_id,
            add_nics=[data_models.Interface(
                network_id=member_private_net.id,
                fixed_ips=[data_models.FixedIP(
                    subnet_id=member_private_subnet.id)])],
            delete_nics=[data_models.Interface(network_id='bad_net')],
            add_subnets=[{
                'subnet_id': member_private_subnet.id,
                'network_id': member_private_net.id,
                'port_id': None
            }],
            delete_subnets=[{
                'subnet_id': 'bad_subnet',
                'network_id': 'bad_net',
                'port_id': None
            }]).to_dict(recurse=True)
        self.assertEqual({self.db_amphora_mock.id: ndm},
                         calc_delta.execute(self.load_balancer_mock, az))

        # Test with one amp and one pool and no members, one network plugged
        # Delta should be one network to remove
        mock_driver.reset_mock()
        pool_mock.members = []
        mock_driver.get_subnet.side_effect = [
            vrrp_subnet]
        mock_driver.get_plugged_networks.return_value = [
            mgmt_interface,
            data_models.Interface(
                network_id=vrrp_subnet.network_id,
                fixed_ips=vrrp_port.fixed_ips),
            data_models.Interface(
                network_id='bad_net',
                fixed_ips=[data_models.FixedIP(subnet_id='bad_subnet')])]

        ndm = data_models.Delta(
            amphora_id=self.db_amphora_mock.id,
            compute_id=self.db_amphora_mock.compute_id,
            add_nics=[],
            delete_nics=[data_models.Interface(network_id='bad_net')],
            add_subnets=[],
            delete_subnets=[{
                'subnet_id': 'bad_subnet',
                'network_id': 'bad_net',
                'port_id': None
            }]).to_dict(recurse=True)
        self.assertEqual({self.db_amphora_mock.id: ndm},
                         calc_delta.execute(self.load_balancer_mock, {}))

        # Add a new member on a new subnet, an interface with another subnet of
        # the same network is already plugged
        # Delta should be one new subnet
        mock_driver.reset_mock()
        pool_mock.members = [member_mock, member2_mock]
        mock_driver.get_subnet.side_effect = [
            vrrp_subnet,
            member_private_subnet,
            member_private_subnet2]
        mock_driver.get_plugged_networks.return_value = [
            mgmt_interface,
            data_models.Interface(
                network_id=vrrp_subnet.network_id,
                fixed_ips=vrrp_port.fixed_ips),
            data_models.Interface(
                network_id=member_private_net_id,
                port_id=member_private_subnet_port.id,
                fixed_ips=member_private_subnet_port.fixed_ips)]

        ndm = data_models.Delta(
            amphora_id=self.db_amphora_mock.id,
            compute_id=self.db_amphora_mock.compute_id,
            add_nics=[],
            delete_nics=[],
            add_subnets=[{
                'subnet_id': member_private_subnet2.id,
                'network_id': member_private_net_id,
                'port_id': member_private_subnet_port.id
            }],
            delete_subnets=[]
        ).to_dict(recurse=True)
        self.assertEqual({self.db_amphora_mock.id: ndm},
                         calc_delta.execute(self.load_balancer_mock, {}))

        # a new member on a new subnet on an existing network, a delete member2
        # on another subnet of the same network
        # Delta should be one new subnet, one deleted subnet, no interface
        # change
        mock_driver.reset_mock()
        pool_mock.members = [member_mock]
        mock_driver.get_subnet.return_value = member_private_subnet
        mock_driver.get_plugged_networks.return_value = [
            mgmt_interface,
            data_models.Interface(
                network_id=vrrp_subnet.network_id,
                fixed_ips=vrrp_port.fixed_ips),
            data_models.Interface(
                network_id=member_private_net_id,
                port_id=member_private_subnet2_port.id,
                fixed_ips=member_private_subnet2_port.fixed_ips)]

        ndm = data_models.Delta(
            amphora_id=self.db_amphora_mock.id,
            compute_id=self.db_amphora_mock.compute_id,
            add_nics=[],
            delete_nics=[],
            add_subnets=[{
                'subnet_id': member_private_subnet.id,
                'network_id': member_private_net_id,
                'port_id': member_private_subnet2_port.id}],
            delete_subnets=[{
                'subnet_id': member_private_subnet2.id,
                'network_id': member_private_net_id,
                'port_id': member_private_subnet2_port.id}]
        ).to_dict(recurse=True)
        self.assertEqual({self.db_amphora_mock.id: ndm},
                         calc_delta.execute(self.load_balancer_mock, {}))

        # member on subnet on the same network as the vip subnet
        mock_driver.reset_mock()
        member_mock.subnet_id = member_vip_subnet.id
        pool_mock.members = [member_mock]
        mock_driver.get_subnet.side_effect = [
            vrrp_subnet,
            member_vip_subnet]
        mock_driver.get_plugged_networks.return_value = [
            mgmt_interface,
            data_models.Interface(
                network_id=vrrp_subnet.network_id,
                port_id=vrrp_port.id,
                fixed_ips=vrrp_port.fixed_ips),
            data_models.Interface(
                network_id=member_private_net_id,
                port_id=member_private_subnet_port.id,
                fixed_ips=member_private_subnet_port.fixed_ips)]

        ndm = data_models.Delta(
            amphora_id=self.db_amphora_mock.id,
            compute_id=self.db_amphora_mock.compute_id,
            add_nics=[],
            delete_nics=[
                data_models.Interface(
                    network_id=member_private_net_id,
                    port_id=member_private_subnet_port.id)],
            add_subnets=[{
                'subnet_id': member_vip_subnet.id,
                'network_id': vip_net.id,
                'port_id': vrrp_port.id}],
            delete_subnets=[{
                'subnet_id': member_private_subnet.id,
                'network_id': member_private_net_id,
                'port_id': member_private_subnet_port.id}]
        ).to_dict(recurse=True)
        self.assertEqual({self.db_amphora_mock.id: ndm},
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

        delta = data_models.Delta(amphora_id=self.db_amphora_mock.id,
                                  compute_id=self.db_amphora_mock.compute_id,
                                  add_nics=[],
                                  delete_nics=[]).to_dict(recurse=True)
        net.execute(self.amphora_mock, delta)
        self.assertFalse(mock_driver.plug_network.called)

        delta = data_models.Delta(amphora_id=self.db_amphora_mock.id,
                                  compute_id=self.db_amphora_mock.compute_id,
                                  add_nics=_interface(1),
                                  delete_nics=[]).to_dict(recurse=True)
        net.execute(self.amphora_mock, delta)
        mock_driver.plug_network.assert_called_once_with(COMPUTE_ID, 1)

        # revert
        net.revert(self.amphora_mock, None)
        self.assertFalse(mock_driver.unplug_network.called)

        delta = data_models.Delta(amphora_id=self.db_amphora_mock.id,
                                  compute_id=self.db_amphora_mock.compute_id,
                                  add_nics=[],
                                  delete_nics=[]).to_dict(recurse=True)
        net.revert(self.amphora_mock, delta)
        self.assertFalse(mock_driver.unplug_network.called)

        delta = data_models.Delta(amphora_id=self.db_amphora_mock.id,
                                  compute_id=self.db_amphora_mock.compute_id,
                                  add_nics=_interface(1),
                                  delete_nics=[]).to_dict(recurse=True)
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

        net.execute(self.db_amphora_mock, None)
        self.assertFalse(mock_driver.unplug_network.called)

        delta = data_models.Delta(amphora_id=self.db_amphora_mock.id,
                                  compute_id=self.db_amphora_mock.compute_id,
                                  add_nics=[],
                                  delete_nics=[]).to_dict(recurse=True)
        net.execute(self.amphora_mock, delta)
        self.assertFalse(mock_driver.unplug_network.called)

        delta = data_models.Delta(amphora_id=self.db_amphora_mock.id,
                                  compute_id=self.db_amphora_mock.compute_id,
                                  add_nics=[],
                                  delete_nics=_interface(1)
                                  ).to_dict(recurse=True)
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
        net_task.execute(self.load_balancer_mock, self.amphora_mock)
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

    @mock.patch('octavia.db.repositories.AmphoraRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=_session_mock)
    def test_handle_network_delta(self, mock_session, mock_amp_get,
                                  mock_get_net_driver):
        mock_net_driver = mock.MagicMock()
        self.db_amphora_mock.to_dict.return_value = {
            constants.ID: AMPHORA_ID, constants.COMPUTE_ID: COMPUTE_ID}
        mock_get_net_driver.return_value = mock_net_driver
        mock_amp_get.return_value = self.db_amphora_mock

        nic1 = data_models.Interface()
        nic1.fixed_ips = [data_models.FixedIP(
            subnet_id=uuidutils.generate_uuid())]
        nic1.network_id = uuidutils.generate_uuid()
        nic2 = data_models.Interface()
        nic2.fixed_ips = [data_models.FixedIP(
            subnet_id=uuidutils.generate_uuid())]
        nic2.network_id = uuidutils.generate_uuid()
        interface1 = mock.MagicMock()
        interface1.port_id = uuidutils.generate_uuid()
        port1 = mock.MagicMock()
        port1.network_id = uuidutils.generate_uuid()
        fixed_ip = mock.MagicMock()
        fixed_ip.subnet_id = nic1.fixed_ips[0].subnet_id
        fixed_ip2 = mock.MagicMock()
        fixed_ip2.subnet_id = uuidutils.generate_uuid()
        port1.fixed_ips = [fixed_ip, fixed_ip2]
        subnet = mock.MagicMock()
        network = mock.MagicMock()

        delta = data_models.Delta(amphora_id=self.db_amphora_mock.id,
                                  compute_id=self.db_amphora_mock.compute_id,
                                  add_nics=[nic1],
                                  delete_nics=[nic2, nic2, nic2],
                                  add_subnets=[],
                                  delete_subnets=[]
                                  ).to_dict(recurse=True)

        mock_net_driver.plug_network.return_value = interface1
        mock_net_driver.get_port.return_value = port1
        fixed_port1 = mock.MagicMock()
        fixed_port1.network_id = port1.network_id
        fixed_port1.fixed_ips = [fixed_ip]
        mock_net_driver.unplug_fixed_ip.return_value = fixed_port1
        mock_net_driver.get_network.return_value = network
        mock_net_driver.get_subnet.return_value = subnet

        mock_net_driver.unplug_network.side_effect = [
            None, net_base.NetworkNotFound, Exception]

        handle_net_delta_obj = network_tasks.HandleNetworkDelta()
        result = handle_net_delta_obj.execute(self.amphora_mock,
                                              delta)

        mock_net_driver.plug_network.assert_called_once_with(
            self.db_amphora_mock.compute_id, nic1.network_id)
        mock_net_driver.unplug_fixed_ip.assert_called_once_with(
            port_id=interface1.port_id, subnet_id=fixed_ip2.subnet_id)
        mock_net_driver.get_port.assert_called_once_with(interface1.port_id)
        mock_net_driver.get_network.assert_called_once_with(port1.network_id)
        mock_net_driver.get_subnet.assert_called_once_with(fixed_ip.subnet_id)

        self.assertEqual({self.db_amphora_mock.id: [fixed_port1.to_dict()]},
                         result)

        mock_net_driver.unplug_network.assert_called_with(
            self.db_amphora_mock.compute_id, nic2.network_id)

        # Revert
        delta2 = data_models.Delta(amphora_id=self.db_amphora_mock.id,
                                   compute_id=self.db_amphora_mock.compute_id,
                                   add_nics=[nic1, nic1],
                                   delete_nics=[nic2, nic2, nic2]
                                   ).to_dict(recurse=True)

        mock_net_driver.unplug_network.reset_mock()
        handle_net_delta_obj.revert(
            failure.Failure.from_exception(Exception('boom')), None, None)
        mock_net_driver.unplug_network.assert_not_called()

        mock_net_driver.unplug_network.reset_mock()
        handle_net_delta_obj.revert(None, None, None)
        mock_net_driver.unplug_network.assert_not_called()

        mock_net_driver.unplug_network.reset_mock()
        handle_net_delta_obj.revert(None, None, delta2)

        mock_net_driver.unplug_network.reset_mock()
        mock_net_driver.delete_port.side_effect = Exception('boom')
        handle_net_delta_obj.revert(None, None, delta2)

    @mock.patch('octavia.db.repositories.AmphoraRepository.get')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=_session_mock)
    def test_handle_network_deltas(self, mock_get_session,
                                   mock_get_lb, mock_get_amp,
                                   mock_get_net_driver):
        mock_driver = mock.MagicMock()
        self.db_load_balancer_mock.amphorae = [self.db_amphora_mock]
        self.db_amphora_mock.to_dict.return_value = {
            constants.ID: AMPHORA_ID, constants.COMPUTE_ID: COMPUTE_ID}
        mock_get_net_driver.return_value = mock_driver
        mock_get_lb.return_value = self.db_load_balancer_mock
        mock_get_amp.return_value = self.db_amphora_mock

        subnet1 = uuidutils.generate_uuid()
        network1 = uuidutils.generate_uuid()
        port1 = uuidutils.generate_uuid()
        subnet2 = uuidutils.generate_uuid()

        def _interface(network_id, port_id=None, subnet_id=None):
            return data_models.Interface(
                network_id=network_id,
                port_id=port_id,
                fixed_ips=[
                    data_models.FixedIP(
                        subnet_id=subnet_id)])

        net = network_tasks.HandleNetworkDeltas()

        net.execute({}, self.load_balancer_mock)
        self.assertFalse(mock_driver.plug_network.called)

        delta = data_models.Delta(amphora_id=self.db_amphora_mock.id,
                                  compute_id=self.db_amphora_mock.compute_id,
                                  add_nics=[],
                                  delete_nics=[],
                                  add_subnets=[],
                                  delete_subnets=[]).to_dict(recurse=True)
        net.execute({self.db_amphora_mock.id: delta}, self.load_balancer_mock)
        self.assertFalse(mock_driver.plug_network.called)

        # Adding a subnet on a new network
        port = data_models.Port(
            id=port1,
            network_id=network1,
            fixed_ips=[
                data_models.FixedIP(subnet_id=subnet1)])
        mock_driver.get_port.return_value = port
        mock_driver.plug_fixed_ip.return_value = port
        mock_driver.get_network.return_value = data_models.Network(
            id=network1)
        mock_driver.get_subnet.return_value = data_models.Subnet(
            id=subnet1,
            network_id=network1)
        add_nics = [_interface(network1, subnet_id=subnet1)]
        add_subnets = [{
            'subnet_id': subnet1,
            'network_id': network1,
            'port_id': None}]

        delta = data_models.Delta(amphora_id=self.db_amphora_mock.id,
                                  compute_id=self.db_amphora_mock.compute_id,
                                  add_nics=add_nics,
                                  delete_nics=[],
                                  add_subnets=add_subnets,
                                  delete_subnets=[]).to_dict(recurse=True)
        updated_ports = net.execute({self.db_amphora_mock.id: delta},
                                    self.load_balancer_mock)
        mock_driver.plug_network.assert_called_once_with(
            self.db_amphora_mock.compute_id, network1)
        mock_driver.unplug_network.assert_not_called()

        self.assertEqual(1, len(updated_ports))

        updated_port = updated_ports[self.db_amphora_mock.id][0]
        self.assertEqual(port1, updated_port['id'])
        self.assertEqual(network1, updated_port['network_id'])
        self.assertEqual(1, len(updated_port['fixed_ips']))
        self.assertEqual(subnet1, updated_port['fixed_ips'][0]['subnet_id'])

        # revert
        net.revert(None, {self.db_amphora_mock.id: delta},
                   self.load_balancer_mock)
        mock_driver.unplug_network.assert_called_once_with(
            self.db_amphora_mock.compute_id, network1)

        # Adding a subnet on an existing network/port
        mock_driver.reset_mock()
        port = data_models.Port(
            id=port1,
            network_id=network1,
            fixed_ips=[
                data_models.FixedIP(subnet_id=subnet2),
                data_models.FixedIP(subnet_id=subnet1)])
        mock_driver.plug_fixed_ip.return_value = port
        mock_driver.get_network.return_value = data_models.Network(
            id=network1)
        mock_driver.get_subnet.side_effect = [
            data_models.Subnet(
                id=subnet2,
                network_id=network1),
            data_models.Subnet(
                id=subnet1,
                network_id=network1)]
        add_subnets = [{
            'subnet_id': subnet1,
            'network_id': network1,
            'port_id': port1}]

        delta = data_models.Delta(amphora_id=self.db_amphora_mock.id,
                                  compute_id=self.db_amphora_mock.compute_id,
                                  add_nics=[],
                                  delete_nics=[],
                                  add_subnets=add_subnets,
                                  delete_subnets=[]).to_dict(recurse=True)
        updated_ports = net.execute({self.db_amphora_mock.id: delta},
                                    self.load_balancer_mock)
        mock_driver.plug_network.assert_not_called()
        mock_driver.unplug_network.assert_not_called()
        mock_driver.get_port.assert_not_called()
        mock_driver.plug_fixed_ip.assert_called_once_with(port_id=port1,
                                                          subnet_id=subnet1)
        self.assertEqual(1, len(updated_ports))

        updated_port = updated_ports[self.db_amphora_mock.id][0]
        self.assertEqual(port1, updated_port['id'])
        self.assertEqual(network1, updated_port['network_id'])
        self.assertEqual(2, len(updated_port['fixed_ips']))
        self.assertEqual(subnet2, updated_port['fixed_ips'][0]['subnet_id'])
        self.assertEqual(subnet1, updated_port['fixed_ips'][1]['subnet_id'])

        # Deleting a subnet
        mock_driver.reset_mock()
        delete_subnets = [{
            'subnet_id': subnet1,
            'network_id': network1,
            'port_id': port1}]
        mock_driver.get_subnet.side_effect = [
            data_models.Subnet(
                id=subnet2,
                network_id=network1)]
        mock_driver.unplug_fixed_ip.return_value = data_models.Port(
            id=port1,
            network_id=network1,
            fixed_ips=[
                data_models.FixedIP(subnet_id=subnet2)])

        delta = data_models.Delta(amphora_id=self.db_amphora_mock.id,
                                  compute_id=self.db_amphora_mock.compute_id,
                                  add_nics=[],
                                  delete_nics=[],
                                  add_subnets=[],
                                  delete_subnets=delete_subnets).to_dict(
                                      recurse=True)
        updated_ports = net.execute({self.db_amphora_mock.id: delta},
                                    self.load_balancer_mock)
        mock_driver.delete_port.assert_not_called()
        mock_driver.plug_network.assert_not_called()
        mock_driver.plug_fixed_ip.assert_not_called()
        mock_driver.unplug_fixed_ip.assert_called_once_with(
            port_id=port1, subnet_id=subnet1)
        self.assertEqual(1, len(updated_ports))
        self.assertEqual(1, len(updated_ports[self.db_amphora_mock.id]))

        updated_port = updated_ports[self.db_amphora_mock.id][0]
        self.assertEqual(port1, updated_port['id'])
        self.assertEqual(network1, updated_port['network_id'])
        self.assertEqual(1, len(updated_port['fixed_ips']))
        self.assertEqual(subnet2, updated_port['fixed_ips'][0]['subnet_id'])

        # Noop update
        # Delta are empty because there's nothing to update
        mock_driver.reset_mock()
        delta = data_models.Delta(amphora_id=self.db_amphora_mock.id,
                                  compute_id=self.db_amphora_mock.compute_id,
                                  add_nics=[],
                                  delete_nics=[],
                                  add_subnets=[],
                                  delete_subnets=[]).to_dict(recurse=True)
        net.execute({self.db_amphora_mock.id: delta},
                    self.load_balancer_mock)
        mock_driver.delete_port.assert_not_called()
        mock_driver.plug_network.assert_not_called()
        mock_driver.plug_fixed_ip.assert_not_called()
        mock_driver.unplug_fixed_ip.assert_not_called()

        # Deleting a subnet and a network
        mock_driver.reset_mock()
        mock_driver.get_subnet.side_effect = [
            data_models.Subnet(
                id=subnet2,
                network_id=network1),
            data_models.Subnet(
                id=subnet1,
                network_id=network1)]
        delete_nics = [_interface(network1, port_id=port1)]
        delete_subnets = [{
            'subnet_id': subnet1,
            'network_id': network1,
            'port_id': port1}]

        delta = data_models.Delta(amphora_id=self.db_amphora_mock.id,
                                  compute_id=self.db_amphora_mock.compute_id,
                                  add_nics=[],
                                  delete_nics=delete_nics,
                                  add_subnets=[],
                                  delete_subnets=delete_subnets).to_dict(
                                      recurse=True)
        updated_ports = net.execute({self.db_amphora_mock.id: delta},
                                    self.load_balancer_mock)
        mock_driver.delete_port.assert_called_once_with(port1)
        mock_driver.plug_network.assert_not_called()
        mock_driver.plug_fixed_ip.assert_not_called()
        self.assertEqual(1, len(updated_ports))
        self.assertEqual(0, len(updated_ports[self.db_amphora_mock.id]))

        delta = data_models.Delta(amphora_id=self.db_amphora_mock.id,
                                  compute_id=self.db_amphora_mock.compute_id,
                                  add_nics=[_interface(1, port_id=12)],
                                  delete_nics=[],
                                  add_subnets=[],
                                  delete_subnets=[]).to_dict(recurse=True)
        mock_driver.reset_mock()
        mock_driver.unplug_network.side_effect = TestException('test')
        net.revert(None, {self.db_amphora_mock.id: delta},
                   self.load_balancer_mock)
        mock_driver.unplug_network.assert_called_once_with(
            self.db_amphora_mock.compute_id, 1)

        mock_driver.reset_mock()
        mock_driver.delete_port.side_effect = TestException('test')
        net.revert(None, {self.db_amphora_mock.id: delta},
                   self.load_balancer_mock)
        mock_driver.unplug_network.assert_called_once_with(
            self.db_amphora_mock.compute_id, 1)
        mock_driver.delete_port.assert_called_once_with(12)

        mock_driver.reset_mock()
        net.execute({}, self.load_balancer_mock)
        self.assertFalse(mock_driver.unplug_network.called)

        delta = data_models.Delta(amphora_id=self.db_amphora_mock.id,
                                  compute_id=self.db_amphora_mock.compute_id,
                                  add_nics=[],
                                  delete_nics=[_interface(1)],
                                  add_subnets=[],
                                  delete_subnets=[]).to_dict(recurse=True)
        net.execute({self.db_amphora_mock.id: delta}, self.load_balancer_mock)
        mock_driver.unplug_network.assert_called_once_with(COMPUTE_ID, 1)

        mock_driver.reset_mock()
        mock_driver.unplug_network.side_effect = net_base.NetworkNotFound
        net.execute({self.db_amphora_mock.id: delta}, self.load_balancer_mock)
        mock_driver.unplug_network.assert_called_once_with(COMPUTE_ID, 1)

        # Do a test with a general exception in case behavior changes
        mock_driver.reset_mock()
        mock_driver.unplug_network.side_effect = Exception()
        net.execute({self.db_amphora_mock.id: delta}, self.load_balancer_mock)
        mock_driver.unplug_network.assert_called_once_with(COMPUTE_ID, 1)

        # Do a test with a general exception in case behavior changes
        delta = data_models.Delta(amphora_id=self.db_amphora_mock.id,
                                  compute_id=self.db_amphora_mock.compute_id,
                                  add_nics=[],
                                  delete_nics=[_interface(1, port_id=12)],
                                  add_subnets=[],
                                  delete_subnets=[]).to_dict(recurse=True)
        mock_driver.reset_mock()
        mock_driver.delete_port.side_effect = Exception()
        net.execute({self.db_amphora_mock.id: delta}, self.load_balancer_mock)
        mock_driver.unplug_network.assert_called_once_with(COMPUTE_ID, 1)
        mock_driver.delete_port.assert_called_once_with(12)

        mock_driver.unplug_network.reset_mock()
        net.revert(
            failure.Failure.from_exception(Exception('boom')), None, None)
        mock_driver.unplug_network.assert_not_called()

        mock_driver.unplug_network.reset_mock()
        net.revert(None, None, None)
        mock_driver.unplug_network.assert_not_called()

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=_session_mock)
    def test_plug_vip(self, mock_get_session, mock_get_lb,
                      mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        LB.amphorae = AMPS_DATA
        mock_get_lb.return_value = LB
        LB.amphorae = AMPS_DATA
        net = network_tasks.PlugVIP()
        amp = mock.MagicMock()
        amp.to_dict.return_value = 'vip'
        mock_driver.plug_vip.return_value = [amp]

        data = net.execute(self.load_balancer_mock)
        mock_driver.plug_vip.assert_called_once_with(LB, LB.vip)
        self.assertEqual(["vip"], data)

        # revert
        net.revert([o_data_models.Amphora().to_dict()],
                   self.load_balancer_mock)
        mock_driver.unplug_vip.assert_called_once_with(LB, LB.vip)

        # revert with exception
        mock_driver.reset_mock()
        mock_driver.unplug_vip.side_effect = Exception('UnplugVipException')
        net.revert([o_data_models.Amphora().to_dict()],
                   self.load_balancer_mock)
        mock_driver.unplug_vip.assert_called_once_with(LB, LB.vip)

    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'get_current_loadbalancer_from_db')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=_session_mock)
    def test_apply_qos_on_creation(self, mock_get_session, mock_get_lb,
                                   mock_get_lb_db, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.ApplyQos()
        mock_get_lb_db.return_value = LB
        mock_get_lb.return_value = LB

        # execute
        UPDATE_DICT[constants.TOPOLOGY] = constants.TOPOLOGY_SINGLE
        update_dict = UPDATE_DICT
        net.execute(self.load_balancer_mock, [AMPS_DATA[0]], update_dict)
        mock_driver.apply_qos_on_port.assert_called_once_with(
            VIP.qos_policy_id, AMPS_DATA[0].vrrp_port_id)
        self.assertEqual(1, mock_driver.apply_qos_on_port.call_count)
        standby_topology = constants.TOPOLOGY_ACTIVE_STANDBY
        mock_driver.reset_mock()
        update_dict[constants.TOPOLOGY] = standby_topology
        net.execute(self.load_balancer_mock, AMPS_DATA, update_dict)
        mock_driver.apply_qos_on_port.assert_called_with(
            t_constants.MOCK_QOS_POLICY_ID1, mock.ANY)
        self.assertEqual(2, mock_driver.apply_qos_on_port.call_count)

        # revert
        mock_driver.reset_mock()
        update_dict = UPDATE_DICT
        net.revert(None, self.load_balancer_mock, [AMPS_DATA[0]], update_dict)
        self.assertEqual(0, mock_driver.apply_qos_on_port.call_count)
        mock_driver.reset_mock()
        update_dict[constants.TOPOLOGY] = standby_topology
        net.revert(None, self.load_balancer_mock, AMPS_DATA, update_dict)
        self.assertEqual(0, mock_driver.apply_qos_on_port.call_count)

    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'get_current_loadbalancer_from_db')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=_session_mock)
    def test_apply_qos_on_update(self, mock_get_session, mock_get_lb,
                                 mock_get_lb_db, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.ApplyQos()
        null_qos_vip = o_data_models.Vip(qos_policy_id=None)
        null_qos_lb = o_data_models.LoadBalancer(
            vip=null_qos_vip, topology=constants.TOPOLOGY_SINGLE,
            amphorae=[AMPS_DATA[0]])
        null_qos_lb_dict = (
            provider_utils.db_loadbalancer_to_provider_loadbalancer(
                null_qos_lb).to_dict())

        tmp_vip_object = o_data_models.Vip(
            qos_policy_id=t_constants.MOCK_QOS_POLICY_ID1)
        tmp_lb = o_data_models.LoadBalancer(
            vip=tmp_vip_object, topology=constants.TOPOLOGY_SINGLE,
            amphorae=[AMPS_DATA[0]])
        pr_tm_dict = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            tmp_lb).to_dict()
        mock_get_lb.return_value = tmp_lb
        # execute
        update_dict = {'description': 'fool'}
        net.execute(pr_tm_dict, update_dict=update_dict)
        mock_driver.apply_qos_on_port.assert_called_once_with(
            t_constants.MOCK_QOS_POLICY_ID1, AMPS_DATA[0].vrrp_port_id)
        self.assertEqual(1, mock_driver.apply_qos_on_port.call_count)

        mock_driver.reset_mock()
        mock_get_lb.reset_mock()
        mock_get_lb.return_value = null_qos_lb
        update_dict = {'vip': {'qos_policy_id': None}}
        net.execute(null_qos_lb_dict, update_dict=update_dict)
        mock_driver.apply_qos_on_port.assert_called_once_with(
            None, AMPS_DATA[0].vrrp_port_id)
        self.assertEqual(1, mock_driver.apply_qos_on_port.call_count)

        mock_driver.reset_mock()
        update_dict = {'name': '123'}
        net.execute(null_qos_lb_dict, update_dict=update_dict)
        self.assertEqual(0, mock_driver.apply_qos_on_port.call_count)

        mock_driver.reset_mock()
        mock_get_lb.reset_mock()
        update_dict = {'description': 'fool'}
        tmp_lb.amphorae = AMPS_DATA
        tmp_lb.topology = constants.TOPOLOGY_ACTIVE_STANDBY
        mock_get_lb.return_value = tmp_lb
        net.execute(pr_tm_dict, update_dict=update_dict)
        mock_driver.apply_qos_on_port.assert_called_with(
            t_constants.MOCK_QOS_POLICY_ID1, mock.ANY)
        self.assertEqual(2, mock_driver.apply_qos_on_port.call_count)

        mock_driver.reset_mock()
        update_dict = {'description': 'fool',
                       'vip': {
                           'qos_policy_id': t_constants.MOCK_QOS_POLICY_ID1}}
        tmp_lb.amphorae = AMPS_DATA
        tmp_lb.topology = constants.TOPOLOGY_ACTIVE_STANDBY
        net.execute(pr_tm_dict, update_dict=update_dict)
        mock_driver.apply_qos_on_port.assert_called_with(
            t_constants.MOCK_QOS_POLICY_ID1, mock.ANY)
        self.assertEqual(2, mock_driver.apply_qos_on_port.call_count)

        mock_get_lb.return_value = null_qos_lb
        mock_driver.reset_mock()
        update_dict = {}
        net.execute(null_qos_lb_dict, update_dict=update_dict)
        self.assertEqual(0, mock_driver.apply_qos_on_port.call_count)

        # revert
        mock_driver.reset_mock()
        mock_get_lb.reset_mock()
        tmp_lb.amphorae = [AMPS_DATA[0]]
        tmp_lb.topology = constants.TOPOLOGY_SINGLE
        update_dict = {'description': 'fool'}
        mock_get_lb_db.return_value = tmp_lb
        net.revert(None, pr_tm_dict, update_dict=update_dict)
        self.assertEqual(0, mock_driver.apply_qos_on_port.call_count)

        mock_driver.reset_mock()
        update_dict = {'vip': {'qos_policy_id': None}}
        ori_lb_db = LB2
        ori_lb_db.amphorae = [AMPS_DATA[0]]
        mock_get_lb_db.return_value = ori_lb_db
        net.revert(None, null_qos_lb_dict, update_dict=update_dict)
        mock_driver.apply_qos_on_port.assert_called_once_with(
            t_constants.MOCK_QOS_POLICY_ID2, AMPS_DATA[0].vrrp_port_id)
        self.assertEqual(1, mock_driver.apply_qos_on_port.call_count)

        mock_driver.reset_mock()
        mock_get_lb.reset_mock()
        update_dict = {'vip': {
            'qos_policy_id': t_constants.MOCK_QOS_POLICY_ID2}}
        tmp_lb.amphorae = AMPS_DATA
        tmp_lb.topology = constants.TOPOLOGY_ACTIVE_STANDBY
        ori_lb_db = LB2
        ori_lb_db.amphorae = [AMPS_DATA[0]]
        mock_get_lb_db.return_value = ori_lb_db
        net.revert(None, pr_tm_dict, update_dict=update_dict)
        mock_driver.apply_qos_on_port.assert_called_with(
            t_constants.MOCK_QOS_POLICY_ID2, mock.ANY)
        self.assertEqual(1, mock_driver.apply_qos_on_port.call_count)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=_session_mock)
    def test_unplug_vip(self, mock_get_session, mock_get_lb,
                        mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_lb.return_value = LB
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.UnplugVIP()

        net.execute(self.load_balancer_mock)
        mock_driver.unplug_vip.assert_called_once_with(LB, LB.vip)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=_session_mock)
    def test_allocate_vip(self, mock_get_session, mock_get_lb,
                          mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_lb.return_value = LB
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.AllocateVIP()

        additional_vip = mock.Mock()
        additional_vip.subnet_id = uuidutils.generate_uuid()
        additional_vip.ip_address = IP_ADDRESS
        mock_driver.allocate_vip.return_value = LB.vip, [additional_vip]

        mock_driver.reset_mock()
        self.assertEqual((LB.vip.to_dict(), [additional_vip.to_dict()]),
                         net.execute(self.load_balancer_mock))
        mock_driver.allocate_vip.assert_called_once_with(LB)

        # revert
        vip_mock = VIP.to_dict()
        additional_vips_mock = mock.MagicMock()
        net.revert((vip_mock, additional_vips_mock), self.load_balancer_mock)
        mock_driver.deallocate_vip.assert_called_once_with(
            o_data_models.Vip(**vip_mock))

        # revert exception
        mock_driver.reset_mock()
        additional_vips_mock.reset_mock()
        mock_driver.deallocate_vip.side_effect = Exception('DeallVipException')
        vip_mock = VIP.to_dict()
        net.revert((vip_mock, additional_vips_mock), self.load_balancer_mock)
        mock_driver.deallocate_vip.assert_called_once_with(o_data_models.Vip(
            **vip_mock))

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=_session_mock)
    def test_allocate_vip_for_failover(self, mock_get_session, mock_get_lb,
                                       mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_lb.return_value = LB
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.AllocateVIPforFailover()

        mock_driver.allocate_vip.return_value = LB.vip, []

        mock_driver.reset_mock()
        self.assertEqual((LB.vip.to_dict(), []),
                         net.execute(self.load_balancer_mock))
        mock_driver.allocate_vip.assert_called_once_with(LB)

        # revert
        vip_mock = VIP.to_dict()
        additional_vips_mock = mock.MagicMock()
        net.revert((vip_mock, additional_vips_mock), self.load_balancer_mock)
        mock_driver.deallocate_vip.assert_not_called()

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=_session_mock)
    def test_deallocate_vip(self, mock_get_session, mock_get_lb,
                            mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.DeallocateVIP()
        vip = o_data_models.Vip()
        lb = o_data_models.LoadBalancer(vip=vip)
        mock_get_lb.return_value = lb
        net.execute(self.load_balancer_mock)
        mock_driver.deallocate_vip.assert_called_once_with(lb.vip)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=_session_mock)
    def test_update_vip(self, mock_get_session, mock_get_lb,
                        mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        vip = o_data_models.Vip()
        lb = o_data_models.LoadBalancer(vip=vip)
        mock_get_lb.return_value = lb
        listeners = [{constants.LOADBALANCER_ID: lb.id}]
        net_task = network_tasks.UpdateVIP()
        net_task.execute(listeners)
        mock_driver.update_vip.assert_called_once_with(lb)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=_session_mock)
    def test_update_vip_for_delete(self, mock_get_session, mock_get_lb,
                                   mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        vip = o_data_models.Vip()
        lb = o_data_models.LoadBalancer(vip=vip)
        mock_get_lb.return_value = lb
        listener = {constants.LOADBALANCER_ID: lb.id}
        net_task = network_tasks.UpdateVIPForDelete()
        net_task.execute(listener)
        mock_driver.update_vip.assert_called_once_with(lb, for_delete=True)

    @mock.patch('octavia.db.api.get_session')
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
        mock_amp_get.assert_called_once_with(mock_get_session(), id=AMP_ID)
        mock_lb_get.assert_called_once_with(mock_get_session(), id=LB_ID)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=_session_mock)
    def test_get_amphorae_network_configs(self, mock_session, mock_lb_get,
                                          mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_lb_get.return_value = LB
        mock_get_net_driver.return_value = mock_driver
        lb = o_data_models.LoadBalancer()
        net_task = network_tasks.GetAmphoraeNetworkConfigs()
        net_task.execute(self.load_balancer_mock)
        mock_driver.get_network_configs.assert_called_once_with(lb)

    @mock.patch('octavia.db.repositories.AmphoraRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=mock.MagicMock())
    def test_failover_preparation_for_amphora(self, mock_session, mock_get,
                                              mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get.return_value = self.db_amphora_mock
        mock_get_net_driver.return_value = mock_driver
        failover = network_tasks.FailoverPreparationForAmphora()
        failover.execute(self.amphora_mock)
        mock_driver.failover_preparation.assert_called_once_with(
            self.db_amphora_mock)

    def test_retrieve_portids_on_amphora_except_lb_network(
            self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver

        def _interface(port_id):
            return [data_models.Interface(port_id=port_id)]

        net_task = network_tasks.RetrievePortIDsOnAmphoraExceptLBNetwork()
        mock_driver.get_plugged_networks.return_value = []
        net_task.execute(self.amphora_mock)
        mock_driver.get_plugged_networks.assert_called_once_with(
            compute_id=COMPUTE_ID)
        self.assertFalse(mock_driver.get_port.called)

        mock_driver.reset_mock()
        net_task = network_tasks.RetrievePortIDsOnAmphoraExceptLBNetwork()
        mock_driver.get_plugged_networks.return_value = _interface(1)
        net_task.execute(self.amphora_mock)
        mock_driver.get_port.assert_called_once_with(port_id=1)

        mock_driver.reset_mock()
        net_task = network_tasks.RetrievePortIDsOnAmphoraExceptLBNetwork()
        port_mock = mock.MagicMock()
        fixed_ip_mock = mock.MagicMock()
        fixed_ip_mock.ip_address = IP_ADDRESS
        port_mock.fixed_ips = [fixed_ip_mock]
        mock_driver.get_plugged_networks.return_value = _interface(1)
        mock_driver.get_port.return_value = port_mock
        ports = net_task.execute(self.amphora_mock)
        self.assertEqual([], ports)

        mock_driver.reset_mock()
        net_task = network_tasks.RetrievePortIDsOnAmphoraExceptLBNetwork()
        port_mock = mock.MagicMock()
        fixed_ip_mock = mock.MagicMock()
        fixed_ip_mock.ip_address = "172.17.17.17"
        port_mock.fixed_ips = [fixed_ip_mock]
        mock_driver.get_plugged_networks.return_value = _interface(1)
        mock_driver.get_port.return_value = port_mock
        ports = net_task.execute(self.amphora_mock)
        self.assertEqual(1, len(ports))

    @mock.patch('octavia.db.repositories.AmphoraRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=mock.MagicMock())
    def test_plug_ports(self, mock_session, mock_get, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get.return_value = self.db_amphora_mock
        mock_get_net_driver.return_value = mock_driver

        port1 = mock.MagicMock()
        port2 = mock.MagicMock()
        amp = {constants.ID: AMPHORA_ID,
               constants.COMPUTE_ID: '1234'}
        plugports = network_tasks.PlugPorts()
        plugports.execute(amp, [port1, port2])

        mock_driver.plug_port.assert_any_call(self.db_amphora_mock, port1)
        mock_driver.plug_port.assert_any_call(self.db_amphora_mock, port2)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=_session_mock)
    def test_update_vip_sg(self, mock_session, mock_lb_get,
                           mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_driver.update_vip_sg.return_value = SG_ID
        mock_lb_get.return_value = LB
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.UpdateVIPSecurityGroup()

        sg_id = net.execute(self.load_balancer_mock)
        mock_driver.update_vip_sg.assert_called_once_with(LB, LB.vip)
        self.assertEqual(sg_id, SG_ID)

    def test_get_subnet_from_vip(self, mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.GetSubnetFromVIP()

        net.execute(self.load_balancer_mock)
        mock_driver.get_subnet.assert_called_once_with(
            SUBNET_ID)

    @mock.patch('octavia.db.repositories.AmphoraRepository.get')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=_session_mock)
    def test_plug_vip_amphora(self, mock_session, mock_lb_get, mock_get,
                              mock_get_net_driver):
        mock_driver = mock.MagicMock()
        amphora = {constants.ID: AMPHORA_ID,
                   constants.LB_NETWORK_IP: IP_ADDRESS}
        mock_lb_get.return_value = LB
        mock_get.return_value = self.db_amphora_mock
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.PlugVIPAmphora()
        subnet = {constants.ID: SUBNET_ID}
        mockSubnet = mock.MagicMock()
        mock_driver.get_subnet.return_value = mockSubnet
        net.execute(self.load_balancer_mock, amphora, subnet)
        mock_driver.plug_aap_port.assert_called_once_with(
            LB, LB.vip, self.db_amphora_mock, mockSubnet)

    @mock.patch('octavia.db.repositories.AmphoraRepository.get')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=_session_mock)
    def test_revert_plug_vip_amphora(self, mock_session, mock_lb_get, mock_get,
                                     mock_get_net_driver):
        mock_driver = mock.MagicMock()
        mock_lb_get.return_value = LB
        mock_get.return_value = self.db_amphora_mock
        mock_get_net_driver.return_value = mock_driver
        net = network_tasks.PlugVIPAmphora()
        amphora = {constants.ID: AMPHORA_ID,
                   constants.LB_NETWORK_IP: IP_ADDRESS}
        subnet = {constants.ID: SUBNET_ID}
        mockSubnet = mock.MagicMock()
        mock_driver.get_subnet.return_value = mockSubnet
        net.revert(AMPS_DATA[0].to_dict(), self.load_balancer_mock,
                   amphora, subnet)
        mock_driver.unplug_aap_port.assert_called_once_with(
            LB.vip, self.db_amphora_mock, mockSubnet)

    @mock.patch('octavia.controller.worker.v2.tasks.network_tasks.DeletePort.'
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
        VIP_IP_ADDRESS2 = 'fd08::1'
        mock_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_driver
        vip_dict = {constants.IP_ADDRESS: VIP_IP_ADDRESS,
                    constants.NETWORK_ID: VIP_NETWORK_ID,
                    constants.QOS_POLICY_ID: VIP_QOS_ID,
                    constants.SUBNET_ID: VIP_SUBNET_ID}
        port_mock = mock.MagicMock()
        port_mock.id = PORT_ID
        additional_vips = [{constants.IP_ADDRESS: VIP_IP_ADDRESS2}]

        mock_driver.create_port.side_effect = [
            port_mock, exceptions.OctaviaException('boom'),
            exceptions.OctaviaException('boom'),
            exceptions.OctaviaException('boom')]
        mock_driver.delete_port.side_effect = [mock.DEFAULT, Exception('boom')]

        net_task = network_tasks.CreateVIPBasePort()

        # Limit the retry attempts for the test run to save time
        net_task.execute.retry.stop = tenacity.stop_after_attempt(2)

        # Test execute
        result = net_task.execute(vip_dict, VIP_SG_ID, AMP_ID, additional_vips)

        self.assertEqual(port_mock.to_dict(), result)
        mock_driver.create_port.assert_called_once_with(
            VIP_NETWORK_ID, name=constants.AMP_BASE_PORT_PREFIX + AMP_ID,
            fixed_ips=[{constants.SUBNET_ID: VIP_SUBNET_ID}],
            secondary_ips=[VIP_IP_ADDRESS, VIP_IP_ADDRESS2],
            security_group_ids=[VIP_SG_ID],
            qos_policy_id=VIP_QOS_ID)

        # Test execute exception
        mock_driver.reset_mock()

        self.assertRaises(exceptions.OctaviaException, net_task.execute,
                          vip_dict, None, AMP_ID, additional_vips)

        # Test revert when this task failed
        mock_driver.reset_mock()

        net_task.revert(failure.Failure.from_exception(Exception('boom')),
                        vip_dict, VIP_SG_ID, AMP_ID, additional_vips)

        mock_driver.delete_port.assert_not_called()

        # Test revert
        mock_driver.reset_mock()

        net_task.revert([port_mock], vip_dict, VIP_SG_ID, AMP_ID,
                        additional_vips)

        mock_driver.delete_port.assert_called_once_with(PORT_ID)

        # Test revert exception
        mock_driver.reset_mock()

        net_task.revert([port_mock], vip_dict, VIP_SG_ID, AMP_ID,
                        additional_vips)

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
