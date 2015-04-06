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

from oslo_utils import uuidutils

from octavia.common import constants
from octavia.tests.functional.api.v1 import base


class TestMember(base.BaseAPITest):

    def setUp(self):
        super(TestMember, self).setUp()
        self.lb = self.create_load_balancer({})
        self.set_lb_status(self.lb.get('id'))
        self.listener = self.create_listener(self.lb.get('id'),
                                             constants.PROTOCOL_HTTP, 80)
        self.set_lb_status(self.lb.get('id'))
        self.pool = self.create_pool(self.lb.get('id'),
                                     self.listener.get('id'),
                                     constants.PROTOCOL_HTTP,
                                     constants.LB_ALGORITHM_ROUND_ROBIN)
        self.set_lb_status(self.lb.get('id'))
        self.members_path = self.MEMBERS_PATH.format(
            lb_id=self.lb.get('id'), listener_id=self.listener.get('id'),
            pool_id=self.pool.get('id'))
        self.member_path = self.members_path + '/{member_id}'

    def test_get(self):
        api_member = self.create_member(self.lb.get('id'),
                                        self.listener.get('id'),
                                        self.pool.get('id'),
                                        '10.0.0.1', 80)
        response = self.get(self.member_path.format(
            member_id=api_member.get('id')))
        response_body = response.json
        self.assertEqual(api_member, response_body)

    def test_bad_get(self):
        self.get(self.member_path.format(member_id=uuidutils.generate_uuid()),
                 status=404)

    def test_get_all(self):
        api_m_1 = self.create_member(self.lb.get('id'),
                                     self.listener.get('id'),
                                     self.pool.get('id'),
                                     '10.0.0.1', 80)
        self.set_lb_status(self.lb.get('id'))
        api_m_2 = self.create_member(self.lb.get('id'),
                                     self.listener.get('id'),
                                     self.pool.get('id'),
                                     '10.0.0.2', 80)
        self.set_lb_status(self.lb.get('id'))
        # Original objects didn't have the updated operating status that exists
        # in the DB.
        api_m_1['operating_status'] = constants.ONLINE
        api_m_2['operating_status'] = constants.ONLINE
        response = self.get(self.members_path)
        response_body = response.json
        self.assertIsInstance(response_body, list)
        self.assertEqual(2, len(response_body))
        self.assertIn(api_m_1, response_body)
        self.assertIn(api_m_2, response_body)

    def test_empty_get_all(self):
        response = self.get(self.members_path)
        response_body = response.json
        self.assertIsInstance(response_body, list)
        self.assertEqual(0, len(response_body))

    def test_create(self):
        api_member = self.create_member(self.lb.get('id'),
                                        self.listener.get('id'),
                                        self.pool.get('id'),
                                        '10.0.0.1', 80)
        self.assertEqual('10.0.0.1', api_member.get('ip_address'))
        self.assertEqual(80, api_member.get('protocol_port'))
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ONLINE)
        self.set_lb_status(self.lb.get('id'))
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.ACTIVE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.ACTIVE, constants.ONLINE)

    def test_create_with_id(self):
        mid = uuidutils.generate_uuid()
        api_member = self.create_member(self.lb.get('id'),
                                        self.listener.get('id'),
                                        self.pool.get('id'),
                                        '10.0.0.1', 80, id=mid)
        self.assertEqual(mid, api_member.get('id'))

    def test_create_with_duplicate_id(self):
        member = self.create_member(self.lb.get('id'),
                                    self.listener.get('id'),
                                    self.pool.get('id'),
                                    '10.0.0.1', 80)
        self.set_lb_status(self.lb.get('id'), constants.ACTIVE)
        path = self.MEMBERS_PATH.format(lb_id=self.lb.get('id'),
                                        listener_id=self.listener.get('id'),
                                        pool_id=self.pool.get('id'))
        body = {'id': member.get('id'), 'ip_address': '10.0.0.3',
                'protocol_port': 81}
        self.post(path, body, status=409, expect_errors=True)

    def test_bad_create(self):
        api_member = {'name': 'test1'}
        self.post(self.members_path, api_member, status=400)

    def test_duplicate_create(self):
        member = {'ip_address': '10.0.0.1', 'protocol_port': 80}
        self.post(self.members_path, member, status=202)
        self.set_lb_status(self.lb.get('id'))
        self.post(self.members_path, member, status=409)

    def test_update(self):
        old_port = 80
        new_port = 88
        api_member = self.create_member(self.lb.get('id'),
                                        self.listener.get('id'),
                                        self.pool.get('id'),
                                        '10.0.0.1', old_port)
        self.set_lb_status(self.lb.get('id'))
        new_member = {'protocol_port': new_port}
        response = self.put(self.member_path.format(
            member_id=api_member.get('id')), new_member, status=202)
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ONLINE)
        self.set_lb_status(self.lb.get('id'))
        response_body = response.json
        self.assertEqual(old_port, response_body.get('protocol_port'))

        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.ACTIVE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.ACTIVE, constants.ONLINE)

    def test_bad_update(self):
        api_member = self.create_member(self.lb.get('id'),
                                        self.listener.get('id'),
                                        self.pool.get('id'),
                                        '10.0.0.1', 80)
        new_member = {'protocol_port': 'ten'}
        self.put(self.member_path.format(member_id=api_member.get('id')),
                 new_member, expect_errors=True)

    def test_duplicate_update(self):
        self.skip('This test should pass after a validation layer.')
        member = {'ip_address': '10.0.0.1', 'protocol_port': 80}
        self.post(self.members_path, member)
        self.set_lb_status(self.lb.get('id'))
        member['protocol_port'] = 81
        response = self.post(self.members_path, member)
        self.set_lb_status(self.lb.get('id'))
        member2 = response.json
        member['protocol_port'] = 80
        self.put(self.member_path.format(member_id=member2.get('id')),
                 member, status=409)

    def test_delete(self):
        api_member = self.create_member(self.lb.get('id'),
                                        self.listener.get('id'),
                                        self.pool.get('id'),
                                        '10.0.0.1', 80)
        self.set_lb_status(self.lb.get('id'))
        response = self.get(self.member_path.format(
            member_id=api_member.get('id')))
        api_member['operating_status'] = constants.ONLINE
        self.assertEqual(api_member, response.json)
        self.delete(self.member_path.format(member_id=api_member.get('id')))
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ONLINE)
        self.set_lb_status(self.lb.get('id'))
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.ACTIVE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.ACTIVE, constants.ONLINE)

    def test_bad_delete(self):
        self.delete(self.member_path.format(
            member_id=uuidutils.generate_uuid()), status=404)

    def test_create_when_lb_pending_update(self):
        self.create_member(self.lb.get('id'), self.listener.get('id'),
                           self.pool.get('id'), ip_address="10.0.0.2",
                           protocol_port=80)
        self.set_lb_status(self.lb.get('id'))
        self.put(self.LB_PATH.format(lb_id=self.lb.get('id')),
                 body={'name': 'test_name_change'})
        self.post(self.members_path,
                  body={'ip_address': '10.0.0.1', 'protocol_port': 80},
                  status=409)

    def test_update_when_lb_pending_update(self):
        member = self.create_member(self.lb.get('id'), self.listener.get('id'),
                                    self.pool.get('id'), ip_address="10.0.0.1",
                                    protocol_port=80)
        self.set_lb_status(self.lb.get('id'))
        self.put(self.LB_PATH.format(lb_id=self.lb.get('id')),
                 body={'name': 'test_name_change'})
        self.put(self.member_path.format(member_id=member.get('id')),
                 body={'protocol_port': 88}, status=409)

    def test_delete_when_lb_pending_update(self):
        member = self.create_member(self.lb.get('id'), self.listener.get('id'),
                                    self.pool.get('id'), ip_address="10.0.0.1",
                                    protocol_port=80)
        self.set_lb_status(self.lb.get('id'))
        self.put(self.LB_PATH.format(lb_id=self.lb.get('id')),
                 body={'name': 'test_name_change'})
        self.delete(self.member_path.format(member_id=member.get('id')),
                    status=409)

    def test_create_when_lb_pending_delete(self):
        self.create_member(self.lb.get('id'), self.listener.get('id'),
                           self.pool.get('id'), ip_address="10.0.0.1",
                           protocol_port=80)
        self.set_lb_status(self.lb.get('id'))
        self.delete(self.LB_PATH.format(lb_id=self.lb.get('id')))
        self.post(self.members_path,
                  body={'ip_address': '10.0.0.2', 'protocol_port': 88},
                  status=409)

    def test_update_when_lb_pending_delete(self):
        member = self.create_member(self.lb.get('id'), self.listener.get('id'),
                                    self.pool.get('id'), ip_address="10.0.0.1",
                                    protocol_port=80)
        self.set_lb_status(self.lb.get('id'))
        self.delete(self.LB_PATH.format(lb_id=self.lb.get('id')))
        self.put(self.member_path.format(member_id=member.get('id')),
                 body={'protocol_port': 88}, status=409)

    def test_delete_when_lb_pending_delete(self):
        member = self.create_member(self.lb.get('id'), self.listener.get('id'),
                                    self.pool.get('id'), ip_address="10.0.0.1",
                                    protocol_port=80)
        self.set_lb_status(self.lb.get('id'))
        self.delete(self.LB_PATH.format(lb_id=self.lb.get('id')))
        self.delete(self.member_path.format(member_id=member.get('id')),
                    status=409)
