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
import json
import os
import random
import socket
import stat
import subprocess

import mock
import netifaces
import six

from octavia.amphorae.backends.agent import api_server
from octavia.amphorae.backends.agent.api_server import certificate_update
from octavia.amphorae.backends.agent.api_server import listener
from octavia.amphorae.backends.agent.api_server import server
from octavia.amphorae.backends.agent.api_server import util
from octavia.common import constants as consts
from octavia.common import utils as octavia_utils
from octavia.tests.common import utils as test_utils
import octavia.tests.unit.base as base


RANDOM_ERROR = 'random error'
OK = dict(message='OK')


class TestServerTestCase(base.TestCase):
    app = None

    def setUp(self):
        self.app = server.app.test_client()
        super(TestServerTestCase, self).setUp()

    @mock.patch('os.path.exists')
    @mock.patch('os.makedirs')
    @mock.patch('os.rename')
    @mock.patch('subprocess.check_output')
    @mock.patch('os.remove')
    def test_haproxy(self, mock_remove, mock_subprocess, mock_rename,
                     mock_makedirs, mock_exists):

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mock_exists.return_value = True
        file_name = '/var/lib/octavia/123/haproxy.cfg.new'
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open

        # happy case upstart file exists
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            rv = self.app.put('/' + api_server.VERSION +
                              '/listeners/amp_123/123/haproxy',
                              data='test')
            mode = stat.S_IRUSR | stat.S_IWUSR
            mock_open.assert_called_with(file_name, flags, mode)
            mock_fdopen.assert_called_with(123, 'w')
            self.assertEqual(202, rv.status_code)
            handle = m()
            handle.write.assert_called_once_with(six.b('test'))
            mock_subprocess.assert_called_once_with(
                "haproxy -c -L {peer} -f {config_file}".format(
                    config_file=file_name,
                    peer=(octavia_utils.
                          base64_sha1_string('amp_123').rstrip('='))).split(),
                stderr=-2)
            mock_rename.assert_called_once_with(
                '/var/lib/octavia/123/haproxy.cfg.new',
                '/var/lib/octavia/123/haproxy.cfg')

        # exception writing
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        m.side_effect = IOError()  # open crashes
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            rv = self.app.put('/' + api_server.VERSION +
                              '/listeners/amp_123/123/haproxy',
                              data='test')
            self.assertEqual(500, rv.status_code)

        # check if files get created
        mock_exists.return_value = False
        init_path = '/etc/init/haproxy-123.conf'
        m = self.useFixture(test_utils.OpenFixture(init_path)).mock_open
        # happy case upstart file exists
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            rv = self.app.put('/' + api_server.VERSION +
                              '/listeners/amp_123/123/haproxy',
                              data='test')

            self.assertEqual(202, rv.status_code)
            mode = (stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP |
                    stat.S_IROTH | stat.S_IXOTH)
            mock_open.assert_called_with(init_path, flags, mode)
            mock_fdopen.assert_called_with(123, 'w')
            handle = mock_fdopen()
            handle.write.assert_any_call(six.b('test'))
            # skip the template stuff
            mock_makedirs.assert_called_with('/var/lib/octavia/123')

        # unhappy case haproxy check fails
        mock_exists.return_value = True
        mock_subprocess.side_effect = [subprocess.CalledProcessError(
            7, 'test', RANDOM_ERROR)]
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            rv = self.app.put('/' + api_server.VERSION +
                              '/listeners/amp_123/123/haproxy',
                              data='test')
            self.assertEqual(400, rv.status_code)
            self.assertEqual(
                {'message': 'Invalid request', u'details': u'random error'},
                json.loads(rv.data.decode('utf-8')))
            mode = stat.S_IRUSR | stat.S_IWUSR
            mock_open.assert_called_with(file_name, flags, mode)
            mock_fdopen.assert_called_with(123, 'w')
            handle = mock_fdopen()
            handle.write.assert_called_with(six.b('test'))
            mock_subprocess.assert_called_with(
                "haproxy -c -L {peer} -f {config_file}".format(
                    config_file=file_name,
                    peer=(octavia_utils.
                          base64_sha1_string('amp_123').rstrip('='))).split(),
                stderr=-2)
            mock_remove.assert_called_once_with(file_name)

    @mock.patch('os.path.exists')
    @mock.patch('octavia.amphorae.backends.agent.api_server.listener.'
                'vrrp_check_script_update')
    @mock.patch('subprocess.check_output')
    def test_start(self, mock_subprocess, mock_vrrp, mock_exists):
        rv = self.app.put('/' + api_server.VERSION + '/listeners/123/error')
        self.assertEqual(400, rv.status_code)
        self.assertEqual(
            {'message': 'Invalid Request',
             'details': 'Unknown action: error', },
            json.loads(rv.data.decode('utf-8')))

        mock_exists.return_value = False
        rv = self.app.put('/' + api_server.VERSION + '/listeners/123/start')
        self.assertEqual(404, rv.status_code)
        self.assertEqual(
            {'message': 'Listener Not Found',
             'details': 'No listener with UUID: 123'},
            json.loads(rv.data.decode('utf-8')))
        mock_exists.assert_called_with('/var/lib/octavia/123/haproxy.cfg')

        mock_exists.return_value = True
        rv = self.app.put('/' + api_server.VERSION + '/listeners/123/start')
        self.assertEqual(202, rv.status_code)
        self.assertEqual(
            {'message': 'OK',
             'details': 'Configuration file is valid\nhaproxy daemon for'
                        ' 123 started'},
            json.loads(rv.data.decode('utf-8')))
        mock_subprocess.assert_called_with(
            ['/usr/sbin/service', 'haproxy-123', 'start'], stderr=-2)

        mock_exists.return_value = True
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            7, 'test', RANDOM_ERROR)
        rv = self.app.put('/' + api_server.VERSION + '/listeners/123/start')
        self.assertEqual(500, rv.status_code)
        self.assertEqual(
            {
                'message': 'Error starting haproxy',
                'details': RANDOM_ERROR,
            }, json.loads(rv.data.decode('utf-8')))
        mock_subprocess.assert_called_with(
            ['/usr/sbin/service', 'haproxy-123', 'start'], stderr=-2)

    @mock.patch('os.path.exists')
    @mock.patch('octavia.amphorae.backends.agent.api_server.listener.'
                'vrrp_check_script_update')
    @mock.patch('octavia.amphorae.backends.agent.api_server.listener.'
                '_check_haproxy_status')
    @mock.patch('subprocess.check_output')
    def test_reload(self, mock_subprocess, mock_haproxy_status,
                    mock_vrrp, mock_exists):

        # Process running so reload
        mock_exists.return_value = True
        mock_haproxy_status.return_value = consts.ACTIVE
        rv = self.app.put('/' + api_server.VERSION + '/listeners/123/reload')
        self.assertEqual(202, rv.status_code)
        self.assertEqual(
            {'message': 'OK',
             'details': 'Listener 123 reloaded'},
            json.loads(rv.data.decode('utf-8')))
        mock_subprocess.assert_called_with(
            ['/usr/sbin/service', 'haproxy-123', 'reload'], stderr=-2)

        # Process not running so start
        mock_exists.return_value = True
        mock_haproxy_status.return_value = consts.OFFLINE
        rv = self.app.put('/' + api_server.VERSION + '/listeners/123/reload')
        self.assertEqual(202, rv.status_code)
        self.assertEqual(
            {'message': 'OK',
             'details': 'Configuration file is valid\nhaproxy daemon for'
                        ' 123 started'},
            json.loads(rv.data.decode('utf-8')))
        mock_subprocess.assert_called_with(
            ['/usr/sbin/service', 'haproxy-123', 'start'], stderr=-2)

    @mock.patch('socket.gethostname')
    @mock.patch('subprocess.check_output')
    def test_info(self, mock_subbprocess, mock_hostname):
        mock_hostname.side_effect = ['test-host']
        mock_subbprocess.side_effect = [
            """Package: haproxy
            Status: install ok installed
            Priority: optional
            Section: net
            Installed-Size: 803
            Maintainer: Ubuntu Developers
            Architecture: amd64
            Version: 1.4.24-2
            """]
        rv = self.app.get('/' + api_server.VERSION + '/info')

        self.assertEqual(200, rv.status_code)
        self.assertEqual(dict(
            api_version='0.5',
            haproxy_version='1.4.24-2',
            hostname='test-host'),
            json.loads(rv.data.decode('utf-8')))

    @mock.patch('os.path.exists')
    @mock.patch('subprocess.check_output')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.' +
                'get_haproxy_pid')
    @mock.patch('shutil.rmtree')
    @mock.patch('os.remove')
    def test_delete_listener(self, mock_remove, mock_rmtree, mock_pid,
                             mock_check_output, mock_exists):
        mock_exists.return_value = False
        rv = self.app.delete('/' + api_server.VERSION + '/listeners/123')
        self.assertEqual(404, rv.status_code)
        self.assertEqual(
            {'message': 'Listener Not Found',
             'details': 'No listener with UUID: 123'},
            json.loads(rv.data.decode('utf-8')))
        mock_exists.assert_called_with('/var/lib/octavia/123/haproxy.cfg')

        # service is stopped + no upstart script
        mock_exists.side_effect = [True, False, False]
        rv = self.app.delete('/' + api_server.VERSION + '/listeners/123')
        self.assertEqual(200, rv.status_code)
        self.assertEqual({u'message': u'OK'},
                         json.loads(rv.data.decode('utf-8')))
        mock_rmtree.assert_called_with('/var/lib/octavia/123')
        mock_exists.assert_called_with('/etc/init/haproxy-123.conf')
        mock_exists.assert_any_call('/var/lib/octavia/123/123.pid')

        # service is stopped + upstart script
        mock_exists.side_effect = [True, False, True]
        rv = self.app.delete('/' + api_server.VERSION + '/listeners/123')
        self.assertEqual(200, rv.status_code)
        self.assertEqual({u'message': u'OK'},
                         json.loads(rv.data.decode('utf-8')))
        mock_remove.assert_called_once_with('/etc/init/haproxy-123.conf')

        # service is running + upstart script
        mock_exists.side_effect = [True, True, True, True]
        mock_pid.return_value = '456'
        rv = self.app.delete('/' + api_server.VERSION + '/listeners/123')
        self.assertEqual(200, rv.status_code)
        self.assertEqual({u'message': u'OK'},
                         json.loads(rv.data.decode('utf-8')))
        mock_pid.assert_called_once_with('123')
        mock_check_output.assert_called_once_with(
            ['/usr/sbin/service', 'haproxy-123', 'stop'], stderr=-2)

        # service is running + stopping fails
        mock_exists.side_effect = [True, True, True]
        mock_check_output.side_effect = subprocess.CalledProcessError(
            7, 'test', RANDOM_ERROR)
        rv = self.app.delete('/' + api_server.VERSION + '/listeners/123')
        self.assertEqual(500, rv.status_code)
        self.assertEqual(
            {'details': 'random error', 'message': 'Error stopping haproxy'},
            json.loads(rv.data.decode('utf-8')))
        # that's the last call before exception
        mock_exists.assert_called_with('/proc/456')

    @mock.patch('os.path.exists')
    def test_get_haproxy(self, mock_exists):
        CONTENT = "bibble\nbibble"
        mock_exists.side_effect = [False]
        rv = self.app.get('/' + api_server.VERSION + '/listeners/123/haproxy')
        self.assertEqual(404, rv.status_code)

        mock_exists.side_effect = [True]

        path = util.config_path('123')
        self.useFixture(test_utils.OpenFixture(path, CONTENT))

        rv = self.app.get('/' + api_server.VERSION +
                          '/listeners/123/haproxy')
        self.assertEqual(200, rv.status_code)
        self.assertEqual(six.b(CONTENT), rv.data)
        self.assertEqual('text/plain; charset=utf-8',
                         rv.headers['Content-Type'])

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_listeners')
    @mock.patch('octavia.amphorae.backends.agent.api_server.listener.'
                '_check_listener_status')
    @mock.patch('octavia.amphorae.backends.agent.api_server.listener.'
                '_parse_haproxy_file')
    def test_get_all_listeners(self, mock_parse, mock_status, mock_listener):
        # no listeners
        mock_listener.side_effect = [[]]
        rv = self.app.get('/' + api_server.VERSION + '/listeners')

        self.assertEqual(200, rv.status_code)
        self.assertFalse(json.loads(rv.data.decode('utf-8')))

        # one listener ACTIVE
        mock_listener.side_effect = [['123']]
        mock_parse.side_effect = [{'mode': 'test'}]
        mock_status.side_effect = [consts.ACTIVE]
        rv = self.app.get('/' + api_server.VERSION + '/listeners')

        self.assertEqual(200, rv.status_code)
        self.assertEqual(
            [{'status': consts.ACTIVE, 'type': 'test', 'uuid': '123'}],
            json.loads(rv.data.decode('utf-8')))

        # two listener one ACTIVE, one ERROR
        mock_listener.side_effect = [['123', '456']]
        mock_parse.side_effect = [{'mode': 'test'}, {'mode': 'http'}]
        mock_status.side_effect = [consts.ACTIVE, consts.ERROR]
        rv = self.app.get('/' + api_server.VERSION + '/listeners')

        self.assertEqual(200, rv.status_code)
        self.assertEqual(
            [{'status': consts.ACTIVE, 'type': 'test', 'uuid': '123'},
             {'status': consts.ERROR, 'type': '', 'uuid': '456'}],
            json.loads(rv.data.decode('utf-8')))

    @mock.patch('octavia.amphorae.backends.agent.api_server.listener.'
                '_check_listener_status')
    @mock.patch('octavia.amphorae.backends.agent.api_server.listener.'
                '_parse_haproxy_file')
    @mock.patch('octavia.amphorae.backends.utils.haproxy_query.HAProxyQuery')
    @mock.patch('os.path.exists')
    def test_get_listener(self, mock_exists, mock_query, mock_parse,
                          mock_status):
        # Listener not found
        mock_exists.side_effect = [False]
        rv = self.app.get('/' + api_server.VERSION + '/listeners/123')
        self.assertEqual(404, rv.status_code)
        self.assertEqual(
            {'message': 'Listener Not Found',
             'details': 'No listener with UUID: 123'},
            json.loads(rv.data.decode('utf-8')))

        # Listener not ACTIVE
        mock_parse.side_effect = [dict(mode='test')]
        mock_status.side_effect = [consts.ERROR]
        mock_exists.side_effect = [True]
        rv = self.app.get('/' + api_server.VERSION + '/listeners/123')
        self.assertEqual(200, rv.status_code)
        self.assertEqual(dict(
            status=consts.ERROR,
            type='',
            uuid='123'), json.loads(rv.data.decode('utf-8')))

        # Listener ACTIVE
        mock_parse.side_effect = [dict(mode='test', stats_socket='blah')]
        mock_status.side_effect = [consts.ACTIVE]
        mock_exists.side_effect = [True]
        mock_pool = mock.Mock()
        mock_query.side_effect = [mock_pool]
        mock_pool.get_pool_status.side_effect = [
            {'tcp-servers': {
                'status': 'DOWN',
                'uuid': 'tcp-servers',
                'members': [
                    {'id-34833': 'DOWN'},
                    {'id-34836': 'DOWN'}]}}]
        rv = self.app.get('/' + api_server.VERSION + '/listeners/123')
        self.assertEqual(200, rv.status_code)
        self.assertEqual(dict(
            status=consts.ACTIVE,
            type='test',
            uuid='123',
            pools=[dict(
                status=consts.DOWN,
                uuid='tcp-servers',
                members=[
                    {u'id-34833': u'DOWN'},
                    {u'id-34836': u'DOWN'}])]),
            json.loads(rv.data.decode('utf-8')))

    @mock.patch('os.path.exists')
    @mock.patch('os.remove')
    def test_delete_cert(self, mock_remove, mock_exists):
        mock_exists.side_effect = [False]
        rv = self.app.delete('/' + api_server.VERSION +
                             '/listeners/123/certificates/test.pem')
        self.assertEqual(404, rv.status_code)
        self.assertEqual(dict(
            details='No certificate with filename: test.pem',
            message='Certificate Not Found'),
            json.loads(rv.data.decode('utf-8')))
        mock_exists.assert_called_once_with(
            '/var/lib/octavia/certs/123/test.pem')

        # wrong file name
        mock_exists.side_effect = [True]
        rv = self.app.put('/' + api_server.VERSION +
                          '/listeners/123/certificates/test.bla',
                          data='TestTest')
        self.assertEqual(400, rv.status_code)

        mock_exists.side_effect = [True]
        rv = self.app.delete('/' + api_server.VERSION +
                             '/listeners/123/certificates/test.pem')
        self.assertEqual(200, rv.status_code)
        self.assertEqual(OK, json.loads(rv.data.decode('utf-8')))
        mock_remove.assert_called_once_with(
            '/var/lib/octavia/certs/123/test.pem')

    @mock.patch('os.path.exists')
    def test_get_certificate_md5(self, mock_exists):
        CONTENT = "TestTest"

        mock_exists.side_effect = [False]
        rv = self.app.get('/' + api_server.VERSION +
                          '/listeners/123/certificates/test.pem')
        self.assertEqual(404, rv.status_code)
        self.assertEqual(dict(
            details='No certificate with filename: test.pem',
            message='Certificate Not Found'),
            json.loads(rv.data.decode('utf-8')))
        mock_exists.assert_called_with('/var/lib/octavia/certs/123/test.pem')

        # wrong file name
        mock_exists.side_effect = [True]
        rv = self.app.put('/' + api_server.VERSION +
                          '/listeners/123/certificates/test.bla',
                          data='TestTest')
        self.assertEqual(400, rv.status_code)

        mock_exists.return_value = True
        mock_exists.side_effect = None
        path = listener._cert_file_path('123', 'test.pem')
        self.useFixture(test_utils.OpenFixture(path, CONTENT))

        rv = self.app.get('/' + api_server.VERSION +
                          '/listeners/123/certificates/test.pem')
        self.assertEqual(200, rv.status_code)
        self.assertEqual(dict(md5sum=hashlib.md5(six.b(CONTENT)).hexdigest()),
                         json.loads(rv.data.decode('utf-8')))

    @mock.patch('os.path.exists')
    @mock.patch('os.makedirs')
    def test_upload_certificate_md5(self, mock_makedir, mock_exists):

        # wrong file name
        rv = self.app.put('/' + api_server.VERSION +
                          '/listeners/123/certificates/test.bla',
                          data='TestTest')
        self.assertEqual(400, rv.status_code)

        mock_exists.return_value = True
        path = listener._cert_file_path('123', 'test.pem')
        m = self.useFixture(test_utils.OpenFixture(path)).mock_open
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):

            rv = self.app.put('/' + api_server.VERSION +
                              '/listeners/123/certificates/test.pem',
                              data='TestTest')
            self.assertEqual(200, rv.status_code)
            self.assertEqual(OK, json.loads(rv.data.decode('utf-8')))
            handle = m()
            handle.write.assert_called_once_with(six.b('TestTest'))

        mock_exists.return_value = False
        m = self.useFixture(test_utils.OpenFixture(path)).mock_open

        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            rv = self.app.put('/' + api_server.VERSION +
                              '/listeners/123/certificates/test.pem',
                              data='TestTest')
            self.assertEqual(200, rv.status_code)
            self.assertEqual(OK, json.loads(rv.data.decode('utf-8')))
            handle = m()
            handle.write.assert_called_once_with(six.b('TestTest'))
            mock_makedir.assert_called_once_with('/var/lib/octavia/certs/123')

    def test_upload_server_certificate(self):
        certificate_update.BUFFER = 5  # test the while loop
        path = '/etc/octavia/certs/server.pem'
        m = self.useFixture(test_utils.OpenFixture(path)).mock_open
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            rv = self.app.put('/' + api_server.VERSION +
                              '/certificate',
                              data='TestTest')
            self.assertEqual(202, rv.status_code)
            self.assertEqual(OK, json.loads(rv.data.decode('utf-8')))
            handle = m()
            handle.write.assert_any_call(six.b('TestT'))
            handle.write.assert_any_call(six.b('est'))

    @mock.patch('netifaces.interfaces')
    @mock.patch('netifaces.ifaddresses')
    @mock.patch('pyroute2.IPRoute')
    @mock.patch('pyroute2.NetNS')
    @mock.patch('subprocess.check_output')
    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'plug._netns_interface_exists')
    def test_plug_network(self, mock_int_exists, mock_check_output, mock_netns,
                          mock_pyroute2, mock_ifaddress, mock_interfaces):
        port_info = {'mac_address': '123'}
        test_int_num = random.randint(0, 9999)

        mock_int_exists.return_value = False
        netns_handle = mock_netns.return_value.__enter__.return_value
        netns_handle.get_links.return_value = [0] * test_int_num

        test_int_num = str(test_int_num)

        # Interface already plugged
        mock_int_exists.return_value = True
        rv = self.app.post('/' + api_server.VERSION + "/plug/network",
                           content_type='application/json',
                           data=json.dumps(port_info))
        self.assertEqual(409, rv.status_code)
        self.assertEqual(dict(message="Interface already exists"),
                         json.loads(rv.data.decode('utf-8')))
        mock_int_exists.return_value = False

        # No interface at all
        mock_interfaces.side_effect = [[]]
        rv = self.app.post('/' + api_server.VERSION + "/plug/network",
                           content_type='application/json',
                           data=json.dumps(port_info))
        self.assertEqual(404, rv.status_code)
        self.assertEqual(dict(details="No suitable network interface found"),
                         json.loads(rv.data.decode('utf-8')))

        # No interface down
        mock_interfaces.side_effect = [['blah']]
        mock_ifaddress.side_effect = [[netifaces.AF_INET]]
        rv = self.app.post('/' + api_server.VERSION + "/plug/network",
                           content_type='application/json',
                           data=json.dumps(port_info))
        self.assertEqual(404, rv.status_code)
        self.assertEqual(dict(details="No suitable network interface found"),
                         json.loads(rv.data.decode('utf-8')))
        mock_ifaddress.assert_called_once_with('blah')

        # One Interface down, Happy Path
        mock_interfaces.side_effect = [['blah']]
        mock_ifaddress.side_effect = [[netifaces.AF_LINK],
                                      {netifaces.AF_LINK: [{'addr': '123'}]}]

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        file_name = '/etc/netns/{0}/network/interfaces.d/eth{1}.cfg'.format(
            consts.AMPHORA_NAMESPACE, test_int_num)
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            rv = self.app.post('/' + api_server.VERSION + "/plug/network",
                               content_type='application/json',
                               data=json.dumps(port_info))
            self.assertEqual(202, rv.status_code)

            mock_open.assert_any_call(file_name, flags, mode)
            mock_fdopen.assert_any_call(123, 'w')

            plug_inf_file = '/var/lib/octavia/plugged_interfaces'
            flags = os.O_RDWR | os.O_CREAT
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_any_call(plug_inf_file, flags, mode)
            mock_fdopen.assert_any_call(123, 'r+')

            handle = m()
            handle.write.assert_any_call(
                '\n# Generated by Octavia agent\n'
                'auto eth' + test_int_num +
                '\niface eth' + test_int_num + ' inet dhcp\n'
                'auto eth' + test_int_num + ':0\n'
                'iface eth' + test_int_num + ':0 inet6 auto\n')
            mock_check_output.assert_called_with(
                ['ip', 'netns', 'exec', consts.AMPHORA_NAMESPACE,
                 'ifup', 'eth' + test_int_num], stderr=-2)

        # fixed IPs happy path
        port_info = {'mac_address': '123', 'fixed_ips': [
            {'ip_address': '10.0.0.5', 'subnet_cidr': '10.0.0.0/24'}]}
        mock_interfaces.side_effect = [['blah']]
        mock_ifaddress.side_effect = [[netifaces.AF_LINK],
                                      {netifaces.AF_LINK: [{'addr': '123'}]}]

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        file_name = '/etc/netns/{0}/network/interfaces.d/eth{1}.cfg'.format(
            consts.AMPHORA_NAMESPACE, test_int_num)
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            rv = self.app.post('/' + api_server.VERSION + "/plug/network",
                               content_type='application/json',
                               data=json.dumps(port_info))
            self.assertEqual(202, rv.status_code)

            mock_open.assert_any_call(file_name, flags, mode)
            mock_fdopen.assert_any_call(123, 'w')

            plug_inf_file = '/var/lib/octavia/plugged_interfaces'
            flags = os.O_RDWR | os.O_CREAT
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_any_call(plug_inf_file, flags, mode)
            mock_fdopen.assert_any_call(123, 'r+')

            handle = m()
            handle.write.assert_any_call(
                '\n\n# Generated by Octavia agent\n'
                'auto eth' + test_int_num +
                '\niface eth' + test_int_num + ' inet static\n' +
                'address 10.0.0.5\nbroadcast 10.0.0.255\n' +
                'netmask 255.255.255.0\n')
            mock_check_output.assert_called_with(
                ['ip', 'netns', 'exec', consts.AMPHORA_NAMESPACE,
                 'ifup', 'eth' + test_int_num], stderr=-2)

        # fixed IPs happy path IPv6
        port_info = {'mac_address': '123', 'fixed_ips': [
            {'ip_address': '2001:db8::2', 'subnet_cidr': '2001:db8::/32'}]}
        mock_interfaces.side_effect = [['blah']]
        mock_ifaddress.side_effect = [[netifaces.AF_LINK],
                                      {netifaces.AF_LINK: [{'addr': '123'}]}]

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        file_name = '/etc/netns/{0}/network/interfaces.d/eth{1}.cfg'.format(
            consts.AMPHORA_NAMESPACE, test_int_num)
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            rv = self.app.post('/' + api_server.VERSION + "/plug/network",
                               content_type='application/json',
                               data=json.dumps(port_info))
            self.assertEqual(202, rv.status_code)

            mock_open.assert_any_call(file_name, flags, mode)
            mock_fdopen.assert_any_call(123, 'w')

            plug_inf_file = '/var/lib/octavia/plugged_interfaces'
            flags = os.O_RDWR | os.O_CREAT
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_any_call(plug_inf_file, flags, mode)
            mock_fdopen.assert_any_call(123, 'r+')

            handle = m()
            handle.write.assert_any_call(
                '\n\n# Generated by Octavia agent\n'
                'auto eth' + test_int_num +
                '\niface eth' + test_int_num + ' inet6 static\n' +
                'address 2001:0db8:0000:0000:0000:0000:0000:0002\n'
                'broadcast 2001:0db8:ffff:ffff:ffff:ffff:ffff:ffff\n' +
                'netmask 32\n')
            mock_check_output.assert_called_with(
                ['ip', 'netns', 'exec', consts.AMPHORA_NAMESPACE,
                 'ifup', 'eth' + test_int_num], stderr=-2)

        # fixed IPs, bogus IP
        port_info = {'mac_address': '123', 'fixed_ips': [
            {'ip_address': '10005', 'subnet_cidr': '10.0.0.0/24'}]}
        mock_interfaces.side_effect = [['blah']]
        mock_ifaddress.side_effect = [[netifaces.AF_LINK],
                                      {netifaces.AF_LINK: [{'addr': '123'}]}]

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        file_name = '/etc/netns/{0}/network/interfaces.d/eth{1}.cfg'.format(
            consts.AMPHORA_NAMESPACE, test_int_num)
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            rv = self.app.post('/' + api_server.VERSION + "/plug/network",
                               content_type='application/json',
                               data=json.dumps(port_info))
            self.assertEqual(400, rv.status_code)

        # same as above but ifup fails
        port_info = {'mac_address': '123', 'fixed_ips': [
            {'ip_address': '10.0.0.5', 'subnet_cidr': '10.0.0.0/24'}]}
        mock_interfaces.side_effect = [['blah']]
        mock_ifaddress.side_effect = [[netifaces.AF_LINK],
                                      {netifaces.AF_LINK: [{'addr': '123'}]}]
        mock_check_output.side_effect = [subprocess.CalledProcessError(
            7, 'test', RANDOM_ERROR), subprocess.CalledProcessError(
            7, 'test', RANDOM_ERROR)]

        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            rv = self.app.post('/' + api_server.VERSION + "/plug/network",
                               content_type='application/json',
                               data=json.dumps(port_info))
            self.assertEqual(500, rv.status_code)
            self.assertEqual(
                {'details': RANDOM_ERROR,
                 'message': 'Error plugging network'},
                json.loads(rv.data.decode('utf-8')))

    @mock.patch('netifaces.interfaces')
    @mock.patch('netifaces.ifaddresses')
    @mock.patch('pyroute2.IPRoute')
    @mock.patch('pyroute2.NetNS')
    @mock.patch('subprocess.check_output')
    def test_plug_network_host_routes(self, mock_check_output, mock_netns,
                                      mock_pyroute2, mock_ifaddress,
                                      mock_interfaces):
        SUBNET_CIDR = '192.0.2.0/24'
        BROADCAST = '192.0.2.255'
        NETMASK = '255.255.255.0'
        IP = '192.0.1.5'
        MAC = '123'
        DEST1 = '198.51.100.0/24'
        DEST2 = '203.0.113.0/24'
        NEXTHOP = '192.0.2.1'

        netns_handle = mock_netns.return_value.__enter__.return_value
        netns_handle.get_links.return_value = [{
            'attrs': [['IFLA_IFNAME', consts.NETNS_PRIMARY_INTERFACE]]}]

        port_info = {'mac_address': MAC, 'fixed_ips': [
            {'ip_address': IP, 'subnet_cidr': SUBNET_CIDR,
             'host_routes': [{'destination': DEST1, 'nexthop': NEXTHOP},
                             {'destination': DEST2, 'nexthop': NEXTHOP}]}]}
        mock_interfaces.side_effect = [['blah']]
        mock_ifaddress.side_effect = [[netifaces.AF_LINK],
                                      {netifaces.AF_LINK: [{'addr': '123'}]}]

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        file_name = '/etc/netns/{0}/network/interfaces.d/{1}.cfg'.format(
            consts.AMPHORA_NAMESPACE, consts.NETNS_PRIMARY_INTERFACE)
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            rv = self.app.post('/' + api_server.VERSION + "/plug/network",
                               content_type='application/json',
                               data=json.dumps(port_info))
            self.assertEqual(202, rv.status_code)

            mock_open.assert_any_call(file_name, flags, mode)
            mock_fdopen.assert_any_call(123, 'w')

            plug_inf_file = '/var/lib/octavia/plugged_interfaces'
            flags = os.O_RDWR | os.O_CREAT
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_any_call(plug_inf_file, flags, mode)
            mock_fdopen.assert_any_call(123, 'r+')

            handle = m()
            handle.write.assert_any_call(
                '\n\n# Generated by Octavia agent\n'
                'auto ' + consts.NETNS_PRIMARY_INTERFACE +
                '\niface ' + consts.NETNS_PRIMARY_INTERFACE +
                ' inet static\n' +
                'address ' + IP + '\nbroadcast ' + BROADCAST + '\n' +
                'netmask ' + NETMASK + '\n' +
                'up route add -net ' + DEST1 + ' gw ' + NEXTHOP +
                ' dev ' + consts.NETNS_PRIMARY_INTERFACE + '\n'
                'down route del -net ' + DEST1 + ' gw ' + NEXTHOP +
                ' dev ' + consts.NETNS_PRIMARY_INTERFACE + '\n'
                'up route add -net ' + DEST2 + ' gw ' + NEXTHOP +
                ' dev ' + consts.NETNS_PRIMARY_INTERFACE + '\n'
                'down route del -net ' + DEST2 + ' gw ' + NEXTHOP +
                ' dev ' + consts.NETNS_PRIMARY_INTERFACE + '\n'
            )
            mock_check_output.assert_called_with(
                ['ip', 'netns', 'exec', consts.AMPHORA_NAMESPACE,
                 'ifup', consts.NETNS_PRIMARY_INTERFACE], stderr=-2)

    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'plug._netns_interface_exists')
    @mock.patch('netifaces.interfaces')
    @mock.patch('netifaces.ifaddresses')
    @mock.patch('pyroute2.IPRoute')
    @mock.patch('pyroute2.netns.create')
    @mock.patch('pyroute2.NetNS')
    @mock.patch('subprocess.check_output')
    @mock.patch('shutil.copytree')
    @mock.patch('os.makedirs')
    def test_plug_VIP4(self, mock_makedirs, mock_copytree, mock_check_output,
                       mock_netns, mock_netns_create, mock_pyroute2,
                       mock_ifaddress, mock_interfaces, mock_int_exists):

        subnet_info = {
            'subnet_cidr': '203.0.113.0/24',
            'gateway': '203.0.113.1',
            'mac_address': '123'
        }

        # malformed ip
        rv = self.app.post('/' + api_server.VERSION + '/plug/vip/error',
                           data=json.dumps(subnet_info),
                           content_type='application/json')
        self.assertEqual(400, rv.status_code)

        # No subnet info
        rv = self.app.post('/' + api_server.VERSION + '/plug/vip/error')
        self.assertEqual(400, rv.status_code)

        # Interface already plugged
        mock_int_exists.return_value = True
        rv = self.app.post('/' + api_server.VERSION + "/plug/vip/203.0.113.2",
                           content_type='application/json',
                           data=json.dumps(subnet_info))
        self.assertEqual(409, rv.status_code)
        self.assertEqual(dict(message="Interface already exists"),
                         json.loads(rv.data.decode('utf-8')))
        mock_int_exists.return_value = False

        # No interface at all
        mock_interfaces.side_effect = [[]]
        rv = self.app.post('/' + api_server.VERSION + "/plug/vip/203.0.113.2",
                           content_type='application/json',
                           data=json.dumps(subnet_info))
        self.assertEqual(404, rv.status_code)
        self.assertEqual(dict(details="No suitable network interface found"),
                         json.loads(rv.data.decode('utf-8')))

        # Two interfaces down
        mock_interfaces.side_effect = [['blah', 'blah2']]
        mock_ifaddress.side_effect = [['blabla'], ['blabla']]
        rv = self.app.post('/' + api_server.VERSION + "/plug/vip/203.0.113.2",
                           content_type='application/json',
                           data=json.dumps(subnet_info))
        self.assertEqual(404, rv.status_code)
        self.assertEqual(dict(details="No suitable network interface found"),
                         json.loads(rv.data.decode('utf-8')))

        # Happy Path IPv4, with VRRP_IP and host route
        full_subnet_info = {
            'subnet_cidr': '203.0.113.0/24',
            'gateway': '203.0.113.1',
            'mac_address': '123',
            'vrrp_ip': '203.0.113.4',
            'host_routes': [{'destination': '203.0.114.0/24',
                             'nexthop': '203.0.113.5'},
                            {'destination': '203.0.115.0/24',
                             'nexthop': '203.0.113.5'}]
        }

        mock_interfaces.side_effect = [['blah']]
        mock_ifaddress.side_effect = [[netifaces.AF_LINK],
                                      {netifaces.AF_LINK: [{'addr': '123'}]}]

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        file_name = ('/etc/netns/{netns}/network/interfaces.d/'
                     '{netns_int}.cfg'.format(
                         netns=consts.AMPHORA_NAMESPACE,
                         netns_int=consts.NETNS_PRIMARY_INTERFACE))
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open

        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            rv = self.app.post('/' + api_server.VERSION +
                               "/plug/vip/203.0.113.2",
                               content_type='application/json',
                               data=json.dumps(full_subnet_info))
            self.assertEqual(202, rv.status_code)
            mock_open.assert_any_call(file_name, flags, mode)
            mock_fdopen.assert_any_call(123, 'w')

            plug_inf_file = '/var/lib/octavia/plugged_interfaces'
            flags = os.O_RDWR | os.O_CREAT
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_any_call(plug_inf_file, flags, mode)
            mock_fdopen.assert_any_call(123, 'r+')

            handle = m()
            handle.write.assert_any_call(
                '\n# Generated by Octavia agent\n'
                'auto {netns_int} {netns_int}:0\n'
                'iface {netns_int} inet static\n'
                'address 203.0.113.4\n'
                'broadcast 203.0.113.255\n'
                'netmask 255.255.255.0\n'
                'gateway 203.0.113.1\n'
                'up route add -net 203.0.114.0/24 gw 203.0.113.5 '
                'dev {netns_int}\n'
                'down route del -net 203.0.114.0/24 gw 203.0.113.5 '
                'dev {netns_int}\n'
                'up route add -net 203.0.115.0/24 gw 203.0.113.5 '
                'dev {netns_int}\n'
                'down route del -net 203.0.115.0/24 gw 203.0.113.5 '
                'dev {netns_int}\n'
                '\n'
                'iface {netns_int}:0 inet static\n'
                'address 203.0.113.2\n'
                'broadcast 203.0.113.255\n'
                'netmask 255.255.255.0'.format(
                    netns_int=consts.NETNS_PRIMARY_INTERFACE))
            mock_check_output.assert_called_with(
                ['ip', 'netns', 'exec', consts.AMPHORA_NAMESPACE,
                 'ifup', '{netns_int}:0'.format(
                     netns_int=consts.NETNS_PRIMARY_INTERFACE)], stderr=-2)

        # One Interface down, Happy Path IPv4
        mock_interfaces.side_effect = [['blah']]
        mock_ifaddress.side_effect = [[netifaces.AF_LINK],
                                      {netifaces.AF_LINK: [{'addr': '123'}]}]

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        file_name = ('/etc/netns/{netns}/network/interfaces.d/'
                     '{netns_int}.cfg'.format(
                         netns=consts.AMPHORA_NAMESPACE,
                         netns_int=consts.NETNS_PRIMARY_INTERFACE))
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open

        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            rv = self.app.post('/' + api_server.VERSION +
                               "/plug/vip/203.0.113.2",
                               content_type='application/json',
                               data=json.dumps(subnet_info))
            self.assertEqual(202, rv.status_code)
            mock_open.assert_any_call(file_name, flags, mode)
            mock_fdopen.assert_any_call(123, 'w')

            plug_inf_file = '/var/lib/octavia/plugged_interfaces'
            flags = os.O_RDWR | os.O_CREAT
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_any_call(plug_inf_file, flags, mode)
            mock_fdopen.assert_any_call(123, 'r+')

            handle = m()
            handle.write.assert_any_call(
                '\n# Generated by Octavia agent\n'
                'auto {netns_int} {netns_int}:0\n'
                'iface {netns_int} inet dhcp\n\n'
                'iface {netns_int}:0 inet static\n'
                'address 203.0.113.2\n'
                'broadcast 203.0.113.255\n'
                'netmask 255.255.255.0'.format(
                    netns_int=consts.NETNS_PRIMARY_INTERFACE))
            mock_check_output.assert_called_with(
                ['ip', 'netns', 'exec', consts.AMPHORA_NAMESPACE,
                 'ifup', '{netns_int}:0'.format(
                     netns_int=consts.NETNS_PRIMARY_INTERFACE)], stderr=-2)

        mock_interfaces.side_effect = [['blah']]
        mock_ifaddress.side_effect = [[netifaces.AF_LINK],
                                      {netifaces.AF_LINK: [{'addr': '123'}]}]
        mock_check_output.side_effect = [
            'unplug1',
            subprocess.CalledProcessError(
                7, 'test', RANDOM_ERROR), subprocess.CalledProcessError(
                7, 'test', RANDOM_ERROR)]

        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            rv = self.app.post('/' + api_server.VERSION +
                               "/plug/vip/203.0.113.2",
                               content_type='application/json',
                               data=json.dumps(subnet_info))
            self.assertEqual(500, rv.status_code)
            self.assertEqual(
                {'details': RANDOM_ERROR,
                 'message': 'Error plugging VIP'},
                json.loads(rv.data.decode('utf-8')))

    @mock.patch('netifaces.interfaces')
    @mock.patch('netifaces.ifaddresses')
    @mock.patch('pyroute2.IPRoute')
    @mock.patch('pyroute2.netns.create')
    @mock.patch('pyroute2.NetNS')
    @mock.patch('subprocess.check_output')
    @mock.patch('shutil.copytree')
    @mock.patch('os.makedirs')
    def test_plug_vip6(self, mock_makedirs, mock_copytree, mock_check_output,
                       mock_netns, mock_netns_create, mock_pyroute2,
                       mock_ifaddress, mock_interfaces):

        subnet_info = {
            'subnet_cidr': '2001:db8::/32',
            'gateway': '2001:db8::1',
            'mac_address': '123'
        }

        # malformed ip
        rv = self.app.post('/' + api_server.VERSION + '/plug/vip/error',
                           data=json.dumps(subnet_info),
                           content_type='application/json')
        self.assertEqual(400, rv.status_code)

        # No subnet info
        rv = self.app.post('/' + api_server.VERSION + '/plug/vip/error')
        self.assertEqual(400, rv.status_code)

        # No interface at all
        mock_interfaces.side_effect = [[]]
        rv = self.app.post('/' + api_server.VERSION + "/plug/vip/2001:db8::2",
                           content_type='application/json',
                           data=json.dumps(subnet_info))
        self.assertEqual(404, rv.status_code)
        self.assertEqual(dict(details="No suitable network interface found"),
                         json.loads(rv.data.decode('utf-8')))

        # Two interfaces down
        mock_interfaces.side_effect = [['blah', 'blah2']]
        mock_ifaddress.side_effect = [['blabla'], ['blabla']]
        rv = self.app.post('/' + api_server.VERSION + "/plug/vip/2001:db8::2",
                           content_type='application/json',
                           data=json.dumps(subnet_info))
        self.assertEqual(404, rv.status_code)
        self.assertEqual(dict(details="No suitable network interface found"),
                         json.loads(rv.data.decode('utf-8')))

        # Happy Path IPv6, with VRRP_IP and host route
        full_subnet_info = {
            'subnet_cidr': '2001:db8::/32',
            'gateway': '2001:db8::1',
            'mac_address': '123',
            'vrrp_ip': '2001:db8::4',
            'host_routes': [{'destination': '2001:db9::/32',
                             'nexthop': '2001:db8::5'},
                            {'destination': '2001:db9::/32',
                             'nexthop': '2001:db8::5'}]
        }

        mock_interfaces.side_effect = [['blah']]
        mock_ifaddress.side_effect = [[netifaces.AF_LINK],
                                      {netifaces.AF_LINK: [{'addr': '123'}]}]

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        file_name = ('/etc/netns/{netns}/network/interfaces.d/'
                     '{netns_int}.cfg'.format(
                         netns=consts.AMPHORA_NAMESPACE,
                         netns_int=consts.NETNS_PRIMARY_INTERFACE))
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open

        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            rv = self.app.post('/' + api_server.VERSION +
                               "/plug/vip/2001:db8::2",
                               content_type='application/json',
                               data=json.dumps(full_subnet_info))
            self.assertEqual(202, rv.status_code)
            mock_open.assert_any_call(file_name, flags, mode)
            mock_fdopen.assert_any_call(123, 'w')

            plug_inf_file = '/var/lib/octavia/plugged_interfaces'
            flags = os.O_RDWR | os.O_CREAT
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_any_call(plug_inf_file, flags, mode)
            mock_fdopen.assert_any_call(123, 'r+')
            handle = m()
            handle.write.assert_any_call(
                '\n# Generated by Octavia agent\n'
                'auto {netns_int} {netns_int}:0\n'
                'iface {netns_int} inet6 static\n'
                'address 2001:db8::4\n'
                'broadcast 2001:0db8:ffff:ffff:ffff:ffff:ffff:ffff\n'
                'netmask 32\n'
                'gateway 2001:db8::1\n'
                'up route add -net 2001:db9::/32 gw 2001:db8::5 '
                'dev {netns_int}\n'
                'down route del -net 2001:db9::/32 gw 2001:db8::5 '
                'dev {netns_int}\n'
                'up route add -net 2001:db9::/32 gw 2001:db8::5 '
                'dev {netns_int}\n'
                'down route del -net 2001:db9::/32 gw 2001:db8::5 '
                'dev {netns_int}\n'
                '\n'
                'iface {netns_int}:0 inet6 static\n'
                'address 2001:0db8:0000:0000:0000:0000:0000:0002\n'
                'broadcast 2001:0db8:ffff:ffff:ffff:ffff:ffff:ffff\n'
                'netmask 32'.format(netns_int=consts.NETNS_PRIMARY_INTERFACE))
            mock_check_output.assert_called_with(
                ['ip', 'netns', 'exec', consts.AMPHORA_NAMESPACE,
                 'ifup', '{netns_int}:0'.format(
                     netns_int=consts.NETNS_PRIMARY_INTERFACE)], stderr=-2)

        # One Interface down, Happy Path IPv6
        mock_interfaces.side_effect = [['blah']]
        mock_ifaddress.side_effect = [[netifaces.AF_LINK],
                                      {netifaces.AF_LINK: [{'addr': '123'}]}]

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        file_name = ('/etc/netns/{netns}/network/interfaces.d/'
                     '{netns_int}.cfg'.format(
                         netns=consts.AMPHORA_NAMESPACE,
                         netns_int=consts.NETNS_PRIMARY_INTERFACE))
        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open

        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            rv = self.app.post('/' + api_server.VERSION +
                               "/plug/vip/2001:db8::2",
                               content_type='application/json',
                               data=json.dumps(subnet_info))
            self.assertEqual(202, rv.status_code)
            mock_open.assert_any_call(file_name, flags, mode)
            mock_fdopen.assert_any_call(123, 'w')

            plug_inf_file = '/var/lib/octavia/plugged_interfaces'
            flags = os.O_RDWR | os.O_CREAT
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_any_call(plug_inf_file, flags, mode)
            mock_fdopen.assert_any_call(123, 'r+')
            handle = m()
            handle.write.assert_any_call(
                '\n# Generated by Octavia agent\n'
                'auto {netns_int} {netns_int}:0\n'
                'iface {netns_int} inet6 auto\n\n'
                'iface {netns_int}:0 inet6 static\n'
                'address 2001:0db8:0000:0000:0000:0000:0000:0002\n'
                'broadcast 2001:0db8:ffff:ffff:ffff:ffff:ffff:ffff\n'
                'netmask 32'.format(netns_int=consts.NETNS_PRIMARY_INTERFACE))
            mock_check_output.assert_called_with(
                ['ip', 'netns', 'exec', consts.AMPHORA_NAMESPACE,
                 'ifup', '{netns_int}:0'.format(
                     netns_int=consts.NETNS_PRIMARY_INTERFACE)], stderr=-2)

        mock_interfaces.side_effect = [['blah']]
        mock_ifaddress.side_effect = [[netifaces.AF_LINK],
                                      {netifaces.AF_LINK: [{'addr': '123'}]}]
        mock_check_output.side_effect = [
            'unplug1',
            subprocess.CalledProcessError(
                7, 'test', RANDOM_ERROR), subprocess.CalledProcessError(
                7, 'test', RANDOM_ERROR)]

        m = self.useFixture(test_utils.OpenFixture(file_name)).mock_open
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            rv = self.app.post('/' + api_server.VERSION +
                               "/plug/vip/2001:db8::2",
                               content_type='application/json',
                               data=json.dumps(subnet_info))
            self.assertEqual(500, rv.status_code)
            self.assertEqual(
                {'details': RANDOM_ERROR,
                 'message': 'Error plugging VIP'},
                json.loads(rv.data.decode('utf-8')))

    @mock.patch('pyroute2.NetNS')
    def test_get_interface(self, mock_netns):

        netns_handle = mock_netns.return_value.__enter__.return_value

        interface_res = {'interface': 'eth0'}

        # Happy path
        netns_handle.get_addr.return_value = [{
            'index': 3, 'family': socket.AF_INET,
            'attrs': [['IFA_ADDRESS', '203.0.113.2']]}]
        netns_handle.get_links.return_value = [{
            'attrs': [['IFLA_IFNAME', 'eth0']]}]
        rv = self.app.get('/' + api_server.VERSION + '/interface/203.0.113.2',
                          data=json.dumps(interface_res),
                          content_type='application/json')
        self.assertEqual(200, rv.status_code)

        # Happy path with IPv6 address normalization
        netns_handle.get_addr.return_value = [{
            'index': 3, 'family': socket.AF_INET6,
            'attrs': [['IFA_ADDRESS',
                       '0000:0000:0000:0000:0000:0000:0000:0001']]}]
        netns_handle.get_links.return_value = [{
            'attrs': [['IFLA_IFNAME', 'eth0']]}]
        rv = self.app.get('/' + api_server.VERSION + '/interface/::1',
                          data=json.dumps(interface_res),
                          content_type='application/json')
        self.assertEqual(200, rv.status_code)

        # Nonexistent interface
        rv = self.app.get('/' + api_server.VERSION + '/interface/10.0.0.1',
                          data=json.dumps(interface_res),
                          content_type='application/json')
        self.assertEqual(404, rv.status_code)

        # Invalid IP address
        rv = self.app.get('/' + api_server.VERSION +
                          '/interface/00:00:00:00:00:00',
                          data=json.dumps(interface_res),
                          content_type='application/json')
        self.assertEqual(400, rv.status_code)

    @mock.patch('os.path.exists')
    @mock.patch('os.makedirs')
    @mock.patch('os.rename')
    @mock.patch('os.remove')
    def test_upload_keepalived_config(self, mock_remove,
                                      mock_rename, mock_makedirs, mock_exists):

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC

        mock_exists.return_value = True
        cfg_path = util.keepalived_cfg_path()
        m = self.useFixture(test_utils.OpenFixture(cfg_path)).mock_open

        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            rv = self.app.put('/' + api_server.VERSION + '/vrrp/upload',
                              data='test')

            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_open.assert_called_with(cfg_path, flags, mode)
            mock_fdopen.assert_called_with(123, 'w')
            self.assertEqual(200, rv.status_code)

        mock_exists.return_value = False
        script_path = util.keepalived_check_script_path()
        m = self.useFixture(test_utils.OpenFixture(script_path)).mock_open

        with mock.patch('os.open') as mock_open, mock.patch.object(
                os, 'fdopen', m) as mock_fdopen:
            mock_open.return_value = 123
            rv = self.app.put('/' + api_server.VERSION + '/vrrp/upload',
                              data='test')
            mode = (stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP |
                    stat.S_IROTH | stat.S_IXOTH)
            mock_open.assert_called_with(script_path, flags, mode)
            mock_fdopen.assert_called_with(123, 'w')
            self.assertEqual(200, rv.status_code)

    @mock.patch('subprocess.check_output')
    def test_manage_service_vrrp(self, mock_check_output):
        rv = self.app.put('/' + api_server.VERSION + '/vrrp/start')
        self.assertEqual(202, rv.status_code)

        rv = self.app.put('/' + api_server.VERSION + '/vrrp/restart')
        self.assertEqual(400, rv.status_code)

        mock_check_output.side_effect = subprocess.CalledProcessError(1,
                                                                      'blah!')

        rv = self.app.put('/' + api_server.VERSION + '/vrrp/start')
        self.assertEqual(500, rv.status_code)
