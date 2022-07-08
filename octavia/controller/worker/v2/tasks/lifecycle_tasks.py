#    Copyright 2016 Rackspace
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

from taskflow import task

from octavia.common import constants
from octavia.controller.worker import task_utils as task_utilities


class BaseLifecycleTask(task.Task):
    """Base task to instansiate common classes."""

    def __init__(self, **kwargs):
        self.task_utils = task_utilities.TaskUtils()
        super().__init__(**kwargs)


class AmphoraIDToErrorOnRevertTask(BaseLifecycleTask):
    """Task to checkpoint Amphora lifecycle milestones."""

    def execute(self, amphora_id):
        pass

    def revert(self, amphora_id, *args, **kwargs):
        self.task_utils.mark_amphora_status_error(amphora_id)


class AmphoraToErrorOnRevertTask(AmphoraIDToErrorOnRevertTask):
    """Task to checkpoint Amphora lifecycle milestones."""

    def execute(self, amphora):
        pass

    def revert(self, amphora, *args, **kwargs):
        super().revert(
            amphora.get(constants.ID))


class HealthMonitorToErrorOnRevertTask(BaseLifecycleTask):
    """Task to set a member to ERROR on revert."""

    def execute(self, health_mon, listeners, loadbalancer):
        pass

    def revert(self, health_mon, listeners, loadbalancer, *args, **kwargs):
        self.task_utils.mark_health_mon_prov_status_error(
            health_mon[constants.HEALTHMONITOR_ID])
        self.task_utils.mark_pool_prov_status_active(
            health_mon[constants.POOL_ID])
        self.task_utils.mark_loadbalancer_prov_status_active(
            loadbalancer[constants.LOADBALANCER_ID])
        for listener in listeners:
            self.task_utils.mark_listener_prov_status_active(
                listener[constants.LISTENER_ID])


class L7PolicyToErrorOnRevertTask(BaseLifecycleTask):
    """Task to set a l7policy to ERROR on revert."""

    def execute(self, l7policy, listeners, loadbalancer_id):
        pass

    def revert(self, l7policy, listeners, loadbalancer_id, *args, **kwargs):
        self.task_utils.mark_l7policy_prov_status_error(
            l7policy[constants.L7POLICY_ID])
        self.task_utils.mark_loadbalancer_prov_status_active(loadbalancer_id)
        for listener in listeners:
            self.task_utils.mark_listener_prov_status_active(
                listener[constants.LISTENER_ID])


class L7RuleToErrorOnRevertTask(BaseLifecycleTask):
    """Task to set a l7rule to ERROR on revert."""

    def execute(self, l7rule, l7policy_id, listeners, loadbalancer_id):
        pass

    def revert(self, l7rule, l7policy_id, listeners, loadbalancer_id, *args,
               **kwargs):
        self.task_utils.mark_l7rule_prov_status_error(
            l7rule[constants.L7RULE_ID])
        self.task_utils.mark_l7policy_prov_status_active(l7policy_id)
        self.task_utils.mark_loadbalancer_prov_status_active(
            loadbalancer_id)
        for listener in listeners:
            self.task_utils.mark_listener_prov_status_active(
                listener[constants.LISTENER_ID])


class ListenerToErrorOnRevertTask(BaseLifecycleTask):
    """Task to set a listener to ERROR on revert."""

    def execute(self, listener):
        pass

    def revert(self, listener, *args, **kwargs):
        self.task_utils.mark_listener_prov_status_error(
            listener[constants.LISTENER_ID])
        self.task_utils.mark_loadbalancer_prov_status_active(
            listener[constants.LOADBALANCER_ID])


class ListenersToErrorOnRevertTask(BaseLifecycleTask):
    """Task to set a listener to ERROR on revert."""

    def execute(self, listeners):
        pass

    def revert(self, listeners, *args, **kwargs):
        for listener in listeners:
            self.task_utils.mark_listener_prov_status_error(
                listener[constants.LISTENER_ID])
        self.task_utils.mark_loadbalancer_prov_status_active(
            listeners[0][constants.LOADBALANCER_ID])


class LoadBalancerIDToErrorOnRevertTask(BaseLifecycleTask):
    """Task to set the load balancer to ERROR on revert."""

    def execute(self, loadbalancer_id):
        pass

    def revert(self, loadbalancer_id, *args, **kwargs):
        self.task_utils.mark_loadbalancer_prov_status_error(loadbalancer_id)


class LoadBalancerToErrorOnRevertTask(LoadBalancerIDToErrorOnRevertTask):
    """Task to set the load balancer to ERROR on revert."""

    def execute(self, loadbalancer):
        pass

    def revert(self, loadbalancer, *args, **kwargs):
        super().revert(
            loadbalancer[constants.LOADBALANCER_ID])


class MemberToErrorOnRevertTask(BaseLifecycleTask):
    """Task to set a member to ERROR on revert."""

    def execute(self, member, listeners, loadbalancer, pool_id):
        pass

    def revert(self, member, listeners, loadbalancer, pool_id, *args,
               **kwargs):
        self.task_utils.mark_member_prov_status_error(
            member[constants.MEMBER_ID])
        for listener in listeners:
            self.task_utils.mark_listener_prov_status_active(
                listener[constants.LISTENER_ID])
        self.task_utils.mark_pool_prov_status_active(pool_id)
        self.task_utils.mark_loadbalancer_prov_status_active(
            loadbalancer[constants.LOADBALANCER_ID])


class MembersToErrorOnRevertTask(BaseLifecycleTask):
    """Task to set members to ERROR on revert."""

    def execute(self, members, listeners, loadbalancer, pool_id):
        pass

    def revert(self, members, listeners, loadbalancer, pool_id, *args,
               **kwargs):
        for m in members:
            self.task_utils.mark_member_prov_status_error(
                m[constants.MEMBER_ID])
        for listener in listeners:
            self.task_utils.mark_listener_prov_status_active(
                listener[constants.LISTENER_ID])
        self.task_utils.mark_pool_prov_status_active(pool_id)
        self.task_utils.mark_loadbalancer_prov_status_active(
            loadbalancer[constants.LOADBALANCER_ID])


class PoolToErrorOnRevertTask(BaseLifecycleTask):
    """Task to set a pool to ERROR on revert."""

    def execute(self, pool_id, listeners, loadbalancer):
        pass

    def revert(self, pool_id, listeners, loadbalancer, *args, **kwargs):
        self.task_utils.mark_pool_prov_status_error(pool_id)
        self.task_utils.mark_loadbalancer_prov_status_active(
            loadbalancer[constants.LOADBALANCER_ID])
        for listener in listeners:
            self.task_utils.mark_listener_prov_status_active(
                listener[constants.LISTENER_ID])
