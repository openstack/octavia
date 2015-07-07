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

from oslo_config import cfg
import oslo_messaging as messaging
import six

from octavia.api.v1.handlers import abstract_handler
from octavia.common import constants
from octavia.common import data_models

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

        :param model:
        """
        model_id = getattr(model, 'id', None)
        p_class = self.payload_class
        if isinstance(model, data_models.HealthMonitor):
            model_id = model.pool_id
            p_class = PoolProducer.PAYLOAD_CLASS
        kw = {"{0}_id".format(p_class): model_id}
        method_name = "create_{0}".format(self.payload_class)
        self.client.cast({}, method_name, **kw)

    def update(self, data_model, updated_model):
        """sends an update message to the controller via oslo.messaging

        :param updated_model:
        :param data_model:
        """
        model_id = getattr(data_model, 'id', None)
        p_class = self.payload_class
        if isinstance(data_model, data_models.HealthMonitor):
            model_id = data_model.pool_id
            p_class = PoolProducer.PAYLOAD_CLASS
        kw = {"{0}_updates".format(self.payload_class):
              updated_model.to_dict(render_unsets=False),
              "{0}_id".format(p_class): model_id}
        method_name = "update_{0}".format(self.payload_class)
        self.client.cast({}, method_name, **kw)

    def delete(self, data_model):
        """sends a delete message to the controller via oslo.messaging

        :param data_model:
        """
        model_id = getattr(data_model, 'id', None)
        p_class = self.payload_class
        if isinstance(data_model, data_models.HealthMonitor):
            model_id = data_model.pool_id
            p_class = PoolProducer.PAYLOAD_CLASS
        kw = {"{0}_id".format(p_class): model_id}
        method_name = "delete_{0}".format(self.payload_class)
        self.client.cast({}, method_name, **kw)


class LoadBalancerProducer(BaseProducer):
    """Sends updates,deletes and creates to the RPC end of the queue consumer

    """
    PAYLOAD_CLASS = "load_balancer"

    @property
    def payload_class(self):
        return self.PAYLOAD_CLASS


class ListenerProducer(BaseProducer):
    """Sends updates,deletes and creates to the RPC end of the queue consumer

    """
    PAYLOAD_CLASS = "listener"

    @property
    def payload_class(self):
        return self.PAYLOAD_CLASS


class PoolProducer(BaseProducer):
    """Sends updates,deletes and creates to the RPC end of the queue consumer

    """
    PAYLOAD_CLASS = "pool"

    @property
    def payload_class(self):
        return self.PAYLOAD_CLASS


class HealthMonitorProducer(BaseProducer):
    """Sends updates,deletes and creates to the RPC end of the queue consumer

    """
    PAYLOAD_CLASS = "health_monitor"

    @property
    def payload_class(self):
        return self.PAYLOAD_CLASS


class MemberProducer(BaseProducer):
    """Sends updates,deletes and creates to the RPC end of the queue consumer

    """
    PAYLOAD_CLASS = "member"

    @property
    def payload_class(self):
        return self.PAYLOAD_CLASS


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
