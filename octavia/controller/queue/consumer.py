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

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging

from octavia.controller.queue import endpoint
from octavia.i18n import _LI

LOG = logging.getLogger(__name__)


class Consumer(object):

    def __init__(self):
        topic = cfg.CONF.oslo_messaging.topic
        server = cfg.CONF.host
        transport = messaging.get_transport(cfg.CONF)
        target = messaging.Target(topic=topic, server=server, fanout=False)
        endpoints = [endpoint.Endpoint()]

        self.server = messaging.get_rpc_server(transport, target, endpoints,
                                               executor='eventlet')

    def listen(self):
        try:
            self.server.start()
            LOG.info(_LI('Consumer is now listening...'))
            self.server.wait()
        finally:
            LOG.info(_LI('Stopping consumer...'))
            self.server.stop()
            LOG.info(_LI('Consumer successfully stopped.'))
