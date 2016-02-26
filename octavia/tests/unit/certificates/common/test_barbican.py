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

import octavia.certificates.common.barbican as barbican_common
import octavia.tests.unit.base as base

X509_IMDS = """-----BEGIN CERTIFICATE-----
First Intermediate Data
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
Second Intermediate Data
-----END CERTIFICATE-----"""

X509_IMDS_LIST = [
    """-----BEGIN CERTIFICATE-----
First Intermediate Data
-----END CERTIFICATE-----""",
    """-----BEGIN CERTIFICATE-----
Second Intermediate Data
-----END CERTIFICATE-----"""
]


class TestBarbicanCert(base.TestCase):

    def setUp(self):
        # Certificate data
        self.certificate = "My Certificate"
        self.intermediates = X509_IMDS_LIST
        self.private_key = "My Private Key"
        self.private_key_passphrase = "My Private Key Passphrase"

        self.certificate_secret = barbican_client.secrets.Secret(
            api=mock.MagicMock(),
            payload=self.certificate
        )
        self.intermediates_secret = barbican_client.secrets.Secret(
            api=mock.MagicMock(),
            payload=X509_IMDS
        )
        self.private_key_secret = barbican_client.secrets.Secret(
            api=mock.MagicMock(),
            payload=self.private_key
        )
        self.private_key_passphrase_secret = barbican_client.secrets.Secret(
            api=mock.MagicMock(),
            payload=self.private_key_passphrase
        )

        super(TestBarbicanCert, self).setUp()

    def test_barbican_cert(self):
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
        self.assertEqual(cert.get_certificate(), self.certificate)
        self.assertEqual(cert.get_intermediates(), self.intermediates)
        self.assertEqual(cert.get_private_key(), self.private_key)
        self.assertEqual(cert.get_private_key_passphrase(),
                         self.private_key_passphrase)
