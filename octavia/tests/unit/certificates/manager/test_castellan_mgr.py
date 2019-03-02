# Copyright 2019 Rackspace, US Inc.
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

import mock

from octavia.certificates.manager import castellan_mgr
from octavia.common import exceptions
import octavia.tests.unit.base as base


class TestCastellanCertManager(base.TestCase):

    def setUp(self):

        self.fake_secret = 'Fake secret'
        self.manager = mock.MagicMock()
        self.certbag = mock.MagicMock()
        self.manager.get.return_value = self.certbag

        super(TestCastellanCertManager, self).setUp()

    @mock.patch('castellan.key_manager.API')
    def test_get_secret(self, mock_api):
        mock_api.return_value = self.manager

        castellan_mgr_obj = castellan_mgr.CastellanCertManager()
        self.certbag.get_encoded.side_effect = [self.fake_secret,
                                                Exception('boom')]

        result = castellan_mgr_obj.get_secret('context', 'secret_ref')

        self.assertEqual(self.fake_secret, result)
        self.manager.get.assert_called_once_with('context', 'secret_ref')
        self.certbag.get_encoded.assert_called_once()

        self.assertRaises(exceptions.CertificateRetrievalException,
                          castellan_mgr_obj.get_secret, 'context',
                          'secret_ref')
