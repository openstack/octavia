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
from octavia.amphorae.backends.agent.api_server import util
from octavia.common.jinja.haproxy.combined_listeners import jinja_cfg
from octavia.tests.common import utils as test_utils
import octavia.tests.unit.base as base
from octavia.tests.unit.common.sample_configs import sample_configs_combined


class TestAmphoraInfo(base.TestCase):

    API_VERSION = random.randrange(0, 10000)
    BASE_AMP_PATH = '/var/lib/octavia'
    BASE_CRT_PATH = BASE_AMP_PATH + '/certs'
    HAPROXY_VERSION = random.randrange(0, 10000)
    KEEPALIVED_VERSION = random.randrange(0, 10000)
    IPVSADM_VERSION = random.randrange(0, 10000)
    FAKE_LISTENER_ID_1 = uuidutils.generate_uuid()
    FAKE_LISTENER_ID_2 = uuidutils.generate_uuid()
    FAKE_LISTENER_ID_3 = uuidutils.generate_uuid()
    FAKE_LISTENER_ID_4 = uuidutils.generate_uuid()
    LB_ID_1 = uuidutils.generate_uuid()

    def setUp(self):
        super(TestAmphoraInfo, self).setUp()
        self.osutils_mock = mock.MagicMock()
        self.amp_info = amphora_info.AmphoraInfo(self.osutils_mock)
        self.udp_driver = mock.MagicMock()

        # setup a fake haproxy config file
        templater = jinja_cfg.JinjaTemplater(
            base_amp_path=self.BASE_AMP_PATH,
            base_crt_dir=self.BASE_CRT_PATH)
        tls_tupel = {'cont_id_1':
                     sample_configs_combined.sample_tls_container_tuple(
                         id='tls_container_id',
                         certificate='imaCert1', private_key='imaPrivateKey1',
                         primary_cn='FakeCN')}
        self.rendered_haproxy_cfg = templater.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='TERMINATED_HTTPS', tls=True, sni=True)],
            tls_tupel)
        path = util.config_path(self.LB_ID_1)
        self.useFixture(test_utils.OpenFixture(path,
                                               self.rendered_haproxy_cfg))

    def _return_version(self, package_name):
        if package_name == 'ipvsadm':
            return self.IPVSADM_VERSION
        elif package_name == 'keepalived':
            return self.KEEPALIVED_VERSION
        else:
            return self.HAPROXY_VERSION

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

    @mock.patch.object(amphora_info, "webob")
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'amphora_info.AmphoraInfo._get_version_of_installed_package')
    @mock.patch('socket.gethostname', return_value='FAKE_HOST')
    def test_compile_amphora_info_for_udp(self, mock_gethostname,
                                          mock_pkg_version, mock_webob):

        mock_pkg_version.side_effect = self._return_version
        self.udp_driver.get_subscribed_amp_compile_info.side_effect = [
            ['keepalived', 'ipvsadm']]
        original_version = api_server.VERSION
        api_server.VERSION = self.API_VERSION
        expected_dict = {'api_version': self.API_VERSION,
                         'hostname': 'FAKE_HOST',
                         'haproxy_version': self.HAPROXY_VERSION,
                         'keepalived_version': self.KEEPALIVED_VERSION,
                         'ipvsadm_version': self.IPVSADM_VERSION
                         }
        self.amp_info.compile_amphora_info(extend_udp_driver=self.udp_driver)
        mock_webob.Response.assert_called_once_with(json=expected_dict)
        api_server.VERSION = original_version

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_listeners', return_value=[FAKE_LISTENER_ID_1,
                                               FAKE_LISTENER_ID_2])
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'amphora_info.AmphoraInfo._get_meminfo')
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'amphora_info.AmphoraInfo._cpu')
    @mock.patch('os.statvfs')
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'amphora_info.AmphoraInfo._get_networks')
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'amphora_info.AmphoraInfo._load')
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'amphora_info.AmphoraInfo._get_version_of_installed_package')
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'amphora_info.AmphoraInfo._count_haproxy_processes')
    @mock.patch('socket.gethostname', return_value='FAKE_HOST')
    def test_compile_amphora_details(self, mhostname, m_count, m_pkg_version,
                                     m_load, m_get_nets, m_os, m_cpu,
                                     mget_mem, mget_listener):
        mget_mem.return_value = {'SwapCached': 0, 'Buffers': 344792,
                                 'MemTotal': 21692784, 'Cached': 4271856,
                                 'Slab': 534384, 'MemFree': 12685624,
                                 'Shmem': 9520}
        m_cpu.return_value = {'user': '252551', 'softirq': '8336',
                              'system': '52554', 'total': 7503411}
        m_pkg_version.side_effect = self._return_version
        mdisk_info = mock.MagicMock()
        m_os.return_value = mdisk_info
        mdisk_info.f_blocks = 34676992
        mdisk_info.f_bfree = 28398016
        mdisk_info.f_frsize = 4096
        mdisk_info.f_bavail = 26630646
        m_get_nets.return_value = {'eth1': {'network_rx': 996,
                                            'network_tx': 418},
                                   'eth2': {'network_rx': 848,
                                            'network_tx': 578}}
        m_load.return_value = ['0.09', '0.11', '0.10']
        m_count.return_value = 5
        original_version = api_server.VERSION
        api_server.VERSION = self.API_VERSION
        expected_dict = {u'active': True,
                         u'api_version': self.API_VERSION,
                         u'cpu': {u'soft_irq': u'8336',
                                  u'system': u'52554',
                                  u'total': 7503411,
                                  u'user': u'252551'},
                         u'disk': {u'available': 109079126016,
                                   u'used': 25718685696},
                         u'haproxy_count': 5,
                         u'haproxy_version': self.HAPROXY_VERSION,
                         u'hostname': u'FAKE_HOST',
                         u'listeners': sorted([self.FAKE_LISTENER_ID_1,
                                               self.FAKE_LISTENER_ID_2]),
                         u'load': [u'0.09', u'0.11', u'0.10'],
                         u'memory': {u'buffers': 344792,
                                     u'cached': 4271856,
                                     u'free': 12685624,
                                     u'shared': 9520,
                                     u'slab': 534384,
                                     u'swap_used': 0,
                                     u'total': 21692784},
                         u'networks': {u'eth1': {u'network_rx': 996,
                                                 u'network_tx': 418},
                                       u'eth2': {u'network_rx': 848,
                                                 u'network_tx': 578}},
                         u'packages': {},
                         u'topology': u'SINGLE',
                         u'topology_status': u'OK'}
        actual = self.amp_info.compile_amphora_details()
        self.assertEqual(expected_dict, actual.json)
        api_server.VERSION = original_version

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_udp_listeners',
                return_value=[FAKE_LISTENER_ID_3, FAKE_LISTENER_ID_4])
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_loadbalancers')
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'amphora_info.AmphoraInfo._get_meminfo')
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'amphora_info.AmphoraInfo._cpu')
    @mock.patch('os.statvfs')
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'amphora_info.AmphoraInfo._get_networks')
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'amphora_info.AmphoraInfo._load')
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'amphora_info.AmphoraInfo._get_version_of_installed_package')
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'amphora_info.AmphoraInfo._count_haproxy_processes')
    @mock.patch('socket.gethostname', return_value='FAKE_HOST')
    def test_compile_amphora_details_for_udp(self, mhostname, m_count,
                                             m_pkg_version, m_load, m_get_nets,
                                             m_os, m_cpu, mget_mem,
                                             mock_get_lb, mget_udp_listener):
        mget_mem.return_value = {'SwapCached': 0, 'Buffers': 344792,
                                 'MemTotal': 21692784, 'Cached': 4271856,
                                 'Slab': 534384, 'MemFree': 12685624,
                                 'Shmem': 9520}
        m_cpu.return_value = {'user': '252551', 'softirq': '8336',
                              'system': '52554', 'total': 7503411}
        m_pkg_version.side_effect = self._return_version
        mdisk_info = mock.MagicMock()
        m_os.return_value = mdisk_info
        mdisk_info.f_blocks = 34676992
        mdisk_info.f_bfree = 28398016
        mdisk_info.f_frsize = 4096
        mdisk_info.f_bavail = 26630646
        m_get_nets.return_value = {'eth1': {'network_rx': 996,
                                            'network_tx': 418},
                                   'eth2': {'network_rx': 848,
                                            'network_tx': 578}}
        m_load.return_value = ['0.09', '0.11', '0.10']
        m_count.return_value = 5
        self.udp_driver.get_subscribed_amp_compile_info.return_value = [
            'keepalived', 'ipvsadm']
        self.udp_driver.is_listener_running.side_effect = [True, False]
        mock_get_lb.return_value = [self.LB_ID_1]
        original_version = api_server.VERSION
        api_server.VERSION = self.API_VERSION
        expected_dict = {u'active': True,
                         u'api_version': self.API_VERSION,
                         u'cpu': {u'soft_irq': u'8336',
                                  u'system': u'52554',
                                  u'total': 7503411,
                                  u'user': u'252551'},
                         u'disk': {u'available': 109079126016,
                                   u'used': 25718685696},
                         u'haproxy_count': 5,
                         u'haproxy_version': self.HAPROXY_VERSION,
                         u'keepalived_version': self.KEEPALIVED_VERSION,
                         u'ipvsadm_version': self.IPVSADM_VERSION,
                         u'udp_listener_process_count': 1,
                         u'hostname': u'FAKE_HOST',
                         u'listeners': sorted(list(set(
                             [self.FAKE_LISTENER_ID_3,
                              self.FAKE_LISTENER_ID_4,
                              'sample_listener_id_1']))),
                         u'load': [u'0.09', u'0.11', u'0.10'],
                         u'memory': {u'buffers': 344792,
                                     u'cached': 4271856,
                                     u'free': 12685624,
                                     u'shared': 9520,
                                     u'slab': 534384,
                                     u'swap_used': 0,
                                     u'total': 21692784},
                         u'networks': {u'eth1': {u'network_rx': 996,
                                                 u'network_tx': 418},
                                       u'eth2': {u'network_rx': 848,
                                                 u'network_tx': 578}},
                         u'packages': {},
                         u'topology': u'SINGLE',
                         u'topology_status': u'OK'}
        actual = self.amp_info.compile_amphora_details(self.udp_driver)
        self.assertEqual(expected_dict, actual.json)
        api_server.VERSION = original_version

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'is_lb_running')
    def test__count_haproxy_process(self, mock_is_running):

        # Test no listeners passed in
        result = self.amp_info._count_haproxy_processes([])
        self.assertEqual(0, result)

        # Test with a listener specified
        mock_is_running.side_effect = [True, False]
        result = self.amp_info._count_haproxy_processes(
            [uuidutils.generate_uuid(), uuidutils.generate_uuid()])
        self.assertEqual(1, result)

    def test__count_udp_listener_processes(self):
        self.udp_driver.is_listener_running.side_effect = [True, False, True]
        expected = 2
        actual = self.amp_info._count_udp_listener_processes(
            self.udp_driver, [self.FAKE_LISTENER_ID_1,
                              self.FAKE_LISTENER_ID_2,
                              self.FAKE_LISTENER_ID_3])
        self.assertEqual(expected, actual)

    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'amphora_info.AmphoraInfo._get_version_of_installed_package')
    def test__get_extend_body_from_udp_driver(self, m_get_version):
        self.udp_driver.get_subscribed_amp_compile_info.return_value = [
            'keepalived', 'ipvsadm']
        m_get_version.side_effect = self._return_version
        expected = {
            "keepalived_version": self.KEEPALIVED_VERSION,
            "ipvsadm_version": self.IPVSADM_VERSION
        }
        actual = self.amp_info._get_extend_body_from_udp_driver(
            self.udp_driver)
        self.assertEqual(expected, actual)

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

    @mock.patch('pyroute2.NetNS', create=True)
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
