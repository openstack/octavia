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

from octavia.controller.worker import task_utils as task_utilities


class BaseLifecycleTask(task.Task):
    """Base task to instansiate common classes."""

    def __init__(self, **kwargs):
        self.task_utils = task_utilities.TaskUtils()
        super(BaseLifecycleTask, self).__init__(**kwargs)


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
        super(AmphoraToErrorOnRevertTask, self).revert(amphora.id)


class HealthMonitorToErrorOnRevertTask(BaseLifecycleTask):
    """Task to set a member to ERROR on revert."""

    def execute(self, health_mon, listeners, loadbalancer):
        pass

    def revert(self, health_mon, listeners, loadbalancer, *args, **kwargs):
        self.task_utils.mark_health_mon_prov_status_error(health_mon.pool_id)
        self.task_utils.mark_loadbalancer_prov_status_active(loadbalancer.id)
        for listener in listeners:
            self.task_utils.mark_listener_prov_status_active(listener.id)


class L7PolicyToErrorOnRevertTask(BaseLifecycleTask):
    """Task to set a l7policy to ERROR on revert."""

    def execute(self, l7policy, listeners, loadbalancer):
        pass

    def revert(self, l7policy, listeners, loadbalancer, *args, **kwargs):
        self.task_utils.mark_l7policy_prov_status_error(l7policy.id)
        self.task_utils.mark_loadbalancer_prov_status_active(loadbalancer.id)
        for listener in listeners:
            self.task_utils.mark_listener_prov_status_active(listener.id)


class L7RuleToErrorOnRevertTask(BaseLifecycleTask):
    """Task to set a l7rule to ERROR on revert."""

    def execute(self, l7rule, listeners, loadbalancer):
        pass

    def revert(self, l7rule, listeners, loadbalancer, *args, **kwargs):
        self.task_utils.mark_l7rule_prov_status_error(l7rule.id)
        self.task_utils.mark_loadbalancer_prov_status_active(loadbalancer.id)
        for listener in listeners:
            self.task_utils.mark_listener_prov_status_active(listener.id)


class ListenerToErrorOnRevertTask(BaseLifecycleTask):
    """Task to set a listener to ERROR on revert."""

    def execute(self, listener):
        pass

    def revert(self, listener, *args, **kwargs):
        self.task_utils.mark_listener_prov_status_error(listener.id)
        self.task_utils.mark_loadbalancer_prov_status_active(
            listener.load_balancer.id)


class ListenersToErrorOnRevertTask(BaseLifecycleTask):
    """Task to set listeners to ERROR on revert."""

    def execute(self, listeners, loadbalancer):
        pass

    def revert(self, listeners, loadbalancer, *args, **kwargs):
        self.task_utils.mark_loadbalancer_prov_status_active(
            loadbalancer.id)
        for listener in listeners:
            self.task_utils.mark_listener_prov_status_error(listener.id)


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
        super(LoadBalancerToErrorOnRevertTask, self).revert(loadbalancer.id)


class MemberToErrorOnRevertTask(BaseLifecycleTask):
    """Task to set a member to ERROR on revert."""

    def execute(self, member, listeners, loadbalancer, pool):
        pass

    def revert(self, member, listeners, loadbalancer, pool, *args, **kwargs):
        self.task_utils.mark_member_prov_status_error(member.id)
        for listener in listeners:
            self.task_utils.mark_listener_prov_status_active(listener.id)
        self.task_utils.mark_pool_prov_status_active(pool.id)
        self.task_utils.mark_loadbalancer_prov_status_active(loadbalancer.id)


class MembersToErrorOnRevertTask(BaseLifecycleTask):
    """Task to set members to ERROR on revert."""

    def execute(self, members, listeners, loadbalancer, pool):
        pass

    def revert(self, members, listeners, loadbalancer, pool, *args, **kwargs):
        for m in members:
            self.task_utils.mark_member_prov_status_error(m.id)
        for listener in listeners:
            self.task_utils.mark_listener_prov_status_active(listener.id)
        self.task_utils.mark_pool_prov_status_active(pool.id)
        self.task_utils.mark_loadbalancer_prov_status_active(loadbalancer.id)


class PoolToErrorOnRevertTask(BaseLifecycleTask):
    """Task to set a pool to ERROR on revert."""

    def execute(self, pool, listeners, loadbalancer):
        pass

    def revert(self, pool, listeners, loadbalancer, *args, **kwargs):
        self.task_utils.mark_pool_prov_status_error(pool.id)
        self.task_utils.mark_loadbalancer_prov_status_active(loadbalancer.id)
        for listener in listeners:
            self.task_utils.mark_listener_prov_status_active(listener.id)
