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

LB_ALGORITHM_ROUND_ROBIN = 'ROUND_ROBIN'
LB_ALGORITHM_LEAST_CONNECTIONS = 'LEAST_CONNECTIONS'
LB_ALGORITHM_SOURCE_IP = 'SOURCE_IP'
SUPPORTED_LB_ALGORITHMS = (LB_ALGORITHM_LEAST_CONNECTIONS,
                           LB_ALGORITHM_ROUND_ROBIN,
                           LB_ALGORITHM_SOURCE_IP)

SESSION_PERSISTENCE_SOURCE_IP = 'SOURCE_IP'
SESSION_PERSISTENCE_HTTP_COOKIE = 'HTTP_COOKIE'
SESSION_PERSISTENCE_APP_COOKIE = 'APP_COOKIE'
SUPPORTED_SP_TYPES = (SESSION_PERSISTENCE_SOURCE_IP,
                      SESSION_PERSISTENCE_HTTP_COOKIE,
                      SESSION_PERSISTENCE_APP_COOKIE)

HEALTH_MONITOR_PING = 'PING'
HEALTH_MONITOR_TCP = 'TCP'
HEALTH_MONITOR_HTTP = 'HTTP'
HEALTH_MONITOR_HTTPS = 'HTTPS'
SUPPORTED_HEALTH_MONITOR_TYPES = (HEALTH_MONITOR_HTTP, HEALTH_MONITOR_HTTPS,
                                  HEALTH_MONITOR_PING, HEALTH_MONITOR_TCP)

UPDATE_STATS = 'UPDATE_STATS'
UPDATE_HEALTH = 'UPDATE_HEALTH'

PROTOCOL_TCP = 'TCP'
PROTOCOL_HTTP = 'HTTP'
PROTOCOL_HTTPS = 'HTTPS'
PROTOCOL_TERMINATED_HTTPS = 'TERMINATED_HTTPS'
SUPPORTED_PROTOCOLS = (PROTOCOL_TCP, PROTOCOL_HTTPS, PROTOCOL_HTTP,
                       PROTOCOL_TERMINATED_HTTPS)

# Note: The database Amphora table has a foreign key constraint against
#       the provisioning_status table
# Amphora has been allocated to a load balancer
AMPHORA_ALLOCATED = 'ALLOCATED'
# Amphora is being built
AMPHORA_BOOTING = 'BOOTING'
# Amphora is ready to be allocated to a load balancer
AMPHORA_READY = 'READY'

ACTIVE = 'ACTIVE'
PENDING_DELETE = 'PENDING_DELETE'
PENDING_UPDATE = 'PENDING_UPDATE'
PENDING_CREATE = 'PENDING_CREATE'
DELETED = 'DELETED'
ERROR = 'ERROR'
SUPPORTED_PROVISIONING_STATUSES = (ACTIVE, AMPHORA_ALLOCATED,
                                   AMPHORA_BOOTING, AMPHORA_READY,
                                   PENDING_DELETE, PENDING_CREATE,
                                   PENDING_UPDATE, DELETED, ERROR)
MUTABLE_STATUSES = (ACTIVE,)
DELETABLE_STATUSES = (ACTIVE, ERROR)

SUPPORTED_AMPHORA_STATUSES = (AMPHORA_ALLOCATED, AMPHORA_BOOTING,
                              AMPHORA_READY, DELETED, PENDING_DELETE)

ONLINE = 'ONLINE'
OFFLINE = 'OFFLINE'
DEGRADED = 'DEGRADED'
ERROR = 'ERROR'
NO_MONITOR = 'NO_MONITOR'
OPERATING_STATUS = 'operating_status'
SUPPORTED_OPERATING_STATUSES = (ONLINE, OFFLINE, DEGRADED, ERROR, NO_MONITOR)

AMPHORA_VM = 'VM'
SUPPORTED_AMPHORA_TYPES = (AMPHORA_VM,)

# L7 constants
L7RULE_TYPE_HOST_NAME = 'HOST_NAME'
L7RULE_TYPE_PATH = 'PATH'
L7RULE_TYPE_FILE_TYPE = 'FILE_TYPE'
L7RULE_TYPE_HEADER = 'HEADER'
L7RULE_TYPE_COOKIE = 'COOKIE'
SUPPORTED_L7RULE_TYPES = (L7RULE_TYPE_HOST_NAME, L7RULE_TYPE_PATH,
                          L7RULE_TYPE_FILE_TYPE, L7RULE_TYPE_HEADER,
                          L7RULE_TYPE_COOKIE)

L7RULE_COMPARE_TYPE_REGEX = 'REGEX'
L7RULE_COMPARE_TYPE_STARTS_WITH = 'STARTS_WITH'
L7RULE_COMPARE_TYPE_ENDS_WITH = 'ENDS_WITH'
L7RULE_COMPARE_TYPE_CONTAINS = 'CONTAINS'
L7RULE_COMPARE_TYPE_EQUAL_TO = 'EQUAL_TO'
SUPPORTED_L7RULE_COMPARE_TYPES = (L7RULE_COMPARE_TYPE_REGEX,
                                  L7RULE_COMPARE_TYPE_STARTS_WITH,
                                  L7RULE_COMPARE_TYPE_ENDS_WITH,
                                  L7RULE_COMPARE_TYPE_CONTAINS,
                                  L7RULE_COMPARE_TYPE_EQUAL_TO)

L7POLICY_ACTION_REJECT = 'REJECT'
L7POLICY_ACTION_REDIRECT_TO_URL = 'REDIRECT_TO_URL'
L7POLICY_ACTION_REDIRECT_TO_POOL = 'REDIRECT_TO_POOL'
SUPPORTED_L7POLICY_ACTIONS = (L7POLICY_ACTION_REJECT,
                              L7POLICY_ACTION_REDIRECT_TO_URL,
                              L7POLICY_ACTION_REDIRECT_TO_POOL)

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

# Task/Flow constants
AMPHORA = 'amphora'
FAILED_AMPHORA = 'failed_amphora'
FAILOVER_AMPHORA = 'failover_amphora'
AMPHORAE = 'amphorae'
AMPHORA_ID = 'amphora_id'
FAILOVER_AMPHORA_ID = 'failover_amphora_id'
DELTA = 'delta'
DELTAS = 'deltas'
HEALTH_MON = 'health_mon'
LISTENER = 'listener'
LISTENERS = 'listeners'
LOADBALANCER = 'loadbalancer'
LOADBALANCER_ID = 'loadbalancer_id'
SERVER_GROUP_ID = 'server_group_id'
ANTI_AFFINITY = 'anti-affinity'
MEMBER = 'member'
MEMBER_ID = 'member_id'
COMPUTE_ID = 'compute_id'
COMPUTE_OBJ = 'compute_obj'
AMP_DATA = 'amp_data'
AMPS_DATA = 'amps_data'
NICS = 'nics'
VIP = 'vip'
POOL = 'pool'
POOL_ID = 'pool_id'
L7POLICY = 'l7policy'
L7RULE = 'l7rule'
OBJECT = 'object'
SERVER_PEM = 'server_pem'
UPDATE_DICT = 'update_dict'
VIP_NETWORK = 'vip_network'
AMPHORAE_NETWORK_CONFIG = 'amphorae_network_config'
ADDED_PORTS = 'added_ports'
PORTS = 'ports'
MEMBER_PORTS = 'member_ports'
LOADBALANCER_TOPOLOGY = 'topology'

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

POST_MAP_AMP_TO_LB_SUBFLOW = 'octavia-post-map-amp-to-lb-subflow'
CREATE_AMP_FOR_LB_SUBFLOW = 'octavia-create-amp-for-lb-subflow'
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

GENERATE_SERVER_PEM_TASK = 'GenerateServerPEMTask'

# Task Names
RELOAD_LB_AFTER_AMP_ASSOC = 'reload-lb-after-amp-assoc'
RELOAD_LB_AFTER_AMP_ASSOC_FULL_GRAPH = 'reload-lb-after-amp-assoc-full-graph'
RELOAD_LB_AFTER_PLUG_VIP = 'reload-lb-after-plug-vip'

NOVA_1 = '1.1'
NOVA_21 = '2.1'
NOVA_3 = '3'
NOVA_VERSIONS = (NOVA_1, NOVA_21, NOVA_3)

RPC_NAMESPACE_CONTROLLER_AGENT = 'controller'


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


NO_CHECK = 'no check'

HAPROXY_MEMBER_STATUSES = (UP, DOWN, NO_CHECK)

API_VERSION = '0.5'

HAPROXY_BASE_PEER_PORT = 1025
KEEPALIVED_CONF = 'keepalived.conf.j2'
CHECK_SCRIPT_CONF = 'keepalived_check_script.conf.j2'

PLUGGED_INTERFACES = '/var/lib/octavia/plugged_interfaces'
AMPHORA_NAMESPACE = 'amphora-haproxy'

# List of HTTP headers which are supported for insertion
SUPPORTED_HTTP_HEADERS = ['X-Forwarded-For',
                          'X-Forwarded-Port']

FLOW_DOC_TITLES = {'AmphoraFlows': 'Amphora Flows',
                   'LoadBalancerFlows': 'Load Balancer Flows',
                   'ListenerFlows': 'Listener Flows',
                   'PoolFlows': 'Pool Flows',
                   'MemberFlows': 'Member Flows',
                   'HealthMonitorFlows': 'Health Monitor Flows',
                   'L7PolicyFlows': 'Layer 7 Policy Flows',
                   'L7RuleFlows': 'Layer 7 Rule Flows'}

NETNS_PRIMARY_INTERFACE = 'eth1'

AMP_ACTION_START = 'start'
AMP_ACTION_STOP = 'stop'
AMP_ACTION_RELOAD = 'reload'
GLANCE_IMAGE_ACTIVE = 'active'
