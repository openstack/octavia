# Copyright 2015 Hewlett Packard Enterprise Development Company LP
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

from oslo_utils import uuidutils

from octavia.amphorae.drivers.keepalived import vrrp_rest_driver
from octavia.common import constants
from octavia.network import data_models as n_data_models
import octavia.tests.unit.base as base

# Version 1.0 is functionally identical to all versions before it
API_VERSION = '1.0'


class TestVRRPRestDriver(base.TestCase):

    def setUp(self):
        self.keepalived_mixin = vrrp_rest_driver.KeepalivedAmphoraDriverMixin()
        self.keepalived_mixin.clients = {
            'base': mock.MagicMock(),
            API_VERSION: mock.MagicMock()}
        self.keepalived_mixin._populate_amphora_api_version = mock.MagicMock()
        self.clients = self.keepalived_mixin.clients
        self.FAKE_CONFIG = 'FAKE CONFIG'
        self.lb_mock = mock.MagicMock()
        self.amphora_mock = mock.MagicMock()
        self.amphora_mock.id = uuidutils.generate_uuid()
        self.amphora_mock.status = constants.AMPHORA_ALLOCATED
        self.amphora_mock.api_version = API_VERSION
        self.lb_mock.amphorae = [self.amphora_mock]
        self.amphorae_network_config = {}
        vip_subnet = mock.MagicMock()
        self.vip_cidr = vip_subnet.cidr = '192.0.2.0/24'
        one_amp_net_config = n_data_models.AmphoraNetworkConfig(
            vip_subnet=vip_subnet
        )
        self.amphorae_network_config[self.amphora_mock.id] = one_amp_net_config

        super().setUp()

    @mock.patch('octavia.amphorae.drivers.keepalived.jinja.'
                'jinja_cfg.KeepalivedJinjaTemplater.build_keepalived_config')
    def test_update_vrrp_conf(self, mock_templater):

        mock_templater.return_value = self.FAKE_CONFIG

        self.keepalived_mixin.update_vrrp_conf(
            self.lb_mock, self.amphorae_network_config, self.amphora_mock)

        mock_templater.assert_called_with(
            self.lb_mock, self.amphora_mock,
            self.amphorae_network_config[self.amphora_mock.id])
        self.clients[API_VERSION].upload_vrrp_config.assert_called_once_with(
            self.amphora_mock,
            self.FAKE_CONFIG)

        # Test with amphorav2 amphorae_network_config list of dicts
        mock_templater.reset_mock()
        self.clients[API_VERSION].upload_vrrp_config.reset_mock()
        v2_amphorae_network_config = {}
        vip_subnet_dict = {
            constants.VIP_SUBNET: {constants.CIDR: '192.0.2.0/24'}}
        v2_amphorae_network_config[self.amphora_mock.id] = vip_subnet_dict

        self.keepalived_mixin.update_vrrp_conf(
            self.lb_mock, v2_amphorae_network_config, self.amphora_mock)

        self.clients[API_VERSION].upload_vrrp_config.assert_called_once_with(
            self.amphora_mock,
            self.FAKE_CONFIG)

        # Test amphora not in AMPHORA_ALLOCATED state
        mock_templater.reset_mock()
        self.clients[API_VERSION].upload_vrrp_config.reset_mock()
        ready_amphora_mock = mock.MagicMock()
        ready_amphora_mock.id = uuidutils.generate_uuid()
        ready_amphora_mock.status = constants.ERROR
        ready_amphora_mock.api_version = API_VERSION

        self.keepalived_mixin.update_vrrp_conf(
            self.lb_mock, self.amphorae_network_config, ready_amphora_mock)

        mock_templater.assert_not_called()
        self.clients[API_VERSION].upload_vrrp_config.assert_not_called()

    def test_stop_vrrp_service(self):

        self.keepalived_mixin.stop_vrrp_service(self.lb_mock)

        self.clients[API_VERSION].stop_vrrp.assert_called_once_with(
            self.amphora_mock)

    def test_start_vrrp_service(self):

        self.keepalived_mixin.start_vrrp_service(self.amphora_mock)

        populate_mock = self.keepalived_mixin._populate_amphora_api_version
        populate_mock.assert_called_once_with(self.amphora_mock,
                                              timeout_dict=None)
        self.clients[API_VERSION].start_vrrp.assert_called_once_with(
            self.amphora_mock, timeout_dict=None)

        # Test amphora not in AMPHORA_ALLOCATED state
        self.clients[API_VERSION].start_vrrp.reset_mock()
        ready_amphora_mock = mock.MagicMock()
        ready_amphora_mock.id = uuidutils.generate_uuid()
        ready_amphora_mock.status = constants.ERROR
        ready_amphora_mock.api_version = API_VERSION

        self.keepalived_mixin.start_vrrp_service(ready_amphora_mock)

        self.clients[API_VERSION].start_vrrp.assert_not_called()

        # With timeout_dict
        self.clients[API_VERSION].start_vrrp.reset_mock()
        populate_mock.reset_mock()

        timeout_dict = mock.Mock()
        self.keepalived_mixin.start_vrrp_service(self.amphora_mock,
                                                 timeout_dict=timeout_dict)

        populate_mock = self.keepalived_mixin._populate_amphora_api_version
        populate_mock.assert_called_once_with(self.amphora_mock,
                                              timeout_dict=timeout_dict)
        self.clients[API_VERSION].start_vrrp.assert_called_once_with(
            self.amphora_mock, timeout_dict=timeout_dict)

    def test_reload_vrrp_service(self):

        self.keepalived_mixin.reload_vrrp_service(self.lb_mock)

        self.clients[API_VERSION].reload_vrrp.assert_called_once_with(
            self.amphora_mock)
