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
#    License for the specific language governing permissions and limitations
#    under the License.

import hashlib
import os
import random
import socket
import stat
import subprocess
from unittest import mock

import fixtures
from oslo_config import fixture as oslo_fixture
from oslo_serialization import jsonutils
from oslo_utils import uuidutils
import webob

from octavia.amphorae.backends.agent import api_server
from octavia.amphorae.backends.agent.api_server import certificate_update
from octavia.amphorae.backends.agent.api_server import server
from octavia.amphorae.backends.agent.api_server import util
from octavia.common import config
from octavia.common import constants as consts
from octavia.common import utils as octavia_utils
from octavia.tests.common import utils as test_utils
import octavia.tests.unit.base as base


AMP_AGENT_CONF_PATH = '/etc/octavia/amphora-agent.conf'
RANDOM_ERROR = 'random error'
OK = dict(message='OK')
FAKE_INTERFACE = 'eth33'


class TestServerTestCase(base.TestCase):
    app = None

    def setUp(self):
        super().setUp()
        self.conf = self.useFixture(oslo_fixture.Config(config.cfg.CONF))
        self.conf.config(group="haproxy_amphora", base_path='/var/lib/octavia')
        self.conf.config(group="controller_worker",
                         loadbalancer_topology=consts.TOPOLOGY_SINGLE)
        self.conf.load_raw_values(project='fake_project')
        self.conf.load_raw_values(prog='fake_prog')
        self.useFixture(fixtures.MockPatch(
            'oslo_config.cfg.find_config_files',
            return_value=[AMP_AGENT_CONF_PATH]))
        hm_queue = mock.MagicMock()
        with mock.patch('distro.id', return_value='ubuntu'), mock.patch(
                'octavia.amphorae.backends.agent.api_server.plug.'
                'Plug.plug_lo'):
            self.ubuntu_test_server = server.Server(hm_queue)
            self.ubuntu_app = self.ubuntu_test_server.app.test_client()

        with mock.patch('distro.id', return_value='centos'), mock.patch(
                'octavia.amphorae.backends.agent.api_server.plug.'
                'Plug.plug_lo'):
            self.centos_test_server = server.Server(hm_queue)
            self.centos_app = self.centos_test_server.app.test_client()

    def test_ubuntu_haproxy(self):
        self._test_haproxy(consts.UBUNTU)

    def test_centos_haproxy(self):
        self._test_haproxy(consts.CENTOS)

    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'haproxy_compatibility.get_haproxy_versions')
    @mock.patch('os.path.exists')
    @mock.patch('os.makedirs')
    @mock.patch('os.rename')
    @mock.patch('subprocess.check_output')
    def _test_haproxy(self, distro,
                      mock_subprocess, mock_rename,
                      mock_makedirs, mock_exists, mock_get_version):

        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])

        mock_get_version.return_value = [1, 6]

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mock_exists.return_value = True
        file_name = '/var/lib/octavia/123/haproxy.cfg.new'
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open

        # happy case upstart file exists
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen, mock.patch(
                'distro.id') as mock_distro_id:
            mock_open.return_value = 123
            mock_distro_id.return_value = distro
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                         '/loadbalancer/amp_123/123/haproxy',
                                         data='test')
            elif distro == consts.CENTOS:
                rv = self.centos_app.put('/' + api_server.VERSION +
                                         '/loadbalancer/amp_123/123/haproxy',
                                         data='test')
            mode = stat.S_IRUSR | stat.S_IWUSR
            mock_open.assert_called_with(file_name, flags, mode)
            mock_fdopen.assert_called_with(123, 'w')
            self.assertEqual(202, rv.status_code)
            m().write.assert_called_once_with('test')
            mock_subprocess.assert_any_call(
                "haproxy -c -L {peer} -f {config_file} -f {haproxy_ug}".format(
                    config_file=file_name,
                    haproxy_ug=consts.HAPROXY_USER_GROUP_CFG,
                    peer=(octavia_utils.
                          base64_sha1_string('amp_123').rstrip('='))).split(),
                stderr=subprocess.STDOUT, encoding='utf-8')
            mock_rename.assert_called_with(
                '/var/lib/octavia/123/haproxy.cfg.new',
                '/var/lib/octavia/123/haproxy.cfg')

        mock_subprocess.assert_any_call(
            ['systemctl', 'enable', 'haproxy-123.service'],
            stderr=subprocess.STDOUT,
            encoding='utf-8')

        # exception writing
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        m.side_effect = IOError()  # open crashes
        with mock.patch('os.open'), mock.patch.object(
                os, 'fdopen', m), mock.patch('distro.id') as mock_distro_id:
            mock_distro_id.return_value = distro
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                         '/loadbalancer/amp_123/123/haproxy',
                                         data='test')
            elif distro == consts.CENTOS:
                rv = self.centos_app.put('/' + api_server.VERSION +
                                         '/loadbalancer/amp_123/123/haproxy',
                                         data='test')
            self.assertEqual(500, rv.status_code)

        # check if files get created
        mock_exists.return_value = False
        init_path = consts.SYSTEMD_DIR + '/haproxy-123.service'

        m = self.useFixture(test_utils.OpenFixture(init_path)).mock_open
        # happy case upstart file exists
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen, mock.patch(
                'distro.id') as mock_distro_id:
            mock_open.return_value = 123
            mock_distro_id.return_value = distro

            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                         '/loadbalancer/amp_123/123/haproxy',
                                         data='test')
            elif distro == consts.CENTOS:
                rv = self.centos_app.put('/' + api_server.VERSION +
                                         '/loadbalancer/amp_123/123/haproxy',
                                         data='test')

            self.assertEqual(202, rv.status_code)
            mode = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP |
                    stat.S_IROTH)
            mock_open.assert_called_with(init_path, flags, mode)
            mock_fdopen.assert_called_with(123, 'w')
            handle = mock_fdopen()
            handle.write.assert_any_call('test')
            # skip the template stuff
            mock_makedirs.assert_called_with('/var/lib/octavia/123')

        # unhappy case haproxy check fails
        mock_exists.return_value = True
        mock_subprocess.side_effect = [subprocess.CalledProcessError(
            7, 'test', RANDOM_ERROR)]
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen, mock.patch(
                'distro.id') as mock_distro_id:
            mock_open.return_value = 123
            mock_distro_id.return_value = distro
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                         '/loadbalancer/amp_123/123/haproxy',
                                         data='test')
            elif distro == consts.CENTOS:
                rv = self.centos_app.put('/' + api_server.VERSION +
                                         '/loadbalancer/amp_123/123/haproxy',
                                         data='test')
            self.assertEqual(400, rv.status_code)
            self.assertEqual(
                {'message': 'Invalid request', 'details': 'random error'},
                jsonutils.loads(rv.data.decode('utf-8')))
            mode = stat.S_IRUSR | stat.S_IWUSR
            mock_open.assert_called_with(file_name, flags, mode)
            mock_fdopen.assert_called_with(123, 'w')
            handle = mock_fdopen()
            handle.write.assert_called_with('test')
            mock_subprocess.assert_called_with(
                "haproxy -c -L {peer} -f {config_file} -f {haproxy_ug}".format(
                    config_file=file_name,
                    haproxy_ug=consts.HAPROXY_USER_GROUP_CFG,
                    peer=(octavia_utils.
                          base64_sha1_string('amp_123').rstrip('='))).split(),
                stderr=subprocess.STDOUT, encoding='utf-8')
            mock_rename.assert_called_with(
                '/var/lib/octavia/123/haproxy.cfg.new',
                '/var/lib/octavia/123/haproxy.cfg.new-failed')

    def test_ubuntu_start(self):
        self._test_start(consts.UBUNTU)

    def test_centos_start(self):
        self._test_start(consts.CENTOS)

    @mock.patch('os.listdir')
    @mock.patch('os.path.exists')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'vrrp_check_script_update')
    @mock.patch('subprocess.check_output')
    def _test_start(self, distro, mock_subprocess, mock_vrrp, mock_exists,
                    mock_listdir):
        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                     '/loadbalancer/123/error')
        elif distro == consts.CENTOS:
            rv = self.centos_app.put('/' + api_server.VERSION +
                                     '/loadbalancer/123/error')
        self.assertEqual(400, rv.status_code)
        self.assertEqual(
            {'message': 'Invalid Request',
             'details': 'Unknown action: error', },
            jsonutils.loads(rv.data.decode('utf-8')))

        mock_exists.reset_mock()
        mock_exists.return_value = False
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                     '/loadbalancer/123/start')
        elif distro == consts.CENTOS:
            rv = self.centos_app.put('/' + api_server.VERSION +
                                     '/loadbalancer/123/start')
        self.assertEqual(404, rv.status_code)
        self.assertEqual(
            {'message': 'Loadbalancer Not Found',
             'details': 'No loadbalancer with UUID: 123'},
            jsonutils.loads(rv.data.decode('utf-8')))
        mock_exists.assert_called_with('/var/lib/octavia')

        mock_exists.return_value = True
        mock_listdir.return_value = ['123']
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                     '/loadbalancer/123/start')
        elif distro == consts.CENTOS:
            rv = self.centos_app.put('/' + api_server.VERSION +
                                     '/loadbalancer/123/start')
        self.assertEqual(202, rv.status_code)
        self.assertEqual(
            {'message': 'OK',
             'details': 'Configuration file is valid\nhaproxy daemon for'
                        ' 123 started'},
            jsonutils.loads(rv.data.decode('utf-8')))
        mock_subprocess.assert_called_with(
            ['systemctl', 'start', 'haproxy-123.service'],
            stderr=subprocess.STDOUT,
            encoding='utf-8')

        mock_exists.return_value = True
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            7, 'test', RANDOM_ERROR)
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                     '/loadbalancer/123/start')
        elif distro == consts.CENTOS:
            rv = self.centos_app.put('/' + api_server.VERSION +
                                     '/loadbalancer/123/start')
        self.assertEqual(500, rv.status_code)
        self.assertEqual(
            {
                'message': 'Error starting haproxy',
                'details': RANDOM_ERROR,
            }, jsonutils.loads(rv.data.decode('utf-8')))
        mock_subprocess.assert_called_with(
            ['systemctl', 'start', 'haproxy-123.service'],
            stderr=subprocess.STDOUT, encoding='utf-8')

    def test_ubuntu_reload(self):
        self._test_reload(consts.UBUNTU)

    def test_centos_reload(self):
        self._test_reload(consts.CENTOS)

    @mock.patch('os.listdir')
    @mock.patch('os.path.exists')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'vrrp_check_script_update')
    @mock.patch('octavia.amphorae.backends.agent.api_server.loadbalancer.'
                'Loadbalancer._check_haproxy_status')
    @mock.patch('subprocess.check_output')
    @mock.patch('octavia.amphorae.backends.utils.haproxy_query.HAProxyQuery')
    def _test_reload(self, distro, mock_haproxy_query, mock_subprocess,
                     mock_haproxy_status, mock_vrrp, mock_exists,
                     mock_listdir):

        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])

        # Process running so reload
        mock_exists.return_value = True
        mock_listdir.return_value = ['123']
        mock_haproxy_status.return_value = consts.ACTIVE
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                     '/loadbalancer/123/reload')
        elif distro == consts.CENTOS:
            rv = self.centos_app.put('/' + api_server.VERSION +
                                     '/loadbalancer/123/reload')
        self.assertEqual(202, rv.status_code)
        self.assertEqual(
            {'message': 'OK',
             'details': 'Listener 123 reloaded'},
            jsonutils.loads(rv.data.decode('utf-8')))
        mock_subprocess.assert_called_with(
            ['systemctl', 'reload', 'haproxy-123.service'],
            stderr=subprocess.STDOUT, encoding='utf-8')

        # Process not running so start
        mock_exists.return_value = True
        mock_haproxy_status.return_value = consts.OFFLINE
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                     '/loadbalancer/123/reload')
        elif distro == consts.CENTOS:
            rv = self.centos_app.put('/' + api_server.VERSION +
                                     '/loadbalancer/123/reload')
        self.assertEqual(202, rv.status_code)
        self.assertEqual(
            {'message': 'OK',
             'details': 'Configuration file is valid\nhaproxy daemon for'
                        ' 123 started'},
            jsonutils.loads(rv.data.decode('utf-8')))
        mock_subprocess.assert_called_with(
            ['systemctl', 'start', 'haproxy-123.service'],
            stderr=subprocess.STDOUT, encoding='utf-8')

    def test_ubuntu_info(self):
        self._test_info(consts.UBUNTU)

    def test_centos_info(self):
        self._test_info(consts.CENTOS)

    @mock.patch('octavia.amphorae.backends.agent.api_server.amphora_info.'
                'AmphoraInfo._get_extend_body_from_lvs_driver',
                return_value={})
    @mock.patch('socket.gethostname')
    @mock.patch('subprocess.check_output')
    def _test_info(self, distro, mock_subbprocess, mock_hostname,
                   mock_get_extend_body):
        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])
        mock_hostname.side_effect = ['test-host']
        mock_subbprocess.side_effect = ['9.9.99-9']

        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.get('/' + api_server.VERSION + '/info')
        elif distro == consts.CENTOS:
            rv = self.centos_app.get('/' + api_server.VERSION + '/info')

        self.assertEqual(200, rv.status_code)
        self.assertEqual(dict(
            api_version='1.0',
            haproxy_version='9.9.99-9',
            hostname='test-host'),
            jsonutils.loads(rv.data.decode('utf-8')))

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_backend_for_lb_object', return_value='HAPROXY')
    def test_delete_ubuntu_listener(self, mock_get_proto):
        self._test_delete_listener(consts.UBUNTU)

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_backend_for_lb_object', return_value='HAPROXY')
    def test_delete_centos_listener(self, mock_get_proto):
        self._test_delete_listener(consts.CENTOS)

    @mock.patch('os.listdir')
    @mock.patch('os.path.exists')
    @mock.patch('subprocess.check_output')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'vrrp_check_script_update')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.' +
                'get_haproxy_pid')
    @mock.patch('shutil.rmtree')
    @mock.patch('os.remove')
    def _test_delete_listener(self, distro,
                              mock_remove, mock_rmtree, mock_pid, mock_vrrp,
                              mock_check_output, mock_exists, mock_listdir):
        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])
        # no listener
        mock_exists.return_value = False
        mock_listdir.return_value = ['123']
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.delete('/' + api_server.VERSION +
                                        '/listeners/123')
        elif distro == consts.CENTOS:
            rv = self.centos_app.delete('/' + api_server.VERSION +
                                        '/listeners/123')
        self.assertEqual(200, rv.status_code)
        self.assertEqual(OK, jsonutils.loads(rv.data.decode('utf-8')))
        mock_exists.assert_called_once_with('/var/lib/octavia')

        # service is stopped + no upstart script + no vrrp
        mock_exists.side_effect = [True, True, False, False, False]
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.delete('/' + api_server.VERSION +
                                        '/listeners/123')
        elif distro == consts.CENTOS:
            rv = self.centos_app.delete('/' + api_server.VERSION +
                                        '/listeners/123')
        self.assertEqual(200, rv.status_code)
        self.assertEqual({'message': 'OK'},
                         jsonutils.loads(rv.data.decode('utf-8')))
        mock_rmtree.assert_called_with('/var/lib/octavia/123')

        mock_exists.assert_called_with(consts.SYSTEMD_DIR +
                                       '/haproxy-123.service')

        mock_exists.assert_any_call('/var/lib/octavia/123/123.pid')

        # service is stopped + no upstart script + vrrp
        mock_exists.side_effect = [True, True, False, True, False]
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.delete('/' + api_server.VERSION +
                                        '/listeners/123')
        elif distro == consts.CENTOS:
            rv = self.centos_app.delete('/' + api_server.VERSION +
                                        '/listeners/123')
        self.assertEqual(200, rv.status_code)
        self.assertEqual({'message': 'OK'},
                         jsonutils.loads(rv.data.decode('utf-8')))
        mock_rmtree.assert_called_with('/var/lib/octavia/123')

        mock_exists.assert_called_with(consts.SYSTEMD_DIR +
                                       '/haproxy-123.service')

        mock_exists.assert_any_call('/var/lib/octavia/123/123.pid')

        # service is stopped + upstart script + no vrrp
        mock_exists.side_effect = [True, True, False, False, True]
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.delete('/' + api_server.VERSION +
                                        '/listeners/123')
        elif distro == consts.CENTOS:
            rv = self.centos_app.delete('/' + api_server.VERSION +
                                        '/listeners/123')
        self.assertEqual(200, rv.status_code)
        self.assertEqual({'message': 'OK'},
                         jsonutils.loads(rv.data.decode('utf-8')))

        mock_remove.assert_called_with(consts.SYSTEMD_DIR +
                                       '/haproxy-123.service')

        # service is stopped + upstart script + vrrp
        mock_exists.side_effect = [True, True, False, True, True]
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.delete('/' + api_server.VERSION +
                                        '/listeners/123')
        elif distro == consts.CENTOS:
            rv = self.centos_app.delete('/' + api_server.VERSION +
                                        '/listeners/123')
        self.assertEqual(200, rv.status_code)
        self.assertEqual({'message': 'OK'},
                         jsonutils.loads(rv.data.decode('utf-8')))

        mock_remove.assert_called_with(consts.SYSTEMD_DIR +
                                       '/haproxy-123.service')

        # service is running + upstart script + no vrrp
        mock_exists.side_effect = [True, True, True, True, False, True]
        mock_pid.return_value = '456'
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.delete('/' + api_server.VERSION +
                                        '/listeners/123')
        elif distro == consts.CENTOS:
            rv = self.centos_app.delete('/' + api_server.VERSION +
                                        '/listeners/123')
        self.assertEqual(200, rv.status_code)
        self.assertEqual({'message': 'OK'},
                         jsonutils.loads(rv.data.decode('utf-8')))
        mock_pid.assert_called_once_with('123')
        mock_check_output.assert_any_call(
            ['systemctl', 'stop', 'haproxy-123.service'],
            stderr=subprocess.STDOUT, encoding='utf-8')

        mock_check_output.assert_any_call(
            ['systemctl', 'disable', 'haproxy-123.service'],
            stderr=subprocess.STDOUT, encoding='utf-8')

        # service is running + upstart script + vrrp
        mock_exists.side_effect = [True, True, True, True, True, True]
        mock_pid.return_value = '456'
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.delete('/' + api_server.VERSION +
                                        '/listeners/123')
        elif distro == consts.CENTOS:
            rv = self.centos_app.delete('/' + api_server.VERSION +
                                        '/listeners/123')
        self.assertEqual(200, rv.status_code)
        self.assertEqual({'message': 'OK'},
                         jsonutils.loads(rv.data.decode('utf-8')))
        mock_pid.assert_called_with('123')
        mock_check_output.assert_any_call(
            ['systemctl', 'stop', 'haproxy-123.service'],
            stderr=subprocess.STDOUT, encoding='utf-8')

        mock_check_output.assert_any_call(
            ['systemctl', 'disable', 'haproxy-123.service'],
            stderr=subprocess.STDOUT, encoding='utf-8')

        # service is running + stopping fails
        mock_exists.side_effect = [True, True, True, True]
        mock_check_output.side_effect = subprocess.CalledProcessError(
            7, 'test', RANDOM_ERROR)
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.delete('/' + api_server.VERSION +
                                        '/listeners/123')
        elif distro == consts.CENTOS:
            rv = self.centos_app.delete('/' + api_server.VERSION +
                                        '/listeners/123')
        self.assertEqual(500, rv.status_code)
        self.assertEqual(
            {'details': 'random error', 'message': 'Error stopping haproxy'},
            jsonutils.loads(rv.data.decode('utf-8')))
        # that's the last call before exception
        mock_exists.assert_called_with('/proc/456')

    def test_ubuntu_get_haproxy(self):
        self._test_get_haproxy(consts.UBUNTU)

    def test_centos_get_haproxy(self):
        self._test_get_haproxy(consts.CENTOS)

    @mock.patch('os.listdir')
    @mock.patch('os.path.exists')
    def _test_get_haproxy(self, distro, mock_exists, mock_listdir):

        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])

        CONTENT = "bibble\nbibble"
        mock_exists.side_effect = [False]
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.get('/' + api_server.VERSION +
                                     '/loadbalancer/123/haproxy')
        elif distro == consts.CENTOS:
            rv = self.centos_app.get('/' + api_server.VERSION +
                                     '/loadbalancer/123/haproxy')
        self.assertEqual(404, rv.status_code)

        mock_exists.side_effect = [True, True]

        path = util.config_path('123')
        self.useFixture(test_utils.OpenFixture(path, CONTENT))

        mock_listdir.return_value = ['123']
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.get('/' + api_server.VERSION +
                                     '/loadbalancer/123/haproxy')
        elif distro == consts.CENTOS:
            rv = self.centos_app.get('/' + api_server.VERSION +
                                     '/loadbalancer/123/haproxy')
        self.assertEqual(200, rv.status_code)
        self.assertEqual(octavia_utils.b(CONTENT), rv.data)
        self.assertEqual('text/plain; charset=utf-8',
                         rv.headers['Content-Type'].lower())

    def test_ubuntu_get_all_listeners(self):
        self._test_get_all_listeners(consts.UBUNTU)

    def test_get_all_listeners(self):
        self._test_get_all_listeners(consts.CENTOS)

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_loadbalancers')
    @mock.patch('octavia.amphorae.backends.agent.api_server.loadbalancer.'
                'Loadbalancer._check_haproxy_status')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'parse_haproxy_file')
    def _test_get_all_listeners(self, distro, mock_parse, mock_status,
                                mock_lbs):
        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])

        # no listeners
        mock_lbs.side_effect = [[]]
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.get('/' + api_server.VERSION + '/listeners')
        elif distro == consts.CENTOS:
            rv = self.centos_app.get('/' + api_server.VERSION + '/listeners')

        self.assertEqual(200, rv.status_code)
        self.assertFalse(jsonutils.loads(rv.data.decode('utf-8')))

        # one listener ACTIVE
        mock_lbs.side_effect = [['123']]
        mock_parse.side_effect = [['fake_socket', {'123': {'mode': 'test'}}]]
        mock_status.side_effect = [consts.ACTIVE]
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.get('/' + api_server.VERSION + '/listeners')
        elif distro == consts.CENTOS:
            rv = self.centos_app.get('/' + api_server.VERSION + '/listeners')

        self.assertEqual(200, rv.status_code)
        self.assertEqual(
            [{'status': consts.ACTIVE, 'type': 'test', 'uuid': '123'}],
            jsonutils.loads(rv.data.decode('utf-8')))

        # two listeners, two modes
        mock_lbs.side_effect = [['123', '456']]
        mock_parse.side_effect = [['fake_socket', {'123': {'mode': 'test'}}],
                                  ['fake_socket', {'456': {'mode': 'http'}}]]
        mock_status.return_value = consts.ACTIVE
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.get('/' + api_server.VERSION + '/listeners')
        elif distro == consts.CENTOS:
            rv = self.centos_app.get('/' + api_server.VERSION + '/listeners')

        self.assertEqual(200, rv.status_code)
        self.assertEqual(
            [{'status': consts.ACTIVE, 'type': 'test', 'uuid': '123'},
             {'status': consts.ACTIVE, 'type': 'http', 'uuid': '456'}],
            jsonutils.loads(rv.data.decode('utf-8')))

    def test_ubuntu_delete_cert(self):
        self._test_delete_cert(consts.UBUNTU)

    def test_centos_delete_cert(self):
        self._test_delete_cert(consts.CENTOS)

    @mock.patch('os.path.exists')
    @mock.patch('os.remove')
    def _test_delete_cert(self, distro, mock_remove, mock_exists):
        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])
        mock_exists.side_effect = [False]
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.delete(
                '/' + api_server.VERSION +
                '/loadbalancer/123/certificates/test.pem')
        elif distro == consts.CENTOS:
            rv = self.centos_app.delete(
                '/' + api_server.VERSION +
                '/loadbalancer/123/certificates/test.pem')
        self.assertEqual(200, rv.status_code)
        self.assertEqual(OK, jsonutils.loads(rv.data.decode('utf-8')))
        mock_exists.assert_called_once_with(
            '/var/lib/octavia/certs/123/test.pem')

        # wrong file name
        mock_exists.side_effect = [True]
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.delete(
                '/' + api_server.VERSION +
                '/loadbalancer/123/certificates/test.bla')
        elif distro == consts.CENTOS:
            rv = self.centos_app.delete(
                '/' + api_server.VERSION +
                '/loadbalancer/123/certificates/test.bla')
        self.assertEqual(400, rv.status_code)

        mock_exists.side_effect = [True]
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.delete(
                '/' + api_server.VERSION +
                '/loadbalancer/123/certificates/test.pem')
        elif distro == consts.CENTOS:
            rv = self.centos_app.delete(
                '/' + api_server.VERSION +
                '/loadbalancer/123/certificates/test.pem')
        self.assertEqual(200, rv.status_code)
        self.assertEqual(OK, jsonutils.loads(rv.data.decode('utf-8')))
        mock_remove.assert_called_once_with(
            '/var/lib/octavia/certs/123/test.pem')

    def test_ubuntu_get_certificate_md5(self):
        self._test_get_certificate_md5(consts.UBUNTU)

    def test_centos_get_certificate_md5(self):
        self._test_get_certificate_md5(consts.CENTOS)

    @mock.patch('os.path.exists')
    def _test_get_certificate_md5(self, distro, mock_exists):

        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])
        CONTENT = "TestTest"

        mock_exists.side_effect = [False]

        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.get('/' + api_server.VERSION +
                                     '/loadbalancer/123/certificates/test.pem')
        elif distro == consts.CENTOS:
            rv = self.centos_app.get('/' + api_server.VERSION +
                                     '/loadbalancer/123/certificates/test.pem')
        self.assertEqual(404, rv.status_code)
        self.assertEqual(dict(
            details='No certificate with filename: test.pem',
            message='Certificate Not Found'),
            jsonutils.loads(rv.data.decode('utf-8')))
        mock_exists.assert_called_with('/var/lib/octavia/certs/123/test.pem')

        # wrong file name
        mock_exists.side_effect = [True]
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                     '/loadbalancer/123/certificates/test.bla',
                                     data='TestTest')
        elif distro == consts.CENTOS:
            rv = self.centos_app.put('/' + api_server.VERSION +
                                     '/loadbalancer/123/certificates/test.bla',
                                     data='TestTest')
        self.assertEqual(400, rv.status_code)

        mock_exists.return_value = True
        mock_exists.side_effect = None
        if distro == consts.UBUNTU:
            path = self.ubuntu_test_server._loadbalancer._cert_file_path(
                '123', 'test.pem')
        elif distro == consts.CENTOS:
            path = self.centos_test_server._loadbalancer._cert_file_path(
                '123', 'test.pem')
        self.useFixture(test_utils.OpenFixture(path, CONTENT))
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.get('/' + api_server.VERSION +
                                     '/loadbalancer/123/certificates/test.pem')
        elif distro == consts.CENTOS:
            rv = self.centos_app.get('/' + api_server.VERSION +
                                     '/loadbalancer/123/certificates/test.pem')
        self.assertEqual(200, rv.status_code)
        self.assertEqual(
            dict(md5sum=hashlib.md5(octavia_utils.b(CONTENT),
                                    usedforsecurity=False).hexdigest()),
            jsonutils.loads(rv.data.decode('utf-8')))

    def test_ubuntu_upload_certificate_md5(self):
        self._test_upload_certificate_md5(consts.UBUNTU)

    def test_centos_upload_certificate_md5(self):
        self._test_upload_certificate_md5(consts.CENTOS)

    @mock.patch('os.path.exists')
    @mock.patch('os.makedirs')
    def _test_upload_certificate_md5(self, distro, mock_makedir, mock_exists):

        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])
        # wrong file name
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                     '/loadbalancer/123/certificates/test.bla',
                                     data='TestTest')
        elif distro == consts.CENTOS:
            rv = self.centos_app.put('/' + api_server.VERSION +
                                     '/loadbalancer/123/certificates/test.bla',
                                     data='TestTest')
        self.assertEqual(400, rv.status_code)

        mock_exists.return_value = True
        if distro == consts.UBUNTU:
            path = self.ubuntu_test_server._loadbalancer._cert_file_path(
                '123', 'test.pem')
        elif distro == consts.CENTOS:
            path = self.centos_test_server._loadbalancer._cert_file_path(
                '123', 'test.pem')

        m = self.useFixture(test_utils.OpenFixture(path)).mock_open
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):

            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                         '/loadbalancer/123/certificates/'
                                         'test.pem', data='TestTest')
            elif distro == consts.CENTOS:
                rv = self.centos_app.put('/' + api_server.VERSION +
                                         '/loadbalancer/123/certificates/'
                                         'test.pem', data='TestTest')
            self.assertEqual(200, rv.status_code)
            self.assertEqual(OK, jsonutils.loads(rv.data.decode('utf-8')))
            handle = m()
            handle.write.assert_called_once_with(octavia_utils.b('TestTest'))

        mock_exists.return_value = False
        m = self.useFixture(test_utils.OpenFixture(path)).mock_open

        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                         '/loadbalancer/123/certificates/'
                                         'test.pem', data='TestTest')
            elif distro == consts.CENTOS:
                rv = self.centos_app.put('/' + api_server.VERSION +
                                         '/loadbalancer/123/certificates/'
                                         'test.pem', data='TestTest')
            self.assertEqual(200, rv.status_code)
            self.assertEqual(OK, jsonutils.loads(rv.data.decode('utf-8')))
            handle = m()
            handle.write.assert_called_once_with(octavia_utils.b('TestTest'))
            mock_makedir.assert_called_once_with('/var/lib/octavia/certs/123')

    def test_ubuntu_upload_server_certificate(self):
        self._test_upload_server_certificate(consts.UBUNTU)

    def test_centos_upload_server_certificate(self):
        self._test_upload_server_certificate(consts.CENTOS)

    def _test_upload_server_certificate(self, distro):
        certificate_update.BUFFER = 5  # test the while loop
        path = '/etc/octavia/certs/server.pem'
        m = self.useFixture(test_utils.OpenFixture(path)).mock_open
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                         '/certificate', data='TestTest')
            elif distro == consts.CENTOS:
                rv = self.centos_app.put('/' + api_server.VERSION +
                                         '/certificate', data='TestTest')
            self.assertEqual(202, rv.status_code)
            self.assertEqual(OK, jsonutils.loads(rv.data.decode('utf-8')))
            handle = m()
            handle.write.assert_any_call(octavia_utils.b('TestT'))
            handle.write.assert_any_call(octavia_utils.b('est'))

    def _check_centos_files(self, handle):
        handle.write.assert_any_call(
            '\n# Generated by Octavia agent\n'
            '#!/bin/bash\n'
            'if [[ "$1" != "lo" ]]\n'
            '  then\n'
            '  /usr/local/bin/lvs-masquerade.sh add ipv4 $1\n'
            '  /usr/local/bin/lvs-masquerade.sh add ipv6 $1\n'
            'fi')
        handle.write.assert_any_call(
            '\n# Generated by Octavia agent\n'
            '#!/bin/bash\n'
            'if [[ "$1" != "lo" ]]\n'
            '  then\n'
            '  /usr/local/bin/lvs-masquerade.sh delete ipv4 $1\n'
            '  /usr/local/bin/lvs-masquerade.sh delete ipv6 $1\n'
            'fi')

    def test_ubuntu_plug_network(self):
        self._test_plug_network(consts.UBUNTU)

    def test_centos_plug_network(self):
        self._test_plug_network(consts.CENTOS)

    @mock.patch('os.chmod')
    @mock.patch('pyroute2.IPRoute', create=True)
    @mock.patch('pyroute2.NetNS', create=True)
    @mock.patch('subprocess.check_output')
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'plug.Plug._netns_interface_exists')
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'plug.Plug._netns_interface_by_mac')
    @mock.patch('os.path.isfile')
    def _test_plug_network(self, distro, mock_isfile, mock_int_by_mac,
                           mock_int_exists, mock_check_output, mock_netns,
                           mock_pyroute2, mock_os_chmod):
        mock_ipr = mock.MagicMock()
        mock_ipr_instance = mock.MagicMock()
        mock_ipr_instance.link_lookup.side_effect = [
            [], [], [33], [33], [33], [33], [33], [33], [33], [33]]
        mock_ipr_instance.get_links.return_value = ({
            'attrs': [('IFLA_IFNAME', FAKE_INTERFACE)]},)
        mock_ipr.__enter__.return_value = mock_ipr_instance
        mock_pyroute2.return_value = mock_ipr

        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])
        port_info = {'mac_address': '123'}
        test_int_num = random.randint(0, 9999)

        mock_int_exists.return_value = False
        netns_handle = mock_netns.return_value.__enter__.return_value
        netns_handle.get_links.return_value = [
            {'attrs': [['IFLA_IFNAME', f'eth{idx}']]}
            for idx in range(test_int_num)]
        mock_isfile.return_value = True

        mock_check_output.return_value = "1\n2\n3\n"

        test_int_num = str(test_int_num)

        # No interface at all
        file_name = '/sys/bus/pci/rescan'
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/network",
                                          content_type='application/json',
                                          data=jsonutils.dumps(port_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/network",
                                          content_type='application/json',
                                          data=jsonutils.dumps(port_info))
            mock_open.assert_called_with(file_name, os.O_WRONLY)
            mock_fdopen.assert_called_with(123, 'w')
        m().write.assert_called_once_with('1')
        self.assertEqual(404, rv.status_code)
        self.assertEqual(dict(details="No suitable network interface found"),
                         jsonutils.loads(rv.data.decode('utf-8')))

        # No interface down
        m().reset_mock()
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen, mock.patch(
                    'octavia.amphorae.backends.utils.interface_file.'
                    'InterfaceFile.dump') as mock_dump:
            mock_open.return_value = 123
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/network",
                                          content_type='application/json',
                                          data=jsonutils.dumps(port_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/network",
                                          content_type='application/json',
                                          data=jsonutils.dumps(port_info))
            mock_open.assert_called_with(file_name, os.O_WRONLY)
            mock_fdopen.assert_called_with(123, 'w')
        m().write.assert_called_once_with('1')
        self.assertEqual(404, rv.status_code)
        self.assertEqual(dict(details="No suitable network interface found"),
                         jsonutils.loads(rv.data.decode('utf-8')))

        # One Interface down, Happy Path
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

        file_name = f'/etc/octavia/interfaces/eth{test_int_num}.json'
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC

        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen, mock.patch(
                    'octavia.amphorae.backends.utils.interface_file.'
                    'InterfaceFile.dump') as mock_dump:
            mock_open.return_value = 123
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/network",
                                          content_type='application/json',
                                          data=jsonutils.dumps(port_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/network",
                                          content_type='application/json',
                                          data=jsonutils.dumps(port_info))
            self.assertEqual(202, rv.status_code)

            mock_open.assert_any_call(file_name, flags, mode)
            mock_fdopen.assert_any_call(123, 'w')

            plug_inf_file = '/var/lib/octavia/plugged_interfaces'
            flags = os.O_RDWR | os.O_CREAT
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_any_call(plug_inf_file, flags, mode)
            mock_fdopen.assert_any_call(123, 'r+')

            expected_dict = {
                consts.NAME: f"eth{test_int_num}",
                consts.ADDRESSES: [
                    {
                        consts.DHCP: True,
                        consts.IPV6AUTO: True
                    }
                ],
                consts.ROUTES: [
                ],
                consts.RULES: [
                ],
                consts.SCRIPTS: {
                    consts.IFACE_UP: [{
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh add ipv4 "
                            "eth{}".format(test_int_num))
                    }, {
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh add ipv6 "
                            "eth{}".format(test_int_num))
                    }],
                    consts.IFACE_DOWN: [{
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh delete ipv4 "
                            "eth{}".format(test_int_num))
                    }, {
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh delete ipv6 "
                            "eth{}".format(test_int_num))
                    }]
                }
            }

            mock_dump.assert_called_once()
            args = mock_dump.mock_calls[0][1]
            test_utils.assert_interface_files_equal(
                self, args[0], expected_dict)

            mock_check_output.assert_called_with(
                ['ip', 'netns', 'exec', consts.AMPHORA_NAMESPACE,
                 'amphora-interface', 'up', 'eth' + test_int_num],
                stderr=subprocess.STDOUT, encoding='utf-8')

        # fixed IPs happy path
        port_info = {'mac_address': '123', 'mtu': 1450, 'fixed_ips': [
            {'ip_address': '10.0.0.5', 'subnet_cidr': '10.0.0.0/24'}]}

        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

        file_name = f'/etc/octavia/interfaces/eth{test_int_num}.json'
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC

        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen, mock.patch(
                    'octavia.amphorae.backends.utils.interface_file.'
                    'InterfaceFile.dump') as mock_dump:
            mock_open.return_value = 123
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/network",
                                          content_type='application/json',
                                          data=jsonutils.dumps(port_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/network",
                                          content_type='application/json',
                                          data=jsonutils.dumps(port_info))
            self.assertEqual(202, rv.status_code)

            mock_open.assert_any_call(file_name, flags, mode)
            mock_fdopen.assert_any_call(123, 'w')

            plug_inf_file = '/var/lib/octavia/plugged_interfaces'
            flags = os.O_RDWR | os.O_CREAT
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_any_call(plug_inf_file, flags, mode)
            mock_fdopen.assert_any_call(123, 'r+')

            expected_dict = {
                consts.NAME: f"eth{test_int_num}",
                consts.MTU: 1450,
                consts.ADDRESSES: [
                    {consts.ADDRESS: '10.0.0.5', consts.PREFIXLEN: 24}
                ],
                consts.ROUTES: [],
                consts.RULES: [],
                consts.SCRIPTS: {
                    consts.IFACE_UP: [
                        {consts.COMMAND:
                         '/usr/local/bin/lvs-masquerade.sh add ipv4 '
                         'eth{}'.format(test_int_num)}],
                    consts.IFACE_DOWN: [
                        {consts.COMMAND:
                         '/usr/local/bin/lvs-masquerade.sh delete ipv4 '
                         'eth{}'.format(test_int_num)}]
                }
            }

            mock_dump.assert_called_once()
            args = mock_dump.mock_calls[0][1]
            test_utils.assert_interface_files_equal(
                self, args[0], expected_dict)

            mock_check_output.assert_called_with(
                ['ip', 'netns', 'exec', consts.AMPHORA_NAMESPACE,
                 'amphora-interface', 'up', 'eth' + test_int_num],
                stderr=subprocess.STDOUT, encoding='utf-8')

        # fixed IPs happy path IPv6
        port_info = {'mac_address': '123', 'mtu': 1450, 'fixed_ips': [
            {'ip_address': '2001:db8::2', 'subnet_cidr': '2001:db8::/32'}]}

        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

        file_name = f'/etc/octavia/interfaces/eth{test_int_num}.json'
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC

        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen, mock.patch(
                    'octavia.amphorae.backends.utils.interface_file.'
                    'InterfaceFile.dump') as mock_dump:
            mock_open.return_value = 123
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/network",
                                          content_type='application/json',
                                          data=jsonutils.dumps(port_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/network",
                                          content_type='application/json',
                                          data=jsonutils.dumps(port_info))
            self.assertEqual(202, rv.status_code)

            mock_open.assert_any_call(file_name, flags, mode)
            mock_fdopen.assert_any_call(123, 'w')

            plug_inf_file = '/var/lib/octavia/plugged_interfaces'
            flags = os.O_RDWR | os.O_CREAT
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_any_call(plug_inf_file, flags, mode)
            mock_fdopen.assert_any_call(123, 'r+')

            expected_dict = {
                consts.NAME: f"eth{test_int_num}",
                consts.MTU: 1450,
                consts.ADDRESSES: [
                    {consts.ADDRESS: '2001:0db8::2',
                     consts.PREFIXLEN: 32}],
                consts.ROUTES: [],
                consts.RULES: [],
                consts.SCRIPTS: {
                    consts.IFACE_UP: [
                        {consts.COMMAND:
                         '/usr/local/bin/lvs-masquerade.sh add ipv6 '
                         'eth{}'.format(test_int_num)}],
                    consts.IFACE_DOWN: [
                        {consts.COMMAND:
                         '/usr/local/bin/lvs-masquerade.sh delete ipv6 '
                         'eth{}'.format(test_int_num)}]
                }
            }

            mock_dump.assert_called_once()
            args = mock_dump.mock_calls[0][1]
            test_utils.assert_interface_files_equal(
                self, args[0], expected_dict)

            mock_check_output.assert_called_with(
                ['ip', 'netns', 'exec', consts.AMPHORA_NAMESPACE,
                 'amphora-interface', 'up', 'eth' + test_int_num],
                stderr=subprocess.STDOUT, encoding='utf-8')

        # fixed IPs, bogus IP
        port_info = {'mac_address': '123', 'fixed_ips': [
            {'ip_address': '10005', 'subnet_cidr': '10.0.0.0/24'}]}

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        file_name = f'/etc/octavia/interfaces/eth{test_int_num}.json'
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/network",
                                          content_type='application/json',
                                          data=jsonutils.dumps(port_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/network",
                                          content_type='application/json',
                                          data=jsonutils.dumps(port_info))
            self.assertEqual(400, rv.status_code)

        # same as above but ifup fails
        port_info = {'mac_address': '123', 'fixed_ips': [
            {'ip_address': '10.0.0.5', 'subnet_cidr': '10.0.0.0/24'}]}
        mock_check_output.side_effect = [
            subprocess.CalledProcessError(7, 'test', RANDOM_ERROR),
            subprocess.CalledProcessError(7, 'test', RANDOM_ERROR)
        ]

        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/network",
                                          content_type='application/json',
                                          data=jsonutils.dumps(port_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/network",
                                          content_type='application/json',
                                          data=jsonutils.dumps(port_info))
            self.assertEqual(500, rv.status_code)
            self.assertEqual(
                {'details': RANDOM_ERROR,
                 'message': 'Error plugging network'},
                jsonutils.loads(rv.data.decode('utf-8')))

        # Bad port_info tests
        port_info = 'Bad data'
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                      "/plug/network",
                                      content_type='application/json',
                                      data=jsonutils.dumps(port_info))
        elif distro == consts.CENTOS:
            rv = self.centos_app.post('/' + api_server.VERSION +
                                      "/plug/network",
                                      content_type='application/json',
                                      data=jsonutils.dumps(port_info))
        self.assertEqual(400, rv.status_code)

        port_info = {'fixed_ips': [{'ip_address': '10.0.0.5',
                                    'subnet_cidr': '10.0.0.0/24'}]}
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                      "/plug/network",
                                      content_type='application/json',
                                      data=jsonutils.dumps(port_info))
        elif distro == consts.CENTOS:
            rv = self.centos_app.post('/' + api_server.VERSION +
                                      "/plug/network",
                                      content_type='application/json',
                                      data=jsonutils.dumps(port_info))
        self.assertEqual(400, rv.status_code)

    def test_ubuntu_plug_network_host_routes(self):
        self._test_plug_network_host_routes(consts.UBUNTU)

    def test_centos_plug_network_host_routes(self):
        self._test_plug_network_host_routes(consts.CENTOS)

    @mock.patch('os.chmod')
    @mock.patch('pyroute2.IPRoute', create=True)
    @mock.patch('pyroute2.NetNS', create=True)
    @mock.patch('subprocess.check_output')
    def _test_plug_network_host_routes(self, distro, mock_check_output,
                                       mock_netns, mock_pyroute2,
                                       mock_os_chmod):
        mock_ipr = mock.MagicMock()
        mock_ipr_instance = mock.MagicMock()
        mock_ipr_instance.link_lookup.return_value = [33]
        mock_ipr_instance.get_links.return_value = ({
            'attrs': [('IFLA_IFNAME', FAKE_INTERFACE)]},)
        mock_ipr.__enter__.return_value = mock_ipr_instance
        mock_pyroute2.return_value = mock_ipr

        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])

        SUBNET_CIDR = '192.0.2.0/24'
        PREFIXLEN = 24
        IP = '192.0.1.5'
        MAC = '123'
        DEST1 = '198.51.100.0/24'
        DEST2 = '203.0.113.1/32'
        NEXTHOP = '192.0.2.1'

        netns_handle = mock_netns.return_value.__enter__.return_value
        netns_handle.get_links.return_value = [{
            'attrs': [['IFLA_IFNAME', 'eth2']]}]

        port_info = {'mac_address': MAC, 'mtu': 1450, 'fixed_ips': [
            {'ip_address': IP, 'subnet_cidr': SUBNET_CIDR,
             'host_routes': [{'destination': DEST1, 'nexthop': NEXTHOP},
                             {'destination': DEST2, 'nexthop': NEXTHOP}]}]}

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        file_name = '/etc/octavia/interfaces/eth3.json'

        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen, mock.patch(
                    'octavia.amphorae.backends.utils.interface_file.'
                    'InterfaceFile.dump') as mock_dump:
            mock_open.return_value = 123
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/network",
                                          content_type='application/json',
                                          data=jsonutils.dumps(port_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/network",
                                          content_type='application/json',
                                          data=jsonutils.dumps(port_info))
            self.assertEqual(202, rv.status_code)

            mock_open.assert_any_call(file_name, flags, mode)
            mock_fdopen.assert_any_call(123, 'w')

            plug_inf_file = '/var/lib/octavia/plugged_interfaces'
            flags = os.O_RDWR | os.O_CREAT
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_any_call(plug_inf_file, flags, mode)
            mock_fdopen.assert_any_call(123, 'r+')

            expected_dict = {
                consts.NAME: 'eth3',
                consts.MTU: 1450,
                consts.ADDRESSES: [
                    {
                        consts.ADDRESS: IP,
                        consts.PREFIXLEN: PREFIXLEN
                    }
                ],
                consts.ROUTES: [
                    {
                        consts.DST: DEST1,
                        consts.GATEWAY: NEXTHOP
                    }, {
                        consts.DST: DEST2,
                        consts.GATEWAY: NEXTHOP
                    }
                ],
                consts.RULES: [
                ],
                consts.SCRIPTS: {
                    consts.IFACE_UP: [{
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh add ipv4 eth3")
                    }],
                    consts.IFACE_DOWN: [{
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh delete ipv4 "
                            "eth3")
                    }]
                }
            }

            mock_dump.assert_called_once()
            args = mock_dump.mock_calls[0][1]
            test_utils.assert_interface_files_equal(
                self, args[0], expected_dict)

            mock_check_output.assert_called_with(
                ['ip', 'netns', 'exec', consts.AMPHORA_NAMESPACE,
                 'amphora-interface', 'up', 'eth3'], stderr=subprocess.STDOUT,
                encoding='utf-8')

    def test_ubuntu_plug_VIP4(self):
        self._test_plug_VIP4(consts.UBUNTU)

    def test_centos_plug_VIP4(self):
        self._test_plug_VIP4(consts.CENTOS)

    @mock.patch('os.chmod')
    @mock.patch('shutil.copy2')
    @mock.patch('pyroute2.NSPopen', create=True)
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'plug.Plug._netns_interface_exists')
    @mock.patch('pyroute2.IPRoute', create=True)
    @mock.patch('pyroute2.NetNS', create=True)
    @mock.patch('subprocess.check_output')
    @mock.patch('shutil.copytree')
    @mock.patch('os.makedirs')
    @mock.patch('os.path.isfile')
    def _test_plug_VIP4(self, distro, mock_isfile, mock_makedirs,
                        mock_copytree, mock_check_output, mock_netns,
                        mock_pyroute2, mock_int_exists,
                        mock_nspopen, mock_copy2, mock_os_chmod):
        mock_ipr = mock.MagicMock()
        mock_ipr_instance = mock.MagicMock()
        mock_ipr_instance.link_lookup.side_effect = [[], [], [33], [33], [33],
                                                     [33], [33], [33]]
        mock_ipr_instance.get_links.return_value = ({
            'attrs': [('IFLA_IFNAME', FAKE_INTERFACE)]},)
        mock_ipr.__enter__.return_value = mock_ipr_instance
        mock_pyroute2.return_value = mock_ipr

        mock_isfile.return_value = True

        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])
        subnet_info = {
            'subnet_cidr': '203.0.113.0/24',
            'gateway': '203.0.113.1',
            'mac_address': '123'
        }

        # malformed ip
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                      '/plug/vip/error',
                                      data=jsonutils.dumps(subnet_info),
                                      content_type='application/json')
        elif distro == consts.CENTOS:
            rv = self.centos_app.post('/' + api_server.VERSION +
                                      '/plug/vip/error',
                                      data=jsonutils.dumps(subnet_info),
                                      content_type='application/json')
        self.assertEqual(400, rv.status_code)

        # No subnet info
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                      '/plug/vip/error')
        elif distro == consts.CENTOS:
            rv = self.centos_app.post('/' + api_server.VERSION +
                                      '/plug/vip/error')

        self.assertEqual(400, rv.status_code)

        # Interface already plugged
        mock_int_exists.return_value = True
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                      "/plug/vip/203.0.113.2",
                                      content_type='application/json',
                                      data=jsonutils.dumps(subnet_info))
        elif distro == consts.CENTOS:
            rv = self.centos_app.post('/' + api_server.VERSION +
                                      "/plug/vip/203.0.113.2",
                                      content_type='application/json',
                                      data=jsonutils.dumps(subnet_info))
        self.assertEqual(409, rv.status_code)
        self.assertEqual(dict(message="Interface already exists"),
                         jsonutils.loads(rv.data.decode('utf-8')))
        mock_int_exists.return_value = False

        # No interface at all
        file_name = '/sys/bus/pci/rescan'
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123

            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/vip/203.0.113.2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(subnet_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/vip/203.0.113.2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(subnet_info))
            mock_open.assert_called_with(file_name, os.O_WRONLY)
            mock_fdopen.assert_called_with(123, 'w')
        m().write.assert_called_once_with('1')
        self.assertEqual(404, rv.status_code)
        self.assertEqual(dict(details="No suitable network interface found"),
                         jsonutils.loads(rv.data.decode('utf-8')))

        # Two interfaces down
        m().reset_mock()
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123

            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/vip/203.0.113.2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(subnet_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/vip/203.0.113.2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(subnet_info))
            mock_open.assert_called_with(file_name, os.O_WRONLY)
            mock_fdopen.assert_called_with(123, 'w')
        m().write.assert_called_once_with('1')
        self.assertEqual(404, rv.status_code)
        self.assertEqual(dict(details="No suitable network interface found"),
                         jsonutils.loads(rv.data.decode('utf-8')))

        # Happy Path IPv4, with VRRP_IP and host route
        full_subnet_info = {
            'subnet_cidr': '203.0.113.0/24',
            'gateway': '203.0.113.1',
            'mac_address': '123',
            'vrrp_ip': '203.0.113.4',
            'mtu': 1450,
            'host_routes': [{'destination': '203.0.114.0/24',
                             'nexthop': '203.0.113.5'},
                            {'destination': '203.0.115.1/32',
                             'nexthop': '203.0.113.5'}]
        }

        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

        file_name = ('/etc/octavia/interfaces/{netns_int}.json'.format(
            netns_int=consts.NETNS_PRIMARY_INTERFACE))
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC

        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open

        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen, mock.patch(
                    'octavia.amphorae.backends.utils.interface_file.'
                    'InterfaceFile.dump') as mock_dump:
            mock_open.return_value = 123
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/vip/203.0.113.2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(
                                              full_subnet_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/vip/203.0.113.2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(
                                              full_subnet_info))
            self.assertEqual(202, rv.status_code)
            mock_open.assert_any_call(file_name, flags, mode)
            mock_fdopen.assert_any_call(123, 'w')

            plug_inf_file = '/var/lib/octavia/plugged_interfaces'
            flags = os.O_RDWR | os.O_CREAT
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_any_call(plug_inf_file, flags, mode)
            mock_fdopen.assert_any_call(123, 'r+')

            expected_dict = {
                consts.NAME: consts.NETNS_PRIMARY_INTERFACE,
                consts.MTU: 1450,
                consts.ADDRESSES: [
                    {
                        consts.ADDRESS: "203.0.113.4",
                        consts.PREFIXLEN: 24
                    }, {
                        consts.ADDRESS: "203.0.113.2",
                        consts.PREFIXLEN: 32
                    }
                ],
                consts.ROUTES: [
                    {
                        consts.DST: '0.0.0.0/0',
                        consts.GATEWAY: '203.0.113.1',
                        consts.FLAGS: [consts.ONLINK]
                    }, {
                        consts.DST: '0.0.0.0/0',
                        consts.GATEWAY: '203.0.113.1',
                        consts.TABLE: 1,
                        consts.FLAGS: [consts.ONLINK]
                    }, {
                        consts.DST: '203.0.113.0/24',
                        consts.SCOPE: 'link'
                    }, {
                        consts.DST: '203.0.113.0/24',
                        consts.PREFSRC: '203.0.113.2',
                        consts.SCOPE: 'link',
                        consts.TABLE: 1
                    }, {
                        consts.DST: '203.0.114.0/24',
                        consts.GATEWAY: '203.0.113.5'
                    }, {
                        consts.DST: '203.0.115.1/32',
                        consts.GATEWAY: '203.0.113.5'
                    }, {
                        consts.DST: '203.0.114.0/24',
                        consts.GATEWAY: '203.0.113.5',
                        consts.TABLE: 1
                    }, {
                        consts.DST: '203.0.115.1/32',
                        consts.GATEWAY: '203.0.113.5',
                        consts.TABLE: 1
                    }
                ],
                consts.RULES: [
                    {
                        consts.SRC: '203.0.113.2',
                        consts.SRC_LEN: 32,
                        consts.TABLE: 1
                    }
                ],
                consts.SCRIPTS: {
                    consts.IFACE_UP: [{
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh add ipv4 "
                            "{}".format(consts.NETNS_PRIMARY_INTERFACE))
                    }],
                    consts.IFACE_DOWN: [{
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh delete ipv4 "
                            "{}".format(consts.NETNS_PRIMARY_INTERFACE))
                    }]
                }
            }

            mock_dump.assert_called_once()
            args = mock_dump.mock_calls[0][1]
            test_utils.assert_interface_files_equal(
                self, args[0], expected_dict)

            mock_check_output.assert_called_with(
                ['ip', 'netns', 'exec', consts.AMPHORA_NAMESPACE,
                 'amphora-interface', 'up',
                 consts.NETNS_PRIMARY_INTERFACE], stderr=subprocess.STDOUT,
                encoding='utf-8')

        # One Interface down, Happy Path IPv4
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

        file_name = ('/etc/octavia/interfaces/{}.json'.format(
            consts.NETNS_PRIMARY_INTERFACE))
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC

        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open

        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen, mock.patch(
                    'octavia.amphorae.backends.utils.interface_file.'
                    'InterfaceFile.dump') as mock_dump:
            mock_open.return_value = 123
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/vip/203.0.113.2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(subnet_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/vip/203.0.113.2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(subnet_info))
            self.assertEqual(202, rv.status_code)
            mock_open.assert_any_call(file_name, flags, mode)
            mock_fdopen.assert_any_call(123, 'w')

            plug_inf_file = '/var/lib/octavia/plugged_interfaces'
            flags = os.O_RDWR | os.O_CREAT
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_any_call(plug_inf_file, flags, mode)
            mock_fdopen.assert_any_call(123, 'r+')

            expected_dict = {
                consts.NAME: consts.NETNS_PRIMARY_INTERFACE,
                consts.ADDRESSES: [
                    {
                        consts.DHCP: True
                    }, {
                        consts.ADDRESS: "203.0.113.2",
                        consts.PREFIXLEN: 32
                    }
                ],
                consts.ROUTES: [
                    {
                        consts.DST: '0.0.0.0/0',
                        consts.GATEWAY: '203.0.113.1',
                        consts.FLAGS: [consts.ONLINK]
                    }, {
                        consts.DST: '0.0.0.0/0',
                        consts.GATEWAY: '203.0.113.1',
                        consts.FLAGS: [consts.ONLINK],
                        consts.TABLE: 1
                    }, {
                        consts.DST: '203.0.113.0/24',
                        consts.SCOPE: 'link'
                    }, {
                        consts.DST: '203.0.113.0/24',
                        consts.PREFSRC: '203.0.113.2',
                        consts.SCOPE: 'link',
                        consts.TABLE: 1
                    }
                ],
                consts.RULES: [
                    {
                        consts.SRC: '203.0.113.2',
                        consts.SRC_LEN: 32,
                        consts.TABLE: 1
                    }
                ],
                consts.SCRIPTS: {
                    consts.IFACE_UP: [{
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh add ipv4 "
                            "{}".format(consts.NETNS_PRIMARY_INTERFACE))
                    }],
                    consts.IFACE_DOWN: [{
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh delete ipv4 "
                            "{}".format(consts.NETNS_PRIMARY_INTERFACE))
                    }]
                }
            }

            mock_dump.assert_called_once()
            args = mock_dump.mock_calls[0][1]
            test_utils.assert_interface_files_equal(
                self, args[0], expected_dict)

            mock_check_output.assert_called_with(
                ['ip', 'netns', 'exec', consts.AMPHORA_NAMESPACE,
                 'amphora-interface', 'up',
                 consts.NETNS_PRIMARY_INTERFACE], stderr=subprocess.STDOUT,
                encoding='utf-8')

        mock_check_output.side_effect = [
            subprocess.CalledProcessError(7, 'test', RANDOM_ERROR),
            subprocess.CalledProcessError(7, 'test', RANDOM_ERROR)
        ]

        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/vip/203.0.113.2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(subnet_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/vip/203.0.113.2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(subnet_info))
            self.assertEqual(500, rv.status_code)
            self.assertEqual(
                {'details': RANDOM_ERROR,
                 'message': 'Error plugging VIP'},
                jsonutils.loads(rv.data.decode('utf-8')))

    def test_ubuntu_plug_VIP6(self):
        self._test_plug_vip6(consts.UBUNTU)

    def test_centos_plug_VIP6(self):
        self._test_plug_vip6(consts.CENTOS)

    @mock.patch('os.chmod')
    @mock.patch('shutil.copy2')
    @mock.patch('pyroute2.NSPopen', create=True)
    @mock.patch('pyroute2.IPRoute', create=True)
    @mock.patch('pyroute2.NetNS', create=True)
    @mock.patch('subprocess.check_output')
    @mock.patch('shutil.copytree')
    @mock.patch('os.makedirs')
    @mock.patch('os.path.isfile')
    def _test_plug_vip6(self, distro, mock_isfile, mock_makedirs,
                        mock_copytree, mock_check_output, mock_netns,
                        mock_pyroute2, mock_nspopen,
                        mock_copy2, mock_os_chmod):
        mock_ipr = mock.MagicMock()
        mock_ipr_instance = mock.MagicMock()
        mock_ipr_instance.link_lookup.side_effect = [[], [], [33], [33], [33],
                                                     [33], [33], [33]]
        mock_ipr_instance.get_links.return_value = ({
            'attrs': [('IFLA_IFNAME', FAKE_INTERFACE)]},)
        mock_ipr.__enter__.return_value = mock_ipr_instance
        mock_pyroute2.return_value = mock_ipr

        mock_isfile.return_value = True

        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])
        subnet_info = {
            'subnet_cidr': '2001:db8::/32',
            'gateway': '2001:db8::1',
            'mac_address': '123'
        }

        # malformed ip
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                      '/plug/vip/error',
                                      data=jsonutils.dumps(
                                          subnet_info),
                                      content_type='application/json')
        elif distro == consts.CENTOS:
            rv = self.centos_app.post('/' + api_server.VERSION +
                                      '/plug/vip/error',
                                      data=jsonutils.dumps(
                                          subnet_info),
                                      content_type='application/json')
        self.assertEqual(400, rv.status_code)

        # No subnet info
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                      '/plug/vip/error',
                                      data=jsonutils.dumps(subnet_info),
                                      content_type='application/json')
        elif distro == consts.CENTOS:
            rv = self.centos_app.post('/' + api_server.VERSION +
                                      '/plug/vip/error',
                                      data=jsonutils.dumps(subnet_info),
                                      content_type='application/json')
        self.assertEqual(400, rv.status_code)

        # No interface at all
        file_name = '/sys/bus/pci/rescan'
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/vip/2001:db8::2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(subnet_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/vip/2001:db8::2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(subnet_info))
            mock_open.assert_called_with(file_name, os.O_WRONLY)
            mock_fdopen.assert_called_with(123, 'w')
        m().write.assert_called_once_with('1')
        self.assertEqual(404, rv.status_code)
        self.assertEqual(dict(details="No suitable network interface found"),
                         jsonutils.loads(rv.data.decode('utf-8')))

        # Two interfaces down
        m().reset_mock()
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/vip/2001:db8::2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(subnet_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/vip/2001:db8::2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(subnet_info))
            mock_open.assert_called_with(file_name, os.O_WRONLY)
            mock_fdopen.assert_called_with(123, 'w')
        m().write.assert_called_once_with('1')
        self.assertEqual(404, rv.status_code)
        self.assertEqual(dict(details="No suitable network interface found"),
                         jsonutils.loads(rv.data.decode('utf-8')))

        # Happy Path IPv6, with VRRP_IP and host route
        full_subnet_info = {
            'subnet_cidr': '2001:db8::/32',
            'gateway': '2001:db8::1',
            'mac_address': '123',
            'vrrp_ip': '2001:db8::4',
            'mtu': 1450,
            'host_routes': [{'destination': '2001:db9::/32',
                             'nexthop': '2001:db8::5'},
                            {'destination': '2001:db9::1/128',
                             'nexthop': '2001:db8::5'}]
        }

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

        file_name = (f'/etc/octavia/interfaces/'
                     f'{consts.NETNS_PRIMARY_INTERFACE}.json')
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open

        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen, mock.patch(
                    'octavia.amphorae.backends.utils.interface_file.'
                    'InterfaceFile.dump') as mock_dump:
            mock_open.return_value = 123
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/vip/2001:db8::2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(
                                              full_subnet_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/vip/2001:db8::2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(
                                              full_subnet_info))
            self.assertEqual(202, rv.status_code)
            mock_open.assert_any_call(file_name, flags, mode)
            mock_fdopen.assert_any_call(123, 'w')

            plug_inf_file = '/var/lib/octavia/plugged_interfaces'
            flags = os.O_RDWR | os.O_CREAT
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_any_call(plug_inf_file, flags, mode)
            mock_fdopen.assert_any_call(123, 'r+')
            expected_dict = {
                consts.NAME: consts.NETNS_PRIMARY_INTERFACE,
                consts.MTU: 1450,
                consts.ADDRESSES: [
                    {
                        consts.ADDRESS: '2001:db8::4',
                        consts.PREFIXLEN: 32
                    }, {
                        consts.ADDRESS: '2001:0db8::2',
                        consts.PREFIXLEN: 128
                    }
                ],
                consts.ROUTES: [
                    {
                        consts.DST: '::/0',
                        consts.GATEWAY: '2001:db8::1',
                        consts.FLAGS: [consts.ONLINK]
                    }, {
                        consts.DST: '::/0',
                        consts.GATEWAY: '2001:db8::1',
                        consts.FLAGS: [consts.ONLINK],
                        consts.TABLE: 1
                    }, {
                        consts.DST: '2001:0db8::/32',
                        consts.SCOPE: 'link'
                    }, {
                        consts.DST: '2001:0db8::/32',
                        consts.PREFSRC: '2001:0db8::2',
                        consts.SCOPE: 'link',
                        consts.TABLE: 1
                    }, {
                        consts.DST: '2001:db9::/32',
                        consts.GATEWAY: '2001:db8::5'
                    }, {
                        consts.DST: '2001:db9::1/128',
                        consts.GATEWAY: '2001:db8::5'
                    }, {
                        consts.DST: '2001:db9::/32',
                        consts.GATEWAY: '2001:db8::5',
                        consts.TABLE: 1
                    }, {
                        consts.DST: '2001:db9::1/128',
                        consts.GATEWAY: '2001:db8::5',
                        consts.TABLE: 1
                    }
                ],
                consts.RULES: [
                    {
                        consts.SRC: '2001:0db8::2',
                        consts.SRC_LEN: 128,
                        consts.TABLE: 1
                    }
                ],
                consts.SCRIPTS: {
                    consts.IFACE_UP: [{
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh add ipv6 "
                            "{}".format(consts.NETNS_PRIMARY_INTERFACE))
                    }],
                    consts.IFACE_DOWN: [{
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh delete ipv6 "
                            "{}".format(consts.NETNS_PRIMARY_INTERFACE))
                    }]
                }
            }

            mock_dump.assert_called_once()
            args = mock_dump.mock_calls[0][1]
            test_utils.assert_interface_files_equal(
                self, args[0], expected_dict)

            mock_check_output.assert_called_with(
                [
                    'ip', 'netns', 'exec', consts.AMPHORA_NAMESPACE,
                    'amphora-interface', 'up', '{netns_int}'.format(
                        netns_int=consts.NETNS_PRIMARY_INTERFACE
                    )
                ],
                stderr=subprocess.STDOUT,
                encoding='utf-8')

        # One Interface down, Happy Path IPv6
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

        file_name = (f'/etc/octavia/interfaces/'
                     f'{consts.NETNS_PRIMARY_INTERFACE}.json')
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open

        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen, mock.patch(
                    'octavia.amphorae.backends.utils.interface_file.'
                    'InterfaceFile.dump') as mock_dump:
            mock_open.return_value = 123
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/vip/2001:db8::2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(subnet_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/vip/2001:db8::2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(subnet_info))
            self.assertEqual(202, rv.status_code)
            mock_open.assert_any_call(file_name, flags, mode)
            mock_fdopen.assert_any_call(123, 'w')

            plug_inf_file = '/var/lib/octavia/plugged_interfaces'
            flags = os.O_RDWR | os.O_CREAT
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_any_call(plug_inf_file, flags, mode)
            mock_fdopen.assert_any_call(123, 'r+')

            expected_dict = {
                consts.NAME: consts.NETNS_PRIMARY_INTERFACE,
                consts.MTU: None,
                consts.ADDRESSES: [
                    {
                        consts.IPV6AUTO: True
                    },
                    {
                        consts.ADDRESS: '2001:db8::2',
                        consts.PREFIXLEN: 128
                    }
                ],
                consts.ROUTES: [
                    {
                        consts.DST: '::/0',
                        consts.GATEWAY: '2001:db8::1',
                        consts.FLAGS: [consts.ONLINK]
                    }, {
                        consts.DST: '::/0',
                        consts.GATEWAY: '2001:db8::1',
                        consts.FLAGS: [consts.ONLINK],
                        consts.TABLE: 1
                    }, {
                        consts.DST: '2001:db8::/32',
                        consts.SCOPE: 'link'
                    }, {
                        consts.DST: '2001:db8::/32',
                        consts.PREFSRC: '2001:db8::2',
                        consts.SCOPE: 'link',
                        consts.TABLE: 1
                    }
                ],
                consts.RULES: [
                    {
                        consts.SRC: '2001:db8::2',
                        consts.SRC_LEN: 128,
                        consts.TABLE: 1
                    }
                ],
                consts.SCRIPTS: {
                    consts.IFACE_UP: [{
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh add ipv6 "
                            "{}".format(consts.NETNS_PRIMARY_INTERFACE))
                    }],
                    consts.IFACE_DOWN: [{
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh delete ipv6 "
                            "{}".format(consts.NETNS_PRIMARY_INTERFACE))
                    }]
                }
            }

            mock_dump.assert_called_once()
            args = mock_dump.mock_calls[0][1]
            test_utils.assert_interface_files_equal(
                self, args[0], expected_dict)

            mock_check_output.assert_called_with([
                'ip', 'netns', 'exec', consts.AMPHORA_NAMESPACE,
                'amphora-interface', 'up', consts.NETNS_PRIMARY_INTERFACE
            ], stderr=subprocess.STDOUT, encoding='utf-8')
        mock_check_output.side_effect = [
            subprocess.CalledProcessError(7, 'test', RANDOM_ERROR),
            subprocess.CalledProcessError(7, 'test', RANDOM_ERROR)
        ]

        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/vip/2001:db8::2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(subnet_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/vip/2001:db8::2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(subnet_info))
            self.assertEqual(500, rv.status_code)
            self.assertEqual(
                {'details': RANDOM_ERROR,
                 'message': 'Error plugging VIP'},
                jsonutils.loads(rv.data.decode('utf-8')))

    def test_ubuntu_plug_VIP_with_additional_VIP6(self):
        self._test_plug_VIP_with_additional_VIP6(consts.UBUNTU)

    def test_centos_plug_VIP_with_additional_VIP6(self):
        self._test_plug_VIP_with_additional_VIP6(consts.CENTOS)

    @mock.patch('os.chmod')
    @mock.patch('shutil.copy2')
    @mock.patch('pyroute2.NSPopen', create=True)
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'plug.Plug._netns_interface_exists')
    @mock.patch('pyroute2.IPRoute', create=True)
    @mock.patch('pyroute2.NetNS', create=True)
    @mock.patch('subprocess.check_output')
    @mock.patch('shutil.copytree')
    @mock.patch('os.makedirs')
    @mock.patch('os.path.isfile')
    def _test_plug_VIP_with_additional_VIP6(self, distro, mock_isfile,
                                            mock_makedirs, mock_copytree,
                                            mock_check_output, mock_netns,
                                            mock_pyroute2,
                                            mock_int_exists, mock_nspopen,
                                            mock_copy2, mock_os_chmod):
        mock_ipr = mock.MagicMock()
        mock_ipr_instance = mock.MagicMock()
        mock_ipr_instance.link_lookup.return_value = [33]
        mock_ipr_instance.get_links.return_value = ({
            'attrs': [('IFLA_IFNAME', FAKE_INTERFACE)]},)
        mock_ipr.__enter__.return_value = mock_ipr_instance
        mock_pyroute2.return_value = mock_ipr

        mock_isfile.return_value = True
        mock_int_exists.return_value = False

        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])

        # Happy Path IPv4 with IPv6 additional VIP, with VRRP_IP and host
        # route
        full_subnet_info = {
            'subnet_cidr': '203.0.113.0/24',
            'gateway': '203.0.113.1',
            'mac_address': '123',
            'vrrp_ip': '203.0.113.4',
            'mtu': 1450,
            'host_routes': [{'destination': '203.0.114.0/24',
                             'nexthop': '203.0.113.5'},
                            {'destination': '203.0.115.1/32',
                             'nexthop': '203.0.113.5'}],
            'additional_vips': [
                {'subnet_cidr': '2001:db8::/32',
                 'gateway': '2001:db8::1',
                 'ip_address': '2001:db8::4',
                 'host_routes': [{'destination': '2001:db9::/32',
                                  'nexthop': '2001:db8::5'},
                                 {'destination': '2001:db9::1/128',
                                  'nexthop': '2001:db8::5'}]
                 },
            ],
        }

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

        file_name = (f'/etc/octavia/interfaces/'
                     f'{consts.NETNS_PRIMARY_INTERFACE}.json')
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open

        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen, mock.patch(
                    'octavia.amphorae.backends.utils.interface_file.'
                    'InterfaceFile.dump') as mock_dump:
            mock_open.return_value = 123
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/vip/203.0.113.2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(
                                              full_subnet_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/vip/203.0.113.2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(
                                              full_subnet_info))
            self.assertEqual(202, rv.status_code)
            mock_open.assert_any_call(file_name, flags, mode)
            mock_fdopen.assert_any_call(123, 'w')

            plug_inf_file = '/var/lib/octavia/plugged_interfaces'
            flags = os.O_RDWR | os.O_CREAT
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_any_call(plug_inf_file, flags, mode)
            mock_fdopen.assert_any_call(123, 'r+')

            expected_dict = {
                consts.NAME: consts.NETNS_PRIMARY_INTERFACE,
                consts.MTU: 1450,
                consts.ADDRESSES: [
                    {
                        consts.ADDRESS: '203.0.113.4',
                        consts.PREFIXLEN: 24
                    }, {
                        consts.ADDRESS: '203.0.113.2',
                        consts.PREFIXLEN: 32
                    }, {
                        consts.ADDRESS: '2001:db8::4',
                        consts.PREFIXLEN: 128
                    }
                ],
                consts.ROUTES: [
                    {
                        consts.DST: '0.0.0.0/0',
                        consts.GATEWAY: '203.0.113.1',
                        consts.FLAGS: [consts.ONLINK]
                    }, {
                        consts.DST: '0.0.0.0/0',
                        consts.GATEWAY: '203.0.113.1',
                        consts.TABLE: 1,
                        consts.FLAGS: [consts.ONLINK]
                    }, {
                        consts.DST: '203.0.113.0/24',
                        consts.SCOPE: 'link',
                    }, {
                        consts.DST: '203.0.113.0/24',
                        consts.PREFSRC: '203.0.113.2',
                        consts.SCOPE: 'link',
                        consts.TABLE: 1
                    }, {
                        consts.DST: '203.0.114.0/24',
                        consts.GATEWAY: '203.0.113.5'
                    }, {
                        consts.DST: '203.0.115.1/32',
                        consts.GATEWAY: '203.0.113.5'
                    }, {
                        consts.DST: '203.0.114.0/24',
                        consts.GATEWAY: '203.0.113.5',
                        consts.TABLE: 1
                    }, {
                        consts.DST: '203.0.115.1/32',
                        consts.GATEWAY: '203.0.113.5',
                        consts.TABLE: 1
                    }, {
                        consts.DST: '::/0',
                        consts.GATEWAY: '2001:db8::1',
                        consts.FLAGS: [consts.ONLINK]
                    }, {
                        consts.DST: '::/0',
                        consts.GATEWAY: '2001:db8::1',
                        consts.FLAGS: [consts.ONLINK],
                        consts.TABLE: 1
                    }, {
                        consts.DST: '2001:db8::/32',
                        consts.SCOPE: 'link'
                    }, {
                        consts.DST: '2001:db8::/32',
                        consts.PREFSRC: '2001:db8::4',
                        consts.SCOPE: 'link',
                        consts.TABLE: 1
                    }, {
                        consts.DST: '2001:db9::/32',
                        consts.GATEWAY: '2001:db8::5'
                    }, {
                        consts.DST: '2001:db9::1/128',
                        consts.GATEWAY: '2001:db8::5'
                    }, {
                        consts.DST: '2001:db9::/32',
                        consts.GATEWAY: '2001:db8::5',
                        consts.TABLE: 1
                    }, {
                        consts.DST: '2001:db9::1/128',
                        consts.GATEWAY: '2001:db8::5',
                        consts.TABLE: 1
                    }
                ],
                consts.RULES: [
                    {
                        consts.SRC: '203.0.113.2',
                        consts.SRC_LEN: 32,
                        consts.TABLE: 1
                    },
                    {
                        consts.SRC: '2001:db8::4',
                        consts.SRC_LEN: 128,
                        consts.TABLE: 1
                    }
                ],
                consts.SCRIPTS: {
                    consts.IFACE_UP: [{
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh add ipv4 "
                            "{}".format(consts.NETNS_PRIMARY_INTERFACE))
                    }, {
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh add ipv6 "
                            "{}".format(consts.NETNS_PRIMARY_INTERFACE))
                    }],
                    consts.IFACE_DOWN: [{
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh delete ipv4 "
                            "{}".format(consts.NETNS_PRIMARY_INTERFACE))
                    }, {
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh delete ipv6 "
                            "{}".format(consts.NETNS_PRIMARY_INTERFACE))
                    }]
                }
            }

            mock_dump.assert_called_once()
            args = mock_dump.mock_calls[0][1]
            test_utils.assert_interface_files_equal(
                self, args[0], expected_dict)

            mock_check_output.assert_called_with([
                'ip', 'netns', 'exec', consts.AMPHORA_NAMESPACE,
                'amphora-interface', 'up',
                consts.NETNS_PRIMARY_INTERFACE
            ], stderr=subprocess.STDOUT, encoding='utf-8')

    def test_ubuntu_plug_VIP6_with_additional_VIP(self):
        self._test_plug_VIP6_with_additional_VIP(consts.UBUNTU)

    def test_centos_plug_VIP6_with_additional_VIP(self):
        self._test_plug_VIP6_with_additional_VIP(consts.CENTOS)

    @mock.patch('os.chmod')
    @mock.patch('shutil.copy2')
    @mock.patch('pyroute2.NSPopen', create=True)
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'plug.Plug._netns_interface_exists')
    @mock.patch('pyroute2.IPRoute', create=True)
    @mock.patch('pyroute2.NetNS', create=True)
    @mock.patch('subprocess.check_output')
    @mock.patch('shutil.copytree')
    @mock.patch('os.makedirs')
    @mock.patch('os.path.isfile')
    def _test_plug_VIP6_with_additional_VIP(self, distro, mock_isfile,
                                            mock_makedirs, mock_copytree,
                                            mock_check_output, mock_netns,
                                            mock_pyroute2,
                                            mock_int_exists, mock_nspopen,
                                            mock_copy2, mock_os_chmod):
        mock_ipr = mock.MagicMock()
        mock_ipr_instance = mock.MagicMock()
        mock_ipr_instance.link_lookup.return_value = [33]
        mock_ipr_instance.get_links.return_value = ({
            'attrs': [('IFLA_IFNAME', FAKE_INTERFACE)]},)
        mock_ipr.__enter__.return_value = mock_ipr_instance
        mock_pyroute2.return_value = mock_ipr

        mock_isfile.return_value = True
        mock_int_exists.return_value = False

        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])

        # Happy Path IPv6 with IPv4 additional VIP, with VRRP_IP and host
        # route
        full_subnet_info = {
            'subnet_cidr': '2001:db8::/32',
            'gateway': '2001:db8::1',
            'vrrp_ip': '2001:db8::4',
            'host_routes': [{'destination': '2001:db9::/32',
                             'nexthop': '2001:db8::5'},
                            {'destination': '2001:db9::1/128',
                             'nexthop': '2001:db8::5'}],
            'mac_address': '123',
            'mtu': 1450,
            'additional_vips': [
                {'subnet_cidr': '203.0.113.0/24',
                 'gateway': '203.0.113.1',
                 'ip_address': '203.0.113.4',
                 'host_routes': [{'destination': '203.0.114.0/24',
                                  'nexthop': '203.0.113.5'},
                                 {'destination': '203.0.115.1/32',
                                  'nexthop': '203.0.113.5'}],
                 },
            ],
        }

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

        file_name = (f'/etc/octavia/interfaces/'
                     f'{consts.NETNS_PRIMARY_INTERFACE}.json')
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open

        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen, mock.patch(
                    'octavia.amphorae.backends.utils.interface_file.'
                    'InterfaceFile.dump') as mock_dump:
            mock_open.return_value = 123
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.post('/' + api_server.VERSION +
                                          "/plug/vip/2001:db8::2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(
                                              full_subnet_info))
            elif distro == consts.CENTOS:
                rv = self.centos_app.post('/' + api_server.VERSION +
                                          "/plug/vip/2001:db8::2",
                                          content_type='application/json',
                                          data=jsonutils.dumps(
                                              full_subnet_info))
            self.assertEqual(202, rv.status_code)
            mock_open.assert_any_call(file_name, flags, mode)
            mock_fdopen.assert_any_call(123, 'w')

            plug_inf_file = '/var/lib/octavia/plugged_interfaces'
            flags = os.O_RDWR | os.O_CREAT
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_any_call(plug_inf_file, flags, mode)
            mock_fdopen.assert_any_call(123, 'r+')

            expected_dict = {
                consts.NAME: consts.NETNS_PRIMARY_INTERFACE,
                consts.MTU: 1450,
                consts.ADDRESSES: [
                    {
                        consts.ADDRESS: '2001:db8::4',
                        consts.PREFIXLEN: 32
                    }, {
                        consts.ADDRESS: '2001:db8::2',
                        consts.PREFIXLEN: 128
                    }, {
                        consts.ADDRESS: '203.0.113.4',
                        consts.PREFIXLEN: 32
                    }
                ],
                consts.ROUTES: [
                    {
                        consts.DST: '::/0',
                        consts.GATEWAY: '2001:db8::1',
                        consts.FLAGS: [consts.ONLINK]
                    }, {
                        consts.DST: '::/0',
                        consts.GATEWAY: '2001:db8::1',
                        consts.FLAGS: [consts.ONLINK],
                        consts.TABLE: 1
                    }, {
                        consts.DST: '2001:db8::/32',
                        consts.SCOPE: 'link'
                    }, {
                        consts.DST: '2001:db8::/32',
                        consts.PREFSRC: '2001:db8::2',
                        consts.SCOPE: 'link',
                        consts.TABLE: 1
                    }, {
                        consts.DST: '2001:db9::/32',
                        consts.GATEWAY: '2001:db8::5'
                    }, {
                        consts.DST: '2001:db9::1/128',
                        consts.GATEWAY: '2001:db8::5'
                    }, {
                        consts.DST: '2001:db9::/32',
                        consts.GATEWAY: '2001:db8::5',
                        consts.TABLE: 1
                    }, {
                        consts.DST: '2001:db9::1/128',
                        consts.GATEWAY: '2001:db8::5',
                        consts.TABLE: 1
                    }, {
                        consts.DST: '0.0.0.0/0',
                        consts.GATEWAY: '203.0.113.1',
                        consts.FLAGS: [consts.ONLINK]
                    }, {
                        consts.DST: '0.0.0.0/0',
                        consts.GATEWAY: '203.0.113.1',
                        consts.TABLE: 1,
                        consts.FLAGS: [consts.ONLINK]
                    }, {
                        consts.DST: '203.0.113.0/24',
                        consts.SCOPE: 'link'
                    }, {
                        consts.DST: '203.0.113.0/24',
                        consts.PREFSRC: '203.0.113.4',
                        consts.SCOPE: 'link',
                        consts.TABLE: 1
                    }, {
                        consts.DST: '203.0.114.0/24',
                        consts.GATEWAY: '203.0.113.5'
                    }, {
                        consts.DST: '203.0.115.1/32',
                        consts.GATEWAY: '203.0.113.5'
                    }, {
                        consts.DST: '203.0.114.0/24',
                        consts.GATEWAY: '203.0.113.5',
                        consts.TABLE: 1
                    }, {
                        consts.DST: '203.0.115.1/32',
                        consts.GATEWAY: '203.0.113.5',
                        consts.TABLE: 1
                    }
                ],
                consts.RULES: [
                    {
                        consts.SRC: '2001:db8::2',
                        consts.SRC_LEN: 128,
                        consts.TABLE: 1
                    }, {
                        consts.SRC: '203.0.113.4',
                        consts.SRC_LEN: 32,
                        consts.TABLE: 1
                    },
                ],
                consts.SCRIPTS: {
                    consts.IFACE_UP: [{
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh add ipv4 "
                            "{}".format(consts.NETNS_PRIMARY_INTERFACE))
                    }, {
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh add ipv6 "
                            "{}".format(consts.NETNS_PRIMARY_INTERFACE))
                    }],
                    consts.IFACE_DOWN: [{
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh delete ipv4 "
                            "{}".format(consts.NETNS_PRIMARY_INTERFACE))
                    }, {
                        consts.COMMAND: (
                            "/usr/local/bin/lvs-masquerade.sh delete ipv6 "
                            "{}".format(consts.NETNS_PRIMARY_INTERFACE))
                    }]
                }
            }

            mock_dump.assert_called_once()
            args = mock_dump.mock_calls[0][1]
            test_utils.assert_interface_files_equal(
                self, args[0], expected_dict)

            mock_check_output.assert_called_with([
                'ip', 'netns', 'exec', consts.AMPHORA_NAMESPACE,
                'amphora-interface', 'up', consts.NETNS_PRIMARY_INTERFACE
            ], stderr=subprocess.STDOUT, encoding='utf-8')

    def test_ubuntu_get_interface(self):
        self._test_get_interface(consts.UBUNTU)

    def test_centos_get_interface(self):
        self._test_get_interface(consts.CENTOS)

    @mock.patch('pyroute2.NetNS', create=True)
    def _test_get_interface(self, distro, mock_netns):

        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])

        netns_handle = mock_netns.return_value.__enter__.return_value

        interface_res = {'interface': 'eth0'}

        # Happy path
        netns_handle.get_addr.return_value = [{
            'index': 3, 'family': socket.AF_INET,
            'attrs': [['IFA_ADDRESS', '203.0.113.2']]}]
        netns_handle.get_links.return_value = [{
            'attrs': [['IFLA_IFNAME', 'eth0']]}]
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.get('/' + api_server.VERSION +
                                     '/interface/203.0.113.2',
                                     data=jsonutils.dumps(interface_res),
                                     content_type='application/json')
        elif distro == consts.CENTOS:
            rv = self.centos_app.get('/' + api_server.VERSION +
                                     '/interface/203.0.113.2',
                                     data=jsonutils.dumps(interface_res),
                                     content_type='application/json')
        self.assertEqual(200, rv.status_code)

        # Happy path with IPv6 address normalization
        netns_handle.get_addr.return_value = [{
            'index': 3, 'family': socket.AF_INET6,
            'attrs': [['IFA_ADDRESS',
                       '0000:0000:0000:0000:0000:0000:0000:0001']]}]
        netns_handle.get_links.return_value = [{
            'attrs': [['IFLA_IFNAME', 'eth0']]}]
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.get('/' + api_server.VERSION +
                                     '/interface/::1',
                                     data=jsonutils.dumps(interface_res),
                                     content_type='application/json')
        elif distro == consts.CENTOS:
            rv = self.centos_app.get('/' + api_server.VERSION +
                                     '/interface/::1',
                                     data=jsonutils.dumps(interface_res),
                                     content_type='application/json')
        self.assertEqual(200, rv.status_code)

        # Nonexistent interface
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.get('/' + api_server.VERSION +
                                     '/interface/10.0.0.1',
                                     data=jsonutils.dumps(interface_res),
                                     content_type='application/json')
        elif distro == consts.CENTOS:
            rv = self.centos_app.get('/' + api_server.VERSION +
                                     '/interface/10.0.0.1',
                                     data=jsonutils.dumps(interface_res),
                                     content_type='application/json')
        self.assertEqual(404, rv.status_code)

        # Invalid IP address
        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.get('/' + api_server.VERSION +
                                     '/interface/00:00:00:00:00:00',
                                     data=jsonutils.dumps(interface_res),
                                     content_type='application/json')
        elif distro == consts.CENTOS:
            rv = self.centos_app.get('/' + api_server.VERSION +
                                     '/interface/00:00:00:00:00:00',
                                     data=jsonutils.dumps(interface_res),
                                     content_type='application/json')
        self.assertEqual(400, rv.status_code)

    def test_ubuntu_upload_keepalived_config(self):
        with mock.patch('distro.id', return_value='ubuntu'):
            self._test_upload_keepalived_config(consts.UBUNTU)

    def test_centos_upload_keepalived_config(self):
        with mock.patch('distro.id', return_value='centos'):
            self._test_upload_keepalived_config(consts.CENTOS)

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'vrrp_check_script_update')
    @mock.patch('os.path.exists')
    @mock.patch('os.makedirs')
    @mock.patch('os.rename')
    @mock.patch('subprocess.check_output')
    @mock.patch('os.remove')
    def _test_upload_keepalived_config(self, distro, mock_remove,
                                       mock_subprocess, mock_rename,
                                       mock_makedirs, mock_exists,
                                       mock_vrrp_check):

        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC

        mock_exists.return_value = True
        cfg_path = util.keepalived_cfg_path()
        m = self.useFixture(test_utils.OpenFixture(cfg_path)).mock_open

        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                         '/vrrp/upload', data='test')
            elif distro == consts.CENTOS:
                rv = self.centos_app.put('/' + api_server.VERSION +
                                         '/vrrp/upload', data='test')

            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_called_with(cfg_path, flags, mode)
            mock_fdopen.assert_called_with(123, 'wb')
            self.assertEqual(200, rv.status_code)
            mock_vrrp_check.assert_called_once_with(None,
                                                    consts.AMP_ACTION_START)

        mock_exists.return_value = False
        mock_vrrp_check.reset_mock()
        script_path = util.keepalived_check_script_path()
        m = self.useFixture(test_utils.OpenFixture(script_path)).mock_open

        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                         '/vrrp/upload', data='test')
            elif distro == consts.CENTOS:
                rv = self.centos_app.put('/' + api_server.VERSION +
                                         '/vrrp/upload', data='test')
            mode = (stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP |
                    stat.S_IROTH | stat.S_IXOTH)
            mock_open.assert_called_with(script_path, flags, mode)
            mock_fdopen.assert_called_with(123, 'w')
            self.assertEqual(200, rv.status_code)
            mock_vrrp_check.assert_called_once_with(None,
                                                    consts.AMP_ACTION_START)

    def test_ubuntu_manage_service_vrrp(self):
        self._test_manage_service_vrrp(consts.UBUNTU)

    def test_centos_manage_service_vrrp(self):
        self._test_manage_service_vrrp(consts.CENTOS)

    @mock.patch('subprocess.check_output')
    def _test_manage_service_vrrp(self, distro, mock_check_output):
        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])

        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.put('/' + api_server.VERSION + '/vrrp/start')
        elif distro == consts.CENTOS:
            rv = self.centos_app.put('/' + api_server.VERSION + '/vrrp/start')

        self.assertEqual(202, rv.status_code)

        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                     '/vrrp/restart')
        elif distro == consts.CENTOS:
            rv = self.centos_app.put('/' + api_server.VERSION +
                                     '/vrrp/restart')
        self.assertEqual(400, rv.status_code)

        mock_check_output.side_effect = subprocess.CalledProcessError(1,
                                                                      'blah!')

        if distro == consts.UBUNTU:
            rv = self.ubuntu_app.put('/' + api_server.VERSION + '/vrrp/start')
        elif distro == consts.CENTOS:
            rv = self.centos_app.put('/' + api_server.VERSION + '/vrrp/start')
        self.assertEqual(500, rv.status_code)

    def test_ubuntu_details(self):
        self._test_details(consts.UBUNTU)

    def test_centos_details(self):
        self._test_details(consts.CENTOS)

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_lvs_listeners',
                return_value=[])
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'amphora_info.AmphoraInfo.'
                '_get_extend_body_from_lvs_driver',
                return_value={
                    "keepalived_version": '1.1.11-1',
                    "ipvsadm_version": '2.2.22-2'
                })
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'amphora_info.AmphoraInfo.'
                '_count_lvs_listener_processes', return_value=0)
    @mock.patch('octavia.amphorae.backends.agent.api_server.amphora_info.'
                'AmphoraInfo._count_haproxy_processes')
    @mock.patch('octavia.amphorae.backends.agent.api_server.amphora_info.'
                'AmphoraInfo._get_networks')
    @mock.patch('octavia.amphorae.backends.agent.api_server.amphora_info.'
                'AmphoraInfo._load')
    @mock.patch('os.statvfs')
    @mock.patch('octavia.amphorae.backends.agent.api_server.amphora_info.'
                'AmphoraInfo._cpu')
    @mock.patch('octavia.amphorae.backends.agent.api_server.amphora_info.'
                'AmphoraInfo._get_meminfo')
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'util.get_listeners')
    @mock.patch('socket.gethostname')
    @mock.patch('subprocess.check_output')
    def _test_details(self, distro, mock_subbprocess, mock_hostname,
                      mock_get_listeners, mock_get_mem, mock_cpu,
                      mock_statvfs, mock_load, mock_get_nets,
                      mock_count_haproxy, mock_count_lvs_listeners,
                      mock_get_ext_from_lvs_driver, mock_get_lvs_listeners):

        self.assertIn(distro, [consts.UBUNTU, consts.CENTOS])

        listener_id = uuidutils.generate_uuid()
        mock_get_listeners.return_value = [listener_id]

        mock_hostname.side_effect = ['test-host']

        mock_subbprocess.side_effect = ['9.9.99-9']

        MemTotal = random.randrange(0, 1000)
        MemFree = random.randrange(0, 1000)
        Buffers = random.randrange(0, 1000)
        Cached = random.randrange(0, 1000)
        SwapCached = random.randrange(0, 1000)
        Shmem = random.randrange(0, 1000)
        Slab = random.randrange(0, 1000)

        memory_dict = {'CmaFree': 0, 'Mapped': 38244, 'CommitLimit': 508048,
                       'MemFree': MemFree, 'AnonPages': 92384,
                       'DirectMap2M': 997376, 'SwapTotal': 0,
                       'NFS_Unstable': 0, 'SReclaimable': 34168,
                       'Writeback': 0, 'PageTables': 3760, 'Shmem': Shmem,
                       'Hugepagesize': 2048, 'MemAvailable': 738356,
                       'HardwareCorrupted': 0, 'SwapCached': SwapCached,
                       'Dirty': 80, 'Active': 237060, 'VmallocUsed': 0,
                       'Inactive(anon)': 2752, 'Slab': Slab, 'Cached': Cached,
                       'Inactive(file)': 149588, 'SUnreclaim': 17796,
                       'Mlocked': 3656, 'AnonHugePages': 6144, 'SwapFree': 0,
                       'Active(file)': 145512, 'CmaTotal': 0,
                       'Unevictable': 3656, 'KernelStack': 2368,
                       'Inactive': 152340, 'MemTotal': MemTotal, 'Bounce': 0,
                       'Committed_AS': 401884, 'Active(anon)': 91548,
                       'VmallocTotal': 34359738367, 'VmallocChunk': 0,
                       'DirectMap4k': 51072, 'WritebackTmp': 0,
                       'Buffers': Buffers}
        mock_get_mem.return_value = memory_dict

        cpu_total = random.randrange(0, 1000)
        cpu_user = random.randrange(0, 1000)
        cpu_system = random.randrange(0, 1000)
        cpu_softirq = random.randrange(0, 1000)

        cpu_dict = {'idle': '7168848', 'system': cpu_system,
                    'total': cpu_total, 'softirq': cpu_softirq, 'nice': '31',
                    'iowait': '902', 'user': cpu_user, 'irq': '0'}

        mock_cpu.return_value = cpu_dict

        f_blocks = random.randrange(0, 1000)
        f_bfree = random.randrange(0, 1000)
        f_frsize = random.randrange(0, 1000)
        f_bavail = random.randrange(0, 1000)

        stats = mock.MagicMock()
        stats.f_blocks = f_blocks
        stats.f_bfree = f_bfree
        stats.f_frsize = f_frsize
        stats.f_bavail = f_bavail
        disk_used = (f_blocks - f_bfree) * f_frsize
        disk_available = f_bavail * f_frsize

        mock_statvfs.return_value = stats

        load_1min = random.randrange(0, 10)
        load_5min = random.randrange(0, 10)
        load_15min = random.randrange(0, 10)

        mock_load.return_value = [load_1min, load_5min, load_15min]

        eth1_rx = random.randrange(0, 1000)
        eth1_tx = random.randrange(0, 1000)
        eth2_rx = random.randrange(0, 1000)
        eth2_tx = random.randrange(0, 1000)
        eth3_rx = random.randrange(0, 1000)
        eth3_tx = random.randrange(0, 1000)

        net_dict = {'eth2': {'network_rx': eth2_rx, 'network_tx': eth2_tx},
                    'eth1': {'network_rx': eth1_rx, 'network_tx': eth1_tx},
                    'eth3': {'network_rx': eth3_rx, 'network_tx': eth3_tx}}

        mock_get_nets.return_value = net_dict

        haproxy_count = random.randrange(0, 100)
        mock_count_haproxy.return_value = haproxy_count
        tuned_profiles = "virtual-guest optimize-serial-console amphora"

        expected_dict = {'active': True,
                         'active_tuned_profiles': tuned_profiles,
                         'api_version': '1.0',
                         'cpu': {'soft_irq': cpu_softirq, 'system': cpu_system,
                                 'total': cpu_total, 'user': cpu_user},
                         'cpu_count': os.cpu_count(),
                         'disk': {'available': disk_available,
                                  'used': disk_used},
                         'haproxy_count': haproxy_count,
                         'haproxy_version': '9.9.99-9',
                         'hostname': 'test-host',
                         'ipvsadm_version': '2.2.22-2',
                         'keepalived_version': '1.1.11-1',
                         'listeners': [listener_id],
                         'load': [load_1min, load_5min, load_15min],
                         'memory': {'buffers': Buffers,
                                    'cached': Cached,
                                    'free': MemFree,
                                    'shared': Shmem,
                                    'slab': Slab,
                                    'swap_used': SwapCached,
                                    'total': MemTotal},
                         'networks': {'eth1': {'network_rx': eth1_rx,
                                               'network_tx': eth1_tx},
                                      'eth2': {'network_rx': eth2_rx,
                                               'network_tx': eth2_tx},
                                      'eth3': {'network_rx': eth3_rx,
                                               'network_tx': eth3_tx}},
                         'packages': {},
                         'topology': consts.TOPOLOGY_SINGLE,
                         'topology_status': consts.TOPOLOGY_STATUS_OK,
                         'lvs_listener_process_count': 0}

        with mock.patch("octavia.amphorae.backends.agent.api_server"
                        ".amphora_info.open",
                        mock.mock_open(read_data=tuned_profiles)):
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.get('/' + api_server.VERSION + '/details')
            elif distro == consts.CENTOS:
                rv = self.centos_app.get('/' + api_server.VERSION + '/details')

        self.assertEqual(200, rv.status_code)
        self.assertEqual(expected_dict,
                         jsonutils.loads(rv.data.decode('utf-8')))

    def test_ubuntu_upload_config(self):
        self._test_upload_config(consts.UBUNTU)

    def test_centos_upload_config(self):
        self._test_upload_config(consts.CENTOS)

    @mock.patch('oslo_config.cfg.CONF.mutate_config_files')
    def _test_upload_config(self, distro, mock_mutate):
        server.BUFFER = 5  # test the while loop
        m = self.useFixture(
            test_utils.OpenFixture(AMP_AGENT_CONF_PATH)).mock_open
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                         '/config', data='TestTest')
            elif distro == consts.CENTOS:
                rv = self.centos_app.put('/' + api_server.VERSION +
                                         '/config', data='TestTest')
            self.assertEqual(202, rv.status_code)
            self.assertEqual(OK, jsonutils.loads(rv.data.decode('utf-8')))
            handle = m()
            handle.write.assert_any_call(octavia_utils.b('TestT'))
            handle.write.assert_any_call(octavia_utils.b('est'))
            mock_mutate.assert_called_once_with()

            # Test the exception handling
            mock_mutate.side_effect = Exception('boom')
            if distro == consts.UBUNTU:
                rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                         '/config', data='TestTest')
            elif distro == consts.CENTOS:
                rv = self.centos_app.put('/' + api_server.VERSION +
                                         '/config', data='TestTest')
            self.assertEqual(500, rv.status_code)

    def test_version_discovery(self):
        hm_queue = mock.MagicMock()
        with mock.patch('distro.id', return_value='ubuntu'), mock.patch(
                'octavia.amphorae.backends.agent.api_server.plug.'
                'Plug.plug_lo'):
            self.test_client = server.Server(hm_queue).app.test_client()
        expected_dict = {'api_version': api_server.VERSION}
        rv = self.test_client.get('/')
        self.assertEqual(200, rv.status_code)
        self.assertEqual(expected_dict,
                         jsonutils.loads(rv.data.decode('utf-8')))

    @mock.patch('octavia.amphorae.backends.utils.nftable_utils.'
                'load_nftables_file')
    @mock.patch('octavia.amphorae.backends.utils.nftable_utils.'
                'write_nftable_rules_file')
    @mock.patch('octavia.amphorae.backends.agent.api_server.amphora_info.'
                'AmphoraInfo.get_interface')
    def test_set_interface_rules(self, mock_get_int, mock_write_rules,
                                 mock_load_rules):
        mock_get_int.side_effect = [
            webob.Response(status=400),
            webob.Response(status=200, json={'interface': 'fake1'}),
            webob.Response(status=200, json={'interface': 'fake1'})]

        # Test can't find interface
        rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                 '/interface/192.0.2.10/rules', data='fake')
        self.assertEqual(400, rv.status_code)
        mock_write_rules.assert_not_called()

        # Test schema validation failure
        rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                 '/interface/192.0.2.10/rules', data='fake')
        self.assertEqual('400 Bad Request', rv.status)

        # Test successful path
        rules_json = ('[{"protocol":"TCP","cidr":"192.0.2.0/24","port":8080},'
                      '{"protocol":"UDP","cidr":null,"port":80}]')
        rv = self.ubuntu_app.put('/' + api_server.VERSION +
                                 '/interface/192.0.2.10/rules',
                                 data=rules_json,
                                 content_type='application/json')
        self.assertEqual('200 OK', rv.status)
        mock_write_rules.assert_called_once_with('fake1',
                                                 jsonutils.loads(rules_json))
        mock_load_rules.assert_called_once()
