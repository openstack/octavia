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

from octavia.api.v1.types import listener as lis_type
from octavia.common import constants
from octavia.tests.unit.api.v1.types import base


class TestListener(object):

    _type = None

    def test_invalid_name(self):
        body = {"protocol": constants.PROTOCOL_HTTP, "protocol_port": 80,
                "name": 0}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_description(self):
        body = {"protocol": constants.PROTOCOL_HTTP, "protocol_port": 80,
                "description": 0}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_enabled(self):
        body = {"protocol": constants.PROTOCOL_HTTP, "protocol_port": 80,
                "enabled": "notvalid"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_protocol(self):
        body = {"protocol": 10, "protocol_port": 80}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_protocol_port(self):
        body = {"protocol": constants.PROTOCOL_HTTP, "protocol_port": "test"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)

    def test_invalid_connection_limit(self):
        body = {"protocol": constants.PROTOCOL_HTTP, "protocol_port": 80,
                "connection_limit": "test"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)


class TestListenerPOST(base.BaseTypesTest, TestListener):

    _type = lis_type.ListenerPOST

    def test_listener(self):
        body = {"name": "test", "description": "test", "connection_limit": 10,
                "protocol": constants.PROTOCOL_HTTP, "protocol_port": 80}
        listener = wsme_json.fromjson(self._type, body)
        self.assertTrue(listener.enabled)

    def test_protocol_mandatory(self):
        body = {"protocol_port": 80}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_protocol_port_mandatory(self):
        body = {"protocol": constants.PROTOCOL_HTTP}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)


class TestListenerPUT(base.BaseTypesTest, TestListener):

    _type = lis_type.ListenerPUT

    def test_listener(self):
        body = {"name": "test", "description": "test", "connection_limit": 10,
                "protocol": constants.PROTOCOL_HTTP, "protocol_port": 80}
        listener = wsme_json.fromjson(self._type, body)
        self.assertEqual(wsme_types.Unset, listener.enabled)
