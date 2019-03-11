
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

from octavia.common import constants
from octavia.controller.worker.v2.flows import amphora_flows
from octavia.controller.worker.v2.flows import health_monitor_flows
from octavia.controller.worker.v2.flows import l7policy_flows
from octavia.controller.worker.v2.flows import l7rule_flows
from octavia.controller.worker.v2.flows import listener_flows
from octavia.controller.worker.v2.flows import load_balancer_flows
from octavia.controller.worker.v2.flows import member_flows
from octavia.controller.worker.v2.flows import pool_flows


LB_FLOWS = load_balancer_flows.LoadBalancerFlows()
AMP_FLOWS = amphora_flows.AmphoraFlows()
HM_FLOWS = health_monitor_flows.HealthMonitorFlows()
L7_POLICY_FLOWS = l7policy_flows.L7PolicyFlows()
L7_RULES_FLOWS = l7rule_flows.L7RuleFlows()
LISTENER_FLOWS = listener_flows.ListenerFlows()
M_FLOWS = member_flows.MemberFlows()
P_FLOWS = pool_flows.PoolFlows()


def get_create_load_balancer_flow(topology, listeners=None):
    return LB_FLOWS.get_create_load_balancer_flow(topology,
                                                  listeners=listeners)


def get_delete_load_balancer_flow(lb):
    return LB_FLOWS.get_delete_load_balancer_flow(lb)


def get_delete_listeners_store(lb):
    return LB_FLOWS.get_delete_listeners_store(lb)


def get_delete_pools_store(lb):
    return LB_FLOWS.get_delete_pools_store(lb)


def get_cascade_delete_load_balancer_flow(lb):
    return LB_FLOWS.get_cascade_delete_load_balancer_flow(lb)


def get_update_load_balancer_flow():
    return LB_FLOWS.get_update_load_balancer_flow()


def get_create_amphora_flow():
    return AMP_FLOWS.get_create_amphora_flow()


def get_delete_amphora_flow():
    return AMP_FLOWS.get_delete_amphora_flow()


def get_failover_flow(role=constants.ROLE_STANDALONE, load_balancer=None):
    return AMP_FLOWS.get_failover_flow(role=role, load_balancer=load_balancer)


def cert_rotate_amphora_flow():
    return AMP_FLOWS.cert_rotate_amphora_flow()


def update_amphora_config_flow():
    return AMP_FLOWS.update_amphora_config_flow()


def get_create_health_monitor_flow():
    return HM_FLOWS.get_create_health_monitor_flow()


def get_delete_health_monitor_flow():
    return HM_FLOWS.get_delete_health_monitor_flow()


def get_update_health_monitor_flow():
    return HM_FLOWS.get_update_health_monitor_flow()


def get_create_l7policy_flow():
    return L7_POLICY_FLOWS.get_create_l7policy_flow()


def get_delete_l7policy_flow():
    return L7_POLICY_FLOWS.get_delete_l7policy_flow()


def get_update_l7policy_flow():
    return L7_POLICY_FLOWS.get_update_l7policy_flow()


def get_create_l7rule_flow():
    return L7_RULES_FLOWS.get_create_l7rule_flow()


def get_delete_l7rule_flow():
    return L7_RULES_FLOWS.get_delete_l7rule_flow()


def get_update_l7rule_flow():
    return L7_RULES_FLOWS.get_update_l7rule_flow()


def get_create_listener_flow():
    return LISTENER_FLOWS.get_create_listener_flow()


def get_create_all_listeners_flow():
    return LISTENER_FLOWS.get_create_all_listeners_flow()


def get_delete_listener_flow():
    return LISTENER_FLOWS.get_delete_listener_flow()


def get_update_listener_flow():
    return LISTENER_FLOWS.get_update_listener_flow()


def get_create_member_flow():
    return M_FLOWS.get_create_member_flow()


def get_delete_member_flow():
    return M_FLOWS.get_delete_member_flow()


def get_update_member_flow():
    return M_FLOWS.get_update_member_flow()


def get_batch_update_members_flow(old_members, new_members, updated_members):
    return M_FLOWS.get_batch_update_members_flow(old_members, new_members,
                                                 updated_members)


def get_create_pool_flow():
    return P_FLOWS.get_create_pool_flow()


def get_delete_pool_flow():
    return P_FLOWS.get_delete_pool_flow()


def get_update_pool_flow():
    return P_FLOWS.get_update_pool_flow()
