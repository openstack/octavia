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

"""
This is just a handler that will simulate successful operations a controller
should perform.  There is nothing useful about this other than database
entity status management.
"""

import threading
import time

from oslo_log import log as logging

from octavia.api.v1.handlers import abstract_handler
from octavia.common import constants
from octavia.common import data_models
from octavia.db import api as db_api
import octavia.db.repositories as repos
from octavia.i18n import _LI


LOG = logging.getLogger(__name__)
ASYNC_TIME = 1


def validate_input(expected, actual):
    if not isinstance(actual, expected):
        raise InvalidHandlerInputObject(obj_type=actual.__class__)


def simulate_controller(data_model, delete=False):
    """Simulates a successful controller operator for a data model.

    :param data_model: data model to simulate controller operation
    :param delete: deletes from the database
    """
    repo = repos.Repositories()

    def controller(model, delete):

        def session():
            return db_api.get_session()

        time.sleep(ASYNC_TIME)
        LOG.info(_LI("Simulating controller operation for %(entity)s...") %
                 {"entity": model.__class__.__name__})
        if isinstance(model, data_models.Member):
            if delete:
                repo.member.delete(session(), id=model.id)
            else:
                repo.member.update(session(), model.id,
                                   operating_status=constants.ONLINE)
            repo.listener.update(session(), model.pool.listener.id,
                                 operating_status=constants.ONLINE,
                                 provisioning_status=constants.ACTIVE)
            repo.load_balancer.update(session(),
                                      model.pool.listener.load_balancer.id,
                                      provisioning_status=constants.ACTIVE)
        elif isinstance(model, data_models.Pool):
            if delete:
                repo.pool.delete(session(), id=model.id)
            else:
                repo.pool.update(session(), model.id,
                                 operating_status=constants.ONLINE)
            repo.listener.update(session(), model.listener.id,
                                 operating_status=constants.ONLINE,
                                 provisioning_status=constants.ACTIVE)
            repo.load_balancer.update(session(),
                                      model.listener.load_balancer.id,
                                      operating_status=constants.ONLINE,
                                      provisioning_status=constants.ACTIVE)
        elif isinstance(model, data_models.Listener):
            if delete:
                repo.listener.update(session(), model.id,
                                     operating_status=constants.OFFLINE,
                                     provisioning_status=constants.DELETED)
            else:
                repo.listener.update(session(), model.id,
                                     operating_status=constants.ONLINE,
                                     provisioning_status=constants.ACTIVE)
            repo.load_balancer.update(session(),
                                      model.load_balancer.id,
                                      operating_status=constants.ONLINE,
                                      provisioning_status=constants.ACTIVE)
        elif isinstance(model, data_models.LoadBalancer):
            if delete:
                repo.load_balancer.update(
                    session(), id=model.id, operating_status=constants.OFFLINE,
                    provisioning_status=constants.DELETED)
            else:
                repo.load_balancer.update(session(), id=model.id,
                                          operating_status=constants.ONLINE,
                                          provisioning_status=constants.ACTIVE)
        else:
            if delete:
                repo.health_monitor.delete(session(), pool_id=model.pool.id)
            repo.listener.update(session(), model.pool.listener.id,
                                 operating_status=constants.ONLINE,
                                 provisioning_status=constants.ACTIVE)
            repo.load_balancer.update(session(),
                                      model.pool.listener.load_balancer.id,
                                      operating_status=constants.ONLINE,
                                      provisioning_status=constants.ACTIVE)
        LOG.info(_LI("Simulated Controller Handler Thread Complete"))

    thread = threading.Thread(target=controller, args=(data_model, delete))
    thread.start()


class InvalidHandlerInputObject(Exception):
    message = "Invalid Input Object %(obj_type)"

    def __init__(self, **kwargs):
        message = self.message % kwargs
        super(InvalidHandlerInputObject, self).__init__(message=message)


class LoadBalancerHandler(abstract_handler.BaseObjectHandler):

    def create(self, load_balancer):
        validate_input(data_models.LoadBalancer, load_balancer)
        LOG.info(_LI("%(entity)s handling the creation of "
                 "load balancer %(id)s") %
                 {"entity": self.__class__.__name__, "id": load_balancer.id})
        simulate_controller(load_balancer)

    def update(self, load_balancer):
        validate_input(data_models.LoadBalancer, load_balancer)
        LOG.info(_LI("%(entity)s handling the update of "
                 "load balancer %(id)s") %
                 {"entity": self.__class__.__name__, "id": load_balancer.id})
        simulate_controller(load_balancer)

    def delete(self, load_balancer):
        validate_input(data_models.LoadBalancer, load_balancer)
        LOG.info(_LI("%(entity)s handling the deletion of "
                 "load balancer %(id)s") %
                 {"entity": self.__class__.__name__, "id": load_balancer.id})
        simulate_controller(load_balancer, delete=True)


class ListenerHandler(abstract_handler.BaseObjectHandler):

    def create(self, listener):
        validate_input(data_models.Listener, listener)
        LOG.info(_LI("%(entity)s handling the creation of listener %(id)s") %
                 {"entity": self.__class__.__name__, "id": listener.id})
        simulate_controller(listener)

    def update(self, listener):
        validate_input(data_models.Listener, listener)
        LOG.info(_LI("%(entity)s handling the update of listener %(id)s") %
                 {"entity": self.__class__.__name__, "id": listener.id})
        simulate_controller(listener)

    def delete(self, listener):
        validate_input(data_models.Listener, listener)
        LOG.info(_LI("%(entity)s handling the deletion of listener %(id)s") %
                 {"entity": self.__class__.__name__, "id": listener.id})
        simulate_controller(listener, delete=True)


class PoolHandler(abstract_handler.BaseObjectHandler):

    def create(self, pool):
        validate_input(data_models.Pool, pool)
        LOG.info(_LI("%(entity)s handling the creation of pool %(id)s") %
                 {"entity": self.__class__.__name__, "id": pool.id})
        simulate_controller(pool)

    def update(self, pool):
        validate_input(data_models.Pool, pool)
        LOG.info(_LI("%(entity)s handling the update of pool %(id)s") %
                 {"entity": self.__class__.__name__, "id": pool.id})
        simulate_controller(pool)

    def delete(self, pool):
        validate_input(data_models.Pool, pool)
        LOG.info(_LI("%(entity)s handling the deletion of pool %(id)s") %
                 {"entity": self.__class__.__name__, "id": pool.id})
        simulate_controller(pool, delete=True)


class HealthMonitorHandler(abstract_handler.BaseObjectHandler):

    def create(self, health_monitor):
        validate_input(data_models.HealthMonitor, health_monitor)
        LOG.info(_LI("%(entity)s handling the creation of health monitor "
                 "on pool  %(id)s") %
                 {"entity": self.__class__.__name__,
                  "id": health_monitor.pool_id})
        simulate_controller(health_monitor)

    def update(self, health_monitor):
        validate_input(data_models.HealthMonitor, health_monitor)
        LOG.info(_LI("%(entity)s handling the update of health monitor "
                 "on pool %(id)s") %
                 {"entity": self.__class__.__name__,
                  "id": health_monitor.pool_id})
        simulate_controller(health_monitor)

    def delete(self, health_monitor):
        validate_input(data_models.HealthMonitor, health_monitor)
        LOG.info(_LI("%(entity)s handling the deletion of health monitor "
                 "on pool %(id)s") %
                 {"entity": self.__class__.__name__,
                  "id": health_monitor.pool_id})
        simulate_controller(health_monitor, delete=True)


class MemberHandler(abstract_handler.BaseObjectHandler):

    def create(self, member):
        validate_input(data_models.Member, member)
        LOG.info(_LI("%(entity)s handling the creation of member %(id)s") %
                 {"entity": self.__class__.__name__, "id": member.id})
        simulate_controller(member)

    def update(self, member):
        validate_input(data_models.Member, member)
        LOG.info(_LI("%(entity)s handling the update of member %(id)s") %
                 {"entity": self.__class__.__name__, "id": member.id})
        simulate_controller(member)

    def delete(self, member):
        validate_input(data_models.Member, member)
        LOG.info(_LI("%(entity)s handling the deletion of member %(id)s") %
                 {"entity": self.__class__.__name__, "id": member.id})
        simulate_controller(member, delete=True)


class SimulatedControllerHandler(abstract_handler.BaseHandler):
    """Handler that simulates database calls of a successful controller."""
    load_balancer = LoadBalancerHandler()
    listener = ListenerHandler()
    pool = PoolHandler()
    member = MemberHandler()
    health_monitor = HealthMonitorHandler()
