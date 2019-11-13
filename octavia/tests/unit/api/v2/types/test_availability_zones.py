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

from oslo_utils import uuidutils
from wsme import exc
from wsme.rest import json as wsme_json

from octavia.api.v2.types import availability_zones as availability_zone_type
from octavia.tests.unit.api.common import base


class TestAvailabilityZone(object):

    _type = None

    def test_availability_zone(self):
        body = {"name": "test_name", "description": "test_description",
                "availability_zone_profile_id": uuidutils.generate_uuid()}
        availability_zone = wsme_json.fromjson(self._type, body)
        self.assertTrue(availability_zone.enabled)

    def test_invalid_name(self):
        body = {"name": 0,
                "availability_zone_profile_id": uuidutils.generate_uuid()}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_name_length(self):
        body = {"name": "x" * 256,
                "availability_zone_profile_id": uuidutils.generate_uuid()}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_description(self):
        body = {"availability_zone_profile_id": uuidutils.generate_uuid(),
                "description": 0, "name": "test"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_description_length(self):
        body = {"name": "x" * 250,
                "availability_zone_profile_id": uuidutils.generate_uuid(),
                "description": "0" * 256}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_enabled(self):
        body = {"name": "test_name",
                "availability_zone_profile_id": uuidutils.generate_uuid(),
                "enabled": "notvalid"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type,
                          body)

    def test_name_mandatory(self):
        body = {"description": "xyz",
                "availability_zone_profile_id": uuidutils.generate_uuid(),
                "enabled": True}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_availability_zone_profile_id_mandatory(self):
        body = {"name": "test_name"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)


class TestAvailabilityZonePOST(base.BaseTypesTest, TestAvailabilityZone):

    _type = availability_zone_type.AvailabilityZonePOST

    def test_non_uuid_project_id(self):
        body = {"name": "test_name", "description": "test_description",
                "availability_zone_profile_id": uuidutils.generate_uuid()}
        lb = wsme_json.fromjson(self._type, body)
        self.assertEqual(lb.availability_zone_profile_id,
                         body['availability_zone_profile_id'])
