#    Copyright 2014 Rackspace
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import copy
import random

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils
from sqlalchemy.orm import exc as sa_exception

from octavia.api.drivers import exceptions as provider_exceptions
from octavia.common import constants
import octavia.common.context
from octavia.common import data_models
from octavia.common import exceptions
from octavia.network import base as network_base
from octavia.network import data_models as network_models
from octavia.tests.functional.api.v2 import base


class TestLoadBalancer(base.BaseAPITest):
    root_tag = 'loadbalancer'
    root_tag_list = 'loadbalancers'
    root_tag_links = 'loadbalancers_links'

    def _assert_request_matches_response(self, req, resp, **optionals):
        self.assertTrue(uuidutils.is_uuid_like(resp.get('id')))
        req_name = req.get('name')
        req_description = req.get('description')
        if not req_name:
            self.assertEqual('', resp.get('name'))
        else:
            self.assertEqual(req.get('name'), resp.get('name'))
        if not req_description:
            self.assertEqual('', resp.get('description'))
        else:
            self.assertEqual(req.get('description'), resp.get('description'))
        self.assertEqual(constants.PENDING_CREATE,
                         resp.get('provisioning_status'))
        self.assertEqual(constants.OFFLINE, resp.get('operating_status'))
        self.assertEqual(req.get('admin_state_up', True),
                         resp.get('admin_state_up'))
        self.assertIsNotNone(resp.get('created_at'))
        self.assertIsNone(resp.get('updated_at'))
        for key, value in optionals.items():
            self.assertEqual(value, req.get(key))

    def test_empty_list(self):
        response = self.get(self.LBS_PATH)
        api_list = response.json.get(self.root_tag_list)
        self.assertEqual([], api_list)

    def test_create(self, **optionals):
        lb_json = {'name': 'test1',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id,
                   'tags': ['test_tag1', 'test_tag2']
                   }
        lb_json.update(optionals)
        body = self._build_body(lb_json)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        return api_lb

    # Make sure the /v2.0 alias is maintained for the life of the v2 API
    def test_create_v2_0(self, **optionals):
        lb_json = {'name': 'test1',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id
                   }
        lb_json.update(optionals)
        body = self._build_body(lb_json)
        response = self.post(self.LBS_PATH, body, use_v2_0=True)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        return api_lb

    def test_create_using_tenant_id(self):
        lb_json = {'name': 'test1',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'tenant_id': self.project_id
                   }
        body = self._build_body(lb_json)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        return api_lb

    def test_create_without_vip(self):
        lb_json = {'name': 'test1',
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        response = self.post(self.LBS_PATH, body, status=400)
        err_msg = ('Validation failure: VIP must contain one of: '
                   'vip_port_id, vip_network_id, vip_subnet_id.')
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_empty_vip(self):
        lb_json = {'vip_subnet_id': '',
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        response = self.post(self.LBS_PATH, body, status=400)
        err_msg = ("Invalid input for field/attribute vip_subnet_id. "
                   "Value: ''. Value should be UUID format")
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_invalid_vip_subnet(self):
        subnet_id = uuidutils.generate_uuid()
        lb_json = {'vip_subnet_id': subnet_id,
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch("octavia.network.drivers.noop_driver.driver"
                        ".NoopManager.get_subnet") as mock_get_subnet:
            mock_get_subnet.side_effect = network_base.SubnetNotFound
            response = self.post(self.LBS_PATH, body, status=400)
            err_msg = 'Subnet {} not found.'.format(subnet_id)
            self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_invalid_vip_network_subnet(self):
        network = network_models.Network(id=uuidutils.generate_uuid(),
                                         subnets=[])
        subnet_id = uuidutils.generate_uuid()
        lb_json = {
            'vip_subnet_id': subnet_id,
            'vip_network_id': network.id,
            'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch("octavia.network.drivers.noop_driver.driver"
                        ".NoopManager.get_network") as mock_get_network:
            mock_get_network.return_value = network
            response = self.post(self.LBS_PATH, body, status=400)
            err_msg = 'Subnet {} not found.'.format(subnet_id)
            self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_vip_subnet_fills_network(self):
        subnet = network_models.Subnet(id=uuidutils.generate_uuid(),
                                       network_id=uuidutils.generate_uuid())
        lb_json = {'vip_subnet_id': subnet.id,
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch("octavia.network.drivers.noop_driver.driver"
                        ".NoopManager.get_subnet") as mock_get_subnet:
            mock_get_subnet.return_value = subnet
            response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        self.assertEqual(subnet.id, api_lb.get('vip_subnet_id'))
        self.assertEqual(subnet.network_id, api_lb.get('vip_network_id'))

    def test_create_with_vip_network_has_no_subnet(self):
        network = network_models.Network(id=uuidutils.generate_uuid(),
                                         subnets=[])
        lb_json = {
            'vip_network_id': network.id,
            'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch("octavia.network.drivers.noop_driver.driver"
                        ".NoopManager.get_network") as mock_get_network:
            mock_get_network.return_value = network
            response = self.post(self.LBS_PATH, body, status=400)
            err_msg = ("Validation failure: "
                       "Supplied network does not contain a subnet.")
            self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_vip_network_picks_subnet_ipv4(self):
        network_id = uuidutils.generate_uuid()
        subnet1 = network_models.Subnet(id=uuidutils.generate_uuid(),
                                        network_id=network_id,
                                        ip_version=6)
        subnet2 = network_models.Subnet(id=uuidutils.generate_uuid(),
                                        network_id=network_id,
                                        ip_version=4)
        network = network_models.Network(id=network_id,
                                         subnets=[subnet1.id, subnet2.id])
        lb_json = {'vip_network_id': network.id,
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_subnet") as mock_get_subnet:
            mock_get_network.return_value = network
            mock_get_subnet.side_effect = [subnet1, subnet2]
            response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        self.assertEqual(subnet2.id, api_lb.get('vip_subnet_id'))
        self.assertEqual(network_id, api_lb.get('vip_network_id'))

    def test_create_with_vip_network_picks_subnet_ipv6(self):
        network_id = uuidutils.generate_uuid()
        subnet = network_models.Subnet(id=uuidutils.generate_uuid(),
                                       network_id=network_id,
                                       ip_version=6)
        network = network_models.Network(id=network_id,
                                         subnets=[subnet.id])
        lb_json = {'vip_network_id': network_id,
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_subnet") as mock_get_subnet:
            mock_get_network.return_value = network
            mock_get_subnet.return_value = subnet
            response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        self.assertEqual(subnet.id, api_lb.get('vip_subnet_id'))
        self.assertEqual(network_id, api_lb.get('vip_network_id'))

    def test_create_with_vip_network_and_address(self):
        ip_address = '198.51.100.10'
        network_id = uuidutils.generate_uuid()
        subnet1 = network_models.Subnet(id=uuidutils.generate_uuid(),
                                        network_id=network_id,
                                        cidr='2001:DB8::/32',
                                        ip_version=6)
        subnet2 = network_models.Subnet(id=uuidutils.generate_uuid(),
                                        network_id=network_id,
                                        cidr='198.51.100.0/24',
                                        ip_version=4)
        network = network_models.Network(id=network_id,
                                         subnets=[subnet1.id, subnet2.id])
        lb_json = {'vip_network_id': network.id,
                   'vip_address': ip_address,
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_subnet") as mock_get_subnet:
            mock_get_network.return_value = network
            mock_get_subnet.side_effect = [subnet1, subnet2]
            response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        self.assertEqual(subnet2.id, api_lb.get('vip_subnet_id'))
        self.assertEqual(network.id, api_lb.get('vip_network_id'))
        self.assertEqual(ip_address, api_lb.get('vip_address'))

    def test_create_with_vip_network_and_address_no_subnet_match(self):
        ip_address = '198.51.100.10'
        network_id = uuidutils.generate_uuid()
        subnet1 = network_models.Subnet(id=uuidutils.generate_uuid(),
                                        network_id=network_id,
                                        cidr='2001:DB8::/32',
                                        ip_version=6)
        subnet2 = network_models.Subnet(id=uuidutils.generate_uuid(),
                                        network_id=network_id,
                                        cidr='203.0.113.0/24',
                                        ip_version=4)
        network = network_models.Network(id=network_id,
                                         subnets=[subnet1.id, subnet2.id])
        lb_json = {'vip_network_id': network.id,
                   'vip_address': ip_address,
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_subnet") as mock_get_subnet:
            mock_get_network.return_value = network
            mock_get_subnet.side_effect = [subnet1, subnet2]
            response = self.post(self.LBS_PATH, body, status=400)
        err_msg = ('Validation failure: Supplied network does not contain a '
                   'subnet for VIP address specified.')
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_vip_network_and_address_ipv6(self):
        ip_address = '2001:DB8::10'
        network_id = uuidutils.generate_uuid()
        subnet1 = network_models.Subnet(id=uuidutils.generate_uuid(),
                                        network_id=network_id,
                                        cidr='2001:DB8::/32',
                                        ip_version=6)
        subnet2 = network_models.Subnet(id=uuidutils.generate_uuid(),
                                        network_id=network_id,
                                        cidr='198.51.100.0/24',
                                        ip_version=4)
        network = network_models.Network(id=network_id,
                                         subnets=[subnet1.id, subnet2.id])
        lb_json = {'vip_network_id': network.id,
                   'vip_address': ip_address,
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_subnet") as mock_get_subnet:
            mock_get_network.return_value = network
            mock_get_subnet.side_effect = [subnet1, subnet2]
            response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        self.assertEqual(subnet1.id, api_lb.get('vip_subnet_id'))
        self.assertEqual(network.id, api_lb.get('vip_network_id'))
        self.assertEqual(ip_address, api_lb.get('vip_address'))

    # Note: This test is using the unique local address range to
    #       validate that we handle a fully expaned IP address properly.
    #       This is not possible with the documentation/testnet range.
    def test_create_with_vip_network_and_address_full_ipv6(self):
        ip_address = 'fdff:ffff:ffff:ffff:ffff:ffff:ffff:ffff'
        network_id = uuidutils.generate_uuid()
        subnet1 = network_models.Subnet(id=uuidutils.generate_uuid(),
                                        network_id=network_id,
                                        cidr='fc00::/7',
                                        ip_version=6)
        subnet2 = network_models.Subnet(id=uuidutils.generate_uuid(),
                                        network_id=network_id,
                                        cidr='198.51.100.0/24',
                                        ip_version=4)
        network = network_models.Network(id=network_id,
                                         subnets=[subnet1.id, subnet2.id])
        lb_json = {'vip_network_id': network.id,
                   'vip_address': ip_address,
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_subnet") as mock_get_subnet:
            mock_get_network.return_value = network
            mock_get_subnet.side_effect = [subnet1, subnet2]
            response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        self.assertEqual(subnet1.id, api_lb.get('vip_subnet_id'))
        self.assertEqual(network.id, api_lb.get('vip_network_id'))
        self.assertEqual(ip_address, api_lb.get('vip_address'))

    def test_create_with_vip_port_1_fixed_ip(self):
        ip_address = '198.51.100.1'
        subnet = network_models.Subnet(id=uuidutils.generate_uuid())
        network = network_models.Network(id=uuidutils.generate_uuid(),
                                         subnets=[subnet])
        fixed_ip = network_models.FixedIP(subnet_id=subnet.id,
                                          ip_address=ip_address)
        port = network_models.Port(id=uuidutils.generate_uuid(),
                                   fixed_ips=[fixed_ip],
                                   network_id=network.id)
        lb_json = {
            'name': 'test1', 'description': 'test1_desc',
            'vip_port_id': port.id, 'admin_state_up': False,
            'project_id': self.project_id}
        body = self._build_body(lb_json)
        # This test needs the provider driver to not supply the VIP port
        # so mocking noop to not supply a VIP port.
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_port") as mock_get_port, mock.patch(
            "octavia.api.drivers.noop_driver.driver.NoopManager."
                "create_vip_port") as mock_provider:
            mock_get_network.return_value = network
            mock_get_port.return_value = port
            mock_provider.side_effect = (provider_exceptions.
                                         NotImplementedError())
            response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        self.assertEqual(ip_address, api_lb.get('vip_address'))
        self.assertEqual(subnet.id, api_lb.get('vip_subnet_id'))
        self.assertEqual(network.id, api_lb.get('vip_network_id'))
        self.assertEqual(port.id, api_lb.get('vip_port_id'))

    def test_create_with_vip_port_2_fixed_ip(self):
        ip_address = '198.51.100.1'
        subnet = network_models.Subnet(id=uuidutils.generate_uuid())
        network = network_models.Network(id=uuidutils.generate_uuid(),
                                         subnets=[subnet])
        fixed_ip = network_models.FixedIP(subnet_id=subnet.id,
                                          ip_address=ip_address)
        fixed_ip_2 = network_models.FixedIP(
            subnet_id=uuidutils.generate_uuid(), ip_address='203.0.113.5')
        port = network_models.Port(id=uuidutils.generate_uuid(),
                                   fixed_ips=[fixed_ip, fixed_ip_2],
                                   network_id=network.id)
        lb_json = {
            'name': 'test1', 'description': 'test1_desc',
            'vip_port_id': port.id, 'admin_state_up': False,
            'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_port") as mock_get_port:
            mock_get_network.return_value = network
            mock_get_port.return_value = port
            response = self.post(self.LBS_PATH, body, status=400)
            err_msg = ("Validation failure: "
                       "VIP port's subnet could not be determined. Please "
                       "specify either a VIP subnet or address.")
            self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_vip_port_and_address(self):
        ip_address = '198.51.100.1'
        subnet = network_models.Subnet(id=uuidutils.generate_uuid())
        network = network_models.Network(id=uuidutils.generate_uuid(),
                                         subnets=[subnet])
        fixed_ip = network_models.FixedIP(subnet_id=subnet.id,
                                          ip_address=ip_address)
        port = network_models.Port(id=uuidutils.generate_uuid(),
                                   fixed_ips=[fixed_ip],
                                   network_id=network.id)
        lb_json = {
            'name': 'test1', 'description': 'test1_desc',
            'vip_port_id': port.id, 'vip_address': ip_address,
            'admin_state_up': False, 'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_port") as mock_get_port:
            mock_get_network.return_value = network
            mock_get_port.return_value = port
            response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        self.assertEqual(ip_address, api_lb.get('vip_address'))
        self.assertEqual(subnet.id, api_lb.get('vip_subnet_id'))
        self.assertEqual(network.id, api_lb.get('vip_network_id'))
        self.assertEqual(port.id, api_lb.get('vip_port_id'))

    def test_create_with_vip_port_and_bad_address(self):
        ip_address = '198.51.100.1'
        subnet = network_models.Subnet(id=uuidutils.generate_uuid())
        network = network_models.Network(id=uuidutils.generate_uuid(),
                                         subnets=[subnet])
        fixed_ip = network_models.FixedIP(subnet_id=subnet.id,
                                          ip_address=ip_address)
        port = network_models.Port(id=uuidutils.generate_uuid(),
                                   fixed_ips=[fixed_ip],
                                   network_id=network.id)
        lb_json = {
            'name': 'test1', 'description': 'test1_desc',
            'vip_port_id': port.id, 'vip_address': '203.0.113.7',
            'admin_state_up': False, 'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_port") as mock_get_port:
            mock_get_network.return_value = network
            mock_get_port.return_value = port
            response = self.post(self.LBS_PATH, body, status=400)
        err_msg = ("Validation failure: "
                   "Specified VIP address not found on the specified VIP "
                   "port.")
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_vip_full(self):
        subnet = network_models.Subnet(id=uuidutils.generate_uuid())
        network = network_models.Network(id=uuidutils.generate_uuid(),
                                         subnets=[subnet])
        port = network_models.Port(id=uuidutils.generate_uuid(),
                                   network_id=network.id)
        lb_json = {
            'name': 'test1', 'description': 'test1_desc',
            'vip_address': '10.0.0.1', 'vip_subnet_id': subnet.id,
            'vip_network_id': network.id, 'vip_port_id': port.id,
            'admin_state_up': False, 'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_port") as mock_get_port:
            mock_get_network.return_value = network
            mock_get_port.return_value = port
            response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        self.assertEqual('10.0.0.1', api_lb.get('vip_address'))
        self.assertEqual(subnet.id, api_lb.get('vip_subnet_id'))
        self.assertEqual(network.id, api_lb.get('vip_network_id'))
        self.assertEqual(port.id, api_lb.get('vip_port_id'))

    def test_create_neutron_failure(self):

        class TestNeutronException(network_base.AllocateVIPException):
            def __init__(self, message, orig_msg, orig_code):
                super(TestNeutronException, self).__init__(
                    message, orig_msg=orig_msg, orig_code=orig_code,
                )

            def __str__(self):
                return repr(self.message)

        subnet = network_models.Subnet(id=uuidutils.generate_uuid())
        network = network_models.Network(id=uuidutils.generate_uuid(),
                                         subnets=[subnet])
        port = network_models.Port(id=uuidutils.generate_uuid(),
                                   network_id=network.id)
        lb_json = {
            'name': 'test1', 'description': 'test1_desc',
            'vip_address': '10.0.0.1', 'vip_subnet_id': subnet.id,
            'vip_network_id': network.id, 'vip_port_id': port.id,
            'admin_state_up': False, 'project_id': self.project_id}
        body = self._build_body(lb_json)
        # This test needs the provider driver to not supply the VIP port
        # so mocking noop to not supply a VIP port.
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_port") as mock_get_port, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".allocate_vip") as mock_allocate_vip, mock.patch(
            "octavia.api.drivers.noop_driver.driver.NoopManager."
                "create_vip_port") as mock_provider:
            mock_get_network.return_value = network
            mock_get_port.return_value = port
            mock_allocate_vip.side_effect = TestNeutronException(
                "octavia_msg", "neutron_msg", 409)
            mock_provider.side_effect = (provider_exceptions.
                                         NotImplementedError())
            response = self.post(self.LBS_PATH, body, status=409)
        # Make sure the faultstring contains the neutron error and not
        # the octavia error message
        self.assertIn("neutron_msg", response.json.get("faultstring"))

    def test_create_with_qos(self):
        subnet = network_models.Subnet(id=uuidutils.generate_uuid(),
                                       network_id=uuidutils.generate_uuid())
        qos_policy_id = uuidutils.generate_uuid()
        # Test with specific vip_qos_policy_id
        lb_json = {'vip_subnet_id': subnet.id,
                   'project_id': self.project_id,
                   'vip_qos_policy_id': qos_policy_id}
        body = self._build_body(lb_json)
        with mock.patch("octavia.network.drivers.noop_driver.driver"
                        ".NoopManager.get_subnet") as mock_get_subnet:
            with mock.patch("octavia.common.validate."
                            "qos_policy_exists") as mock_get_qos:
                mock_get_subnet.return_value = subnet
                mock_get_qos.return_value = qos_policy_id
                response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        self.assertEqual(subnet.id, api_lb.get('vip_subnet_id'))
        self.assertEqual(qos_policy_id, api_lb.get('vip_qos_policy_id'))

    def test_create_with_qos_vip_port(self):
        # Test with vip_port_id which applied qos_policy
        subnet = network_models.Subnet(id=uuidutils.generate_uuid(),
                                       network_id=uuidutils.generate_uuid())
        port_qos_policy_id = uuidutils.generate_uuid()
        ip_address = '192.168.50.50'
        network = network_models.Network(id=uuidutils.generate_uuid(),
                                         subnets=[subnet])
        fixed_ip = network_models.FixedIP(subnet_id=subnet.id,
                                          ip_address=ip_address)
        port = network_models.Port(id=uuidutils.generate_uuid(),
                                   fixed_ips=[fixed_ip],
                                   network_id=network.id,
                                   qos_policy_id=port_qos_policy_id)
        lb_json = {'vip_port_id': port.id,
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver."
                "NoopManager.get_network") as m_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_port") as mock_get_port, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".allocate_vip") as mock_allocate_vip, mock.patch(
            "octavia.common.validate."
                "qos_policy_exists") as m_get_qos:
            m_get_qos.return_value = port_qos_policy_id
            mock_allocate_vip.return_value = data_models.Vip(
                ip_address=ip_address, subnet_id=subnet.id,
                network_id=network.id, port_id=port.id)
            m_get_network.return_value = network
            mock_get_port.return_value = port
            response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        self.assertEqual(port.id, api_lb.get('vip_port_id'))
        self.assertEqual(subnet.id, api_lb.get('vip_subnet_id'))
        self.assertEqual(network.id, api_lb.get('vip_network_id'))
        self.assertEqual(port_qos_policy_id, api_lb.get(
            'vip_qos_policy_id'))

    def test_create_with_qos_vip_port_and_vip_qos(self):
        subnet = network_models.Subnet(id=uuidutils.generate_uuid(),
                                       network_id=uuidutils.generate_uuid())
        port_qos_policy_id = uuidutils.generate_uuid()
        new_qos_policy_id = uuidutils.generate_uuid()
        ip_address = '192.168.50.50'
        network = network_models.Network(id=uuidutils.generate_uuid(),
                                         subnets=[subnet])
        fixed_ip = network_models.FixedIP(subnet_id=subnet.id,
                                          ip_address=ip_address)
        port = network_models.Port(id=uuidutils.generate_uuid(),
                                   fixed_ips=[fixed_ip],
                                   network_id=network.id,
                                   qos_policy_id=port_qos_policy_id)
        lb_json = {'vip_port_id': port.id,
                   'project_id': self.project_id,
                   'vip_qos_policy_id': new_qos_policy_id}
        body = self._build_body(lb_json)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver."
                "NoopManager.get_network") as m_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_port") as mock_get_port, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".allocate_vip") as mock_allocate_vip, mock.patch(
            "octavia.common.validate."
                "qos_policy_exists") as m_get_qos:
            m_get_qos.return_value = mock.ANY
            mock_allocate_vip.return_value = data_models.Vip(
                ip_address=ip_address, subnet_id=subnet.id,
                network_id=network.id, port_id=port.id)
            m_get_network.return_value = network
            mock_get_port.return_value = port
            response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        self.assertEqual(port.id, api_lb.get('vip_port_id'))
        self.assertEqual(subnet.id, api_lb.get('vip_subnet_id'))
        self.assertEqual(network.id, api_lb.get('vip_network_id'))
        self.assertEqual(new_qos_policy_id, api_lb.get(
            'vip_qos_policy_id'))

    def test_create_with_non_exist_qos_policy_id(self):
        subnet = network_models.Subnet(id=uuidutils.generate_uuid(),
                                       network_id=uuidutils.generate_uuid())
        qos_policy_id = uuidutils.generate_uuid()
        lb_json = {'vip_subnet_id': subnet.id,
                   'project_id': self.project_id,
                   'vip_qos_policy_id': qos_policy_id}
        body = self._build_body(lb_json)
        with mock.patch("octavia.network.drivers.noop_driver.driver"
                        ".NoopManager.get_subnet") as mock_get_subnet:
            with mock.patch("octavia.network.drivers.noop_driver."
                            "driver.NoopManager."
                            "get_qos_policy") as mock_get_qos:
                mock_get_subnet.return_value = subnet
                mock_get_qos.side_effect = Exception()
                response = self.post(self.LBS_PATH, body, status=400)
        err_msg = "qos_policy %s not found." % qos_policy_id
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_long_name(self):
        lb_json = {'name': 'n' * 256,
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id}
        response = self.post(self.LBS_PATH, self._build_body(lb_json),
                             status=400)
        self.assertIn('Invalid input for field/attribute name',
                      response.json.get('faultstring'))

    def test_create_with_long_description(self):
        lb_json = {'description': 'n' * 256,
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id}
        response = self.post(self.LBS_PATH, self._build_body(lb_json),
                             status=400)
        self.assertIn('Invalid input for field/attribute description',
                      response.json.get('faultstring'))

    def test_create_with_nonuuid_vip_attributes(self):
        lb_json = {'vip_subnet_id': 'HI',
                   'project_id': self.project_id}
        response = self.post(self.LBS_PATH, self._build_body(lb_json),
                             status=400)
        self.assertIn('Invalid input for field/attribute vip_subnet_id',
                      response.json.get('faultstring'))

    def test_create_with_allowed_network_id(self):
        network_id = uuidutils.generate_uuid()
        self.conf.config(group="networking", valid_vip_networks=network_id)
        subnet = network_models.Subnet(id=uuidutils.generate_uuid(),
                                       network_id=network_id,
                                       ip_version=4)
        network = network_models.Network(id=network_id, subnets=[subnet.id])
        lb_json = {'vip_network_id': network.id,
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_subnet") as mock_get_subnet:
            mock_get_network.return_value = network
            mock_get_subnet.return_value = subnet
            response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        self.assertEqual(subnet.id, api_lb.get('vip_subnet_id'))
        self.assertEqual(network_id, api_lb.get('vip_network_id'))

    def test_create_with_disallowed_network_id(self):
        network_id1 = uuidutils.generate_uuid()
        network_id2 = uuidutils.generate_uuid()
        self.conf.config(group="networking", valid_vip_networks=network_id1)
        subnet = network_models.Subnet(id=uuidutils.generate_uuid(),
                                       network_id=network_id2,
                                       ip_version=4)
        network = network_models.Network(id=network_id2, subnets=[subnet.id])
        lb_json = {'vip_network_id': network.id,
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_subnet") as mock_get_subnet:
            mock_get_network.return_value = network
            mock_get_subnet.return_value = subnet
            response = self.post(self.LBS_PATH, body, status=400)
        self.assertIn("Supplied VIP network_id is not allowed",
                      response.json.get('faultstring'))

    def test_create_with_disallowed_vip_objects(self):
        self.conf.config(group="networking", allow_vip_network_id=False)
        self.conf.config(group="networking", allow_vip_subnet_id=False)
        self.conf.config(group="networking", allow_vip_port_id=False)

        lb_json = {'vip_network_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id}
        response = self.post(self.LBS_PATH, self._build_body(lb_json),
                             status=400)
        self.assertIn('use of vip_network_id is disallowed',
                      response.json.get('faultstring'))

        lb_json = {'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id}
        response = self.post(self.LBS_PATH, self._build_body(lb_json),
                             status=400)
        self.assertIn('use of vip_subnet_id is disallowed',
                      response.json.get('faultstring'))

        lb_json = {'vip_port_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id}
        response = self.post(self.LBS_PATH, self._build_body(lb_json),
                             status=400)
        self.assertIn('use of vip_port_id is disallowed',
                      response.json.get('faultstring'))

    def test_create_with_project_id(self):
        project_id = uuidutils.generate_uuid()
        api_lb = self.test_create(project_id=project_id)
        self.assertEqual(project_id, api_lb.get('project_id'))

    def test_create_no_project_id(self, **optionals):
        lb_json = {'name': 'test1',
                   'vip_subnet_id': uuidutils.generate_uuid()
                   }
        lb_json.update(optionals)
        body = self._build_body(lb_json)
        self.post(self.LBS_PATH, body, status=400)

    def test_create_context_project_id(self, **optionals):
        lb_json = {'name': 'test1',
                   'vip_subnet_id': uuidutils.generate_uuid()
                   }
        lb_json.update(optionals)
        body = self._build_body(lb_json)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)

    def test_create_authorized(self, **optionals):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        project_id = uuidutils.generate_uuid()
        lb_json = {'name': 'test1',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': project_id
                   }
        lb_json.update(optionals)
        body = self._build_body(lb_json)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self._assert_request_matches_response(lb_json, api_lb)

    def test_create_not_authorized(self, **optionals):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        lb_json = {'name': 'test1',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': uuidutils.generate_uuid()
                   }
        lb_json.update(optionals)
        body = self._build_body(lb_json)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            response = self.post(self.LBS_PATH, body, status=403)
        api_lb = response.json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, api_lb)

    def test_create_provider_octavia(self, **optionals):
        lb_json = {'name': 'test1',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id,
                   'provider': constants.OCTAVIA
                   }
        lb_json.update(optionals)
        body = self._build_body(lb_json)
        with mock.patch('oslo_messaging.get_rpc_transport'):
            with mock.patch('oslo_messaging.Target'):
                with mock.patch('oslo_messaging.RPCClient'):
                    response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_request_matches_response(lb_json, api_lb)
        return api_lb

    def test_create_provider_bogus(self, **optionals):
        lb_json = {'name': 'test1',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id,
                   'provider': 'BOGUS'
                   }
        lb_json.update(optionals)
        body = self._build_body(lb_json)
        response = self.post(self.LBS_PATH, body, status=400)
        self.assertIn("Provider 'BOGUS' is not enabled.",
                      response.json.get('faultstring'))

    def test_create_flavor_bad_type(self, **optionals):
        lb_json = {'name': 'test1',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id,
                   'flavor_id': 'BOGUS'
                   }
        lb_json.update(optionals)
        body = self._build_body(lb_json)
        response = self.post(self.LBS_PATH, body, status=400)
        self.assertIn("Invalid input for field/attribute flavor_id. Value: "
                      "'BOGUS'. Value should be UUID format",
                      response.json.get('faultstring'))

    def test_create_flavor_invalid(self, **optionals):
        lb_json = {'name': 'test1',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id,
                   'flavor_id': uuidutils.generate_uuid()
                   }
        lb_json.update(optionals)
        body = self._build_body(lb_json)
        response = self.post(self.LBS_PATH, body, status=400)
        self.assertIn("Validation failure: Invalid flavor_id.",
                      response.json.get('faultstring'))

    def test_create_flavor_disabled(self, **optionals):
        fp = self.create_flavor_profile('test1', 'noop_driver',
                                        '{"image": "ubuntu"}')
        flavor = self.create_flavor('name1', 'description',
                                    fp.get('id'), False)
        test_flavor_id = flavor.get('id')
        lb_json = {'name': 'test1',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id,
                   'flavor_id': test_flavor_id,
                   }
        lb_json.update(optionals)
        body = self._build_body(lb_json)
        response = self.post(self.LBS_PATH, body, status=400)
        ref_faultstring = ('The selected flavor is not allowed in this '
                           'deployment: {}'.format(test_flavor_id))
        self.assertEqual(ref_faultstring, response.json.get('faultstring'))

    def test_create_flavor_missing(self, **optionals):
        fp = self.create_flavor_profile('test1', 'noop_driver',
                                        '{"image": "ubuntu"}')
        flavor = self.create_flavor('name1', 'description', fp.get('id'), True)
        test_flavor_id = flavor.get('id')
        lb_json = {'name': 'test1',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id,
                   'flavor_id': test_flavor_id
                   }
        lb_json.update(optionals)
        body = self._build_body(lb_json)
        with mock.patch('octavia.db.repositories.FlavorRepository.'
                        'get_flavor_metadata_dict',
                        side_effect=sa_exception.NoResultFound):
            response = self.post(self.LBS_PATH, body, status=400)
        self.assertIn("Validation failure: Invalid flavor_id.",
                      response.json.get('faultstring'))

    def test_create_flavor_no_provider(self, **optionals):
        fp = self.create_flavor_profile('test1', 'noop_driver',
                                        '{"image": "ubuntu"}')
        flavor = self.create_flavor('name1', 'description', fp.get('id'), True)
        test_flavor_id = flavor.get('id')
        lb_json = {'name': 'test1',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id,
                   'flavor_id': test_flavor_id,
                   }
        lb_json.update(optionals)
        body = self._build_body(lb_json)
        response = self.post(self.LBS_PATH, body, status=201)
        api_lb = response.json.get(self.root_tag)
        self.assertEqual('noop_driver', api_lb.get('provider'))
        self.assertEqual(test_flavor_id, api_lb.get('flavor_id'))

    def test_matching_providers(self, **optionals):
        fp = self.create_flavor_profile('test1', 'noop_driver',
                                        '{"image": "ubuntu"}')
        flavor = self.create_flavor('name1', 'description', fp.get('id'), True)
        test_flavor_id = flavor.get('id')
        lb_json = {'name': 'test1',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id,
                   'flavor_id': test_flavor_id,
                   'provider': 'noop_driver'
                   }
        lb_json.update(optionals)
        body = self._build_body(lb_json)
        response = self.post(self.LBS_PATH, body, status=201)
        api_lb = response.json.get(self.root_tag)
        self.assertEqual('noop_driver', api_lb.get('provider'))
        self.assertEqual(test_flavor_id, api_lb.get('flavor_id'))

    def test_conflicting_providers(self, **optionals):
        fp = self.create_flavor_profile('test1', 'noop_driver',
                                        '{"image": "ubuntu"}')
        flavor = self.create_flavor('name1', 'description', fp.get('id'), True)
        test_flavor_id = flavor.get('id')
        lb_json = {'name': 'test1',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id,
                   'flavor_id': test_flavor_id,
                   'provider': 'noop_driver-alt'
                   }
        lb_json.update(optionals)
        body = self._build_body(lb_json)
        response = self.post(self.LBS_PATH, body, status=400)
        self.assertIn("Flavor '{}' is not compatible with provider "
                      "'noop_driver-alt'".format(test_flavor_id),
                      response.json.get('faultstring'))

    def test_get_all_admin(self):
        project_id = uuidutils.generate_uuid()
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb1', project_id=self.project_id,
                                        tags=['test_tag1'])
        lb2 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb2', project_id=project_id,
                                        tags=['test_tag2'])
        lb3 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb3', project_id=project_id,
                                        tags=['test_tag3'])
        response = self.get(self.LBS_PATH)
        lbs = response.json.get(self.root_tag_list)
        self.assertEqual(3, len(lbs))
        lb_id_names = [(lb.get('id'),
                        lb.get('name'),
                        lb.get('tags')) for lb in lbs]
        lb1 = lb1.get(self.root_tag)
        lb2 = lb2.get(self.root_tag)
        lb3 = lb3.get(self.root_tag)
        self.assertIn((lb1.get('id'), lb1.get('name'), lb1.get('tags')),
                      lb_id_names)
        self.assertIn((lb2.get('id'), lb2.get('name'), lb2.get('tags')),
                      lb_id_names)
        self.assertIn((lb3.get('id'), lb3.get('name'), lb3.get('tags')),
                      lb_id_names)

    def test_get_all_non_admin(self):
        project_id = uuidutils.generate_uuid()
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb1', project_id=project_id)
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb2', project_id=project_id)
        lb3 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb3', project_id=self.project_id)
        lb3 = lb3.get(self.root_tag)

        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings',
                         auth_strategy=constants.KEYSTONE)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                response = self.get(self.LBS_PATH)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        lbs = response.json.get(self.root_tag_list)
        self.assertEqual(1, len(lbs))
        lb_id_names = [(lb.get('id'), lb.get('name')) for lb in lbs]
        self.assertIn((lb3.get('id'), lb3.get('name')), lb_id_names)

    def test_get_all_non_admin_global_observer(self):
        project_id = uuidutils.generate_uuid()
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb1', project_id=project_id)
        lb2 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb2', project_id=project_id)
        lb3 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb3', project_id=self.project_id)
        lb1 = lb1.get(self.root_tag)
        lb2 = lb2.get(self.root_tag)
        lb3 = lb3.get(self.root_tag)

        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings',
                         auth_strategy=constants.KEYSTONE)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_global_observer'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                response = self.get(self.LBS_PATH)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        lbs = response.json.get(self.root_tag_list)
        self.assertEqual(3, len(lbs))
        lb_id_names = [(lb.get('id'), lb.get('name')) for lb in lbs]
        self.assertIn((lb1.get('id'), lb1.get('name')), lb_id_names)
        self.assertIn((lb2.get('id'), lb2.get('name')), lb_id_names)
        self.assertIn((lb3.get('id'), lb3.get('name')), lb_id_names)

    def test_get_all_not_authorized(self):
        project_id = uuidutils.generate_uuid()
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb1', project_id=self.project_id)
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb2', project_id=project_id)
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb3', project_id=project_id)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        LB_PROJECT_PATH = '{}?project_id={}'.format(self.LBS_PATH, project_id)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            response = self.get(LB_PROJECT_PATH, status=403)
        api_lb = response.json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, api_lb)

    def test_get_all_by_project_id(self):
        project1_id = uuidutils.generate_uuid()
        project2_id = uuidutils.generate_uuid()
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb1',
                                        project_id=project1_id)
        lb2 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb2',
                                        project_id=project1_id)
        lb3 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb3',
                                        project_id=project2_id)
        response = self.get(self.LBS_PATH,
                            params={'project_id': project1_id})
        lbs = response.json.get(self.root_tag_list)

        self.assertEqual(2, len(lbs))

        lb_id_names = [(lb.get('id'), lb.get('name')) for lb in lbs]
        lb1 = lb1.get(self.root_tag)
        lb2 = lb2.get(self.root_tag)
        lb3 = lb3.get(self.root_tag)
        self.assertIn((lb1.get('id'), lb1.get('name')), lb_id_names)
        self.assertIn((lb2.get('id'), lb2.get('name')), lb_id_names)
        response = self.get(self.LBS_PATH,
                            params={'project_id': project2_id})
        lbs = response.json.get(self.root_tag_list)
        lb_id_names = [(lb.get('id'), lb.get('name')) for lb in lbs]
        self.assertEqual(1, len(lbs))
        self.assertIn((lb3.get('id'), lb3.get('name')), lb_id_names)

    def test_get_all_sorted(self):
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb1',
                                  project_id=self.project_id)
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb2',
                                  project_id=self.project_id)
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb3',
                                  project_id=self.project_id)
        response = self.get(self.LBS_PATH,
                            params={'sort': 'name:desc'})
        lbs_desc = response.json.get(self.root_tag_list)
        response = self.get(self.LBS_PATH,
                            params={'sort': 'name:asc'})
        lbs_asc = response.json.get(self.root_tag_list)

        self.assertEqual(3, len(lbs_desc))
        self.assertEqual(3, len(lbs_asc))

        lb_id_names_desc = [(lb.get('id'), lb.get('name')) for lb in lbs_desc]
        lb_id_names_asc = [(lb.get('id'), lb.get('name')) for lb in lbs_asc]
        self.assertEqual(lb_id_names_asc, list(reversed(lb_id_names_desc)))

    def test_get_all_limited(self):
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb1',
                                  project_id=self.project_id)
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb2',
                                  project_id=self.project_id)
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb3',
                                  project_id=self.project_id)

        # First two -- should have 'next' link
        first_two = self.get(self.LBS_PATH, params={'limit': 2}).json
        objs = first_two[self.root_tag_list]
        links = first_two[self.root_tag_links]
        self.assertEqual(2, len(objs))
        self.assertEqual(1, len(links))
        self.assertEqual('next', links[0]['rel'])

        # Third + off the end -- should have previous link
        third = self.get(self.LBS_PATH, params={
            'limit': 2,
            'marker': first_two[self.root_tag_list][1]['id']}).json
        objs = third[self.root_tag_list]
        links = third[self.root_tag_links]
        self.assertEqual(1, len(objs))
        self.assertEqual(1, len(links))
        self.assertEqual('previous', links[0]['rel'])

        # Middle -- should have both links
        middle = self.get(self.LBS_PATH, params={
            'limit': 1,
            'marker': first_two[self.root_tag_list][0]['id']}).json
        objs = middle[self.root_tag_list]
        links = middle[self.root_tag_links]
        self.assertEqual(1, len(objs))
        self.assertEqual(2, len(links))
        self.assertItemsEqual(['previous', 'next'], [l['rel'] for l in links])

    def test_get_all_fields_filter(self):
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb1',
                                  project_id=self.project_id)
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb2',
                                  project_id=self.project_id)
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb3',
                                  project_id=self.project_id)

        lbs = self.get(self.LBS_PATH, params={
            'fields': ['id', 'project_id']}).json
        for lb in lbs['loadbalancers']:
            self.assertIn(u'id', lb)
            self.assertIn(u'project_id', lb)
            self.assertNotIn(u'description', lb)

    def test_get_one_fields_filter(self):
        lb1 = self.create_load_balancer(
            uuidutils.generate_uuid(),
            name='lb1', project_id=self.project_id).get(self.root_tag)

        lb = self.get(
            self.LB_PATH.format(lb_id=lb1.get('id')),
            params={'fields': ['id', 'project_id']}).json.get(self.root_tag)
        self.assertIn(u'id', lb)
        self.assertIn(u'project_id', lb)
        self.assertNotIn(u'description', lb)

    def test_get_all_admin_state_up_filter(self):
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  admin_state_up=True,
                                  name='lb1',
                                  project_id=self.project_id)
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  admin_state_up=False,
                                  name='lb2',
                                  project_id=self.project_id)

        lbs = self.get(self.LBS_PATH, params={'admin_state_up': 'false'}).json
        self.assertEqual(1, len(lbs['loadbalancers']))
        self.assertFalse(lbs['loadbalancers'][0]['admin_state_up'])
        self.assertEqual('lb2', lbs['loadbalancers'][0]['name'])

    def test_get_all_filter(self):
        lb1 = self.create_load_balancer(
            uuidutils.generate_uuid(),
            name='lb1',
            project_id=self.project_id,
            vip_address='10.0.0.1').get(self.root_tag)
        self.create_load_balancer(
            uuidutils.generate_uuid(),
            name='lb2',
            project_id=self.project_id).get(self.root_tag)
        self.create_load_balancer(
            uuidutils.generate_uuid(),
            name='lb3',
            project_id=self.project_id).get(self.root_tag)
        lbs = self.get(self.LBS_PATH, params={
            'id': lb1['id'], 'vip_address': lb1['vip_address']}).json
        self.assertEqual(1, len(lbs['loadbalancers']))
        self.assertEqual(lb1['id'],
                         lbs['loadbalancers'][0]['id'])

    def test_get_all_tags_filter(self):
        lb1 = self.create_load_balancer(
            uuidutils.generate_uuid(),
            name='lb1',
            project_id=self.project_id,
            vip_address='10.0.0.1',
            tags=['test_tag1', 'test_tag2']
        ).get(self.root_tag)
        lb2 = self.create_load_balancer(
            uuidutils.generate_uuid(),
            name='lb2',
            project_id=self.project_id,
            tags=['test_tag2', 'test_tag3']
        ).get(self.root_tag)
        lb3 = self.create_load_balancer(
            uuidutils.generate_uuid(),
            name='lb3',
            project_id=self.project_id,
            tags=['test_tag4', 'test_tag5']
        ).get(self.root_tag)

        lbs = self.get(
            self.LBS_PATH,
            params={'tags': 'test_tag2'}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(lbs, list)
        self.assertEqual(2, len(lbs))
        self.assertEqual(
            [lb1.get('id'), lb2.get('id')],
            [lb.get('id') for lb in lbs]
        )

        lbs = self.get(
            self.LBS_PATH,
            params={'tags': ['test_tag2', 'test_tag3']}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(lbs, list)
        self.assertEqual(1, len(lbs))
        self.assertEqual(
            [lb2.get('id')],
            [lb.get('id') for lb in lbs]
        )

        lbs = self.get(
            self.LBS_PATH,
            params={'tags-any': 'test_tag2'}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(lbs, list)
        self.assertEqual(2, len(lbs))
        self.assertEqual(
            [lb1.get('id'), lb2.get('id')],
            [lb.get('id') for lb in lbs]
        )

        lbs = self.get(
            self.LBS_PATH,
            params={'not-tags': 'test_tag2'}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(lbs, list)
        self.assertEqual(1, len(lbs))
        self.assertEqual(
            [lb3.get('id')],
            [lb.get('id') for lb in lbs]
        )

        lbs = self.get(
            self.LBS_PATH,
            params={'not-tags-any': ['test_tag2', 'test_tag4']}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(lbs, list)
        self.assertEqual(0, len(lbs))

        lbs = self.get(
            self.LBS_PATH,
            params={'tags': 'test_tag2',
                    'tags-any': ['test_tag1', 'test_tag3']}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(lbs, list)
        self.assertEqual(2, len(lbs))
        self.assertEqual(
            [lb1.get('id'), lb2.get('id')],
            [lb.get('id') for lb in lbs]
        )

        lbs = self.get(
            self.LBS_PATH,
            params={'tags': 'test_tag2', 'not-tags': 'test_tag2'}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(lbs, list)
        self.assertEqual(0, len(lbs))

    def test_get_all_hides_deleted(self):
        api_lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get(self.root_tag)

        response = self.get(self.LBS_PATH)
        objects = response.json.get(self.root_tag_list)
        self.assertEqual(len(objects), 1)
        self.set_object_status(self.lb_repo, api_lb.get('id'),
                               provisioning_status=constants.DELETED)
        response = self.get(self.LBS_PATH)
        objects = response.json.get(self.root_tag_list)
        self.assertEqual(len(objects), 0)

    def test_get(self):
        project_id = uuidutils.generate_uuid()
        subnet = network_models.Subnet(id=uuidutils.generate_uuid())
        network = network_models.Network(id=uuidutils.generate_uuid(),
                                         subnets=[subnet])
        port = network_models.Port(id=uuidutils.generate_uuid(),
                                   network_id=network.id)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_port") as mock_get_port:
            mock_get_network.return_value = network
            mock_get_port.return_value = port

            lb = self.create_load_balancer(subnet.id,
                                           vip_address='10.0.0.1',
                                           vip_network_id=network.id,
                                           vip_port_id=port.id,
                                           name='lb1',
                                           project_id=project_id,
                                           description='desc1',
                                           admin_state_up=False,
                                           tags=['test_tag'])
        lb_dict = lb.get(self.root_tag)
        response = self.get(
            self.LB_PATH.format(
                lb_id=lb_dict.get('id'))).json.get(self.root_tag)
        self.assertEqual('lb1', response.get('name'))
        self.assertEqual(project_id, response.get('project_id'))
        self.assertEqual('desc1', response.get('description'))
        self.assertFalse(response.get('admin_state_up'))
        self.assertEqual('10.0.0.1', response.get('vip_address'))
        self.assertEqual(subnet.id, response.get('vip_subnet_id'))
        self.assertEqual(network.id, response.get('vip_network_id'))
        self.assertEqual(port.id, response.get('vip_port_id'))
        self.assertEqual(['test_tag'], response.get('tags'))

    def test_get_deleted_gives_404(self):
        api_lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get(self.root_tag)

        self.set_object_status(self.lb_repo, api_lb.get('id'),
                               provisioning_status=constants.DELETED)

        self.get(self.LB_PATH.format(lb_id=api_lb.get('id')), status=404)

    def test_get_bad_lb_id(self):
        path = self.LB_PATH.format(lb_id='SEAN-CONNERY')
        self.get(path, status=404)

    def test_get_authorized(self):
        project_id = uuidutils.generate_uuid()
        subnet = network_models.Subnet(id=uuidutils.generate_uuid())
        network = network_models.Network(id=uuidutils.generate_uuid(),
                                         subnets=[subnet])
        port = network_models.Port(id=uuidutils.generate_uuid(),
                                   network_id=network.id)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_port") as mock_get_port:
            mock_get_network.return_value = network
            mock_get_port.return_value = port

            lb = self.create_load_balancer(subnet.id,
                                           vip_address='10.0.0.1',
                                           vip_network_id=network.id,
                                           vip_port_id=port.id,
                                           name='lb1',
                                           project_id=project_id,
                                           description='desc1',
                                           admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                response = self.get(self.LB_PATH.format(
                    lb_id=lb_dict.get('id'))).json.get(self.root_tag)
        self.assertEqual('lb1', response.get('name'))
        self.assertEqual(project_id, response.get('project_id'))
        self.assertEqual('desc1', response.get('description'))
        self.assertFalse(response.get('admin_state_up'))
        self.assertEqual('10.0.0.1', response.get('vip_address'))
        self.assertEqual(subnet.id, response.get('vip_subnet_id'))
        self.assertEqual(network.id, response.get('vip_network_id'))
        self.assertEqual(port.id, response.get('vip_port_id'))
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

    def test_get_not_authorized(self):
        project_id = uuidutils.generate_uuid()
        subnet = network_models.Subnet(id=uuidutils.generate_uuid())
        network = network_models.Network(id=uuidutils.generate_uuid(),
                                         subnets=[subnet])
        port = network_models.Port(id=uuidutils.generate_uuid(),
                                   network_id=network.id)
        with mock.patch(
                "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_network") as mock_get_network, mock.patch(
            "octavia.network.drivers.noop_driver.driver.NoopManager"
                ".get_port") as mock_get_port:
            mock_get_network.return_value = network
            mock_get_port.return_value = port

            lb = self.create_load_balancer(subnet.id,
                                           vip_address='10.0.0.1',
                                           vip_network_id=network.id,
                                           vip_port_id=port.id,
                                           name='lb1',
                                           project_id=project_id,
                                           description='desc1',
                                           admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            response = self.get(self.LB_PATH.format(lb_id=lb_dict.get('id')),
                                status=403)
        api_lb = response.json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, api_lb)

    def test_create_over_quota(self):
        self.start_quota_mock(data_models.LoadBalancer)
        lb_json = {'name': 'test1',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id}
        body = self._build_body(lb_json)
        self.post(self.LBS_PATH, body, status=403)

    def test_update(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False,
                                       tags=['test_tag1'])
        lb_dict = lb.get(self.root_tag)
        lb_json = self._build_body({'name': 'lb2', 'tags': ['test_tag2']})
        lb = self.set_lb_status(lb_dict.get('id'))
        response = self.put(self.LB_PATH.format(lb_id=lb_dict.get('id')),
                            lb_json)
        api_lb = response.json.get(self.root_tag)
        self.assertIsNotNone(api_lb.get('vip_subnet_id'))
        self.assertEqual('lb2', api_lb.get('name'))
        self.assertEqual(['test_tag2'], api_lb.get('tags'))
        self.assertEqual(project_id, api_lb.get('project_id'))
        self.assertEqual('desc1', api_lb.get('description'))
        self.assertFalse(api_lb.get('admin_state_up'))
        self.assertIsNotNone(api_lb.get('created_at'))
        self.assertIsNotNone(api_lb.get('updated_at'))
        self.assert_correct_lb_status(api_lb.get('id'), constants.ONLINE,
                                      constants.PENDING_UPDATE)

    def test_update_with_vip(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb_json = self._build_body({'vip_subnet_id': '1234'})
        lb = self.set_lb_status(lb_dict.get('id'))
        self.put(self.LB_PATH.format(lb_id=lb_dict.get('id')),
                 lb_json, status=400)

    def test_update_with_qos(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(
            uuidutils.generate_uuid(), name='lb1',
            project_id=project_id,
            vip_qos_policy_id=uuidutils.generate_uuid())
        lb_dict = lb.get(self.root_tag)
        self.set_lb_status(lb_dict.get('id'))
        lb_json = self._build_body(
            {'vip_qos_policy_id': uuidutils.generate_uuid()})
        self.put(self.LB_PATH.format(lb_id=lb_dict.get('id')),
                 lb_json, status=200)

    def test_update_with_bad_qos(self):
        project_id = uuidutils.generate_uuid()
        vip_qos_policy_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       vip_qos_policy_id=vip_qos_policy_id)
        lb_dict = lb.get(self.root_tag)
        lb_json = self._build_body({'vip_qos_policy_id': 'BAD'})
        self.set_lb_status(lb_dict.get('id'))
        self.put(self.LB_PATH.format(lb_id=lb_dict.get('id')),
                 lb_json, status=400)

    def test_update_bad_lb_id(self):
        path = self.LB_PATH.format(lb_id='SEAN-CONNERY')
        self.put(path, body={}, status=404)

    def test_update_pending_create(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb_json = self._build_body({'name': 'Roberto'})
        self.put(self.LB_PATH.format(lb_id=lb_dict.get('id')),
                 lb_json, status=409)

    def test_update_authorized(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb_json = self._build_body({'name': 'lb2'})
        lb = self.set_lb_status(lb_dict.get('id'))

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                response = self.put(
                    self.LB_PATH.format(lb_id=lb_dict.get('id')), lb_json)
        api_lb = response.json.get(self.root_tag)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertIsNotNone(api_lb.get('vip_subnet_id'))
        self.assertEqual('lb2', api_lb.get('name'))
        self.assertEqual(project_id, api_lb.get('project_id'))
        self.assertEqual('desc1', api_lb.get('description'))
        self.assertFalse(api_lb.get('admin_state_up'))
        self.assertIsNotNone(api_lb.get('created_at'))
        self.assertIsNotNone(api_lb.get('updated_at'))
        self.assert_correct_lb_status(api_lb.get('id'), constants.ONLINE,
                                      constants.PENDING_UPDATE)

    def test_update_not_authorized(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb_json = self._build_body({'name': 'lb2'})
        lb = self.set_lb_status(lb_dict.get('id'))

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            response = self.put(self.LB_PATH.format(lb_id=lb_dict.get('id')),
                                lb_json, status=403)
        api_lb = response.json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, api_lb)
        self.assert_correct_lb_status(lb_dict.get('id'), constants.ONLINE,
                                      constants.ACTIVE)

    def test_delete_pending_create(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        self.delete(self.LB_PATH.format(lb_id=lb_dict.get('id')), status=409)

    def test_update_pending_update(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb_json = self._build_body({'name': 'Bob'})
        lb = self.set_lb_status(lb_dict.get('id'))
        self.put(self.LB_PATH.format(lb_id=lb_dict.get('id')), lb_json)
        self.put(self.LB_PATH.format(lb_id=lb_dict.get('id')),
                 lb_json, status=409)

    def test_delete_pending_update(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_json = self._build_body({'name': 'Steve'})
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'))
        self.put(self.LB_PATH.format(lb_id=lb_dict.get('id')), lb_json)
        self.delete(self.LB_PATH.format(lb_id=lb_dict.get('id')), status=409)

    def test_delete_with_error_status(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'), status=constants.ERROR)
        self.delete(self.LB_PATH.format(lb_id=lb_dict.get('id')), status=204)

    def test_update_pending_delete(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'))
        self.delete(self.LB_PATH.format(lb_id=lb_dict.get('id')))
        lb_json = self._build_body({'name': 'John'})
        self.put(self.LB_PATH.format(lb_id=lb_dict.get('id')),
                 lb_json, status=409)

    def test_delete_pending_delete(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'))
        self.delete(self.LB_PATH.format(lb_id=lb_dict.get('id')))
        self.delete(self.LB_PATH.format(lb_id=lb_dict.get('id')), status=409)

    def test_update_already_deleted(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'), status=constants.DELETED)
        lb_json = self._build_body({'name': 'John'})
        self.put(self.LB_PATH.format(lb_id=lb_dict.get('id')),
                 lb_json, status=404)

    def test_delete_already_deleted(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'), status=constants.DELETED)
        self.delete(self.LB_PATH.format(lb_id=lb_dict.get('id')), status=404)

    def test_delete(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1', project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'))
        self.delete(self.LB_PATH.format(lb_id=lb_dict.get('id')))
        response = self.get(self.LB_PATH.format(lb_id=lb_dict.get('id')))
        api_lb = response.json.get(self.root_tag)
        self.assertEqual('lb1', api_lb.get('name'))
        self.assertEqual('desc1', api_lb.get('description'))
        self.assertEqual(project_id, api_lb.get('project_id'))
        self.assertFalse(api_lb.get('admin_state_up'))
        self.assert_correct_lb_status(api_lb.get('id'), constants.ONLINE,
                                      constants.PENDING_DELETE)

    def test_delete_authorized(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'))
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                self.delete(self.LB_PATH.format(lb_id=lb_dict.get('id')))
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        response = self.get(self.LB_PATH.format(lb_id=lb_dict.get('id')))
        api_lb = response.json.get(self.root_tag)
        self.assertEqual('lb1', api_lb.get('name'))
        self.assertEqual('desc1', api_lb.get('description'))
        self.assertEqual(project_id, api_lb.get('project_id'))
        self.assertFalse(api_lb.get('admin_state_up'))
        self.assertEqual(lb.get('operational_status'),
                         api_lb.get('operational_status'))
        self.assert_correct_lb_status(api_lb.get('id'), constants.ONLINE,
                                      constants.PENDING_DELETE)

    def test_delete_not_authorized(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'))
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            self.delete(self.LB_PATH.format(lb_id=lb_dict.get('id')),
                        status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        response = self.get(self.LB_PATH.format(lb_id=lb_dict.get('id')))
        api_lb = response.json.get(self.root_tag)
        self.assertEqual('lb1', api_lb.get('name'))
        self.assertEqual('desc1', api_lb.get('description'))
        self.assertEqual(project_id, api_lb.get('project_id'))
        self.assertFalse(api_lb.get('admin_state_up'))
        self.assert_correct_lb_status(api_lb.get('id'), constants.ONLINE,
                                      constants.ACTIVE)

    def test_delete_fails_with_pool(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1').get(self.root_tag)
        lb_id = lb.get('id')
        self.set_lb_status(lb_id)
        self.create_pool(
            lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN)
        self.set_lb_status(lb_id)
        self.delete(self.LB_PATH.format(lb_id=lb_id), status=400)
        self.assert_correct_status(lb_id=lb_id)

    def test_delete_fails_with_listener(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1').get(self.root_tag)
        lb_id = lb.get('id')
        self.set_lb_status(lb_id)
        self.create_listener(constants.PROTOCOL_HTTP, 80, lb_id)
        self.set_lb_status(lb_id)
        self.delete(self.LB_PATH.format(lb_id=lb_id), status=400)
        self.assert_correct_status(lb_id=lb_id)

    def test_cascade_delete(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1').get(self.root_tag)
        lb_id = lb.get('id')
        self.set_lb_status(lb_id)
        listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb_id).get('listener')
        listener_id = listener.get('id')
        self.set_lb_status(lb_id)
        self.create_pool(
            lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=listener_id)
        self.set_lb_status(lb_id)
        self.delete(self.LB_PATH.format(lb_id=lb_id),
                    params={'cascade': "true"})

    def test_delete_bad_lb_id(self):
        path = self.LB_PATH.format(lb_id='bad_uuid')
        self.delete(path, status=404)

    def test_failover(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'))
        self.app.put(self._get_full_path(
            self.LB_PATH.format(lb_id=lb_dict.get('id')) + "/failover"),
            status=202)

    def test_failover_pending(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'),
                                status=constants.PENDING_UPDATE)
        self.app.put(self._get_full_path(
            self.LB_PATH.format(lb_id=lb_dict.get('id')) + "/failover"),
            status=409)

    def test_failover_error(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'),
                                status=constants.ERROR)
        self.app.put(self._get_full_path(
            self.LB_PATH.format(lb_id=lb_dict.get('id')) + "/failover"),
            status=202)

    def test_failover_not_authorized(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'))

        path = self._get_full_path(self.LB_PATH.format(
            lb_id=lb_dict.get('id')) + "/failover")
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
                response = self.app.put(path, status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response.json)

    def test_failover_not_authorized_no_role(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'))

        path = self._get_full_path(self.LB_PATH.format(
            lb_id=lb_dict.get('id')) + "/failover")
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': [],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                response = self.app.put(path, status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response.json)

    def test_failover_authorized_lb_admin(self):
        project_id = uuidutils.generate_uuid()
        project_id_2 = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'))

        path = self._get_full_path(self.LB_PATH.format(
            lb_id=lb_dict.get('id')) + "/failover")
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               project_id_2):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_admin'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': project_id_2}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                self.app.put(path, status=202)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

    def test_failover_authorized_no_auth(self):
        project_id = uuidutils.generate_uuid()
        project_id_2 = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'))

        path = self._get_full_path(self.LB_PATH.format(
            lb_id=lb_dict.get('id')) + "/failover")
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               project_id_2):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': project_id_2}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                self.app.put(path, status=202)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

    def test_failover_deleted(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1',
                                       project_id=project_id,
                                       description='desc1',
                                       admin_state_up=False)
        lb_dict = lb.get(self.root_tag)
        lb = self.set_lb_status(lb_dict.get('id'), status=constants.DELETED)

        path = self._get_full_path(self.LB_PATH.format(
            lb_id=lb_dict.get('id')) + "/failover")
        self.app.put(path, status=404)

    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_create_with_bad_provider(self, mock_provider):
        mock_provider.side_effect = exceptions.ProviderDriverError(
            prov='bad_driver', user_msg='broken')
        lb_json = {'name': 'test-lb',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id}
        response = self.post(self.LBS_PATH, self._build_body(lb_json),
                             status=500)
        self.assertIn('Provider \'bad_driver\' reports error: broken',
                      response.json.get('faultstring'))

    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_update_with_bad_provider(self, mock_provider):
        api_lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get(self.root_tag)
        self.set_lb_status(lb_id=api_lb.get('id'))
        new_listener = {'name': 'new_name'}
        mock_provider.side_effect = exceptions.ProviderDriverError(
            prov='bad_driver', user_msg='broken')
        response = self.put(self.LB_PATH.format(lb_id=api_lb.get('id')),
                            self._build_body(new_listener), status=500)
        self.assertIn('Provider \'bad_driver\' reports error: broken',
                      response.json.get('faultstring'))

    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_delete_with_bad_provider(self, mock_provider):
        api_lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get(self.root_tag)
        self.set_lb_status(lb_id=api_lb.get('id'))
        # Set status to ACTIVE/ONLINE because set_lb_status did it in the db
        api_lb['provisioning_status'] = constants.ACTIVE
        api_lb['operating_status'] = constants.ONLINE
        response = self.get(self.LB_PATH.format(
            lb_id=api_lb.get('id'))).json.get(self.root_tag)

        self.assertIsNone(api_lb.pop('updated_at'))
        self.assertIsNotNone(response.pop('updated_at'))
        self.assertEqual(api_lb, response)
        mock_provider.side_effect = exceptions.ProviderDriverError(
            prov='bad_driver', user_msg='broken')
        self.delete(self.LB_PATH.format(lb_id=api_lb.get('id')), status=500)

    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_create_with_provider_not_implemented(self, mock_provider):
        mock_provider.side_effect = exceptions.ProviderNotImplementedError(
            prov='bad_driver', user_msg='broken')
        lb_json = {'name': 'test-lb',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id}
        response = self.post(self.LBS_PATH, self._build_body(lb_json),
                             status=501)
        self.assertIn('Provider \'bad_driver\' does not support a requested '
                      'action: broken', response.json.get('faultstring'))

    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_update_with_provider_not_implemented(self, mock_provider):
        api_lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get(self.root_tag)
        self.set_lb_status(lb_id=api_lb.get('id'))
        new_listener = {'name': 'new_name'}
        mock_provider.side_effect = exceptions.ProviderNotImplementedError(
            prov='bad_driver', user_msg='broken')
        response = self.put(self.LB_PATH.format(lb_id=api_lb.get('id')),
                            self._build_body(new_listener), status=501)
        self.assertIn('Provider \'bad_driver\' does not support a requested '
                      'action: broken', response.json.get('faultstring'))

    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_delete_with_provider_not_implemented(self, mock_provider):
        api_lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get(self.root_tag)
        self.set_lb_status(lb_id=api_lb.get('id'))
        # Set status to ACTIVE/ONLINE because set_lb_status did it in the db
        api_lb['provisioning_status'] = constants.ACTIVE
        api_lb['operating_status'] = constants.ONLINE
        response = self.get(self.LB_PATH.format(
            lb_id=api_lb.get('id'))).json.get(self.root_tag)

        self.assertIsNone(api_lb.pop('updated_at'))
        self.assertIsNotNone(response.pop('updated_at'))
        self.assertEqual(api_lb, response)
        mock_provider.side_effect = exceptions.ProviderNotImplementedError(
            prov='bad_driver', user_msg='broken')
        self.delete(self.LB_PATH.format(lb_id=api_lb.get('id')), status=501)

    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_create_with_provider_unsupport_option(self, mock_provider):
        mock_provider.side_effect = exceptions.ProviderUnsupportedOptionError(
            prov='bad_driver', user_msg='broken')
        lb_json = {'name': 'test-lb',
                   'vip_subnet_id': uuidutils.generate_uuid(),
                   'project_id': self.project_id}
        response = self.post(self.LBS_PATH, self._build_body(lb_json),
                             status=501)
        self.assertIn('Provider \'bad_driver\' does not support a requested '
                      'option: broken', response.json.get('faultstring'))

    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_update_with_provider_unsupport_option(self, mock_provider):
        api_lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get(self.root_tag)
        self.set_lb_status(lb_id=api_lb.get('id'))
        new_listener = {'name': 'new_name'}
        mock_provider.side_effect = exceptions.ProviderUnsupportedOptionError(
            prov='bad_driver', user_msg='broken')
        response = self.put(self.LB_PATH.format(lb_id=api_lb.get('id')),
                            self._build_body(new_listener), status=501)
        self.assertIn('Provider \'bad_driver\' does not support a requested '
                      'option: broken', response.json.get('faultstring'))

    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_delete_with_provider_unsupport_option(self, mock_provider):
        api_lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get(self.root_tag)
        self.set_lb_status(lb_id=api_lb.get('id'))
        # Set status to ACTIVE/ONLINE because set_lb_status did it in the db
        api_lb['provisioning_status'] = constants.ACTIVE
        api_lb['operating_status'] = constants.ONLINE
        response = self.get(self.LB_PATH.format(
            lb_id=api_lb.get('id'))).json.get(self.root_tag)

        self.assertIsNone(api_lb.pop('updated_at'))
        self.assertIsNotNone(response.pop('updated_at'))
        self.assertEqual(api_lb, response)
        mock_provider.side_effect = exceptions.ProviderUnsupportedOptionError(
            prov='bad_driver', user_msg='broken')
        self.delete(self.LB_PATH.format(lb_id=api_lb.get('id')), status=501)


class TestLoadBalancerGraph(base.BaseAPITest):

    root_tag = 'loadbalancer'

    def setUp(self):
        super(TestLoadBalancerGraph, self).setUp()
        self._project_id = uuidutils.generate_uuid()

    def _build_body(self, json):
        return {self.root_tag: json}

    def _assert_graphs_equal(self, expected_graph, observed_graph):
        observed_graph_copy = copy.deepcopy(observed_graph)
        del observed_graph_copy['created_at']
        del observed_graph_copy['updated_at']
        self.assertEqual(observed_graph_copy['project_id'],
                         observed_graph_copy.pop('tenant_id'))

        obs_lb_id = observed_graph_copy.pop('id')
        self.assertTrue(uuidutils.is_uuid_like(obs_lb_id))

        expected_listeners = expected_graph.pop('listeners', [])
        observed_listeners = observed_graph_copy.pop('listeners', [])
        expected_pools = expected_graph.pop('pools', [])
        observed_pools = observed_graph_copy.pop('pools', [])
        self.assertEqual(expected_graph, observed_graph_copy)

        self.assertEqual(len(expected_pools), len(observed_pools))

        self.assertEqual(len(expected_listeners), len(observed_listeners))
        for observed_listener in observed_listeners:
            del observed_listener['created_at']
            del observed_listener['updated_at']
            self.assertEqual(observed_listener['project_id'],
                             observed_listener.pop('tenant_id'))

            self.assertTrue(uuidutils.is_uuid_like(
                observed_listener.pop('id')))
            if observed_listener.get('default_pool_id'):
                self.assertTrue(uuidutils.is_uuid_like(
                    observed_listener.pop('default_pool_id')))

            default_pool = observed_listener.get('default_pool')
            if default_pool:
                observed_listener.pop('default_pool_id')
                self.assertTrue(default_pool.get('id'))
                default_pool.pop('id')
                default_pool.pop('created_at')
                default_pool.pop('updated_at')
                hm = default_pool.get('health_monitor')
                if hm:
                    self.assertTrue(hm.get('id'))
                    hm.pop('id')
                for member in default_pool.get('members', []):
                    self.assertTrue(member.get('id'))
                    member.pop('id')
                    member.pop('created_at')
                    member.pop('updated_at')
            if observed_listener.get('sni_containers'):
                observed_listener['sni_containers'].sort()
            o_l7policies = observed_listener.get('l7policies')
            if o_l7policies:
                for o_l7policy in o_l7policies:
                    o_l7policy.pop('created_at')
                    o_l7policy.pop('updated_at')
                    self.assertEqual(o_l7policy['project_id'],
                                     o_l7policy.pop('tenant_id'))
                    if o_l7policy.get('redirect_pool_id'):
                        r_pool_id = o_l7policy.pop('redirect_pool_id')
                        self.assertTrue(uuidutils.is_uuid_like(r_pool_id))
                    o_l7policy_id = o_l7policy.pop('id')
                    self.assertTrue(uuidutils.is_uuid_like(o_l7policy_id))
                    o_l7policy_l_id = o_l7policy.pop('listener_id')
                    self.assertTrue(uuidutils.is_uuid_like(o_l7policy_l_id))
                    l7rules = o_l7policy.get('rules') or []
                    for l7rule in l7rules:
                        l7rule.pop('created_at')
                        l7rule.pop('updated_at')
                        self.assertEqual(l7rule['project_id'],
                                         l7rule.pop('tenant_id'))
                        self.assertTrue(l7rule.pop('id'))
            self.assertIn(observed_listener, expected_listeners)

    def _get_lb_bodies(self, create_listeners, expected_listeners,
                       create_pools=None):
        create_lb = {
            'name': 'lb1',
            'project_id': self._project_id,
            'vip_subnet_id': uuidutils.generate_uuid(),
            'vip_port_id': uuidutils.generate_uuid(),
            'vip_address': '198.51.100.10',
            'provider': 'noop_driver',
            'listeners': create_listeners,
            'pools': create_pools or []
        }
        expected_lb = {
            'description': '',
            'admin_state_up': True,
            'provisioning_status': constants.PENDING_CREATE,
            'operating_status': constants.OFFLINE,
            # TODO(rm_work): vip_network_id is a weird case, as it will be
            # replaced from the port, which in the noop network driver will be
            # freshly generated... I don't see a way to actually set it sanely
            # for this test without interfering with a ton of stuff, and it is
            # expected that this would be overwritten anyway, so 'ANY' is fine?
            'vip_network_id': mock.ANY,
            'vip_qos_policy_id': None,
            'flavor_id': None,
            'provider': 'noop_driver',
            'tags': []
        }
        expected_lb.update(create_lb)
        expected_lb['listeners'] = expected_listeners
        expected_lb['pools'] = create_pools or []
        return create_lb, expected_lb

    def _get_listener_bodies(
            self, name='listener1', protocol_port=80,
            create_default_pool_name=None, create_default_pool_id=None,
            create_l7policies=None, expected_l7policies=None,
            create_sni_containers=None, expected_sni_containers=None,
            create_client_ca_tls_container=None,
            expected_client_ca_tls_container=None,
            create_protocol=constants.PROTOCOL_HTTP,
            create_client_authentication=None,
            expected_client_authentication=constants.CLIENT_AUTH_NONE,
            create_client_crl_container=None,
            expected_client_crl_container=None):
        create_listener = {
            'name': name,
            'protocol_port': protocol_port,
            'protocol': create_protocol
        }
        expected_listener = {
            'description': '',
            'default_tls_container_ref': None,
            'sni_container_refs': [],
            'connection_limit': -1,
            'admin_state_up': True,
            'provisioning_status': constants.PENDING_CREATE,
            'operating_status': constants.OFFLINE,
            'insert_headers': {},
            'project_id': self._project_id,
            'timeout_client_data': constants.DEFAULT_TIMEOUT_CLIENT_DATA,
            'timeout_member_connect': constants.DEFAULT_TIMEOUT_MEMBER_CONNECT,
            'timeout_member_data': constants.DEFAULT_TIMEOUT_MEMBER_DATA,
            'timeout_tcp_inspect': constants.DEFAULT_TIMEOUT_TCP_INSPECT,
            'tags': [],
            'client_ca_tls_container_ref': None,
            'client_authentication': constants.CLIENT_AUTH_NONE,
            'client_crl_container_ref': None
        }
        if create_sni_containers:
            create_listener['sni_container_refs'] = create_sni_containers
        expected_listener.update(create_listener)
        if create_default_pool_name:
            pool = {'name': create_default_pool_name}
            create_listener['default_pool'] = pool
        elif create_default_pool_id:
            create_listener['default_pool_id'] = create_default_pool_id
            expected_listener['default_pool_id'] = create_default_pool_id
        else:
            expected_listener['default_pool_id'] = None
        if create_l7policies:
            l7policies = create_l7policies
            create_listener['l7policies'] = l7policies
        if create_client_ca_tls_container:
            create_listener['client_ca_tls_container_ref'] = (
                create_client_ca_tls_container)
        if create_client_authentication:
            create_listener['client_authentication'] = (
                create_client_authentication)
        if create_client_crl_container:
            create_listener['client_crl_container_ref'] = (
                create_client_crl_container)
        if expected_sni_containers:
            expected_listener['sni_container_refs'] = expected_sni_containers
        if expected_l7policies:
            expected_listener['l7policies'] = expected_l7policies
        else:
            expected_listener['l7policies'] = []
        if expected_client_ca_tls_container:
            expected_listener['client_ca_tls_container_ref'] = (
                expected_client_ca_tls_container)
            expected_listener['client_authentication'] = (
                constants.CLIENT_AUTH_NONE)
        if expected_client_authentication:
            expected_listener[
                'client_authentication'] = expected_client_authentication
        if expected_client_crl_container:
            expected_listener['client_crl_container_ref'] = (
                expected_client_crl_container)
        return create_listener, expected_listener

    def _get_pool_bodies(self, name='pool1', create_members=None,
                         expected_members=None, create_hm=None,
                         expected_hm=None, protocol=constants.PROTOCOL_HTTP,
                         session_persistence=True):
        create_pool = {
            'name': name,
            'protocol': protocol,
            'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
        }
        if session_persistence:
            create_pool['session_persistence'] = {
                'type': constants.SESSION_PERSISTENCE_SOURCE_IP,
                'cookie_name': None}
        if create_members:
            create_pool['members'] = create_members
        if create_hm:
            create_pool['healthmonitor'] = create_hm
        expected_pool = {
            'description': None,
            'session_persistence': None,
            'members': [],
            'enabled': True,
            'provisioning_status': constants.PENDING_CREATE,
            'operating_status': constants.OFFLINE,
            'project_id': self._project_id,
            'tags': []
        }
        expected_pool.update(create_pool)
        if expected_members:
            expected_pool['members'] = expected_members
        if expected_hm:
            expected_pool['healthmonitor'] = expected_hm
        return create_pool, expected_pool

    def _get_member_bodies(self, protocol_port=80):
        create_member = {
            'address': '10.0.0.1',
            'protocol_port': protocol_port
        }
        expected_member = {
            'weight': 1,
            'enabled': True,
            'subnet_id': None,
            'operating_status': constants.OFFLINE,
            'project_id': self._project_id,
            'tags': []
        }
        expected_member.update(create_member)
        return create_member, expected_member

    def _get_hm_bodies(self):
        create_hm = {
            'type': constants.HEALTH_MONITOR_PING,
            'delay': 1,
            'timeout': 1,
            'max_retries_down': 1,
            'max_retries': 1
        }
        expected_hm = {
            'http_method': 'GET',
            'url_path': '/',
            'expected_codes': '200',
            'admin_state_up': True,
            'project_id': self._project_id,
            'provisioning_status': constants.PENDING_CREATE,
            'operating_status': constants.OFFLINE,
            'tags': []
        }
        expected_hm.update(create_hm)
        return create_hm, expected_hm

    def _get_sni_container_bodies(self):
        create_sni_container1 = uuidutils.generate_uuid()
        create_sni_container2 = uuidutils.generate_uuid()
        create_sni_containers = [create_sni_container1, create_sni_container2]
        expected_sni_containers = [create_sni_container1,
                                   create_sni_container2]
        expected_sni_containers.sort()
        return create_sni_containers, expected_sni_containers

    def _get_l7policies_bodies(self,
                               create_pool_name=None, create_pool_id=None,
                               create_l7rules=None, expected_l7rules=None):
        create_l7policies = []
        if create_pool_name:
            create_l7policy = {
                'action': constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
                'redirect_pool': {'name': create_pool_name},
                'position': 1,
                'admin_state_up': False
            }
        else:
            create_l7policy = {
                'action': constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                'redirect_url': 'http://127.0.0.1/',
                'position': 1,
                'redirect_http_code': 302,
                'admin_state_up': False
            }
        create_l7policies.append(create_l7policy)
        expected_l7policy = {
            'name': '',
            'description': '',
            'redirect_http_code': None,
            'redirect_url': None,
            'redirect_prefix': None,
            'rules': [],
            'project_id': self._project_id,
            'provisioning_status': constants.PENDING_CREATE,
            'operating_status': constants.OFFLINE,
            'tags': []
        }
        expected_l7policy.update(create_l7policy)
        expected_l7policy.pop('redirect_pool', None)
        expected_l7policies = []
        if not create_pool_name:
            expected_l7policy['redirect_pool_id'] = create_pool_id
        expected_l7policies.append(expected_l7policy)
        if expected_l7rules:
            expected_l7policies[0]['rules'] = expected_l7rules
        if create_l7rules:
            create_l7policies[0]['rules'] = create_l7rules
        return create_l7policies, expected_l7policies

    def _get_l7rules_bodies(self, value="localhost"):
        create_l7rules = [{
            'type': constants.L7RULE_TYPE_HOST_NAME,
            'compare_type': constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
            'value': value,
            'invert': False,
            'admin_state_up': True
        }]
        expected_l7rules = [{
            'key': None,
            'project_id': self._project_id,
            'provisioning_status': constants.PENDING_CREATE,
            'operating_status': constants.OFFLINE,
            'tags': []
        }]
        expected_l7rules[0].update(create_l7rules[0])
        return create_l7rules, expected_l7rules

    def test_with_one_listener(self):
        create_listener, expected_listener = self._get_listener_bodies()
        create_lb, expected_lb = self._get_lb_bodies([create_listener],
                                                     [expected_listener])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_many_listeners(self):
        create_listener1, expected_listener1 = self._get_listener_bodies()
        create_listener2, expected_listener2 = self._get_listener_bodies(
            name='listener2', protocol_port=81)
        create_lb, expected_lb = self._get_lb_bodies(
            [create_listener1, create_listener2],
            [expected_listener1, expected_listener2])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_one_listener_one_pool(self):
        create_pool, expected_pool = self._get_pool_bodies()
        create_listener, expected_listener = self._get_listener_bodies(
            create_default_pool_name=create_pool['name'])
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_many_listeners_one_pool(self):
        create_pool1, expected_pool1 = self._get_pool_bodies()
        create_pool2, expected_pool2 = self._get_pool_bodies(name='pool2')
        create_listener1, expected_listener1 = self._get_listener_bodies(
            create_default_pool_name=create_pool1['name'])
        create_listener2, expected_listener2 = self._get_listener_bodies(
            create_default_pool_name=create_pool2['name'],
            name='listener2', protocol_port=81)
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener1, create_listener2],
            expected_listeners=[expected_listener1, expected_listener2],
            create_pools=[create_pool1, create_pool2])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_one_listener_one_member(self):
        create_member, expected_member = self._get_member_bodies()
        create_pool, expected_pool = self._get_pool_bodies(
            create_members=[create_member],
            expected_members=[expected_member])
        create_listener, expected_listener = self._get_listener_bodies(
            create_default_pool_name=create_pool['name'])
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_one_listener_one_hm(self):
        create_hm, expected_hm = self._get_hm_bodies()
        create_pool, expected_pool = self._get_pool_bodies(
            create_hm=create_hm,
            expected_hm=expected_hm)
        create_listener, expected_listener = self._get_listener_bodies(
            create_default_pool_name=create_pool['name'])
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    # TODO(johnsom) Fix this when there is a noop certificate manager
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_with_one_listener_sni_containers(self, mock_cert_data):
        cert1 = data_models.TLSContainer(certificate='cert 1')
        cert2 = data_models.TLSContainer(certificate='cert 2')
        cert3 = data_models.TLSContainer(certificate='cert 3')
        mock_cert_data.return_value = {'tls_cert': cert1,
                                       'sni_certs': [cert2, cert3]}
        create_sni_containers, expected_sni_containers = (
            self._get_sni_container_bodies())
        create_listener, expected_listener = self._get_listener_bodies(
            create_protocol=constants.PROTOCOL_TERMINATED_HTTPS,
            create_sni_containers=create_sni_containers,
            expected_sni_containers=expected_sni_containers)
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    @mock.patch('cryptography.hazmat.backends.default_backend')
    @mock.patch('cryptography.x509.load_pem_x509_crl')
    @mock.patch('cryptography.x509.load_pem_x509_certificate')
    @mock.patch('octavia.api.drivers.utils._get_secret_data')
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_with_full_listener_certs(self, mock_cert_data, mock_get_secret,
                                      mock_x509_cert, mock_x509_crl,
                                      mock_backend):
        cert1 = data_models.TLSContainer(certificate='cert 1')
        cert2 = data_models.TLSContainer(certificate='cert 2')
        cert3 = data_models.TLSContainer(certificate='cert 3')
        mock_get_secret.side_effect = ['ca cert', 'X509 CRL FILE']
        mock_cert_data.return_value = {'tls_cert': cert1,
                                       'sni_certs': [cert2, cert3]}
        cert_mock = mock.MagicMock()
        mock_x509_cert.return_value = cert_mock
        create_client_ca_tls_container, create_client_crl_container = (
            uuidutils.generate_uuid(), uuidutils.generate_uuid())
        expected_client_ca_tls_container = create_client_ca_tls_container
        create_client_authentication = constants.CLIENT_AUTH_MANDATORY
        expected_client_authentication = constants.CLIENT_AUTH_MANDATORY
        expected_client_crl_container = create_client_crl_container
        create_sni_containers, expected_sni_containers = (
            self._get_sni_container_bodies())
        create_listener, expected_listener = self._get_listener_bodies(
            create_protocol=constants.PROTOCOL_TERMINATED_HTTPS,
            create_sni_containers=create_sni_containers,
            expected_sni_containers=expected_sni_containers,
            create_client_ca_tls_container=create_client_ca_tls_container,
            expected_client_ca_tls_container=expected_client_ca_tls_container,
            create_client_authentication=create_client_authentication,
            expected_client_authentication=expected_client_authentication,
            create_client_crl_container=create_client_crl_container,
            expected_client_crl_container=expected_client_crl_container)
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_l7policy_redirect_pool_no_rule(self):
        create_pool, expected_pool = self._get_pool_bodies(create_members=[],
                                                           expected_members=[])
        create_l7policies, expected_l7policies = self._get_l7policies_bodies(
            create_pool_name=create_pool['name'])
        create_listener, expected_listener = self._get_listener_bodies(
            create_l7policies=create_l7policies,
            expected_l7policies=expected_l7policies)
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_l7policy_redirect_pool_one_rule(self):
        create_pool, expected_pool = self._get_pool_bodies(create_members=[],
                                                           expected_members=[])
        create_l7rules, expected_l7rules = self._get_l7rules_bodies()
        create_l7policies, expected_l7policies = self._get_l7policies_bodies(
            create_pool_name=create_pool['name'],
            create_l7rules=create_l7rules,
            expected_l7rules=expected_l7rules)
        create_listener, expected_listener = self._get_listener_bodies(
            create_l7policies=create_l7policies,
            expected_l7policies=expected_l7policies)
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_l7policies_one_redirect_pool_one_rule(self):
        create_pool, expected_pool = self._get_pool_bodies(create_members=[],
                                                           expected_members=[])
        create_l7rules, expected_l7rules = self._get_l7rules_bodies()
        create_l7policies, expected_l7policies = self._get_l7policies_bodies(
            create_pool_name=create_pool['name'],
            create_l7rules=create_l7rules,
            expected_l7rules=expected_l7rules)
        c_l7policies_url, e_l7policies_url = self._get_l7policies_bodies()
        for policy in c_l7policies_url:
            policy['position'] = 2
            create_l7policies.append(policy)
        for policy in e_l7policies_url:
            policy['position'] = 2
            expected_l7policies.append(policy)
        create_listener, expected_listener = self._get_listener_bodies(
            create_l7policies=create_l7policies,
            expected_l7policies=expected_l7policies)
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_l7policies_one_redirect_url_with_default_pool(self):
        create_pool, expected_pool = self._get_pool_bodies(create_members=[],
                                                           expected_members=[])
        create_l7rules, expected_l7rules = self._get_l7rules_bodies()
        create_l7policies, expected_l7policies = self._get_l7policies_bodies(
            create_l7rules=create_l7rules,
            expected_l7rules=expected_l7rules)
        create_listener, expected_listener = self._get_listener_bodies(
            create_default_pool_name=create_pool['name'],
            create_l7policies=create_l7policies,
            expected_l7policies=expected_l7policies,
        )
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_l7policies_redirect_pools_no_rules(self):
        create_pool, expected_pool = self._get_pool_bodies()
        create_l7policies, expected_l7policies = self._get_l7policies_bodies(
            create_pool_name=create_pool['name'])
        r_create_pool, r_expected_pool = self._get_pool_bodies(name='pool2')
        c_l7policies_url, e_l7policies_url = self._get_l7policies_bodies(
            create_pool_name=r_create_pool['name'])
        for policy in c_l7policies_url:
            policy['position'] = 2
            create_l7policies.append(policy)
        for policy in e_l7policies_url:
            policy['position'] = 2
            expected_l7policies.append(policy)
        create_listener, expected_listener = self._get_listener_bodies(
            create_l7policies=create_l7policies,
            expected_l7policies=expected_l7policies)
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool, r_create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_with_l7policy_redirect_pool_bad_rule(self):
        create_pool, expected_pool = self._get_pool_bodies(create_members=[],
                                                           expected_members=[])
        create_l7rules, expected_l7rules = self._get_l7rules_bodies(
            value="local host")
        create_l7policies, expected_l7policies = self._get_l7policies_bodies(
            create_pool_name=create_pool['name'],
            create_l7rules=create_l7rules,
            expected_l7rules=expected_l7rules)
        create_listener, expected_listener = self._get_listener_bodies(
            create_l7policies=create_l7policies,
            expected_l7policies=expected_l7policies)
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body, status=400)
        self.assertIn('L7Rule: Invalid characters',
                      response.json.get('faultstring'))

    def test_with_member_invalid_address(self):
        # 169.254.169.254 is the default invalid member address
        create_member = {
            'address': '169.254.169.254',
            'protocol_port': 80,
        }
        create_pool, _ = self._get_pool_bodies(
            create_members=[create_member],
            protocol=constants.PROTOCOL_TCP
        )
        create_listener, _ = self._get_listener_bodies(
            create_default_pool_name="pool1",
        )
        create_lb, _ = self._get_lb_bodies(
            [create_listener],
            [],
            create_pools=[create_pool]
        )

        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body, expect_errors=True)

        self.assertEqual(400, response.status_code)
        expect_error_msg = ("169.254.169.254 is not a valid option for member "
                            "address")
        self.assertEqual(expect_error_msg, response.json['faultstring'])

    def _test_with_one_of_everything_helper(self):
        create_member, expected_member = self._get_member_bodies()
        create_hm, expected_hm = self._get_hm_bodies()
        create_pool, expected_pool = self._get_pool_bodies(
            create_members=[create_member],
            expected_members=[expected_member],
            create_hm=create_hm,
            expected_hm=expected_hm,
            protocol=constants.PROTOCOL_TCP)
        create_sni_containers, expected_sni_containers = (
            self._get_sni_container_bodies())
        create_l7rules, expected_l7rules = self._get_l7rules_bodies()
        r_create_member, r_expected_member = self._get_member_bodies(
            protocol_port=88)
        r_create_pool, r_expected_pool = self._get_pool_bodies(
            create_members=[r_create_member],
            expected_members=[r_expected_member])
        create_l7policies, expected_l7policies = self._get_l7policies_bodies(
            create_pool_name=r_create_pool['name'],
            create_l7rules=create_l7rules,
            expected_l7rules=expected_l7rules)
        create_listener, expected_listener = self._get_listener_bodies(
            create_default_pool_name=create_pool['name'],
            create_protocol=constants.PROTOCOL_TERMINATED_HTTPS,
            create_l7policies=create_l7policies,
            expected_l7policies=expected_l7policies,
            create_sni_containers=create_sni_containers,
            expected_sni_containers=expected_sni_containers)
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        return body, expected_lb

    # TODO(johnsom) Fix this when there is a noop certificate manager
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_with_one_of_everything(self, mock_cert_data):
        cert1 = data_models.TLSContainer(certificate='cert 1')
        cert2 = data_models.TLSContainer(certificate='cert 2')
        cert3 = data_models.TLSContainer(certificate='cert 3')
        mock_cert_data.return_value = {'tls_cert': cert1,
                                       'sni_certs': [cert2, cert3]}
        body, expected_lb = self._test_with_one_of_everything_helper()
        response = self.post(self.LBS_PATH, body)
        api_lb = response.json.get(self.root_tag)
        self._assert_graphs_equal(expected_lb, api_lb)

    def test_db_create_failure(self):
        create_listener, expected_listener = self._get_listener_bodies()
        create_lb, _ = self._get_lb_bodies([create_listener],
                                           [expected_listener])
        body = self._build_body(create_lb)
        with mock.patch('octavia.db.repositories.Repositories.'
                        'create_load_balancer_and_vip') as repo_mock:
            repo_mock.side_effect = Exception('I am a DB Error')
            self.post(self.LBS_PATH, body, status=500)

    def test_pool_names_not_unique(self):
        create_pool1, expected_pool1 = self._get_pool_bodies()
        create_pool2, expected_pool2 = self._get_pool_bodies()
        create_listener, expected_listener = self._get_listener_bodies(
            create_default_pool_name=create_pool1['name'])
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool1, create_pool2])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body, status=400)
        self.assertIn("Pool names must be unique",
                      response.json.get('faultstring'))

    def test_pool_names_must_have_specs(self):
        create_pool, expected_pool = self._get_pool_bodies()
        create_listener, expected_listener = self._get_listener_bodies(
            create_default_pool_name="my_nonexistent_pool")
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body, status=400)
        self.assertIn("referenced but no full definition",
                      response.json.get('faultstring'))

    def test_pool_mandatory_attributes(self):
        create_pool, expected_pool = self._get_pool_bodies()
        create_pool.pop('protocol')
        create_listener, expected_listener = self._get_listener_bodies(
            create_default_pool_name=create_pool['name'])
        create_lb, expected_lb = self._get_lb_bodies(
            create_listeners=[create_listener],
            expected_listeners=[expected_listener],
            create_pools=[create_pool])
        body = self._build_body(create_lb)
        response = self.post(self.LBS_PATH, body, status=400)
        self.assertIn("missing required attribute: protocol",
                      response.json.get('faultstring'))

    def test_create_over_quota_lb(self):
        body, _ = self._test_with_one_of_everything_helper()
        self.start_quota_mock(data_models.LoadBalancer)
        self.post(self.LBS_PATH, body, status=403)

    def test_create_over_quota_pools(self):
        body, _ = self._test_with_one_of_everything_helper()
        self.start_quota_mock(data_models.Pool)
        self.post(self.LBS_PATH, body, status=403)

    def test_create_over_quota_listeners(self):
        body, _ = self._test_with_one_of_everything_helper()
        self.start_quota_mock(data_models.Listener)
        self.post(self.LBS_PATH, body, status=403)

    def test_create_over_quota_members(self):
        body, _ = self._test_with_one_of_everything_helper()
        self.start_quota_mock(data_models.Member)
        self.post(self.LBS_PATH, body, status=403)

    def test_create_over_quota_hms(self):
        body, _ = self._test_with_one_of_everything_helper()
        self.start_quota_mock(data_models.HealthMonitor)
        self.post(self.LBS_PATH, body, status=403)

    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_create_over_quota_sanity_check(self, mock_cert_data):
        cert1 = data_models.TLSContainer(certificate='cert 1')
        cert2 = data_models.TLSContainer(certificate='cert 2')
        cert3 = data_models.TLSContainer(certificate='cert 3')
        mock_cert_data.return_value = {'tls_cert': cert1,
                                       'sni_certs': [cert2, cert3]}
        # This one should create, as we don't check quotas on L7Policies
        body, _ = self._test_with_one_of_everything_helper()
        self.start_quota_mock(data_models.L7Policy)
        self.post(self.LBS_PATH, body)

    def _getStatus(self, lb_id):
        res = self.get(self.LB_PATH.format(lb_id=lb_id + "/status"))
        return res.json.get('statuses').get('loadbalancer')

    # Test the "statuses" alias for "status".
    # This is required for backward compatibility with neutron-lbaas
    def test_statuses(self):
        lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')

        statuses = self.get(self.LB_PATH.format(lb_id=lb['id'] + "/statuses"))
        response = statuses.json.get('statuses').get('loadbalancer')
        self.assertEqual(lb['name'], response['name'])
        self.assertEqual(lb['id'], response['id'])
        self.assertEqual(lb['operating_status'],
                         response['operating_status'])
        self.assertEqual(lb['provisioning_status'],
                         response['provisioning_status'])

    def test_status(self):
        lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')

        response = self._getStatus(lb['id'])
        self.assertEqual(lb['name'], response['name'])
        self.assertEqual(lb['id'], response['id'])
        self.assertEqual(lb['operating_status'],
                         response['operating_status'])
        self.assertEqual(lb['provisioning_status'],
                         response['provisioning_status'])

    def _assertLB(self, lb, response):
        self.assertEqual(lb['name'], response['name'])
        self.assertEqual(lb['id'], response['id'])
        self.assertEqual(constants.ONLINE,
                         response['operating_status'])
        self.assertEqual(constants.PENDING_UPDATE,
                         response['provisioning_status'])

    def test_statuses_listener(self):
        lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')
        self.set_lb_status(lb['id'])
        listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb['id']).get('listener')

        response = self._getStatus(lb['id'])

        self._assertLB(lb, response)
        response = response.get('listeners')[0]
        self.assertEqual(listener['name'], response['name'])
        self.assertEqual(listener['id'], response['id'])
        self.assertEqual(listener['operating_status'],
                         response['operating_status'])
        self.assertEqual(listener['provisioning_status'],
                         response['provisioning_status'])

    def _assertListener(self, listener, response,
                        prov_status=constants.ACTIVE):
        self.assertEqual(listener['name'], response['name'])
        self.assertEqual(listener['id'], response['id'])
        self.assertEqual(constants.ONLINE,
                         response['operating_status'])
        self.assertEqual(prov_status, response['provisioning_status'])

    def _assertListenerPending(self, listener, response):
        self._assertListener(listener, response, constants.PENDING_UPDATE)

    def test_statuses_multiple_listeners(self):
        lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')
        self.set_lb_status(lb['id'])
        listener1 = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb['id']).get('listener')

        self.set_lb_status(lb['id'])
        listener2 = self.create_listener(
            constants.PROTOCOL_HTTPS, 443, lb['id']).get('listener')

        response = self._getStatus(lb['id'])

        self._assertLB(lb, response)
        self._assertListener(listener1, response.get('listeners')[0])
        response = response.get('listeners')[1]
        self.assertEqual(listener2['name'], response['name'])
        self.assertEqual(listener2['id'], response['id'])
        self.assertEqual(listener2['operating_status'],
                         response['operating_status'])
        self.assertEqual(listener2['provisioning_status'],
                         response['provisioning_status'])

    def test_statuses_pool(self):
        lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')
        self.set_lb_status(lb['id'])
        listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb['id']).get('listener')
        self.set_lb_status(lb['id'])
        pool = self.create_pool(
            lb['id'],
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=listener['id']).get('pool')

        response = self._getStatus(lb['id'])

        self._assertLB(lb, response)
        self._assertListenerPending(listener, response.get('listeners')[0])
        response = response.get('listeners')[0]['pools'][0]
        self.assertEqual(pool['name'], response['name'])
        self.assertEqual(pool['id'], response['id'])
        self.assertEqual(pool['operating_status'],
                         response['operating_status'])
        self.assertEqual(pool['provisioning_status'],
                         response['provisioning_status'])

    def _assertPool(self, pool, response,
                    prov_status=constants.ACTIVE):
        self.assertEqual(pool['name'], response['name'])
        self.assertEqual(pool['id'], response['id'])
        self.assertEqual(constants.ONLINE,
                         response['operating_status'])
        self.assertEqual(prov_status, response['provisioning_status'])

    def _assertPoolPending(self, pool, response):
        self._assertPool(pool, response, constants.PENDING_UPDATE)

    def test_statuses_pools(self):
        lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')
        self.set_lb_status(lb['id'])
        listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb['id']).get('listener')
        self.set_lb_status(lb['id'])
        pool1 = self.create_pool(
            lb['id'],
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=listener['id']).get('pool')
        self.set_lb_status(lb['id'])
        pool2 = self.create_pool(
            lb['id'],
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN).get('pool')
        self.set_lb_status(lb['id'])
        l7_policy = self.create_l7policy(
            listener['id'],
            constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
            redirect_pool_id=pool2.get('id')).get('l7policy')
        self.set_lb_status(lb['id'])
        self.create_l7rule(
            l7_policy['id'], constants.L7RULE_TYPE_HOST_NAME,
            constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
            'www.example.com').get(self.root_tag)

        response = self._getStatus(lb['id'])

        self._assertLB(lb, response)
        self._assertListenerPending(listener, response.get('listeners')[0])
        self._assertPool(pool1, response.get('listeners')[0]['pools'][0])
        self._assertPool(pool2, response.get('listeners')[0]['pools'][1])

    def test_statuses_health_monitor(self):
        lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')
        self.set_lb_status(lb['id'])
        listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb['id']).get('listener')
        self.set_lb_status(lb['id'])
        pool = self.create_pool(
            lb['id'],
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=listener['id']).get('pool')
        self.set_lb_status(lb['id'])
        hm = self.create_health_monitor(
            pool['id'], constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get('healthmonitor')

        response = self._getStatus(lb['id'])

        self._assertLB(lb, response)
        self._assertListenerPending(listener, response.get('listeners')[0])
        self._assertPoolPending(pool, response.get('listeners')[0]['pools'][0])
        response = response.get('listeners')[0]['pools'][0]['health_monitor']
        self.assertEqual(hm['name'], response['name'])
        self.assertEqual(hm['id'], response['id'])
        self.assertEqual(hm['type'], response['type'])
        self.assertEqual(hm['operating_status'],
                         response['operating_status'])
        self.assertEqual(hm['provisioning_status'],
                         response['provisioning_status'])

    def test_statuses_member(self):
        lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')
        self.set_lb_status(lb['id'])
        listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb['id']).get('listener')
        self.set_lb_status(lb['id'])
        pool = self.create_pool(
            lb['id'],
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=listener['id']).get('pool')
        self.set_lb_status(lb['id'])
        member = self.create_member(
            pool['id'], '10.0.0.1', 80).get('member')

        response = self._getStatus(lb['id'])

        self._assertLB(lb, response)
        self._assertListenerPending(listener, response.get('listeners')[0])
        self._assertPoolPending(pool, response.get('listeners')[0]['pools'][0])
        response = response.get('listeners')[0]['pools'][0]['members'][0]
        self.assertEqual(member['name'], response['name'])
        self.assertEqual(member['id'], response['id'])
        self.assertEqual(member['address'], response['address'])
        self.assertEqual(member['protocol_port'], response['protocol_port'])
        self.assertEqual(member['operating_status'],
                         response['operating_status'])
        self.assertEqual(member['provisioning_status'],
                         response['provisioning_status'])

    def test_statuses_members(self):
        lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')
        self.set_lb_status(lb['id'])
        listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb['id']).get('listener')
        self.set_lb_status(lb['id'])
        pool = self.create_pool(
            lb['id'],
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=listener['id']).get('pool')
        self.set_lb_status(lb['id'])
        member1 = self.create_member(
            pool['id'], '10.0.0.1', 80).get('member')
        self.set_lb_status(lb['id'])
        member2 = self.create_member(
            pool['id'], '10.0.0.2', 88, name='test').get('member')

        response = self._getStatus(lb['id'])

        self._assertLB(lb, response)
        self._assertListenerPending(listener, response.get('listeners')[0])
        self._assertPoolPending(pool, response.get('listeners')[0]['pools'][0])
        members = response.get('listeners')[0]['pools'][0]['members']
        response = members[0]
        self.assertEqual(member1['name'], response['name'])
        self.assertEqual(member1['id'], response['id'])
        self.assertEqual(member1['address'], response['address'])
        self.assertEqual(member1['protocol_port'], response['protocol_port'])
        self.assertEqual(constants.ONLINE,
                         response['operating_status'])
        self.assertEqual(constants.ACTIVE,
                         response['provisioning_status'])
        response = members[1]
        self.assertEqual(member2['name'], response['name'])
        self.assertEqual(member2['id'], response['id'])
        self.assertEqual(member2['address'], response['address'])
        self.assertEqual(member2['protocol_port'], response['protocol_port'])

    def test_statuses_authorized(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(
            uuidutils.generate_uuid(),
            project_id=project_id).get('loadbalancer')

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)

        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                response = self._getStatus(lb['id'])
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        self.assertEqual(lb['name'], response['name'])
        self.assertEqual(lb['id'], response['id'])
        self.assertEqual(lb['operating_status'],
                         response['operating_status'])
        self.assertEqual(lb['provisioning_status'],
                         response['provisioning_status'])

    def test_statuses_not_authorized(self):
        lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):

            res = self.get(self.LB_PATH.format(lb_id=lb['id'] + "/status"),
                           status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, res.json)

    def test_statuses_get_deleted(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(
            uuidutils.generate_uuid(),
            project_id=project_id).get('loadbalancer')
        self.set_lb_status(lb['id'], status=constants.DELETED)
        self.get(self.LB_PATH.format(lb_id=lb['id'] + "/status"),
                 status=404)

    def _getStats(self, lb_id):
        res = self.get(self.LB_PATH.format(lb_id=lb_id + "/stats"))
        return res.json.get('stats')

    def test_statistics(self):
        lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')
        self.set_lb_status(lb['id'])
        li = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb.get('id')).get('listener')
        amphora = self.create_amphora(uuidutils.generate_uuid(), lb['id'])
        ls = self.create_listener_stats_dynamic(
            listener_id=li.get('id'),
            amphora_id=amphora.id,
            bytes_in=random.randint(1, 9),
            bytes_out=random.randint(1, 9),
            total_connections=random.randint(1, 9),
            request_errors=random.randint(1, 9))

        response = self._getStats(lb['id'])
        self.assertEqual(ls['bytes_in'], response['bytes_in'])
        self.assertEqual(ls['bytes_out'], response['bytes_out'])
        self.assertEqual(ls['total_connections'],
                         response['total_connections'])
        self.assertEqual(ls['active_connections'],
                         response['active_connections'])
        self.assertEqual(ls['request_errors'],
                         response['request_errors'])

    def test_statistics_authorized(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(
            uuidutils.generate_uuid(),
            project_id=project_id).get('loadbalancer')
        self.set_lb_status(lb['id'])
        li = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb.get('id')).get('listener')
        amphora = self.create_amphora(uuidutils.generate_uuid(), lb['id'])
        ls = self.create_listener_stats_dynamic(
            listener_id=li.get('id'),
            amphora_id=amphora.id,
            bytes_in=random.randint(1, 9),
            bytes_out=random.randint(1, 9),
            total_connections=random.randint(1, 9),
            request_errors=random.randint(1, 9))

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)

        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                response = self._getStats(lb['id'])
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        self.assertEqual(ls['bytes_in'], response['bytes_in'])
        self.assertEqual(ls['bytes_out'], response['bytes_out'])
        self.assertEqual(ls['total_connections'],
                         response['total_connections'])
        self.assertEqual(ls['active_connections'],
                         response['active_connections'])
        self.assertEqual(ls['request_errors'],
                         response['request_errors'])

    def test_statistics_not_authorized(self):
        lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')
        self.set_lb_status(lb['id'])
        li = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb.get('id')).get('listener')
        amphora = self.create_amphora(uuidutils.generate_uuid(), lb['id'])
        self.create_listener_stats_dynamic(
            listener_id=li.get('id'),
            amphora_id=amphora.id,
            bytes_in=random.randint(1, 9),
            bytes_out=random.randint(1, 9),
            total_connections=random.randint(1, 9))
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            res = self.get(self.LB_PATH.format(lb_id=lb['id'] + "/stats"),
                           status=403)

        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, res.json)

    def test_statistics_get_deleted(self):
        lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')
        self.set_lb_status(lb['id'])
        li = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb.get('id')).get('listener')
        amphora = self.create_amphora(uuidutils.generate_uuid(), lb['id'])
        self.create_listener_stats_dynamic(
            listener_id=li.get('id'),
            amphora_id=amphora.id,
            bytes_in=random.randint(1, 9),
            bytes_out=random.randint(1, 9),
            total_connections=random.randint(1, 9))
        self.set_lb_status(lb['id'], status=constants.DELETED)
        self.get(self.LB_PATH.format(lb_id=lb['id'] + "/stats"), status=404)
