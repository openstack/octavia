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

from taskflow import task

from octavia.db import api as db_apis
from octavia.db import repositories as repo


class BaseControllerTask(task.Task):
    """Base task to load drivers common to the tasks."""

    def __init__(self, **kwargs):
        from octavia.controller.worker import controller_worker
        self.cntrlr_worker = controller_worker.ControllerWorker()
        self.listener_repo = repo.ListenerRepository()
        self.amp_repo = repo.AmphoraRepository()
        self.pool_repo = repo.PoolRepository()
        super(BaseControllerTask, self).__init__(**kwargs)


# todo(xgerman): Make sure this is used outside tests
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
