#    Copyright (c) 2018 OpenStack Foundation
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

PROTOCOL_MAP = {
    constants.PROTOCOL_UDP: 'udp'
}

BALANCE_MAP = {
    constants.LB_ALGORITHM_ROUND_ROBIN: 'rr',
    constants.LB_ALGORITHM_LEAST_CONNECTIONS: 'lc',
    constants.LB_ALGORITHM_SOURCE_IP: 'sh'
}

BASE_PATH = CONF.haproxy_amphora.base_path

CHECK_SCRIPT_NAME = 'udp_check.sh'

KEEPALIVED_LVS_TEMPLATE = os.path.abspath(
    os.path.join(os.path.dirname(__file__),
                 'templates/keepalivedlvs.cfg.j2'))

JINJA_ENV = None


class LvsJinjaTemplater(object):

    def __init__(self, base_amp_path=None, keepalivedlvs_template=None):
        """Keepalived LVS configuration generation

        :param base_amp_path: Base path for amphora data
        :param keepalivedlvs_template: Absolute path to Jinja template
        """

        self.base_amp_path = base_amp_path or BASE_PATH
        self.keepalivedlvs_template = (keepalivedlvs_template or
                                       KEEPALIVED_LVS_TEMPLATE)

    def build_config(self, listener, **kwargs):
        """Convert a logical configuration to the Keepalived LVS version

        :param listener: The listener configuration
        :return: Rendered configuration
        """
        return self.render_loadbalancer_obj(listener)

    def _get_template(self):
        """Returns the specified Jinja configuration template."""
        global JINJA_ENV
        if not JINJA_ENV:
            template_loader = jinja2.FileSystemLoader(
                searchpath=os.path.dirname(self.keepalivedlvs_template))
            JINJA_ENV = jinja2.Environment(
                autoescape=True,
                loader=template_loader,
                trim_blocks=True,
                lstrip_blocks=True,
                extensions=['jinja2.ext.do'])
        return JINJA_ENV.get_template(os.path.basename(
            self.keepalivedlvs_template))

    def render_loadbalancer_obj(self, listener, **kwargs):
        """Renders a templated configuration from a load balancer object

        :param host_amphora: The Amphora this configuration is hosted on
        :param listener: The listener configuration
        :return: Rendered configuration
        """
        loadbalancer = self._transform_loadbalancer(
            listener.load_balancer,
            listener)
        return self._get_template().render(
            {'loadbalancer': loadbalancer},
            constants=constants)

    def _transform_loadbalancer(self, loadbalancer, listener):
        """Transforms a load balancer into an object that will

           be processed by the templating system
        """
        t_listener = self._transform_listener(listener)
        ret_value = {
            'id': loadbalancer.id,
            'vip_address': loadbalancer.vip.ip_address,
            'listener': t_listener,
            'enabled': loadbalancer.enabled
        }
        return ret_value

    def _transform_listener(self, listener):
        """Transforms a listener into an object that will

            be processed by the templating system
        """
        ret_value = {
            'id': listener.id,
            'protocol_port': listener.protocol_port,
            'protocol_mode': PROTOCOL_MAP[listener.protocol],
            'enabled': listener.enabled
        }
        if listener.connection_limit and listener.connection_limit > -1:
            ret_value['connection_limit'] = listener.connection_limit
        if listener.default_pool:
            ret_value['default_pool'] = self._transform_pool(
                listener.default_pool)
        return ret_value

    def _transform_pool(self, pool):
        """Transforms a pool into an object that will

            be processed by the templating system
        """
        ret_value = {
            'id': pool.id,
            'protocol': PROTOCOL_MAP[pool.protocol],
            'lb_algorithm': BALANCE_MAP.get(pool.lb_algorithm,
                                            'roundrobin'),
            'members': [],
            'health_monitor': '',
            'session_persistence': '',
            'enabled': pool.enabled
        }
        members = [self._transform_member(x) for x in pool.members]
        ret_value['members'] = members
        if pool.health_monitor:
            ret_value['health_monitor'] = self._transform_health_monitor(
                pool.health_monitor)
        if pool.session_persistence:
            func = self._transform_session_persistence
            ret_value['session_persistence'] = func(
                pool.session_persistence)
        return ret_value

    @staticmethod
    def _transform_session_persistence(persistence):
        """Transforms session persistence into an object that will

            be processed by the templating system
        """
        return {
            'type': persistence.type,
            'persistence_timeout': persistence.persistence_timeout,
            'persistence_granularity': persistence.persistence_granularity
        }

    @staticmethod
    def _transform_member(member):
        """Transforms a member into an object that will

            be processed by the templating system
        """
        return {
            'id': member.id,
            'address': member.ip_address,
            'protocol_port': member.protocol_port,
            'weight': member.weight,
            'enabled': member.enabled
        }

    def _get_default_lvs_check_script_path(self):
        return (CONF.haproxy_amphora.base_path +
                '/lvs/check/' + CHECK_SCRIPT_NAME)

    def _transform_health_monitor(self, monitor):
        """Transforms a health monitor into an object that will

            be processed by the templating system
        """
        return {
            'id': monitor.id,
            'type': monitor.type,
            'delay': monitor.delay,
            'timeout': monitor.timeout,
            'enabled': monitor.enabled,
            'fall_threshold': monitor.fall_threshold,
            'check_script_path': (self._get_default_lvs_check_script_path()
                                  if monitor.type ==
                                  constants.HEALTH_MONITOR_UDP_CONNECT else
                                  None)
        }
