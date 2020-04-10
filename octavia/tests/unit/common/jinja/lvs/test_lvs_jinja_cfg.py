# Copyright 2018 OpenStack Foundation
# All Rights Reserved.
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

from octavia.common import constants
from octavia.common.jinja.lvs import jinja_cfg
from octavia.tests.unit import base
from octavia.tests.unit.common.sample_configs import sample_configs_combined

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture

BASE_PATH = '/var/lib/octavia'


class TestLvsCfg(base.TestCase):
    def setUp(self):
        super(TestLvsCfg, self).setUp()
        self.udp_jinja_cfg = jinja_cfg.LvsJinjaTemplater()
        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="haproxy_amphora", base_path=BASE_PATH)

    def test_udp_get_template(self):
        template = self.udp_jinja_cfg._get_template()
        self.assertEqual('keepalivedlvs.cfg.j2', template.name)

    def test_render_template_udp_source_ip(self):
        exp = ("# Configuration for Loadbalancer sample_loadbalancer_id_1\n"
               "# Configuration for Listener sample_listener_id_1\n\n"
               "net_namespace amphora-haproxy\n\n"
               "virtual_server 10.0.0.2 80 {\n"
               "    lb_algo rr\n"
               "    lb_kind NAT\n"
               "    protocol UDP\n"
               "    persistence_timeout 33\n"
               "    persistence_granularity 255.255.0.0\n"
               "    delay_loop 30\n"
               "    delay_before_retry 30\n"
               "    retry 3\n\n\n"
               "    # Configuration for Pool sample_pool_id_1\n"
               "    # Configuration for HealthMonitor sample_monitor_id_1\n"
               "    # Configuration for Member sample_member_id_1\n"
               "    real_server 10.0.0.99 82 {\n"
               "        weight 13\n"
               "        uthreshold 98\n"
               "        MISC_CHECK {\n"
               "            misc_path \"/var/lib/octavia/lvs/check/"
               "udp_check.sh 10.0.0.99 82\"\n"
               "            misc_timeout 31\n"
               "        }\n"
               "    }\n\n"
               "    # Configuration for Member sample_member_id_2\n"
               "    real_server 10.0.0.98 82 {\n"
               "        weight 13\n"
               "        uthreshold 98\n"
               "        MISC_CHECK {\n"
               "            misc_path \"/var/lib/octavia/lvs/check/"
               "udp_check.sh 10.0.0.98 82\"\n"
               "            misc_timeout 31\n"
               "        }\n"
               "    }\n\n"
               "}\n\n")
        rendered_obj = self.udp_jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_listener_tuple(
                proto=constants.PROTOCOL_UDP,
                persistence_type=constants.SESSION_PERSISTENCE_SOURCE_IP,
                persistence_timeout=33,
                persistence_granularity='255.255.0.0',
                monitor_proto=constants.HEALTH_MONITOR_UDP_CONNECT,
                connection_limit=98))
        self.assertEqual(exp, rendered_obj)

    def test_render_template_udp_one_packet(self):
        exp = ("# Configuration for Loadbalancer sample_loadbalancer_id_1\n"
               "# Configuration for Listener sample_listener_id_1\n\n"
               "net_namespace amphora-haproxy\n\n"
               "virtual_server 10.0.0.2 80 {\n"
               "    lb_algo rr\n"
               "    lb_kind NAT\n"
               "    protocol UDP\n"
               "    delay_loop 30\n"
               "    delay_before_retry 30\n"
               "    retry 3\n\n\n"
               "    # Configuration for Pool sample_pool_id_1\n"
               "    # Configuration for HealthMonitor sample_monitor_id_1\n"
               "    # Configuration for Member sample_member_id_1\n"
               "    real_server 10.0.0.99 82 {\n"
               "        weight 13\n"
               "        uthreshold 98\n"
               "        MISC_CHECK {\n"
               "            misc_path \"/var/lib/octavia/lvs/check/"
               "udp_check.sh 10.0.0.99 82\"\n"
               "            misc_timeout 31\n"
               "        }\n"
               "    }\n\n"
               "    # Configuration for Member sample_member_id_2\n"
               "    real_server 10.0.0.98 82 {\n"
               "        weight 13\n"
               "        uthreshold 98\n"
               "        MISC_CHECK {\n"
               "            misc_path \"/var/lib/octavia/lvs/check/"
               "udp_check.sh 10.0.0.98 82\"\n"
               "            misc_timeout 31\n"
               "        }\n"
               "    }\n\n"
               "}\n\n")

        listener = sample_configs_combined.sample_listener_tuple(
            proto=constants.PROTOCOL_UDP,
            monitor_proto=constants.HEALTH_MONITOR_UDP_CONNECT,
            connection_limit=98,
            persistence=False)
        rendered_obj = self.udp_jinja_cfg.render_loadbalancer_obj(listener)
        self.assertEqual(exp, rendered_obj)

    def test_render_template_udp_with_health_monitor(self):
        exp = ("# Configuration for Loadbalancer sample_loadbalancer_id_1\n"
               "# Configuration for Listener sample_listener_id_1\n\n"
               "net_namespace amphora-haproxy\n\n"
               "virtual_server 10.0.0.2 80 {\n"
               "    lb_algo rr\n"
               "    lb_kind NAT\n"
               "    protocol UDP\n"
               "    delay_loop 30\n"
               "    delay_before_retry 30\n"
               "    retry 3\n\n\n"
               "    # Configuration for Pool sample_pool_id_1\n"
               "    # Configuration for HealthMonitor sample_monitor_id_1\n"
               "    # Configuration for Member sample_member_id_1\n"
               "    real_server 10.0.0.99 82 {\n"
               "        weight 13\n"
               "        uthreshold 98\n"
               "        MISC_CHECK {\n"
               "            misc_path \"/var/lib/octavia/lvs/check/"
               "udp_check.sh 10.0.0.99 82\"\n"
               "            misc_timeout 31\n"
               "        }\n"
               "    }\n\n"
               "    # Configuration for Member sample_member_id_2\n"
               "    real_server 10.0.0.98 82 {\n"
               "        weight 13\n"
               "        uthreshold 98\n"
               "        MISC_CHECK {\n"
               "            misc_path \"/var/lib/octavia/lvs/check/"
               "udp_check.sh 10.0.0.98 82\"\n"
               "            misc_timeout 31\n"
               "        }\n"
               "    }\n\n"
               "}\n\n")

        rendered_obj = self.udp_jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_listener_tuple(
                proto=constants.PROTOCOL_UDP,
                monitor_proto=constants.HEALTH_MONITOR_UDP_CONNECT,
                persistence=False,
                connection_limit=98))
        self.assertEqual(exp, rendered_obj)

    def test_render_template_udp_with_health_monitor_ip_port(self):
        exp = ("# Configuration for Loadbalancer sample_loadbalancer_id_1\n"
               "# Configuration for Listener sample_listener_id_1\n\n"
               "net_namespace amphora-haproxy\n\n"
               "virtual_server 10.0.0.2 80 {\n"
               "    lb_algo rr\n"
               "    lb_kind NAT\n"
               "    protocol UDP\n"
               "    delay_loop 30\n"
               "    delay_before_retry 30\n"
               "    retry 3\n\n\n"
               "    # Configuration for Pool sample_pool_id_1\n"
               "    # Configuration for HealthMonitor sample_monitor_id_1\n"
               "    # Configuration for Member sample_member_id_1\n"
               "    real_server 10.0.0.99 82 {\n"
               "        weight 13\n"
               "        uthreshold 98\n"
               "        MISC_CHECK {\n"
               "            misc_path \"/var/lib/octavia/lvs/check/"
               "udp_check.sh 192.168.1.1 9000\"\n"
               "            misc_timeout 31\n"
               "        }\n"
               "    }\n\n"
               "    # Configuration for Member sample_member_id_2\n"
               "    real_server 10.0.0.98 82 {\n"
               "        weight 13\n"
               "        uthreshold 98\n"
               "        MISC_CHECK {\n"
               "            misc_path \"/var/lib/octavia/lvs/check/"
               "udp_check.sh 192.168.1.1 9000\"\n"
               "            misc_timeout 31\n"
               "        }\n"
               "    }\n\n"
               "}\n\n")

        rendered_obj = self.udp_jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_listener_tuple(
                proto=constants.PROTOCOL_UDP,
                monitor_ip_port=True,
                monitor_proto=constants.HEALTH_MONITOR_UDP_CONNECT,
                persistence=False,
                connection_limit=98))
        self.assertEqual(exp, rendered_obj)

    def test_render_template_udp_no_other_resources(self):
        exp = ("# Configuration for Loadbalancer sample_loadbalancer_id_1\n"
               "# Configuration for Listener sample_listener_id_1\n\n"
               "net_namespace amphora-haproxy\n\n\n")

        rendered_obj = self.udp_jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_listener_tuple(
                proto=constants.PROTOCOL_UDP, monitor=False,
                persistence=False, alloc_default_pool=False))
        self.assertEqual(exp, rendered_obj)

    def test_udp_transform_session_persistence(self):
        persistence_src_ip = (
            sample_configs_combined.sample_session_persistence_tuple(
                persistence_type=constants.SESSION_PERSISTENCE_SOURCE_IP,
                persistence_cookie=None,
                persistence_timeout=33,
                persistence_granularity='255.0.0.0'
            ))
        exp = sample_configs_combined.UDP_SOURCE_IP_BODY
        ret = self.udp_jinja_cfg._transform_session_persistence(
            persistence_src_ip)
        self.assertEqual(exp, ret)

    def test_udp_transform_health_monitor(self):
        in_hm = sample_configs_combined.sample_health_monitor_tuple(
            proto=constants.HEALTH_MONITOR_UDP_CONNECT
        )
        ret = self.udp_jinja_cfg._transform_health_monitor(in_hm)
        self.assertEqual(sample_configs_combined.RET_UDP_HEALTH_MONITOR, ret)

    def test_udp_transform_member(self):
        in_member = sample_configs_combined.sample_member_tuple(
            'member_id_1', '192.0.2.10')
        ret = self.udp_jinja_cfg._transform_member(in_member)
        self.assertEqual(sample_configs_combined.RET_UDP_MEMBER, ret)

        in_member = sample_configs_combined.sample_member_tuple(
            'member_id_1',
            '192.0.2.10',
            monitor_ip_port=True)
        ret = self.udp_jinja_cfg._transform_member(in_member)
        self.assertEqual(
            sample_configs_combined.RET_UDP_MEMBER_MONITOR_IP_PORT, ret)

    def test_udp_transform_pool(self):
        in_pool = sample_configs_combined.sample_pool_tuple(
            proto=constants.PROTOCOL_UDP,
            persistence_type=constants.SESSION_PERSISTENCE_SOURCE_IP,
            persistence_timeout=33, persistence_granularity='255.0.0.0',
        )
        ret = self.udp_jinja_cfg._transform_pool(in_pool)
        self.assertEqual(sample_configs_combined.RET_UDP_POOL, ret)

        in_pool = sample_configs_combined.sample_pool_tuple(
            proto=constants.PROTOCOL_UDP,
            persistence_type=constants.SESSION_PERSISTENCE_SOURCE_IP,
            persistence_timeout=33, persistence_granularity='255.0.0.0',
            monitor=False)
        sample_configs_combined.RET_UDP_POOL['health_monitor'] = ''
        ret = self.udp_jinja_cfg._transform_pool(in_pool)
        self.assertEqual(sample_configs_combined.RET_UDP_POOL, ret)

    def test_udp_transform_listener(self):
        in_listener = sample_configs_combined.sample_listener_tuple(
            proto=constants.PROTOCOL_UDP,
            persistence_type=constants.SESSION_PERSISTENCE_SOURCE_IP,
            persistence_timeout=33,
            persistence_granularity='255.0.0.0',
            monitor_proto=constants.HEALTH_MONITOR_UDP_CONNECT,
            connection_limit=98
        )
        ret = self.udp_jinja_cfg._transform_listener(in_listener)
        self.assertEqual(sample_configs_combined.RET_UDP_LISTENER, ret)

        in_listener = sample_configs_combined.sample_listener_tuple(
            proto=constants.PROTOCOL_UDP,
            persistence_type=constants.SESSION_PERSISTENCE_SOURCE_IP,
            persistence_timeout=33,
            persistence_granularity='255.0.0.0',
            monitor_proto=constants.HEALTH_MONITOR_UDP_CONNECT,
            connection_limit=-1)

        ret = self.udp_jinja_cfg._transform_listener(in_listener)
        sample_configs_combined.RET_UDP_LISTENER.pop('connection_limit')
        self.assertEqual(sample_configs_combined.RET_UDP_LISTENER, ret)
