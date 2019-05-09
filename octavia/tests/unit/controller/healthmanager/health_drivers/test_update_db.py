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
import time

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils
import six
import sqlalchemy

from octavia.common import constants
from octavia.common import data_models
from octavia.controller.healthmanager.health_drivers import update_db
from octavia.db import models as db_models
from octavia.tests.unit import base


class TestException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class TestUpdateHealthDb(base.TestCase):
    FAKE_UUID_1 = uuidutils.generate_uuid()

    def setUp(self):
        super(TestUpdateHealthDb, self).setUp()

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(group="health_manager",
                         event_streamer_driver='queue_event_streamer')

        session_patch = mock.patch('octavia.db.api.get_session')
        self.addCleanup(session_patch.stop)
        self.mock_session = session_patch.start()
        self.session_mock = mock.MagicMock()
        self.mock_session.return_value = self.session_mock

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
        self.hm.amphora_health_repo = self.amphora_health_repo
        self.hm.listener_repo = self.listener_repo
        self.hm.listener_repo.count.return_value = 1
        self.hm.loadbalancer_repo = self.loadbalancer_repo
        self.hm.member_repo = self.member_repo
        self.hm.pool_repo = self.pool_repo

    def _make_mock_lb_tree(self, listener=True, pool=True, health_monitor=True,
                           members=1, lb_prov_status=constants.ACTIVE):
        mock_lb = mock.Mock()
        mock_lb.id = self.FAKE_UUID_1
        mock_lb.pools = []
        mock_lb.listeners = []
        mock_lb.provisioning_status = lb_prov_status
        mock_lb.operating_status = 'blah'

        mock_listener1 = None
        mock_pool1 = None
        mock_members = None

        if listener:
            mock_listener1 = mock.Mock()
            mock_listener1.id = 'listener-id-1'
            mock_lb.listeners = [mock_listener1]

        if pool:
            mock_pool1 = mock.Mock()
            mock_pool1.id = "pool-id-1"
            mock_pool1.members = []
            if health_monitor:
                mock_hm1 = mock.Mock()
                mock_pool1.health_monitor = mock_hm1
            else:
                mock_pool1.health_monitor = None
            mock_lb.pools = [mock_pool1]
            if mock_listener1:
                mock_listener1.pools = [mock_pool1]
                mock_listener1.default_pool = mock_pool1
            for i in range(members):
                mock_member_x = mock.Mock()
                mock_member_x.id = 'member-id-%s' % (i + 1)
                if health_monitor:
                    mock_member_x.operating_status = 'NOTHING_MATCHABLE'
                else:
                    mock_member_x.operating_status = constants.NO_MONITOR
                mock_pool1.members.append(mock_member_x)
            mock_members = mock_pool1.members

        return mock_lb, mock_listener1, mock_pool1, mock_members

    def _make_fake_lb_health_dict(self, listener=True, pool=True,
                                  health_monitor=True, members=1,
                                  lb_prov_status=constants.ACTIVE,
                                  listener_protocol=constants.PROTOCOL_TCP):

        lb_ref = {'enabled': True, 'id': self.FAKE_UUID_1,
                  constants.OPERATING_STATUS: 'bogus',
                  constants.PROVISIONING_STATUS: lb_prov_status}

        if pool:
            members_dict = {}
            if health_monitor:
                member_operating_status = 'NOTHING_MATCHABLE'
            else:
                member_operating_status = constants.NO_MONITOR

            for i in range(members):
                member_id = 'member-id-%s' % (i + 1)
                members_dict[member_id] = {
                    constants.OPERATING_STATUS: member_operating_status}

            pool_ref = {'pool-id-1': {'members': members_dict,
                        constants.OPERATING_STATUS: 'bogus'}}
            lb_ref['pools'] = pool_ref

        if listener:
            listener_ref = {'listener-id-1': {
                constants.OPERATING_STATUS: 'bogus',
                'protocol': listener_protocol}}
            lb_ref['listeners'] = listener_ref

        return lb_ref

    def test_update_health_event_stream(self):
        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.OPEN, "pools": {
                    "pool-id-1": {"status": constants.UP,
                                  "members": {"member-id-1": constants.UP,
                                              "member-id-2": constants.UP}
                                  }
                }
                }
            },
            "recv_time": time.time()
        }

        lb_ref = self._make_fake_lb_health_dict()
        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref

        self.hm.update_health(health, '192.0.2.1')
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
            "listeners": {},
            "recv_time": time.time()
        }

        lb_ref = self._make_fake_lb_health_dict(listener=False, pool=False)
        self.hm.amphora_repo.get_lb_for_health_update.return_value = lb_ref

        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_repo.get_lb_for_health_update.called)
        self.assertTrue(self.loadbalancer_repo.update.called)
        self.assertTrue(self.amphora_health_repo.replace.called)

    def test_update_health_lb_pending_no_listener(self):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {},
            "recv_time": time.time()
        }

        lb_ref = self._make_fake_lb_health_dict(
            listener=True, pool=False, lb_prov_status=constants.PENDING_UPDATE)
        self.hm.amphora_repo.get_lb_for_health_update.return_value = lb_ref

        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_repo.get_lb_for_health_update.called)
        self.assertTrue(self.loadbalancer_repo.update.called)
        self.assertTrue(self.amphora_health_repo.replace.called)

    def test_update_health_missing_listener(self):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {},
            "recv_time": time.time()
        }

        lb_ref = self._make_fake_lb_health_dict(listener=True, pool=False)
        self.hm.amphora_repo.get_lb_for_health_update.return_value = lb_ref

        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_repo.get_lb_for_health_update.called)
        self.assertTrue(self.loadbalancer_repo.update.called)
        self.assertFalse(self.amphora_health_repo.replace.called)

    def test_update_health_recv_time_stale(self):
        hb_interval = cfg.CONF.health_manager.heartbeat_interval
        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {},
            "recv_time": time.time() - hb_interval - 1  # extra -1 for buffer
        }

        lb_ref = self._make_fake_lb_health_dict(listener=False, pool=False)

        self.hm.amphora_repo.get_lb_for_health_update.return_value = lb_ref

        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_repo.get_lb_for_health_update.called)
        # Receive time is stale, so we shouldn't see this called
        self.assertFalse(self.loadbalancer_repo.update.called)

    def test_update_health_replace_error(self):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.OPEN, "pools": {
                    "pool-id-1": {"status": constants.UP,
                                  "members": {"member-id-1": constants.UP}
                                  }
                }
                }
            },
            "recv_time": time.time()
        }

        self.session_mock.commit.side_effect = TestException('boom')

        lb_ref = self._make_fake_lb_health_dict()

        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref

        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_health_repo.replace.called)
        self.session_mock.rollback.assert_called_once()

    def test_update_health_online(self):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.OPEN, "pools": {
                    "pool-id-1": {"status": constants.UP,
                                  "members": {"member-id-1": constants.UP}
                                  }
                }
                }
            },
            "recv_time": time.time()
        }

        lb_ref = self._make_fake_lb_health_dict()
        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref
        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                self.session_mock, listener_id,
                operating_status=constants.ONLINE)

            for pool_id, pool in six.iteritems(listener.get('pools', {})):

                self.hm.pool_repo.update.assert_any_call(
                    self.session_mock, pool_id,
                    operating_status=constants.ONLINE)

                for member_id, member in six.iteritems(
                        pool.get('members', {})):
                    self.member_repo.update.assert_any_call(
                        self.session_mock, member_id,
                        operating_status=constants.ONLINE)

        # If the listener count is wrong, make sure we don't update
        lb_ref['listeners']['listener-id-2'] = {
            constants.OPERATING_STATUS: 'bogus'}

        self.amphora_health_repo.replace.reset_mock()

        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(not self.amphora_health_repo.replace.called)

    def test_update_lb_pool_health_offline(self):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.OPEN, "pools": {}}
            },
            "recv_time": time.time()
        }

        lb_ref = self._make_fake_lb_health_dict()

        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref
        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                self.session_mock, listener_id,
                operating_status=constants.ONLINE)
        self.pool_repo.update.assert_any_call(
            self.session_mock, 'pool-id-1',
            operating_status=constants.OFFLINE
        )

    def test_update_lb_multiple_listeners_one_error_pool(self):
        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.OPEN, "pools": {
                    "pool-id-1": {"status": constants.DOWN,
                                  "members": {"member-id-1": constants.ERROR}}
                }},
                "listener-id-2": {"status": constants.OPEN, "pools": {
                    "pool-id-2": {"status": constants.UP,
                                  "members": {"member-id-2": constants.UP}}
                }}
            },
            "recv_time": time.time()
        }

        lb_ref = self._make_fake_lb_health_dict()

        lb_ref['pools']['pool-id-2'] = {
            constants.OPERATING_STATUS: 'bogus',
            'members': {'member-id-2': {constants.OPERATING_STATUS: 'bogus'}}}

        lb_ref['listeners']['listener-id-2'] = {
            constants.OPERATING_STATUS: 'bogus',
            'protocol': constants.PROTOCOL_TCP}

        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref
        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners')):
            self.listener_repo.update.assert_any_call(
                self.session_mock, listener_id,
                operating_status=constants.ONLINE)

        # Call count should be exactly 2, as each pool should be processed once
        self.assertEqual(2, self.pool_repo.update.call_count)
        self.pool_repo.update.assert_has_calls([
            mock.call(self.session_mock, 'pool-id-1',
                      operating_status=constants.ERROR),
            mock.call(self.session_mock, 'pool-id-2',
                      operating_status=constants.ONLINE)
        ], any_order=True)

    def test_update_lb_and_list_pool_health_online(self):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.OPEN, "pools": {
                    "pool-id-1": {"status": constants.UP,
                                  "members": {"member-id-1": constants.UP}
                                  }
                }
                }
            },
            "recv_time": time.time()
        }

        lb_ref = self._make_fake_lb_health_dict()
        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref
        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                self.session_mock, listener_id,
                operating_status=constants.ONLINE)

            for pool_id, pool in six.iteritems(listener.get('pools', {})):

                # We should not double process a shared pool
                self.hm.pool_repo.update.assert_called_once_with(
                    self.session_mock, pool_id,
                    operating_status=constants.ONLINE)

                for member_id, member in six.iteritems(
                        pool.get('members', {})):
                    self.member_repo.update.assert_any_call(
                        self.session_mock, member_id,
                        operating_status=constants.ONLINE)

    def test_update_pool_offline(self):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.OPEN, "pools": {
                    "pool-id-5": {"status": constants.UP,
                                  "members": {"member-id-1": constants.UP}
                                  }
                }
                }
            },
            "recv_time": time.time()
        }

        lb_ref = self._make_fake_lb_health_dict()

        lb_ref['pools']['pool-id-2'] = {
            constants.OPERATING_STATUS: constants.OFFLINE}

        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref
        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                self.session_mock, listener_id,
                operating_status=constants.ONLINE)

            self.hm.pool_repo.update.assert_any_call(
                self.session_mock, "pool-id-1",
                operating_status=constants.OFFLINE)

    def test_update_health_member_drain(self):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {
                    "status": constants.OPEN,
                    "pools": {
                        "pool-id-1": {
                            "status": constants.UP,
                            "members": {"member-id-1": constants.DRAIN}}}}},
            "recv_time": time.time()}

        lb_ref = self._make_fake_lb_health_dict()
        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref
        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                self.session_mock, listener_id,
                operating_status=constants.ONLINE)

            for pool_id, pool in six.iteritems(listener.get('pools', {})):

                self.hm.pool_repo.update.assert_any_call(
                    self.session_mock, pool_id,
                    operating_status=constants.ONLINE)

                for member_id, member in six.iteritems(
                        pool.get('members', {})):

                    self.member_repo.update.assert_any_call(
                        self.session_mock, member_id,
                        operating_status=constants.DRAINING)

    def test_update_health_member_maint(self):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {
                    "status": constants.OPEN,
                    "pools": {
                        "pool-id-1": {
                            "status": constants.UP,
                            "members": {"member-id-1": constants.MAINT}}}}},
            "recv_time": time.time()}

        lb_ref = self._make_fake_lb_health_dict()
        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref
        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                self.session_mock, listener_id,
                operating_status=constants.ONLINE)

            for pool_id, pool in six.iteritems(listener.get('pools', {})):

                self.hm.pool_repo.update.assert_any_call(
                    self.session_mock, pool_id,
                    operating_status=constants.ONLINE)

                for member_id, member in six.iteritems(
                        pool.get('members', {})):

                    self.member_repo.update.assert_any_call(
                        self.session_mock, member_id,
                        operating_status=constants.OFFLINE)

    def test_update_health_member_unknown(self):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {
                    "status": constants.OPEN,
                    "pools": {
                        "pool-id-1": {
                            "status": constants.UP,
                            "members": {"member-id-1": "blah"}}}}},
            "recv_time": time.time()}

        lb_ref = self._make_fake_lb_health_dict()
        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref
        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                self.session_mock, listener_id,
                operating_status=constants.ONLINE)

            for pool_id, pool in six.iteritems(listener.get('pools', {})):

                self.hm.pool_repo.update.assert_any_call(
                    self.session_mock, pool_id,
                    operating_status=constants.ONLINE)
                self.assertTrue(not self.member_repo.update.called)

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
            },
            "recv_time": time.time()
        }

        lb_ref = self._make_fake_lb_health_dict()
        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref

        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                self.session_mock, listener_id,
                operating_status=constants.ONLINE)

            for pool_id, pool in six.iteritems(listener.get('pools', {})):

                self.hm.pool_repo.update.assert_any_call(
                    self.session_mock, pool_id,
                    operating_status=constants.DEGRADED)

                for member_id, member in six.iteritems(
                        pool.get('members', {})):

                    self.member_repo.update.assert_any_call(
                        self.session_mock, member_id,
                        operating_status=constants.ERROR)

    def test_update_health_member_missing_no_hm(self):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.OPEN, "pools": {
                    "pool-id-1": {"status": constants.UP,
                                  "members": {}
                                  }
                }
                }
            },
            "recv_time": time.time()
        }

        lb_ref = self._make_fake_lb_health_dict(health_monitor=False)
        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref

        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                self.session_mock, listener_id,
                operating_status=constants.ONLINE)

            for pool_id, pool in six.iteritems(listener.get('pools', {})):

                self.hm.pool_repo.update.assert_any_call(
                    self.session_mock, pool_id,
                    operating_status=constants.ONLINE)

                self.member_repo.update.assert_not_called()

    def test_update_health_member_down_no_hm(self):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.OPEN, "pools": {
                    "pool-id-1": {"status": constants.UP,
                                  "members": {"member-id-1": constants.MAINT}
                                  }
                }
                }
            },
            "recv_time": time.time()
        }

        lb_ref = self._make_fake_lb_health_dict(health_monitor=False)
        member1 = lb_ref['pools']['pool-id-1']['members']['member-id-1']
        member1[constants.OPERATING_STATUS] = constants.NO_MONITOR

        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref

        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                self.session_mock, listener_id,
                operating_status=constants.ONLINE)

            for pool_id, pool in six.iteritems(listener.get('pools', {})):

                self.hm.pool_repo.update.assert_any_call(
                    self.session_mock, pool_id,
                    operating_status=constants.ONLINE)

                self.member_repo.update.assert_any_call(
                    self.session_mock, 'member-id-1',
                    operating_status=constants.OFFLINE)

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
            },
            "recv_time": time.time()
        }

        lb_ref = self._make_fake_lb_health_dict()
        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref
        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                self.session_mock, listener_id,
                operating_status=constants.ONLINE)

            for pool_id, pool in six.iteritems(listener.get('pools', {})):

                self.hm.pool_repo.update.assert_any_call(
                    self.session_mock, pool_id,
                    operating_status=constants.ONLINE)

                for member_id, member in six.iteritems(
                        pool.get('members', {})):

                    self.member_repo.update.assert_any_call(
                        self.session_mock, member_id,
                        operating_status=constants.NO_MONITOR)

    def test_update_health_member_admin_down(self):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {
                    "status": constants.OPEN,
                    "pools": {
                        "pool-id-1": {
                            "status": constants.UP,
                            "members": {
                                "member-id-1": constants.UP}}}}},
            "recv_time": time.time()}

        lb_ref = self._make_fake_lb_health_dict(members=2)

        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref

        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_repo.get_lb_for_health_update.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                self.session_mock, listener_id,
                operating_status=constants.ONLINE)

            for pool_id, pool in six.iteritems(listener.get('pools', {})):

                self.hm.pool_repo.update.assert_any_call(
                    self.session_mock, pool_id,
                    operating_status=constants.ONLINE)

                for member_id, member in six.iteritems(
                        pool.get('members', {})):

                    self.member_repo.update.assert_any_call(
                        self.session_mock, member_id,
                        operating_status=constants.ONLINE)
        self.member_repo.update.assert_any_call(
            self.session_mock, 'member-id-2',
            operating_status=constants.OFFLINE)

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
            },
            "recv_time": time.time()
        }

        lb_ref = self._make_fake_lb_health_dict()
        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref
        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                self.session_mock, listener_id,
                operating_status=constants.DEGRADED)

            for pool_id, pool in six.iteritems(listener.get('pools', {})):

                self.hm.pool_repo.update.assert_any_call(
                    self.session_mock, pool_id,
                    operating_status=constants.DEGRADED)

                for member_id, member in six.iteritems(
                        pool.get('members', {})):

                    self.member_repo.update.assert_any_call(
                        self.session_mock, member_id,
                        operating_status=constants.ERROR)

        lb_ref['listeners']['listener-id-2'] = {
            constants.OPERATING_STATUS: 'bogus'}

        self.amphora_health_repo.replace.reset_mock()

        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(not self.amphora_health_repo.replace.called)

    def test_update_health_error(self):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.OPEN, "pools": {
                    "pool-id-1": {"status": constants.DOWN,
                                  "members": {"member-id-1": constants.DOWN}
                                  }
                }
                }
            },
            "recv_time": time.time()
        }

        lb_ref = self._make_fake_lb_health_dict()
        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref

        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                self.session_mock, listener_id,
                operating_status=constants.ONLINE)

            for pool_id, pool in six.iteritems(listener.get('pools', {})):

                self.hm.pool_repo.update.assert_any_call(
                    self.session_mock, pool_id,
                    operating_status=constants.ERROR)

                for member_id, member in six.iteritems(
                        pool.get('members', {})):

                    self.member_repo.update.assert_any_call(
                        self.session_mock, member_id,
                        operating_status=constants.ERROR)

    # Test the logic code paths
    def test_update_health_full(self):

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
                "listener-id-4": {
                    "status": constants.OPEN,
                    "pools": {
                        "pool-id-4": {
                            "status": constants.UP,
                            "members": {"member-id-4": constants.DRAINING}
                        }
                    }
                },
                "listener-id-5": {
                    "status": "bogus",
                    "pools": {
                        "pool-id-5": {
                            "status": "bogus",
                            "members": {"member-id-5": "bogus"}
                        }
                    }
                }
            },
            "recv_time": time.time()
        }

        lb_ref = self._make_fake_lb_health_dict()
        # Build our own custom listeners/pools/members
        for i in [1, 2, 3, 4, 5]:

            lb_ref['listeners']['listener-id-%s' % i] = {
                constants.OPERATING_STATUS: 'bogus',
                'protocol': constants.PROTOCOL_TCP}

            if i == 3:
                members_dict = {'member-id-3': {
                    constants.OPERATING_STATUS: 'bogus'}, 'member-id-31': {
                        constants.OPERATING_STATUS: 'bogus'}}
            else:
                members_dict = {'member-id-%s' % i: {
                                constants.OPERATING_STATUS: 'bogus'}}
            lb_ref['pools']['pool-id-%s' % i] = {
                'members': members_dict, constants.OPERATING_STATUS: 'bogus'}

        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref

        self.hm.update_health(health, '192.0.2.1')

        # test listener
        self.listener_repo.update.assert_any_call(
            self.session_mock, "listener-id-1",
            operating_status=constants.DEGRADED)
        self.listener_repo.update.assert_any_call(
            self.session_mock, "listener-id-2",
            operating_status=constants.DEGRADED)
        self.pool_repo.update.assert_any_call(
            self.session_mock, "pool-id-1",
            operating_status=constants.ERROR)
        self.pool_repo.update.assert_any_call(
            self.session_mock, "pool-id-2",
            operating_status=constants.ONLINE)
        self.pool_repo.update.assert_any_call(
            self.session_mock, "pool-id-3",
            operating_status=constants.DEGRADED)
        self.pool_repo.update.assert_any_call(
            self.session_mock, "pool-id-4",
            operating_status=constants.ONLINE)

    # Test code paths where objects are not found in the database
    def test_update_health_not_found(self):

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.OPEN, "pools": {
                    "pool-id-1": {"status": constants.UP,
                                  "members": {"member-id-1": constants.UP}
                                  }
                }
                }
            },
            "recv_time": time.time()
        }

        self.hm.listener_repo.update.side_effect = (
            [sqlalchemy.orm.exc.NoResultFound])
        self.hm.member_repo.update.side_effect = (
            [sqlalchemy.orm.exc.NoResultFound])
        self.hm.pool_repo.update.side_effect = (
            sqlalchemy.orm.exc.NoResultFound)
        self.hm.loadbalancer_repo.update.side_effect = (
            [sqlalchemy.orm.exc.NoResultFound])

        lb_ref = self._make_fake_lb_health_dict()

        lb_ref['pools']['pool-id-2'] = {constants.OPERATING_STATUS: 'bogus'}

        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref

        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_health_repo.replace.called)

        # test listener, member
        for listener_id, listener in six.iteritems(
                health.get('listeners', {})):

            self.listener_repo.update.assert_any_call(
                self.session_mock, listener_id,
                operating_status=constants.ONLINE)

            for pool_id, pool in six.iteritems(listener.get('pools', {})):

                self.hm.pool_repo.update.assert_any_call(
                    self.session_mock, pool_id,
                    operating_status=constants.ONLINE)

                for member_id, member in six.iteritems(
                        pool.get('members', {})):

                    self.member_repo.update.assert_any_call(
                        self.session_mock, member_id,
                        operating_status=constants.ONLINE)

    @mock.patch('stevedore.driver.DriverManager.driver')
    def test_update_health_zombie(self, mock_driver):
        health = {"id": self.FAKE_UUID_1, "listeners": {}}

        self.amphora_repo.get_lb_for_health_update.return_value = None
        amp_mock = mock.MagicMock()
        self.amphora_repo.get.return_value = amp_mock
        self.hm.update_health(health, '192.0.2.1')
        mock_driver.delete.assert_called_once_with(
            amp_mock.compute_id)

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
            },
            "recv_time": time.time()
        }

        lb_ref = self._make_fake_lb_health_dict()

        # Start everything ONLINE
        lb_ref[constants.OPERATING_STATUS] = constants.ONLINE
        listener1 = lb_ref['listeners']['listener-id-1']
        listener1[constants.OPERATING_STATUS] = constants.ONLINE
        pool1 = lb_ref['pools']['pool-id-1']
        pool1[constants.OPERATING_STATUS] = constants.ONLINE
        member1 = pool1['members']['member-id-1']
        member1[constants.OPERATING_STATUS] = constants.ONLINE

        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref

        self.hm.update_health(health, '192.0.2.1')
        self.event_client.cast.assert_not_called()
        self.loadbalancer_repo.update.assert_not_called()
        self.listener_repo.update.assert_not_called()
        self.pool_repo.update.assert_not_called()
        self.member_repo.update.assert_not_called()

    def test_update_health_lb_admin_down(self):
        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {},
            "recv_time": time.time()}

        lb_ref = self._make_fake_lb_health_dict(listener=False, pool=False)
        lb_ref['enabled'] = False
        self.hm.amphora_repo.get_lb_for_health_update.return_value = lb_ref

        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_repo.get_lb_for_health_update.called)
        self.assertTrue(self.loadbalancer_repo.update.called)
        self.loadbalancer_repo.update.assert_called_with(
            self.mock_session(), self.FAKE_UUID_1,
            operating_status='OFFLINE')

    def test_update_health_lb_admin_up(self):
        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {},
            "recv_time": time.time(),
            "ver": 1}

        lb_ref = self._make_fake_lb_health_dict(listener=False, pool=False)
        self.hm.amphora_repo.get_lb_for_health_update.return_value = lb_ref

        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_repo.get_lb_for_health_update.called)
        self.assertTrue(self.loadbalancer_repo.update.called)
        self.loadbalancer_repo.update.assert_called_with(
            self.mock_session(), self.FAKE_UUID_1,
            operating_status='ONLINE')

    def test_update_health_forbid_to_stale_udp_listener_amphora(self):
        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {},
            "recv_time": time.time()
        }

        mock_lb = mock.Mock()
        mock_lb.id = self.FAKE_UUID_1
        mock_lb.pools = []
        mock_lb.listeners = []
        mock_lb.provisioning_status = constants.ACTIVE
        mock_lb.operating_status = 'blah'

        # The default pool of udp listener1 has no enabled member
        mock_member1 = mock.Mock()
        mock_member1.id = 'member-id-1'
        mock_member1.enabled = False
        mock_pool1 = mock.Mock()
        mock_pool1.id = "pool-id-1"
        mock_pool1.members = [mock_member1]
        mock_listener1 = mock.Mock()
        mock_listener1.id = 'listener-id-1'
        mock_listener1.default_pool = mock_pool1
        mock_listener1.protocol = constants.PROTOCOL_UDP

        # The default pool of udp listener2 has no member
        mock_pool2 = mock.Mock()
        mock_pool2.id = "pool-id-2"
        mock_pool2.members = []
        mock_listener2 = mock.Mock()
        mock_listener2.id = 'listener-id-2'
        mock_listener2.default_pool = mock_pool2
        mock_listener2.protocol = constants.PROTOCOL_UDP

        # The udp listener3 has no default_pool
        mock_listener3 = mock.Mock()
        mock_listener3.id = 'listener-id-3'
        mock_listener3.default_pool = None
        mock_listener3.protocol = constants.PROTOCOL_UDP

        mock_lb.listeners.extend([mock_listener1, mock_listener2,
                                  mock_listener3])
        mock_lb.pools.extend([mock_pool1, mock_pool2])

        self.loadbalancer_repo.get.return_value = mock_lb

        lb_ref = self._make_fake_lb_health_dict(
            listener_protocol=constants.PROTOCOL_UDP)
        lb_ref['listeners']['listener-id-2'] = {
            constants.OPERATING_STATUS: 'bogus',
            'protocol': constants.PROTOCOL_UDP}
        lb_ref['listeners']['listener-id-3'] = {
            constants.OPERATING_STATUS: 'bogus',
            'protocol': constants.PROTOCOL_UDP}

        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref
        self.hm.update_health(health, '192.0.2.1')
        self.assertTrue(self.amphora_repo.get_lb_for_health_update.called)
        self.assertTrue(self.loadbalancer_repo.update.called)
        self.assertTrue(self.amphora_health_repo.replace.called)

    def test_update_health_no_db_lb(self):
        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {},
            "recv_time": time.time()
        }
        self.hm.amphora_repo.get_lb_for_health_update.return_value = {}

        self.hm.update_health(health, '192.0.2.1')

        self.assertTrue(self.amphora_repo.get_lb_for_health_update.called)
        self.assertFalse(self.amphora_health_repo.replace.called)

        # Test missing amp in addition to missing lb DB record
        self.amphora_repo.get_lb_for_health_update.reset_mock()
        self.amphora_health_repo.replace.reset_mock()

        mock_amphora = mock.MagicMock()
        mock_amphora.load_balancer_id = None
        self.amphora_repo.get.return_value = mock_amphora

        self.hm.update_health(health, '192.0.2.1')

        self.assertTrue(self.amphora_repo.get_lb_for_health_update.called)
        self.assertTrue(self.amphora_repo.get.called)
        self.assertTrue(self.amphora_health_repo.replace.called)

    def test_update_health_with_without_udp_listeners(self):
        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.OPEN, "pools": {
                    "pool-id-1": {"status": constants.UP,
                                  "members": {"member-id-1": constants.DOWN}
                                  }
                }}},
            "recv_time": time.time()
        }

        # Test with a TCP listener
        lb_ref = self._make_fake_lb_health_dict(
            listener_protocol=constants.PROTOCOL_TCP)
        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref

        self.hm.update_health(health, '192.0.2.1')
        # We should have no calls to listener_repo.get, because we skip
        # running the extra UDP function
        self.assertFalse(self.listener_repo.get.called)

        # Reset the mocks to try again
        self.listener_repo.reset_mock()

        # Test with a UDP listener
        lb_ref = self._make_fake_lb_health_dict(
            listener_protocol=constants.PROTOCOL_UDP)
        self.amphora_repo.get_lb_for_health_update.return_value = lb_ref

        self.hm.update_health(health, '192.0.2.1')
        # This time we should have a call to listener_repo.get because the
        # UDP helper function is triggered
        self.assertTrue(self.listener_repo.get.called)

    def test_update_listener_count_for_UDP(self):
        mock_lb, mock_listener1, mock_pool1, mock_members = (
            self._make_mock_lb_tree())

        mock_listener1.protocol = constants.PROTOCOL_TCP

        self.hm.listener_repo.get.return_value = mock_listener1

        # Test only TCP listeners
        lb_ref = self._make_fake_lb_health_dict(
            listener_protocol=constants.PROTOCOL_TCP)
        result = self.hm._update_listener_count_for_UDP(
            'bogus_session', lb_ref, 0)
        self.assertEqual(0, result)

        # Test with a valid member
        lb_ref = self._make_fake_lb_health_dict(
            listener_protocol=constants.PROTOCOL_UDP)
        mock_listener1.protocol = constants.PROTOCOL_UDP

        result = self.hm._update_listener_count_for_UDP(
            'bogus_session', lb_ref, 1)
        self.assertEqual(1, result)

        # Test with a disabled member
        mock_listener1.protocol = constants.PROTOCOL_UDP
        mock_members[0].enabled = False

        result = self.hm._update_listener_count_for_UDP(
            'bogus_session', lb_ref, 1)
        self.assertEqual(0, result)

    def test_update_status_and_emit_event(self):

        # Test update with the same operating status
        self.conf.config(group="health_manager",
                         event_streamer_driver=constants.NOOP_EVENT_STREAMER)
        self.hm._update_status_and_emit_event(
            'fake_session', self.loadbalancer_repo, constants.LOADBALANCER,
            1, 'ONLINE', 'ONLINE')
        self.assertFalse(self.loadbalancer_repo.update.called)
        self.assertFalse(self.event_client.cast.called)

        self.conf.config(group="health_manager",
                         event_streamer_driver='queue_event_streamer',
                         sync_provisioning_status=True)

        self.loadbalancer_repo.update.reset_mock()
        self.event_client.reset_mock()

        # Test stream with provisioning sync
        self.hm._update_status_and_emit_event(
            'fake_session', self.loadbalancer_repo, constants.LOADBALANCER,
            1, 'ONLINE', 'OFFLINE')
        self.assertTrue(self.loadbalancer_repo.update.called)
        self.assertTrue(self.event_client.cast.called)

        self.conf.config(group="health_manager",
                         sync_provisioning_status=False)

        self.loadbalancer_repo.update.reset_mock()
        self.event_client.reset_mock()

        # Test stream with no provisioning sync
        self.hm._update_status_and_emit_event(
            'fake_session', self.loadbalancer_repo, constants.LOADBALANCER,
            1, 'ONLINE', 'ONLINE')
        self.assertFalse(self.loadbalancer_repo.update.called)
        self.assertFalse(self.event_client.cast.called)


class TestUpdateStatsDb(base.TestCase):

    def setUp(self):
        super(TestUpdateStatsDb, self).setUp()

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(group="health_manager",
                         event_streamer_driver='queue_event_streamer')

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
    def test_update_stats(self, mock_session):

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

        mock_session.return_value = 'blah'

        self.sm.update_stats(health, '192.0.2.1')

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

        # Test with noop streamer
        self.event_client.cast.reset_mock()
        self.conf.config(group="health_manager",
                         event_streamer_driver=constants.NOOP_EVENT_STREAMER)

        self.sm.update_stats(health, '192.0.2.1')

        self.conf.config(group="health_manager",
                         event_streamer_driver='queue_event_streamer')
        self.assertFalse(self.event_client.cast.called)

        # Test with missing DB listener
        self.event_client.cast.reset_mock()
        self.sm.repo_listener.get.return_value = None

        self.sm.update_stats(health, '192.0.2.1')

        self.event_client.cast.assert_called_once_with(
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

        # Test with update failure
        self.event_client.cast.reset_mock()
        mock_session.side_effect = Exception
        self.sm.update_stats(health, '192.0.2.1')
        self.assertFalse(self.event_client.cast.called)
