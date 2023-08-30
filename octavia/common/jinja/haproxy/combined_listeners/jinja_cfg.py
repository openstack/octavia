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
from typing import Optional

import jinja2
from octavia_lib.common import constants as lib_consts
from oslo_utils import versionutils

from octavia.common.config import cfg
from octavia.common import constants
from octavia.common import utils as octavia_utils
from octavia.db import models

PROTOCOL_MAP = {
    constants.PROTOCOL_TCP: 'tcp',
    constants.PROTOCOL_HTTP: 'http',
    constants.PROTOCOL_HTTPS: 'tcp',
    constants.PROTOCOL_PROXY: 'proxy',
    lib_consts.PROTOCOL_PROXYV2: 'proxy',
    constants.PROTOCOL_TERMINATED_HTTPS: 'http',
    lib_consts.PROTOCOL_PROMETHEUS: 'http'
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

    def build_config(self, host_amphora, listeners, tls_certs,
                     haproxy_versions, amp_details, socket_path=None):
        """Convert a logical configuration to the HAProxy version

        :param host_amphora: The Amphora this configuration is hosted on
        :param listener: The listener configuration
        :param amp_details: Detail information from the amphora
        :param socket_path: The socket path for Haproxy process
        :return: Rendered configuration
        """

        # Check for any backward compatibility items we need to check
        # This is done here for upgrade scenarios where one amp in a
        # pair might be running an older amphora version.

        feature_compatibility = {}
        version = ".".join(haproxy_versions)
        # Is it newer than haproxy 1.5?
        if versionutils.is_compatible("1.6.0", version, same_major=False):
            feature_compatibility[constants.HTTP_REUSE] = True
            feature_compatibility[constants.SERVER_STATE_FILE] = True
        if versionutils.is_compatible("1.9.0", version, same_major=False):
            feature_compatibility[constants.POOL_ALPN] = True
        if int(haproxy_versions[0]) >= 2:
            feature_compatibility[lib_consts.PROTOCOL_PROMETHEUS] = True
        # haproxy 2.2 requires insecure-fork-wanted for PING healthchecks
        if versionutils.is_compatible("2.2.0", version, same_major=False):
            feature_compatibility[constants.INSECURE_FORK] = True

        return self.render_loadbalancer_obj(
            host_amphora, listeners, tls_certs=tls_certs,
            socket_path=socket_path,
            feature_compatibility=feature_compatibility,
            amp_details=amp_details)

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

    def _format_log_string(self, load_balancer, protocol):
        log_format = CONF.haproxy_amphora.user_log_format.replace(
            '{{ project_id }}', load_balancer.project_id)
        log_format = log_format.replace('{{ lb_id }}', load_balancer.id)

        # Order of these filters matter.
        # TODO(johnsom) Remove when HAProxy handles the format string
        #               with HTTP variables in TCP listeners.
        #               Currently it either throws an error or just fails
        #               to log the message.
        if protocol not in constants.HAPROXY_HTTP_PROTOCOLS:
            log_format = log_format.replace('%{+Q}r', '-')
            log_format = log_format.replace('%r', '-')
            log_format = log_format.replace('%{+Q}ST', '-')
            log_format = log_format.replace('%ST', '-')

        log_format = log_format.replace(' ', '\\ ')
        return log_format

    def render_loadbalancer_obj(self, host_amphora, listeners,
                                tls_certs=None, socket_path=None,
                                feature_compatibility=None,
                                amp_details: Optional[dict] = None):
        """Renders a templated configuration from a load balancer object

        :param host_amphora: The Amphora this configuration is hosted on
        :param listener: The listener configuration
        :param tls_certs: Dict of the TLS certificates for the listener
        :param socket_path: The socket path for Haproxy process
        :param amp_details: Detail information from the amphora
        :return: Rendered configuration
        """
        feature_compatibility = feature_compatibility or {}
        loadbalancer = self._transform_loadbalancer(
            host_amphora,
            listeners[0].load_balancer,
            listeners,
            tls_certs,
            feature_compatibility)
        if not socket_path:
            socket_path = '%s/%s.sock' % (self.base_amp_path,
                                          listeners[0].load_balancer.id)
        state_file_path = '%s/%s/servers-state' % (
            self.base_amp_path,
            listeners[0].load_balancer.id) if feature_compatibility.get(
            constants.SERVER_STATE_FILE) else ''
        prometheus_listener = any(
            lsnr.protocol == lib_consts.PROTOCOL_PROMETHEUS for lsnr in
            listeners)
        require_insecure_fork = feature_compatibility.get(
            constants.INSECURE_FORK)
        enable_prometheus = prometheus_listener and feature_compatibility.get(
            lib_consts.PROTOCOL_PROMETHEUS, False)
        term_https_listener = any(
            lsnr.protocol == lib_consts.PROTOCOL_TERMINATED_HTTPS for lsnr in
            listeners)

        jinja_dict = {
            'loadbalancer': loadbalancer,
            'stats_sock': socket_path,
            'log_http': self.log_http,
            'log_server': self.log_server,
            'state_file': state_file_path,
            'administrative_log_facility':
                CONF.amphora_agent.administrative_log_facility,
            'user_log_facility':
                CONF.amphora_agent.user_log_facility,
            'connection_logging': self.connection_logging,
            'enable_prometheus': enable_prometheus,
            'require_insecure_fork': require_insecure_fork,
        }
        try:
            # Enable cpu-pinning only if the amphora TuneD profile is active
            if "amphora" in amp_details["active_tuned_profiles"].split():
                jinja_dict["cpu_count"] = int(amp_details["cpu_count"])
        except (KeyError, TypeError):
            pass

        if term_https_listener:
            try:
                mem = amp_details["memory"]
                # Account for 32 KB per established connection for each
                # pair of HAProxy network sockets. Use 1024 as fallback
                # because that is what ulimit -n typically returns.
                max_conn_mem_kb = 32 * loadbalancer.get(
                    "global_connection_limit", 1024)
                # Use half of the remaining memory for SSL caches
                ssl_cache_mem_kb = (mem["free"] + mem["buffers"] +
                                    mem["cached"] - max_conn_mem_kb) // 2
                # A cache block uses about 200 bytes of data.
                # The HAProxy default of ssl_cache (20000) would take up
                # 4000 KB. We don't want to go below that.
                if ssl_cache_mem_kb > 4000:
                    jinja_dict["ssl_cache"] = ssl_cache_mem_kb * 5
            except (KeyError, TypeError):
                pass

        return self._get_template().render(
            jinja_dict, constants=constants, lib_consts=lib_consts)

    def _transform_loadbalancer(self, host_amphora, loadbalancer, listeners,
                                tls_certs, feature_compatibility):
        """Transforms a load balancer into an object that will

           be processed by the templating system
        """
        listener_transforms = []
        for listener in listeners:
            if listener.protocol in constants.LVS_PROTOCOLS:
                continue
            listener_transforms.append(self._transform_listener(
                listener, tls_certs, feature_compatibility, loadbalancer))
        additional_vips = [
            vip.ip_address for vip in loadbalancer.additional_vips]

        ret_value = {
            'id': loadbalancer.id,
            'vip_address': loadbalancer.vip.ip_address,
            'additional_vips': additional_vips,
            'listeners': listener_transforms,
            'topology': loadbalancer.topology,
            'enabled': loadbalancer.enabled,
            'peer_port': listeners[0].peer_port,
            'host_amphora': self._transform_amphora(
                host_amphora, feature_compatibility),
            'amphorae': loadbalancer.amphorae
        }
        # NOTE(sbalukoff): Global connection limit should be a sum of all
        # listeners' connection limits.
        connection_limit_sum = 0
        for listener in listeners:
            if not listener.enabled:
                continue
            if listener.protocol in constants.LVS_PROTOCOLS:
                continue
            if listener.connection_limit and listener.connection_limit > -1:
                connection_limit_sum += listener.connection_limit
            else:
                connection_limit_sum += (
                    CONF.haproxy_amphora.default_connection_limit)
        # If there's a limit between 0 and MAX, set it, otherwise just set MAX
        if 0 < connection_limit_sum < constants.HAPROXY_MAX_MAXCONN:
            ret_value['global_connection_limit'] = connection_limit_sum
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

    def _transform_listener(self, listener: models.Listener, tls_certs,
                            feature_compatibility,
                            loadbalancer):
        """Transforms a listener into an object that will

            be processed by the templating system
        """
        ret_value = {
            'id': listener.id,
            'protocol_port': listener.protocol_port,
            'protocol_mode': PROTOCOL_MAP[listener.protocol],
            'protocol': listener.protocol,
            'insert_headers': listener.insert_headers,
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
            lib_consts.PROTOCOL_PROMETHEUS: feature_compatibility.get(
                lib_consts.PROTOCOL_PROMETHEUS, False)
        }
        if self.connection_logging:
            ret_value['user_log_format'] = (
                self._format_log_string(loadbalancer, listener.protocol))
        if listener.connection_limit and listener.connection_limit > -1:
            ret_value['connection_limit'] = listener.connection_limit
        else:
            ret_value['connection_limit'] = (
                CONF.haproxy_amphora.default_connection_limit)

        if listener.tls_certificate_id:
            ret_value['crt_list_filename'] = os.path.join(
                CONF.haproxy_amphora.base_cert_dir,
                loadbalancer.id, '{}.pem'.format(listener.id))

        if tls_certs is not None:
            if listener.client_ca_tls_certificate_id:
                ret_value['client_ca_tls_path'] = '%s' % (
                    os.path.join(
                        self.base_crt_dir, loadbalancer.id,
                        tls_certs[listener.client_ca_tls_certificate_id]))
                ret_value['client_auth'] = CLIENT_AUTH_MAP.get(
                    listener.client_authentication)

            if listener.client_crl_container_id:
                ret_value['client_crl_path'] = '%s' % (
                    os.path.join(self.base_crt_dir, loadbalancer.id,
                                 tls_certs[listener.client_crl_container_id]))

        tls_enabled = False
        if listener.protocol in (constants.PROTOCOL_TERMINATED_HTTPS,
                                 constants.PROTOCOL_PROMETHEUS):
            tls_enabled = True
            if listener.tls_ciphers is not None:
                ret_value['tls_ciphers'] = listener.tls_ciphers
            if listener.tls_versions is not None:
                ret_value['tls_versions'] = listener.tls_versions
            if listener.alpn_protocols is not None:
                ret_value['alpn_protocols'] = ",".join(listener.alpn_protocols)
            if listener.hsts_max_age is not None:
                hsts_directives = f"max-age={listener.hsts_max_age};"
                if listener.hsts_include_subdomains:
                    hsts_directives += " includeSubDomains;"
                if listener.hsts_preload:
                    hsts_directives += " preload;"
                ret_value['hsts_directives'] = hsts_directives

        pools = []
        pool_gen = (pool for pool in listener.pools if
                    pool.provisioning_status != constants.PENDING_DELETE)
        for pool in pool_gen:
            kwargs = {}
            if tls_certs is not None and tls_certs.get(pool.id):
                kwargs = {'pool_tls_certs': tls_certs.get(pool.id)}
            pools.append(self._transform_pool(
                pool, feature_compatibility, tls_enabled, **kwargs))
        ret_value['pools'] = pools
        policy_gen = (policy for policy in listener.l7policies if
                      policy.provisioning_status != constants.PENDING_DELETE)
        if listener.default_pool:
            for pool in pools:
                if pool['id'] == listener.default_pool.id:
                    ret_value['default_pool'] = pool
                    break

        l7policies = [self._transform_l7policy(
                      x, feature_compatibility, tls_enabled, tls_certs)
                      for x in policy_gen]
        ret_value['l7policies'] = l7policies
        return ret_value

    def _transform_pool(self, pool, feature_compatibility,
                        listener_tls_enabled, pool_tls_certs=None):
        """Transforms a pool into an object that will

            be processed by the templating system
        """
        proxy_protocol_version = None
        if pool.protocol == constants.PROTOCOL_PROXY:
            proxy_protocol_version = 1
        if pool.protocol == lib_consts.PROTOCOL_PROXYV2:
            proxy_protocol_version = 2
        ret_value = {
            'id': pool.id,
            'protocol': PROTOCOL_MAP[pool.protocol],
            'proxy_protocol': proxy_protocol_version,
            'listener_tls_enabled': listener_tls_enabled,
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
        members_gen = (mem for mem in pool.members if
                       mem.provisioning_status != constants.PENDING_DELETE)
        members = [self._transform_member(x, feature_compatibility)
                   for x in members_gen]
        ret_value['members'] = members
        health_mon = pool.health_monitor
        if (health_mon and
                health_mon.provisioning_status != constants.PENDING_DELETE):
            ret_value['health_monitor'] = self._transform_health_monitor(
                health_mon, feature_compatibility)
        if pool.session_persistence:
            ret_value[
                'session_persistence'] = self._transform_session_persistence(
                pool.session_persistence, feature_compatibility)
        if (pool.tls_certificate_id and pool_tls_certs and
                pool_tls_certs.get('client_cert')):
            ret_value['client_cert'] = pool_tls_certs.get('client_cert')
        if pool.tls_enabled is True:
            if pool.tls_ciphers is not None:
                ret_value['tls_ciphers'] = pool.tls_ciphers
            if pool.tls_versions is not None:
                ret_value['tls_versions'] = pool.tls_versions
            if (pool.alpn_protocols is not None and
                    feature_compatibility.get(constants.POOL_ALPN, False)):
                ret_value['alpn_protocols'] = ",".join(pool.alpn_protocols)
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
            codes = '|'.join(octavia_utils.expand_expected_codes(
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
                            listener_tls_enabled, tls_certs=None):
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
        if (l7policy.redirect_pool and
            l7policy.redirect_pool.provisioning_status !=
                constants.PENDING_DELETE):
            kwargs = {}
            if tls_certs is not None and tls_certs.get(
                    l7policy.redirect_pool.id):
                kwargs = {'pool_tls_certs':
                          tls_certs.get(l7policy.redirect_pool.id)}
            ret_value['redirect_pool'] = self._transform_pool(
                l7policy.redirect_pool, feature_compatibility,
                listener_tls_enabled, **kwargs)
        else:
            ret_value['redirect_pool'] = None
        if (l7policy.action in [constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                                constants.L7POLICY_ACTION_REDIRECT_PREFIX] and
                l7policy.redirect_http_code):
            ret_value['redirect_http_code'] = l7policy.redirect_http_code
        else:
            ret_value['redirect_http_code'] = None
        rule_gen = (rule for rule in l7policy.l7rules if rule.enabled and
                    rule.provisioning_status != constants.PENDING_DELETE)
        l7rules = [self._transform_l7rule(x, feature_compatibility)
                   for x in rule_gen]
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
