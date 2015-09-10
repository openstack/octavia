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
import subprocess

import mock
import netifaces
import six

from octavia.amphorae.backends.agent import api_server
from octavia.amphorae.backends.agent.api_server import certificate_update
from octavia.amphorae.backends.agent.api_server import server
from octavia.amphorae.backends.agent.api_server import util
from octavia.common import constants as consts
import octavia.tests.unit.base as base

RANDOM_ERROR = 'random error'
OK = dict(message='OK')

BUILTINS = '__builtin__'
if six.PY3:
    BUILTINS = 'builtins'


class ServerTestCase(base.TestCase):
    app = None

    def setUp(self):
        self.app = server.app.test_client()
        super(ServerTestCase, self).setUp()

    @mock.patch('os.path.exists')
    @mock.patch('os.makedirs')
    @mock.patch('os.rename')
    @mock.patch('subprocess.check_output')
    @mock.patch('os.remove')
    def test_haproxy(self, mock_remove, mock_subprocess, mock_rename,
                     mock_makedirs, mock_exists):
        mock_exists.return_value = True
        m = mock.mock_open()

        # happy case upstart file exists
        with mock.patch('%s.open' % BUILTINS, m, create=True):
            rv = self.app.put('/' + api_server.VERSION +
                              '/listeners/123/haproxy', data='test')
            self.assertEqual(202, rv.status_code)
            m.assert_called_once_with(
                '/var/lib/octavia/123/haproxy.cfg.new', 'w')
            handle = m()
            handle.write.assert_called_once_with(six.b('test'))
            mock_subprocess.assert_called_once_with(
                "haproxy -c -f /var/lib/octavia/123/haproxy.cfg.new".split(),
                stderr=-2)
            mock_rename.assert_called_once_with(
                '/var/lib/octavia/123/haproxy.cfg.new',
                '/var/lib/octavia/123/haproxy.cfg')

        # exception writing
        m = mock.Mock()
        m.side_effect = Exception()  # open crashes
        with mock.patch('%s.open' % BUILTINS, m, create=True):
            rv = self.app.put('/' + api_server.VERSION +
                              '/listeners/123/haproxy', data='test')
            self.assertEqual(500, rv.status_code)

        # check if files get created
        mock_exists.return_value = False
        m = mock.mock_open()

        # happy case upstart file exists
        with mock.patch('%s.open' % BUILTINS, m, create=True):
            rv = self.app.put('/' + api_server.VERSION +
                              '/listeners/123/haproxy', data='test')
            self.assertEqual(202, rv.status_code)
            m.assert_any_call('/var/lib/octavia/123/haproxy.cfg.new', 'w')
            m.assert_any_call(util.UPSTART_DIR + '/haproxy-123.conf', 'w')
            handle = m()
            handle.write.assert_any_call(six.b('test'))
            # skip the template stuff
            mock_makedirs.assert_called_with('/var/lib/octavia/123')

        # unhappy case haproxy check fails
        mock_exists.return_value = True
        mock_subprocess.side_effect = [subprocess.CalledProcessError(
            7, 'test', RANDOM_ERROR)]
        with mock.patch('%s.open' % BUILTINS, m, create=True):
            rv = self.app.put('/' + api_server.VERSION +
                              '/listeners/123/haproxy', data='test')
            self.assertEqual(400, rv.status_code)
            self.assertEqual(
                {'message': 'Invalid request', u'details': u'random error'},
                json.loads(rv.data.decode('utf-8')))
            m.assert_called_with('/var/lib/octavia/123/haproxy.cfg.new', 'w')
            handle = m()
            handle.write.assert_called_with(six.b('test'))
            mock_subprocess.assert_called_with(
                "haproxy -c -f /var/lib/octavia/123/haproxy.cfg.new".split(),
                stderr=-2)
            mock_remove.assert_called_once_with(
                '/var/lib/octavia/123/haproxy.cfg.new')

    @mock.patch('os.path.exists')
    @mock.patch('subprocess.check_output')
    def test_start(self, mock_subprocess, mock_exists):
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
                        + ' 123 started'},
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
        m = mock.mock_open(read_data=CONTENT)

        with mock.patch('%s.open' % BUILTINS, m, create=True):
            rv = self.app.get('/' + api_server.VERSION +
                              '/listeners/123/haproxy')
            self.assertEqual(200, rv.status_code)
            self.assertEqual(six.b(CONTENT), rv.data)
            self.assertEqual('text/plain; charset=utf-8',
                             rv.headers['Content-Type'])

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                + 'get_listeners')
    @mock.patch('octavia.amphorae.backends.agent.api_server.listener.'
                + '_check_listener_status')
    @mock.patch('octavia.amphorae.backends.agent.api_server.listener.'
                + '_parse_haproxy_file')
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
             {'status': consts.ERROR, 'type': 'http', 'uuid': '456'}],
            json.loads(rv.data.decode('utf-8')))

    @mock.patch('octavia.amphorae.backends.agent.api_server.listener.'
                + '_check_listener_status')
    @mock.patch('octavia.amphorae.backends.agent.api_server.listener.'
                + '_parse_haproxy_file')
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
            type='test',
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

        mock_exists.side_effect = [True, False]
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

        m = mock.mock_open(read_data=CONTENT)
        mock_exists.return_value = True
        mock_exists.side_effect = None
        with mock.patch('%s.open' % BUILTINS, m, create=True):
            rv = self.app.get('/' + api_server.VERSION +
                              '/listeners/123/certificates/test.pem')
        self.assertEqual(200, rv.status_code)
        self.assertEqual(dict(md5sum=hashlib.md5(six.b(CONTENT)).hexdigest()),
                         json.loads(rv.data.decode('utf-8')))

    @mock.patch('os.path.exists')
    @mock.patch('os.fchmod')
    @mock.patch('os.makedirs')
    def test_upload_certificate_md5(self, mock_makedir, mock_chmod,
                                    mock_exists):
        mock_exists.side_effect = [False]
        rv = self.app.put('/' + api_server.VERSION +
                          '/listeners/123/certificates/test.pem',
                          data='TestTest')
        self.assertEqual(404, rv.status_code)

        # wrong file name
        mock_exists.side_effect = [True]
        rv = self.app.put('/' + api_server.VERSION +
                          '/listeners/123/certificates/test.bla',
                          data='TestTest')
        self.assertEqual(400, rv.status_code)

        mock_exists.side_effect = [True, True, True]
        m = mock.mock_open()

        with mock.patch('%s.open' % BUILTINS, m, create=True):
            rv = self.app.put('/' + api_server.VERSION +
                              '/listeners/123/certificates/test.pem',
                              data='TestTest')
            self.assertEqual(200, rv.status_code)
            self.assertEqual(OK, json.loads(rv.data.decode('utf-8')))
            handle = m()
            handle.write.assert_called_once_with(six.b('TestTest'))
            mock_chmod.assert_called_once_with(handle.fileno(), 0o600)

        mock_exists.side_effect = [True, False]
        m = mock.mock_open()

        with mock.patch('%s.open' % BUILTINS, m, create=True):
            rv = self.app.put('/' + api_server.VERSION +
                              '/listeners/123/certificates/test.pem',
                              data='TestTest')
            self.assertEqual(200, rv.status_code)
            self.assertEqual(OK, json.loads(rv.data.decode('utf-8')))
            handle = m()
            mock_makedir.called_once_with('/var/lib/octavia/123')

    @mock.patch('os.fchmod')
    def test_upload_server_certificate(self, mock_chmod):
        certificate_update.BUFFER = 5  # test the while loop
        m = mock.mock_open()

        with mock.patch('%s.open' % BUILTINS, m, create=True):
            rv = self.app.put('/' + api_server.VERSION +
                              '/certificate',
                              data='TestTest')
            self.assertEqual(202, rv.status_code)
            self.assertEqual(OK, json.loads(rv.data.decode('utf-8')))
            handle = m()
            handle.write.assert_any_call(six.b('TestT'))
            handle.write.assert_any_call(six.b('est'))
            mock_chmod.assert_called_once_with(handle.fileno(), 0o600)

    @mock.patch('netifaces.interfaces')
    @mock.patch('netifaces.ifaddresses')
    @mock.patch('subprocess.check_output')
    def test_plug_network(self, mock_check_output, mock_ifaddress,
                          mock_interfaces):
        port_info = {'mac_address': '123'}

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
        m = mock.mock_open()
        with mock.patch('%s.open' % BUILTINS, m, create=True):
            rv = self.app.post('/' + api_server.VERSION + "/plug/network",
                               content_type='application/json',
                               data=json.dumps(port_info))
            self.assertEqual(202, rv.status_code)
            m.assert_called_once_with(
                '/etc/network/interfaces.d/blah.cfg', 'w')
            handle = m()
            handle.write.assert_called_once_with(
                '\n# Generated by Octavia agent\n'
                'auto blah blah:0\n'
                'iface blah inet dhcp')
            mock_check_output.assert_called_with(
                ['ifup', 'blah'], stderr=-2)

        # same as above but ifup fails
        mock_interfaces.side_effect = [['blah']]
        mock_ifaddress.side_effect = [[netifaces.AF_LINK],
                                      {netifaces.AF_LINK: [{'addr': '123'}]}]
        mock_check_output.side_effect = [subprocess.CalledProcessError(
            7, 'test', RANDOM_ERROR), subprocess.CalledProcessError(
            7, 'test', RANDOM_ERROR)]
        m = mock.mock_open()
        with mock.patch('%s.open' % BUILTINS, m, create=True):
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
    @mock.patch('subprocess.check_output')
    @mock.patch('pyroute2.IPRoute')
    def test_plug_VIP(self, mock_pyroute2, mock_check_output, mock_ifaddress,
                      mock_interfaces):

        subnet_info = {'subnet_cidr': '10.0.0.0/24',
                       'gateway': '10.0.0.1',
                       'mac_address': '123'}

        # malformated ip
        rv = self.app.post('/' + api_server.VERSION + '/plug/vip/error',
                           data=json.dumps(subnet_info),
                           content_type='application/json')
        self.assertEqual(400, rv.status_code)

        # No subnet info
        rv = self.app.post('/' + api_server.VERSION + '/plug/vip/error')
        self.assertEqual(400, rv.status_code)

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

        # One Interface down, Happy Path
        mock_interfaces.side_effect = [['blah']]
        mock_ifaddress.side_effect = [[netifaces.AF_LINK],
                                      {netifaces.AF_LINK: [{'addr': '123'}]}]
        m = mock.mock_open()
        with mock.patch('%s.open' % BUILTINS, m, create=True):
            rv = self.app.post('/' + api_server.VERSION +
                               "/plug/vip/203.0.113.2",
                               content_type='application/json',
                               data=json.dumps(subnet_info))
            self.assertEqual(202, rv.status_code)
            m.assert_called_once_with(
                '/etc/network/interfaces.d/blah.cfg', 'w')
            handle = m()
            handle.write.assert_called_once_with(
                '\n# Generated by Octavia agent\n'
                'auto blah blah:0\n'
                'iface blah inet dhcp\n'
                'iface blah:0 inet static\n'
                'address 203.0.113.2\n'
                'broadcast 203.0.113.255\n'
                'netmask 255.255.255.0')
            mock_check_output.assert_called_with(
                ['ifup', 'blah:0'], stderr=-2)

        mock_interfaces.side_effect = [['blah']]
        mock_ifaddress.side_effect = [[netifaces.AF_LINK],
                                      {netifaces.AF_LINK: [{'addr': '123'}]}]
        mock_check_output.side_effect = [
            'unplug1',
            subprocess.CalledProcessError(
                7, 'test', RANDOM_ERROR), subprocess.CalledProcessError(
                7, 'test', RANDOM_ERROR)]
        m = mock.mock_open()
        with mock.patch('%s.open' % BUILTINS, m, create=True):
            rv = self.app.post('/' + api_server.VERSION +
                               "/plug/vip/203.0.113.2",
                               content_type='application/json',
                               data=json.dumps(subnet_info))
            self.assertEqual(500, rv.status_code)
            self.assertEqual(
                {'details': RANDOM_ERROR,
                 'message': 'Error plugging VIP'},
                json.loads(rv.data.decode('utf-8')))
