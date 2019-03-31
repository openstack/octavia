#    Copyright 2014 Rackspace
#    Copyright 2016 Blue Box, an IBM Company
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

from octavia.api.handlers import abstract_handler
from octavia.common import constants
from octavia.common import data_models
from octavia.db import api as db_api
import octavia.db.repositories as repos

LOG = logging.getLogger(__name__)
ASYNC_TIME = 1


def validate_input(expected, actual):
    if not isinstance(actual, expected):
        raise InvalidHandlerInputObject(obj_type=actual.__class__)


def simulate_controller(data_model, delete=False, update=False, create=False,
                        batch_update=False):
    """Simulates a successful controller operator for a data model.

    :param data_model: data model to simulate controller operation
    :param delete: deletes from the database
    """
    repo = repos.Repositories()

    def member_controller(member, delete=False, update=False, create=False,
                          batch_update=False):
        time.sleep(ASYNC_TIME)
        LOG.info("Simulating controller operation for member...")

        db_mem = None
        if delete:
            db_mem = repo.member.get(db_api.get_session(), id=member.id)
            repo.member.delete(db_api.get_session(), id=member.id)
        elif update:
            db_mem = repo.member.get(db_api.get_session(), id=member.id)
            member_dict = member.to_dict()
            member_dict['operating_status'] = db_mem.operating_status
            repo.member.update(db_api.get_session(), member.id, **member_dict)
        elif create:
            repo.member.update(db_api.get_session(), member.id,
                               operating_status=constants.ONLINE)
        elif batch_update:
            members = member
            for m in members:
                repo.member.update(db_api.get_session(), m.id,
                                   operating_status=constants.ONLINE)
        listeners = []
        if db_mem:
            for listener in db_mem.pool.listeners:
                if listener not in listeners:
                    listeners.append(listener)
        if member.pool.listeners:
            for listener in member.pool.listeners:
                if listener not in listeners:
                    listeners.append(listener)
        if listeners:
            for listener in listeners:
                repo.listener.update(db_api.get_session(), listener.id,
                                     operating_status=constants.ONLINE,
                                     provisioning_status=constants.ACTIVE)
        repo.load_balancer.update(db_api.get_session(),
                                  member.pool.load_balancer.id,
                                  operating_status=constants.ONLINE,
                                  provisioning_status=constants.ACTIVE)
        LOG.info("Simulated Controller Handler Thread Complete")

    def l7policy_controller(l7policy, delete=False, update=False,
                            create=False):
        time.sleep(ASYNC_TIME)
        LOG.info("Simulating controller operation for l7policy...")

        db_l7policy = None
        if delete:
            db_l7policy = repo.l7policy.get(db_api.get_session(),
                                            id=l7policy.id)
            repo.l7policy.delete(db_api.get_session(), id=l7policy.id)
        elif update:
            db_l7policy = repo.l7policy.get(db_api.get_session(),
                                            id=l7policy.id)
            l7policy_dict = l7policy.to_dict()
            repo.l7policy.update(db_api.get_session(), l7policy.id,
                                 **l7policy_dict)
        elif create:
            db_l7policy = repo.l7policy.create(db_api.get_session(),
                                               **l7policy.to_dict())
        if db_l7policy.listener:
            repo.listener.update(db_api.get_session(), db_l7policy.listener.id,
                                 operating_status=constants.ONLINE,
                                 provisioning_status=constants.ACTIVE)
            repo.load_balancer.update(db_api.get_session(),
                                      db_l7policy.listener.load_balancer.id,
                                      operating_status=constants.ONLINE,
                                      provisioning_status=constants.ACTIVE)
        LOG.info("Simulated Controller Handler Thread Complete")

    def l7rule_controller(l7rule, delete=False, update=False, create=False):
        time.sleep(ASYNC_TIME)
        LOG.info("Simulating controller operation for l7rule...")

        db_l7rule = None
        if delete:
            db_l7rule = repo.l7rule.get(db_api.get_session(), id=l7rule.id)
            repo.l7rule.delete(db_api.get_session(), id=l7rule.id)
        elif update:
            db_l7rule = repo.l7rule.get(db_api.get_session(), id=l7rule.id)
            l7rule_dict = l7rule.to_dict()
            repo.l7rule.update(db_api.get_session(), l7rule.id, **l7rule_dict)
        elif create:
            l7rule_dict = l7rule.to_dict()
            db_l7rule = repo.l7rule.create(db_api.get_session(), **l7rule_dict)
        if db_l7rule.l7policy.listener:
            listener = db_l7rule.l7policy.listener
            repo.listener.update(db_api.get_session(), listener.id,
                                 operating_status=constants.ONLINE,
                                 provisioning_status=constants.ACTIVE)
            repo.load_balancer.update(db_api.get_session(),
                                      listener.load_balancer.id,
                                      operating_status=constants.ONLINE,
                                      provisioning_status=constants.ACTIVE)
        LOG.info("Simulated Controller Handler Thread Complete")

    def health_monitor_controller(health_monitor, delete=False, update=False,
                                  create=False):
        time.sleep(ASYNC_TIME)
        LOG.info("Simulating controller operation for health monitor...")

        db_hm = None
        if delete:
            db_hm = repo.health_monitor.get(db_api.get_session(),
                                            pool_id=health_monitor.pool.id)
            repo.health_monitor.delete(db_api.get_session(),
                                       pool_id=health_monitor.pool.id)
        elif update:
            db_hm = repo.health_monitor.get(db_api.get_session(),
                                            pool_id=health_monitor.pool_id)
            hm_dict = health_monitor.to_dict()
            hm_dict['operating_status'] = db_hm.operating_status()
            repo.health_monitor.update(db_api.get_session(), **hm_dict)
        elif create:
            repo.pool.update(db_api.get_session(), health_monitor.pool_id,
                             operating_status=constants.ONLINE)
        listeners = []
        if db_hm:
            for listener in db_hm.pool.listeners:
                if listener not in listeners:
                    listeners.append(listener)
        if health_monitor.pool.listeners:
            for listener in health_monitor.pool.listeners:
                if listener not in listeners:
                    listeners.append(listener)
        if listeners:
            for listener in listeners:
                repo.test_and_set_lb_and_listener_prov_status(
                    db_api.get_session(),
                    health_monitor.pool.load_balancer.id,
                    listener.id, constants.ACTIVE,
                    constants.ACTIVE)
                repo.listener.update(db_api.get_session(),
                                     listener.id,
                                     operating_status=constants.ONLINE,
                                     provisioning_status=constants.ACTIVE)
        repo.load_balancer.update(
            db_api.get_session(),
            health_monitor.pool.load_balancer.id,
            operating_status=constants.ONLINE,
            provisioning_status=constants.ACTIVE)
        LOG.info("Simulated Controller Handler Thread Complete")

    def pool_controller(pool, delete=False, update=False, create=False):
        time.sleep(ASYNC_TIME)
        LOG.info("Simulating controller operation for pool...")

        db_pool = None
        if delete:
            db_pool = repo.pool.get(db_api.get_session(), id=pool.id)
            repo.pool.delete(db_api.get_session(), id=pool.id)
        elif update:
            db_pool = repo.pool.get(db_api.get_session(), id=pool.id)
            pool_dict = pool.to_dict()
            pool_dict['operating_status'] = db_pool.operating_status
            repo.update_pool_and_sp(db_api.get_session(), pool.id, pool_dict)
        elif create:
            repo.pool.update(db_api.get_session(), pool.id,
                             operating_status=constants.ONLINE)
        listeners = []
        if db_pool:
            for listener in db_pool.listeners:
                if listener not in listeners:
                    listeners.append(listener)
        if pool.listeners:
            for listener in pool.listeners:
                if listener not in listeners:
                    listeners.append(listener)
        if listeners:
            for listener in listeners:
                repo.listener.update(db_api.get_session(), listener.id,
                                     operating_status=constants.ONLINE,
                                     provisioning_status=constants.ACTIVE)
        repo.load_balancer.update(db_api.get_session(),
                                  pool.load_balancer.id,
                                  operating_status=constants.ONLINE,
                                  provisioning_status=constants.ACTIVE)
        LOG.info("Simulated Controller Handler Thread Complete")

    def listener_controller(listener, delete=False, update=False,
                            create=False):
        time.sleep(ASYNC_TIME)
        LOG.info("Simulating controller operation for listener...")

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
        LOG.info("Simulated Controller Handler Thread Complete")

    def loadbalancer_controller(loadbalancer, delete=False, update=False,
                                create=False, failover=False):
        time.sleep(ASYNC_TIME)
        LOG.info("Simulating controller operation for loadbalancer...")

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
        elif failover:
            repo.load_balancer.update(
                db_api.get_session(), id=loadbalancer.id,
                operating_status=constants.ONLINE,
                provisioning_status=constants.PENDING_UPDATE)
        LOG.info("Simulated Controller Handler Thread Complete")

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
    message = "Invalid Input Object %(obj_type)s"

    def __init__(self, **kwargs):
        message = self.message % kwargs
        super(InvalidHandlerInputObject, self).__init__(message=message)


class LoadBalancerHandler(abstract_handler.BaseObjectHandler):

    def create(self, load_balancer_id):
        LOG.info("%(entity)s handling the creation of load balancer %(id)s",
                 {"entity": self.__class__.__name__, "id": load_balancer_id})
        simulate_controller(load_balancer_id, create=True)

    def update(self, old_lb, load_balancer):
        validate_input(data_models.LoadBalancer, load_balancer)
        LOG.info("%(entity)s handling the update of load balancer %(id)s",
                 {"entity": self.__class__.__name__, "id": old_lb.id})
        load_balancer.id = old_lb.id
        simulate_controller(load_balancer, update=True)

    def delete(self, load_balancer_id):
        LOG.info("%(entity)s handling the deletion of load balancer %(id)s",
                 {"entity": self.__class__.__name__, "id": load_balancer_id})
        simulate_controller(load_balancer_id, delete=True)


class ListenerHandler(abstract_handler.BaseObjectHandler):

    def create(self, listener_id):
        LOG.info("%(entity)s handling the creation of listener %(id)s",
                 {"entity": self.__class__.__name__, "id": listener_id})
        simulate_controller(listener_id, create=True)

    def update(self, old_listener, listener):
        validate_input(data_models.Listener, listener)
        LOG.info("%(entity)s handling the update of listener %(id)s",
                 {"entity": self.__class__.__name__, "id": old_listener.id})
        listener.id = old_listener.id
        simulate_controller(listener, update=True)

    def delete(self, listener_id):
        LOG.info("%(entity)s handling the deletion of listener %(id)s",
                 {"entity": self.__class__.__name__, "id": listener_id})
        simulate_controller(listener_id, delete=True)


class PoolHandler(abstract_handler.BaseObjectHandler):

    def create(self, pool_id):
        LOG.info("%(entity)s handling the creation of pool %(id)s",
                 {"entity": self.__class__.__name__, "id": pool_id})
        simulate_controller(pool_id, create=True)

    def update(self, old_pool, pool):
        validate_input(data_models.Pool, pool)
        LOG.info("%(entity)s handling the update of pool %(id)s",
                 {"entity": self.__class__.__name__, "id": old_pool.id})
        pool.id = old_pool.id
        simulate_controller(pool, update=True)

    def delete(self, pool_id):
        LOG.info("%(entity)s handling the deletion of pool %(id)s",
                 {"entity": self.__class__.__name__, "id": pool_id})
        simulate_controller(pool_id, delete=True)


class HealthMonitorHandler(abstract_handler.BaseObjectHandler):

    def create(self, pool_id):
        LOG.info("%(entity)s handling the creation of health monitor "
                 "on pool  %(id)s",
                 {"entity": self.__class__.__name__, "id": pool_id})
        simulate_controller(pool_id, create=True)

    def update(self, old_health_monitor, health_monitor):
        validate_input(data_models.HealthMonitor, health_monitor)
        LOG.info("%(entity)s handling the update of health monitor "
                 "on pool %(id)s",
                 {"entity": self.__class__.__name__,
                  "id": old_health_monitor.pool_id})
        health_monitor.pool_id = old_health_monitor.pool_id
        simulate_controller(health_monitor, update=True)

    def delete(self, pool_id):
        LOG.info("%(entity)s handling the deletion of health monitor "
                 "on pool %(id)s",
                 {"entity": self.__class__.__name__, "id": pool_id})
        simulate_controller(pool_id, delete=True)


class MemberHandler(abstract_handler.BaseObjectHandler):

    def create(self, member_id):
        LOG.info("%(entity)s handling the creation of member %(id)s",
                 {"entity": self.__class__.__name__, "id": member_id})
        simulate_controller(member_id, create=True)

    def update(self, old_member, member):
        validate_input(data_models.Member, member)
        LOG.info("%(entity)s handling the update of member %(id)s",
                 {"entity": self.__class__.__name__, "id": old_member.id})
        member.id = old_member.id
        simulate_controller(member, update=True)

    def batch_update(self, old_member_ids, new_member_ids, updated_members):
        for m in updated_members:
            validate_input(data_models.Member, m)
        LOG.info("%(entity)s handling the batch update of members: "
                 "old=%(old)s, new=%(new)s",
                 {"entity": self.__class__.__name__, "old": old_member_ids,
                  "new": new_member_ids})

        repo = repos.Repositories()
        old_members = [repo.member.get(db_api.get_session(), id=mid)
                       for mid in old_member_ids]
        new_members = [repo.member.get(db_api.get_session(), id=mid)
                       for mid in new_member_ids]
        all_members = []
        all_members.extend(old_members)
        all_members.extend(new_members)
        all_members.extend(updated_members)
        simulate_controller(all_members, batch_update=True)

    def delete(self, member_id):
        LOG.info("%(entity)s handling the deletion of member %(id)s",
                 {"entity": self.__class__.__name__, "id": member_id})
        simulate_controller(member_id, delete=True)


class L7PolicyHandler(abstract_handler.BaseObjectHandler):

    def create(self, l7policy_id):
        LOG.info("%(entity)s handling the creation of l7policy %(id)s",
                 {"entity": self.__class__.__name__, "id": l7policy_id})
        simulate_controller(l7policy_id, create=True)

    def update(self, old_l7policy, l7policy):
        validate_input(data_models.L7Policy, l7policy)
        LOG.info("%(entity)s handling the update of l7policy %(id)s",
                 {"entity": self.__class__.__name__, "id": old_l7policy.id})
        l7policy.id = old_l7policy.id
        simulate_controller(l7policy, update=True)

    def delete(self, l7policy_id):
        LOG.info("%(entity)s handling the deletion of l7policy %(id)s",
                 {"entity": self.__class__.__name__, "id": l7policy_id})
        simulate_controller(l7policy_id, delete=True)


class L7RuleHandler(abstract_handler.BaseObjectHandler):

    def create(self, l7rule):
        LOG.info("%(entity)s handling the creation of l7rule %(id)s",
                 {"entity": self.__class__.__name__, "id": l7rule.id})
        simulate_controller(l7rule, create=True)

    def update(self, old_l7rule, l7rule):
        validate_input(data_models.L7Rule, l7rule)
        LOG.info("%(entity)s handling the update of l7rule %(id)s",
                 {"entity": self.__class__.__name__, "id": old_l7rule.id})
        l7rule.id = old_l7rule.id
        simulate_controller(l7rule, update=True)

    def delete(self, l7rule):
        LOG.info("%(entity)s handling the deletion of l7rule %(id)s",
                 {"entity": self.__class__.__name__, "id": l7rule.id})
        simulate_controller(l7rule, delete=True)


class SimulatedControllerHandler(abstract_handler.BaseHandler):
    """Handler that simulates database calls of a successful controller."""
    load_balancer = LoadBalancerHandler()
    listener = ListenerHandler()
    pool = PoolHandler()
    health_monitor = HealthMonitorHandler()
    member = MemberHandler()
    l7policy = L7PolicyHandler()
    l7rule = L7RuleHandler()
