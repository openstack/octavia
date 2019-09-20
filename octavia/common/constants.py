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

# 'provisioning_status'
PROVISIONING_STATUS = lib_consts.PROVISIONING_STATUS
# Amphora has been allocated to a load balancer 'ALLOCATED'
AMPHORA_ALLOCATED = lib_consts.AMPHORA_ALLOCATED
# Amphora is being built 'BOOTING'
AMPHORA_BOOTING = lib_consts.AMPHORA_BOOTING
# Amphora is ready to be allocated to a load balancer 'READY'
AMPHORA_READY = lib_consts.AMPHORA_READY
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

# 1 year:     y     d    h    m    ms
MAX_TIMEOUT = 365 * 24 * 60 * 60 * 1000
MIN_TIMEOUT = 0

DEFAULT_TIMEOUT_CLIENT_DATA = 50000
DEFAULT_TIMEOUT_MEMBER_CONNECT = 5000
DEFAULT_TIMEOUT_MEMBER_DATA = 50000
DEFAULT_TIMEOUT_TCP_INSPECT = 0

MUTABLE_STATUSES = (lib_consts.ACTIVE,)
DELETABLE_STATUSES = (lib_consts.ACTIVE, lib_consts.ERROR)
FAILOVERABLE_STATUSES = (lib_consts.ACTIVE, lib_consts.ERROR)

# Note: The database Amphora table has a foreign key constraint against
#       the provisioning_status table
SUPPORTED_AMPHORA_STATUSES = (
    lib_consts.AMPHORA_ALLOCATED, lib_consts.AMPHORA_BOOTING, lib_consts.ERROR,
    lib_consts.AMPHORA_READY, lib_consts.DELETED, lib_consts.PENDING_CREATE,
    lib_consts.PENDING_DELETE)

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

# Task/Flow constants
AMPHORA = 'amphora'
FAILED_AMPHORA = 'failed_amphora'
FAILOVER_AMPHORA = 'failover_amphora'
AMPHORAE = 'amphorae'
AMPHORA_ID = 'amphora_id'
AMPHORA_INDEX = 'amphora_index'
FAILOVER_AMPHORA_ID = 'failover_amphora_id'
DELTA = 'delta'
DELTAS = 'deltas'
HEALTH_MON = 'health_mon'
HEALTH_MONITOR = 'health_monitor'
LISTENER = 'listener'
LISTENER_ID = 'listener_id'
LOADBALANCER = 'loadbalancer'
LOADBALANCER_ID = 'loadbalancer_id'
LOAD_BALANCER_ID = 'load_balancer_id'
SERVER_GROUP_ID = 'server_group_id'
ANTI_AFFINITY = 'anti-affinity'
SOFT_ANTI_AFFINITY = 'soft-anti-affinity'
MEMBER = 'member'
MEMBER_ID = 'member_id'
COMPUTE_ID = 'compute_id'
COMPUTE_OBJ = 'compute_obj'
AMP_DATA = 'amp_data'
AMPS_DATA = 'amps_data'
NICS = 'nics'
VIP = 'vip'
POOL = 'pool'
POOL_CHILD_COUNT = 'pool_child_count'
POOL_ID = 'pool_id'
L7POLICY = 'l7policy'
L7RULE = 'l7rule'
OBJECT = 'object'
SERVER_PEM = 'server_pem'
UPDATE_DICT = 'update_dict'
VIP_NETWORK = 'vip_network'
AMPHORA_NETWORK_CONFIG = 'amphora_network_config'
AMPHORAE_NETWORK_CONFIG = 'amphorae_network_config'
ADDED_PORTS = 'added_ports'
PORTS = 'ports'
MEMBER_PORTS = 'member_ports'
TOPOLOGY = 'topology'
HEALTH_MONITOR_ID = 'health_monitor_id'
L7POLICY_ID = 'l7policy_id'
L7RULE_ID = 'l7rule_id'
LOAD_BALANCER_UPDATES = 'load_balancer_updates'
LISTENER_UPDATES = 'listener_updates'
POOL_UPDATES = 'pool_updates'
MEMBER_UPDATES = 'member_updates'
HEALTH_MONITOR_UPDATES = 'health_monitor_updates'
L7POLICY_UPDATES = 'l7policy_updates'
L7RULE_UPDATES = 'l7rule_updates'
TIMEOUT_DICT = 'timeout_dict'
REQ_CONN_TIMEOUT = 'req_conn_timeout'
REQ_READ_TIMEOUT = 'req_read_timeout'
CONN_MAX_RETRIES = 'conn_max_retries'
CONN_RETRY_INTERVAL = 'conn_retry_interval'
SUBNET = 'subnet'
AMP_DATA = 'amp_data'
ACTIVE_CONNECTIONS = 'active_connections'
BYTES_IN = 'bytes_in'
BYTES_OUT = 'bytes_out'
REQUEST_ERRORS = 'request_errors'
TOTAL_CONNECTIONS = 'total_connections'
NAME = 'name'
PROVIDER_NAME = 'provider_name'

CERT_ROTATE_AMPHORA_FLOW = 'octavia-cert-rotate-amphora-flow'
CREATE_AMPHORA_FLOW = 'octavia-create-amphora-flow'
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
DELETE_HEALTH_MONITOR_FLOW = 'octavia-delete-health-monitor-flow'
DELETE_LISTENER_FLOW = 'octavia-delete-listener_flow'
DELETE_LOADBALANCER_FLOW = 'octavia-delete-loadbalancer-flow'
DELETE_MEMBER_FLOW = 'octavia-delete-member-flow'
DELETE_POOL_FLOW = 'octavia-delete-pool-flow'
DELETE_L7POLICY_FLOW = 'octavia-delete-l7policy-flow'
DELETE_L7RULE_FLOW = 'octavia-delete-l7policy-flow'
FAILOVER_AMPHORA_FLOW = 'octavia-failover-amphora-flow'
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
AMP_PLUG_NET_SUBFLOW = 'octavia-plug-net-subflow'
GET_AMPHORA_FOR_LB_SUBFLOW = 'octavia-get-amphora-for-lb-subflow'
POST_LB_AMP_ASSOCIATION_SUBFLOW = (
    'octavia-post-loadbalancer-amp_association-subflow')

MAP_LOADBALANCER_TO_AMPHORA = 'octavia-mapload-balancer-to-amphora'
RELOAD_AMPHORA = 'octavia-reload-amphora'
CREATE_AMPHORA_INDB = 'octavia-create-amphora-indb'
GENERATE_SERVER_PEM = 'octavia-generate-serverpem'
UPDATE_CERT_EXPIRATION = 'octavia-update-cert-expiration'
CERT_COMPUTE_CREATE = 'octavia-cert-compute-create'
COMPUTE_CREATE = 'octavia-compute-create'
UPDATE_AMPHORA_COMPUTEID = 'octavia-update-amphora-computeid'
MARK_AMPHORA_BOOTING_INDB = 'octavia-mark-amphora-booting-indb'
WAIT_FOR_AMPHORA = 'octavia-wait_for_amphora'
COMPUTE_WAIT = 'octavia-compute-wait'
UPDATE_AMPHORA_INFO = 'octavia-update-amphora-info'
AMPHORA_FINALIZE = 'octavia-amphora-finalize'
MARK_AMPHORA_ALLOCATED_INDB = 'octavia-mark-amphora-allocated-indb'
RELOADLOAD_BALANCER = 'octavia-reloadload-balancer'
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
PLUG_VIP_AMPHORA = 'octavia-amp-plug-vip'
APPLY_QOS_AMP = 'octavia-amp-apply-qos'
UPDATE_AMPHORA_VIP_DATA = 'ocatvia-amp-update-vip-data'
GET_AMP_NETWORK_CONFIG = 'octavia-amp-get-network-config'
AMP_POST_VIP_PLUG = 'octavia-amp-post-vip-plug'
GENERATE_SERVER_PEM_TASK = 'GenerateServerPEMTask'
AMPHORA_CONFIG_UPDATE_TASK = 'AmphoraConfigUpdateTask'

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
RELOAD_AMP_AFTER_PLUG_VIP = 'reload-amp-after-plug-vip'
RELOAD_LB_AFTER_AMP_ASSOC = 'reload-lb-after-amp-assoc'
RELOAD_LB_AFTER_AMP_ASSOC_FULL_GRAPH = 'reload-lb-after-amp-assoc-full-graph'
RELOAD_LB_AFTER_PLUG_VIP = 'reload-lb-after-plug-vip'
RELOAD_LB_BEFOR_ALLOCATE_VIP = "reload-lb-before-allocate-vip"

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
LB_CREATE_SPARES_POOL_PRIORITY = 60
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

AGENT_CONF_TEMPLATE = 'amphora_agent_conf.template'
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

# Current maximum number of conccurent connections in HAProxy.
# This is limited by the systemd "LimitNOFILE" and
# the sysctl fs.file-max fs.nr_open settings in the image
HAPROXY_MAX_MAXCONN = 1000000

# Quota Constants
QUOTA_UNLIMITED = -1
MIN_QUOTA = QUOTA_UNLIMITED
MAX_QUOTA = 2000000000

API_VERSION = '0.5'

NOOP_EVENT_STREAMER = 'noop_event_streamer'

HAPROXY_BASE_PEER_PORT = 1025
KEEPALIVED_JINJA2_UPSTART = 'keepalived.upstart.j2'
KEEPALIVED_JINJA2_SYSTEMD = 'keepalived.systemd.j2'
KEEPALIVED_JINJA2_SYSVINIT = 'keepalived.sysvinit.j2'
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

INIT_SYSTEMD = 'systemd'
INIT_UPSTART = 'upstart'
INIT_SYSVINIT = 'sysvinit'
INIT_UNKOWN = 'unknown'
VALID_INIT_SYSTEMS = (INIT_SYSTEMD, INIT_SYSVINIT, INIT_UPSTART)
INIT_PATH = '/sbin/init'

SYSTEMD_DIR = '/usr/lib/systemd/system'
SYSVINIT_DIR = '/etc/init.d'
UPSTART_DIR = '/etc/init'

INIT_PROC_COMM_PATH = '/proc/1/comm'

KEEPALIVED_SYSTEMD = 'octavia-keepalived.service'
KEEPALIVED_SYSVINIT = 'octavia-keepalived'
KEEPALIVED_UPSTART = 'octavia-keepalived.conf'

KEEPALIVED_SYSTEMD_PREFIX = 'octavia-keepalivedlvs-%s.service'
KEEPALIVED_SYSVINIT_PREFIX = 'octavia-keepalivedlvs-%s'
KEEPALIVED_UPSTART_PREFIX = 'octavia-keepalivedlvs-%s.conf'

# Authentication
KEYSTONE = 'keystone'
NOAUTH = 'noauth'
TESTING = 'testing'

# Amphora distro-specific data
UBUNTU_AMP_NET_DIR_TEMPLATE = '/etc/netns/{netns}/network/interfaces.d/'
RH_AMP_NET_DIR_TEMPLATE = '/etc/netns/{netns}/sysconfig/network-scripts/'
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
RBAC_LOADBALANCER = '{}:loadbalancer:'.format(LOADBALANCER_API)
RBAC_LISTENER = '{}:listener:'.format(LOADBALANCER_API)
RBAC_POOL = '{}:pool:'.format(LOADBALANCER_API)
RBAC_MEMBER = '{}:member:'.format(LOADBALANCER_API)
RBAC_HEALTHMONITOR = '{}:healthmonitor:'.format(LOADBALANCER_API)
RBAC_L7POLICY = '{}:l7policy:'.format(LOADBALANCER_API)
RBAC_L7RULE = '{}:l7rule:'.format(LOADBALANCER_API)
RBAC_QUOTA = '{}:quota:'.format(LOADBALANCER_API)
RBAC_AMPHORA = '{}:amphora:'.format(LOADBALANCER_API)
RBAC_PROVIDER = '{}:provider:'.format(LOADBALANCER_API)
RBAC_PROVIDER_FLAVOR = '{}:provider-flavor:'.format(LOADBALANCER_API)
RBAC_FLAVOR = '{}:flavor:'.format(LOADBALANCER_API)
RBAC_FLAVOR_PROFILE = '{}:flavor-profile:'.format(LOADBALANCER_API)
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

# PROVIDERS
OCTAVIA = 'octavia'

# systemctl commands
DISABLE = 'disable'
ENABLE = 'enable'

# systemd amphora netns service prefix
AMP_NETNS_SVC_PREFIX = 'amphora-netns'

# Amphora Feature Compatibility
HTTP_REUSE = 'has_http_reuse'

# TODO(johnsom) convert this to octavia_lib constant flavor
# once octavia is transitioned to use octavia_lib
FLAVOR = 'flavor'
FLAVOR_DATA = 'flavor_data'

# Flavor metadata
LOADBALANCER_TOPOLOGY = 'loadbalancer_topology'
COMPUTE_FLAVOR = 'compute_flavor'

# TODO(johnsom) move to octavia_lib
# client certification authorization option
CLIENT_AUTH_NONE = 'NONE'
CLIENT_AUTH_OPTIONAL = 'OPTIONAL'
CLIENT_AUTH_MANDATORY = 'MANDATORY'
SUPPORTED_CLIENT_AUTH_MODES = [CLIENT_AUTH_NONE, CLIENT_AUTH_OPTIONAL,
                               CLIENT_AUTH_MANDATORY]
