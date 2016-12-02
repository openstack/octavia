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

from oslo_utils import uuidutils
from wsme import exc
from wsme.rest import json as wsme_json
from wsme import types as wsme_types

from octavia.api.v2.types import l7policy as l7policy_type
from octavia.common import constants
from octavia.tests.unit.api.common import base


class TestL7PolicyPOST(base.BaseTypesTest):

    _type = l7policy_type.L7PolicyPOST

    def setUp(self):
        super(TestL7PolicyPOST, self).setUp()
        self.listener_id = uuidutils.generate_uuid()

    def test_l7policy(self):
        body = {"listener_id": self.listener_id,
                "action": constants.L7POLICY_ACTION_REJECT}
        l7policy = wsme_json.fromjson(self._type, body)
        self.assertEqual(self.listener_id, l7policy.listener_id)
        self.assertEqual(constants.MAX_POLICY_POSITION, l7policy.position)
        self.assertEqual(wsme_types.Unset, l7policy.redirect_url)
        self.assertEqual(wsme_types.Unset, l7policy.redirect_pool_id)
        self.assertTrue(l7policy.admin_state_up)

    def test_action_mandatory(self):
        body = {"listener_id": self.listener_id}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_listener_id_mandatory(self):
        body = {"action": constants.L7POLICY_ACTION_REJECT}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_action(self):
        body = {"listener_id": self.listener_id,
                "action": "test"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_with_redirect_url(self):
        url = "http://www.example.com/"
        body = {"listener_id": self.listener_id,
                "action": constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                "redirect_url": url}
        l7policy = wsme_json.fromjson(self._type, body)
        self.assertEqual(constants.MAX_POLICY_POSITION, l7policy.position)
        self.assertEqual(url, l7policy.redirect_url)
        self.assertEqual(wsme_types.Unset, l7policy.redirect_pool_id)

    def test_invalid_position(self):
        body = {"listener_id": self.listener_id,
                "action": constants.L7POLICY_ACTION_REJECT,
                "position": "notvalid"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type,
                          body)

    def test_l7policy_min_position(self):
        body = {"listener_id": self.listener_id,
                "action": constants.L7POLICY_ACTION_REJECT,
                "position": constants.MIN_POLICY_POSITION - 1}
        self.assertRaises(
            exc.InvalidInput, wsme_json.fromjson, self._type, body)
        body = {"listener_id": self.listener_id,
                "action": constants.L7POLICY_ACTION_REJECT,
                "position": constants.MIN_POLICY_POSITION}
        l7policy = wsme_json.fromjson(self._type, body)
        self.assertEqual(constants.MIN_POLICY_POSITION, l7policy.position)

    def test_l7policy_max_position(self):
        body = {"listener_id": self.listener_id,
                "action": constants.L7POLICY_ACTION_REJECT,
                "position": constants.MAX_POLICY_POSITION + 1}
        self.assertRaises(
            exc.InvalidInput, wsme_json.fromjson, self._type, body)
        body = {"listener_id": self.listener_id,
                "action": constants.L7POLICY_ACTION_REJECT,
                "position": constants.MAX_POLICY_POSITION}
        l7policy = wsme_json.fromjson(self._type, body)
        self.assertEqual(constants.MAX_POLICY_POSITION, l7policy.position)

    def test_invalid_admin_state_up(self):
        body = {"listener_id": self.listener_id,
                "action": constants.L7POLICY_ACTION_REJECT,
                "admin_state_up": "notvalid"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_url(self):
        body = {"listener_id": self.listener_id,
                "action": constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                "redirect_url": "notvalid"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)


class TestL7PolicyPUT(base.BaseTypesTest):

    _type = l7policy_type.L7PolicyPUT

    def test_l7policy(self):
        body = {"action": constants.L7POLICY_ACTION_REJECT,
                "position": constants.MIN_POLICY_POSITION}
        l7policy = wsme_json.fromjson(self._type, body)
        self.assertEqual(constants.MIN_POLICY_POSITION, l7policy.position)
        self.assertEqual(wsme_types.Unset, l7policy.redirect_url)
        self.assertEqual(wsme_types.Unset, l7policy.redirect_pool_id)

    def test_l7policy_min_position(self):
        body = {"position": constants.MIN_POLICY_POSITION - 1}
        self.assertRaises(
            exc.InvalidInput, wsme_json.fromjson, self._type, body)
        body = {"position": constants.MIN_POLICY_POSITION}
        l7policy = wsme_json.fromjson(self._type, body)
        self.assertEqual(constants.MIN_POLICY_POSITION, l7policy.position)

    def test_l7policy_max_position(self):
        body = {"position": constants.MAX_POLICY_POSITION + 1}
        self.assertRaises(
            exc.InvalidInput, wsme_json.fromjson, self._type, body)
        body = {"position": constants.MAX_POLICY_POSITION}
        l7policy = wsme_json.fromjson(self._type, body)
        self.assertEqual(constants.MAX_POLICY_POSITION, l7policy.position)

    def test_invalid_position(self):
        body = {"position": "test"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type, body)

    def test_invalid_action(self):
        body = {"action": "test"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)
