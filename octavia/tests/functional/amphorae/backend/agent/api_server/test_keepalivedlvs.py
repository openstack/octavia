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
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import stat
import subprocess

import flask
import mock
from werkzeug import exceptions

from oslo_utils import uuidutils

from octavia.amphorae.backends.agent.api_server import keepalivedlvs
from octavia.amphorae.backends.agent.api_server import server
from octavia.amphorae.backends.agent.api_server import util
from octavia.common import constants as consts
from octavia.tests.common import utils as test_utils
from octavia.tests.unit import base


class KeepalivedLvsTestCase(base.TestCase):
    FAKE_ID = uuidutils.generate_uuid()
    LISTENER_ID = 'listener-1111-1111-1111-listenerid00'
    POOL_ID = 'poolpool-1111-1111-1111-poolid000000'
    MEMBER_ID1 = 'memberid-1111-1111-1111-memberid1111'
    MEMBER_ID2 = 'memberid-2222-2222-2222-memberid2222'
    HEALTHMONITOR_ID = 'hmidhmid-1111-1111-1111-healthmonito'
    NORMAL_CFG_CONTENT = (
        "# Configuration for Listener %(listener_id)s\n\n"
        "net_namespace haproxy-amphora\n\n"
        "virtual_server 10.0.0.2 80 {\n"
        "    lb_algo rr\n"
        "    lb_kind NAT\n"
        "    protocol udp\n"
        "    delay_loop 30\n"
        "    delay_before_retry 31\n"
        "    retry 3\n\n\n"
        "    # Configuration for Pool %(pool_id)s\n"
        "    # Configuration for HealthMonitor %(hm_id)s\n"
        "    # Configuration for Member %(member1_id)s\n"
        "    real_server 10.0.0.99 82 {\n"
        "        weight 13\n"
        "        inhibit_on_failure\n"
        "        uthreshold 98\n"
        "        persistence_timeout 33\n"
        "        persistence_granularity 255.255.0.0\n"
        "        delay_before_retry 31\n"
        "        retry 3\n"
        "        MISC_CHECK {\n"
        "            misc_path \"/var/lib/octavia/lvs/check/"
        "udp_check.sh 10.0.0.99 82\"\n"
        "            misc_timeout 30\n"
        "            misc_dynamic\n"
        "        }\n"
        "    }\n\n"
        "    # Configuration for Member %(member2_id)s\n"
        "    real_server 10.0.0.98 82 {\n"
        "        weight 13\n"
        "        inhibit_on_failure\n"
        "        uthreshold 98\n"
        "        persistence_timeout 33\n"
        "        persistence_granularity 255.255.0.0\n"
        "        delay_before_retry 31\n"
        "        retry 3\n"
        "        MISC_CHECK {\n"
        "            misc_path \"/var/lib/octavia/lvs/check/"
        "udp_check.sh 10.0.0.98 82\"\n"
        "            misc_timeout 30\n"
        "            misc_dynamic\n"
        "        }\n"
        "    }\n\n"
        "}\n\n") % {'listener_id': LISTENER_ID, 'pool_id': POOL_ID,
                    'hm_id': HEALTHMONITOR_ID, 'member1_id': MEMBER_ID1,
                    'member2_id': MEMBER_ID2}
    PROC_CONTENT = (
        "IP Virtual Server version 1.2.1 (size=4096)\n"
        "Prot LocalAddress:Port Scheduler Flags\n"
        "  -> RemoteAddress:Port Forward Weight ActiveConn InActConn\n"
        "UDP  0A000002:0050 sh\n"
        "  -> 0A000063:0052      Masq    13     1          0\n"
        "  -> 0A000062:0052      Masq    13     1          0\n"
    )
    NORMAL_PID_CONTENT = "1988"
    TEST_URL = server.PATH_PREFIX + '/listeners/%s/%s/udp_listener'

    def setUp(self):
        super(KeepalivedLvsTestCase, self).setUp()
        self.app = flask.Flask(__name__)
        self.client = self.app.test_client()
        self._ctx = self.app.test_request_context()
        self._ctx.push()
        self.test_keepalivedlvs = keepalivedlvs.KeepalivedLvs()
        self.app.add_url_rule(
            rule=self.TEST_URL % ('<amphora_id>', '<listener_id>'),
            view_func=(lambda amphora_id, listener_id:
                       self.test_keepalivedlvs.upload_udp_listener_config(
                           listener_id)),
            methods=['PUT'])

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'run_systemctl_command')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'install_netns_systemd_service')
    @mock.patch('pyroute2.NetNS')
    @mock.patch('shutil.copy2')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_os_init_system', return_value=consts.INIT_SYSTEMD)
    @mock.patch('os.chmod')
    @mock.patch('os.path.exists')
    @mock.patch('os.makedirs')
    @mock.patch('os.remove')
    @mock.patch('subprocess.check_output')
    def test_upload_udp_listener_config_no_vrrp_check_dir(
            self, m_check_output, m_os_rm, m_os_mkdir, m_exists, m_os_chmod,
            m_os_sysinit, m_copy2, mock_netns, mock_install_netns,
            mock_systemctl):
        m_exists.side_effect = [False, False, True, True, False, False]
        cfg_path = util.keepalived_lvs_cfg_path(self.FAKE_ID)
        m = self.useFixture(test_utils.OpenFixture(cfg_path)).mock_open

        with mock.patch('os.open') as m_open, mock.patch.object(os,
                                                                'fdopen',
                                                                m) as m_fdopen:
            m_open.side_effect = ['TEST-WRITE-CFG',
                                  'TEST-WRITE-SYSINIT']

            res = self.client.put(self.TEST_URL % ('123', self.FAKE_ID),
                                  data=self.NORMAL_CFG_CONTENT)

            mock_install_netns.assert_called_once()
            systemctl_calls = [
                mock.call(consts.ENABLE,
                          consts.AMP_NETNS_SVC_PREFIX),
                mock.call(consts.ENABLE,
                          'octavia-keepalivedlvs-%s' % str(self.FAKE_ID)),
            ]
            mock_systemctl.assert_has_calls(systemctl_calls)
            os_mkdir_calls = [
                mock.call(util.keepalived_lvs_dir()),
                mock.call(util.keepalived_backend_check_script_dir())
            ]
            m_os_mkdir.assert_has_calls(os_mkdir_calls)

            m_os_chmod.assert_called_with(
                util.keepalived_backend_check_script_path(), stat.S_IEXEC)

            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            systemd_cfg_path = util.keepalived_lvs_init_path(
                consts.INIT_SYSTEMD, self.FAKE_ID)

            m_open_calls = [
                mock.call(cfg_path, flags, mode),
                mock.call(systemd_cfg_path, flags, mode)
            ]
            m_open.assert_has_calls(m_open_calls)
            m_fdopen.assert_any_call('TEST-WRITE-CFG', 'wb')
            m_fdopen.assert_any_call('TEST-WRITE-SYSINIT', 'w')
            self.assertEqual(200, res.status_code)

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'run_systemctl_command')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'install_netns_systemd_service')
    @mock.patch('pyroute2.NetNS')
    @mock.patch('shutil.copy2')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_os_init_system', return_value=consts.INIT_SYSTEMD)
    @mock.patch('os.chmod')
    @mock.patch('os.path.exists')
    @mock.patch('os.makedirs')
    @mock.patch('os.remove')
    @mock.patch('subprocess.check_output')
    def test_upload_udp_listener_config_with_vrrp_check_dir(
            self, m_check_output, m_os_rm, m_os_mkdir, m_exists, m_os_chmod,
            m_os_sysinit, m_copy2, mock_netns, mock_install_netns,
            mock_systemctl):
        m_exists.side_effect = [False, False, True, True, True, False, False]
        cfg_path = util.keepalived_lvs_cfg_path(self.FAKE_ID)
        m = self.useFixture(test_utils.OpenFixture(cfg_path)).mock_open

        with mock.patch('os.open') as m_open, mock.patch.object(os,
                                                                'fdopen',
                                                                m) as m_fdopen:
            m_open.side_effect = ['TEST-WRITE-CFG',
                                  'TEST-WRITE-SYSINIT',
                                  'TEST-WRITE-UDP-VRRP-CHECK']
            res = self.client.put(self.TEST_URL % ('123', self.FAKE_ID),
                                  data=self.NORMAL_CFG_CONTENT)
            os_mkdir_calls = [
                mock.call(util.keepalived_lvs_dir()),
                mock.call(util.keepalived_backend_check_script_dir())
            ]
            m_os_mkdir.assert_has_calls(os_mkdir_calls)

            mock_install_netns.assert_called_once()
            systemctl_calls = [
                mock.call(consts.ENABLE,
                          consts.AMP_NETNS_SVC_PREFIX),
                mock.call(consts.ENABLE,
                          'octavia-keepalivedlvs-%s' % str(self.FAKE_ID)),
            ]
            mock_systemctl.assert_has_calls(systemctl_calls)

            m_os_chmod.assert_called_with(
                util.keepalived_backend_check_script_path(), stat.S_IEXEC)
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            systemd_cfg_path = util.keepalived_lvs_init_path(
                consts.INIT_SYSTEMD, self.FAKE_ID)
            script_path = os.path.join(
                util.keepalived_check_scripts_dir(),
                keepalivedlvs.KEEPALIVED_CHECK_SCRIPT_NAME)
            m_open_calls = [
                mock.call(cfg_path, flags, mode),
                mock.call(systemd_cfg_path, flags, mode),
                mock.call(script_path, flags, stat.S_IEXEC)
            ]
            m_open.assert_has_calls(m_open_calls)
            m_fdopen.assert_any_call('TEST-WRITE-CFG', 'wb')
            m_fdopen.assert_any_call('TEST-WRITE-SYSINIT', 'w')
            m_fdopen.assert_any_call('TEST-WRITE-UDP-VRRP-CHECK', 'w')
            self.assertEqual(200, res.status_code)

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'run_systemctl_command')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'install_netns_systemd_service')
    @mock.patch('shutil.copy2')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_os_init_system', return_value=consts.INIT_SYSTEMD)
    @mock.patch('os.chmod')
    @mock.patch('os.path.exists')
    @mock.patch('os.makedirs')
    @mock.patch('os.remove')
    @mock.patch('subprocess.check_output')
    def test_upload_udp_listener_config_start_service_failure(
            self, m_check_output, m_os_rm, m_os_mkdir, m_exists, m_os_chmod,
            m_os_sysinit, m_copy2, mock_install_netns, mock_systemctl):
        m_exists.side_effect = [False, False, True, True, True, False]
        m_check_output.side_effect = subprocess.CalledProcessError(1, 'blah!')
        cfg_path = util.keepalived_lvs_cfg_path(self.FAKE_ID)
        m = self.useFixture(test_utils.OpenFixture(cfg_path)).mock_open

        with mock.patch('os.open') as m_open, mock.patch.object(os,
                                                                'fdopen',
                                                                m) as m_fdopen:
            m_open.side_effect = ['TEST-WRITE-CFG',
                                  'TEST-WRITE-SYSINIT']
            res = self.client.put(self.TEST_URL % ('123', self.FAKE_ID),
                                  data=self.NORMAL_CFG_CONTENT)
            os_mkdir_calls = [
                mock.call(util.keepalived_lvs_dir()),
                mock.call(util.keepalived_backend_check_script_dir())
            ]
            m_os_mkdir.assert_has_calls(os_mkdir_calls)

            mock_install_netns.assert_called_once()
            systemctl_calls = [
                mock.call(consts.ENABLE,
                          consts.AMP_NETNS_SVC_PREFIX),
                mock.call(consts.ENABLE,
                          'octavia-keepalivedlvs-%s' % str(self.FAKE_ID)),
            ]
            mock_systemctl.assert_has_calls(systemctl_calls)

            m_os_chmod.assert_called_with(
                util.keepalived_backend_check_script_path(), stat.S_IEXEC)
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            systemd_cfg_path = util.keepalived_lvs_init_path(
                consts.INIT_SYSTEMD, self.FAKE_ID)
            m_open_calls = [
                mock.call(cfg_path, flags, mode),
                mock.call(systemd_cfg_path, flags, mode)
            ]
            m_open.assert_has_calls(m_open_calls)
            m_fdopen.assert_any_call('TEST-WRITE-CFG', 'wb')
            m_fdopen.assert_any_call('TEST-WRITE-SYSINIT', 'w')
            self.assertEqual(500, res.status_code)

    @mock.patch('subprocess.check_output')
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'keepalivedlvs.KeepalivedLvs.'
                '_check_udp_listener_exists')
    def test_manage_udp_listener(self, mock_udp_exist, mock_check_output):
        res = self.test_keepalivedlvs.manage_udp_listener(self.FAKE_ID,
                                                          'start')
        cmd = ("/usr/sbin/service octavia-keepalivedlvs-{listener_id}"
               " {action}".format(listener_id=self.FAKE_ID, action='start'))
        mock_check_output.assert_called_once_with(cmd.split(),
                                                  stderr=subprocess.STDOUT)
        self.assertEqual(202, res.status_code)

        res = self.test_keepalivedlvs.manage_udp_listener(self.FAKE_ID,
                                                          'restart')
        self.assertEqual(400, res.status_code)

        mock_check_output.side_effect = subprocess.CalledProcessError(1,
                                                                      'blah!')

        res = self.test_keepalivedlvs.manage_udp_listener(self.FAKE_ID,
                                                          'start')
        self.assertEqual(500, res.status_code)

    @mock.patch('octavia.amphorae.backends.utils.keepalivedlvs_query.'
                'get_listener_realserver_mapping')
    @mock.patch('subprocess.check_output', return_value=PROC_CONTENT)
    @mock.patch('os.path.exists')
    def test_get_udp_listener_status(self, m_exist, m_check_output,
                                     mget_mapping):
        mget_mapping.return_value = (
            True, {'10.0.0.99:82': {'status': 'UP',
                                    'Weight': '13',
                                    'InActConn': '0',
                                    'ActiveConn': '0'},
                   '10.0.0.98:82': {'status': 'UP',
                                    'Weight': '13',
                                    'InActConn': '0',
                                    'ActiveConn': '0'}})
        pid_path = ('/var/lib/octavia/lvs/octavia-'
                    'keepalivedlvs-%s.pid' % self.FAKE_ID)
        self.useFixture(test_utils.OpenFixture(pid_path,
                                               self.NORMAL_PID_CONTENT))

        cfg_path = ('/var/lib/octavia/lvs/octavia-'
                    'keepalivedlvs-%s.conf' % self.FAKE_ID)
        self.useFixture(test_utils.OpenFixture(cfg_path,
                                               self.NORMAL_CFG_CONTENT))

        m_exist.return_value = True
        expected = {'status': 'ACTIVE',
                    'pools': [{'lvs': {
                        'members': {self.MEMBER_ID1: 'UP',
                                    self.MEMBER_ID2: 'UP'},
                        'status': 'UP',
                        'uuid': self.POOL_ID}}],
                    'type': 'UDP', 'uuid': self.FAKE_ID}
        res = self.test_keepalivedlvs.get_udp_listener_status(self.FAKE_ID)
        self.assertEqual(200, res.status_code)
        self.assertEqual(expected, res.json)

    @mock.patch('os.path.exists')
    def test_get_udp_listener_status_no_exists(self, m_exist):
        m_exist.return_value = False
        self.assertRaises(exceptions.HTTPException,
                          self.test_keepalivedlvs.get_udp_listener_status,
                          self.FAKE_ID)

    @mock.patch('os.path.exists')
    def test_get_udp_listener_status_offline_status(self, m_exist):
        m_exist.return_value = True
        pid_path = ('/var/lib/octavia/lvs/octavia-'
                    'keepalivedlvs-%s.pid' % self.FAKE_ID)
        self.useFixture(test_utils.OpenFixture(pid_path,
                                               self.NORMAL_PID_CONTENT))
        cfg_path = ('/var/lib/octavia/lvs/octavia-'
                    'keepalivedlvs-%s.conf' % self.FAKE_ID)
        self.useFixture(test_utils.OpenFixture(cfg_path, 'NO VS CONFIG'))
        expected = {'status': 'OFFLINE',
                    'type': 'UDP',
                    'uuid': self.FAKE_ID}
        res = self.test_keepalivedlvs.get_udp_listener_status(self.FAKE_ID)
        self.assertEqual(200, res.status_code)
        self.assertEqual(expected, res.json)

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_udp_listeners', return_value=[LISTENER_ID])
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_os_init_system', return_value=consts.INIT_SYSTEMD)
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_keepalivedlvs_pid', return_value="12345")
    @mock.patch('subprocess.check_output')
    @mock.patch('os.remove')
    @mock.patch('os.path.exists')
    def test_delete_udp_listener(self, m_exist, m_remove, m_check_output,
                                 mget_pid, m_init_sys, mget_udp_listeners):
        m_exist.return_value = True
        res = self.test_keepalivedlvs.delete_udp_listener(self.FAKE_ID)

        cmd1 = ("/usr/sbin/service "
                "octavia-keepalivedlvs-{0} stop".format(self.FAKE_ID))
        cmd2 = ("systemctl disable "
                "octavia-keepalivedlvs-{list}".format(list=self.FAKE_ID))
        calls = [
            mock.call(cmd1.split(), stderr=subprocess.STDOUT),
            mock.call(cmd2.split(), stderr=subprocess.STDOUT)
        ]
        m_check_output.assert_has_calls(calls)
        self.assertEqual(200, res.status_code)

    @mock.patch.object(keepalivedlvs, "webob")
    @mock.patch('os.path.exists')
    def test_delete_udp_listener_not_exist(self, m_exist, m_webob):
        m_exist.return_value = False
        self.test_keepalivedlvs.delete_udp_listener(self.FAKE_ID)
        calls = [
            mock.call(
                json=dict(message='UDP Listener Not Found',
                          details="No UDP listener with UUID: "
                                  "{0}".format(self.FAKE_ID)), status=404),
            mock.call(json={'message': 'OK'})
        ]
        m_webob.Response.assert_has_calls(calls)

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_keepalivedlvs_pid', return_value="12345")
    @mock.patch('subprocess.check_output')
    @mock.patch('os.path.exists')
    def test_delete_udp_listener_stop_service_fail(self, m_exist,
                                                   m_check_output, mget_pid):
        m_exist.return_value = True
        m_check_output.side_effect = subprocess.CalledProcessError(1,
                                                                   'Woops!')
        res = self.test_keepalivedlvs.delete_udp_listener(self.FAKE_ID)
        self.assertEqual(500, res.status_code)
        self.assertEqual({'message': 'Error stopping keepalivedlvs',
                          'details': None}, res.json)

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_os_init_system', return_value=consts.INIT_SYSVINIT)
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_keepalivedlvs_pid', return_value="12345")
    @mock.patch('subprocess.check_output')
    @mock.patch('os.remove')
    @mock.patch('os.path.exists')
    def test_delete_udp_listener_disable_service_fail(self, m_exist, m_remove,
                                                      m_check_output, mget_pid,
                                                      m_init_sys):
        m_exist.return_value = True
        m_check_output.side_effect = [True,
                                      subprocess.CalledProcessError(
                                          1, 'Woops!')]
        res = self.test_keepalivedlvs.delete_udp_listener(self.FAKE_ID)
        self.assertEqual(500, res.status_code)
        self.assertEqual({
            'message': 'Error disabling '
                       'octavia-keepalivedlvs-%s service' % self.FAKE_ID,
            'details': None}, res.json)

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_os_init_system')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_keepalivedlvs_pid', return_value="12345")
    @mock.patch('subprocess.check_output')
    @mock.patch('os.remove')
    @mock.patch('os.path.exists')
    def test_delete_udp_listener_unsupported_sysinit(self, m_exist, m_remove,
                                                     m_check_output, mget_pid,
                                                     m_init_sys):
        m_exist.return_value = True
        self.assertRaises(
            util.UnknownInitError, self.test_keepalivedlvs.delete_udp_listener,
            self.FAKE_ID)
