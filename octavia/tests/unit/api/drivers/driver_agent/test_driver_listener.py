#    Copyright 2018 Rackspace, US Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import errno

import mock

from oslo_config import cfg
from oslo_serialization import jsonutils

from octavia.api.drivers.driver_agent import driver_listener
import octavia.tests.unit.base as base

CONF = cfg.CONF


class TestDriverListener(base.TestCase):

    def setUp(self):
        super(TestDriverListener, self).setUp()

    @mock.patch('octavia.api.drivers.driver_agent.driver_listener.memoryview')
    def test_recv(self, mock_memoryview):
        # TEST_STRING len() is 15
        TEST_STRING = '{"test": "msg"}'
        ref_object = jsonutils.loads(TEST_STRING)

        mock_recv_socket = mock.MagicMock()
        mock_recv = mock.MagicMock()
        mock_recv.side_effect = [b'1', b'5', b'\n']
        mock_recv_socket.recv = mock_recv
        mock_recv_socket.recv_into.return_value = 15
        mock_mv_buffer = mock.MagicMock()
        mock_tobytes = mock.MagicMock()
        mock_tobytes.return_value = TEST_STRING
        mock_mv_buffer.tobytes = mock_tobytes
        mock_memoryview.return_value = mock_mv_buffer

        result = driver_listener._recv(mock_recv_socket)

        self.assertEqual(ref_object, result)
        calls = [mock.call(1), mock.call(1), mock.call(1)]
        mock_recv.assert_has_calls(calls)
        mock_memoryview.assert_called_once_with(bytearray(15))
        mock_recv_socket.recv_into.assert_called_once_with(mock_mv_buffer[0:],
                                                           15)

    @mock.patch('octavia.api.drivers.driver_agent.driver_updater.'
                'DriverUpdater')
    @mock.patch('octavia.api.drivers.driver_agent.driver_listener._recv')
    def test_StatusRequestHandler_handle(self, mock_recv, mock_driverupdater):
        TEST_OBJECT = {"test": "msg"}
        mock_recv.return_value = 'bogus'
        mock_updater = mock.MagicMock()
        mock_update_loadbalancer_status = mock.MagicMock()
        mock_update_loadbalancer_status.return_value = TEST_OBJECT
        mock_updater.update_loadbalancer_status = (
            mock_update_loadbalancer_status)
        mock_driverupdater.return_value = mock_updater
        mock_request = mock.MagicMock()
        mock_send = mock.MagicMock()
        mock_sendall = mock.MagicMock()
        mock_request.send = mock_send
        mock_request.sendall = mock_sendall

        StatusRequestHandler = driver_listener.StatusRequestHandler(
            mock_request, 'bogus', 'bogus')
        StatusRequestHandler.handle()

        mock_recv.assert_called_with(mock_request)
        mock_update_loadbalancer_status.assert_called_with('bogus')
        mock_send.assert_called_with(b'15\n')
        mock_sendall.assert_called_with(
            jsonutils.dumps(TEST_OBJECT).encode('utf-8'))

    @mock.patch('octavia.api.drivers.driver_agent.driver_updater.'
                'DriverUpdater')
    @mock.patch('octavia.api.drivers.driver_agent.driver_listener._recv')
    def test_StatsRequestHandler_handle(self, mock_recv, mock_driverupdater):
        TEST_OBJECT = {"test": "msg"}
        mock_recv.return_value = 'bogus'
        mock_updater = mock.MagicMock()
        mock_update_listener_stats = mock.MagicMock()
        mock_update_listener_stats.return_value = TEST_OBJECT
        mock_updater.update_listener_statistics = (mock_update_listener_stats)
        mock_driverupdater.return_value = mock_updater
        mock_request = mock.MagicMock()
        mock_send = mock.MagicMock()
        mock_sendall = mock.MagicMock()
        mock_request.send = mock_send
        mock_request.sendall = mock_sendall

        StatsRequestHandler = driver_listener.StatsRequestHandler(
            mock_request, 'bogus', 'bogus')
        StatsRequestHandler.handle()

        mock_recv.assert_called_with(mock_request)
        mock_update_listener_stats.assert_called_with('bogus')
        mock_send.assert_called_with(b'15\n')
        mock_sendall.assert_called_with(jsonutils.dump_as_bytes(TEST_OBJECT))

    @mock.patch('octavia.api.drivers.driver_agent.driver_get.'
                'process_get')
    @mock.patch('octavia.api.drivers.driver_agent.driver_listener._recv')
    def test_GetRequestHandler_handle(self, mock_recv, mock_process_get):
        TEST_OBJECT = {"test": "msg"}

        mock_recv.return_value = 'bogus'

        mock_process_get.return_value = TEST_OBJECT
        mock_request = mock.MagicMock()
        mock_send = mock.MagicMock()
        mock_sendall = mock.MagicMock()
        mock_request.send = mock_send
        mock_request.sendall = mock_sendall

        GetRequestHandler = driver_listener.GetRequestHandler(
            mock_request, 'bogus', 'bogus')
        GetRequestHandler.handle()

        mock_recv.assert_called_with(mock_request)
        mock_process_get.assert_called_with('bogus')

        mock_send.assert_called_with(b'15\n')
        mock_sendall.assert_called_with(jsonutils.dump_as_bytes(TEST_OBJECT))

    @mock.patch('os.remove')
    def test_cleanup_socket_file(self, mock_remove):
        mock_remove.side_effect = [mock.DEFAULT, OSError,
                                   OSError(errno.ENOENT, 'no_file')]
        driver_listener._cleanup_socket_file('fake_filename')
        mock_remove.assert_called_once_with('fake_filename')

        self.assertRaises(OSError, driver_listener._cleanup_socket_file,
                          'fake_filename')
        # Make sure we just pass if the file was not found
        driver_listener._cleanup_socket_file('fake_filename')

    @mock.patch('octavia.api.drivers.driver_agent.driver_listener.'
                '_cleanup_socket_file')
    @mock.patch('octavia.api.drivers.driver_agent.driver_listener.'
                'ForkingUDSServer')
    def test_status_listener(self, mock_forking_server, mock_cleanup):
        mock_server = mock.MagicMock()
        mock_active_children = mock.PropertyMock(
            side_effect=['a', 'a', 'a',
                         'a' * CONF.driver_agent.status_max_processes, 'a',
                         'a' * 1000, ''])
        type(mock_server).active_children = mock_active_children
        mock_forking_server.return_value = mock_server
        mock_exit_event = mock.MagicMock()
        mock_exit_event.is_set.side_effect = [False, False, False, False, True]

        driver_listener.status_listener(mock_exit_event)
        mock_server.handle_request.assert_called()
        mock_server.server_close.assert_called_once()
        self.assertEqual(2, mock_cleanup.call_count)

    @mock.patch('octavia.api.drivers.driver_agent.driver_listener.'
                '_cleanup_socket_file')
    @mock.patch('octavia.api.drivers.driver_agent.driver_listener.'
                'ForkingUDSServer')
    def test_stats_listener(self, mock_forking_server, mock_cleanup):
        mock_server = mock.MagicMock()
        mock_active_children = mock.PropertyMock(
            side_effect=['a', 'a', 'a',
                         'a' * CONF.driver_agent.status_max_processes, 'a',
                         'a' * 1000, ''])
        type(mock_server).active_children = mock_active_children
        mock_forking_server.return_value = mock_server
        mock_exit_event = mock.MagicMock()
        mock_exit_event.is_set.side_effect = [False, False, False, False, True]

        driver_listener.stats_listener(mock_exit_event)
        mock_server.handle_request.assert_called()
        mock_server.server_close.assert_called_once()

    @mock.patch('octavia.api.drivers.driver_agent.driver_listener.'
                '_cleanup_socket_file')
    @mock.patch('octavia.api.drivers.driver_agent.driver_listener.'
                'ForkingUDSServer')
    def test_get_listener(self, mock_forking_server, mock_cleanup):
        mock_server = mock.MagicMock()
        mock_active_children = mock.PropertyMock(
            side_effect=['a', 'a', 'a',
                         'a' * CONF.driver_agent.status_max_processes, 'a',
                         'a' * 1000, ''])
        type(mock_server).active_children = mock_active_children
        mock_forking_server.return_value = mock_server
        mock_exit_event = mock.MagicMock()
        mock_exit_event.is_set.side_effect = [False, False, False, False, True]

        driver_listener.get_listener(mock_exit_event)
        mock_server.handle_request.assert_called()
        mock_server.server_close.assert_called_once()
