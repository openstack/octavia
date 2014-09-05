# Copyright 2014,  Doug Wiegley,  A10 Networks.
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

import octavia.tests.unit.base as base
import octavia.openstack.common.cache
import octavia.openstack.common.context
import octavia.openstack.common.excutils
import octavia.openstack.common.fixture
import octavia.openstack.common.gettextutils
import octavia.openstack.common.importutils
import octavia.openstack.common.jsonutils
import octavia.openstack.common.local
import octavia.openstack.common.lockutils
import octavia.openstack.common.log
import octavia.openstack.common.loopingcall
import octavia.openstack.common.middleware
import octavia.openstack.common.network_utils
import octavia.openstack.common.periodic_task
import octavia.openstack.common.policy
import octavia.openstack.common.processutils
import octavia.openstack.common.service
import octavia.openstack.common.sslutils
import octavia.openstack.common.strutils
import octavia.openstack.common.systemd
import octavia.openstack.common.threadgroup
import octavia.openstack.common.timeutils
import octavia.openstack.common.uuidutils
import octavia.openstack.common.versionutils


class TestCommon(base.TestCase):
    def test_openstack_common(self):
        # The test is the imports
        pass
