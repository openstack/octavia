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
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import socket

import mock

from octavia.amphorae.backends.utils import haproxy_query as query
import octavia.tests.unit.base as base

STATS_SOCKET_SAMPLE = (
    "# pxname,svname,qcur,qmax,scur,smax,slim,stot,bin,bout,dreq,dresp,ereq,"
    "econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,"
    "downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,"
    "rate_max,check_status,check_code,check_duration,hrsp_1xx,hrsp_2xx,hrsp"
    "_3xx,hrsp_4xx,hrsp_5xx,hrsp_other,hanafail,req_rate,req_rate_max,req_tot"
    ",cli_abrt,srv_abrt,comp_in,comp_out,comp_byp,comp_rsp,lastsess,last_chk,"
    "last_agt,qtime,ctime,rtime,ttime,\n"
    "http-servers,id-34821,0,0,0,0,,0,0,0,,0,,0,0,0,0,DOWN,1,1,0,1,1,575,575"
    ",,1,3,1,,0,,2,0,,0,L4TOUT,,30001,0,0,0,0,0,0,0,,,,0,0,,,,,-1,,,0,0,0,0,\n"
    "http-servers,id-34824,0,0,0,0,,0,0,0,,0,,0,0,0,0,DOWN,1,1,0,1,1,567,567,"
    ",1,3,2,,0,,2,0,,0,L4TOUT,,30001,0,0,0,0,0,0,0,,,,0,0,,,,,-1,,,0,0,0,0,\n"
    "http-servers,BACKEND,0,0,0,0,200,0,0,0,0,0,,0,0,0,0,DOWN,0,0,0,,1,567,567"
    ",,1,3,0,,0,,1,0,,0,,,,0,0,0,0,0,0,,,,,0,0,0,0,0,0,-1,,,0,0,0,0,\n"
    "tcp-servers,id-34833,0,0,0,0,,0,0,0,,0,,0,0,0,0,UP,1,1,0,1,1,560,560,,"
    "1,5,1,,0,,2,0,,0,L4TOUT,,30000,,,,,,,0,,,,0,0,,,,,-1,,,0,0,0,0,\n"
    "tcp-servers,id-34836,0,0,0,0,,0,0,0,,0,,0,0,0,0,UP,1,1,0,1,1,552,552,,"
    "1,5,2,,0,,2,0,,0,L4TOUT,,30001,,,,,,,0,,,,0,0,,,,,-1,,,0,0,0,0,\n"
    "tcp-servers,BACKEND,0,0,0,0,200,0,0,0,0,0,,0,0,0,0,UP,0,0,0,,1,552,552"
    ",,1,5,0,,0,,1,0,,0,,,,,,,,,,,,,,0,0,0,0,0,0,-1,,,0,0,0,0,"
)

INFO_SOCKET_SAMPLE = (
    'Name: HAProxy\nVersion: 1.5.3\nRelease_date: 2014/07/25\nNbproc: 1\n'
    'Process_num: 1\nPid: 2238\nUptime: 0d 2h22m17s\nUptime_sec: 8537\n'
    'Memmax_MB: 0\nUlimit-n: 4031\nMaxsock: 4031\nMaxconn: 2000\n'
    'Hard_maxconn: 2000\nCurrConns: 0\nCumConns: 32\nCumReq: 32\n'
    'MaxSslConns: 0\nCurrSslConns: 0\nCumSslConns: 0\nMaxpipes: 0\n'
    'PipesUsed: 0\nPipesFree: 0\nConnRate: 0\nConnRateLimit: 0\n'
    'MaxConnRate: 0\nSessRate: 0\nSessRateLimit: 0\nMaxSessRate: 0\n'
    'SslRate:0\nSslRateLimit: 0\nMaxSslRate: 0\nSslFrontendKeyRate: 0\n'
    'SslFrontendMaxKeyRate: 0\nSslFrontendSessionReuse_pct: 0\n'
    'SslBackendKeyRate: 0\nSslBackendMaxKeyRate: 0\nSslCacheLookups: 0\n'
    'SslCacheMisses: 0\nCompressBpsIn: 0\nCompressBpsOut: 0\n'
    'CompressBpsRateLim: 0\nZlibMemUsage: 0\nMaxZlibMemUsage: 0\nTasks: 4\n'
    'Run_queue: 1\nIdle_pct: 100\nnode: amphora-abd35de5-e377-49c5-be32\n'
    'description:'
)


class QueryTestCase(base.TestCase):
    def setUp(self):
        self.q = query.HAProxyQuery('')
        super(QueryTestCase, self).setUp()

    @mock.patch('socket.socket')
    def test_query(self, mock_socket):

        sock = mock.MagicMock()
        sock.connect.side_effect = [None, socket.error]
        sock.recv.side_effect = ['testdata', None]
        mock_socket.return_value = sock

        self.q._query('test')

        sock.connect.assert_called_once_with('')
        sock.send.assert_called_once_with('test' + '\n')
        sock.recv.assert_called_with(1024)
        self.assertTrue(sock.close.called)

        self.assertRaisesRegexp(Exception,
                                'HAProxy \'test\' query failed.',
                                self.q._query, 'test')

    def test_get_pool_status(self):
        query_mock = mock.Mock()
        self.q._query = query_mock
        query_mock.return_value = STATS_SOCKET_SAMPLE
        self.assertEqual(
            {'tcp-servers': {
                'status': 'UP',
                'uuid': 'tcp-servers',
                'members':
                    {'id-34833': 'UP',
                     'id-34836': 'UP'}},
             'http-servers': {
                'status': 'DOWN',
                'uuid': 'http-servers',
                'members':
                    {'id-34821': 'DOWN',
                     'id-34824': 'DOWN'}}},
            self.q.get_pool_status()
        )

    def test_show_info(self):
        query_mock = mock.Mock()
        self.q._query = query_mock
        query_mock.return_value = INFO_SOCKET_SAMPLE
        self.assertEqual(
            {'SslRateLimit': '0', 'SessRateLimit': '0', 'Version': '1.5.3',
             'Hard_maxconn': '2000', 'Ulimit-n': '4031', 'PipesFree': '0',
             'SslRate': '0', 'ZlibMemUsage': '0', 'CumConns': '32',
             'ConnRate': '0', 'Memmax_MB': '0', 'CompressBpsOut': '0',
             'MaxConnRate': '0', 'Uptime_sec': '8537', 'SslCacheMisses': '0',
             'MaxZlibMemUsage': '0', 'SslCacheLookups': '0',
             'CurrSslConns': '0', 'SslBackendKeyRate': '0',
             'CompressBpsRateLim': '0', 'Run_queue': '1', 'CumReq': '32',
             'SslBackendMaxKeyRate': '0', 'SslFrontendSessionReuse_pct': '0',
             'Nbproc': '1', 'Tasks': '4', 'Maxpipes': '0', 'Maxconn': '2000',
             'Pid': '2238', 'Maxsock': '4031', 'CurrConns': '0',
             'Idle_pct': '100', 'CompressBpsIn': '0',
             'SslFrontendKeyRate': '0', 'MaxSessRate': '0', 'Process_num': '1',
             'Uptime': '0d 2h22m17s', 'PipesUsed': '0', 'SessRate': '0',
             'MaxSslRate': '0', 'ConnRateLimit': '0', 'CumSslConns': '0',
             'Name': 'HAProxy', 'SslFrontendMaxKeyRate': '0',
             'MaxSslConns': '0', 'node': 'amphora-abd35de5-e377-49c5-be32',
             'description': '', 'Release_date': '2014/07/25'},
            self.q.show_info()
        )
