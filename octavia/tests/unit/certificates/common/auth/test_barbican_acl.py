# Copyright 2014 Rackspace
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

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture

import octavia.certificates.common.auth.barbican_acl as barbican_acl
import octavia.certificates.manager.barbican as barbican_cert_mgr
from octavia.common import keystone
import octavia.tests.unit.base as base

CONF = cfg.CONF


class TestBarbicanACLAuth(base.TestCase):

    def setUp(self):
        # Reset the client
        keystone._SESSION = None
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group="certificates", region_name=None)
        conf.config(group="certificates", endpoint_type='publicURL')
        super(TestBarbicanACLAuth, self).setUp()

    @mock.patch('keystoneauth1.session.Session', mock.Mock())
    def test_get_barbican_client(self):
        # Mock out the keystone session and get the client
        acl_auth_object = barbican_acl.BarbicanACLAuth()
        bc1 = acl_auth_object.get_barbican_client()

        # Our returned object should have elements that proves it is a real
        # Barbican client object. We shouldn't use `isinstance` because that's
        # an evil pattern, instead we can check for very unique things in the
        # stable client API like "register_consumer", since this should fairly
        # reliably prove we're dealing with a Barbican client.
        self.assertTrue(hasattr(bc1, 'containers') and
                        hasattr(bc1.containers, 'register_consumer'))

        # Getting the session again with new class should get the same object
        acl_auth_object2 = barbican_acl.BarbicanACLAuth()
        bc2 = acl_auth_object2.get_barbican_client()
        self.assertIs(bc1, bc2)

    def test_load_auth_driver(self):
        bcm = barbican_cert_mgr.BarbicanCertManager()
        self.assertIsInstance(bcm.auth, barbican_acl.BarbicanACLAuth)
