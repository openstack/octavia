#    Copyright (c) 2015 Rackspace
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
import re

import jinja2
import six

from octavia.common.config import cfg
from octavia.common import constants
from octavia.common import utils as octavia_utils

PROTOCOL_MAP = {
    constants.PROTOCOL_TCP: 'tcp',
    constants.PROTOCOL_HTTP: 'http',
    constants.PROTOCOL_HTTPS: 'tcp',
    constants.PROTOCOL_PROXY: 'proxy',
    constants.PROTOCOL_TERMINATED_HTTPS: 'http'
}

BALANCE_MAP = {
    constants.LB_ALGORITHM_ROUND_ROBIN: 'roundrobin',
    constants.LB_ALGORITHM_LEAST_CONNECTIONS: 'leastconn',
    constants.LB_ALGORITHM_SOURCE_IP: 'source'
}

ACTIVE_PENDING_STATUSES = constants.SUPPORTED_PROVISIONING_STATUSES + (
    constants.DEGRADED,)

BASE_PATH = '/var/lib/octavia'
BASE_CRT_DIR = BASE_PATH + '/certs'

HAPROXY_TEMPLATE = os.path.abspath(
    os.path.join(os.path.dirname(__file__),
                 'templates/haproxy.cfg.j2'))

CONF = cfg.CONF

JINJA_ENV = None


class JinjaTemplater(object):

    def __init__(self,
                 base_amp_path=None,
                 base_crt_dir=None,
                 haproxy_template=None,
                 log_http=None,
                 log_server=None,
                 timeout_client=None,
                 timeout_server=None,
                 timeout_connect=None):
        """HaProxy configuration generation

        :param base_amp_path: Base path for amphora data
        :param base_crt_dir: Base directory for certificate storage
        :param haproxy_template: Absolute path to Jinja template
        :param log_http: Haproxy HTTP logging path
        :param log_server: Haproxy Server logging path
        :param timeout_client: Timeout client
        :param timeout_server: Timeout server
        :param timeout_connect: Timeout connect
        """

        self.base_amp_path = base_amp_path or BASE_PATH
        self.base_crt_dir = base_crt_dir or BASE_CRT_DIR
        self.haproxy_template = haproxy_template or HAPROXY_TEMPLATE
        self.log_http = log_http
        self.log_server = log_server
        self.timeout_client = timeout_client
        self.timeout_server = timeout_server
        self.timeout_connect = timeout_connect

    def build_config(self, host_amphora, listener, tls_cert,
                     socket_path=None,
                     user_group='nogroup'):
        """Convert a logical configuration to the HAProxy version

        :param host_amphora: The Amphora this configuration is hosted on
        :param listener: The listener configuration
        :param tls_cert: The TLS certificates for the listener
        :param socket_path: The socket path for Haproxy process
        :param user_group: The user group
        :return: Rendered configuration
        """
        return self.render_loadbalancer_obj(host_amphora, listener,
                                            tls_cert=tls_cert,
                                            user_group=user_group,
                                            socket_path=socket_path)

    def _get_template(self):
        """Returns the specified Jinja configuration template."""
        global JINJA_ENV
        if not JINJA_ENV:
            template_loader = jinja2.FileSystemLoader(
                searchpath=os.path.dirname(self.haproxy_template))
            JINJA_ENV = jinja2.Environment(
                autoescape=True,
                loader=template_loader,
                trim_blocks=True,
                lstrip_blocks=True)
        JINJA_ENV.filters['hash_amp_id'] = octavia_utils.base64_sha1_string
        return JINJA_ENV.get_template(os.path.basename(self.haproxy_template))

    def render_loadbalancer_obj(self, host_amphora, listener,
                                tls_cert=None,
                                user_group='nogroup',
                                socket_path=None):
        """Renders a templated configuration from a load balancer object

        :param host_amphora: The Amphora this configuration is hosted on
        :param listener: The listener configuration
        :param tls_cert: The TLS certificates for the listener
        :param socket_path: The socket path for Haproxy process
        :param user_group: The user group
        :return: Rendered configuration
        """
        loadbalancer = self._transform_loadbalancer(
            host_amphora,
            listener.load_balancer,
            listener,
            tls_cert)
        if not socket_path:
            socket_path = '%s/%s.sock' % (self.base_amp_path, listener.id)
        return self._get_template().render(
            {'loadbalancer': loadbalancer,
             'user_group': user_group,
             'stats_sock': socket_path,
             'log_http': self.log_http,
             'log_server': self.log_server,
             'timeout_client': self.timeout_client,
             'timeout_server': self.timeout_server,
             'timeout_connect': self.timeout_connect},
            constants=constants)

    def _transform_loadbalancer(self, host_amphora, loadbalancer, listener,
                                tls_cert):
        """Transforms a load balancer into an object that will

           be processed by the templating system
        """
        t_listener = self._transform_listener(listener, tls_cert)
        ret_value = {
            'name': loadbalancer.name,
            'vip_address': loadbalancer.vip.ip_address,
            'listener': t_listener,
            'topology': loadbalancer.topology,
            'enabled': loadbalancer.enabled,
            'host_amphora': self._transform_amphora(host_amphora)
        }
        # NOTE(sbalukoff): Global connection limit should be a sum of all
        # listeners' connection limits. Since Octavia presently supports
        # just one listener per haproxy process, this makes determining
        # the global value trivial.
        if listener.connection_limit and listener.connection_limit > -1:
            ret_value['global_connection_limit'] = listener.connection_limit
        return ret_value

    def _transform_amphora(self, amphora):
        """Transform an amphora into an object that will

           be processed by the templating system.
        """
        return {
            'id': amphora.id,
            'lb_network_ip': amphora.lb_network_ip,
            'vrrp_ip': amphora.vrrp_ip,
            'ha_ip': amphora.ha_ip,
            'vrrp_port_id': amphora.vrrp_port_id,
            'ha_port_id': amphora.ha_port_id,
            'role': amphora.role,
            'status': amphora.status,
            'vrrp_interface': amphora.vrrp_interface,
            'vrrp_priority': amphora.vrrp_priority
        }

    def _transform_listener(self, listener, tls_cert):
        """Transforms a listener into an object that will

            be processed by the templating system
        """
        ret_value = {
            'id': listener.id,
            'protocol_port': listener.protocol_port,
            'protocol_mode': PROTOCOL_MAP[listener.protocol],
            'protocol': listener.protocol,
            'peer_port': listener.peer_port,
            'insert_headers': listener.insert_headers,
            'topology': listener.load_balancer.topology,
            'amphorae': listener.load_balancer.amphorae,
            'enabled': listener.enabled
        }
        if listener.connection_limit and listener.connection_limit > -1:
            ret_value['connection_limit'] = listener.connection_limit
        if listener.tls_certificate_id:
            ret_value['default_tls_path'] = '%s.pem' % (
                os.path.join(self.base_crt_dir,
                             listener.id,
                             tls_cert.primary_cn))
        if listener.sni_containers:
            ret_value['crt_dir'] = os.path.join(self.base_crt_dir, listener.id)
        if listener.default_pool:
            ret_value['default_pool'] = self._transform_pool(
                listener.default_pool)
        pools = [self._transform_pool(x) for x in listener.pools]
        ret_value['pools'] = pools
        l7policies = [self._transform_l7policy(x) for x in listener.l7policies]
        ret_value['l7policies'] = l7policies
        return ret_value

    def _transform_pool(self, pool):
        """Transforms a pool into an object that will

            be processed by the templating system
        """
        ret_value = {
            'id': pool.id,
            'protocol': PROTOCOL_MAP[pool.protocol],
            'lb_algorithm': BALANCE_MAP.get(pool.lb_algorithm, 'roundrobin'),
            'members': [],
            'health_monitor': '',
            'session_persistence': '',
            'enabled': pool.enabled,
            'operating_status': pool.operating_status,
            'stick_size': CONF.haproxy_amphora.haproxy_stick_size
        }
        members = [self._transform_member(x) for x in pool.members]
        ret_value['members'] = members
        if pool.health_monitor:
            ret_value['health_monitor'] = self._transform_health_monitor(
                pool.health_monitor)
        if pool.session_persistence:
            ret_value[
                'session_persistence'] = self._transform_session_persistence(
                pool.session_persistence)
        return ret_value

    @staticmethod
    def _transform_session_persistence(persistence):
        """Transforms session persistence into an object that will

            be processed by the templating system
        """
        return {
            'type': persistence.type,
            'cookie_name': persistence.cookie_name
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
            'enabled': member.enabled,
            'subnet_id': member.subnet_id,
            'operating_status': member.operating_status,
            'monitor_address': member.monitor_address,
            'monitor_port': member.monitor_port
        }

    def _transform_health_monitor(self, monitor):
        """Transforms a health monitor into an object that will

            be processed by the templating system
        """
        codes = None
        if monitor.expected_codes:
            codes = '|'.join(self._expand_expected_codes(
                monitor.expected_codes))
        return {
            'id': monitor.id,
            'type': monitor.type,
            'delay': monitor.delay,
            'timeout': monitor.timeout,
            'fall_threshold': monitor.fall_threshold,
            'rise_threshold': monitor.rise_threshold,
            'http_method': monitor.http_method,
            'url_path': monitor.url_path,
            'expected_codes': codes,
            'enabled': monitor.enabled,
        }

    def _transform_l7policy(self, l7policy):
        """Transforms an L7 policy into an object that will

            be processed by the templating system
        """
        ret_value = {
            'id': l7policy.id,
            'action': l7policy.action,
            'redirect_url': l7policy.redirect_url,
            'enabled': l7policy.enabled
        }
        if l7policy.redirect_pool:
            ret_value['redirect_pool'] = self._transform_pool(
                l7policy.redirect_pool)
        else:
            ret_value['redirect_pool'] = None
        l7rules = [self._transform_l7rule(x) for x in l7policy.l7rules
                   if x.enabled]
        ret_value['l7rules'] = l7rules
        return ret_value

    def _transform_l7rule(self, l7rule):
        """Transforms an L7 rule into an object that will

            be processed by the templating system
        """
        return {
            'id': l7rule.id,
            'type': l7rule.type,
            'compare_type': l7rule.compare_type,
            'key': l7rule.key,
            'value': self._escape_haproxy_config_string(l7rule.value),
            'invert': l7rule.invert,
            'enabled': l7rule.enabled
        }

    @staticmethod
    def _escape_haproxy_config_string(value):
        """Escapes certain characters in a given string such that

            haproxy will parse the string as a single value
        """
        # Escape backslashes first
        value = re.sub(r'\\', r'\\\\', value)
        # Spaces next
        value = re.sub(' ', '\\ ', value)
        return value

    @staticmethod
    def _expand_expected_codes(codes):
        """Expand the expected code string in set of codes.

        200-204 -> 200, 201, 202, 204
        200, 203 -> 200, 203
        """

        retval = set()
        for code in codes.replace(',', ' ').split(' '):
            code = code.strip()

            if not code:
                continue
            elif '-' in code:
                low, hi = code.split('-')[:2]
                retval.update(
                    str(i) for i in six.moves.xrange(int(low), int(hi) + 1))
            else:
                retval.add(code)
        return retval
