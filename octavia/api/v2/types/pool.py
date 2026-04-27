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

from octavia_lib.common import constants as lib_constants
from wsme import types as wtypes

from octavia.api.common import types
from octavia.api.v2.types import health_monitor as health_monitor_types
from octavia.api.v2.types import member as member_types
from octavia.common import constants


class SessionPersistenceResponse(types.BaseType):
    """Defines which attributes are to be shown on any response."""
    type = wtypes.wsattr(wtypes.text)
    cookie_name = wtypes.wsattr(wtypes.text)
    persistence_timeout = wtypes.wsattr(wtypes.IntegerType())
    persistence_granularity = wtypes.wsattr(types.IPAddressType())


class SessionPersistencePOST(types.BaseType):
    """Defines mandatory and optional attributes of a POST request."""
    type = wtypes.wsattr(wtypes.Enum(str, *constants.SUPPORTED_SP_TYPES),
                         mandatory=True)
    # pattern of invalid characters is based on
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie
    cookie_name = wtypes.wsattr(wtypes.StringType(
        max_length=255, pattern=r'^[^\s,;\\]+$'),
        default=None)
    persistence_timeout = wtypes.wsattr(wtypes.IntegerType(), default=None)
    persistence_granularity = wtypes.wsattr(types.IPAddressType(),
                                            default=None)


class SessionPersistencePUT(types.BaseType):
    """Defines attributes that are acceptable of a PUT request."""
    type = wtypes.wsattr(wtypes.Enum(str, *constants.SUPPORTED_SP_TYPES))
    # pattern of invalid characters is based on
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie
    cookie_name = wtypes.wsattr(wtypes.StringType(
        max_length=255, pattern=r'^[^\s,;\\]+$'),
        default=None)
    persistence_timeout = wtypes.wsattr(wtypes.IntegerType(), default=None)
    persistence_granularity = wtypes.wsattr(types.IPAddressType(),
                                            default=None)


class BasePoolType(types.BaseType):
    _type_to_db_map = {'admin_state_up': 'enabled',
                       'healthmonitor': 'health_monitor',
                       'healthmonitor_id': 'health_monitor.id',
                       'tls_container_ref': 'tls_certificate_id',
                       'ca_tls_container_ref': 'ca_tls_certificate_id',
                       'crl_container_ref': 'crl_container_id'}

    _child_map = {'health_monitor': {'id': 'healthmonitor_id'}}


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
    tags = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType()))
    tls_container_ref = wtypes.wsattr(wtypes.StringType())
    ca_tls_container_ref = wtypes.wsattr(wtypes.StringType())
    crl_container_ref = wtypes.wsattr(wtypes.StringType())
    tls_enabled = wtypes.wsattr(bool)
    tls_ciphers = wtypes.wsattr(wtypes.StringType())
    tls_versions = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType()))
    alpn_protocols = wtypes.wsattr(wtypes.ArrayType(types.AlpnProtocolType()))

    @classmethod
    def from_db_obj(cls, db_obj):
        result = super().from_db_obj(db_obj)

        result.listeners = [
            types.IdOnlyType.from_db_obj(listener)
            for listener in db_obj.listeners
        ]

        if db_obj.session_persistence:
            result.session_persistence = (
                SessionPersistenceResponse
                .from_db_obj(db_obj.session_persistence)
            )

        if cls._full_response():
            if db_obj.health_monitor:
                result.healthmonitor = (
                    health_monitor_types.HealthMonitorFullResponse
                    .from_db_obj(db_obj.health_monitor)
                )

            result.members = [
                member_types.MemberFullResponse.from_db_obj(member)
                for member in db_obj.members
            ]
        else:
            if db_obj.load_balancer:
                result.loadbalancers = [
                    types.IdOnlyType.from_db_obj(db_obj.load_balancer)
                ]
            else:
                result.loadbalancers = []

            if db_obj.health_monitor:
                result.healthmonitor_id = db_obj.health_monitor.id

            result.members = [
                types.IdOnlyType.from_db_obj(member)
                for member in db_obj.members
            ]

        return result


class PoolFullResponse(PoolResponse):
    @classmethod
    def _full_response(cls):
        return True

    members = wtypes.wsattr([member_types.MemberFullResponse])
    healthmonitor = wtypes.wsattr(
        health_monitor_types.HealthMonitorFullResponse)


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
    protocol = wtypes.wsattr(
        wtypes.Enum(str, *lib_constants.POOL_SUPPORTED_PROTOCOLS),
        mandatory=True)
    lb_algorithm = wtypes.wsattr(
        wtypes.Enum(str, *constants.SUPPORTED_LB_ALGORITHMS),
        mandatory=True)
    session_persistence = wtypes.wsattr(SessionPersistencePOST)
    # TODO(johnsom) Remove after deprecation (R series)
    project_id = wtypes.wsattr(wtypes.StringType(max_length=36))
    healthmonitor = wtypes.wsattr(
        health_monitor_types.HealthMonitorSingleCreate)
    members = wtypes.wsattr([member_types.MemberSingleCreate])
    tags = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType(max_length=255)))
    tls_container_ref = wtypes.wsattr(
        wtypes.StringType(max_length=255))
    ca_tls_container_ref = wtypes.wsattr(wtypes.StringType(max_length=255))
    crl_container_ref = wtypes.wsattr(wtypes.StringType(max_length=255))
    tls_enabled = wtypes.wsattr(bool, default=False)
    tls_ciphers = wtypes.wsattr(wtypes.StringType(max_length=2048))
    tls_versions = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType(
        max_length=32)))
    alpn_protocols = wtypes.wsattr(wtypes.ArrayType(types.AlpnProtocolType()))


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
    tags = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType(max_length=255)))
    tls_container_ref = wtypes.wsattr(wtypes.StringType(max_length=255))
    ca_tls_container_ref = wtypes.wsattr(wtypes.StringType(max_length=255))
    crl_container_ref = wtypes.wsattr(wtypes.StringType(max_length=255))
    tls_enabled = wtypes.wsattr(bool)
    tls_ciphers = wtypes.wsattr(wtypes.StringType(max_length=2048))
    tls_versions = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType(
        max_length=32)))
    alpn_protocols = wtypes.wsattr(wtypes.ArrayType(types.AlpnProtocolType()))


class PoolRootPut(types.BaseType):
    pool = wtypes.wsattr(PoolPUT)


class PoolSingleCreate(BasePoolType):
    """Defines mandatory and optional attributes of a POST request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    admin_state_up = wtypes.wsattr(bool, default=True)
    protocol = wtypes.wsattr(
        wtypes.Enum(str, *lib_constants.POOL_SUPPORTED_PROTOCOLS))
    lb_algorithm = wtypes.wsattr(
        wtypes.Enum(str, *constants.SUPPORTED_LB_ALGORITHMS))
    session_persistence = wtypes.wsattr(SessionPersistencePOST)
    healthmonitor = wtypes.wsattr(
        health_monitor_types.HealthMonitorSingleCreate)
    members = wtypes.wsattr([member_types.MemberSingleCreate])
    tags = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType(max_length=255)))
    tls_container_ref = wtypes.wsattr(wtypes.StringType(max_length=255))
    ca_tls_container_ref = wtypes.wsattr(wtypes.StringType(max_length=255))
    crl_container_ref = wtypes.wsattr(wtypes.StringType(max_length=255))
    tls_enabled = wtypes.wsattr(bool, default=False)
    tls_ciphers = wtypes.wsattr(wtypes.StringType(max_length=2048))
    tls_versions = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType(
        max_length=32)))
    alpn_protocols = wtypes.wsattr(wtypes.ArrayType(types.AlpnProtocolType()))


class PoolStatusResponse(BasePoolType):
    """Defines which attributes are to be shown on status response."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType())
    provisioning_status = wtypes.wsattr(wtypes.StringType())
    operating_status = wtypes.wsattr(wtypes.StringType())
    health_monitor = wtypes.wsattr(
        health_monitor_types.HealthMonitorStatusResponse)
    members = wtypes.wsattr([member_types.MemberStatusResponse])

    @classmethod
    def from_db_obj(cls, db_obj):
        result = super().from_db_obj(db_obj)

        if db_obj.health_monitor:
            result.health_monitor = (
                health_monitor_types.HealthMonitorStatusResponse
                .from_db_obj(db_obj.health_monitor)
            )

        result.members = [
            member_types.MemberStatusResponse.from_db_obj(member)
            for member in db_obj.members
        ]

        return result
