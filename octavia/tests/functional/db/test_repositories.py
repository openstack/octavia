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

from oslo_utils import uuidutils

from octavia.common import constants
from octavia.common import data_models as models
from octavia.db import repositories as repo
from octavia.tests.functional.db import base


class BaseRepositoryTest(base.OctaviaDBTestBase):

    FAKE_IP = "10.0.0.1"
    FAKE_UUID_1 = uuidutils.generate_uuid()
    FAKE_UUID_2 = uuidutils.generate_uuid()
    FAKE_UUID_3 = uuidutils.generate_uuid()
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

    def test_get_all_return_value(self):
        pool_list = self.pool_repo.get_all(self.session,
                                           tenant_id=self.FAKE_UUID_2)
        self.assertIsInstance(pool_list, list)
        lb_list = self.lb_repo.get_all(self.session,
                                       tenant_id=self.FAKE_UUID_2)
        self.assertIsInstance(lb_list, list)
        listener_list = self.listener_repo.get_all(self.session,
                                                   tenant_id=self.FAKE_UUID_2)
        self.assertIsInstance(listener_list, list)
        member_list = self.member_repo.get_all(self.session,
                                               tenant_id=self.FAKE_UUID_2)
        self.assertIsInstance(member_list, list)


class AllRepositoriesTest(base.OctaviaDBTestBase):

    def setUp(self):
        super(AllRepositoriesTest, self).setUp()
        self.repos = repo.Repositories()
        self.listener = self.repos.listener.create(
            self.session, protocol=constants.PROTOCOL_HTTP, protocol_port=80,
            enabled=True, provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE)

    def test_all_repos_has_correct_repos(self):
        repo_attr_names = ('load_balancer', 'vip', 'health_monitor',
                           'session_persistence', 'pool', 'member', 'listener',
                           'listener_stats', 'amphora', 'sni',
                           'amphorahealth')
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
            self.assertFalse(isinstance(possible_repo, repo.BaseRepository),
                             msg=message)

    def test_create_load_balancer_and_vip(self):
        lb = {'name': 'test1', 'description': 'desc1', 'enabled': True,
              'provisioning_status': constants.PENDING_UPDATE,
              'operating_status': constants.OFFLINE,
              'topology': constants.TOPOLOGY_ACTIVE_STANDBY}
        vip = {'ip_address': '10.0.0.1',
               'port_id': uuidutils.generate_uuid(),
               'subnet_id': uuidutils.generate_uuid()}
        lb_dm = self.repos.create_load_balancer_and_vip(self.session, lb, vip)
        lb_dm_dict = lb_dm.to_dict()
        del lb_dm_dict['vip']
        del lb_dm_dict['listeners']
        del lb_dm_dict['amphorae']
        del lb_dm_dict['tenant_id']
        self.assertEqual(lb, lb_dm_dict)
        vip_dm_dict = lb_dm.vip.to_dict()
        vip_dm_dict['load_balancer_id'] = lb_dm.id
        del vip_dm_dict['load_balancer']
        self.assertEqual(vip, vip_dm_dict)

    def test_create_pool_on_listener_without_sp(self):
        pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                'description': 'desc1',
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                'enabled': True, 'operating_status': constants.ONLINE}
        pool_dm = self.repos.create_pool_on_listener(self.session,
                                                     self.listener.id,
                                                     pool)
        pool_dm_dict = pool_dm.to_dict()
        del pool_dm_dict['members']
        del pool_dm_dict['health_monitor']
        del pool_dm_dict['session_persistence']
        del pool_dm_dict['listener']
        del pool_dm_dict['tenant_id']
        self.assertEqual(pool, pool_dm_dict)
        new_listener = self.repos.listener.get(self.session,
                                               id=self.listener.id)
        self.assertEqual(pool_dm.id, new_listener.default_pool_id)

    def test_create_pool_on_listener_with_sp(self):
        pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                'description': 'desc1',
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                'enabled': True, 'operating_status': constants.ONLINE}
        sp = {'type': constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              'cookie_name': 'cookie_monster'}
        pool_dm = self.repos.create_pool_on_listener(self.session,
                                                     self.listener.id,
                                                     pool, sp_dict=sp)
        pool_dm_dict = pool_dm.to_dict()
        del pool_dm_dict['members']
        del pool_dm_dict['health_monitor']
        del pool_dm_dict['session_persistence']
        del pool_dm_dict['listener']
        del pool_dm_dict['tenant_id']
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

    def test_update_pool_on_listener_without_sp(self):
        pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                'description': 'desc1',
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                'enabled': True, 'operating_status': constants.ONLINE}
        pool_dm = self.repos.create_pool_on_listener(self.session,
                                                     self.listener.id, pool)
        update_pool = {'protocol': constants.PROTOCOL_TCP, 'name': 'up_pool'}
        new_pool_dm = self.repos.update_pool_on_listener(
            self.session, pool_dm.id, update_pool, None)
        pool_dm_dict = new_pool_dm.to_dict()
        del pool_dm_dict['members']
        del pool_dm_dict['health_monitor']
        del pool_dm_dict['session_persistence']
        del pool_dm_dict['listener']
        del pool_dm_dict['tenant_id']
        pool.update(update_pool)
        self.assertEqual(pool, pool_dm_dict)
        self.assertIsNone(new_pool_dm.session_persistence)

    def test_update_pool_on_listener_with_existing_sp(self):
        pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                'description': 'desc1',
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                'enabled': True, 'operating_status': constants.ONLINE}
        sp = {'type': constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              'cookie_name': 'cookie_monster'}
        pool_dm = self.repos.create_pool_on_listener(self.session,
                                                     self.listener.id,
                                                     pool, sp_dict=sp)
        update_pool = {'protocol': constants.PROTOCOL_TCP, 'name': 'up_pool'}
        update_sp = {'type': constants.SESSION_PERSISTENCE_SOURCE_IP}
        new_pool_dm = self.repos.update_pool_on_listener(
            self.session, pool_dm.id, update_pool, update_sp)
        pool_dm_dict = new_pool_dm.to_dict()
        del pool_dm_dict['members']
        del pool_dm_dict['health_monitor']
        del pool_dm_dict['session_persistence']
        del pool_dm_dict['listener']
        del pool_dm_dict['tenant_id']
        pool.update(update_pool)
        self.assertEqual(pool, pool_dm_dict)
        sp_dm_dict = new_pool_dm.session_persistence.to_dict()
        del sp_dm_dict['pool']
        sp['pool_id'] = pool_dm.id
        sp.update(update_sp)
        self.assertEqual(sp, sp_dm_dict)

    def test_update_pool_on_listener_with_nonexisting_sp(self):
        pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                'description': 'desc1',
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                'enabled': True, 'operating_status': constants.ONLINE}
        pool_dm = self.repos.create_pool_on_listener(self.session,
                                                     self.listener.id,
                                                     pool)
        update_pool = {'protocol': constants.PROTOCOL_TCP, 'name': 'up_pool'}
        update_sp = {'type': constants.SESSION_PERSISTENCE_HTTP_COOKIE,
                     'cookie_name': 'monster_cookie'}
        new_pool_dm = self.repos.update_pool_on_listener(
            self.session, pool_dm.id, update_pool, update_sp)
        sp_dm_dict = new_pool_dm.session_persistence.to_dict()
        del sp_dm_dict['pool']
        update_sp['pool_id'] = pool_dm.id
        update_sp.update(update_sp)
        self.assertEqual(update_sp, sp_dm_dict)

    def test_update_pool_on_listener_with_nonexisting_sp_delete_sp(self):
        pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                'description': 'desc1',
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                'enabled': True, 'operating_status': constants.ONLINE}
        pool_dm = self.repos.create_pool_on_listener(self.session,
                                                     self.listener.id,
                                                     pool)
        update_pool = {'protocol': constants.PROTOCOL_TCP, 'name': 'up_pool'}
        new_pool_dm = self.repos.update_pool_on_listener(
            self.session, pool_dm.id, update_pool, None)
        self.assertIsNone(new_pool_dm.session_persistence)

    def test_update_pool_on_listener_with_existing_sp_delete_sp(self):
        pool = {'protocol': constants.PROTOCOL_HTTP, 'name': 'pool1',
                'description': 'desc1',
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                'enabled': True, 'operating_status': constants.ONLINE}
        sp = {'type': constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              'cookie_name': 'cookie_monster'}
        pool_dm = self.repos.create_pool_on_listener(self.session,
                                                     self.listener.id,
                                                     pool, sp_dict=sp)
        update_pool = {'protocol': constants.PROTOCOL_TCP, 'name': 'up_pool'}
        new_pool_dm = self.repos.update_pool_on_listener(
            self.session, pool_dm.id, update_pool, None)
        self.assertIsNone(new_pool_dm.session_persistence)


class PoolRepositoryTest(BaseRepositoryTest):

    def create_pool(self, pool_id, tenant_id):
        pool = self.pool_repo.create(
            self.session, id=pool_id, tenant_id=tenant_id, name="pool_test",
            description="pool_description", protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            operating_status=constants.ONLINE, enabled=True)
        return pool

    def test_get(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                tenant_id=self.FAKE_UUID_2)
        new_pool = self.pool_repo.get(self.session, id=pool.id)
        self.assertIsInstance(new_pool, models.Pool)
        self.assertEqual(pool, new_pool)

    def test_get_all(self):
        pool_one = self.create_pool(pool_id=self.FAKE_UUID_1,
                                    tenant_id=self.FAKE_UUID_2)
        pool_two = self.create_pool(pool_id=self.FAKE_UUID_3,
                                    tenant_id=self.FAKE_UUID_2)
        pool_list = self.pool_repo.get_all(self.session,
                                           tenant_id=self.FAKE_UUID_2)
        self.assertIsInstance(pool_list, list)
        self.assertEqual(2, len(pool_list))
        self.assertEqual(pool_one, pool_list[0])
        self.assertEqual(pool_two, pool_list[1])

    def test_create(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                tenant_id=self.FAKE_UUID_2)
        self.assertIsInstance(pool, models.Pool)
        self.assertEqual(self.FAKE_UUID_2, pool.tenant_id)
        self.assertEqual("pool_test", pool.name)
        self.assertEqual("pool_description", pool.description)
        self.assertEqual(constants.PROTOCOL_HTTP, pool.protocol)
        self.assertEqual(constants.LB_ALGORITHM_ROUND_ROBIN, pool.lb_algorithm)
        self.assertEqual(constants.ONLINE, pool.operating_status)

    def test_update(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                tenant_id=self.FAKE_UUID_2)
        self.pool_repo.update(self.session, pool.id,
                              description="other_pool_description")
        new_pool = self.pool_repo.get(self.session, id=self.FAKE_UUID_1)
        self.assertEqual("other_pool_description", new_pool.description)

    def test_delete(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                tenant_id=self.FAKE_UUID_2)
        self.pool_repo.delete(self.session, id=pool.id)
        self.assertIsNone(self.pool_repo.get(self.session, id=pool.id))

    def test_delete_with_member(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                tenant_id=self.FAKE_UUID_2)
        member = self.member_repo.create(self.session, id=self.FAKE_UUID_3,
                                         tenant_id=self.FAKE_UUID_2,
                                         pool_id=pool.id,
                                         ip_address="10.0.0.1",
                                         protocol_port=80, enabled=True,
                                         operating_status=constants.ONLINE)
        new_pool = self.pool_repo.get(self.session, id=pool.id)
        self.assertEqual(1, len(new_pool.members))
        self.assertEqual(member, new_pool.members[0])
        self.pool_repo.delete(self.session, id=pool.id)
        self.assertIsNone(self.pool_repo.get(self.session, id=pool.id))
        self.assertIsNone(self.member_repo.get(self.session, id=member.id))

    def test_delete_with_health_monitor(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                tenant_id=self.FAKE_UUID_2)
        hm = self.hm_repo.create(self.session, pool_id=pool.id,
                                 type=constants.HEALTH_MONITOR_HTTP,
                                 delay=1, timeout=1, fall_threshold=1,
                                 rise_threshold=1, enabled=True)
        new_pool = self.pool_repo.get(self.session, id=pool.id)
        self.assertEqual(pool, new_pool)
        self.assertEqual(hm, new_pool.health_monitor)
        self.pool_repo.delete(self.session, id=pool.id)
        self.assertIsNone(self.pool_repo.get(self.session, id=pool.id))
        self.assertIsNone(self.hm_repo.get(self.session, pool_id=hm.pool_id))

    def test_delete_with_session_persistence(self):
        pool = self.create_pool(pool_id=self.FAKE_UUID_1,
                                tenant_id=self.FAKE_UUID_2)
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
                                tenant_id=self.FAKE_UUID_2)
        hm = self.hm_repo.create(self.session, pool_id=pool.id,
                                 type=constants.HEALTH_MONITOR_HTTP,
                                 delay=1, timeout=1, fall_threshold=1,
                                 rise_threshold=1, enabled=True)
        member = self.member_repo.create(self.session, id=self.FAKE_UUID_3,
                                         tenant_id=self.FAKE_UUID_2,
                                         pool_id=pool.id,
                                         ip_address="10.0.0.1",
                                         protocol_port=80,
                                         operating_status=constants.ONLINE,
                                         enabled=True)
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
            self.session, id=self.FAKE_UUID_1, tenant_id=self.FAKE_UUID_2,
            name="pool_test", description="pool_description",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            operating_status=constants.ONLINE, enabled=True)

    def create_member(self, member_id, tenant_id, pool_id, ip_address):
        member = self.member_repo.create(self.session, id=member_id,
                                         tenant_id=tenant_id, pool_id=pool_id,
                                         ip_address=ip_address,
                                         protocol_port=80,
                                         operating_status=constants.ONLINE,
                                         enabled=True)
        return member

    def test_get(self):
        member = self.create_member(self.FAKE_UUID_1, self.FAKE_UUID_2,
                                    self.pool.id, "10.0.0.1")
        new_member = self.member_repo.get(self.session, id=member.id)
        self.assertIsInstance(new_member, models.Member)
        self.assertEqual(member, new_member)

    def test_get_all(self):
        member_one = self.create_member(self.FAKE_UUID_1, self.FAKE_UUID_2,
                                        self.pool.id, "10.0.0.1")
        member_two = self.create_member(self.FAKE_UUID_3, self.FAKE_UUID_2,
                                        self.pool.id, "10.0.0.2")
        member_list = self.member_repo.get_all(self.session,
                                               tenant_id=self.FAKE_UUID_2)
        self.assertIsInstance(member_list, list)
        self.assertEqual(2, len(member_list))
        self.assertEqual(member_one, member_list[0])
        self.assertEqual(member_two, member_list[1])

    def test_create(self):
        member = self.create_member(self.FAKE_UUID_1, self.FAKE_UUID_2,
                                    self.pool.id, ip_address="10.0.0.1")
        new_member = self.member_repo.get(self.session, id=member.id)
        self.assertEqual(self.FAKE_UUID_1, new_member.id)
        self.assertEqual(self.FAKE_UUID_2, new_member.tenant_id)
        self.assertEqual(self.pool.id, new_member.pool_id)
        self.assertEqual("10.0.0.1", new_member.ip_address)
        self.assertEqual(80, new_member.protocol_port)
        self.assertEqual(constants.ONLINE, new_member.operating_status)
        self.assertEqual(True, new_member.enabled)

    def test_update(self):
        ip_address_change = "10.0.0.2"
        member = self.create_member(self.FAKE_UUID_1, self.FAKE_UUID_2,
                                    self.pool.id, "10.0.0.1")
        self.member_repo.update(self.session, id=member.id,
                                ip_address=ip_address_change)
        new_member = self.member_repo.get(self.session, id=member.id)
        self.assertEqual(ip_address_change, new_member.ip_address)

    def test_delete(self):
        member = self.create_member(self.FAKE_UUID_1, self.FAKE_UUID_2,
                                    self.pool.id, "10.0.0.1")
        self.member_repo.delete(self.session, id=member.id)
        self.assertIsNone(self.member_repo.get(self.session, id=member.id))
        new_pool = self.pool_repo.get(self.session, id=self.pool.id)
        self.assertIsNotNone(new_pool)
        self.assertEqual(0, len(new_pool.members))


class SessionPersistenceRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super(SessionPersistenceRepositoryTest, self).setUp()
        self.pool = self.pool_repo.create(
            self.session, id=self.FAKE_UUID_1, tenant_id=self.FAKE_UUID_2,
            name="pool_test", description="pool_description",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
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


class ListenerRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super(ListenerRepositoryTest, self).setUp()
        self.load_balancer = self.lb_repo.create(
            self.session, id=self.FAKE_UUID_1, tenant_id=self.FAKE_UUID_2,
            name="lb_name", description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)

    def create_listener(self, listener_id, port, default_pool_id=None):
        listener = self.listener_repo.create(
            self.session, id=listener_id, tenant_id=self.FAKE_UUID_2,
            name="listener_name", description="listener_description",
            protocol=constants.PROTOCOL_HTTP, protocol_port=port,
            connection_limit=1, load_balancer_id=self.load_balancer.id,
            default_pool_id=default_pool_id, operating_status=constants.ONLINE,
            provisioning_status=constants.ACTIVE, enabled=True)
        return listener

    def test_get(self):
        listener = self.create_listener(self.FAKE_UUID_1, 80)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIsInstance(new_listener, models.Listener)
        self.assertEqual(listener, new_listener)

    def test_get_all(self):
        listener_one = self.create_listener(self.FAKE_UUID_1, 80)
        listener_two = self.create_listener(self.FAKE_UUID_3, 88)
        listener_list = self.listener_repo.get_all(self.session,
                                                   tenant_id=self.FAKE_UUID_2)
        self.assertIsInstance(listener_list, list)
        self.assertEqual(2, len(listener_list))
        self.assertEqual(listener_one, listener_list[0])
        self.assertEqual(listener_two, listener_list[1])

    def test_create(self):
        listener = self.create_listener(self.FAKE_UUID_1, 80)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertEqual(self.FAKE_UUID_1, new_listener.id)
        self.assertEqual(self.FAKE_UUID_2, new_listener.tenant_id)
        self.assertEqual("listener_name", new_listener.name)
        self.assertEqual("listener_description", new_listener.description)
        self.assertEqual(constants.PROTOCOL_HTTP, new_listener.protocol)
        self.assertEqual(80, new_listener.protocol_port)
        self.assertEqual(1, new_listener.connection_limit)
        self.assertEqual(self.load_balancer.id, new_listener.load_balancer_id)
        self.assertEqual(constants.ACTIVE, new_listener.provisioning_status)
        self.assertEqual(constants.ONLINE, new_listener.operating_status)
        self.assertEqual(True, new_listener.enabled)

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
        stats = self.listener_stats_repo.create(
            self.session, listener_id=listener.id, bytes_in=1, bytes_out=1,
            active_connections=1, total_connections=1)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIsNotNone(new_listener)
        self.assertEqual(stats, new_listener.stats)
        self.listener_repo.delete(self.session, id=listener.id)
        self.assertIsNone(self.listener_repo.get(self.session, id=listener.id))
        self.assertIsNone(self.listener_stats_repo.get(
            self.session, listener_id=listener.id))

    def test_delete_with_pool(self):
        pool = self.pool_repo.create(
            self.session, id=self.FAKE_UUID_3, tenant_id=self.FAKE_UUID_2,
            name="pool_test", description="pool_description",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            operating_status=constants.ONLINE, enabled=True)
        listener = self.create_listener(self.FAKE_UUID_1, 80,
                                        default_pool_id=pool.id)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIsNotNone(new_listener)
        self.assertEqual(pool, new_listener.default_pool)
        self.listener_repo.delete(self.session, id=new_listener.id)
        self.assertIsNone(self.listener_repo.get(self.session, id=listener.id))
        self.assertIsNone(self.pool_repo.get(self.session, id=pool.id))

    def test_delete_with_all_children(self):
        pool = self.pool_repo.create(
            self.session, id=self.FAKE_UUID_3, tenant_id=self.FAKE_UUID_2,
            name="pool_test", description="pool_description",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            operating_status=constants.ONLINE, enabled=True)
        listener = self.create_listener(self.FAKE_UUID_1, 80,
                                        default_pool_id=pool.id)
        sni = self.sni_repo.create(self.session, listener_id=listener.id,
                                   tls_container_id=self.FAKE_UUID_3)
        stats = self.listener_stats_repo.create(
            self.session, listener_id=listener.id, bytes_in=1, bytes_out=1,
            active_connections=1, total_connections=1)
        new_listener = self.listener_repo.get(self.session, id=listener.id)
        self.assertIsNotNone(new_listener)
        self.assertEqual(pool, new_listener.default_pool)
        self.assertEqual(sni, new_listener.sni_containers[0])
        self.assertEqual(stats, new_listener.stats)
        self.listener_repo.delete(self.session, id=listener.id)
        self.assertIsNone(self.listener_repo.get(self.session, id=listener.id))
        self.assertIsNone(self.sni_repo.get(self.session,
                                            listener_id=listener.id))
        self.assertIsNone(self.listener_stats_repo.get(
            self.session, listener_id=sni.listener_id))
        self.assertIsNone(self.pool_repo.get(self.session, id=pool.id))


class ListenerStatisticsRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super(ListenerStatisticsRepositoryTest, self).setUp()
        self.listener = self.listener_repo.create(
            self.session, id=self.FAKE_UUID_1, tenant_id=self.FAKE_UUID_2,
            name="listener_name", description="listener_description",
            protocol=constants.PROTOCOL_HTTP, protocol_port=80,
            connection_limit=1, provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)

    def create_listener_stats(self, listener_id):
        stats = self.listener_stats_repo.create(
            self.session, listener_id=listener_id, bytes_in=1, bytes_out=1,
            active_connections=1, total_connections=1)
        return stats

    def test_get(self):
        stats = self.create_listener_stats(self.listener.id)
        new_stats = self.listener_stats_repo.get(self.session,
                                                 listener_id=stats.listener_id)
        self.assertIsInstance(new_stats, models.ListenerStatistics)
        self.assertEqual(stats.listener_id, new_stats.listener_id)

    def test_create(self):
        stats = self.create_listener_stats(self.listener.id)
        new_stats = self.listener_stats_repo.get(self.session,
                                                 listener_id=stats.listener_id)
        self.assertEqual(self.listener.id, new_stats.listener_id)
        self.assertEqual(1, new_stats.bytes_in)
        self.assertEqual(1, new_stats.bytes_out)
        self.assertEqual(1, new_stats.active_connections)
        self.assertEqual(1, new_stats.total_connections)

    def test_update(self):
        bytes_in_change = 2
        stats = self.create_listener_stats(self.listener.id)
        self.listener_stats_repo.update(self.session, stats.listener_id,
                                        bytes_in=bytes_in_change)
        new_stats = self.listener_stats_repo.get(self.session,
                                                 listener_id=stats.listener_id)
        self.assertIsInstance(new_stats, models.ListenerStatistics)
        self.assertEqual(stats.listener_id, new_stats.listener_id)

    def test_delete(self):
        stats = self.create_listener_stats(self.listener.id)
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
        self.assertIsNone(self.listener_stats_repo.get(
            self.session, listener_id=self.listener.id))
        self.listener_stats_repo.replace(self.session, self.listener.id,
                                         bytes_in=bytes_in,
                                         bytes_out=bytes_out,
                                         active_connections=active_conns,
                                         total_connections=total_conns)
        obj = self.listener_stats_repo.get(self.session,
                                           listener_id=self.listener.id)
        self.assertIsNotNone(obj)
        self.assertEqual(self.listener.id, obj.listener_id)
        self.assertEqual(bytes_in, obj.bytes_in)
        self.assertEqual(bytes_out, obj.bytes_out)
        self.assertEqual(active_conns, obj.active_connections)
        self.assertEqual(total_conns, obj.total_connections)

        # Test the update path
        bytes_in_2 = random.randrange(1000000000)
        bytes_out_2 = random.randrange(1000000000)
        active_conns_2 = random.randrange(1000000000)
        total_conns_2 = random.randrange(1000000000)
        self.listener_stats_repo.replace(self.session, self.listener.id,
                                         bytes_in=bytes_in_2,
                                         bytes_out=bytes_out_2,
                                         active_connections=active_conns_2,
                                         total_connections=total_conns_2)
        obj = self.listener_stats_repo.get(self.session,
                                           listener_id=self.listener.id)
        self.assertIsNotNone(obj)
        self.assertEqual(self.listener.id, obj.listener_id)
        self.assertEqual(bytes_in_2, obj.bytes_in)
        self.assertEqual(bytes_out_2, obj.bytes_out)
        self.assertEqual(active_conns_2, obj.active_connections)
        self.assertEqual(total_conns_2, obj.total_connections)


class HealthMonitorRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super(HealthMonitorRepositoryTest, self).setUp()
        self.pool = self.pool_repo.create(
            self.session, id=self.FAKE_UUID_1, tenant_id=self.FAKE_UUID_2,
            name="pool_test", description="pool_description",
            protocol=constants.PROTOCOL_HTTP,
            lb_algorithm=constants.LB_ALGORITHM_ROUND_ROBIN,
            operating_status=constants.ONLINE, enabled=True)

    def create_health_monitor(self, pool_id):
        health_monitor = self.hm_repo.create(
            self.session, type=constants.HEALTH_MONITOR_HTTP, pool_id=pool_id,
            delay=1, timeout=1, fall_threshold=1, rise_threshold=1,
            http_method="POST", url_path="http://localhost:80/index.php",
            expected_codes="200", enabled=True)
        return health_monitor

    def test_get(self):
        hm = self.create_health_monitor(self.pool.id)
        new_hm = self.hm_repo.get(self.session, pool_id=hm.pool_id)
        self.assertIsInstance(new_hm, models.HealthMonitor)
        self.assertEqual(hm, new_hm)

    def test_create(self):
        hm = self.create_health_monitor(self.pool.id)
        new_hm = self.hm_repo.get(self.session, pool_id=hm.pool_id)
        self.assertEqual(constants.HEALTH_MONITOR_HTTP, new_hm.type)
        self.assertEqual(self.pool.id, new_hm.pool_id)
        self.assertEqual(1, new_hm.delay)
        self.assertEqual(1, new_hm.timeout)
        self.assertEqual(1, new_hm.fall_threshold)
        self.assertEqual(1, new_hm.rise_threshold)
        self.assertEqual("POST", new_hm.http_method)
        self.assertEqual("http://localhost:80/index.php", new_hm.url_path)
        self.assertEqual("200", new_hm.expected_codes)
        self.assertEqual(True, new_hm.enabled)

    def test_update(self):
        delay_change = 2
        hm = self.create_health_monitor(self.pool.id)
        self.hm_repo.update(self.session, hm.pool.id, delay=delay_change)
        new_hm = self.hm_repo.get(self.session, pool_id=hm.pool_id)
        self.assertEqual(delay_change, new_hm.delay)

    def test_delete(self):
        hm = self.create_health_monitor(self.pool.id)
        self.hm_repo.delete(self.session, pool_id=hm.pool_id)
        self.assertIsNone(self.hm_repo.get(self.session, pool_id=hm.pool_id))
        new_pool = self.pool_repo.get(self.session, id=self.pool.id)
        self.assertIsNotNone(new_pool)
        self.assertIsNone(new_pool.health_monitor)


class LoadBalancerRepositoryTest(BaseRepositoryTest):

    def create_loadbalancer(self, lb_id):
        lb = self.lb_repo.create(self.session, id=lb_id,
                                 tenant_id=self.FAKE_UUID_2, name="lb_name",
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
        lb_list = self.lb_repo.get_all(self.session,
                                       tenant_id=self.FAKE_UUID_2)
        self.assertEqual(2, len(lb_list))
        self.assertEqual(lb_one, lb_list[0])
        self.assertEqual(lb_two, lb_list[1])

    def test_create(self):
        lb = self.create_loadbalancer(self.FAKE_UUID_1)
        self.assertEqual(self.FAKE_UUID_1, lb.id)
        self.assertEqual(self.FAKE_UUID_2, lb.tenant_id)
        self.assertEqual("lb_name", lb.name)
        self.assertEqual("lb_description", lb.description)
        self.assertEqual(constants.ACTIVE, lb.provisioning_status)
        self.assertEqual(constants.ONLINE, lb.operating_status)
        self.assertEqual(True, lb.enabled)

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
                                   ip_address="10.0.0.1")
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
            self.session, id=self.FAKE_UUID_1, tenant_id=self.FAKE_UUID_2,
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
            self.session, id=self.FAKE_UUID_1, tenant_id=self.FAKE_UUID_2,
            name="listener_name", description="listener_description",
            load_balancer_id=lb.id, protocol=constants.PROTOCOL_HTTP,
            protocol_port=80, connection_limit=1,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)
        listener_2 = self.listener_repo.create(
            self.session, id=self.FAKE_UUID_3, tenant_id=self.FAKE_UUID_2,
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
                                   ip_address="10.0.0.1")
        listener = self.listener_repo.create(
            self.session, id=self.FAKE_UUID_1, tenant_id=self.FAKE_UUID_2,
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


class VipRepositoryTest(BaseRepositoryTest):

    def setUp(self):
        super(VipRepositoryTest, self).setUp()
        self.lb = self.lb_repo.create(
            self.session, id=self.FAKE_UUID_1, tenant_id=self.FAKE_UUID_2,
            name="lb_name", description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)

    def create_vip(self, lb_id):
        vip = self.vip_repo.create(self.session, load_balancer_id=lb_id,
                                   ip_address="10.0.0.1")
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
        self.assertEqual("10.0.0.1", vip.ip_address)

    def test_update(self):
        address_change = "10.0.0.2"
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
            self.session, id=self.FAKE_UUID_1, tenant_id=self.FAKE_UUID_2,
            name="listener_name", description="listener_description",
            protocol=constants.PROTOCOL_HTTP, protocol_port=80,
            connection_limit=1, provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)

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
            self.session, id=self.FAKE_UUID_1, tenant_id=self.FAKE_UUID_2,
            name="lb_name", description="lb_description",
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE, enabled=True)

    def create_amphora(self, amphora_id):
        amphora = self.amphora_repo.create(self.session, id=amphora_id,
                                           compute_id=self.FAKE_UUID_3,
                                           status=constants.ACTIVE,
                                           lb_network_ip=self.FAKE_IP,
                                           vrrp_ip=self.FAKE_IP,
                                           ha_ip=self.FAKE_IP,
                                           role=constants.ROLE_MASTER)
        return amphora

    def test_get(self):
        amphora = self.create_amphora(self.FAKE_UUID_1)
        new_amphora = self.amphora_repo.get(self.session, id=amphora.id)
        self.assertIsInstance(new_amphora, models.Amphora)
        self.assertEqual(amphora, new_amphora)

    def test_count(self):
        amphora = self.create_amphora(self.FAKE_UUID_1)
        amp_count = self.amphora_repo.count(self.session, id=amphora.id)
        self.assertEqual(amp_count, 1)

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

    def test_get_all_lbs_on_amphora(self):
        amphora = self.create_amphora(self.FAKE_UUID_1)
        self.amphora_repo.associate(self.session, self.lb.id, amphora.id)
        lb_list = self.amphora_repo.get_all_lbs_on_amphora(self.session,
                                                           amphora.id)
        self.assertIsNotNone(lb_list)
        self.assertIn(self.lb, lb_list)

    def test_get_spare_amphora_count(self):
        count = self.amphora_repo.get_spare_amphora_count(self.session)
        self.assertEqual(count, 0)

        amphora1 = self.create_amphora(self.FAKE_UUID_1)
        self.amphora_repo.update(self.session, amphora1.id,
                                 status=constants.AMPHORA_READY)
        amphora2 = self.create_amphora(self.FAKE_UUID_2)
        self.amphora_repo.update(self.session, amphora2.id,
                                 status=constants.AMPHORA_READY)
        count = self.amphora_repo.get_spare_amphora_count(self.session)
        self.assertEqual(count, 2)


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

    def test_check_amphora_out_of_date(self):
        """When exp_age is None."""
        self.create_amphora_health(self.amphora.id)
        checkres = self.amphora_health_repo.check_amphora_expired(
            self.session, self.amphora.id)
        self.assertTrue(checkres)

    def test_check_amphora_expired_with_exp_age(self):
        """When exp_age is passed as an argument."""
        exp_age = datetime.timedelta(
            seconds=self.FAKE_EXP_AGE)
        self.create_amphora_health(self.amphora.id)
        checkres = self.amphora_health_repo.check_amphora_expired(
            self.session, self.amphora.id, exp_age)
        self.assertTrue(checkres)

    def test_get_stale_amphora(self):
        stale_amphora = self.amphora_health_repo.get_stale_amphora(
            self.session)
        self.assertIsNone(stale_amphora)

        self.create_amphora_health(self.amphora.id)
        stale_amphora = self.amphora_health_repo.get_stale_amphora(
            self.session)
        self.assertEqual(stale_amphora.amphora_id, self.amphora.id)

    def test_create(self):
        amphora_health = self.create_amphora_health(self.FAKE_UUID_1)
        self.assertEqual(self.FAKE_UUID_1, amphora_health.amphora_id)
        newcreatedtime = datetime.datetime.utcnow()
        oldcreatetime = amphora_health.last_update

        diff = newcreatedtime - oldcreatetime
        self.assertEqual(diff.seconds, 600)

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
