# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
from unittest import mock

from oslo_config import cfg

from octavia.certificates.common import local
from octavia.common import utils
from octavia.controller.worker.v2.tasks import cert_task
import octavia.tests.unit.base as base

CONF = cfg.CONF


class TestCertTasks(base.TestCase):

    @mock.patch('stevedore.driver.DriverManager.driver')
    def test_execute(self, mock_driver):
        fer = utils.get_server_certs_key_passphrases_fernet()
        dummy_cert = local.LocalCert(
            utils.get_compatible_value('test_cert'),
            utils.get_compatible_value('test_key'))
        mock_driver.generate_cert_key_pair.side_effect = [dummy_cert]
        c = cert_task.GenerateServerPEMTask()
        pem = c.execute('123')
        self.assertEqual(
            fer.decrypt(pem.encode('utf-8')),
            dummy_cert.get_certificate() +
            dummy_cert.get_private_key()
        )
        mock_driver.generate_cert_key_pair.assert_called_once_with(
            cn='123', validity=CONF.certificates.cert_validity_time)
