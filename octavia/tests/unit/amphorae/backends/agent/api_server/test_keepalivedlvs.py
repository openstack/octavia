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
from unittest import mock

from oslo_utils import uuidutils

from octavia.amphorae.backends.agent.api_server import keepalivedlvs
from octavia.tests.unit import base


class KeepalivedLvsTestCase(base.TestCase):
    FAKE_ID = uuidutils.generate_uuid()

    def setUp(self):
        super().setUp()
        self.test_keepalivedlvs = keepalivedlvs.KeepalivedLvs()

    @mock.patch.object(keepalivedlvs, "webob")
    @mock.patch('os.path.exists')
    def test_delete_lvs_listener_not_exist(self, m_exist, m_webob):
        m_exist.return_value = False
        self.test_keepalivedlvs.delete_lvs_listener(self.FAKE_ID)
        calls = [
            mock.call(
                json=dict(message='UDP Listener Not Found',
                          details="No UDP listener with UUID: "
                                  "{}".format(self.FAKE_ID)), status=404),
            mock.call(json={'message': 'OK'})
        ]
        m_webob.Response.assert_has_calls(calls)
