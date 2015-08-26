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

from octavia.api.v1.types import health_monitor as hm_type
from octavia.common import constants
from octavia.tests.unit.api.v1.types import base


class TestHealthMonitor(object):

    _type = None

    def test_invalid_type(self):
        body = {"type": 10, "delay": 1, "timeout": 1, "fall_threshold": 1}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_delay(self):
        body = {"type": constants.HEALTH_MONITOR_HTTP, "delay": "one",
                "timeout": 1, "fall_threshold": 1}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)

    def test_invalid_timeout(self):
        body = {"type": constants.HEALTH_MONITOR_HTTP, "delay": 1,
                "timeout": "one", "fall_threshold": 1}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)

    def test_invalid_fall_threshold(self):
        body = {"type": constants.HEALTH_MONITOR_HTTP, "delay": 1,
                "timeout": 1, "fall_threshold": "one"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)

    def test_invalid_rise_threshold(self):
        body = {"type": constants.HEALTH_MONITOR_HTTP, "delay": 1,
                "timeout": 1, "fall_threshold": 1, "rise_threshold": "one"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)

    def test_invalid_http_method(self):
        body = {"type": constants.HEALTH_MONITOR_HTTP, "delay": 1,
                "timeout": 1, "fall_threshold": 1, "http_method": 1}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_url_path(self):
        body = {"type": constants.HEALTH_MONITOR_HTTP, "delay": 1,
                "timeout": 1, "fall_threshold": 1, "url_path": 1}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_expected_codes(self):
        body = {"type": constants.HEALTH_MONITOR_HTTP, "delay": 1,
                "timeout": 1, "fall_threshold": 1, "expected_codes": 1}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)


class TestHealthMonitorPOST(base.BaseTypesTest, TestHealthMonitor):

    _type = hm_type.HealthMonitorPOST

    def test_health_monitor(self):
        body = {"type": constants.HEALTH_MONITOR_HTTP, "delay": 1,
                "timeout": 1, "fall_threshold": 1, "rise_threshold": 1}
        hm = wsme_json.fromjson(self._type, body)
        self.assertTrue(hm.enabled)

    def test_type_mandatory(self):
        body = {"delay": 80, "timeout": 1, "fall_threshold": 1,
                "rise_threshold": 1}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_delay_mandatory(self):
        body = {"type": constants.HEALTH_MONITOR_HTTP, "timeout": 1,
                "fall_threshold": 1, "rise_threshold": 1}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_timeout_mandatory(self):
        body = {"type": constants.HEALTH_MONITOR_HTTP, "delay": 1,
                "fall_threshold": 1, "rise_threshold": 1}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_fall_threshold_mandatory(self):
        body = {"type": constants.HEALTH_MONITOR_HTTP, "delay": 1,
                "timeout": 1, "rise_threshold": 1}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_rise_threshold_mandatory(self):
        body = {"type": constants.HEALTH_MONITOR_HTTP, "delay": 1,
                "timeout": 1, "fall_threshold": 1}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)


class TestHealthMonitorPUT(base.BaseTypesTest, TestHealthMonitor):

    _type = hm_type.HealthMonitorPUT

    def test_health_monitor(self):
        body = {"http_method": constants.PROTOCOL_HTTPS}
        hm = wsme_json.fromjson(self._type, body)
        self.assertEqual(wsme_types.Unset, hm.enabled)
