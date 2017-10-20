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
from tempest import config


from octavia.tests.tempest.v1.scenario import base

config = config.CONF


class TestLoadBalancerTreeMinimal(base.BaseTestCase):

    @utils.services('compute', 'network')
    def test_load_balancer_tree_minimal(self):
        """This test checks basic load balancing.

        The following is the scenario outline:
        1. Create an instance.
        2. SSH to the instance and start two servers.
        3. Create a load balancer graph with two members and with ROUND_ROBIN
           algorithm.
        4. Associate the VIP with a floating ip.
        5. Send NUM requests to the floating ip and check that they are shared
           between the two servers.
        """
        self._create_server('server1')
        self._start_backend_httpd_processes('server1')
        self._create_server('server2')
        self._start_backend_httpd_processes('server2')
        self._create_load_balancer_tree(cleanup=False)
        self._check_members_balanced(['server1_0', 'server2_0'])
        self._delete_load_balancer_cascade(self.load_balancer.get('id'))
