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

from oslo_log import log as logging
from taskflow import task

from octavia.common import constants # noqa H306
from octavia.common import context
from octavia.common import rpc

LOG = logging.getLogger(__name__)


class BaseNotificationTask(task.Task):
    event_type = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rpc_notifier = rpc.get_notifier()

    def execute(self, loadbalancer):
        ctx = context.RequestContext(
            project_id=loadbalancer[constants.PROJECT_ID])
        LOG.debug(f"Sending rpc notification: {self.event_type} "
                  f"{loadbalancer[constants.LOADBALANCER_ID]}")
        self._rpc_notifier.info(
            ctx,
            self.event_type,
            loadbalancer
        )


class SendUpdateNotification(BaseNotificationTask):
    event_type = 'octavia.loadbalancer.update.end'


class SendCreateNotification(BaseNotificationTask):
    event_type = 'octavia.loadbalancer.create.end'


class SendDeleteNotification(BaseNotificationTask):
    event_type = 'octavia.loadbalancer.delete.end'
