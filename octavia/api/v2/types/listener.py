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
from octavia.api.v2.types import l7policy as l7policy_types
from octavia.api.v2.types import pool as pool_types
from octavia.common import constants


class BaseListenerType(types.BaseType):
    _type_to_db_map = {
        'admin_state_up': 'enabled',
        'default_tls_container_ref': 'tls_certificate_id',
        'sni_container_refs': 'sni_containers',
        'client_ca_tls_container_ref': 'client_ca_tls_certificate_id',
        'client_crl_container_ref': 'client_crl_container_id'}
    _child_map = {}


class ListenerResponse(BaseListenerType):
    """Defines which attributes are to be shown on any response."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType())
    description = wtypes.wsattr(wtypes.StringType())
    provisioning_status = wtypes.wsattr(wtypes.StringType())
    operating_status = wtypes.wsattr(wtypes.StringType())
    admin_state_up = wtypes.wsattr(bool)
    protocol = wtypes.wsattr(wtypes.text)
    protocol_port = wtypes.wsattr(wtypes.IntegerType())
    connection_limit = wtypes.wsattr(wtypes.IntegerType())
    default_tls_container_ref = wtypes.wsattr(wtypes.StringType())
    sni_container_refs = [wtypes.StringType()]
    project_id = wtypes.wsattr(wtypes.StringType())
    default_pool_id = wtypes.wsattr(wtypes.UuidType())
    l7policies = wtypes.wsattr([types.IdOnlyType])
    insert_headers = wtypes.wsattr(wtypes.DictType(str, str))
    created_at = wtypes.wsattr(wtypes.datetime.datetime)
    updated_at = wtypes.wsattr(wtypes.datetime.datetime)
    loadbalancers = wtypes.wsattr([types.IdOnlyType])
    timeout_client_data = wtypes.wsattr(wtypes.IntegerType())
    timeout_member_connect = wtypes.wsattr(wtypes.IntegerType())
    timeout_member_data = wtypes.wsattr(wtypes.IntegerType())
    timeout_tcp_inspect = wtypes.wsattr(wtypes.IntegerType())
    tags = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType()))
    client_ca_tls_container_ref = wtypes.StringType()
    client_authentication = wtypes.wsattr(wtypes.StringType())
    client_crl_container_ref = wtypes.wsattr(wtypes.StringType())
    allowed_cidrs = wtypes.wsattr([types.CidrType()])
    tls_ciphers = wtypes.StringType()
    tls_versions = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType()))
    alpn_protocols = wtypes.wsattr(wtypes.ArrayType(types.AlpnProtocolType()))
    hsts_max_age = wtypes.wsattr(wtypes.IntegerType())
    hsts_include_subdomains = wtypes.wsattr(bool)
    hsts_preload = wtypes.wsattr(bool)

    @classmethod
    def from_db_obj(cls, db_obj):
        result = super().from_db_obj(db_obj)

        result.sni_container_refs = [
            sni_container.tls_container_id
            for sni_container in db_obj.sni_containers
        ]
        result.allowed_cidrs = [
            allowed_cidr.cidr
            for allowed_cidr in db_obj.allowed_cidrs
        ] or None

        result.insert_headers = db_obj.insert_headers or {}

        if cls._full_response():
            result.l7policies = [
                l7policy_types.L7PolicyFullResponse.from_db_obj(l7policy)
                for l7policy in db_obj.l7policies
            ]
        else:
            result.l7policies = [
                types.IdOnlyType.from_db_obj(l7policy)
                for l7policy in db_obj.l7policies
            ]
            result.loadbalancers = [
                types.IdOnlyType.from_db_obj(db_obj.load_balancer)
            ]

        return result


class ListenerFullResponse(ListenerResponse):
    @classmethod
    def _full_response(cls):
        return True

    l7policies = wtypes.wsattr([l7policy_types.L7PolicyFullResponse])


class ListenerRootResponse(types.BaseType):
    listener = wtypes.wsattr(ListenerResponse)


class ListenersRootResponse(types.BaseType):
    listeners = wtypes.wsattr([ListenerResponse])
    listeners_links = wtypes.wsattr([types.PageType])


class ListenerPOST(BaseListenerType):
    """Defines mandatory and optional attributes of a POST request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    admin_state_up = wtypes.wsattr(bool, default=True)
    protocol = wtypes.wsattr(wtypes.Enum(str,
                             *lib_constants.LISTENER_SUPPORTED_PROTOCOLS),
                             mandatory=True)
    protocol_port = wtypes.wsattr(
        wtypes.IntegerType(minimum=constants.MIN_PORT_NUMBER,
                           maximum=constants.MAX_PORT_NUMBER), mandatory=True)
    connection_limit = wtypes.wsattr(
        wtypes.IntegerType(minimum=constants.MIN_CONNECTION_LIMIT),
        default=constants.DEFAULT_CONNECTION_LIMIT)
    default_tls_container_ref = wtypes.wsattr(
        wtypes.StringType(max_length=255))
    sni_container_refs = [wtypes.StringType(max_length=255)]
    # TODO(johnsom) Remove after deprecation (R series)
    project_id = wtypes.wsattr(wtypes.StringType(max_length=36))
    default_pool_id = wtypes.wsattr(wtypes.UuidType())
    default_pool = wtypes.wsattr(pool_types.PoolSingleCreate)
    l7policies = wtypes.wsattr(
        [l7policy_types.L7PolicySingleCreate], default=[])
    insert_headers = wtypes.wsattr(
        wtypes.DictType(str, wtypes.StringType(max_length=255)))
    loadbalancer_id = wtypes.wsattr(wtypes.UuidType(), mandatory=True)
    timeout_client_data = wtypes.wsattr(
        wtypes.IntegerType(minimum=constants.MIN_TIMEOUT,
                           maximum=constants.MAX_TIMEOUT))
    timeout_member_connect = wtypes.wsattr(
        wtypes.IntegerType(minimum=constants.MIN_TIMEOUT,
                           maximum=constants.MAX_TIMEOUT))
    timeout_member_data = wtypes.wsattr(
        wtypes.IntegerType(minimum=constants.MIN_TIMEOUT,
                           maximum=constants.MAX_TIMEOUT))
    timeout_tcp_inspect = wtypes.wsattr(
        wtypes.IntegerType(minimum=constants.MIN_TIMEOUT,
                           maximum=constants.MAX_TIMEOUT))
    tags = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType(max_length=255)))
    client_ca_tls_container_ref = wtypes.StringType(max_length=255)
    client_authentication = wtypes.wsattr(
        wtypes.Enum(str, *constants.SUPPORTED_CLIENT_AUTH_MODES),
        default=constants.CLIENT_AUTH_NONE)
    client_crl_container_ref = wtypes.StringType(max_length=255)
    allowed_cidrs = wtypes.wsattr([types.CidrType()])
    tls_ciphers = wtypes.StringType(max_length=2048)
    tls_versions = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType(
        max_length=32)))
    alpn_protocols = wtypes.wsattr(wtypes.ArrayType(types.AlpnProtocolType()))
    hsts_max_age = wtypes.wsattr(wtypes.IntegerType(minimum=0))
    hsts_include_subdomains = wtypes.wsattr(bool, default=False)
    hsts_preload = wtypes.wsattr(bool, default=False)


class ListenerRootPOST(types.BaseType):
    listener = wtypes.wsattr(ListenerPOST)


class ListenerPUT(BaseListenerType):
    """Defines attributes that are acceptable of a PUT request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    admin_state_up = wtypes.wsattr(bool)
    connection_limit = wtypes.wsattr(
        wtypes.IntegerType(minimum=constants.MIN_CONNECTION_LIMIT))
    default_tls_container_ref = wtypes.wsattr(
        wtypes.StringType(max_length=255))
    sni_container_refs = [wtypes.StringType(max_length=255)]
    default_pool_id = wtypes.wsattr(wtypes.UuidType())
    insert_headers = wtypes.wsattr(
        wtypes.DictType(str, wtypes.StringType(max_length=255)))
    timeout_client_data = wtypes.wsattr(
        wtypes.IntegerType(minimum=constants.MIN_TIMEOUT,
                           maximum=constants.MAX_TIMEOUT))
    timeout_member_connect = wtypes.wsattr(
        wtypes.IntegerType(minimum=constants.MIN_TIMEOUT,
                           maximum=constants.MAX_TIMEOUT))
    timeout_member_data = wtypes.wsattr(
        wtypes.IntegerType(minimum=constants.MIN_TIMEOUT,
                           maximum=constants.MAX_TIMEOUT))
    timeout_tcp_inspect = wtypes.wsattr(
        wtypes.IntegerType(minimum=constants.MIN_TIMEOUT,
                           maximum=constants.MAX_TIMEOUT))
    tags = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType(max_length=255)))
    client_ca_tls_container_ref = wtypes.StringType(max_length=255)
    client_authentication = wtypes.wsattr(
        wtypes.Enum(str, *constants.SUPPORTED_CLIENT_AUTH_MODES))
    client_crl_container_ref = wtypes.StringType(max_length=255)
    allowed_cidrs = wtypes.wsattr([types.CidrType()])
    tls_ciphers = wtypes.StringType(max_length=2048)
    tls_versions = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType(
        max_length=32)))
    alpn_protocols = wtypes.wsattr(wtypes.ArrayType(types.AlpnProtocolType()))
    hsts_max_age = wtypes.wsattr(wtypes.IntegerType(minimum=0))
    hsts_include_subdomains = wtypes.wsattr(bool)
    hsts_preload = wtypes.wsattr(bool)


class ListenerRootPUT(types.BaseType):
    listener = wtypes.wsattr(ListenerPUT)


class ListenerSingleCreate(BaseListenerType):
    """Defines mandatory and optional attributes of a POST request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    admin_state_up = wtypes.wsattr(bool, default=True)
    protocol = wtypes.wsattr(wtypes.Enum(str,
                             *lib_constants.LISTENER_SUPPORTED_PROTOCOLS),
                             mandatory=True)
    protocol_port = wtypes.wsattr(
        wtypes.IntegerType(minimum=constants.MIN_PORT_NUMBER,
                           maximum=constants.MAX_PORT_NUMBER), mandatory=True)
    connection_limit = wtypes.wsattr(
        wtypes.IntegerType(minimum=constants.MIN_CONNECTION_LIMIT),
        default=constants.DEFAULT_CONNECTION_LIMIT)
    default_tls_container_ref = wtypes.wsattr(
        wtypes.StringType(max_length=255))
    sni_container_refs = [wtypes.StringType(max_length=255)]
    default_pool_id = wtypes.wsattr(wtypes.UuidType())
    default_pool = wtypes.wsattr(pool_types.PoolSingleCreate)
    l7policies = wtypes.wsattr(
        [l7policy_types.L7PolicySingleCreate], default=[])
    insert_headers = wtypes.wsattr(
        wtypes.DictType(str, wtypes.StringType(max_length=255)))
    timeout_client_data = wtypes.wsattr(
        wtypes.IntegerType(minimum=constants.MIN_TIMEOUT,
                           maximum=constants.MAX_TIMEOUT))
    timeout_member_connect = wtypes.wsattr(
        wtypes.IntegerType(minimum=constants.MIN_TIMEOUT,
                           maximum=constants.MAX_TIMEOUT))
    timeout_member_data = wtypes.wsattr(
        wtypes.IntegerType(minimum=constants.MIN_TIMEOUT,
                           maximum=constants.MAX_TIMEOUT))
    timeout_tcp_inspect = wtypes.wsattr(
        wtypes.IntegerType(minimum=constants.MIN_TIMEOUT,
                           maximum=constants.MAX_TIMEOUT))
    tags = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType(max_length=255)))
    client_ca_tls_container_ref = wtypes.StringType(max_length=255)
    client_authentication = wtypes.wsattr(
        wtypes.Enum(str, *constants.SUPPORTED_CLIENT_AUTH_MODES),
        default=constants.CLIENT_AUTH_NONE)
    client_crl_container_ref = wtypes.StringType(max_length=255)
    allowed_cidrs = wtypes.wsattr([types.CidrType()])
    tls_ciphers = wtypes.StringType(max_length=2048)
    tls_versions = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType(
        max_length=32)))
    alpn_protocols = wtypes.wsattr(wtypes.ArrayType(types.AlpnProtocolType()))
    hsts_max_age = wtypes.wsattr(wtypes.IntegerType())
    hsts_include_subdomains = wtypes.wsattr(bool, default=False)
    hsts_preload = wtypes.wsattr(bool, default=False)


class ListenerStatusResponse(BaseListenerType):
    """Defines which attributes are to be shown on status response."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType())
    operating_status = wtypes.wsattr(wtypes.StringType())
    provisioning_status = wtypes.wsattr(wtypes.StringType())
    pools = wtypes.wsattr([pool_types.PoolStatusResponse])

    @classmethod
    def from_db_obj(cls, db_obj):
        result = super().from_db_obj(db_obj)

        result.pools = [
            pool_types.PoolStatusResponse.from_db_obj(pool)
            for pool in db_obj.pools
        ]

        if not result.name:
            result.name = ""

        return result


class ListenerStatisticsResponse(BaseListenerType):
    """Defines which attributes are to show on stats response."""
    bytes_in = wtypes.wsattr(wtypes.IntegerType())
    bytes_out = wtypes.wsattr(wtypes.IntegerType())
    active_connections = wtypes.wsattr(wtypes.IntegerType())
    total_connections = wtypes.wsattr(wtypes.IntegerType())
    request_errors = wtypes.wsattr(wtypes.IntegerType())


class StatisticsRootResponse(types.BaseType):
    stats = wtypes.wsattr(ListenerStatisticsResponse)
