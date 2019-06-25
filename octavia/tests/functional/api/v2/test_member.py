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

import mock
from octavia_lib.api.drivers import data_models as driver_dm
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.api.drivers import utils as driver_utils
from octavia.common import constants
import octavia.common.context
from octavia.common import data_models
from octavia.common import exceptions
from octavia.db import repositories
from octavia.network import base as network_base
from octavia.tests.functional.api.v2 import base


class TestMember(base.BaseAPITest):

    root_tag = 'member'
    root_tag_list = 'members'
    root_tag_links = 'members_links'

    def setUp(self):
        super(TestMember, self).setUp()
        vip_subnet_id = uuidutils.generate_uuid()
        self.lb = self.create_load_balancer(vip_subnet_id)
        self.lb_id = self.lb.get('loadbalancer').get('id')
        self.project_id = self.lb.get('loadbalancer').get('project_id')
        self.set_lb_status(self.lb_id)
        self.listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80,
            lb_id=self.lb_id)
        self.listener_id = self.listener.get('listener').get('id')
        self.set_lb_status(self.lb_id)
        self.pool = self.create_pool(self.lb_id, constants.PROTOCOL_HTTP,
                                     constants.LB_ALGORITHM_ROUND_ROBIN)
        self.pool_id = self.pool.get('pool').get('id')
        self.set_lb_status(self.lb_id)
        self.pool_with_listener = self.create_pool(
            self.lb_id, constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN, listener_id=self.listener_id)
        self.pool_with_listener_id = (
            self.pool_with_listener.get('pool').get('id'))
        self.set_lb_status(self.lb_id)
        self.members_path = self.MEMBERS_PATH.format(
            pool_id=self.pool_id)
        self.member_path = self.members_path + '/{member_id}'
        self.members_path_listener = self.MEMBERS_PATH.format(
            pool_id=self.pool_with_listener_id)
        self.member_path_listener = self.members_path_listener + '/{member_id}'
        self.pool_repo = repositories.PoolRepository()

    def test_get(self):
        api_member = self.create_member(
            self.pool_id, '192.0.2.1', 80).get(self.root_tag)
        response = self.get(self.member_path.format(
            member_id=api_member.get('id'))).json.get(self.root_tag)
        self.assertEqual(api_member, response)
        self.assertEqual(api_member.get('name'), '')
        self.assertEqual([], api_member['tags'])

    def test_get_authorized(self):
        api_member = self.create_member(
            self.pool_id, '192.0.2.1', 80).get(self.root_tag)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                response = self.get(self.member_path.format(
                    member_id=api_member.get('id'))).json.get(self.root_tag)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(api_member, response)
        self.assertEqual(api_member.get('name'), '')

    def test_get_not_authorized(self):
        api_member = self.create_member(
            self.pool_id, '192.0.2.1', 80).get(self.root_tag)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            response = self.get(self.member_path.format(
                member_id=api_member.get('id')), status=403).json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response)

    def test_get_deleted_gives_404(self):
        api_member = self.create_member(
            self.pool_id, '192.0.2.1', 80).get(self.root_tag)

        self.set_object_status(self.member_repo, api_member.get('id'),
                               provisioning_status=constants.DELETED)
        self.get(self.member_path.format(member_id=api_member.get('id')),
                 status=404)

    def test_bad_get(self):
        self.get(self.member_path.format(member_id=uuidutils.generate_uuid()),
                 status=404)

    def test_get_all(self):
        api_m_1 = self.create_member(
            self.pool_id, '192.0.2.1', 80,
            tags=['test_tag1']).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        api_m_2 = self.create_member(
            self.pool_id, '192.0.2.2', 80,
            tags=['test_tag2']).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        # Original objects didn't have the updated operating/provisioning
        # status that exists in the DB.
        for m in [api_m_1, api_m_2]:
            m['operating_status'] = constants.ONLINE
            m['provisioning_status'] = constants.ACTIVE
            m.pop('updated_at')
        response = self.get(self.members_path).json.get(self.root_tag_list)
        self.assertIsInstance(response, list)
        self.assertEqual(2, len(response))
        for m in response:
            m.pop('updated_at')
        for m in [api_m_1, api_m_2]:
            self.assertIn(m, response)

    def test_get_all_hides_deleted(self):
        api_member = self.create_member(
            self.pool_id, '10.0.0.1', 80).get(self.root_tag)

        response = self.get(self.members_path)
        objects = response.json.get(self.root_tag_list)
        self.assertEqual(len(objects), 1)
        self.set_object_status(self.member_repo, api_member.get('id'),
                               provisioning_status=constants.DELETED)
        response = self.get(self.members_path)
        objects = response.json.get(self.root_tag_list)
        self.assertEqual(len(objects), 0)

    def test_get_all_authorized(self):
        api_m_1 = self.create_member(
            self.pool_id, '192.0.2.1', 80).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        api_m_2 = self.create_member(
            self.pool_id, '192.0.2.2', 80).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        # Original objects didn't have the updated operating/provisioning
        # status that exists in the DB.
        for m in [api_m_1, api_m_2]:
            m['operating_status'] = constants.ONLINE
            m['provisioning_status'] = constants.ACTIVE
            m.pop('updated_at')

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                response = self.get(self.members_path)
                response = response.json.get(self.root_tag_list)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        self.assertIsInstance(response, list)
        self.assertEqual(2, len(response))
        for m in response:
            m.pop('updated_at')
        for m in [api_m_1, api_m_2]:
            self.assertIn(m, response)

    def test_get_all_not_authorized(self):
        api_m_1 = self.create_member(
            self.pool_id, '192.0.2.1', 80).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        api_m_2 = self.create_member(
            self.pool_id, '192.0.2.2', 80).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        # Original objects didn't have the updated operating/provisioning
        # status that exists in the DB.
        for m in [api_m_1, api_m_2]:
            m['operating_status'] = constants.ONLINE
            m['provisioning_status'] = constants.ACTIVE
            m.pop('updated_at')

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            response = self.get(self.members_path, status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response.json)

    def test_get_all_sorted(self):
        self.create_member(self.pool_id, '192.0.2.1', 80, name='member1')
        self.set_lb_status(self.lb_id)
        self.create_member(self.pool_id, '192.0.2.2', 80, name='member2')
        self.set_lb_status(self.lb_id)
        self.create_member(self.pool_id, '192.0.2.3', 80, name='member3')
        self.set_lb_status(self.lb_id)

        response = self.get(self.members_path,
                            params={'sort': 'name:desc'})
        members_desc = response.json.get(self.root_tag_list)
        response = self.get(self.members_path,
                            params={'sort': 'name:asc'})
        members_asc = response.json.get(self.root_tag_list)

        self.assertEqual(3, len(members_desc))
        self.assertEqual(3, len(members_asc))

        member_id_names_desc = [(member.get('id'), member.get('name'))
                                for member in members_desc]
        member_id_names_asc = [(member.get('id'), member.get('name'))
                               for member in members_asc]
        self.assertEqual(member_id_names_asc,
                         list(reversed(member_id_names_desc)))

    def test_get_all_limited(self):
        self.create_member(self.pool_id, '192.0.2.1', 80, name='member1')
        self.set_lb_status(self.lb_id)
        self.create_member(self.pool_id, '192.0.2.2', 80, name='member2')
        self.set_lb_status(self.lb_id)
        self.create_member(self.pool_id, '192.0.2.3', 80, name='member3')
        self.set_lb_status(self.lb_id)

        # First two -- should have 'next' link
        first_two = self.get(self.members_path, params={'limit': 2}).json
        objs = first_two[self.root_tag_list]
        links = first_two[self.root_tag_links]
        self.assertEqual(2, len(objs))
        self.assertEqual(1, len(links))
        self.assertEqual('next', links[0]['rel'])

        # Third + off the end -- should have previous link
        third = self.get(self.members_path, params={
            'limit': 2,
            'marker': first_two[self.root_tag_list][1]['id']}).json
        objs = third[self.root_tag_list]
        links = third[self.root_tag_links]
        self.assertEqual(1, len(objs))
        self.assertEqual(1, len(links))
        self.assertEqual('previous', links[0]['rel'])

        # Middle -- should have both links
        middle = self.get(self.members_path, params={
            'limit': 1,
            'marker': first_two[self.root_tag_list][0]['id']}).json
        objs = middle[self.root_tag_list]
        links = middle[self.root_tag_links]
        self.assertEqual(1, len(objs))
        self.assertEqual(2, len(links))
        self.assertItemsEqual(['previous', 'next'], [l['rel'] for l in links])

    def test_get_all_fields_filter(self):
        self.create_member(self.pool_id, '192.0.2.1', 80, name='member1')
        self.set_lb_status(self.lb_id)
        self.create_member(self.pool_id, '192.0.2.2', 80, name='member2')
        self.set_lb_status(self.lb_id)
        self.create_member(self.pool_id, '192.0.2.3', 80, name='member3')
        self.set_lb_status(self.lb_id)

        members = self.get(self.members_path, params={
            'fields': ['id', 'address']}).json
        for member in members['members']:
            self.assertIn(u'id', member)
            self.assertIn(u'address', member)
            self.assertNotIn(u'name', member)
            self.assertNotIn(u'monitor_address', member)

    def test_get_one_fields_filter(self):
        member1 = self.create_member(
            self.pool_id, '192.0.2.1', 80, name='member1').get(self.root_tag)
        self.set_lb_status(self.lb_id)

        member = self.get(
            self.member_path.format(member_id=member1.get('id')),
            params={'fields': ['id', 'address']}).json.get(self.root_tag)
        self.assertIn(u'id', member)
        self.assertIn(u'address', member)
        self.assertNotIn(u'name', member)
        self.assertNotIn(u'monitor_address', member)

    def test_get_all_filter(self):
        mem1 = self.create_member(self.pool_id,
                                  '192.0.2.1',
                                  80,
                                  name='member1').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_member(self.pool_id,
                           '192.0.2.2',
                           80,
                           name='member2').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_member(self.pool_id,
                           '192.0.2.3',
                           80,
                           name='member3').get(self.root_tag)
        self.set_lb_status(self.lb_id)

        members = self.get(self.members_path, params={
            'id': mem1['id']}).json
        self.assertEqual(1, len(members['members']))
        self.assertEqual(mem1['id'],
                         members['members'][0]['id'])

    def test_get_all_tags_filter(self):
        mem1 = self.create_member(
            self.pool_id,
            '192.0.2.1',
            80,
            name='member1',
            tags=['test_tag1', 'test_tag2']
        ).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        mem2 = self.create_member(
            self.pool_id,
            '192.0.2.2',
            80,
            name='member2',
            tags=['test_tag2', 'test_tag3']
        ).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        mem3 = self.create_member(
            self.pool_id,
            '192.0.2.3',
            80,
            name='member3',
            tags=['test_tag4', 'test_tag5']
        ).get(self.root_tag)
        self.set_lb_status(self.lb_id)

        mems = self.get(
            self.members_path,
            params={'tags': 'test_tag2'}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(mems, list)
        self.assertEqual(2, len(mems))
        self.assertEqual(
            [mem1.get('id'), mem2.get('id')],
            [mem.get('id') for mem in mems]
        )

        mems = self.get(
            self.members_path,
            params={'tags': ['test_tag2', 'test_tag3']}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(mems, list)
        self.assertEqual(1, len(mems))
        self.assertEqual(
            [mem2.get('id')],
            [mem.get('id') for mem in mems]
        )

        mems = self.get(
            self.members_path,
            params={'tags-any': 'test_tag2'}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(mems, list)
        self.assertEqual(2, len(mems))
        self.assertEqual(
            [mem1.get('id'), mem2.get('id')],
            [mem.get('id') for mem in mems]
        )

        mems = self.get(
            self.members_path,
            params={'not-tags': 'test_tag2'}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(mems, list)
        self.assertEqual(1, len(mems))
        self.assertEqual(
            [mem3.get('id')],
            [mem.get('id') for mem in mems]
        )

        mems = self.get(
            self.members_path,
            params={'not-tags-any': ['test_tag2', 'test_tag4']}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(mems, list)
        self.assertEqual(0, len(mems))

        mems = self.get(
            self.members_path,
            params={'tags': 'test_tag2',
                    'tags-any': ['test_tag1', 'test_tag3']}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(mems, list)
        self.assertEqual(2, len(mems))
        self.assertEqual(
            [mem1.get('id'), mem2.get('id')],
            [mem.get('id') for mem in mems]
        )

        mems = self.get(
            self.members_path,
            params={'tags': 'test_tag2', 'not-tags': 'test_tag2'}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(mems, list)
        self.assertEqual(0, len(mems))

    def test_empty_get_all(self):
        response = self.get(self.members_path).json.get(self.root_tag_list)
        self.assertIsInstance(response, list)
        self.assertEqual(0, len(response))

    def test_create_sans_listener(self):
        api_member = self.create_member(
            self.pool_id, '192.0.2.1', 80).get(self.root_tag)
        self.assertEqual('192.0.2.1', api_member['address'])
        self.assertEqual(80, api_member['protocol_port'])
        self.assertIsNotNone(api_member['created_at'])
        self.assertIsNone(api_member['updated_at'])
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id,
            member_id=api_member.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.ACTIVE,
            pool_prov_status=constants.PENDING_UPDATE,
            member_prov_status=constants.PENDING_CREATE,
            member_op_status=constants.NO_MONITOR)
        self.set_lb_status(self.lb_id)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id, member_id=api_member.get('id'))

    def test_create_authorized(self):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)

        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):

                api_member = self.create_member(
                    self.pool_id, '192.0.2.1', 80,
                    tags=['test_tag']).get(self.root_tag)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        self.assertEqual('192.0.2.1', api_member['address'])
        self.assertEqual(80, api_member['protocol_port'])
        self.assertEqual(['test_tag'], api_member['tags'])
        self.assertIsNotNone(api_member['created_at'])
        self.assertIsNone(api_member['updated_at'])
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id,
            member_id=api_member.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.ACTIVE,
            pool_prov_status=constants.PENDING_UPDATE,
            member_prov_status=constants.PENDING_CREATE,
            member_op_status=constants.NO_MONITOR)
        self.set_lb_status(self.lb_id)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id, member_id=api_member.get('id'))

    def test_create_not_authorized(self):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)

        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            api_member = self.create_member(
                self.pool_id, '192.0.2.1', 80, status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, api_member)

    def test_create_pool_in_error(self):
        project_id = uuidutils.generate_uuid()
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(), name='lb1',
                                        project_id=project_id)
        lb1_id = lb1.get('loadbalancer').get('id')
        self.set_lb_status(lb1_id)
        pool1 = self.create_pool(
            lb1_id, constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN).get('pool')
        pool1_id = pool1.get('id')
        self.set_lb_status(lb1_id)
        self.set_object_status(self.pool_repo, pool1_id,
                               provisioning_status=constants.ERROR)
        api_member = self.create_member(pool1_id, '192.0.2.1', 80, status=409)
        ref_msg = 'Pool %s is immutable and cannot be updated.' % pool1_id
        self.assertEqual(ref_msg, api_member.get('faultstring'))

    # TODO(rm_work) Remove after deprecation of project_id in POST (R series)
    def test_create_with_project_id_is_ignored(self):
        pid = uuidutils.generate_uuid()
        api_member = self.create_member(
            self.pool_id, '192.0.2.1', 80, project_id=pid).get(self.root_tag)
        self.assertEqual(self.project_id, api_member['project_id'])

    def test_create_backup(self):
        api_member = self.create_member(
            self.pool_id, '192.0.2.1', 80, backup=True).get(self.root_tag)
        self.assertTrue(api_member['backup'])
        self.set_lb_status(self.lb_id)
        api_member = self.create_member(
            self.pool_id, '192.0.2.1', 81, backup=False).get(self.root_tag)
        self.assertFalse(api_member['backup'])

    def test_bad_create(self):
        member = {'name': 'test1'}
        self.post(self.members_path, self._build_body(member), status=400)

    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_create_with_bad_provider(self, mock_provider):
        mock_provider.side_effect = exceptions.ProviderDriverError(
            prov='bad_driver', user_msg='broken')
        response = self.create_member(self.pool_id, '192.0.2.1', 80,
                                      status=500)
        self.assertIn('Provider \'bad_driver\' reports error: broken',
                      response.get('faultstring'))

    @mock.patch('octavia.api.drivers.driver_factory.get_driver')
    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_full_batch_members(self, mock_provider, mock_get_driver):
        mock_driver = mock.MagicMock()
        mock_driver.name = 'noop_driver'
        mock_get_driver.return_value = mock_driver

        member1 = {'address': '192.0.2.1', 'protocol_port': 80,
                   'project_id': self.project_id}
        member2 = {'address': '192.0.2.2', 'protocol_port': 80,
                   'project_id': self.project_id}
        member3 = {'address': '192.0.2.3', 'protocol_port': 80,
                   'project_id': self.project_id}
        member4 = {'address': '192.0.2.4', 'protocol_port': 80,
                   'project_id': self.project_id}
        member5 = {'address': '192.0.2.5', 'protocol_port': 80,
                   'project_id': self.project_id}
        member6 = {'address': '192.0.2.6', 'protocol_port': 80,
                   'project_id': self.project_id}
        members = [member1, member2, member3, member4]
        for m in members:
            self.create_member(pool_id=self.pool_id, **m)
            self.set_lb_status(self.lb_id)

        # We are only concerned about the batch update, so clear out the
        # create members calls above.
        mock_provider.reset_mock()

        req_dict = [member1, member2, member5, member6]
        body = {self.root_tag_list: req_dict}
        path = self.MEMBERS_PATH.format(pool_id=self.pool_id)
        self.put(path, body, status=202)
        returned_members = self.get(
            self.MEMBERS_PATH.format(pool_id=self.pool_id)
        ).json.get(self.root_tag_list)

        expected_members = [
            ('192.0.2.1', 80, 'PENDING_UPDATE'),
            ('192.0.2.2', 80, 'PENDING_UPDATE'),
            ('192.0.2.3', 80, 'PENDING_DELETE'),
            ('192.0.2.4', 80, 'PENDING_DELETE'),
            ('192.0.2.5', 80, 'PENDING_CREATE'),
            ('192.0.2.6', 80, 'PENDING_CREATE'),
        ]

        provider_creates = []
        provider_updates = []
        for rm in returned_members:
            self.assertIn(
                (rm['address'],
                 rm['protocol_port'],
                 rm['provisioning_status']), expected_members)

            provider_dict = driver_utils.member_dict_to_provider_dict(rm)
            # Adjust for API response
            provider_dict['pool_id'] = self.pool_id
            if rm['provisioning_status'] == 'PENDING_UPDATE':
                del provider_dict['name']
                del provider_dict['subnet_id']
                provider_updates.append(driver_dm.Member(**provider_dict))
            elif rm['provisioning_status'] == 'PENDING_CREATE':
                provider_dict['name'] = None
                provider_creates.append(driver_dm.Member(**provider_dict))
        # Order matters here
        provider_creates += provider_updates

        mock_provider.assert_called_once_with(u'noop_driver',
                                              mock_driver.member_batch_update,
                                              provider_creates)

    @mock.patch('octavia.api.drivers.driver_factory.get_driver')
    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_create_batch_members(self, mock_provider, mock_get_driver):
        mock_driver = mock.MagicMock()
        mock_driver.name = 'noop_driver'
        mock_get_driver.return_value = mock_driver

        member5 = {'address': '192.0.2.5', 'protocol_port': 80,
                   'tags': ['test_tag1']}
        member6 = {'address': '192.0.2.6', 'protocol_port': 80,
                   'tags': ['test_tag2']}

        req_dict = [member5, member6]
        body = {self.root_tag_list: req_dict}
        path = self.MEMBERS_PATH.format(pool_id=self.pool_id)
        self.put(path, body, status=202)
        returned_members = self.get(
            self.MEMBERS_PATH.format(pool_id=self.pool_id)
        ).json.get(self.root_tag_list)

        expected_members = [
            ('192.0.2.5', 80, 'PENDING_CREATE', ['test_tag1']),
            ('192.0.2.6', 80, 'PENDING_CREATE', ['test_tag2']),
        ]

        provider_members = []
        for rm in returned_members:
            self.assertIn(
                (rm['address'],
                 rm['protocol_port'],
                 rm['provisioning_status'],
                 rm['tags']), expected_members)

            provider_dict = driver_utils.member_dict_to_provider_dict(rm)
            # Adjust for API response
            provider_dict['pool_id'] = self.pool_id
            provider_dict['name'] = None
            provider_members.append(driver_dm.Member(**provider_dict))

        mock_provider.assert_called_once_with(u'noop_driver',
                                              mock_driver.member_batch_update,
                                              provider_members)

    def test_create_batch_members_with_bad_subnet(self):
        subnet_id = uuidutils.generate_uuid()
        member5 = {'address': '10.0.0.5',
                   'protocol_port': 80,
                   'subnet_id': subnet_id}

        req_dict = [member5]
        body = {self.root_tag_list: req_dict}
        path = self.MEMBERS_PATH.format(pool_id=self.pool_id)

        with mock.patch(
                'octavia.common.utils.get_network_driver') as net_mock:
            net_mock.return_value.get_subnet = mock.Mock(
                side_effect=network_base.SubnetNotFound('Subnet not found'))
            response = self.put(path, body, status=400).json
            err_msg = 'Subnet ' + subnet_id + ' not found.'
            self.assertEqual(response.get('faultstring'), err_msg)

    def test_create_batch_members_with_invalid_address(self):
        # 169.254.169.254 is the default invalid member address
        member5 = {'address': '169.254.169.254',
                   'protocol_port': 80}

        req_dict = [member5]
        body = {self.root_tag_list: req_dict}
        path = self.MEMBERS_PATH.format(pool_id=self.pool_id)

        response = self.put(path, body, status=400).json
        err_msg = ("169.254.169.254 is not a valid option for member address")
        self.assertEqual(err_msg, response.get('faultstring'))

    @mock.patch('octavia.api.drivers.driver_factory.get_driver')
    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_additive_only_batch_members(self, mock_provider, mock_get_driver):
        mock_driver = mock.MagicMock()
        mock_driver.name = 'noop_driver'
        mock_get_driver.return_value = mock_driver

        member1 = {'address': '192.0.2.1', 'protocol_port': 80}
        member2 = {'address': '192.0.2.2', 'protocol_port': 80}
        member3 = {'address': '192.0.2.3', 'protocol_port': 80}
        member4 = {'address': '192.0.2.4', 'protocol_port': 80}
        member5 = {'address': '192.0.2.5', 'protocol_port': 80}
        member6 = {'address': '192.0.2.6', 'protocol_port': 80}
        members = [member1, member2, member3, member4]
        for m in members:
            self.create_member(pool_id=self.pool_id, **m)
            self.set_lb_status(self.lb_id)

        # We are only concerned about the batch update, so clear out the
        # create members calls above.
        mock_provider.reset_mock()

        req_dict = [member1, member2, member5, member6]
        body = {self.root_tag_list: req_dict}
        path = self.MEMBERS_PATH.format(pool_id=self.pool_id)
        path = "{}?additive_only=True".format(path)
        self.put(path, body, status=202)
        returned_members = self.get(
            self.MEMBERS_PATH.format(pool_id=self.pool_id)
        ).json.get(self.root_tag_list)

        # Members 1+2 should be updated, 3+4 left alone, and 5+6 created
        expected_members = [
            ('192.0.2.1', 80, 'PENDING_UPDATE'),
            ('192.0.2.2', 80, 'PENDING_UPDATE'),
            ('192.0.2.3', 80, 'ACTIVE'),
            ('192.0.2.4', 80, 'ACTIVE'),
            ('192.0.2.5', 80, 'PENDING_CREATE'),
            ('192.0.2.6', 80, 'PENDING_CREATE'),
        ]

        provider_creates = []
        provider_updates = []
        provider_ignored = []
        for rm in returned_members:
            self.assertIn(
                (rm['address'],
                 rm['protocol_port'],
                 rm['provisioning_status']), expected_members)

            provider_dict = driver_utils.member_dict_to_provider_dict(rm)
            # Adjust for API response
            provider_dict['pool_id'] = self.pool_id
            if rm['provisioning_status'] == 'PENDING_UPDATE':
                del provider_dict['name']
                del provider_dict['subnet_id']
                provider_updates.append(driver_dm.Member(**provider_dict))
            elif rm['provisioning_status'] == 'PENDING_CREATE':
                provider_dict['name'] = None
                provider_creates.append(driver_dm.Member(**provider_dict))
            elif rm['provisioning_status'] == 'ACTIVE':
                provider_dict['name'] = None
                provider_ignored.append(driver_dm.Member(**provider_dict))
        # Order matters here
        provider_creates += provider_updates
        provider_creates += provider_ignored

        mock_provider.assert_called_once_with(u'noop_driver',
                                              mock_driver.member_batch_update,
                                              provider_creates)

    @mock.patch('octavia.api.drivers.driver_factory.get_driver')
    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_update_batch_members(self, mock_provider, mock_get_driver):
        mock_driver = mock.MagicMock()
        mock_driver.name = 'noop_driver'
        mock_get_driver.return_value = mock_driver

        member1 = {'address': '192.0.2.1', 'protocol_port': 80,
                   'project_id': self.project_id}
        member2 = {'address': '192.0.2.2', 'protocol_port': 80,
                   'project_id': self.project_id}
        members = [member1, member2]
        for m in members:
            self.create_member(pool_id=self.pool_id, **m)
            self.set_lb_status(self.lb_id)

        # We are only concerned about the batch update, so clear out the
        # create members calls above.
        mock_provider.reset_mock()

        req_dict = [member1, member2]
        body = {self.root_tag_list: req_dict}
        path = self.MEMBERS_PATH.format(pool_id=self.pool_id)
        self.put(path, body, status=202)
        returned_members = self.get(
            self.MEMBERS_PATH.format(pool_id=self.pool_id)
        ).json.get(self.root_tag_list)

        expected_members = [
            ('192.0.2.1', 80, 'PENDING_UPDATE'),
            ('192.0.2.2', 80, 'PENDING_UPDATE'),
        ]

        provider_members = []
        for rm in returned_members:
            self.assertIn(
                (rm['address'],
                 rm['protocol_port'],
                 rm['provisioning_status']), expected_members)

            provider_dict = driver_utils.member_dict_to_provider_dict(rm)
            # Adjust for API response
            provider_dict['pool_id'] = self.pool_id
            del provider_dict['name']
            del provider_dict['subnet_id']
            provider_members.append(driver_dm.Member(**provider_dict))

        mock_provider.assert_called_once_with(u'noop_driver',
                                              mock_driver.member_batch_update,
                                              provider_members)

    @mock.patch('octavia.api.drivers.driver_factory.get_driver')
    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_delete_batch_members(self, mock_provider, mock_get_driver):
        mock_driver = mock.MagicMock()
        mock_driver.name = 'noop_driver'
        mock_get_driver.return_value = mock_driver

        member3 = {'address': '192.0.2.3', 'protocol_port': 80}
        member4 = {'address': '192.0.2.4', 'protocol_port': 80}
        members = [member3, member4]
        for m in members:
            self.create_member(pool_id=self.pool_id, **m)
            self.set_lb_status(self.lb_id)

        # We are only concerned about the batch update, so clear out the
        # create members calls above.
        mock_provider.reset_mock()

        req_dict = []
        body = {self.root_tag_list: req_dict}
        path = self.MEMBERS_PATH.format(pool_id=self.pool_id)
        self.put(path, body, status=202)
        returned_members = self.get(
            self.MEMBERS_PATH.format(pool_id=self.pool_id)
        ).json.get(self.root_tag_list)

        expected_members = [
            ('192.0.2.3', 80, 'PENDING_DELETE'),
            ('192.0.2.4', 80, 'PENDING_DELETE'),
        ]

        provider_members = []
        for rm in returned_members:
            self.assertIn(
                (rm['address'],
                 rm['protocol_port'],
                 rm['provisioning_status']), expected_members)

        mock_provider.assert_called_once_with(u'noop_driver',
                                              mock_driver.member_batch_update,
                                              provider_members)

    def test_create_with_attached_listener(self):
        api_member = self.create_member(
            self.pool_with_listener_id, '192.0.2.1', 80).get(self.root_tag)
        self.assertEqual('192.0.2.1', api_member['address'])
        self.assertEqual(80, api_member['protocol_port'])
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=api_member.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            member_prov_status=constants.PENDING_CREATE,
            member_op_status=constants.NO_MONITOR)
        self.set_lb_status(self.lb_id)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=api_member.get('id'))

    def test_create_with_monitor_address_and_port(self):
        api_member = self.create_member(
            self.pool_with_listener_id, '192.0.2.1', 80,
            monitor_address='192.0.2.3',
            monitor_port=80).get(self.root_tag)
        self.assertEqual('192.0.2.1', api_member['address'])
        self.assertEqual(80, api_member['protocol_port'])
        self.assertEqual('192.0.2.3', api_member['monitor_address'])
        self.assertEqual(80, api_member['monitor_port'])
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=api_member.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            member_prov_status=constants.PENDING_CREATE,
            member_op_status=constants.NO_MONITOR)
        self.set_lb_status(self.lb_id)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=api_member.get('id'))

    def test_create_with_health_monitor(self):
        self.create_health_monitor(self.pool_with_listener_id,
                                   constants.HEALTH_MONITOR_HTTP,
                                   1, 1, 1, 1)
        self.set_lb_status(self.lb_id)
        api_member = self.create_member(
            self.pool_with_listener_id, '192.0.2.1', 80).get(self.root_tag)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=api_member.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            member_prov_status=constants.PENDING_CREATE,
            member_op_status=constants.OFFLINE)

    def test_duplicate_create(self):
        member = {'address': '192.0.2.1', 'protocol_port': 80,
                  'project_id': self.project_id}
        self.post(self.members_path, self._build_body(member))
        self.set_lb_status(self.lb_id)
        self.post(self.members_path, self._build_body(member), status=409)

    def test_create_with_bad_subnet(self):
        with mock.patch(
                'octavia.common.utils.get_network_driver') as net_mock:
            net_mock.return_value.get_subnet = mock.Mock(
                side_effect=network_base.SubnetNotFound('Subnet not found'))
            subnet_id = uuidutils.generate_uuid()
            response = self.create_member(self.pool_id, '192.0.2.1', 80,
                                          subnet_id=subnet_id, status=400)
            err_msg = 'Subnet ' + subnet_id + ' not found.'
            self.assertEqual(response.get('faultstring'), err_msg)

    def test_create_with_valid_subnet(self):
        with mock.patch(
                'octavia.common.utils.get_network_driver') as net_mock:
            subnet_id = uuidutils.generate_uuid()
            net_mock.return_value.get_subnet.return_value = subnet_id
            response = self.create_member(
                self.pool_id, '192.0.2.1', 80,
                subnet_id=subnet_id).get(self.root_tag)
            self.assertEqual('192.0.2.1', response['address'])
            self.assertEqual(80, response['protocol_port'])
            self.assertEqual(subnet_id, response['subnet_id'])

    def test_create_bad_port_number(self):
        member = {'address': '192.0.2.3',
                  'protocol_port': constants.MIN_PORT_NUMBER - 1}
        resp = self.post(self.members_path, self._build_body(member),
                         status=400)
        self.assertIn('Value should be greater or equal to',
                      resp.json.get('faultstring'))
        member = {'address': '192.0.2.3',
                  'protocol_port': constants.MAX_PORT_NUMBER + 1}
        resp = self.post(self.members_path, self._build_body(member),
                         status=400)
        self.assertIn('Value should be lower or equal to',
                      resp.json.get('faultstring'))

    def test_create_over_quota(self):
        self.start_quota_mock(data_models.Member)
        member = {'address': '192.0.2.3', 'protocol_port': 81}
        self.post(self.members_path, self._build_body(member), status=403)

    def test_update_with_attached_listener(self):
        old_name = "name1"
        new_name = "name2"
        api_member = self.create_member(
            self.pool_with_listener_id, '192.0.2.1', 80,
            name=old_name).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_member = {'name': new_name}
        response = self.put(
            self.member_path_listener.format(member_id=api_member.get('id')),
            self._build_body(new_member)).json.get(self.root_tag)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=api_member.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            member_prov_status=constants.PENDING_UPDATE)
        self.set_lb_status(self.lb_id)
        self.assertEqual(new_name, response.get('name'))
        self.assertEqual(api_member.get('created_at'),
                         response.get('created_at'))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=api_member.get('id'))

    def test_update_authorized(self):
        old_name = "name1"
        new_name = "name2"
        api_member = self.create_member(
            self.pool_with_listener_id, '192.0.2.1', 80,
            name=old_name, tags=['old_tag']).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_member = {'name': new_name, 'tags': ['new_tag']}
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                member_path = self.member_path_listener.format(
                    member_id=api_member.get('id'))
                response = self.put(
                    member_path,
                    self._build_body(new_member)).json.get(self.root_tag)

        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=api_member.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            member_prov_status=constants.PENDING_UPDATE)
        self.set_lb_status(self.lb_id)
        self.assertEqual(new_name, response.get('name'))
        self.assertEqual(['new_tag'], response['tags'])
        self.assertEqual(api_member.get('created_at'),
                         response.get('created_at'))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=api_member.get('id'))

    def test_update_not_authorized(self):
        old_name = "name1"
        new_name = "name2"
        api_member = self.create_member(
            self.pool_with_listener_id, '192.0.2.1', 80,
            name=old_name).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_member = {'name': new_name}
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            member_path = self.member_path_listener.format(
                member_id=api_member.get('id'))
            response = self.put(
                member_path,
                self._build_body(new_member), status=403)

        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response.json)

        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=api_member.get('id'),
            lb_prov_status=constants.ACTIVE,
            listener_prov_status=constants.ACTIVE,
            pool_prov_status=constants.ACTIVE,
            member_prov_status=constants.ACTIVE)

    def test_update_sans_listener(self):
        old_name = "name1"
        new_name = "name2"
        api_member = self.create_member(
            self.pool_id, '192.0.2.1', 80, name=old_name).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        member_path = self.member_path.format(
            member_id=api_member.get('id'))
        new_member = {'name': new_name}
        response = self.put(
            member_path, self._build_body(new_member)).json.get(self.root_tag)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id, member_id=api_member.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.ACTIVE,
            pool_prov_status=constants.PENDING_UPDATE,
            member_prov_status=constants.PENDING_UPDATE)
        self.set_lb_status(self.lb_id)
        self.assertEqual(new_name, response.get('name'))
        self.assertEqual(api_member.get('created_at'),
                         response.get('created_at'))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id, member_id=api_member.get('id'))

    def test_bad_update(self):
        api_member = self.create_member(
            self.pool_id, '192.0.2.1', 80).get(self.root_tag)
        new_member = {'protocol_port': 'ten'}
        self.put(self.member_path.format(member_id=api_member.get('id')),
                 self._build_body(new_member), status=400)

    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_update_with_bad_provider(self, mock_provider):
        api_member = self.create_member(
            self.pool_with_listener_id, '192.0.2.1', 80,
            name="member1").get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_member = {'name': "member2"}
        mock_provider.side_effect = exceptions.ProviderDriverError(
            prov='bad_driver', user_msg='broken')
        response = self.put(self.member_path_listener.format(
            member_id=api_member.get('id')), self._build_body(new_member),
            status=500)
        self.assertIn('Provider \'bad_driver\' reports error: broken',
                      response.json.get('faultstring'))

    def test_update_unset_defaults(self):
        old_name = "name1"
        api_member = self.create_member(
            self.pool_with_listener_id, '192.0.2.1', 80,
            name=old_name, backup=True, monitor_address='192.0.2.2',
            monitor_port=8888, weight=10).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        unset_params = {'name': None, 'backup': None, 'monitor_address': None,
                        'monitor_port': None, 'weight': None}
        member_path = self.member_path_listener.format(
            member_id=api_member.get('id'))
        response = self.put(member_path, self._build_body(unset_params))
        response = response.json.get(self.root_tag)

        self.assertFalse(response['backup'])
        self.assertIsNone(response['monitor_address'])
        self.assertIsNone(response['monitor_port'])
        self.assertEqual('', response['name'])
        self.assertEqual(constants.DEFAULT_WEIGHT, response['weight'])

    def test_delete(self):
        api_member = self.create_member(
            self.pool_with_listener_id, '192.0.2.1', 80).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        member = self.get(self.member_path_listener.format(
            member_id=api_member.get('id'))).json.get(self.root_tag)
        api_member['provisioning_status'] = constants.ACTIVE
        api_member['operating_status'] = constants.ONLINE
        self.assertIsNone(api_member.pop('updated_at'))
        self.assertIsNotNone(member.pop('updated_at'))
        self.assertEqual(api_member, member)
        self.delete(self.member_path_listener.format(
            member_id=api_member.get('id')))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=member.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            member_prov_status=constants.PENDING_DELETE)

        self.set_lb_status(self.lb_id)
        member = self.get(self.member_path_listener.format(
            member_id=api_member.get('id')), status=404)

    def test_delete_authorized(self):
        api_member = self.create_member(
            self.pool_with_listener_id, '192.0.2.1', 80).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        member = self.get(self.member_path_listener.format(
            member_id=api_member.get('id'))).json.get(self.root_tag)
        api_member['provisioning_status'] = constants.ACTIVE
        api_member['operating_status'] = constants.ONLINE
        self.assertIsNone(api_member.pop('updated_at'))
        self.assertIsNotNone(member.pop('updated_at'))
        self.assertEqual(api_member, member)

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                self.delete(self.member_path_listener.format(
                    member_id=api_member.get('id')))
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=member.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            member_prov_status=constants.PENDING_DELETE)

        self.set_lb_status(self.lb_id)
        member = self.get(self.member_path_listener.format(
            member_id=api_member.get('id')), status=404)

    def test_delete_not_authorized(self):
        api_member = self.create_member(
            self.pool_with_listener_id, '192.0.2.1', 80).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        member = self.get(self.member_path_listener.format(
            member_id=api_member.get('id'))).json.get(self.root_tag)
        api_member['provisioning_status'] = constants.ACTIVE
        api_member['operating_status'] = constants.ONLINE
        self.assertIsNone(api_member.pop('updated_at'))
        self.assertIsNotNone(member.pop('updated_at'))
        self.assertEqual(api_member, member)

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            self.delete(self.member_path_listener.format(
                member_id=api_member.get('id')), status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=member.get('id'),
            lb_prov_status=constants.ACTIVE,
            listener_prov_status=constants.ACTIVE,
            pool_prov_status=constants.ACTIVE,
            member_prov_status=constants.ACTIVE)

    def test_bad_delete(self):
        self.delete(self.member_path.format(
            member_id=uuidutils.generate_uuid()), status=404)

    def test_delete_mismatch_pool(self):
        # Create a pool that will not have the member, but is valid.
        self.pool = self.create_pool(self.lb_id, constants.PROTOCOL_HTTP,
                                     constants.LB_ALGORITHM_ROUND_ROBIN)
        bad_pool_id = self.pool.get('pool').get('id')
        self.set_lb_status(self.lb_id)
        # Create a member on our reference pool
        api_member = self.create_member(
            self.pool_with_listener_id, '192.0.2.1', 80).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        # Attempt to delete the member using the wrong pool in the path
        member_path = self.MEMBERS_PATH.format(
            pool_id=bad_pool_id) + '/' + api_member['id']
        result = self.delete(member_path, status=404).json
        ref_msg = 'Member %s not found.' % api_member['id']
        self.assertEqual(ref_msg, result.get('faultstring'))

    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_delete_with_bad_provider(self, mock_provider):
        api_member = self.create_member(
            self.pool_with_listener_id, '192.0.2.1', 80).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        member = self.get(self.member_path_listener.format(
            member_id=api_member.get('id'))).json.get(self.root_tag)
        api_member['provisioning_status'] = constants.ACTIVE
        api_member['operating_status'] = constants.ONLINE
        self.assertIsNone(api_member.pop('updated_at'))
        self.assertIsNotNone(member.pop('updated_at'))
        self.assertEqual(api_member, member)

        mock_provider.side_effect = exceptions.ProviderDriverError(
            prov='bad_driver', user_msg='broken')
        self.delete(self.member_path_listener.format(
            member_id=api_member.get('id')), status=500)

    def test_create_when_lb_pending_update(self):
        self.create_member(self.pool_id, address="192.0.2.2",
                           protocol_port=80)
        self.set_lb_status(self.lb_id)
        self.put(self.LB_PATH.format(lb_id=self.lb_id),
                 body={'loadbalancer': {'name': 'test_name_change'}})
        member = {'address': '192.0.2.1', 'protocol_port': 80,
                  'project_id': self.project_id}
        self.post(self.members_path,
                  body=self._build_body(member),
                  status=409)

    def test_update_when_lb_pending_update(self):
        member = self.create_member(
            self.pool_id, address="192.0.2.1", protocol_port=80,
            name="member1").get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.put(self.LB_PATH.format(lb_id=self.lb_id),
                 body={'loadbalancer': {'name': 'test_name_change'}})
        self.put(
            self.member_path.format(member_id=member.get('id')),
            body=self._build_body({'name': "member2"}), status=409)

    def test_delete_when_lb_pending_update(self):
        member = self.create_member(
            self.pool_id, address="192.0.2.1",
            protocol_port=80).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.put(self.LB_PATH.format(lb_id=self.lb_id),
                 body={'loadbalancer': {'name': 'test_name_change'}})
        self.delete(self.member_path.format(
            member_id=member.get('id')), status=409)

    def test_create_when_lb_pending_delete(self):
        self.create_member(self.pool_id, address="192.0.2.1",
                           protocol_port=80)
        self.set_lb_status(self.lb_id)
        self.delete(self.LB_PATH.format(lb_id=self.lb_id),
                    params={'cascade': "true"})
        member = {'address': '192.0.2.2', 'protocol_port': 88,
                  'project_id': self.project_id}
        self.post(self.members_path, body=self._build_body(member),
                  status=409)

    def test_update_when_lb_pending_delete(self):
        member = self.create_member(
            self.pool_id, address="192.0.2.1", protocol_port=80,
            name="member1").get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.delete(self.LB_PATH.format(lb_id=self.lb_id),
                    params={'cascade': "true"})
        self.put(self.member_path.format(member_id=member.get('id')),
                 body=self._build_body({'name': "member2"}), status=409)

    def test_update_when_deleted(self):
        member = self.create_member(
            self.pool_id, address="10.0.0.1",
            protocol_port=80).get(self.root_tag)
        self.set_lb_status(self.lb_id, status=constants.DELETED)
        self.put(self.member_path.format(member_id=member.get('id')),
                 body=self._build_body({'name': "member2"}), status=404)

    def test_delete_when_lb_pending_delete(self):
        member = self.create_member(
            self.pool_id, address="192.0.2.1",
            protocol_port=80).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.delete(self.LB_PATH.format(lb_id=self.lb_id),
                    params={'cascade': "true"})
        self.delete(self.member_path.format(
            member_id=member.get('id')), status=409)

    def test_delete_already_deleted(self):
        member = self.create_member(
            self.pool_id, address="192.0.2.1",
            protocol_port=80).get(self.root_tag)
        self.set_lb_status(self.lb_id, status=constants.DELETED)
        self.delete(self.member_path.format(
            member_id=member.get('id')), status=404)
