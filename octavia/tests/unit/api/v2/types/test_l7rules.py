#    Copyright 2016 Blue Box, an IBM Company
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

from octavia.api.v1.types import l7rule as l7rule_type
from octavia.common import constants
from octavia.tests.unit.api.common import base


class TestL7RulePOST(base.BaseTypesTest):

    _type = l7rule_type.L7RulePOST

    def test_l7rule(self):
        body = {"type": constants.L7RULE_TYPE_PATH,
                "compare_type": constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                "value": "/api"}
        l7rule = wsme_json.fromjson(self._type, body)
        self.assertEqual(wsme_types.Unset, l7rule.key)
        self.assertFalse(l7rule.invert)

    def test_type_mandatory(self):
        body = {"compare_type": constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                "value": "/api"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_compare_type_mandatory(self):
        body = {"type": constants.L7RULE_TYPE_PATH,
                "value": "/api"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_value_mandatory(self):
        body = {"type": constants.L7RULE_TYPE_PATH,
                "compare_type": constants.L7RULE_COMPARE_TYPE_STARTS_WITH}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_type(self):
        body = {"type": "notvalid",
                "compare_type": constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                "value": "/api"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_compare_type(self):
        body = {"type": constants.L7RULE_TYPE_PATH,
                "compare_type": "notvalid",
                "value": "/api"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_invert(self):
        body = {"type": constants.L7RULE_TYPE_PATH,
                "compare_type": constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                "value": "/api",
                "invert": "notvalid"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type,
                          body)


class TestL7RulePUT(base.BaseTypesTest):

    _type = l7rule_type.L7RulePUT

    def test_l7rule(self):
        body = {"type": constants.L7RULE_TYPE_PATH,
                "compare_type": constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                "value": "/api"}
        l7rule = wsme_json.fromjson(self._type, body)
        self.assertEqual(wsme_types.Unset, l7rule.key)
        self.assertFalse(l7rule.invert)

    def test_invalid_type(self):
        body = {"type": "notvalid",
                "compare_type": constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                "value": "/api"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_compare_type(self):
        body = {"type": constants.L7RULE_TYPE_PATH,
                "compare_type": "notvalid",
                "value": "/api"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_invert(self):
        body = {"type": constants.L7RULE_TYPE_PATH,
                "compare_type": constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                "value": "/api",
                "invert": "notvalid"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type,
                          body)
