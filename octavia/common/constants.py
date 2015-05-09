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
SUPPORTED_SP_TYPES = (SESSION_PERSISTENCE_SOURCE_IP,
                      SESSION_PERSISTENCE_HTTP_COOKIE)

HEALTH_MONITOR_PING = 'PING'
HEALTH_MONITOR_TCP = 'TCP'
HEALTH_MONITOR_HTTP = 'HTTP'
HEALTH_MONITOR_HTTPS = 'HTTPS'
SUPPORTED_HEALTH_MONITOR_TYPES = (HEALTH_MONITOR_HTTP, HEALTH_MONITOR_HTTPS,
                                  HEALTH_MONITOR_PING, HEALTH_MONITOR_TCP)

PROTOCOL_TCP = 'TCP'
PROTOCOL_HTTP = 'HTTP'
PROTOCOL_HTTPS = 'HTTPS'
PROTOCOL_TERMINATED_HTTPS = 'TERMINATED_HTTPS'
SUPPORTED_PROTOCOLS = (PROTOCOL_TCP, PROTOCOL_HTTPS, PROTOCOL_HTTP)

# Note: The database Amphora table has a foreign key constraint against
#       the provisioning_status table
# Amphora has been allocated to a load balancer
AMPHORA_ALLOCATED = 'ALLOCATED'
# Amphora healthy with listener(s) deployed
# TODO(johnsom) This doesn't exist
AMPHORA_UP = 'UP'
# Amphora unhealthy with listener(s) deployed
# TODO(johnsom) This doesn't exist
AMPHORA_DOWN = 'DOWN'
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

SUPPORTED_AMPHORA_STATUSES = (AMPHORA_ALLOCATED, AMPHORA_UP, AMPHORA_DOWN,
                              AMPHORA_BOOTING, AMPHORA_READY, DELETED,
                              PENDING_DELETE)

ONLINE = 'ONLINE'
OFFLINE = 'OFFLINE'
DEGRADED = 'DEGRADED'
ERROR = 'ERROR'
SUPPORTED_OPERATING_STATUSES = (ONLINE, OFFLINE, DEGRADED, ERROR)

AMPHORA_VM = 'VM'
SUPPORTED_AMPHORA_TYPES = (AMPHORA_VM,)

# Task/Flow constants
AMPHORA = 'amphora'
AMPHORA_ID = 'amphora_id'
DELTA = 'delta'
DELTAS = 'deltas'
LISTENER = 'listener'
LOADBALANCER = 'loadbalancer'
LOADBALANCER_ID = 'loadbalancer_id'
COMPUTE_ID = 'compute_id'
COMPUTE_OBJ = 'compute_obj'
AMPS_DATA = 'amps_data'
NICS = 'nics'
VIP = 'vip'

CREATE_AMPHORA_FLOW = 'octavia-create-amphora-flow'
CREATE_AMPHORA_FOR_LB_FLOW = 'octavia-create-amp-for-lb-flow'
CREATE_HEALTH_MONITOR_FLOW = 'octavia-create-health-monitor-flow'
CREATE_LISTENER_FLOW = 'octavia-create-listener_flow'
CREATE_LOADBALANCER_FLOW = 'octavia-create-loadbalancer-flow'
CREATE_MEMBER_FLOW = 'octavia-create-member-flow'
CREATE_POOL_FLOW = 'octavia-create-pool-flow'
DELETE_AMPHORA_FLOW = 'octavia-delete-amphora-flow'
DELETE_HEALTH_MONITOR_FLOW = 'octavia-delete-health-monitor-flow'
DELETE_LISTENER_FLOW = 'octavia-delete-listener_flow'
DELETE_LOADBALANCER_FLOW = 'octavia-delete-loadbalancer-flow'
DELETE_MEMBER_FLOW = 'octavia-delete-member-flow'
DELETE_POOL_FLOW = 'octavia-delete-pool-flow'
LOADBALANCER_NETWORKING_SUBFLOW = 'octavia-new-loadbalancer-net-subflow'
UPDATE_HEALTH_MONITOR_FLOW = 'octavia-update-health-monitor-flow'
UPDATE_LISTENER_FLOW = 'octavia-update-listener-flow'
UPDATE_LOADBALANCER_FLOW = 'octavia-update-loadbalancer-flow'
UPDATE_MEMBER_FLOW = 'octavia-update-member-flow'
UPDATE_POOL_FLOW = 'octavia-update-pool-flow'

# Task Names
RELOAD_LB_AFTER_AMP_ASSOC = 'reload-lb-after-amp-assoc'
RELOAD_LB_AFTER_PLUG_VIP = 'reload-lb-after-plug-vip'

NOVA_1 = '1.1'
NOVA_2 = '2'
NOVA_3 = '3'
NOVA_VERSIONS = (NOVA_1, NOVA_2, NOVA_3)

RPC_NAMESPACE_CONTROLLER_AGENT = 'controller'
