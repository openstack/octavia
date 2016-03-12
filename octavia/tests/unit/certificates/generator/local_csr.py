# Copyright 2015 Hewlett Packard Enterprise Development Company LP
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

from cryptography.hazmat import backends
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography import x509
import mock

import octavia.tests.unit.base as base


class BaseLocalCSRTestCase(base.TestCase):
    def setUp(self):
        self.signing_digest = "sha256"

        # Set up CSR data
        csr_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=backends.default_backend()
        )
        csr = x509.CertificateSigningRequestBuilder().subject_name(
            x509.Name([
                x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, u"test"),
            ])).sign(csr_key, hashes.SHA256(), backends.default_backend())
        self.certificate_signing_request = csr.public_bytes(
            serialization.Encoding.PEM)

        # Set up keys
        self.ca_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=backends.default_backend()
        )

        self.ca_private_key_passphrase = b"Testing"
        self.ca_private_key = self.ca_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.BestAvailableEncryption(
                self.ca_private_key_passphrase),
        )

        super(BaseLocalCSRTestCase, self).setUp()

    def test_generate_csr(self):
        cn = 'testCN'
        # Attempt to generate a CSR
        csr = self.cert_generator._generate_csr(
            cn=cn,
            private_key=self.ca_private_key,
            passphrase=self.ca_private_key_passphrase
        )

        # Attempt to load the generated CSR
        csro = x509.load_pem_x509_csr(data=csr,
                                      backend=backends.default_backend())

        # Make sure the CN is correct
        self.assertEqual(cn, csro.subject.get_attributes_for_oid(
            x509.oid.NameOID.COMMON_NAME)[0].value)

    def test_generate_private_key(self):
        bit_length = 1024
        # Attempt to generate a private key
        pk = self.cert_generator._generate_private_key(
            bit_length=bit_length
        )

        # Attempt to load the generated private key
        pko = serialization.load_pem_private_key(
            data=pk, password=None, backend=backends.default_backend())

        # Make sure the bit_length is what we set
        self.assertEqual(pko.key_size, bit_length)

    def test_generate_private_key_with_passphrase(self):
        bit_length = 2048
        # Attempt to generate a private key
        pk = self.cert_generator._generate_private_key(
            bit_length=bit_length,
            passphrase=self.ca_private_key_passphrase
        )

        # Attempt to load the generated private key
        pko = serialization.load_pem_private_key(
            data=pk, password=self.ca_private_key_passphrase,
            backend=backends.default_backend())

        # Make sure the bit_length is what we set
        self.assertEqual(pko.key_size, bit_length)

    def test_generate_cert_key_pair_mock(self):
        cn = 'testCN'

        with mock.patch.object(self.cert_generator, 'sign_cert') as m:
            # Attempt to generate a cert/key pair
            self.cert_generator.generate_cert_key_pair(
                cn=cn,
                validity=2 * 365 * 24 * 60 * 60,
            )
            self.assertTrue(m.called)
