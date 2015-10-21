# Copyright 2015 Rackspace
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock
import netifaces

from octavia.amphorae.backends.agent.api_server import plug
import octavia.tests.unit.base as base


@mock.patch.object(plug, "netifaces")
class TestPlug(base.TestCase):

    def test__interface_by_mac_case_insensitive(self, mock_netifaces):
        mock_netifaces.AF_LINK = netifaces.AF_LINK
        mock_interface = 'eth0'
        mock_netifaces.interfaces.return_value = [mock_interface]
        mock_netifaces.ifaddresses.return_value = {
            netifaces.AF_LINK: [
                {'addr': 'ab:cd:ef:00:ff:22'}
            ]
        }
        interface = plug._interface_by_mac('AB:CD:EF:00:FF:22')
        self.assertEqual('eth0', interface)
