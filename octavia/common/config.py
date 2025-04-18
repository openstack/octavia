# Copyright 2011 VMware, Inc., 2014 A10 Networks
# All Rights Reserved.
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

"""
Routines for configuring Octavia
"""

import os
import sys

from keystoneauth1 import loading as ks_loading
from octavia_lib.common import constants as lib_consts
from oslo_config import cfg
from oslo_db import options as db_options
from oslo_log import log as logging
import oslo_messaging as messaging
from oslo_policy import opts as policy_opts

from octavia.certificates.common import local
from octavia.common import constants
from octavia.common import utils
from octavia.common import validate
from octavia.i18n import _
from octavia import version

LOG = logging.getLogger(__name__)

core_opts = [
    cfg.HostnameOpt('host', default=utils.get_hostname(),
                    sample_default='<server-hostname.example.com>',
                    help=_("The hostname Octavia is running on")),
    cfg.StrOpt('octavia_plugins', default='hot_plug_plugin',
               help=_("Name of the controller plugin to use")),
]

api_opts = [
    cfg.IPOpt('bind_host', default='127.0.0.1',
              help=_("The host IP to bind to")),
    cfg.PortOpt('bind_port', default=9876,
                help=_("The port to bind to")),
    cfg.StrOpt('auth_strategy', default=constants.KEYSTONE,
               choices=[constants.NOAUTH,
                        constants.KEYSTONE,
                        constants.TESTING],
               help=_("The auth strategy for API requests.")),
    cfg.BoolOpt('allow_pagination', default=True,
                help=_("Allow the usage of pagination")),
    cfg.BoolOpt('allow_sorting', default=True,
                help=_("Allow the usage of sorting")),
    cfg.BoolOpt('allow_filtering', default=True,
                help=_("Allow the usage of filtering")),
    cfg.BoolOpt('allow_field_selection', default=True,
                help=_("Allow the usage of field selection")),
    cfg.StrOpt('pagination_max_limit',
               default=str(constants.DEFAULT_PAGE_SIZE),
               help=_("The maximum number of items returned in a single "
                      "response. The string 'infinite' or a negative "
                      "integer value means 'no limit'")),
    cfg.StrOpt('api_base_uri',
               help=_("Base URI for the API for use in pagination links. "
                      "This will be autodetected from the request if not "
                      "overridden here.")),
    cfg.BoolOpt('allow_tls_terminated_listeners', default=True,
                help=_("Allow users to create TLS Terminated listeners?")),
    cfg.BoolOpt('allow_ping_health_monitors', default=True,
                help=_("Allow users to create PING type Health Monitors?")),
    cfg.BoolOpt('allow_prometheus_listeners', default=True,
                help=_("Allow users to create PROMETHEUS type listeners?")),
    cfg.DictOpt('enabled_provider_drivers',
                help=_('A comma separated list of dictionaries of the '
                       'enabled provider driver names and descriptions. '
                       'Must match the driver name in the '
                       'octavia.api.drivers entrypoint.'),
                default={'amphora': 'The Octavia Amphora driver.',
                         'octavia': 'Deprecated alias of the Octavia Amphora '
                                    'driver.',
                         }),
    cfg.StrOpt('default_provider_driver', default='amphora',
               help=_('Default provider driver.')),
    cfg.IntOpt('udp_connect_min_interval_health_monitor',
               default=3,
               help=_("The minimum health monitor delay interval for the "
                      "UDP-CONNECT Health Monitor type. A negative integer "
                      "value means 'no limit'.")),
    cfg.BoolOpt('healthcheck_enabled', default=False,
                help=_("When True, the oslo middleware healthcheck endpoint "
                       "is enabled in the Octavia API.")),
    cfg.IntOpt('healthcheck_refresh_interval', default=5,
               help=_("The interval healthcheck plugins should cache results, "
                      "in seconds.")),
    cfg.StrOpt('default_listener_ciphers',
               default=constants.CIPHERS_OWASP_SUITE_B,
               help=_("Default OpenSSL cipher string (colon-separated) for "
                      "new TLS-enabled listeners.")),
    cfg.StrOpt('default_pool_ciphers',
               default=constants.CIPHERS_OWASP_SUITE_B,
               help=_("Default OpenSSL cipher string (colon-separated) for "
                      "new TLS-enabled pools.")),
    cfg.StrOpt('tls_cipher_prohibit_list', default='',
               deprecated_name='tls_cipher_blacklist',
               help=_("Colon separated list of OpenSSL ciphers. "
                      "Usage of these ciphers will be blocked.")),
    cfg.ListOpt('default_listener_tls_versions',
                default=constants.TLS_VERSIONS_OWASP_SUITE_B,
                help=_('List of TLS versions to use for new TLS-enabled '
                       'listeners.')),
    cfg.ListOpt('default_pool_tls_versions',
                default=constants.TLS_VERSIONS_OWASP_SUITE_B,
                help=_('List of TLS versions to use for new TLS-enabled '
                       'pools.')),
    cfg.StrOpt('minimum_tls_version',
               default=None,
               choices=constants.TLS_ALL_VERSIONS + [None],
               help=_('Minimum allowed TLS version for listeners and pools.')),
    cfg.ListOpt('default_listener_alpn_protocols',
                default=[lib_consts.ALPN_PROTOCOL_HTTP_2,
                         lib_consts.ALPN_PROTOCOL_HTTP_1_1,
                         lib_consts.ALPN_PROTOCOL_HTTP_1_0],
                help=_('List of ALPN protocols to use for new TLS-enabled '
                       'listeners.')),
    cfg.ListOpt('default_pool_alpn_protocols',
                default=[lib_consts.ALPN_PROTOCOL_HTTP_2,
                         lib_consts.ALPN_PROTOCOL_HTTP_1_1,
                         lib_consts.ALPN_PROTOCOL_HTTP_1_0],
                help=_('List of ALPN protocols to use for new TLS-enabled '
                       'pools.')),
]

# Options only used by the amphora agent
amphora_agent_opts = [
    cfg.StrOpt('agent_server_ca', default='/etc/octavia/certs/client_ca.pem',
               help=_("The ca which signed the client certificates")),
    cfg.StrOpt('agent_server_cert', default='/etc/octavia/certs/server.pem',
               help=_("The server certificate for the agent server "
                      "to use")),
    cfg.StrOpt('agent_server_network_dir',
               help=_("The directory where new network interfaces "
                      "are located")),
    cfg.IntOpt('agent_request_read_timeout', default=180,
               help=_("The time in seconds to allow a request from the "
                      "controller to run before terminating the socket.")),
    cfg.StrOpt('agent_tls_protocol', default=lib_consts.TLS_VERSION_1_2,
               help=_("Minimum TLS protocol for communication with the "
                      "amphora agent."),
               choices=constants.TLS_ALL_VERSIONS),

    # Logging setup
    cfg.ListOpt('admin_log_targets',
                help=_('List of log server ip and port pairs for '
                       'Administrative logs. Additional hosts are backup to '
                       'the primary server. If none is '
                       'specified remote logging is disabled. Example '
                       '127.0.0.1:10514, 192.168.0.1:10514')),
    cfg.ListOpt('tenant_log_targets',
                help=_('List of log server ip and port pairs for '
                       'tenant traffic logs. Additional hosts are backup to '
                       'the primary server. If none is '
                       'specified remote logging is disabled. Example '
                       '127.0.0.1:10514, 192.168.0.1:10514')),
    cfg.IntOpt('user_log_facility', default=0, min=0, max=7,
               help=_('LOG_LOCAL facility number to use for user traffic '
                      'logs.')),
    cfg.IntOpt('administrative_log_facility', default=1, min=0, max=7,
               help=_('LOG_LOCAL facility number to use for amphora processes '
                      'logs.')),
    cfg.StrOpt('log_protocol', default=lib_consts.PROTOCOL_UDP,
               choices=[lib_consts.PROTOCOL_TCP, lib_consts.PROTOCOL_UDP],
               help=_("The log forwarding transport protocol. One of UDP or "
                      "TCP.")),
    cfg.IntOpt('log_retry_count', default=5,
               help=_('The maximum attempts to retry connecting to the '
                      'logging host.')),
    cfg.IntOpt('log_retry_interval', default=2,
               help=_('The time, in seconds, to wait between retries '
                      'connecting to the logging host.')),
    cfg.IntOpt('log_queue_size', default=10000,
               help=_('The queue size (messages) to buffer log messages.')),
    cfg.StrOpt('logging_template_override',
               help=_('Custom logging configuration template.')),
    cfg.BoolOpt('forward_all_logs', default=False,
                help=_('When True, the amphora will forward all of the '
                       'system logs (except tenant traffic logs) to the '
                       'admin log target(s). When False, '
                       'only amphora specific admin logs will be forwarded.')),
    cfg.BoolOpt('disable_local_log_storage', default=False,
                help=_('When True, no logs will be written to the amphora '
                       'filesystem. When False, log files will be written to '
                       'the local filesystem.')),

    # Do not specify in octavia.conf, loaded at runtime
    cfg.StrOpt('amphora_id', help=_("The amphora ID.")),
    cfg.StrOpt('amphora_udp_driver',
               default='keepalived_lvs',
               help='The UDP API backend for amphora agent.',
               deprecated_for_removal=True,
               deprecated_reason=_('amphora-agent will not support any other '
                                   'backend than keepalived_lvs.'),
               deprecated_since='Wallaby'),
]

compute_opts = [
    cfg.IntOpt('max_retries', default=15,
               help=_('The maximum attempts to retry an action with the '
                      'compute service.')),
    cfg.IntOpt('retry_interval', default=1,
               help=_('Seconds to wait before retrying an action with the '
                      'compute service.')),
    cfg.IntOpt('retry_backoff', default=1,
               help=_('The seconds to backoff retry attempts.')),
    cfg.IntOpt('retry_max', default=10,
               help=_('The maximum interval in seconds between retry '
                      'attempts.')),
]

networking_opts = [
    cfg.IntOpt('max_retries', default=15,
               help=_('The maximum attempts to retry an action with the '
                      'networking service.')),
    cfg.IntOpt('retry_interval', default=1,
               help=_('Seconds to wait before retrying an action with the '
                      'networking service.')),
    cfg.IntOpt('retry_backoff', default=1,
               help=_('The seconds to backoff retry attempts.')),
    cfg.IntOpt('retry_max', default=10,
               help=_('The maximum interval in seconds between retry '
                      'attempts.')),
    cfg.IntOpt('port_detach_timeout', default=300,
               help=_('Seconds to wait for a port to detach from an '
                      'amphora.')),
    cfg.BoolOpt('allow_vip_network_id', default=True,
                help=_('Can users supply a network_id for their VIP?')),
    cfg.BoolOpt('allow_vip_subnet_id', default=True,
                help=_('Can users supply a subnet_id for their VIP?')),
    cfg.BoolOpt('allow_vip_port_id', default=True,
                help=_('Can users supply a port_id for their VIP?')),
    cfg.ListOpt('valid_vip_networks',
                help=_('List of network_ids that are valid for VIP '
                       'creation. If this field is empty, no validation '
                       'is performed.')),
    cfg.ListOpt('reserved_ips',
                default=['169.254.169.254'],
                item_type=cfg.types.IPAddress(),
                help=_('List of IP addresses reserved from being used for '
                       'member addresses. IPv6 addresses should be in '
                       'expanded, uppercase form.')),
    cfg.BoolOpt('allow_invisible_resource_usage', default=False,
                help=_("When True, users can use network resources they "
                       "cannot normally see as VIP or member subnets. Making "
                       "this True may allow users to access resources on "
                       "subnets they do not normally have access to via "
                       "neutron RBAC policies.")),
]

health_manager_opts = [
    cfg.IPOpt('bind_ip', default='127.0.0.1',
              help=_('IP address the controller will listen on for '
                     'heart beats')),
    cfg.PortOpt('bind_port', default=5555,
                help=_('Port number the controller will listen on '
                       'for heart beats')),
    cfg.IntOpt('failover_threads',
               default=10,
               help=_('Number of threads performing amphora failovers.')),
    cfg.IntOpt('health_update_threads',
               default=None,
               help=_('Number of processes for amphora health update.')),
    cfg.IntOpt('stats_update_threads',
               default=None,
               help=_('Number of processes for amphora stats update.')),
    cfg.StrOpt('heartbeat_key',
               mutable=True,
               help=_('key used to validate amphora sending '
                      'the message'), secret=True),
    cfg.IntOpt('heartbeat_timeout',
               default=60,
               help=_('Interval, in seconds, to wait before failing over an '
                      'amphora.')),
    cfg.IntOpt('health_check_interval',
               default=3,
               help=_('Sleep time between health checks in seconds.')),
    cfg.IntOpt('sock_rlimit', default=0,
               help=_(' sets the value of the heartbeat recv buffer')),
    cfg.IntOpt('failover_threshold', default=None,
               help=_('Stop failovers if the count of simultaneously failed '
                      'amphora reaches this number. This may prevent large '
                      'scale accidental failover events, like in the case of '
                      'network failures or read-only database issues.')),

    # Used by the health manager on the amphora
    cfg.ListOpt('controller_ip_port_list',
                help=_('List of controller ip and port pairs for the '
                       'heartbeat receivers. Example 127.0.0.1:5555, '
                       '192.168.0.1:5555'),
                mutable=True,
                default=[]),
    cfg.IntOpt('heartbeat_interval',
               default=10,
               mutable=True,
               help=_('Sleep time between sending heartbeats.')),
]

oslo_messaging_opts = [
    cfg.StrOpt('topic', help=_('Topic (i.e. Queue) Name')),
]

haproxy_amphora_opts = [
    cfg.StrOpt('base_path',
               default='/var/lib/octavia',
               help=_('Base directory for amphora files.')),
    cfg.StrOpt('base_cert_dir',
               default='/var/lib/octavia/certs',
               help=_('Base directory for cert storage.')),
    cfg.StrOpt('haproxy_template', help=_('Custom haproxy template.')),
    cfg.BoolOpt('connection_logging', default=True,
                help=_('Set this to False to disable connection logging.')),
    cfg.IntOpt('connection_max_retries',
               default=120,
               help=_('Retry threshold for connecting to amphorae.')),
    cfg.IntOpt('connection_retry_interval',
               default=5,
               help=_('Retry timeout between connection attempts in '
                      'seconds.')),
    cfg.IntOpt('active_connection_max_retries',
               default=15,
               help=_('Retry threshold for connecting to active amphorae.')),
    cfg.IntOpt('active_connection_retry_interval',
               default=2,
               deprecated_name='active_connection_rety_interval',
               help=_('Retry timeout between connection attempts in '
                      'seconds for active amphora.')),
    cfg.IntOpt('failover_connection_max_retries',
               default=2,
               help=_('Retry threshold for connecting to an amphora in '
                      'failover.')),
    cfg.IntOpt('failover_connection_retry_interval',
               default=5,
               help=_('Retry timeout between connection attempts in '
                      'seconds for amphora in failover.')),
    cfg.IntOpt('build_rate_limit',
               default=-1,
               help=_('Number of amphorae that could be built per controller '
                      'worker, simultaneously.')),
    cfg.IntOpt('build_active_retries',
               default=120,
               help=_('Retry threshold for waiting for a build slot for '
                      'an amphorae.')),
    cfg.IntOpt('build_retry_interval',
               default=5,
               help=_('Retry timeout between build attempts in '
                      'seconds.')),
    cfg.StrOpt('haproxy_stick_size', default='10k',
               help=_('Size of the HAProxy stick table. Accepts k, m, g '
                      'suffixes.')),
    cfg.StrOpt('user_log_format',
               default='{{ project_id }} {{ lb_id }} %f %ci %cp %t %{+Q}r %ST '
                       '%B %U %[ssl_c_verify] %{+Q}[ssl_c_s_dn] %b %s %Tt '
                       '%tsc',
               help=_('Log format string for user flow logging.')),

    # REST server
    cfg.IPOpt('bind_host', default='::',  # nosec
              help=_("The host IP to bind to")),
    cfg.PortOpt('bind_port', default=9443,
                help=_("The port to bind to")),
    cfg.StrOpt('lb_network_interface',
               default='o-hm0',
               help=_('Network interface through which to reach amphora, only '
                      'required if using IPv6 link local addresses.')),
    cfg.StrOpt('haproxy_cmd', default='/usr/sbin/haproxy',
               help=_("The full path to haproxy")),
    cfg.IntOpt('respawn_count', default=2,
               deprecated_for_removal=True,
               deprecated_reason='upstart support has been removed and this '
                                 'option is no longer used.',
               help=_("The respawn count for haproxy's upstart script")),
    cfg.IntOpt('respawn_interval', default=2,
               deprecated_for_removal=True,
               deprecated_reason='upstart support has been removed and this '
                                 'option is no longer used.',
               help=_("The respawn interval for haproxy's upstart script")),
    cfg.FloatOpt('rest_request_conn_timeout', default=10,
                 help=_("The time in seconds to wait for a REST API "
                        "to connect.")),
    cfg.FloatOpt('rest_request_read_timeout', default=60,
                 help=_("The time in seconds to wait for a REST API "
                        "response.")),
    cfg.IntOpt('timeout_client_data',
               default=constants.DEFAULT_TIMEOUT_CLIENT_DATA,
               help=_('Frontend client inactivity timeout.')),
    cfg.IntOpt('timeout_member_connect',
               default=constants.DEFAULT_TIMEOUT_MEMBER_CONNECT,
               help=_('Backend member connection timeout.')),
    cfg.IntOpt('timeout_member_data',
               default=constants.DEFAULT_TIMEOUT_MEMBER_DATA,
               help=_('Backend member inactivity timeout.')),
    cfg.IntOpt('timeout_tcp_inspect',
               default=constants.DEFAULT_TIMEOUT_TCP_INSPECT,
               help=_('Time to wait for TCP packets for content inspection.')),
    # REST client
    cfg.StrOpt('client_cert', default='/etc/octavia/certs/client.pem',
               help=_("The client certificate to talk to the agent")),
    cfg.StrOpt('server_ca', default='/etc/octavia/certs/server_ca.pem',
               help=_("The ca which signed the server certificates")),
    cfg.IntOpt('api_db_commit_retry_attempts', default=15,
               help=_('The number of times the database action will be '
                      'attempted.')),
    cfg.IntOpt('api_db_commit_retry_initial_delay', default=1,
               help=_('The initial delay before a retry attempt.')),
    cfg.IntOpt('api_db_commit_retry_backoff', default=1,
               help=_('The time to backoff retry attempts.')),
    cfg.IntOpt('api_db_commit_retry_max', default=5,
               help=_('The maximum amount of time to wait between retry '
                      'attempts.')),
    cfg.IntOpt('default_connection_limit',
               default=constants.HAPROXY_DEFAULT_MAXCONN,
               help=_('Default connection_limit for listeners, used when '
                      'setting "-1" or when unsetting connection_limit with '
                      'the listener API.')),
]

controller_worker_opts = [
    cfg.IntOpt('workers',
               default=1, min=1,
               help='Number of workers for the controller-worker service.'),
    cfg.IntOpt('amp_active_retries',
               default=30,
               help=_('Retry attempts to wait for Amphora to become active')),
    cfg.IntOpt('amp_active_wait_sec',
               default=10,
               help=_('Seconds to wait between checks on whether an Amphora '
                      'has become active')),
    cfg.StrOpt('amp_flavor_id',
               default='',
               help=_('Nova instance flavor id for the Amphora')),
    cfg.StrOpt('amp_image_tag',
               default='',
               help=_('Glance image tag for the Amphora image to boot. '
                      'Use this option to be able to update the image '
                      'without reconfiguring Octavia.')),
    cfg.StrOpt('amp_image_owner_id',
               default='',
               help=_('Restrict glance image selection to a specific '
                      'owner ID.  This is a recommended security setting.')),
    cfg.StrOpt('amp_ssh_key_name',
               default='',
               help=_('Optional SSH keypair name, in nova, that will be used '
                      'for the authorized_keys inside the amphora.')),
    cfg.StrOpt('amp_timezone',
               default='UTC',
               help=_('The timezone to use in the Amphora as represented in '
                      '/usr/share/zoneinfo.')),
    cfg.ListOpt('amp_boot_network_list',
                default='',
                help=_('List of networks to attach to the Amphorae. '
                       'All networks defined in the list will '
                       'be attached to each amphora.')),
    cfg.ListOpt('amp_secgroup_list',
                default='',
                help=_('List of security groups to attach to the Amphora.')),
    cfg.StrOpt('client_ca',
               default='/etc/octavia/certs/ca_01.pem',
               help=_('Client CA for the amphora agent to use')),
    cfg.StrOpt('amphora_driver',
               default='amphora_haproxy_rest_driver',
               help=_('Name of the amphora driver to use')),
    cfg.StrOpt('compute_driver',
               default='compute_nova_driver',
               help=_('Name of the compute driver to use')),
    cfg.StrOpt('network_driver',
               default='allowed_address_pairs_driver',
               help=_('Name of the network driver to use')),
    cfg.StrOpt('volume_driver',
               default=constants.VOLUME_NOOP_DRIVER,
               choices=constants.SUPPORTED_VOLUME_DRIVERS,
               help=_('Name of the volume driver to use')),
    cfg.StrOpt('image_driver',
               default='image_glance_driver',
               choices=constants.SUPPORTED_IMAGE_DRIVERS,
               help=_('Name of the image driver to use')),
    cfg.StrOpt('distributor_driver',
               default='distributor_noop_driver',
               help=_('Name of the distributor driver to use')),
    cfg.ListOpt('statistics_drivers', default=['stats_db'],
                help=_('List of drivers for updating amphora statistics.')),
    cfg.StrOpt('loadbalancer_topology',
               default=constants.TOPOLOGY_SINGLE,
               choices=constants.SUPPORTED_LB_TOPOLOGIES,
               mutable=True,
               help=_('Load balancer topology configuration. '
                      'SINGLE - One amphora per load balancer. '
                      'ACTIVE_STANDBY - Two amphora per load balancer.')),
    cfg.BoolOpt('user_data_config_drive', default=False,
                deprecated_for_removal=True,
                deprecated_reason=_('User_data nova option is not used and is '
                                    ' too small to replace the config_drive.'),
                deprecated_since='Antelope(2023.1)',
                help=_('If True, build cloud-init user-data that is passed '
                       'to the config drive on Amphora boot instead of '
                       'personality files. If False, utilize personality '
                       'files.')),
    cfg.IntOpt('amphora_delete_retries', default=5,
               help=_('Number of times an amphora delete should be retried.')),
    cfg.IntOpt('amphora_delete_retry_interval', default=5,
               help=_('Time, in seconds, between amphora delete retries.')),
    cfg.BoolOpt('event_notifications', default=True,
                help=_('Enable octavia event notifications. See '
                       'oslo_messaging_notifications section for additional '
                       'requirements.')),
    # 2000 attempts is around 2h45 with the default settings
    cfg.IntOpt('db_commit_retry_attempts', default=2000,
               help=_('The number of times the database action will be '
                      'attempted.')),
    cfg.IntOpt('db_commit_retry_initial_delay', default=1,
               help=_('The initial delay before a retry attempt.')),
    cfg.IntOpt('db_commit_retry_backoff', default=1,
               help=_('The time to backoff retry attempts.')),
    cfg.IntOpt('db_commit_retry_max', default=5,
               help=_('The maximum amount of time to wait between retry '
                      'attempts.')),
]

task_flow_opts = [
    cfg.StrOpt('engine',
               default='parallel',
               choices=constants.SUPPORTED_TASKFLOW_ENGINE_TYPES,
               help=_('TaskFlow engine to use.')),
    cfg.IntOpt('max_workers',
               default=5,
               help=_('The maximum number of workers')),
    cfg.BoolOpt('disable_revert', default=False,
                help=_('If True, disables the controller worker taskflow '
                       'flows from reverting.  This will leave resources in '
                       'an inconsistent state and should only be used for '
                       'debugging purposes.')),
    cfg.StrOpt('persistence_connection',
               default='sqlite://',
               help='Persistence database, which will be used to store tasks '
                    'states. Database connection url with db name'),
    cfg.BoolOpt('jobboard_enabled', default=False,
                help=_('If True, enables TaskFlow jobboard.')),
    cfg.StrOpt('jobboard_backend_driver',
               default='redis_taskflow_driver',
               choices=[('redis_taskflow_driver',
                         'Driver that will use Redis to store job states.'),
                        ('zookeeper_taskflow_driver',
                         'Driver that will use Zookeeper to store job '
                         'states.'),
                        ('etcd_taskflow_driver',
                         'Driver that will user Etcd to store job states.')],
               help='Jobboard backend driver that will monitor job state.'),
    cfg.ListOpt('jobboard_backend_hosts', default=['127.0.0.1'],
                help='Jobboard backend server host(s).'),
    cfg.PortOpt('jobboard_backend_port', default=6379,
                help='Jobboard backend server port'),
    cfg.StrOpt('jobboard_backend_username',
               help='Jobboard backend server user name'),
    cfg.StrOpt('jobboard_backend_password', secret=True,
               help='Jobboard backend server password'),
    cfg.StrOpt('jobboard_backend_namespace', default='octavia_jobboard',
               help='Jobboard name that should be used to store taskflow '
                    'job id and claims for it.'),
    cfg.IntOpt('jobboard_redis_backend_db',
               default=0, min=0,
               help='Database ID in redis server.'),
    cfg.StrOpt('jobboard_redis_sentinel', default=None,
               help='Sentinel name if it is used for Redis.'),
    cfg.StrOpt('jobboard_redis_sentinel_username',
               help='Redis Sentinel server user name'),
    cfg.StrOpt('jobboard_redis_sentinel_password', secret=True,
               help='Redis Sentinel server password'),
    cfg.DictOpt('jobboard_redis_backend_ssl_options',
                help='Redis jobboard backend ssl configuration options.',
                default={'ssl': False,
                         'ssl_keyfile': None,
                         'ssl_certfile': None,
                         'ssl_ca_certs': None,
                         'ssl_cert_reqs': 'required'}),
    cfg.DictOpt('jobboard_redis_sentinel_ssl_options',
                help='Redis sentinel ssl configuration options.',
                default={'ssl': False,
                         'ssl_keyfile': None,
                         'ssl_certfile': None,
                         'ssl_ca_certs': None,
                         'ssl_cert_reqs': 'required'}),
    cfg.DictOpt('jobboard_zookeeper_ssl_options',
                help='Zookeeper jobboard backend ssl configuration options.',
                default={'use_ssl': False,
                         'keyfile': None,
                         'keyfile_password': None,
                         'certfile': None,
                         'verify_certs': True}),
    cfg.DictOpt('jobboard_etcd_ssl_options',
                help='Etcd jobboard backend ssl configuration options.',
                default={'use_ssl': False,
                         'ca_cert': None,
                         'cert_key': None,
                         'cert_cert': None}),
    cfg.IntOpt('jobboard_etcd_timeout', default=None,
               help='Timeout when communicating with the Etcd backend.'),
    cfg.StrOpt('jobboard_etcd_api_path', default=None,
               help='API Path of the Etcd server.'),
    cfg.IntOpt('jobboard_expiration_time', default=30,
               help='For backends like redis claiming jobs requiring setting '
                    'the expiry - how many seconds the claim should be '
                    'retained for.'),
    cfg.BoolOpt('jobboard_save_logbook', default=False,
                help='If for analysis required saving logbooks info, set this '
                     'parameter to True. By default remove logbook from '
                     'persistence backend when job completed.'),
]

core_cli_opts = []

certificate_opts = [
    cfg.StrOpt('cert_manager',
               default='barbican_cert_manager',
               help='Name of the cert manager to use'),
    cfg.StrOpt('cert_generator',
               default='local_cert_generator',
               help='Name of the cert generator to use'),
    cfg.StrOpt('barbican_auth',
               default='barbican_acl_auth',
               help='Name of the Barbican authentication method to use'),
    cfg.StrOpt('service_name',
               help=_('The name of the certificate service in the keystone '
                      'catalog')),
    cfg.StrOpt('endpoint', help=_('A new endpoint to override the endpoint '
                                  'in the keystone catalog.')),
    cfg.StrOpt('region_name',
               help='Region in Identity service catalog to use for '
                    'communication with the barbican service.'),
    cfg.StrOpt('endpoint_type',
               default='publicURL',
               help='The endpoint_type to be used for barbican service.'),
    cfg.StrOpt('ca_certificates_file',
               help=_('CA certificates file path for the key manager service '
                      '(such as Barbican).')),
    cfg.BoolOpt('insecure',
                default=False,
                help=_('Disable certificate validation on SSL connections ')),
]

house_keeping_opts = [
    cfg.IntOpt('cleanup_interval',
               default=30,
               help=_('DB cleanup interval in seconds')),
    cfg.IntOpt('amphora_expiry_age',
               default=604800,
               help=_('Amphora expiry age in seconds')),
    cfg.IntOpt('load_balancer_expiry_age',
               default=604800,
               help=_('Load balancer expiry age in seconds')),
    cfg.IntOpt('cert_interval',
               default=3600,
               help=_('Certificate check interval in seconds')),
    # 14 days for cert expiry buffer
    cfg.IntOpt('cert_expiry_buffer',
               default=1209600,
               help=_('Seconds until certificate expiration')),
    cfg.IntOpt('cert_rotate_threads',
               default=10,
               help=_('Number of threads performing amphora certificate'
                      ' rotation'))
]

keepalived_vrrp_opts = [
    cfg.IntOpt('vrrp_advert_int',
               default=1,
               help=_('Amphora role and priority advertisement interval '
                      'in seconds.')),
    cfg.IntOpt('vrrp_check_interval',
               default=5,
               help=_('VRRP health check script run interval in seconds.')),
    cfg.IntOpt('vrrp_fail_count',
               default=2,
               help=_('Number of successive failures before transition to a '
                      'fail state.')),
    cfg.IntOpt('vrrp_success_count',
               default=2,
               help=_('Number of consecutive successes before transition to a '
                      'success state.')),
    cfg.IntOpt('vrrp_garp_refresh_interval',
               default=5,
               help=_('Time in seconds between gratuitous ARP announcements '
                      'from the MASTER.')),
    cfg.IntOpt('vrrp_garp_refresh_count',
               default=2,
               help=_('Number of gratuitous ARP announcements to make on '
                      'each refresh interval.'))

]

nova_opts = [
    cfg.StrOpt('service_name',
               help=_('The name of the nova service in the keystone catalog')),
    cfg.StrOpt('endpoint', help=_('A new endpoint to override the endpoint '
                                  'in the keystone catalog.')),
    cfg.StrOpt('region_name',
               help=_('Region in Identity service catalog to use for '
                      'communication with the OpenStack services.')),
    cfg.StrOpt('endpoint_type', default='publicURL',
               help=_('Endpoint interface in identity service to use')),
    cfg.StrOpt('ca_certificates_file',
               help=_('CA certificates file path')),
    cfg.BoolOpt('insecure',
                default=False,
                help=_('Disable certificate validation on SSL connections')),
    cfg.BoolOpt('enable_anti_affinity', default=False,
                help=_('Flag to indicate if nova anti-affinity feature is '
                       'turned on. This option is only used when creating '
                       'amphorae in ACTIVE_STANDBY topology.')),
    cfg.StrOpt('anti_affinity_policy', default=constants.ANTI_AFFINITY,
               choices=[constants.ANTI_AFFINITY, constants.SOFT_ANTI_AFFINITY],
               help=_('Sets the anti-affinity policy for nova')),
    cfg.IntOpt('random_amphora_name_length', default=0,
               help=_('If non-zero, generate a random name of the length '
                      'provided for each amphora, in the format "a[A-Z0-9]*". '
                      'Otherwise, the default name format will be used: '
                      '"amphora-{UUID}".')),
    cfg.StrOpt('availability_zone', default=None,
               help=_('Availability zone to use for creating Amphorae')),
]

cinder_opts = [
    cfg.StrOpt('service_name',
               help=_('The name of the cinder service in the keystone '
                      'catalog')),
    cfg.StrOpt('endpoint', help=_('A new endpoint to override the endpoint '
                                  'in the keystone catalog.')),
    cfg.StrOpt('region_name',
               help=_('Region in Identity service catalog to use for '
                      'communication with the OpenStack services.')),
    cfg.StrOpt('endpoint_type', default='publicURL',
               help=_('Endpoint interface in identity service to use')),
    cfg.StrOpt('ca_certificates_file',
               help=_('CA certificates file path')),
    cfg.StrOpt('availability_zone', default=None,
               help=_('Availability zone to use for creating Volume')),
    cfg.BoolOpt('insecure',
                default=False,
                help=_('Disable certificate validation on SSL connections')),
    cfg.IntOpt('volume_size', default=16,
               help=_('Size of volume, in GB, for Amphora instance')),
    cfg.StrOpt('volume_type', default=None,
               help=_('Type of volume for Amphorae volume root disk')),
    cfg.IntOpt('volume_create_retry_interval', default=5,
               help=_('Interval time to wait volume is created in available '
                      'state')),
    cfg.IntOpt('volume_create_timeout', default=300,
               help=_('Timeout to wait for volume creation success')),
    cfg.IntOpt('volume_create_max_retries', default=5,
               help=_('Maximum number of retries to create volume'))
]

neutron_opts = [
    cfg.StrOpt('endpoint', help=_('A new endpoint to override the endpoint '
                                  'in the keystone catalog.'),
               deprecated_for_removal=True,
               deprecated_reason=_('The endpoint_override option defined by '
                                   'keystoneauth1 is the new name for this '
                                   'option.'),
               deprecated_since='2023.2/Bobcat'),
    cfg.StrOpt('endpoint_type', help=_('Endpoint interface in identity '
                                       'service to use'),
               deprecated_for_removal=True,
               deprecated_reason=_('This option was replaced by the '
                                   'valid_interfaces option defined by '
                                   'keystoneauth.'),
               deprecated_since='2023.2/Bobcat'),
    cfg.StrOpt('ca_certificates_file',
               help=_('CA certificates file path'),
               deprecated_for_removal=True,
               deprecated_reason=_('The cafile option defined by '
                                   'keystoneauth1 is the new name for this '
                                   'option.'),
               deprecated_since='2023.2/Bobcat'),
]

glance_opts = [
    cfg.StrOpt('service_name',
               help=_('The name of the glance service in the '
                      'keystone catalog')),
    cfg.StrOpt('endpoint', help=_('A new endpoint to override the endpoint '
                                  'in the keystone catalog.')),
    cfg.StrOpt('region_name',
               help=_('Region in Identity service catalog to use for '
                      'communication with the OpenStack services.')),
    cfg.StrOpt('endpoint_type', default='publicURL',
               help=_('Endpoint interface in identity service to use')),
    cfg.StrOpt('ca_certificates_file',
               help=_('CA certificates file path')),
    cfg.BoolOpt('insecure',
                default=False,
                help=_('Disable certificate validation on SSL connections ')),
]

quota_opts = [
    cfg.IntOpt('default_load_balancer_quota',
               default=constants.QUOTA_UNLIMITED,
               help=_('Default per project load balancer quota.')),
    cfg.IntOpt('default_listener_quota',
               default=constants.QUOTA_UNLIMITED,
               help=_('Default per project listener quota.')),
    cfg.IntOpt('default_member_quota',
               default=constants.QUOTA_UNLIMITED,
               help=_('Default per project member quota.')),
    cfg.IntOpt('default_pool_quota',
               default=constants.QUOTA_UNLIMITED,
               help=_('Default per project pool quota.')),
    cfg.IntOpt('default_health_monitor_quota',
               default=constants.QUOTA_UNLIMITED,
               help=_('Default per project health monitor quota.')),
    cfg.IntOpt('default_l7policy_quota',
               default=constants.QUOTA_UNLIMITED,
               help=_('Default per project l7policy quota.')),
    cfg.IntOpt('default_l7rule_quota',
               default=constants.QUOTA_UNLIMITED,
               help=_('Default per project l7rule quota.')),
]

audit_opts = [
    cfg.BoolOpt('enabled', default=False,
                help=_('Enable auditing of API requests')),
    cfg.StrOpt('audit_map_file',
               default='/etc/octavia/octavia_api_audit_map.conf',
               help=_('Path to audit map file for octavia-api service. '
                      'Used only when API audit is enabled.')),
    cfg.StrOpt('ignore_req_list', default='',
               help=_('Comma separated list of REST API HTTP methods to be '
                      'ignored during audit. For example: auditing will not '
                      'be done on any GET or POST requests if this is set to '
                      '"GET,POST". It is used only when API audit is '
                      'enabled.')),
]

driver_agent_opts = [
    cfg.StrOpt('status_socket_path',
               default='/var/run/octavia/status.sock',
               help=_('Path to the driver status unix domain socket file.')),
    cfg.StrOpt('stats_socket_path',
               default='/var/run/octavia/stats.sock',
               help=_('Path to the driver statistics unix domain socket '
                      'file.')),
    cfg.StrOpt('get_socket_path',
               default='/var/run/octavia/get.sock',
               help=_('Path to the driver get unix domain socket file.')),
    cfg.IntOpt('status_request_timeout',
               default=5,
               help=_('Time, in seconds, to wait for a status update '
                      'request.')),
    cfg.IntOpt('status_max_processes',
               default=50,
               help=_('Maximum number of concurrent processes to use '
                      'servicing status updates.')),
    cfg.IntOpt('stats_request_timeout',
               default=5,
               help=_('Time, in seconds, to wait for a statistics update '
                      'request.')),
    cfg.IntOpt('stats_max_processes',
               default=50,
               help=_('Maximum number of concurrent processes to use '
                      'servicing statistics updates.')),
    cfg.IntOpt('get_request_timeout',
               default=5,
               help=_('Time, in seconds, to wait for a get request.')),
    cfg.IntOpt('get_max_processes',
               default=50,
               help=_('Maximum number of concurrent processes to use '
                      'servicing get requests.')),
    cfg.FloatOpt('max_process_warning_percent',
                 default=0.75, min=0.01, max=0.99,
                 help=_('Percentage of max_processes (both status and stats) '
                        'in use to start logging warning messages about an '
                        'overloaded driver-agent.')),
    cfg.IntOpt('provider_agent_shutdown_timeout',
               default=60,
               help=_('The time, in seconds, to wait for provider agents '
                      'to shutdown after the exit event has been set.')),
    cfg.ListOpt('enabled_provider_agents', default='',
                help=_('List of enabled provider agents. The driver-agent '
                       'will launch these agents at startup.'))
]

watcher_opts = [
    cfg.BoolOpt('enabled',
                default=False,
                help=_('Enable the openstack-watcher-middleware')),
    cfg.StrOpt('service_type',
               default='loadbalancer',
               help=_('The type of the service')),
    cfg.StrOpt('cadf_service_name',
               default=None,
               help=_('The name of the service according to CADF')),
    cfg.StrOpt('config_file',
               help=_('Path to configuration file')),
    cfg.StrOpt('statsd_host',
               default='127.0.0.1',
               help=_('Host of the StatsD backend')),
    cfg.StrOpt('statsd_namespace',
               default='openstack_watcher',
               help=_('Namespace to use for metrics')),
    cfg.IntOpt('statsd_port',
               default=9125,
               help=_('Port of the StatsD backend')),
    cfg.BoolOpt('target_project_id_from_path',
                default=False,
                help=_('Whether to get the target project uid from the path')),
    cfg.BoolOpt('target_project_id_from_service_catalog',
                default=True,
                help=_('Whether to get the target project uid from the service catalog')),
    cfg.BoolOpt('include_target_project_id_in_metric',
                default=True,
                help=_('Whether to include the target project id in the metrics')),
    cfg.BoolOpt('include_target_domain_id_in_metric',
                default=True,
                help=_('Whether to include the target domain id in the metrics')),
    cfg.BoolOpt('include_authentication_initiator_user_id_in_metric',
                default=True,
                help=_('Whether to include the initiator user id for authentication request in the metrics'))
]

# Register the configuration options
cfg.CONF.register_opts(core_opts)
cfg.CONF.register_opts(api_opts, group='api_settings')
cfg.CONF.register_opts(amphora_agent_opts, group='amphora_agent')
cfg.CONF.register_opts(compute_opts, group='compute')
cfg.CONF.register_opts(networking_opts, group='networking')
cfg.CONF.register_opts(oslo_messaging_opts, group='oslo_messaging')
cfg.CONF.register_opts(haproxy_amphora_opts, group='haproxy_amphora')
cfg.CONF.register_opts(controller_worker_opts, group='controller_worker')
cfg.CONF.register_opts(keepalived_vrrp_opts, group='keepalived_vrrp')
cfg.CONF.register_opts(task_flow_opts, group='task_flow')
cfg.CONF.register_opts(house_keeping_opts, group='house_keeping')
cfg.CONF.register_opts(certificate_opts, group='certificates')
cfg.CONF.register_opts(health_manager_opts, group='health_manager')
cfg.CONF.register_opts(nova_opts, group='nova')
cfg.CONF.register_opts(cinder_opts, group='cinder')
cfg.CONF.register_opts(glance_opts, group='glance')
cfg.CONF.register_opts(neutron_opts, group='neutron')
cfg.CONF.register_opts(quota_opts, group='quotas')
cfg.CONF.register_opts(audit_opts, group='audit')
cfg.CONF.register_opts(driver_agent_opts, group='driver_agent')

cfg.CONF.register_opts(local.certgen_opts, group='certificates')
cfg.CONF.register_opts(local.certmgr_opts, group='certificates')
cfg.CONF.register_opts(watcher_opts, group='watcher')

# Ensure that the control exchange is set correctly
messaging.set_transport_defaults(control_exchange='octavia')
_SQL_CONNECTION_DEFAULT = 'sqlite://'
# Update the default QueuePool parameters. These can be tweaked by the
# configuration variables - max_pool_size, max_overflow and pool_timeout
db_options.set_defaults(cfg.CONF, connection=_SQL_CONNECTION_DEFAULT,
                        max_pool_size=10, max_overflow=20, pool_timeout=10)


def register_ks_options(group):
    ks_loading.register_auth_conf_options(cfg.CONF, group)
    ks_loading.register_session_conf_options(cfg.CONF, group)
    ks_loading.register_adapter_conf_options(cfg.CONF, group,
                                             include_deprecated=False)


register_ks_options(constants.SERVICE_AUTH)
register_ks_options('neutron')


def register_cli_opts():
    cfg.CONF.register_cli_opts(core_cli_opts)
    logging.register_options(cfg.CONF)


def handle_neutron_deprecations():
    # Apply neutron deprecated options to their new setting if needed

    # Basically: if the new option is not set and the value of the deprecated
    # option is not the default, it means that the deprecated setting is still
    # used in the config file:
    # * convert it to a valid "new" value if needed
    # * set it as the default for the new option
    # Thus [neutron].<new_option> has an higher precedence than
    # [neutron].<deprecated_option>
    loc = cfg.CONF.get_location('endpoint', 'neutron')
    new_loc = cfg.CONF.get_location('endpoint_override', 'neutron')
    if not new_loc and loc and loc.location != cfg.Locations.opt_default:
        cfg.CONF.set_default('endpoint_override', cfg.CONF.neutron.endpoint,
                             'neutron')

    loc = cfg.CONF.get_location('endpoint_type', 'neutron')
    new_loc = cfg.CONF.get_location('valid_interfaces', 'neutron')
    if not new_loc and loc and loc.location != cfg.Locations.opt_default:
        endpoint_type = cfg.CONF.neutron.endpoint_type.replace('URL', '')
        cfg.CONF.set_default('valid_interfaces', [endpoint_type],
                             'neutron')

    loc = cfg.CONF.get_location('ca_certificates_file', 'neutron')
    new_loc = cfg.CONF.get_location('cafile', 'neutron')
    if not new_loc and loc and loc.location != cfg.Locations.opt_default:
        cfg.CONF.set_default('cafile', cfg.CONF.neutron.ca_certificates_file,
                             'neutron')


def init(args, **kwargs):
    register_cli_opts()
    cfg.CONF(args=args, project='octavia',
             version=f'%prog {version.version_info.release_string()}',
             **kwargs)
    validate.check_default_tls_versions_min_conflict()
    setup_remote_debugger()
    validate.check_default_ciphers_prohibit_list_conflict()

    # Override default auth_type for plugins with the default from service_auth
    auth_type = cfg.CONF.service_auth.auth_type
    cfg.CONF.set_default('auth_type', auth_type, 'neutron')

    handle_neutron_deprecations()


def setup_logging(conf):
    """Sets up the logging options for a log with supplied name.

    :param conf: a cfg.ConfOpts object
    """
    ll = logging.get_default_log_levels()
    logging.set_defaults(default_log_levels=ll)
    product_name = "octavia"
    logging.setup(conf, product_name)
    LOG.info("Logging enabled!")
    LOG.info("%(prog)s version %(version)s",
             {'prog': sys.argv[0],
              'version': version.version_info.release_string()})
    LOG.debug("command line: %s", " ".join(sys.argv))


def _enable_pydev(debugger_host, debugger_port):
    try:
        from pydev import pydevd  # pylint: disable=import-outside-toplevel
    except ImportError:
        import pydevd  # pylint: disable=import-outside-toplevel

    pydevd.settrace(debugger_host,
                    suspend=False,
                    port=int(debugger_port),
                    stdoutToServer=True,
                    stderrToServer=True)


def _enable_ptvsd(debuggger_host, debugger_port):
    import ptvsd  # pylint: disable=import-outside-toplevel

    # Allow other computers to attach to ptvsd at this IP address and port.
    ptvsd.enable_attach(address=(debuggger_host, debugger_port),
                        redirect_output=True)

    # Pause the program until a remote debugger is attached
    ptvsd.wait_for_attach()


def setup_remote_debugger():
    """Required setup for remote debugging."""

    debugger_type = os.environ.get('DEBUGGER_TYPE', 'pydev')
    debugger_host = os.environ.get('DEBUGGER_HOST')
    debugger_port = os.environ.get('DEBUGGER_PORT')

    if not debugger_type or not debugger_host or not debugger_port:
        return

    try:
        LOG.warning("Connecting to remote debugger. Once connected, resume "
                    "the program on the debugger to continue with the "
                    "initialization of the service.")
        if debugger_type == 'pydev':
            _enable_pydev(debugger_host, debugger_port)
        elif debugger_type == 'ptvsd':
            _enable_ptvsd(debugger_host, debugger_port)
        else:
            LOG.exception('Debugger %(debugger)s is not supported',
                          debugger_type)
    except Exception:
        LOG.exception('Unable to join debugger, please make sure that the '
                      'debugger processes is listening on debug-host '
                      '\'%(debug-host)s\' debug-port \'%(debug-port)s\'.',
                      {'debug-host': debugger_host,
                       'debug-port': debugger_port})
        raise


def set_lib_defaults():
    """Update default value for configuration options from other namespace.

    Example, oslo lib config options. This is needed for
    config generator tool to pick these default value changes.
    https://docs.openstack.org/oslo.config/latest/cli/
    generator.html#modifying-defaults-from-other-namespaces
    """

    # TODO(gmann): Remove setting the default value of config policy_file
    # once oslo_policy change the default value to 'policy.yaml'.
    # https://github.com/openstack/oslo.policy/blob/a626ad12fe5a3abd49d70e3e5b95589d279ab578/oslo_policy/opts.py#L49
    # Update default value of oslo.policy policy_file config option.
    policy_opts.set_defaults(cfg.CONF, 'policy.yaml')
