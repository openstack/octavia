# Copyright 2022 Red Hat
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
import signal
from unittest import mock

from octavia.cmd import prometheus_proxy
from octavia.tests.unit import base


class TestPrometheusProxyCMD(base.TestCase):

    @mock.patch('http.server.SimpleHTTPRequestHandler.log_request')
    @mock.patch('http.server.SimpleHTTPRequestHandler.__init__')
    def test_log_request(self, mock_req_handler_init, mock_log_request):
        mock_req_handler_init.return_value = None
        proxy = prometheus_proxy.PrometheusProxy()
        proxy.log_request()
        mock_log_request.assert_not_called()

    @mock.patch('os.cpu_count', return_value=2)
    @mock.patch('psutil.getloadavg', return_value=(1, 2, 3))
    @mock.patch('http.server.SimpleHTTPRequestHandler.__init__')
    def test_add_cpu_utilization(self, mock_req_handler_init, mock_getloadavg,
                                 mock_cpu_count):
        mock_req_handler_init.return_value = None
        proxy = prometheus_proxy.PrometheusProxy()
        test_buffer = "TestStringBuffer\n"
        result = proxy._add_cpu_utilization(test_buffer)

        expected_result = (
            "TestStringBuffer\n"
            "# HELP octavia_loadbalancer_cpu Load balancer CPU utilization "
            "(percentage).\n"
            "# TYPE octavia_loadbalancer_cpu gauge\n"
            "octavia_loadbalancer_cpu 50.0\n")

        self.assertEqual(expected_result, result)

    @mock.patch('psutil.virtual_memory', return_value=(1, 2, 23.5))
    @mock.patch('http.server.SimpleHTTPRequestHandler.__init__')
    def test__add_memory_utilization(self, mock_req_handler_init,
                                     mock_virt_mem):
        mock_req_handler_init.return_value = None
        proxy = prometheus_proxy.PrometheusProxy()
        test_buffer = "TestStringMemoryBuffer\n"
        result = proxy._add_memory_utilization(test_buffer)

        expected_result = (
            "TestStringMemoryBuffer\n"
            "# HELP octavia_loadbalancer_memory Load balancer memory "
            "utilization (percentage).\n"
            "# TYPE octavia_loadbalancer_memory gauge\n"
            "octavia_loadbalancer_memory 23.5\n")

        self.assertEqual(expected_result, result)

    @mock.patch('octavia.cmd.prometheus_proxy.PRINT_REJECTED', True)
    # No need to print all of the rejected lines to the log
    @mock.patch('builtins.print')
    @mock.patch('urllib.request.urlopen')
    @mock.patch('os.cpu_count', return_value=2)
    @mock.patch('psutil.getloadavg', return_value=(1, 2, 3))
    @mock.patch('psutil.virtual_memory', return_value=(1, 2, 23.5))
    @mock.patch('http.server.SimpleHTTPRequestHandler.__init__')
    def test_do_get(self, mock_req_handler_init, mock_virt_mem,
                    mock_getloadavg, mock_cpu_count, mock_urlopen, mock_print):
        mock_req_handler_init.return_value = None
        proxy = prometheus_proxy.PrometheusProxy()

        mock_send_response = mock.MagicMock()
        proxy.send_response = mock_send_response
        mock_send_header = mock.MagicMock()
        proxy.send_header = mock_send_header
        mock_end_headers = mock.MagicMock()
        proxy.end_headers = mock_end_headers
        mock_wfile = mock.MagicMock()
        proxy.wfile = mock_wfile

        with open("octavia/tests/common/sample_haproxy_prometheus",
                  "rb") as file:
            mock_urlopen.return_value = file

            proxy.do_GET()

            mock_send_response.assert_called_once_with(200)

            with open("octavia/tests/common/sample_octavia_prometheus",
                      "rb") as file2:
                octavia_metrics = file2.read()
                mock_wfile.write.assert_called_once_with(octavia_metrics)

    @mock.patch('urllib.request.urlopen')
    @mock.patch('os.cpu_count', return_value=2)
    @mock.patch('psutil.getloadavg', return_value=(1, 2, 3))
    @mock.patch('psutil.virtual_memory', return_value=(1, 2, 23.5))
    @mock.patch('http.server.SimpleHTTPRequestHandler.__init__')
    def test_do_get_exception(self, mock_req_handler_init, mock_virt_mem,
                              mock_getloadavg, mock_cpu_count, mock_urlopen):
        mock_urlopen.side_effect = [Exception('boom')]
        mock_req_handler_init.return_value = None
        proxy = prometheus_proxy.PrometheusProxy()

        mock_send_response = mock.MagicMock()
        proxy.send_response = mock_send_response
        mock_send_header = mock.MagicMock()
        proxy.send_header = mock_send_header
        mock_end_headers = mock.MagicMock()
        proxy.end_headers = mock_end_headers

        proxy.do_GET()

        mock_send_response.assert_called_once_with(502)

    @mock.patch('signal.signal')
    def test_signalhandler(self, mock_signal):

        sig_handler = prometheus_proxy.SignalHandler()

        calls = [mock.call(signal.SIGINT, sig_handler.shutdown),
                 mock.call(signal.SIGTERM, sig_handler.shutdown)]
        mock_signal.assert_has_calls(calls)

        self.assertFalse(prometheus_proxy.EXIT_EVENT.is_set())
        sig_handler.shutdown()
        self.assertTrue(prometheus_proxy.EXIT_EVENT.is_set())

    @mock.patch('octavia.cmd.prometheus_proxy.EXIT_EVENT')
    @mock.patch('signal.signal')
    def test_shutdown_thread(self, mock_signal, mock_exit_event):

        mock_http = mock.MagicMock()

        prometheus_proxy.shutdown_thread(mock_http)

        mock_exit_event.wait.assert_called_once()
        mock_http.shutdown.assert_called_once()

    @mock.patch('threading.Thread')
    # TODO(johnsom) Switch this when we move to ThreadingHTTPServer
    # @mock.patch('http.server.ThreadingHTTPServer.serve_forever')
    @mock.patch('octavia.cmd.prometheus_proxy.ThreadedHTTPServer.'
                'serve_forever')
    @mock.patch('octavia.amphorae.backends.utils.network_namespace.'
                'NetworkNamespace.__exit__')
    @mock.patch('octavia.amphorae.backends.utils.network_namespace.'
                'NetworkNamespace.__enter__')
    @mock.patch('octavia.cmd.prometheus_proxy.EXIT_EVENT')
    @mock.patch('octavia.cmd.prometheus_proxy.SignalHandler')
    def test_main(self, mock_signal_handler, mock_exit_event, mock_netns_enter,
                  mock_netns_exit, mock_serve_forever, mock_thread):

        mock_exit_event.is_set.side_effect = [False, False, True]
        mock_netns_enter.side_effect = [Exception('boom'), True]

        prometheus_proxy.main()

        mock_signal_handler.assert_called_once()
        mock_serve_forever.assert_called_once()
