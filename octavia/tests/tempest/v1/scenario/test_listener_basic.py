# Copyright 2016 Rackspace US Inc.
#  All Rights Reserved.
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

from tempest.common import utils

from octavia.tests.tempest.v1.scenario import base


class TestListenerBasic(base.BaseTestCase):
    """This test checks basic listener functionality.

    The following is the scenario outline:
    1. Create an instance.
    2. SSH to the instance and start two web server processes.
    3. Create a load balancer, listener, pool and two members and with
       ROUND_ROBIN algorithm. Associate the VIP with a floating ip.
    4. Send NUM requests to the floating ip and check that they are shared
       between the two web server processes.
    5. Delete listener and validate the traffic is not sent to any members.
    """

    @utils.services('compute', 'network')
    def test_load_balancer_basic(self):
        self._create_server('server1')
        self._start_backend_httpd_processes('server1')
        lb_id = self._create_load_balancer()
        pool = self._create_pool(lb_id)
        listener = self._create_listener(lb_id, default_pool_id=pool['id'])
        self._create_members(lb_id, pool['id'], 'server1',
                             subnet_id=self.subnet['id'])
        self._check_members_balanced(['server1_0', 'server1_1'])
        self._cleanup_pool(pool['id'], lb_id)
        self._cleanup_listener(listener['id'], lb_id)
        self._check_load_balancing_after_deleting_resources()
