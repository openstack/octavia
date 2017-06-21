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
from oslo_config import fixture as oslo_fixture
import oslo_messaging as messaging
from oslo_messaging.rpc import dispatcher

from octavia.controller.queue import consumer
from octavia.controller.queue import endpoint
from octavia.tests.unit import base


@mock.patch.object(messaging, 'get_rpc_transport')
@mock.patch.object(messaging, 'Target')
@mock.patch.object(endpoint, 'Endpoint')
@mock.patch.object(messaging, 'get_rpc_server')
class TestConsumer(base.TestCase):

    def setUp(self):
        super(TestConsumer, self).setUp()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group="oslo_messaging", topic='foo_topic')
        conf.config(host='test-hostname')
        self.conf = conf.conf

    def test_consumer_run(self, mock_rpc_server, mock_endpoint, mock_target,
                          mock_get_transport):
        mock_get_transport_rv = mock.Mock()
        mock_get_transport.return_value = mock_get_transport_rv
        mock_rpc_server_rv = mock.Mock()
        mock_rpc_server.return_value = mock_rpc_server_rv
        mock_endpoint_rv = mock.Mock()
        mock_endpoint.return_value = mock_endpoint_rv
        mock_target_rv = mock.Mock()
        mock_target.return_value = mock_target_rv

        consumer.ConsumerService(1, self.conf).run()

        mock_get_transport.assert_called_once_with(cfg.CONF)
        mock_target.assert_called_once_with(topic='foo_topic',
                                            server='test-hostname',
                                            fanout=False)
        mock_endpoint.assert_called_once_with()
        access_policy = dispatcher.DefaultRPCAccessPolicy
        mock_rpc_server.assert_called_once_with(mock_get_transport_rv,
                                                mock_target_rv,
                                                [mock_endpoint_rv],
                                                executor='threading',
                                                access_policy=access_policy)

    def test_consumer_terminate(self, mock_rpc_server, mock_endpoint,
                                mock_target, mock_get_transport):
        mock_rpc_server_rv = mock.Mock()
        mock_rpc_server.return_value = mock_rpc_server_rv

        cons = consumer.ConsumerService(1, self.conf)
        cons.run()
        cons.terminate()
        mock_rpc_server_rv.stop.assert_called_once_with()
        self.assertFalse(mock_rpc_server_rv.wait.called)

    def test_consumer_graceful_terminate(self, mock_rpc_server, mock_endpoint,
                                         mock_target, mock_get_transport):
        mock_rpc_server_rv = mock.Mock()
        mock_rpc_server.return_value = mock_rpc_server_rv

        cons = consumer.ConsumerService(1, self.conf)
        cons.run()
        cons.terminate(graceful=True)
        mock_rpc_server_rv.stop.assert_called_once_with()
        mock_rpc_server_rv.wait.assert_called_once_with()
