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

from octavia.api.v1.types import load_balancer as lb_type
from octavia.tests.unit.api.v1.types import base


class TestLoadBalancer(object):

    _type = None

    def test_load_balancer(self):
        body = {"name": "test_name", "description": "test_description",
                "vip": {}}
        lb = wsme_json.fromjson(self._type, body)
        self.assertTrue(lb.enabled)

    def test_invalid_name(self):
        body = {"name": 0}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_name_length(self):
        body = {"name": "x" * 256}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_description(self):
        body = {"description": 0}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_description_length(self):
        body = {"name": "x" * 256}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_enabled(self):
        body = {"enabled": "notvalid"}
        self.assertRaises(ValueError, wsme_json.fromjson, self._type,
                          body)


class TestLoadBalancerPOST(base.BaseTypesTest, TestLoadBalancer):

    _type = lb_type.LoadBalancerPOST

    def test_vip_mandatory(self):
        body = {"name": "test"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)


class TestLoadBalancerPUT(base.BaseTypesTest, TestLoadBalancer):

    _type = lb_type.LoadBalancerPUT

    def test_load_balancer(self):
        body = {"name": "test_name", "description": "test_description"}
        lb = wsme_json.fromjson(self._type, body)
        self.assertEqual(wsme_types.Unset, lb.enabled)


class TestVip(base.BaseTypesTest):

    _type = lb_type.VIP

    def test_vip(self):
        body = {"ip_address": "10.0.0.1",
                "port_id": uuidutils.generate_uuid()}
        wsme_json.fromjson(self._type, body)

    def test_invalid_ip_address(self):
        body = {"ip_address": uuidutils.generate_uuid()}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_port_id(self):
        body = {"port_id": "invalid_uuid"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)

    def test_invalid_subnet_id(self):
        body = {"subnet_id": "invalid_uuid"}
        self.assertRaises(exc.InvalidInput, wsme_json.fromjson, self._type,
                          body)
