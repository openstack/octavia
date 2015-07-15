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
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.amphorae.backends.agent import agent_jinja_cfg
import octavia.tests.unit.base as base

AMP_ID = uuidutils.generate_uuid()


class AgentJinjaTestCase(base.TestCase):
    def setUp(self):
        super(AgentJinjaTestCase, self).setUp()

        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(debug=False)
        conf.config(group="amphora_agent",
                    agent_server_ca='/etc/octavia/certs/client_ca.pem')
        conf.config(group="amphora_agent",
                    agent_server_cert='/etc/octavia/certs/server.pem')
        conf.config(group="amphora_agent",
                    agent_server_network_dir='/etc/network/interfaces.d/')
        conf.config(group="haproxy_amphora",
                    base_cert_dir='/var/lib/octavia/certs')
        conf.config(group="haproxy_amphora", base_path='/var/lib/octavia')
        conf.config(group="haproxy_amphora", bind_host='0.0.0.0')
        conf.config(group="haproxy_amphora", bind_port=9443)
        conf.config(group="haproxy_amphora", haproxy_cmd='/usr/sbin/haproxy')
        conf.config(group="haproxy_amphora", respawn_count=2)
        conf.config(group="haproxy_amphora", respawn_interval=2)
        conf.config(group="health_manager",
                    controller_ip_port_list=['192.0.2.10:5555'])
        conf.config(group="health_manager", heartbeat_interval=10)
        conf.config(group="health_manager", heartbeat_key='TEST')

        self.expected_config = ('\n[DEFAULT]\n'
                                'debug = False\n\n'
                                '[haproxy_amphora]\n'
                                'base_cert_dir = /var/lib/octavia/certs\n'
                                'base_path = /var/lib/octavia\n'
                                'bind_host = 0.0.0.0\n'
                                'bind_port = 9443\n'
                                'haproxy_cmd = /usr/sbin/haproxy\n'
                                'respawn_count = 2\n'
                                'respawn_interval = 2\n\n'
                                '[health_manager]\n'
                                'controller_ip_port_list = 192.0.2.10:5555\n'
                                'heartbeat_interval = 10\n'
                                'heartbeat_key = TEST\n\n'
                                '[amphora_agent]\n'
                                'agent_server_ca = '
                                '/etc/octavia/certs/client_ca.pem\n'
                                'agent_server_cert = '
                                '/etc/octavia/certs/server.pem\n'
                                'agent_server_network_dir = '
                                '/etc/network/interfaces.d/\n'
                                'amphora_id = ' + AMP_ID)

    def test_build_agent_config(self):
        ajc = agent_jinja_cfg.AgentJinjaTemplater()
        agent_cfg = ajc.build_agent_config(AMP_ID)
        self.assertEqual(self.expected_config, agent_cfg)
