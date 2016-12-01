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

import mock

from oslo_utils import uuidutils

from octavia.common import constants
import octavia.common.context
from octavia.tests.functional.api.v2 import base

import testtools


class TestListener(base.BaseAPITest):

    root_tag = 'listener'
    root_tag_list = 'listeners'

    def setUp(self):
        super(TestListener, self).setUp()
        self.lb = self.create_load_balancer(uuidutils.generate_uuid())
        self.set_lb_status(self.lb['loadbalancer']['id'])
        self.listeners_path = self.LISTENERS_PATH
        self.listener_path = self.LISTENERS_PATH + '/{listener_id}'
        # self.pool = self.create_pool(
        #     self.lb['loadbalancer']['id'], constants.PROTOCOL_HTTP,
        #     constants.LB_ALGORITHM_ROUND_ROBIN, 'pool')
        # self.set_lb_status(self.lb['loadbalancer']['id'])

    def _build_body(self, json):
        return {self.root_tag: json}

    def test_get_all_admin(self):
        project_id = uuidutils.generate_uuid()
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb1', project_id=project_id)
        self.set_lb_status(lb1['loadbalancer']['id'])
        listener1 = self.create_listener(constants.PROTOCOL_HTTP, 80,
                                         lb1['loadbalancer']['id'])
        self.set_lb_status(lb1['loadbalancer']['id'])
        listener2 = self.create_listener(constants.PROTOCOL_HTTP, 81,
                                         lb1['loadbalancer']['id'])
        self.set_lb_status(lb1['loadbalancer']['id'])
        listener3 = self.create_listener(constants.PROTOCOL_HTTP, 82,
                                         lb1['loadbalancer']['id'])
        self.set_lb_status(lb1['loadbalancer']['id'])
        response = self.get(self.listeners_path)
        listeners = response.json.get(self.root_tag_list)
        self.assertEqual(3, len(listeners))
        listener_id_names = [(l.get('id'), l.get('name')) for l in listeners]
        listener1 = listener1.get(self.root_tag)
        listener2 = listener2.get(self.root_tag)
        listener3 = listener3.get(self.root_tag)
        self.assertIn((listener1.get('id'), listener1.get('name')),
                      listener_id_names)
        self.assertIn((listener2.get('id'), listener2.get('name')),
                      listener_id_names)
        self.assertIn((listener3.get('id'), listener3.get('name')),
                      listener_id_names)

    def test_get_all_non_admin(self):
        project_id = uuidutils.generate_uuid()
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb1', project_id=project_id)
        self.set_lb_status(lb1['loadbalancer']['id'])
        self.create_listener(constants.PROTOCOL_HTTP, 80,
                             lb1['loadbalancer']['id'])
        self.set_lb_status(lb1['loadbalancer']['id'])
        self.create_listener(constants.PROTOCOL_HTTP, 81,
                             lb1['loadbalancer']['id'])
        self.set_lb_status(self.lb['loadbalancer']['id'])
        listener3 = self.create_listener(constants.PROTOCOL_HTTP, 82,
                                         self.lb['loadbalancer']['id'])
        listener3 = listener3.get(self.root_tag)
        self.set_lb_status(self.lb['loadbalancer']['id'])

        auth_strategy = self.conf.conf.get('auth_strategy')
        self.conf.config(auth_strategy=constants.KEYSTONE)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               listener3['project_id']):
            response = self.get(self.LISTENERS_PATH)
        self.conf.config(auth_strategy=auth_strategy)

        listeners = response.json.get(self.root_tag_list)
        self.assertEqual(1, len(listeners))
        listener_id_names = [(l.get('id'), l.get('name')) for l in listeners]
        self.assertIn((listener3.get('id'), listener3.get('name')),
                      listener_id_names)

    def test_get_all_by_project_id(self):
        project1_id = uuidutils.generate_uuid()
        project2_id = uuidutils.generate_uuid()
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb1',
                                        project_id=project1_id)
        self.set_lb_status(lb1['loadbalancer']['id'])
        lb2 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb2',
                                        project_id=project2_id)
        self.set_lb_status(lb2['loadbalancer']['id'])
        listener1 = self.create_listener(constants.PROTOCOL_HTTP, 80,
                                         lb1['loadbalancer']['id'],
                                         name='listener1')
        self.set_lb_status(lb1['loadbalancer']['id'])
        listener2 = self.create_listener(constants.PROTOCOL_HTTP, 81,
                                         lb1['loadbalancer']['id'],
                                         name='listener2')
        self.set_lb_status(lb1['loadbalancer']['id'])
        listener3 = self.create_listener(constants.PROTOCOL_HTTP, 82,
                                         lb2['loadbalancer']['id'],
                                         name='listener3')
        self.set_lb_status(lb2['loadbalancer']['id'])
        response = self.get(self.LISTENERS_PATH,
                            params={'project_id': project1_id})
        listeners = response.json.get(self.root_tag_list)

        self.assertEqual(2, len(listeners))

        listener_id_names = [(l.get('id'), l.get('name')) for l in listeners]
        listener1 = listener1.get(self.root_tag)
        listener2 = listener2.get(self.root_tag)
        listener3 = listener3.get(self.root_tag)
        self.assertIn((listener1.get('id'), listener1.get('name')),
                      listener_id_names)
        self.assertIn((listener2.get('id'), listener2.get('name')),
                      listener_id_names)
        response = self.get(self.LISTENERS_PATH,
                            params={'project_id': project2_id})
        listeners = response.json.get(self.root_tag_list)
        listener_id_names = [(l.get('id'), l.get('name')) for l in listeners]
        self.assertEqual(1, len(listeners))
        self.assertIn((listener3.get('id'), listener3.get('name')),
                      listener_id_names)

    def test_get(self):
        listener = self.create_listener(constants.PROTOCOL_HTTP, 80,
                                        self.lb['loadbalancer']['id'])
        listener_path = self.listener_path
        response = self.get(listener_path.format(
                            listener_id=listener['listener']['id']))
        api_lb = response.json['listener']
        expected = {'name': None, 'description': None, 'admin_state_up': True,
                    'operating_status': constants.OFFLINE,
                    'provisioning_status': constants.PENDING_CREATE,
                    'connection_limit': None}
        listener.update(expected)
        self.assertEqual(listener['listener'], api_lb)

    def test_get_bad_listener_id(self):
        listener_path = self.listener_path
        self.get(listener_path.format(listener_id='SEAN-CONNERY'), status=404)

    def test_create(self, **optionals):
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
                       'loadbalancer_id': self.lb['loadbalancer']['id']}
        lb_listener.update(optionals)
        body = self._build_body(lb_listener)
        response = self.post(self.listeners_path, body)
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
        self.assert_correct_lb_status(self.lb['loadbalancer']['id'],
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_final_lb_statuses(self.lb['loadbalancer']['id'])
        self.assert_final_listener_statuses(self.lb['loadbalancer']['id'],
                                            listener_api.get('id'))

    def test_create_duplicate_fails(self):
        self.create_listener(constants.PROTOCOL_HTTP, 80,
                             self.lb['loadbalancer']['id'])
        self.set_lb_status(self.lb['loadbalancer']['id'])
        self.create_listener(constants.PROTOCOL_HTTP, 80,
                             self.lb['loadbalancer']['id'],
                             status=409)

    @testtools.skip('Skip until complete v2 merge')
    def test_create_with_default_pool_id(self):
        lb_listener = {'name': 'listener1',
                       'default_pool_id': self.pool.get('id'),
                       'description': 'desc1',
                       'admin_state_up': False,
                       'protocol': constants.PROTOCOL_HTTP,
                       'protocol_port': 80}
        response = self.post(self.listeners_path, lb_listener)
        api_listener = response.json
        self.assertEqual(api_listener.get('default_pool_id'),
                         self.pool.get('id'))

    def test_create_with_bad_default_pool_id(self):
        lb_listener = {'name': 'listener1',
                       'default_pool_id': uuidutils.generate_uuid(),
                       'description': 'desc1',
                       'admin_state_up': False,
                       'protocol': constants.PROTOCOL_HTTP,
                       'protocol_port': 80,
                       'loadbalancer_id': self.lb['loadbalancer']['id']}
        body = self._build_body(lb_listener)
        self.post(self.listeners_path, body, status=404)

    @testtools.skip('Skip until complete v2 merge')
    def test_create_with_shared_default_pool_id(self):
        lb_listener1 = {'name': 'listener1',
                        'default_pool_id': self.pool.get('id'),
                        'description': 'desc1',
                        'admin_state_up': False,
                        'protocol': constants.PROTOCOL_HTTP,
                        'protocol_port': 80}
        lb_listener2 = {'name': 'listener2',
                        'default_pool_id': self.pool.get('id'),
                        'description': 'desc2',
                        'admin_state_up': False,
                        'protocol': constants.PROTOCOL_HTTP,
                        'protocol_port': 81}
        body1 = self._build_body(lb_listener1)
        body2 = self._build_body(lb_listener2)
        listener1 = self.post(self.listeners_path, body1).json
        self.set_lb_status(self.lb.get('id'), constants.ACTIVE)
        listener2 = self.post(self.listeners_path, body2).json
        self.assertEqual(listener1['default_pool_id'], self.pool.get('id'))
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
                       'loadbalancer_id': self.lb['loadbalancer']['id']}
        body = self._build_body(lb_listener)
        response = self.post(self.listeners_path, body)
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
        self.assert_correct_lb_status(self.lb['loadbalancer']['id'],
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_final_lb_statuses(self.lb['loadbalancer']['id'])
        self.assert_final_listener_statuses(self.lb['loadbalancer']['id'],
                                            listener_api['id'])

    @testtools.skip('Skip until complete v2 merge')
    def test_update(self):
        tls_uuid = uuidutils.generate_uuid()
        listener = self.create_listener(self.lb['loadbalancer']['id'],
                                        constants.PROTOCOL_TCP, 80,
                                        name='listener1', description='desc1',
                                        enabled=False, connection_limit=10,
                                        default_tls_container_ref=tls_uuid,
                                        default_pool_id=None)
        self.set_lb_status(self.lb['loadbalancer']['id'])
        new_listener = {'name': 'listener2', 'admin_state_up': True,
                        'default_pool_id': self.pool.get('id')}
        listener_path = self.LISTENER_PATH.format(listener_id=listener['id'])
        api_listener = self.put(listener_path, new_listener).json
        update_expect = {'name': 'listener2', 'admin_state_up': True,
                         'default_pool_id': self.pool.get('id'),
                         'provisioning_status': constants.PENDING_UPDATE,
                         'operating_status': constants.ONLINE}
        listener.update(update_expect)
        self.assertEqual(listener.pop('created_at'),
                         api_listener.pop('created_at'))
        self.assertNotEqual(listener.pop('updated_at'),
                            api_listener.pop('updated_at'))
        self.assertNotEqual(listener, api_listener)
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_final_listener_statuses(self.lb.get('id'),
                                            api_listener.get('id'))

    def test_update_bad_listener_id(self):
        self.put(self.listener_path.format(listener_id='SEAN-CONNERY'),
                 body={}, status=404)

    @testtools.skip('Skip until complete v2 merge')
    def test_update_with_bad_default_pool_id(self):
        bad_pool_uuid = uuidutils.generate_uuid()
        listener = self.create_listener(self.lb.get('id'),
                                        constants.PROTOCOL_TCP, 80,
                                        name='listener1', description='desc1',
                                        enabled=False, connection_limit=10,
                                        default_pool_id=self.pool.get('id'))
        self.set_lb_status(self.lb.get('id'))
        new_listener = {'name': 'listener2', 'admin_state_up': True,
                        'default_pool_id': bad_pool_uuid}
        listener_path = self.LISTENER_PATH.format(
            lb_id=self.lb.get('id'), listener_id=listener.get('id'))
        self.put(listener_path, new_listener, status=404)
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.ACTIVE,
                                      constants.ONLINE)
        self.assert_final_listener_statuses(self.lb.get('id'),
                                            listener.get('id'))

    def test_create_listeners_same_port(self):
        listener1 = self.create_listener(constants.PROTOCOL_TCP, 80,
                                         self.lb['loadbalancer']['id'])
        self.set_lb_status(self.lb['loadbalancer']['id'])
        listener2_post = {'protocol': listener1['listener']['protocol'],
                          'protocol_port':
                          listener1['listener']['protocol_port'],
                          'loadbalancer_id': self.lb['loadbalancer']['id']}
        body = self._build_body(listener2_post)
        self.post(self.listeners_path, body, status=409)

    def test_delete(self):
        listener = self.create_listener(constants.PROTOCOL_HTTP, 80,
                                        self.lb['loadbalancer']['id'])
        self.set_lb_status(self.lb['loadbalancer']['id'])
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
        self.assert_correct_lb_status(self.lb['loadbalancer']['id'],
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_final_lb_statuses(self.lb['loadbalancer']['id'])
        self.assert_final_listener_statuses(self.lb['loadbalancer']['id'],
                                            api_listener['id'],
                                            delete=True)

    def test_delete_bad_listener_id(self):
        listener_path = self.LISTENER_PATH.format(listener_id='SEAN-CONNERY')
        self.delete(listener_path, status=404)

    def test_create_listener_bad_protocol(self):
        lb_listener = {'protocol': 'SEAN_CONNERY',
                       'protocol_port': 80}
        self.post(self.listeners_path, lb_listener, status=400)

    def test_update_listener_bad_protocol(self):
        listener = self.create_listener(constants.PROTOCOL_TCP, 80,
                                        self.lb['loadbalancer']['id'])
        self.set_lb_status(self.lb['loadbalancer']['id'])
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
        listener = self.create_listener(constants.PROTOCOL_TCP, 80,
                                        self.lb['loadbalancer']['id'])
        self.set_lb_status(self.lb['loadbalancer']['id'])
        listener_path = self.LISTENER_PATH.format(
            listener_id=listener['listener'].get('id'))
        self.put(listener_path, {}, status=400)

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
        self.delete(self.LB_PATH.format(lb_id=lb['loadbalancer']['id']))
        lb_listener_put = {'name': 'listener1_updated'}
        body = self._build_body(lb_listener_put)
        listener_path = self.LISTENER_PATH.format(
            listener_id=api_listener['id'])
        self.put(listener_path, body, status=409)

    def test_delete_pending_delete(self):
        lb = self.create_load_balancer(uuidutils.generate_uuid(),
                                       name='lb1', description='desc1',
                                       admin_state_up=False)
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
        self.delete(self.LB_PATH.format(lb_id=lb['loadbalancer']['id']))
        listener_path = self.LISTENER_PATH.format(
            listener_id=api_listener['id'])
        self.delete(listener_path, status=409)

    def test_create_with_tls_termination_data(self):
        cert_id = uuidutils.generate_uuid()
        listener = self.create_listener(constants.PROTOCOL_HTTP, 80,
                                        self.lb['loadbalancer']['id'],
                                        default_tls_container_ref=cert_id)
        listener_path = self.LISTENER_PATH.format(
            listener_id=listener['listener']['id'])
        get_listener = self.get(listener_path).json['listener']
        self.assertEqual(cert_id, get_listener['default_tls_container_ref'])

    def test_update_with_tls_termination_data(self):
        cert_id = uuidutils.generate_uuid()
        listener = self.create_listener(constants.PROTOCOL_HTTP, 80,
                                        self.lb['loadbalancer']['id'])
        self.set_lb_status(self.lb['loadbalancer']['id'])
        listener_path = self.LISTENER_PATH.format(
            listener_id=listener['listener']['id'])
        get_listener = self.get(listener_path).json['listener']
        self.assertIsNone(get_listener.get('default_tls_container_ref'))
        self.put(listener_path,
                 self._build_body({'default_tls_container_ref': cert_id}))
        get_listener = self.get(listener_path).json['listener']
        self.assertIsNone(get_listener.get('default_tls_container_ref'))

    def test_create_with_sni_data(self):
        sni_id1 = uuidutils.generate_uuid()
        sni_id2 = uuidutils.generate_uuid()
        listener = self.create_listener(constants.PROTOCOL_HTTP, 80,
                                        self.lb['loadbalancer']['id'],
                                        sni_container_refs=[sni_id1, sni_id2])
        listener_path = self.LISTENER_PATH.format(
            listener_id=listener['listener']['id'])
        get_listener = self.get(listener_path).json['listener']
        self.assertItemsEqual([sni_id1, sni_id2],
                              get_listener['sni_container_refs'])

    def test_update_with_sni_data(self):
        sni_id1 = uuidutils.generate_uuid()
        sni_id2 = uuidutils.generate_uuid()
        listener = self.create_listener(constants.PROTOCOL_HTTP, 80,
                                        self.lb['loadbalancer']['id'])
        self.set_lb_status(self.lb['loadbalancer']['id'])
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
                       'loadbalancer_id': self.lb['loadbalancer']['id'],
                       'insert_headers': {'X-Forwarded-For': 'true'}}
        body = self._build_body(lb_listener)
        self.post(self.listeners_path, body, status=201)

    def test_create_with_bad_insert_headers(self):
        lb_listener = {'protocol': 'HTTP',
                       'protocol_port': 80,
                       'loadbalancer_id': self.lb['loadbalancer']['id'],
                       # 'insert_headers': {'x': 'x'}}
                       'insert_headers': {'X-Forwarded-Four': 'true'}}
        body = self._build_body(lb_listener)
        self.post(self.listeners_path, body, status=400)
