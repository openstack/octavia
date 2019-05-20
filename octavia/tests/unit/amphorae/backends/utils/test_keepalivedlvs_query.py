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

import mock
from oslo_utils import uuidutils

from octavia.amphorae.backends.agent.api_server import util
from octavia.amphorae.backends.utils import keepalivedlvs_query as lvs_query
from octavia.common import constants
from octavia.tests.common import utils as test_utils
from octavia.tests.unit import base

# Kernal_file_sample which is in /proc/net/ip_vs
# The realservers and the listened ports are
# 10.0.0.25:2222, 10.0.0.35:3333.
# Realserver 10.0.0.45:4444 is not listed because healthcheck failed.
# The virtual server and the listened port is
# 10.0.0.37:7777.
KERNAL_FILE_SAMPLE_V4 = (
    "IP Virtual Server version 1.2.1 (size=4096)\n"
    "Prot LocalAddress:Port Scheduler Flags\n"
    "  -> RemoteAddress:Port Forward Weight ActiveConn InActConn\n"
    "UDP  0A000025:1E61 rr\n"
    "  -> 0A000023:0D05      Masq    2      0          0\n"
    "  -> 0A000019:08AE      Masq    3      0          0")
# Kernal_file_sample which is in /proc/net/ip_vs
# The realservers and the listened ports are
# [fd79:35e2:9963:0:f816:3eff:feca:b7bf]:2222,
# [fd79:35e2:9963:0:f816:3eff:fe9d:94df]:3333.
# Readlserver [fd79:35e2:9963:0:f816:3eff:fe9d:8f3f]:4444 is not listed
# because healthcheck failed.
# The virtual server and the listened port is
# [fd79:35e2:9963:0:f816:3eff:fe6d:7a2a]:7777.
KERNAL_FILE_SAMPLE_V6 = (
    "IP Virtual Server version 1.2.1 (size=4096)\n"
    "Prot LocalAddress:Port Scheduler Flags\n"
    "  -> RemoteAddress:Port Forward Weight ActiveConn InActConn\n"
    "UDP  [fd79:35e2:9963:0000:f816:3eff:fe6d:7a2a]:1E61 rr\n"
    "  -> [fd79:35e2:9963:0000:f816:3eff:feca:b7bf]:08AE      "
    "Masq    3      0          0\n"
    "  -> [fd79:35e2:9963:0000:f816:3eff:fe9d:94df]:0D05      "
    "Masq    2      0          0")

CFG_FILE_TEMPLATE_v4 = (
    "# Configuration for Listener %(listener_id)s\n\n"
    "net_namespace %(ns_name)s\n\n"
    "virtual_server 10.0.0.37 7777 {\n"
    "    lb_algo rr\n"
    "    lb_kind NAT\n"
    "    protocol udp\n\n\n"
    "    # Configuration for Pool %(pool_id)s\n"
    "    # Configuration for Member %(member_id1)s\n"
    "    real_server 10.0.0.25 2222 {\n"
    "        weight 3\n"
    "        persistence_timeout 5\n"
    "        persistence_granularity 255.0.0.0\n\n"
    "        MISC_CHECK {\n\n"
    "            misc_path \"/usr/bin/check_script.sh\"\n\n"
    "            misc_timeout 5\n\n"
    "        }\n\n"
    "    }\n\n"
    "    # Configuration for Member %(member_id2)s\n"
    "    real_server 10.0.0.35 3333 {\n"
    "        weight 2\n"
    "        persistence_timeout 5\n"
    "        persistence_granularity 255.0.0.0\n\n"
    "        MISC_CHECK {\n\n"
    "            misc_path \"/usr/bin/check_script.sh\"\n\n"
    "            misc_timeout 5\n\n"
    "        }\n\n"
    "    }\n\n"
    "    # Configuration for Member %(member_id3)s\n"
    "    real_server 10.0.0.45 4444 {\n"
    "        weight 2\n"
    "        persistence_timeout 5\n"
    "        persistence_granularity 255.0.0.0\n\n"
    "        MISC_CHECK {\n\n"
    "            misc_path \"/usr/bin/check_script.sh\"\n\n"
    "            misc_timeout 5\n\n"
    "        }\n\n"
    "    }\n\n"
    "    # Member %(member_id4)s is disabled\n\n"
    "}")

CFG_FILE_TEMPLATE_v6 = (
    "# Configuration for Listener %(listener_id)s\n\n"
    "net_namespace %(ns_name)s\n\n"
    "virtual_server fd79:35e2:9963:0:f816:3eff:fe6d:7a2a 7777 {\n"
    "    lb_algo rr\n"
    "    lb_kind NAT\n"
    "    protocol udp\n\n\n"
    "    # Configuration for Pool %(pool_id)s\n"
    "    # Configuration for Member %(member_id1)s\n"
    "    real_server fd79:35e2:9963:0:f816:3eff:feca:b7bf 2222 {\n"
    "        weight 3\n"
    "        MISC_CHECK {\n\n"
    "            misc_path \"/usr/bin/check_script.sh\"\n\n"
    "            misc_timeout 5\n\n"
    "        }\n\n"
    "    }\n\n"
    "    # Configuration for Member %(member_id2)s\n"
    "    real_server fd79:35e2:9963:0:f816:3eff:fe9d:94df 3333 {\n"
    "        weight 2\n"
    "        MISC_CHECK {\n\n"
    "            misc_path \"/usr/bin/check_script.sh\"\n\n"
    "            misc_timeout 5\n\n"
    "        }\n\n"
    "    }\n\n"
    "    # Configuration for Member %(member_id3)s\n"
    "    real_server fd79:35e2:9963:0:f816:3eff:fe9d:8f3f 4444 {\n"
    "        weight 2\n"
    "        MISC_CHECK {\n\n"
    "            misc_path \"/usr/bin/check_script.sh\"\n\n"
    "            misc_timeout 5\n\n"
    "        }\n\n"
    "    }\n\n"
    "    # Member %(member_id4)s is disabled\n\n"
    "}")

IPVSADM_OUTPUT_TEMPLATE = (
    "IP Virtual Server version 1.2.1 (size=4096)\n"
    "Prot LocalAddress:Port Scheduler Flags\n"
    "  -> RemoteAddress:Port           Forward Weight ActiveConn InActConn\n"
    "UDP  %(listener_ipport)s rr\n"
    "  -> %(member1_ipport)s               Masq    3      0          0\n"
    "  -> %(member2_ipport)s               Masq    2      0          0")

IPVSADM_STATS_OUTPUT_TEMPLATE = (
    "IP Virtual Server version 1.2.1 (size=4096)\n"
    "Prot LocalAddress:Port               Conns   InPkts  OutPkts  "
    "InBytes OutBytes\n"
    "  -> RemoteAddress:Port\n"
    "UDP  %(listener_ipport)s                      5     4264        5"
    "  6387472     7490\n"
    "  -> %(member1_ipport)s                      2     1706        2"
    "  2555588     2996\n"
    "  -> %(member2_ipport)s                      3     2558        3"
    "  3831884     4494")


class LvsQueryTestCase(base.TestCase):
    def setUp(self):
        super(LvsQueryTestCase, self).setUp()
        self.listener_id_v4 = uuidutils.generate_uuid()
        self.pool_id_v4 = uuidutils.generate_uuid()
        self.member_id1_v4 = uuidutils.generate_uuid()
        self.member_id2_v4 = uuidutils.generate_uuid()
        self.member_id3_v4 = uuidutils.generate_uuid()
        self.member_id4_v4 = uuidutils.generate_uuid()
        self.listener_id_v6 = uuidutils.generate_uuid()
        self.pool_id_v6 = uuidutils.generate_uuid()
        self.member_id1_v6 = uuidutils.generate_uuid()
        self.member_id2_v6 = uuidutils.generate_uuid()
        self.member_id3_v6 = uuidutils.generate_uuid()
        self.member_id4_v6 = uuidutils.generate_uuid()
        cfg_content_v4 = CFG_FILE_TEMPLATE_v4 % {
            'listener_id': self.listener_id_v4,
            'ns_name': constants.AMPHORA_NAMESPACE,
            'pool_id': self.pool_id_v4,
            'member_id1': self.member_id1_v4,
            'member_id2': self.member_id2_v4,
            'member_id3': self.member_id3_v4,
            'member_id4': self.member_id4_v4,
        }
        cfg_content_v6 = CFG_FILE_TEMPLATE_v6 % {
            'listener_id': self.listener_id_v6,
            'ns_name': constants.AMPHORA_NAMESPACE,
            'pool_id': self.pool_id_v6,
            'member_id1': self.member_id1_v6,
            'member_id2': self.member_id2_v6,
            'member_id3': self.member_id3_v6,
            'member_id4': self.member_id4_v6
        }
        self.useFixture(test_utils.OpenFixture(
            util.keepalived_lvs_cfg_path(self.listener_id_v4), cfg_content_v4))
        self.useFixture(test_utils.OpenFixture(
            util.keepalived_lvs_cfg_path(self.listener_id_v6), cfg_content_v6))

    @mock.patch('subprocess.check_output')
    def test_get_listener_realserver_mapping(self, mock_check_output):
        # Ipv4 resolver
        input_listener_ip_port = '10.0.0.37:7777'
        target_ns = constants.AMPHORA_NAMESPACE
        mock_check_output.return_value = KERNAL_FILE_SAMPLE_V4
        result = lvs_query.get_listener_realserver_mapping(
            target_ns, input_listener_ip_port,
            health_monitor_enabled=True)
        expected = {'10.0.0.25:2222': {'status': 'UP',
                                       'Forward': 'Masq',
                                       'Weight': '3',
                                       'ActiveConn': '0',
                                       'InActConn': '0'},
                    '10.0.0.35:3333': {'status': 'UP',
                                       'Forward': 'Masq',
                                       'Weight': '2',
                                       'ActiveConn': '0',
                                       'InActConn': '0'}}
        self.assertEqual((True, expected), result)

        # Ipv6 resolver
        input_listener_ip_port = '[fd79:35e2:9963:0:f816:3eff:fe6d:7a2a]:7777'
        mock_check_output.return_value = KERNAL_FILE_SAMPLE_V6
        result = lvs_query.get_listener_realserver_mapping(
            target_ns, input_listener_ip_port,
            health_monitor_enabled=True)
        expected = {'[fd79:35e2:9963:0:f816:3eff:feca:b7bf]:2222':
                    {'status': constants.UP,
                     'Forward': 'Masq',
                     'Weight': '3',
                     'ActiveConn': '0',
                     'InActConn': '0'},
                    '[fd79:35e2:9963:0:f816:3eff:fe9d:94df]:3333':
                        {'status': constants.UP,
                         'Forward': 'Masq',
                         'Weight': '2',
                         'ActiveConn': '0',
                         'InActConn': '0'}}
        self.assertEqual((True, expected), result)

        # negetive cases
        mock_check_output.return_value = KERNAL_FILE_SAMPLE_V4
        for listener_ip_port in ['10.0.0.37:7776', '10.0.0.31:7777']:
            result = lvs_query.get_listener_realserver_mapping(
                target_ns, listener_ip_port,
                health_monitor_enabled=True)
            self.assertEqual((False, {}), result)

        mock_check_output.return_value = KERNAL_FILE_SAMPLE_V6
        for listener_ip_port in [
            '[fd79:35e2:9963:0:f816:3eff:fe6d:7a2a]:7776',
                '[fd79:35e2:9973:0:f816:3eff:fe6d:7a2a]:7777']:
            result = lvs_query.get_listener_realserver_mapping(
                target_ns, listener_ip_port,
                health_monitor_enabled=True)
            self.assertEqual((False, {}), result)

    def test_get_udp_listener_resource_ipports_nsname(self):
        # ipv4
        res = lvs_query.get_udp_listener_resource_ipports_nsname(
            self.listener_id_v4)
        expected = {'Listener': {'id': self.listener_id_v4,
                                 'ipport': '10.0.0.37:7777'},
                    'Pool': {'id': self.pool_id_v4},
                    'Members': [{'id': self.member_id1_v4,
                                 'ipport': '10.0.0.25:2222'},
                                {'id': self.member_id2_v4,
                                 'ipport': '10.0.0.35:3333'},
                                {'id': self.member_id3_v4,
                                 'ipport': '10.0.0.45:4444'},
                                {'id': self.member_id4_v4,
                                 'ipport': None}]}
        self.assertEqual((expected, constants.AMPHORA_NAMESPACE), res)

        # ipv6
        res = lvs_query.get_udp_listener_resource_ipports_nsname(
            self.listener_id_v6)
        expected = {'Listener': {
            'id': self.listener_id_v6,
            'ipport': '[fd79:35e2:9963:0:f816:3eff:fe6d:7a2a]:7777'},
            'Pool': {'id': self.pool_id_v6},
            'Members': [
                {'id': self.member_id1_v6,
                 'ipport': '[fd79:35e2:9963:0:f816:3eff:feca:b7bf]:2222'},
                {'id': self.member_id2_v6,
                 'ipport': '[fd79:35e2:9963:0:f816:3eff:fe9d:94df]:3333'},
                {'id': self.member_id3_v6,
                 'ipport': '[fd79:35e2:9963:0:f816:3eff:fe9d:8f3f]:4444'},
                {'id': self.member_id4_v6,
                 'ipport': None}]}
        self.assertEqual((expected, constants.AMPHORA_NAMESPACE), res)

    @mock.patch('subprocess.check_output')
    def test_get_udp_listener_pool_status(self, mock_check_output):
        # test with ipv4 and ipv6
        mock_check_output.return_value = KERNAL_FILE_SAMPLE_V4
        res = lvs_query.get_udp_listener_pool_status(self.listener_id_v4)
        expected = {
            'lvs':
            {'uuid': self.pool_id_v4,
             'status': constants.UP,
             'members': {self.member_id1_v4: constants.UP,
                         self.member_id2_v4: constants.UP,
                         self.member_id3_v4: constants.DOWN,
                         self.member_id4_v4: constants.MAINT}}}
        self.assertEqual(expected, res)

        mock_check_output.return_value = KERNAL_FILE_SAMPLE_V6
        res = lvs_query.get_udp_listener_pool_status(self.listener_id_v6)
        expected = {
            'lvs':
            {'uuid': self.pool_id_v6,
             'status': constants.UP,
             'members': {self.member_id1_v6: constants.UP,
                         self.member_id2_v6: constants.UP,
                         self.member_id3_v6: constants.DOWN,
                         self.member_id4_v6: constants.MAINT}}}
        self.assertEqual(expected, res)

    @mock.patch('octavia.amphorae.backends.utils.keepalivedlvs_query.'
                'get_udp_listener_resource_ipports_nsname')
    def test_get_udp_listener_pool_status_when_no_pool(
            self, mock_get_resource_ipports):
        # Just test with ipv4, ipv6 tests is same.
        # the returned resource_ipport_mapping doesn't contains the 'Pool'
        # resource, that means the listener doesn't have a pool resource, it
        # isn't usable at this moment, then the pool status will
        # return nothing.
        mock_get_resource_ipports.return_value = (
            {
                'Listener': {
                    'id': self.listener_id_v4,
                    'ipport': '10.0.0.37:7777'}},
            constants.AMPHORA_NAMESPACE)
        res = lvs_query.get_udp_listener_pool_status(self.listener_id_v4)
        self.assertEqual({}, res)

    @mock.patch('octavia.amphorae.backends.utils.keepalivedlvs_query.'
                'get_udp_listener_resource_ipports_nsname')
    def test_get_udp_listener_pool_status_when_no_members(
            self, mock_get_resource_ipports):
        # Just test with ipv4, ipv6 tests is same.
        # the returned resource_ipport_mapping doesn't contains the 'Members'
        # resources, that means the pool of listener doesn't have a enabled
        # pool resource, so the pool is not usable, then the pool status will
        # return DOWN.
        mock_get_resource_ipports.return_value = (
            {
                'Listener': {'id': self.listener_id_v4,
                             'ipport': '10.0.0.37:7777'},
                'Pool': {'id': self.pool_id_v4}},
            constants.AMPHORA_NAMESPACE)
        res = lvs_query.get_udp_listener_pool_status(self.listener_id_v4)
        expected = {'lvs': {
            'uuid': self.pool_id_v4,
            'status': constants.DOWN,
            'members': {}
        }}
        self.assertEqual(expected, res)

    @mock.patch('octavia.amphorae.backends.utils.keepalivedlvs_query.'
                'get_listener_realserver_mapping')
    def test_get_udp_listener_pool_status_when_not_get_realserver_result(
            self, mock_get_mapping):
        # This will hit if the kernel lvs file (/proc/net/ip_vs)
        # lose its content. So at this moment, eventhough we configure the
        # pool and member into udp keepalived config file, we have to set
        # ths status of pool and its members to DOWN.
        mock_get_mapping.return_value = (False, {})
        res = lvs_query.get_udp_listener_pool_status(self.listener_id_v4)
        expected = {
            'lvs':
            {'uuid': self.pool_id_v4,
             'status': constants.DOWN,
             'members': {self.member_id1_v4: constants.DOWN,
                         self.member_id2_v4: constants.DOWN,
                         self.member_id3_v4: constants.DOWN,
                         self.member_id4_v4: constants.MAINT}}}
        self.assertEqual(expected, res)

    @mock.patch('subprocess.check_output')
    def test_get_ipvsadm_info(self, mock_check_output):
        for ip_list in [["10.0.0.37:7777", "10.0.0.25:2222", "10.0.0.35:3333"],
                        ["[fd79:35e2:9963:0:f816:3eff:fe6d:7a2a]:7777",
                         "[fd79:35e2:9963:0:f816:3eff:feca:b7bf]:2222",
                         "[fd79:35e2:9963:0:f816:3eff:fe9d:94df]:3333"]]:
            mock_check_output.return_value = IPVSADM_OUTPUT_TEMPLATE % {
                "listener_ipport": ip_list[0],
                "member1_ipport": ip_list[1],
                "member2_ipport": ip_list[2]}
            res = lvs_query.get_ipvsadm_info(constants.AMPHORA_NAMESPACE)
            # This expected result can reference on IPVSADM_OUTPUT_TEMPLATE,
            # that means the function can get every element of the virtual
            # server and the real servers.
            expected = {
                ip_list[0]: {
                    'Listener': [('Prot', 'UDP'),
                                 ('LocalAddress:Port', ip_list[0]),
                                 ('Scheduler', 'rr')],
                    'Members': [[('RemoteAddress:Port', ip_list[1]),
                                 ('Forward', 'Masq'), ('Weight', '3'),
                                 ('ActiveConn', '0'), ('InActConn', '0')],
                                [('RemoteAddress:Port', ip_list[2]),
                                 ('Forward', 'Masq'), ('Weight', '2'),
                                 ('ActiveConn', '0'), ('InActConn', '0')]]}}
            self.assertEqual(expected, res)

            # ipvsadm stats
            mock_check_output.return_value = IPVSADM_STATS_OUTPUT_TEMPLATE % {
                "listener_ipport": ip_list[0],
                "member1_ipport": ip_list[1],
                "member2_ipport": ip_list[2]}
            res = lvs_query.get_ipvsadm_info(constants.AMPHORA_NAMESPACE,
                                             is_stats_cmd=True)
            expected = {
                ip_list[0]:
                    {'Listener': [('Prot', 'UDP'),
                                  ('LocalAddress:Port', ip_list[0]),
                                  ('Conns', '5'),
                                  ('InPkts', '4264'),
                                  ('OutPkts', '5'),
                                  ('InBytes', '6387472'),
                                  ('OutBytes', '7490')],
                     'Members': [[('RemoteAddress:Port', ip_list[1]),
                                  ('Conns', '2'),
                                  ('InPkts', '1706'),
                                  ('OutPkts', '2'),
                                  ('InBytes', '2555588'),
                                  ('OutBytes', '2996')],
                                 [('RemoteAddress:Port', ip_list[2]),
                                  ('Conns', '3'),
                                  ('InPkts', '2558'),
                                  ('OutPkts', '3'),
                                  ('InBytes', '3831884'),
                                  ('OutBytes', '4494')]]}}
            self.assertEqual(expected, res)

    @mock.patch('subprocess.check_output')
    @mock.patch("octavia.amphorae.backends.agent.api_server.util."
                "is_udp_listener_running", return_value=True)
    @mock.patch("octavia.amphorae.backends.agent.api_server.util."
                "get_udp_listeners")
    def test_get_udp_listeners_stats(
            self, mock_get_listener, mock_is_running, mock_check_output):
        # The ipv6 test is same with ipv4, so just test ipv4 here
        mock_get_listener.return_value = [self.listener_id_v4]
        output_list = list()
        output_list.append(IPVSADM_OUTPUT_TEMPLATE % {
            "listener_ipport": "10.0.0.37:7777",
            "member1_ipport": "10.0.0.25:2222",
            "member2_ipport": "10.0.0.35:3333"})
        output_list.append(IPVSADM_STATS_OUTPUT_TEMPLATE % {
            "listener_ipport": "10.0.0.37:7777",
            "member1_ipport": "10.0.0.25:2222",
            "member2_ipport": "10.0.0.35:3333"})
        mock_check_output.side_effect = output_list
        res = lvs_query.get_udp_listeners_stats()
        # We can check the expected result reference the stats sample,
        # that means this func can compute the stats info of single listener.
        expected = {self.listener_id_v4: {
            'status': constants.OPEN,
            'stats': {'bin': 6387472, 'stot': 5, 'bout': 7490,
                      'ereq': 0, 'scur': 0}}}
        self.assertEqual(expected, res)

        # if no udp listener need to be collected.
        # Then this function will return nothing.
        mock_is_running.return_value = False
        res = lvs_query.get_udp_listeners_stats()
        self.assertEqual({}, res)
