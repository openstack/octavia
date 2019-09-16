# Copyright 2015 Hewlett-Packard Development Company, L.P.
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

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils
import six

from octavia.amphorae.backends.health_daemon import health_daemon
from octavia.common import constants
import octavia.tests.unit.base as base

if six.PY2:
    import Queue as queue
else:
    import queue


LISTENER_ID1 = uuidutils.generate_uuid()
LISTENER_ID2 = uuidutils.generate_uuid()
LISTENER_IDS = [LISTENER_ID1, LISTENER_ID2]
BASE_PATH = '/tmp/test'
SAMPLE_POOL_STATUS = {'432fc8b3-d446-48d4-bb64-13beb90e22bc': {
                      'status': 'UP',
                      'uuid': '432fc8b3-d446-48d4-bb64-13beb90e22bc',
                      'members': {
                          '302e33d9-dee1-4de9-98d5-36329a06fb58': 'DOWN'}}}

SAMPLE_BOGUS_POOL_STATUS = {LISTENER_ID1: {
                            'status': 'UP',
                            'uuid': LISTENER_ID1,
                            'members': {
                                '302e33d9-dee1-4de9-98d5-36329a06fb58':
                                'DOWN'}}}

SAMPLE_STATS = ({'': '', 'status': 'OPEN', 'lastchg': '',
                 'weight': '', 'slim': '2000', 'pid': '1', 'comp_byp': '0',
                 'lastsess': '', 'rate_lim': '0', 'check_duration': '',
                 'rate': '0', 'req_rate': '0', 'check_status': '',
                 'econ': '', 'comp_out': '0', 'wredis': '', 'dresp': '0',
                 'ereq': '0', 'tracked': '', 'comp_in': '0',
                 'pxname': LISTENER_ID1,
                 'dreq': '0', 'hrsp_5xx': '0', 'last_chk': '',
                 'check_code': '', 'sid': '0', 'bout': '0', 'hrsp_1xx': '0',
                 'qlimit': '', 'hrsp_other': '0', 'bin': '0', 'rtime': '',
                 'smax': '0', 'req_tot': '0', 'lbtot': '', 'stot': '0',
                 'wretr': '', 'req_rate_max': '0', 'ttime': '', 'iid': '2',
                 'hrsp_4xx': '0', 'chkfail': '', 'hanafail': '',
                 'downtime': '', 'qcur': '', 'eresp': '', 'comp_rsp': '0',
                 'cli_abrt': '', 'ctime': '', 'qtime': '', 'srv_abrt': '',
                 'throttle': '', 'last_agt': '', 'scur': '0', 'type': '0',
                 'bck': '', 'qmax': '', 'rate_max': '0', 'hrsp_2xx': '0',
                 'act': '', 'chkdown': '', 'svname': 'FRONTEND',
                 'hrsp_3xx': '0'},
                {'': '', 'status': 'no check', 'lastchg': '', 'weight': '1',
                 'slim': '', 'pid': '1', 'comp_byp': '', 'lastsess': '-1',
                 'rate_lim': '', 'check_duration': '', 'rate': '0',
                 'req_rate': '', 'check_status': '', 'econ': '0',
                 'comp_out': '', 'wredis': '0', 'dresp': '0', 'ereq': '',
                 'tracked': '', 'comp_in': '',
                 'pxname': '432fc8b3-d446-48d4-bb64-13beb90e22bc',
                 'dreq': '', 'hrsp_5xx': '0', 'last_chk': '',
                 'check_code': '', 'sid': '1', 'bout': '0', 'hrsp_1xx': '0',
                 'qlimit': '', 'hrsp_other': '0', 'bin': '0', 'rtime': '0',
                 'smax': '0', 'req_tot': '', 'lbtot': '0', 'stot': '0',
                 'wretr': '0', 'req_rate_max': '', 'ttime': '0', 'iid': '3',
                 'hrsp_4xx': '0', 'chkfail': '', 'hanafail': '0',
                 'downtime': '', 'qcur': '0', 'eresp': '0', 'comp_rsp': '',
                 'cli_abrt': '0', 'ctime': '0', 'qtime': '0', 'srv_abrt': '0',
                 'throttle': '', 'last_agt': '', 'scur': '0', 'type': '2',
                 'bck': '0', 'qmax': '0', 'rate_max': '0', 'hrsp_2xx': '0',
                 'act': '1', 'chkdown': '',
                 'svname': '302e33d9-dee1-4de9-98d5-36329a06fb58',
                 'hrsp_3xx': '0'},
                {'': '', 'status': 'UP', 'lastchg': '122', 'weight': '1',
                 'slim': '200', 'pid': '1', 'comp_byp': '0', 'lastsess': '-1',
                 'rate_lim': '', 'check_duration': '', 'rate': '0',
                 'req_rate': '', 'check_status': '', 'econ': '0',
                 'comp_out': '0', 'wredis': '0', 'dresp': '0', 'ereq': '',
                 'tracked': '', 'comp_in': '0',
                 'pxname': '432fc8b3-d446-48d4-bb64-13beb90e22bc', 'dreq': '0',
                 'hrsp_5xx': '0', 'last_chk': '', 'check_code': '', 'sid': '0',
                 'bout': '0', 'hrsp_1xx': '0', 'qlimit': '', 'hrsp_other': '0',
                 'bin': '0', 'rtime': '0', 'smax': '0', 'req_tot': '',
                 'lbtot': '0', 'stot': '0', 'wretr': '0', 'req_rate_max': '',
                 'ttime': '0', 'iid': '3', 'hrsp_4xx': '0', 'chkfail': '',
                 'hanafail': '', 'downtime': '0', 'qcur': '0', 'eresp': '0',
                 'comp_rsp': '0', 'cli_abrt': '0', 'ctime': '0', 'qtime': '0',
                 'srv_abrt': '0', 'throttle': '', 'last_agt': '', 'scur': '0',
                 'type': '1', 'bck': '0', 'qmax': '0', 'rate_max': '0',
                 'hrsp_2xx': '0', 'act': '1', 'chkdown': '0',
                 'svname': 'BACKEND', 'hrsp_3xx': '0'})

SAMPLE_STATS_MSG = {
    'listeners': {
        LISTENER_ID1: {
            'stats': {
                'totconns': 0, 'conns': 0,
                'tx': 0, 'rx': 0, 'ereq': 0},
            'status': 'OPEN'},
    },
    'pools': {'432fc8b3-d446-48d4-bb64-13beb90e22bc': {
        'members': {'302e33d9-dee1-4de9-98d5-36329a06fb58': 'DOWN'},
        'status': 'UP'}, '432fc8b3-d446-48d4-bb64-13beb90e22bc': {
        'members': {'302e33d9-dee1-4de9-98d5-36329a06fb58': 'DOWN'},
        'status': 'UP'},
    },
    'id': None,
    'seq': 0,
    'ver': health_daemon.MSG_VER
}


class TestHealthDaemon(base.TestCase):

    def setUp(self):
        super(TestHealthDaemon, self).setUp()
        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="haproxy_amphora", base_path=BASE_PATH)

    @mock.patch('octavia.amphorae.backends.agent.'
                'api_server.util.get_loadbalancers')
    def test_list_sock_stat_files(self, mock_get_listener):
        mock_get_listener.return_value = LISTENER_IDS

        health_daemon.list_sock_stat_files()

        files = health_daemon.list_sock_stat_files(BASE_PATH)

        expected_files = {LISTENER_ID1: BASE_PATH + '/' +
                          LISTENER_ID1 + '.sock',
                          LISTENER_ID2: BASE_PATH + '/' +
                          LISTENER_ID2 + '.sock'}
        self.assertEqual(expected_files, files)

    @mock.patch('os.kill')
    @mock.patch('os.path.isfile')
    @mock.patch('octavia.amphorae.backends.health_daemon.'
                'health_daemon.time.sleep')
    @mock.patch('oslo_config.cfg.CONF.reload_config_files')
    @mock.patch('octavia.amphorae.backends.health_daemon.'
                'health_daemon.build_stats_message')
    @mock.patch('octavia.amphorae.backends.health_daemon.'
                'health_sender.UDPStatusSender')
    def test_run_sender(self, mock_UDPStatusSender, mock_build_msg,
                        mock_reload_cfg, mock_sleep, mock_isfile, mock_kill):
        sender_mock = mock.MagicMock()
        dosend_mock = mock.MagicMock()
        sender_mock.dosend = dosend_mock
        mock_UDPStatusSender.return_value = sender_mock
        mock_build_msg.side_effect = ['TEST']

        mock_isfile.return_value = False

        test_queue = queue.Queue()
        with mock.patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = Exception('break')
            self.assertRaisesRegex(Exception, 'break',
                                   health_daemon.run_sender, test_queue)

        sender_mock.dosend.assert_called_once_with('TEST')

        # Test a reload event
        mock_build_msg.reset_mock()
        mock_build_msg.side_effect = ['TEST']
        test_queue.put('reload')
        with mock.patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = Exception('break')
            self.assertRaisesRegex(Exception, 'break',
                                   health_daemon.run_sender, test_queue)
        mock_reload_cfg.assert_called_once_with()

        # Test the shutdown path
        sender_mock.reset_mock()
        dosend_mock.reset_mock()
        mock_build_msg.reset_mock()
        mock_build_msg.side_effect = ['TEST', 'TEST']
        test_queue.put('shutdown')
        health_daemon.run_sender(test_queue)
        sender_mock.dosend.assert_called_once_with('TEST')

        # Test an unknown command
        mock_build_msg.reset_mock()
        mock_build_msg.side_effect = ['TEST']
        test_queue.put('bogus')
        with mock.patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = Exception('break')
            self.assertRaisesRegex(Exception, 'break',
                                   health_daemon.run_sender, test_queue)

        # Test keepalived config, but no PID
        mock_build_msg.reset_mock()
        dosend_mock.reset_mock()
        mock_isfile.return_value = True
        with mock.patch('octavia.amphorae.backends.health_daemon.'
                        'health_daemon.open', mock.mock_open()) as mock_open:
            mock_open.side_effect = FileNotFoundError
            test_queue.put('shutdown')
            health_daemon.run_sender(test_queue)
            mock_build_msg.assert_not_called()
            dosend_mock.assert_not_called()

        # Test keepalived config, but PID file error
        mock_build_msg.reset_mock()
        dosend_mock.reset_mock()
        mock_isfile.return_value = True
        with mock.patch('octavia.amphorae.backends.health_daemon.'
                        'health_daemon.open', mock.mock_open()) as mock_open:
            mock_open.side_effect = IOError
            test_queue.put('shutdown')
            health_daemon.run_sender(test_queue)
            mock_build_msg.assert_not_called()
            dosend_mock.assert_not_called()

        # Test keepalived config, but bogus PID
        mock_build_msg.reset_mock()
        dosend_mock.reset_mock()
        mock_isfile.return_value = True
        with mock.patch('octavia.amphorae.backends.health_daemon.'
                        'health_daemon.open',
                        mock.mock_open(read_data='foo')) as mock_open:
            test_queue.put('shutdown')
            health_daemon.run_sender(test_queue)
            mock_build_msg.assert_not_called()
            dosend_mock.assert_not_called()

        # Test keepalived config, but not running
        mock_build_msg.reset_mock()
        dosend_mock.reset_mock()
        mock_isfile.return_value = True
        with mock.patch('octavia.amphorae.backends.health_daemon.'
                        'health_daemon.open',
                        mock.mock_open(read_data='999999')) as mock_open:
            mock_kill.side_effect = ProccessNotFoundError
            test_queue.put('shutdown')
            health_daemon.run_sender(test_queue)
            mock_build_msg.assert_not_called()
            dosend_mock.assert_not_called()

        # Test keepalived config, but process error
        mock_build_msg.reset_mock()
        dosend_mock.reset_mock()
        mock_isfile.return_value = True
        with mock.patch('octavia.amphorae.backends.health_daemon.'
                        'health_daemon.open',
                        mock.mock_open(read_data='999999')) as mock_open:
            mock_kill.side_effect = OSError
            test_queue.put('shutdown')
            health_daemon.run_sender(test_queue)
            mock_build_msg.assert_not_called()
            dosend_mock.assert_not_called()

        # Test with happy keepalive
        sender_mock.reset_mock()
        dosend_mock.reset_mock()
        mock_kill.side_effect = [True]
        mock_build_msg.reset_mock()
        mock_build_msg.side_effect = ['TEST', 'TEST']
        mock_isfile.return_value = True
        test_queue.put('shutdown')
        with mock.patch('octavia.amphorae.backends.health_daemon.'
                        'health_daemon.open',
                        mock.mock_open(read_data='999999')) as mock_open:
            health_daemon.run_sender(test_queue)
        sender_mock.dosend.assert_called_once_with('TEST')

    @mock.patch('octavia.amphorae.backends.utils.haproxy_query.HAProxyQuery')
    def test_get_stats(self, mock_query):
        stats_query_mock = mock.MagicMock()
        mock_query.return_value = stats_query_mock

        health_daemon.get_stats('TEST')

        stats_query_mock.show_stat.assert_called_once_with()
        stats_query_mock.get_pool_status.assert_called_once_with()

    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'util.is_lb_running')
    @mock.patch('octavia.amphorae.backends.health_daemon.'
                'health_daemon.get_stats')
    @mock.patch('octavia.amphorae.backends.health_daemon.'
                'health_daemon.list_sock_stat_files')
    def test_build_stats_message(self, mock_list_files,
                                 mock_get_stats, mock_is_running):
        mock_list_files.return_value = {LISTENER_ID1: 'TEST',
                                        LISTENER_ID2: 'TEST2'}

        mock_is_running.return_value = True
        mock_get_stats.return_value = SAMPLE_STATS, SAMPLE_POOL_STATUS

        msg = health_daemon.build_stats_message()

        self.assertEqual(SAMPLE_STATS_MSG, msg)

        mock_get_stats.assert_any_call('TEST')
        mock_get_stats.assert_any_call('TEST2')

    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'util.is_lb_running')
    @mock.patch('octavia.amphorae.backends.health_daemon.'
                'health_daemon.get_stats')
    @mock.patch('octavia.amphorae.backends.health_daemon.'
                'health_daemon.list_sock_stat_files')
    def test_build_stats_message_no_listener(self, mock_list_files,
                                             mock_get_stats,
                                             mock_is_running):
        mock_list_files.return_value = {LISTENER_ID1: 'TEST',
                                        LISTENER_ID2: 'TEST2'}

        mock_is_running.side_effect = [True, False]
        mock_get_stats.return_value = SAMPLE_STATS, SAMPLE_POOL_STATUS

        health_daemon.build_stats_message()

        self.assertEqual(1, mock_get_stats.call_count)

    @mock.patch("octavia.amphorae.backends.utils.keepalivedlvs_query."
                "get_udp_listener_pool_status")
    @mock.patch("octavia.amphorae.backends.utils.keepalivedlvs_query."
                "get_udp_listeners_stats")
    @mock.patch("octavia.amphorae.backends.agent.api_server.util."
                "get_udp_listeners")
    def test_build_stats_message_with_udp_listener(
            self, mock_get_udp_listeners, mock_get_listener_stats,
            mock_get_pool_status):
        udp_listener_id1 = uuidutils.generate_uuid()
        udp_listener_id2 = uuidutils.generate_uuid()
        udp_listener_id3 = uuidutils.generate_uuid()
        pool_id = uuidutils.generate_uuid()
        member_id1 = uuidutils.generate_uuid()
        member_id2 = uuidutils.generate_uuid()
        mock_get_udp_listeners.return_value = [udp_listener_id1,
                                               udp_listener_id2,
                                               udp_listener_id3]
        mock_get_listener_stats.return_value = {
            udp_listener_id1: {
                'status': constants.OPEN,
                'stats': {'bin': 6387472, 'stot': 5, 'bout': 7490,
                          'ereq': 0, 'scur': 0}},
            udp_listener_id3: {
                'status': constants.DOWN,
                'stats': {'bin': 0, 'stot': 0, 'bout': 0,
                          'ereq': 0, 'scur': 0}}
        }
        udp_pool_status = {
            'lvs': {
                'uuid': pool_id,
                'status': constants.UP,
                'members': {member_id1: constants.UP,
                            member_id2: constants.UP}}}
        mock_get_pool_status.side_effect = (
            lambda x: udp_pool_status if x == udp_listener_id1 else {})
        # the first listener can get all necessary info.
        # the second listener can not get listener stats, so we won't report it
        # the third listener can get listener stats, but can not get pool
        # status, so the result will just contain the listener status for it.
        expected = {
            'listeners': {
                udp_listener_id1: {
                    'status': constants.OPEN,
                    'stats': {'conns': 0, 'totconns': 5, 'ereq': 0,
                              'rx': 6387472, 'tx': 7490}},
                udp_listener_id3: {
                    'status': constants.DOWN,
                    'stats': {'conns': 0, 'totconns': 0, 'ereq': 0,
                              'rx': 0, 'tx': 0}}},
            'pools': {
                pool_id: {
                    'status': constants.UP,
                    'members': {
                        member_id1: constants.UP,
                        member_id2: constants.UP}}},
            'id': None,
            'seq': mock.ANY, 'ver': health_daemon.MSG_VER}
        msg = health_daemon.build_stats_message()
        self.assertEqual(expected, msg)


class FileNotFoundError(IOError):
    errno = 2


class ProccessNotFoundError(OSError):
    errno = 3
