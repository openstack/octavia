# Copyright 2015 Hewlett Packard Enterprise Development Company LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

import copy

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture

from octavia.amphorae.drivers.keepalived.jinja import jinja_cfg
from octavia.common import constants
import octavia.tests.unit.base as base


class TestVRRPRestDriver(base.TestCase):

    def setUp(self):
        super(TestVRRPRestDriver, self).setUp()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group="haproxy_amphora", base_path='/tmp/test')
        conf.config(group="keepalived_vrrp", vrrp_garp_refresh_interval=5)
        conf.config(group="keepalived_vrrp", vrrp_garp_refresh_count=2)
        conf.config(group="keepalived_vrrp", vrrp_check_interval=5)
        conf.config(group="keepalived_vrrp", vrrp_fail_count=2)
        conf.config(group="keepalived_vrrp", vrrp_success_count=2)

        self.templater = jinja_cfg.KeepalivedJinjaTemplater()

        self.amphora1 = mock.MagicMock()
        self.amphora1.status = constants.AMPHORA_ALLOCATED
        self.amphora1.vrrp_ip = '10.0.0.1'
        self.amphora1.role = constants.ROLE_MASTER
        self.amphora1.vrrp_interface = 'eth1'
        self.amphora1.vrrp_id = 1
        self.amphora1.vrrp_priority = 100

        self.amphora2 = mock.MagicMock()
        self.amphora2.status = constants.AMPHORA_ALLOCATED
        self.amphora2.vrrp_ip = '10.0.0.2'
        self.amphora2.role = constants.ROLE_BACKUP
        self.amphora2.vrrp_interface = 'eth1'
        self.amphora2.vrrp_id = 1
        self.amphora2.vrrp_priority = 90

        self.lb = mock.MagicMock()
        self.lb.amphorae = [self.amphora1, self.amphora2]
        self.lb.vrrp_group.vrrp_group_name = 'TESTGROUP'
        self.lb.vrrp_group.vrrp_auth_type = constants.VRRP_AUTH_DEFAULT
        self.lb.vrrp_group.vrrp_auth_pass = 'TESTPASSWORD'
        self.lb.vip.ip_address = '10.1.0.5'
        self.lb.vrrp_group.advert_int = 10

        self.ref_conf = ("vrrp_script check_script {\n"
                         "  script /tmp/test/vrrp/check_script.sh\n"
                         "  interval 5\n"
                         "  fall 2\n"
                         "  rise 2\n"
                         "}\n"
                         "\n"
                         "vrrp_instance TESTGROUP {\n"
                         "  state MASTER\n"
                         "  interface eth1\n"
                         "  virtual_router_id 1\n"
                         "  priority 100\n"
                         "  nopreempt\n"
                         "  accept\n"
                         "  garp_master_refresh 5\n"
                         "  garp_master_refresh_repeat 2\n"
                         "  advert_int 10\n"
                         "  authentication {\n"
                         "    auth_type PASS\n"
                         "    auth_pass TESTPASSWORD\n"
                         "  }\n"
                         "\n"
                         "  unicast_src_ip 10.0.0.1\n"
                         "  unicast_peer {\n"
                         "    10.0.0.2\n"
                         "  }\n"
                         "\n"
                         "  virtual_ipaddress {\n"
                         "    10.1.0.5\n"
                         "  }\n\n"
                         "  virtual_routes {\n"
                         "    10.1.0.0/24 dev eth1 src 10.1.0.5 scope link "
                         "table 1\n"
                         "  }\n\n"
                         "  virtual_rules {\n"
                         "    from 10.1.0.5/32 table 1 priority 100\n"
                         "  }\n\n"
                         "  track_script {\n"
                         "    check_script\n"
                         "  }\n"
                         "}")

        self.amphora1v6 = copy.deepcopy(self.amphora1)
        self.amphora1v6.vrrp_ip = '2001:db8::10'
        self.amphora2v6 = copy.deepcopy(self.amphora2)
        self.amphora2v6.vrrp_ip = '2001:db8::11'
        self.lbv6 = copy.deepcopy(self.lb)
        self.lbv6.amphorae = [self.amphora1v6, self.amphora2v6]
        self.lbv6.vip.ip_address = '2001:db8::15'

        self.ref_v6_conf = ("vrrp_script check_script {\n"
                            "  script /tmp/test/vrrp/check_script.sh\n"
                            "  interval 5\n"
                            "  fall 2\n"
                            "  rise 2\n"
                            "}\n"
                            "\n"
                            "vrrp_instance TESTGROUP {\n"
                            "  state MASTER\n"
                            "  interface eth1\n"
                            "  virtual_router_id 1\n"
                            "  priority 100\n"
                            "  nopreempt\n"
                            "  accept\n"
                            "  garp_master_refresh 5\n"
                            "  garp_master_refresh_repeat 2\n"
                            "  advert_int 10\n"
                            "  authentication {\n"
                            "    auth_type PASS\n"
                            "    auth_pass TESTPASSWORD\n"
                            "  }\n"
                            "\n"
                            "  unicast_src_ip 2001:db8::10\n"
                            "  unicast_peer {\n"
                            "    2001:db8::11\n"
                            "  }\n"
                            "\n"
                            "  virtual_ipaddress {\n"
                            "    2001:db8::15\n"
                            "  }\n\n"
                            "  virtual_routes {\n"
                            "    2001:db8::/64 dev eth1 src "
                            "2001:db8::15 scope link table 1\n"
                            "  }\n\n"
                            "  virtual_rules {\n"
                            "    from 2001:db8::15/128 table 1 "
                            "priority 100\n"
                            "  }\n\n"
                            "  track_script {\n"
                            "    check_script\n"
                            "  }\n"
                            "}")

    def test_build_keepalived_config(self):
        config = self.templater.build_keepalived_config(
            self.lb, self.amphora1, '10.1.0.0/24')
        self.assertEqual(self.ref_conf, config)

    def test_build_keepalived_ipv6_config(self):
        config = self.templater.build_keepalived_config(
            self.lbv6, self.amphora1v6, '2001:db8::/64')
        self.assertEqual(self.ref_v6_conf, config)
