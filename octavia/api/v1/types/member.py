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
from octavia.common import constants


class MemberResponse(base.BaseType):
    """Defines which attributes are to be shown on any response."""
    id = wtypes.wsattr(wtypes.UuidType())
    operating_status = wtypes.wsattr(wtypes.StringType())
    enabled = wtypes.wsattr(bool)
    ip_address = wtypes.wsattr(base.IPAddressType())
    protocol_port = wtypes.wsattr(wtypes.IntegerType())
    weight = wtypes.wsattr(wtypes.IntegerType())
    subnet_id = wtypes.wsattr(wtypes.UuidType())
    project_id = wtypes.wsattr(wtypes.StringType())
    created_at = wtypes.wsattr(wtypes.datetime.datetime)
    updated_at = wtypes.wsattr(wtypes.datetime.datetime)
    monitor_address = wtypes.wsattr(base.IPAddressType())
    monitor_port = wtypes.wsattr(wtypes.IntegerType())


class MemberPOST(base.BaseType):
    """Defines mandatory and optional attributes of a POST request."""
    id = wtypes.wsattr(wtypes.UuidType())
    enabled = wtypes.wsattr(bool, default=True)
    ip_address = wtypes.wsattr(base.IPAddressType(), mandatory=True)
    protocol_port = wtypes.wsattr(wtypes.IntegerType(), mandatory=True)
    weight = wtypes.wsattr(wtypes.IntegerType(), default=1)
    subnet_id = wtypes.wsattr(wtypes.UuidType())
    # TODO(johnsom) Remove after deprecation (R series)
    project_id = wtypes.wsattr(wtypes.StringType(max_length=36))
    monitor_port = wtypes.wsattr(wtypes.IntegerType(
        minimum=constants.MIN_PORT_NUMBER, maximum=constants.MAX_PORT_NUMBER),
        default=None)
    monitor_address = wtypes.wsattr(base.IPAddressType(), default=None)


class MemberPUT(base.BaseType):
    """Defines attributes that are acceptable of a PUT request."""
    protocol_port = wtypes.wsattr(wtypes.IntegerType())
    enabled = wtypes.wsattr(bool)
    weight = wtypes.wsattr(wtypes.IntegerType())
    monitor_address = wtypes.wsattr(base.IPAddressType())
    monitor_port = wtypes.wsattr(wtypes.IntegerType(
        minimum=constants.MIN_PORT_NUMBER, maximum=constants.MAX_PORT_NUMBER))
