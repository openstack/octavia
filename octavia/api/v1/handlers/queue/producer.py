#    Copyright 2014 Rackspace
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
#    under the License.#    Copyright 2014 Rackspace
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

from oslo.config import cfg
from oslo import messaging
import six

from octavia.api.v1.handlers import abstract_handler
from octavia.common import constants

cfg.CONF.import_group('oslo_messaging', 'octavia.common.config')


@six.add_metaclass(abc.ABCMeta)
class BaseProducer(abstract_handler.BaseObjectHandler):
    """Base queue producer class."""
    @abc.abstractproperty
    def payload_class(self):
        """returns a string representing the container class."""
        pass

    def __init__(self):
        topic = cfg.CONF.oslo_messaging.topic
        self.transport = messaging.get_transport(cfg.CONF)
        self.target = messaging.Target(
            namespace=constants.RPC_NAMESPACE_CONTROLLER_AGENT,
            topic=topic, version="1.0", fanout=False)
        self.client = messaging.RPCClient(self.transport, target=self.target)

    def create(self, model):
        """Sends a create message to the controller via oslo.messaging

        :param data_model:
        """
        kw = {"{0}_id".format(self.payload_class): model.id}
        method_name = "create_{0}".format(self.payload_class)
        self.client.cast({}, method_name, **kw)

    def update(self, model, updated_dict):
        """sends an update message to the controller via oslo.messaging

        :param updated_model:
        :param data_model:
        """
        kw = {"{0}_updates".format(self.payload_class): updated_dict,
              "{0}_id".format(self.payload_class): model.id}
        method_name = "update_{0}".format(self.payload_class)
        self.client.cast({}, method_name, **kw)

    def delete(self, model):
        """sends a delete message to the controller via oslo.messaging

        :param updated_model:
        :param data_model:
        """
        kw = {"{0}_id".format(self.payload_class): model.id}
        method_name = "delete_{0}".format(self.payload_class)
        self.client.cast({}, method_name, **kw)


class LoadBalancerProducer(BaseProducer):
    """Sends updates,deletes and creates to the RPC end of the queue consumer

    """
    @property
    def payload_class(self):
        return "load_balancer"


class ListenerProducer(BaseProducer):
    """Sends updates,deletes and creates to the RPC end of the queue consumer


    """
    @property
    def payload_class(self):
        return "listener"


class PoolProducer(BaseProducer):
    """Sends updates,deletes and creates to the RPC end of the queue consumer

    """
    @property
    def payload_class(self):
        return "pool"


class HealthMonitorProducer(BaseProducer):
    """Sends updates,deletes and creates to the RPC end of the queue consumer

    """
    @property
    def payload_class(self):
        return "health_monitor"


class MemberProducer(BaseProducer):
    """Sends updates,deletes and creates to the RPC end of the queue consumer

    """
    @property
    def payload_class(self):
        return "member"


class ProducerHandler(abstract_handler.BaseHandler):
    """Base class for all QueueProducers.

    used to send messages via the Class variables load_balancer, listener,
    health_monitor, and member.
    """

    load_balancer = LoadBalancerProducer()
    listener = ListenerProducer()
    pool = PoolProducer()
    health_monitor = HealthMonitorProducer()
    member = MemberProducer()