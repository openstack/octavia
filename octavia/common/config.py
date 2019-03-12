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
from oslo_config import cfg
from oslo_db import options as db_options
from oslo_log import log as logging
import oslo_messaging as messaging

from octavia.certificates.common import local
from octavia.common import constants
from octavia.common import utils
from octavia.i18n import _
from octavia import version

LOG = logging.getLogger(__name__)


core_opts = [
    cfg.HostnameOpt('host', default=utils.get_hostname(),
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
    cfg.StrOpt('api_handler', default='queue_producer',
               help=_("The handler that the API communicates with")),
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
    cfg.BoolOpt('api_v1_enabled', default=True,
                help=_("Expose the v1 API?")),
    cfg.BoolOpt('api_v2_enabled', default=True,
                help=_("Expose the v2 API?")),
    cfg.BoolOpt('allow_tls_terminated_listeners', default=True,
                help=_("Allow users to create TLS Terminated listeners?")),
    cfg.BoolOpt('allow_ping_health_monitors', default=True,
                help=_("Allow users to create PING type Health Monitors?")),
    cfg.DictOpt('enabled_provider_drivers',
                help=_('List of enabled provider drivers and description '
                       'dictionaries. Must match the driver name in the '
                       'octavia.api.drivers entrypoint. Example: '
                       '{\'amphora\': \'The Octavia Amphora driver.\', '
                       '\'octavia\': \'Deprecated alias of the Octavia '
                       'Amphora driver.\'}'),
                default={'amphora': 'The Octavia Amphora driver.',
                         'octavia': 'Deprecated alias of the Octavia Amphora '
                         'driver.'}),
    cfg.StrOpt('default_provider_driver', default='amphora',
               help=_('Default provider driver.')),
    cfg.IntOpt('udp_connect_min_interval_health_monitor',
               default=3,
               help=_("The minimum health monitor delay interval for the "
                      "UDP-CONNECT Health Monitor type. A negative integer "
                      "value means 'no limit'.")),
]

# Options only used by the amphora agent
amphora_agent_opts = [
    cfg.StrOpt('agent_server_ca', default='/etc/octavia/certs/client_ca.pem',
               help=_("The ca which signed the client certificates")),
    cfg.StrOpt('agent_server_cert', default='/etc/octavia/certs/server.pem',
               help=_("The server certificate for the agent.py server "
                      "to use")),
    cfg.StrOpt('agent_server_network_dir',
               help=_("The directory where new network interfaces "
                      "are located")),
    cfg.StrOpt('agent_server_network_file',
               help=_("The file where the network interfaces are located. "
                      "Specifying this will override any value set for "
                      "agent_server_network_dir.")),
    cfg.IntOpt('agent_request_read_timeout', default=180,
               help=_("The time in seconds to allow a request from the "
                      "controller to run before terminating the socket.")),
    # Do not specify in octavia.conf, loaded at runtime
    cfg.StrOpt('amphora_id', help=_("The amphora ID.")),
    cfg.StrOpt('amphora_udp_driver',
               default='keepalived_lvs',
               help='The UDP API backend for amphora agent.'),
]

networking_opts = [
    cfg.IntOpt('max_retries', default=15,
               help=_('The maximum attempts to retry an action with the '
                      'networking service.')),
    cfg.IntOpt('retry_interval', default=1,
               help=_('Seconds to wait before retrying an action with the '
                      'networking service.')),
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
]

healthmanager_opts = [
    cfg.IPOpt('bind_ip', default='127.0.0.1',
              help=_('IP address the controller will listen on for '
                     'heart beats')),
    cfg.PortOpt('bind_port', default=5555,
                help=_('Port number the controller will listen on '
                       'for heart beats')),
    cfg.IntOpt('failover_threads',
               default=10,
               help=_('Number of threads performing amphora failovers.')),
    # TODO(tatsuma) Remove in or after "T" release
    cfg.IntOpt('status_update_threads',
               default=None,
               help=_('Number of processes for amphora status update.'),
               deprecated_for_removal=True,
               deprecated_reason=_('This option is replaced as '
                                   'health_update_threads and '
                                   'stats_update_threads')),
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

    # Used for updating health and stats
    cfg.StrOpt('health_update_driver', default='health_db',
               help=_('Driver for updating amphora health system.')),
    cfg.StrOpt('stats_update_driver', default='stats_db',
               help=_('Driver for updating amphora statistics.')),

    # Used for synchronizing neutron-lbaas and octavia
    cfg.StrOpt('event_streamer_driver',
               help=_('Specifies which driver to use for the event_streamer '
                      'for syncing the octavia and neutron_lbaas dbs. If you '
                      'don\'t need to sync the database or are running '
                      'octavia in stand alone mode use the '
                      'noop_event_streamer'),
               default='noop_event_streamer'),
    cfg.BoolOpt('sync_provisioning_status', default=False,
                help=_("Enable provisioning status sync with neutron db"))]

oslo_messaging_opts = [
    cfg.StrOpt('topic'),
    cfg.StrOpt('event_stream_topic',
               default='neutron_lbaas_event',
               help=_('topic name for communicating events through a queue')),
    cfg.StrOpt('event_stream_transport_url', default=None,
               help=_('Transport URL to use for the neutron-lbaas '
                      'synchronization event stream when neutron and octavia '
                      'have separate queues.')),
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
    cfg.IntOpt('active_connection_rety_interval',
               default=2,
               help=_('Retry timeout between connection attempts in '
                      'seconds for active amphora.')),
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
                      'suffixes.  Example: 10k')),

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
               help=_("The respawn count for haproxy's upstart script")),
    cfg.IntOpt('respawn_interval', default=2,
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
    cfg.BoolOpt('use_upstart', default=True,
                deprecated_for_removal=True,
                deprecated_reason='This is now automatically discovered '
                                  ' and configured.',
                help=_("If False, use sysvinit.")),
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
                      'without reconfiguring Octavia. '
                      'Ignored if amp_image_id is defined.')),
    cfg.StrOpt('amp_image_id',
               default='',
               deprecated_for_removal=True,
               deprecated_reason='Superseded by amp_image_tag option.',
               help=_('Glance image id for the Amphora image to boot')),
    cfg.StrOpt('amp_image_owner_id',
               default='',
               help=_('Restrict glance image selection to a specific '
                      'owner ID.  This is a recommended security setting.')),
    cfg.StrOpt('amp_ssh_key_name',
               default='',
               help=_('Optional SSH keypair name, in nova, that will be used '
                      'for the authorized_keys inside the amphora.')),
    cfg.BoolOpt('amp_ssh_access_allowed',
                default=True,
                deprecated_for_removal=True,
                deprecated_reason='This option and amp_ssh_key_name overlap '
                                  'in functionality, and only one is needed. '
                                  'SSH access can be enabled/disabled simply '
                                  'by setting amp_ssh_key_name, or not.',
                help=_('Determines whether or not to allow access '
                       'to the Amphorae')),
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
               default='amphora_noop_driver',
               help=_('Name of the amphora driver to use')),
    cfg.StrOpt('compute_driver',
               default='compute_noop_driver',
               help=_('Name of the compute driver to use')),
    cfg.StrOpt('network_driver',
               default='network_noop_driver',
               help=_('Name of the network driver to use')),
    cfg.StrOpt('distributor_driver',
               default='distributor_noop_driver',
               help=_('Name of the distributor driver to use')),
    cfg.StrOpt('loadbalancer_topology',
               default=constants.TOPOLOGY_SINGLE,
               choices=constants.SUPPORTED_LB_TOPOLOGIES,
               mutable=True,
               help=_('Load balancer topology configuration. '
                      'SINGLE - One amphora per load balancer. '
                      'ACTIVE_STANDBY - Two amphora per load balancer.')),
    cfg.BoolOpt('user_data_config_drive', default=False,
                help=_('If True, build cloud-init user-data that is passed '
                       'to the config drive on Amphora boot instead of '
                       'personality files. If False, utilize personality '
                       'files.'))
]

task_flow_opts = [
    cfg.StrOpt('engine',
               default='serial',
               help=_('TaskFlow engine to use')),
    cfg.IntOpt('max_workers',
               default=5,
               help=_('The maximum number of workers')),
    cfg.BoolOpt('disable_revert', default=False,
                help=_('If True, disables the controller worker taskflow '
                       'flows from reverting.  This will leave resources in '
                       'an inconsistent state and should only be used for '
                       'debugging purposes.'))
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
               help=_('CA certificates file path')),
    cfg.BoolOpt('insecure',
                default=False,
                help=_('Disable certificate validation on SSL connections ')),
]

house_keeping_opts = [
    cfg.IntOpt('spare_check_interval',
               default=30,
               help=_('Spare check interval in seconds')),
    cfg.IntOpt('spare_amphora_pool_size',
               default=0,
               help=_('Number of spare amphorae')),
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

anchor_opts = [
    cfg.StrOpt('url',
               default='http://localhost:9999/v1/sign/default',
               help=_('Anchor URL')),
    cfg.StrOpt('username',
               help=_('Anchor username')),
    cfg.StrOpt('password',
               help=_('Anchor password'),
               secret=True)
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
                       'turned on.')),
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
neutron_opts = [
    cfg.StrOpt('service_name',
               help=_('The name of the neutron service in the '
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
    cfg.FloatOpt('max_process_warning_percent',
                 default=0.75, min=0.01, max=0.99,
                 help=_('Percentage of max_processes (both status and stats) '
                        'in use to start logging warning messages about an '
                        'overloaded driver-agent.')),
]

# Register the configuration options
cfg.CONF.register_opts(core_opts)
cfg.CONF.register_opts(api_opts, group='api_settings')
cfg.CONF.register_opts(amphora_agent_opts, group='amphora_agent')
cfg.CONF.register_opts(networking_opts, group='networking')
cfg.CONF.register_opts(oslo_messaging_opts, group='oslo_messaging')
cfg.CONF.register_opts(haproxy_amphora_opts, group='haproxy_amphora')
cfg.CONF.register_opts(controller_worker_opts, group='controller_worker')
cfg.CONF.register_opts(keepalived_vrrp_opts, group='keepalived_vrrp')
cfg.CONF.register_opts(task_flow_opts, group='task_flow')
cfg.CONF.register_opts(house_keeping_opts, group='house_keeping')
cfg.CONF.register_opts(anchor_opts, group='anchor')
cfg.CONF.register_cli_opts(core_cli_opts)
cfg.CONF.register_opts(certificate_opts, group='certificates')
cfg.CONF.register_cli_opts(healthmanager_opts, group='health_manager')
cfg.CONF.register_opts(nova_opts, group='nova')
cfg.CONF.register_opts(glance_opts, group='glance')
cfg.CONF.register_opts(neutron_opts, group='neutron')
cfg.CONF.register_opts(quota_opts, group='quotas')
cfg.CONF.register_opts(audit_opts, group='audit')
cfg.CONF.register_opts(driver_agent_opts, group='driver_agent')

cfg.CONF.register_opts(local.certgen_opts, group='certificates')
cfg.CONF.register_opts(local.certmgr_opts, group='certificates')

# Ensure that the control exchange is set correctly
messaging.set_transport_defaults(control_exchange='octavia')
_SQL_CONNECTION_DEFAULT = 'sqlite://'
# Update the default QueuePool parameters. These can be tweaked by the
# configuration variables - max_pool_size, max_overflow and pool_timeout
db_options.set_defaults(cfg.CONF, connection=_SQL_CONNECTION_DEFAULT,
                        max_pool_size=10, max_overflow=20, pool_timeout=10)

logging.register_options(cfg.CONF)

ks_loading.register_auth_conf_options(cfg.CONF, constants.SERVICE_AUTH)
ks_loading.register_session_conf_options(cfg.CONF, constants.SERVICE_AUTH)


def init(args, **kwargs):
    cfg.CONF(args=args, project='octavia',
             version='%%prog %s' % version.version_info.release_string(),
             **kwargs)
    handle_deprecation_compatibility()
    setup_remote_pydev_debug()


def setup_logging(conf):
    """Sets up the logging options for a log with supplied name.

    :param conf: a cfg.ConfOpts object
    """
    product_name = "octavia"
    logging.setup(conf, product_name)
    LOG.info("Logging enabled!")
    LOG.info("%(prog)s version %(version)s",
             {'prog': sys.argv[0],
              'version': version.version_info.release_string()})
    LOG.debug("command line: %s", " ".join(sys.argv))


# Use cfg.CONF.set_default to override the new configuration setting
# default value.  This allows a value set, at the new location, to override
# a value set in the previous location while allowing settings that have
# not yet been moved to be utilized.
def handle_deprecation_compatibility():
    # TODO(tatsuma) Remove in or after "T" release
    if cfg.CONF.health_manager.status_update_threads is not None:
        cfg.CONF.set_default('health_update_threads',
                             cfg.CONF.health_manager.status_update_threads,
                             group='health_manager')
        cfg.CONF.set_default('stats_update_threads',
                             cfg.CONF.health_manager.status_update_threads,
                             group='health_manager')


def setup_remote_pydev_debug():
    """Required setup for remote debugging."""

    pydev_debug_host = os.environ.get('PYDEV_DEBUG_HOST')
    pydev_debug_port = os.environ.get('PYDEV_DEBUG_PORT')

    if not pydev_debug_host or not pydev_debug_port:
        return

    try:
        try:
            from pydev import pydevd
        except ImportError:
            import pydevd

        LOG.warning("Connecting to remote debugger. Once connected, resume "
                    "the program on the debugger to continue with the "
                    "initialization of the service.")
        pydevd.settrace(pydev_debug_host,
                        port=int(pydev_debug_port),
                        stdoutToServer=True,
                        stderrToServer=True)
    except Exception:
        LOG.exception('Unable to join debugger, please make sure that the '
                      'debugger processes is listening on debug-host '
                      '\'%(debug-host)s\' debug-port \'%(debug-port)s\'.',
                      {'debug-host': pydev_debug_host,
                       'debug-port': pydev_debug_port})
        raise
