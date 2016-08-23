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

import random

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils
import six
import sqlalchemy

from octavia.common import constants
from octavia.common import data_models
from octavia.controller.healthmanager import update_db
from octavia.db import models as db_models
from octavia.tests.unit import base


class TestUpdateHealthDb(base.TestCase):
    FAKE_UUID_1 = uuidutils.generate_uuid()

    def setUp(self):
        super(TestUpdateHealthDb, self).setUp()

        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group="health_manager",
                    event_streamer_driver='queue_event_streamer')

        session_patch = mock.patch('octavia.db.api.get_session')
        self.addCleanup(session_patch.stop)
        self.mock_session = session_patch.start()

        self.hm = update_db.UpdateHealthDb()
        self.event_client = mock.MagicMock()
        self.hm.event_streamer.client = self.event_client
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

    def test_update_health_event_stream(self):
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
        self.hm.update_health(health)
        self.event_client.cast.assert_any_call(
            {}, 'update_info', container={
                'info_type': 'listener', 'info_id': 'listener-id-1',
                'info_payload': {'operating_status': 'ONLINE'}})
        self.event_client.cast.assert_any_call(
            {}, 'update_info', container={
                'info_type': 'member', 'info_id': 'member-id-1',
                'info_payload': {'operating_status': 'ONLINE'}})
        self.event_client.cast.assert_any_call(
            {}, 'update_info', container={
                'info_type': 'pool', 'info_id': 'pool-id-1',
                'info_payload': {'operating_status': 'ONLINE'}})

    def test_update_health_no_listener(self):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {}}

        lb = mock.MagicMock()
        lb.operating_status.lower.return_value = 'blah'
        self.amphora_repo.get.load_balancer_id.return_value = self.FAKE_UUID_1
        self.loadbalancer_repo.get.return_value = lb

        self.hm.update_health(health)
        self.assertTrue(self.amphora_repo.get.called)
        self.assertTrue(lb.operating_status.lower.called)
        self.assertTrue(self.loadbalancer_repo.update.called)

    def test_update_health_Online(self):

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

        self.mock_session.return_value = 'blah'

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
                        'blah', member_id,
                        operating_status=constants.ONLINE)

        self.hm.listener_repo.count.return_value = 2

        self.hm.update_health(health)

    def test_update_health_member_down(self):

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

        self.mock_session.return_value = 'blah'

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
                        'blah', member_id,
                        operating_status=constants.ERROR)

        self.hm.listener_repo.count.return_value = 2

        self.hm.update_health(health)

    def test_update_health_member_no_check(self):

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

        self.mock_session.return_value = 'blah'

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
                        'blah', member_id,
                        operating_status=constants.NO_MONITOR)

        self.hm.listener_repo.count.return_value = 2

        self.hm.update_health(health)

    def test_update_health_list_full_member_down(self):

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

        self.mock_session.return_value = 'blah'

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
                        'blah', member_id,
                        operating_status=constants.ERROR)

        self.hm.listener_repo.count.return_value = 2

        self.hm.update_health(health)

    def test_update_health_Error(self):

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

        self.mock_session.return_value = 'blah'

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
                        'blah', member_id, operating_status=constants.ERROR)

    # Test the logic code paths
    def test_update_health_Full(self):

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

        self.mock_session.return_value = 'blah'

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
    def test_update_health_Not_Found(self):

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

        self.hm.listener_repo.update.side_effect = (
            [sqlalchemy.orm.exc.NoResultFound])
        self.hm.member_repo.update.side_effect = (
            [sqlalchemy.orm.exc.NoResultFound])
        self.hm.pool_repo.update.side_effect = (
            [sqlalchemy.orm.exc.NoResultFound])
        self.hm.loadbalancer_repo.update.side_effect = (
            [sqlalchemy.orm.exc.NoResultFound])

        self.mock_session.return_value = 'blah'

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
                        'blah', member_id,
                        operating_status=constants.ONLINE)

    def test_update_health_no_status_change(self):
        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {
                    "status": constants.OPEN, "pools": {
                        "pool-id-1": {
                            "status": constants.UP, "members": {
                                "member-id-1": constants.UP
                            }
                        }
                    }
                }
            }
        }
        db_lb = data_models.LoadBalancer(
            id=self.FAKE_UUID_1, operating_status=constants.ONLINE
        )
        db_listener = data_models.Listener(
            id='listener-id-', operating_status=constants.ONLINE,
            load_balancer_id=self.FAKE_UUID_1
        )
        db_pool = data_models.Pool(
            id='pool-id-1', operating_status=constants.ONLINE
        )
        db_member = data_models.Member(
            id='member-id-1', operating_status=constants.ONLINE
        )
        self.listener_repo.get.return_value = db_listener
        self.pool_repo.get.return_value = db_pool
        self.member_repo.get.return_value = db_member
        self.loadbalancer_repo.get.return_value = db_lb
        self.hm.update_health(health)
        self.event_client.cast.assert_not_called()
        self.loadbalancer_repo.update.assert_not_called()
        self.listener_repo.update.assert_not_called()
        self.pool_repo.update.assert_not_called()
        self.member_repo.update.assert_not_called()


class TestUpdateStatsDb(base.TestCase):

    def setUp(self):
        super(TestUpdateStatsDb, self).setUp()
        self.sm = update_db.UpdateStatsDb()
        self.event_client = mock.MagicMock()
        self.sm.event_streamer.client = self.event_client

        self.listener_stats_repo = mock.MagicMock()
        self.sm.listener_stats_repo = self.listener_stats_repo

        self.loadbalancer_id = uuidutils.generate_uuid()
        self.listener_id = uuidutils.generate_uuid()

        self.listener_stats = data_models.ListenerStatistics(
            listener_id=self.listener_id,
            bytes_in=random.randrange(1000000000),
            bytes_out=random.randrange(1000000000),
            active_connections=random.randrange(1000000000),
            total_connections=random.randrange(1000000000),
            request_errors=random.randrange(1000000000))

        self.sm.get_listener_stats = mock.MagicMock()
        self.sm.get_listener_stats.return_value = self.listener_stats

        self.loadbalancer_id = uuidutils.generate_uuid()
        self.amphora_id = uuidutils.generate_uuid()
        self.listener_id = uuidutils.generate_uuid()

        self.listener = db_models.Listener(
            load_balancer_id=self.loadbalancer_id)

        self.listener_repo = mock.MagicMock()
        self.sm.repo_listener = self.listener_repo
        self.sm.repo_listener.get.return_value = self.listener

        self.loadbalancer_repo = mock.MagicMock()
        self.sm.repo_loadbalancer = self.loadbalancer_repo

        self.loadbalancer = db_models.LoadBalancer(
            id=self.loadbalancer_id,
            listeners=[self.listener])
        self.loadbalancer_repo.get.return_value = self.loadbalancer

    @mock.patch('octavia.db.api.get_session')
    def test_update_stats(self, session):

        health = {
            "id": self.amphora_id,
            "listeners": {
                self.listener_id: {
                    "status": constants.OPEN,
                    "stats": {
                        "ereq": self.listener_stats.request_errors,
                        "conns": self.listener_stats.active_connections,
                        "totconns": self.listener_stats.total_connections,
                        "rx": self.listener_stats.bytes_in,
                        "tx": self.listener_stats.bytes_out,
                    },
                    "pools": {
                        "pool-id-1": {
                            "status": constants.UP,
                            "members": {"member-id-1": constants.ONLINE}
                        }
                    }
                }
            }
        }

        session.return_value = 'blah'

        self.sm.update_stats(health)

        self.listener_stats_repo.replace.assert_called_once_with(
            'blah', self.listener_id, self.amphora_id,
            bytes_in=self.listener_stats.bytes_in,
            bytes_out=self.listener_stats.bytes_out,
            active_connections=self.listener_stats.active_connections,
            total_connections=self.listener_stats.total_connections,
            request_errors=self.listener_stats.request_errors)
        self.event_client.cast.assert_any_call(
            {}, 'update_info', container={
                'info_type': 'listener_stats',
                'info_id': self.listener_id,
                'info_payload': {
                    'bytes_in': self.listener_stats.bytes_in,
                    'total_connections':
                        self.listener_stats.total_connections,
                    'active_connections':
                        self.listener_stats.active_connections,
                    'bytes_out': self.listener_stats.bytes_out,
                    'request_errors': self.listener_stats.request_errors}})

        self.event_client.cast.assert_any_call(
            {}, 'update_info',
            container={
                'info_type': 'loadbalancer_stats',
                'info_id': self.loadbalancer_id,
                'info_payload': {
                    'bytes_in': self.listener_stats.bytes_in,
                    'total_connections':
                        self.listener_stats.total_connections,
                    'active_connections':
                        self.listener_stats.active_connections,
                    'bytes_out': self.listener_stats.bytes_out,
                    'request_errors': self.listener_stats.request_errors}})
