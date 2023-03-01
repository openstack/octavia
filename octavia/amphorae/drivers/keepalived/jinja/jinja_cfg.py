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

import ipaddress
import os

import jinja2
from oslo_config import cfg
from oslo_log import log as logging

from octavia.amphorae.backends.agent.api_server import util
from octavia.common import constants


KEEPALIVED_TEMPLATE = os.path.abspath(
    os.path.join(os.path.dirname(__file__),
                 'templates/keepalived_base.template'))
CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class KeepalivedJinjaTemplater(object):

    def __init__(self, keepalived_template=None):
        """Keepalived configuration generation

        :param keepalived_template: Absolute path to keepalived Jinja template
        """
        super().__init__()
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

    def build_keepalived_config(self, loadbalancer, amphora, amp_net_config):
        """Renders the loadblanacer keepalived configuration for Active/Standby

        :param loadbalancer: A loadbalancer object
        :param amphora: An amphora object
        :param amp_net_config: The amphora network config, a dict
        """
        # Note on keepalived configuration: The current base configuration
        # enforced Master election whenever a high priority VRRP instance
        # start advertising its presence. Accordingly, the fallback behavior
        # - which I described in the blueprint - is the default behavior.
        # Although this is a stable behavior, this can be undesirable for
        # several backend services. To disable the fallback behavior, we need
        #  to add the "nopreempt" flag in the backup instance section.
        peers_ips = []

        # Get the VIP subnet for the amphora
        additional_vip_data = amp_net_config['additional_vip_data']
        vip_subnet = amp_net_config[constants.VIP_SUBNET]

        # Sort VIPs by their IP so we can guarantee interface_index matching
        sorted_add_vips = sorted(additional_vip_data,
                                 key=lambda x: x['ip_address'])

        # The primary VIP is always first in the list
        vip_list = [{
            'ip_address': loadbalancer.vip.ip_address,
            'subnet': vip_subnet
        }] + sorted_add_vips

        # Handle the case of multiple IP family types
        vrrp_addr = ipaddress.ip_address(amphora.vrrp_ip)
        vrrp_ipv6 = vrrp_addr.version == 6

        # Handle all VIPs:
        rendered_vips = []
        for index, add_vip in enumerate(vip_list):
            # Validate the VIP address and see if it is IPv6
            vip = add_vip['ip_address']
            vip_addr = ipaddress.ip_address(vip)
            vip_ipv6 = vip_addr.version == 6
            vip_cidr = add_vip['subnet']['cidr']

            # Normalize and validate the VIP subnet CIDR
            vip_network_cidr = ipaddress.ip_network(
                vip_cidr).with_prefixlen

            host_routes = add_vip['subnet'].get('host_routes', [])

            # Addresses that aren't the same family as the VRRP
            # interface will be in the "excluded" block
            rendered_vips.append({
                'ip_address': vip,
                'network_cidr': vip_network_cidr,
                'ipv6': vip_ipv6,
                'interface_index': index,
                'gateway': add_vip['subnet']['gateway_ip'],
                'excluded': vip_ipv6 != vrrp_ipv6,
                'host_routes': host_routes
            })

        for amp in filter(
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
             'advert_int': loadbalancer.vrrp_group.advert_int,
             'check_script_path': util.keepalived_check_script_path(),
             'vrrp_check_interval':
                 CONF.keepalived_vrrp.vrrp_check_interval,
             'vrrp_fail_count': CONF.keepalived_vrrp.vrrp_fail_count,
             'vrrp_success_count':
                 CONF.keepalived_vrrp.vrrp_success_count,
             'vips': rendered_vips},
            constants=constants)
