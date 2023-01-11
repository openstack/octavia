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

from unittest import mock
import octavia # noqa H306
from octavia.common import constants
from octavia.controller.worker.v2.tasks import notification_tasks
import octavia.tests.unit.base as base


class MockNOTIFIER(mock.MagicMock):
    info = mock.MagicMock()


@mock.patch('octavia.common.rpc.NOTIFIER',
            new_callable=MockNOTIFIER)
@mock.patch('octavia.common.context.RequestContext',
            new_callable=mock.MagicMock)
@mock.patch('octavia.api.v2.types.load_balancer.LoadBalancerFullResponse.'
            'from_data_model',
            new_callable=mock.MagicMock)
class TestNotificationTasks(base.TestCase):
    def test_update_notification_execute(self, *args):
        noti = notification_tasks.SendUpdateNotification()
        id = 1
        lb = {constants.PROJECT_ID: id,
              constants.LOADBALANCER_ID: id}
        noti.execute(lb)
        octavia.common.context.RequestContext.assert_called_with(project_id=id)
        call_args, call_kwargs = octavia.common.rpc.NOTIFIER.info.call_args
        self.assertEqual('octavia.loadbalancer.update.end', call_args[1])

    def test_create_notification(self, *args):
        noti = notification_tasks.SendCreateNotification()
        id = 2
        lb = {constants.PROJECT_ID: id,
              constants.LOADBALANCER_ID: id}
        noti.execute(lb)
        octavia.common.context.RequestContext.assert_called_with(project_id=id)
        call_args, call_kwargs = octavia.common.rpc.NOTIFIER.info.call_args
        self.assertEqual('octavia.loadbalancer.create.end', call_args[1])

    def test_delete_notification(self, *args):
        noti = notification_tasks.SendDeleteNotification()
        id = 3
        lb = {constants.PROJECT_ID: id,
              constants.LOADBALANCER_ID: id}
        noti.execute(lb)
        octavia.common.context.RequestContext.assert_called_with(project_id=id)
        call_args, call_kwargs = octavia.common.rpc.NOTIFIER.info.call_args
        self.assertEqual('octavia.loadbalancer.delete.end', call_args[1])
