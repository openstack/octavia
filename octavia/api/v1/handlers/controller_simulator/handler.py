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


def simulate_controller(data_model, delete=False, update=False, create=False):
    """Simulates a successful controller operator for a data model.

    :param data_model: data model to simulate controller operation
    :param delete: deletes from the database
    """
    repo = repos.Repositories()

    def member_controller(member, delete=False, update=False, create=False):
        time.sleep(ASYNC_TIME)
        LOG.info(_LI("Simulating controller operation for member..."))

        if delete:
            repo.member.delete(db_api.get_session(), id=member.id)
        elif update:
            old_mem = repo.member.get(db_api.get_session(), member.id)
            member_dict = member.to_dict()
            member_dict['operating_status'] = old_mem.operating_status
            repo.member.update(db_api.get_session(), member.id, **member_dict)
        elif create:
            repo.member.update(db_api.get_session(), member.id,
                               operating_status=constants.ONLINE)
        repo.listener.update(db_api.get_session(), member.pool.listener.id,
                             operating_status=constants.ONLINE,
                             provisioning_status=constants.ACTIVE)
        repo.load_balancer.update(db_api.get_session(),
                                  member.pool.listener.load_balancer.id,
                                  operating_status=constants.ONLINE,
                                  provisioning_status=constants.ACTIVE)
        LOG.info(_LI("Simulated Controller Handler Thread Complete"))

    def health_monitor_controller(health_monitor, delete=False, update=False,
                                  create=False):
        time.sleep(ASYNC_TIME)
        LOG.info(_LI("Simulating controller operation for health monitor..."))

        if delete:
            repo.health_monitor.delete(db_api.get_session(),
                                       pool_id=health_monitor.pool.id)
        elif update:
            hm = repo.health_monitor.get(db_api.get_session(),
                                         health_monitor.pool_id)
            hm_dict = health_monitor.to_dict()
            hm_dict['operating_status'] = hm.operating_status()
            repo.health_monitor.update(db_api.get_session(), **hm_dict)
        elif create:
            repo.pool.update(db_api.get_session(), health_monitor.pool_id,
                             operating_status=constants.ONLINE)
        repo.test_and_set_lb_and_listener_prov_status(
            db_api.get_session(),
            health_monitor.pool.listener.load_balancer.id,
            health_monitor.pool.listener.id, constants.ACTIVE,
            constants.ACTIVE)
        repo.listener.update(db_api.get_session(),
                             health_monitor.pool.listener.id,
                             operating_status=constants.ONLINE,
                             provisioning_status=constants.ACTIVE)
        repo.load_balancer.update(
            db_api.get_session(),
            health_monitor.pool.listener.load_balancer.id,
            operating_status=constants.ONLINE,
            provisioning_status=constants.ACTIVE)
        LOG.info(_LI("Simulated Controller Handler Thread Complete"))

    def pool_controller(pool, delete=False, update=False, create=False):
        time.sleep(ASYNC_TIME)
        LOG.info(_LI("Simulating controller operation for pool..."))

        if delete:
            repo.pool.delete(db_api.get_session(), id=pool.id)
        elif update:
            db_pool = repo.pool.get(db_api.get_session(), id=pool.id)
            pool_dict = pool.to_dict()
            pool_dict['operating_status'] = db_pool.operating_status
            sp_dict = pool_dict.pop('session_persistence', None)
            repo.update_pool_on_listener(db_api.get_session(), pool.id,
                                         pool_dict, sp_dict)
        elif create:
            repo.pool.update(db_api.get_session(), pool.id,
                             operating_status=constants.ONLINE)
        repo.listener.update(db_api.get_session(), pool.listener.id,
                             operating_status=constants.ONLINE,
                             provisioning_status=constants.ACTIVE)
        repo.load_balancer.update(db_api.get_session(),
                                  pool.listener.load_balancer.id,
                                  operating_status=constants.ONLINE,
                                  provisioning_status=constants.ACTIVE)
        LOG.info(_LI("Simulated Controller Handler Thread Complete"))

    def listener_controller(listener, delete=False, update=False,
                            create=False):
        time.sleep(ASYNC_TIME)
        LOG.info(_LI("Simulating controller operation for listener..."))

        if delete:
            repo.listener.update(db_api.get_session(), listener.id,
                                 operating_status=constants.OFFLINE,
                                 provisioning_status=constants.DELETED)
        elif update:
            db_listener = repo.listener.get(db_api.get_session(),
                                            id=listener.id)
            listener_dict = listener.to_dict()
            listener_dict['operating_status'] = db_listener.operating_status
            repo.listener.update(db_api.get_session(), listener.id,
                                 **listener_dict)
        elif create:
            repo.listener.update(db_api.get_session(), listener.id,
                                 operating_status=constants.ONLINE,
                                 provisioning_status=constants.ACTIVE)
        repo.load_balancer.update(db_api.get_session(),
                                  listener.load_balancer.id,
                                  operating_status=constants.ONLINE,
                                  provisioning_status=constants.ACTIVE)
        LOG.info(_LI("Simulated Controller Handler Thread Complete"))

    def loadbalancer_controller(loadbalancer, delete=False, update=False,
                                create=False):
        time.sleep(ASYNC_TIME)
        LOG.info(_LI("Simulating controller operation for loadbalancer..."))

        if delete:
            repo.load_balancer.update(
                db_api.get_session(), id=loadbalancer.id,
                operating_status=constants.OFFLINE,
                provisioning_status=constants.DELETED)
        elif update:
            db_lb = repo.listener.get(db_api.get_session(), id=loadbalancer.id)
            lb_dict = loadbalancer.to_dict()
            lb_dict['operating_status'] = db_lb.operating_status
            repo.load_balancer.update(db_api.get_session(), loadbalancer.id,
                                      **lb_dict)
        elif create:
            repo.load_balancer.update(db_api.get_session(), id=loadbalancer.id,
                                      operating_status=constants.ONLINE,
                                      provisioning_status=constants.ACTIVE)
        LOG.info(_LI("Simulated Controller Handler Thread Complete"))

    controller = loadbalancer_controller
    if isinstance(data_model, data_models.Member):
        controller = member_controller
    elif isinstance(data_model, data_models.HealthMonitor):
        controller = health_monitor_controller
    elif isinstance(data_model, data_models.Pool):
        controller = pool_controller
    elif isinstance(data_model, data_models.Listener):
        controller = listener_controller

    thread = threading.Thread(target=controller, args=(data_model, delete,
                                                       update, create))
    thread.start()


class InvalidHandlerInputObject(Exception):
    message = "Invalid Input Object %(obj_type)"

    def __init__(self, **kwargs):
        message = self.message % kwargs
        super(InvalidHandlerInputObject, self).__init__(message=message)


class LoadBalancerHandler(abstract_handler.BaseObjectHandler):

    def create(self, load_balancer_id):
        LOG.info(_LI("%(entity)s handling the creation of "
                 "load balancer %(id)s") %
                 {"entity": self.__class__.__name__, "id": load_balancer_id})
        simulate_controller(load_balancer_id, create=True)

    def update(self, old_lb, load_balancer):
        validate_input(data_models.LoadBalancer, load_balancer)
        LOG.info(_LI("%(entity)s handling the update of "
                 "load balancer %(id)s") %
                 {"entity": self.__class__.__name__, "id": old_lb.id})
        load_balancer.id = old_lb.id
        simulate_controller(load_balancer, update=True)

    def delete(self, load_balancer_id):
        LOG.info(_LI("%(entity)s handling the deletion of "
                 "load balancer %(id)s") %
                 {"entity": self.__class__.__name__, "id": load_balancer_id})
        simulate_controller(load_balancer_id, delete=True)


class ListenerHandler(abstract_handler.BaseObjectHandler):

    def create(self, listener_id):
        LOG.info(_LI("%(entity)s handling the creation of listener %(id)s") %
                 {"entity": self.__class__.__name__, "id": listener_id})
        simulate_controller(listener_id, create=True)

    def update(self, old_listener, listener):
        validate_input(data_models.Listener, listener)
        LOG.info(_LI("%(entity)s handling the update of listener %(id)s") %
                 {"entity": self.__class__.__name__, "id": old_listener.id})
        listener.id = old_listener.id
        simulate_controller(listener, update=True)

    def delete(self, listener_id):
        LOG.info(_LI("%(entity)s handling the deletion of listener %(id)s") %
                 {"entity": self.__class__.__name__, "id": listener_id})
        simulate_controller(listener_id, delete=True)


class PoolHandler(abstract_handler.BaseObjectHandler):

    def create(self, pool_id):
        LOG.info(_LI("%(entity)s handling the creation of pool %(id)s") %
                 {"entity": self.__class__.__name__, "id": pool_id})
        simulate_controller(pool_id, create=True)

    def update(self, old_pool, pool):
        validate_input(data_models.Pool, pool)
        LOG.info(_LI("%(entity)s handling the update of pool %(id)s") %
                 {"entity": self.__class__.__name__, "id": old_pool.id})
        pool.id = old_pool.id
        simulate_controller(pool, update=True)

    def delete(self, pool_id):
        LOG.info(_LI("%(entity)s handling the deletion of pool %(id)s") %
                 {"entity": self.__class__.__name__, "id": pool_id})
        simulate_controller(pool_id, delete=True)


class HealthMonitorHandler(abstract_handler.BaseObjectHandler):

    def create(self, pool_id):
        LOG.info(_LI("%(entity)s handling the creation of health monitor "
                 "on pool  %(id)s") % {"entity": self.__class__.__name__,
                                       "id": pool_id})
        simulate_controller(pool_id, create=True)

    def update(self, old_health_monitor, health_monitor):
        validate_input(data_models.HealthMonitor, health_monitor)
        LOG.info(_LI("%(entity)s handling the update of health monitor "
                 "on pool %(id)s") % {"entity": self.__class__.__name__,
                                      "id": old_health_monitor.pool_id})
        health_monitor.pool_id = old_health_monitor.pool_id
        simulate_controller(health_monitor, update=True)

    def delete(self, pool_id):
        LOG.info(_LI("%(entity)s handling the deletion of health monitor "
                 "on pool %(id)s") % {"entity": self.__class__.__name__,
                                      "id": pool_id})
        simulate_controller(pool_id, delete=True)


class MemberHandler(abstract_handler.BaseObjectHandler):

    def create(self, member_id):
        LOG.info(_LI("%(entity)s handling the creation of member %(id)s") %
                 {"entity": self.__class__.__name__, "id": member_id})
        simulate_controller(member_id, create=True)

    def update(self, old_member, member):
        validate_input(data_models.Member, member)
        LOG.info(_LI("%(entity)s handling the update of member %(id)s") %
                 {"entity": self.__class__.__name__, "id": old_member.id})
        member.id = old_member.id
        simulate_controller(member, update=True)

    def delete(self, member_id):
        LOG.info(_LI("%(entity)s handling the deletion of member %(id)s") %
                 {"entity": self.__class__.__name__, "id": member_id})
        simulate_controller(member_id, delete=True)


class SimulatedControllerHandler(abstract_handler.BaseHandler):
    """Handler that simulates database calls of a successful controller."""
    load_balancer = LoadBalancerHandler()
    listener = ListenerHandler()
    pool = PoolHandler()
    member = MemberHandler()
    health_monitor = HealthMonitorHandler()
