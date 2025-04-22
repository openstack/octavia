# Copyright 2014 Rackspace
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

from octavia_lib.common import constants as lib_consts

##############################################################################
# Constants common to the provider drivers moved to
#     octavia_lib.common.constants
# These are deprecated, to be removed in the 'U' release
##############################################################################
# 'loadbalancers'
LOADBALANCERS = lib_consts.LOADBALANCERS
# 'listeners'
LISTENERS = lib_consts.LISTENERS
# 'pools'
POOLS = lib_consts.POOLS
# HEALTHMONITORS = 'healthmonitors'
HEALTHMONITORS = lib_consts.HEALTHMONITORS
# 'members'
MEMBERS = lib_consts.MEMBERS
# 'l7policies'
L7POLICIES = lib_consts.L7POLICIES
# 'l7rules'
L7RULES = lib_consts.L7RULES

# 'PING'
HEALTH_MONITOR_PING = lib_consts.HEALTH_MONITOR_PING
# 'TCP'
HEALTH_MONITOR_TCP = lib_consts.HEALTH_MONITOR_TCP
# 'HTTP'
HEALTH_MONITOR_HTTP = lib_consts.HEALTH_MONITOR_HTTP
# 'HTTPS'
HEALTH_MONITOR_HTTPS = lib_consts.HEALTH_MONITOR_HTTPS
# 'TLS-HELLO'
HEALTH_MONITOR_TLS_HELLO = lib_consts.HEALTH_MONITOR_TLS_HELLO
# 'UDP-CONNECT'
HEALTH_MONITOR_UDP_CONNECT = lib_consts.HEALTH_MONITOR_UDP_CONNECT
SUPPORTED_HEALTH_MONITOR_TYPES = lib_consts.SUPPORTED_HEALTH_MONITOR_TYPES

# 'GET'
HEALTH_MONITOR_HTTP_METHOD_GET = lib_consts.HEALTH_MONITOR_HTTP_METHOD_GET
# 'HEAD'
HEALTH_MONITOR_HTTP_METHOD_HEAD = lib_consts.HEALTH_MONITOR_HTTP_METHOD_HEAD
# 'POST'
HEALTH_MONITOR_HTTP_METHOD_POST = lib_consts.HEALTH_MONITOR_HTTP_METHOD_POST
# 'PUT'
HEALTH_MONITOR_HTTP_METHOD_PUT = lib_consts.HEALTH_MONITOR_HTTP_METHOD_PUT
# 'DELETE'
HEALTH_MONITOR_HTTP_METHOD_DELETE = (
    lib_consts.HEALTH_MONITOR_HTTP_METHOD_DELETE)
# 'TRACE'
HEALTH_MONITOR_HTTP_METHOD_TRACE = lib_consts.HEALTH_MONITOR_HTTP_METHOD_TRACE
# 'OPTIONS'
HEALTH_MONITOR_HTTP_METHOD_OPTIONS = (
    lib_consts.HEALTH_MONITOR_HTTP_METHOD_OPTIONS)
# 'CONNECT'
HEALTH_MONITOR_HTTP_METHOD_CONNECT = (
    lib_consts.HEALTH_MONITOR_HTTP_METHOD_CONNECT)
# 'PATCH'
HEALTH_MONITOR_HTTP_METHOD_PATCH = lib_consts.HEALTH_MONITOR_HTTP_METHOD_PATCH
SUPPORTED_HEALTH_MONITOR_HTTP_METHODS = (
    lib_consts.SUPPORTED_HEALTH_MONITOR_HTTP_METHODS)

# 'REJECT'
L7POLICY_ACTION_REJECT = lib_consts.L7POLICY_ACTION_REJECT
# 'REDIRECT_TO_URL'
L7POLICY_ACTION_REDIRECT_TO_URL = lib_consts.L7POLICY_ACTION_REDIRECT_TO_URL
# 'REDIRECT_TO_POOL'
L7POLICY_ACTION_REDIRECT_TO_POOL = lib_consts.L7POLICY_ACTION_REDIRECT_TO_POOL
# 'REDIRECT_PREFIX'
L7POLICY_ACTION_REDIRECT_PREFIX = lib_consts.L7POLICY_ACTION_REDIRECT_PREFIX
SUPPORTED_L7POLICY_ACTIONS = lib_consts.SUPPORTED_L7POLICY_ACTIONS

# 'REGEX'
L7RULE_COMPARE_TYPE_REGEX = lib_consts.L7RULE_COMPARE_TYPE_REGEX
# 'STARTS_WITH'
L7RULE_COMPARE_TYPE_STARTS_WITH = lib_consts.L7RULE_COMPARE_TYPE_STARTS_WITH
# 'ENDS_WITH'
L7RULE_COMPARE_TYPE_ENDS_WITH = lib_consts.L7RULE_COMPARE_TYPE_ENDS_WITH
# 'CONTAINS'
L7RULE_COMPARE_TYPE_CONTAINS = lib_consts.L7RULE_COMPARE_TYPE_CONTAINS
# 'EQUAL_TO'
L7RULE_COMPARE_TYPE_EQUAL_TO = lib_consts.L7RULE_COMPARE_TYPE_EQUAL_TO
SUPPORTED_L7RULE_COMPARE_TYPES = lib_consts.SUPPORTED_L7RULE_COMPARE_TYPES

# 'HOST_NAME'
L7RULE_TYPE_HOST_NAME = lib_consts.L7RULE_TYPE_HOST_NAME
# 'PATH'
L7RULE_TYPE_PATH = lib_consts.L7RULE_TYPE_PATH
# 'FILE_TYPE'
L7RULE_TYPE_FILE_TYPE = lib_consts.L7RULE_TYPE_FILE_TYPE
# 'HEADER'
L7RULE_TYPE_HEADER = lib_consts.L7RULE_TYPE_HEADER
# 'COOKIE'
L7RULE_TYPE_COOKIE = lib_consts.L7RULE_TYPE_COOKIE
# 'SSL_CONN_HAS_CERT'
L7RULE_TYPE_SSL_CONN_HAS_CERT = lib_consts.L7RULE_TYPE_SSL_CONN_HAS_CERT
# 'SSL_VERIFY_RESULT'
L7RULE_TYPE_SSL_VERIFY_RESULT = lib_consts.L7RULE_TYPE_SSL_VERIFY_RESULT
# 'SSL_DN_FIELD'
L7RULE_TYPE_SSL_DN_FIELD = lib_consts.L7RULE_TYPE_SSL_DN_FIELD
SUPPORTED_L7RULE_TYPES = lib_consts.SUPPORTED_L7RULE_TYPES

# 'ROUND_ROBIN'
LB_ALGORITHM_ROUND_ROBIN = lib_consts.LB_ALGORITHM_ROUND_ROBIN
# 'LEAST_CONNECTIONS'
LB_ALGORITHM_LEAST_CONNECTIONS = lib_consts.LB_ALGORITHM_LEAST_CONNECTIONS
# 'SOURCE_IP'
LB_ALGORITHM_SOURCE_IP = lib_consts.LB_ALGORITHM_SOURCE_IP
SUPPORTED_LB_ALGORITHMS = lib_consts.SUPPORTED_LB_ALGORITHMS

# 'operating_status'
OPERATING_STATUS = lib_consts.OPERATING_STATUS
# 'ONLINE'
ONLINE = lib_consts.ONLINE
# 'OFFLINE'
OFFLINE = lib_consts.OFFLINE
# 'DEGRADED'
DEGRADED = lib_consts.DEGRADED
# 'ERROR'
ERROR = lib_consts.ERROR
# 'DRAINING'
DRAINING = lib_consts.DRAINING
# 'NO_MONITOR'
NO_MONITOR = lib_consts.NO_MONITOR
# 'operating_status'
SUPPORTED_OPERATING_STATUSES = lib_consts.SUPPORTED_OPERATING_STATUSES

# 'TCP'
PROTOCOL_TCP = lib_consts.PROTOCOL_TCP
# 'UDP'
PROTOCOL_UDP = lib_consts.PROTOCOL_UDP
# 'HTTP'
PROTOCOL_HTTP = lib_consts.PROTOCOL_HTTP
# 'HTTPS'
PROTOCOL_HTTPS = lib_consts.PROTOCOL_HTTPS
# 'TERMINATED_HTTPS'
PROTOCOL_TERMINATED_HTTPS = lib_consts.PROTOCOL_TERMINATED_HTTPS
# 'PROXY'
PROTOCOL_PROXY = lib_consts.PROTOCOL_PROXY
SUPPORTED_PROTOCOLS = lib_consts.SUPPORTED_PROTOCOLS
# 'PROMETHEUS'
PROTOCOL_PROMETHEUS = lib_consts.PROTOCOL_PROMETHEUS

# 'provisioning_status'
PROVISIONING_STATUS = lib_consts.PROVISIONING_STATUS
# Amphora has been allocated to a load balancer 'ALLOCATED'
AMPHORA_ALLOCATED = lib_consts.AMPHORA_ALLOCATED
# Amphora is being built 'BOOTING'
AMPHORA_BOOTING = lib_consts.AMPHORA_BOOTING
# Amphora is ready to be allocated to a load balancer 'READY'
AMPHORA_READY = lib_consts.AMPHORA_READY
# 'FAILOVER_STOPPED'. Failover threshold level has been reached.
AMPHORA_FAILOVER_STOPPED = lib_consts.AMPHORA_FAILOVER_STOPPED
# 'ACTIVE'
ACTIVE = lib_consts.ACTIVE
# 'PENDING_DELETE'
PENDING_DELETE = lib_consts.PENDING_DELETE
# 'PENDING_UPDATE'
PENDING_UPDATE = lib_consts.PENDING_UPDATE
# 'PENDING_CREATE'
PENDING_CREATE = lib_consts.PENDING_CREATE
# 'DELETED'
DELETED = lib_consts.DELETED
SUPPORTED_PROVISIONING_STATUSES = lib_consts.SUPPORTED_PROVISIONING_STATUSES

# 'SOURCE_IP'
SESSION_PERSISTENCE_SOURCE_IP = lib_consts.SESSION_PERSISTENCE_SOURCE_IP
# 'HTTP_COOKIE'
SESSION_PERSISTENCE_HTTP_COOKIE = lib_consts.SESSION_PERSISTENCE_HTTP_COOKIE
# 'APP_COOKIE'
SESSION_PERSISTENCE_APP_COOKIE = lib_consts.SESSION_PERSISTENCE_APP_COOKIE
SUPPORTED_SP_TYPES = lib_consts.SUPPORTED_SP_TYPES

# List of HTTP headers which are supported for insertion
SUPPORTED_HTTP_HEADERS = lib_consts.SUPPORTED_HTTP_HEADERS

# List of SSL headers for client certificate
SUPPORTED_SSL_HEADERS = lib_consts.SUPPORTED_SSL_HEADERS

###############################################################################

HEALTH_MONITOR_DEFAULT_EXPECTED_CODES = '200'
HEALTH_MONITOR_HTTP_DEFAULT_METHOD = lib_consts.HEALTH_MONITOR_HTTP_METHOD_GET
HEALTH_MONITOR_DEFAULT_URL_PATH = '/'
TYPE = 'type'
URL_PATH = 'url_path'
HTTP_METHOD = 'http_method'
HTTP_VERSION = 'http_version'
EXPECTED_CODES = 'expected_codes'
DELAY = 'delay'
TIMEOUT = 'timeout'
MAX_RETRIES = 'max_retries'
MAX_RETRIES_DOWN = 'max_retries_down'
RISE_THRESHOLD = 'rise_threshold'
DOMAIN_NAME = 'domain_name'

UPDATE_STATS = 'UPDATE_STATS'
UPDATE_HEALTH = 'UPDATE_HEALTH'

VALID_LISTENER_POOL_PROTOCOL_MAP = {
    PROTOCOL_TCP: [PROTOCOL_HTTP, PROTOCOL_HTTPS,
                   PROTOCOL_PROXY, lib_consts.PROTOCOL_PROXYV2, PROTOCOL_TCP],
    PROTOCOL_HTTP: [PROTOCOL_HTTP, PROTOCOL_PROXY,
                    lib_consts.PROTOCOL_PROXYV2],
    PROTOCOL_HTTPS: [PROTOCOL_HTTPS, PROTOCOL_PROXY,
                     lib_consts.PROTOCOL_PROXYV2, PROTOCOL_TCP],
    PROTOCOL_TERMINATED_HTTPS: [PROTOCOL_HTTP, PROTOCOL_PROXY,
                                lib_consts.PROTOCOL_PROXYV2],
    PROTOCOL_UDP: [PROTOCOL_UDP],
    lib_consts.PROTOCOL_SCTP: [lib_consts.PROTOCOL_SCTP],
    lib_consts.PROTOCOL_PROMETHEUS: []}

L4_ESD_POLICIES = ['proxy_protocol_2edF_v1_0', 'proxy_protocol_V2_e8f6_v1_0']
L4_ESD_TCP_POLICIES = ['ccloud_special_fastl4_noaging',
                       'ccloud_special_tcp_mirror', 'standard_tcp_a3de_v1_0']
L4_ESD_UDP_POLICIES = ['ccloud_special_udp_stateless']
L7_ESD_POLICIES = ['x_forward_5b6e_v1_0', 'one_connect_dd5c_v1_0',
                   'no_one_connect_3caB_v1_0', 'http_compression_e4a2_v1_0',
                   'cookie_encryption_b82a_v1_0', 'sso_22b0_v1_0',
                   'sso_required_f544_v1_0', 'http_redirect_a26c_v1_0',
                   'ccloud_special_xfh_override']
ALL_ESD_POLICIES = (L4_ESD_POLICIES + L4_ESD_UDP_POLICIES +
                    L7_ESD_POLICIES + L4_ESD_TCP_POLICIES)
VALID_LISTENER_ESD_MAP = {
    PROTOCOL_TCP: L4_ESD_POLICIES + L4_ESD_TCP_POLICIES,
    PROTOCOL_HTTP: L4_ESD_POLICIES + L7_ESD_POLICIES,
    PROTOCOL_HTTPS: L4_ESD_POLICIES,
    PROTOCOL_TERMINATED_HTTPS: L4_ESD_POLICIES + L7_ESD_POLICIES,
    PROTOCOL_UDP: L4_ESD_UDP_POLICIES,
    lib_consts.PROTOCOL_SCTP: [],
    lib_consts.PROTOCOL_PROMETHEUS: [],
}
ONLY_ESD_L7POLICY_PROTO = [PROTOCOL_TCP, PROTOCOL_HTTPS]

# API Integer Ranges
MIN_PORT_NUMBER = 1
MAX_PORT_NUMBER = 65535

DEFAULT_CONNECTION_LIMIT = -1
MIN_CONNECTION_LIMIT = -1

DEFAULT_WEIGHT = 1
MIN_WEIGHT = 0
MAX_WEIGHT = 256

DEFAULT_MAX_RETRIES_DOWN = 3
MIN_HM_RETRIES = 1
MAX_HM_RETRIES = 10

# 24 days:   days  d    h    m    ms
MAX_TIMEOUT = 24 * 24 * 60 * 60 * 1000
MIN_TIMEOUT = 0

DEFAULT_TIMEOUT_CLIENT_DATA = 50000
DEFAULT_TIMEOUT_MEMBER_CONNECT = 5000
DEFAULT_TIMEOUT_MEMBER_DATA = 50000
DEFAULT_TIMEOUT_TCP_INSPECT = 0

MUTABLE_STATUSES = (lib_consts.ACTIVE,)
DELETABLE_STATUSES = (lib_consts.ACTIVE, lib_consts.ERROR)
FAILOVERABLE_STATUSES = (lib_consts.ACTIVE, lib_consts.ERROR)

AMPHORA_VM = 'VM'
SUPPORTED_AMPHORA_TYPES = (AMPHORA_VM,)

DISTINGUISHED_NAME_FIELD_REGEX = lib_consts.DISTINGUISHED_NAME_FIELD_REGEX

# For redirect, only codes 301, 302, 303, 307 and 308 are # supported.
SUPPORTED_L7POLICY_REDIRECT_HTTP_CODES = [301, 302, 303, 307, 308]

SUPPORTED_HTTP_VERSIONS = [1.0, 1.1]

MIN_POLICY_POSITION = 1
# Largest a 32-bit integer can be, which is a limitation
# here if you're using MySQL, as most probably are. This just needs
# to be larger than any existing rule position numbers which will
# definitely be the case with 2147483647
MAX_POLICY_POSITION = 2147483647

# Testing showed haproxy config failed to parse after more than
# 53 rules per policy
MAX_L7RULES_PER_L7POLICY = 50

# See RFCs 2616, 2965, 6265, 7230: Should match characters valid in a
# http header or cookie name.
HTTP_HEADER_NAME_REGEX = r'\A[a-zA-Z0-9!#$%&\'*+-.^_`|~]+\Z'

# See RFCs 2616, 2965, 6265: Should match characters valid in a cookie value.
HTTP_COOKIE_VALUE_REGEX = r'\A[a-zA-Z0-9!#$%&\'()*+-./:<=>?@[\]^_`{|}~]+\Z'

# See RFC 7230: Should match characters valid in a header value.
HTTP_HEADER_VALUE_REGEX = (r'\A[a-zA-Z0-9'
                           r'!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~\\]+\Z')

# Also in RFC 7230: Should match characters valid in a header value
# when quoted with double quotes.
HTTP_QUOTED_HEADER_VALUE_REGEX = (r'\A"[a-zA-Z0-9 \t'
                                  r'!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~\\]*"\Z')

DOMAIN_NAME_REGEX = (
    r'^(?=.{1,253}\.?$)(?:(?!-|[^.]+_)[A-Za-z0-9-_]{1,63}(?<!-)(?:\.|$))+$')

# TaskFlow
SUPPORTED_TASKFLOW_ENGINE_TYPES = [
    ('serial', 'Runs all tasks on a single thread'),
    ('parallel', 'Schedules tasks onto different threads to allow for running '
                 'non-dependent tasks simultaneously')]

# Task/Flow constants
ACCEPT = 'accept'
ACTIVE_CONNECTIONS = 'active_connections'
ADD_NICS = 'add_nics'
ADD_SUBNETS = 'add_subnets'
ADDITIONAL_VIPS = 'additional_vips'
ADMIN_STATE_UP = 'admin_state_up'
ALLOWED_ADDRESS_PAIRS = 'allowed_address_pairs'
AMP_DATA = 'amp_data'
AMP_VRRP_INT = 'amp_vrrp_int'
AMPHORA = 'amphora'
AMPHORA_DICT = 'amphora_dict'
AMPHORA_FIREWALL_RULES = 'amphora_firewall_rules'
AMPHORA_ID = 'amphora_id'
AMPHORA_INDEX = 'amphora_index'
AMPHORA_NETWORK_CONFIG = 'amphora_network_config'
AMPHORAE = 'amphorae'
AMPHORAE_NETWORK_CONFIG = 'amphorae_network_config'
AMPHORAE_STATUS = 'amphorae_status'
AMPS_DATA = 'amps_data'
ANTI_AFFINITY = 'anti-affinity'
ATTEMPT_NUMBER = 'attempt_number'
BASE_PORT = 'base_port'
BINDING_VNIC_TYPE = 'binding_vnic_type'
BUILD_AMP_DATA = 'build_amp_data'
BYTES_IN = 'bytes_in'
BYTES_OUT = 'bytes_out'
CACHED_ZONE = 'cached_zone'
CA_TLS_CERTIFICATE_ID = 'ca_tls_certificate_id'
CIDR = 'cidr'
CLIENT_CA_TLS_CERTIFICATE_ID = 'client_ca_tls_certificate_id'
CLIENT_CRL_CONTAINER_ID = 'client_crl_container_id'
CODE = 'code'
COMPUTE_ID = 'compute_id'
COMPUTE_OBJ = 'compute_obj'
COMPUTE_ZONE = 'compute_zone'
CONN_MAX_RETRIES = 'conn_max_retries'
CONN_RETRY_INTERVAL = 'conn_retry_interval'
CREATED_AT = 'created_at'
CRL_CONTAINER_ID = 'crl_container_id'
DEFAULT_TLS_CONTAINER_DATA = 'default_tls_container_data'
DELETE_NICS = 'delete_nics'
DELETE_SUBNETS = 'delete_subnets'
DELTA = 'delta'
DELTAS = 'deltas'
DESCRIPTION = 'description'
DESTINATION = 'destination'
DETAIL = 'detail'
DEVICE_OWNER = 'device_owner'
ENABLED = 'enabled'
ERRORS = 'errors'
FAILED_AMP_VRRP_PORT_ID = 'failed_amp_vrrp_port_id'
FAILED_AMPHORA = 'failed_amphora'
FAILOVER_AMPHORA = 'failover_amphora'
FAILOVER_AMPHORA_ID = 'failover_amphora_id'
FIELDS = 'fields'
FIXED_IPS = 'fixed_ips'
FLAVOR_ID = 'flavor_id'
GATEWAY_IP = 'gateway_ip'
HA_IP = 'ha_ip'
HA_PORT_ID = 'ha_port_id'
HEALTH_MON = 'health_mon'
HEALTH_MONITOR = 'health_monitor'
HEALTH_MONITOR_ID = 'health_monitor_id'
HEALTHMONITOR_ID = 'healthmonitor_id'
HEALTH_MONITOR_UPDATES = 'health_monitor_updates'
HOST_ROUTES = 'host_routes'
ID = 'id'
IMAGE_ID = 'image_id'
IP_ADDRESS = 'ip_address'
IPV6_ICMP = 'ipv6-icmp'
IS_SRIOV = 'is_sriov'
LB_NETWORK_IP = 'lb_network_ip'
L7POLICY = 'l7policy'
L7POLICY_ID = 'l7policy_id'
L7POLICY_UPDATES = 'l7policy_updates'
L7RULE = 'l7rule'
L7RULE_ID = 'l7rule_id'
L7RULE_UPDATES = 'l7rule_updates'
LISTENER = 'listener'
LISTENER_ID = 'listener_id'
LISTENER_UPDATES = 'listener_updates'
LOADBALANCER = 'loadbalancer'
LOADBALANCER_ID = 'loadbalancer_id'
LOAD_BALANCER_ID = 'load_balancer_id'
LOAD_BALANCER_UPDATES = 'load_balancer_updates'
MAC_ADDRESS = 'mac_address'
MANAGEMENT_NETWORK = 'management_network'
MEMBER = 'member'
MEMBER_ID = 'member_id'
MEMBER_PORTS = 'member_ports'
MEMBER_UPDATES = 'member_updates'
MESSAGE = 'message'
NAME = 'name'
NETWORK = 'network'
NETWORK_ID = 'network_id'
NEW_AMPHORAE = 'new_amphorae'
NEW_AMPHORA_ID = 'new_amphora_id'
NEXTHOP = 'nexthop'
NICS = 'nics'
OBJECT = 'object'
ORIGINAL_HEALTH_MONITOR = 'original_health_monitor'
ORIGINAL_L7POLICY = 'original_l7policy'
ORIGINAL_L7RULE = 'original_l7rule'
ORIGINAL_LISTENER = 'original_listener'
ORIGINAL_LOADBALANCER = 'original_load_balancer'
ORIGINAL_MEMBER = 'original_member'
ORIGINAL_POOL = 'original_pool'
PASSIVE_FAILURE = 'passive_failure'
PEER_PORT = 'peer_port'
POOL = 'pool'
POOL_CHILD_COUNT = 'pool_child_count'
POOL_ID = 'pool_id'
POOL_UPDATES = 'pool_updates'
PORT = 'port'
PORT_DATA = 'port_data'
PORT_ID = 'port_id'
PORTS = 'ports'
PROJECT_ID = 'project_id'
PROVIDER = 'provider'
PROVIDER_NAME = 'provider_name'
QOS_POLICY_ID = 'qos_policy_id'
REDIRECT_POOL = 'redirect_pool'
REQ_CONN_TIMEOUT = 'req_conn_timeout'
REQ_READ_TIMEOUT = 'req_read_timeout'
REQUEST_ERRORS = 'request_errors'
REQUEST_ID = 'request_id'
REQUEST_SRIOV = 'request_sriov'
ROLE = 'role'
SECURITY_GROUP_IDS = 'security_group_ids'
SECURITY_GROUPS = 'security_groups'
SECURITY_GROUP_RULES = 'security_group_rules'
SERVER_GROUP_ID = 'server_group_id'
SERVER_PEM = 'server_pem'
SG_IDS = 'sg_ids'
SG_ID = 'sg_id'
SNI_CONTAINER_DATA = 'sni_container_data'
SNI_CONTAINERS = 'sni_containers'
SOFT_ANTI_AFFINITY = 'soft-anti-affinity'
STATUS = 'status'
STATUS_CODE = 'status_code'
SUBNET = 'subnet'
SUBNET_ID = 'subnet_id'
TAGS = 'tags'
TENANT_ID = 'tenant_id'
TIMEOUT_DICT = 'timeout_dict'
TITLE = 'title'
TLS_CERTIFICATE_ID = 'tls_certificate_id'
TLS_CONTAINER_ID = 'tls_container_id'
TOPOLOGY = 'topology'
TOTAL_CONNECTIONS = 'total_connections'
UNREACHABLE = 'unreachable'
UPDATED_AT = 'updated_at'
UPDATE_DICT = 'update_dict'
UPDATED_PORTS = 'updated_ports'
VALID_VIP_NETWORKS = 'valid_vip_networks'
VIP = 'vip'
VIP_ADDRESS = 'vip_address'
VIP_NETWORK = 'vip_network'
VIP_NETWORK_ID = 'vip_network_id'
VIP_PORT_ID = 'vip_port_id'
VIP_QOS_POLICY_ID = 'vip_qos_policy_id'
VIP_SG_ID = 'vip_sg_id'
VIP_SUBNET = 'vip_subnet'
VIP_SUBNET_ID = 'vip_subnet_id'
VIP_VNIC_TYPE = 'vip_vnic_type'
VNIC_TYPE = 'vnic_type'
VNIC_TYPE_DIRECT = 'direct'
VNIC_TYPE_NORMAL = 'normal'
VRRP = 'vrrp'
VRRP_ID = 'vrrp_id'
VRRP_IP = 'vrrp_ip'
VRRP_GROUP = 'vrrp_group'
VRRP_PORT = 'vrrp_port'
VRRP_PORT_ID = 'vrrp_port_id'
VRRP_PRIORITY = 'vrrp_priority'

# Taskflow flow and task names
AMP_UPDATE_FW_SUBFLOW = 'amphora-update-firewall-subflow'
CERT_ROTATE_AMPHORA_FLOW = 'octavia-cert-rotate-amphora-flow'
CREATE_AMPHORA_FLOW = 'octavia-create-amphora-flow'
CREATE_AMPHORA_RETRY_SUBFLOW = 'octavia-create-amphora-retry-subflow'
CREATE_AMPHORA_FOR_LB_FLOW = 'octavia-create-amp-for-lb-flow'
CREATE_HEALTH_MONITOR_FLOW = 'octavia-create-health-monitor-flow'
CREATE_LISTENER_FLOW = 'octavia-create-listener_flow'
PRE_CREATE_LOADBALANCER_FLOW = 'octavia-pre-create-loadbalancer-flow'
CREATE_SERVER_GROUP_FLOW = 'octavia-create-server-group-flow'
UPDATE_LB_SERVERGROUPID_FLOW = 'octavia-update-lb-server-group-id-flow'
CREATE_LISTENERS_FLOW = 'octavia-create-all-listeners-flow'
CREATE_LOADBALANCER_FLOW = 'octavia-create-loadbalancer-flow'
CREATE_LOADBALANCER_GRAPH_FLOW = 'octavia-create-loadbalancer-graph-flow'
CREATE_MEMBER_FLOW = 'octavia-create-member-flow'
CREATE_POOL_FLOW = 'octavia-create-pool-flow'
CREATE_L7POLICY_FLOW = 'octavia-create-l7policy-flow'
CREATE_L7RULE_FLOW = 'octavia-create-l7rule-flow'
DELETE_AMPHORA_FLOW = 'octavia-delete-amphora-flow'
DELETE_EXTRA_AMPHORAE_FLOW = 'octavia-delete-extra-amphorae-flow'
DELETE_HEALTH_MONITOR_FLOW = 'octavia-delete-health-monitor-flow'
DELETE_LISTENER_FLOW = 'octavia-delete-listener_flow'
DELETE_LOADBALANCER_FLOW = 'octavia-delete-loadbalancer-flow'
DELETE_MEMBER_FLOW = 'octavia-delete-member-flow'
DELETE_POOL_FLOW = 'octavia-delete-pool-flow'
DELETE_L7POLICY_FLOW = 'octavia-delete-l7policy-flow'
DELETE_L7RULE_FLOW = 'octavia-delete-l7policy-flow'
FAILOVER_AMPHORA_FLOW = 'octavia-failover-amphora-flow'
FAILOVER_LOADBALANCER_FLOW = 'octavia-failover-loadbalancer-flow'
FINALIZE_AMPHORA_FLOW = 'octavia-finalize-amphora-flow'
FIREWALL_RULES_SUBFLOW = 'firewall-rules-subflow'
LOADBALANCER_NETWORKING_SUBFLOW = 'octavia-new-loadbalancer-net-subflow'
UPDATE_HEALTH_MONITOR_FLOW = 'octavia-update-health-monitor-flow'
UPDATE_LISTENER_FLOW = 'octavia-update-listener-flow'
UPDATE_LOADBALANCER_FLOW = 'octavia-update-loadbalancer-flow'
UPDATE_MEMBER_FLOW = 'octavia-update-member-flow'
UPDATE_POOL_FLOW = 'octavia-update-pool-flow'
UPDATE_L7POLICY_FLOW = 'octavia-update-l7policy-flow'
UPDATE_L7RULE_FLOW = 'octavia-update-l7rule-flow'
UPDATE_AMPS_SUBFLOW = 'octavia-update-amps-subflow'
UPDATE_AMPHORA_CONFIG_FLOW = 'octavia-update-amp-config-flow'

POST_MAP_AMP_TO_LB_SUBFLOW = 'octavia-post-map-amp-to-lb-subflow'
CREATE_AMP_FOR_LB_SUBFLOW = 'octavia-create-amp-for-lb-subflow'
CREATE_AMP_FOR_FAILOVER_SUBFLOW = 'octavia-create-amp-for-failover-subflow'
AMP_PLUG_NET_SUBFLOW = 'octavia-plug-net-subflow'
GET_AMPHORA_FOR_LB_SUBFLOW = 'octavia-get-amphora-for-lb-subflow'
POST_LB_AMP_ASSOCIATION_SUBFLOW = (
    'octavia-post-loadbalancer-amp_association-subflow')
AMPHORA_LISTENER_START_SUBFLOW = 'amphora-listener-start-subflow'
AMPHORA_LISTENER_RELOAD_SUBFLOW = 'amphora-listener-start-subflow'

MAP_LOADBALANCER_TO_AMPHORA = 'octavia-mapload-balancer-to-amphora'
RELOAD_AMPHORA = 'octavia-reload-amphora'
CREATE_AMPHORA_INDB = 'octavia-create-amphora-indb'
GENERATE_SERVER_PEM = 'octavia-generate-serverpem'
UPDATE_CERT_EXPIRATION = 'octavia-update-cert-expiration'
CERT_COMPUTE_CREATE = 'octavia-cert-compute-create'
COMPUTE_CREATE = 'octavia-compute-create'
COMPUTE_CREATE_RETRY_SUBFLOW = 'octavia-compute-create-retry-subflow'
UPDATE_AMPHORA_COMPUTEID = 'octavia-update-amphora-computeid'
MARK_AMPHORA_BOOTING_INDB = 'octavia-mark-amphora-booting-indb'
WAIT_FOR_AMPHORA = 'octavia-wait_for_amphora'
COMPUTE_WAIT = 'octavia-compute-wait'
UPDATE_AMPHORA_INFO = 'octavia-update-amphora-info'
AMPHORA_FINALIZE = 'octavia-amphora-finalize'
MARK_AMPHORA_ALLOCATED_INDB = 'octavia-mark-amphora-allocated-indb'
MARK_AMPHORA_READY_INDB = 'octavia-mark-amphora-ready-indb'
MARK_LB_ACTIVE_INDB = 'octavia-mark-lb-active-indb'
MARK_AMP_MASTER_INDB = 'octavia-mark-amp-master-indb'
MARK_AMP_BACKUP_INDB = 'octavia-mark-amp-backup-indb'
MARK_AMP_STANDALONE_INDB = 'octavia-mark-amp-standalone-indb'
GET_VRRP_SUBFLOW = 'octavia-get-vrrp-subflow'
AMP_VRRP_UPDATE = 'octavia-amphora-vrrp-update'
AMP_VRRP_START = 'octavia-amphora-vrrp-start'
AMP_VRRP_STOP = 'octavia-amphora-vrrp-stop'
AMP_UPDATE_VRRP_INTF = 'octavia-amphora-update-vrrp-intf'
CREATE_VRRP_GROUP_FOR_LB = 'octavia-create-vrrp-group-for-lb'
CREATE_VRRP_SECURITY_RULES = 'octavia-create-vrrp-security-rules'
AMP_COMPUTE_CONNECTIVITY_WAIT = 'octavia-amp-compute-connectivity-wait'
AMP_LISTENER_UPDATE = 'octavia-amp-listeners-update'
AMP_LISTENER_START = 'octavia-amp-listeners-start'
PLUG_VIP_AMPHORA = 'octavia-amp-plug-vip'
APPLY_QOS_AMP = 'octavia-amp-apply-qos'
UPDATE_AMPHORA_VIP_DATA = 'ocatvia-amp-update-vip-data'
GET_AMP_NETWORK_CONFIG = 'octavia-amp-get-network-config'
AMP_POST_VIP_PLUG = 'octavia-amp-post-vip-plug'
GENERATE_SERVER_PEM_TASK = 'GenerateServerPEMTask'
AMPHORA_CONFIG_UPDATE_TASK = 'AmphoraConfigUpdateTask'
FIRST_AMP_NETWORK_CONFIGS = 'first-amp-network-configs'
FIRST_AMP_VRRP_INTERFACE = 'first-amp-vrrp_interface'

# Batch Member Update constants
UNORDERED_MEMBER_UPDATES_FLOW = 'octavia-unordered-member-updates-flow'
UNORDERED_MEMBER_ACTIVE_FLOW = 'octavia-unordered-member-active-flow'
UPDATE_ATTRIBUTES_FLOW = 'octavia-update-attributes-flow'
DELETE_MODEL_OBJECT_FLOW = 'octavia-delete-model-object-flow'
BATCH_UPDATE_MEMBERS_FLOW = 'octavia-batch-update-members-flow'
MEMBER_TO_ERROR_ON_REVERT_FLOW = 'octavia-member-to-error-on-revert-flow'
DECREMENT_MEMBER_QUOTA_FLOW = 'octavia-decrement-member-quota-flow'
MARK_MEMBER_ACTIVE_INDB = 'octavia-mark-member-active-indb'
UPDATE_MEMBER_INDB = 'octavia-update-member-indb'
DELETE_MEMBER_INDB = 'octavia-delete-member-indb'

# Task Names
ADMIN_DOWN_PORT = 'admin-down-port'
AMPHORA_POST_VIP_PLUG = 'amphora-post-vip-plug'
AMPHORA_RELOAD_LISTENER = 'amphora-reload-listener'
AMPHORA_TO_AMPHORAE_VRRP_IP = 'amphora-to-amphorae-vrrp-ip'
AMPHORA_TO_ERROR_ON_REVERT = 'amphora-to-error-on-revert'
AMPHORAE_GET_CONNECTIVITY_STATUS = 'amphorae-get-connectivity-status'
AMPHORAE_POST_NETWORK_PLUG = 'amphorae-post-network-plug'
ATTACH_PORT = 'attach-port'
CALCULATE_AMPHORA_DELTA = 'calculate-amphora-delta'
CREATE_VIP_BASE_PORT = 'create-vip-base-port'
DELETE_AMPHORA = 'delete-amphora'
DELETE_AMPHORA_MEMBER_PORTS = 'delete-amphora-member-ports'
DELETE_PORT = 'delete-port'
DISABLE_AMP_HEALTH_MONITORING = 'disable-amphora-health-monitoring'
GET_AMPHORA_FIREWALL_RULES = 'get-amphora-firewall-rules'
GET_AMPHORA_NETWORK_CONFIGS_BY_ID = 'get-amphora-network-configs-by-id'
GET_AMPHORAE_FROM_LB = 'get-amphorae-from-lb'
GET_SUBNET_FROM_VIP = 'get-subnet-from-vip'
HANDLE_NETWORK_DELTA = 'handle-network-delta'
MARK_AMPHORA_DELETED = 'mark-amphora-deleted'
MARK_AMPHORA_PENDING_DELETE = 'mark-amphora-pending-delete'
MARK_AMPHORA_HEALTH_BUSY = 'mark-amphora-health-busy'
RELOAD_AMP_AFTER_PLUG_VIP = 'reload-amp-after-plug-vip'
RELOAD_LB_AFTER_AMP_ASSOC = 'reload-lb-after-amp-assoc'
RELOAD_LB_AFTER_AMP_ASSOC_FULL_GRAPH = 'reload-lb-after-amp-assoc-full-graph'
RELOAD_LB_AFTER_PLUG_VIP = 'reload-lb-after-plug-vip'
RELOAD_LB_BEFOR_ALLOCATE_VIP = 'reload-lb-before-allocate-vip'
SET_AMPHORA_FIREWALL_RULES = 'set-amphora-firewall-rules'
UPDATE_AMP_FAILOVER_DETAILS = 'update-amp-failover-details'


NOVA_1 = '1.1'
NOVA_21 = '2.1'
NOVA_3 = '3'
NOVA_VERSIONS = (NOVA_1, NOVA_21, NOVA_3)

# Auth sections
SERVICE_AUTH = 'service_auth'

RPC_NAMESPACE_CONTROLLER_AGENT = 'controller'

# Build Type Priority
LB_CREATE_FAILOVER_PRIORITY = 20
LB_CREATE_NORMAL_PRIORITY = 40
LB_CREATE_ADMIN_FAILOVER_PRIORITY = 80
BUILD_TYPE_PRIORITY = 'build_type_priority'

# Active standalone roles and topology
TOPOLOGY_SINGLE = 'SINGLE'
TOPOLOGY_ACTIVE_STANDBY = 'ACTIVE_STANDBY'
ROLE_MASTER = 'MASTER'
ROLE_BACKUP = 'BACKUP'
ROLE_STANDALONE = 'STANDALONE'

SUPPORTED_LB_TOPOLOGIES = (TOPOLOGY_ACTIVE_STANDBY, TOPOLOGY_SINGLE)
SUPPORTED_AMPHORA_ROLES = (ROLE_BACKUP, ROLE_MASTER, ROLE_STANDALONE)

TOPOLOGY_STATUS_OK = 'OK'

ROLE_MASTER_PRIORITY = 100
ROLE_BACKUP_PRIORITY = 90

VRRP_AUTH_DEFAULT = 'PASS'
VRRP_AUTH_AH = 'AH'
SUPPORTED_VRRP_AUTH = (VRRP_AUTH_DEFAULT, VRRP_AUTH_AH)

KEEPALIVED_CMD = '/usr/sbin/keepalived '
# The DEFAULT_VRRP_ID value needs to be variable for multi tenant support
# per amphora in the future
DEFAULT_VRRP_ID = 1
VRRP_PROTOCOL_NUM = 112
AUTH_HEADER_PROTOCOL_NUMBER = 51

TEMPLATES = '/templates'
AGENT_API_TEMPLATES = '/templates'
LOGGING_TEMPLATES = '/templates'

AGENT_CONF_TEMPLATE = 'amphora_agent_conf.template'
LOGGING_CONF_TEMPLATE = '10-rsyslog.conf.template'
USER_DATA_CONFIG_DRIVE_TEMPLATE = 'user_data_config_drive.template'

OPEN = 'OPEN'
FULL = 'FULL'

# OPEN = HAProxy listener status nbconn < maxconn
# FULL = HAProxy listener status not nbconn < maxconn
HAPROXY_LISTENER_STATUSES = (OPEN, FULL)

UP = 'UP'
DOWN = 'DOWN'

# UP = HAProxy backend has working or no servers
# DOWN = HAProxy backend has no working servers
HAPROXY_BACKEND_STATUSES = (UP, DOWN)


DRAIN = 'DRAIN'
MAINT = 'MAINT'
NO_CHECK = 'no check'

# DRAIN = member is weight 0 and is in draining mode
# MAINT = member is downed for maintenance? not sure when this happens
# NO_CHECK = no health monitor is enabled
HAPROXY_MEMBER_STATUSES = (UP, DOWN, DRAIN, MAINT, NO_CHECK)

# Default number of concurrent connections in a HAProxy listener.
HAPROXY_DEFAULT_MAXCONN = 50000

# Current maximum number of conccurent connections in HAProxy.
# This is limited by the systemd "LimitNOFILE" and
# the sysctl fs.file-max fs.nr_open settings in the image
HAPROXY_MAX_MAXCONN = 1000000

RESTARTING = 'RESTARTING'

# Quota Constants
QUOTA_UNLIMITED = -1
MIN_QUOTA = QUOTA_UNLIMITED
MAX_QUOTA = 2000000000

HAPROXY_BASE_PEER_PORT = 1025
KEEPALIVED_JINJA2_SYSTEMD = 'keepalived.systemd.j2'
CHECK_SCRIPT_CONF = 'keepalived_check_script.conf.j2'
KEEPALIVED_CHECK_SCRIPT = 'keepalived_lvs_check_script.sh.j2'

PLUGGED_INTERFACES = '/var/lib/octavia/plugged_interfaces'
HAPROXY_USER_GROUP_CFG = '/var/lib/octavia/haproxy-default-user-group.conf'
AMPHORA_NAMESPACE = 'amphora-haproxy'

FLOW_DOC_TITLES = {'AmphoraFlows': 'Amphora Flows',
                   'LoadBalancerFlows': 'Load Balancer Flows',
                   'ListenerFlows': 'Listener Flows',
                   'PoolFlows': 'Pool Flows',
                   'MemberFlows': 'Member Flows',
                   'HealthMonitorFlows': 'Health Monitor Flows',
                   'L7PolicyFlows': 'Layer 7 Policy Flows',
                   'L7RuleFlows': 'Layer 7 Rule Flows'}

NETNS_PRIMARY_INTERFACE = 'eth1'
SYSCTL_CMD = '/sbin/sysctl'

AMP_ACTION_START = 'start'
AMP_ACTION_STOP = 'stop'
AMP_ACTION_RELOAD = 'reload'
AMP_ACTION_RESTART = 'restart'
GLANCE_IMAGE_ACTIVE = 'active'

INIT_PATH = '/sbin/init'

SYSTEMD_DIR = '/usr/lib/systemd/system'

INIT_PROC_COMM_PATH = '/proc/1/comm'

LOADBALANCER_SYSTEMD = 'haproxy-%s.service'

KEEPALIVED_SYSTEMD = 'octavia-keepalived.service'

KEEPALIVEDLVS_SYSTEMD = 'octavia-keepalivedlvs-%s.service'

# Authentication
KEYSTONE = 'keystone'
NOAUTH = 'noauth'
TESTING = 'testing'

# Amphora distro-specific data
UBUNTU = 'ubuntu'
CENTOS = 'centos'

# Pagination, sorting, filtering values
APPLICATION_JSON = 'application/json'
PAGINATION_HELPER = 'pagination_helper'
ASC = 'asc'
DESC = 'desc'
ALLOWED_SORT_DIR = (ASC, DESC)
DEFAULT_SORT_DIR = ASC
DEFAULT_SORT_KEYS = ['created_at', 'id']
DEFAULT_PAGE_SIZE = 1000

# RBAC
LOADBALANCER_API = 'os_load-balancer_api'

RULE_API_ADMIN = 'rule:load-balancer:admin'
RULE_API_READ = 'rule:load-balancer:read'
RULE_API_READ_GLOBAL = 'rule:load-balancer:read-global'
RULE_API_WRITE = 'rule:load-balancer:write'
RULE_API_READ_QUOTA = 'rule:load-balancer:read-quota'
RULE_API_READ_QUOTA_GLOBAL = 'rule:load-balancer:read-quota-global'
RULE_API_WRITE_QUOTA = 'rule:load-balancer:write-quota'

RBAC_LOADBALANCER = f'{LOADBALANCER_API}:loadbalancer:'
RBAC_LISTENER = f'{LOADBALANCER_API}:listener:'
RBAC_POOL = f'{LOADBALANCER_API}:pool:'
RBAC_MEMBER = f'{LOADBALANCER_API}:member:'
RBAC_HEALTHMONITOR = f'{LOADBALANCER_API}:healthmonitor:'
RBAC_L7POLICY = f'{LOADBALANCER_API}:l7policy:'
RBAC_L7RULE = f'{LOADBALANCER_API}:l7rule:'
RBAC_QUOTA = f'{LOADBALANCER_API}:quota:'
RBAC_AMPHORA = f'{LOADBALANCER_API}:amphora:'
RBAC_PROVIDER = f'{LOADBALANCER_API}:provider:'
RBAC_PROVIDER_FLAVOR = f'{LOADBALANCER_API}:provider-flavor:'
RBAC_PROVIDER_AVAILABILITY_ZONE = (f'{LOADBALANCER_API}:'
                                   f'provider-availability-zone:')
RBAC_FLAVOR = f'{LOADBALANCER_API}:flavor:'
RBAC_FLAVOR_PROFILE = f'{LOADBALANCER_API}:flavor-profile:'
RBAC_AVAILABILITY_ZONE = f'{LOADBALANCER_API}:availability-zone:'
RBAC_AVAILABILITY_ZONE_PROFILE = (f'{LOADBALANCER_API}:'
                                  f'availability-zone-profile:')

RBAC_POST = 'post'
RBAC_PUT = 'put'
RBAC_PUT_CONFIG = 'put_config'
RBAC_PUT_FAILOVER = 'put_failover'
RBAC_DELETE = 'delete'
RBAC_GET_ONE = 'get_one'
RBAC_GET_ALL = 'get_all'
RBAC_GET_ALL_GLOBAL = 'get_all-global'
RBAC_GET_DEFAULTS = 'get_defaults'
RBAC_GET_STATS = 'get_stats'
RBAC_GET_STATUS = 'get_status'

RBAC_SCOPE_PROJECT = 'project'
RBAC_SCOPE_SYSTEM = 'system'

RBAC_ROLES_DEPRECATED_REASON = (
    'The Octavia API now requires the OpenStack default roles and scoped '
    'tokens. '
    'See https://docs.openstack.org/octavia/latest/configuration/policy.html '
    'and https://docs.openstack.org/keystone/latest/contributor/'
    'services.html#reusable-default-roles for more information.')

# PROVIDERS
OCTAVIA = 'octavia'
AMPHORAV2 = 'amphorav2'

# systemctl commands
DISABLE = 'disable'
ENABLE = 'enable'
STOP = 'stop'
START = 'start'
RESTART = 'restart'
RELOAD = 'reload'

# systemd amphora netns service prefix
AMP_NETNS_SVC_PREFIX = 'amphora-netns'

# Amphora Feature Compatibility
HTTP_REUSE = 'has_http_reuse'
SERVER_STATE_FILE = 'has_server_state_file'
POOL_ALPN = 'has_pool_alpn'
INSECURE_FORK = 'requires_insecure_fork'

# TODO(johnsom) convert these to octavia_lib constants
# once octavia is transitioned to use octavia_lib
FLAVOR = 'flavor'
FLAVOR_DATA = 'flavor_data'
AVAILABILITY_ZONE = 'availability_zone'
AVAILABILITY_ZONE_DATA = 'availability_zone_data'

# Flavor metadata
LOADBALANCER_TOPOLOGY = 'loadbalancer_topology'
COMPUTE_FLAVOR = 'compute_flavor'
AMP_IMAGE_TAG = 'amp_image_tag'

# TODO(johnsom) move to octavia_lib
# client certification authorization option
CLIENT_AUTH_NONE = 'NONE'
CLIENT_AUTH_OPTIONAL = 'OPTIONAL'
CLIENT_AUTH_MANDATORY = 'MANDATORY'
SUPPORTED_CLIENT_AUTH_MODES = [CLIENT_AUTH_NONE, CLIENT_AUTH_OPTIONAL,
                               CLIENT_AUTH_MANDATORY]

TOPIC_AMPHORA_V2 = 'octavia_provisioning_v2'

HAPROXY_HTTP_PROTOCOLS = [lib_consts.PROTOCOL_HTTP,
                          lib_consts.PROTOCOL_TERMINATED_HTTPS]

LVS_PROTOCOLS = [PROTOCOL_UDP,
                 lib_consts.PROTOCOL_SCTP]

HAPROXY_BACKEND = 'HAPROXY'
LVS_BACKEND = 'LVS'

# Map each supported protocol to its L4 protocol
L4_PROTOCOL_MAP = {
    PROTOCOL_TCP: PROTOCOL_TCP,
    PROTOCOL_HTTP: PROTOCOL_TCP,
    PROTOCOL_HTTPS: PROTOCOL_TCP,
    PROTOCOL_TERMINATED_HTTPS: PROTOCOL_TCP,
    PROTOCOL_PROXY: PROTOCOL_TCP,
    lib_consts.PROTOCOL_PROXYV2: PROTOCOL_TCP,
    PROTOCOL_UDP: PROTOCOL_UDP,
    lib_consts.PROTOCOL_SCTP: lib_consts.PROTOCOL_SCTP,
    lib_consts.PROTOCOL_PROMETHEUS: lib_consts.PROTOCOL_TCP,
}

# Image drivers
SUPPORTED_IMAGE_DRIVERS = ['image_noop_driver',
                           'image_glance_driver']

# Volume drivers
VOLUME_NOOP_DRIVER = 'volume_noop_driver'
SUPPORTED_VOLUME_DRIVERS = [VOLUME_NOOP_DRIVER,
                            'volume_cinder_driver']

# Cinder volume driver constants
CINDER_STATUS_AVAILABLE = 'available'
CINDER_STATUS_ERROR = 'error'
CINDER_ACTION_CREATE_VOLUME = 'create volume'

# The nil UUID (used in octavia for deleted references) - RFC 4122
NIL_UUID = '00000000-0000-0000-0000-000000000000'

# OpenSSL cipher strings
CIPHERS_OWASP_SUITE_B = ('TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:'
                         'TLS_AES_128_GCM_SHA256:DHE-RSA-AES256-GCM-SHA384:'
                         'DHE-RSA-AES128-GCM-SHA256:'
                         'ECDHE-RSA-AES256-GCM-SHA384:'
                         'ECDHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-SHA256:'
                         'DHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384:'
                         'ECDHE-RSA-AES128-SHA256')

TLS_VERSIONS_OWASP_SUITE_B = [lib_consts.TLS_VERSION_1_2,
                              lib_consts.TLS_VERSION_1_3]

# All supported TLS versions in ascending order (oldest to newest)
TLS_ALL_VERSIONS = [
    lib_consts.SSL_VERSION_3,
    lib_consts.TLS_VERSION_1,
    lib_consts.TLS_VERSION_1_1,
    lib_consts.TLS_VERSION_1_2,
    lib_consts.TLS_VERSION_1_3
]

VIP_SECURITY_GROUP_PREFIX = 'lb-'

AMP_BASE_PORT_PREFIX = 'octavia-lb-vrrp-'
OCTAVIA_OWNED = 'octavia_owned'
OCTAVIA_OWNER = 'Octavia'

# Sadly in the LBaaS v2 API, header insertions are on the listener objects
# but they should be on the pool. Dealing with it until v3.
LISTENER_PROTOCOLS_SUPPORTING_HEADER_INSERTION = [PROTOCOL_HTTP,
                                                  PROTOCOL_TERMINATED_HTTPS]

SUPPORTED_ALPN_PROTOCOLS = [lib_consts.ALPN_PROTOCOL_HTTP_2,
                            lib_consts.ALPN_PROTOCOL_HTTP_1_1,
                            lib_consts.ALPN_PROTOCOL_HTTP_1_0]

AMPHORA_SUPPORTED_ALPN_PROTOCOLS = [lib_consts.ALPN_PROTOCOL_HTTP_2,
                                    lib_consts.ALPN_PROTOCOL_HTTP_1_1,
                                    lib_consts.ALPN_PROTOCOL_HTTP_1_0]

SRIOV_VIP = 'sriov_vip'
ALLOW_MEMBER_SRIOV = 'allow_member_sriov'

# Amphora interface fields
IF_TYPE = 'if_type'
BACKEND = 'backend'
LO = 'lo'
MTU = 'mtu'
ADDRESSES = 'addresses'
ROUTES = 'routes'
RULES = 'rules'
SCRIPTS = 'scripts'

# pyroute2 fields
STATE = 'state'

FAMILY = 'family'
ADDRESS = 'address'
PREFIXLEN = 'prefixlen'
DHCP = 'dhcp'
IPV6AUTO = 'ipv6auto'

DST = 'dst'
PREFSRC = 'prefsrc'
GATEWAY = 'gateway'
FLAGS = 'flags'
ONLINK = 'onlink'
TABLE = 'table'
SCOPE = 'scope'

SRC = 'src'
SRC_LEN = 'src_len'

IFACE_UP = 'up'
IFACE_DOWN = 'down'

COMMAND = 'command'

IFLA_ADDRESS = 'IFLA_ADDRESS'
IFLA_IFNAME = 'IFLA_IFNAME'

# Amphora network directory
AMP_NET_DIR_TEMPLATE = '/etc/octavia/interfaces/'

# Amphora nftables constants
NFT_ADD = 'add'
NFT_CMD = '/usr/sbin/nft'
NFT_FAMILY = 'inet'
NFT_RULES_FILE = '/var/lib/octavia/nftables-vip.rules'
NFT_TABLE = 'amphora_table'
NFT_CHAIN = 'amphora_chain'
NFT_VIP_CHAIN = 'amphora_vip_chain'
PROTOCOL = 'protocol'
