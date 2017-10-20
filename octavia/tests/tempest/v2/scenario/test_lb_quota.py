# Copyright 2017 Rackspace, US Inc.
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
from tempest.lib import decorators

from octavia.tests.tempest.v2.scenario import base


class TestLoadBalancerQuota(base.BaseTestCase):
    """This tests attempts to exceed a set load balancer quota.

    The following is the scenario outline:
    1. Set the load balancer quota to one.
    2. Create two load balancers, expecting the second create to fail
       with a quota exceeded code.
    """

    @utils.services('compute', 'network')
    @decorators.skip_because(bug="1656110")
    def test_load_balancer_quota(self):
        self._set_quotas(project_id=None, load_balancer=1)
        self._create_load_balancer_over_quota()
