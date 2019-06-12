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
import stat

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

import octavia.certificates.common.cert as cert
import octavia.certificates.manager.local as local_cert_mgr
from octavia.common import exceptions
from octavia.tests.common import sample_certs
import octavia.tests.unit.base as base


class TestLocalManager(base.TestCase):

    def setUp(self):
        self.certificate = sample_certs.X509_CERT.decode('utf-8')
        self.intermediates = sample_certs.X509_IMDS.decode('utf-8')
        self.private_key = sample_certs.X509_CERT_KEY.decode('utf-8')
        self.private_key_passphrase = "My Private Key Passphrase"

        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="certificates", storage_path="/tmp/")

        super(TestLocalManager, self).setUp()

    def _store_cert(self):
        fd_mock = mock.mock_open()
        open_mock = mock.Mock()
        # Attempt to store the cert
        with mock.patch('os.open', open_mock), mock.patch.object(
                os, 'fdopen', fd_mock):
            cert_id = local_cert_mgr.LocalCertManager.store_cert(
                context=None,
                certificate=self.certificate,
                intermediates=self.intermediates,
                private_key=self.private_key,
                private_key_passphrase=self.private_key_passphrase
            )

        # Check that something came back
        self.assertIsNotNone(cert_id)

        # Verify the correct files were opened
        flags = os.O_WRONLY | os.O_CREAT
        mode = stat.S_IRUSR | stat.S_IWUSR  # mode 0600
        open_mock.assert_has_calls([
            mock.call(
                os.path.join('/tmp/{0}.crt'.format(cert_id)), flags, mode),
            mock.call(
                os.path.join('/tmp/{0}.key'.format(cert_id)), flags, mode),
            mock.call(
                os.path.join('/tmp/{0}.int'.format(cert_id)), flags, mode),
            mock.call(
                os.path.join('/tmp/{0}.pass'.format(cert_id)), flags, mode)
        ], any_order=True)

        # Verify the writes were made
        fd_mock().write.assert_has_calls([
            mock.call(self.certificate),
            mock.call(self.intermediates),
            mock.call(self.private_key),
            mock.call(self.private_key_passphrase)
        ], any_order=True)

        return cert_id

    def _get_cert(self, cert_id):
        fd_mock = mock.mock_open()
        fd_mock.side_effect = [
            mock.mock_open(read_data=self.certificate).return_value,
            mock.mock_open(read_data=self.private_key).return_value,
            mock.mock_open(read_data=self.intermediates).return_value,
            mock.mock_open(read_data=self.private_key_passphrase).return_value
        ]
        open_mock = mock.Mock()
        # Attempt to retrieve the cert
        with mock.patch('os.open', open_mock), mock.patch.object(
                os, 'fdopen', fd_mock):
            data = local_cert_mgr.LocalCertManager.get_cert(None, cert_id)

        # Verify the correct files were opened
        flags = os.O_RDONLY
        open_mock.assert_has_calls([
            mock.call(os.path.join('/tmp/{0}.crt'.format(cert_id)), flags),
            mock.call(os.path.join('/tmp/{0}.key'.format(cert_id)), flags),
            mock.call(os.path.join('/tmp/{0}.int'.format(cert_id)), flags),
            mock.call(os.path.join('/tmp/{0}.pass'.format(cert_id)), flags)
        ], any_order=True)

        # The returned data should be a Cert object
        self.assertIsInstance(data, cert.Cert)

        return data

    def _delete_cert(self, cert_id):
        remove_mock = mock.Mock()
        # Delete the cert
        with mock.patch('os.remove', remove_mock):
            local_cert_mgr.LocalCertManager.delete_cert(None, cert_id)

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
        # Get the cert
        self._get_cert("cert1")

    def test_delete_cert(self):
        # Store a cert
        cert_id = self._store_cert()

        # Verify the cert exists
        self._get_cert(cert_id)

        # Delete the cert
        self._delete_cert(cert_id)

    def test_get_secret(self):
        fd_mock = mock.mock_open()
        open_mock = mock.Mock()
        secret_id = uuidutils.generate_uuid()
        # Attempt to retrieve the secret
        with mock.patch('os.open', open_mock), mock.patch.object(
                os, 'fdopen', fd_mock):
            local_cert_mgr.LocalCertManager.get_secret(None, secret_id)

        # Verify the correct files were opened
        flags = os.O_RDONLY
        open_mock.assert_called_once_with('/tmp/{0}.crt'.format(secret_id),
                                          flags)

        # Test failure path
        with mock.patch('os.open', open_mock), mock.patch.object(
                os, 'fdopen', fd_mock) as mock_open:
            mock_open.side_effect = IOError
            self.assertRaises(exceptions.CertificateRetrievalException,
                              local_cert_mgr.LocalCertManager.get_secret,
                              None, secret_id)
