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

from barbicanclient.v1 import containers
from barbicanclient.v1 import secrets
import mock
from oslo_utils import uuidutils
import six

import octavia.certificates.common.barbican as barbican_common
import octavia.certificates.common.cert as cert
import octavia.certificates.manager.barbican_legacy as barbican_cert_mgr
import octavia.tests.unit.base as base
import octavia.tests.unit.common.sample_configs.sample_certs as sample


PROJECT_ID = "12345"


class TestBarbicanManager(base.TestCase):

    def setUp(self):
        # Make a fake Container and contents
        self.barbican_endpoint = 'http://localhost:9311/v1'
        self.container_uuid = uuidutils.generate_uuid()
        self.certificate_uuid = uuidutils.generate_uuid()
        self.intermediates_uuid = uuidutils.generate_uuid()
        self.private_key_uuid = uuidutils.generate_uuid()
        self.private_key_passphrase_uuid = uuidutils.generate_uuid()

        self.container_ref = '{0}/containers/{1}'.format(
            self.barbican_endpoint, self.container_uuid
        )

        self.barbican_api = mock.MagicMock()

        self.name = 'My Fancy Cert'
        self.certificate = secrets.Secret(
            api=self.barbican_api,
            payload=sample.X509_CERT,
            secret_ref=self.certificate_uuid
        )
        self.intermediates = secrets.Secret(
            api=self.barbican_api,
            payload=sample.X509_IMDS,
            secret_ref=self.intermediates_uuid
        )
        self.private_key = secrets.Secret(
            api=self.barbican_api,
            payload=sample.X509_CERT_KEY_ENCRYPTED,
            secret_ref=self.private_key_uuid
        )
        self.private_key_passphrase = secrets.Secret(
            api=self.barbican_api,
            payload=sample.X509_CERT_KEY_PASSPHRASE,
            secret_ref=self.private_key_passphrase_uuid
        )

        container = mock.Mock(spec=containers.CertificateContainer)
        container.container_ref = self.container_ref
        container.name = self.name
        container.private_key = self.private_key
        container.certificate = self.certificate
        container.intermediates = self.intermediates
        container.private_key_passphrase = self.private_key_passphrase
        self.container = container

        self.empty_container = mock.Mock(spec=containers.CertificateContainer)

        self.secret1 = mock.Mock(spec=secrets.Secret)
        self.secret2 = mock.Mock(spec=secrets.Secret)
        self.secret3 = mock.Mock(spec=secrets.Secret)
        self.secret4 = mock.Mock(spec=secrets.Secret)

        # Mock out the client
        self.bc = mock.Mock()
        self.bc.containers.get.return_value = self.container
        barbican_auth = mock.Mock(spec=barbican_common.BarbicanAuth)
        barbican_auth.get_barbican_client.return_value = self.bc

        self.cert_manager = barbican_cert_mgr.BarbicanCertManager()
        self.cert_manager.auth = barbican_auth

        self.context = mock.Mock()
        self.context.project_id = PROJECT_ID

        super(TestBarbicanManager, self).setUp()

    def test_store_cert(self):
        # Mock out the client
        self.bc.containers.create_certificate.return_value = (
            self.empty_container)

        # Attempt to store a cert
        container_ref = self.cert_manager.store_cert(
            context=self.context,
            certificate=self.certificate,
            private_key=self.private_key,
            intermediates=self.intermediates,
            private_key_passphrase=self.private_key_passphrase,
            name=self.name
        )

        self.assertEqual(self.empty_container.container_ref, container_ref)

        # create_secret should be called four times with our data
        calls = [
            mock.call(payload=self.certificate, expiration=None,
                      name=mock.ANY),
            mock.call(payload=self.private_key, expiration=None,
                      name=mock.ANY),
            mock.call(payload=self.intermediates, expiration=None,
                      name=mock.ANY),
            mock.call(payload=self.private_key_passphrase, expiration=None,
                      name=mock.ANY)
        ]
        self.bc.secrets.create.assert_has_calls(calls, any_order=True)

        # create_certificate should be called once
        self.assertEqual(1, self.bc.containers.create_certificate.call_count)

        # Container should be stored once
        self.empty_container.store.assert_called_once_with()

    def test_store_cert_failure(self):
        # Mock out the client
        self.bc.containers.create_certificate.return_value = (
            self.empty_container)
        test_secrets = [
            self.secret1,
            self.secret2,
            self.secret3,
            self.secret4
        ]
        self.bc.secrets.create.side_effect = test_secrets
        self.empty_container.store.side_effect = ValueError()

        # Attempt to store a cert
        self.assertRaises(
            ValueError,
            self.cert_manager.store_cert,
            context=self.context,
            certificate=self.certificate,
            private_key=self.private_key,
            intermediates=self.intermediates,
            private_key_passphrase=self.private_key_passphrase,
            name=self.name
        )

        # create_secret should be called four times with our data
        calls = [
            mock.call(payload=self.certificate, expiration=None,
                      name=mock.ANY),
            mock.call(payload=self.private_key, expiration=None,
                      name=mock.ANY),
            mock.call(payload=self.intermediates, expiration=None,
                      name=mock.ANY),
            mock.call(payload=self.private_key_passphrase, expiration=None,
                      name=mock.ANY)
        ]
        self.bc.secrets.create.assert_has_calls(calls, any_order=True)

        # create_certificate should be called once
        self.assertEqual(1, self.bc.containers.create_certificate.call_count)

        # Container should be stored once
        self.empty_container.store.assert_called_once_with()

        # All secrets should be deleted (or at least an attempt made)
        for s in test_secrets:
            s.delete.assert_called_once_with()

    def test_get_cert(self):
        # Mock out the client
        self.bc.containers.register_consumer.return_value = self.container

        # Get the container data
        data = self.cert_manager.get_cert(
            context=self.context,
            cert_ref=self.container_ref,
            resource_ref=self.container_ref,
            service_name='Octavia'
        )

        # 'register_consumer' should be called once with the container_ref
        self.bc.containers.register_consumer.assert_called_once_with(
            container_ref=self.container_ref,
            url=self.container_ref,
            name='Octavia'
        )

        # The returned data should be a Cert object with the correct values
        self.assertIsInstance(data, cert.Cert)
        self.assertEqual(data.get_private_key(),
                         self.private_key.payload)
        self.assertEqual(data.get_certificate(),
                         self.certificate.payload)
        self.assertEqual(data.get_intermediates(),
                         sample.X509_IMDS_LIST)
        self.assertEqual(data.get_private_key_passphrase(),
                         six.b(self.private_key_passphrase.payload))

    def test_get_cert_no_registration(self):
        self.bc.containers.get.return_value = self.container

        # Get the container data
        data = self.cert_manager.get_cert(
            context=self.context,
            cert_ref=self.container_ref, check_only=True
        )

        # 'get' should be called once with the container_ref
        self.bc.containers.get.assert_called_once_with(
            container_ref=self.container_ref
        )

        # The returned data should be a Cert object with the correct values
        self.assertIsInstance(data, cert.Cert)
        self.assertEqual(data.get_private_key(),
                         self.private_key.payload)
        self.assertEqual(data.get_certificate(),
                         self.certificate.payload)
        self.assertEqual(data.get_intermediates(),
                         sample.X509_IMDS_LIST)
        self.assertEqual(data.get_private_key_passphrase(),
                         six.b(self.private_key_passphrase.payload))

    def test_get_cert_no_registration_raise_on_secret_access_failure(self):
        self.bc.containers.get.return_value = self.container
        type(self.certificate).payload = mock.PropertyMock(
            side_effect=ValueError)

        # Get the container data
        self.assertRaises(
            ValueError, self.cert_manager.get_cert,
            context=self.context,
            cert_ref=self.container_ref, check_only=True
        )

        # 'get' should be called once with the container_ref
        self.bc.containers.get.assert_called_once_with(
            container_ref=self.container_ref
        )

    def test_delete_cert(self):
        # Attempt to deregister as a consumer
        self.cert_manager.delete_cert(
            context=self.context,
            cert_ref=self.container_ref,
            resource_ref=self.container_ref,
            service_name='Octavia'
        )

        # remove_consumer should be called once with the container_ref
        self.bc.containers.remove_consumer.assert_called_once_with(
            container_ref=self.container_ref,
            url=self.container_ref,
            name='Octavia'
        )

    def test_set_acls(self):
        self.cert_manager.set_acls(
            context=self.context,
            cert_ref=self.container_ref
        )

        # our mock_bc should have one call to ensure_secret_access for each
        # of our secrets, and the container
        self.cert_manager.auth.ensure_secret_access.assert_has_calls([
            mock.call(self.context, self.certificate_uuid),
            mock.call(self.context, self.intermediates_uuid),
            mock.call(self.context, self.private_key_uuid),
            mock.call(self.context, self.private_key_passphrase_uuid)
        ], any_order=True)

    def test_unset_acls(self):
        self.cert_manager.unset_acls(
            context=self.context,
            cert_ref=self.container_ref
        )

        # our mock_bc should have one call to revoke_secret_access for each
        # of our secrets, and the container
        self.cert_manager.auth.revoke_secret_access.assert_has_calls([
            mock.call(self.context, self.certificate_uuid),
            mock.call(self.context, self.intermediates_uuid),
            mock.call(self.context, self.private_key_uuid),
            mock.call(self.context, self.private_key_passphrase_uuid)
        ], any_order=True)

    def test_get_secret(self):
        self.assertIsNone(self.cert_manager.get_secret('fake context',
                                                       'fake secret ref'))
