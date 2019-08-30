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

import uuid

from barbicanclient.v1 import secrets
import mock

import octavia.certificates.common.barbican as barbican_common
import octavia.certificates.common.cert as cert
import octavia.certificates.manager.barbican as barbican_cert_mgr
from octavia.common import exceptions
import octavia.tests.unit.base as base
import octavia.tests.unit.common.sample_configs.sample_certs as sample


PROJECT_ID = "12345"


class TestBarbicanManager(base.TestCase):

    def setUp(self):
        # Make a fake Secret and contents
        self.barbican_endpoint = 'http://localhost:9311/v1'
        self.secret_uuid = uuid.uuid4()

        self.secret_ref = '{0}/secrets/{1}'.format(
            self.barbican_endpoint, self.secret_uuid
        )

        self.name = 'My Fancy Cert'
        self.secret_pkcs12 = secrets.Secret(
            api=mock.MagicMock(),
            payload=sample.PKCS12_BUNDLE
        )

        self.fake_secret = 'Fake secret'
        self.secret = secrets.Secret(api=mock.MagicMock(),
                                     payload=self.fake_secret)
        self.empty_secret = mock.Mock(spec=secrets.Secret)

        # Mock out the client
        self.bc = mock.Mock()
        barbican_auth = mock.Mock(spec=barbican_common.BarbicanAuth)
        barbican_auth.get_barbican_client.return_value = self.bc

        self.cert_manager = barbican_cert_mgr.BarbicanCertManager()
        self.cert_manager.auth = barbican_auth

        self.context = mock.Mock()
        self.context.project_id = PROJECT_ID

        super(TestBarbicanManager, self).setUp()

    def test_store_cert(self):
        # Mock out the client
        self.bc.secrets.create.return_value = (
            self.empty_secret)

        # Attempt to store a cert
        secret_ref = self.cert_manager.store_cert(
            context=self.context,
            certificate=sample.X509_CERT,
            private_key=sample.X509_CERT_KEY,
            intermediates=sample.X509_IMDS,
            name=self.name
        )

        self.assertEqual(secret_ref, self.empty_secret.secret_ref)

        # create_secret should be called once with our data
        calls = [
            mock.call(payload=mock.ANY, expiration=None,
                      name=self.name)
        ]
        self.bc.secrets.create.assert_has_calls(calls)

        # Container should be stored once
        self.empty_secret.store.assert_called_once_with()

    def test_store_cert_failure(self):
        # Mock out the client
        self.bc.secrets.create.return_value = (
            self.empty_secret)

        self.empty_secret.store.side_effect = ValueError()

        # Attempt to store a cert
        self.assertRaises(
            ValueError,
            self.cert_manager.store_cert,
            context=self.context,
            certificate=sample.X509_CERT,
            private_key=sample.X509_CERT_KEY,
            intermediates=sample.X509_IMDS,
            name=self.name
        )

        # create_certificate should be called once
        self.assertEqual(1, self.bc.secrets.create.call_count)

        # Container should be stored once
        self.empty_secret.store.assert_called_once_with()

    def test_get_cert(self):
        # Mock out the client
        self.bc.secrets.get.return_value = self.secret_pkcs12

        # Get the secret data
        data = self.cert_manager.get_cert(
            context=self.context,
            cert_ref=self.secret_ref,
            resource_ref=self.secret_ref,
            service_name='Octavia'
        )

        # 'get_secret' should be called once with the secret_ref
        self.bc.secrets.get.assert_called_once_with(
            secret_ref=self.secret_ref
        )

        # The returned data should be a Cert object with the correct values
        self.assertIsInstance(data, cert.Cert)
        self.assertEqual(sample.X509_CERT_KEY, data.get_private_key())
        self.assertEqual(sample.X509_CERT, data.get_certificate())
        self.assertEqual(sorted(sample.X509_IMDS_LIST),
                         sorted(data.get_intermediates()))
        self.assertIsNone(data.get_private_key_passphrase())

    def test_delete_cert_legacy(self):
        # Attempt to deregister as a consumer
        self.cert_manager.delete_cert(
            context=self.context,
            cert_ref=self.secret_ref,
            resource_ref=self.secret_ref,
            service_name='Octavia'
        )

        # remove_consumer should be called once with the container_ref (legacy)
        self.bc.containers.remove_consumer.assert_called_once_with(
            container_ref=self.secret_ref,
            url=self.secret_ref,
            name='Octavia'
        )

    def test_set_acls(self):
        # if used pkcs12 certificate containers.get raises exception
        self.bc.containers.get.side_effect = Exception("container not found")
        self.cert_manager.set_acls(
            context=self.context,
            cert_ref=self.secret_ref
        )

        # our mock_bc should have one call to ensure_secret_access
        self.cert_manager.auth.ensure_secret_access.assert_called_once_with(
            self.context, self.secret_ref
        )

    def test_unset_acls(self):
        # if used pkcs12 certificate containers.get raises exception
        self.bc.containers.get.side_effect = Exception("container not found")
        self.cert_manager.unset_acls(
            context=self.context,
            cert_ref=self.secret_ref
        )

        # our mock_bc should have one call to revoke_secret_access
        self.cert_manager.auth.revoke_secret_access.assert_called_once_with(
            self.context, self.secret_ref
        )

    def test_get_secret(self):
        # Mock out the client
        self.bc.secrets.get.side_effect = [self.secret, Exception]

        # Get the secret data
        data = self.cert_manager.get_secret(
            context=self.context,
            secret_ref=self.secret_ref,
        )

        # 'get_secret' should be called once with the secret_ref
        self.bc.secrets.get.assert_called_once_with(
            secret_ref=self.secret_ref
        )

        self.assertEqual(self.fake_secret, data)

        # Test with a failure
        self.assertRaises(exceptions.CertificateRetrievalException,
                          self.cert_manager.get_secret,
                          context=self.context, secret_ref=self.secret_ref)
