# Copyright 2018 Rackspace, US Inc.
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

import os

import jinja2

from octavia.common.config import cfg
from octavia.common import constants

CONF = cfg.CONF

TEMPLATES_DIR = (os.path.dirname(os.path.realpath(__file__)) +
                 constants.LOGGING_TEMPLATES + '/')


class LoggingJinjaTemplater(object):

    def __init__(self, logging_templates=None):
        self.logging_templates = logging_templates or TEMPLATES_DIR
        template_loader = jinja2.FileSystemLoader(searchpath=os.path.dirname(
            self.logging_templates))
        jinja_env = jinja2.Environment(loader=template_loader, autoescape=True)
        self.logging_template = jinja_env.get_template(
            constants.LOGGING_CONF_TEMPLATE)

    def build_logging_config(self):
        admin_log_hosts = []
        for server in CONF.amphora_agent.admin_log_targets or []:
            (host, port) = server.rsplit(':', 1)
            admin_log_hosts.append({
                'host': host,
                'port': port,
            })
        tenant_log_hosts = []
        for server in CONF.amphora_agent.tenant_log_targets or []:
            (host, port) = server.rsplit(':', 1)
            tenant_log_hosts.append({
                'host': host,
                'port': port,
            })
        return self.logging_template.render(
            {'admin_log_hosts': admin_log_hosts,
             'tenant_log_hosts': tenant_log_hosts,
             'protocol': CONF.amphora_agent.log_protocol,
             'retry_count': CONF.amphora_agent.log_retry_count,
             'retry_interval': CONF.amphora_agent.log_retry_interval,
             'queue_size': CONF.amphora_agent.log_queue_size,
             'forward_all_logs': CONF.amphora_agent.forward_all_logs,
             'disable_local_log_storage':
                 CONF.amphora_agent.disable_local_log_storage,
             'admin_log_facility':
                 CONF.amphora_agent.administrative_log_facility,
             'user_log_facility': CONF.amphora_agent.user_log_facility,
             })
