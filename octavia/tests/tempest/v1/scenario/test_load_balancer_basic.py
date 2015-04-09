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

from tempest import test

from octavia.tests.tempest.v1.scenario import base


class TestLoadBalancerBasic(base.BaseTestCase):

    @test.services('compute', 'network')
    def test_load_balancer_basic(self):
        """This test checks basic load balancing.

        The following is the scenario outline:
        1. Create an instance.
        2. SSH to the instance and start two servers.
        3. Create a load balancer with two members and with ROUND_ROBIN
           algorithm.
        4. Associate the VIP with a floating ip.
        5. Send NUM requests to the floating ip and check that they are shared
           between the two servers.
        """
        self._create_server('server1')
        self._start_servers()
        self._create_load_balancer()
        self._check_load_balancing()
