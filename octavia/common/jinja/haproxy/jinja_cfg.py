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

CLIENT_AUTH_MAP = {constants.CLIENT_AUTH_NONE: 'none',
                   constants.CLIENT_AUTH_OPTIONAL: 'optional',
                   constants.CLIENT_AUTH_MANDATORY: 'required'}

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
                 connection_logging=True):
        """HaProxy configuration generation

        :param base_amp_path: Base path for amphora data
        :param base_crt_dir: Base directory for certificate storage
        :param haproxy_template: Absolute path to Jinja template
        :param log_http: Haproxy HTTP logging path
        :param log_server: Haproxy Server logging path
        :param connection_logging: enable logging connections in haproxy
        """

        self.base_amp_path = base_amp_path or BASE_PATH
        self.base_crt_dir = base_crt_dir or BASE_CRT_DIR
        self.haproxy_template = haproxy_template or HAPROXY_TEMPLATE
        self.log_http = log_http
        self.log_server = log_server
        self.connection_logging = connection_logging

    def build_config(self, host_amphora, listener, tls_cert,
                     haproxy_versions, socket_path=None,
                     client_ca_filename=None, client_crl=None,
                     pool_tls_certs=None):
        """Convert a logical configuration to the HAProxy version

        :param host_amphora: The Amphora this configuration is hosted on
        :param listener: The listener configuration
        :param tls_cert: The TLS certificates for the listener
        :param socket_path: The socket path for Haproxy process
        :return: Rendered configuration
        """

        # Check for any backward compatibility items we need to check
        # This is done here for upgrade scenarios where one amp in a
        # pair might be running an older amphora version.

        feature_compatibility = {}
        # Is it newer than haproxy 1.5?
        if not (int(haproxy_versions[0]) < 2 and int(haproxy_versions[1]) < 6):
            feature_compatibility[constants.HTTP_REUSE] = True

        return self.render_loadbalancer_obj(
            host_amphora, listener, tls_cert=tls_cert, socket_path=socket_path,
            feature_compatibility=feature_compatibility,
            client_ca_filename=client_ca_filename, client_crl=client_crl,
            pool_tls_certs=pool_tls_certs)

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
                                tls_cert=None, socket_path=None,
                                feature_compatibility=None,
                                client_ca_filename=None, client_crl=None,
                                pool_tls_certs=None):
        """Renders a templated configuration from a load balancer object

        :param host_amphora: The Amphora this configuration is hosted on
        :param listener: The listener configuration
        :param tls_cert: The TLS certificates for the listener
        :param client_ca_filename: The CA certificate for client authorization
        :param socket_path: The socket path for Haproxy process
        :return: Rendered configuration
        """
        feature_compatibility = feature_compatibility or {}
        loadbalancer = self._transform_loadbalancer(
            host_amphora,
            listener.load_balancer,
            listener,
            tls_cert,
            feature_compatibility,
            client_ca_filename=client_ca_filename,
            client_crl=client_crl,
            pool_tls_certs=pool_tls_certs)
        if not socket_path:
            socket_path = '%s/%s.sock' % (self.base_amp_path, listener.id)
        return self._get_template().render(
            {'loadbalancer': loadbalancer,
             'stats_sock': socket_path,
             'log_http': self.log_http,
             'log_server': self.log_server,
             'connection_logging': self.connection_logging},
            constants=constants)

    def _transform_loadbalancer(self, host_amphora, loadbalancer, listener,
                                tls_cert, feature_compatibility,
                                client_ca_filename=None, client_crl=None,
                                pool_tls_certs=None):
        """Transforms a load balancer into an object that will

           be processed by the templating system
        """
        t_listener = self._transform_listener(
            listener, tls_cert, feature_compatibility,
            client_ca_filename=client_ca_filename, client_crl=client_crl,
            pool_tls_certs=pool_tls_certs)
        ret_value = {
            'id': loadbalancer.id,
            'vip_address': loadbalancer.vip.ip_address,
            'listener': t_listener,
            'topology': loadbalancer.topology,
            'enabled': loadbalancer.enabled,
            'host_amphora': self._transform_amphora(
                host_amphora, feature_compatibility)
        }
        # NOTE(sbalukoff): Global connection limit should be a sum of all
        # listeners' connection limits. Since Octavia presently supports
        # just one listener per haproxy process, this makes determining
        # the global value trivial.
        if listener.connection_limit and listener.connection_limit > -1:
            ret_value['global_connection_limit'] = listener.connection_limit
        else:
            ret_value['global_connection_limit'] = (
                constants.HAPROXY_MAX_MAXCONN)
        return ret_value

    def _transform_amphora(self, amphora, feature_compatibility):
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

    def _transform_listener(self, listener, tls_cert, feature_compatibility,
                            client_ca_filename=None, client_crl=None,
                            pool_tls_certs=None):
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
            'enabled': listener.enabled,
            'timeout_client_data': (
                listener.timeout_client_data or
                CONF.haproxy_amphora.timeout_client_data),
            'timeout_member_connect': (
                listener.timeout_member_connect or
                CONF.haproxy_amphora.timeout_member_connect),
            'timeout_member_data': (
                listener.timeout_member_data or
                CONF.haproxy_amphora.timeout_member_data),
            'timeout_tcp_inspect': (listener.timeout_tcp_inspect or
                                    CONF.haproxy_amphora.timeout_tcp_inspect),
        }
        if listener.connection_limit and listener.connection_limit > -1:
            ret_value['connection_limit'] = listener.connection_limit
        else:
            ret_value['connection_limit'] = constants.HAPROXY_MAX_MAXCONN
        if listener.tls_certificate_id:
            ret_value['default_tls_path'] = '%s.pem' % (
                os.path.join(self.base_crt_dir,
                             listener.id,
                             tls_cert.id))
        if listener.sni_containers:
            ret_value['crt_dir'] = os.path.join(self.base_crt_dir, listener.id)
        if listener.client_ca_tls_certificate_id:
            ret_value['client_ca_tls_path'] = '%s' % (
                os.path.join(self.base_crt_dir, listener.id,
                             client_ca_filename))
            ret_value['client_auth'] = CLIENT_AUTH_MAP.get(
                listener.client_authentication)
        if listener.client_crl_container_id:
            ret_value['client_crl_path'] = '%s' % (
                os.path.join(self.base_crt_dir, listener.id, client_crl))

        if listener.default_pool:
            kwargs = {}
            if pool_tls_certs and pool_tls_certs.get(listener.default_pool.id):
                kwargs = {'pool_tls_certs': pool_tls_certs.get(
                    listener.default_pool.id)}
            ret_value['default_pool'] = self._transform_pool(
                listener.default_pool, feature_compatibility, **kwargs)
        pools = []
        for x in listener.pools:
            kwargs = {}
            if pool_tls_certs and pool_tls_certs.get(x.id):
                kwargs = {'pool_tls_certs': pool_tls_certs.get(x.id)}
            pools.append(self._transform_pool(
                x, feature_compatibility, **kwargs))
        ret_value['pools'] = pools
        l7policies = [self._transform_l7policy(
                      x, feature_compatibility, pool_tls_certs)
                      for x in listener.l7policies]
        ret_value['l7policies'] = l7policies
        return ret_value

    def _transform_pool(self, pool, feature_compatibility,
                        pool_tls_certs=None):
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
            'stick_size': CONF.haproxy_amphora.haproxy_stick_size,
            constants.HTTP_REUSE: feature_compatibility.get(
                constants.HTTP_REUSE, False),
            'ca_tls_path': '',
            'crl_path': '',
            'tls_enabled': pool.tls_enabled
        }
        members = [self._transform_member(x, feature_compatibility)
                   for x in pool.members]
        ret_value['members'] = members
        if pool.health_monitor:
            ret_value['health_monitor'] = self._transform_health_monitor(
                pool.health_monitor, feature_compatibility)
        if pool.session_persistence:
            ret_value[
                'session_persistence'] = self._transform_session_persistence(
                pool.session_persistence, feature_compatibility)
        if (pool.tls_certificate_id and pool_tls_certs and
                pool_tls_certs.get('client_cert')):
            ret_value['client_cert'] = pool_tls_certs.get('client_cert')
        if (pool.ca_tls_certificate_id and pool_tls_certs and
                pool_tls_certs.get('ca_cert')):
            ret_value['ca_cert'] = pool_tls_certs.get('ca_cert')
        if (pool.crl_container_id and pool_tls_certs and
                pool_tls_certs.get('crl')):
            ret_value['crl'] = pool_tls_certs.get('crl')

        return ret_value

    @staticmethod
    def _transform_session_persistence(persistence, feature_compatibility):
        """Transforms session persistence into an object that will

            be processed by the templating system
        """
        return {
            'type': persistence.type,
            'cookie_name': persistence.cookie_name
        }

    @staticmethod
    def _transform_member(member, feature_compatibility):
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
            'monitor_port': member.monitor_port,
            'backup': member.backup
        }

    def _transform_health_monitor(self, monitor, feature_compatibility):
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
            'http_version': monitor.http_version,
            'domain_name': monitor.domain_name,
        }

    def _transform_l7policy(self, l7policy, feature_compatibility,
                            pool_tls_certs=None):
        """Transforms an L7 policy into an object that will

            be processed by the templating system
        """
        ret_value = {
            'id': l7policy.id,
            'action': l7policy.action,
            'redirect_url': l7policy.redirect_url,
            'redirect_prefix': l7policy.redirect_prefix,
            'enabled': l7policy.enabled
        }
        if l7policy.redirect_pool:
            kwargs = {}
            if pool_tls_certs and pool_tls_certs.get(
                    l7policy.redirect_pool.id):
                kwargs = {'pool_tls_certs':
                          pool_tls_certs.get(l7policy.redirect_pool.id)}
            ret_value['redirect_pool'] = self._transform_pool(
                l7policy.redirect_pool, feature_compatibility, **kwargs)
        else:
            ret_value['redirect_pool'] = None
        if (l7policy.action in [constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                                constants.L7POLICY_ACTION_REDIRECT_PREFIX] and
                l7policy.redirect_http_code):
            ret_value['redirect_http_code'] = l7policy.redirect_http_code
        else:
            ret_value['redirect_http_code'] = None
        l7rules = [self._transform_l7rule(x, feature_compatibility)
                   for x in l7policy.l7rules if x.enabled]
        ret_value['l7rules'] = l7rules
        return ret_value

    def _transform_l7rule(self, l7rule, feature_compatibility):
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
