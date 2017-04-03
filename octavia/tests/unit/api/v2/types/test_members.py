#    Copyright 2014 Rackspace
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

from wsme import exc
from wsme.rest import json as wsme_json
from wsme import types as wsme_types

from octavia.api.v2.types import member as member_type
from octavia.common import constants
from octavia.tests.unit.api.v2.types import base


class TestMemberPOST(base.BaseTypesTest):

    _type = member_type.MemberPOST

    def test_member(self):
        body = {"name": "member1", "address": "10.0.0.1",
                "protocol_port": 80}
        member = wsme_json.fromjson(self._type, body)
        self.assertTrue(member.admin_state_up)
        self.assertEqual(1, member.weight)
        self.assertEqual(wsme_types.Unset, member.subnet_id)

    def test_address_mandatory(self):
        body = {}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_protocol_mandatory(self):
        body = {}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_address(self):
        body = {"address": "test", "protocol_port": 443}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_subnet_id(self):
        body = {"address": "10.0.0.1", "protocol_port": 443,
                "subnet_id": "invalid_uuid"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_admin_state_up(self):
        body = {"address": "10.0.0.1", "protocol_port": 443,
                "admin_state_up": "notvalid"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_protocol_port(self):
        body = {"address": "10.0.0.1", "protocol_port": "test"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)

    def test_invalid_weight(self):
        body = {"address": "10.0.0.1", "protocol_port": 443,
                "weight": "test"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)

    def test_min_weight(self):
        body = {"address": "10.0.0.1", "protocol_port": 443,
                "weight": constants.MIN_WEIGHT - 1}
        self.assertRaises(
            exc.InvalidInput, wsme_json.fromjson, self._type, body)
        body = {"address": "10.0.0.1", "protocol_port": 443,
                "weight": constants.MIN_WEIGHT}
        member = wsme_json.fromjson(self._type, body)
        self.assertEqual(constants.MIN_WEIGHT, member.weight)

    def test_max_weight(self):
        body = {"address": "10.0.0.1", "protocol_port": 443,
                "weight": constants.MAX_WEIGHT + 1}
        self.assertRaises(
            exc.InvalidInput, wsme_json.fromjson, self._type, body)
        body = {"address": "10.0.0.1", "protocol_port": 443,
                "weight": constants.MAX_WEIGHT}
        member = wsme_json.fromjson(self._type, body)
        self.assertEqual(constants.MAX_WEIGHT, member.weight)

    def test_non_uuid_project_id(self):
        body = {"address": "10.0.0.1", "protocol_port": 80,
                "project_id": "non-uuid"}
        member = wsme_json.fromjson(self._type, body)
        self.assertEqual(member.project_id, body['project_id'])


class TestMemberPUT(base.BaseTypesTest):

    _type = member_type.MemberPUT

    def test_member(self):
        body = {"name": "new_name"}
        member = wsme_json.fromjson(self._type, body)
        self.assertEqual(wsme_types.Unset, member.weight)
        self.assertEqual(wsme_types.Unset, member.admin_state_up)

    def test_member_full(self):
        name = "new_name"
        weight = 1
        admin_state = True
        body = {"name": name, "weight": weight, "admin_state_up": admin_state}
        member = wsme_json.fromjson(self._type, body)
        self.assertEqual(name, member.name)
        self.assertEqual(weight, member.weight)
        self.assertEqual(admin_state, member.admin_state_up)

    def test_invalid_admin_state(self):
        body = {"admin_state_up": "test"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)

    def test_invalid_weight(self):
        body = {"weight": "test"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)

    def test_min_weight(self):
        body = {"weight": constants.MIN_WEIGHT - 1}
        self.assertRaises(
            exc.InvalidInput, wsme_json.fromjson, self._type, body)
        body = {"weight": constants.MIN_WEIGHT}
        member = wsme_json.fromjson(self._type, body)
        self.assertEqual(constants.MIN_WEIGHT, member.weight)

    def test_max_weight(self):
        body = {"weight": constants.MAX_WEIGHT + 1}
        self.assertRaises(
            exc.InvalidInput, wsme_json.fromjson, self._type, body)
        body = {"weight": constants.MAX_WEIGHT}
        member = wsme_json.fromjson(self._type, body)
        self.assertEqual(constants.MAX_WEIGHT, member.weight)
