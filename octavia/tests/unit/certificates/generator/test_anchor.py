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

from oslo_config import cfg
import requests_mock
import six

from octavia.certificates.generator import anchor
from octavia.common import exceptions
from octavia.tests.unit.certificates.generator import local_csr


CONF = cfg.CONF


class TestAnchorGenerator(local_csr.BaseLocalCSRTestCase):
    def setUp(self):
        super(TestAnchorGenerator, self).setUp()
        self.cert_generator = anchor.AnchorCertGenerator

    @requests_mock.mock()
    def test_sign_cert(self, m):

        m.post(CONF.anchor.url, content=six.b('test'))

        # Attempt to sign a cert
        signed_cert = self.cert_generator.sign_cert(
            csr=self.certificate_signing_request
        )
        self.assertEqual("test", signed_cert.decode('ascii'))
        self.assertTrue(m.called)

        m.post(CONF.anchor.url, status_code=400)
        self.assertRaises(exceptions.CertificateGenerationException,
                          self.cert_generator.sign_cert,
                          self.certificate_signing_request)
