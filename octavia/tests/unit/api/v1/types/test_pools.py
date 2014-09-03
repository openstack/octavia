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

from octavia.api.v1.types import pool as pool_type
from octavia.common import constants
from octavia.tests.unit.api.v1.types import base


class TestSessionPersistence(object):

    _type = None

    def test_session_persistence(self):
        body = {"type": constants.SESSION_PERSISTENCE_HTTP_COOKIE}
        sp = wsme_json.fromjson(self._type, body)
        self.assertIsNotNone(sp.type)

    def test_invalid_type(self):
        body = {"type": 10}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_cookie_name(self):
        body = {"type": constants.SESSION_PERSISTENCE_HTTP_COOKIE,
                "cookie_name": 10}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)


class TestPoolPOST(base.BaseTypesTest):

    _type = pool_type.PoolPOST

    def test_pool(self):
        body = {"protocol": constants.PROTOCOL_HTTP,
                "lb_algorithm": constants.LB_ALGORITHM_ROUND_ROBIN}
        pool = wsme_json.fromjson(self._type, body)
        self.assertTrue(pool.enabled)

    def test_protocol_mandatory(self):
        body = {"lb_algorithm": constants.LB_ALGORITHM_ROUND_ROBIN}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_lb_algorithm_mandatory(self):
        body = {"protocol": constants.PROTOCOL_HTTP}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_name(self):
        body = {"name": 10, "protocol": constants.PROTOCOL_HTTP,
                "lb_algorithm": constants.LB_ALGORITHM_ROUND_ROBIN}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_description(self):
        body = {"description": 10, "protocol": constants.PROTOCOL_HTTP,
                "lb_algorithm": constants.LB_ALGORITHM_ROUND_ROBIN}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_protocol(self):
        body = {"protocol": 10,
                "lb_algorithm": constants.LB_ALGORITHM_ROUND_ROBIN}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_lb_algorithm(self):
        body = {"protocol": constants.PROTOCOL_HTTP, "lb_algorithm": 10}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)


class TestPoolPUT(base.BaseTypesTest):

    _type = pool_type.PoolPUT

    def test_pool(self):
        body = {"name": "test_name"}
        pool = wsme_json.fromjson(self._type, body)
        self.assertEqual(wsme_types.Unset, pool.enabled)

    def test_invalid_name(self):
        body = {"name": 10}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_description(self):
        body = {"description": 10}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_lb_algorithm(self):
        body = {"lb_algorithm": 10}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)


class TestSessionPersistencePOST(base.BaseTypesTest, TestSessionPersistence):

    _type = pool_type.SessionPersistencePOST

    def test_type_mandatory(self):
        body = {"cookie_name": "test_name"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)


class TestSessionPersistencePUT(base.BaseTypesTest, TestSessionPersistence):

    _type = pool_type.SessionPersistencePUT