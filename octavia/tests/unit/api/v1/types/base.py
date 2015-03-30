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

from octavia.api.v1.types import base as base_type
from octavia.common import constants
from octavia.tests.unit import base


def build_body(mandatory_fields, extra_attributes):
    body = {}
    for key in mandatory_fields:
        body[key] = mandatory_fields[key]
    for key in extra_attributes:
        body[key] = extra_attributes[key]
    return body


class BaseTypesTest(base.TestCase):
    _type = base_type.BaseType
    _mandatory_fields = {}


class BaseTestUuid(base.TestCase):

    def assert_uuid_attr(self, attr):
        kwargs = {attr: uuidutils.generate_uuid()}
        self._type(**kwargs)

    def assert_uuid_attr_fail_with_integer(self, attr):
        kwargs = {attr: 1}
        self.assertRaises(exc.InvalidInput, self._type, **kwargs)

    def assert_uuid_attr_fail_with_short_str(self, attr):
        kwargs = {attr: '12345'}
        self.assertRaises(exc.InvalidInput, self._type, **kwargs)

    def assert_uuid_attr_fail_with_shorter_than_uuid(self, attr):
        kwargs = {attr: uuidutils.generate_uuid()[1:]}
        self.assertRaises(exc.InvalidInput, self._type, **kwargs)

    def assert_uuid_attr_fail_with_longer_than_uuid(self, attr):
        kwargs = {attr: uuidutils.generate_uuid() + "0"}
        self.assertRaises(exc.InvalidInput, self._type, **kwargs)


class BaseTestString(base.TestCase):

    def _default_min_max_lengths(self, min_length=None, max_length=None):
        if max_length is None:
            if min_length is None:
                max_length = 255
                min_length = 2
            else:
                max_length = min_length + 1
        else:
            if min_length is None:
                min_length = max_length - 1
        return min_length, max_length

    def assert_string_attr(self, attr, min_length=None, max_length=None):
        min_length, max_length = self._default_min_max_lengths(min_length,
                                                               max_length)
        string_val = 'a' * (max_length - 1)
        kwargs = {attr: string_val}
        self._type(**kwargs)

    def assert_string_attr_min_length(self, attr, min_length):
        min_length, max_length = self._default_min_max_lengths(min_length)
        string_val = 'a' * (min_length - 1)
        kwargs = {attr: string_val}
        # No point in testing if min_length is <= 0
        if min_length > 0:
            self.assertRaises(exc.InvalidInput, self._type, **kwargs)

    def assert_string_attr_max_length(self, attr, max_length=None):
        min_length, max_length = self._default_min_max_lengths(max_length)
        string_val = 'a' * (max_length + 1)
        kwargs = {attr: string_val}
        self.assertRaises(exc.InvalidInput, self._type, **kwargs)


class BaseTestBool(base.TestCase):

    def assert_bool_attr(self, attr):
        kwargs = {attr: True}
        self.assertIsNotNone(self._type(**kwargs))
        kwargs = {attr: False}
        self.assertIsNotNone(self._type(**kwargs))

    def assert_bool_attr_non_bool(self, attr):
        kwargs = {attr: 'test'}
        self.assertRaises(exc.InvalidInput, self._type, **kwargs)


class TestIdMixin(BaseTestUuid):
    id_attr = 'id'

    def test_id(self):
        self.assert_uuid_attr(self.id_attr)
        self.assert_uuid_attr_fail_with_integer(self.id_attr)
        self.assert_uuid_attr_fail_with_short_str(self.id_attr)
        self.assert_uuid_attr_fail_with_shorter_than_uuid(self.id_attr)
        self.assert_uuid_attr_fail_with_longer_than_uuid(self.id_attr)

    def test_id_readonly(self):
        body = build_body(self._mandatory_fields,
                          {self.id_attr: uuidutils.generate_uuid()})
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)


class TestTenantIdMixin(BaseTestUuid):
    tenant_id_attr = 'tenant_id'

    def test_tenant_id(self):
        self.assert_uuid_attr(self.tenant_id_attr)
        self.assert_uuid_attr_fail_with_integer(self.tenant_id_attr)
        self.assert_uuid_attr_fail_with_short_str(self.tenant_id_attr)
        self.assert_uuid_attr_fail_with_shorter_than_uuid(self.tenant_id_attr)
        self.assert_uuid_attr_fail_with_longer_than_uuid(self.tenant_id_attr)

    def test_tenant_id_readonly(self):
        body = build_body(self._mandatory_fields,
                          {self.tenant_id_attr: uuidutils.generate_uuid()})
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)


class TestNameMixin(BaseTestString):
    name_attr = 'name'

    def test_name(self):
        self.assert_string_attr(self.name_attr, min_length=0, max_length=255)
        self.assert_string_attr_min_length(self.name_attr, 0)
        self.assert_string_attr_max_length(self.name_attr, 255)

    def test_editable_name(self):
        name = "Name"
        body = build_body(self._mandatory_fields, {self.name_attr: name})
        type_instance = wsme_json.fromjson(self._type, body)
        self.assertEqual(name, type_instance.name)


class TestDescriptionMixin(BaseTestString):
    description_attr = 'description'

    def test_description(self):
        self.assert_string_attr(self.description_attr, min_length=0,
                                max_length=255)
        self.assert_string_attr_min_length(self.description_attr, 0)
        self.assert_string_attr_max_length(self.description_attr, 255)

    def test_editable_description(self):
        description = "Description"
        body = build_body(self._mandatory_fields,
                          {self.description_attr: description})
        type_instance = wsme_json.fromjson(self._type, body)
        self.assertEqual(description, type_instance.description)


class TestEnabledMixin(BaseTestBool):
    enabled_attr = 'enabled'

    def test_enabled(self):
        self.assert_bool_attr(self.enabled_attr)
        self.assert_bool_attr_non_bool(self.enabled_attr)

    def test_default_enabled_true(self):
        body = build_body(self._mandatory_fields, {})
        type_instance = wsme_json.fromjson(self._type, body)
        self.assertTrue(type_instance.enabled)

    def test_editable_enabled(self):
        body = build_body(self._mandatory_fields, {"enabled": False})
        type_instance = wsme_json.fromjson(self._type, body)
        self.assertFalse(type_instance.enabled)


class TestProvisioningStatusMixin(BaseTestString):
    provisioning_attr = 'provisioning_status'

    def test_provisioning_status(self):
        self.assert_string_attr(self.provisioning_attr, min_length=0,
                                max_length=16)
        self.assert_string_attr_min_length(self.provisioning_attr, 0)
        self.assert_string_attr_max_length(self.provisioning_attr, 16)

    def test_provisioning_status_readonly(self):
        status = constants.ACTIVE
        body = build_body(self._mandatory_fields,
                          {self.provisioning_attr: status})
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)


class TestOperatingStatusMixin(BaseTestString):
    operating_attr = 'operating_status'

    def test_operating_status(self):
        self.assert_string_attr(self.operating_attr, min_length=0,
                                max_length=16)
        self.assert_string_attr_min_length(self.operating_attr, 0)
        self.assert_string_attr_max_length(self.operating_attr, 16)

    def test_operating_status_readonly(self):
        status = constants.ONLINE
        body = build_body(self._mandatory_fields,
                          {self.operating_attr: status})
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson,
                          self._type, body)
