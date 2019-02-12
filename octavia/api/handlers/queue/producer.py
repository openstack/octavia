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

from octavia.api.handlers import abstract_handler
from octavia.common import constants
from octavia.common import rpc


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
        self.target = messaging.Target(
            namespace=constants.RPC_NAMESPACE_CONTROLLER_AGENT,
            topic=topic, version="1.0", fanout=False)
        self.client = rpc.get_client(self.target)

    def create(self, model):
        """Sends a create message to the controller via oslo.messaging

        :param model:
        """
        model_id = getattr(model, 'id', None)
        kw = {"{0}_id".format(self.payload_class): model_id}
        method_name = "create_{0}".format(self.payload_class)
        self.client.cast({}, method_name, **kw)

    def update(self, data_model, updated_model):
        """sends an update message to the controller via oslo.messaging

        :param updated_model:
        :param data_model:
        """
        model_id = getattr(data_model, 'id', None)
        kw = {"{0}_updates".format(self.payload_class):
              updated_model.to_dict(render_unsets=False),
              "{0}_id".format(self.payload_class): model_id}
        method_name = "update_{0}".format(self.payload_class)
        self.client.cast({}, method_name, **kw)

    def delete(self, data_model):
        """sends a delete message to the controller via oslo.messaging

        :param data_model:
        """
        model_id = getattr(data_model, 'id', None)
        kw = {"{0}_id".format(self.payload_class): model_id}
        method_name = "delete_{0}".format(self.payload_class)
        self.client.cast({}, method_name, **kw)


class LoadBalancerProducer(BaseProducer):
    """Sends updates,deletes and creates to the RPC end of the queue consumer

    """
    PAYLOAD_CLASS = "load_balancer"

    @property
    def payload_class(self):
        return self.PAYLOAD_CLASS

    def delete(self, data_model, cascade):
        """sends a delete message to the controller via oslo.messaging

        :param data_model:
        :param: cascade: delete listeners, etc. as well
        """
        model_id = getattr(data_model, 'id', None)
        p_class = self.payload_class
        kw = {"{0}_id".format(p_class): model_id, "cascade": cascade}
        method_name = "delete_{0}".format(self.payload_class)
        self.client.cast({}, method_name, **kw)

    def failover(self, data_model):
        """sends a failover message to the controller via oslo.messaging

        :param data_model:
        """
        model_id = getattr(data_model, 'id', None)
        p_class = self.payload_class
        kw = {"{0}_id".format(p_class): model_id}
        method_name = "failover_{0}".format(self.payload_class)
        self.client.cast({}, method_name, **kw)


class AmphoraProducer(BaseProducer):
    """Sends failover messages to the RPC end of the queue consumer

    """
    PAYLOAD_CLASS = "amphora"

    @property
    def payload_class(self):
        return self.PAYLOAD_CLASS

    def failover(self, data_model):
        """sends a failover message to the controller via oslo.messaging

        :param data_model:
        """
        model_id = getattr(data_model, 'id', None)
        p_class = self.payload_class
        kw = {"{0}_id".format(p_class): model_id}
        method_name = "failover_{0}".format(self.payload_class)
        self.client.cast({}, method_name, **kw)


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

    def batch_update(self, old_ids, new_ids, updated_models):
        """sends an update message to the controller via oslo.messaging

        :param old_ids: list of member ids that are being deleted
        :param new_ids: list of member ids that are being created
        :param updated_models: list of member model objects to update
        """
        updated_dicts = [m.to_dict(render_unsets=False)
                         for m in updated_models]
        kw = {"old_{0}_ids".format(self.payload_class): old_ids,
              "new_{0}_ids".format(self.payload_class): new_ids,
              "updated_{0}s".format(self.payload_class): updated_dicts}
        method_name = "batch_update_{0}s".format(self.payload_class)
        self.client.cast({}, method_name, **kw)


class L7PolicyProducer(BaseProducer):
    """Sends updates,deletes and creates to the RPC end of the queue consumer

    """
    PAYLOAD_CLASS = "l7policy"

    @property
    def payload_class(self):
        return self.PAYLOAD_CLASS


class L7RuleProducer(BaseProducer):
    """Sends updates,deletes and creates to the RPC end of the queue consumer

    """
    PAYLOAD_CLASS = "l7rule"

    @property
    def payload_class(self):
        return self.PAYLOAD_CLASS


class ProducerHandler(abstract_handler.BaseHandler):
    """Base class for all QueueProducers.

    used to send messages via the Class variables load_balancer, listener,
    health_monitor, member, l7policy and l7rule.
    """
    def __init__(self):
        self.load_balancer = LoadBalancerProducer()
        self.listener = ListenerProducer()
        self.pool = PoolProducer()
        self.health_monitor = HealthMonitorProducer()
        self.member = MemberProducer()
        self.l7policy = L7PolicyProducer()
        self.l7rule = L7RuleProducer()
        self.amphora = AmphoraProducer()
