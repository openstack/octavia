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

from octavia.api.common import types as base
from octavia.api.v1.types import l7policy
from octavia.api.v1.types import pool
from octavia.common import constants


class TLSTermination(base.BaseType):
    certificate = wtypes.wsattr(wtypes.StringType())
    intermediate_certificate = wtypes.wsattr(wtypes.StringType())
    private_key = wtypes.wsattr(wtypes.StringType())
    passphrase = wtypes.wsattr(wtypes.StringType())


class ListenerResponse(base.BaseType):
    """Defines which attributes are to be shown on any response."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType())
    description = wtypes.wsattr(wtypes.StringType())
    provisioning_status = wtypes.wsattr(wtypes.StringType())
    operating_status = wtypes.wsattr(wtypes.StringType())
    enabled = wtypes.wsattr(bool)
    protocol = wtypes.wsattr(wtypes.text)
    protocol_port = wtypes.wsattr(wtypes.IntegerType())
    connection_limit = wtypes.wsattr(wtypes.IntegerType())
    tls_certificate_id = wtypes.wsattr(wtypes.StringType(max_length=255))
    sni_containers = [wtypes.StringType(max_length=255)]
    project_id = wtypes.wsattr(wtypes.StringType())
    default_pool_id = wtypes.wsattr(wtypes.UuidType())
    default_pool = wtypes.wsattr(pool.PoolResponse)
    l7policies = wtypes.wsattr([l7policy.L7PolicyResponse])
    insert_headers = wtypes.wsattr(wtypes.DictType(str, str))
    created_at = wtypes.wsattr(wtypes.datetime.datetime)
    updated_at = wtypes.wsattr(wtypes.datetime.datetime)

    @classmethod
    def from_data_model(cls, data_model, children=False):
        listener = super(ListenerResponse, cls).from_data_model(
            data_model, children=children)
        # NOTE(blogan): we should show sni_containers for every call to show
        # a listener
        listener.sni_containers = [sni_c.tls_container_id
                                   for sni_c in data_model.sni_containers]
        if not children:
            # NOTE(blogan): do not show default_pool if the request does not
            # want to see children
            del listener.default_pool
            del listener.l7policies
            return listener
        if data_model.default_pool:
            listener.default_pool = pool.PoolResponse.from_data_model(
                data_model.default_pool, children=children)
        if data_model.l7policies:
            listener.l7policies = [l7policy.L7PolicyResponse.from_data_model(
                policy, children=children) for policy in data_model.l7policies]
        if not listener.default_pool:
            del listener.default_pool
            del listener.default_pool_id
        if not listener.l7policies or len(listener.l7policies) <= 0:
            del listener.l7policies
        return listener


class ListenerPOST(base.BaseType):
    """Defines mandatory and optional attributes of a POST request."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    enabled = wtypes.wsattr(bool, default=True)
    protocol = wtypes.wsattr(wtypes.Enum(str, *constants.SUPPORTED_PROTOCOLS),
                             mandatory=True)
    protocol_port = wtypes.wsattr(wtypes.IntegerType(), mandatory=True)
    connection_limit = wtypes.wsattr(wtypes.IntegerType())
    tls_certificate_id = wtypes.wsattr(wtypes.StringType(max_length=255))
    tls_termination = wtypes.wsattr(TLSTermination)
    sni_containers = [wtypes.StringType(max_length=255)]
    # TODO(johnsom) Remove after deprecation (R series)
    project_id = wtypes.wsattr(wtypes.StringType(max_length=36))
    default_pool_id = wtypes.wsattr(wtypes.UuidType())
    default_pool = wtypes.wsattr(pool.PoolPOST)
    l7policies = wtypes.wsattr([l7policy.L7PolicyPOST], default=[])
    insert_headers = wtypes.wsattr(wtypes.DictType(str, str))


class ListenerPUT(base.BaseType):
    """Defines attributes that are acceptable of a PUT request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    enabled = wtypes.wsattr(bool)
    protocol = wtypes.wsattr(wtypes.Enum(str, *constants.SUPPORTED_PROTOCOLS))
    protocol_port = wtypes.wsattr(wtypes.IntegerType())
    connection_limit = wtypes.wsattr(wtypes.IntegerType())
    tls_certificate_id = wtypes.wsattr(wtypes.StringType(max_length=255))
    tls_termination = wtypes.wsattr(TLSTermination)
    sni_containers = [wtypes.StringType(max_length=255)]
    default_pool_id = wtypes.wsattr(wtypes.UuidType())
    insert_headers = wtypes.wsattr(wtypes.DictType(str, str))
