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

import mock

from octavia.amphorae.backends.utils import haproxy_query as query
import octavia.tests.unit.base as base

STATS_SOCKET_SAMPLE = [
    "# pxname,svname,qcur,qmax,scur,smax,slim,stot,bin,bout,dreq,dresp,ereq,"
    "econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,"
    "downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,"
    "rate_max,check_status,check_code,check_duration,hrsp_1xx,hrsp_2xx,hrsp"
    "_3xx,hrsp_4xx,hrsp_5xx,hrsp_other,hanafail,req_rate,req_rate_max,req_tot"
    ",cli_abrt,srv_abrt,comp_in,comp_out,comp_byp,comp_rsp,lastsess,last_chk,"
    "last_agt,qtime,ctime,rtime,ttime,",

    "http-servers,id-34821,0,0,0,0,,0,0,0,,0,,0,0,0,0,DOWN,1,1,0,1,1,575,575"
    ",,1,3,1,,0,,2,0,,0,L4TOUT,,30001,0,0,0,0,0,0,0,,,,0,0,,,,,-1,,,0,0,0,0,",

    "http-servers,id-34824,0,0,0,0,,0,0,0,,0,,0,0,0,0,DOWN,1,1,0,1,1,567,567,"
    ",1,3,2,,0,,2,0,,0,L4TOUT,,30001,0,0,0,0,0,0,0,,,,0,0,,,,,-1,,,0,0,0,0,",

    "http-servers,BACKEND,0,0,0,0,200,0,0,0,0,0,,0,0,0,0,DOWN,0,0,0,,1,567,567"
    ",,1,3,0,,0,,1,0,,0,,,,0,0,0,0,0,0,,,,,0,0,0,0,0,0,-1,,,0,0,0,0,",

    "tcp-servers,id-34833,0,0,0,0,,0,0,0,,0,,0,0,0,0,DOWN,1,1,0,1,1,"
    "560,560,,1,5,1,,0,,2,0,,0,L4TOUT,,30000,,,,,,,0,,,,0,0,,,,,-1,,"
    ",0,0,0,0,",

    "tcp-servers,id-34836,0,0,0,0,,0,0,0,,0,,0,0,0,0,DOWN,1,1,0,1,1,552,552,,"
    "1,5,2,,0,,2,0,,0,L4TOUT,,30001,,,,,,,0,,,,0,0,,,,,-1,,,0,0,0,0,",

    "tcp-servers,BACKEND,0,0,0,0,200,0,0,0,0,0,,0,0,0,0,DOWN,0,0,0,,1,552,552"
    ",,1,5,0,,0,,1,0,,0,,,,,,,,,,,,,,0,0,0,0,0,0,-1,,,0,0,0,0,"]


class QueryTestCase(base.TestCase):
    def setUp(self):
        self.q = query.HAProxyQuery('')
        super(QueryTestCase, self).setUp()

    def test_get_pool_status(self):
        stat_mock = mock.Mock()
        self.q.show_stat = stat_mock
        stat_mock.return_value = STATS_SOCKET_SAMPLE
        self.assertEqual(
            {'tcp-servers':
                 {'status': 'DOWN',
                  'uuid': 'tcp-servers',
                  'members': [
                      {'id-34833': 'DOWN'},
                      {'id-34836': 'DOWN'}]},
             'http-servers': {
                 'status': 'DOWN',
                 'uuid': 'http-servers',
                 'members': [
                     {'id-34821': 'DOWN'},
                     {'id-34824': 'DOWN'}]}},
            self.q.get_pool_status()
        )