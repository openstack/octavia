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
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture

import octavia.certificates.common.auth.barbican_acl as barbican_acl
import octavia.certificates.manager.barbican as barbican_cert_mgr
from octavia.common import keystone
import octavia.tests.unit.base as base

CONF = cfg.CONF


class TestBarbicanACLAuth(base.TestCase):

    def setUp(self):
        super().setUp()
        # Reset the client
        keystone._SESSION = None
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.region_name = 'RegionOne'
        self.endpoint_type = 'publicURL'
        self.endpoint = 'barbican'
        self.conf.config(group="certificates", region_name=self.region_name)
        self.conf.config(group="certificates",
                         endpoint_type=self.endpoint_type)
        self.conf.config(group="certificates", endpoint=self.endpoint)

    @mock.patch('barbicanclient.client.Client')
    @mock.patch('keystoneauth1.session.Session')
    def test_get_barbican_client(self, mock_ksession, mock_client):
        session_mock = mock.Mock()
        mock_ksession.return_value = session_mock
        mock_client.return_value = mock.MagicMock()

        # Mock out the keystone session and get the client
        acl_auth_object = barbican_acl.BarbicanACLAuth()
        bc1 = acl_auth_object.get_barbican_client()

        mock_client.assert_called_once_with(session=session_mock,
                                            region_name=self.region_name,
                                            interface=self.endpoint_type)

        mock_client.reset_mock()
        # Getting the session again with new class should get the same object
        acl_auth_object2 = barbican_acl.BarbicanACLAuth()
        bc2 = acl_auth_object2.get_barbican_client()
        self.assertIs(bc1, bc2)

        mock_client.assert_not_called()

    def test_load_auth_driver(self):
        bcm = barbican_cert_mgr.BarbicanCertManager()
        self.assertIsInstance(bcm.auth, barbican_acl.BarbicanACLAuth)

    @mock.patch('barbicanclient.client.Client')
    @mock.patch('octavia.common.keystone.KeystoneSession')
    def test_ensure_secret_access(self, mock_ksession, mock_client):
        service_user_id = 'uuid1'
        client_mock = mock.MagicMock()
        mock_client.return_value = client_mock
        mock_ksession().get_service_user_id.return_value = service_user_id

        mock_acl = mock.MagicMock()
        client_mock.acls.get.return_value = mock_acl

        mock_read = mock.MagicMock()
        mock_read.users = []
        mock_acl.get.return_value = mock_read

        acl_auth_object = barbican_acl.BarbicanACLAuth()
        acl_auth_object.ensure_secret_access(mock.Mock(), mock.Mock())
        mock_acl.submit.assert_called_once()
        self.assertEqual([service_user_id], mock_read.users)

    @mock.patch('barbicanclient.client.Client')
    @mock.patch('octavia.common.keystone.KeystoneSession')
    def test_revoke_secret_access(self, mock_ksession, mock_client):
        service_user_id = 'uuid1'

        client_mock = mock.MagicMock()
        mock_client.return_value = client_mock
        mock_ksession().get_service_user_id.return_value = service_user_id

        mock_acl = mock.MagicMock()
        client_mock.acls.get.return_value = mock_acl

        mock_read = mock.MagicMock()
        mock_read.users = [service_user_id]
        mock_acl.get.return_value = mock_read

        acl_auth_object = barbican_acl.BarbicanACLAuth()
        acl_auth_object.revoke_secret_access(mock.Mock(), mock.Mock())
        mock_acl.submit.assert_called_once()

    @mock.patch('octavia.common.keystone.KeystoneSession')
    @mock.patch('barbicanclient.client.Client')
    @mock.patch('keystoneauth1.session.Session')
    def test_get_barbican_client_user_auth(self, mock_ksession, mock_client,
                                           mock_keystone):
        session_mock = mock.MagicMock()
        mock_ksession.return_value = session_mock
        acl_auth_object = barbican_acl.BarbicanACLAuth()
        acl_auth_object.get_barbican_client_user_auth(mock.Mock())

        mock_client.assert_called_once_with(session=session_mock,
                                            endpoint=self.endpoint)
