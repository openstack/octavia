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

from barbicanclient.v1 import acls
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
        super(TestBarbicanACLAuth, self).setUp()
        # Reset the client
        keystone._SESSION = None
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(group="certificates", region_name='RegionOne')
        self.conf.config(group="certificates", endpoint_type='publicURL')

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

    @mock.patch('barbicanclient.v1.acls.ACLManager.get')
    @mock.patch('octavia.common.keystone.KeystoneSession')
    def test_ensure_secret_access(self, mock_ksession, mock_aclm):
        acl = mock.MagicMock(spec=acls.SecretACL)
        mock_aclm.return_value = acl

        acl_auth_object = barbican_acl.BarbicanACLAuth()
        acl_auth_object.ensure_secret_access(mock.Mock(), mock.Mock())
        acl.submit.assert_called_once()

    @mock.patch('barbicanclient.v1.acls.ACLManager.get')
    @mock.patch('octavia.common.keystone.KeystoneSession')
    def test_revoke_secret_access(self, mock_ksession, mock_aclm):
        service_user_id = 'uuid1'

        mock_ksession().get_service_user_id.return_value = service_user_id
        acl = mock.MagicMock(spec=acls.SecretACL)
        poacl = mock.MagicMock(spec=acls._PerOperationACL)
        type(poacl).users = mock.PropertyMock(return_value=[service_user_id])
        acl.get.return_value = poacl
        mock_aclm.return_value = acl

        acl_auth_object = barbican_acl.BarbicanACLAuth()
        acl_auth_object.revoke_secret_access(mock.Mock(), mock.Mock())
        acl.submit.assert_called_once()

    @mock.patch('octavia.common.keystone.KeystoneSession')
    def test_get_barbican_client_user_auth(self, mock_ksession):
        acl_auth_object = barbican_acl.BarbicanACLAuth()
        bc = acl_auth_object.get_barbican_client_user_auth(mock.Mock())
        self.assertTrue(hasattr(bc, 'containers') and
                        hasattr(bc.containers, 'register_consumer'))
        self.assertEqual('publicURL', bc.client.interface)
        self.assertEqual('RegionOne', bc.client.region_name)
