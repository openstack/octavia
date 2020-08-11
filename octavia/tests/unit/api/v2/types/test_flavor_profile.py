#    Copyright 2017 Walmart Stores Inc.
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

from octavia.api.v2.types import flavor_profile as fp_type
from octavia.common import constants
from octavia.tests.unit.api.common import base


class TestFlavorProfile(object):

    _type = None

    def test_flavor_profile(self):
        body = {"name": "test_name", "provider_name": "test1",
                constants.FLAVOR_DATA: '{"hello": "world"}'}
        flavor = wsme_json.fromjson(self._type, body)
        self.assertEqual(flavor.name, body["name"])

    def test_invalid_name(self):
        body = {"name": 0}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_name_length(self):
        body = {"name": "x" * 256}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_provider_name_length(self):
        body = {"name": "x" * 250,
                "provider_name": "X" * 256}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)

    def test_name_mandatory(self):
        body = {"provider_name": "test1",
                constants.FLAVOR_DATA: '{"hello": "world"}'}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_provider_name_mandatory(self):
        body = {"name": "test_name",
                constants.FLAVOR_DATA: '{"hello": "world"}'}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_meta_mandatory(self):
        body = {"name": "test_name", "provider_name": "test1"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)


class TestFlavorProfilePOST(base.BaseTypesTest, TestFlavorProfile):

    _type = fp_type.FlavorProfilePOST
