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

import datetime
import random
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_db import exception as db_exception
from oslo_utils import uuidutils
from sqlalchemy.orm import defer
from sqlalchemy.orm import exc as sa_exception

from octavia.common import constants
from octavia.common import data_models
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
        super().setUp()
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
        self.flavor_repo = repo.FlavorRepository()
        self.flavor_profile_repo = repo.FlavorProfileRepository()

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
        fp_list, _ = self.flavor_profile_repo.get_all(
            self.session, id=self.FAKE_UUID_2)
        self.assertIsInstance(fp_list, list)
        flavor_list, _ = self.flavor_repo.get_all(
            self.session, id=self.FAKE_UUID_2)
        self.assertIsInstance(flavor_list, list)


class AllRepositoriesTest(base.OctaviaDBTestBase):

    FAKE_UUID_1 = uuidutils.generate_uuid()
    FAKE_UUID_2 = uuidutils.generate_uuid()
    FAKE_UUID_3 = uuidutils.generate_uuid()
    FAKE_UUID_4 = uuidutils.generate_uuid()
    FAKE_IP = '192.0.2.44'

    def setUp(self):
        super().setUp()
        self.repos = repo.Repositories()
        self.load_balancer = self.repos.load_balancer.create(
            self.session, id=self.FAKE_UUID_1, project_id=self.FAKE_UUID_2,
            name="lb_name", description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        self.listener = self.repos.listener.create(
            self.session, id=self.FAKE_UUID_4,
            protocol=constants.PROTOCOL_HTTP, protocol_port=80,
            enabled=True, provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            load_balancer_id=self.load_balancer.id)
        self.amphora = self.repos.amphora.create(
            self.session, id=uuidutils.generate_uuid(),
            load_balancer_id=self.load_balancer.id,
            compute_id=self.FAKE_UUID_3, status=constants.ACTIVE,
            vrrp_ip=self.FAKE_IP, lb_network_ip=self.FAKE_IP)
        self.session.commit()

    def test_all_repos_has_correct_repos(self):
        repo_attr_names = ('load_balancer', 'vip', 'health_monitor',
                           'session_persistence', 'pool', 'member', 'listener',
                           'listener_stats', 'amphora', 'sni',
                           'amphorahealth', 'vrrpgroup', 'l7rule', 'l7policy',
                           'amp_build_slots', 'amp_build_req', 'quotas',
                           'flavor', 'flavor_profile', 'listener_cidr',
                           'availability_zone', 'availability_zone_profile',
                           'additional_vip')
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
              'id': uuidutils.generate_uuid(), 'flavor_id': None,
              'tags': ['test_tag']}
        vip = {'ip_address': '192.0.2.1',
               'port_id': uuidutils.generate_uuid(),
               'subnet_id': uuidutils.generate_uuid(),
               'network_id': uuidutils.generate_uuid(),
               'qos_policy_id': None, 'octavia_owned': True}
        additional_vips = [{'subnet_id': uuidutils.generate_uuid(),
                            'ip_address': '192.0.2.2'}]
        lb_dm = self.repos.create_load_balancer_and_vip(self.session, lb, vip,
                                                        additional_vips)
        self.session.commit()
        lb_dm_dict = lb_dm.to_dict()
        del lb_dm_dict['vip']
        del lb_dm_dict['additional_vips']
        del lb_dm_dict['listeners']
        del lb_dm_dict['amphorae']
        del lb_dm_dict['pools']
        del lb_dm_dict['created_at']
        del lb_dm_dict['updated_at']
        self.assertIsNone(lb_dm_dict.pop('availability_zone'))
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
                'provisioning_status': constants.ACTIVE,
                'tags': ['test_tag'],
                'tls_certificate_id': uuidutils.generate_uuid(),
                'tls_enabled': False, 'tls_ciphers': None,
                'tls_versions': None,
                'alpn_protocols': None}
        pool_dm = self.repos.create_pool_on_load_balancer(
            self.session, pool, listener_id=self.listener.id)
        self.session.commit()
        pool_dm_dict = pool_dm.to_dict()
        # These are not defined in the sample pool dict but will
        # be in the live data.
        del pool_dm_dict['members']
        del pool_dm_dict['health_monitor']
        del pool_dm_dict['session_persistence']
        del pool_dm_dict['listeners']
        del pool_dm_dict['load_balancer']
        del pool_dm_dict['load_balancer_id']
        del pool_dm_dict['l7policies']
        del pool_dm_dict['created_at']
        del pool_dm_dict['updated_at']
        del pool_dm_dict['ca_tls_certificate_id']
        del pool_dm_dict['crl_container_id']
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
                'provisioning_status': constants.ACTIVE,
                'tags': ['test_tag'],
                'tls_certificate_id': uuidutils.generate_uuid(),
                'tls_enabled': False,
                'tls_ciphers': None,
                'tls_versions': None,
                'alpn_protocols': None}
        sp = {'type': constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              'cookie_name': 'cookie_monster',
              'pool_id': pool['id'],
              'persistence_granularity': None,
              'persistence_timeout': None}
        pool.update({'session_persistence': sp})
        pool_dm = self.repos.create_pool_on_load_balancer(
            self.session, pool, listener_id=self.listener.id)
        self.session.commit()
        pool_dm_dict = pool_dm.to_dict()
        # These are not defined in the sample pool dict but will
        # be in the live data.
        del pool_dm_dict['members']
        del pool_dm_dict['health_monitor']
        del pool_dm_dict['session_persistence']
        del pool_dm_dict['listeners']
        del pool_dm_dict['load_balancer']
        del pool_dm_dict['load_balancer_id']
        del pool_dm_dict['l7policies']
        del pool_dm_dict['created_at']
        del pool_dm_dict['updated_at']
        del pool_dm_dict['ca_tls_certificate_id']
        del pool_dm_dict['crl_container_id']
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
                'provisioning_status': constants.ACTIVE,
                'tags': ['test_tag'], 'tls_enabled': False,
                'tls_ciphers': None,
                'tls_versions': None,
                'alpn_protocols': None}
        pool_dm = self.repos.create_pool_on_load_balancer(
            self.session, pool, listener_id=self.listener.id)
        update_pool = {'protocol': constants.PROTOCOL_TCP, 'name': 'up_pool'}
        new_pool_dm = self.repos.update_pool_and_sp(
            self.session, pool_dm.id, update_pool)
        self.session.commit()
        pool_dm_dict = new_pool_dm.to_dict()
        # These are not defined in the sample pool dict but will
        # be in the live data.
        del pool_dm_dict['members']
        del pool_dm_dict['health_monitor']
        del pool_dm_dict['session_persistence']
        del pool_dm_dict['listeners']
        del pool_dm_dict['load_balancer']
        del pool_dm_dict['load_balancer_id']
        del pool_dm_dict['l7policies']
        del pool_dm_dict['created_at']
        del pool_dm_dict['updated_at']
        del pool_dm_dict['ca_tls_certificate_id']
        del pool_dm_dict['crl_container_id']
        pool.update(update_pool)
        pool['tls_certificate_id'] = None
        self.assertEqual(pool, pool_dm_dict)
        self.assertIsNone(new_pool_dm.session_persistence)

    def test_update_pool_with_existing_sp(self):
        pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                'description': 'desc1',
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                'enabled': True, 'operating_status': constants.ONLINE,
                'project_id': uuidutils.generate_uuid(),
                'id': uuidutils.generate_uuid(),
                'provisioning_status': constants.ACTIVE,
                'tags': ['test_tag'],
                'tls_certificate_id': uuidutils.generate_uuid(),
                'tls_enabled': False, 'tls_ciphers': None,
                'tls_versions': None,
                'alpn_protocols': None}
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
        self.session.commit()
        pool_dm_dict = new_pool_dm.to_dict()
        # These are not defined in the sample pool dict but will
        # be in the live data.
        del pool_dm_dict['members']
        del pool_dm_dict['health_monitor']
        del pool_dm_dict['session_persistence']
        del pool_dm_dict['listeners']
        del pool_dm_dict['load_balancer']
        del pool_dm_dict['load_balancer_id']
        del pool_dm_dict['l7policies']
        del pool_dm_dict['created_at']
        del pool_dm_dict['updated_at']
        del pool_dm_dict['ca_tls_certificate_id']
        del pool_dm_dict['crl_container_id']
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
        self.session.commit()
        update_pool = {'protocol': constants.PROTOCOL_TCP, 'name': 'up_pool'}
        update_sp = {'type': constants.SESSION_PERSISTENCE_HTTP_COOKIE,
                     'cookie_name': 'monster_cookie',
                     'persistence_granularity': None,
                     'persistence_timeout': None}
        update_pool.update({'session_persistence': update_sp})
        new_pool_dm = self.repos.update_pool_and_sp(
            self.session, pool_dm.id, update_pool)
        self.session.commit()
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
        self.session.commit()
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
        self.session.commit()
        update_pool = {'protocol': constants.PROTOCOL_TCP, 'name': 'up_pool',
                       'session_persistence': {}}
        new_pool_dm = self.repos.update_pool_and_sp(
            self.session, pool_dm.id, update_pool)
        self.session.commit()
        self.assertIsNone(new_pool_dm.session_persistence)

    def test_update_pool_with_cert(self):
        pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                'description': 'desc1',
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                'enabled': True, 'operating_status': constants.ONLINE,
                'project_id': uuidutils.generate_uuid(),
                'id': uuidutils.generate_uuid(),
                'provisioning_status': constants.ACTIVE,
                'tls_enabled': False, 'tls_ciphers': None,
                'tls_versions': None,
                'alpn_protocols': None}
        pool_dm = self.repos.create_pool_on_load_balancer(
            self.session, pool, listener_id=self.listener.id)
        update_pool = {'tls_certificate_id': uuidutils.generate_uuid()}
        new_pool_dm = self.repos.update_pool_and_sp(
            self.session, pool_dm.id, update_pool)
        self.session.commit()
        pool_dm_dict = new_pool_dm.to_dict()
        # These are not defined in the sample pool dict but will
        # be in the live data.
        del pool_dm_dict['members']
        del pool_dm_dict['health_monitor']
        del pool_dm_dict['session_persistence']
        del pool_dm_dict['listeners']
        del pool_dm_dict['load_balancer']
        del pool_dm_dict['load_balancer_id']
        del pool_dm_dict['l7policies']
        del pool_dm_dict['created_at']
        del pool_dm_dict['updated_at']
        del pool_dm_dict['tags']
        del pool_dm_dict['ca_tls_certificate_id']
        del pool_dm_dict['crl_container_id']
        pool.update(update_pool)
        self.assertEqual(pool, pool_dm_dict)

    def test_sqlite_transactions_broken(self):
        self.skipTest("SLQAlchemy/PySqlite transaction handling is broken. "
                      "Version 1.3.16 of sqlachemy changes how sqlite3 "
                      "transactions are handled and this test fails as "
                      "The LB created early in this process now disappears "
                      "from the transaction context.")
        """This test is a canary for pysqlite fixing transaction handling.

        When this test starts failing, we can fix and un-skip the deadlock.
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
        lock_session = db_api.get_session()
        lbs = lock_session.query(db_models.LoadBalancer).filter_by(
            project_id=project_id).all()
        self.assertEqual(0, len(lbs))  # Initially: 0
        self.repos.create_load_balancer_and_vip(lock_session, lb, vip)
        self.session.commit()
        lbs = lock_session.query(db_models.LoadBalancer).filter_by(
            project_id=project_id).all()
        self.assertEqual(1, len(lbs))  # After create: 1
        lock_session.rollback()
        lbs = lock_session.query(db_models.LoadBalancer).filter_by(
            project_id=project_id).all()
        self.assertEqual(0, len(lbs))  # After rollback: 0
        self.repos.create_load_balancer_and_vip(lock_session, lb, vip)
        self.session.commit()
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
        self.session.commit()
        lbs = lock_session.query(db_models.LoadBalancer).filter_by(
            project_id=project_id).all()
        self.assertEqual(1, len(lbs))  # After create: 1
        lock_session.rollback()
        lbs = lock_session.query(db_models.LoadBalancer).filter_by(
            project_id=project_id).all()
        self.assertEqual(1, len(lbs))  # After rollback: 1 (broken!)

    def test_check_quota_met(self):

        project_id = uuidutils.generate_uuid()

        # Test auth_strategy == NOAUTH
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.LoadBalancer,
                                                    project_id))
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # Test check for missing project_id
        self.assertRaises(exceptions.MissingProjectID,
                          self.repos.check_quota_met,
                          self.session, self.session,
                          data_models.LoadBalancer, None)
        self.session.commit()

        # Test non-quota object
        project_id = uuidutils.generate_uuid()
        self.assertFalse(
            self.repos.check_quota_met(self.session,
                                       self.session,
                                       data_models.SessionPersistence,
                                       project_id))
        self.session.commit()

        # Test DB deadlock case
        project_id = uuidutils.generate_uuid()
        mock_session = mock.MagicMock()
        mock_session.query = mock.MagicMock(
            side_effect=db_exception.DBDeadlock)
        self.assertRaises(exceptions.ProjectBusyException,
                          self.repos.check_quota_met,
                          self.session, mock_session,
                          data_models.LoadBalancer, project_id)
        self.session.commit()

        # ### Test load balancer quota
        # Test with no pre-existing quota record default 0
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_load_balancer_quota=0)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.LoadBalancer,
                                                   project_id))
        self.session.commit()
        self.assertIsNone(self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)

        # Test with no pre-existing quota record default 1
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_load_balancer_quota=1)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.LoadBalancer,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.LoadBalancer,
                                                   project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)

        # Test with no pre-existing quota record default unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas',
                    default_load_balancer_quota=constants.QUOTA_UNLIMITED)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.LoadBalancer,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)
        # Test above project adding another load balancer
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.LoadBalancer,
                                                    project_id))
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)

        # Test upgrade case with pre-quota load balancers
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_load_balancer_quota=1)
        self.repos.load_balancer.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="lb_name",
            description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True)
        self.session.commit()
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.LoadBalancer,
                                                   project_id))
        self.session.commit()

        # Test upgrade case with pre-quota deleted load balancers
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_load_balancer_quota=1)
        self.repos.load_balancer.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="lb_name",
            description="lb_description",
            provisioning_status=constants.DELETED,
            operating_status=constants.ONLINE,
            enabled=True)
        self.session.commit()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.LoadBalancer,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)

        # Test pre-existing quota with quota of zero
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_load_balancer_quota=10)
        quota = {'load_balancer': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.session.commit()
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.LoadBalancer,
                                                   project_id))
        self.session.commit()

        # Test pre-existing quota with quota of one
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_load_balancer_quota=0)
        quota = {'load_balancer': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.session.commit()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.LoadBalancer,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.LoadBalancer,
                                                   project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)

        # Test pre-existing quota with quota of unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_load_balancer_quota=0)
        quota = {'load_balancer': constants.QUOTA_UNLIMITED}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.session.commit()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.LoadBalancer,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)
        # Test above project adding another load balancer
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.LoadBalancer,
                                                    project_id))
        self.session.commit()
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)

        # ### Test listener quota
        # Test with no pre-existing quota record default 0
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_listener_quota=0)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.Listener,
                                                   project_id))
        self.session.commit()
        self.assertIsNone(self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)

        # Test with no pre-existing quota record default 1
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_listener_quota=1)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Listener,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.Listener,
                                                   project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)

        # Test with no pre-existing quota record default unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas',
                    default_listener_quota=constants.QUOTA_UNLIMITED)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Listener,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)
        # Test above project adding another listener
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Listener,
                                                    project_id))
        self.session.commit()
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
        self.session.commit()
        self.repos.listener.create(
            self.session, id=uuidutils.generate_uuid(),
            protocol=constants.PROTOCOL_HTTP, protocol_port=80,
            enabled=True, provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, project_id=project_id,
            load_balancer_id=lb.id)
        self.session.commit()
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.Listener,
                                                   project_id))
        self.session.commit()

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
        self.session.commit()
        self.repos.listener.create(
            self.session, id=uuidutils.generate_uuid(),
            protocol=constants.PROTOCOL_HTTP, protocol_port=80,
            enabled=True, provisioning_status=constants.DELETED,
            operating_status=constants.ONLINE, project_id=project_id,
            load_balancer_id=lb.id)
        self.session.commit()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Listener,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)

        # Test pre-existing quota with quota of zero
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_listener_quota=10)
        quota = {'listener': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.session.commit()
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.Listener,
                                                   project_id))
        self.session.commit()

        # Test pre-existing quota with quota of one
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_listener_quota=0)
        quota = {'listener': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.session.commit()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Listener,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.Listener,
                                                   project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)

        # Test pre-existing quota with quota of unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_listener_quota=0)
        quota = {'listener': constants.QUOTA_UNLIMITED}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.session.commit()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Listener,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)
        # Test above project adding another listener
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Listener,
                                                    project_id))
        self.session.commit()
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)

        # ### Test pool quota
        # Test with no pre-existing quota record default 0
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_pool_quota=0)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.Pool,
                                                   project_id))
        self.session.commit()
        self.assertIsNone(self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)

        # Test with no pre-existing quota record default 1
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_pool_quota=1)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Pool,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.Pool,
                                                   project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)

        # Test with no pre-existing quota record default unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas',
                    default_pool_quota=constants.QUOTA_UNLIMITED)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Pool,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)
        # Test above project adding another pool
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Pool,
                                                    project_id))
        self.session.commit()
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
        self.session.commit()
        self.repos.pool.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="pool1",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True, load_balancer_id=lb.id)
        self.session.commit()
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.Pool,
                                                   project_id))
        self.session.commit()

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
        self.session.commit()
        self.repos.pool.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="pool1",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.DELETED,
            operating_status=constants.ONLINE,
            enabled=True, load_balancer_id=lb.id)
        self.session.commit()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Pool,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)

        # Test pre-existing quota with quota of zero
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_pool_quota=10)
        quota = {'pool': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.Pool,
                                                   project_id))
        self.session.commit()

        # Test pre-existing quota with quota of one
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_pool_quota=0)
        quota = {'pool': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Pool,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.Pool,
                                                   project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)

        # Test pre-existing quota with quota of unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_pool_quota=0)
        quota = {'pool': constants.QUOTA_UNLIMITED}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.session.commit()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Pool,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)
        # Test above project adding another pool
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Pool,
                                                    project_id))
        self.session.commit()
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)

        # ### Test health monitor quota
        # Test with no pre-existing quota record default 0
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_health_monitor_quota=0)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.HealthMonitor,
                                                   project_id))
        self.session.commit()
        self.assertIsNone(self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)

        # Test with no pre-existing quota record default 1
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_health_monitor_quota=1)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.HealthMonitor,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.HealthMonitor,
                                                   project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)

        # Test with no pre-existing quota record default unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas',
                    default_health_monitor_quota=constants.QUOTA_UNLIMITED)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.HealthMonitor,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)
        # Test above project adding another health monitor
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.HealthMonitor,
                                                    project_id))
        self.session.commit()
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
        self.session.commit()
        pool = self.repos.pool.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="pool1",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True, load_balancer_id=lb.id)
        self.session.commit()
        self.repos.health_monitor.create(
            self.session, project_id=project_id,
            name="health_mon1", type=constants.HEALTH_MONITOR_HTTP,
            delay=1, timeout=1, fall_threshold=1, rise_threshold=1,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True, pool_id=pool.id)
        self.session.commit()
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.HealthMonitor,
                                                   project_id))
        self.session.commit()

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
        self.session.commit()
        pool = self.repos.pool.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="pool1",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True, load_balancer_id=lb.id)
        self.session.commit()
        self.repos.health_monitor.create(
            self.session, project_id=project_id,
            name="health_mon1", type=constants.HEALTH_MONITOR_HTTP,
            delay=1, timeout=1, fall_threshold=1, rise_threshold=1,
            provisioning_status=constants.DELETED,
            operating_status=constants.OFFLINE,
            enabled=True, pool_id=pool.id)
        self.session.commit()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.HealthMonitor,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)

        # Test pre-existing quota with quota of zero
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_health_monitor_quota=10)
        quota = {'health_monitor': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.session.commit()
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.HealthMonitor,
                                                   project_id))
        self.session.commit()

        # Test pre-existing quota with quota of one
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_health_monitor_quota=0)
        quota = {'health_monitor': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.HealthMonitor,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.HealthMonitor,
                                                   project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)

        # Test pre-existing quota with quota of unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_health_monitor_quota=0)
        quota = {'health_monitor': constants.QUOTA_UNLIMITED}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.session.commit()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.HealthMonitor,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)
        # Test above project adding another health monitor
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.HealthMonitor,
                                                    project_id))
        self.session.commit()
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)

        # ### Test member quota
        # Test with no pre-existing quota record default 0
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_member_quota=0)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.Member,
                                                   project_id))
        self.session.commit()
        self.assertIsNone(self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)

        # Test with no pre-existing quota record default 1
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_member_quota=1)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Member,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.Member,
                                                   project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)

        # Test with no pre-existing quota record default unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas',
                    default_member_quota=constants.QUOTA_UNLIMITED)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Member,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)
        # Test above project adding another member
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Member,
                                                    project_id))
        self.session.commit()
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
        self.session.commit()
        pool = self.repos.pool.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="pool1",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True, load_balancer_id=lb.id)
        self.session.commit()
        self.repos.member.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id,
            ip_address='192.0.2.1', protocol_port=80,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True, pool_id=pool.id, backup=False)
        self.session.commit()
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.Member,
                                                   project_id))
        self.session.commit()

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
        self.session.commit()
        pool = self.repos.pool.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="pool1",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True, load_balancer_id=lb.id)
        self.session.commit()
        self.repos.member.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id,
            ip_address='192.0.2.1', protocol_port=80,
            provisioning_status=constants.DELETED,
            operating_status=constants.ONLINE,
            enabled=True, pool_id=pool.id, backup=False)
        self.session.commit()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Member,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)

        # Test pre-existing quota with quota of zero
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_member_quota=10)
        quota = {'member': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.session.commit()
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.Member,
                                                   project_id))
        self.session.commit()

        # Test pre-existing quota with quota of one
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_member_quota=0)
        quota = {'member': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.session.commit()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Member,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.Member,
                                                   project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)

        # Test pre-existing quota with quota of unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_member_quota=0)
        quota = {'member': constants.QUOTA_UNLIMITED}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.session.commit()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Member,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)
        # Test above project adding another member
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.Member,
                                                    project_id))
        self.session.commit()
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)

        # ### Test l7policy quota
        # Test with no pre-existing quota record default 0
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_l7policy_quota=0)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.L7Policy,
                                                   project_id))
        self.session.commit()
        self.assertIsNone(self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7policy)

        # Test with no pre-existing quota record default 1
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_l7policy_quota=1)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.L7Policy,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7policy)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.L7Policy,
                                                   project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7policy)

        # Test with no pre-existing quota record default unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas',
                    default_l7policy_quota=constants.QUOTA_UNLIMITED)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.L7Policy,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7policy)
        # Test above project adding another l7policy
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.L7Policy,
                                                    project_id))
        self.session.commit()
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7policy)

        # Test upgrade case with pre-quota l7policy
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_l7policy_quota=1)
        lb = self.repos.load_balancer.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="lb_name",
            description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True)
        self.session.commit()
        listener = self.repos.listener.create(
            self.session, id=uuidutils.generate_uuid(),
            protocol=constants.PROTOCOL_HTTP, protocol_port=80,
            enabled=True, provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, project_id=project_id,
            load_balancer_id=lb.id)
        self.session.commit()
        self.repos.l7policy.create(
            self.session, name='l7policy', enabled=True, position=1,
            action=constants.L7POLICY_ACTION_REJECT,
            provisioning_status=constants.ACTIVE, listener_id=listener.id,
            operating_status=constants.ONLINE, project_id=project_id,
            id=uuidutils.generate_uuid())
        self.session.commit()
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.L7Policy,
                                                   project_id))
        self.session.commit()

        # Test upgrade case with pre-quota deleted l7policy
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_l7policy_quota=1)
        lb = self.repos.load_balancer.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="lb_name",
            description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True)
        self.session.commit()
        listener = self.repos.listener.create(
            self.session, id=uuidutils.generate_uuid(),
            protocol=constants.PROTOCOL_HTTP, protocol_port=80,
            enabled=True, provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, project_id=project_id,
            load_balancer_id=lb.id)
        self.session.commit()
        self.repos.l7policy.create(
            self.session, name='l7policy', enabled=True, position=1,
            action=constants.L7POLICY_ACTION_REJECT,
            provisioning_status=constants.DELETED, listener_id=listener.id,
            operating_status=constants.ONLINE, project_id=project_id,
            id=uuidutils.generate_uuid())
        self.session.commit()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.L7Policy,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7policy)

        # Test pre-existing quota with quota of zero
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_l7policy_quota=10)
        quota = {'l7policy': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.session.commit()
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.L7Policy,
                                                   project_id))
        self.session.commit()

        # Test pre-existing quota with quota of one
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_l7policy_quota=0)
        quota = {'l7policy': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.session.commit()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.L7Policy,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7policy)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.L7Policy,
                                                   project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7policy)

        # Test pre-existing quota with quota of unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_l7policy_quota=0)
        quota = {'l7policy': constants.QUOTA_UNLIMITED}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.session.commit()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.L7Policy,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7policy)
        # Test above project adding another l7policy
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.L7Policy,
                                                    project_id))
        self.session.commit()
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7policy)

        # ### Test l7rule quota
        # Test with no pre-existing quota record default 0
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_l7rule_quota=0)
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.L7Rule,
                                                   project_id))
        self.session.commit()
        self.assertIsNone(self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7rule)

        # Test with no pre-existing quota record default 1
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_l7rule_quota=1)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.L7Rule,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7rule)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.L7Rule,
                                                   project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7rule)

        # Test with no pre-existing quota record default unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas',
                    default_l7rule_quota=constants.QUOTA_UNLIMITED)
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.L7Rule,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7rule)
        # Test above project adding another l7rule
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.L7Rule,
                                                    project_id))
        self.session.commit()
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7rule)

        # Test upgrade case with pre-quota l7rule
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_l7rule_quota=1)
        lb = self.repos.load_balancer.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="lb_name",
            description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True)
        self.session.commit()
        listener = self.repos.listener.create(
            self.session, id=uuidutils.generate_uuid(),
            protocol=constants.PROTOCOL_HTTP, protocol_port=80,
            enabled=True, provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, project_id=project_id,
            load_balancer_id=lb.id)
        self.session.commit()
        l7policy = self.repos.l7policy.create(
            self.session, name='l7policy', enabled=True, position=1,
            action=constants.L7POLICY_ACTION_REJECT,
            provisioning_status=constants.ACTIVE, listener_id=listener.id,
            operating_status=constants.ONLINE, project_id=project_id,
            id=uuidutils.generate_uuid())
        self.session.commit()
        self.repos.l7rule.create(
            self.session, id=uuidutils.generate_uuid(),
            l7policy_id=l7policy.id, type=constants.L7RULE_TYPE_HOST_NAME,
            compare_type=constants.L7RULE_COMPARE_TYPE_EQUAL_TO, enabled=True,
            provisioning_status=constants.ACTIVE, value='hostname',
            operating_status=constants.ONLINE, project_id=project_id)
        self.session.commit()
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.L7Rule,
                                                   project_id))
        self.session.commit()

        # Test upgrade case with pre-quota deleted l7rule
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_l7policy_quota=1)
        lb = self.repos.load_balancer.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=project_id, name="lb_name",
            description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True)
        self.session.commit()
        listener = self.repos.listener.create(
            self.session, id=uuidutils.generate_uuid(),
            protocol=constants.PROTOCOL_HTTP, protocol_port=80,
            enabled=True, provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, project_id=project_id,
            load_balancer_id=lb.id)
        self.session.commit()
        l7policy = self.repos.l7policy.create(
            self.session, name='l7policy', enabled=True, position=1,
            action=constants.L7POLICY_ACTION_REJECT,
            provisioning_status=constants.ACTIVE, listener_id=listener.id,
            operating_status=constants.ONLINE, project_id=project_id,
            id=uuidutils.generate_uuid())
        self.session.commit()
        self.repos.l7rule.create(
            self.session, id=uuidutils.generate_uuid(),
            l7policy_id=l7policy.id, type=constants.L7RULE_TYPE_HOST_NAME,
            compare_type=constants.L7RULE_COMPARE_TYPE_EQUAL_TO, enabled=True,
            provisioning_status=constants.DELETED, value='hostname',
            operating_status=constants.ONLINE, project_id=project_id)
        self.session.commit()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.L7Rule,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7rule)

        # Test pre-existing quota with quota of zero
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_l7rule_quota=10)
        quota = {'l7rule': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.session.commit()
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.L7Rule,
                                                   project_id))
        self.session.commit()

        # Test pre-existing quota with quota of one
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_l7rule_quota=0)
        quota = {'l7rule': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.session.commit()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.L7Rule,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7rule)
        # Test above project is now at quota
        self.assertTrue(self.repos.check_quota_met(self.session,
                                                   self.session,
                                                   data_models.L7Rule,
                                                   project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7rule)

        # Test pre-existing quota with quota of unlimited
        project_id = uuidutils.generate_uuid()
        conf.config(group='quotas', default_l7rule_quota=0)
        quota = {'l7rule': constants.QUOTA_UNLIMITED}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.session.commit()
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.L7Rule,
                                                    project_id))
        self.session.commit()
        self.assertEqual(1, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7rule)
        # Test above project adding another l7rule
        self.assertFalse(self.repos.check_quota_met(self.session,
                                                    self.session,
                                                    data_models.L7Rule,
                                                    project_id))
        self.session.commit()
        self.assertEqual(2, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7rule)

    def test_decrement_quota(self):
        # Test decrement on non-existent quota with noauth
        project_id = uuidutils.generate_uuid()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        self.repos.decrement_quota(self.session,
                                   data_models.LoadBalancer,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.count(self.session,
                                                    project_id=project_id))
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # Test decrement on non-existent quota
        project_id = uuidutils.generate_uuid()
        self.repos.decrement_quota(self.session,
                                   data_models.LoadBalancer,
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
                          data_models.LoadBalancer, project_id)

        # ### Test load balancer quota
        # Test decrement on zero in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_load_balancer': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   data_models.LoadBalancer,
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
                                   data_models.LoadBalancer,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_load_balancer)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # Test decrement on in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_load_balancer': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   data_models.LoadBalancer,
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
                                   data_models.LoadBalancer,
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
                                   data_models.Listener,
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
                                   data_models.Listener,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_listener)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # Test decrement on in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_listener': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   data_models.Listener,
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
                                   data_models.Listener,
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
                                   data_models.Pool,
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
                                   data_models.Pool,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_pool)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # Test decrement on in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_pool': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   data_models.Pool,
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
                                   data_models.Pool,
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
                                   data_models.HealthMonitor,
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
                                   data_models.HealthMonitor,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_health_monitor)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # Test decrement on in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_health_monitor': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   data_models.HealthMonitor,
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
                                   data_models.HealthMonitor,
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
                                   data_models.Member,
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
                                   data_models.Member,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # Test decrement on in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_member': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   data_models.Member,
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
                                   data_models.Member,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_member)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)
        # ### Test l7policy quota
        # Test decrement on zero in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_l7policy': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   data_models.L7Policy,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7policy)

        # Test decrement on zero in use quota with noauth
        project_id = uuidutils.generate_uuid()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        quota = {'in_use_l7policy': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   data_models.L7Policy,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7policy)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # Test decrement on in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_l7policy': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   data_models.L7Policy,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7policy)

        # Test decrement on in use quota with noauth
        project_id = uuidutils.generate_uuid()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        quota = {'in_use_l7policy': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   data_models.L7Policy,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7policy)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # ### Test l7rule quota
        # Test decrement on zero in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_l7rule': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   data_models.L7Rule,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7rule)

        # Test decrement on zero in use quota with noauth
        project_id = uuidutils.generate_uuid()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        quota = {'in_use_l7rule': 0}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   data_models.L7Rule,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7rule)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

        # Test decrement on in use quota
        project_id = uuidutils.generate_uuid()
        quota = {'in_use_l7rule': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   data_models.L7Rule,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7rule)

        # Test decrement on in use quota with noauth
        project_id = uuidutils.generate_uuid()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        quota = {'in_use_l7rule': 1}
        self.repos.quotas.update(self.session, project_id, quota=quota)
        self.repos.decrement_quota(self.session,
                                   data_models.L7Rule,
                                   project_id)
        self.assertEqual(0, self.repos.quotas.get(
            self.session, project_id=project_id).in_use_l7rule)
        conf.config(group='api_settings', auth_strategy=constants.TESTING)

    def test_get_amphora_stats(self):
        listener2_id = uuidutils.generate_uuid()
        self.repos.listener_stats.create(
            self.session, listener_id=self.listener.id,
            amphora_id=self.amphora.id, bytes_in=1, bytes_out=2,
            active_connections=3, total_connections=4, request_errors=5)
        self.repos.listener_stats.create(
            self.session, listener_id=listener2_id,
            amphora_id=self.amphora.id, bytes_in=6, bytes_out=7,
            active_connections=8, total_connections=9, request_errors=10)
        amp_stats = self.repos.get_amphora_stats(self.session, self.amphora.id)
        self.assertEqual(2, len(amp_stats))
        for stats in amp_stats:
            if stats['listener_id'] == self.listener.id:
                self.assertEqual(self.load_balancer.id,
                                 stats['loadbalancer_id'])
                self.assertEqual(self.listener.id, stats['listener_id'])
                self.assertEqual(self.amphora.id, stats['id'])
                self.assertEqual(1, stats['bytes_in'])
                self.assertEqual(2, stats['bytes_out'])
                self.assertEqual(3, stats['active_connections'])
                self.assertEqual(4, stats['total_connections'])
                self.assertEqual(5, stats['request_errors'])
            else:
                self.assertEqual(self.load_balancer.id,
                                 stats['loadbalancer_id'])
                self.assertEqual(listener2_id, stats['listener_id'])
                self.assertEqual(self.amphora.id, stats['id'])
                self.assertEqual(6, stats['bytes_in'])
                self.assertEqual(7, stats['bytes_out'])
                self.assertEqual(8, stats['active_connections'])
                self.assertEqual(9, stats['total_connections'])
                self.assertEqual(10, stats['request_errors'])


class PoolRepositoryTest(BaseRepositoryTest):

    def create_pool(self, pool_id, project_id):
        pool = self.pool_repo.create(
            self.session, id=pool_id, project_id=project_id, name="pool_test",
            description="pool_description", protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True, tags=['test_tag'])
        self.session.commit()
        return pool

    def test_get(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                project_id=self.FAKE_UUID_2)
        new_pool = self.pool_repo.get(self.session, id=pool.id)
        self.assertIsInstance(new_pool, data_models.Pool)
        self.assertEqual(pool.id, new_pool.id)
        self.assertEqual(pool.project_id, new_pool.project_id)

    def test_get_all(self):
        pool_one = self.create_pool(pool_id=self.FAKE_UUID_1,
                                    project_id=self.FAKE_UUID_2)
        pool_two = self.create_pool(pool_id=self.FAKE_UUID_3,
                                    project_id=self.FAKE_UUID_2)
        pool_list, _ = self.pool_repo.get_all(self.session,
                                              project_id=self.FAKE_UUID_2)
        self.assertIsInstance(pool_list, list)
        self.assertEqual(2, len(pool_list))
        self.assertEqual(pool_one.id, pool_list[0].id)
        self.assertEqual(pool_one.project_id, pool_list[0].project_id)
        self.assertEqual(pool_two.id, pool_list[1].id)
        self.assertEqual(pool_two.project_id, pool_list[1].project_id)

    def test_create(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                project_id=self.FAKE_UUID_2)
        self.assertIsInstance(pool, data_models.Pool)
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
        self.session.commit()
        new_pool = self.pool_repo.get(self.session, id=self.FAKE_UUID_1)
        self.assertEqual("other_pool_description", new_pool.description)

    def test_delete(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                project_id=self.FAKE_UUID_2)
        self.pool_repo.delete(self.session, id=pool.id)
        self.session.commit()
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
        self.session.commit()
        new_pool = self.pool_repo.get(self.session, id=pool.id)
        self.assertEqual(1, len(new_pool.members))
        self.assertEqual(member.id, new_pool.members[0].id)
        self.assertEqual(member.ip_address, new_pool.members[0].ip_address)
        self.pool_repo.delete(self.session, id=pool.id)
        self.session.commit()
        self.assertIsNone(self.pool_repo.get(self.session, id=pool.id))
        self.assertIsNone(self.member_repo.get(self.session, id=member.id))

    def test_delete_with_health_monitor(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                project_id=self.FAKE_UUID_2)
        hm = self.hm_repo.create(self.session, id=uuidutils.generate_uuid(),
                                 pool_id=pool.id,
                                 type=constants.HEALTH_MONITOR_HTTP,
                                 delay=1, timeout=1, fall_threshold=1,
                                 rise_threshold=1, enabled=True,
                                 provisioning_status=constants.ACTIVE,
                                 operating_status=constants.ONLINE)
        self.session.commit()
        new_pool = self.pool_repo.get(self.session, id=pool.id)
        self.assertEqual(pool.id, new_pool.id)
        self.assertEqual(pool.name, new_pool.name)
        self.assertEqual(pool.project_id, new_pool.project_id)
        self.assertEqual(hm.id, new_pool.health_monitor.id)
        self.assertEqual(hm.name, new_pool.health_monitor.name)
        self.assertEqual(hm.type, new_pool.health_monitor.type)
        self.assertEqual(hm.pool_id, new_pool.health_monitor.pool_id)
        self.pool_repo.delete(self.session, id=pool.id)
        self.session.commit()
        self.assertIsNone(self.pool_repo.get(self.session, id=pool.id))
        self.assertIsNone(self.hm_repo.get(self.session, pool_id=hm.pool_id))

    def test_delete_with_session_persistence(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                project_id=self.FAKE_UUID_2)
        sp = self.sp_repo.create(
            self.session, pool_id=pool.id,
            type=constants.SESSION_PERSISTENCE_HTTP_COOKIE,
            cookie_name="cookie_name")
        self.session.commit()
        new_pool = self.pool_repo.get(self.session, id=pool.id)
        self.assertEqual(pool.id, new_pool.id)
        self.assertEqual(pool.project_id, new_pool.project_id)
        self.assertEqual(sp.pool_id, new_pool.session_persistence.pool_id)
        self.pool_repo.delete(self.session, id=new_pool.id)
        self.session.commit()
        self.assertIsNone(self.pool_repo.get(self.session, id=pool.id))
        self.assertIsNone(self.sp_repo.get(self.session, pool_id=sp.pool_id))

    def test_delete_with_all_children(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                project_id=self.FAKE_UUID_2)
        hm = self.hm_repo.create(self.session,
                                 id=uuidutils.generate_uuid(),
                                 pool_id=pool.id,
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
        self.session.commit()
        new_pool = self.pool_repo.get(self.session, id=pool.id)
        self.assertEqual(pool.id, new_pool.id)
        self.assertEqual(pool.project_id, new_pool.project_id)
        self.assertEqual(1, len(new_pool.members))
        new_member = self.member_repo.get(self.session, id=member.id)
        self.assertEqual(new_member.id, new_pool.members[0].id)
        self.assertEqual(new_member.pool_id, new_pool.members[0].pool_id)
        self.assertEqual(new_member.ip_address, new_pool.members[0].ip_address)
        self.assertEqual(hm.id, new_pool.health_monitor.id)
        self.assertEqual(hm.type, new_pool.health_monitor.type)
        self.assertEqual(hm.pool_id, new_pool.health_monitor.pool_id)
        self.assertEqual(sp.type, new_pool.session_persistence.type)
        self.assertEqual(sp.pool_id, new_pool.session_persistence.pool_id)
        self.pool_repo.delete(self.session, id=pool.id)
        self.session.commit()
        self.assertIsNone(self.pool_repo.get(self.session, id=pool.id))
        self.assertIsNone(self.member_repo.get(self.session, id=member.id))
        self.assertIsNone(self.hm_repo.get(self.session, pool_id=hm.pool_id))
        self.assertIsNone(self.sp_repo.get(self.session, pool_id=sp.pool_id))

    def test_get_children_count(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                project_id=self.FAKE_UUID_2)
        hm_count, member_count = (
            self.pool_repo.get_children_count(self.session, pool.id))
        self.assertEqual(0, hm_count)
        self.assertEqual(0, member_count)

        self.hm_repo.create(self.session, pool_id=pool.id,
                            type=constants.HEALTH_MONITOR_HTTP,
                            delay=1, timeout=1, fall_threshold=1,
                            rise_threshold=1, enabled=True,
                            provisioning_status=constants.ACTIVE,
                            operating_status=constants.ONLINE)
        self.session.commit()

        hm_count, member_count = (
            self.pool_repo.get_children_count(self.session, pool.id))
        self.assertEqual(1, hm_count)
        self.assertEqual(0, member_count)

        self.member_repo.create(self.session, id=self.FAKE_UUID_3,
                                project_id=self.FAKE_UUID_2,
                                pool_id=pool.id,
                                ip_address="192.0.2.1",
                                protocol_port=80,
                                provisioning_status=constants.ACTIVE,
                                operating_status=constants.ONLINE,
                                enabled=True,
                                backup=False)
        self.member_repo.create(self.session, id=self.FAKE_UUID_4,
                                project_id=self.FAKE_UUID_2,
                                pool_id=pool.id,
                                ip_address="192.0.2.2",
                                protocol_port=80,
                                provisioning_status=constants.ACTIVE,
                                operating_status=constants.ONLINE,
                                enabled=True,
                                backup=False)
        self.session.commit()

        hm_count, member_count = (
            self.pool_repo.get_children_count(self.session, pool.id))
        self.assertEqual(1, hm_count)
        self.assertEqual(2, member_count)


class MemberRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super().setUp()
        self.pool = self.pool_repo.create(
            self.session, id=self.FAKE_UUID_1, project_id=self.FAKE_UUID_2,
            name="pool_test", description="pool_description",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True, tags=['test_tag'])
        self.session.commit()

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
        self.session.commit()
        return member

    def test_get(self):
        member = self.create_member(self.FAKE_UUID_1, self.FAKE_UUID_2,
                                    self.pool.id, "192.0.2.1")
        new_member = self.member_repo.get(self.session, id=member.id)
        self.assertIsInstance(new_member, data_models.Member)
        self.assertEqual(member.id, new_member.id)
        self.assertEqual(member.pool_id, new_member.pool_id)
        self.assertEqual(member.ip_address, new_member.ip_address)

    def test_get_all(self):
        member_one = self.create_member(self.FAKE_UUID_1, self.FAKE_UUID_2,
                                        self.pool.id, "192.0.2.1")
        member_two = self.create_member(self.FAKE_UUID_3, self.FAKE_UUID_2,
                                        self.pool.id, "192.0.2.2")
        member_list, _ = self.member_repo.get_all(self.session,
                                                  project_id=self.FAKE_UUID_2)
        self.assertIsInstance(member_list, list)
        self.assertEqual(2, len(member_list))
        self.assertEqual(member_one.id, member_list[0].id)
        self.assertEqual(member_one.pool_id, member_list[0].pool_id)
        self.assertEqual(member_one.ip_address, member_list[0].ip_address)
        self.assertEqual(member_two.id, member_list[1].id)
        self.assertEqual(member_two.pool_id, member_list[1].pool_id)
        self.assertEqual(member_two.ip_address, member_list[1].ip_address)

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
        self.session.commit()
        new_member = self.member_repo.get(self.session, id=member.id)
        self.assertEqual(ip_address_change, new_member.ip_address)

    def test_delete(self):
        member = self.create_member(self.FAKE_UUID_1, self.FAKE_UUID_2,
                                    self.pool.id, "192.0.2.1")
        self.member_repo.delete(self.session, id=member.id)
        self.session.commit()
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
        self.session.commit()
        new_member1 = self.member_repo.get(self.session, id=member1.id)
        new_member2 = self.member_repo.get(self.session, id=member2.id)
        self.assertEqual(constants.OFFLINE, new_member1.operating_status)
        self.assertEqual(constants.OFFLINE, new_member2.operating_status)


class SessionPersistenceRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super().setUp()
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
        self.assertIsInstance(new_sp, data_models.SessionPersistence)
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
        super().setUp()
        self.load_balancer = self.lb_repo.create(
            self.session, id=self.FAKE_UUID_1, project_id=self.FAKE_UUID_2,
            name="lb_name", description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True,
            server_group_id=self.FAKE_UUID_1)
        self.session.commit()

    def create_listener(self, listener_id, port, default_pool_id=None,
                        provisioning_status=constants.ACTIVE):
        listener = self.listener_repo.create(
            self.session, id=listener_id, project_id=self.FAKE_UUID_2,
            name="listener_name", description="listener_description",
            protocol=constants.PROTOCOL_HTTP, protocol_port=port,
            connection_limit=1, load_balancer_id=self.load_balancer.id,
            default_pool_id=default_pool_id, operating_status=constants.ONLINE,
            provisioning_status=provisioning_status, enabled=True,
            peer_port=1025, tags=['test_tag'])
        self.session.commit()
        return listener

    def create_amphora(self, amphora_id, loadbalancer_id):
        amphora = self.amphora_repo.create(self.session, id=amphora_id,
                                           load_balancer_id=loadbalancer_id,
                                           compute_id=self.FAKE_UUID_3,
                                           status=constants.ACTIVE,
                                           vrrp_ip=self.FAKE_IP,
                                           lb_network_ip=self.FAKE_IP)
        self.session.commit()
        return amphora

    def create_loadbalancer(self, lb_id):
        lb = self.lb_repo.create(self.session, id=lb_id,
                                 project_id=self.FAKE_UUID_2, name="lb_name",
                                 description="lb_description",
                                 provisioning_status=constants.ACTIVE,
                                 operating_status=constants.ONLINE,
                                 enabled=True)
        self.session.commit()
        return lb

    def test_get(self):
        listener = self.create_listener(self.FAKE_UUID_1, 80)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIsInstance(new_listener, data_models.Listener)
        self.assertEqual(listener.id, new_listener.id)
        self.assertEqual(listener.name, new_listener.name)
        self.assertEqual(listener.protocol, new_listener.protocol)
        self.assertEqual(listener.protocol_port, new_listener.protocol_port)

    def test_get_all(self):
        listener_one = self.create_listener(self.FAKE_UUID_1, 80)
        listener_two = self.create_listener(self.FAKE_UUID_3, 88)
        listener_list, _ = self.listener_repo.get_all(
            self.session, project_id=self.FAKE_UUID_2)
        self.assertIsInstance(listener_list, list)
        self.assertEqual(2, len(listener_list))
        self.assertEqual(listener_one.id, listener_list[0].id)
        self.assertEqual(listener_two.id, listener_list[1].id)

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
        self.session.commit()
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
        self.session.commit()
        listener_b = self.listener_repo.create(
            self.session, id=uuidutils.generate_uuid(),
            project_id=self.FAKE_UUID_2,
            load_balancer_id=lb.id, protocol=constants.PROTOCOL_HTTP,
            protocol_port=81, provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        self.session.commit()
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
        self.session.commit()
        pool = self.pool_repo.create(
            self.session, id=self.FAKE_UUID_4, project_id=self.FAKE_UUID_2,
            name="pool_test", description="pool_description",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True,
            load_balancer_id=load_balancer2.id)
        self.session.commit()
        self.assertRaises(exceptions.NotFound, self.create_listener,
                          self.FAKE_UUID_1, 80, default_pool_id=pool.id)

    def test_create_2_sni_containers(self):
        listener = self.create_listener(self.FAKE_UUID_1, 80)
        container1 = {'listener_id': listener.id,
                      'tls_container_id': self.FAKE_UUID_1}
        container2 = {'listener_id': listener.id,
                      'tls_container_id': self.FAKE_UUID_2}
        container1_dm = data_models.SNI(**container1)
        container2_dm = data_models.SNI(**container2)
        self.sni_repo.create(self.session, **container1)
        self.sni_repo.create(self.session, **container2)
        self.session.commit()
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIn(container1_dm, new_listener.sni_containers)
        self.assertIn(container2_dm, new_listener.sni_containers)

    def test_update(self):
        name_change = "new_listener_name"
        listener = self.create_listener(self.FAKE_UUID_1, 80)
        self.session.commit()
        self.listener_repo.update(self.session, listener.id,
                                  name=name_change)
        self.session.commit()
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertEqual(name_change, new_listener.name)

    def test_update_with_sni(self):
        listener = self.create_listener(self.FAKE_UUID_1, 80)
        container1 = {'listener_id': listener.id,
                      'tls_container_id': self.FAKE_UUID_2}
        container1_dm = data_models.SNI(**container1)
        self.listener_repo.update(self.session, listener.id,
                                  sni_containers=[self.FAKE_UUID_2])
        self.session.commit()
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIn(container1_dm, new_listener.sni_containers)

    def test_update_bad_id(self):
        self.assertRaises(exceptions.NotFound, self.listener_repo.update,
                          self.session, id=uuidutils.generate_uuid())

    def test_delete(self):
        listener = self.create_listener(self.FAKE_UUID_1, 80)
        self.listener_repo.delete(self.session, id=listener.id)
        self.assertIsNone(self.listener_repo.get(self.session, id=listener.id))

    def test_delete_with_sni(self):
        listener = self.create_listener(self.FAKE_UUID_1, 80)
        sni = self.sni_repo.create(self.session, listener_id=listener.id,
                                   tls_container_id=self.FAKE_UUID_3)
        self.session.commit()
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIsNotNone(new_listener)
        self.assertEqual(sni, new_listener.sni_containers[0])
        self.listener_repo.delete(self.session, id=new_listener.id)
        self.session.commit()
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
        self.session.commit()
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIsNotNone(new_listener)
        self.assertIsNotNone(self.listener_stats_repo.get(
            self.session, listener_id=listener.id))
        self.listener_repo.delete(self.session, id=listener.id)
        self.session.commit()
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
        self.session.commit()
        listener = self.create_listener(self.FAKE_UUID_1, 80,
                                        default_pool_id=pool.id)
        pool = self.pool_repo.get(self.session, id=pool.id)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIsNotNone(new_listener)
        self.assertEqual(pool, new_listener.default_pool)
        self.listener_repo.delete(self.session, id=new_listener.id)
        self.session.commit()
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
        self.session.commit()
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
        self.session.commit()
        pool = self.pool_repo.get(self.session, id=pool.id)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIsNotNone(new_listener)
        self.assertEqual(pool, new_listener.default_pool)
        self.assertEqual(sni, new_listener.sni_containers[0])
        self.listener_repo.delete(self.session, id=listener.id)
        self.session.commit()
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
        self.session.commit()
        listener = self.create_listener(self.FAKE_UUID_1, 80,
                                        default_pool_id=pool.id)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIsNotNone(new_listener)
        self.assertEqual(pool.id, new_listener.default_pool.id)
        self.assertEqual(pool.load_balancer_id,
                         new_listener.default_pool.load_balancer_id)
        self.assertEqual(pool.project_id, new_listener.default_pool.project_id)
        self.pool_repo.delete(self.session, id=pool.id)
        self.session.commit()
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIsNone(new_listener.default_pool)

    def test_prov_status_active_if_not_error_active(self):
        listener = self.create_listener(self.FAKE_UUID_1, 80,
                                        provisioning_status=constants.ACTIVE)
        self.listener_repo.prov_status_active_if_not_error(self.session,
                                                           listener.id)
        self.session.commit()
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertEqual(constants.ACTIVE, new_listener.provisioning_status)

    def test_prov_status_active_if_not_error_error(self):
        listener = self.create_listener(self.FAKE_UUID_1, 80,
                                        provisioning_status=constants.ERROR)
        self.listener_repo.prov_status_active_if_not_error(self.session,
                                                           listener.id)
        self.session.commit()
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertEqual(constants.ERROR, new_listener.provisioning_status)

    def test_prov_status_active_if_not_error_pending_update(self):
        listener = self.create_listener(
            self.FAKE_UUID_1, 80, provisioning_status=constants.PENDING_UPDATE)
        self.listener_repo.prov_status_active_if_not_error(self.session,
                                                           listener.id)
        self.session.commit()
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertEqual(constants.ACTIVE, new_listener.provisioning_status)

    def test_prov_status_active_if_not_error_bogus_listener(self):
        listener = self.create_listener(
            self.FAKE_UUID_1, 80, provisioning_status=constants.PENDING_UPDATE)
        # Should not raise an exception nor change any status
        self.listener_repo.prov_status_active_if_not_error(self.session,
                                                           'bogus_id')
        self.session.commit()
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertEqual(constants.PENDING_UPDATE,
                         new_listener.provisioning_status)


class ListenerStatisticsRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super().setUp()
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
        self.session.commit()

    def create_listener_stats(self, listener_id, amphora_id):
        stats = self.listener_stats_repo.create(
            self.session, listener_id=listener_id, amphora_id=amphora_id,
            bytes_in=1, bytes_out=1,
            active_connections=1, total_connections=1, request_errors=1)
        self.session.commit()
        return stats

    def test_get(self):
        stats = self.create_listener_stats(self.listener.id, self.amphora.id)
        new_stats = self.listener_stats_repo.get(self.session,
                                                 listener_id=stats.listener_id)
        self.assertIsInstance(new_stats, data_models.ListenerStatistics)
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
        self.session.commit()
        new_stats = self.listener_stats_repo.get(self.session,
                                                 listener_id=stats.listener_id)
        self.assertIsInstance(new_stats, data_models.ListenerStatistics)
        self.assertEqual(stats.listener_id, new_stats.listener_id)

    def test_delete(self):
        stats = self.create_listener_stats(self.listener.id, self.amphora.id)
        self.listener_stats_repo.delete(self.session,
                                        listener_id=stats.listener_id)
        self.session.commit()
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
        stats_obj = data_models.ListenerStatistics(
            listener_id=self.listener.id,
            amphora_id=self.amphora.id,
            bytes_in=bytes_in,
            bytes_out=bytes_out,
            active_connections=active_conns,
            total_connections=total_conns,
            request_errors=request_errors
        )
        self.listener_stats_repo.replace(self.session, stats_obj)
        self.session.commit()
        obj = self.listener_stats_repo.get(self.session,
                                           listener_id=self.listener.id)
        self.assertIsNotNone(obj)
        self.assertEqual(self.listener.id, obj.listener_id)
        self.assertEqual(self.amphora.id, obj.amphora_id)
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
        stats_obj_2 = data_models.ListenerStatistics(
            listener_id=self.listener.id,
            amphora_id=self.amphora.id,
            bytes_in=bytes_in_2,
            bytes_out=bytes_out_2,
            active_connections=active_conns_2,
            total_connections=total_conns_2,
            request_errors=request_errors_2
        )
        self.listener_stats_repo.replace(self.session, stats_obj_2)
        self.session.commit()
        obj = self.listener_stats_repo.get(self.session,
                                           listener_id=self.listener.id)
        self.assertIsNotNone(obj)
        self.assertEqual(self.listener.id, obj.listener_id)
        self.assertEqual(self.amphora.id, obj.amphora_id)
        self.assertEqual(bytes_in_2, obj.bytes_in)
        self.assertEqual(bytes_out_2, obj.bytes_out)
        self.assertEqual(active_conns_2, obj.active_connections)
        self.assertEqual(total_conns_2, obj.total_connections)
        self.assertEqual(request_errors_2, obj.request_errors)

        # Test uses listener_id as amphora_id if not passed
        stats_obj = data_models.ListenerStatistics(
            listener_id=self.listener.id,
            bytes_in=bytes_in,
            bytes_out=bytes_out,
            active_connections=active_conns,
            total_connections=total_conns,
            request_errors=request_errors
        )
        self.listener_stats_repo.replace(self.session, stats_obj)
        self.session.commit()
        obj = self.listener_stats_repo.get(self.session,
                                           listener_id=self.listener.id,
                                           amphora_id=self.listener.id)
        self.assertIsNotNone(obj)
        self.assertEqual(self.listener.id, obj.listener_id)
        self.assertEqual(self.listener.id, obj.amphora_id)
        self.assertEqual(bytes_in, obj.bytes_in)
        self.assertEqual(bytes_out, obj.bytes_out)
        self.assertEqual(active_conns, obj.active_connections)
        self.assertEqual(total_conns, obj.total_connections)
        self.assertEqual(request_errors, obj.request_errors)

    def test_increment(self):
        # Test the create path
        bytes_in = random.randrange(1000000000)
        bytes_out = random.randrange(1000000000)
        active_conns = random.randrange(1000000000)
        total_conns = random.randrange(1000000000)
        request_errors = random.randrange(1000000000)
        self.assertIsNone(self.listener_stats_repo.get(
            self.session, listener_id=self.listener.id))
        delta_stats = data_models.ListenerStatistics(
            listener_id=self.listener.id,
            amphora_id=self.amphora.id,
            bytes_in=bytes_in,
            bytes_out=bytes_out,
            active_connections=active_conns,
            total_connections=total_conns,
            request_errors=request_errors
        )
        self.listener_stats_repo.increment(self.session, delta_stats)
        self.session.commit()
        obj = self.listener_stats_repo.get(self.session,
                                           listener_id=self.listener.id)
        self.assertIsNotNone(obj)
        self.assertEqual(self.listener.id, obj.listener_id)
        self.assertEqual(self.amphora.id, obj.amphora_id)
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
        delta_stats_2 = data_models.ListenerStatistics(
            listener_id=self.listener.id,
            amphora_id=self.amphora.id,
            bytes_in=bytes_in_2,
            bytes_out=bytes_out_2,
            active_connections=active_conns_2,
            total_connections=total_conns_2,
            request_errors=request_errors_2
        )
        self.listener_stats_repo.increment(self.session, delta_stats_2)
        self.session.commit()
        obj = self.listener_stats_repo.get(self.session,
                                           listener_id=self.listener.id)
        self.assertIsNotNone(obj)
        self.assertEqual(self.listener.id, obj.listener_id)
        self.assertEqual(self.amphora.id, obj.amphora_id)
        self.assertEqual(bytes_in + bytes_in_2, obj.bytes_in)
        self.assertEqual(bytes_out + bytes_out_2, obj.bytes_out)
        self.assertEqual(active_conns_2, obj.active_connections)  # not a delta
        self.assertEqual(total_conns + total_conns_2, obj.total_connections)
        self.assertEqual(request_errors + request_errors_2, obj.request_errors)

        # Test uses listener_id as amphora_id if not passed
        stats_obj = data_models.ListenerStatistics(
            listener_id=self.listener.id,
            bytes_in=bytes_in,
            bytes_out=bytes_out,
            active_connections=active_conns,
            total_connections=total_conns,
            request_errors=request_errors
        )
        self.listener_stats_repo.increment(self.session, stats_obj)
        self.session.commit()
        obj = self.listener_stats_repo.get(self.session,
                                           listener_id=self.listener.id,
                                           amphora_id=self.listener.id)
        self.assertIsNotNone(obj)
        self.assertEqual(self.listener.id, obj.listener_id)
        self.assertEqual(self.listener.id, obj.amphora_id)
        self.assertEqual(bytes_in, obj.bytes_in)
        self.assertEqual(bytes_out, obj.bytes_out)
        self.assertEqual(active_conns, obj.active_connections)
        self.assertEqual(total_conns, obj.total_connections)
        self.assertEqual(request_errors, obj.request_errors)


class HealthMonitorRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super().setUp()
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
        self.session.commit()

    def create_health_monitor(self, hm_id, pool_id):
        health_monitor = self.hm_repo.create(
            self.session, type=constants.HEALTH_MONITOR_HTTP, id=hm_id,
            pool_id=pool_id, delay=1, timeout=1, fall_threshold=1,
            rise_threshold=1, http_method="POST",
            url_path="http://localhost:80/index.php",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            expected_codes="200", enabled=True, tags=['test_tag'])
        self.session.commit()
        self.assertEqual(hm_id, health_monitor.id)
        return health_monitor

    def test_get(self):
        hm = self.create_health_monitor(self.FAKE_UUID_3, self.pool.id)
        new_hm = self.hm_repo.get(self.session, id=hm.id)
        self.assertIsInstance(new_hm, data_models.HealthMonitor)
        self.assertEqual(hm.id, new_hm.id)
        self.assertEqual(hm.pool_id, new_hm.pool_id)
        self.assertEqual(hm.type, new_hm.type)

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
        self.session.commit()
        new_hm = self.hm_repo.get(self.session, id=hm.id)
        self.assertEqual(delay_change, new_hm.delay)

    def test_delete(self):
        hm = self.create_health_monitor(self.FAKE_UUID_3, self.pool.id)
        self.hm_repo.delete(self.session, id=hm.id)
        self.session.commit()
        self.assertIsNone(self.hm_repo.get(self.session, id=hm.id))
        new_pool = self.pool_repo.get(self.session, id=self.pool.id)
        self.assertIsNotNone(new_pool)
        self.assertIsNone(new_pool.health_monitor)


class LoadBalancerRepositoryTest(BaseRepositoryTest):

    def create_loadbalancer(self, lb_id, **overrides):
        settings = dict(
            id=lb_id,
            project_id=self.FAKE_UUID_2, name="lb_name",
            description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            enabled=True, tags=['test_tag'],
        )
        settings.update(**overrides)
        lb = self.lb_repo.create(self.session, **settings)
        self.session.commit()
        return lb

    def test_get(self):
        lb = self.create_loadbalancer(self.FAKE_UUID_1)
        new_lb = self.lb_repo.get(self.session, id=lb.id)
        self.assertIsInstance(new_lb, data_models.LoadBalancer)
        self.assertEqual(lb.id, new_lb.id)
        self.assertEqual(lb.project_id, new_lb.project_id)

    def test_get_all(self):
        lb_one = self.create_loadbalancer(self.FAKE_UUID_1)
        lb_two = self.create_loadbalancer(self.FAKE_UUID_3)
        lb_list, _ = self.lb_repo.get_all(self.session,
                                          project_id=self.FAKE_UUID_2)
        self.assertEqual(2, len(lb_list))
        self.assertEqual(lb_one.id, lb_list[0].id)
        self.assertEqual(lb_one.project_id, lb_list[0].project_id)
        self.assertEqual(lb_two.id, lb_list[1].id)
        self.assertEqual(lb_two.project_id, lb_list[1].project_id)

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
        self.session.commit()
        new_lb = self.lb_repo.get(self.session, id=lb.id)
        self.assertEqual(name_change, new_lb.name)

    def test_delete(self):
        lb = self.create_loadbalancer(self.FAKE_UUID_1)
        self.lb_repo.delete(self.session, id=lb.id)
        self.session.commit()
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
        self.assertEqual(amphora.id, new_lb.amphorae[0].id)
        self.assertEqual(amphora.load_balancer_id,
                         new_lb.amphorae[0].load_balancer_id)
        self.assertEqual(amphora.compute_id, new_lb.amphorae[0].compute_id)
        self.lb_repo.delete(self.session, id=new_lb.id)
        self.session.commit()
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
        self.session.commit()
        amphora_2 = self.amphora_repo.create(self.session, id=self.FAKE_UUID_3,
                                             load_balancer_id=lb.id,
                                             compute_id=self.FAKE_UUID_3,
                                             lb_network_ip=self.FAKE_IP,
                                             vrrp_ip=self.FAKE_IP,
                                             status=constants.ACTIVE)
        self.session.commit()
        new_lb = self.lb_repo.get(self.session, id=lb.id)
        self.assertIsNotNone(new_lb)
        self.assertEqual(2, len(new_lb.amphorae))
        amphora_ids = [amp.id for amp in new_lb.amphorae]
        self.assertIn(amphora_1.id, amphora_ids)
        self.assertIn(amphora_2.id, amphora_ids)
        self.lb_repo.delete(self.session, id=new_lb.id)
        self.session.commit()
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
        self.session.commit()
        new_lb = self.lb_repo.get(self.session, id=lb.id)
        self.assertIsNotNone(new_lb)
        self.assertIsNotNone(new_lb.vip)
        self.assertEqual(vip, new_lb.vip)
        self.lb_repo.delete(self.session, id=new_lb.id)
        self.session.commit()
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
        self.session.commit()
        new_lb = self.lb_repo.get(self.session, id=lb.id)
        self.assertIsNotNone(new_lb)
        self.assertEqual(1, len(new_lb.listeners))
        self.assertEqual(listener.id, new_lb.listeners[0].id)
        self.assertEqual(listener.load_balancer_id,
                         new_lb.listeners[0].load_balancer_id)
        self.assertEqual(listener.project_id, new_lb.listeners[0].project_id)
        self.lb_repo.delete(self.session, id=new_lb.id)
        self.session.commit()
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
        self.session.commit()
        listener_2 = self.listener_repo.create(
            self.session, id=self.FAKE_UUID_3, project_id=self.FAKE_UUID_2,
            name="listener_name", description="listener_description",
            load_balancer_id=lb.id, protocol=constants.PROTOCOL_HTTPS,
            protocol_port=443, connection_limit=1,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        self.session.commit()
        new_lb = self.lb_repo.get(self.session, id=lb.id)
        self.assertIsNotNone(new_lb)
        self.assertEqual(2, len(new_lb.listeners))
        listener_ids = [lstnr.id for lstnr in new_lb.listeners]
        self.assertIn(listener_1.id, listener_ids)
        self.assertIn(listener_2.id, listener_ids)
        self.lb_repo.delete(self.session, id=new_lb.id)
        self.session.commit()
        self.assertIsNone(self.lb_repo.get(self.session, id=lb.id))
        self.assertIsNone(self.listener_repo.get(self.session,
                                                 id=listener_1.id))
        self.assertIsNone(self.listener_repo.get(self.session,
                                                 id=listener_2.id))

    def test_delete_with_all_children(self):
        lb = self.create_loadbalancer(self.FAKE_UUID_1)
        self.session.commit()
        amphora = self.amphora_repo.create(self.session, id=self.FAKE_UUID_1,
                                           load_balancer_id=lb.id,
                                           compute_id=self.FAKE_UUID_3,
                                           lb_network_ip=self.FAKE_IP,
                                           status=constants.ACTIVE)
        self.session.commit()
        vip = self.vip_repo.create(self.session, load_balancer_id=lb.id,
                                   ip_address="192.0.2.1")
        self.session.commit()
        listener = self.listener_repo.create(
            self.session, id=self.FAKE_UUID_1, project_id=self.FAKE_UUID_2,
            name="listener_name", description="listener_description",
            load_balancer_id=lb.id, protocol=constants.PROTOCOL_HTTP,
            protocol_port=80, connection_limit=1,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        self.session.commit()
        new_lb = self.lb_repo.get(self.session, id=lb.id)
        self.assertIsNotNone(new_lb)
        self.assertIsNotNone(new_lb.vip)
        self.assertEqual(vip, new_lb.vip)
        self.assertEqual(1, len(new_lb.amphorae))
        self.assertEqual(1, len(new_lb.listeners))
        self.assertEqual(amphora.id, new_lb.amphorae[0].id)
        self.assertEqual(amphora.load_balancer_id,
                         new_lb.amphorae[0].load_balancer_id)
        self.assertEqual(amphora.compute_id, new_lb.amphorae[0].compute_id)
        self.assertEqual(listener.id, new_lb.listeners[0].id)
        self.assertEqual(listener.name, new_lb.listeners[0].name)
        self.assertEqual(listener.protocol, new_lb.listeners[0].protocol)
        self.assertEqual(listener.protocol_port,
                         new_lb.listeners[0].protocol_port)
        self.lb_repo.delete(self.session, id=new_lb.id)
        self.session.commit()
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
        self.session.commit()
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
        self.session.commit()
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
        self.session.commit()
        self.lb_repo.test_and_set_provisioning_status(
            self.session, lb_id, constants.PENDING_UPDATE)
        self.session.commit()
        lb = self.lb_repo.get(self.session, id=lb_id)
        self.assertEqual(constants.PENDING_UPDATE, lb.provisioning_status)

    def test_test_and_set_provisioning_status_error_on_delete(self):
        lb_id = uuidutils.generate_uuid()
        self.lb_repo.create(self.session, id=lb_id,
                            provisioning_status=constants.ERROR,
                            operating_status=constants.OFFLINE,
                            enabled=True)
        self.session.commit()
        self.lb_repo.test_and_set_provisioning_status(
            self.session, lb_id, constants.PENDING_DELETE)
        self.session.commit()
        lb = self.lb_repo.get(self.session, id=lb_id)
        self.assertEqual(constants.PENDING_DELETE, lb.provisioning_status)

    def test_test_and_set_provisioning_status_concurrent(self):
        lb_id = uuidutils.generate_uuid()
        self.lb_repo.create(self.session, id=lb_id,
                            provisioning_status=constants.ACTIVE,
                            operating_status=constants.ONLINE,
                            enabled=True)
        self.session.commit()

        # Create a concurrent session
        session2 = self._get_db_engine_session()[1]

        # Load LB into session2's identity map
        session2.query(db_models.LoadBalancer).filter_by(
            id=lb_id).one()

        # Update provisioning status in lock_session1
        self.lb_repo.test_and_set_provisioning_status(
            self.session, lb_id, constants.PENDING_UPDATE)
        self.session.commit()

        # Assert concurrent updates are rejected
        self.assertFalse(self.lb_repo.test_and_set_provisioning_status(
            self.session, lb_id, constants.PENDING_UPDATE))

    def test_set_status_for_failover_immutable(self):
        lb_id = uuidutils.generate_uuid()
        self.lb_repo.create(self.session, id=lb_id,
                            provisioning_status=constants.PENDING_CREATE,
                            operating_status=constants.OFFLINE,
                            enabled=True)
        self.session.commit()
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
        self.session.commit()
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
        self.session.commit()
        self.lb_repo.set_status_for_failover(
            self.session, lb_id, constants.PENDING_UPDATE)
        self.session.commit()
        lb = self.lb_repo.get(self.session, id=lb_id)
        self.assertEqual(constants.PENDING_UPDATE, lb.provisioning_status)

    def test_set_status_for_failover_error(self):
        lb_id = uuidutils.generate_uuid()
        self.lb_repo.create(self.session, id=lb_id,
                            provisioning_status=constants.ERROR,
                            operating_status=constants.OFFLINE,
                            enabled=True)
        self.session.commit()
        self.lb_repo.set_status_for_failover(
            self.session, lb_id, constants.PENDING_UPDATE)
        self.session.commit()
        lb = self.lb_repo.get(self.session, id=lb_id)
        self.assertEqual(constants.PENDING_UPDATE, lb.provisioning_status)

    def test_get_all_deleted_expiring_load_balancer(self):
        exp_age = datetime.timedelta(seconds=self.FAKE_EXP_AGE)
        updated_at = datetime.datetime.utcnow() - exp_age
        lb1 = self.create_loadbalancer(
            self.FAKE_UUID_1, updated_at=updated_at,
            provisioning_status=constants.DELETED)
        lb2 = self.create_loadbalancer(
            self.FAKE_UUID_2, provisioning_status=constants.DELETED)

        expiring_ids = self.lb_repo.get_all_deleted_expiring(
            self.session, exp_age=exp_age)
        self.assertIn(lb1.id, expiring_ids)
        self.assertNotIn(lb2.id, expiring_ids)


class VipRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super().setUp()
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
        self.assertIsInstance(new_vip, data_models.Vip)
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

    def test_create_ipv6(self):
        vip = self.vip_repo.create(self.session, load_balancer_id=self.lb.id,
                                   ip_address="2001:DB8::10")
        self.assertEqual(self.lb.id, vip.load_balancer_id)
        self.assertEqual("2001:DB8::10", vip.ip_address)

    # Note: This test is using the unique local address range to
    #       validate that we handle a fully expaned IP address properly.
    #       This is not possible with the documentation/testnet range.
    def test_create_ipv6_full(self):
        vip = self.vip_repo.create(
            self.session, load_balancer_id=self.lb.id,
            ip_address="fdff:ffff:ffff:ffff:ffff:ffff:ffff:ffff")
        self.assertEqual(self.lb.id, vip.load_balancer_id)
        self.assertEqual("fdff:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
                         vip.ip_address)


class SNIRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super().setUp()
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
        self.assertIsInstance(new_sni, data_models.SNI)
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
        super().setUp()
        self.lb = self.lb_repo.create(
            self.session, id=self.FAKE_UUID_1, project_id=self.FAKE_UUID_2,
            name="lb_name", description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        self.session.commit()

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
        self.session.commit()
        return amphora

    def test_get(self):
        amphora = self.create_amphora(self.FAKE_UUID_1)
        new_amphora = self.amphora_repo.get(self.session, id=amphora.id)
        self.assertIsInstance(new_amphora, data_models.Amphora)
        self.assertEqual(amphora.id, new_amphora.id)
        self.assertEqual(amphora.load_balancer_id,
                         new_amphora.load_balancer_id)
        self.assertEqual(amphora.compute_id, new_amphora.compute_id)

    def test_count(self):
        comp_id = uuidutils.generate_uuid()
        self.create_amphora(self.FAKE_UUID_1, compute_id=comp_id)
        self.create_amphora(self.FAKE_UUID_2, compute_id=comp_id,
                            status=constants.DELETED)
        amp_count = self.amphora_repo.count(self.session, compute_id=comp_id)
        self.assertEqual(2, amp_count)

    def test_count_not_deleted(self):
        comp_id = uuidutils.generate_uuid()
        self.create_amphora(self.FAKE_UUID_1, compute_id=comp_id)
        self.create_amphora(self.FAKE_UUID_2, compute_id=comp_id,
                            status=constants.DELETED)
        amp_count = self.amphora_repo.count(self.session, compute_id=comp_id,
                                            show_deleted=False)
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
        self.assertIsInstance(new_amphora.load_balancer,
                              data_models.LoadBalancer)

    def test_delete_amphora_with_load_balancer(self):
        amphora = self.create_amphora(self.FAKE_UUID_1)
        self.amphora_repo.associate(self.session, self.lb.id, amphora.id)
        self.session.commit()
        self.amphora_repo.delete(self.session, id=amphora.id)
        self.session.commit()
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
        self.assertIsInstance(new_amphora, data_models.Amphora)

    def test_get_lb_for_amphora(self):
        # TODO(bzhao) this test will raise error as there are more than 64
        # tables in a Join statement in sqlite env. This is a new issue when
        # we introduce resources tags and client certificates, both of them
        # are 1:1 relationship. But we can image that if we have many
        # associated loadbalancer subresources, such as listeners, pools,
        # members and l7 resources. Even though, we don't have tags and
        # client certificates features, we will still hit this issue in
        # sqlite env.
        self.skipTest("No idea how this should work yet")
        amphora = self.create_amphora(self.FAKE_UUID_1)
        self.amphora_repo.associate(self.session, self.lb.id, amphora.id)
        self.session.commit()
        lb = self.amphora_repo.get_lb_for_amphora(self.session, amphora.id)
        self.assertIsNotNone(lb)
        self.assertEqual(self.lb, lb)

    def test_get_all_deleted_expiring_amphora(self):
        exp_age = datetime.timedelta(seconds=self.FAKE_EXP_AGE)
        updated_at = datetime.datetime.utcnow() - exp_age
        amphora1 = self.create_amphora(
            self.FAKE_UUID_1, updated_at=updated_at, status=constants.DELETED)
        amphora2 = self.create_amphora(
            self.FAKE_UUID_2, status=constants.DELETED)

        expiring_ids = self.amphora_repo.get_all_deleted_expiring(
            self.session, exp_age=exp_age)
        self.assertIn(amphora1.id, expiring_ids)
        self.assertNotIn(amphora2.id, expiring_ids)

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

    def test_get_cert_expired_amphora_deleted(self):
        amphora = self.create_amphora(self.FAKE_UUID_3)
        expiration = datetime.datetime.utcnow() + datetime.timedelta(seconds=1)
        self.amphora_repo.update(self.session, amphora.id,
                                 status=constants.DELETED,
                                 cert_expiration=expiration)

        cert_expired_amphora = self.amphora_repo.get_cert_expiring_amphora(
            self.session)

        self.assertIsNone(cert_expired_amphora)

    def test_get_lb_for_health_update(self):
        amphora1 = self.create_amphora(self.FAKE_UUID_1)
        amphora2 = self.create_amphora(self.FAKE_UUID_3)
        self.amphora_repo.associate(self.session, self.lb.id, amphora1.id)
        self.amphora_repo.associate(self.session, self.lb.id, amphora2.id)
        self.session.commit()

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
        self.session.commit()

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

        listener_ref = {listener.id: {'operating_status': constants.ONLINE,
                                      'protocol': constants.PROTOCOL_HTTP,
                                      'enabled': 1}}
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
        self.session.commit()

        member2 = self.member_repo.create(self.session, id=self.FAKE_UUID_7,
                                          project_id=self.FAKE_UUID_2,
                                          pool_id=pool.id,
                                          ip_address="192.0.2.21",
                                          protocol_port=80, enabled=True,
                                          provisioning_status=constants.ACTIVE,
                                          operating_status=constants.OFFLINE,
                                          backup=False)
        self.session.commit()

        member_ref = {member1.id: {'operating_status': constants.ONLINE},
                      member2.id: {'operating_status': constants.OFFLINE}}
        lb_ref['pools'][pool.id]['members'] = member_ref

        # Test with an LB, pool, listener, and members
        lb = self.amphora_repo.get_lb_for_health_update(self.session,
                                                        self.FAKE_UUID_1)
        self.assertEqual(lb_ref, lb)

    def test_and_set_status_for_delete(self):
        # Normal path
        amphora = self.create_amphora(self.FAKE_UUID_1,
                                      status=constants.AMPHORA_READY)
        self.amphora_repo.test_and_set_status_for_delete(self.session,
                                                         amphora.id)
        new_amphora = self.amphora_repo.get(self.session, id=amphora.id)
        self.assertEqual(constants.PENDING_DELETE, new_amphora.status)

        # Test deleted path
        amphora = self.create_amphora(self.FAKE_UUID_2,
                                      status=constants.DELETED)
        self.assertRaises(sa_exception.NoResultFound,
                          self.amphora_repo.test_and_set_status_for_delete,
                          self.session, amphora.id)

        # Test in use path
        amphora = self.create_amphora(self.FAKE_UUID_3,
                                      status=constants.AMPHORA_ALLOCATED)
        self.assertRaises(exceptions.ImmutableObject,
                          self.amphora_repo.test_and_set_status_for_delete,
                          self.session, amphora.id)


class AmphoraHealthRepositoryTest(BaseRepositoryTest):
    def setUp(self):
        super().setUp()
        self._fake_ip_gen = (self.FAKE_IP + str(ip_end) for ip_end in
                             range(100))
        self.amphora = self.amphora_repo.create(self.session,
                                                id=self.FAKE_UUID_1,
                                                compute_id=self.FAKE_UUID_3,
                                                status=constants.ACTIVE,
                                                lb_network_ip=self.FAKE_IP)

    def create_amphora(self, amphora_id, **overrides):
        fake_ip = next(self._fake_ip_gen)
        settings = {
            'id': amphora_id,
            'compute_id': uuidutils.generate_uuid(),
            'status': constants.ACTIVE,
            'lb_network_ip': fake_ip,
            'vrrp_ip': fake_ip,
            'ha_ip': fake_ip,
            'role': constants.ROLE_MASTER,
            'cert_expiration': datetime.datetime.utcnow(),
            'cert_busy': False
        }
        settings.update(overrides)
        amphora = self.amphora_repo.create(self.session, **settings)
        return amphora

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

        self.assertIsInstance(new_amphora_health, data_models.AmphoraHealth)
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

        uuid = uuidutils.generate_uuid()
        self.create_amphora(uuid)
        self.amphora_repo.update(self.session, uuid,
                                 status=constants.AMPHORA_ALLOCATED)
        self.create_amphora_health(uuid)
        stale_amphora = self.amphora_health_repo.get_stale_amphora(
            self.session)
        self.assertEqual(uuid, stale_amphora.amphora_id)

    def test_get_stale_amphora_past_threshold(self):
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='health_manager', failover_threshold=3)

        stale_amphora = self.amphora_health_repo.get_stale_amphora(
            self.session)
        self.assertIsNone(stale_amphora)

        # Two stale amphora expected, should return that amp
        # These will go into failover and be marked "busy"
        uuids = []
        for _ in range(2):
            uuid = uuidutils.generate_uuid()
            uuids.append(uuid)
            self.create_amphora(uuid)
            self.amphora_repo.update(self.session, uuid,
                                     status=constants.AMPHORA_ALLOCATED)
            self.create_amphora_health(uuid)
            stale_amphora = self.amphora_health_repo.get_stale_amphora(
                self.session)
            self.assertIn(stale_amphora.amphora_id, uuids)

        # Creating more stale amphorae should return no amps (past threshold)
        stale_uuids = []
        for _ in range(4):
            uuid = uuidutils.generate_uuid()
            stale_uuids.append(uuid)
            self.create_amphora(uuid)
            self.amphora_repo.update(self.session, uuid,
                                     status=constants.AMPHORA_ALLOCATED)
            self.create_amphora_health(uuid)
        stale_amphora = self.amphora_health_repo.get_stale_amphora(
            self.session)
        self.assertIsNone(stale_amphora)
        num_fo_stopped = self.session.query(db_models.Amphora).filter(
            db_models.Amphora.status == constants.AMPHORA_FAILOVER_STOPPED
        ).count()
        # Note that the two amphora started failover, so are "busy" and
        # should not be marked FAILOVER_STOPPED.
        self.assertEqual(4, num_fo_stopped)

        # One recovered, but still over threshold
        # Two "busy", One fully healthy, three in FAILOVER_STOPPED
        amp = self.session.query(db_models.AmphoraHealth).filter_by(
            amphora_id=stale_uuids[2]).first()
        amp.last_update = datetime.datetime.utcnow()
        self.session.flush()
        stale_amphora = self.amphora_health_repo.get_stale_amphora(
            self.session)
        self.assertIsNone(stale_amphora)
        num_fo_stopped = self.session.query(db_models.Amphora).filter(
            db_models.Amphora.status == constants.AMPHORA_FAILOVER_STOPPED
        ).count()
        self.assertEqual(3, num_fo_stopped)

        # Another one recovered, now below threshold
        # Two are "busy", Two are fully healthy, Two are in FAILOVER_STOPPED
        amp = self.session.query(db_models.AmphoraHealth).filter_by(
            amphora_id=stale_uuids[3]).first()
        amp.last_update = datetime.datetime.utcnow()
        stale_amphora = self.amphora_health_repo.get_stale_amphora(
            self.session)
        self.assertIsNotNone(stale_amphora)
        num_fo_stopped = self.session.query(db_models.Amphora).filter(
            db_models.Amphora.status == constants.AMPHORA_FAILOVER_STOPPED
        ).count()
        self.assertEqual(2, num_fo_stopped)

        # After error recovery all amps should be allocated again
        now = datetime.datetime.utcnow()
        for amp in self.session.query(db_models.AmphoraHealth).all():
            amp.last_update = now
        stale_amphora = self.amphora_health_repo.get_stale_amphora(
            self.session)
        self.assertIsNone(stale_amphora)
        num_allocated = self.session.query(db_models.Amphora).filter(
            db_models.Amphora.status == constants.AMPHORA_ALLOCATED
        ).count()
        self.assertEqual(5, num_allocated)

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
        super().setUp()
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
        super().setUp()
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
            operating_status=constants.ONLINE, enabled=True, tags=['test_tag'])
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
        self.assertIsInstance(new_l7policy, data_models.L7Policy)
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

    def test_l7policy_create_no_listener_id(self):
        self.assertRaises(
            db_exception.DBError, self.l7policy_repo.create,
            self.session, action=constants.L7POLICY_ACTION_REJECT,
            operating_status=constants.ONLINE,
            provisioning_status=constants.ACTIVE,
            enabled=True)

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
        self.session.commit()
        new_l7policy = self.l7policy_repo.get(self.session, id=l7policy.id)
        self.assertIsNone(new_l7policy.redirect_pool_id)
        self.l7policy_repo.update(
            self.session, id=l7policy.id,
            redirect_pool_id=pool.id)
        self.session.commit()
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
        self.session.commit()
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
        self.session.commit()
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
        super().setUp()
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
            operating_status=constants.ONLINE, enabled=enabled,
            tags=['test_tag'])
        return l7rule

    def test_get(self):
        l7rule = self.create_l7rule(uuidutils.generate_uuid(),
                                    self.l7policy.id)
        new_l7rule = self.l7rule_repo.get(self.session, id=l7rule.id)
        self.assertIsInstance(new_l7rule, data_models.L7Rule)
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

    def test_l7rule_create_wihout_l7policy_id(self):
        self.assertRaises(
            db_exception.DBError, self.l7rule_repo.create,
            self.session, id=None, type=constants.L7RULE_TYPE_PATH,
            compare_type=constants.L7RULE_COMPARE_TYPE_CONTAINS,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE,
            value='something',
            enabled=True)

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
        super().setUp()

    def update_quotas(self, project_id, load_balancer=20, listener=20, pool=20,
                      health_monitor=20, member=20, l7policy=20, l7rule=20):
        quota = {'load_balancer': load_balancer,
                 'listener': listener,
                 'pool': pool,
                 'health_monitor': health_monitor,
                 'member': member,
                 'l7policy': l7policy,
                 'l7rule': l7rule}
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
        self.assertEqual(expected.l7policy,
                         observed.l7policy)
        self.assertEqual(expected.l7rule,
                         observed.l7rule)

    def test_get(self):
        expected = self.update_quotas(self.FAKE_UUID_1)
        observed = self.quota_repo.get(self.session,
                                       project_id=self.FAKE_UUID_1)
        self.assertIsInstance(observed, data_models.Quotas)
        self._compare(expected, observed)

    def test_update(self):
        first_expected = self.update_quotas(self.FAKE_UUID_1)
        first_observed = self.quota_repo.get(self.session,
                                             project_id=self.FAKE_UUID_1)
        second_expected = self.update_quotas(self.FAKE_UUID_1, load_balancer=1)
        second_observed = self.quota_repo.get(self.session,
                                              project_id=self.FAKE_UUID_1)
        self.assertIsInstance(first_expected, data_models.Quotas)
        self._compare(first_expected, first_observed)
        self.assertIsInstance(second_expected, data_models.Quotas)
        self._compare(second_expected, second_observed)
        self.assertIsNot(first_expected.load_balancer,
                         second_expected.load_balancer)

    def test_delete(self):
        expected = self.update_quotas(self.FAKE_UUID_1)
        observed = self.quota_repo.get(self.session,
                                       project_id=self.FAKE_UUID_1)
        self.assertIsInstance(observed, data_models.Quotas)
        self._compare(expected, observed)
        self.quota_repo.delete(self.session, self.FAKE_UUID_1)
        observed = self.quota_repo.get(self.session,
                                       project_id=self.FAKE_UUID_1)
        self.assertIsNone(observed.health_monitor)
        self.assertIsNone(observed.load_balancer)
        self.assertIsNone(observed.listener)
        self.assertIsNone(observed.member)
        self.assertIsNone(observed.pool)
        self.assertIsNone(observed.l7policy)
        self.assertIsNone(observed.l7rule)

    def test_delete_non_existent(self):
        self.assertRaises(exceptions.NotFound,
                          self.quota_repo.delete,
                          self.session, 'bogus')


class FlavorProfileRepositoryTest(BaseRepositoryTest):

    def create_flavor_profile(self, fp_id):
        fp = self.flavor_profile_repo.create(
            self.session, id=fp_id, name="fp1", provider_name='pr1',
            flavor_data="{'image': 'unbuntu'}")
        return fp

    def test_get(self):
        fp = self.create_flavor_profile(fp_id=self.FAKE_UUID_1)
        new_fp = self.flavor_profile_repo.get(self.session, id=fp.id)
        self.assertIsInstance(new_fp, data_models.FlavorProfile)
        self.assertEqual(fp, new_fp)

    def test_get_all(self):
        fp1 = self.create_flavor_profile(fp_id=self.FAKE_UUID_1)
        fp2 = self.create_flavor_profile(fp_id=self.FAKE_UUID_2)
        fp_list, _ = self.flavor_profile_repo.get_all(
            self.session,
            query_options=defer(db_models.FlavorProfile.name))
        self.assertIsInstance(fp_list, list)
        self.assertEqual(2, len(fp_list))
        self.assertEqual(fp1, fp_list[0])
        self.assertEqual(fp2, fp_list[1])

    def test_create(self):
        fp = self.create_flavor_profile(fp_id=self.FAKE_UUID_1)
        self.assertIsInstance(fp, data_models.FlavorProfile)
        self.assertEqual(self.FAKE_UUID_1, fp.id)
        self.assertEqual("fp1", fp.name)

    def test_delete(self):
        fp = self.create_flavor_profile(fp_id=self.FAKE_UUID_1)
        self.flavor_profile_repo.delete(self.session, id=fp.id)
        self.assertIsNone(self.flavor_profile_repo.get(
            self.session, id=fp.id))


class FlavorRepositoryTest(BaseRepositoryTest):

    PROVIDER_NAME = 'provider1'

    def create_flavor_profile(self):
        fp = self.flavor_profile_repo.create(
            self.session, id=uuidutils.generate_uuid(),
            name="fp1", provider_name=self.PROVIDER_NAME,
            flavor_data='{"image": "ubuntu"}')
        self.session.commit()
        return fp

    def create_flavor(self, flavor_id, name):
        fp = self.create_flavor_profile()
        flavor = self.flavor_repo.create(
            self.session, id=flavor_id, name=name,
            flavor_profile_id=fp.id, description='test',
            enabled=True)
        self.session.commit()
        return flavor

    def test_get(self):
        flavor = self.create_flavor(flavor_id=self.FAKE_UUID_2, name='flavor')
        new_flavor = self.flavor_repo.get(self.session, id=flavor.id)
        self.assertIsInstance(new_flavor, data_models.Flavor)
        self.assertEqual(flavor.id, new_flavor.id)
        self.assertEqual(flavor.name, new_flavor.name)

    def test_get_all(self):
        fl1 = self.create_flavor(flavor_id=self.FAKE_UUID_2, name='flavor1')
        fl2 = self.create_flavor(flavor_id=self.FAKE_UUID_3, name='flavor2')
        fl_list, _ = self.flavor_repo.get_all(
            self.session,
            query_options=defer(db_models.Flavor.enabled))
        self.assertIsInstance(fl_list, list)
        self.assertEqual(2, len(fl_list))
        self.assertEqual(fl1.id, fl_list[0].id)
        self.assertEqual(fl1.name, fl_list[0].name)
        self.assertEqual(fl2.id, fl_list[1].id)
        self.assertEqual(fl2.name, fl_list[1].name)

    def test_create(self):
        fl = self.create_flavor(flavor_id=self.FAKE_UUID_2, name='fl1')
        self.assertIsInstance(fl, data_models.Flavor)
        self.assertEqual(self.FAKE_UUID_2, fl.id)
        self.assertEqual("fl1", fl.name)

    def test_delete(self):
        fl = self.create_flavor(flavor_id=self.FAKE_UUID_2, name='fl1')
        self.flavor_repo.delete(self.session, id=fl.id)
        self.assertIsNone(self.flavor_repo.get(
            self.session, id=fl.id))

    def test_get_flavor_metadata_dict(self):
        ref_dict = {'image': 'ubuntu'}
        self.create_flavor(flavor_id=self.FAKE_UUID_2, name='fl1')
        flavor_metadata_dict = self.flavor_repo.get_flavor_metadata_dict(
            self.session, self.FAKE_UUID_2)
        self.assertEqual(ref_dict, flavor_metadata_dict)

        # Test missing flavor
        self.assertRaises(sa_exception.NoResultFound,
                          self.flavor_repo.get_flavor_metadata_dict,
                          self.session, self.FAKE_UUID_1)

    def test_get_flavor_provider(self):
        self.create_flavor(flavor_id=self.FAKE_UUID_2, name='fl1')
        provider_name = self.flavor_repo.get_flavor_provider(self.session,
                                                             self.FAKE_UUID_2)
        self.assertEqual(self.PROVIDER_NAME, provider_name)

        # Test missing flavor
        self.assertRaises(sa_exception.NoResultFound,
                          self.flavor_repo.get_flavor_provider,
                          self.session, self.FAKE_UUID_1)
