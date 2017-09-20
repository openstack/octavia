# Copyright 2015 Hewlett Packard Enterprise Development Company LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import subprocess

import flask
import mock

from octavia.amphorae.backends.agent.api_server import keepalived
import octavia.tests.unit.base as base


class KeepalivedTestCase(base.TestCase):
    def setUp(self):
        super(KeepalivedTestCase, self).setUp()
        self.app = flask.Flask(__name__)
        self.client = self.app.test_client()
        self._ctx = self.app.test_request_context()
        self._ctx.push()
        self.test_keepalived = keepalived.Keepalived()

    @mock.patch('subprocess.check_output')
    def test_manager_keepalived_service(self, mock_check_output):
        res = self.test_keepalived.manager_keepalived_service('start')
        cmd = ("/usr/sbin/service octavia-keepalived {action}".format(
            action='start'))
        mock_check_output.assert_called_once_with(cmd.split(),
                                                  stderr=subprocess.STDOUT)
        self.assertEqual(202, res.status_code)

        res = self.test_keepalived.manager_keepalived_service('restart')
        self.assertEqual(400, res.status_code)

        mock_check_output.side_effect = subprocess.CalledProcessError(1,
                                                                      'blah!')

        res = self.test_keepalived.manager_keepalived_service('start')
        self.assertEqual(500, res.status_code)
