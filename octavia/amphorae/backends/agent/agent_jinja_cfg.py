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

import os

import jinja2

from octavia.common.config import cfg
from octavia.common import constants

CONF = cfg.CONF
CONF.import_group('amphora_agent', 'octavia.common.config')
CONF.import_group('haproxy_amphora', 'octavia.common.config')
CONF.import_group('health_manager', 'octavia.common.config')

TEMPLATES_DIR = (os.path.dirname(os.path.realpath(__file__)) +
                 constants.AGENT_API_TEMPLATES + '/')


class AgentJinjaTemplater(object):

    def __init__(self):
        template_loader = jinja2.FileSystemLoader(searchpath=os.path.dirname(
            TEMPLATES_DIR))
        jinja_env = jinja2.Environment(loader=template_loader)
        self.agent_template = jinja_env.get_template(
            constants.AGENT_CONF_TEMPLATE)

    def build_agent_config(self, amphora_id):
        return self.agent_template.render(
            {'agent_server_ca': CONF.amphora_agent.agent_server_ca,
             'agent_server_cert': CONF.amphora_agent.agent_server_cert,
             'agent_server_network_dir':
                 CONF.amphora_agent.agent_server_network_dir,
             'amphora_id': amphora_id,
             'base_cert_dir': CONF.haproxy_amphora.base_cert_dir,
             'base_path': CONF.haproxy_amphora.base_path,
             'bind_host': CONF.haproxy_amphora.bind_host,
             'bind_port': CONF.haproxy_amphora.bind_port,
             'controller_list': CONF.health_manager.controller_ip_port_list,
             'debug': CONF.debug,
             'haproxy_cmd': CONF.haproxy_amphora.haproxy_cmd,
             'heartbeat_interval': CONF.health_manager.heartbeat_interval,
             'heartbeat_key': CONF.health_manager.heartbeat_key,
             'respawn_count': CONF.haproxy_amphora.respawn_count,
             'respawn_interval': CONF.haproxy_amphora.respawn_interval})
