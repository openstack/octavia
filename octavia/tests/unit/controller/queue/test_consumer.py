# Copyright 2014 Rackspace
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

import mock
from oslo_config import cfg
import oslo_messaging as messaging

from octavia.controller.queue import consumer
from octavia.controller.queue import endpoint
from octavia.tests.unit import base


@mock.patch.object(messaging, 'get_transport')
@mock.patch.object(messaging, 'Target')
@mock.patch.object(endpoint, 'Endpoint')
@mock.patch.object(messaging, 'get_rpc_server')
class TestConsumer(base.TestCase):

    def setUp(self):
        super(TestConsumer, self).setUp()
        cfg.CONF.import_group('oslo_messaging', 'octavia.common.config')
        cfg.CONF.set_override('topic', 'foo_topic', group='oslo_messaging')
        cfg.CONF.set_override('host', 'foo_host')

    def test_consumer_start(self, mock_rpc_server, mock_endpoint, mock_target,
                            mock_get_transport):
        mock_get_transport_rv = mock.Mock()
        mock_get_transport.return_value = mock_get_transport_rv
        mock_rpc_server_rv = mock.Mock()
        mock_rpc_server.return_value = mock_rpc_server_rv
        mock_endpoint_rv = mock.Mock()
        mock_endpoint.return_value = mock_endpoint_rv
        mock_target_rv = mock.Mock()
        mock_target.return_value = mock_target_rv

        consumer.Consumer().start()

        mock_get_transport.assert_called_once_with(cfg.CONF)
        mock_target.assert_called_once_with(topic='foo_topic',
                                            server='foo_host', fanout=False)
        mock_endpoint.assert_called_once_with()
        mock_rpc_server.assert_called_once_with(mock_get_transport_rv,
                                                mock_target_rv,
                                                [mock_endpoint_rv],
                                                executor='eventlet')

    def test_consumer_stop(self, mock_rpc_server, mock_endpoint, mock_target,
                           mock_get_transport):
        mock_rpc_server_rv = mock.Mock()
        mock_rpc_server.return_value = mock_rpc_server_rv

        cons = consumer.Consumer()
        cons.start()
        cons.stop()
        mock_rpc_server_rv.stop.assert_called_once_with()
        self.assertFalse(mock_rpc_server_rv.wait.called)

    def test_consumer_graceful_stop(self, mock_rpc_server, mock_endpoint,
                                    mock_target, mock_get_transport):
        mock_rpc_server_rv = mock.Mock()
        mock_rpc_server.return_value = mock_rpc_server_rv

        cons = consumer.Consumer()
        cons.start()
        cons.stop(graceful=True)
        mock_rpc_server_rv.stop.assert_called_once_with()
        mock_rpc_server_rv.wait.assert_called_once_with()
