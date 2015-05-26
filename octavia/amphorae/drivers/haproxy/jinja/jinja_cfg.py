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

import jinja2
import six

from octavia.common import constants

PROTOCOL_MAP = {
    constants.PROTOCOL_TCP: 'tcp',
    constants.PROTOCOL_HTTP: 'http',
    constants.PROTOCOL_HTTPS: 'tcp',
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
                 'templates/haproxy_listener.template'))

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

        self.base_amp_path = base_amp_path if base_amp_path else BASE_PATH
        self.base_crt_dir = base_crt_dir if base_crt_dir else BASE_CRT_DIR
        self.haproxy_template = (haproxy_template if haproxy_template
                                 else HAPROXY_TEMPLATE)
        self.log_http = log_http
        self.log_server = log_server
        self.timeout_client = timeout_client
        self.timeout_server = timeout_server
        self.timeout_connect = timeout_connect

    def build_config(self, listener, tls_cert,
                     socket_path=None,
                     user_group='nogroup'):
        """Convert a logical configuration to the HAProxy version

        :param listener: The listener configuration
        :param tls_cert: The TLS certificates for the listener
        :param socket_path: The socket path for Haproxy process
        :param user_group: The user group
        :return: Rendered configuration
        """
        return self.render_loadbalancer_obj(listener,
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
                loader=template_loader,
                trim_blocks=True,
                lstrip_blocks=True)
        return JINJA_ENV.get_template(os.path.basename(self.haproxy_template))

    def render_loadbalancer_obj(self, listener,
                                tls_cert=None,
                                user_group='nogroup',
                                socket_path=None):
        """Renders a templated configuration from a load balancer object

        :param listener: The listener configuration
        :param tls_cert: The TLS certificates for the listener
        :param socket_path: The socket path for Haproxy process
        :param user_group: The user group
        :return: Rendered configuration
        """
        loadbalancer = self._transform_loadbalancer(
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

    def _transform_loadbalancer(self, loadbalancer, listener, tls_cert):
        """Transforms a load balanacer into an object that will

           be processed by the templating system
        """
        listener = self._transform_listener(listener, tls_cert)
        return {
            'name': loadbalancer.name,
            'vip_address': loadbalancer.vip.ip_address,
            'listener': listener
        }

    def _transform_listener(self, listener, tls_cert):
        """Transforms a listener into an object that will

            be processed by the templating system
        """
        ret_value = {
            'id': listener.id,
            'protocol_port': listener.protocol_port,
            'protocol_mode': PROTOCOL_MAP[listener.protocol],
            'protocol': listener.protocol
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
            'operating_status': pool.operating_status
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
            'operating_status': member.operating_status
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
