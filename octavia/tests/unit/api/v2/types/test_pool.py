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

from octavia.api.common import types
from octavia.api.v2.types import health_monitor as health_monitor_type
from octavia.api.v2.types import member as member_type
from octavia.api.v2.types import pool as pool_type
from octavia.common import constants
from octavia.common import data_models
from octavia.tests.unit.api.common import base


class TestSessionPersistence(object):

    _type = None

    def test_session_persistence(self):
        body = {"type": constants.SESSION_PERSISTENCE_HTTP_COOKIE}
        sp = wsme_json.fromjson(self._type, body)
        self.assertIsNotNone(sp.type)

    def test_invalid_type(self):
        body = {"type": "source_ip"}
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
        body = {
            "loadbalancer_id": uuidutils.generate_uuid(),
            "listener_id": uuidutils.generate_uuid(),
            "protocol": constants.PROTOCOL_HTTP,
            "lb_algorithm": constants.LB_ALGORITHM_ROUND_ROBIN,
            "tags": ['test_tag']}
        pool = wsme_json.fromjson(self._type, body)
        self.assertTrue(pool.admin_state_up)

    def test_load_balancer_mandatory(self):
        body = {"loadbalancer_id": uuidutils.generate_uuid()}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_protocol_mandatory(self):
        body = {"lb_algorithm": constants.LB_ALGORITHM_ROUND_ROBIN}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_lb_algorithm_mandatory(self):
        body = {"protocol": constants.PROTOCOL_HTTP}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_name(self):
        body = {"name": 10,
                "loadbalancer_id": uuidutils.generate_uuid(),
                "protocol": constants.PROTOCOL_HTTP,
                "lb_algorithm": constants.LB_ALGORITHM_ROUND_ROBIN}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_description(self):
        body = {"description": 10,
                "loadbalancer_id": uuidutils.generate_uuid(),
                "protocol": constants.PROTOCOL_HTTP,
                "lb_algorithm": constants.LB_ALGORITHM_ROUND_ROBIN}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_too_long_name(self):
        body = {"name": "n" * 256,
                "loadbalancer_id": uuidutils.generate_uuid(),
                "protocol": constants.PROTOCOL_HTTP,
                "lb_algorithm": constants.LB_ALGORITHM_ROUND_ROBIN}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_too_long_description(self):
        body = {"description": "d" * 256,
                "loadbalancer_id": uuidutils.generate_uuid(),
                "protocol": constants.PROTOCOL_HTTP,
                "lb_algorithm": constants.LB_ALGORITHM_ROUND_ROBIN}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_load_balacer_id(self):
        body = {"loadbalancer_id": 10,
                "protocol": constants.PROTOCOL_HTTP,
                "lb_algorithm": constants.LB_ALGORITHM_ROUND_ROBIN}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_protocol(self):
        body = {"loadbalancer_id": uuidutils.generate_uuid(),
                "protocol": "http",
                "lb_algorithm": constants.LB_ALGORITHM_ROUND_ROBIN}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_lb_algorithm(self):
        body = {"loadbalancer_id": uuidutils.generate_uuid(),
                "protocol": constants.PROTOCOL_HTTP,
                "lb_algorithm": "source_ip"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_non_uuid_project_id(self):
        body = {"loadbalancer_id": uuidutils.generate_uuid(),
                "protocol": constants.PROTOCOL_HTTP,
                "lb_algorithm": constants.LB_ALGORITHM_ROUND_ROBIN,
                "project_id": "non-uuid"}
        pool = wsme_json.fromjson(self._type, body)
        self.assertEqual(pool.project_id, body['project_id'])

    def test_invalid_tags(self):
        body = {"protocol": constants.PROTOCOL_HTTP,
                "lb_algorithm": constants.LB_ALGORITHM_ROUND_ROBIN,
                "tags": "invalid_tag"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type,
                          body)
        body = {"protocol": constants.PROTOCOL_HTTP,
                "lb_algorithm": constants.LB_ALGORITHM_ROUND_ROBIN,
                "tags": [1, 2]}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_alpn_protocols(self):
        body = {"protocol": constants.PROTOCOL_HTTP,
                "loadbalancer_id": uuidutils.generate_uuid(),
                "alpn_protocols": ["bad", "boy"]}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)


class TestPoolPUT(base.BaseTypesTest):

    _type = pool_type.PoolPUT

    def test_pool(self):
        body = {"name": "test_name", "tags": ['new_tag']}
        pool = wsme_json.fromjson(self._type, body)
        self.assertEqual(wsme_types.Unset, pool.admin_state_up)

    def test_invalid_name(self):
        body = {"name": 10}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_too_long_name(self):
        body = {"name": "n" * 256}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_too_long_description(self):
        body = {"description": "d" * 256}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_description(self):
        body = {"description": 10}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_lb_algorithm(self):
        body = {"lb_algorithm": "source_ip"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_tags(self):
        body = {"tags": "invalid_tag"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type,
                          body)
        body = {"tags": [1, 2]}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_alpn_protocols(self):
        body = {"alpn_protocols": ["bad", "boy"]}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)


class TestSessionPersistencePOST(base.BaseTypesTest, TestSessionPersistence):

    _type = pool_type.SessionPersistencePOST

    def test_type_mandatory(self):
        body = {"cookie_name": "test_name"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_app_cookie_name(self):
        body = {"cookie_name": "cookie,monster"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)


class TestSessionPersistencePUT(base.BaseTypesTest, TestSessionPersistence):

    _type = pool_type.SessionPersistencePUT

    def test_invalid_app_cookie_name(self):
        body = {"cookie_name": "cookie\nmonster"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)


class TestPoolResponse(base.BaseTypesTest):

    _type = pool_type.PoolResponse

    def test_pool_response_with_health_monitor(self):
        health_monitor_id = uuidutils.generate_uuid()
        health_monitor_model = data_models.HealthMonitor(id=health_monitor_id)
        pool_model = data_models.Pool(health_monitor=health_monitor_model)
        pool = self._type.from_data_model(data_model=pool_model)
        self.assertEqual(pool.healthmonitor_id, health_monitor_id)

    def test_pool_response_with_members(self):
        member_id = uuidutils.generate_uuid()
        members = [data_models.Member(id=member_id)]
        pool_model = data_models.Pool(members=members)
        pool = self._type.from_data_model(data_model=pool_model)
        self.assertIsInstance(pool.members[0], types.IdOnlyType)
        self.assertEqual(pool.members[0].id, member_id)

    def test_pool_response_with_load_balancer(self):
        load_balancer_id = uuidutils.generate_uuid()
        load_balancer = data_models.LoadBalancer(id=load_balancer_id)
        pool_model = data_models.Pool(load_balancer=load_balancer)
        pool = self._type.from_data_model(data_model=pool_model)
        self.assertIsInstance(pool.loadbalancers[0], types.IdOnlyType)
        self.assertEqual(pool.loadbalancers[0].id, load_balancer_id)

    def test_pool_response_with_session_persistence(self):
        session_persistence = data_models.SessionPersistence(
            cookie_name="test"
        )
        pool_model = data_models.Pool(session_persistence=session_persistence)
        pool = self._type.from_data_model(data_model=pool_model)
        self.assertEqual(pool.session_persistence.cookie_name, "test")

    def test_pool_response_without_children(self):
        pool = self._type.from_data_model(data_model=data_models.Pool())
        self.assertEqual(len(pool.loadbalancers), 0)
        self.assertIsNone(pool.session_persistence)
        self.assertEqual(len(pool.members), 0)
        self.assertEqual(len(pool.listeners), 0)
        self.assertEqual(pool.healthmonitor_id, wsme_types.Unset)


class TestPoolFullResponse(base.BaseTypesTest):

    _type = pool_type.PoolFullResponse

    def test_pool_full_response_with_health_monitor(self):
        health_monitor_model = data_models.HealthMonitor()
        pool_model = data_models.Pool(health_monitor=health_monitor_model)
        pool = self._type.from_data_model(data_model=pool_model)
        self.assertIsInstance(
            pool.healthmonitor, health_monitor_type.HealthMonitorFullResponse
        )

    def test_pool_full_response_with_members(self):
        members = [data_models.Member()]
        pool_model = data_models.Pool(members=members)
        pool = self._type.from_data_model(data_model=pool_model)
        self.assertIsInstance(pool.members[0], member_type.MemberFullResponse)

    def test_pool_full_response_without_children(self):
        pool = self._type.from_data_model(data_model=data_models.Pool())
        self.assertIsNone(pool.healthmonitor)
