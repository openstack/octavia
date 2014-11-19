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

        self.ca_private_key_passphrase = "Testing"
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

        self.assertIn("-----BEGIN CERTIFICATE-----", signed_cert)

        # Load the cert for specific tests
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, signed_cert)

        # Make sure expiry time is accurate
        expires = datetime.datetime.strptime(cert.get_notAfter(),
                                             '%Y%m%d%H%M%SZ')
        should_expire = (datetime.datetime.utcnow() +
                         datetime.timedelta(seconds=2 * 365 * 24 * 60 * 60))
        diff = should_expire - expires
        self.assertTrue(diff < datetime.timedelta(seconds=10))
