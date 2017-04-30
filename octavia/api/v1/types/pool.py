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
from octavia.api.v1.types import health_monitor
from octavia.api.v1.types import member
from octavia.common import constants


class SessionPersistenceResponse(base.BaseType):
    """Defines which attributes are to be shown on any response."""
    type = wtypes.wsattr(wtypes.text)
    cookie_name = wtypes.wsattr(wtypes.text)


class SessionPersistencePOST(base.BaseType):
    """Defines mandatory and optional attributes of a POST request."""
    type = wtypes.wsattr(wtypes.Enum(str, *constants.SUPPORTED_SP_TYPES),
                         mandatory=True)
    cookie_name = wtypes.wsattr(wtypes.text)


class SessionPersistencePUT(base.BaseType):
    """Defines attributes that are acceptable of a PUT request."""
    type = wtypes.wsattr(wtypes.Enum(str, *constants.SUPPORTED_SP_TYPES))
    cookie_name = wtypes.wsattr(wtypes.text, default=None)


class PoolResponse(base.BaseType):
    """Defines which attributes are to be shown on any response."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType())
    description = wtypes.wsattr(wtypes.StringType())
    operating_status = wtypes.wsattr(wtypes.StringType())
    enabled = wtypes.wsattr(bool)
    protocol = wtypes.wsattr(wtypes.text)
    lb_algorithm = wtypes.wsattr(wtypes.text)
    session_persistence = wtypes.wsattr(SessionPersistenceResponse)
    project_id = wtypes.wsattr(wtypes.StringType())
    health_monitor = wtypes.wsattr(health_monitor.HealthMonitorResponse)
    members = wtypes.wsattr([member.MemberResponse])
    created_at = wtypes.wsattr(wtypes.datetime.datetime)
    updated_at = wtypes.wsattr(wtypes.datetime.datetime)

    @classmethod
    def from_data_model(cls, data_model, children=False):
        pool = super(PoolResponse, cls).from_data_model(
            data_model, children=children)
        # NOTE(blogan): we should show session persistence on every request
        # to show a pool
        if data_model.session_persistence:
            pool.session_persistence = (
                SessionPersistenceResponse.from_data_model(
                    data_model.session_persistence))
        if not children:
            # NOTE(blogan): do not show members or health_monitor if the
            # request does not want to see children
            del pool.members
            del pool.health_monitor
            return pool
        pool.members = [
            member.MemberResponse.from_data_model(member_dm, children=children)
            for member_dm in data_model.members
        ]
        if data_model.health_monitor:
            pool.health_monitor = (
                health_monitor.HealthMonitorResponse.from_data_model(
                    data_model.health_monitor, children=children))
        if not pool.health_monitor:
            del pool.health_monitor
        return pool


class PoolPOST(base.BaseType):
    """Defines mandatory and optional attributes of a POST request."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    enabled = wtypes.wsattr(bool, default=True)
    listener_id = wtypes.wsattr(wtypes.UuidType())
    protocol = wtypes.wsattr(wtypes.Enum(str, *constants.SUPPORTED_PROTOCOLS),
                             mandatory=True)
    lb_algorithm = wtypes.wsattr(
        wtypes.Enum(str, *constants.SUPPORTED_LB_ALGORITHMS),
        mandatory=True)
    session_persistence = wtypes.wsattr(SessionPersistencePOST)
    # TODO(johnsom) Remove after deprecation (R series)
    project_id = wtypes.wsattr(wtypes.StringType(max_length=36))
    health_monitor = wtypes.wsattr(health_monitor.HealthMonitorPOST)
    members = wtypes.wsattr([member.MemberPOST])


class PoolPUT(base.BaseType):
    """Defines attributes that are acceptable of a PUT request."""
    name = wtypes.wsattr(wtypes.StringType())
    description = wtypes.wsattr(wtypes.StringType())
    enabled = wtypes.wsattr(bool)
    protocol = wtypes.wsattr(wtypes.Enum(str, *constants.SUPPORTED_PROTOCOLS))
    lb_algorithm = wtypes.wsattr(
        wtypes.Enum(str, *constants.SUPPORTED_LB_ALGORITHMS))
    session_persistence = wtypes.wsattr(SessionPersistencePUT)
