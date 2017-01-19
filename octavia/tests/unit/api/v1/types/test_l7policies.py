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

from octavia.api.v1.types import l7policy as l7policy_type
from octavia.common import constants
from octavia.tests.unit.api.common import base


class TestL7PolicyPOST(base.BaseTypesTest):

    _type = l7policy_type.L7PolicyPOST

    def test_l7policy(self):
        body = {"action": constants.L7POLICY_ACTION_REJECT}
        l7policy = wsme_json.fromjson(self._type, body)
        self.assertEqual(constants.MAX_POLICY_POSITION, l7policy.position)
        self.assertEqual(wsme_types.Unset, l7policy.redirect_url)
        self.assertEqual(wsme_types.Unset, l7policy.redirect_pool_id)
        self.assertTrue(l7policy.enabled)

    def test_action_mandatory(self):
        body = {}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_action(self):
        body = {"action": "test"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_with_redirect_url(self):
        url = "http://www.example.com/"
        body = {"action": constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                "redirect_url": url}
        l7policy = wsme_json.fromjson(self._type, body)
        self.assertEqual(constants.MAX_POLICY_POSITION, l7policy.position)
        self.assertEqual(url, l7policy.redirect_url)
        self.assertEqual(wsme_types.Unset, l7policy.redirect_pool_id)

    def test_invalid_position(self):
        body = {"action": constants.L7POLICY_ACTION_REJECT,
                "position": "notvalid"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_enabled(self):
        body = {"action": constants.L7POLICY_ACTION_REJECT,
                "enabled": "notvalid"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_url(self):
        body = {"action": constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                "redirect_url": "notvalid"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)


class TestL7PolicyPUT(base.BaseTypesTest):

    _type = l7policy_type.L7PolicyPUT

    def test_l7policy(self):
        body = {"action": constants.L7POLICY_ACTION_REJECT,
                "position": 0}
        l7policy = wsme_json.fromjson(self._type, body)
        self.assertEqual(0, l7policy.position)
        self.assertEqual(wsme_types.Unset, l7policy.redirect_url)
        self.assertEqual(wsme_types.Unset, l7policy.redirect_pool_id)

    def test_invalid_position(self):
        body = {"position": "test"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)

    def test_invalid_action(self):
        body = {"action": "test"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)
