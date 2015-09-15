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

"""
Defines interface for DB access that Resource or Octavia Controllers may
reference
"""

import datetime

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import uuidutils

from octavia.common import constants
from octavia.common import exceptions
from octavia.db import models

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
CONF.import_group('health_manager', 'octavia.common.config')


class BaseRepository(object):
    model_class = None

    def count(self, session, **filters):
        """Retrieves a count of entities from the database.

        :param session: A Sql Alchemy database session.
        :param filters: Filters to decide which entities should be retrieved.
        :returns: int
        """
        return session.query(self.model_class).filter_by(**filters).count()

    def create(self, session, **model_kwargs):
        """Base create method for a database entity.

        :param session: A Sql Alchemy database session.
        :param model_kwargs: Attributes of the model to insert.
        :returns: octavia.common.data_model
        """
        with session.begin(subtransactions=True):
            model = self.model_class(**model_kwargs)
            session.add(model)
        return model.to_data_model()

    def delete(self, session, **filters):
        """Deletes an entity from the database.

        :param session: A Sql Alchemy database session.
        :param filters: Filters to decide which entity should be deleted.
        :returns: None
        """
        model = session.query(self.model_class).filter_by(**filters).first()
        with session.begin(subtransactions=True):
            session.delete(model)
            session.flush()

    def delete_batch(self, session, ids=None):
        """Batch deletes by entity ids."""
        ids = ids or []
        [self.delete(session, id) for id in ids]

    def update(self, session, id, **model_kwargs):
        """Updates an entity in the database.

        :param session: A Sql Alchemy database session.
        :param model_kwargs: Entity attributes that should be updates.
        :returns: octavia.common.data_model
        """
        with session.begin(subtransactions=True):
            session.query(self.model_class).filter_by(
                id=id).update(model_kwargs)

    def get(self, session, **filters):
        """Retrieves an entity from the database.

        :param session: A Sql Alchemy database session.
        :param filters: Filters to decide which entity should be retrieved.
        :returns: octavia.common.data_model
        """
        model = session.query(self.model_class).filter_by(**filters).first()
        if not model:
            return
        return model.to_data_model()

    def get_all(self, session, **filters):
        """Retrieves a list of entities from the database.

        :param session: A Sql Alchemy database session.
        :param filters: Filters to decide which entities should be retrieved.
        :returns: [octavia.common.data_model]
        """
        model_list = session.query(self.model_class).filter_by(**filters).all()
        data_model_list = [model.to_data_model() for model in model_list]
        return data_model_list

    def exists(self, session, id):
        """Determines whether an entity exists in the database by its id.

        :param session: A Sql Alchemy database session.
        :param id: id of entity to check for existance.
        :returns: octavia.common.data_model
        """
        return bool(session.query(self.model_class).filter_by(id=id).first())


class Repositories(object):
    def __init__(self):
        self.load_balancer = LoadBalancerRepository()
        self.vip = VipRepository()
        self.health_monitor = HealthMonitorRepository()
        self.session_persistence = SessionPersistenceRepository()
        self.pool = PoolRepository()
        self.member = MemberRepository()
        self.listener = ListenerRepository()
        self.listener_stats = ListenerStatisticsRepository()
        self.amphora = AmphoraRepository()
        self.sni = SNIRepository()
        self.amphorahealth = AmphoraHealthRepository()

    def create_load_balancer_and_vip(self, session, lb_dict, vip_dict):
        """Inserts load balancer and vip entities into the database.

        Inserts load balancer and vip entities into the database in one
        transaction and returns the data model of the load balancer.

        :param session: A Sql Alchemy database session.
        :param lb_dict: Dictionary representation of a load balancer
        :param vip_dict: Dictionary representation of a vip
        :returns: octava.common.data_models.LoadBalancer
        """
        with session.begin():
            if not lb_dict.get('id'):
                lb_dict['id'] = uuidutils.generate_uuid()
            lb = models.LoadBalancer(**lb_dict)
            session.add(lb)
            vip_dict['load_balancer_id'] = lb_dict['id']
            vip = models.Vip(**vip_dict)
            session.add(vip)
        return self.load_balancer.get(session, id=lb.id)

    def create_pool_on_listener(self, session, listener_id,
                                pool_dict, sp_dict=None):
        """Inserts a pool and session persistence entity into the database.

        :param session: A Sql Alchemy database session.
        :param listener_id: id of the listener the pool will be referenced by
        :param pool_dict: Dictionary representation of a pool
        :param sp_dict: Dictionary representation of a session persistence
        :returns: octavia.common.data_models.Pool
        """
        with session.begin(subtransactions=True):
            if not pool_dict.get('id'):
                pool_dict['id'] = uuidutils.generate_uuid()
            db_pool = self.pool.create(session, **pool_dict)
            if sp_dict:
                sp_dict['pool_id'] = pool_dict['id']
                self.session_persistence.create(session, **sp_dict)
            self.listener.update(session, listener_id,
                                 default_pool_id=pool_dict['id'])
        return self.pool.get(session, id=db_pool.id)

    def update_pool_on_listener(self, session, pool_id, pool_dict, sp_dict):
        """Updates a pool and session persistence entity in the database.

        :param session: A Sql Alchemy database session.
        :param pool_dict: Dictionary representation of a pool
        :param sp_dict: Dictionary representation of a session persistence
        :returns: octavia.common.data_models.Pool
        """
        with session.begin(subtransactions=True):
            self.pool.update(session, pool_id, **pool_dict)
            if sp_dict:
                if self.session_persistence.exists(session, pool_id):
                    self.session_persistence.update(session, pool_id,
                                                    **sp_dict)
                else:
                    sp_dict['pool_id'] = pool_id
                    self.session_persistence.create(session, **sp_dict)
        db_pool = self.pool.get(session, id=pool_id)
        if db_pool.session_persistence is not None and not sp_dict:
            self.session_persistence.delete(session, pool_id=pool_id)
            db_pool = self.pool.get(session, id=pool_id)
        return db_pool

    def test_and_set_lb_and_listener_prov_status(self, session, lb_id,
                                                 listener_id, lb_prov_status,
                                                 listener_prov_status):
        """Tests and sets a load balancer and listener provisioning status.

        Puts a lock on the load balancer table to check the status of a
        load balancer.  If the status is ACTIVE then the status of the load
        balancer and listener is updated and the method returns True.  If the
        status is not ACTIVE, then nothing is done and False is returned.

        :param session: A Sql Alchemy database session.
        :param lb_id: id of Load Balancer
        :param listener_id: id of a Listener
        :param lb_prov_status: Status to set Load Balancer and Listener if
                               check passes.
        :returns: bool
        """
        success = self.load_balancer.test_and_set_provisioning_status(
            session, lb_id, lb_prov_status)
        self.listener.update(session, listener_id,
                             provisioning_status=listener_prov_status)
        return success


class LoadBalancerRepository(BaseRepository):
    model_class = models.LoadBalancer

    def test_and_set_provisioning_status(self, session, id, status):
        """Tests and sets a load balancer and provisioning status.

        Puts a lock on the load balancer table to check the status of a
        load balancer.  If the status is ACTIVE then the status of the load
        balancer is updated and the method returns True.  If the
        status is not ACTIVE, then nothing is done and False is returned.

        :param session: A Sql Alchemy database session.
        :param id: id of Load Balancer
        :param status: Status to set Load Balancer if check passes.
        :returns: bool
        """
        with session.begin(subtransactions=True):
            lb = session.query(self.model_class).with_for_update().filter_by(
                id=id).one()
            if lb.provisioning_status not in constants.MUTABLE_STATUSES:
                return False
            lb.provisioning_status = status
            session.add(lb)
            return True


class VipRepository(BaseRepository):
    model_class = models.Vip

    def update(self, session, load_balancer_id, **model_kwargs):
        """Updates a vip entity in the database by load_balancer_id."""
        with session.begin(subtransactions=True):
            session.query(self.model_class).filter_by(
                load_balancer_id=load_balancer_id).update(model_kwargs)


class HealthMonitorRepository(BaseRepository):
    model_class = models.HealthMonitor

    def update(self, session, pool_id, **model_kwargs):
        """Updates a health monitor entity in the database by pool_id."""
        with session.begin(subtransactions=True):
            session.query(self.model_class).filter_by(
                pool_id=pool_id).update(model_kwargs)


class SessionPersistenceRepository(BaseRepository):
    model_class = models.SessionPersistence

    def update(self, session, pool_id, **model_kwargs):
        """Updates a session persistence entity in the database by pool_id."""
        with session.begin(subtransactions=True):
            session.query(self.model_class).filter_by(
                pool_id=pool_id).update(model_kwargs)

    def exists(self, session, pool_id):
        """Checks if session persistence exists on a pool."""
        return bool(session.query(self.model_class).filter_by(
            pool_id=pool_id).first())


class PoolRepository(BaseRepository):
    model_class = models.Pool


class MemberRepository(BaseRepository):
    model_class = models.Member

    def delete_members(self, session, member_ids):
        """Batch deletes members from a pool."""
        self.delete_batch(session, member_ids)


class ListenerRepository(BaseRepository):
    model_class = models.Listener

    def has_pool(self, session, id):
        """Checks if a listener has a pool."""
        listener = self.get(session, id=id)
        return bool(listener.default_pool)

    def update(self, session, id, **model_kwargs):
        with session.begin(subtransactions=True):
            listener_db = session.query(self.model_class).filter_by(
                id=id).first()
            sni_containers = model_kwargs.pop('sni_containers', [])
            for container_ref in sni_containers:
                sni = models.SNI(listener_id=id,
                                 tls_certificate_id=container_ref)
                listener_db.sni_containers.append(sni)
            listener_db.update(model_kwargs)


class ListenerStatisticsRepository(BaseRepository):
    model_class = models.ListenerStatistics

    def replace(self, session, listener_id, **model_kwargs):
        """replace or insert listener into database."""
        with session.begin(subtransactions=True):
            count = session.query(self.model_class).filter_by(
                listener_id=listener_id).count()
            if count:
                session.query(self.model_class).filter_by(
                    listener_id=listener_id).update(model_kwargs,
                                                    synchronize_session=False)
            else:
                model_kwargs['listener_id'] = listener_id
                self.create(session, **model_kwargs)

    def update(self, session, listener_id, **model_kwargs):
        """Updates a listener's statistics by a listener's id."""
        with session.begin(subtransactions=True):
            session.query(self.model_class).filter_by(
                listener_id=listener_id).update(model_kwargs)


class AmphoraRepository(BaseRepository):
    model_class = models.Amphora

    def associate(self, session, load_balancer_id, amphora_id):
        """Associates an amphora with a load balancer.

        :param session: A Sql Alchemy database session.
        :param load_balancer_id: The load balancer id to associate
        :param amphora_id: The amphora id to associate
        """
        with session.begin(subtransactions=True):
            load_balancer = session.query(models.LoadBalancer).filter_by(
                id=load_balancer_id).first()
            amphora = session.query(self.model_class).filter_by(
                id=amphora_id).first()
            load_balancer.amphorae.append(amphora)

    def allocate_and_associate(self, session, load_balancer_id):
        """Allocate an amphora for a load balancer.

        For v0.5 this is simple, find a free amp and
        associate the lb.  In the future this needs to be
        enhanced.

        :param session: A Sql Alchemy database session.
        :param load_balancer_id: The load balancer id to associate
        :returns: The amphora ID for the load balancer or None
        """
        with session.begin(subtransactions=True):
            amp = session.query(self.model_class).with_for_update().filter_by(
                status='READY', load_balancer_id=None).first()

            if amp is None:
                return None

            amp.status = 'ALLOCATED'
            amp.load_balancer_id = load_balancer_id

        return amp.to_data_model()

    def get_all_lbs_on_amphora(self, session, amphora_id):
        """Get all of the load balancers on an amphora.

        :param session: A Sql Alchemy database session.
        :param amphora_id: The amphora id to list the load balancers from
        :returns: [octavia.common.data_model]
        """
        with session.begin(subtransactions=True):
            lb_subquery = (session.query(self.model_class.load_balancer_id).
                           filter_by(id=amphora_id).subquery())
            lb_list = (session.query(models.LoadBalancer).
                       filter(models.LoadBalancer.id.in_(lb_subquery)).all())
            data_model_list = [model.to_data_model() for model in lb_list]
            return data_model_list

    def get_spare_amphora_count(self, session):
        """Get the count of the spare amphora.

        :returns: Number of current spare amphora.
        """
        with session.begin(subtransactions=True):
            count = session.query(self.model_class).filter_by(
                status=constants.AMPHORA_READY, load_balancer_id=None).count()

        return count


class SNIRepository(BaseRepository):
    model_class = models.SNI

    def update(self, session, listener_id=None, tls_container_id=None,
               **model_kwargs):
        """Updates an SNI entity in the database."""
        if not listener_id and tls_container_id:
            raise exceptions.MissingArguments
        with session.begin(subtransactions=True):
            if listener_id:
                session.query(self.model_class).filter_by(
                    listener_id=listener_id).update(model_kwargs)
            elif tls_container_id:
                session.query(self.model_class).filter_by(
                    tls_container_id=tls_container_id).update(model_kwargs)


class AmphoraHealthRepository(BaseRepository):
    model_class = models.AmphoraHealth

    def update(self, session, amphora_id, **model_kwargs):
        """Updates a healthmanager entity in the database by amphora_id."""
        with session.begin(subtransactions=True):
            session.query(self.model_class).filter_by(
                amphora_id=amphora_id).update(model_kwargs)

    def replace(self, session, amphora_id, **model_kwargs):
        """replace or insert amphora into database."""
        with session.begin(subtransactions=True):
            count = session.query(self.model_class).filter_by(
                amphora_id=amphora_id).count()
            if count:
                session.query(self.model_class).filter_by(
                    amphora_id=amphora_id).update(model_kwargs,
                                                  synchronize_session=False)
            else:
                model_kwargs['amphora_id'] = amphora_id
                self.create(session, **model_kwargs)

    def check_amphora_expired(self, session, amphora_id, exp_age=None):
        """check if a specific amphora is expired

        :param session: A Sql Alchemy database session.
        :param amphora_id: id of an amphora object
        :param exp_age: A standard datetime which is used to see if an
        amphora needs to be updated (default: now - 10s)
        :returns: boolean
        """
        if not exp_age:
            timestamp = datetime.datetime.utcnow() - datetime.timedelta(
                seconds=10)
        else:
            timestamp = datetime.datetime.utcnow() - exp_age
        amphora_health = self.get(session, amphora_id=amphora_id)
        return amphora_health.last_update < timestamp

    def get_stale_amphora(self, session):
        """Retrieves a staled amphora from the health manager database.

        :param session: A Sql Alchemy database session.
        :returns: [octavia.common.data_model]
        """

        timeout = CONF.health_manager.heartbeat_timeout
        expired_time = datetime.datetime.utcnow() - datetime.timedelta(
            seconds=timeout)

        with session.begin(subtransactions=True):
            amp = session.query(self.model_class).with_for_update().filter_by(
                busy=False).filter(
                self.model_class.last_update < expired_time).first()

            if amp is None:
                return None

            amp.busy = True

        return amp.to_data_model()
