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
import ssl

import mock

from octavia.cmd import agent
from octavia.tests.unit import base


class TestAmphoraAgentCMD(base.TestCase):

    def setUp(self):
        super(TestAmphoraAgentCMD, self).setUp()

    @mock.patch('octavia.cmd.agent.AmphoraAgent')
    @mock.patch('octavia.amphorae.backends.agent.api_server.server.Server')
    @mock.patch('multiprocessing.Process')
    @mock.patch('octavia.common.service.prepare_service')
    def test_main(self, mock_service, mock_process, mock_server, mock_amp):
        mock_health_proc = mock.MagicMock()
        mock_server_instance = mock.MagicMock()
        mock_amp_instance = mock.MagicMock()

        mock_process.return_value = mock_health_proc
        mock_server.return_value = mock_server_instance
        mock_amp.return_value = mock_amp_instance

        agent.main()

        # Ensure gunicorn is initialized with the correct cert_reqs option.
        # This option is what enforces use of a valid client certificate.
        self.assertEqual(
            ssl.CERT_REQUIRED,
            mock_amp.call_args[0][1]['cert_reqs'])

        mock_health_proc.start.assert_called_once_with()
        mock_amp_instance.run.assert_called_once()
