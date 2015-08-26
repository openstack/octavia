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

from octavia.api.v1.types import member as member_type
from octavia.tests.unit.api.v1.types import base


class TestMemberPOST(base.BaseTypesTest):

    _type = member_type.MemberPOST

    def test_member(self):
        body = {"ip_address": "10.0.0.1", "protocol_port": 80}
        member = wsme_json.fromjson(self._type, body)
        self.assertTrue(member.enabled)
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
        body = {"ip_address": "test", "protocol_port": 443}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_subnet_id(self):
        body = {"ip_address": "10.0.0.1", "protocol_port": 443,
                "subnet_id": "invalid_uuid"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_enabled(self):
        body = {"ip_address": "10.0.0.1", "protocol_port": 443,
                "enabled": "notvalid"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_protocol_port(self):
        body = {"ip_address": "10.0.0.1", "protocol_port": "test"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)

    def test_invalid_weight(self):
        body = {"ip_address": "10.0.0.1", "protocol_port": 443,
                "weight": "test"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)


class TestMemberPUT(base.BaseTypesTest):

    _type = member_type.MemberPUT

    def test_member(self):
        body = {"protocol_port": 80}
        member = wsme_json.fromjson(self._type, body)
        self.assertEqual(wsme_types.Unset, member.weight)
        self.assertEqual(wsme_types.Unset, member.enabled)

    def test_invalid_protocol_port(self):
        body = {"protocol_port": "test"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)

    def test_invalid_weight(self):
        body = {"weight": "test"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)
