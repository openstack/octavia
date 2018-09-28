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

from oslo_utils import uuidutils
from wsme import exc
from wsme.rest import json as wsme_json
from wsme import types as wsme_types

from octavia.api.v2.types import listener as lis_type
from octavia.common import constants
from octavia.tests.unit.api.common import base


class TestListener(object):

    _type = None

    def test_invalid_name(self):
        body = {"name": 0}
        if self._type is lis_type.ListenerPOST:
            body.update({"protocol": constants.PROTOCOL_HTTP,
                         "protocol_port": 80,
                         "loadbalancer_id": uuidutils.generate_uuid()})
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_description(self):
        body = {"description": 0}
        if self._type is lis_type.ListenerPOST:
            body.update({"protocol": constants.PROTOCOL_HTTP,
                         "protocol_port": 80,
                         "loadbalancer_id": uuidutils.generate_uuid()})
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_admin_state_up(self):
        body = {"admin_state_up": "notvalid"}
        if self._type is lis_type.ListenerPOST:
            body.update({"protocol": constants.PROTOCOL_HTTP,
                         "protocol_port": 80,
                         "loadbalancer_id": uuidutils.generate_uuid()})
        self.assertRaises(ValueError, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_connection_limit(self):
        body = {"connection_limit": "test"}
        if self._type is lis_type.ListenerPOST:
            body.update({"protocol": constants.PROTOCOL_HTTP,
                         "protocol_port": 80,
                         "loadbalancer_id": uuidutils.generate_uuid()})
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)

    def test_invalid_tags(self):
        body = {"tags": "invalid_tag"}
        if self._type is lis_type.ListenerPOST:
            body.update({"protocol": constants.PROTOCOL_HTTP,
                         "protocol_port": 80,
                         "loadbalancer_id": uuidutils.generate_uuid()})
        self.assertRaises(ValueError, wsme_json.fromjson, self._type,
                          body)
        body = {"tags": [1, 2]}
        if self._type is lis_type.ListenerPOST:
            body.update({"protocol": constants.PROTOCOL_HTTP,
                         "protocol_port": 80,
                         "loadbalancer_id": uuidutils.generate_uuid()})
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)


class TestListenerPOST(base.BaseTypesTest, TestListener):

    _type = lis_type.ListenerPOST

    def test_listener(self):
        body = {"name": "test", "description": "test", "connection_limit": 10,
                "protocol": constants.PROTOCOL_HTTP, "protocol_port": 80,
                "default_pool_id": uuidutils.generate_uuid(),
                "loadbalancer_id": uuidutils.generate_uuid(),
                "tags": ['test_tag']}
        listener = wsme_json.fromjson(self._type, body)
        self.assertTrue(listener.admin_state_up)

    def test_protocol_mandatory(self):
        body = {"protocol_port": 80,
                "loadbalancer_id": uuidutils.generate_uuid()}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_protocol_port_mandatory(self):
        body = {"protocol": constants.PROTOCOL_HTTP,
                "loadbalancer_id": uuidutils.generate_uuid()}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_protocol(self):
        body = {"protocol": "http", "protocol_port": 80}
        if self._type is lis_type.ListenerPOST:
            body.update({"loadbalancer_id": uuidutils.generate_uuid()})
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_protocol_port(self):
        body = {"protocol": constants.PROTOCOL_HTTP, "protocol_port": "test"}
        if self._type is lis_type.ListenerPOST:
            body.update({"loadbalancer_id": uuidutils.generate_uuid()})
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)

    def test_loadbalancer_id_mandatory(self):
        body = {"protocol": constants.PROTOCOL_HTTP,
                "protocol_port": 80}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_loadbalancer_id(self):
        body = {"protocol": constants.PROTOCOL_HTTP, "protocol_port": 80,
                "loadbalancer_id": "a"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_non_uuid_project_id(self):
        body = {"name": "test", "description": "test", "connection_limit": 10,
                "protocol": constants.PROTOCOL_HTTP, "protocol_port": 80,
                "default_pool_id": uuidutils.generate_uuid(),
                "loadbalancer_id": uuidutils.generate_uuid(),
                "project_id": "non-uuid"}
        listener = wsme_json.fromjson(self._type, body)
        self.assertEqual(listener.project_id, body['project_id'])


class TestListenerPUT(base.BaseTypesTest, TestListener):

    _type = lis_type.ListenerPUT

    def test_listener(self):
        body = {"name": "test", "description": "test",
                "connection_limit": 10,
                "default_tls_container_ref": uuidutils.generate_uuid(),
                "sni_container_refs": [uuidutils.generate_uuid(),
                                       uuidutils.generate_uuid()],
                "default_pool_id": uuidutils.generate_uuid(),
                "insert_headers": {"a": "1", "b": "2"},
                "tags": ['test_tag']}
        listener = wsme_json.fromjson(self._type, body)
        self.assertEqual(wsme_types.Unset, listener.admin_state_up)
