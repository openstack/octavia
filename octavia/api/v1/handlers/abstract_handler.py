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
#    under the License.

import abc

import six


@six.add_metaclass(abc.ABCMeta)
class BaseObjectHandler(object):
    """Base class for any object handler."""
    @abc.abstractmethod
    def create(self, model_id):
        """Begins process of actually creating data_model."""
        pass

    @abc.abstractmethod
    def update(self, model_id, updated_dict):
        """Begins process of actually updating data_model."""
        pass

    @abc.abstractmethod
    def delete(self, model_id):
        """Begins process of actually deleting data_model."""
        pass


class NotImplementedObjectHandler(BaseObjectHandler):
    """Default Object Handler to force implementation of subclasses.

    Helper class to make any subclass of AbstractHandler explode if it
    is missing any of the required object managers.
    """
    @staticmethod
    def update(model_id, updated_dict):
        raise NotImplementedError()

    @staticmethod
    def delete(model_id):
        raise NotImplementedError()

    @staticmethod
    def create(model_id):
        raise NotImplementedError()


@six.add_metaclass(abc.ABCMeta)
class BaseHandler(object):
    """Base class for all handlers."""
    load_balancer = NotImplementedObjectHandler()
    listener = NotImplementedObjectHandler()
    pool = NotImplementedObjectHandler()
    health_monitor = NotImplementedObjectHandler()
    member = NotImplementedObjectHandler()
