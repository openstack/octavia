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

from wsme import types as wtypes

from octavia.api.common import types as base
from octavia.api.v1.types import listener_statistics


class ListenerStatistics(listener_statistics.ListenerStatisticsResponse):
    id = wtypes.wsattr(wtypes.UuidType())

    @classmethod
    def from_data_model(cls, data_model, children=False):
        ls_stats = super(ListenerStatistics, cls).from_data_model(
            data_model, children=children)
        ls_stats.id = data_model.listener_id
        return ls_stats


class LoadBalancerStatisticsResponse(base.BaseType):
    bytes_in = wtypes.wsattr(wtypes.IntegerType())
    bytes_out = wtypes.wsattr(wtypes.IntegerType())
    active_connections = wtypes.wsattr(wtypes.IntegerType())
    total_connections = wtypes.wsattr(wtypes.IntegerType())
    request_errors = wtypes.wsattr(wtypes.IntegerType())
    listeners = wtypes.wsattr([ListenerStatistics])

    @classmethod
    def from_data_model(cls, data_model, children=False):
        lb_stats = super(LoadBalancerStatisticsResponse, cls).from_data_model(
            data_model, children=children)

        lb_stats.listeners = [
            ListenerStatistics.from_data_model(
                listener_dm, children=children)
            for listener_dm in data_model.listeners
        ]
        return lb_stats
