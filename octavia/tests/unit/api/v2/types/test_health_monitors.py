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

from octavia.api.v2.types import health_monitor as hm_type
from octavia.common import constants
from octavia.tests.unit.api.v2.types import base


class TestHealthMonitor(object):

    _type = None

    def test_invalid_type(self):
        body = {"delay": 1, "timeout": 1, "max_retries": 1}
        if self._type is hm_type.HealthMonitorPOST:
            body.update({"type": 1, "pool_id": uuidutils.generate_uuid()})
            self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                              body)

    def test_invalid_delay(self):
        body = {"delay": "one", "timeout": 1, "max_retries": 1}
        if self._type is hm_type.HealthMonitorPOST:
            body.update({"type": constants.PROTOCOL_HTTP,
                         "pool_id": uuidutils.generate_uuid()})
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)

    def test_invalid_timeout(self):
        body = {"delay": 1, "timeout": "one", "max_retries": 1}
        if self._type is hm_type.HealthMonitorPOST:
            body.update({"type": constants.PROTOCOL_HTTP,
                         "pool_id": uuidutils.generate_uuid()})
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)

    def test_invalid_max_retries_down(self):
        body = {"delay": 1, "timeout": 1, "max_retries": "one"}
        if self._type is hm_type.HealthMonitorPOST:
            body.update({"type": constants.PROTOCOL_HTTP,
                         "pool_id": uuidutils.generate_uuid()})
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)

    def test_invalid_max_retries(self):
        body = {"delay": 1, "timeout": 1, "max_retries": "one"}
        if self._type is hm_type.HealthMonitorPOST:
            body.update({"type": constants.PROTOCOL_HTTP,
                         "pool_id": uuidutils.generate_uuid()})
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)

    def test_invalid_http_method(self):
        body = {"delay": 1, "timeout": 1, "max_retries": 1,
                "http_method": 1}
        if self._type is hm_type.HealthMonitorPOST:
            body.update({"type": constants.PROTOCOL_HTTP,
                         "pool_id": uuidutils.generate_uuid()})
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_url_path(self):
        body = {"delay": 1, "timeout": 1, "max_retries": 1, "url_path": 1}
        if self._type is hm_type.HealthMonitorPOST:
            body.update({"type": constants.PROTOCOL_HTTP,
                         "pool_id": uuidutils.generate_uuid()})
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)

    def test_invalid_url_path_with_url(self):
        body = {"delay": 1, "timeout": 1, "max_retries": 1,
                "url_path": 'https://www.openstack.org'}
        if self._type is hm_type.HealthMonitorPOST:
            body.update({"type": constants.PROTOCOL_HTTP,
                         "pool_id": uuidutils.generate_uuid()})
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)

    def test_invalid_url_path_no_leading_slash(self):
        body = {"delay": 1, "timeout": 1, "max_retries": 1,
                "url_path": 'blah'}
        if self._type is hm_type.HealthMonitorPOST:
            body.update({"type": constants.PROTOCOL_HTTP,
                         "pool_id": uuidutils.generate_uuid()})
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)

    def test_invalid_expected_codes(self):
        body = {"delay": 1, "timeout": 1, "max_retries": 1,
                "expected_codes": "lol"}
        if self._type is hm_type.HealthMonitorPOST:
            body.update({"type": constants.PROTOCOL_HTTP,
                         "pool_id": uuidutils.generate_uuid()})
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)


class TestHealthMonitorPOST(base.BaseTypesTest, TestHealthMonitor):

    _type = hm_type.HealthMonitorPOST

    def test_health_monitor(self):
        body = {"type": constants.HEALTH_MONITOR_HTTP, "delay": 1,
                "timeout": 1, "max_retries_down": 1, "max_retries": 1,
                "pool_id": uuidutils.generate_uuid()}
        hm = wsme_json.fromjson(self._type, body)
        self.assertTrue(hm.admin_state_up)

    def test_type_mandatory(self):
        body = {"delay": 80, "timeout": 1, "max_retries": 1,
                "pool_id": uuidutils.generate_uuid()}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_delay_mandatory(self):
        body = {"type": constants.HEALTH_MONITOR_HTTP, "timeout": 1,
                "max_retries": 1, "pool_id": uuidutils.generate_uuid()}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_timeout_mandatory(self):
        body = {"type": constants.HEALTH_MONITOR_HTTP, "delay": 1,
                "max_retries": 1, "pool_id": uuidutils.generate_uuid()}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_max_retries_mandatory(self):
        body = {"type": constants.HEALTH_MONITOR_HTTP, "delay": 1,
                "timeout": 1, "pool_id": uuidutils.generate_uuid()}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_default_health_monitor_values(self):
        # http_method = 'GET'
        # url_path = '/'
        # expected_codes = '200'
        # max_retries_down = 3
        # admin_state_up = True
        # The above are not required but should have the above example defaults
        body = {"type": constants.HEALTH_MONITOR_HTTP, "delay": 1,
                "timeout": 1, "max_retries": 1,
                "pool_id": uuidutils.generate_uuid()}
        hmpost = wsme_json.fromjson(self._type, body)
        self.assertEqual(wsme_types.Unset, hmpost.http_method)
        self.assertEqual(wsme_types.Unset, hmpost.url_path)
        self.assertEqual(wsme_types.Unset, hmpost.expected_codes)
        self.assertEqual(3, hmpost.max_retries_down)
        self.assertTrue(hmpost.admin_state_up)

    def test_url_path_with_query_and_fragment(self):
        url_path = "/v2/index?a=12,b=34#123dd"
        body = {"type": constants.HEALTH_MONITOR_HTTP, "delay": 1,
                "timeout": 1, "max_retries": 1,
                "pool_id": uuidutils.generate_uuid(),
                "url_path": url_path}
        hmpost = wsme_json.fromjson(self._type, body)
        self.assertEqual(wsme_types.Unset, hmpost.http_method)
        self.assertEqual(url_path, hmpost.url_path)
        self.assertEqual(wsme_types.Unset, hmpost.expected_codes)
        self.assertEqual(3, hmpost.max_retries_down)
        self.assertTrue(hmpost.admin_state_up)

    def test_non_uuid_project_id(self):
        body = {"type": constants.HEALTH_MONITOR_HTTP, "delay": 1,
                "timeout": 1, "max_retries_down": 1, "max_retries": 1,
                "project_id": "non-uuid",
                "pool_id": uuidutils.generate_uuid()}
        hm = wsme_json.fromjson(self._type, body)
        self.assertEqual(hm.project_id, body['project_id'])


class TestHealthMonitorPUT(base.BaseTypesTest, TestHealthMonitor):

    _type = hm_type.HealthMonitorPUT

    def test_health_monitor(self):
        body = {"http_method": constants.HEALTH_MONITOR_HTTP_METHOD_HEAD}
        hm = wsme_json.fromjson(self._type, body)
        self.assertEqual(wsme_types.Unset, hm.admin_state_up)
