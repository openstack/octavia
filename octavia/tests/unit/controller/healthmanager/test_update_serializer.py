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

import uuid

from octavia.common import constants
from octavia.controller.healthmanager import update_serializer
import octavia.tests.unit.base as base


class TestUpdateSerializer(base.TestCase):
    def setUp(self):
        super(TestUpdateSerializer, self).setUp()

    def test_serializer_from_dict_to_dict(self):
        obj_id = str(uuid.uuid4())
        obj_type = constants.UPDATE_HEALTH
        obj_payload = {'test': [1, 2, 3, 4], id: obj_id}
        obj = update_serializer.InfoContainer(obj_id, obj_type, obj_payload)
        cloned_obj = update_serializer.InfoContainer.from_dict(obj.to_dict())
        self.assertEqual(obj, cloned_obj)

        obj_id = str(uuid.uuid4())
        obj_type = constants.UPDATE_HEALTH
        obj_payload = {'test': [3, 2, 1, 6], id: obj_id, 'x': {'y': 1}}
        obj = update_serializer.InfoContainer(obj_id, obj_type, obj_payload)
        cloned_obj = update_serializer.InfoContainer.from_dict(obj.to_dict())
        self.assertEqual(obj, cloned_obj)
