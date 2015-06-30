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
import os

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
import six

import octavia.certificates.common.cert as cert
import octavia.certificates.manager.local as local_cert_mgr
import octavia.tests.unit.base as base

if six.PY2:
    import __builtin__ as builtins

    import mock
else:

    import builtins

    import unittest.mock as mock


class TestLocalManager(base.TestCase):

    def setUp(self):
        self.certificate = "My Certificate"
        self.intermediates = "My Intermediates"
        self.private_key = "My Private Key"
        self.private_key_passphrase = "My Private Key Passphrase"

        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="certificates", storage_path="/tmp/")

        super(TestLocalManager, self).setUp()

    def _store_cert(self):
        file_mock = mock.mock_open()
        # Attempt to store the cert
        with mock.patch.object(builtins, 'open', file_mock):
            cert_id = local_cert_mgr.LocalCertManager.store_cert(
                certificate=self.certificate,
                intermediates=self.intermediates,
                private_key=self.private_key,
                private_key_passphrase=self.private_key_passphrase
            )

        # Check that something came back
        self.assertIsNotNone(cert_id)

        # Verify the correct files were opened
        file_mock.assert_has_calls([
            mock.call(os.path.join('/tmp/{0}.crt'.format(cert_id)), 'w'),
            mock.call(os.path.join('/tmp/{0}.key'.format(cert_id)), 'w'),
            mock.call(os.path.join('/tmp/{0}.int'.format(cert_id)), 'w'),
            mock.call(os.path.join('/tmp/{0}.pass'.format(cert_id)), 'w')
        ], any_order=True)

        # Verify the writes were made
        file_mock().write.assert_has_calls([
            mock.call(self.certificate),
            mock.call(self.intermediates),
            mock.call(self.private_key),
            mock.call(self.private_key_passphrase)
        ], any_order=True)

        return cert_id

    def _get_cert(self, cert_id):
        file_mock = mock.mock_open()
        # Attempt to retrieve the cert
        with mock.patch.object(builtins, 'open', file_mock):
            data = local_cert_mgr.LocalCertManager.get_cert(cert_id)

        # Verify the correct files were opened
        file_mock.assert_has_calls([
            mock.call(os.path.join('/tmp/{0}.crt'.format(cert_id)), 'r'),
            mock.call(os.path.join('/tmp/{0}.key'.format(cert_id)), 'r'),
            mock.call(os.path.join('/tmp/{0}.int'.format(cert_id)), 'r'),
            mock.call(os.path.join('/tmp/{0}.pass'.format(cert_id)), 'r')
        ], any_order=True)

        # The returned data should be a Cert object
        self.assertIsInstance(data, cert.Cert)

        return data

    def _delete_cert(self, cert_id):
        remove_mock = mock.Mock()
        # Delete the cert
        with mock.patch('os.remove', remove_mock):
            local_cert_mgr.LocalCertManager.delete_cert(cert_id)

        # Verify the correct files were removed
        remove_mock.assert_has_calls([
            mock.call(os.path.join('/tmp/{0}.crt'.format(cert_id))),
            mock.call(os.path.join('/tmp/{0}.key'.format(cert_id))),
            mock.call(os.path.join('/tmp/{0}.int'.format(cert_id))),
            mock.call(os.path.join('/tmp/{0}.pass'.format(cert_id)))
        ], any_order=True)

    def test_store_cert(self):
        self._store_cert()

    def test_get_cert(self):
        # Store a cert
        cert_id = self._store_cert()

        # Get the cert
        self._get_cert(cert_id)

    def test_delete_cert(self):
        # Store a cert
        cert_id = self._store_cert()

        # Verify the cert exists
        self._get_cert(cert_id)

        # Delete the cert
        self._delete_cert(cert_id)
