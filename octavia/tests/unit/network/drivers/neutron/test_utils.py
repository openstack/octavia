#    Copyright 2017 GoDaddy
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
from octavia.network.drivers.neutron import utils
from octavia.tests.common import constants as t_constants
from octavia.tests.unit import base


class TestNeutronUtils(base.TestCase):

    def setUp(self):
        super(TestNeutronUtils, self).setUp()

    def _compare_ignore_value_none(self, obj1_in, obj2_in):
        obj1 = {key: obj1_in[key] for key in obj1_in
                if obj1_in[key] is not None}
        obj2 = {key: obj2_in[key] for key in obj2_in
                if obj2_in[key] is not None}
        self.assertEqual(obj1, obj2)

    def _in_ignore_value_none(self, needle, haystack):
        newneedle = {key: needle[key] for key in needle
                     if needle[key] is not None}
        newhaystack = []
        for hay in haystack:
            newhaystack.append({key: hay[key] for key in hay
                                if hay[key] is not None})
        self.assertIn(newneedle, newhaystack)

    def test_convert_subnet_dict_to_model(self):
        model_obj = utils.convert_subnet_dict_to_model(
            t_constants.MOCK_SUBNET)
        assert_dict = dict(
            id=t_constants.MOCK_SUBNET_ID,
            name=t_constants.MOCK_SUBNET_NAME,
            network_id=t_constants.MOCK_NETWORK_ID,
            project_id=t_constants.MOCK_PROJECT_ID,
            gateway_ip=t_constants.MOCK_GATEWAY_IP,
            cidr=t_constants.MOCK_CIDR,
            ip_version=t_constants.MOCK_IP_VERSION,
            host_routes=[],
        )
        self._compare_ignore_value_none(model_obj.to_dict(), assert_dict)

    def test_convert_port_dict_to_model(self):
        model_obj = utils.convert_port_dict_to_model(
            t_constants.MOCK_NEUTRON_PORT)
        assert_dict = dict(
            id=t_constants.MOCK_PORT_ID,
            name=t_constants.MOCK_PORT_NAME,
            device_id=t_constants.MOCK_DEVICE_ID,
            device_owner=t_constants.MOCK_DEVICE_OWNER,
            mac_address=t_constants.MOCK_MAC_ADDR,
            network_id=t_constants.MOCK_NETWORK_ID,
            status=t_constants.MOCK_STATUS,
            project_id=t_constants.MOCK_PROJECT_ID,
            admin_state_up=t_constants.MOCK_ADMIN_STATE_UP,
            fixed_ips=[],
        )
        self._compare_ignore_value_none(model_obj.to_dict(), assert_dict)
        fixed_ips = t_constants.MOCK_NEUTRON_PORT['port']['fixed_ips']
        for ip in model_obj.fixed_ips:
            self._in_ignore_value_none(ip.to_dict(), fixed_ips)

    def test_convert_network_dict_to_model(self):
        model_obj = utils.convert_network_dict_to_model(
            t_constants.MOCK_NETWORK)
        assert_dict = dict(
            id=t_constants.MOCK_NETWORK_ID,
            name=t_constants.MOCK_NETWORK_NAME,
            subnets=[t_constants.MOCK_SUBNET_ID],
            project_id=t_constants.MOCK_PROJECT_ID,
            admin_state_up=t_constants.MOCK_ADMIN_STATE_UP,
            mtu=t_constants.MOCK_MTU,
            provider_network_type=t_constants.MOCK_NETWORK_TYPE,
            provider_physical_network=t_constants.MOCK_NETWORK_NAME,
            provider_segmentation_id=t_constants.MOCK_SEGMENTATION_ID,
            router_external=t_constants.MOCK_ROUTER_EXTERNAL
        )
        model_dict = model_obj.to_dict()
        model_dict['subnets'] = model_obj.subnets
        self._compare_ignore_value_none(model_dict, assert_dict)

    def test_convert_fixed_ip_dict_to_model(self):
        model_obj = utils.convert_fixed_ip_dict_to_model(
            t_constants.MOCK_FIXED_IP)
        assert_dict = dict(
            subnet_id=t_constants.MOCK_SUBNET_ID,
            ip_address=t_constants.MOCK_IP_ADDRESS
        )
        self._compare_ignore_value_none(model_obj.to_dict(), assert_dict)

    def test_convert_floatingip_dict_to_model(self):
        model_obj = utils.convert_floatingip_dict_to_model(
            t_constants.MOCK_FLOATING_IP)
        assert_dict = dict(
            id=t_constants.MOCK_FLOATING_IP_ID,
            description=t_constants.MOCK_FLOATING_IP_DESC,
            project_id=t_constants.MOCK_PROJECT_ID,
            status=t_constants.MOCK_STATUS,
            router_id=t_constants.MOCK_ROUTER_ID,
            port_id=t_constants.MOCK_PORT_ID,
            floating_network_id=t_constants.MOCK_NETWORK_ID,
            network_id=t_constants.MOCK_NETWORK_ID,
            floating_ip_address=t_constants.MOCK_IP_ADDRESS,
            fixed_ip_address=t_constants.MOCK_IP_ADDRESS2,
            fixed_port_id=t_constants.MOCK_PORT_ID2
        )
        self._compare_ignore_value_none(model_obj.to_dict(), assert_dict)

    def test_convert_network_ip_availability_dict_to_model(self):
        model_obj = utils.convert_network_ip_availability_dict_to_model(
            t_constants.MOCK_NETWORK_IP_AVAILABILITY)
        assert_dict = dict(
            network_id=t_constants.MOCK_NETWORK_ID,
            tenant_id=t_constants.MOCK_PROJECT_ID,
            network_name=t_constants.MOCK_NETWORK_NAME,
            total_ips=t_constants.MOCK_NETWORK_TOTAL_IPS,
            used_ips=t_constants.MOCK_NETWORK_USED_IPS,
            subnet_ip_availability=t_constants.MOCK_SUBNET_IP_AVAILABILITY
        )
        self._compare_ignore_value_none(model_obj.to_dict(recurse=True),
                                        assert_dict)
