# Copyright 2023 Red Hat
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

from oslo_utils import uuidutils

from octavia.certificates.common import cert
from octavia.certificates.manager import noop as noop_cert_mgr
from octavia.tests.common import sample_certs
import octavia.tests.unit.base as base


class TestNoopManager(base.TestCase):

    def setUp(self):
        super().setUp()
        self.manager = noop_cert_mgr.NoopCertManager()

    def test_store_cert(self):
        certificate = self.manager.store_cert(
            None,
            sample_certs.X509_CERT,
            sample_certs.X509_CERT_KEY_ENCRYPTED,
            sample_certs.X509_IMDS,
            private_key_passphrase=sample_certs.X509_CERT_KEY_PASSPHRASE)
        self.assertIsNotNone(certificate)
        self.assertIsInstance(certificate, cert.Cert)

    def test_get_cert(self):
        cert_ref = uuidutils.generate_uuid()
        certificate = self.manager.get_cert(
            context=None,
            cert_ref=cert_ref)
        self.assertIsNotNone(certificate)
        self.assertIsInstance(certificate, cert.Cert)

    def test_get_secret(self):
        secret_ref = uuidutils.generate_uuid()
        secret = self.manager.get_secret(
            context=None,
            secret_ref=secret_ref)
        self.assertIsNotNone(secret)
        self.assertIsInstance(secret, cert.Cert)
