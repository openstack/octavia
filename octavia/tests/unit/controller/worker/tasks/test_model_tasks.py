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

import six

from octavia.controller.worker.tasks import model_tasks
import octavia.tests.unit.base as base

if six.PY2:
    import mock
else:
    import unittest.mock as mock


class TestObjectUpdateTasks(base.TestCase):

    def setUp(self):

        self.listener_mock = mock.MagicMock()
        self.listener_mock.name = 'TEST'

        super(TestObjectUpdateTasks, self).setUp()

    def test_delete_model_object(self):

        delete_object = model_tasks.DeleteModelObject()
        delete_object.execute(self.listener_mock)

        self.listener_mock.delete.assert_called_once_with()

    def test_update_listener(self):

        update_attr = model_tasks.UpdateAttributes()
        update_attr.execute(self.listener_mock,
                            {'name': 'TEST2'})

        assert self.listener_mock.name == 'TEST2'
