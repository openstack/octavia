# Copyright (c) 2018 China Telecom Corporation
# All Rights Reserved.
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

from octavia.api.v2.types import quotas as quota_type
from octavia.common import constants
from octavia.tests.unit.api.v2.types import base


class TestQuotaPut(base.BaseTypesTest):

    _type = quota_type.QuotaPUT

    def test_quota(self):
        body = {'quota': {'loadbalancer': 5}}
        quota = wsme_json.fromjson(self._type, body)
        self.assertEqual(wsme_types.Unset, quota.quota.listener)
        self.assertEqual(wsme_types.Unset, quota.quota.pool)
        self.assertEqual(wsme_types.Unset, quota.quota.member)
        self.assertEqual(wsme_types.Unset, quota.quota.healthmonitor)
        self.assertEqual(wsme_types.Unset, quota.quota.l7policy)
        self.assertEqual(wsme_types.Unset, quota.quota.l7rule)

    def test_invalid_quota(self):
        body = {'quota': {'loadbalancer': constants.MAX_QUOTA + 1}}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)
        body = {'quota': {'loadbalancer': constants.MIN_QUOTA - 1}}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)

        body = {'quota': {'listener': constants.MAX_QUOTA + 1}}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)
        body = {'quota': {'listener': constants.MIN_QUOTA - 1}}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)

        body = {'quota': {'pool': constants.MAX_QUOTA + 1}}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)
        body = {'quota': {'pool': constants.MIN_QUOTA - 1}}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)

        body = {'quota': {'member': constants.MAX_QUOTA + 1}}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)
        body = {'quota': {'member': constants.MIN_QUOTA - 1}}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)

        body = {'quota': {'healthmonitor': constants.MAX_QUOTA + 1}}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)
        body = {'quota': {'healthmonitor': constants.MIN_QUOTA - 1}}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)

        body = {'quota': {'l7policy': constants.MAX_QUOTA + 1}}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)
        body = {'quota': {'l7policy': constants.MIN_QUOTA - 1}}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)

        body = {'quota': {'l7rule': constants.MAX_QUOTA + 1}}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)
        body = {'quota': {'l7rule': constants.MIN_QUOTA - 1}}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)
