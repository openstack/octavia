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


class TestLoadBalancer(base.BaseAPITest):

    def test_empty_list(self):
        response = self.get(self.LBS_PATH)
        api_list = response.json
        self.assertEqual([], api_list)

    def test_create(self, **optionals):
        lb_json = {'name': 'test1', 'vip': {}}
        lb_json.update(optionals)
        response = self.post(self.LBS_PATH, lb_json)
        api_lb = response.json
        self.assertTrue(uuidutils.is_uuid_like(api_lb.get('id')))
        self.assertEqual(lb_json.get('name'), api_lb.get('name'))
        self.assertEqual(constants.PENDING_CREATE,
                         api_lb.get('provisioning_status'))
        self.assertEqual(constants.OFFLINE,
                         api_lb.get('operating_status'))
        self.assertTrue(api_lb.get('enabled'))
        for key, value in optionals.items():
            self.assertEqual(value, lb_json.get(key))
        self.assert_final_lb_statuses(api_lb.get('id'))

    def test_create_with_id(self):
        self.test_create(id=uuidutils.generate_uuid())

    def test_create_with_duplicate_id(self):
        lb = self.create_load_balancer({})
        self.post(self.LBS_PATH, {'id': lb.get('id'), 'vip': {}},
                  status=409, expect_errors=True)

    def test_create_without_vip(self):
        lb_json = {'name': 'test1'}
        self.post(self.LB_PATH, lb_json, status=400)

    def test_get_all(self):
        lb1 = self.create_load_balancer({}, name='lb1')
        lb2 = self.create_load_balancer({}, name='lb2')
        lb3 = self.create_load_balancer({}, name='lb3')
        response = self.get(self.LBS_PATH)
        lbs = response.json
        lb_id_names = [(lb.get('id'), lb.get('name')) for lb in lbs]
        self.assertEqual(3, len(lbs))
        self.assertIn((lb1.get('id'), lb1.get('name')), lb_id_names)
        self.assertIn((lb2.get('id'), lb2.get('name')), lb_id_names)
        self.assertIn((lb3.get('id'), lb3.get('name')), lb_id_names)

    def test_get(self):
        vip = {'ip_address': '10.0.0.1',
               'port_id': uuidutils.generate_uuid(),
               'subnet_id': uuidutils.generate_uuid()}
        lb = self.create_load_balancer(vip, name='lb1',
                                       description='test1_desc',
                                       enabled=False)
        response = self.get(self.LB_PATH.format(lb_id=lb.get('id')))
        self.assertEqual('lb1', response.json.get('name'))
        self.assertEqual('test1_desc', response.json.get('description'))
        self.assertFalse(response.json.get('enabled'))
        self.assertEqual(vip, response.json.get('vip'))

    def test_get_bad_lb_id(self):
        path = self.LB_PATH.format(lb_id='SEAN-CONNERY')
        self.get(path, status=404)

    def test_create_with_vip(self):
        vip = {'ip_address': '10.0.0.1',
               'subnet_id': uuidutils.generate_uuid(),
               'port_id': uuidutils.generate_uuid()}
        lb_json = {'name': 'test1', 'description': 'test1_desc',
                   'vip': vip, 'enabled': False}
        response = self.post(self.LBS_PATH, lb_json)
        api_lb = response.json
        self.assertTrue(uuidutils.is_uuid_like(api_lb.get('id')))
        self.assertEqual(lb_json.get('name'), api_lb.get('name'))
        self.assertEqual(lb_json.get('description'), api_lb.get('description'))
        self.assertEqual(constants.PENDING_CREATE,
                         api_lb['provisioning_status'])
        self.assertEqual(constants.OFFLINE,
                         api_lb['operating_status'])
        self.assertEqual(vip, api_lb.get('vip'))
        self.assertEqual(lb_json.get('enabled'), api_lb.get('enabled'))
        self.assert_final_lb_statuses(api_lb.get('id'))

    def test_create_with_long_name(self):
        lb_json = {'name': 'n' * 256, 'vip': {}}
        self.post(self.LBS_PATH, lb_json, status=400)

    def test_create_with_long_description(self):
        lb_json = {'description': 'n' * 256, 'vip': {}}
        self.post(self.LBS_PATH, lb_json, status=400)

    def test_create_with_nonuuid_vip_attributes(self):
        lb_json = {'vip': {'subnet_id': 'HI'}}
        self.post(self.LBS_PATH, lb_json, status=400)

    def test_update(self):
        lb = self.create_load_balancer({}, name='lb1', description='desc1',
                                       enabled=False)
        lb_json = {'name': 'lb2'}
        lb = self.set_lb_status(lb.get('id'))
        response = self.put(self.LB_PATH.format(lb_id=lb.get('id')), lb_json)
        api_lb = response.json
        r_vip = api_lb.get('vip')
        self.assertIsNone(r_vip.get('network_id'))
        self.assertEqual('lb1', api_lb.get('name'))
        self.assertEqual('desc1', api_lb.get('description'))
        self.assertFalse(api_lb.get('enabled'))
        self.assertEqual(constants.PENDING_UPDATE,
                         api_lb.get('provisioning_status'))
        self.assertEqual(lb.get('operational_status'),
                         api_lb.get('operational_status'))
        self.assert_final_lb_statuses(api_lb.get('id'))

    def test_update_with_vip(self):
        lb = self.create_load_balancer({}, name='lb1', description='desc1',
                                       enabled=False)
        lb_json = {'vip': {'subnet_id': '1234'}}
        lb = self.set_lb_status(lb.get('id'))
        self.put(self.LB_PATH.format(lb_id=lb.get('id')), lb_json, status=400)

    def test_update_bad_lb_id(self):
        path = self.LB_PATH.format(lb_id='SEAN-CONNERY')
        self.put(path, body={}, status=404)

    def test_update_pending_create(self):
        lb = self.create_load_balancer({}, name='lb1', description='desc1',
                                       enabled=False)
        lb_json = {'name': 'Roberto'}
        self.put(self.LB_PATH.format(lb_id=lb.get('id')), lb_json, status=409)

    def test_delete_pending_create(self):
        lb = self.create_load_balancer({}, name='lb1', description='desc1',
                                       enabled=False)
        self.delete(self.LB_PATH.format(lb_id=lb.get('id')), status=409)

    def test_update_pending_update(self):
        lb = self.create_load_balancer({}, name='lb1', description='desc1',
                                       enabled=False)
        lb_json = {'name': 'Bob'}
        lb = self.set_lb_status(lb.get('id'))
        self.put(self.LB_PATH.format(lb_id=lb.get('id')), lb_json)
        self.put(self.LB_PATH.format(lb_id=lb.get('id')), lb_json, status=409)

    def test_delete_pending_update(self):
        lb = self.create_load_balancer({}, name='lb1', description='desc1',
                                       enabled=False)
        lb_json = {'name': 'Steve'}
        lb = self.set_lb_status(lb.get('id'))
        self.put(self.LB_PATH.format(lb_id=lb.get('id')), lb_json)
        self.delete(self.LB_PATH.format(lb_id=lb.get('id')), status=409)

    def test_update_pending_delete(self):
        lb = self.create_load_balancer({}, name='lb1', description='desc1',
                                       enabled=False)
        lb = self.set_lb_status(lb.get('id'))
        self.delete(self.LB_PATH.format(lb_id=lb.get('id')))
        lb_json = {'name': 'John'}
        self.put(self.LB_PATH.format(lb_id=lb.get('id')), lb_json, status=409)

    def test_delete_pending_delete(self):
        lb = self.create_load_balancer({}, name='lb1', description='desc1',
                                       enabled=False)
        lb = self.set_lb_status(lb.get('id'))
        self.delete(self.LB_PATH.format(lb_id=lb.get('id')))
        self.delete(self.LB_PATH.format(lb_id=lb.get('id')), status=409)

    def test_delete(self):
        lb = self.create_load_balancer({}, name='lb1', description='desc1',
                                       enabled=False)
        lb = self.set_lb_status(lb.get('id'))
        self.delete(self.LB_PATH.format(lb_id=lb.get('id')))
        response = self.get(self.LB_PATH.format(lb_id=lb.get('id')))
        api_lb = response.json
        self.assertEqual('lb1', api_lb.get('name'))
        self.assertEqual('desc1', api_lb.get('description'))
        self.assertFalse(api_lb.get('enabled'))
        self.assertEqual(constants.PENDING_DELETE,
                         api_lb.get('provisioning_status'))
        self.assertEqual(lb.get('operational_status'),
                         api_lb.get('operational_status'))
        self.assert_final_lb_statuses(api_lb.get('id'), delete=True)

    def test_delete_bad_lb_id(self):
        path = self.LB_PATH.format(lb_id='bad_uuid')
        self.delete(path, status=404)
