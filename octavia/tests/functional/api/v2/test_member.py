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
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.common import constants
import octavia.common.context
from octavia.common import data_models
from octavia.network import base as network_base
from octavia.tests.functional.api.v2 import base

import testtools


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

    def test_get(self):
        api_member = self.create_member(
            self.pool_id, '10.0.0.1', 80).get(self.root_tag)
        response = self.get(self.member_path.format(
            member_id=api_member.get('id'))).json.get(self.root_tag)
        self.assertEqual(api_member, response)
        self.assertEqual(api_member.get('name'), '')

    def test_get_authorized(self):
        api_member = self.create_member(
            self.pool_id, '10.0.0.1', 80).get(self.root_tag)
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
            self.pool_id, '10.0.0.1', 80).get(self.root_tag)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            response = self.get(self.member_path.format(
                member_id=api_member.get('id')), status=403).json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response)

    def test_get_hides_deleted(self):
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

    def test_bad_get(self):
        self.get(self.member_path.format(member_id=uuidutils.generate_uuid()),
                 status=404)

    def test_get_all(self):
        api_m_1 = self.create_member(
            self.pool_id, '10.0.0.1', 80).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        api_m_2 = self.create_member(
            self.pool_id, '10.0.0.2', 80).get(self.root_tag)
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

    def test_get_all_authorized(self):
        api_m_1 = self.create_member(
            self.pool_id, '10.0.0.1', 80).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        api_m_2 = self.create_member(
            self.pool_id, '10.0.0.2', 80).get(self.root_tag)
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
            self.pool_id, '10.0.0.1', 80).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        api_m_2 = self.create_member(
            self.pool_id, '10.0.0.2', 80).get(self.root_tag)
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
        self.create_member(self.pool_id, '10.0.0.1', 80, name='member1')
        self.set_lb_status(self.lb_id)
        self.create_member(self.pool_id, '10.0.0.2', 80, name='member2')
        self.set_lb_status(self.lb_id)
        self.create_member(self.pool_id, '10.0.0.3', 80, name='member3')
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
        self.create_member(self.pool_id, '10.0.0.1', 80, name='member1')
        self.set_lb_status(self.lb_id)
        self.create_member(self.pool_id, '10.0.0.2', 80, name='member2')
        self.set_lb_status(self.lb_id)
        self.create_member(self.pool_id, '10.0.0.3', 80, name='member3')
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
        self.create_member(self.pool_id, '10.0.0.1', 80, name='member1')
        self.set_lb_status(self.lb_id)
        self.create_member(self.pool_id, '10.0.0.2', 80, name='member2')
        self.set_lb_status(self.lb_id)
        self.create_member(self.pool_id, '10.0.0.3', 80, name='member3')
        self.set_lb_status(self.lb_id)

        members = self.get(self.members_path, params={
            'fields': ['id', 'project_id']}).json
        for member in members['members']:
            self.assertIn(u'id', member.keys())
            self.assertIn(u'project_id', member.keys())
            self.assertNotIn(u'description', member.keys())

    def test_get_all_filter(self):
        mem1 = self.create_member(self.pool_id,
                                  '10.0.0.1',
                                  80,
                                  name='member1').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_member(self.pool_id,
                           '10.0.0.2',
                           80,
                           name='member2').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_member(self.pool_id,
                           '10.0.0.3',
                           80,
                           name='member3').get(self.root_tag)
        self.set_lb_status(self.lb_id)

        members = self.get(self.members_path, params={
            'id': mem1['id']}).json
        self.assertEqual(1, len(members['members']))
        self.assertEqual(mem1['id'],
                         members['members'][0]['id'])

    def test_empty_get_all(self):
        response = self.get(self.members_path).json.get(self.root_tag_list)
        self.assertIsInstance(response, list)
        self.assertEqual(0, len(response))

    def test_create_sans_listener(self):
        api_member = self.create_member(
            self.pool_id, '10.0.0.1', 80).get(self.root_tag)
        self.assertEqual('10.0.0.1', api_member['address'])
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
                    self.pool_id, '10.0.0.1', 80).get(self.root_tag)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        self.assertEqual('10.0.0.1', api_member['address'])
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

    def test_create_not_authorized(self):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)

        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            api_member = self.create_member(
                self.pool_id, '10.0.0.1', 80, status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, api_member)

    # TODO(rm_work) Remove after deprecation of project_id in POST (R series)
    def test_create_with_project_id_is_ignored(self):
        pid = uuidutils.generate_uuid()
        api_member = self.create_member(
            self.pool_id, '10.0.0.1', 80, project_id=pid).get(self.root_tag)
        self.assertEqual(self.project_id, api_member['project_id'])

    def test_bad_create(self):
        member = {'name': 'test1'}
        self.post(self.members_path, self._build_body(member), status=400)

    def test_create_with_bad_handler(self):
        self.handler_mock().member.create.side_effect = Exception()
        api_member = self.create_member(
            self.pool_with_listener_id, '10.0.0.1', 80).get(self.root_tag)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id,
            member_id=api_member.get('id'),
            lb_prov_status=constants.ACTIVE,
            listener_prov_status=constants.ACTIVE,
            pool_prov_status=constants.ACTIVE,
            member_prov_status=constants.ERROR,
            member_op_status=constants.NO_MONITOR)

    def test_create_with_attached_listener(self):
        api_member = self.create_member(
            self.pool_with_listener_id, '10.0.0.1', 80).get(self.root_tag)
        self.assertEqual('10.0.0.1', api_member['address'])
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
            self.pool_with_listener_id, '10.0.0.1', 80,
            monitor_address='192.0.2.3',
            monitor_port=80).get(self.root_tag)
        self.assertEqual('10.0.0.1', api_member['address'])
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

    @testtools.skip("Enable this with v2 Health Monitor patch")
    def test_create_with_health_monitor(self):
        self.create_health_monitor_with_listener(
            self.lb_id, self.listener_id, self.pool_with_listener_id,
            constants.HEALTH_MONITOR_PING, 1, 1, 1, 1)
        api_member = self.create_member(
            self.pool_with_listener_id, '10.0.0.1', 80).get(self.root_tag)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=api_member.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            member_prov_status=constants.PENDING_CREATE,
            member_op_status=constants.OFFLINE)

    def test_duplicate_create(self):
        member = {'address': '10.0.0.1', 'protocol_port': 80,
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
            response = self.create_member(self.pool_id, '10.0.0.1', 80,
                                          subnet_id=subnet_id, status=400)
            err_msg = 'Subnet ' + subnet_id + ' not found.'
            self.assertEqual(response.get('faultstring'), err_msg)

    def test_create_with_valid_subnet(self):
        with mock.patch(
                'octavia.common.utils.get_network_driver') as net_mock:
            subnet_id = uuidutils.generate_uuid()
            net_mock.return_value.get_subnet.return_value = subnet_id
            response = self.create_member(
                self.pool_id, '10.0.0.1', 80,
                subnet_id=subnet_id).get(self.root_tag)
            self.assertEqual('10.0.0.1', response['address'])
            self.assertEqual(80, response['protocol_port'])
            self.assertEqual(subnet_id, response['subnet_id'])

    def test_create_bad_port_number(self):
        member = {'address': '10.0.0.3',
                  'protocol_port': constants.MIN_PORT_NUMBER - 1}
        resp = self.post(self.members_path, self._build_body(member),
                         status=400)
        self.assertIn('Value should be greater or equal to',
                      resp.json.get('faultstring'))
        member = {'address': '10.0.0.3',
                  'protocol_port': constants.MAX_PORT_NUMBER + 1}
        resp = self.post(self.members_path, self._build_body(member),
                         status=400)
        self.assertIn('Value should be lower or equal to',
                      resp.json.get('faultstring'))

    def test_create_over_quota(self):
        self.start_quota_mock(data_models.Member)
        member = {'address': '10.0.0.3', 'protocol_port': 81}
        self.post(self.members_path, self._build_body(member), status=403)

    def test_update_with_attached_listener(self):
        old_name = "name1"
        new_name = "name2"
        api_member = self.create_member(
            self.pool_with_listener_id, '10.0.0.1', 80,
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
        self.assertEqual(old_name, response.get('name'))
        self.assertEqual(api_member.get('created_at'),
                         response.get('created_at'))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=api_member.get('id'))

    def test_update_authorized(self):
        old_name = "name1"
        new_name = "name2"
        api_member = self.create_member(
            self.pool_with_listener_id, '10.0.0.1', 80,
            name=old_name).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_member = {'name': new_name}
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
        self.assertEqual(old_name, response.get('name'))
        self.assertEqual(api_member.get('created_at'),
                         response.get('created_at'))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=api_member.get('id'))

    def test_update_not_authorized(self):
        old_name = "name1"
        new_name = "name2"
        api_member = self.create_member(
            self.pool_with_listener_id, '10.0.0.1', 80,
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
            self.pool_id, '10.0.0.1', 80, name=old_name).get(self.root_tag)
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
        self.assertEqual(old_name, response.get('name'))
        self.assertEqual(api_member.get('created_at'),
                         response.get('created_at'))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id, member_id=api_member.get('id'))

    def test_bad_update(self):
        api_member = self.create_member(
            self.pool_id, '10.0.0.1', 80).get(self.root_tag)
        new_member = {'protocol_port': 'ten'}
        self.put(self.member_path.format(member_id=api_member.get('id')),
                 self._build_body(new_member), status=400)

    def test_update_with_bad_handler(self):
        api_member = self.create_member(
            self.pool_with_listener_id, '10.0.0.1', 80,
            name="member1").get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_member = {'name': "member2"}
        self.handler_mock().member.update.side_effect = Exception()
        self.put(self.member_path_listener.format(
            member_id=api_member.get('id')), self._build_body(new_member))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=api_member.get('id'),
            member_prov_status=constants.ERROR)

    def test_delete(self):
        api_member = self.create_member(
            self.pool_with_listener_id, '10.0.0.1', 80).get(self.root_tag)
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
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=member.get('id'),
            lb_prov_status=constants.ACTIVE,
            listener_prov_status=constants.ACTIVE,
            pool_prov_status=constants.ACTIVE,
            member_prov_status=constants.DELETED)

    def test_delete_authorized(self):
        api_member = self.create_member(
            self.pool_with_listener_id, '10.0.0.1', 80).get(self.root_tag)
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
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=member.get('id'),
            lb_prov_status=constants.ACTIVE,
            listener_prov_status=constants.ACTIVE,
            pool_prov_status=constants.ACTIVE,
            member_prov_status=constants.DELETED)

    def test_delete_not_authorized(self):
        api_member = self.create_member(
            self.pool_with_listener_id, '10.0.0.1', 80).get(self.root_tag)
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

    def test_delete_with_bad_handler(self):
        api_member = self.create_member(
            self.pool_with_listener_id, '10.0.0.1', 80).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        member = self.get(self.member_path_listener.format(
            member_id=api_member.get('id'))).json.get(self.root_tag)
        api_member['provisioning_status'] = constants.ACTIVE
        api_member['operating_status'] = constants.ONLINE
        self.assertIsNone(api_member.pop('updated_at'))
        self.assertIsNotNone(member.pop('updated_at'))
        self.assertEqual(api_member, member)
        self.handler_mock().member.delete.side_effect = Exception()
        self.delete(self.member_path_listener.format(
            member_id=api_member.get('id')))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, member_id=member.get('id'),
            lb_prov_status=constants.ACTIVE,
            listener_prov_status=constants.ACTIVE,
            pool_prov_status=constants.ACTIVE,
            member_prov_status=constants.ERROR)

    def test_create_when_lb_pending_update(self):
        self.create_member(self.pool_id, address="10.0.0.2",
                           protocol_port=80)
        self.set_lb_status(self.lb_id)
        self.put(self.LB_PATH.format(lb_id=self.lb_id),
                 body={'loadbalancer': {'name': 'test_name_change'}})
        member = {'address': '10.0.0.1', 'protocol_port': 80,
                  'project_id': self.project_id}
        self.post(self.members_path,
                  body=self._build_body(member),
                  status=409)

    def test_update_when_lb_pending_update(self):
        member = self.create_member(
            self.pool_id, address="10.0.0.1", protocol_port=80,
            name="member1").get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.put(self.LB_PATH.format(lb_id=self.lb_id),
                 body={'loadbalancer': {'name': 'test_name_change'}})
        self.put(
            self.member_path.format(member_id=member.get('id')),
            body=self._build_body({'name': "member2"}), status=409)

    def test_delete_when_lb_pending_update(self):
        member = self.create_member(
            self.pool_id, address="10.0.0.1",
            protocol_port=80).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.put(self.LB_PATH.format(lb_id=self.lb_id),
                 body={'loadbalancer': {'name': 'test_name_change'}})
        self.delete(self.member_path.format(
            member_id=member.get('id')), status=409)

    def test_create_when_lb_pending_delete(self):
        self.create_member(self.pool_id, address="10.0.0.1",
                           protocol_port=80)
        self.set_lb_status(self.lb_id)
        self.delete(self.LB_PATH.format(lb_id=self.lb_id),
                    params={'cascade': "true"})
        member = {'address': '10.0.0.2', 'protocol_port': 88,
                  'project_id': self.project_id}
        self.post(self.members_path, body=self._build_body(member),
                  status=409)

    def test_update_when_lb_pending_delete(self):
        member = self.create_member(
            self.pool_id, address="10.0.0.1", protocol_port=80,
            name="member1").get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.delete(self.LB_PATH.format(lb_id=self.lb_id),
                    params={'cascade': "true"})
        self.put(self.member_path.format(member_id=member.get('id')),
                 body=self._build_body({'name': "member2"}), status=409)

    def test_delete_when_lb_pending_delete(self):
        member = self.create_member(
            self.pool_id, address="10.0.0.1",
            protocol_port=80).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.delete(self.LB_PATH.format(lb_id=self.lb_id),
                    params={'cascade': "true"})
        self.delete(self.member_path.format(
            member_id=member.get('id')), status=409)
