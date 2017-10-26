# Copyright 2015 Rackspace
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

import abc

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging
import six


LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class EventStreamerBase(object):
    """Base class for EventStreamer

    A stand in abstract class that defines what methods are stevedore loaded
    implementations of event streamer is expected to provide.
    """
    @abc.abstractmethod
    def emit(self, cnt):
        """method to send a DB event to neutron-lbaas if it is needed.

        :param cnt: an InfoContainer container object
        :return: None
        """


class EventStreamerNoop(EventStreamerBase):
    """Nop class implementation of EventStreamer

    Useful if you're running in standalone mode and don't need to send
    updates to Neutron LBaaS
    """

    def emit(self, cnt):
        pass


class EventStreamerNeutron(EventStreamerBase):
    """Neutron LBaaS

    When you're using Octavia alongside neutron LBaaS this class provides
    a mechanism to send updates to neutron LBaaS database via
    oslo_messaging queues.
    """

    def __init__(self):
        topic = cfg.CONF.oslo_messaging.event_stream_topic
        if cfg.CONF.oslo_messaging.event_stream_transport_url:
            # Use custom URL
            self.transport = oslo_messaging.get_rpc_transport(
                cfg.CONF, cfg.CONF.oslo_messaging.event_stream_transport_url)
        else:
            self.transport = oslo_messaging.get_rpc_transport(cfg.CONF)
        self.target = oslo_messaging.Target(topic=topic, exchange="common",
                                            namespace='control', fanout=False,
                                            version='1.0')
        self.client = oslo_messaging.RPCClient(self.transport, self.target)

    def emit(self, cnt):
        LOG.debug("Emitting data to event streamer %s", cnt.to_dict())
        self.client.cast({}, 'update_info', container=cnt.to_dict())
