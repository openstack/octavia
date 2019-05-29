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
from octavia.common import constants


class BaseMemberType(types.BaseType):
    _type_to_model_map = {'admin_state_up': 'enabled',
                          'address': 'ip_address'}
    _child_map = {}


class MemberResponse(BaseMemberType):
    """Defines which attributes are to be shown on any response."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType())
    operating_status = wtypes.wsattr(wtypes.StringType())
    provisioning_status = wtypes.wsattr(wtypes.StringType())
    admin_state_up = wtypes.wsattr(bool)
    address = wtypes.wsattr(types.IPAddressType())
    protocol_port = wtypes.wsattr(wtypes.IntegerType())
    weight = wtypes.wsattr(wtypes.IntegerType())
    backup = wtypes.wsattr(bool)
    subnet_id = wtypes.wsattr(wtypes.UuidType())
    project_id = wtypes.wsattr(wtypes.StringType())
    created_at = wtypes.wsattr(wtypes.datetime.datetime)
    updated_at = wtypes.wsattr(wtypes.datetime.datetime)
    monitor_address = wtypes.wsattr(types.IPAddressType())
    monitor_port = wtypes.wsattr(wtypes.IntegerType())
    tags = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType()))

    @classmethod
    def from_data_model(cls, data_model, children=False):
        member = super(MemberResponse, cls).from_data_model(
            data_model, children=children)
        return member


class MemberFullResponse(MemberResponse):
    @classmethod
    def _full_response(cls):
        return True


class MemberRootResponse(types.BaseType):
    member = wtypes.wsattr(MemberResponse)


class MembersRootResponse(types.BaseType):
    members = wtypes.wsattr([MemberResponse])
    members_links = wtypes.wsattr([types.PageType])


class MemberPOST(BaseMemberType):
    """Defines mandatory and optional attributes of a POST request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    admin_state_up = wtypes.wsattr(bool, default=True)
    address = wtypes.wsattr(types.IPAddressType(), mandatory=True)
    protocol_port = wtypes.wsattr(wtypes.IntegerType(
        minimum=constants.MIN_PORT_NUMBER, maximum=constants.MAX_PORT_NUMBER),
        mandatory=True)
    weight = wtypes.wsattr(wtypes.IntegerType(
        minimum=constants.MIN_WEIGHT, maximum=constants.MAX_WEIGHT),
        default=constants.DEFAULT_WEIGHT)
    backup = wtypes.wsattr(bool, default=False)
    subnet_id = wtypes.wsattr(wtypes.UuidType())
    # TODO(johnsom) Remove after deprecation (R series)
    project_id = wtypes.wsattr(wtypes.StringType(max_length=36))
    monitor_port = wtypes.wsattr(wtypes.IntegerType(
        minimum=constants.MIN_PORT_NUMBER, maximum=constants.MAX_PORT_NUMBER),
        default=None)
    monitor_address = wtypes.wsattr(types.IPAddressType(), default=None)
    tags = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType(max_length=255)))


class MemberRootPOST(types.BaseType):
    member = wtypes.wsattr(MemberPOST)


class MemberPUT(BaseMemberType):
    """Defines attributes that are acceptable of a PUT request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    admin_state_up = wtypes.wsattr(bool)
    weight = wtypes.wsattr(wtypes.IntegerType(
        minimum=constants.MIN_WEIGHT, maximum=constants.MAX_WEIGHT))
    backup = wtypes.wsattr(bool)
    monitor_port = wtypes.wsattr(wtypes.IntegerType(
        minimum=constants.MIN_PORT_NUMBER, maximum=constants.MAX_PORT_NUMBER))
    monitor_address = wtypes.wsattr(types.IPAddressType())
    tags = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType(max_length=255)))


class MemberRootPUT(types.BaseType):
    member = wtypes.wsattr(MemberPUT)


class MembersRootPUT(types.BaseType):
    members = wtypes.wsattr([MemberPOST])


class MemberSingleCreate(BaseMemberType):
    """Defines mandatory and optional attributes of a POST request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    admin_state_up = wtypes.wsattr(bool, default=True)
    address = wtypes.wsattr(types.IPAddressType(), mandatory=True)
    protocol_port = wtypes.wsattr(wtypes.IntegerType(
        minimum=constants.MIN_PORT_NUMBER, maximum=constants.MAX_PORT_NUMBER),
        mandatory=True)
    weight = wtypes.wsattr(wtypes.IntegerType(
        minimum=constants.MIN_WEIGHT, maximum=constants.MAX_WEIGHT),
        default=constants.DEFAULT_WEIGHT)
    backup = wtypes.wsattr(bool, default=False)
    subnet_id = wtypes.wsattr(wtypes.UuidType())
    monitor_port = wtypes.wsattr(wtypes.IntegerType(
        minimum=constants.MIN_PORT_NUMBER, maximum=constants.MAX_PORT_NUMBER))
    monitor_address = wtypes.wsattr(types.IPAddressType())
    tags = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType(max_length=255)))


class MemberStatusResponse(BaseMemberType):
    """Defines which attributes are to be shown on status response."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType())
    operating_status = wtypes.wsattr(wtypes.StringType())
    provisioning_status = wtypes.wsattr(wtypes.StringType())
    address = wtypes.wsattr(types.IPAddressType())
    protocol_port = wtypes.wsattr(wtypes.IntegerType())

    @classmethod
    def from_data_model(cls, data_model, children=False):
        member = super(MemberStatusResponse, cls).from_data_model(
            data_model, children=children)

        if not member.name:
            member.name = ""

        return member
