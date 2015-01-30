# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

import logging

from taskflow import task

from octavia.db import api as db_apis
from octavia.db import repositories as repo

LOG = logging.getLogger(__name__)


class BaseControllerTask(task.Task):
    """Base task to load drivers common to the tasks."""

    def __init__(self, **kwargs):
        from octavia.controller.worker import controller_worker
        self.cntrlr_worker = controller_worker.ControllerWorker()
        self.listener_repo = repo.ListenerRepository()
        self.amp_repo = repo.AmphoraRepository()
        super(BaseControllerTask, self).__init__(**kwargs)


class DeleteLoadBalancersOnAmp(BaseControllerTask):
    """Delete the load balancers on an amphora."""

    def execute(self, amphora):
        """Deletes the load balancers on an amphora.

        Iterate across the load balancers on an amphora and
        call back into the controller worker to delete the
        load balancers.

        :param amphora: The amphora to delete the load balancers from
        """
        lbs = self.amp_repo.get_all_lbs_on_amphora(db_apis.get_session(),
                                                   amphora_id=amphora.id)
        for lb in lbs:
            self.cntrlr_worker.delete_load_balancer(lb.id)


class DeleteListenersOnLB(BaseControllerTask):
    """Deletes listeners on a load balancer."""

    def execute(self, loadbalancer):
        """Deletes listeners on a load balancer.

        Iterate across the listeners on a load balancer and
        call back into the controller worker to delete the
        listeners.

        :param loadbalancer: The load balancer to delete listeners from
        """
        listeners = self.listener_repo.get_all(db_apis.get_session(),
                                               load_balancer_id=(
                                                   loadbalancer.id))
        for listener in listeners:
            self.cntrlr_worker.delete_listener(listener.id)


class DisableEnableLB(BaseControllerTask):
    """Enables or disables a load balancer."""

    def execute(self, loadbalancer):
        """Enables or disables a load balancer.

        Iterate across the listeners starting or stoping them
        based on the load balancer enabled / disable.

        :param loadbalancer: The load balancer to enable/disable
        """
        listeners = self.listener_repo.get_all(db_apis.get_session(),
                                               load_balancer_id=(
                                                   loadbalancer.id))
        for listener in listeners:
            if loadbalancer.enabled != listener.enabled:
                self.cntrlr_worker.update_listener(
                    {'enabled': loadbalancer.enabled}, listener.id)
