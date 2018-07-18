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

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.common import constants
import octavia.common.context
from octavia.tests.functional.api.v2 import base


class TestAmphora(base.BaseAPITest):

    root_tag = 'amphora'
    root_tag_list = 'amphorae'
    root_tag_links = 'amphorae_links'

    def setUp(self):
        super(TestAmphora, self).setUp()
        self.lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')
        self.lb_id = self.lb.get('id')
        self.project_id = self.lb.get('project_id')
        self.set_lb_status(self.lb_id)
        self.amp_args = {
            'load_balancer_id': self.lb_id,
            'compute_id': uuidutils.generate_uuid(),
            'lb_network_ip': '192.168.1.2',
            'vrrp_ip': '192.168.1.5',
            'ha_ip': '192.168.1.10',
            'vrrp_port_id': uuidutils.generate_uuid(),
            'ha_port_id': uuidutils.generate_uuid(),
            'cert_expiration': datetime.datetime.now(),
            'cert_busy': False,
            'role': constants.ROLE_STANDALONE,
            'status': constants.AMPHORA_ALLOCATED,
            'vrrp_interface': 'eth1',
            'vrrp_id': 1,
            'vrrp_priority': 100,
            'cached_zone': None
        }
        self.amp = self.amphora_repo.create(self.session, **self.amp_args)
        self.amp_id = self.amp.id
        self.amp_args['id'] = self.amp_id

    def _create_additional_amp(self):
        amp_args = {
            'load_balancer_id': None,
            'compute_id': uuidutils.generate_uuid(),
            'lb_network_ip': '192.168.1.2',
            'vrrp_ip': '192.168.1.5',
            'ha_ip': '192.168.1.10',
            'vrrp_port_id': uuidutils.generate_uuid(),
            'ha_port_id': uuidutils.generate_uuid(),
            'cert_expiration': None,
            'cert_busy': False,
            'role': constants.ROLE_MASTER,
            'status': constants.AMPHORA_READY,
            'vrrp_interface': 'eth1',
            'vrrp_id': 1,
            'vrrp_priority': 100,
        }
        return self.amphora_repo.create(self.session, **amp_args)

    def _assert_amp_equal(self, source, response):
        self.assertEqual(source.pop('load_balancer_id'),
                         response.pop('loadbalancer_id'))
        self.assertEqual(source.pop('cert_expiration').isoformat(),
                         response.pop('cert_expiration'))
        self.assertEqual(source, response)

    def test_get(self):
        response = self.get(self.AMPHORA_PATH.format(
            amphora_id=self.amp_id)).json.get(self.root_tag)
        self._assert_amp_equal(self.amp_args, response)

    def test_failover(self):
        self.put(self.AMPHORA_FAILOVER_PATH.format(
            amphora_id=self.amp_id), body={}, status=202)
        self.handler_mock().amphora.failover.assert_has_calls(
            [mock.call(self.amp)]
        )

    def test_failover_bad_amp_id(self):
        self.put(self.AMPHORA_FAILOVER_PATH.format(
            amphora_id='asdf'), body={}, status=404)
        self.assertFalse(self.handler_mock().amphora.failover.called)

    def test_get_authorized(self):
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
                'is_admin': True,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                response = self.get(self.AMPHORA_PATH.format(
                    amphora_id=self.amp_id)).json.get(self.root_tag)
        # Reset api auth setting
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        self._assert_amp_equal(self.amp_args, response)

    def test_get_not_authorized(self):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            response = self.get(self.AMPHORA_PATH.format(
                amphora_id=self.amp_id), status=403)
        # Reset api auth setting
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response.json)

    def test_get_hides_deleted(self):
        new_amp = self._create_additional_amp()

        response = self.get(self.AMPHORAE_PATH)
        objects = response.json.get(self.root_tag_list)
        self.assertEqual(len(objects), 2)
        self.amphora_repo.update(self.session, new_amp.id,
                                 status=constants.DELETED)
        response = self.get(self.AMPHORAE_PATH)
        objects = response.json.get(self.root_tag_list)
        self.assertEqual(len(objects), 1)

    def test_bad_get(self):
        self.get(self.AMPHORA_PATH.format(
            amphora_id=uuidutils.generate_uuid()), status=404)

    def test_get_all(self):
        amps = self.get(self.AMPHORAE_PATH).json.get(self.root_tag_list)
        self.assertIsInstance(amps, list)
        self.assertEqual(1, len(amps))
        self.assertEqual(self.amp_id, amps[0].get('id'))

    def test_get_all_authorized(self):
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': True,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                amps = self.get(self.AMPHORAE_PATH).json.get(
                    self.root_tag_list)

        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertIsInstance(amps, list)
        self.assertEqual(1, len(amps))
        self.assertEqual(self.amp_id, amps[0].get('id'))

    def test_get_all_not_authorized(self):
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            amps = self.get(self.AMPHORAE_PATH, status=403).json

        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, amps)

    def test_get_by_loadbalancer_id(self):
        amps = self.get(
            self.AMPHORAE_PATH,
            params={'loadbalancer_id': self.lb_id}
        ).json.get(self.root_tag_list)

        self.assertEqual(1, len(amps))
        amps = self.get(
            self.AMPHORAE_PATH,
            params={'loadbalancer_id': uuidutils.generate_uuid()}
        ).json.get(self.root_tag_list)
        self.assertEqual(0, len(amps))

    def test_get_by_project_id(self):
        amps = self.get(
            self.AMPHORAE_PATH,
            params={'project_id': self.project_id}
        ).json.get(self.root_tag_list)
        self.assertEqual(1, len(amps))

        false_project_id = uuidutils.generate_uuid()
        amps = self.get(
            self.AMPHORAE_PATH,
            params={'project_id': false_project_id}
        ).json.get(self.root_tag_list)

        self.assertEqual(int(false_project_id == self.project_id),
                         len(amps))

    def test_get_all_sorted(self):
        self._create_additional_amp()

        response = self.get(self.AMPHORAE_PATH, params={'sort': 'role:desc'})
        amps_desc = response.json.get(self.root_tag_list)
        response = self.get(self.AMPHORAE_PATH, params={'sort': 'role:asc'})
        amps_asc = response.json.get(self.root_tag_list)

        self.assertEqual(2, len(amps_desc))
        self.assertEqual(2, len(amps_asc))

        amp_id_roles_desc = [(amp.get('id'), amp.get('role'))
                             for amp in amps_desc]
        amp_id_roles_asc = [(amp.get('id'), amp.get('role'))
                            for amp in amps_asc]
        self.assertEqual(amp_id_roles_asc, list(reversed(amp_id_roles_desc)))

    def test_get_all_limited(self):
        self._create_additional_amp()
        self._create_additional_amp()

        # First two -- should have 'next' link
        first_two = self.get(self.AMPHORAE_PATH, params={'limit': 2}).json
        objs = first_two[self.root_tag_list]
        links = first_two[self.root_tag_links]
        self.assertEqual(2, len(objs))
        self.assertEqual(1, len(links))
        self.assertEqual('next', links[0]['rel'])

        # Third + off the end -- should have previous link
        third = self.get(self.AMPHORAE_PATH, params={
            'limit': 2,
            'marker': first_two[self.root_tag_list][1]['id']}).json
        objs = third[self.root_tag_list]
        links = third[self.root_tag_links]
        self.assertEqual(1, len(objs))
        self.assertEqual(1, len(links))
        self.assertEqual('previous', links[0]['rel'])

        # Middle -- should have both links
        middle = self.get(self.AMPHORAE_PATH, params={
            'limit': 1,
            'marker': first_two[self.root_tag_list][0]['id']}).json
        objs = middle[self.root_tag_list]
        links = middle[self.root_tag_links]
        self.assertEqual(1, len(objs))
        self.assertEqual(2, len(links))
        self.assertItemsEqual(['previous', 'next'], [l['rel'] for l in links])

    def test_get_all_fields_filter(self):
        amps = self.get(self.AMPHORAE_PATH, params={
            'fields': ['id', 'role']}).json
        for amp in amps['amphorae']:
            self.assertIn(u'id', amp)
            self.assertIn(u'role', amp)
            self.assertNotIn(u'ha_port_id', amp)

    def test_get_one_fields_filter(self):
        amp = self.get(
            self.AMPHORA_PATH.format(amphora_id=self.amp_id),
            params={'fields': ['id', 'role']}).json.get(self.root_tag)
        self.assertIn(u'id', amp)
        self.assertIn(u'role', amp)
        self.assertNotIn(u'ha_port_id', amp)

    def test_get_all_filter(self):
        self._create_additional_amp()

        amps = self.get(self.AMPHORAE_PATH, params={
            'id': self.amp_id}).json.get(self.root_tag_list)
        self.assertEqual(1, len(amps))
        self.assertEqual(self.amp_id,
                         amps[0]['id'])

    def test_empty_get_all(self):
        self.amphora_repo.delete(self.session, id=self.amp_id)
        response = self.get(self.AMPHORAE_PATH).json.get(self.root_tag_list)
        self.assertIsInstance(response, list)
        self.assertEqual(0, len(response))
