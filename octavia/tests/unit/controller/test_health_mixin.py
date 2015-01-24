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


import mock

from octavia.common import constants
from octavia.controller.healthmanager import update_health_mixin as healthmixin
from octavia.openstack.common import uuidutils
import octavia.tests.unit.base as base


class TestUpdateHealthMixin(base.TestCase):
    FAKE_UUID_1 = uuidutils.generate_uuid()

    def setUp(self):
        super(TestUpdateHealthMixin, self).setUp()
        self.hm = healthmixin.UpdateHealthMixin()

        self.amphora_health_repo = mock.MagicMock()
        self.listener_repo = mock.MagicMock()
        self.member_repo = mock.MagicMock()
        self.pool_repo = mock.MagicMock()

        self.hm.amphora_health_repo = self.amphora_health_repo
        self.hm.listener_repo = self.listener_repo
        self.hm.member_repo = self.member_repo
        self.hm.pool_repo = self.pool_repo

    @mock.patch('octavia.db.api.get_session')
    @mock.patch('sqlalchemy.sql.func.now')
    def test_update_health_Online(self, lastupdate, session):

        health = {
            "amphora-status": constants.AMPHORA_UP,
            "amphora-id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"listener-status": constants.ONLINE,
                                  "members": {"member-id-1": constants.ONLINE}
                                  }

            }
        }

        session.return_value = 'blah'
        lastupdate.return_value = '2014-02-12'

        self.hm.update_health(health)
        self.assertTrue(self.amphora_health_repo.update.called)

        # test listener, member
        for listener_id, listener in health.get('listeners', {}).iteritems():

            self.listener_repo.update.assert_any_call(
                'blah', listener_id, operating_status=constants.ONLINE)

            for member_id, member in listener.get('members', {}).iteritems():
                self.member_repo.update.assert_any_call(
                    'blah', id=member_id, operating_status=constants.ONLINE)

    @mock.patch('octavia.db.api.get_session')
    @mock.patch('sqlalchemy.sql.func.now')
    def test_update_health_Error(self, lastupdate, session):

        health = {
            "amphora-status": constants.AMPHORA_DOWN,
            "amphora-id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"listener-status": constants.ERROR,
                                  "members": {"member-id-1": constants.ERROR}
                                  },
                "listener-id-2": {"listener-status": constants.ERROR,
                                  "members": {"member-id-2": constants.ERROR}
                                  }
            }
        }

        session.return_value = 'blah'
        lastupdate.return_value = '2014-02-12'

        self.hm.update_health(health)
        self.assertFalse(self.amphora_health_repo.update.called)

        # test listener, member
        for listener_id, listener in health.get('listeners', {}).iteritems():

            self.listener_repo.update.assert_any_call(
                'blah', listener_id, operating_status=constants.ERROR)

            for member_id, member in listener.get('members', {}).iteritems():
                self.member_repo.update.assert_any_call(
                    'blah', id=member_id, operating_status=constants.ERROR)
