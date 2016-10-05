#    Copyright 2016 Rackspace
#    All Rights Reserved.
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

import operator

from oslo_serialization import jsonutils as json
from oslo_utils import uuidutils

from octavia.common import constants
from octavia.tests.functional.api.v1 import base


class TestApiSort(base.BaseAPITest):
    def setUp(self):
        super(TestApiSort, self).setUp()
        self.random_name_desc = [
            ('b', 'g'), ('h', 'g'), ('b', 'a'), ('c', 'g'),
            ('g', 'c'), ('h', 'h'), ('a', 'e'), ('g', 'h'),
            ('g', 'd'), ('e', 'h'), ('h', 'e'), ('b', 'f'),
            ('b', 'h'), ('a', 'h'), ('g', 'g'), ('h', 'f'),
            ('c', 'h'), ('g', 'f'), ('f', 'f'), ('d', 'd'),
            ('g', 'b'), ('a', 'c'), ('h', 'a'), ('h', 'c'),
            ('e', 'd'), ('d', 'g'), ('c', 'b'), ('f', 'b'),
            ('c', 'c'), ('d', 'c'), ('f', 'a'), ('h', 'd'),
            ('f', 'c'), ('d', 'a'), ('d', 'e'), ('d', 'f'),
            ('g', 'e'), ('a', 'a'), ('e', 'c'), ('e', 'b'),
            ('f', 'g'), ('d', 'b'), ('e', 'a'), ('b', 'e'),
            ('f', 'h'), ('a', 'g'), ('c', 'd'), ('b', 'd'),
            ('b', 'b'), ('a', 'b'), ('f', 'd'), ('f', 'e'),
            ('c', 'a'), ('b', 'c'), ('e', 'f'), ('a', 'f'),
            ('e', 'e'), ('h', 'b'), ('d', 'h'), ('e', 'g'),
            ('c', 'e'), ('g', 'a'), ('a', 'd'), ('c', 'f')]

        self.headers = {'accept': constants.APPLICATION_JSON,
                        'content-type': constants.APPLICATION_JSON}
        self.lbs = []
        self.lb_names = ['lb_c', 'lb_a', 'lb_b', 'lb_e', 'lb_d']

    def _create_loadbalancers(self):
        for name in self.lb_names:
            lb = self.create_load_balancer(
                {'subnet_id': uuidutils.generate_uuid()}, name=name)
            self.lbs.append(lb)

    def test_lb_keysort(self):
        self._create_loadbalancers()
        params = {'sort': 'name:desc',
                  'project_id': self.project_id}
        resp = self.get(self.LBS_PATH, params=params,
                        headers=self.headers)

        lbs = json.loads(resp.body)
        act_names = [l['name'] for l in lbs]
        ref_names = sorted(self.lb_names[:], reverse=True)
        self.assertEqual(ref_names, act_names)  # Should be in order

    def test_loadbalancer_sorting_and_pagination(self):
        # Python's stable sort will allow us to simulate the full sorting
        # capabilities of the api during testing.
        exp_order = self.random_name_desc[:]
        exp_order.sort(key=operator.itemgetter(1), reverse=False)
        exp_order.sort(key=operator.itemgetter(0), reverse=True)

        for (name, desc) in self.random_name_desc:
            self.create_load_balancer(
                {'subnet_id': uuidutils.generate_uuid()},
                name=name, description=desc)

        params = {'sort': 'name:desc,description:asc',
                  'project_id': self.project_id}

        # Get all lbs
        resp = self.get(self.LBS_PATH, headers=self.headers, params=params)
        all_lbs = json.loads(resp.body)

        # Test the first 8 which is just limit=8
        params.update({'limit': '8'})
        resp = self.get(self.LBS_PATH, headers=self.headers, params=params)
        lbs = json.loads(resp.body)
        fnd_name_descs = [(lb['name'], lb['description']) for lb in lbs]
        self.assertEqual(exp_order[0:8], fnd_name_descs)

        # Test the slice at 8:24 which is marker=7 limit=16
        params.update({'marker': all_lbs[7].get('id'), 'limit': '16'})
        resp = self.get(self.LBS_PATH, headers=self.headers, params=params)
        lbs = json.loads(resp.body)
        fnd_name_descs = [(lb['name'], lb['description']) for lb in lbs]
        self.assertEqual(exp_order[8:24], fnd_name_descs)

        # Test the slice at 32:56 which is marker=31 limit=24
        params.update({'marker': all_lbs[31].get('id'), 'limit': '24'})
        resp = self.get(self.LBS_PATH, headers=self.headers, params=params)
        lbs = json.loads(resp.body)
        fnd_name_descs = [(lb['name'], lb['description']) for lb in lbs]
        self.assertEqual(exp_order[32:56], fnd_name_descs)

        # Test the last 8 entries which is slice 56:64 marker=55 limit=8
        params.update({'marker': all_lbs[55].get('id'), 'limit': '8'})
        resp = self.get(self.LBS_PATH, headers=self.headers, params=params)
        lbs = json.loads(resp.body)
        fnd_name_descs = [(lb['name'], lb['description']) for lb in lbs]
        self.assertEqual(exp_order[56:64], fnd_name_descs)

        # Test that we don't get an overflow or some other error if
        # the number of entries is less then the limit.
        # This should only return 4 entries
        params.update({'marker': all_lbs[59].get('id'), 'limit': '8'})
        resp = self.get(self.LBS_PATH, headers=self.headers, params=params)
        lbs = json.loads(resp.body)
        fnd_name_descs = [(lb['name'], lb['description']) for lb in lbs]
        self.assertEqual(exp_order[60:64], fnd_name_descs)

    def test_listeners_sorting_and_pagination(self):
        #  Create a loadbalancer and create 2 listeners on it
        lb = self.create_load_balancer(
            {'subnet_id': uuidutils.generate_uuid()}, name="single_lb")
        lb_id = lb['id']
        self.set_lb_status(lb_id)
        exp_desc_names = self.random_name_desc[30:40]
        exp_desc_names.sort(key=operator.itemgetter(0), reverse=True)
        exp_desc_names.sort(key=operator.itemgetter(1), reverse=True)

        port = 0
        # We did some heavy testing already and the set_lb_status function
        # is recursive and leads to n*(n-1) iterations during this test so
        # we only test 10 entries
        for (name, description) in self.random_name_desc[30:40]:
            port += 1
            opts = {"name": name, "description": description}
            self.create_listener(lb_id, constants.PROTOCOL_HTTP, port, **opts)
            # Set the lb to active but don't recurse the child objects as
            # that will create a n*(n-1) operation in this loop
            self.set_lb_status(lb_id)

        url = self.LISTENERS_PATH.format(lb_id=lb_id)
        params = {'sort': 'description:desc,name:desc',
                  'project_id': self.project_id}

        # Get all listeners
        resp = self.get(url, headers=self.headers, params=params)
        all_listeners = json.loads(resp.body)

        # Test the slice at 3:6
        params.update({'marker': all_listeners[2].get('id'), 'limit': '3'})
        resp = self.get(url, headers=self.headers, params=params)
        listeners = json.loads(resp.body)
        fnd_name_desc = [(l['name'], l['description']) for l in listeners]
        self.assertEqual(exp_desc_names[3:6], fnd_name_desc)

        # Test the slice at 1:8
        params.update({'marker': all_listeners[0].get('id'), 'limit': '7'})
        resp = self.get(url, headers=self.headers, params=params)
        listeners = json.loads(resp.body)
        fnd_name_desc = [(l['name'], l['description']) for l in listeners]
        self.assertEqual(exp_desc_names[1:8], fnd_name_desc)

    def test_members_sorting_and_pagination(self):
        lb = self.create_load_balancer(
            {'subnet_id': uuidutils.generate_uuid()}, name="single_lb")
        lb_id = lb['id']
        self.set_lb_status(lb_id)
        li = self.create_listener(lb_id, constants.PROTOCOL_HTTP, 80)
        li_id = li['id']
        self.set_lb_status(lb_id)
        p = self.create_pool(lb_id, li_id, constants.PROTOCOL_HTTP,
                             constants.LB_ALGORITHM_ROUND_ROBIN)
        self.set_lb_status(lb_id)
        pool_id = p['id']
        exp_ip_weights = [('127.0.0.4', 3), ('127.0.0.5', 1), ('127.0.0.2', 5),
                          ('127.0.0.1', 4), ('127.0.0.3', 2)]

        for(ip, weight) in exp_ip_weights:
            self.create_member(lb_id, pool_id, ip, 80, weight=weight)
            self.set_lb_status(lb_id)

        exp_ip_weights.sort(key=operator.itemgetter(1))
        exp_ip_weights.sort(key=operator.itemgetter(0))

        url = self.MEMBERS_PATH.format(lb_id=lb_id, pool_id=pool_id)
        params = {'sort': 'ip_address,weight:asc',
                  'project_id': self.project_id}

        # Get all members
        resp = self.get(url, headers=self.headers, params=params)
        all_members = json.loads(resp.body)

        # These tests are getting exhaustive -- just test marker=0 limit=2
        params.update({'marker': all_members[0].get('id'), 'limit': '2'})
        resp = self.get(url, headers=self.headers, params=params)
        members = json.loads(resp.body)
        fnd_ip_subs = [(m['ip_address'], m['weight']) for m in members]
        self.assertEqual(exp_ip_weights[1:3], fnd_ip_subs)

    def test_invalid_limit(self):
        params = {'project_id': self.project_id,
                  'limit': 'a'}

        self.get(self.LBS_PATH, headers=self.headers, params=params,
                 status=400)

    def test_invalid_marker(self):
        params = {'project_id': self.project_id,
                  'marker': 'not_a_valid_uuid'}

        self.get(self.LBS_PATH, headers=self.headers, params=params,
                 status=400)

    def test_invalid_sort_key(self):
        params = {'sort': 'name:desc:asc',
                  'project_id': self.project_id}

        self.get(self.LBS_PATH, headers=self.headers, params=params,
                 status=400)
