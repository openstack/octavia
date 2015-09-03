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

from oslo_utils import uuidutils
import six
import sqlalchemy

from octavia.common import constants
from octavia.controller.healthmanager import update_health_mixin as healthmixin
import octavia.tests.unit.base as base

if six.PY2:
    import mock
else:
    import unittest.mock as mock


class TestUpdateHealthMixin(base.TestCase):
    FAKE_UUID_1 = uuidutils.generate_uuid()

    def setUp(self):
        super(TestUpdateHealthMixin, self).setUp()
        self.hm = healthmixin.UpdateHealthMixin()

        self.amphora_repo = mock.MagicMock()
        self.amphora_health_repo = mock.MagicMock()
        self.listener_repo = mock.MagicMock()
        self.loadbalancer_repo = mock.MagicMock()
        self.member_repo = mock.MagicMock()
        self.pool_repo = mock.MagicMock()

        self.hm.amphora_repo = self.amphora_repo
        fake_lb = mock.MagicMock()
        self.hm.amphora_repo.get_all_lbs_on_amphora.return_value = [fake_lb]
        self.hm.amphora_health_repo = self.amphora_health_repo
        self.hm.listener_repo = self.listener_repo
        self.hm.listener_repo.count.return_value = 1
        self.hm.loadbalancer_repo = self.loadbalancer_repo
        self.hm.member_repo = self.member_repo
        self.hm.pool_repo = self.pool_repo

    @mock.patch('octavia.db.api.get_session')
    def test_update_health_Online(self, session):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.OPEN, "pools": {
                    "pool-id-1": {"status": constants.UP,
                                  "members": {"member-id-1": constants.UP}
                                  }
                }
                }
            }
        }

        session.return_value = 'blah'

        self.hm.update_health(health)
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                'blah', listener_id, operating_status=constants.ONLINE)

            for pool_id, pool in six.iteritems(listener.get('pools', {})):

                self.hm.pool_repo.update.assert_any_call(
                    'blah', pool_id, operating_status=constants.ONLINE)

                for member_id, member in six.iteritems(
                        pool.get('members', {})):
                    self.member_repo.update.assert_any_call(
                        'blah', id=member_id,
                        operating_status=constants.ONLINE)

        self.hm.listener_repo.count.return_value = 2

        self.hm.update_health(health)

    @mock.patch('octavia.db.api.get_session')
    def test_update_health_member_down(self, session):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.OPEN, "pools": {
                    "pool-id-1": {"status": constants.UP,
                                  "members": {"member-id-1": constants.DOWN}
                                  }
                }
                }
            }
        }

        session.return_value = 'blah'

        self.hm.update_health(health)
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                'blah', listener_id, operating_status=constants.ONLINE)

            for pool_id, pool in six.iteritems(listener.get('pools', {})):

                self.hm.pool_repo.update.assert_any_call(
                    'blah', pool_id, operating_status=constants.DEGRADED)

                for member_id, member in six.iteritems(
                        pool.get('members', {})):

                    self.member_repo.update.assert_any_call(
                        'blah', id=member_id,
                        operating_status=constants.ERROR)

        self.hm.listener_repo.count.return_value = 2

        self.hm.update_health(health)

    @mock.patch('octavia.db.api.get_session')
    def test_update_health_member_no_check(self, session):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.OPEN, "pools": {
                    "pool-id-1": {"status": constants.UP,
                                  "members": {"member-id-1":
                                              constants.NO_CHECK}
                                  }
                }
                }
            }
        }

        session.return_value = 'blah'

        self.hm.update_health(health)
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                'blah', listener_id, operating_status=constants.ONLINE)

            for pool_id, pool in six.iteritems(listener.get('pools', {})):

                self.hm.pool_repo.update.assert_any_call(
                    'blah', pool_id, operating_status=constants.ONLINE)

                for member_id, member in six.iteritems(
                        pool.get('members', {})):

                    self.member_repo.update.assert_any_call(
                        'blah', id=member_id,
                        operating_status=constants.NO_MONITOR)

        self.hm.listener_repo.count.return_value = 2

        self.hm.update_health(health)

    @mock.patch('octavia.db.api.get_session')
    def test_update_health_list_full_member_down(self, session):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.FULL, "pools": {
                    "pool-id-1": {"status": constants.UP,
                                  "members": {"member-id-1": constants.DOWN}
                                  }
                }
                }
            }
        }

        session.return_value = 'blah'

        self.hm.update_health(health)
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                'blah', listener_id, operating_status=constants.DEGRADED)

            for pool_id, pool in six.iteritems(listener.get('pools', {})):

                self.hm.pool_repo.update.assert_any_call(
                    'blah', pool_id, operating_status=constants.DEGRADED)

                for member_id, member in six.iteritems(
                        pool.get('members', {})):

                    self.member_repo.update.assert_any_call(
                        'blah', id=member_id,
                        operating_status=constants.ERROR)

        self.hm.listener_repo.count.return_value = 2

        self.hm.update_health(health)

    @mock.patch('octavia.db.api.get_session')
    def test_update_health_Error(self, session):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.OPEN, "pools": {
                    "pool-id-1": {"status": constants.DOWN,
                                  "members": {"member-id-1": constants.DOWN}
                                  }
                }
                }
            }
        }

        session.return_value = 'blah'

        self.hm.update_health(health)
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                'blah', listener_id, operating_status=constants.ONLINE)

            for pool_id, pool in six.iteritems(listener.get('pools', {})):

                self.hm.pool_repo.update.assert_any_call(
                    'blah', pool_id, operating_status=constants.ERROR)

                for member_id, member in six.iteritems(
                        pool.get('members', {})):

                    self.member_repo.update.assert_any_call(
                        'blah', id=member_id, operating_status=constants.ERROR)

    # Test the logic code paths
    @mock.patch('octavia.db.api.get_session')
    def test_update_health_Full(self, session):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.FULL, "pools": {
                    "pool-id-1": {"status": constants.DOWN,
                                  "members": {"member-id-1": constants.DOWN}
                                  }
                }
                },
                "listener-id-2": {"status": constants.FULL, "pools": {
                    "pool-id-2": {"status": constants.UP,
                                  "members": {"member-id-2": constants.UP}
                                  }
                }
                },
                "listener-id-3": {"status": constants.OPEN, "pools": {
                    "pool-id-3": {"status": constants.UP,
                                  "members": {"member-id-3": constants.UP,
                                              "member-id-31": constants.DOWN}
                                  }
                }
                },
                "listener-id-4": {"status": "bogus", "pools": {
                    "pool-id-4": {"status": "bogus",
                                  "members": {"member-id-4": "bogus"}
                                  }
                }
                }
            }
        }

        session.return_value = 'blah'

        self.hm.update_health(health)

        # test listener
        self.listener_repo.update.assert_any_call(
            'blah', "listener-id-1", operating_status=constants.DEGRADED)
        self.listener_repo.update.assert_any_call(
            'blah', "listener-id-2", operating_status=constants.DEGRADED)
        self.pool_repo.update.assert_any_call(
            'blah', "pool-id-1", operating_status=constants.ERROR)
        self.pool_repo.update.assert_any_call(
            'blah', "pool-id-2", operating_status=constants.ONLINE)
        self.pool_repo.update.assert_any_call(
            'blah', "pool-id-3", operating_status=constants.DEGRADED)

    # Test code paths where objects are not found in the database
    @mock.patch('octavia.db.api.get_session')
    def test_update_health_Not_Found(self, session):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.OPEN, "pools": {
                    "pool-id-1": {"status": constants.UP,
                                  "members": {"member-id-1": constants.UP}
                                  }
                }
                }
            }
        }

        session.return_value = 'blah'

        self.hm.listener_repo.update.side_effect = (
            [sqlalchemy.orm.exc.NoResultFound])
        self.hm.member_repo.update.side_effect = (
            [sqlalchemy.orm.exc.NoResultFound])
        self.hm.pool_repo.update.side_effect = (
            [sqlalchemy.orm.exc.NoResultFound])
        self.hm.loadbalancer_repo.update.side_effect = (
            [sqlalchemy.orm.exc.NoResultFound])

        self.hm.update_health(health)
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                'blah', listener_id, operating_status=constants.ONLINE)

            for pool_id, pool in six.iteritems(listener.get('pools', {})):

                self.hm.pool_repo.update.assert_any_call(
                    'blah', pool_id, operating_status=constants.ONLINE)

                for member_id, member in six.iteritems(
                        pool.get('members', {})):

                    self.member_repo.update.assert_any_call(
                        'blah', id=member_id,
                        operating_status=constants.ONLINE)
