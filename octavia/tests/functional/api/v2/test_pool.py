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
from octavia.tests.functional.api.v2 import base

import testtools


class TestPool(base.BaseAPITest):

    root_tag = 'pool'
    root_tag_list = 'pools'
    root_tag_links = 'pools_links'

    def setUp(self):
        super(TestPool, self).setUp()

        self.lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')
        self.lb_id = self.lb['id']

        self.set_lb_status(self.lb_id)

        self.listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80,
            self.lb_id).get('listener')
        self.listener_id = self.listener['id']

        self.set_lb_status(self.lb_id)

    def test_get(self):
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.listener_id)
        pool = api_pool.get('pool')
        # Set status to ACTIVE/ONLINE because set_lb_status did it in the db
        pool['provisioning_status'] = constants.ACTIVE
        pool['operating_status'] = constants.ONLINE
        pool.pop('updated_at')
        self.set_lb_status(lb_id=self.lb_id)
        response = self.get(self.POOL_PATH.format(pool_id=pool.get('id'))).json
        response_body = response.get('pool')
        response_body.pop('updated_at')
        self.assertEqual(pool, response_body)

    def test_bad_get(self):
        self.get(self.POOL_PATH.format(pool_id=uuidutils.generate_uuid()),
                 status=404)

    def test_get_all(self):
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.listener_id)
        pool = api_pool.get('pool')
        self.set_lb_status(lb_id=self.lb_id)
        response = self.get(self.POOLS_PATH).json
        response_body = response.get('pools')
        self.assertIsInstance(response_body, list)
        self.assertEqual(1, len(response_body))
        self.assertEqual(
            pool.get('id'), response_body[0].get('id'))

    def test_get_all_with_listener(self):
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.listener_id)
        pool = api_pool.get('pool')
        self.set_lb_status(lb_id=self.lb_id)
        response = self.get(self.POOLS_PATH).json
        response_body = response.get('pools')
        self.assertIsInstance(response_body, list)
        self.assertEqual(1, len(response_body))
        self.assertEqual(pool.get('id'), response_body[0].get('id'))

    def test_empty_get_all(self):
        response = self.get(self.POOLS_PATH).json
        response_body = response.get('pools')
        self.assertIsInstance(response_body, list)
        self.assertEqual(0, len(response_body))

    def test_create(self):
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.listener_id)
        pool = api_pool.get('pool')
        self.assert_correct_lb_status(
            self.lb_id,
            constants.PENDING_UPDATE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.PENDING_UPDATE,
            constants.ONLINE,
            self.listener_id)
        self.set_lb_status(self.lb_id)
        self.assertEqual(constants.PROTOCOL_HTTP, pool.get('protocol'))
        self.assertEqual(constants.LB_ALGORITHM_ROUND_ROBIN,
                         pool.get('lb_algorithm'))
        self.assertIsNotNone(pool.get('created_at'))
        self.assertIsNone(pool.get('updated_at'))
        self.assert_correct_lb_status(
            self.lb_id,
            constants.ACTIVE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.ACTIVE,
            constants.ONLINE,
            self.listener_id)

    def test_create_sans_listener(self):
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN)
        pool = api_pool.get('pool')
        self.assertEqual(constants.PROTOCOL_HTTP, pool.get('protocol'))
        self.assertEqual(constants.LB_ALGORITHM_ROUND_ROBIN,
                         pool.get('lb_algorithm'))
        # Make sure listener status is unchanged, but LB status is changed.
        # LB should still be locked even with pool and subordinate object
        # updates.
        self.assert_correct_listener_status(
            constants.ACTIVE,
            constants.ONLINE,
            self.listener_id)
        self.assert_correct_lb_status(
            self.lb_id,
            constants.PENDING_UPDATE,
            constants.ONLINE)

    def test_create_sans_loadbalancer_id(self):
        api_pool = self.create_pool(
            None,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.listener_id)
        pool = api_pool.get('pool')
        self.assertEqual(constants.PROTOCOL_HTTP, pool.get('protocol'))
        self.assertEqual(constants.LB_ALGORITHM_ROUND_ROBIN,
                         pool.get('lb_algorithm'))
        self.assert_correct_listener_status(
            constants.PENDING_UPDATE,
            constants.ONLINE,
            self.listener_id)
        self.assert_correct_lb_status(
            self.lb_id,
            constants.PENDING_UPDATE,
            constants.ONLINE)

    def test_create_with_listener_id_in_pool_dict(self):
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.listener_id)
        pool = api_pool.get('pool')
        self.assert_correct_lb_status(
            self.lb_id,
            constants.PENDING_UPDATE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.PENDING_UPDATE,
            constants.ONLINE,
            self.listener_id)
        self.set_lb_status(self.lb_id)
        self.assertEqual(constants.PROTOCOL_HTTP, pool.get('protocol'))
        self.assertEqual(constants.LB_ALGORITHM_ROUND_ROBIN,
                         pool.get('lb_algorithm'))
        self.assert_correct_lb_status(
            self.lb_id,
            constants.ACTIVE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.ACTIVE,
            constants.ONLINE,
            self.listener_id)

    def test_create_with_project_id(self):
        pid = self.lb.get('project_id')
        optionals = {
            'listener_id': self.listener_id,
            'project_id': pid}
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            **optionals)
        pool = api_pool.get('pool')
        self.assertEqual(pid, pool.get('tenant_id'))

    def test_bad_create(self):
        lb_pool = {'name': 'test1'}
        self.post(self.POOLS_PATH, self._build_body(lb_pool), status=400)
        self.assert_correct_lb_status(
            self.lb_id,
            constants.ACTIVE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.ACTIVE,
            constants.ONLINE,
            self.listener_id)

    def test_create_with_listener_with_default_pool_id_set(self):
        self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.listener_id)
        self.set_lb_status(self.lb_id, constants.ACTIVE)
        path = self.POOLS_PATH
        lb_pool = {
            'loadbalancer_id': self.lb_id,
            'listener_id': self.listener_id,
            'protocol': constants.PROTOCOL_HTTP,
            'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
            'project_id': self.project_id}
        self.post(path, self._build_body(lb_pool), status=409)

    def test_create_bad_protocol(self):
        lb_pool = {
            'loadbalancer_id': self.lb_id,
            'protocol': 'STUPID_PROTOCOL',
            'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN}
        self.post(self.POOLS_PATH, self._build_body(lb_pool), status=400)

    def test_create_with_bad_handler(self):
        self.handler_mock_bug_workaround.pool.create.side_effect = Exception()
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.listener_id)
        # This mock doesn't recycle properly so we have to do cleanup manually
        self.handler_mock_bug_workaround.pool.create.side_effect = None
        self.assert_correct_lb_status(
            self.lb_id,
            constants.ACTIVE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.ACTIVE,
            constants.ONLINE,
            self.listener_id)
        self.assert_correct_pool_status(
            constants.ERROR,
            constants.OFFLINE,
            api_pool['pool']['id']
        )

    def test_create_over_quota(self):
        self.check_quota_met_true_mock.start()
        self.addCleanup(self.check_quota_met_true_mock.stop)
        lb_pool = {
            'loadbalancer_id': self.lb_id,
            'protocol': constants.PROTOCOL_HTTP,
            'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
            'project_id': self.project_id}
        self.post(self.POOLS_PATH, self._build_body(lb_pool), status=403)

    def test_update(self):
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.listener_id)
        pool = api_pool.get('pool')
        self.set_lb_status(lb_id=self.lb_id)
        new_pool = {'name': 'new_name'}
        self.put(self.POOL_PATH.format(pool_id=pool.get('id')),
                 self._build_body(new_pool))
        self.assert_correct_lb_status(
            self.lb_id,
            constants.PENDING_UPDATE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.PENDING_UPDATE,
            constants.ONLINE,
            self.listener_id)
        self.assert_correct_pool_status(
            constants.PENDING_UPDATE,
            constants.ONLINE,
            pool.get('id'))
        self.set_lb_status(self.lb_id)
        response = self.get(self.POOL_PATH.format(pool_id=pool.get('id'))).json
        response_body = response.get('pool')
        self.assertNotEqual('new_name', response_body.get('name'))
        self.assertIsNotNone(response_body.get('created_at'))
        self.assertIsNotNone(response_body.get('updated_at'))
        self.assert_correct_lb_status(
            self.lb_id,
            constants.ACTIVE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.ACTIVE,
            constants.ONLINE,
            self.listener_id)

    def test_bad_update(self):
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.listener_id)
        pool = api_pool.get('pool')
        self.set_lb_status(self.lb_id)
        new_pool = {'enabled': 'one'}
        self.put(self.POOL_PATH.format(pool_id=pool.get('id')),
                 self._build_body(new_pool), status=400)
        self.assert_correct_lb_status(
            self.lb_id,
            constants.ACTIVE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.ACTIVE,
            constants.ONLINE,
            self.listener_id)

    def test_update_with_bad_handler(self):
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.listener_id)
        pool = api_pool.get('pool')
        self.set_lb_status(lb_id=self.lb_id)
        new_pool = {'name': 'new_name'}
        self.handler_mock_bug_workaround.pool.update.side_effect = Exception()
        self.put(self.POOL_PATH.format(pool_id=pool.get('id')),
                 self._build_body(new_pool))
        # This mock doesn't recycle properly so we have to do cleanup manually
        self.handler_mock_bug_workaround.pool.update.side_effect = None
        self.assert_correct_lb_status(
            self.lb_id,
            constants.ACTIVE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.ACTIVE,
            constants.ONLINE,
            self.listener_id)
        self.assert_correct_pool_status(
            constants.ERROR,
            constants.ONLINE,
            pool.get('id')
        )

    def test_delete(self):
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.listener_id)
        pool = api_pool.get('pool')
        self.set_lb_status(lb_id=self.lb_id)
        # Set status to ACTIVE/ONLINE because set_lb_status did it in the db
        pool['provisioning_status'] = constants.ACTIVE
        pool['operating_status'] = constants.ONLINE
        pool.pop('updated_at')

        response = self.get(self.POOL_PATH.format(
            pool_id=pool.get('id'))).json
        pool_body = response.get('pool')

        pool_body.pop('updated_at')
        self.assertEqual(pool, pool_body)

        self.delete(self.POOL_PATH.format(pool_id=pool.get('id')))

        self.assert_correct_lb_status(
            self.lb_id,
            constants.PENDING_UPDATE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.PENDING_UPDATE,
            constants.ONLINE,
            self.listener_id)
        self.assert_correct_pool_status(
            constants.PENDING_DELETE,
            constants.ONLINE,
            pool.get('id'))

    def test_bad_delete(self):
        self.delete(self.POOL_PATH.format(
            pool_id=uuidutils.generate_uuid()), status=404)

    @testtools.skip('Skip until complete v2 merge.')
    def test_delete_with_l7policy(self):
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.listener_id)
        self.set_lb_status(lb_id=self.lb_id)
        pool = api_pool.get('pool')
        self.create_l7policy(
            self.listener_id,
            constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
            redirect_pool_id=api_pool.get('id'))
        self.set_lb_status(lb_id=self.lb_id)
        self.delete(self.POOL_PATH.format(
            pool_id=pool.get('id')), status=409)

    def test_delete_with_bad_handler(self):
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.listener_id)
        pool = api_pool.get('pool')
        self.set_lb_status(lb_id=self.lb_id)
        # Set status to ACTIVE/ONLINE because set_lb_status did it in the db
        pool['provisioning_status'] = constants.ACTIVE
        pool['operating_status'] = constants.ONLINE
        response = self.get(self.POOL_PATH.format(
            pool_id=pool.get('id'))).json
        pool_body = response.get('pool')

        self.assertIsNone(pool.pop('updated_at'))
        self.assertIsNotNone(pool_body.pop('updated_at'))
        self.assertEqual(pool, pool_body)
        self.handler_mock_bug_workaround.pool.delete.side_effect = Exception()
        self.delete(self.POOL_PATH.format(pool_id=pool.get('id')))
        # This mock doesn't recycle properly so we have to do cleanup manually
        self.handler_mock_bug_workaround.pool.delete.side_effect = None
        self.assert_correct_lb_status(
            self.lb_id,
            constants.ACTIVE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.ACTIVE,
            constants.ONLINE,
            self.listener_id)
        self.assert_correct_pool_status(
            constants.ERROR,
            constants.ONLINE,
            pool.get('id')
        )

    def test_create_with_session_persistence(self):
        sp = {"type": constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              "cookie_name": "test_cookie_name"}
        optionals = {"listener_id": self.listener_id,
                     "session_persistence": sp}
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            **optionals)
        pool = api_pool.get('pool')
        self.assert_correct_lb_status(
            self.lb_id,
            constants.PENDING_UPDATE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.PENDING_UPDATE,
            constants.ONLINE,
            self.listener_id)
        self.set_lb_status(self.lb_id)
        response = self.get(self.POOL_PATH.format(
            pool_id=pool.get('id'))).json
        pool_body = response.get('pool')
        sess_p = pool_body.get('session_persistence')
        self.assertIsNotNone(sess_p)
        self.assertEqual(constants.SESSION_PERSISTENCE_HTTP_COOKIE,
                         sess_p.get('type'))
        self.assertEqual('test_cookie_name', sess_p.get('cookie_name'))
        self.assert_correct_lb_status(
            self.lb_id,
            constants.ACTIVE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.ACTIVE,
            constants.ONLINE,
            self.listener_id)

    def test_create_with_bad_session_persistence(self):
        sp = {"type": "persistence_type",
              "cookie_name": "test_cookie_name"}
        lb_pool = {
            'loadbalancer_id': self.lb_id,
            'listener_id': self.listener_id,
            'protocol': constants.PROTOCOL_HTTP,
            'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
            'session_persistence': sp}
        self.post(self.POOLS_PATH, self._build_body(lb_pool), status=400)

    def test_add_session_persistence(self):
        sp = {"type": constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              "cookie_name": "test_cookie_name"}
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.listener_id)
        pool = api_pool.get('pool')
        self.set_lb_status(lb_id=self.lb_id)
        new_pool = {'session_persistence': sp}
        self.put(self.POOL_PATH.format(pool_id=pool.get('id')),
                 self._build_body(new_pool))
        response = self.get(self.POOL_PATH.format(pool_id=pool.get('id'))).json
        pool_body = response.get('pool')
        self.assert_correct_lb_status(
            self.lb_id,
            constants.PENDING_UPDATE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.PENDING_UPDATE,
            constants.ONLINE,
            self.listener_id)
        self.assertNotEqual(sp, pool_body.get('session_persistence'))

    def test_update_session_persistence(self):
        sp = {"type": constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              "cookie_name": "test_cookie_name"}
        optionals = {"listener_id": self.listener_id,
                     "session_persistence": sp}
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            **optionals)
        pool = api_pool.get('pool')
        self.set_lb_status(lb_id=self.lb_id)
        response = self.get(self.POOL_PATH.format(
            pool_id=pool.get('id'))).json
        pool_body = response.get('pool')
        sess_p = pool_body.get('session_persistence')
        sess_p['cookie_name'] = None
        sess_p['type'] = constants.SESSION_PERSISTENCE_SOURCE_IP
        new_pool = {'session_persistence': sess_p}
        self.put(self.POOL_PATH.format(pool_id=pool.get('id')),
                 self._build_body(new_pool))
        response = self.get(self.POOL_PATH.format(pool_id=pool.get('id'))).json
        pool_body = response.get('pool')
        self.assert_correct_lb_status(
            self.lb_id,
            constants.PENDING_UPDATE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.PENDING_UPDATE,
            constants.ONLINE,
            self.listener_id)
        self.assertNotEqual(sess_p, pool_body.get('session_persistence'))
        self.set_lb_status(self.lb_id)
        self.assert_correct_lb_status(
            self.lb_id,
            constants.ACTIVE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.ACTIVE,
            constants.ONLINE,
            self.listener_id)

    def test_update_preserve_session_persistence(self):
        sp = {"type": constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              "cookie_name": "test_cookie_name"}
        optionals = {"listener_id": self.listener_id,
                     "name": "name", "session_persistence": sp}
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            **optionals)
        pool = api_pool.get('pool')
        self.set_lb_status(lb_id=self.lb_id)
        new_pool = {'name': 'update_name'}
        self.put(self.POOL_PATH.format(pool_id=pool.get('id')),
                 self._build_body(new_pool))
        response = self.get(self.POOL_PATH.format(pool_id=pool.get('id'))).json
        pool_body = response.get('pool')
        self.assert_correct_lb_status(
            self.lb_id,
            constants.PENDING_UPDATE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.PENDING_UPDATE,
            constants.ONLINE,
            self.listener_id)
        response = self.get(self.POOL_PATH.format(
            pool_id=pool_body.get('id'))).json
        pool_body = response.get('pool')
        self.assertEqual(sp, pool_body.get('session_persistence'))

    @testtools.skip('This test should pass with a validation layer')
    def test_update_bad_session_persistence(self):
        sp = {"type": constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              "cookie_name": "test_cookie_name"}
        optionals = {"listener_id": self.listener_id,
                     "session_persistence": sp}
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            **optionals)
        pool = api_pool.get('pool')
        self.set_lb_status(lb_id=self.lb_id)
        response = self.get(self.POOL_PATH.format(
            pool_id=api_pool.get('id'))).json
        pool_body = response.get('pools')
        sess_p = pool_body.get('session_persistence')
        sess_p['type'] = 'persistence_type'
        new_pool = {'session_persistence': sess_p}
        self.put(self.POOL_PATH.format(pool_id=pool.get('id')),
                 self._build_body(new_pool), status=400)

    def test_delete_with_session_persistence(self):
        sp = {"type": constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              "cookie_name": "test_cookie_name"}
        optionals = {"listener_id": self.listener_id,
                     "session_persistence": sp}
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            **optionals)
        pool = api_pool.get('pool')
        self.set_lb_status(lb_id=self.lb_id)
        self.delete(self.POOL_PATH.format(pool_id=pool.get('id')))
        self.assert_correct_lb_status(
            self.lb_id,
            constants.PENDING_UPDATE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.PENDING_UPDATE,
            constants.ONLINE,
            self.listener_id)
        self.set_lb_status(self.lb_id)
        self.assert_correct_lb_status(
            self.lb_id,
            constants.ACTIVE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.ACTIVE,
            constants.ONLINE,
            self.listener_id)

    def test_delete_session_persistence(self):
        sp = {"type": constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              "cookie_name": "test_cookie_name"}
        optionals = {"listener_id": self.listener_id,
                     "session_persistence": sp}
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            **optionals)
        pool = api_pool.get('pool')
        self.set_lb_status(lb_id=self.lb_id)
        new_sp = {"pool": {"session_persistence": None}}
        response = self.put(self.POOL_PATH.format(pool_id=pool.get('id')),
                            new_sp).json
        pool_body = response.get('pool')
        self.assert_correct_lb_status(
            self.lb_id,
            constants.PENDING_UPDATE,
            constants.ONLINE)
        self.assert_correct_listener_status(
            constants.PENDING_UPDATE,
            constants.ONLINE,
            self.listener_id)
        self.assertIsNotNone(pool_body.get('session_persistence'))

    def test_create_when_lb_pending_update(self):
        self.put(self.LB_PATH.format(lb_id=self.lb_id),
                 {'loadbalancer': {'name': 'test_name_change'}})
        lb_pool = {
            'loadbalancer_id': self.lb_id,
            'listener_id': self.listener_id,
            'protocol': constants.PROTOCOL_HTTP,
            'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
            'project_id': self.project_id}
        self.post(self.POOLS_PATH, self._build_body(lb_pool), status=409)

    def test_update_when_lb_pending_update(self):
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.listener_id)
        pool = api_pool.get('pool')
        self.set_lb_status(self.lb_id)
        self.put(self.LB_PATH.format(lb_id=self.lb_id),
                 {'loadbalancer': {'name': 'test_name_change'}})
        new_pool = {'admin_state_up': False}
        self.put(self.POOL_PATH.format(pool_id=pool.get('id')),
                 self._build_body(new_pool), status=409)

    def test_delete_when_lb_pending_update(self):
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.listener_id)
        pool = api_pool.get('pool')
        self.set_lb_status(self.lb_id)
        self.put(self.LB_PATH.format(lb_id=self.lb_id),
                 {"loadbalancer": {'name': 'test_name_change'}})
        self.delete(self.POOL_PATH.format(pool_id=pool.get('id')), status=409)

    def test_create_when_lb_pending_delete(self):
        self.delete(self.LB_PATH.format(lb_id=self.lb_id))
        new_pool = {
            'loadbalancer_id': self.lb_id,
            'listener_id': self.listener_id,
            'protocol': constants.PROTOCOL_HTTP,
            'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
            'project_id': self.project_id}
        self.post(self.POOLS_PATH, self._build_body(new_pool), status=409)

    def test_update_when_lb_pending_delete(self):
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.listener_id)
        pool = api_pool.get('pool')
        self.set_lb_status(self.lb_id)
        self.delete(self.LB_PATH.format(lb_id=self.lb_id))
        new_pool = {'admin_state_up': False}
        self.put(self.POOL_PATH.format(pool_id=pool.get('id')),
                 self._build_body(new_pool), status=409)

    def test_delete_when_lb_pending_delete(self):
        api_pool = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.listener_id)
        pool = api_pool.get('pool')
        self.set_lb_status(self.lb_id)
        self.delete(self.LB_PATH.format(lb_id=self.lb_id))
        self.delete(self.POOL_PATH.format(pool_id=pool.get('id')), status=409)
