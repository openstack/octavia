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
import uuid

from OpenSSL import crypto
import six

import octavia.certificates.generator.barbican as barbican_cert_gen
import octavia.tests.unit.base as base

if six.PY2:
    import mock
else:
    import unittest.mock as mock


class TestBarbicanGenerator(base.TestCase):

    def setUp(self):
        # Make a fake Order and contents
        self.barbican_endpoint = 'http://localhost:9311/v1'
        self.container_uuid = uuid.uuid4()

        # TODO(rm_work): fill this section, right now it is placeholder data
        self.order_uuid = uuid.uuid4()
        self.order_ref = '{0}/orders/{1}'.format(
            self.barbican_endpoint, self.container_uuid
        )

        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 1024)
        req = crypto.X509Req()
        req.set_pubkey(key)
        self.certificate_signing_request = crypto.dump_certificate_request(
            crypto.FILETYPE_PEM, req
        )

        order = mock.Mock()
        self.order = order

        super(TestBarbicanGenerator, self).setUp()

    def test_sign_cert(self):
        # TODO(rm_work): Update this test when Barbican supports this, right
        #                now this is all guesswork
        self.skipTest("Barbican does not yet support signing.")

        # Mock out the client
        bc = mock.MagicMock()
        bc.orders.create.return_value = self.order
        barbican_cert_gen.BarbicanCertGenerator._barbican_client = bc

        # Attempt to order a cert signing
        barbican_cert_gen.BarbicanCertGenerator.sign_cert(
            csr=self.certificate_signing_request
        )

        # create order should be called once
        # should get back a valid order
        bc.orders.create.assert_called_once_with()

    def test_generate_cert_key_pair(self):
        self.skipTest("Barbican does not yet support signing.")