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


class TestHealthMonitor(base.BaseAPITest):

    root_tag = 'healthmonitor'
    root_tag_list = 'healthmonitors'
    root_tag_links = 'healthmonitors_links'

    def setUp(self):
        super(TestHealthMonitor, self).setUp()
        self.lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')
        self.lb_id = self.lb.get('id')
        self.set_lb_status(self.lb_id)
        self.listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80,
            self.lb_id).get('listener')
        self.listener_id = self.listener.get('id')
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

    def test_get(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        # Set status to ACTIVE/ONLINE because set_lb_status did it in the db
        api_hm['provisioning_status'] = constants.ACTIVE
        api_hm['operating_status'] = constants.ONLINE
        api_hm.pop('updated_at')
        self.set_lb_status(self.lb_id)
        response = self.get(self.HM_PATH.format(
            healthmonitor_id=api_hm.get('id'))).json.get(self.root_tag)
        response.pop('updated_at')
        self.assertEqual(api_hm, response)

    def test_bad_get(self):
        self.get(self.HM_PATH.format(
            healthmonitor_id=uuidutils.generate_uuid()), status=404)

    def test_get_all(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        hms = self.get(self.HMS_PATH).json.get(self.root_tag_list)
        self.assertIsInstance(hms, list)
        self.assertEqual(1, len(hms))
        self.assertEqual(api_hm.get('id'), hms[0].get('id'))

    def test_create_http_monitor_with_relative_path(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1, url_path="/").get(self.root_tag)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.ACTIVE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_CREATE,
            hm_op_status=constants.OFFLINE)

    def test_create_sans_listener(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.ACTIVE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_CREATE,
            hm_op_status=constants.OFFLINE)
        self.set_lb_status(self.lb_id)
        self.assertEqual(constants.HEALTH_MONITOR_HTTP, api_hm.get('type'))
        self.assertEqual(1, api_hm.get('delay'))
        self.assertEqual(1, api_hm.get('timeout'))
        self.assertEqual(1, api_hm.get('max_retries_down'))
        self.assertEqual(1, api_hm.get('max_retries'))
        # Verify optional field defaults
        self.assertEqual('GET', api_hm.get('http_method'))
        self.assertEqual('/', api_hm.get('url_path'))
        self.assertEqual('200', api_hm.get('expected_codes'))

    def test_create_with_listener(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_CREATE,
            hm_op_status=constants.OFFLINE)
        self.set_lb_status(self.lb_id)
        self.assertEqual(constants.HEALTH_MONITOR_HTTP, api_hm.get('type'))
        self.assertEqual(1, api_hm.get('delay'))
        self.assertEqual(1, api_hm.get('timeout'))
        self.assertEqual(1, api_hm.get('max_retries_down'))
        self.assertEqual(1, api_hm.get('max_retries'))
        # Verify optional field defaults
        self.assertEqual('GET', api_hm.get('http_method'))
        self.assertEqual('/', api_hm.get('url_path'))
        self.assertEqual('200', api_hm.get('expected_codes'))

    # TODO(rm_work) Remove after deprecation of project_id in POST (R series)
    def test_create_with_project_id_is_ignored(self):
        pid = uuidutils.generate_uuid()
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1,
            project_id=pid).get(self.root_tag)
        self.assertEqual(self.project_id, api_hm.get('project_id'))

    def test_bad_create(self):
        hm_json = {'name': 'test1', 'pool_id': self.pool_id}
        self.post(self.HMS_PATH, self._build_body(hm_json), status=400)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id)

    def test_create_with_bad_handler(self):
        self.handler_mock().health_monitor.create.side_effect = Exception()
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1).get(self.root_tag)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id,
            hm_id=api_hm.get('id'),
            lb_prov_status=constants.ACTIVE,
            listener_prov_status=constants.ACTIVE,
            pool_prov_status=constants.ACTIVE,
            hm_prov_status=constants.ERROR,
            hm_op_status=constants.OFFLINE)

    def test_duplicate_create(self):
        # TODO(rm_work): I am fairly certain this is the same issue as we see
        # in test_repositories.py where PySqlite commits too early and can't
        # roll back, causing things to get out of whack. This runs fine solo.
        # It would be useful to test this *in reality* and see if it breaks.
        self.skipTest("PySqlite transaction handling is broken. We can unskip"
                      "this when `test_sqlite_transactions_broken` fails.")
        self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1)
        self.set_lb_status(self.lb_id)
        self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1,
            status=409)

    def test_update(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_hm = {'max_retries': 2}
        self.put(
            self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
            self._build_body(new_hm))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_UPDATE)

    def test_bad_update(self):
        self.skip("This test will need reviewed after a validation layer is "
                  "built")
        self.create_health_monitor(self.lb_id,
                                   self.pool_id,
                                   constants.HEALTH_MONITOR_HTTP,
                                   1, 1, 1, 1)
        new_hm = {'type': 'bad_type', 'delay': 2}
        self.set_lb_status(self.lb_id)
        self.put(self.HM_PATH, self._build_body(new_hm), status=400)

    def test_update_with_bad_handler(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_hm = {'max_retries': 2}
        self.handler_mock().health_monitor.update.side_effect = Exception()
        self.put(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                 self._build_body(new_hm))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, hm_id=api_hm.get('id'),
            hm_prov_status=constants.ERROR)

    def test_delete(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        hm = self.get(self.HM_PATH.format(
            healthmonitor_id=api_hm.get('id'))).json.get(self.root_tag)
        api_hm['provisioning_status'] = constants.ACTIVE
        api_hm['operating_status'] = constants.ONLINE
        self.assertIsNone(api_hm.pop('updated_at'))
        self.assertIsNotNone(hm.pop('updated_at'))
        self.assertEqual(api_hm, hm)
        self.delete(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_DELETE)

    def test_bad_delete(self):
        self.delete(
            self.HM_PATH.format(healthmonitor_id=uuidutils.generate_uuid()),
            status=404)

    def test_delete_with_bad_handler(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        hm = self.get(self.HM_PATH.format(
            healthmonitor_id=api_hm.get('id'))).json.get(self.root_tag)
        api_hm['provisioning_status'] = constants.ACTIVE
        api_hm['operating_status'] = constants.ONLINE
        self.assertIsNone(api_hm.pop('updated_at'))
        self.assertIsNotNone(hm.pop('updated_at'))
        self.assertEqual(api_hm, hm)
        self.handler_mock().health_monitor.delete.side_effect = Exception()
        self.delete(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, hm_id=api_hm.get('id'),
            hm_prov_status=constants.ERROR)

    def test_create_when_lb_pending_update(self):
        self.put(self.LB_PATH.format(lb_id=self.lb_id),
                 body={'loadbalancer': {'name': 'test_name_change'}})
        self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1, status=409)

    def test_update_when_lb_pending_update(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.put(self.LB_PATH.format(lb_id=self.lb_id),
                 body={'loadbalancer': {'name': 'test_name_change'}})
        new_hm = {'max_retries': 2}
        self.put(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                 body=self._build_body(new_hm), status=409)

    def test_delete_when_lb_pending_update(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.put(self.LB_PATH.format(lb_id=self.lb_id),
                 body={'loadbalancer': {'name': 'test_name_change'}})
        self.delete(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                    status=409)

    def test_create_when_lb_pending_delete(self):
        self.delete(self.LB_PATH.format(lb_id=self.lb_id))
        self.create_health_monitor(
            self.pool_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1, status=409)

    def test_update_when_lb_pending_delete(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.delete(self.LB_PATH.format(lb_id=self.lb_id))
        new_hm = {'max_retries': 2}
        self.put(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                 body=self._build_body(new_hm), status=409)

    def test_delete_when_lb_pending_delete(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.delete(self.LB_PATH.format(lb_id=self.lb_id))
        self.delete(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                    status=409)
