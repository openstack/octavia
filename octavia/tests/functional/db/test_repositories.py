#    Copyright 2014 Rackspace
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

import copy
import datetime
import random

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_db import exception as db_exception
from oslo_utils import uuidutils

from octavia.common import constants
from octavia.common import data_models as models
from octavia.common import exceptions
from octavia.db import api as db_api
from octavia.db import models as db_models
from octavia.db import repositories as repo
from octavia.tests.functional.db import base

CONF = cfg.CONF


class BaseRepositoryTest(base.OctaviaDBTestBase):

    FAKE_IP = "192.0.2.1"
    FAKE_UUID_1 = uuidutils.generate_uuid()
    FAKE_UUID_2 = uuidutils.generate_uuid()
    FAKE_UUID_3 = uuidutils.generate_uuid()
    FAKE_UUID_4 = uuidutils.generate_uuid()
    FAKE_UUID_5 = uuidutils.generate_uuid()
    FAKE_UUID_6 = uuidutils.generate_uuid()
    FAKE_UUID_7 = uuidutils.generate_uuid()
    FAKE_EXP_AGE = 10

    def setUp(self):
        super(BaseRepositoryTest, self).setUp()
        self.pool_repo = repo.PoolRepository()
        self.member_repo = repo.MemberRepository()
        self.lb_repo = repo.LoadBalancerRepository()
        self.vip_repo = repo.VipRepository()
        self.listener_repo = repo.ListenerRepository()
        self.listener_stats_repo = repo.ListenerStatisticsRepository()
        self.sp_repo = repo.SessionPersistenceRepository()
        self.hm_repo = repo.HealthMonitorRepository()
        self.sni_repo = repo.SNIRepository()
        self.amphora_repo = repo.AmphoraRepository()
        self.amphora_health_repo = repo.AmphoraHealthRepository()
        self.vrrp_group_repo = repo.VRRPGroupRepository()
        self.l7policy_repo = repo.L7PolicyRepository()
        self.l7rule_repo = repo.L7RuleRepository()
        self.quota_repo = repo.QuotasRepository()

    def test_get_all_return_value(self):
        pool_list, _ = self.pool_repo.get_all(self.session,
                                              project_id=self.FAKE_UUID_2)
        self.assertIsInstance(pool_list, list)
        lb_list, _ = self.lb_repo.get_all(self.session,
                                          project_id=self.FAKE_UUID_2)
        self.assertIsInstance(lb_list, list)
        listener_list, _ = self.listener_repo.get_all(
            self.session, project_id=self.FAKE_UUID_2)
        self.assertIsInstance(listener_list, list)
        member_list, _ = self.member_repo.get_all(self.session,
                                                  project_id=self.FAKE_UUID_2)
        self.assertIsInstance(member_list, list)


class AllRepositoriesTest(base.OctaviaDBTestBase):

    FAKE_UUID_1 = uuidutils.generate_uuid()
    FAKE_UUID_2 = uuidutils.generate_uuid()

    def setUp(self):
        super(AllRepositoriesTest, self).setUp()
        self.repos = repo.Repositories()
        self.load_balancer = self.repos.load_balancer.create(
            self.session, id=self.FAKE_UUID_1, project_id=self.FAKE_UUID_2,
            name="lb_name", description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        self.listener = self.repos.listener.create(
            self.session, protocol=constants.PROTOCOL_HTTP, protocol_port=80,
            enabled=True, provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            load_balancer_id=self.load_balancer.id)

    def test_all_repos_has_correct_repos(self):
        repo_attr_names = ('load_balancer', 'vip', 'health_monitor',
                           'session_persistence', 'pool', 'member', 'listener',
                           'listener_stats', 'amphora', 'sni',
                           'amphorahealth', 'vrrpgroup', 'l7rule', 'l7policy',
                           'amp_build_slots', 'amp_build_req', 'quotas')
        for repo_attr in repo_attr_names:
            single_repo = getattr(self.repos, repo_attr, None)
            message = ("Class Repositories should have %s instance"
                       " variable.") % repo_attr
            self.assertIsNotNone(single_repo, message=message)
            message = (("instance variable, %(repo_name)s, of class "
                        "Repositories should be an instance of %(base)s") %
                       {'repo_name': repo_attr,
                        'base': repo.BaseRepository.__name__})
            self.assertIsInstance(single_repo, repo.BaseRepository,
                                  msg=message)

        for attr in vars(self.repos):
            if attr.startswith('_') or attr in repo_attr_names:
                continue
            possible_repo = getattr(self.repos, attr, None)
            message = ('Class Repositories is not expected to have %s instance'
                       ' variable as a repository.' % attr)
            self.assertNotIsInstance(possible_repo, repo.BaseRepository,
                                     msg=message)

    def test_create_load_balancer_and_vip(self):
        lb = {'name': 'test1', 'description': 'desc1', 'enabled': True,
              'provisioning_status': constants.PENDING_UPDATE,
              'operating_status': constants.OFFLINE,
              'topology': constants.TOPOLOGY_ACTIVE_STANDBY,
              'vrrp_group': None,
              'provider': 'amphora',
              'server_group_id': uuidutils.generate_uuid(),
              'project_id': uuidutils.generate_uuid(),
              'id': uuidutils.generate_uuid()}
        vip = {'ip_address': '192.0.2.1',
               'port_id': uuidutils.generate_uuid(),
               'subnet_id': uuidutils.generate_uuid(),
               'network_id': uuidutils.generate_uuid(),
               'qos_policy_id': None, 'octavia_owned': True}
        lb_dm = self.repos.create_load_balancer_and_vip(self.session, lb, vip)
        lb_dm_dict = lb_dm.to_dict()
        del lb_dm_dict['vip']
        del lb_dm_dict['listeners']
        del lb_dm_dict['amphorae']
        del lb_dm_dict['pools']
        del lb_dm_dict['created_at']
        del lb_dm_dict['updated_at']
        self.assertEqual(lb, lb_dm_dict)
        vip_dm_dict = lb_dm.vip.to_dict()
        vip_dm_dict['load_balancer_id'] = lb_dm.id
        del vip_dm_dict['load_balancer']
        self.assertEqual(vip, vip_dm_dict)

    def test_create_pool_on_listener_without_sp(self):
        pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                'description': 'desc1',
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                'enabled': True, 'operating_status': constants.ONLINE,
                'project_id': uuidutils.generate_uuid(),
                'id': uuidutils.generate_uuid(),
                'provisioning_status': constants.ACTIVE}
        pool_dm = self.repos.create_pool_on_load_balancer(
            self.session, pool, listener_id=self.listener.id)
        pool_dm_dict = pool_dm.to_dict()
        del pool_dm_dict['members']
        del pool_dm_dict['health_monitor']
        del pool_dm_dict['session_persistence']
        del pool_dm_dict['listeners']
        del pool_dm_dict['load_balancer']
        del pool_dm_dict['load_balancer_id']
        del pool_dm_dict['l7policies']
        del pool_dm_dict['created_at']
        del pool_dm_dict['updated_at']
        self.assertEqual(pool, pool_dm_dict)
        new_listener = self.repos.listener.get(self.session,
                                               id=self.listener.id)
        self.assertEqual(pool_dm.id, new_listener.default_pool_id)

    def test_create_pool_on_listener_with_sp(self):
        pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                'description': 'desc1',
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                'enabled': True, 'operating_status': constants.ONLINE,
                'project_id': uuidutils.generate_uuid(),
                'id': uuidutils.generate_uuid(),
                'provisioning_status': constants.ACTIVE}
        sp = {'type': constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              'cookie_name': 'cookie_monster',
              'pool_id': pool['id'],
              'persistence_granularity': None,
              'persistence_timeout': None}
        pool.update({'session_persistence': sp})
        pool_dm = self.repos.create_pool_on_load_balancer(
            self.session, pool, listener_id=self.listener.id)
        pool_dm_dict = pool_dm.to_dict()
        del pool_dm_dict['members']
        del pool_dm_dict['health_monitor']
        del pool_dm_dict['session_persistence']
        del pool_dm_dict['listeners']
        del pool_dm_dict['load_balancer']
        del pool_dm_dict['load_balancer_id']
        del pool_dm_dict['l7policies']
        del pool_dm_dict['created_at']
        del pool_dm_dict['updated_at']
        self.assertEqual(pool, pool_dm_dict)
        sp_dm_dict = pool_dm.session_persistence.to_dict()
        del sp_dm_dict['pool']
        sp['pool_id'] = pool_dm.id
        self.assertEqual(sp, sp_dm_dict)
        new_listener = self.repos.listener.get(self.session,
                                               id=self.listener.id)
        self.assertEqual(pool_dm.id, new_listener.default_pool_id)
        new_sp = self.repos.session_persistence.get(self.session,
                                                    pool_id=pool_dm.id)
        self.assertIsNotNone(new_sp)

    def test_update_pool_without_sp(self):
        pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                'description': 'desc1',
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                'enabled': True, 'operating_status': constants.ONLINE,
                'project_id': uuidutils.generate_uuid(),
                'id': uuidutils.generate_uuid(),
                'provisioning_status': constants.ACTIVE}
        pool_dm = self.repos.create_pool_on_load_balancer(
            self.session, pool, listener_id=self.listener.id)
        update_pool = {'protocol': constants.PROTOCOL_TCP, 'name': 'up_pool'}
        new_pool_dm = self.repos.update_pool_and_sp(
            self.session, pool_dm.id, update_pool)
        pool_dm_dict = new_pool_dm.to_dict()
        del pool_dm_dict['members']
        del pool_dm_dict['health_monitor']
        del pool_dm_dict['session_persistence']
        del pool_dm_dict['listeners']
        del pool_dm_dict['load_balancer']
        del pool_dm_dict['load_balancer_id']
        del pool_dm_dict['l7policies']
        del pool_dm_dict['created_at']
        del pool_dm_dict['updated_at']
        pool.update(update_pool)
        self.assertEqual(pool, pool_dm_dict)
        self.assertIsNone(new_pool_dm.session_persistence)

    def test_update_pool_with_existing_sp(self):
        pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                'description': 'desc1',
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                'enabled': True, 'operating_status': constants.ONLINE,
                'project_id': uuidutils.generate_uuid(),
                'id': uuidutils.generate_uuid(),
                'provisioning_status': constants.ACTIVE}
        sp = {'type': constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              'cookie_name': 'cookie_monster',
              'pool_id': pool['id'],
              'persistence_granularity': None,
              'persistence_timeout': None}
        pool.update({'session_persistence': sp})
        pool_dm = self.repos.create_pool_on_load_balancer(
            self.session, pool, listener_id=self.listener.id)
        update_pool = {'protocol': constants.PROTOCOL_TCP, 'name': 'up_pool'}
        update_sp = {'type': constants.SESSION_PERSISTENCE_SOURCE_IP}
        update_pool.update({'session_persistence': update_sp})
        new_pool_dm = self.repos.update_pool_and_sp(
            self.session, pool_dm.id, update_pool)
        pool_dm_dict = new_pool_dm.to_dict()
        del pool_dm_dict['members']
        del pool_dm_dict['health_monitor']
        del pool_dm_dict['session_persistence']
        del pool_dm_dict['listeners']
        del pool_dm_dict['load_balancer']
        del pool_dm_dict['load_balancer_id']
        del pool_dm_dict['l7policies']
        del pool_dm_dict['created_at']
        del pool_dm_dict['updated_at']
        pool.update(update_pool)
        self.assertEqual(pool, pool_dm_dict)
        sp_dm_dict = new_pool_dm.session_persistence.to_dict()
        del sp_dm_dict['pool']
        sp['pool_id'] = pool_dm.id
        sp.update(update_sp)
        self.assertEqual(sp, sp_dm_dict)

    def test_update_pool_with_nonexisting_sp(self):
        pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                'description': 'desc1',
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                'enabled': True, 'operating_status': constants.ONLINE,
                'provisioning_status': constants.ACTIVE,
                'project_id': uuidutils.generate_uuid(),
                'id': uuidutils.generate_uuid()}
        pool_dm = self.repos.create_pool_on_load_balancer(
            self.session, pool, listener_id=self.listener.id)
        update_pool = {'protocol': constants.PROTOCOL_TCP, 'name': 'up_pool'}
        update_sp = {'type': constants.SESSION_PERSISTENCE_HTTP_COOKIE,
                     'cookie_name': 'monster_cookie',
                     'persistence_granularity': None,
                     'persistence_timeout': None}
        update_pool.update({'session_persistence': update_sp})
        new_pool_dm = self.repos.update_pool_and_sp(
            self.session, pool_dm.id, update_pool)
        sp_dm_dict = new_pool_dm.session_persistence.to_dict()
        del sp_dm_dict['pool']
        update_sp['pool_id'] = pool_dm.id
        update_sp.update(update_sp)
        self.assertEqual(update_sp, sp_dm_dict)

    def test_update_pool_with_nonexisting_sp_delete_sp(self):
        pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                'description': 'desc1',
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                'enabled': True, 'operating_status': constants.ONLINE,
                'provisioning_status': constants.ACTIVE,
                'project_id': uuidutils.generate_uuid(),
                'id': uuidutils.generate_uuid()}
        pool_dm = self.repos.create_pool_on_load_balancer(
            self.session, pool, listener_id=self.listener.id)
        update_pool = {'protocol': constants.PROTOCOL_TCP, 'name': 'up_pool',
                       'session_persistence': None}
        new_pool_dm = self.repos.update_pool_and_sp(
            self.session, pool_dm.id, update_pool)
        self.assertIsNone(new_pool_dm.session_persistence)

    def test_update_pool_with_existing_sp_delete_sp(self):
        pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                'description': 'desc1',
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                'enabled': True, 'operating_status': constants.ONLINE,
                'provisioning_status': constants.PENDING_CREATE,
                'project_id': uuidutils.generate_uuid(),
                'id': uuidutils.generate_uuid()}
        sp = {'type': constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              'cookie_name': 'cookie_monster',
              'pool_id': pool['id']}
        pool.update({'session_persistence': sp})
        pool_dm = self.repos.create_pool_on_load_balancer(
            self.session, pool, listener_id=self.listener.id)
        update_pool = {'protocol': constants.PROTOCOL_TCP, 'name': 'up_pool',
                       'session_persistence': {}}
        new_pool_dm = self.repos.update_pool_and_sp(
            self.session, pool_dm.id, update_pool)
        self.assertIsNone(new_pool_dm.session_persistence)

    def test_create_load_balancer_tree(self):
        project_id = uuidutils.generate_uuid()
        member = {'project_id': project_id, 'ip_address': '11.0.0.1',
                  'protocol_port': 80, 'enabled': True, 'backup': False,
                  'operating_status': constants.ONLINE,
                  'provisioning_status': constants.PENDING_CREATE,
                  'id': uuidutils.generate_uuid()}
        health_monitor = {'type': constants.HEALTH_MONITOR_HTTP, 'delay': 1,
                          'timeout': 1, 'fall_threshold': 1,
                          'rise_threshold': 1, 'enabled': True,
                          'operating_status': constants.OFFLINE,
                          'provisioning_status': constants.PENDING_CREATE}
        sp = {'type': constants.SESSION_PERSISTENCE_APP_COOKIE,
              'cookie_name': 'cookie_name'}
        pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                'description': 'desc1', 'listener_id': None,
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                'enabled': True, 'operating_status': constants.ONLINE,
                'provisioning_status': constants.PENDING_CREATE,
                'project_id': project_id, 'members': [member],
                'health_monitor': health_monitor, 'session_persistence': sp,
                'id': uuidutils.generate_uuid()}
        sp['pool_id'] = pool.get('id')
        member['pool_id'] = pool.get('id')
        health_monitor['pool_id'] = pool.get('id')
        l7rule = {'type': constants.L7RULE_TYPE_HOST_NAME,
                  'compare_type': constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
                  'operating_status': constants.ONLINE,
                  'provisioning_status': constants.PENDING_CREATE,
                  'value': 'localhost',
                  'enabled': True}
        r_health_monitor = {'type': constants.HEALTH_MONITOR_HTTP, 'delay': 1,
                            'timeout': 1, 'fall_threshold': 1,
                            'rise_threshold': 1, 'enabled': True,
                            'operating_status': constants.OFFLINE,
                            'provisioning_status': constants.PENDING_CREATE}
        redirect_pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                         'description': 'desc1', 'project_id': project_id,
                         'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                         'enabled': True, 'operating_status': constants.ONLINE,
                         'provisioning_status': constants.PENDING_CREATE,
                         'id': uuidutils.generate_uuid(),
                         'health_monitor': r_health_monitor}
        l7policy = {'name': 'l7policy1', 'enabled': True,
                    'description': 'l7policy_description', 'position': 1,
                    'action': constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
                    'redirect_pool': redirect_pool, 'l7rules': [l7rule],
                    'redirect_pool_id': redirect_pool.get('id'),
                    'id': uuidutils.generate_uuid(),
                    'provisioning_status': constants.PENDING_CREATE,
                    'operating_status': constants.ONLINE}
        l7rule['l7policy_id'] = l7policy.get('id')
        listener = {'project_id': project_id, 'name': 'listener1',
                    'description': 'listener_description',
                    'protocol': constants.PROTOCOL_HTTP, 'protocol_port': 80,
                    'connection_limit': 1, 'enabled': True,
                    'default_pool': pool, 'l7policies': [l7policy],
                    'provisioning_status': constants.PENDING_CREATE,
                    'operating_status': constants.ONLINE,
                    'id': uuidutils.generate_uuid()}
        l7policy['listener_id'] = listener.get('id')
        vip = {'ip_address': '192.0.2.1', 'port_id': uuidutils.generate_uuid(),
               'subnet_id': uuidutils.generate_uuid()}
        lb = {'name': 'lb1', 'description': 'desc1', 'enabled': True,
              'topology': constants.TOPOLOGY_ACTIVE_STANDBY,
              'vrrp_group': None, 'server_group_id': uuidutils.generate_uuid(),
              'project_id': project_id, 'vip': vip,
              'provisioning_status': constants.PENDING_CREATE,
              'operating_status': constants.ONLINE,
              'id': uuidutils.generate_uuid(), 'listeners': [listener]}
        listener['load_balancer_id'] = lb.get('id')
        pool['load_balancer_id'] = lb.get('id')
        redirect_pool['load_balancer_id'] = lb.get('id')
        lock_session = db_api.get_session(autocommit=False)
        db_lb = self.repos.create_load_balancer_tree(self.session,
                                                     lock_session, lb)
        self.assertIsNotNone(db_lb)
        self.assertIsInstance(db_lb, models.LoadBalancer)

    def test_sqlite_transactions_broken(self):
        """This test is a canary for pysqlite fixing transaction handling.

        When this test starts failing, we can fix and un-skip the deadlock
        test below: `test_create_load_balancer_tree_quotas`.
        """
        project_id = uuidutils.generate_uuid()
        vip = {'ip_address': '192.0.2.1', 'port_id': uuidutils.generate_uuid(),
               'subnet_id': uuidutils.generate_uuid()}
        lb = {'name': 'lb1', 'description': 'desc1', 'enabled': True,
              'topology': constants.TOPOLOGY_ACTIVE_STANDBY,
              'vrrp_group': None, 'server_group_id': uuidutils.generate_uuid(),
              'project_id': project_id,
              'provisioning_status': constants.PENDING_CREATE,
              'operating_status': constants.ONLINE,
              'id': uuidutils.generate_uuid()}

        session = db_api.get_session()
        lock_session = db_api.get_session(autocommit=False)
        lbs = lock_session.query(db_models.LoadBalancer).filter_by(
            project_id=project_id).all()
        self.assertEqual(0, len(lbs))  # Initially: 0
        self.repos.create_load_balancer_and_vip(lock_session, lb, vip)
        lbs = lock_session.query(db_models.LoadBalancer).filter_by(
            project_id=project_id).all()
        self.assertEqual(1, len(lbs))  # After create: 1
        lock_session.rollback()
        lbs = lock_session.query(db_models.LoadBalancer).filter_by(
            project_id=project_id).all()
        self.assertEqual(0, len(lbs))  # After rollback: 0
        self.repos.create_load_balancer_and_vip(lock_session, lb, vip)
        lbs = lock_session.query(db_models.LoadBalancer).filter_by(
            project_id=project_id).all()
        self.assertEqual(1, len(lbs))  # After create: 1
        lock_session.rollback()
        lbs = lock_session.query(db_models.LoadBalancer).filter_by(
            project_id=project_id).all()
        self.assertEqual(0, len(lbs))  # After rollback: 0
        # Force a count(), which breaks transaction integrity in pysqlite
        session.query(db_models.LoadBalancer).filter(
            db_models.LoadBalancer.project_id == project_id).count()
        self.repos.create_load_balancer_and_vip(lock_session, lb, vip)
        lbs = lock_session.query(db_models.LoadBalancer).filter_by(
            project_id=project_id).all()
        self.assertEqual(1, len(lbs))  # After create: 1
        lock_session.rollback()
        lbs = lock_session.query(db_models.LoadBalancer).filter_by(
            project_id=project_id).all()
        self.assertEqual(1, len(lbs))  # After rollback: 1 (broken!)

    def test_create_load_balancer_tree_quotas(self):
        self.skipTest("PySqlite transaction handling is broken. We can unskip"
                      "this when `test_sqlite_transactions_broken` fails.")
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', auth_strategy=constants.TESTING)
        project_id = uuidutils.generate_uuid()
        member = {'project_id': project_id, 'ip_address': '11.0.0.1',
                  'protocol_port': 80, 'enabled': True,
                  'operating_status': constants.ONLINE,
                  'id': uuidutils.generate_uuid()}
        member2 = {'project_id': project_id, 'ip_address': '11.0.0.2',
                   'protocol_port': 81, 'enabled': True,
                   'operating_status': constants.ONLINE,
                   'id': uuidutils.generate_uuid()}
        member3 = {'project_id': project_id, 'ip_address': '11.0.0.3',
                   'protocol_port': 81, 'enabled': True,
                   'operating_status': constants.ONLINE,
                   'id': uuidutils.generate_uuid()}
        health_monitor = {'type': constants.HEALTH_MONITOR_HTTP, 'delay': 1,
                          'timeout': 1, 'fall_threshold': 1,
                          'rise_threshold': 1, 'enabled': True}
        sp = {'type': constants.SESSION_PERSISTENCE_APP_COOKIE,
              'cookie_name': 'cookie_name'}
        pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                'description': 'desc1', 'listener_id': None,
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                'enabled': True, 'operating_status': constants.ONLINE,
                'project_id': project_id, 'members': [member],
                'health_monitor': health_monitor, 'session_persistence': sp,
                'id': uuidutils.generate_uuid()}
        pool2 = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool2',
                 'description': 'desc1', 'listener_id': None,
                 'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                 'enabled': True, 'operating_status': constants.ONLINE,
                 'project_id': project_id, 'members': [member2],
                 'health_monitor': health_monitor,
                 'id': uuidutils.generate_uuid()}
        sp['pool_id'] = pool.get('id')
        member['pool_id'] = pool.get('id')
        health_monitor['pool_id'] = pool.get('id')
        l7rule = {'type': constants.L7RULE_TYPE_HOST_NAME,
                  'compare_type': constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
                  'value': 'localhost'}
        r_health_monitor = {'type': constants.HEALTH_MONITOR_HTTP, 'delay': 1,
                            'timeout': 1, 'fall_threshold': 1,
                            'rise_threshold': 1, 'enabled': True}
        redirect_pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                         'description': 'desc1', 'project_id': project_id,
                         'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                         'enabled': True, 'operating_status': constants.ONLINE,
                         'id': uuidutils.generate_uuid(),
                         'health_monitor': r_health_monitor,
                         'members': [member3]}
        l7policy = {'name': 'l7policy1', 'enabled': True,
                    'description': 'l7policy_description', 'position': 1,
                    'action': constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
                    'redirect_pool': redirect_pool, 'l7rules': [l7rule],
                    'redirect_pool_id': redirect_pool.get('id'),
                    'id': uuidutils.generate_uuid()}
        l7rule['l7policy_id'] = l7policy.get('id')
        listener = {'project_id': project_id, 'name': 'listener1',
                    'description': 'listener_description',
                    'protocol': constants.PROTOCOL_HTTP, 'protocol_port': 80,
                    'connection_limit': 1, 'enabled': True,
                    'default_pool': pool, 'l7policies': [l7policy],
                    'provisioning_status': constants.PENDING_CREATE,
                    'operating_status': constants.ONLINE,
                    'id': uuidutils.generate_uuid()}
        listener2 = {'project_id': project_id, 'name': 'listener2',
                     'description': 'listener_description',
                     'protocol': constants.PROTOCOL_HTTP, 'protocol_port': 83,
                     'connection_limit': 1, 'enabled': True,
                     'default_pool': pool2,
                     'provisioning_status': constants.PENDING_CREATE,
                     'operating_status': constants.ONLINE,
                     'id': uuidutils.generate_uuid()}
        l7policy['listener_id'] = listener.get('id')
        vip = {'ip_address': '192.0.2.1', 'port_id': uuidutils.generate_uuid(),
               'subnet_id': uuidutils.generate_uuid()}
        lb = {'name': 'lb1', 'description': 'desc1', 'enabled': True,
              'topology': constants.TOPOLOGY_ACTIVE_STANDBY,
              'vrrp_group': None, 'server_group_id': uuidutils.generate_uuid(),
              'project_id': project_id, 'vip': vip,
              'provisioning_status': constants.PENDING_CREATE,
              'operating_status': constants.ONLINE,
              'id': uuidutils.generate_uuid(), 'listeners': [listener,
                                                             listener2]}
        listener['load_balancer_id'] = lb.get('id')
        listener2['load_balancer_id'] = lb.get('id')
        pool['load_balancer_id'] = lb.get('id')
        redirect_pool['load_balancer_id'] = lb.get('id')

        lb2_health_monitor = {'type': constants.HEALTH_MONITOR_HTTP,
                              'delay': 1, 'timeout': 1, 'fall_threshold': 1,
                              'rise_threshold': 1, 'enabled': True}
        lb2_member = {'project_id': project_id, 'ip_address': '11.0.0.3',
                      'protocol_port': 80, 'enabled': True,
                      'operating_status': constants.ONLINE,
                      'id': uuidutils.generate_uuid()}
        lb2_pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'lb2_pool',
                    'description': 'desc1', 'listener_id': None,
                    'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                    'enabled': True, 'operating_status': constants.ONLINE,
                    'project_id': project_id, 'members': [lb2_member],
                    'health_monitor': lb2_health_monitor,
                    'session_persistence': sp,
                    'id': uuidutils.generate_uuid()}
        lb2_listener = {'project_id': project_id, 'name': 'lb2_listener',
                        'description': 'listener_description',
                        'protocol': constants.PROTOCOL_HTTP,
                        'protocol_port': 83, 'connection_limit': 1,
                        'enabled': True,
                        'default_pool': lb2_pool,
                        'provisioning_status': constants.PENDING_CREATE,
                        'operating_status': constants.ONLINE,
                        'id': uuidutils.generate_uuid()}
        lb2 = {'name': 'lb2', 'description': 'desc2', 'enabled': True,
               'topology': constants.TOPOLOGY_ACTIVE_STANDBY,
               'vrrp_group': None,
               'server_group_id': uuidutils.generate_uuid(),
               'project_id': project_id, 'vip': vip,
               'provisioning_status': constants.PENDING_CREATE,
               'operating_status': constants.ONLINE,
               'id': uuidutils.generate_uuid(), 'listeners': [lb2_listener]}
        lb2_listener['load_balancer_id'] = lb2.get('id')
        lb2_pool['load_balancer_id'] = lb2.get('id')

        # Test zero quota
        quota = {'load_balancer': 0,
                 'listener': 10,
                 'pool': 10,
                 'health_monitor': 10,
                 'member': 10}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        lock_session = db_api.get_session(autocommit=False)
        self.assertRaises(
            exceptions.QuotaException,
            self.repos.create_load_balancer_tree,
            self.session, lock_session, copy.deepcopy(lb))
        # Make sure we didn't create the load balancer anyway
        self.assertIsNone(self.repos.load_balancer.get(self.session,
                                                       name='lb1'))

        quota = {'load_balancer': 10,
                 'listener': 0,
                 'pool': 10,
                 'health_monitor': 10,
                 'member': 10}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        lock_session = db_api.get_session(autocommit=False)
        self.assertRaises(
            exceptions.QuotaException,
            self.repos.create_load_balancer_tree,
            self.session, lock_session, copy.deepcopy(lb))
        # Make sure we didn't create the load balancer anyway
        self.assertIsNone(self.repos.load_balancer.get(self.session,
                                                       name='lb1'))

        quota = {'load_balancer': 10,
                 'listener': 10,
                 'pool': 0,
                 'health_monitor': 10,
                 'member': 10}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        lock_session = db_api.get_session(autocommit=False)
        self.assertRaises(
            exceptions.QuotaException,
            self.repos.create_load_balancer_tree,
            self.session, lock_session, copy.deepcopy(lb))
        # Make sure we didn't create the load balancer anyway
        self.assertIsNone(self.repos.load_balancer.get(self.session,
                                                       name='lb1'))

        quota = {'load_balancer': 10,
                 'listener': 10,
                 'pool': 10,
                 'health_monitor': 0,
                 'member': 10}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        lock_session = db_api.get_session(autocommit=False)
        self.assertRaises(
            exceptions.QuotaException,
            self.repos.create_load_balancer_tree,
            self.session, lock_session, copy.deepcopy(lb))
        # Make sure we didn't create the load balancer anyway
        self.assertIsNone(self.repos.load_balancer.get(self.session,
                                                       name='lb1'))

        quota = {'load_balancer': 10,
                 'listener': 10,
                 'pool': 10,
                 'health_monitor': 10,
                 'member': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        lock_session = db_api.get_session(autocommit=False)
        self.assertRaises(
            exceptions.QuotaException,
            self.repos.create_load_balancer_tree,
            self.session, lock_session, copy.deepcopy(lb))
        # Make sure we didn't create the load balancer anyway
        self.assertIsNone(self.repos.load_balancer.get(self.session,
                                                       name='lb1'))

        # Test l7policy quota for pools
        quota = {'load_balancer': 10,
                 'listener': 10,
                 'pool': 1,
                 'health_monitor': 10,
                 'member': 10}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        lock_session = db_api.get_session(autocommit=False)
        self.assertRaises(
            exceptions.QuotaException,
            self.repos.create_load_balancer_tree,
            self.session, lock_session, copy.deepcopy(lb))
        # Make sure we didn't create the load balancer anyway
        self.assertIsNone(self.repos.load_balancer.get(self.session,
                                                       name='lb1'))

        # Test l7policy quota for health monitor
        quota = {'load_balancer': 10,
                 'listener': 10,
                 'pool': 10,
                 'health_monitor': 1,
                 'member': 10}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        lock_session = db_api.get_session(autocommit=False)
        self.assertRaises(
            exceptions.QuotaException,
            self.repos.create_load_balancer_tree,
            self.session, lock_session, copy.deepcopy(lb))
        # Make sure we didn't create the load balancer anyway
        self.assertIsNone(self.repos.load_balancer.get(self.session,
                                                       name='lb1'))

        # Test l7policy quota for member
        quota = {'load_balancer': 10,
                 'listener': 10,
                 'pool': 10,
                 'health_monitor': 10,
                 'member': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        lock_session = db_api.get_session(autocommit=False)
        self.assertRaises(
            exceptions.QuotaException,
            self.repos.create_load_balancer_tree,
            self.session, lock_session, copy.deepcopy(lb))
        # Make sure we didn't create the load balancer anyway
        self.assertIsNone(self.repos.load_balancer.get(self.session,
                                                       name='lb1'))

        # ### Test load balancer quota
        # Test one quota, attempt to create another
        quota = {'load_balancer': 1,
                 'listener': 10,
                 'pool': 10,
                 'health_monitor': 10,
                 'member': 10}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        lock_session = db_api.get_session(autocommit=False)
        self.repos.create_load_balancer_tree(self.session, lock_session,
                                             copy.deepcopy(lb))
        # Check if first LB build passed quota checks
        self.assertIsNotNone(self.repos.load_balancer.get(self.session,
                                                          name='lb1'))
        # Try building another LB, it should fail
        lock_session = db_api.get_session(autocommit=False)
        self.assertRaises(
            exceptions.QuotaException,
            self.repos.create_load_balancer_tree,
            self.session, lock_session, copy.deepcopy(lb2))
        # Make sure we didn't create the load balancer anyway
        self.assertIsNone(self.repos.load_balancer.get(self.session,
                                                       name='lb2'))

        # ### Test listener quota
        # Create with custom quotas and limit to two listener (lb has two),
        # expect error of too many listeners/over quota
        quota = {'load_balancer': 10,
                 'listener': 2,
                 'pool': 10,
                 'health_monitor': 10,
                 'member': 10}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        lock_session = db_api.get_session(autocommit=False)
        self.assertRaises(
            exceptions.QuotaException,
            self.repos.create_load_balancer_tree,
            self.session, lock_session, copy.deepcopy(lb2))
        # Make sure we didn't create the load balancer anyway
        self.assertIsNone(self.repos.load_balancer.get(self.session,
                                                       name='lb2'))

        # ### Test pool quota
        # Create with custom quotas and limit to two pools (lb has two),
        # expect error of too many pool/over quota
        quota = {'load_balancer': 10,
                 'listener': 10,
                 'pool': 2,
                 'health_monitor': 10,
                 'member': 10}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        lock_session = db_api.get_session(autocommit=False)
        self.assertRaises(
            exceptions.QuotaException,
            self.repos.create_load_balancer_tree,
            self.session, lock_session, copy.deepcopy(lb2))
        # Make sure we didn't create the load balancer anyway
        self.assertIsNone(self.repos.load_balancer.get(self.session,
                                                       name='lb2'))

        # ### Test health monitor quota
        # Create with custom quotas and limit to one health monitor,
        # expect error of too many health monitor/over quota
        quota = {'load_balancer': 10,
                 'listener': 10,
                 'pool': 10,
                 'health_monitor': 1,
                 'member': 10}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        lock_session = db_api.get_session(autocommit=False)
        self.assertRaises(
            exceptions.QuotaException,
            self.repos.create_load_balancer_tree,
            self.session, lock_session, copy.deepcopy(lb2))
        # Make sure we didn't create the load balancer anyway
        self.assertIsNone(self.repos.load_balancer.get(self.session,
                                                       name='lb2'))

        # ### Test member quota
        # Create with custom quotas and limit to two member (lb has two),
        # expect error of too many member/over quota
        quota = {'load_balancer': 10,
                 'listener': 10,
                 'pool': 10,
                 'health_monitor': 10,
                 'member': 2}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        lock_session = db_api.get_session(autocommit=False)
        self.assertRaises(
            exceptions.QuotaException,
            self.repos.create_load_balancer_tree,
            self.session, lock_session, copy.deepcopy(lb2))
        # Make sure we didn't create the load balancer anyway
        self.assertIsNone(self.repos.load_balancer.get(self.session,
                                                       name='lb2'))

    def test_check_quota_met(self):

        project_id = uuidutils.generate_uuid()

        # Test auth_strategy == NOAUTH
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.LoadBalancer,
                                                    project_id))
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # Test check for missing project_id
        self.assertRaises(exceptions.MissingProjectID,
                          self.repos.check_quota_met,
                          self.session, self.session,
                          models.LoadBalancer, None)

        # Test non-quota object
        project_id = uuidutils.generate_uuid()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.SessionPersistence,
                                                    project_id))
        # Test DB deadlock case
        project_id = uuidutils.generate_uuid()
        mock_session = mock.MagicMock()
        mock_session.query = mock.MagicMock(
            side_effect=db_exception.DBDeadlock)
        self.assertRaises(exceptions.ProjectBusyException,
                          self.repos.check_quota_met,
                          self.session, mock_session,
                          models.LoadBalancer, project_id)

        # ### Test load balancer quota
        # Test with no pre-existing quota record default 0
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_load_balancer_quota=0)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.LoadBalancer,
                                                   project_id))
        self.assertIsNone(self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)

        # Test with no pre-existing quota record default 1
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_load_balancer_quota=1)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.LoadBalancer,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.LoadBalancer,
                                                   project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)

        # Test with no pre-existing quota record default unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas',
                    default_load_balancer_quota=constants.QUOTA_UNLIMITED)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.LoadBalancer,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)
        # Test above project adding another load balancer
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.LoadBalancer,
                                                    project_id))
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)

        # Test upgrade case with pre-quota load balancers
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_load_balancer_quota=1)
        lb = self.repos.load_balancer.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="lb_name",
            description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.LoadBalancer,
                                                   project_id))

        # Test upgrade case with pre-quota deleted load balancers
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_load_balancer_quota=1)
        lb = self.repos.load_balancer.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="lb_name",
            description="lb_description",
            provisioning_status=constants.DELETED,
            operating_status=constants.ONLINE,
            enabled=True)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.LoadBalancer,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)

        # Test pre-existing quota with quota of zero
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_load_balancer_quota=10)
        quota = {'load_balancer': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.LoadBalancer,
                                                   project_id))

        # Test pre-existing quota with quota of one
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_load_balancer_quota=0)
        quota = {'load_balancer': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.LoadBalancer,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.LoadBalancer,
                                                   project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)

        # Test pre-existing quota with quota of unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_load_balancer_quota=0)
        quota = {'load_balancer': constants.QUOTA_UNLIMITED}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.LoadBalancer,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)
        # Test above project adding another load balancer
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.LoadBalancer,
                                                    project_id))
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)

        # ### Test listener quota
        # Test with no pre-existing quota record default 0
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_listener_quota=0)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.Listener,
                                                   project_id))
        self.assertIsNone(self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)

        # Test with no pre-existing quota record default 1
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_listener_quota=1)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Listener,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.Listener,
                                                   project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)

        # Test with no pre-existing quota record default unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas',
                    default_listener_quota=constants.QUOTA_UNLIMITED)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Listener,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)
        # Test above project adding another listener
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Listener,
                                                    project_id))
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)

        # Test upgrade case with pre-quota listener
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_listener_quota=1)
        lb = self.repos.load_balancer.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="lb_name",
            description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True)
        self.repos.listener.create(
            self.session, protocol=constants.PROTOCOL_HTTP, protocol_port=80,
            enabled=True, provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, project_id=project_id,
            load_balancer_id=lb.id)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.Listener,
                                                   project_id))

        # Test upgrade case with pre-quota deleted listener
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_listener_quota=1)
        lb = self.repos.load_balancer.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="lb_name",
            description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True)
        self.repos.listener.create(
            self.session, protocol=constants.PROTOCOL_HTTP, protocol_port=80,
            enabled=True, provisioning_status=constants.DELETED,
            operating_status=constants.ONLINE, project_id=project_id,
            load_balancer_id=lb.id)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Listener,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)

        # Test pre-existing quota with quota of zero
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_listener_quota=10)
        quota = {'listener': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.Listener,
                                                   project_id))

        # Test pre-existing quota with quota of one
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_listener_quota=0)
        quota = {'listener': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Listener,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.Listener,
                                                   project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)

        # Test pre-existing quota with quota of unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_listener_quota=0)
        quota = {'listener': constants.QUOTA_UNLIMITED}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Listener,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)
        # Test above project adding another listener
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Listener,
                                                    project_id))
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)

        # ### Test pool quota
        # Test with no pre-existing quota record default 0
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_pool_quota=0)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.Pool,
                                                   project_id))
        self.assertIsNone(self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)

        # Test with no pre-existing quota record default 1
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_pool_quota=1)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Pool,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.Pool,
                                                   project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)

        # Test with no pre-existing quota record default unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas',
                    default_pool_quota=constants.QUOTA_UNLIMITED)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Pool,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)
        # Test above project adding another pool
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Pool,
                                                    project_id))
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)

        # Test upgrade case with pre-quota pool
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_pool_quota=1)
        lb = self.repos.load_balancer.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="lb_name",
            description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True)
        pool = self.repos.pool.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="pool1",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True, load_balancer_id=lb.id)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.Pool,
                                                   project_id))

        # Test upgrade case with pre-quota deleted pool
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_pool_quota=1)
        lb = self.repos.load_balancer.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="lb_name",
            description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True)
        pool = self.repos.pool.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="pool1",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.DELETED,
            operating_status=constants.ONLINE,
            enabled=True, load_balancer_id=lb.id)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Pool,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)

        # Test pre-existing quota with quota of zero
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_pool_quota=10)
        quota = {'pool': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.Pool,
                                                   project_id))

        # Test pre-existing quota with quota of one
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_pool_quota=0)
        quota = {'pool': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Pool,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.Pool,
                                                   project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)

        # Test pre-existing quota with quota of unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_pool_quota=0)
        quota = {'pool': constants.QUOTA_UNLIMITED}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Pool,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)
        # Test above project adding another pool
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Pool,
                                                    project_id))
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)

        # ### Test health monitor quota
        # Test with no pre-existing quota record default 0
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_health_monitor_quota=0)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.HealthMonitor,
                                                   project_id))
        self.assertIsNone(self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)

        # Test with no pre-existing quota record default 1
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_health_monitor_quota=1)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.HealthMonitor,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.HealthMonitor,
                                                   project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)

        # Test with no pre-existing quota record default unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas',
                    default_health_monitor_quota=constants.QUOTA_UNLIMITED)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.HealthMonitor,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)
        # Test above project adding another health monitor
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.HealthMonitor,
                                                    project_id))
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)

        # Test upgrade case with pre-quota health monitor
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_health_monitor_quota=1)
        lb = self.repos.load_balancer.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="lb_name",
            description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True)
        pool = self.repos.pool.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="pool1",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True, load_balancer_id=lb.id)
        self.repos.health_monitor.create(
            self.session, project_id=project_id,
            name="health_mon1", type=constants.HEALTH_MONITOR_HTTP,
            delay=1, timeout=1, fall_threshold=1, rise_threshold=1,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True, pool_id=pool.id)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.HealthMonitor,
                                                   project_id))

        # Test upgrade case with pre-quota deleted health monitor
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_health_monitor_quota=1)
        lb = self.repos.load_balancer.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="lb_name",
            description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True)
        pool = self.repos.pool.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="pool1",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True, load_balancer_id=lb.id)
        self.repos.health_monitor.create(
            self.session, project_id=project_id,
            name="health_mon1", type=constants.HEALTH_MONITOR_HTTP,
            delay=1, timeout=1, fall_threshold=1, rise_threshold=1,
            provisioning_status=constants.DELETED,
            operating_status=constants.OFFLINE,
            enabled=True, pool_id=pool.id)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.HealthMonitor,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)

        # Test pre-existing quota with quota of zero
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_health_monitor_quota=10)
        quota = {'health_monitor': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.HealthMonitor,
                                                   project_id))

        # Test pre-existing quota with quota of one
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_health_monitor_quota=0)
        quota = {'health_monitor': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.HealthMonitor,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.HealthMonitor,
                                                   project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)

        # Test pre-existing quota with quota of unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_health_monitor_quota=0)
        quota = {'health_monitor': constants.QUOTA_UNLIMITED}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.HealthMonitor,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)
        # Test above project adding another health monitor
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.HealthMonitor,
                                                    project_id))
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)

        # ### Test member quota
        # Test with no pre-existing quota record default 0
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_member_quota=0)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.Member,
                                                   project_id))
        self.assertIsNone(self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)

        # Test with no pre-existing quota record default 1
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_member_quota=1)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Member,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.Member,
                                                   project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)

        # Test with no pre-existing quota record default unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas',
                    default_member_quota=constants.QUOTA_UNLIMITED)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Member,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)
        # Test above project adding another member
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Member,
                                                    project_id))
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)

        # Test upgrade case with pre-quota member
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_member_quota=1)
        lb = self.repos.load_balancer.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="lb_name",
            description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True)
        pool = self.repos.pool.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="pool1",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True, load_balancer_id=lb.id)
        self.repos.member.create(
            self.session, project_id=project_id,
            ip_address='192.0.2.1', protocol_port=80,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True, pool_id=pool.id, backup=False)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.Member,
                                                   project_id))

        # Test upgrade case with pre-quota deleted member
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_member_quota=1)
        lb = self.repos.load_balancer.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="lb_name",
            description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True)
        pool = self.repos.pool.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="pool1",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True, load_balancer_id=lb.id)
        self.repos.member.create(
            self.session, project_id=project_id,
            ip_address='192.0.2.1', protocol_port=80,
            provisioning_status=constants.DELETED,
            operating_status=constants.ONLINE,
            enabled=True, pool_id=pool.id, backup=False)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Member,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)

        # Test pre-existing quota with quota of zero
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_member_quota=10)
        quota = {'member': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.Member,
                                                   project_id))

        # Test pre-existing quota with quota of one
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_member_quota=0)
        quota = {'member': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Member,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   models.Member,
                                                   project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)

        # Test pre-existing quota with quota of unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_member_quota=0)
        quota = {'member': constants.QUOTA_UNLIMITED}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Member,
                                                    project_id))
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)
        # Test above project adding another member
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    models.Member,
                                                    project_id))
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)

    def test_decrement_quota(self):
        # Test decrement on non-existent quota with noauth
        project_id = uuidutils.generate_uuid()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        self.repos.decrement_quota(self.session,
                                   models.LoadBalancer,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.count(self.session,
                                                    project_id=project_id))
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # Test decrement on non-existent quota
        project_id = uuidutils.generate_uuid()
        self.repos.decrement_quota(self.session,
                                   models.LoadBalancer,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.count(self.session,
                                                    project_id=project_id))

        # Test DB deadlock case
        project_id = uuidutils.generate_uuid()
        mock_session = mock.MagicMock()
        mock_session.query = mock.MagicMock(
            side_effect=db_exception.DBDeadlock)
        self.assertRaises(exceptions.ProjectBusyException,
                          self.repos.decrement_quota,
                          mock_session,
                          models.LoadBalancer, project_id)

        # ### Test load balancer quota
        # Test decrement on zero in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_load_balancer': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.LoadBalancer,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)

        # Test decrement on zero in use quota with noauth
        project_id = uuidutils.generate_uuid()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        quota = {'in_use_load_balancer': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.LoadBalancer,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # Test decrement on in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_load_balancer': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.LoadBalancer,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)

        # Test decrement on in use quota with noauth
        project_id = uuidutils.generate_uuid()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        quota = {'in_use_load_balancer': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.LoadBalancer,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # ### Test listener quota
        # Test decrement on zero in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_listener': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.Listener,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)

        # Test decrement on zero in use quota with noauth
        project_id = uuidutils.generate_uuid()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        quota = {'in_use_listener': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.Listener,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # Test decrement on in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_listener': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.Listener,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)

        # Test decrement on in use quota with noauth
        project_id = uuidutils.generate_uuid()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        quota = {'in_use_listener': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.Listener,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # ### Test pool quota
        # Test decrement on zero in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_pool': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.Pool,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)

        # Test decrement on zero in use quota with noauth
        project_id = uuidutils.generate_uuid()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        quota = {'in_use_pool': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.Pool,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # Test decrement on in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_pool': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.Pool,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)

        # Test decrement on in use quota with noauth
        project_id = uuidutils.generate_uuid()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        quota = {'in_use_pool': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.Pool,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # ### Test health monitor quota
        # Test decrement on zero in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_health_monitor': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.HealthMonitor,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)

        # Test decrement on zero in use quota with noauth
        project_id = uuidutils.generate_uuid()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        quota = {'in_use_health_monitor': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.HealthMonitor,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # Test decrement on in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_health_monitor': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.HealthMonitor,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)

        # Test decrement on in use quota with noauth
        project_id = uuidutils.generate_uuid()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        quota = {'in_use_health_monitor': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.HealthMonitor,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # ### Test member quota
        # Test decrement on zero in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_member': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.Member,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)

        # Test decrement on zero in use quota with noauth
        project_id = uuidutils.generate_uuid()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        quota = {'in_use_member': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.Member,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # Test decrement on in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_member': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.Member,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)

        # Test decrement on in use quota with noauth
        project_id = uuidutils.generate_uuid()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        quota = {'in_use_member': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   models.Member,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)


class PoolRepositoryTest(BaseRepositoryTest):

    def create_pool(self, pool_id, project_id):
        pool = self.pool_repo.create(
            self.session, id=pool_id, project_id=project_id, name="pool_test",
            description="pool_description", protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        return pool

    def test_get(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                project_id=self.FAKE_UUID_2)
        new_pool = self.pool_repo.get(self.session, id=pool.id)
        self.assertIsInstance(new_pool, models.Pool)
        self.assertEqual(pool, new_pool)

    def test_get_all(self):
        pool_one = self.create_pool(pool_id=self.FAKE_UUID_1,
                                    project_id=self.FAKE_UUID_2)
        pool_two = self.create_pool(pool_id=self.FAKE_UUID_3,
                                    project_id=self.FAKE_UUID_2)
        pool_list, _ = self.pool_repo.get_all(self.session,
                                              project_id=self.FAKE_UUID_2)
        self.assertIsInstance(pool_list, list)
        self.assertEqual(2, len(pool_list))
        self.assertEqual(pool_one, pool_list[0])
        self.assertEqual(pool_two, pool_list[1])

    def test_create(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                project_id=self.FAKE_UUID_2)
        self.assertIsInstance(pool, models.Pool)
        self.assertEqual(self.FAKE_UUID_2, pool.project_id)
        self.assertEqual("pool_test", pool.name)
        self.assertEqual("pool_description", pool.description)
        self.assertEqual(constants.PROTOCOL_HTTP, pool.protocol)
        self.assertEqual(constants.LB_ALGORITHM_ROUND_ROBIN, pool.lb_algorithm)
        self.assertEqual(constants.ONLINE, pool.operating_status)

    def test_update(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                project_id=self.FAKE_UUID_2)
        self.pool_repo.update(self.session, pool.id,
                              description="other_pool_description")
        new_pool = self.pool_repo.get(self.session, id=self.FAKE_UUID_1)
        self.assertEqual("other_pool_description", new_pool.description)

    def test_delete(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                project_id=self.FAKE_UUID_2)
        self.pool_repo.delete(self.session, id=pool.id)
        self.assertIsNone(self.pool_repo.get(self.session, id=pool.id))

    def test_delete_with_member(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                project_id=self.FAKE_UUID_2)
        member = self.member_repo.create(self.session, id=self.FAKE_UUID_3,
                                         project_id=self.FAKE_UUID_2,
                                         pool_id=pool.id,
                                         ip_address="192.0.2.1",
                                         protocol_port=80, enabled=True,
                                         provisioning_status=constants.ACTIVE,
                                         operating_status=constants.ONLINE,
                                         backup=False)
        new_pool = self.pool_repo.get(self.session, id=pool.id)
        self.assertEqual(1, len(new_pool.members))
        self.assertEqual(member, new_pool.members[0])
        self.pool_repo.delete(self.session, id=pool.id)
        self.assertIsNone(self.pool_repo.get(self.session, id=pool.id))
        self.assertIsNone(self.member_repo.get(self.session, id=member.id))

    def test_delete_with_health_monitor(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                project_id=self.FAKE_UUID_2)
        hm = self.hm_repo.create(self.session, pool_id=pool.id,
                                 type=constants.HEALTH_MONITOR_HTTP,
                                 delay=1, timeout=1, fall_threshold=1,
                                 rise_threshold=1, enabled=True,
                                 provisioning_status=constants.ACTIVE,
                                 operating_status=constants.ONLINE)
        new_pool = self.pool_repo.get(self.session, id=pool.id)
        self.assertEqual(pool, new_pool)
        self.assertEqual(hm, new_pool.health_monitor)
        self.pool_repo.delete(self.session, id=pool.id)
        self.assertIsNone(self.pool_repo.get(self.session, id=pool.id))
        self.assertIsNone(self.hm_repo.get(self.session, pool_id=hm.pool_id))

    def test_delete_with_session_persistence(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                project_id=self.FAKE_UUID_2)
        sp = self.sp_repo.create(
            self.session, pool_id=pool.id,
            type=constants.SESSION_PERSISTENCE_HTTP_COOKIE,
            cookie_name="cookie_name")
        new_pool = self.pool_repo.get(self.session, id=pool.id)
        self.assertEqual(pool, new_pool)
        self.assertEqual(sp, new_pool.session_persistence)
        self.pool_repo.delete(self.session, id=new_pool.id)
        self.assertIsNone(self.pool_repo.get(self.session, id=pool.id))
        self.assertIsNone(self.sp_repo.get(self.session, pool_id=sp.pool_id))

    def test_delete_with_all_children(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                project_id=self.FAKE_UUID_2)
        hm = self.hm_repo.create(self.session, pool_id=pool.id,
                                 type=constants.HEALTH_MONITOR_HTTP,
                                 delay=1, timeout=1, fall_threshold=1,
                                 rise_threshold=1, enabled=True,
                                 provisioning_status=constants.ACTIVE,
                                 operating_status=constants.ONLINE)
        member = self.member_repo.create(self.session, id=self.FAKE_UUID_3,
                                         project_id=self.FAKE_UUID_2,
                                         pool_id=pool.id,
                                         ip_address="192.0.2.1",
                                         protocol_port=80,
                                         provisioning_status=constants.ACTIVE,
                                         operating_status=constants.ONLINE,
                                         enabled=True,
                                         backup=False)
        sp = self.sp_repo.create(
            self.session, pool_id=pool.id,
            type=constants.SESSION_PERSISTENCE_HTTP_COOKIE,
            cookie_name="cookie_name")
        new_pool = self.pool_repo.get(self.session, id=pool.id)
        self.assertEqual(pool, new_pool)
        self.assertEqual(1, len(new_pool.members))
        new_member = self.member_repo.get(self.session, id=member.id)
        self.assertEqual(new_member, new_pool.members[0])
        self.assertEqual(hm, new_pool.health_monitor)
        self.assertEqual(sp, new_pool.session_persistence)
        self.pool_repo.delete(self.session, id=pool.id)
        self.assertIsNone(self.pool_repo.get(self.session, id=pool.id))
        self.assertIsNone(self.member_repo.get(self.session, id=member.id))
        self.assertIsNone(self.hm_repo.get(self.session, pool_id=hm.pool_id))
        self.assertIsNone(self.sp_repo.get(self.session, pool_id=sp.pool_id))


class MemberRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super(MemberRepositoryTest, self).setUp()
        self.pool = self.pool_repo.create(
            self.session, id=self.FAKE_UUID_1, project_id=self.FAKE_UUID_2,
            name="pool_test", description="pool_description",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)

    def create_member(self, member_id, project_id, pool_id, ip_address):
        member = self.member_repo.create(self.session, id=member_id,
                                         project_id=project_id,
                                         pool_id=pool_id,
                                         ip_address=ip_address,
                                         protocol_port=80,
                                         operating_status=constants.ONLINE,
                                         provisioning_status=constants.ACTIVE,
                                         enabled=True,
                                         backup=False)
        return member

    def test_get(self):
        member = self.create_member(self.FAKE_UUID_1, self.FAKE_UUID_2,
                                    self.pool.id, "192.0.2.1")
        new_member = self.member_repo.get(self.session, id=member.id)
        self.assertIsInstance(new_member, models.Member)
        self.assertEqual(member, new_member)

    def test_get_all(self):
        member_one = self.create_member(self.FAKE_UUID_1, self.FAKE_UUID_2,
                                        self.pool.id, "192.0.2.1")
        member_two = self.create_member(self.FAKE_UUID_3, self.FAKE_UUID_2,
                                        self.pool.id, "192.0.2.2")
        member_list, _ = self.member_repo.get_all(self.session,
                                                  project_id=self.FAKE_UUID_2)
        self.assertIsInstance(member_list, list)
        self.assertEqual(2, len(member_list))
        self.assertEqual(member_one, member_list[0])
        self.assertEqual(member_two, member_list[1])

    def test_create(self):
        member = self.create_member(self.FAKE_UUID_1, self.FAKE_UUID_2,
                                    self.pool.id, ip_address="192.0.2.1")
        new_member = self.member_repo.get(self.session, id=member.id)
        self.assertEqual(self.FAKE_UUID_1, new_member.id)
        self.assertEqual(self.FAKE_UUID_2, new_member.project_id)
        self.assertEqual(self.pool.id, new_member.pool_id)
        self.assertEqual("192.0.2.1", new_member.ip_address)
        self.assertEqual(80, new_member.protocol_port)
        self.assertEqual(constants.ONLINE, new_member.operating_status)
        self.assertTrue(new_member.enabled)

    def test_update(self):
        ip_address_change = "192.0.2.2"
        member = self.create_member(self.FAKE_UUID_1, self.FAKE_UUID_2,
                                    self.pool.id, "192.0.2.1")
        self.member_repo.update(self.session, id=member.id,
                                ip_address=ip_address_change)
        new_member = self.member_repo.get(self.session, id=member.id)
        self.assertEqual(ip_address_change, new_member.ip_address)

    def test_delete(self):
        member = self.create_member(self.FAKE_UUID_1, self.FAKE_UUID_2,
                                    self.pool.id, "192.0.2.1")
        self.member_repo.delete(self.session, id=member.id)
        self.assertIsNone(self.member_repo.get(self.session, id=member.id))
        new_pool = self.pool_repo.get(self.session, id=self.pool.id)
        self.assertIsNotNone(new_pool)
        self.assertEqual(0, len(new_pool.members))

    def test_update_pool_members(self):
        member1 = self.create_member(self.FAKE_UUID_1, self.FAKE_UUID_2,
                                     self.pool.id, "192.0.2.1")
        member2 = self.create_member(self.FAKE_UUID_3, self.FAKE_UUID_2,
                                     self.pool.id, "192.0.2.2")
        self.member_repo.update_pool_members(
            self.session,
            pool_id=self.pool.id,
            operating_status=constants.OFFLINE)
        new_member1 = self.member_repo.get(self.session, id=member1.id)
        new_member2 = self.member_repo.get(self.session, id=member2.id)
        self.assertEqual(constants.OFFLINE, new_member1.operating_status)
        self.assertEqual(constants.OFFLINE, new_member2.operating_status)


class SessionPersistenceRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super(SessionPersistenceRepositoryTest, self).setUp()
        self.pool = self.pool_repo.create(
            self.session, id=self.FAKE_UUID_1, project_id=self.FAKE_UUID_2,
            name="pool_test", description="pool_description",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)

    def create_session_persistence(self, pool_id):
        sp = self.sp_repo.create(
            self.session, pool_id=pool_id,
            type=constants.SESSION_PERSISTENCE_HTTP_COOKIE,
            cookie_name="cookie_name")
        return sp

    def test_get(self):
        sp = self.create_session_persistence(self.pool.id)
        new_sp = self.sp_repo.get(self.session, pool_id=sp.pool_id)
        self.assertIsInstance(new_sp, models.SessionPersistence)
        self.assertEqual(sp, new_sp)

    def test_create(self):
        sp = self.create_session_persistence(self.pool.id)
        new_sp = self.sp_repo.get(self.session, pool_id=sp.pool_id)
        self.assertEqual(self.pool.id, new_sp.pool_id)
        self.assertEqual(constants.SESSION_PERSISTENCE_HTTP_COOKIE,
                         new_sp.type)
        self.assertEqual("cookie_name", new_sp.cookie_name)

    def test_update(self):
        name_change = "new_cookie_name"
        sp = self.create_session_persistence(self.pool.id)
        self.sp_repo.update(self.session, pool_id=sp.pool_id,
                            cookie_name=name_change)
        new_sp = self.sp_repo.get(self.session, pool_id=sp.pool_id)
        self.assertEqual(name_change, new_sp.cookie_name)

    def test_delete(self):
        sp = self.create_session_persistence(self.pool.id)
        self.sp_repo.delete(self.session, pool_id=sp.pool_id)
        self.assertIsNone(self.member_repo.get(self.session,
                                               pool_id=sp.pool_id))
        new_pool = self.pool_repo.get(self.session, id=self.pool.id)
        self.assertIsNotNone(new_pool)
        self.assertIsNone(new_pool.session_persistence)


class TestListenerRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super(TestListenerRepositoryTest, self).setUp()
        self.load_balancer = self.lb_repo.create(
            self.session, id=self.FAKE_UUID_1, project_id=self.FAKE_UUID_2,
            name="lb_name", description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True,
            server_group_id=self.FAKE_UUID_1)

    def create_listener(self, listener_id, port, default_pool_id=None):
        listener = self.listener_repo.create(
            self.session, id=listener_id, project_id=self.FAKE_UUID_2,
            name="listener_name", description="listener_description",
            protocol=constants.PROTOCOL_HTTP, protocol_port=port,
            connection_limit=1, load_balancer_id=self.load_balancer.id,
            default_pool_id=default_pool_id, operating_status=constants.ONLINE,
            provisioning_status=constants.ACTIVE, enabled=True, peer_port=1025)
        return listener

    def create_amphora(self, amphora_id, loadbalancer_id):
        amphora = self.amphora_repo.create(self.session, id=amphora_id,
                                           load_balancer_id=loadbalancer_id,
                                           compute_id=self.FAKE_UUID_3,
                                           status=constants.ACTIVE,
                                           vrrp_ip=self.FAKE_IP,
                                           lb_network_ip=self.FAKE_IP)
        return amphora

    def create_loadbalancer(self, lb_id):
        lb = self.lb_repo.create(self.session, id=lb_id,
                                 project_id=self.FAKE_UUID_2, name="lb_name",
                                 description="lb_description",
                                 provisioning_status=constants.ACTIVE,
                                 operating_status=constants.ONLINE,
                                 enabled=True)
        return lb

    def test_get(self):
        listener = self.create_listener(self.FAKE_UUID_1, 80)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIsInstance(new_listener, models.Listener)
        self.assertEqual(listener, new_listener)

    def test_get_all(self):
        listener_one = self.create_listener(self.FAKE_UUID_1, 80)
        listener_two = self.create_listener(self.FAKE_UUID_3, 88)
        listener_list, _ = self.listener_repo.get_all(
            self.session, project_id=self.FAKE_UUID_2)
        self.assertIsInstance(listener_list, list)
        self.assertEqual(2, len(listener_list))
        self.assertEqual(listener_one, listener_list[0])
        self.assertEqual(listener_two, listener_list[1])

    def test_create(self):
        listener = self.create_listener(self.FAKE_UUID_1, 80)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertEqual(self.FAKE_UUID_1, new_listener.id)
        self.assertEqual(self.FAKE_UUID_2, new_listener.project_id)
        self.assertEqual("listener_name", new_listener.name)
        self.assertEqual("listener_description", new_listener.description)
        self.assertEqual(constants.PROTOCOL_HTTP, new_listener.protocol)
        self.assertEqual(80, new_listener.protocol_port)
        self.assertEqual(1, new_listener.connection_limit)
        self.assertEqual(self.load_balancer.id, new_listener.load_balancer_id)
        self.assertEqual(constants.ACTIVE, new_listener.provisioning_status)
        self.assertEqual(constants.ONLINE, new_listener.operating_status)
        self.assertEqual(1025, new_listener.peer_port)
        self.assertTrue(new_listener.enabled)

    def test_create_no_peer_port(self):
        lb = self.create_loadbalancer(uuidutils.generate_uuid())
        listener = self.listener_repo.create(
            self.session, id=self.FAKE_UUID_1, project_id=self.FAKE_UUID_2,
            load_balancer_id=lb.id, protocol=constants.PROTOCOL_HTTP,
            protocol_port=80, provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertEqual(1025, new_listener.peer_port)

    def test_create_no_peer_port_increments(self):
        lb = self.create_loadbalancer(uuidutils.generate_uuid())
        listener_a = self.listener_repo.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=self.FAKE_UUID_2,
            load_balancer_id=lb.id, protocol=constants.PROTOCOL_HTTP,
            protocol_port=80, provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        listener_b = self.listener_repo.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=self.FAKE_UUID_2,
            load_balancer_id=lb.id, protocol=constants.PROTOCOL_HTTP,
            protocol_port=81, provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        new_listener_a = self.listener_repo.get(self.session, id=listener_a.id)
        new_listener_b = self.listener_repo.get(self.session, id=listener_b.id)
        self.assertEqual(1025, new_listener_a.peer_port)
        self.assertEqual(1026, new_listener_b.peer_port)

    def test_create_listener_on_different_lb_than_default_pool(self):
        load_balancer2 = self.lb_repo.create(
            self.session, id=self.FAKE_UUID_3, project_id=self.FAKE_UUID_2,
            name="lb_name2", description="lb_description2",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        pool = self.pool_repo.create(
            self.session, id=self.FAKE_UUID_4, project_id=self.FAKE_UUID_2,
            name="pool_test", description="pool_description",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True,
            load_balancer_id=load_balancer2.id)
        self.assertRaises(exceptions.NotFound, self.create_listener,
                          self.FAKE_UUID_1, 80, default_pool_id=pool.id)

    def test_create_2_sni_containers(self):
        listener = self.create_listener(self.FAKE_UUID_1, 80)
        container1 = {'listener_id': listener.id,
                      'tls_container_id': self.FAKE_UUID_1}
        container2 = {'listener_id': listener.id,
                      'tls_container_id': self.FAKE_UUID_2}
        container1_dm = models.SNI(**container1)
        container2_dm = models.SNI(**container2)
        self.sni_repo.create(self.session, **container1)
        self.sni_repo.create(self.session, **container2)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIn(container1_dm, new_listener.sni_containers)
        self.assertIn(container2_dm, new_listener.sni_containers)

    def test_update(self):
        name_change = "new_listener_name"
        listener = self.create_listener(self.FAKE_UUID_1, 80)
        self.listener_repo.update(self.session, listener.id,
                                  name=name_change)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertEqual(name_change, new_listener.name)

    def test_delete(self):
        listener = self.create_listener(self.FAKE_UUID_1, 80)
        self.listener_repo.delete(self.session, id=listener.id)
        self.assertIsNone(self.listener_repo.get(self.session, id=listener.id))

    def test_delete_with_sni(self):
        listener = self.create_listener(self.FAKE_UUID_1, 80)
        sni = self.sni_repo.create(self.session, listener_id=listener.id,
                                   tls_container_id=self.FAKE_UUID_3)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIsNotNone(new_listener)
        self.assertEqual(sni, new_listener.sni_containers[0])
        self.listener_repo.delete(self.session, id=new_listener.id)
        self.assertIsNone(self.listener_repo.get(self.session, id=listener.id))
        self.assertIsNone(self.sni_repo.get(self.session,
                                            listener_id=listener.id))

    def test_delete_with_stats(self):
        listener = self.create_listener(self.FAKE_UUID_1, 80)
        lb = self.create_loadbalancer(uuidutils.generate_uuid())
        amphora = self.create_amphora(uuidutils.generate_uuid(), lb.id)
        self.listener_stats_repo.create(
            self.session, listener_id=listener.id, amphora_id=amphora.id,
            bytes_in=1, bytes_out=1,
            active_connections=1, total_connections=1, request_errors=1)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIsNotNone(new_listener)
        self.assertIsNotNone(self.listener_stats_repo.get(
            self.session, listener_id=listener.id))
        self.listener_repo.delete(self.session, id=listener.id)
        self.assertIsNone(self.listener_repo.get(self.session, id=listener.id))
        # ListenerStatistics should stick around
        self.assertIsNotNone(self.listener_stats_repo.get(
            self.session, listener_id=listener.id))

    def test_delete_with_pool(self):
        pool = self.pool_repo.create(
            self.session, id=self.FAKE_UUID_3, project_id=self.FAKE_UUID_2,
            name="pool_test", description="pool_description",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True,
            load_balancer_id=self.load_balancer.id)
        listener = self.create_listener(self.FAKE_UUID_1, 80,
                                        default_pool_id=pool.id)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIsNotNone(new_listener)
        self.assertEqual(pool, new_listener.default_pool)
        self.listener_repo.delete(self.session, id=new_listener.id)
        self.assertIsNone(self.listener_repo.get(self.session, id=listener.id))
        # Pool should stick around
        self.assertIsNotNone(self.pool_repo.get(self.session, id=pool.id))

    def test_delete_with_all_children(self):
        pool = self.pool_repo.create(
            self.session, id=self.FAKE_UUID_3, project_id=self.FAKE_UUID_2,
            name="pool_test", description="pool_description",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True,
            load_balancer_id=self.load_balancer.id)
        listener = self.create_listener(self.FAKE_UUID_1, 80,
                                        default_pool_id=pool.id)
        sni = self.sni_repo.create(self.session, listener_id=listener.id,
                                   tls_container_id=self.FAKE_UUID_3)
        lb = self.create_loadbalancer(uuidutils.generate_uuid())
        amphora = self.create_amphora(uuidutils.generate_uuid(), lb.id)
        self.listener_stats_repo.create(
            self.session, listener_id=listener.id,
            amphora_id=amphora.id,
            bytes_in=1, bytes_out=1,
            active_connections=1, total_connections=1, request_errors=1)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIsNotNone(new_listener)
        self.assertEqual(pool, new_listener.default_pool)
        self.assertEqual(sni, new_listener.sni_containers[0])
        self.listener_repo.delete(self.session, id=listener.id)
        self.assertIsNone(self.listener_repo.get(self.session, id=listener.id))
        self.assertIsNone(self.sni_repo.get(self.session,
                                            listener_id=listener.id))
        # ListenerStatistics should stick around
        self.assertIsNotNone(self.listener_stats_repo.get(
            self.session, listener_id=sni.listener_id))
        # Pool should stick around
        self.assertIsNotNone(self.pool_repo.get(self.session, id=pool.id))

    def test_delete_default_pool_from_beneath_listener(self):
        pool = self.pool_repo.create(
            self.session, id=self.FAKE_UUID_3, project_id=self.FAKE_UUID_2,
            name="pool_test", description="pool_description",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True,
            load_balancer_id=self.load_balancer.id)
        listener = self.create_listener(self.FAKE_UUID_1, 80,
                                        default_pool_id=pool.id)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIsNotNone(new_listener)
        self.assertEqual(pool, new_listener.default_pool)
        self.pool_repo.delete(self.session, id=pool.id)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIsNone(new_listener.default_pool)


class ListenerStatisticsRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super(ListenerStatisticsRepositoryTest, self).setUp()
        self.listener = self.listener_repo.create(
            self.session, id=self.FAKE_UUID_1, project_id=self.FAKE_UUID_2,
            name="listener_name", description="listener_description",
            protocol=constants.PROTOCOL_HTTP, protocol_port=80,
            connection_limit=1, provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True, peer_port=1025)
        self.lb = self.lb_repo.create(self.session,
                                      id=uuidutils.generate_uuid(),
                                      project_id=self.FAKE_UUID_2,
                                      name="lb_name",
                                      description="lb_description",
                                      provisioning_status=constants.ACTIVE,
                                      operating_status=constants.ONLINE,
                                      enabled=True)
        self.amphora = self.amphora_repo.create(self.session,
                                                id=uuidutils.generate_uuid(),
                                                load_balancer_id=self.lb.id,
                                                compute_id=self.FAKE_UUID_3,
                                                status=constants.ACTIVE,
                                                vrrp_ip=self.FAKE_IP,
                                                lb_network_ip=self.FAKE_IP)

    def create_listener_stats(self, listener_id, amphora_id):
        stats = self.listener_stats_repo.create(
            self.session, listener_id=listener_id, amphora_id=amphora_id,
            bytes_in=1, bytes_out=1,
            active_connections=1, total_connections=1, request_errors=1)
        return stats

    def test_get(self):
        stats = self.create_listener_stats(self.listener.id, self.amphora.id)
        new_stats = self.listener_stats_repo.get(self.session,
                                                 listener_id=stats.listener_id)
        self.assertIsInstance(new_stats, models.ListenerStatistics)
        self.assertEqual(stats.listener_id, new_stats.listener_id)

    def test_create(self):
        stats = self.create_listener_stats(self.listener.id, self.amphora.id)
        new_stats = self.listener_stats_repo.get(self.session,
                                                 listener_id=stats.listener_id)
        self.assertEqual(self.listener.id, new_stats.listener_id)
        self.assertEqual(1, new_stats.bytes_in)
        self.assertEqual(1, new_stats.bytes_out)
        self.assertEqual(1, new_stats.active_connections)
        self.assertEqual(1, new_stats.total_connections)
        self.assertEqual(1, new_stats.request_errors)

    def test_update(self):
        bytes_in_change = 2
        stats = self.create_listener_stats(self.listener.id, self.amphora.id)
        self.listener_stats_repo.update(self.session, stats.listener_id,
                                        bytes_in=bytes_in_change)
        new_stats = self.listener_stats_repo.get(self.session,
                                                 listener_id=stats.listener_id)
        self.assertIsInstance(new_stats, models.ListenerStatistics)
        self.assertEqual(stats.listener_id, new_stats.listener_id)

    def test_delete(self):
        stats = self.create_listener_stats(self.listener.id, self.amphora.id)
        self.listener_stats_repo.delete(self.session,
                                        listener_id=stats.listener_id)
        self.assertIsNone(self.listener_stats_repo.get(
            self.session, listener_id=stats.listener_id))
        new_listener = self.listener_repo.get(self.session,
                                              id=self.listener.id)
        self.assertIsNotNone(new_listener)
        self.assertIsNone(new_listener.stats)

    def test_replace(self):
        # Test the create path
        bytes_in = random.randrange(1000000000)
        bytes_out = random.randrange(1000000000)
        active_conns = random.randrange(1000000000)
        total_conns = random.randrange(1000000000)
        request_errors = random.randrange(1000000000)
        self.assertIsNone(self.listener_stats_repo.get(
            self.session, listener_id=self.listener.id))
        self.listener_stats_repo.replace(self.session, self.listener.id,
                                         self.amphora.id,
                                         bytes_in=bytes_in,
                                         bytes_out=bytes_out,
                                         active_connections=active_conns,
                                         total_connections=total_conns,
                                         request_errors=request_errors)
        obj = self.listener_stats_repo.get(self.session,
                                           listener_id=self.listener.id)
        self.assertIsNotNone(obj)
        self.assertEqual(self.listener.id, obj.listener_id)
        self.assertEqual(bytes_in, obj.bytes_in)
        self.assertEqual(bytes_out, obj.bytes_out)
        self.assertEqual(active_conns, obj.active_connections)
        self.assertEqual(total_conns, obj.total_connections)
        self.assertEqual(request_errors, obj.request_errors)

        # Test the update path
        bytes_in_2 = random.randrange(1000000000)
        bytes_out_2 = random.randrange(1000000000)
        active_conns_2 = random.randrange(1000000000)
        total_conns_2 = random.randrange(1000000000)
        request_errors_2 = random.randrange(1000000000)
        self.listener_stats_repo.replace(self.session, self.listener.id,
                                         self.amphora.id,
                                         bytes_in=bytes_in_2,
                                         bytes_out=bytes_out_2,
                                         active_connections=active_conns_2,
                                         total_connections=total_conns_2,
                                         request_errors=request_errors_2)
        obj = self.listener_stats_repo.get(self.session,
                                           listener_id=self.listener.id)
        self.assertIsNotNone(obj)
        self.assertEqual(self.listener.id, obj.listener_id)
        self.assertEqual(bytes_in_2, obj.bytes_in)
        self.assertEqual(bytes_out_2, obj.bytes_out)
        self.assertEqual(active_conns_2, obj.active_connections)
        self.assertEqual(total_conns_2, obj.total_connections)
        self.assertEqual(request_errors_2, obj.request_errors)


class HealthMonitorRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super(HealthMonitorRepositoryTest, self).setUp()
        self.pool = self.pool_repo.create(
            self.session, id=self.FAKE_UUID_1, project_id=self.FAKE_UUID_2,
            name="pool_test", description="pool_description",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        self.pool2 = self.pool_repo.create(
            self.session, id=self.FAKE_UUID_2, project_id=self.FAKE_UUID_2,
            name="pool2_test", description="pool2_description",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)

    def create_health_monitor(self, hm_id, pool_id):
        health_monitor = self.hm_repo.create(
            self.session, type=constants.HEALTH_MONITOR_HTTP, id=hm_id,
            pool_id=pool_id, delay=1, timeout=1, fall_threshold=1,
            rise_threshold=1, http_method="POST",
            url_path="http://localhost:80/index.php",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            expected_codes="200", enabled=True)
        self.assertEqual(hm_id, health_monitor.id)
        return health_monitor

    def test_get(self):
        hm = self.create_health_monitor(self.FAKE_UUID_3, self.pool.id)
        new_hm = self.hm_repo.get(self.session, id=hm.id)
        self.assertIsInstance(new_hm, models.HealthMonitor)
        self.assertEqual(hm, new_hm)

    def test_create(self):
        hm = self.create_health_monitor(self.FAKE_UUID_3, self.pool.id)
        new_hm = self.hm_repo.get(self.session, id=hm.id)
        self.assertEqual(constants.HEALTH_MONITOR_HTTP, new_hm.type)
        self.assertEqual(self.pool.id, new_hm.pool_id)
        self.assertEqual(1, new_hm.delay)
        self.assertEqual(1, new_hm.timeout)
        self.assertEqual(1, new_hm.fall_threshold)
        self.assertEqual(1, new_hm.rise_threshold)
        self.assertEqual("POST", new_hm.http_method)
        self.assertEqual("http://localhost:80/index.php", new_hm.url_path)
        self.assertEqual("200", new_hm.expected_codes)
        self.assertTrue(new_hm.enabled)

    def test_update(self):
        delay_change = 2
        hm = self.create_health_monitor(self.FAKE_UUID_3, self.pool.id)
        self.hm_repo.update(
            self.session, hm.id, delay=delay_change)
        new_hm = self.hm_repo.get(self.session, id=hm.id)
        self.assertEqual(delay_change, new_hm.delay)

    def test_delete(self):
        hm = self.create_health_monitor(self.FAKE_UUID_3, self.pool.id)
        self.hm_repo.delete(self.session, id=hm.id)
        self.assertIsNone(self.hm_repo.get(self.session, id=hm.id))
        new_pool = self.pool_repo.get(self.session, id=self.pool.id)
        self.assertIsNotNone(new_pool)
        self.assertIsNone(new_pool.health_monitor)


class LoadBalancerRepositoryTest(BaseRepositoryTest):

    def create_loadbalancer(self, lb_id):
        lb = self.lb_repo.create(self.session, id=lb_id,
                                 project_id=self.FAKE_UUID_2, name="lb_name",
                                 description="lb_description",
                                 provisioning_status=constants.ACTIVE,
                                 operating_status=constants.ONLINE,
                                 enabled=True)
        return lb

    def test_get(self):
        lb = self.create_loadbalancer(self.FAKE_UUID_1)
        new_lb = self.lb_repo.get(self.session, id=lb.id)
        self.assertIsInstance(new_lb, models.LoadBalancer)
        self.assertEqual(lb, new_lb)

    def test_get_all(self):
        lb_one = self.create_loadbalancer(self.FAKE_UUID_1)
        lb_two = self.create_loadbalancer(self.FAKE_UUID_3)
        lb_list, _ = self.lb_repo.get_all(self.session,
                                          project_id=self.FAKE_UUID_2)
        self.assertEqual(2, len(lb_list))
        self.assertEqual(lb_one, lb_list[0])
        self.assertEqual(lb_two, lb_list[1])

    def test_create(self):
        lb = self.create_loadbalancer(self.FAKE_UUID_1)
        self.assertEqual(self.FAKE_UUID_1, lb.id)
        self.assertEqual(self.FAKE_UUID_2, lb.project_id)
        self.assertEqual("lb_name", lb.name)
        self.assertEqual("lb_description", lb.description)
        self.assertEqual(constants.ACTIVE, lb.provisioning_status)
        self.assertEqual(constants.ONLINE, lb.operating_status)
        self.assertTrue(lb.enabled)

    def test_update(self):
        name_change = "load_balancer_name"
        lb = self.create_loadbalancer(self.FAKE_UUID_1)
        self.lb_repo.update(self.session, lb.id, name=name_change)
        new_lb = self.lb_repo.get(self.session, id=lb.id)
        self.assertEqual(name_change, new_lb.name)

    def test_delete(self):
        lb = self.create_loadbalancer(self.FAKE_UUID_1)
        self.lb_repo.delete(self.session, id=lb.id)
        self.assertIsNone(self.lb_repo.get(self.session, id=lb.id))

    def test_delete_with_amphora(self):
        lb = self.create_loadbalancer(self.FAKE_UUID_1)
        amphora = self.amphora_repo.create(self.session, id=self.FAKE_UUID_1,
                                           load_balancer_id=lb.id,
                                           compute_id=self.FAKE_UUID_3,
                                           status=constants.ACTIVE,
                                           vrrp_ip=self.FAKE_IP,
                                           lb_network_ip=self.FAKE_IP)
        new_lb = self.lb_repo.get(self.session, id=lb.id)
        self.assertIsNotNone(new_lb)
        self.assertEqual(1, len(new_lb.amphorae))
        self.assertEqual(amphora, new_lb.amphorae[0])
        self.lb_repo.delete(self.session, id=new_lb.id)
        self.assertIsNone(self.lb_repo.get(self.session, id=lb.id))
        new_amphora = self.amphora_repo.get(self.session, id=amphora.id)
        self.assertIsNotNone(new_amphora)
        self.assertIsNone(new_amphora.load_balancer_id)

    def test_delete_with_many_amphora(self):
        lb = self.create_loadbalancer(self.FAKE_UUID_1)
        amphora_1 = self.amphora_repo.create(self.session, id=self.FAKE_UUID_1,
                                             load_balancer_id=lb.id,
                                             compute_id=self.FAKE_UUID_3,
                                             status=constants.ACTIVE)
        amphora_2 = self.amphora_repo.create(self.session, id=self.FAKE_UUID_3,
                                             load_balancer_id=lb.id,
                                             compute_id=self.FAKE_UUID_3,
                                             lb_network_ip=self.FAKE_IP,
                                             vrrp_ip=self.FAKE_IP,
                                             status=constants.ACTIVE)
        new_lb = self.lb_repo.get(self.session, id=lb.id)
        self.assertIsNotNone(new_lb)
        self.assertEqual(2, len(new_lb.amphorae))
        self.assertIn(amphora_1, new_lb.amphorae)
        self.assertIn(amphora_2, new_lb.amphorae)
        self.lb_repo.delete(self.session, id=new_lb.id)
        self.assertIsNone(self.lb_repo.get(self.session, id=lb.id))
        new_amphora_1 = self.amphora_repo.get(self.session, id=amphora_1.id)
        new_amphora_2 = self.amphora_repo.get(self.session, id=amphora_2.id)
        self.assertIsNotNone(new_amphora_1)
        self.assertIsNotNone(new_amphora_2)
        self.assertIsNone(new_amphora_1.load_balancer_id)
        self.assertIsNone(new_amphora_2.load_balancer_id)

    def test_delete_with_vip(self):
        lb = self.create_loadbalancer(self.FAKE_UUID_1)
        vip = self.vip_repo.create(self.session, load_balancer_id=lb.id,
                                   ip_address="192.0.2.1")
        new_lb = self.lb_repo.get(self.session, id=lb.id)
        self.assertIsNotNone(new_lb)
        self.assertIsNotNone(new_lb.vip)
        self.assertEqual(vip, new_lb.vip)
        self.lb_repo.delete(self.session, id=new_lb.id)
        self.assertIsNone(self.lb_repo.get(self.session, id=lb.id))
        self.assertIsNone(self.vip_repo.get(self.session,
                                            load_balancer_id=lb.id))

    def test_delete_with_listener(self):
        lb = self.create_loadbalancer(self.FAKE_UUID_1)
        listener = self.listener_repo.create(
            self.session, id=self.FAKE_UUID_1, project_id=self.FAKE_UUID_2,
            name="listener_name", description="listener_description",
            load_balancer_id=lb.id, protocol=constants.PROTOCOL_HTTP,
            protocol_port=80, connection_limit=1,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        new_lb = self.lb_repo.get(self.session, id=lb.id)
        self.assertIsNotNone(new_lb)
        self.assertEqual(1, len(new_lb.listeners))
        self.assertEqual(listener, new_lb.listeners[0])
        self.lb_repo.delete(self.session, id=new_lb.id)
        self.assertIsNone(self.lb_repo.get(self.session, id=lb.id))
        self.assertIsNone(self.listener_repo.get(self.session, id=listener.id))

    def test_delete_with_many_listeners(self):
        lb = self.create_loadbalancer(self.FAKE_UUID_1)
        listener_1 = self.listener_repo.create(
            self.session, id=self.FAKE_UUID_1, project_id=self.FAKE_UUID_2,
            name="listener_name", description="listener_description",
            load_balancer_id=lb.id, protocol=constants.PROTOCOL_HTTP,
            protocol_port=80, connection_limit=1,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        listener_2 = self.listener_repo.create(
            self.session, id=self.FAKE_UUID_3, project_id=self.FAKE_UUID_2,
            name="listener_name", description="listener_description",
            load_balancer_id=lb.id, protocol=constants.PROTOCOL_HTTPS,
            protocol_port=443, connection_limit=1,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        new_lb = self.lb_repo.get(self.session, id=lb.id)
        self.assertIsNotNone(new_lb)
        self.assertEqual(2, len(new_lb.listeners))
        self.assertIn(listener_1, new_lb.listeners)
        self.assertIn(listener_2, new_lb.listeners)
        self.lb_repo.delete(self.session, id=new_lb.id)
        self.assertIsNone(self.lb_repo.get(self.session, id=lb.id))
        self.assertIsNone(self.listener_repo.get(self.session,
                                                 id=listener_1.id))
        self.assertIsNone(self.listener_repo.get(self.session,
                                                 id=listener_2.id))

    def test_delete_with_all_children(self):
        lb = self.create_loadbalancer(self.FAKE_UUID_1)
        amphora = self.amphora_repo.create(self.session, id=self.FAKE_UUID_1,
                                           load_balancer_id=lb.id,
                                           compute_id=self.FAKE_UUID_3,
                                           lb_network_ip=self.FAKE_IP,
                                           status=constants.ACTIVE)
        vip = self.vip_repo.create(self.session, load_balancer_id=lb.id,
                                   ip_address="192.0.2.1")
        listener = self.listener_repo.create(
            self.session, id=self.FAKE_UUID_1, project_id=self.FAKE_UUID_2,
            name="listener_name", description="listener_description",
            load_balancer_id=lb.id, protocol=constants.PROTOCOL_HTTP,
            protocol_port=80, connection_limit=1,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        new_lb = self.lb_repo.get(self.session, id=lb.id)
        self.assertIsNotNone(new_lb)
        self.assertIsNotNone(new_lb.vip)
        self.assertEqual(vip, new_lb.vip)
        self.assertEqual(1, len(new_lb.amphorae))
        self.assertEqual(1, len(new_lb.listeners))
        self.assertEqual(amphora, new_lb.amphorae[0])
        self.assertEqual(listener, new_lb.listeners[0])
        self.lb_repo.delete(self.session, id=new_lb.id)
        self.assertIsNone(self.lb_repo.get(self.session, id=lb.id))
        new_amphora = self.amphora_repo.get(self.session, id=amphora.id)
        self.assertIsNotNone(new_amphora)
        self.assertIsNone(new_amphora.load_balancer_id)
        self.assertIsNone(self.vip_repo.get(self.session,
                                            load_balancer_id=lb.id))
        self.assertIsNone(self.listener_repo.get(self.session, id=listener.id))

    def test_test_and_set_provisioning_status_immutable(self):
        lb_id = uuidutils.generate_uuid()
        self.lb_repo.create(self.session, id=lb_id,
                            provisioning_status=constants.PENDING_CREATE,
                            operating_status=constants.OFFLINE,
                            enabled=True)
        self.assertFalse(self.lb_repo.test_and_set_provisioning_status(
            self.session, lb_id, constants.PENDING_UPDATE))
        lb = self.lb_repo.get(self.session, id=lb_id)
        self.assertEqual(constants.PENDING_CREATE, lb.provisioning_status)

    def test_test_and_set_provisioning_status_immutable_raise(self):
        lb_id = uuidutils.generate_uuid()
        self.lb_repo.create(self.session, id=lb_id,
                            provisioning_status=constants.PENDING_CREATE,
                            operating_status=constants.OFFLINE,
                            enabled=True)
        self.assertRaises(exceptions.ImmutableObject,
                          self.lb_repo.test_and_set_provisioning_status,
                          self.session, lb_id,
                          status=constants.PENDING_UPDATE,
                          raise_exception=True)
        lb = self.lb_repo.get(self.session, id=lb_id)
        self.assertEqual(constants.PENDING_CREATE, lb.provisioning_status)

    def test_test_and_set_provisioning_status_mutable(self):
        lb_id = uuidutils.generate_uuid()
        self.lb_repo.create(self.session, id=lb_id,
                            provisioning_status=constants.ACTIVE,
                            operating_status=constants.OFFLINE,
                            enabled=True)
        self.lb_repo.test_and_set_provisioning_status(
            self.session, lb_id, constants.PENDING_UPDATE)
        lb = self.lb_repo.get(self.session, id=lb_id)
        self.assertEqual(constants.PENDING_UPDATE, lb.provisioning_status)

    def test_test_and_set_provisioning_status_error_on_delete(self):
        lb_id = uuidutils.generate_uuid()
        self.lb_repo.create(self.session, id=lb_id,
                            provisioning_status=constants.ERROR,
                            operating_status=constants.OFFLINE,
                            enabled=True)
        self.lb_repo.test_and_set_provisioning_status(
            self.session, lb_id, constants.PENDING_DELETE)
        lb = self.lb_repo.get(self.session, id=lb_id)
        self.assertEqual(constants.PENDING_DELETE, lb.provisioning_status)

    def test_set_status_for_failover_immutable(self):
        lb_id = uuidutils.generate_uuid()
        self.lb_repo.create(self.session, id=lb_id,
                            provisioning_status=constants.PENDING_CREATE,
                            operating_status=constants.OFFLINE,
                            enabled=True)
        self.assertFalse(self.lb_repo.set_status_for_failover(
            self.session, lb_id, constants.PENDING_UPDATE))
        lb = self.lb_repo.get(self.session, id=lb_id)
        self.assertEqual(constants.PENDING_CREATE, lb.provisioning_status)

    def test_set_status_for_failover_immutable_raise(self):
        lb_id = uuidutils.generate_uuid()
        self.lb_repo.create(self.session, id=lb_id,
                            provisioning_status=constants.PENDING_CREATE,
                            operating_status=constants.OFFLINE,
                            enabled=True)
        self.assertRaises(exceptions.ImmutableObject,
                          self.lb_repo.set_status_for_failover,
                          self.session, lb_id,
                          status=constants.PENDING_UPDATE,
                          raise_exception=True)
        lb = self.lb_repo.get(self.session, id=lb_id)
        self.assertEqual(constants.PENDING_CREATE, lb.provisioning_status)

    def test_set_status_for_failover_mutable(self):
        lb_id = uuidutils.generate_uuid()
        self.lb_repo.create(self.session, id=lb_id,
                            provisioning_status=constants.ACTIVE,
                            operating_status=constants.OFFLINE,
                            enabled=True)
        self.lb_repo.set_status_for_failover(
            self.session, lb_id, constants.PENDING_UPDATE)
        lb = self.lb_repo.get(self.session, id=lb_id)
        self.assertEqual(constants.PENDING_UPDATE, lb.provisioning_status)

    def test_set_status_for_failover_error(self):
        lb_id = uuidutils.generate_uuid()
        self.lb_repo.create(self.session, id=lb_id,
                            provisioning_status=constants.ERROR,
                            operating_status=constants.OFFLINE,
                            enabled=True)
        self.lb_repo.set_status_for_failover(
            self.session, lb_id, constants.PENDING_UPDATE)
        lb = self.lb_repo.get(self.session, id=lb_id)
        self.assertEqual(constants.PENDING_UPDATE, lb.provisioning_status)

    def test_check_load_balancer_expired_default_exp_age(self):
        """When exp_age defaults to load_balancer_expiry_age."""
        newdate = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
        self.lb_repo.create(self.session, id=self.FAKE_UUID_1,
                            project_id=self.FAKE_UUID_2,
                            provisioning_status=constants.ACTIVE,
                            operating_status=constants.ONLINE,
                            enabled=True,
                            updated_at=newdate)
        check_res = self.lb_repo.check_load_balancer_expired(
            self.session, self.FAKE_UUID_1)
        # Default load_balancer_expiry_age value is 1 week so load balancer
        # shouldn't be considered expired.
        self.assertFalse(check_res)

    def test_check_load_balancer_expired_with_exp_age(self):
        """When exp_age is passed as an argument."""
        exp_age = datetime.timedelta(
            seconds=self.FAKE_EXP_AGE)
        newdate = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
        self.lb_repo.create(self.session, id=self.FAKE_UUID_1,
                            project_id=self.FAKE_UUID_2,
                            provisioning_status=constants.ACTIVE,
                            operating_status=constants.ONLINE,
                            enabled=True,
                            updated_at=newdate)
        check_res = self.lb_repo.check_load_balancer_expired(
            self.session, self.FAKE_UUID_1, exp_age)
        self.assertTrue(check_res)


class VipRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super(VipRepositoryTest, self).setUp()
        self.lb = self.lb_repo.create(
            self.session, id=self.FAKE_UUID_1, project_id=self.FAKE_UUID_2,
            name="lb_name", description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)

    def create_vip(self, lb_id):
        vip = self.vip_repo.create(self.session, load_balancer_id=lb_id,
                                   ip_address="192.0.2.1")
        return vip

    def test_get(self):
        vip = self.create_vip(self.lb.id)
        new_vip = self.vip_repo.get(self.session,
                                    load_balancer_id=vip.load_balancer_id)
        self.assertIsInstance(new_vip, models.Vip)
        self.assertEqual(vip, new_vip)

    def test_create(self):
        vip = self.create_vip(self.lb.id)
        self.assertEqual(self.lb.id, vip.load_balancer_id)
        self.assertEqual("192.0.2.1", vip.ip_address)

    def test_update(self):
        address_change = "192.0.2.2"
        vip = self.create_vip(self.lb.id)
        self.vip_repo.update(self.session, vip.load_balancer_id,
                             ip_address=address_change)
        new_vip = self.vip_repo.get(self.session,
                                    load_balancer_id=vip.load_balancer_id)
        self.assertEqual(address_change, new_vip.ip_address)

    def test_delete(self):
        vip = self.create_vip(self.lb.id)
        self.vip_repo.delete(self.session,
                             load_balancer_id=vip.load_balancer_id)
        self.assertIsNone(self.vip_repo.get(
            self.session, load_balancer_id=vip.load_balancer_id))
        new_lb = self.lb_repo.get(self.session, id=self.lb.id)
        self.assertIsNotNone(new_lb)
        self.assertIsNone(new_lb.vip)


class SNIRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super(SNIRepositoryTest, self).setUp()
        self.listener = self.listener_repo.create(
            self.session, id=self.FAKE_UUID_1, project_id=self.FAKE_UUID_2,
            name="listener_name", description="listener_description",
            protocol=constants.PROTOCOL_HTTP, protocol_port=80,
            connection_limit=1, provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True, peer_port=1025)

    def create_sni(self, listener_id):
        sni = self.sni_repo.create(self.session,
                                   listener_id=listener_id,
                                   tls_container_id=self.FAKE_UUID_3,
                                   position=0)
        return sni

    def test_get(self):
        sni = self.create_sni(self.listener.id)
        new_sni = self.sni_repo.get(self.session, listener_id=sni.listener_id)
        self.assertIsInstance(new_sni, models.SNI)
        self.assertEqual(sni, new_sni)

    def test_create(self):
        sni = self.create_sni(self.listener.id)
        new_sni = self.sni_repo.get(self.session, listener_id=sni.listener_id)
        self.assertEqual(self.listener.id, new_sni.listener_id)
        self.assertEqual(self.FAKE_UUID_3, new_sni.tls_container_id)
        self.assertEqual(0, new_sni.position)

    def test_update(self):
        position_change = 10
        sni = self.create_sni(self.listener.id)
        self.sni_repo.update(self.session, listener_id=sni.listener_id,
                             position=position_change)
        new_sni = self.sni_repo.get(self.session, listener_id=sni.listener_id)
        self.assertEqual(position_change, new_sni.position)

    def test_delete(self):
        sni = self.create_sni(self.listener.id)
        self.sni_repo.delete(self.session, listener_id=sni.listener_id)
        self.assertIsNone(self.sni_repo.get(self.session,
                                            listener_id=sni.listener_id))
        new_listener = self.listener_repo.get(self.session,
                                              id=self.listener.id)
        self.assertIsNotNone(new_listener)
        self.assertEqual(0, len(new_listener.sni_containers))


class AmphoraRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super(AmphoraRepositoryTest, self).setUp()
        self.lb = self.lb_repo.create(
            self.session, id=self.FAKE_UUID_1, project_id=self.FAKE_UUID_2,
            name="lb_name", description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)

    def create_amphora(self, amphora_id, **overrides):
        settings = {
            'id': amphora_id,
            'compute_id': self.FAKE_UUID_3,
            'status': constants.ACTIVE,
            'lb_network_ip': self.FAKE_IP,
            'vrrp_ip': self.FAKE_IP,
            'ha_ip': self.FAKE_IP,
            'role': constants.ROLE_MASTER,
            'cert_expiration': datetime.datetime.utcnow(),
            'cert_busy': False
        }
        settings.update(overrides)
        amphora = self.amphora_repo.create(self.session, **settings)
        return amphora

    def test_get(self):
        amphora = self.create_amphora(self.FAKE_UUID_1)
        new_amphora = self.amphora_repo.get(self.session, id=amphora.id)
        self.assertIsInstance(new_amphora, models.Amphora)
        self.assertEqual(amphora, new_amphora)

    def test_count(self):
        amphora = self.create_amphora(self.FAKE_UUID_1)
        amp_count = self.amphora_repo.count(self.session, id=amphora.id)
        self.assertEqual(1, amp_count)

    def test_create(self):
        amphora = self.create_amphora(self.FAKE_UUID_1)
        self.assertEqual(self.FAKE_UUID_1, amphora.id)
        self.assertEqual(self.FAKE_UUID_3, amphora.compute_id)
        self.assertEqual(constants.ACTIVE, amphora.status)
        self.assertEqual(constants.ROLE_MASTER, amphora.role)

    def test_exists_true(self):
        amphora = self.create_amphora(self.FAKE_UUID_1)
        exist = self.amphora_repo.exists(self.session, id=amphora.id)
        self.assertTrue(exist)

    def test_exists_false(self):
        self.create_amphora(self.FAKE_UUID_1)
        exist = self.amphora_repo.exists(self.session, id='test')
        self.assertFalse(exist)

    def test_update(self):
        status_change = constants.PENDING_UPDATE
        amphora = self.create_amphora(self.FAKE_UUID_1)
        self.amphora_repo.update(self.session, amphora.id,
                                 status=status_change)
        new_amphora = self.amphora_repo.get(self.session, id=amphora.id)
        self.assertEqual(status_change, new_amphora.status)

    def test_delete(self):
        amphora = self.create_amphora(self.FAKE_UUID_1)
        self.amphora_repo.delete(self.session, id=amphora.id)
        self.assertIsNone(self.amphora_repo.get(self.session, id=amphora.id))

    def test_associate_amphora_load_balancer(self):
        amphora = self.create_amphora(self.FAKE_UUID_1)
        self.amphora_repo.associate(self.session, self.lb.id, amphora.id)
        new_amphora = self.amphora_repo.get(self.session,
                                            id=amphora.id)
        self.assertIsNotNone(new_amphora.load_balancer)
        self.assertIsInstance(new_amphora.load_balancer, models.LoadBalancer)

    def test_delete_amphora_with_load_balancer(self):
        amphora = self.create_amphora(self.FAKE_UUID_1)
        self.amphora_repo.associate(self.session, self.lb.id, amphora.id)
        self.amphora_repo.delete(self.session, id=amphora.id)
        self.assertIsNone(self.amphora_repo.get(self.session, id=amphora.id))
        new_lb = self.lb_repo.get(self.session, id=self.lb.id)
        self.assertEqual(0, len(new_lb.amphorae))

    def test_allocate_and_associate(self):
        new_amphora = self.amphora_repo.allocate_and_associate(self.session,
                                                               self.lb.id)
        self.assertIsNone(new_amphora)

        amphora = self.create_amphora(self.FAKE_UUID_1)
        self.amphora_repo.update(self.session, amphora.id,
                                 status=constants.AMPHORA_READY)
        new_amphora = self.amphora_repo.allocate_and_associate(self.session,
                                                               self.lb.id)
        self.assertIsNotNone(new_amphora)
        self.assertIsInstance(new_amphora, models.Amphora)

    def test_get_lb_for_amphora(self):
        amphora = self.create_amphora(self.FAKE_UUID_1)
        self.amphora_repo.associate(self.session, self.lb.id, amphora.id)
        lb = self.amphora_repo.get_lb_for_amphora(self.session, amphora.id)
        self.assertIsNotNone(lb)
        self.assertEqual(self.lb, lb)

    def get_all_deleted_expiring_amphora(self):
        exp_age = datetime.timedelta(seconds=self.FAKE_EXP_AGE)
        updated_at = datetime.datetime.utcnow() - exp_age
        amphora1 = self.create_amphora(
            self.FAKE_UUID_1, updated_at=updated_at, status=constants.DELETED)
        amphora2 = self.create_amphora(
            self.FAKE_UUID_2, status=constants.DELETED)

        expiring_list = self.amphora_repo.get_all_deleted_expiring_amphora(
            self.session, exp_age=exp_age)
        expiring_ids = [amp.id for amp in expiring_list]
        self.assertIn(amphora1.id, expiring_ids)
        self.assertNotIn(amphora2.id, expiring_ids)

    def test_get_spare_amphora_count(self):
        count = self.amphora_repo.get_spare_amphora_count(self.session)
        self.assertEqual(0, count)

        amphora1 = self.create_amphora(self.FAKE_UUID_1)
        self.amphora_repo.update(self.session, amphora1.id,
                                 status=constants.AMPHORA_READY)
        amphora2 = self.create_amphora(self.FAKE_UUID_2)
        self.amphora_repo.update(self.session, amphora2.id,
                                 status=constants.AMPHORA_READY)
        count = self.amphora_repo.get_spare_amphora_count(self.session)
        self.assertEqual(2, count)

    def test_get_none_cert_expired_amphora(self):
        # test with no expired amphora
        amp = self.amphora_repo.get_cert_expiring_amphora(self.session)
        self.assertIsNone(amp)

        amphora = self.create_amphora(self.FAKE_UUID_1)

        expired_interval = CONF.house_keeping.cert_expiry_buffer
        expiration = datetime.datetime.utcnow() + datetime.timedelta(
            seconds=2 * expired_interval)

        self.amphora_repo.update(self.session, amphora.id,
                                 cert_expiration=expiration)
        amp = self.amphora_repo.get_cert_expiring_amphora(self.session)
        self.assertIsNone(amp)

    def test_get_cert_expired_amphora(self):
        # test with expired amphora
        amphora2 = self.create_amphora(self.FAKE_UUID_2)

        expiration = datetime.datetime.utcnow() + datetime.timedelta(
            seconds=1)
        self.amphora_repo.update(self.session, amphora2.id,
                                 cert_expiration=expiration)

        cert_expired_amphora = self.amphora_repo.get_cert_expiring_amphora(
            self.session)

        self.assertEqual(cert_expired_amphora.cert_expiration, expiration)
        self.assertEqual(cert_expired_amphora.id, amphora2.id)

    def test_get_lb_for_health_update(self):
        amphora1 = self.create_amphora(self.FAKE_UUID_1)
        amphora2 = self.create_amphora(self.FAKE_UUID_3)
        self.amphora_repo.associate(self.session, self.lb.id, amphora1.id)
        self.amphora_repo.associate(self.session, self.lb.id, amphora2.id)

        lb_ref = {'enabled': True, 'id': self.lb.id,
                  'operating_status': constants.ONLINE,
                  'provisioning_status': constants.ACTIVE}

        # Test with just a load balancer
        lb = self.amphora_repo.get_lb_for_health_update(self.session,
                                                        self.FAKE_UUID_1)
        self.assertEqual(lb_ref, lb)

        pool = self.pool_repo.create(
            self.session, id=self.FAKE_UUID_4, project_id=self.FAKE_UUID_2,
            name="pool_test", description="pool_description",
            protocol=constants.PROTOCOL_HTTP, load_balancer_id=self.lb.id,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)

        pool_ref = {pool.id: {'members': {},
                    'operating_status': constants.ONLINE}}
        lb_ref['pools'] = pool_ref

        # Test with an LB and a pool
        lb = self.amphora_repo.get_lb_for_health_update(self.session,
                                                        self.FAKE_UUID_1)
        self.assertEqual(lb_ref, lb)

        listener = self.listener_repo.create(
            self.session, id=self.FAKE_UUID_5, project_id=self.FAKE_UUID_2,
            name="listener_name", description="listener_description",
            protocol=constants.PROTOCOL_HTTP, protocol_port=80,
            connection_limit=1, operating_status=constants.ONLINE,
            load_balancer_id=self.lb.id, provisioning_status=constants.ACTIVE,
            enabled=True, peer_port=1025, default_pool_id=pool.id)

        listener_ref = {listener.id: {'operating_status': constants.ONLINE}}
        lb_ref['listeners'] = listener_ref

        # Test with an LB, pool, and listener (no members)
        lb = self.amphora_repo.get_lb_for_health_update(self.session,
                                                        self.FAKE_UUID_1)
        self.assertEqual(lb_ref, lb)

        member1 = self.member_repo.create(self.session, id=self.FAKE_UUID_6,
                                          project_id=self.FAKE_UUID_2,
                                          pool_id=pool.id,
                                          ip_address="192.0.2.1",
                                          protocol_port=80, enabled=True,
                                          provisioning_status=constants.ACTIVE,
                                          operating_status=constants.ONLINE,
                                          backup=False)

        member2 = self.member_repo.create(self.session, id=self.FAKE_UUID_7,
                                          project_id=self.FAKE_UUID_2,
                                          pool_id=pool.id,
                                          ip_address="192.0.2.21",
                                          protocol_port=80, enabled=True,
                                          provisioning_status=constants.ACTIVE,
                                          operating_status=constants.OFFLINE,
                                          backup=False)

        member_ref = {member1.id: {'operating_status': constants.ONLINE},
                      member2.id: {'operating_status': constants.OFFLINE}}
        lb_ref['pools'][pool.id]['members'] = member_ref

        # Test with an LB, pool, listener, and members
        lb = self.amphora_repo.get_lb_for_health_update(self.session,
                                                        self.FAKE_UUID_1)
        self.assertEqual(lb_ref, lb)


class AmphoraHealthRepositoryTest(BaseRepositoryTest):
    def setUp(self):
        super(AmphoraHealthRepositoryTest, self).setUp()
        self.amphora = self.amphora_repo.create(self.session,
                                                id=self.FAKE_UUID_1,
                                                compute_id=self.FAKE_UUID_3,
                                                status=constants.ACTIVE,
                                                lb_network_ip=self.FAKE_IP)

    def create_amphora_health(self, amphora_id):
        newdate = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)

        amphora_health = self.amphora_health_repo.create(
            self.session, amphora_id=amphora_id,
            last_update=newdate,
            busy=False)
        return amphora_health

    def test_replace(self):
        amphora_id = uuidutils.generate_uuid()
        now = datetime.datetime.utcnow()
        self.assertIsNone(self.amphora_health_repo.get(
            self.session, amphora_id=amphora_id))
        self.amphora_health_repo.replace(self.session, amphora_id,
                                         last_update=now)
        obj = self.amphora_health_repo.get(self.session, amphora_id=amphora_id)
        self.assertIsNotNone(obj)
        self.assertEqual(amphora_id, obj.amphora_id)
        self.assertEqual(now, obj.last_update)

        now += datetime.timedelta(seconds=69)
        self.amphora_health_repo.replace(self.session, amphora_id,
                                         last_update=now)
        obj = self.amphora_health_repo.get(self.session, amphora_id=amphora_id)
        self.assertIsNotNone(obj)
        self.assertEqual(amphora_id, obj.amphora_id)
        self.assertEqual(now, obj.last_update)

    def test_get(self):
        amphora_health = self.create_amphora_health(self.amphora.id)
        new_amphora_health = self.amphora_health_repo.get(
            self.session, amphora_id=amphora_health.amphora_id)

        self.assertIsInstance(new_amphora_health, models.AmphoraHealth)
        self.assertEqual(amphora_health, new_amphora_health)

    def test_check_amphora_expired_default_exp_age(self):
        """When exp_age defaults to CONF.house_keeping.amphora_expiry_age."""
        self.create_amphora_health(self.amphora.id)
        checkres = self.amphora_health_repo.check_amphora_health_expired(
            self.session, self.amphora.id)
        # Default amphora_expiry_age value is 1 week so amphora shouldn't be
        # considered expired.
        self.assertFalse(checkres)

    def test_check_amphora_expired_with_exp_age(self):
        """When exp_age is passed as an argument."""
        exp_age = datetime.timedelta(
            seconds=self.FAKE_EXP_AGE)
        self.create_amphora_health(self.amphora.id)
        checkres = self.amphora_health_repo.check_amphora_health_expired(
            self.session, self.amphora.id, exp_age)
        self.assertTrue(checkres)

    def test_check_amphora_expired_with_no_age(self):
        """When the amphora_health entry is missing in the DB."""
        checkres = self.amphora_health_repo.check_amphora_health_expired(
            self.session, self.amphora.id)
        self.assertTrue(checkres)

    def test_get_stale_amphora(self):
        stale_amphora = self.amphora_health_repo.get_stale_amphora(
            self.session)
        self.assertIsNone(stale_amphora)

        self.create_amphora_health(self.amphora.id)
        stale_amphora = self.amphora_health_repo.get_stale_amphora(
            self.session)
        self.assertEqual(self.amphora.id, stale_amphora.amphora_id)

    def test_create(self):
        amphora_health = self.create_amphora_health(self.FAKE_UUID_1)
        self.assertEqual(self.FAKE_UUID_1, amphora_health.amphora_id)
        newcreatedtime = datetime.datetime.utcnow()
        oldcreatetime = amphora_health.last_update

        diff = newcreatedtime - oldcreatetime
        self.assertEqual(600, diff.seconds)

    def test_update(self):
        d = datetime.datetime.today()
        amphora_health = self.create_amphora_health(self.FAKE_UUID_1)
        self.amphora_health_repo.update(self.session,
                                        amphora_health.amphora_id,
                                        last_update=d)
        new_amphora_health = self.amphora_health_repo.get(
            self.session, amphora_id=amphora_health.amphora_id)
        self.assertEqual(d, new_amphora_health.last_update)

    def test_delete(self):
        amphora_health = self.create_amphora_health(self.FAKE_UUID_1)
        self.amphora_health_repo.delete(
            self.session, amphora_id=amphora_health.amphora_id)
        self.assertIsNone(self.amphora_health_repo.get(
            self.session, amphora_id=amphora_health.amphora_id))


class VRRPGroupRepositoryTest(BaseRepositoryTest):
    def setUp(self):
        super(VRRPGroupRepositoryTest, self).setUp()
        self.lb = self.lb_repo.create(
            self.session, id=self.FAKE_UUID_1, project_id=self.FAKE_UUID_2,
            name="lb_name", description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)

    def test_update(self):
        self.vrrpgroup = self.vrrp_group_repo.create(
            self.session,
            load_balancer_id=self.lb.id,
            vrrp_group_name='TESTVRRPGROUP',
            vrrp_auth_type=constants.VRRP_AUTH_DEFAULT,
            vrrp_auth_pass='TESTPASS',
            advert_int=1)

        # Validate baseline
        old_vrrp_group = self.vrrp_group_repo.get(self.session,
                                                  load_balancer_id=self.lb.id)

        self.assertEqual('TESTVRRPGROUP', old_vrrp_group.vrrp_group_name)
        self.assertEqual(constants.VRRP_AUTH_DEFAULT,
                         old_vrrp_group.vrrp_auth_type)
        self.assertEqual('TESTPASS', old_vrrp_group.vrrp_auth_pass)
        self.assertEqual(1, old_vrrp_group.advert_int)

        # Test update
        self.vrrp_group_repo.update(self.session,
                                    load_balancer_id=self.lb.id,
                                    vrrp_group_name='TESTVRRPGROUP2',
                                    vrrp_auth_type='AH',
                                    vrrp_auth_pass='TESTPASS2',
                                    advert_int=2)

        new_vrrp_group = self.vrrp_group_repo.get(self.session,
                                                  load_balancer_id=self.lb.id)

        self.assertEqual('TESTVRRPGROUP2', new_vrrp_group.vrrp_group_name)
        self.assertEqual('AH', new_vrrp_group.vrrp_auth_type)
        self.assertEqual('TESTPASS2', new_vrrp_group.vrrp_auth_pass)
        self.assertEqual(2, new_vrrp_group.advert_int)


class L7PolicyRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super(L7PolicyRepositoryTest, self).setUp()
        self.pool = self.create_pool(self.FAKE_UUID_1)
        self.listener = self.create_listener(self.FAKE_UUID_1, 80)

    def create_listener(self, listener_id, port):
        listener = self.listener_repo.create(
            self.session, id=listener_id, project_id=self.FAKE_UUID_2,
            name="listener_name", description="listener_description",
            protocol=constants.PROTOCOL_HTTP, protocol_port=port,
            connection_limit=1, operating_status=constants.ONLINE,
            provisioning_status=constants.ACTIVE, enabled=True, peer_port=1025)
        return listener

    def create_pool(self, pool_id):
        pool = self.pool_repo.create(
            self.session, id=pool_id, project_id=self.FAKE_UUID_2,
            name="pool_test", description="pool_description",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        return pool

    def create_l7policy(self, l7policy_id, listener_id, position,
                        action=constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
                        redirect_pool_id=None, redirect_url=None):
        l7policy = self.l7policy_repo.create(
            self.session, id=l7policy_id, name='l7policy_test',
            description='l7policy_description', listener_id=listener_id,
            position=position, action=action,
            redirect_pool_id=redirect_pool_id, redirect_url=redirect_url,
            operating_status=constants.ONLINE,
            provisioning_status=constants.ACTIVE, enabled=True)
        return l7policy

    def create_l7rule(self, l7rule_id, l7policy_id,
                      type=constants.L7RULE_TYPE_PATH,
                      compare_type=constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                      key=None, value="/api", enabled=True):
        l7rule = self.l7rule_repo.create(
            self.session, id=l7rule_id, l7policy_id=l7policy_id,
            type=type, compare_type=compare_type, key=key, value=value,
            operating_status=constants.ONLINE, enabled=enabled,
            provisioning_status=constants.ACTIVE)
        return l7rule

    def test_get(self):
        listener = self.create_listener(uuidutils.generate_uuid(), 80)
        pool = self.create_pool(uuidutils.generate_uuid())
        l7policy = self.create_l7policy(uuidutils.generate_uuid(),
                                        listener.id, 999,
                                        redirect_pool_id=pool.id)
        new_l7policy = self.l7policy_repo.get(self.session, id=l7policy.id)
        self.assertIsInstance(new_l7policy, models.L7Policy)
        self.assertEqual(l7policy, new_l7policy)
        self.assertEqual(1, new_l7policy.position)

    def test_get_all(self):
        listener = self.create_listener(uuidutils.generate_uuid(), 80)
        pool = self.create_pool(uuidutils.generate_uuid())
        l7policy_a = self.create_l7policy(uuidutils.generate_uuid(),
                                          listener.id,
                                          1, redirect_pool_id=pool.id)
        l7policy_c = self.create_l7policy(uuidutils.generate_uuid(),
                                          listener.id,
                                          2, redirect_pool_id=pool.id)
        l7policy_b = self.create_l7policy(uuidutils.generate_uuid(),
                                          listener.id,
                                          2, redirect_pool_id=pool.id)
        new_l7policy_a = self.l7policy_repo.get(self.session,
                                                id=l7policy_a.id)
        new_l7policy_b = self.l7policy_repo.get(self.session,
                                                id=l7policy_b.id)
        new_l7policy_c = self.l7policy_repo.get(self.session,
                                                id=l7policy_c.id)

        self.assertEqual(1, new_l7policy_a.position)
        self.assertEqual(2, new_l7policy_b.position)
        self.assertEqual(3, new_l7policy_c.position)
        l7policy_list, _ = self.l7policy_repo.get_all(
            self.session, listener_id=listener.id)
        self.assertIsInstance(l7policy_list, list)
        self.assertEqual(3, len(l7policy_list))
        self.assertEqual(l7policy_a.id, l7policy_list[0].id)
        self.assertEqual(l7policy_b.id, l7policy_list[1].id)
        self.assertEqual(l7policy_c.id, l7policy_list[2].id)

    def test_create(self):
        listener = self.create_listener(uuidutils.generate_uuid(), 80)
        pool = self.create_pool(uuidutils.generate_uuid())
        l7policy = self.create_l7policy(self.FAKE_UUID_1, listener.id, 1,
                                        redirect_pool_id=pool.id)
        new_l7policy = self.l7policy_repo.get(self.session, id=l7policy.id)
        self.assertEqual(self.FAKE_UUID_1, new_l7policy.id)
        self.assertEqual(listener.id, new_l7policy.listener_id)
        self.assertEqual(pool.id, new_l7policy.redirect_pool_id)
        self.assertEqual(constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
                         new_l7policy.action)
        self.assertEqual(1, new_l7policy.position)
        self.assertIsNone(new_l7policy.redirect_url)

    def test_create_no_id(self):
        listener = self.create_listener(uuidutils.generate_uuid(), 80)
        l7policy = self.l7policy_repo.create(
            self.session, listener_id=listener.id,
            action=constants.L7POLICY_ACTION_REJECT,
            operating_status=constants.ONLINE,
            provisioning_status=constants.ACTIVE,
            enabled=True)
        new_l7policy = self.l7policy_repo.get(self.session, id=l7policy.id)
        self.assertEqual(listener.id, new_l7policy.listener_id)
        self.assertIsNone(new_l7policy.redirect_pool_id)
        self.assertIsNone(new_l7policy.redirect_url)
        self.assertEqual(constants.L7POLICY_ACTION_REJECT,
                         new_l7policy.action)
        self.assertEqual(1, new_l7policy.position)

    def test_update(self):
        new_url = 'http://www.example.com/'
        listener = self.create_listener(uuidutils.generate_uuid(), 80)
        pool = self.create_pool(uuidutils.generate_uuid())
        l7policy = self.create_l7policy(uuidutils.generate_uuid(),
                                        listener.id, 1,
                                        redirect_pool_id=pool.id)
        self.l7policy_repo.update(
            self.session, id=l7policy.id,
            action=constants.L7POLICY_ACTION_REDIRECT_TO_URL,
            redirect_url=new_url, position=l7policy.position)
        new_l7policy = self.l7policy_repo.get(self.session, id=l7policy.id)
        new_pool = self.pool_repo.get(self.session, id=pool.id)
        self.assertEqual(new_url, new_l7policy.redirect_url)
        self.assertEqual(constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                         new_l7policy.action)
        self.assertIsNone(new_l7policy.redirect_pool_id)
        self.assertNotIn(new_l7policy.id, new_pool.l7policies)

    def test_update_bad_id(self):
        self.assertRaises(exceptions.NotFound, self.l7policy_repo.update,
                          self.session, id=uuidutils.generate_uuid())

    def test_delete(self):
        listener = self.create_listener(uuidutils.generate_uuid(), 80)
        pool = self.create_pool(uuidutils.generate_uuid())
        l7policy = self.create_l7policy(uuidutils.generate_uuid(),
                                        listener.id, 1,
                                        redirect_pool_id=pool.id)
        self.l7policy_repo.delete(self.session, id=l7policy.id)
        self.assertIsNone(self.l7policy_repo.get(self.session, id=l7policy.id))
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIsNotNone(new_listener)
        self.assertEqual(0, len(new_listener.l7policies))

    def test_delete_bad_id(self):
        self.assertRaises(exceptions.NotFound, self.l7policy_repo.delete,
                          self.session, id=uuidutils.generate_uuid())

    def test_reorder_policies(self):
        listener = self.create_listener(uuidutils.generate_uuid(), 80)
        pool = self.create_pool(uuidutils.generate_uuid())
        l7policy_a = self.create_l7policy(uuidutils.generate_uuid(),
                                          listener.id,
                                          1, redirect_pool_id=pool.id)
        l7policy_b = self.create_l7policy(uuidutils.generate_uuid(),
                                          listener.id,
                                          2, redirect_pool_id=pool.id)
        l7policy_c = self.create_l7policy(uuidutils.generate_uuid(),
                                          listener.id,
                                          3, redirect_pool_id=pool.id)
        new_l7policy_a = self.l7policy_repo.get(self.session,
                                                id=l7policy_a.id)
        new_l7policy_b = self.l7policy_repo.get(self.session,
                                                id=l7policy_b.id)
        new_l7policy_c = self.l7policy_repo.get(self.session,
                                                id=l7policy_c.id)
        self.assertEqual(1, new_l7policy_a.position)
        self.assertEqual(2, new_l7policy_b.position)
        self.assertEqual(3, new_l7policy_c.position)
        self.l7policy_repo.update(self.session, id=l7policy_a.id, position=2)
        new_l7policy_a = self.l7policy_repo.get(self.session,
                                                id=l7policy_a.id)
        new_l7policy_b = self.l7policy_repo.get(self.session,
                                                id=l7policy_b.id)
        new_l7policy_c = self.l7policy_repo.get(self.session,
                                                id=l7policy_c.id)
        self.assertEqual(2, new_l7policy_a.position)
        self.assertEqual(1, new_l7policy_b.position)
        self.assertEqual(3, new_l7policy_c.position)
        self.l7policy_repo.update(self.session, id=l7policy_c.id, position=1)
        new_l7policy_a = self.l7policy_repo.get(self.session,
                                                id=l7policy_a.id)
        new_l7policy_b = self.l7policy_repo.get(self.session,
                                                id=l7policy_b.id)
        new_l7policy_c = self.l7policy_repo.get(self.session,
                                                id=l7policy_c.id)
        self.assertEqual(3, new_l7policy_a.position)
        self.assertEqual(2, new_l7policy_b.position)
        self.assertEqual(1, new_l7policy_c.position)
        self.l7policy_repo.update(self.session, id=l7policy_c.id, position=1)
        new_l7policy_a = self.l7policy_repo.get(self.session,
                                                id=l7policy_a.id)
        new_l7policy_b = self.l7policy_repo.get(self.session,
                                                id=l7policy_b.id)
        new_l7policy_c = self.l7policy_repo.get(self.session,
                                                id=l7policy_c.id)
        self.assertEqual(3, new_l7policy_a.position)
        self.assertEqual(2, new_l7policy_b.position)
        self.assertEqual(1, new_l7policy_c.position)

    def test_delete_forcing_reorder(self):
        listener = self.create_listener(uuidutils.generate_uuid(), 80)
        pool = self.create_pool(uuidutils.generate_uuid())
        l7policy_a = self.create_l7policy(uuidutils.generate_uuid(),
                                          listener.id,
                                          1, redirect_pool_id=pool.id)
        l7policy_b = self.create_l7policy(uuidutils.generate_uuid(),
                                          listener.id,
                                          2, redirect_pool_id=pool.id)
        l7policy_c = self.create_l7policy(uuidutils.generate_uuid(),
                                          listener.id,
                                          999, redirect_pool_id=pool.id)
        new_l7policy_a = self.l7policy_repo.get(self.session,
                                                id=l7policy_a.id)
        new_l7policy_b = self.l7policy_repo.get(self.session,
                                                id=l7policy_b.id)
        new_l7policy_c = self.l7policy_repo.get(self.session,
                                                id=l7policy_c.id)
        self.assertEqual(1, new_l7policy_a.position)
        self.assertEqual(2, new_l7policy_b.position)
        self.assertEqual(3, new_l7policy_c.position)
        self.l7policy_repo.delete(self.session, id=l7policy_b.id)
        l7policy_list, _ = self.l7policy_repo.get_all(
            self.session, listener_id=listener.id)
        self.assertIsInstance(l7policy_list, list)
        self.assertEqual(2, len(l7policy_list))
        new_l7policy_a = self.l7policy_repo.get(self.session,
                                                id=l7policy_a.id)
        new_l7policy_c = self.l7policy_repo.get(self.session,
                                                id=l7policy_c.id)
        self.assertEqual(1, new_l7policy_a.position)
        self.assertEqual(2, new_l7policy_c.position)

    def test_delete_with_rule(self):
        listener = self.create_listener(uuidutils.generate_uuid(), 80)
        pool = self.create_pool(uuidutils.generate_uuid())
        l7policy = self.create_l7policy(uuidutils.generate_uuid(),
                                        listener.id, 1,
                                        redirect_pool_id=pool.id,)
        l7rule = self.create_l7rule(uuidutils.generate_uuid(), l7policy.id)
        new_l7policy = self.l7policy_repo.get(self.session, id=l7policy.id)
        new_l7rule = self.l7rule_repo.get(self.session, id=l7rule.id)
        self.assertEqual(l7policy.id, new_l7policy.id)
        self.assertEqual(l7rule.id, new_l7rule.id)
        self.l7policy_repo.delete(self.session, id=l7policy.id)
        self.assertIsNone(self.l7policy_repo.get(self.session, id=l7policy.id))
        self.assertIsNone(self.l7rule_repo.get(self.session, id=l7rule.id))

    def test_update_action_rdr_url_to_redirect_pool(self):
        listener = self.create_listener(uuidutils.generate_uuid(), 80)
        pool = self.create_pool(uuidutils.generate_uuid())
        l7policy = self.create_l7policy(
            uuidutils.generate_uuid(), listener.id, 1,
            action=constants.L7POLICY_ACTION_REDIRECT_TO_URL,
            redirect_url="http://www.example.com/")
        new_l7policy = self.l7policy_repo.get(self.session, id=l7policy.id)
        self.assertIsNone(new_l7policy.redirect_pool_id)
        self.l7policy_repo.update(
            self.session, id=l7policy.id,
            redirect_pool_id=pool.id)
        new_l7policy = self.l7policy_repo.get(self.session, id=l7policy.id)
        self.assertEqual(pool.id, new_l7policy.redirect_pool.id)
        self.assertEqual(constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
                         new_l7policy.action)
        self.assertIsNone(new_l7policy.redirect_url)

    def test_update_action_rdr_url_to_reject(self):
        listener = self.create_listener(uuidutils.generate_uuid(), 80)
        l7policy = self.create_l7policy(
            uuidutils.generate_uuid(), listener.id, 1,
            action=constants.L7POLICY_ACTION_REDIRECT_TO_URL,
            redirect_url="http://www.example.com/")
        new_l7policy = self.l7policy_repo.get(self.session, id=l7policy.id)
        self.assertIsNone(new_l7policy.redirect_pool_id)
        self.assertEqual(constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                         new_l7policy.action)
        self.l7policy_repo.update(
            self.session, id=l7policy.id,
            action=constants.L7POLICY_ACTION_REJECT)
        new_l7policy = self.l7policy_repo.get(self.session, id=l7policy.id)
        self.assertEqual(constants.L7POLICY_ACTION_REJECT,
                         new_l7policy.action)
        self.assertIsNone(new_l7policy.redirect_url)
        self.assertIsNone(new_l7policy.redirect_pool_id)

    def test_update_action_rdr_pool_to_reject(self):
        listener = self.create_listener(uuidutils.generate_uuid(), 80)
        pool = self.create_pool(uuidutils.generate_uuid())
        l7policy = self.create_l7policy(
            uuidutils.generate_uuid(), listener.id, 1,
            action=constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
            redirect_pool_id=pool.id)
        new_l7policy = self.l7policy_repo.get(self.session, id=l7policy.id)
        self.assertIsNone(new_l7policy.redirect_url)
        self.l7policy_repo.update(
            self.session, id=l7policy.id,
            action=constants.L7POLICY_ACTION_REJECT)
        new_l7policy = self.l7policy_repo.get(self.session, id=l7policy.id)
        self.assertEqual(constants.L7POLICY_ACTION_REJECT,
                         new_l7policy.action)
        self.assertIsNone(new_l7policy.redirect_url)
        self.assertIsNone(new_l7policy.redirect_pool_id)

    def test_update_reject_to_rdr_pool(self):
        listener = self.create_listener(uuidutils.generate_uuid(), 80)
        pool = self.create_pool(uuidutils.generate_uuid())
        l7policy = self.create_l7policy(
            uuidutils.generate_uuid(), listener.id, 1,
            action=constants.L7POLICY_ACTION_REJECT)
        new_l7policy = self.l7policy_repo.get(self.session, id=l7policy.id)
        self.assertIsNone(new_l7policy.redirect_url)
        self.assertIsNone(new_l7policy.redirect_pool_id)
        self.l7policy_repo.update(
            self.session, id=l7policy.id,
            redirect_pool_id=pool.id)
        new_l7policy = self.l7policy_repo.get(self.session, id=l7policy.id)
        self.assertEqual(pool.id, new_l7policy.redirect_pool_id)
        self.assertEqual(constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
                         new_l7policy.action)
        self.assertIsNone(new_l7policy.redirect_url)

    def test_update_reject_to_rdr_url(self):
        listener = self.create_listener(uuidutils.generate_uuid(), 80)
        l7policy = self.create_l7policy(
            uuidutils.generate_uuid(), listener.id, 1,
            action=constants.L7POLICY_ACTION_REJECT)
        new_l7policy = self.l7policy_repo.get(self.session, id=l7policy.id)
        self.assertIsNone(new_l7policy.redirect_url)
        self.assertIsNone(new_l7policy.redirect_pool_id)
        self.l7policy_repo.update(
            self.session, id=l7policy.id,
            redirect_url='http://www.example.com/')
        new_l7policy = self.l7policy_repo.get(self.session, id=l7policy.id)
        self.assertEqual('http://www.example.com/', new_l7policy.redirect_url)
        self.assertEqual(constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                         new_l7policy.action)
        self.assertIsNone(new_l7policy.redirect_pool_id)

    def test_update_position_only(self):
        listener = self.create_listener(uuidutils.generate_uuid(), 80)
        l7policy_a = self.create_l7policy(
            uuidutils.generate_uuid(), listener.id, 1,
            action=constants.L7POLICY_ACTION_REJECT)
        l7policy_b = self.create_l7policy(
            uuidutils.generate_uuid(), listener.id, 2,
            action=constants.L7POLICY_ACTION_REJECT)
        new_l7policy_a = self.l7policy_repo.get(self.session, id=l7policy_a.id)
        new_l7policy_b = self.l7policy_repo.get(self.session, id=l7policy_b.id)
        self.assertEqual(1, new_l7policy_a.position)
        self.assertEqual(2, new_l7policy_b.position)
        self.l7policy_repo.update(
            self.session, id=l7policy_a.id,
            position=999)
        new_l7policy_a = self.l7policy_repo.get(self.session, id=l7policy_a.id)
        new_l7policy_b = self.l7policy_repo.get(self.session, id=l7policy_b.id)
        self.assertEqual(2, new_l7policy_a.position)
        self.assertEqual(1, new_l7policy_b.position)
        self.l7policy_repo.update(
            self.session, id=l7policy_a.id,
            position=1)
        new_l7policy_a = self.l7policy_repo.get(self.session, id=l7policy_a.id)
        new_l7policy_b = self.l7policy_repo.get(self.session, id=l7policy_b.id)
        self.assertEqual(1, new_l7policy_a.position)
        self.assertEqual(2, new_l7policy_b.position)

    def test_create_with_invalid_redirect_pool_id(self):
        bad_lb = self.lb_repo.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=uuidutils.generate_uuid(),
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        bad_pool = self.pool_repo.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=bad_lb.project_id,
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        self.assertRaises(exceptions.NotFound, self.create_l7policy,
                          uuidutils.generate_uuid(), self.listener.id, 1,
                          action=constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
                          redirect_pool_id=bad_pool.id)

    def test_create_with_invalid_redirect_url(self):
        self.assertRaises(exceptions.InvalidURL, self.create_l7policy,
                          uuidutils.generate_uuid(), self.listener.id, 1,
                          action=constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                          redirect_url="This is not a URL.")


class L7RuleRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super(L7RuleRepositoryTest, self).setUp()
        self.listener = self.listener_repo.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=self.FAKE_UUID_2,
            protocol=constants.PROTOCOL_HTTP, protocol_port=80,
            connection_limit=1, operating_status=constants.ONLINE,
            provisioning_status=constants.ACTIVE, enabled=True, peer_port=1025)
        self.l7policy = self.l7policy_repo.create(
            self.session, id=self.FAKE_UUID_1, name='l7policy_test',
            description='l7policy_description', listener_id=self.listener.id,
            position=1, action=constants.L7POLICY_ACTION_REJECT,
            operating_status=constants.ONLINE,
            provisioning_status=constants.ACTIVE, enabled=True)

    def create_l7rule(self, l7rule_id, l7policy_id,
                      type=constants.L7RULE_TYPE_PATH,
                      compare_type=constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                      key=None, value="/api", invert=False, enabled=True):
        l7rule = self.l7rule_repo.create(
            self.session, id=l7rule_id, l7policy_id=l7policy_id,
            type=type, compare_type=compare_type, key=key, value=value,
            invert=invert, provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=enabled)
        return l7rule

    def test_get(self):
        l7rule = self.create_l7rule(uuidutils.generate_uuid(),
                                    self.l7policy.id)
        new_l7rule = self.l7rule_repo.get(self.session, id=l7rule.id)
        self.assertIsInstance(new_l7rule, models.L7Rule)
        self.assertEqual(l7rule, new_l7rule)

    def test_get_all(self):
        l7policy = self.l7policy_repo.create(
            self.session, id=uuidutils.generate_uuid(), name='l7policy_test',
            description='l7policy_description', listener_id=self.listener.id,
            position=1, action=constants.L7POLICY_ACTION_REJECT,
            operating_status=constants.ONLINE,
            provisioning_status=constants.ACTIVE, enabled=True)
        l7rule_a = self.create_l7rule(uuidutils.generate_uuid(), l7policy.id)
        l7rule_b = self.create_l7rule(uuidutils.generate_uuid(), l7policy.id)
        new_l7rule_a = self.l7rule_repo.get(self.session,
                                            id=l7rule_a.id)
        new_l7rule_b = self.l7rule_repo.get(self.session,
                                            id=l7rule_b.id)
        l7rule_list, _ = self.l7rule_repo.get_all(
            self.session, l7policy_id=l7policy.id)
        self.assertIsInstance(l7rule_list, list)
        self.assertEqual(2, len(l7rule_list))
        self.assertIn(new_l7rule_a.id, [r.id for r in l7rule_list])
        self.assertIn(new_l7rule_b.id, [r.id for r in l7rule_list])

    def test_create(self):
        l7rule = self.create_l7rule(self.FAKE_UUID_1,
                                    self.l7policy.id)
        new_l7rule = self.l7rule_repo.get(self.session, id=l7rule.id)
        self.assertEqual(self.FAKE_UUID_1, new_l7rule.id)
        self.assertEqual(self.l7policy.id, new_l7rule.l7policy_id)
        self.assertEqual(constants.L7RULE_TYPE_PATH, new_l7rule.type)
        self.assertEqual(constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                         new_l7rule.compare_type)
        self.assertIsNone(new_l7rule.key)
        self.assertEqual('/api', new_l7rule.value)
        self.assertFalse(new_l7rule.invert)

    def test_create_without_id(self):
        l7rule = self.l7rule_repo.create(
            self.session, id=None, l7policy_id=self.l7policy.id,
            type=constants.L7RULE_TYPE_PATH,
            compare_type=constants.L7RULE_COMPARE_TYPE_CONTAINS,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            value='something',
            enabled=True)
        new_l7rule = self.l7rule_repo.get(self.session, id=l7rule.id)
        self.assertIsNotNone(l7rule.id)
        self.assertEqual(self.l7policy.id, new_l7rule.l7policy_id)
        self.assertEqual(constants.L7RULE_TYPE_PATH, new_l7rule.type)
        self.assertEqual(constants.L7RULE_COMPARE_TYPE_CONTAINS,
                         new_l7rule.compare_type)
        self.assertIsNone(new_l7rule.key)
        self.assertEqual('something', new_l7rule.value)
        self.assertFalse(new_l7rule.invert)

    def test_update(self):
        l7rule = self.create_l7rule(uuidutils.generate_uuid(),
                                    self.l7policy.id,
                                    type=constants.L7RULE_TYPE_HEADER,
                                    key="My-Header")
        new_l7rule = self.l7rule_repo.get(self.session, id=l7rule.id)
        self.assertEqual('/api', new_l7rule.value)
        self.assertFalse(new_l7rule.invert)
        update_dict = {'type': constants.L7RULE_TYPE_PATH,
                       'value': '/images',
                       'invert': True}
        self.l7rule_repo.update(self.session, id=l7rule.id, **update_dict)
        new_l7rule = self.l7rule_repo.get(self.session, id=l7rule.id)
        self.assertEqual(constants.L7RULE_TYPE_PATH, new_l7rule.type)
        self.assertEqual('/images', new_l7rule.value)
        self.assertIsNone(new_l7rule.key)
        self.assertTrue(new_l7rule.invert)

    def test_update_bad_id(self):
        self.assertRaises(exceptions.NotFound,
                          self.l7rule_repo.update, self.session,
                          id='bad id', value='/some/path')

    def test_bad_update(self):
        l7rule = self.create_l7rule(uuidutils.generate_uuid(),
                                    self.l7policy.id)
        new_l7rule = self.l7rule_repo.get(self.session, id=l7rule.id)
        self.assertEqual('/api', new_l7rule.value)
        self.assertRaises(exceptions.InvalidString,
                          self.l7rule_repo.update, self.session,
                          id=l7rule.id, value='bad path')

    def test_delete(self):
        l7rule = self.create_l7rule(uuidutils.generate_uuid(),
                                    self.l7policy.id)
        self.l7rule_repo.delete(self.session, id=l7rule.id)
        self.assertIsNone(self.l7rule_repo.get(self.session, id=l7rule.id))

    def test_create_bad_rule_type(self):
        self.assertRaises(exceptions.InvalidL7Rule, self.create_l7rule,
                          self.FAKE_UUID_1, self.l7policy.id,
                          type="not valid")

    def test_create_header_rule(self):
        l7rule = self.create_l7rule(
            uuidutils.generate_uuid(),
            self.l7policy.id,
            type=constants.L7RULE_TYPE_HEADER,
            compare_type=constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
            key="Some-header",
            value='"some value"')
        new_l7rule = self.l7rule_repo.get(self.session, id=l7rule.id)
        self.assertEqual(constants.L7RULE_TYPE_HEADER, new_l7rule.type)
        self.assertEqual(constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
                         new_l7rule.compare_type)
        self.assertEqual('Some-header', new_l7rule.key)
        self.assertEqual('"some value"', new_l7rule.value)

    def test_create_header_rule_no_key(self):
        self.assertRaises(
            exceptions.InvalidL7Rule, self.create_l7rule,
            self.FAKE_UUID_1, self.l7policy.id,
            type=constants.L7RULE_TYPE_HEADER,
            compare_type=constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
            value='"some value"')

    def test_create_header_rule_invalid_key(self):
        self.assertRaises(
            exceptions.InvalidString, self.create_l7rule,
            self.FAKE_UUID_1, self.l7policy.id,
            type=constants.L7RULE_TYPE_HEADER,
            compare_type=constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
            key='bad key;',
            value='"some value"')

    def test_create_header_rule_invalid_value_string(self):
        self.assertRaises(
            exceptions.InvalidString, self.create_l7rule,
            self.FAKE_UUID_1, self.l7policy.id,
            type=constants.L7RULE_TYPE_HEADER,
            compare_type=constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
            key='Some-header',
            value='\x18')

    def test_create_header_rule_invalid_value_regex(self):
        self.assertRaises(
            exceptions.InvalidRegex, self.create_l7rule,
            self.FAKE_UUID_1, self.l7policy.id,
            type=constants.L7RULE_TYPE_HEADER,
            compare_type=constants.L7RULE_COMPARE_TYPE_REGEX,
            key='Some-header',
            value='bad regex\\')

    def test_create_header_rule_bad_compare_type(self):
        self.assertRaises(
            exceptions.InvalidL7Rule, self.create_l7rule,
            self.FAKE_UUID_1, self.l7policy.id,
            type=constants.L7RULE_TYPE_HEADER,
            compare_type="bad compare",
            key="Some-header",
            value='"some value"')

    def test_create_cookie_rule(self):
        l7rule = self.create_l7rule(
            uuidutils.generate_uuid(),
            self.l7policy.id,
            type=constants.L7RULE_TYPE_COOKIE,
            compare_type=constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
            key="some_cookie",
            value='some-value')
        new_l7rule = self.l7rule_repo.get(self.session, id=l7rule.id)
        self.assertEqual(constants.L7RULE_TYPE_COOKIE, new_l7rule.type)
        self.assertEqual(constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
                         new_l7rule.compare_type)
        self.assertEqual('some_cookie', new_l7rule.key)
        self.assertEqual('some-value', new_l7rule.value)

    def test_create_cookie_rule_no_key(self):
        self.assertRaises(
            exceptions.InvalidL7Rule, self.create_l7rule,
            self.FAKE_UUID_1, self.l7policy.id,
            type=constants.L7RULE_TYPE_COOKIE,
            compare_type=constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
            value='some-value')

    def test_create_cookie_rule_invalid_key(self):
        self.assertRaises(
            exceptions.InvalidString, self.create_l7rule,
            self.FAKE_UUID_1, self.l7policy.id,
            type=constants.L7RULE_TYPE_COOKIE,
            compare_type=constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
            key='bad key;',
            value='some-value')

    def test_create_cookie_rule_invalid_value_string(self):
        self.assertRaises(
            exceptions.InvalidString, self.create_l7rule,
            self.FAKE_UUID_1, self.l7policy.id,
            type=constants.L7RULE_TYPE_COOKIE,
            compare_type=constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
            key='some_cookie',
            value='bad value;')

    def test_create_cookie_rule_invalid_value_regex(self):
        self.assertRaises(
            exceptions.InvalidRegex, self.create_l7rule,
            self.FAKE_UUID_1, self.l7policy.id,
            type=constants.L7RULE_TYPE_COOKIE,
            compare_type=constants.L7RULE_COMPARE_TYPE_REGEX,
            key='some_cookie',
            value='bad regex\\')

    def test_create_cookie_rule_bad_compare_type(self):
        self.assertRaises(
            exceptions.InvalidL7Rule, self.create_l7rule,
            self.FAKE_UUID_1, self.l7policy.id,
            type=constants.L7RULE_TYPE_COOKIE,
            compare_type="bad compare",
            key="some_cookie",
            value='some-value')

    def test_create_path_rule(self):
        l7rule = self.create_l7rule(
            uuidutils.generate_uuid(),
            self.l7policy.id,
            type=constants.L7RULE_TYPE_PATH,
            compare_type=constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            value='/some/path')
        new_l7rule = self.l7rule_repo.get(self.session, id=l7rule.id)
        self.assertEqual(constants.L7RULE_TYPE_PATH, new_l7rule.type)
        self.assertEqual(constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                         new_l7rule.compare_type)
        self.assertEqual('/some/path', new_l7rule.value)

    def test_create_path_rule_invalid_value_string(self):
        self.assertRaises(
            exceptions.InvalidString, self.create_l7rule,
            self.FAKE_UUID_1, self.l7policy.id,
            type=constants.L7RULE_TYPE_PATH,
            compare_type=constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            value='bad path')

    def test_create_path_rule_invalid_value_regex(self):
        self.assertRaises(
            exceptions.InvalidRegex, self.create_l7rule,
            self.FAKE_UUID_1, self.l7policy.id,
            type=constants.L7RULE_TYPE_PATH,
            compare_type=constants.L7RULE_COMPARE_TYPE_REGEX,
            value='bad regex\\')

    def test_create_path_rule_bad_compare_type(self):
        self.assertRaises(
            exceptions.InvalidL7Rule, self.create_l7rule,
            self.FAKE_UUID_1, self.l7policy.id,
            type=constants.L7RULE_TYPE_PATH,
            compare_type="bad compare",
            value='/some/path')

    def test_create_host_name_rule(self):
        l7rule = self.create_l7rule(
            uuidutils.generate_uuid(),
            self.l7policy.id,
            type=constants.L7RULE_TYPE_HOST_NAME,
            compare_type=constants.L7RULE_COMPARE_TYPE_ENDS_WITH,
            value='.example.com')
        new_l7rule = self.l7rule_repo.get(self.session, id=l7rule.id)
        self.assertEqual(constants.L7RULE_TYPE_HOST_NAME, new_l7rule.type)
        self.assertEqual(constants.L7RULE_COMPARE_TYPE_ENDS_WITH,
                         new_l7rule.compare_type)
        self.assertEqual('.example.com', new_l7rule.value)

    def test_create_host_name_rule_invalid_value_string(self):
        self.assertRaises(
            exceptions.InvalidString, self.create_l7rule,
            self.FAKE_UUID_1, self.l7policy.id,
            type=constants.L7RULE_TYPE_HOST_NAME,
            compare_type=constants.L7RULE_COMPARE_TYPE_ENDS_WITH,
            value='bad hostname')

    def test_create_host_name_rule_invalid_value_regex(self):
        self.assertRaises(
            exceptions.InvalidRegex, self.create_l7rule,
            self.FAKE_UUID_1, self.l7policy.id,
            type=constants.L7RULE_TYPE_HOST_NAME,
            compare_type=constants.L7RULE_COMPARE_TYPE_REGEX,
            value='bad regex\\')

    def test_create_host_name_rule_bad_compare_type(self):
        self.assertRaises(
            exceptions.InvalidL7Rule, self.create_l7rule,
            self.FAKE_UUID_1, self.l7policy.id,
            type=constants.L7RULE_TYPE_HOST_NAME,
            compare_type="bad compare",
            value='.example.com')

    def test_create_file_type_rule(self):
        l7rule = self.create_l7rule(
            uuidutils.generate_uuid(),
            self.l7policy.id,
            type=constants.L7RULE_TYPE_FILE_TYPE,
            compare_type=constants.L7RULE_COMPARE_TYPE_REGEX,
            value='png|jpg')
        new_l7rule = self.l7rule_repo.get(self.session, id=l7rule.id)
        self.assertEqual(constants.L7RULE_TYPE_FILE_TYPE, new_l7rule.type)
        self.assertEqual(constants.L7RULE_COMPARE_TYPE_REGEX,
                         new_l7rule.compare_type)
        self.assertEqual('png|jpg', new_l7rule.value)

    def test_create_file_type_rule_invalid_value_string(self):
        self.assertRaises(
            exceptions.InvalidString, self.create_l7rule,
            self.FAKE_UUID_1, self.l7policy.id,
            type=constants.L7RULE_TYPE_FILE_TYPE,
            compare_type=constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
            value='bad file type')

    def test_create_file_type_rule_invalid_value_regex(self):
        self.assertRaises(
            exceptions.InvalidRegex, self.create_l7rule,
            self.FAKE_UUID_1, self.l7policy.id,
            type=constants.L7RULE_TYPE_FILE_TYPE,
            compare_type=constants.L7RULE_COMPARE_TYPE_REGEX,
            value='bad regex\\')

    def test_create_file_type_rule_bad_compare_type(self):
        self.assertRaises(
            exceptions.InvalidL7Rule, self.create_l7rule,
            self.FAKE_UUID_1, self.l7policy.id,
            type=constants.L7RULE_TYPE_FILE_TYPE,
            compare_type=constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            value='png|jpg')


class TestQuotasRepository(BaseRepositoryTest):

    def setUp(self):
        super(TestQuotasRepository, self).setUp()

    def update_quotas(self, project_id, load_balancer=20, listener=20, pool=20,
                      health_monitor=20, member=20):
        quota = {'load_balancer': load_balancer,
                 'listener': listener,
                 'pool': pool,
                 'health_monitor': health_monitor,
                 'member': member}
        quotas = self.quota_repo.update(self.session, project_id, quota=quota)
        return quotas

    def _compare(self, expected, observed):
        self.assertEqual(expected.project_id, observed.project_id)
        self.assertEqual(expected.load_balancer,
                         observed.load_balancer)
        self.assertEqual(expected.listener,
                         observed.listener)
        self.assertEqual(expected.pool,
                         observed.pool)
        self.assertEqual(expected.health_monitor,
                         observed.health_monitor)
        self.assertEqual(expected.member,
                         observed.member)

    def test_get(self):
        expected = self.update_quotas(self.FAKE_UUID_1)
        observed = self.quota_repo.get(self.session,
                                       project_id=self.FAKE_UUID_1)
        self.assertIsInstance(observed, models.Quotas)
        self._compare(expected, observed)

    def test_update(self):
        first_expected = self.update_quotas(self.FAKE_UUID_1)
        first_observed = self.quota_repo.get(self.session,
                                             project_id=self.FAKE_UUID_1)
        second_expected = self.update_quotas(self.FAKE_UUID_1, load_balancer=1)
        second_observed = self.quota_repo.get(self.session,
                                              project_id=self.FAKE_UUID_1)
        self.assertIsInstance(first_expected, models.Quotas)
        self._compare(first_expected, first_observed)
        self.assertIsInstance(second_expected, models.Quotas)
        self._compare(second_expected, second_observed)
        self.assertIsNot(first_expected.load_balancer,
                         second_expected.load_balancer)

    def test_delete(self):
        expected = self.update_quotas(self.FAKE_UUID_1)
        observed = self.quota_repo.get(self.session,
                                       project_id=self.FAKE_UUID_1)
        self.assertIsInstance(observed, models.Quotas)
        self._compare(expected, observed)
        self.quota_repo.delete(self.session, self.FAKE_UUID_1)
        observed = self.quota_repo.get(self.session,
                                       project_id=self.FAKE_UUID_1)
        self.assertIsNone(observed.health_monitor)
        self.assertIsNone(observed.load_balancer)
        self.assertIsNone(observed.listener)
        self.assertIsNone(observed.member)
        self.assertIsNone(observed.pool)

    def test_delete_non_existent(self):
        self.assertRaises(exceptions.NotFound,
                          self.quota_repo.delete,
                          self.session, 'bogus')
