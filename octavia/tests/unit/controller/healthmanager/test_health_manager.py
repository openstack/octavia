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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import uuidutils
import six

from octavia.controller.healthmanager import health_manager as healthmanager
import octavia.tests.unit.base as base

if six.PY2:
    import mock
else:
    import unittest.mock as mock

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
CONF.import_group('health_manager', 'octavia.common.config')

AMPHORA_ID = uuidutils.generate_uuid()


class TestException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class TestHealthManager(base.TestCase):

    def setUp(self):
        super(TestHealthManager, self).setUp()

    @mock.patch('octavia.controller.worker.controller_worker.'
                'ControllerWorker.failover_amphora')
    @mock.patch('octavia.db.repositories.AmphoraHealthRepository.'
                'get_stale_amphora')
    @mock.patch('time.sleep')
    @mock.patch('octavia.db.api.get_session')
    def test_health_check_stale_amphora(self, session_mock,
                                        sleep_mock, get_stale_amp_mock,
                                        failover_mock):
        amphora_health = mock.MagicMock()
        amphora_health.amphora_id = AMPHORA_ID

        session_mock.side_effect = [None, TestException('test')]
        get_stale_amp_mock.side_effect = [amphora_health, None]

        hm = healthmanager.HealthManager()
        self.assertRaises(TestException, hm.health_check)

        failover_mock.assert_called_once_with(AMPHORA_ID)

    @mock.patch('octavia.controller.worker.controller_worker.'
                'ControllerWorker.failover_amphora')
    @mock.patch('octavia.db.repositories.AmphoraHealthRepository.'
                'get_stale_amphora', return_value=None)
    @mock.patch('time.sleep')
    @mock.patch('octavia.db.api.get_session')
    def test_health_check_nonestale_amphora(self, session_mock,
                                            sleep_mock, get_stale_amp_mock,
                                            failover_mock):
        session_mock.side_effect = [None, TestException('test')]
        get_stale_amp_mock.return_value = None

        hm = healthmanager.HealthManager()
        self.assertRaises(TestException, hm.health_check)

        self.assertFalse(failover_mock.called)
