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
Defines interface for DB access that Resource or Octavia Controllers may
reference
"""

from octavia.common import exceptions
from octavia.db import models


class BaseRepository(object):

    model_class = None

    def create(self, session, **model_kwargs):
        with session.begin():
            model = self.model_class(**model_kwargs)
            session.add(model)
        return model.to_data_model()

    def delete(self, session, **filters):
        model = session.query(self.model_class).filter_by(**filters).first()
        with session.begin():
            session.delete(model)
            session.flush()

    def delete_batch(self, session, ids=None):
        [self.delete(session, id) for id in ids]

    def update(self, session, id, **model_kwargs):
        with session.begin():
            session.query(self.model_class).filter_by(
                id=id).update(model_kwargs)

    def get(self, session, **filters):
        model = session.query(self.model_class).filter_by(**filters).first()
        if not model:
            raise exceptions.NotFound(resource=self.model_class.__name__)
        return model.to_data_model()

    def get_all(self, session, **filters):
        model_list = session.query(self.model_class).filter_by(**filters).all()
        data_model_list = [model.to_data_model() for model in model_list]
        return data_model_list


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


class LoadBalancerRepository(BaseRepository):

    model_class = models.LoadBalancer


class VipRepository(BaseRepository):

    model_class = models.Vip

    def update(self, session, load_balancer_id, **model_kwargs):
        with session.begin():
            session.query(self.model_class).filter_by(
                load_balancer_id=load_balancer_id).update(model_kwargs)


class HealthMonitorRepository(BaseRepository):

    model_class = models.HealthMonitor

    def update(self, session, pool_id, **model_kwargs):
        with session.begin():
            session.query(self.model_class).filter_by(
                pool_id=pool_id).update(model_kwargs)


class SessionPersistenceRepository(BaseRepository):

    model_class = models.SessionPersistence

    def update(self, session, pool_id, **model_kwargs):
        with session.begin():
            session.query(self.model_class).filter_by(
                pool_id=pool_id).update(model_kwargs)


class PoolRepository(BaseRepository):

    model_class = models.Pool


class MemberRepository(BaseRepository):

    model_class = models.Member

    def delete_members(self, session, member_ids):
        self.delete_batch(session, member_ids)


class ListenerRepository(BaseRepository):

    model_class = models.Listener


class ListenerStatisticsRepository(BaseRepository):

    model_class = models.ListenerStatistics

    def update(self, session, listener_id, **model_kwargs):
        with session.begin():
            session.query(self.model_class).filter_by(
                listener_id=listener_id).update(model_kwargs)


class AmphoraRepository(BaseRepository):

    model_class = models.Amphora

    def associate(self, session, load_balancer_id, amphora_id):
        with session.begin():
            load_balancer = session.query(models.LoadBalancer).filter_by(
                id=load_balancer_id).first()
            amphora = session.query(self.model_class).filter_by(
                id=amphora_id).first()
            load_balancer.amphorae.append(amphora)


class SNIRepository(BaseRepository):

    model_class = models.SNI

    def update(self, session, listener_id=None, tls_container_id=None,
               **model_kwargs):
        if not listener_id and tls_container_id:
            raise exceptions.MissingArguments
        with session.begin():
            if listener_id:
                session.query(self.model_class).filter_by(
                    listener_id=listener_id).update(model_kwargs)
            elif tls_container_id:
                session.query(self.model_class).filter_by(
                    tls_container_id=tls_container_id).update(model_kwargs)
