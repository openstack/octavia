# Copyright 2017 Rackspace US, Inc.
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

import random

import mock
from oslo_utils import uuidutils

from octavia.amphorae.backends.agent import api_server
from octavia.amphorae.backends.agent.api_server import amphora_info
from octavia.tests.common import utils as test_utils
import octavia.tests.unit.base as base


class TestAmphoraInfo(base.TestCase):

    API_VERSION = random.randrange(0, 10000)
    HAPROXY_VERSION = random.randrange(0, 10000)

    def setUp(self):
        super(TestAmphoraInfo, self).setUp()
        self.osutils_mock = mock.MagicMock()
        self.amp_info = amphora_info.AmphoraInfo(self.osutils_mock)

    @mock.patch.object(amphora_info, "webob")
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'amphora_info.AmphoraInfo._get_version_of_installed_package',
                return_value=HAPROXY_VERSION)
    @mock.patch('socket.gethostname', return_value='FAKE_HOST')
    def test_compile_amphora_info(self, mock_gethostname, mock_pkg_version,
                                  mock_webob):
        original_version = api_server.VERSION
        api_server.VERSION = self.API_VERSION
        expected_dict = {'api_version': self.API_VERSION,
                         'hostname': 'FAKE_HOST',
                         'haproxy_version': self.HAPROXY_VERSION}
        self.amp_info.compile_amphora_info()
        mock_webob.Response.assert_called_once_with(json=expected_dict)
        api_server.VERSION = original_version

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'is_listener_running')
    def test__count_haproxy_process(self, mock_is_running):

        # Test no listeners passed in
        result = self.amp_info._count_haproxy_processes([])
        self.assertEqual(0, result)

        # Test with a listener specified
        mock_is_running.side_effect = [True, False]
        result = self.amp_info._count_haproxy_processes(
            [uuidutils.generate_uuid(), uuidutils.generate_uuid()])
        self.assertEqual(1, result)

    def test__get_meminfo(self):
        # Known data test
        meminfo = ('MemTotal:       21692784 kB\n'
                   'MemFree:        12685624 kB\n'
                   'MemAvailable:   17384072 kB\n'
                   'Buffers:          344792 kB\n'
                   'Cached:          4271856 kB\n'
                   'SwapCached:            0 kB\n'
                   'Active:          5808816 kB\n'
                   'Inactive:        2445236 kB\n'
                   'Active(anon):    3646184 kB\n'
                   'Inactive(anon):     8672 kB\n'
                   'Active(file):    2162632 kB\n'
                   'Inactive(file):  2436564 kB\n'
                   'Unevictable:       52664 kB\n'
                   'Mlocked:           52664 kB\n'
                   'SwapTotal:      20476924 kB\n'
                   'SwapFree:       20476924 kB\n'
                   'Dirty:                92 kB\n'
                   'Writeback:             0 kB\n'
                   'AnonPages:       3690088 kB\n'
                   'Mapped:           108520 kB\n'
                   'Shmem:              9520 kB\n'
                   'Slab:             534384 kB\n'
                   'SReclaimable:     458160 kB\n'
                   'SUnreclaim:        76224 kB\n'
                   'KernelStack:       11776 kB\n'
                   'PageTables:        33088 kB\n'
                   'NFS_Unstable:          0 kB\n'
                   'Bounce:                0 kB\n'
                   'WritebackTmp:          0 kB\n'
                   'CommitLimit:    31323316 kB\n'
                   'Committed_AS:    6930732 kB\n'
                   'VmallocTotal:   34359738367 kB\n'
                   'VmallocUsed:           0 kB\n'
                   'VmallocChunk:          0 kB\n'
                   'HardwareCorrupted:     0 kB\n'
                   'AnonHugePages:   1400832 kB\n'
                   'CmaTotal:              0 kB\n'
                   'CmaFree:               0 kB\n'
                   'HugePages_Total:       0\n'
                   'HugePages_Free:        0\n'
                   'HugePages_Rsvd:        0\n'
                   'HugePages_Surp:        0\n'
                   'Hugepagesize:       2048 kB\n'
                   'DirectMap4k:      130880 kB\n'
                   'DirectMap2M:     8376320 kB\n'
                   'DirectMap1G:    14680064 kB\n')

        self.useFixture(test_utils.OpenFixture('/proc/meminfo',
                                               contents=meminfo))

        expected_result = {'SwapCached': 0, 'DirectMap2M': 8376320,
                           'CmaTotal': 0, 'Inactive': 2445236,
                           'KernelStack': 11776, 'SwapTotal': 20476924,
                           'VmallocUsed': 0, 'Buffers': 344792,
                           'MemTotal': 21692784, 'Mlocked': 52664,
                           'Cached': 4271856, 'AnonPages': 3690088,
                           'Unevictable': 52664, 'SUnreclaim': 76224,
                           'MemFree': 12685624, 'Writeback': 0,
                           'NFS_Unstable': 0, 'VmallocTotal': 34359738367,
                           'MemAvailable': 17384072, 'CmaFree': 0,
                           'SwapFree': 20476924, 'AnonHugePages': 1400832,
                           'DirectMap1G': 14680064, 'Hugepagesize': 2048,
                           'Dirty': 92, 'Bounce': 0, 'PageTables': 33088,
                           'SReclaimable': 458160, 'Active': 5808816,
                           'Mapped': 108520, 'Slab': 534384,
                           'Active(anon)': 3646184, 'VmallocChunk': 0,
                           'Inactive(file)': 2436564, 'WritebackTmp': 0,
                           'Shmem': 9520, 'Inactive(anon)': 8672,
                           'HardwareCorrupted': 0, 'Active(file)': 2162632,
                           'DirectMap4k': 130880, 'Committed_AS': 6930732,
                           'CommitLimit': 31323316}

        result = self.amp_info._get_meminfo()
        self.assertEqual(expected_result, result)

    def test__cpu(self):

        sample_stat = 'cpu  252551 802 52554 7181757 7411 0 8336 0 0 0'

        expected_result = {'user': '252551', 'iowait': '7411', 'nice': '802',
                           'softirq': '8336', 'idle': '7181757',
                           'system': '52554', 'total': 7503411, 'irq': '0'}

        self.useFixture(test_utils.OpenFixture('/proc/stat',
                                               contents=sample_stat))

        result = self.amp_info._cpu()

        self.assertEqual(expected_result, result)

    def test__load(self):

        sample_loadavg = '0.09 0.11 0.10 2/630 15346'

        expected_result = ['0.09', '0.11', '0.10']

        self.useFixture(test_utils.OpenFixture('/proc/loadavg',
                                               contents=sample_loadavg))

        result = self.amp_info._load()

        self.assertEqual(expected_result, result)

    @mock.patch('pyroute2.NetNS')
    def test__get_networks(self, mock_netns):

        # The output of get_links is huge, just pulling out the parts we
        # care about for this test.
        sample_get_links_minimal = [
            {'attrs': [('IFLA_IFNAME', 'lo')]},
            {'attrs': [('IFLA_IFNAME', 'eth1'),
                       ('IFLA_STATS64', {'tx_bytes': 418, 'rx_bytes': 996})]},
            {'attrs': [('IFLA_IFNAME', 'eth2'),
                       ('IFLA_STATS64', {'tx_bytes': 578, 'rx_bytes': 848})]},
            {'attrs': [('IFLA_IFNAME', 'eth3')]}]

        netns_handle = mock_netns.return_value.__enter__.return_value
        netns_handle.get_links.return_value = sample_get_links_minimal

        expected_result = {'eth1': {'network_rx': 996, 'network_tx': 418},
                           'eth2': {'network_rx': 848, 'network_tx': 578}}

        result = self.amp_info._get_networks()

        self.assertEqual(expected_result, result)
