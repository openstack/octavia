# Copyright 2026 Cleura
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

import multiprocessing
from unittest import mock

from octavia.cmd import octavia_worker
from octavia.tests.unit import base


class TestOctaviaWorkerCMD(base.TestCase):

    @mock.patch('cotyledon.oslo_config_glue.setup')
    @mock.patch('cotyledon.ServiceManager')
    @mock.patch('octavia.common.service.prepare_service')
    def test_main_uses_fork_mp_context(self, mock_prepare, mock_sm,
                                       mock_glue):
        mock_sm_instance = mock.MagicMock()
        mock_sm.return_value = mock_sm_instance

        octavia_worker.main()

        fork_ctx = multiprocessing.get_context("fork")
        mock_sm.assert_called_once_with(
            mp_context=mock.ANY)
        actual_ctx = mock_sm.call_args.kwargs['mp_context']
        self.assertEqual(fork_ctx.get_start_method(),
                         actual_ctx.get_start_method())
