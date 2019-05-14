# Copyright 2016 Blue Box, an IBM Company
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

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

import octavia.common.constants as constants
import octavia.common.exceptions as exceptions
import octavia.common.validate as validate
from octavia.network import base as network_base
from octavia.network import data_models as network_models
import octavia.tests.unit.base as base


class TestValidations(base.TestCase):
    # Note that particularly complex validation testing is handled via
    # functional tests elsewhere (ex. repository tests)

    def setUp(self):
        super(TestValidations, self).setUp()
        self.conf = oslo_fixture.Config(cfg.CONF)

    def test_validate_url(self):
        ret = validate.url('http://example.com')
        self.assertTrue(ret)

    def test_validate_bad_url(self):
        self.assertRaises(exceptions.InvalidURL, validate.url, 'bad url')

    def test_validate_url_bad_schema(self):
        self.assertRaises(exceptions.InvalidURL, validate.url,
                          'ssh://www.example.com/')

    def test_validate_header_name(self):
        ret = validate.header_name('Some-header')
        self.assertTrue(ret)

    def test_validate_bad_header_name(self):
        self.assertRaises(exceptions.InvalidString,
                          validate.cookie_value_string,
                          'bad header')

    def test_validate_cookie_value_string(self):
        ret = validate.cookie_value_string('some-cookie')
        self.assertTrue(ret)

    def test_validate_bad_cookie_value_string(self):
        self.assertRaises(exceptions.InvalidString,
                          validate.cookie_value_string,
                          'bad cookie value;')

    def test_validate_header_value_string(self):
        ret = validate.header_value_string('some-value')
        self.assertTrue(ret)

    def test_validate_header_value_string_quoted(self):
        ret = validate.header_value_string('"some value"')
        self.assertTrue(ret)

    def test_validate_bad_header_value_string(self):
        self.assertRaises(exceptions.InvalidString,
                          validate.header_value_string,
                          '\x18')

    def test_validate_regex(self):
        ret = validate.regex('some regex.*')
        self.assertTrue(ret)

    def test_validate_bad_regex(self):
        self.assertRaises(exceptions.InvalidRegex, validate.regex,
                          'bad regex\\')

    def test_sanitize_l7policy_api_args_action_reject(self):
        l7p = {'action': constants.L7POLICY_ACTION_REJECT,
               'redirect_url': 'http://www.example.com/',
               'redirect_pool_id': 'test-pool',
               'redirect_pool': {
                   'protocol': constants.PROTOCOL_HTTP,
                   'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN}}
        s_l7p = validate.sanitize_l7policy_api_args(l7p)
        self.assertIsNone(s_l7p['redirect_url'])
        self.assertIsNone(s_l7p['redirect_pool_id'])
        self.assertNotIn('redirect_pool', s_l7p.keys())

    def test_sanitize_l7policy_api_args_action_rdr_pool_id(self):
        l7p = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
               'redirect_url': 'http://www.example.com/',
               'redirect_pool_id': 'test-pool',
               'redirect_pool': {
                   'protocol': constants.PROTOCOL_HTTP,
                   'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN}}
        s_l7p = validate.sanitize_l7policy_api_args(l7p)
        self.assertIsNone(s_l7p['redirect_url'])
        self.assertNotIn('redirect_pool', s_l7p.keys())
        self.assertIn('redirect_pool_id', s_l7p.keys())

    def test_sanitize_l7policy_api_args_action_rdr_pool_model(self):
        l7p = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
               'redirect_url': 'http://www.example.com/',
               'redirect_pool_id': None,
               'redirect_pool': {
                   'protocol': constants.PROTOCOL_HTTP,
                   'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN}}
        s_l7p = validate.sanitize_l7policy_api_args(l7p)
        self.assertIsNone(s_l7p['redirect_url'])
        self.assertNotIn('redirect_pool_id', s_l7p.keys())
        self.assertIn('redirect_pool', s_l7p.keys())

    def test_sanitize_l7policy_api_args_action_rdr_url(self):
        l7p = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_URL,
               'redirect_url': 'http://www.example.com/',
               'redirect_pool_id': 'test-pool',
               'redirect_pool': {
                   'protocol': constants.PROTOCOL_HTTP,
                   'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN}}
        s_l7p = validate.sanitize_l7policy_api_args(l7p)
        self.assertIn('redirect_url', s_l7p.keys())
        self.assertIsNone(s_l7p['redirect_pool_id'])
        self.assertNotIn('redirect_pool', s_l7p.keys())

    def test_sanitize_l7policy_api_args_bad_action(self):
        l7p = {'action': 'bad-action',
               'redirect_url': 'http://www.example.com/',
               'redirect_pool_id': 'test-pool',
               'redirect_pool': {
                   'protocol': constants.PROTOCOL_HTTP,
                   'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN}}
        self.assertRaises(exceptions.InvalidL7PolicyAction,
                          validate.sanitize_l7policy_api_args, l7p)

    def test_sanitize_l7policy_api_args_action_none(self):
        l7p = {'action': None}
        self.assertRaises(exceptions.InvalidL7PolicyAction,
                          validate.sanitize_l7policy_api_args, l7p, True)

    def test_sanitize_l7policy_api_args_both_rdr_args_a(self):
        l7p = {'redirect_url': 'http://www.example.com/',
               'redirect_pool_id': 'test-pool'}
        self.assertRaises(exceptions.InvalidL7PolicyArgs,
                          validate.sanitize_l7policy_api_args, l7p)

    def test_sanitize_l7policy_api_args_both_rdr_args_b(self):
        l7p = {'redirect_url': 'http://www.example.com/',
               'redirect_pool': {
                   'protocol': constants.PROTOCOL_HTTP,
                   'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN}}
        self.assertRaises(exceptions.InvalidL7PolicyArgs,
                          validate.sanitize_l7policy_api_args, l7p)

    def test_sanitize_l7policy_api_args_rdr_pool_id(self):
        l7p = {'redirect_pool_id': 'test-pool',
               'redirect_url': None,
               'redirect_pool': None}
        s_l7p = validate.sanitize_l7policy_api_args(l7p)
        self.assertIn('redirect_pool_id', s_l7p.keys())
        self.assertIsNone(s_l7p['redirect_url'])
        self.assertNotIn('redirect_pool', s_l7p.keys())
        self.assertIn('action', s_l7p.keys())
        self.assertEqual(constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
                         s_l7p['action'])

    def test_sanitize_l7policy_api_args_rdr_pool_noid(self):
        l7p = {'redirect_pool_id': None,
               'redirect_url': None,
               'redirect_pool': {
                   'protocol': constants.PROTOCOL_HTTP,
                   'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN}}
        s_l7p = validate.sanitize_l7policy_api_args(l7p)
        self.assertIn('redirect_pool', s_l7p.keys())
        self.assertIsNone(s_l7p['redirect_url'])
        self.assertNotIn('redirect_pool_id', s_l7p.keys())
        self.assertIn('action', s_l7p.keys())
        self.assertEqual(constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
                         s_l7p['action'])

    def test_sanitize_l7policy_api_args_rdr_pool_id_none_create(self):
        l7p = {'redirect_pool_id': None}
        self.assertRaises(exceptions.InvalidL7PolicyAction,
                          validate.sanitize_l7policy_api_args, l7p, True)

    def test_sanitize_l7policy_api_args_rdr_pool_noid_none_create(self):
        l7p = {'redirect_pool': None}
        self.assertRaises(exceptions.InvalidL7PolicyAction,
                          validate.sanitize_l7policy_api_args, l7p, True)

    def test_sanitize_l7policy_api_args_rdr_pool_both_none_create(self):
        l7p = {'redirect_pool': None,
               'redirect_pool_id': None}
        self.assertRaises(exceptions.InvalidL7PolicyAction,
                          validate.sanitize_l7policy_api_args, l7p, True)

    def test_sanitize_l7policy_api_args_rdr_url(self):
        l7p = {'redirect_pool_id': None,
               'redirect_url': 'http://www.example.com/',
               'redirect_pool': None}
        s_l7p = validate.sanitize_l7policy_api_args(l7p)
        self.assertIsNone(s_l7p['redirect_pool_id'])
        self.assertNotIn('redirect_pool', s_l7p.keys())
        self.assertIn('redirect_url', s_l7p.keys())
        self.assertIn('action', s_l7p.keys())
        self.assertEqual(constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                         s_l7p['action'])

    def test_sanitize_l7policy_api_args_rdr_url_none_create(self):
        l7p = {'redirect_url': None}
        self.assertRaises(exceptions.InvalidL7PolicyAction,
                          validate.sanitize_l7policy_api_args, l7p, True)

    def test_sanitize_l7policy_api_args_rdr_url_bad_url(self):
        l7p = {'redirect_url': 'bad url'}
        self.assertRaises(exceptions.InvalidURL,
                          validate.sanitize_l7policy_api_args, l7p, True)

    def test_sanitize_l7policy_api_args_update_action_rdr_pool_arg(self):
        l7p = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
               'redirect_url': None,
               'redirect_pool_id': None,
               'redirect_pool': None}
        self.assertRaises(exceptions.InvalidL7PolicyArgs,
                          validate.sanitize_l7policy_api_args, l7p)

    def test_sanitize_l7policy_api_args_update_action_rdr_url_arg(self):
        l7p = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_URL,
               'redirect_url': None,
               'redirect_pool_id': None,
               'redirect_pool': None}
        self.assertRaises(exceptions.InvalidL7PolicyArgs,
                          validate.sanitize_l7policy_api_args, l7p)

    def test_sanitize_l7policy_api_args_create_must_have_action(self):
        l7p = {}
        self.assertRaises(exceptions.InvalidL7PolicyAction,
                          validate.sanitize_l7policy_api_args, l7p, True)

    def test_sanitize_l7policy_api_args_update_must_have_args(self):
        l7p = {}
        self.assertRaises(exceptions.InvalidL7PolicyArgs,
                          validate.sanitize_l7policy_api_args, l7p)

    def test_port_exists_with_bad_port(self):
        port_id = uuidutils.generate_uuid()
        with mock.patch(
                'octavia.common.utils.get_network_driver') as net_mock:
            net_mock.return_value.get_port = mock.Mock(
                side_effect=network_base.PortNotFound('Port not found'))
            self.assertRaises(
                exceptions.InvalidSubresource,
                validate.port_exists, port_id)

    def test_port_exists_with_valid_port(self):
        port_id = uuidutils.generate_uuid()
        port = network_models.Port(id=port_id)
        with mock.patch(
                'octavia.common.utils.get_network_driver') as net_mock:
            net_mock.return_value.get_port.return_value = port
            self.assertEqual(validate.port_exists(port_id), port)

    def test_check_port_in_use(self):
        port_id = uuidutils.generate_uuid()
        device_id = uuidutils.generate_uuid()
        port = network_models.Port(id=port_id, device_id=device_id)
        with mock.patch(
                'octavia.common.utils.get_network_driver') as net_mock:
            net_mock.return_value.get_port.device_id = port
            self.assertRaises(
                exceptions.ValidationException,
                validate.check_port_in_use, port)

    def test_subnet_exists_with_bad_subnet(self):
        subnet_id = uuidutils.generate_uuid()
        with mock.patch(
                'octavia.common.utils.get_network_driver') as net_mock:
            net_mock.return_value.get_subnet = mock.Mock(
                side_effect=network_base.SubnetNotFound('Subnet not found'))
            self.assertRaises(
                exceptions.InvalidSubresource,
                validate.subnet_exists, subnet_id)

    def test_subnet_exists_with_valid_subnet(self):
        subnet_id = uuidutils.generate_uuid()
        subnet = network_models.Subnet(id=subnet_id)
        with mock.patch(
                'octavia.common.utils.get_network_driver') as net_mock:
            net_mock.return_value.get_subnet.return_value = subnet
            self.assertEqual(validate.subnet_exists(subnet_id), subnet)

    def test_network_exists_with_bad_network(self):
        network_id = uuidutils.generate_uuid()
        with mock.patch(
                'octavia.common.utils.get_network_driver') as net_mock:
            net_mock.return_value.get_network = mock.Mock(
                side_effect=network_base.NetworkNotFound('Network not found'))
            self.assertRaises(
                exceptions.InvalidSubresource,
                validate.network_exists_optionally_contains_subnet, network_id)

    def test_network_exists_with_valid_network(self):
        network_id = uuidutils.generate_uuid()
        network = network_models.Network(id=network_id)
        with mock.patch(
                'octavia.common.utils.get_network_driver') as net_mock:
            net_mock.return_value.get_network.return_value = network
            self.assertEqual(
                validate.network_exists_optionally_contains_subnet(network_id),
                network)

    def test_network_exists_with_valid_subnet(self):
        network_id = uuidutils.generate_uuid()
        subnet_id = uuidutils.generate_uuid()
        network = network_models.Network(
            id=network_id,
            subnets=[subnet_id])
        with mock.patch(
                'octavia.common.utils.get_network_driver') as net_mock:
            net_mock.return_value.get_network.return_value = network
            self.assertEqual(
                validate.network_exists_optionally_contains_subnet(
                    network_id, subnet_id),
                network)

    def test_network_exists_with_bad_subnet(self):
        network_id = uuidutils.generate_uuid()
        subnet_id = uuidutils.generate_uuid()
        network = network_models.Network(id=network_id)
        with mock.patch(
                'octavia.common.utils.get_network_driver') as net_mock:
            net_mock.return_value.get_network.return_value = network
            self.assertRaises(
                exceptions.InvalidSubresource,
                validate.network_exists_optionally_contains_subnet,
                network_id, subnet_id)

    def test_network_allowed_by_config(self):
        net_id1 = uuidutils.generate_uuid()
        net_id2 = uuidutils.generate_uuid()
        net_id3 = uuidutils.generate_uuid()
        valid_net_ids = ",".join((net_id1, net_id2))
        self.conf.config(group="networking", valid_vip_networks=valid_net_ids)
        validate.network_allowed_by_config(net_id1)
        validate.network_allowed_by_config(net_id2)
        self.assertRaises(
            exceptions.ValidationException,
            validate.network_allowed_by_config, net_id3)

    def test_qos_policy_exists(self):
        qos_policy_id = uuidutils.generate_uuid()
        qos_policy = network_models.QosPolicy(id=qos_policy_id)
        with mock.patch(
                'octavia.common.utils.get_network_driver') as net_mock:
            net_mock.return_value.get_qos_policy.return_value = qos_policy
            self.assertEqual(
                validate.qos_policy_exists(qos_policy_id),
                qos_policy)

            net_mock.return_value.get_qos_policy.side_effect = Exception
            self.assertRaises(exceptions.InvalidSubresource,
                              validate.qos_policy_exists,
                              qos_policy_id)

    def test_qos_extension_enabled(self):
        network_driver = mock.Mock()
        network_driver.qos_enabled.return_value = True
        self.assertIsNone(validate.qos_extension_enabled(network_driver))

    def test_qos_extension_disabled(self):
        network_driver = mock.Mock()
        network_driver.qos_enabled.return_value = False
        self.assertRaises(exceptions.ValidationException,
                          validate.qos_extension_enabled,
                          network_driver)

    def test_check_session_persistence(self):
        valid_cookie_name_dict = {'type': 'APP_COOKIE',
                                  'cookie_name': 'chocolate_chip'}
        invalid_cookie_name_dict = {'type': 'APP_COOKIE',
                                    'cookie_name': '@chocolate_chip'}
        invalid_type_HTTP_cookie_name_dict = {'type': 'HTTP_COOKIE',
                                              'cookie_name': 'chocolate_chip'}
        invalid_type_IP_cookie_name_dict = {'type': 'SOURCE_IP',
                                            'cookie_name': 'chocolate_chip'}
        invalid_missing_cookie_name_dict = {'type': 'APP_COOKIE'}

        # Validate that a good cookie name passes
        validate.check_session_persistence(valid_cookie_name_dict)

        # Test raises with providing an invalid cookie name
        self.assertRaises(exceptions.ValidationException,
                          validate.check_session_persistence,
                          invalid_cookie_name_dict)

        # Test raises type HTTP_COOKIE and providing cookie_name
        self.assertRaises(exceptions.ValidationException,
                          validate.check_session_persistence,
                          invalid_type_HTTP_cookie_name_dict)

        # Test raises type SOURCE_IP and providing cookie_name
        self.assertRaises(exceptions.ValidationException,
                          validate.check_session_persistence,
                          invalid_type_IP_cookie_name_dict)

        # Test raises when type APP_COOKIE but no cookie_name
        self.assertRaises(exceptions.ValidationException,
                          validate.check_session_persistence,
                          invalid_missing_cookie_name_dict)

        # Test catch all exception raises a user friendly message
        with mock.patch('re.compile') as compile_mock:
            compile_mock.side_effect = Exception
            self.assertRaises(exceptions.ValidationException,
                              validate.check_session_persistence,
                              valid_cookie_name_dict)

    def test_ip_not_reserved(self):
        self.conf.config(group="networking", reserved_ips=['198.51.100.4'])

        # Test good address
        validate.ip_not_reserved('203.0.113.5')

        # Test IPv4 reserved address
        self.assertRaises(exceptions.InvalidOption,
                          validate.ip_not_reserved,
                          '198.51.100.4')

        self.conf.config(
            group="networking",
            reserved_ips=['2001:0DB8:0000:0000:0000:0000:0000:0005'])

        # Test good IPv6 address
        validate.ip_not_reserved('2001:0DB8::9')

        # Test reserved IPv6 expanded
        self.assertRaises(exceptions.InvalidOption,
                          validate.ip_not_reserved,
                          '2001:0DB8:0000:0000:0000:0000:0000:0005')

        # Test reserved IPv6 short hand notation
        self.assertRaises(exceptions.InvalidOption,
                          validate.ip_not_reserved,
                          '2001:0DB8::5')

    def test_is_flavor_spares_compatible(self):
        not_compat_flavor = {constants.COMPUTE_FLAVOR: 'chocolate'}
        compat_flavor = {constants.LOADBALANCER_TOPOLOGY:
                         constants.TOPOLOGY_SINGLE}

        self.assertTrue(validate.is_flavor_spares_compatible(None))
        self.assertTrue(validate.is_flavor_spares_compatible(compat_flavor))
        self.assertFalse(
            validate.is_flavor_spares_compatible(not_compat_flavor))
