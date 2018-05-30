#    Copyright 2014 Rackspace
#    Copyright 2016 Blue Box, an IBM Company
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

import random

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.common import constants
import octavia.common.context
from octavia.common import data_models
from octavia.common import exceptions
from octavia.tests.functional.api.v2 import base


class TestListener(base.BaseAPITest):

    root_tag = 'listener'
    root_tag_list = 'listeners'
    root_tag_links = 'listeners_links'

    def setUp(self):
        super(TestListener, self).setUp()
        self.lb = self.create_load_balancer(uuidutils.generate_uuid())
        self.lb_id = self.lb.get('loadbalancer').get('id')
        self.project_id = self.lb.get('loadbalancer').get('project_id')
        self.set_lb_status(self.lb_id)
        self.listener_path = self.LISTENERS_PATH + '/{listener_id}'
        self.pool = self.create_pool(
            self.lb_id, constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN)
        self.pool_id = self.pool.get('pool').get('id')
        self.set_lb_status(self.lb_id)

    def test_get_all_admin(self):
        project_id = uuidutils.generate_uuid()
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb1', project_id=project_id)
        lb1_id = lb1.get('loadbalancer').get('id')
        self.set_lb_status(lb1_id)
        listener1 = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb1_id).get(self.root_tag)
        self.set_lb_status(lb1_id)
        listener2 = self.create_listener(
            constants.PROTOCOL_HTTP, 81, lb1_id).get(self.root_tag)
        self.set_lb_status(lb1_id)
        listener3 = self.create_listener(
            constants.PROTOCOL_HTTP, 82, lb1_id).get(self.root_tag)
        self.set_lb_status(lb1_id)
        listeners = self.get(self.LISTENERS_PATH).json.get(self.root_tag_list)
        self.assertEqual(3, len(listeners))
        listener_id_ports = [(l.get('id'), l.get('protocol_port'))
                             for l in listeners]
        self.assertIn((listener1.get('id'), listener1.get('protocol_port')),
                      listener_id_ports)
        self.assertIn((listener2.get('id'), listener2.get('protocol_port')),
                      listener_id_ports)
        self.assertIn((listener3.get('id'), listener3.get('protocol_port')),
                      listener_id_ports)

    def test_get_all_non_admin(self):
        project_id = uuidutils.generate_uuid()
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb1', project_id=project_id)
        lb1_id = lb1.get('loadbalancer').get('id')
        self.set_lb_status(lb1_id)
        self.create_listener(constants.PROTOCOL_HTTP, 80,
                             lb1_id)
        self.set_lb_status(lb1_id)
        self.create_listener(constants.PROTOCOL_HTTP, 81,
                             lb1_id)
        self.set_lb_status(lb1_id)
        listener3 = self.create_listener(constants.PROTOCOL_HTTP, 82,
                                         self.lb_id).get(self.root_tag)
        self.set_lb_status(self.lb_id)

        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings',
                         auth_strategy=constants.KEYSTONE)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               listener3['project_id']):
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
                listeners = self.get(
                    self.LISTENERS_PATH).json.get(self.root_tag_list)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        self.assertEqual(1, len(listeners))
        listener_id_ports = [(l.get('id'), l.get('protocol_port'))
                             for l in listeners]
        self.assertIn((listener3.get('id'), listener3.get('protocol_port')),
                      listener_id_ports)

    def test_get_all_non_admin_global_observer(self):
        project_id = uuidutils.generate_uuid()
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb1', project_id=project_id)
        lb1_id = lb1.get('loadbalancer').get('id')
        self.set_lb_status(lb1_id)
        listener1 = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb1_id).get(self.root_tag)
        self.set_lb_status(lb1_id)
        listener2 = self.create_listener(
            constants.PROTOCOL_HTTP, 81, lb1_id).get(self.root_tag)
        self.set_lb_status(lb1_id)
        listener3 = self.create_listener(
            constants.PROTOCOL_HTTP, 82, lb1_id).get(self.root_tag)
        self.set_lb_status(lb1_id)

        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings',
                         auth_strategy=constants.KEYSTONE)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_global_observer'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                listeners = self.get(self.LISTENERS_PATH)
                listeners = listeners.json.get(self.root_tag_list)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        self.assertEqual(3, len(listeners))
        listener_id_ports = [(l.get('id'), l.get('protocol_port'))
                             for l in listeners]
        self.assertIn((listener1.get('id'), listener1.get('protocol_port')),
                      listener_id_ports)
        self.assertIn((listener2.get('id'), listener2.get('protocol_port')),
                      listener_id_ports)
        self.assertIn((listener3.get('id'), listener3.get('protocol_port')),
                      listener_id_ports)

    def test_get_all_not_authorized(self):
        project_id = uuidutils.generate_uuid()
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb1', project_id=project_id)
        lb1_id = lb1.get('loadbalancer').get('id')
        self.set_lb_status(lb1_id)
        self.create_listener(constants.PROTOCOL_HTTP, 80,
                             lb1_id)
        self.set_lb_status(lb1_id)
        self.create_listener(constants.PROTOCOL_HTTP, 81,
                             lb1_id)
        self.set_lb_status(lb1_id)
        self.create_listener(constants.PROTOCOL_HTTP, 82,
                             self.lb_id).get(self.root_tag)
        self.set_lb_status(self.lb_id)

        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings',
                         auth_strategy=constants.KEYSTONE)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            listeners = self.get(self.LISTENERS_PATH, status=403).json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, listeners)

    def test_get_all_by_project_id(self):
        project1_id = uuidutils.generate_uuid()
        project2_id = uuidutils.generate_uuid()
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(), name='lb1',
                                        project_id=project1_id)
        lb1_id = lb1.get('loadbalancer').get('id')
        self.set_lb_status(lb1_id)
        lb2 = self.create_load_balancer(uuidutils.generate_uuid(), name='lb2',
                                        project_id=project2_id)
        lb2_id = lb2.get('loadbalancer').get('id')

        self.set_lb_status(lb2_id)
        listener1 = self.create_listener(constants.PROTOCOL_HTTP, 80, lb1_id,
                                         name='listener1').get(self.root_tag)
        self.set_lb_status(lb1_id)
        listener2 = self.create_listener(constants.PROTOCOL_HTTP, 81, lb1_id,
                                         name='listener2').get(self.root_tag)
        self.set_lb_status(lb1_id)
        listener3 = self.create_listener(constants.PROTOCOL_HTTP, 82, lb2_id,
                                         name='listener3').get(self.root_tag)
        self.set_lb_status(lb2_id)
        listeners = self.get(
            self.LISTENERS_PATH,
            params={'project_id': project1_id}).json.get(self.root_tag_list)

        self.assertEqual(2, len(listeners))
        listener_id_ports = [(l.get('id'), l.get('protocol_port'))
                             for l in listeners]
        self.assertIn((listener1.get('id'), listener1.get('protocol_port')),
                      listener_id_ports)
        self.assertIn((listener2.get('id'), listener2.get('protocol_port')),
                      listener_id_ports)
        listeners = self.get(
            self.LISTENERS_PATH,
            params={'project_id': project2_id}).json.get(self.root_tag_list)
        listener_id_ports = [(l.get('id'), l.get('protocol_port'))
                             for l in listeners]
        self.assertEqual(1, len(listeners))
        self.assertIn((listener3.get('id'), listener3.get('protocol_port')),
                      listener_id_ports)

    def test_get_all_sorted(self):
        self.create_listener(constants.PROTOCOL_HTTP, 80,
                             self.lb_id,
                             name='listener1')
        self.set_lb_status(self.lb_id)
        self.create_listener(constants.PROTOCOL_HTTP, 81,
                             self.lb_id,
                             name='listener2')
        self.set_lb_status(self.lb_id)
        self.create_listener(constants.PROTOCOL_HTTP, 82,
                             self.lb_id,
                             name='listener3')
        self.set_lb_status(self.lb_id)
        response = self.get(self.LISTENERS_PATH,
                            params={'sort': 'name:desc'})
        listeners_desc = response.json.get(self.root_tag_list)
        response = self.get(self.LISTENERS_PATH,
                            params={'sort': 'name:asc'})
        listeners_asc = response.json.get(self.root_tag_list)

        self.assertEqual(3, len(listeners_desc))
        self.assertEqual(3, len(listeners_asc))

        listener_id_names_desc = [(listener.get('id'), listener.get('name'))
                                  for listener in listeners_desc]
        listener_id_names_asc = [(listener.get('id'), listener.get('name'))
                                 for listener in listeners_asc]
        self.assertEqual(listener_id_names_asc,
                         list(reversed(listener_id_names_desc)))

    def test_get_all_limited(self):
        self.create_listener(constants.PROTOCOL_HTTP, 80,
                             self.lb_id,
                             name='listener1')
        self.set_lb_status(self.lb_id)
        self.create_listener(constants.PROTOCOL_HTTP, 81,
                             self.lb_id,
                             name='listener2')
        self.set_lb_status(self.lb_id)
        self.create_listener(constants.PROTOCOL_HTTP, 82,
                             self.lb_id,
                             name='listener3')
        self.set_lb_status(self.lb_id)

        # First two -- should have 'next' link
        first_two = self.get(self.LISTENERS_PATH, params={'limit': 2}).json
        objs = first_two[self.root_tag_list]
        links = first_two[self.root_tag_links]
        self.assertEqual(2, len(objs))
        self.assertEqual(1, len(links))
        self.assertEqual('next', links[0]['rel'])

        # Third + off the end -- should have previous link
        third = self.get(self.LISTENERS_PATH, params={
            'limit': 2,
            'marker': first_two[self.root_tag_list][1]['id']}).json
        objs = third[self.root_tag_list]
        links = third[self.root_tag_links]
        self.assertEqual(1, len(objs))
        self.assertEqual(1, len(links))
        self.assertEqual('previous', links[0]['rel'])

        # Middle -- should have both links
        middle = self.get(self.LISTENERS_PATH, params={
            'limit': 1,
            'marker': first_two[self.root_tag_list][0]['id']}).json
        objs = middle[self.root_tag_list]
        links = middle[self.root_tag_links]
        self.assertEqual(1, len(objs))
        self.assertEqual(2, len(links))
        self.assertItemsEqual(['previous', 'next'], [l['rel'] for l in links])

    def test_get_all_fields_filter(self):
        self.create_listener(constants.PROTOCOL_HTTP, 80,
                             self.lb_id,
                             name='listener1')
        self.set_lb_status(self.lb_id)
        self.create_listener(constants.PROTOCOL_HTTP, 81,
                             self.lb_id,
                             name='listener2')
        self.set_lb_status(self.lb_id)
        self.create_listener(constants.PROTOCOL_HTTP, 82,
                             self.lb_id,
                             name='listener3')
        self.set_lb_status(self.lb_id)

        lis = self.get(self.LISTENERS_PATH, params={
            'fields': ['id', 'project_id']}).json
        for li in lis['listeners']:
            self.assertIn(u'id', li)
            self.assertIn(u'project_id', li)
            self.assertNotIn(u'description', li)

    def test_get_one_fields_filter(self):
        listener1 = self.create_listener(
            constants.PROTOCOL_HTTP, 80, self.lb_id,
            name='listener1').get(self.root_tag)
        self.set_lb_status(self.lb_id)

        li = self.get(
            self.LISTENER_PATH.format(listener_id=listener1.get('id')),
            params={'fields': ['id', 'project_id']}).json.get(self.root_tag)
        self.assertIn(u'id', li)
        self.assertIn(u'project_id', li)
        self.assertNotIn(u'description', li)

    def test_get_all_filter(self):
        li1 = self.create_listener(constants.PROTOCOL_HTTP,
                                   80,
                                   self.lb_id,
                                   name='listener1').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_listener(constants.PROTOCOL_HTTP,
                             81,
                             self.lb_id,
                             name='listener2').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_listener(constants.PROTOCOL_HTTP,
                             82,
                             self.lb_id,
                             name='listener3').get(self.root_tag)
        self.set_lb_status(self.lb_id)

        lis = self.get(self.LISTENERS_PATH, params={
            'id': li1['id']}).json
        self.assertEqual(1, len(lis['listeners']))
        self.assertEqual(li1['id'],
                         lis['listeners'][0]['id'])

    def test_get_all_hides_deleted(self):
        api_listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80, self.lb_id).get(self.root_tag)

        response = self.get(self.LISTENERS_PATH)
        objects = response.json.get(self.root_tag_list)
        self.assertEqual(len(objects), 1)
        self.set_object_status(self.listener_repo, api_listener.get('id'),
                               provisioning_status=constants.DELETED)
        response = self.get(self.LISTENERS_PATH)
        objects = response.json.get(self.root_tag_list)
        self.assertEqual(len(objects), 0)

    def test_get(self):
        listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80, self.lb_id).get(self.root_tag)
        response = self.get(self.listener_path.format(
            listener_id=listener['id']))
        api_listener = response.json.get(self.root_tag)
        self.assertEqual(listener, api_listener)

    def test_get_authorized(self):
        listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80, self.lb_id).get(self.root_tag)

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings',
                         auth_strategy=constants.TESTING)
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

                response = self.get(self.listener_path.format(
                    listener_id=listener['id']))
        api_listener = response.json.get(self.root_tag)
        self.assertEqual(listener, api_listener)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

    def test_get_not_authorized(self):
        listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80, self.lb_id).get(self.root_tag)

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings',
                         auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            response = self.get(self.listener_path.format(
                listener_id=listener['id']), status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response.json)

    def test_get_deleted_gives_404(self):
        api_listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80, self.lb_id).get(self.root_tag)

        self.set_object_status(self.listener_repo, api_listener.get('id'),
                               provisioning_status=constants.DELETED)
        self.get(self.LISTENER_PATH.format(listener_id=api_listener.get('id')),
                 status=404)

    def test_get_bad_listener_id(self):
        listener_path = self.listener_path
        self.get(listener_path.format(listener_id='SEAN-CONNERY'), status=404)

    # TODO(johnsom) Fix this when there is a noop certificate manager
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_create(self, mock_cert_data, response_status=201, **optionals):
        cert1 = data_models.TLSContainer(certificate='cert 1')
        cert2 = data_models.TLSContainer(certificate='cert 2')
        cert3 = data_models.TLSContainer(certificate='cert 3')
        mock_cert_data.return_value = {'tls_cert': cert1,
                                       'sni_certs': [cert2, cert3]}
        sni1 = uuidutils.generate_uuid()
        sni2 = uuidutils.generate_uuid()
        lb_listener = {'name': 'listener1', 'default_pool_id': None,
                       'description': 'desc1',
                       'admin_state_up': False,
                       'protocol': constants.PROTOCOL_HTTP,
                       'protocol_port': 80, 'connection_limit': 10,
                       'default_tls_container_ref': uuidutils.generate_uuid(),
                       'sni_container_refs': [sni1, sni2],
                       'insert_headers': {},
                       'project_id': self.project_id,
                       'loadbalancer_id': self.lb_id}
        lb_listener.update(optionals)
        body = self._build_body(lb_listener)
        response = self.post(self.LISTENERS_PATH, body, status=response_status)
        if response_status >= 300:
            return response
        listener_api = response.json['listener']
        extra_expects = {'provisioning_status': constants.PENDING_CREATE,
                         'operating_status': constants.OFFLINE}
        lb_listener.update(extra_expects)
        self.assertTrue(uuidutils.is_uuid_like(listener_api.get('id')))
        for key, value in optionals.items():
            self.assertEqual(value, lb_listener.get(key))
        lb_listener['id'] = listener_api.get('id')
        lb_listener.pop('sni_container_refs')
        sni_ex = [sni1, sni2]
        sni_resp = listener_api.pop('sni_container_refs')
        self.assertEqual(2, len(sni_resp))
        for sni in sni_resp:
            self.assertIn(sni, sni_ex)
        self.assertIsNotNone(listener_api.pop('created_at'))
        self.assertIsNone(listener_api.pop('updated_at'))
        self.assertNotEqual(lb_listener, listener_api)
        self.assert_correct_lb_status(self.lb_id, constants.ONLINE,
                                      constants.PENDING_UPDATE)
        self.assert_final_listener_statuses(self.lb_id, listener_api.get('id'))
        return listener_api

    def test_create_with_timeouts(self):
        optionals = {
            'timeout_client_data': 1,
            'timeout_member_connect': 2,
            'timeout_member_data': constants.MIN_TIMEOUT,
            'timeout_tcp_inspect': constants.MAX_TIMEOUT,
        }
        listener_api = self.test_create(**optionals)
        self.assertEqual(1, listener_api.get('timeout_client_data'))
        self.assertEqual(2, listener_api.get('timeout_member_connect'))
        self.assertEqual(constants.MIN_TIMEOUT,
                         listener_api.get('timeout_member_data'))
        self.assertEqual(constants.MAX_TIMEOUT,
                         listener_api.get('timeout_tcp_inspect'))

    def test_create_with_timeouts_too_high(self):
        optionals = {
            'timeout_client_data': 1,
            'timeout_member_connect': 2,
            'timeout_member_data': 3,
            'timeout_tcp_inspect': constants.MAX_TIMEOUT + 1,
        }
        resp = self.test_create(response_status=400, **optionals).json
        fault = resp.get('faultstring')
        self.assertIn(
            'Invalid input for field/attribute timeout_tcp_inspect', fault)
        self.assertIn(
            'Value should be lower or equal to {0}'.format(
                constants.MAX_TIMEOUT), fault)

    def test_create_with_timeouts_too_low(self):
        optionals = {
            'timeout_client_data': 1,
            'timeout_member_connect': 2,
            'timeout_member_data': 3,
            'timeout_tcp_inspect': constants.MIN_TIMEOUT - 1,
        }
        resp = self.test_create(response_status=400, **optionals).json
        fault = resp.get('faultstring')
        self.assertIn(
            'Invalid input for field/attribute timeout_tcp_inspect', fault)
        self.assertIn(
            'Value should be greater or equal to {0}'.format(
                constants.MIN_TIMEOUT), fault)

    def test_create_udp_case(self):
        api_listener = self.create_listener(constants.PROTOCOL_UDP, 6666,
                                            self.lb_id).get(self.root_tag)
        self.assertEqual(constants.PROTOCOL_UDP, api_listener.get('protocol'))
        self.assertEqual(6666, api_listener.get('protocol_port'))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=api_listener.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_CREATE,
            listener_op_status=constants.OFFLINE)

    def test_negative_create_udp_case(self):
        sni1 = uuidutils.generate_uuid()
        sni2 = uuidutils.generate_uuid()
        req_dict = {'name': 'listener1', 'default_pool_id': None,
                    'description': 'desc1',
                    'admin_state_up': False,
                    'protocol': constants.PROTOCOL_UDP,
                    'protocol_port': 6666, 'connection_limit': 10,
                    'default_tls_container_ref': uuidutils.generate_uuid(),
                    'sni_container_refs': [sni1, sni2],
                    'insert_headers': {
                        "X-Forwarded-Port": "true",
                        "X-Forwarded-For": "true"},
                    'loadbalancer_id': self.lb_id}
        expect_error_msg = (
            "Validation failure: %s protocol listener does not support TLS or "
            "header insertion.") % constants.PROTOCOL_UDP
        res = self.post(self.LISTENERS_PATH, self._build_body(req_dict),
                        status=400, expect_errors=True)
        self.assertEqual(expect_error_msg, res.json['faultstring'])
        self.assert_correct_status(lb_id=self.lb_id)

        # Default pool protocol is udp which is different with listener
        # protocol.
        udp_pool_id = self.create_pool(
            self.lb_id, constants.PROTOCOL_UDP,
            constants.LB_ALGORITHM_ROUND_ROBIN).get('pool').get('id')
        self.set_lb_status(self.lb_id)
        lb_listener = {'name': 'listener1',
                       'default_pool_id': udp_pool_id,
                       'description': 'desc1',
                       'admin_state_up': False,
                       'protocol': constants.PROTOCOL_HTTP,
                       'protocol_port': 80,
                       'loadbalancer_id': self.lb_id}
        expect_error_msg = ("Validation failure: Listeners of type %s can "
                            "only have pools of "
                            "type UDP.") % constants.PROTOCOL_UDP
        res = self.post(self.LISTENERS_PATH, self._build_body(lb_listener),
                        status=400, expect_errors=True)
        self.assertEqual(expect_error_msg, res.json['faultstring'])
        self.assert_correct_status(lb_id=self.lb_id)

    def test_create_duplicate_fails(self):
        self.create_listener(constants.PROTOCOL_HTTP, 80, self.lb_id)
        self.set_lb_status(self.lb_id)
        self.create_listener(constants.PROTOCOL_HTTP, 80, self.lb_id,
                             status=409)

    def test_create_bad_tls_ref(self):
        sni1 = uuidutils.generate_uuid()
        sni2 = uuidutils.generate_uuid()
        tls_ref = uuidutils.generate_uuid()
        lb_listener = {'name': 'listener1', 'default_pool_id': None,
                       'protocol': constants.PROTOCOL_TERMINATED_HTTPS,
                       'protocol_port': 80,
                       'sni_container_refs': [sni1, sni2],
                       'default_tls_container_ref': tls_ref,
                       'loadbalancer_id': self.lb_id}

        body = self._build_body(lb_listener)
        self.cert_manager_mock().get_cert.side_effect = [
            Exception("bad cert"), None, Exception("bad_cert")]
        response = self.post(self.LISTENERS_PATH, body, status=400).json
        self.assertIn(sni1, response['faultstring'])
        self.assertNotIn(sni2, response['faultstring'])
        self.assertIn(tls_ref, response['faultstring'])

    def test_create_with_default_pool_id(self):
        lb_listener = {'name': 'listener1',
                       'default_pool_id': self.pool_id,
                       'description': 'desc1',
                       'admin_state_up': False,
                       'protocol': constants.PROTOCOL_HTTP,
                       'protocol_port': 80,
                       'loadbalancer_id': self.lb_id}
        body = self._build_body(lb_listener)
        response = self.post(self.LISTENERS_PATH, body)
        api_listener = response.json['listener']
        self.assertEqual(api_listener.get('default_pool_id'),
                         self.pool_id)

    def test_create_with_bad_default_pool_id(self):
        lb_listener = {'name': 'listener1',
                       'default_pool_id': uuidutils.generate_uuid(),
                       'description': 'desc1',
                       'admin_state_up': False,
                       'protocol': constants.PROTOCOL_HTTP,
                       'protocol_port': 80,
                       'loadbalancer_id': self.lb_id}
        body = self._build_body(lb_listener)
        self.post(self.LISTENERS_PATH, body, status=404)

    def test_create_with_shared_default_pool_id(self):
        lb_listener1 = {'name': 'listener1',
                        'default_pool_id': self.pool_id,
                        'description': 'desc1',
                        'admin_state_up': False,
                        'protocol': constants.PROTOCOL_HTTP,
                        'protocol_port': 80,
                        'loadbalancer_id': self.lb_id}
        lb_listener2 = {'name': 'listener2',
                        'default_pool_id': self.pool_id,
                        'description': 'desc2',
                        'admin_state_up': False,
                        'protocol': constants.PROTOCOL_HTTP,
                        'protocol_port': 81,
                        'loadbalancer_id': self.lb_id}
        body1 = self._build_body(lb_listener1)
        body2 = self._build_body(lb_listener2)
        listener1 = self.post(self.LISTENERS_PATH, body1).json['listener']
        self.set_lb_status(self.lb_id, constants.ACTIVE)
        listener2 = self.post(self.LISTENERS_PATH, body2).json['listener']
        self.assertEqual(listener1['default_pool_id'], self.pool_id)
        self.assertEqual(listener1['default_pool_id'],
                         listener2['default_pool_id'])

    def test_create_with_project_id(self):
        self.test_create(project_id=self.project_id)

    def test_create_defaults(self):
        defaults = {'name': None, 'default_pool_id': None,
                    'description': None, 'admin_state_up': True,
                    'connection_limit': None,
                    'default_tls_container_ref': None,
                    'sni_container_refs': [], 'project_id': None,
                    'insert_headers': {}}
        lb_listener = {'protocol': constants.PROTOCOL_HTTP,
                       'protocol_port': 80,
                       'loadbalancer_id': self.lb_id}
        body = self._build_body(lb_listener)
        response = self.post(self.LISTENERS_PATH, body)
        listener_api = response.json['listener']
        extra_expects = {'provisioning_status': constants.PENDING_CREATE,
                         'operating_status': constants.OFFLINE}
        lb_listener.update(extra_expects)
        lb_listener.update(defaults)
        self.assertTrue(uuidutils.is_uuid_like(listener_api.get('id')))
        lb_listener['id'] = listener_api.get('id')
        self.assertIsNotNone(listener_api.pop('created_at'))
        self.assertIsNone(listener_api.pop('updated_at'))
        self.assertNotEqual(lb_listener, listener_api)
        self.assert_correct_lb_status(self.lb_id, constants.ONLINE,
                                      constants.PENDING_UPDATE)
        self.assert_final_listener_statuses(self.lb_id, listener_api['id'])

    def test_create_over_quota(self):
        self.start_quota_mock(data_models.Listener)
        lb_listener = {'name': 'listener1',
                       'protocol': constants.PROTOCOL_HTTP,
                       'protocol_port': 80,
                       'loadbalancer_id': self.lb_id}
        body = self._build_body(lb_listener)
        self.post(self.LISTENERS_PATH, body, status=403)

    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_create_with_bad_provider(self, mock_provider):
        mock_provider.side_effect = exceptions.ProviderDriverError(
            prov='bad_driver', user_msg='broken')
        lb_listener = {'name': 'listener1',
                       'protocol': constants.PROTOCOL_HTTP,
                       'protocol_port': 80,
                       'loadbalancer_id': self.lb_id}
        body = self._build_body(lb_listener)
        response = self.post(self.LISTENERS_PATH, body, status=500)
        self.assertIn('Provider \'bad_driver\' reports error: broken',
                      response.json.get('faultstring'))

    # TODO(johnsom) Fix this when there is a noop certificate manager
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_create_authorized(self, mock_cert_data, **optionals):
        cert1 = data_models.TLSContainer(certificate='cert 1')
        cert2 = data_models.TLSContainer(certificate='cert 2')
        cert3 = data_models.TLSContainer(certificate='cert 3')
        mock_cert_data.return_value = {'tls_cert': cert1,
                                       'sni_certs': [cert2, cert3]}
        sni1 = uuidutils.generate_uuid()
        sni2 = uuidutils.generate_uuid()
        lb_listener = {'name': 'listener1', 'default_pool_id': None,
                       'description': 'desc1',
                       'admin_state_up': False,
                       'protocol': constants.PROTOCOL_HTTP,
                       'protocol_port': 80, 'connection_limit': 10,
                       'default_tls_container_ref': uuidutils.generate_uuid(),
                       'sni_container_refs': [sni1, sni2],
                       'insert_headers': {},
                       'project_id': self.project_id,
                       'loadbalancer_id': self.lb_id}
        lb_listener.update(optionals)
        body = self._build_body(lb_listener)

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings',
                         auth_strategy=constants.TESTING)

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
                response = self.post(self.LISTENERS_PATH, body)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        listener_api = response.json['listener']
        extra_expects = {'provisioning_status': constants.PENDING_CREATE,
                         'operating_status': constants.OFFLINE}
        lb_listener.update(extra_expects)
        self.assertTrue(uuidutils.is_uuid_like(listener_api.get('id')))
        for key, value in optionals.items():
            self.assertEqual(value, lb_listener.get(key))
        lb_listener['id'] = listener_api.get('id')
        lb_listener.pop('sni_container_refs')
        sni_ex = [sni1, sni2]
        sni_resp = listener_api.pop('sni_container_refs')
        self.assertEqual(2, len(sni_resp))
        for sni in sni_resp:
            self.assertIn(sni, sni_ex)
        self.assertIsNotNone(listener_api.pop('created_at'))
        self.assertIsNone(listener_api.pop('updated_at'))
        self.assertNotEqual(lb_listener, listener_api)
        self.assert_correct_lb_status(self.lb_id, constants.ONLINE,
                                      constants.PENDING_UPDATE)
        self.assert_final_listener_statuses(self.lb_id, listener_api.get('id'))

    def test_create_not_authorized(self, **optionals):
        sni1 = uuidutils.generate_uuid()
        sni2 = uuidutils.generate_uuid()
        lb_listener = {'name': 'listener1', 'default_pool_id': None,
                       'description': 'desc1',
                       'admin_state_up': False,
                       'protocol': constants.PROTOCOL_HTTP,
                       'protocol_port': 80, 'connection_limit': 10,
                       'default_tls_container_ref': uuidutils.generate_uuid(),
                       'sni_container_refs': [sni1, sni2],
                       'insert_headers': {},
                       'project_id': self.project_id,
                       'loadbalancer_id': self.lb_id}
        lb_listener.update(optionals)
        body = self._build_body(lb_listener)

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings',
                         auth_strategy=constants.TESTING)

        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            response = self.post(self.LISTENERS_PATH, body, status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response.json)

    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_update_with_bad_provider(self, mock_provider):
        api_listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80,
            self.lb_id).get(self.root_tag)
        self.set_lb_status(lb_id=self.lb_id)
        new_listener = {'name': 'new_name'}
        mock_provider.side_effect = exceptions.ProviderDriverError(
            prov='bad_driver', user_msg='broken')
        response = self.put(
            self.LISTENER_PATH.format(listener_id=api_listener.get('id')),
            self._build_body(new_listener), status=500)
        self.assertIn('Provider \'bad_driver\' reports error: broken',
                      response.json.get('faultstring'))

    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_delete_with_bad_provider(self, mock_provider):
        api_listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80,
            self.lb_id).get(self.root_tag)
        self.set_lb_status(lb_id=self.lb_id)
        # Set status to ACTIVE/ONLINE because set_lb_status did it in the db
        api_listener['provisioning_status'] = constants.ACTIVE
        api_listener['operating_status'] = constants.ONLINE
        response = self.get(self.LISTENER_PATH.format(
            listener_id=api_listener.get('id'))).json.get(self.root_tag)
        self.assertIsNone(api_listener.pop('updated_at'))
        self.assertIsNotNone(response.pop('updated_at'))
        self.assertEqual(api_listener, response)
        mock_provider.side_effect = exceptions.ProviderDriverError(
            prov='bad_driver', user_msg='broken')
        self.delete(self.LISTENER_PATH.format(
            listener_id=api_listener.get('id')), status=500)

    # TODO(johnsom) Fix this when there is a noop certificate manager
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_update(self, mock_cert_data):
        cert1 = data_models.TLSContainer(certificate='cert 1')
        mock_cert_data.return_value = {'tls_cert': cert1}
        tls_uuid = uuidutils.generate_uuid()
        listener = self.create_listener(
            constants.PROTOCOL_TCP, 80, self.lb_id,
            name='listener1', description='desc1',
            admin_state_up=False, connection_limit=10,
            default_tls_container_ref=tls_uuid,
            default_pool_id=None).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_listener = {'name': 'listener2', 'admin_state_up': True,
                        'default_pool_id': self.pool_id,
                        'timeout_client_data': 1,
                        'timeout_member_connect': 2,
                        'timeout_member_data': 3,
                        'timeout_tcp_inspect': 4}
        body = self._build_body(new_listener)
        listener_path = self.LISTENER_PATH.format(
            listener_id=listener['id'])
        api_listener = self.put(listener_path, body).json.get(self.root_tag)
        update_expect = {'provisioning_status': constants.PENDING_UPDATE,
                         'operating_status': constants.ONLINE}
        update_expect.update(new_listener)
        listener.update(update_expect)
        self.assertEqual(listener['created_at'], api_listener['created_at'])
        self.assertNotEqual(listener['updated_at'], api_listener['updated_at'])
        self.assertNotEqual(listener, api_listener)
        self.assert_correct_lb_status(self.lb_id, constants.ONLINE,
                                      constants.PENDING_UPDATE)
        self.assert_final_listener_statuses(self.lb_id,
                                            api_listener['id'])

    def test_negative_update_udp_case(self):
        api_listener = self.create_listener(constants.PROTOCOL_UDP, 6666,
                                            self.lb_id).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        sni1 = uuidutils.generate_uuid()
        sni2 = uuidutils.generate_uuid()
        new_listener = {'name': 'new-listener',
                        'admin_state_up': True,
                        'connection_limit': 10,
                        'default_tls_container_ref':
                            uuidutils.generate_uuid(),
                        'sni_container_refs': [sni1, sni2],
                        'insert_headers': {
                            "X-Forwarded-Port": "true",
                            "X-Forwarded-For": "true"}}
        listener_path = self.LISTENER_PATH.format(
            listener_id=api_listener['id'])
        expect_error_msg = (
            "Validation failure: %s protocol listener does not support TLS or "
            "header insertion.") % constants.PROTOCOL_UDP
        res = self.put(listener_path, self._build_body(new_listener),
                       status=400, expect_errors=True)
        self.assertEqual(expect_error_msg, res.json['faultstring'])
        self.assert_correct_status(lb_id=self.lb_id)

    def test_update_bad_listener_id(self):
        self.put(self.listener_path.format(listener_id='SEAN-CONNERY'),
                 body={}, status=404)

    def test_update_with_bad_default_pool_id(self):
        bad_pool_uuid = uuidutils.generate_uuid()
        listener = self.create_listener(
            constants.PROTOCOL_TCP, 80, self.lb_id,
            name='listener1', description='desc1',
            admin_state_up=False, connection_limit=10,
            default_pool_id=self.pool_id)
        self.set_lb_status(self.lb_id)
        new_listener = {'name': 'listener2', 'admin_state_up': True,
                        'default_pool_id': bad_pool_uuid}
        body = self._build_body(new_listener)
        listener_path = self.LISTENER_PATH.format(
            listener_id=listener['listener']['id'])
        self.put(listener_path, body, status=404)
        self.assert_correct_lb_status(self.lb_id, constants.ONLINE,
                                      constants.ACTIVE)
        self.assert_final_listener_statuses(self.lb_id,
                                            listener['listener']['id'])

    # TODO(johnsom) Fix this when there is a noop certificate manager
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_update_authorized(self, mock_cert_data):
        cert1 = data_models.TLSContainer(certificate='cert 1')
        mock_cert_data.return_value = {'tls_cert': cert1}
        tls_uuid = uuidutils.generate_uuid()
        listener = self.create_listener(
            constants.PROTOCOL_TCP, 80, self.lb_id,
            name='listener1', description='desc1',
            admin_state_up=False, connection_limit=10,
            default_tls_container_ref=tls_uuid,
            default_pool_id=None).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_listener = {'name': 'listener2', 'admin_state_up': True,
                        'default_pool_id': self.pool_id}
        body = self._build_body(new_listener)
        listener_path = self.LISTENER_PATH.format(
            listener_id=listener['id'])

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings',
                         auth_strategy=constants.TESTING)
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
                api_listener = self.put(listener_path, body)
                api_listener = api_listener.json.get(self.root_tag)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        update_expect = {'name': 'listener2', 'admin_state_up': True,
                         'default_pool_id': self.pool_id,
                         'provisioning_status': constants.PENDING_UPDATE,
                         'operating_status': constants.ONLINE}
        listener.update(update_expect)
        self.assertEqual(listener['created_at'], api_listener['created_at'])
        self.assertNotEqual(listener['updated_at'], api_listener['updated_at'])
        self.assertNotEqual(listener, api_listener)
        self.assert_correct_lb_status(self.lb_id, constants.ONLINE,
                                      constants.PENDING_UPDATE)
        self.assert_final_listener_statuses(self.lb_id,
                                            api_listener['id'])

    # TODO(johnsom) Fix this when there is a noop certificate manager
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_update_not_authorized(self, mock_cert_data):
        cert1 = data_models.TLSContainer(certificate='cert 1')
        mock_cert_data.return_value = {'tls_cert': cert1}
        tls_uuid = uuidutils.generate_uuid()
        listener = self.create_listener(
            constants.PROTOCOL_TCP, 80, self.lb_id,
            name='listener1', description='desc1',
            admin_state_up=False, connection_limit=10,
            default_tls_container_ref=tls_uuid,
            default_pool_id=None).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_listener = {'name': 'listener2', 'admin_state_up': True,
                        'default_pool_id': self.pool_id}
        body = self._build_body(new_listener)
        listener_path = self.LISTENER_PATH.format(
            listener_id=listener['id'])

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings',
                         auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
                api_listener = self.put(listener_path, body, status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, api_listener.json)
        self.assert_correct_lb_status(self.lb_id, constants.ONLINE,
                                      constants.ACTIVE)

    def test_create_listeners_same_port(self):
        listener1 = self.create_listener(constants.PROTOCOL_TCP, 80,
                                         self.lb_id)
        self.set_lb_status(self.lb_id)
        listener2_post = {'protocol': listener1['listener']['protocol'],
                          'protocol_port':
                          listener1['listener']['protocol_port'],
                          'loadbalancer_id': self.lb_id}
        body = self._build_body(listener2_post)
        self.post(self.LISTENERS_PATH, body, status=409)

    def test_delete(self):
        listener = self.create_listener(constants.PROTOCOL_HTTP, 80,
                                        self.lb_id)
        self.set_lb_status(self.lb_id)
        listener_path = self.LISTENER_PATH.format(
            listener_id=listener['listener']['id'])
        self.delete(listener_path)
        response = self.get(listener_path)
        api_listener = response.json['listener']
        expected = {'name': None, 'default_pool_id': None,
                    'description': None, 'admin_state_up': True,
                    'operating_status': constants.ONLINE,
                    'provisioning_status': constants.PENDING_DELETE,
                    'connection_limit': None}
        listener['listener'].update(expected)

        self.assertIsNone(listener['listener'].pop('updated_at'))
        self.assertIsNotNone(api_listener.pop('updated_at'))
        self.assertNotEqual(listener, api_listener)
        self.assert_correct_lb_status(self.lb_id, constants.ONLINE,
                                      constants.PENDING_UPDATE)
        self.assert_final_listener_statuses(self.lb_id, api_listener['id'],
                                            delete=True)

    def test_delete_authorized(self):
        listener = self.create_listener(constants.PROTOCOL_HTTP, 80,
                                        self.lb_id)
        self.set_lb_status(self.lb_id)
        listener_path = self.LISTENER_PATH.format(
            listener_id=listener['listener']['id'])

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings',
                         auth_strategy=constants.TESTING)
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

                self.delete(listener_path)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        response = self.get(listener_path)
        api_listener = response.json['listener']
        expected = {'name': None, 'default_pool_id': None,
                    'description': None, 'admin_state_up': True,
                    'operating_status': constants.ONLINE,
                    'provisioning_status': constants.PENDING_DELETE,
                    'connection_limit': None}
        listener['listener'].update(expected)

        self.assertIsNone(listener['listener'].pop('updated_at'))
        self.assertIsNotNone(api_listener.pop('updated_at'))
        self.assertNotEqual(listener, api_listener)
        self.assert_correct_lb_status(self.lb_id, constants.ONLINE,
                                      constants.PENDING_UPDATE)
        self.assert_final_listener_statuses(self.lb_id, api_listener['id'],
                                            delete=True)

    def test_delete_not_authorized(self):
        listener = self.create_listener(constants.PROTOCOL_HTTP, 80,
                                        self.lb_id)
        self.set_lb_status(self.lb_id)
        listener_path = self.LISTENER_PATH.format(
            listener_id=listener['listener']['id'])

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
                self.delete(listener_path, status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assert_correct_lb_status(self.lb_id, constants.ONLINE,
                                      constants.ACTIVE)

    def test_delete_bad_listener_id(self):
        listener_path = self.LISTENER_PATH.format(listener_id='SEAN-CONNERY')
        self.delete(listener_path, status=404)

    def test_create_listener_bad_protocol(self):
        lb_listener = {'protocol': 'SEAN_CONNERY',
                       'protocol_port': 80}
        self.post(self.LISTENERS_PATH, lb_listener, status=400)

    def test_update_listener_bad_protocol(self):
        listener = self.create_listener(constants.PROTOCOL_TCP, 80, self.lb_id)
        self.set_lb_status(self.lb_id)
        new_listener = {'protocol': 'SEAN_CONNERY',
                        'protocol_port': 80}
        listener_path = self.LISTENER_PATH.format(
            listener_id=listener['listener'].get('id'))
        self.put(listener_path, new_listener, status=400)

    def test_update_pending_create(self):
        lb = self.create_load_balancer(uuidutils.generate_uuid())
        optionals = {'name': 'lb1', 'description': 'desc1',
                     'admin_state_up': False}
        lb.update(optionals)

        lb_listener = {'name': 'listener1', 'description': 'desc1',
                       'admin_state_up': False,
                       'protocol': constants.PROTOCOL_HTTP,
                       'protocol_port': 80, 'connection_limit': 10,
                       'loadbalancer_id': lb['loadbalancer']['id']}
        body = self._build_body(lb_listener)
        self.post(self.LISTENERS_PATH, body, status=409)

    def test_delete_pending_update(self):
        lb = self.create_load_balancer(uuidutils.generate_uuid())
        optionals = {'name': 'lb1', 'description': 'desc1',
                     'admin_state_up': False}
        lb.update(optionals)

        self.set_lb_status(lb['loadbalancer']['id'])
        lb_listener = {'name': 'listener1', 'description': 'desc1',
                       'admin_state_up': False,
                       'protocol': constants.PROTOCOL_HTTP,
                       'protocol_port': 80, 'connection_limit': 10,
                       'loadbalancer_id': lb['loadbalancer']['id']}
        body = self._build_body(lb_listener)
        api_listener = self.post(
            self.LISTENERS_PATH, body).json['listener']
        listener_path = self.LISTENER_PATH.format(
            listener_id=api_listener['id'])
        self.delete(listener_path, status=409)

    def test_update_empty_body(self):
        listener = self.create_listener(constants.PROTOCOL_TCP, 80, self.lb_id)
        self.set_lb_status(self.lb_id)
        listener_path = self.LISTENER_PATH.format(
            listener_id=listener['listener'].get('id'))
        self.put(listener_path, {}, status=400)

    # TODO(johnsom) Fix this when there is a noop certificate manager
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_update_bad_tls_ref(self, mock_cert_data):
        cert2 = data_models.TLSContainer(certificate='cert 2')
        cert3 = data_models.TLSContainer(certificate='cert 3')
        mock_cert_data.return_value = {'sni_certs': [cert2, cert3]}
        sni1 = uuidutils.generate_uuid()
        sni2 = uuidutils.generate_uuid()
        tls_ref = uuidutils.generate_uuid()
        tls_ref2 = uuidutils.generate_uuid()
        lb_listener = {'name': 'listener1', 'default_pool_id': None,
                       'protocol': constants.PROTOCOL_TERMINATED_HTTPS,
                       'protocol_port': 80,
                       'sni_container_refs': [sni1, sni2],
                       'default_tls_container_ref': tls_ref,
                       'loadbalancer_id': self.lb_id}

        body = self._build_body(lb_listener)
        api_listener = self.post(
            self.LISTENERS_PATH, body).json['listener']
        self.set_lb_status(self.lb_id)
        lb_listener_put = {
            'default_tls_container_ref': tls_ref2,
            'sni_container_refs': [sni1, sni2]
        }
        body = self._build_body(lb_listener_put)
        listener_path = self.LISTENER_PATH.format(
            listener_id=api_listener['id'])
        self.cert_manager_mock().get_cert.side_effect = [
            Exception("bad cert"), None, Exception("bad cert")]
        response = self.put(listener_path, body, status=400).json
        self.assertIn(tls_ref2, response['faultstring'])
        self.assertIn(sni1, response['faultstring'])
        self.assertNotIn(sni2, response['faultstring'])
        self.assertNotIn(tls_ref, response['faultstring'])

    def test_update_pending_update(self):
        lb = self.create_load_balancer(uuidutils.generate_uuid())
        optionals = {'name': 'lb1', 'description': 'desc1',
                     'admin_state_up': False}
        lb.update(optionals)
        self.set_lb_status(lb['loadbalancer']['id'])
        lb_listener = {'name': 'listener1', 'description': 'desc1',
                       'admin_state_up': False,
                       'protocol': constants.PROTOCOL_HTTP,
                       'protocol_port': 80, 'connection_limit': 10,
                       'loadbalancer_id': lb['loadbalancer']['id']}
        body = self._build_body(lb_listener)
        api_listener = self.post(
            self.LISTENERS_PATH, body).json['listener']
        self.set_lb_status(lb['loadbalancer']['id'])
        self.put(self.LB_PATH.format(lb_id=lb['loadbalancer']['id']),
                 {'loadbalancer': {'name': 'hi'}})
        lb_listener_put = {'name': 'listener1_updated'}
        body = self._build_body(lb_listener_put)
        listener_path = self.LISTENER_PATH.format(
            listener_id=api_listener['id'])
        self.put(listener_path, body, status=409)

    def test_update_pending_delete(self):
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1', description='desc1',
                                       admin_state_up=False)
        lb_id = lb['loadbalancer'].get('id')
        self.set_lb_status(lb_id)
        lb_listener = {'name': 'listener1', 'description': 'desc1',
                       'admin_state_up': False,
                       'protocol': constants.PROTOCOL_HTTP,
                       'protocol_port': 80, 'connection_limit': 10,
                       'loadbalancer_id': lb_id}
        body = self._build_body(lb_listener)
        api_listener = self.post(
            self.LISTENERS_PATH, body).json.get(self.root_tag)
        self.set_lb_status(lb_id)
        self.delete(self.LB_PATH.format(lb_id=lb_id),
                    params={'cascade': "true"})
        lb_listener_put = {'name': 'listener1_updated'}
        body = self._build_body(lb_listener_put)
        listener_path = self.LISTENER_PATH.format(
            listener_id=api_listener['id'])
        self.put(listener_path, body, status=409)

    def test_update_deleted(self):
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1', description='desc1',
                                       admin_state_up=False)
        lb_id = lb['loadbalancer'].get('id')
        self.set_lb_status(lb_id)
        lb_listener = {'name': 'listener1', 'description': 'desc1',
                       'admin_state_up': False,
                       'protocol': constants.PROTOCOL_HTTP,
                       'protocol_port': 80, 'connection_limit': 10,
                       'loadbalancer_id': lb_id}
        body = self._build_body(lb_listener)
        api_listener = self.post(
            self.LISTENERS_PATH, body).json.get(self.root_tag)
        # This updates the child objects
        self.set_lb_status(lb_id, status=constants.DELETED)
        lb_listener_put = {'name': 'listener1_updated'}
        body = self._build_body(lb_listener_put)
        listener_path = self.LISTENER_PATH.format(
            listener_id=api_listener['id'])
        self.put(listener_path, body, status=404)

    def test_delete_pending_delete(self):
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1', description='desc1',
                                       admin_state_up=False)
        lb_id = lb['loadbalancer'].get('id')
        self.set_lb_status(lb_id)
        lb_listener = {'name': 'listener1', 'description': 'desc1',
                       'admin_state_up': False,
                       'protocol': constants.PROTOCOL_HTTP,
                       'protocol_port': 80, 'connection_limit': 10,
                       'loadbalancer_id': lb_id}
        body = self._build_body(lb_listener)
        api_listener = self.post(
            self.LISTENERS_PATH, body).json.get(self.root_tag)
        self.set_lb_status(lb_id)
        self.delete(self.LB_PATH.format(lb_id=lb_id),
                    params={'cascade': "true"})
        listener_path = self.LISTENER_PATH.format(
            listener_id=api_listener['id'])
        self.delete(listener_path, status=409)

    def test_delete_already_deleted(self):
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1', description='desc1',
                                       admin_state_up=False)
        lb_id = lb['loadbalancer'].get('id')
        self.set_lb_status(lb_id)
        lb_listener = {'name': 'listener1', 'description': 'desc1',
                       'admin_state_up': False,
                       'protocol': constants.PROTOCOL_HTTP,
                       'protocol_port': 80, 'connection_limit': 10,
                       'loadbalancer_id': lb_id}
        body = self._build_body(lb_listener)
        api_listener = self.post(
            self.LISTENERS_PATH, body).json.get(self.root_tag)
        # This updates the child objects
        self.set_lb_status(lb_id, status=constants.DELETED)
        listener_path = self.LISTENER_PATH.format(
            listener_id=api_listener['id'])
        self.delete(listener_path, status=404)

    # TODO(johnsom) Fix this when there is a noop certificate manager
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_create_with_tls_termination_data(self, mock_cert_data):
        cert1 = data_models.TLSContainer(certificate='cert 1')
        cert2 = data_models.TLSContainer(certificate='cert 2')
        cert3 = data_models.TLSContainer(certificate='cert 3')
        mock_cert_data.return_value = {'tls_cert': cert1,
                                       'sni_certs': [cert2, cert3]}
        cert_id = uuidutils.generate_uuid()
        listener = self.create_listener(constants.PROTOCOL_TERMINATED_HTTPS,
                                        80, self.lb_id,
                                        default_tls_container_ref=cert_id)
        listener_path = self.LISTENER_PATH.format(
            listener_id=listener['listener']['id'])
        get_listener = self.get(listener_path).json['listener']
        self.assertEqual(cert_id, get_listener['default_tls_container_ref'])

    # TODO(johnsom) Fix this when there is a noop certificate manager
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_update_with_tls_termination_data(self, mock_cert_data):
        cert1 = data_models.TLSContainer(certificate='cert 1')
        mock_cert_data.return_value = {'tls_cert': cert1}
        cert_id = uuidutils.generate_uuid()
        listener = self.create_listener(constants.PROTOCOL_TERMINATED_HTTPS,
                                        80, self.lb_id)
        self.set_lb_status(self.lb_id)
        listener_path = self.LISTENER_PATH.format(
            listener_id=listener['listener']['id'])
        get_listener = self.get(listener_path).json['listener']
        self.assertIsNone(get_listener.get('default_tls_container_ref'))
        self.put(listener_path,
                 self._build_body({'default_tls_container_ref': cert_id}))
        get_listener = self.get(listener_path).json['listener']
        self.assertEqual(cert_id,
                         get_listener.get('default_tls_container_ref'))

    def test_create_with_tls_termination_disabled(self):
        self.conf.config(group='api_settings',
                         allow_tls_terminated_listeners=False)
        cert_id = uuidutils.generate_uuid()
        listener = self.create_listener(constants.PROTOCOL_TERMINATED_HTTPS,
                                        80, self.lb_id,
                                        default_tls_container_ref=cert_id,
                                        status=400)
        self.assertIn(
            'The selected protocol is not allowed in this deployment: {0}'
            .format(constants.PROTOCOL_TERMINATED_HTTPS),
            listener.get('faultstring'))

    # TODO(johnsom) Fix this when there is a noop certificate manager
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_create_with_sni_data(self, mock_cert_data):
        cert1 = data_models.TLSContainer(certificate='cert 1')
        cert2 = data_models.TLSContainer(certificate='cert 2')
        cert3 = data_models.TLSContainer(certificate='cert 3')
        mock_cert_data.return_value = {'tls_cert': cert1,
                                       'sni_certs': [cert2, cert3]}
        sni_id1 = uuidutils.generate_uuid()
        sni_id2 = uuidutils.generate_uuid()
        listener = self.create_listener(constants.PROTOCOL_HTTP, 80,
                                        self.lb_id,
                                        sni_container_refs=[sni_id1, sni_id2])
        listener_path = self.LISTENER_PATH.format(
            listener_id=listener['listener']['id'])
        get_listener = self.get(listener_path).json['listener']
        self.assertItemsEqual([sni_id1, sni_id2],
                              get_listener['sni_container_refs'])

    # TODO(johnsom) Fix this when there is a noop certificate manager
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_update_with_sni_data(self, mock_cert_data):
        cert2 = data_models.TLSContainer(certificate='cert 2')
        cert3 = data_models.TLSContainer(certificate='cert 3')
        mock_cert_data.return_value = {'sni_certs': [cert2, cert3]}
        sni_id1 = uuidutils.generate_uuid()
        sni_id2 = uuidutils.generate_uuid()
        listener = self.create_listener(constants.PROTOCOL_HTTP, 80,
                                        self.lb_id)
        self.set_lb_status(self.lb_id)
        listener_path = self.LISTENER_PATH.format(
            listener_id=listener['listener']['id'])
        get_listener = self.get(listener_path).json['listener']
        self.assertEqual([], get_listener.get('sni_container_refs'))
        self.put(listener_path,
                 self._build_body({'sni_container_refs': [sni_id1, sni_id2]}))
        get_listener = self.get(listener_path).json['listener']
        self.assertEqual([], get_listener.get('sni_container_refs'))

    def test_create_with_valid_insert_headers(self):
        lb_listener = {'protocol': 'HTTP',
                       'protocol_port': 80,
                       'loadbalancer_id': self.lb_id,
                       'insert_headers': {'X-Forwarded-For': 'true'}}
        body = self._build_body(lb_listener)
        self.post(self.LISTENERS_PATH, body, status=201)

    def test_create_with_bad_insert_headers(self):
        lb_listener = {'protocol': 'HTTP',
                       'protocol_port': 80,
                       'loadbalancer_id': self.lb_id,
                       'insert_headers': {'X-Forwarded-Four': 'true'}}
        body = self._build_body(lb_listener)
        self.post(self.LISTENERS_PATH, body, status=400)

    def _getStats(self, listener_id):
        res = self.get(self.LISTENER_PATH.format(
            listener_id=listener_id + "/stats"))
        return res.json.get('stats')

    def test_statistics(self):
        lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')
        self.set_lb_status(lb['id'])
        li = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb.get('id')).get('listener')
        amphora = self.create_amphora(uuidutils.generate_uuid(), lb['id'])
        ls = self.create_listener_stats_dynamic(
            listener_id=li.get('id'),
            amphora_id=amphora.id,
            bytes_in=random.randint(1, 9),
            bytes_out=random.randint(1, 9),
            total_connections=random.randint(1, 9),
            request_errors=random.randint(1, 9))

        response = self._getStats(li['id'])
        self.assertEqual(ls['bytes_in'], response['bytes_in'])
        self.assertEqual(ls['bytes_out'], response['bytes_out'])
        self.assertEqual(ls['total_connections'],
                         response['total_connections'])
        self.assertEqual(ls['active_connections'],
                         response['active_connections'])
        self.assertEqual(ls['request_errors'],
                         response['request_errors'])

    def test_statistics_authorized(self):
        project_id = uuidutils.generate_uuid()
        lb = self.create_load_balancer(
            uuidutils.generate_uuid(),
            project_id=project_id).get('loadbalancer')
        self.set_lb_status(lb['id'])
        li = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb.get('id')).get('listener')
        amphora = self.create_amphora(uuidutils.generate_uuid(), lb['id'])
        ls = self.create_listener_stats_dynamic(
            listener_id=li.get('id'),
            amphora_id=amphora.id,
            bytes_in=random.randint(1, 9),
            bytes_out=random.randint(1, 9),
            total_connections=random.randint(1, 9),
            request_errors=random.randint(1, 9))
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)

        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               project_id):
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
                'project_id': project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                response = self._getStats(li['id'])
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        self.assertEqual(ls['bytes_in'], response['bytes_in'])
        self.assertEqual(ls['bytes_out'], response['bytes_out'])
        self.assertEqual(ls['total_connections'],
                         response['total_connections'])
        self.assertEqual(ls['active_connections'],
                         response['active_connections'])
        self.assertEqual(ls['request_errors'],
                         response['request_errors'])

    def test_statistics_not_authorized(self):
        lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')
        self.set_lb_status(lb['id'])
        li = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb.get('id')).get('listener')
        amphora = self.create_amphora(uuidutils.generate_uuid(), lb['id'])
        self.create_listener_stats_dynamic(
            listener_id=li.get('id'),
            amphora_id=amphora.id,
            bytes_in=random.randint(1, 9),
            bytes_out=random.randint(1, 9),
            total_connections=random.randint(1, 9),
            request_errors=random.randint(1, 9))
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            res = self.get(self.LISTENER_PATH.format(
                listener_id=li['id'] + "/stats"), status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, res.json)

    def test_statistics_get_deleted(self):
        lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')
        self.set_lb_status(lb['id'])
        li = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb.get('id')).get('listener')
        amphora = self.create_amphora(uuidutils.generate_uuid(), lb['id'])
        self.create_listener_stats_dynamic(
            listener_id=li.get('id'),
            amphora_id=amphora.id,
            bytes_in=random.randint(1, 9),
            bytes_out=random.randint(1, 9),
            total_connections=random.randint(1, 9),
            request_errors=random.randint(1, 9))
        self.set_lb_status(lb['id'], status=constants.DELETED)
        self.get(self.LISTENER_PATH.format(
            listener_id=li.get('id') + "/stats"), status=404)
