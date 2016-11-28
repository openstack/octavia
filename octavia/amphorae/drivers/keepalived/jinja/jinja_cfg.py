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

import os

import jinja2
from oslo_config import cfg
import six

from octavia.amphorae.backends.agent.api_server import util
from octavia.common import constants


KEEPALIVED_TEMPLATE = os.path.abspath(
    os.path.join(os.path.dirname(__file__),
                 'templates/keepalived_base.template'))
CONF = cfg.CONF


class KeepalivedJinjaTemplater(object):

    def __init__(self, keepalived_template=None):
        """Keepalived configuration generation

        :param keepalived_template: Absolute path to keepalived Jinja template
        """
        super(KeepalivedJinjaTemplater, self).__init__()
        self.keepalived_template = (keepalived_template if
                                    keepalived_template else
                                    KEEPALIVED_TEMPLATE)
        self._jinja_env = None

    def get_template(self, template_file):
        """Returns the specified Jinja configuration template."""
        if not self._jinja_env:
            template_loader = jinja2.FileSystemLoader(
                searchpath=os.path.dirname(template_file))
            self._jinja_env = jinja2.Environment(
                autoescape=True,
                loader=template_loader,
                trim_blocks=True,
                lstrip_blocks=True)
        return self._jinja_env.get_template(os.path.basename(template_file))

    def build_keepalived_config(self, loadbalancer, amphora):
        """Renders the loadblanacer keepalived configuration for Active/Standby

        :param loadbalancer: A lodabalancer object
        :param amp: An amphora object
        """
        # Note on keepalived configuration: The current base configuration
        # enforced Master election whenever a high priority VRRP instance
        # start advertising its presence. Accordingly, the fallback behavior
        # - which I described in the blueprint - is the default behavior.
        # Although this is a stable behavior, this can be undesirable for
        # several backend services. To disable the fallback behavior, we need
        #  to add the "nopreempt" flag in the backup instance section.
        peers_ips = []
        for amp in six.moves.filter(
            lambda amp: amp.status == constants.AMPHORA_ALLOCATED,
                loadbalancer.amphorae):
            if amp.vrrp_ip != amphora.vrrp_ip:
                peers_ips.append(amp.vrrp_ip)
        return self.get_template(self.keepalived_template).render(
            {'vrrp_group_name': loadbalancer.vrrp_group.vrrp_group_name,
             'amp_role': amphora.role,
             'amp_intf': amphora.vrrp_interface,
             'amp_vrrp_id': amphora.vrrp_id,
             'amp_priority': amphora.vrrp_priority,
             'vrrp_garp_refresh':
                 CONF.keepalived_vrrp.vrrp_garp_refresh_interval,
             'vrrp_garp_refresh_repeat':
                 CONF.keepalived_vrrp.vrrp_garp_refresh_count,
             'vrrp_auth_type': loadbalancer.vrrp_group.vrrp_auth_type,
             'vrrp_auth_pass': loadbalancer.vrrp_group.vrrp_auth_pass,
             'amp_vrrp_ip': amphora.vrrp_ip,
             'peers_vrrp_ips': peers_ips,
             'vip_ip_address': loadbalancer.vip.ip_address,
             'advert_int': loadbalancer.vrrp_group.advert_int,
             'check_script_path': util.keepalived_check_script_path(),
             'vrrp_check_interval':
                 CONF.keepalived_vrrp.vrrp_check_interval,
             'vrrp_fail_count': CONF.keepalived_vrrp.vrrp_fail_count,
             'vrrp_success_count':
                 CONF.keepalived_vrrp.vrrp_success_count},
            constants=constants)
