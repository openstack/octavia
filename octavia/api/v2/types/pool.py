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

from wsme import types as wtypes

from octavia.api.common import types
from octavia.api.v2.types import health_monitor
from octavia.api.v2.types import member
from octavia.common import constants


class SessionPersistenceResponse(types.BaseType):
    """Defines which attributes are to be shown on any response."""
    type = wtypes.wsattr(wtypes.text)
    cookie_name = wtypes.wsattr(wtypes.text)


class SessionPersistencePOST(types.BaseType):
    """Defines mandatory and optional attributes of a POST request."""
    type = wtypes.wsattr(wtypes.Enum(str, *constants.SUPPORTED_SP_TYPES),
                         mandatory=True)
    cookie_name = wtypes.wsattr(wtypes.text)


class SessionPersistencePUT(types.BaseType):
    """Defines attributes that are acceptable of a PUT request."""
    type = wtypes.wsattr(wtypes.Enum(str, *constants.SUPPORTED_SP_TYPES))
    cookie_name = wtypes.wsattr(wtypes.text, default=None)


class BasePoolType(types.BaseType):
    _type_to_model_map = {'admin_state_up': 'enabled',
                          'healthmonitor': 'health_monitor'}
    _child_map = {}


class PoolResponse(BasePoolType):
    """Defines which attributes are to be shown on any response."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType())
    description = wtypes.wsattr(wtypes.StringType())
    provisioning_status = wtypes.wsattr(wtypes.StringType())
    operating_status = wtypes.wsattr(wtypes.StringType())
    admin_state_up = wtypes.wsattr(bool)
    protocol = wtypes.wsattr(wtypes.text)
    lb_algorithm = wtypes.wsattr(wtypes.text)
    session_persistence = wtypes.wsattr(SessionPersistenceResponse)
    project_id = wtypes.wsattr(wtypes.StringType())
    loadbalancers = wtypes.wsattr([types.IdOnlyType])
    listeners = wtypes.wsattr([types.IdOnlyType])
    created_at = wtypes.wsattr(wtypes.datetime.datetime)
    updated_at = wtypes.wsattr(wtypes.datetime.datetime)
    healthmonitor_id = wtypes.wsattr(wtypes.UuidType())
    members = wtypes.wsattr([types.IdOnlyType])

    @classmethod
    def from_data_model(cls, data_model, children=False):
        pool = super(PoolResponse, cls).from_data_model(
            data_model, children=children)
        if data_model.session_persistence:
            pool.session_persistence = (
                SessionPersistenceResponse.from_data_model(
                    data_model.session_persistence))

        if cls._full_response():
            del pool.loadbalancers
            member_model = member.MemberFullResponse
            if pool.healthmonitor:
                pool.healthmonitor = (
                    health_monitor.HealthMonitorFullResponse
                    .from_data_model(data_model.health_monitor))
        else:
            if data_model.load_balancer:
                pool.loadbalancers = [
                    types.IdOnlyType.from_data_model(data_model.load_balancer)]
            else:
                pool.loadbalancers = []
            member_model = types.IdOnlyType
            if data_model.health_monitor:
                pool.healthmonitor_id = data_model.health_monitor.id

        pool.listeners = [
            types.IdOnlyType.from_data_model(i) for i in data_model.listeners]
        pool.members = [
            member_model.from_data_model(i) for i in data_model.members]

        return pool


class PoolFullResponse(PoolResponse):
    @classmethod
    def _full_response(cls):
        return True

    members = wtypes.wsattr([member.MemberFullResponse])
    healthmonitor = wtypes.wsattr(health_monitor.HealthMonitorFullResponse)


class PoolRootResponse(types.BaseType):
    pool = wtypes.wsattr(PoolResponse)


class PoolsRootResponse(types.BaseType):
    pools = wtypes.wsattr([PoolResponse])
    pools_links = wtypes.wsattr([types.PageType])


class PoolPOST(BasePoolType):
    """Defines mandatory and optional attributes of a POST request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    admin_state_up = wtypes.wsattr(bool, default=True)
    listener_id = wtypes.wsattr(wtypes.UuidType())
    loadbalancer_id = wtypes.wsattr(wtypes.UuidType())
    protocol = wtypes.wsattr(wtypes.Enum(str, *constants.SUPPORTED_PROTOCOLS),
                             mandatory=True)
    lb_algorithm = wtypes.wsattr(
        wtypes.Enum(str, *constants.SUPPORTED_LB_ALGORITHMS),
        mandatory=True)
    session_persistence = wtypes.wsattr(SessionPersistencePOST)
    # TODO(johnsom) Remove after deprecation (R series)
    project_id = wtypes.wsattr(wtypes.StringType(max_length=36))
    healthmonitor = wtypes.wsattr(health_monitor.HealthMonitorSingleCreate)
    members = wtypes.wsattr([member.MemberSingleCreate])


class PoolRootPOST(types.BaseType):
    pool = wtypes.wsattr(PoolPOST)


class PoolPUT(BasePoolType):
    """Defines attributes that are acceptable of a PUT request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    admin_state_up = wtypes.wsattr(bool)
    lb_algorithm = wtypes.wsattr(
        wtypes.Enum(str, *constants.SUPPORTED_LB_ALGORITHMS))
    session_persistence = wtypes.wsattr(SessionPersistencePUT)


class PoolRootPut(types.BaseType):
    pool = wtypes.wsattr(PoolPUT)


class PoolSingleCreate(BasePoolType):
    """Defines mandatory and optional attributes of a POST request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    admin_state_up = wtypes.wsattr(bool, default=True)
    protocol = wtypes.wsattr(wtypes.Enum(str, *constants.SUPPORTED_PROTOCOLS))
    lb_algorithm = wtypes.wsattr(
        wtypes.Enum(str, *constants.SUPPORTED_LB_ALGORITHMS))
    session_persistence = wtypes.wsattr(SessionPersistencePOST)
    healthmonitor = wtypes.wsattr(health_monitor.HealthMonitorSingleCreate)
    members = wtypes.wsattr([member.MemberSingleCreate])


class PoolStatusResponse(BasePoolType):
    """Defines which attributes are to be shown on status response."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType())
    provisioning_status = wtypes.wsattr(wtypes.StringType())
    operating_status = wtypes.wsattr(wtypes.StringType())
    health_monitor = wtypes.wsattr(
        health_monitor.HealthMonitorStatusResponse)
    members = wtypes.wsattr([member.MemberStatusResponse])

    @classmethod
    def from_data_model(cls, data_model, children=False):
        pool = super(PoolStatusResponse, cls).from_data_model(
            data_model, children=children)

        member_model = member.MemberStatusResponse
        if data_model.health_monitor:
            pool.health_monitor = (
                health_monitor.HealthMonitorStatusResponse.from_data_model(
                    data_model.health_monitor))
        pool.members = [
            member_model.from_data_model(i) for i in data_model.members]

        return pool
