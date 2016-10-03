# Copyright 2015 Rackspace.
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

import os

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture

from octavia.amphorae.backends.agent.api_server import util
from octavia.tests.unit import base


class TestUtils(base.TestCase):
    def setUp(self):
        self.dir = '/etc/network/interfaces.d'
        self.file = '/etc/network/interfaces'

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(group="amphora_agent",
                         agent_server_network_dir=self.dir)

        super(TestUtils, self).setUp()

    def test_get_network_interface_file(self):
        interface = 'eth0'

        self.conf.config(group="amphora_agent",
                         agent_server_network_file=None)
        path = util.get_network_interface_file(interface)
        expected_path = os.path.join(self.dir, interface + '.cfg')
        self.assertEqual(expected_path, path)

        self.conf.config(group="amphora_agent",
                         agent_server_network_file=self.file)
        path = util.get_network_interface_file(interface)
        self.assertEqual(self.file, path)
