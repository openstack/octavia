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

from barbicanclient import client as barbican_client
import mock
import six

import octavia.certificates.common.barbican as barbican_common
import octavia.tests.unit.base as base
import octavia.tests.unit.common.sample_configs.sample_certs as sample


class TestBarbicanCert(base.TestCase):

    def _prepare(self):
        self.certificate_secret = barbican_client.secrets.Secret(
            api=mock.MagicMock(),
            payload=self.certificate
        )
        self.intermediates_secret = barbican_client.secrets.Secret(
            api=mock.MagicMock(),
            payload=sample.X509_IMDS
        )
        self.private_key_secret = barbican_client.secrets.Secret(
            api=mock.MagicMock(),
            payload=self.private_key
        )
        self.private_key_passphrase_secret = barbican_client.secrets.Secret(
            api=mock.MagicMock(),
            payload=self.private_key_passphrase
        )

    def test_barbican_cert(self):
        # Certificate data
        self.certificate = six.binary_type(sample.X509_CERT)
        self.intermediates = sample.X509_IMDS_LIST
        self.private_key = six.binary_type(sample.X509_CERT_KEY_ENCRYPTED)
        self.private_key_passphrase = sample.X509_CERT_KEY_PASSPHRASE
        self._prepare()

        container = barbican_client.containers.CertificateContainer(
            api=mock.MagicMock(),
            certificate=self.certificate_secret,
            intermediates=self.intermediates_secret,
            private_key=self.private_key_secret,
            private_key_passphrase=self.private_key_passphrase_secret
        )
        # Create a cert
        cert = barbican_common.BarbicanCert(
            cert_container=container
        )

        # Validate the cert functions
        self.assertEqual(cert.get_certificate(), sample.X509_CERT)
        self.assertEqual(cert.get_intermediates(), sample.X509_IMDS_LIST)
        self.assertEqual(cert.get_private_key(),
                         sample.X509_CERT_KEY_ENCRYPTED)
        self.assertEqual(cert.get_private_key_passphrase(),
                         six.b(sample.X509_CERT_KEY_PASSPHRASE))

    def test_barbican_cert_text(self):
        # Certificate data
        self.certificate = six.text_type(sample.X509_CERT)
        self.intermediates = six.text_type(sample.X509_IMDS_LIST)
        self.private_key = six.text_type(sample.X509_CERT_KEY_ENCRYPTED)
        self.private_key_passphrase = six.text_type(
            sample.X509_CERT_KEY_PASSPHRASE)
        self._prepare()

        container = barbican_client.containers.CertificateContainer(
            api=mock.MagicMock(),
            certificate=self.certificate_secret,
            intermediates=self.intermediates_secret,
            private_key=self.private_key_secret,
            private_key_passphrase=self.private_key_passphrase_secret
        )
        # Create a cert
        cert = barbican_common.BarbicanCert(
            cert_container=container
        )

        # Validate the cert functions
        self.assertEqual(cert.get_certificate(),
                         six.b(six.text_type(sample.X509_CERT)))
        self.assertEqual(cert.get_intermediates(), sample.X509_IMDS_LIST)
        self.assertEqual(cert.get_private_key(), six.b(six.text_type(
            sample.X509_CERT_KEY_ENCRYPTED)))
        self.assertEqual(cert.get_private_key_passphrase(),
                         six.b(sample.X509_CERT_KEY_PASSPHRASE))
