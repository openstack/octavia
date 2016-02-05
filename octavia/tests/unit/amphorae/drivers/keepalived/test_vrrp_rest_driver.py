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

import mock

from octavia.amphorae.drivers.keepalived import vrrp_rest_driver
from octavia.common import constants
import octavia.tests.unit.base as base


class TestVRRPRestDriver(base.TestCase):

    def setUp(self):
        self.keepalived_mixin = vrrp_rest_driver.KeepalivedAmphoraDriverMixin()
        self.keepalived_mixin.client = mock.MagicMock()
        self.client = self.keepalived_mixin.client
        self.FAKE_CONFIG = 'FAKE CONFIG'
        self.lb_mock = mock.MagicMock()
        self.amphora_mock = mock.MagicMock()
        self.amphora_mock.status = constants.AMPHORA_ALLOCATED
        self.lb_mock.amphorae = [self.amphora_mock]
        super(TestVRRPRestDriver, self).setUp()

    @mock.patch('octavia.amphorae.drivers.keepalived.jinja.'
                'jinja_cfg.KeepalivedJinjaTemplater.build_keepalived_config')
    def test_update_vrrp_conf(self, mock_templater):

        mock_templater.return_value = self.FAKE_CONFIG

        self.keepalived_mixin.update_vrrp_conf(self.lb_mock)

        self.client.upload_vrrp_config.assert_called_once_with(
            self.amphora_mock,
            self.FAKE_CONFIG)

    def test_stop_vrrp_service(self):

        self.keepalived_mixin.stop_vrrp_service(self.lb_mock)

        self.client.stop_vrrp.assert_called_once_with(self.amphora_mock)

    def test_start_vrrp_service(self):

        self.keepalived_mixin.start_vrrp_service(self.lb_mock)

        self.client.start_vrrp.assert_called_once_with(self.amphora_mock)

    def test_reload_vrrp_service(self):

        self.keepalived_mixin.reload_vrrp_service(self.lb_mock)

        self.client.reload_vrrp.assert_called_once_with(self.amphora_mock)
