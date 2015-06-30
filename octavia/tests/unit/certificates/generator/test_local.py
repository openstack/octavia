# Copyright 2014 Rackspace US, Inc
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
import datetime

from OpenSSL import crypto
import six

import octavia.certificates.generator.local as local_cert_gen
import octavia.tests.unit.base as base


class TestLocalGenerator(base.TestCase):

    def setUp(self):
        self.signing_digest = "sha256"

        # Set up CSR data
        csr_key = crypto.PKey()
        csr_key.generate_key(crypto.TYPE_RSA, 2048)
        csr = crypto.X509Req()
        csr.set_pubkey(csr_key)
        self.certificate_signing_request = crypto.dump_certificate_request(
            crypto.FILETYPE_PEM, csr
        )

        # Set up CA data
        ca_key = crypto.PKey()
        ca_key.generate_key(crypto.TYPE_RSA, 2048)

        self.ca_private_key_passphrase = b"Testing"
        self.ca_private_key = crypto.dump_privatekey(
            crypto.FILETYPE_PEM,
            ca_key,
            'aes-256-cbc',
            self.ca_private_key_passphrase
        )

        ca_cert = crypto.X509()
        ca_subject = ca_cert.get_subject()
        ca_subject.C = "US"
        ca_subject.ST = "Oregon"
        ca_subject.L = "Springfield"
        ca_subject.O = "Springfield Nuclear Power Plant"
        ca_subject.OU = "Section 7-G"
        ca_subject.CN = "maggie1"
        ca_cert.set_issuer(ca_cert.get_subject())
        ca_cert.set_pubkey(ca_key)
        ca_cert.gmtime_adj_notBefore(0)
        ca_cert.gmtime_adj_notAfter(2 * 365 * 24 * 60 * 60)
        ca_cert.sign(ca_key, self.signing_digest)

        self.ca_certificate = crypto.dump_certificate(
            crypto.FILETYPE_PEM, ca_cert
        )

        super(TestLocalGenerator, self).setUp()

    def test_sign_cert(self):
        # Attempt sign a cert
        signed_cert = local_cert_gen.LocalCertGenerator.sign_cert(
            csr=self.certificate_signing_request,
            validity=2 * 365 * 24 * 60 * 60,
            ca_cert=self.ca_certificate,
            ca_key=self.ca_private_key,
            ca_key_pass=self.ca_private_key_passphrase,
            ca_digest=self.signing_digest
        )

        self.assertIn("-----BEGIN CERTIFICATE-----",
                      signed_cert.decode('ascii'))

        # Load the cert for specific tests
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, signed_cert)

        # Make sure expiry time is accurate
        expires = datetime.datetime.strptime(
            cert.get_notAfter().decode('ascii'),
            '%Y%m%d%H%M%SZ'
        )
        should_expire = (datetime.datetime.utcnow() +
                         datetime.timedelta(seconds=2 * 365 * 24 * 60 * 60))
        diff = should_expire - expires
        self.assertTrue(diff < datetime.timedelta(seconds=10))

        # Use the openSSL highlevel text output to verify attributes
        cert_text = crypto.dump_certificate(crypto.FILETYPE_TEXT, cert)

        # Make sure this is a version 3 X509.
        self.assertIn(six.b("Version: 3"), cert_text)

        # Make sure this cert is marked as Server and Client Cert via the
        # The extended Key Usage extension
        self.assertIn(six.b("TLS Web Server Authentication"), cert_text)
        self.assertIn(six.b("TLS Web Client Authentication"), cert_text)

        # Make sure this cert has the nsCertType server, and client
        # attributes set
        self.assertIn(six.b("SSL Server"), cert_text)
        self.assertIn(six.b("SSL Client"), cert_text)

        # Make sure this cert can't sign other certs
        self.assertIn(six.b("CA:FALSE"), cert_text)

    def test_generate_private_key(self):
        bit_length = 1024
        # Attempt to generate a private key
        pk = local_cert_gen.LocalCertGenerator._generate_private_key(
            bit_length=bit_length
        )

        # Attempt to load the generated private key
        pko = crypto.load_privatekey(crypto.FILETYPE_PEM, pk)

        # Make sure the bit_length is what we set
        self.assertEqual(pko.bits(), bit_length)

    def test_generate_private_key_with_passphrase(self):
        bit_length = 2048
        # Attempt to generate a private key
        pk = local_cert_gen.LocalCertGenerator._generate_private_key(
            bit_length=bit_length,
            passphrase=self.ca_private_key_passphrase
        )

        # Attempt to load the generated private key
        pko = crypto.load_privatekey(crypto.FILETYPE_PEM, pk,
                                     self.ca_private_key_passphrase)

        # Make sure the bit_length is what we set
        self.assertEqual(pko.bits(), bit_length)

    def test_generate_csr(self):
        cn = 'test_cn'
        # Attempt to generate a CSR
        csr = local_cert_gen.LocalCertGenerator._generate_csr(
            cn=cn,
            private_key=self.ca_private_key,
            passphrase=self.ca_private_key_passphrase
        )

        # Attempt to load the generated CSR
        csro = crypto.load_certificate_request(crypto.FILETYPE_PEM, csr)

        # Make sure the CN is correct
        self.assertEqual(csro.get_subject().CN, cn)

    def test_generate_cert_key_pair(self):
        cn = 'test_cn'
        bit_length = 512
        # Attempt to generate a cert/key pair
        cert_object = local_cert_gen.LocalCertGenerator.generate_cert_key_pair(
            cn=cn,
            validity=2 * 365 * 24 * 60 * 60,
            bit_length=bit_length,
            passphrase=self.ca_private_key_passphrase,
            ca_cert=self.ca_certificate,
            ca_key=self.ca_private_key,
            ca_key_pass=self.ca_private_key_passphrase
        )

        # Validate that the cert and key are loadable
        cert = crypto.load_certificate(
            crypto.FILETYPE_PEM,
            cert_object.certificate
        )
        self.assertIsNotNone(cert)

        key = crypto.load_privatekey(
            crypto.FILETYPE_PEM,
            cert_object.private_key,
            cert_object.private_key_passphrase
        )
        self.assertIsNotNone(key)
