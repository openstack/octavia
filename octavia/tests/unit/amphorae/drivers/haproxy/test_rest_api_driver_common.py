# Copyright 2020 Red Hat, Inc. All rights reserved.
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

from octavia.amphorae.drivers.haproxy import exceptions as exc
from octavia.amphorae.drivers.haproxy import rest_api_driver
import octavia.tests.unit.base as base


class TestHAProxyAmphoraDriver(base.TestCase):

    def setUp(self):
        super(TestHAProxyAmphoraDriver, self).setUp()
        self.driver = rest_api_driver.HaproxyAmphoraLoadBalancerDriver()

    @mock.patch('octavia.amphorae.drivers.haproxy.rest_api_driver.'
                'HaproxyAmphoraLoadBalancerDriver.'
                '_populate_amphora_api_version')
    def test_get_interface_from_ip(self, mock_api_version):
        FAKE_INTERFACE = 'fake0'
        IP_ADDRESS = '203.0.113.42'
        TIMEOUT_DICT = {'outa': 'time'}
        amphora_mock = mock.MagicMock()
        amphora_mock.api_version = '0'
        client_mock = mock.MagicMock()
        client_mock.get_interface.side_effect = [
            {'interface': FAKE_INTERFACE}, {'interface': FAKE_INTERFACE},
            {}, exc.NotFound]
        self.driver.clients['0'] = client_mock

        # Test interface found no timeout

        result = self.driver.get_interface_from_ip(amphora_mock, IP_ADDRESS)

        self.assertEqual(FAKE_INTERFACE, result)
        mock_api_version.assert_called_once_with(amphora_mock, None)
        client_mock.get_interface.assert_called_once_with(
            amphora_mock, IP_ADDRESS, None, log_error=False)

        # Test interface found with timeout
        mock_api_version.reset_mock()
        client_mock.reset_mock()

        result = self.driver.get_interface_from_ip(amphora_mock, IP_ADDRESS,
                                                   timeout_dict=TIMEOUT_DICT)

        self.assertEqual(FAKE_INTERFACE, result)
        mock_api_version.assert_called_once_with(amphora_mock, TIMEOUT_DICT)
        client_mock.get_interface.assert_called_once_with(
            amphora_mock, IP_ADDRESS, TIMEOUT_DICT, log_error=False)

        # Test no interface data
        mock_api_version.reset_mock()
        client_mock.reset_mock()

        result = self.driver.get_interface_from_ip(amphora_mock, IP_ADDRESS)

        self.assertIsNone(result)
        mock_api_version.assert_called_once_with(amphora_mock, None)
        client_mock.get_interface.assert_called_once_with(
            amphora_mock, IP_ADDRESS, None, log_error=False)

        # Test NotFound
        mock_api_version.reset_mock()
        client_mock.reset_mock()

        result = self.driver.get_interface_from_ip(amphora_mock, IP_ADDRESS)

        self.assertIsNone(result)
        mock_api_version.assert_called_once_with(amphora_mock, None)
        client_mock.get_interface.assert_called_once_with(
            amphora_mock, IP_ADDRESS, None, log_error=False)
