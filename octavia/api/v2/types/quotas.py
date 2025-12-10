#    Copyright 2016 Rackspace
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
from octavia.common import constants as consts


class BaseQuotaType(types.BaseType):
    _type_to_db_map = {'loadbalancer': 'load_balancer',
                       'healthmonitor': 'health_monitor'}
    _child_map = {}


class QuotaResponse(BaseQuotaType):
    project_id = wtypes.wsattr(wtypes.StringType())
    loadbalancer = wtypes.wsattr(wtypes.IntegerType(
        minimum=consts.MIN_QUOTA, maximum=consts.MAX_QUOTA))
    # Misspelled version, deprecated in Rocky
    load_balancer = wtypes.wsattr(wtypes.IntegerType(
        minimum=consts.MIN_QUOTA, maximum=consts.MAX_QUOTA))
    listener = wtypes.wsattr(wtypes.IntegerType(
        minimum=consts.MIN_QUOTA, maximum=consts.MAX_QUOTA))
    member = wtypes.wsattr(wtypes.IntegerType(
        minimum=consts.MIN_QUOTA, maximum=consts.MAX_QUOTA))
    pool = wtypes.wsattr(wtypes.IntegerType(
        minimum=consts.MIN_QUOTA, maximum=consts.MAX_QUOTA))
    healthmonitor = wtypes.wsattr(wtypes.IntegerType(
        minimum=consts.MIN_QUOTA, maximum=consts.MAX_QUOTA))
    # Misspelled version, deprecated in Rocky
    health_monitor = wtypes.wsattr(wtypes.IntegerType(
        minimum=consts.MIN_QUOTA, maximum=consts.MAX_QUOTA))
    l7policy = wtypes.wsattr(wtypes.IntegerType(
        minimum=consts.MIN_QUOTA, maximum=consts.MAX_QUOTA))
    l7rule = wtypes.wsattr(wtypes.IntegerType(
        minimum=consts.MIN_QUOTA, maximum=consts.MAX_QUOTA))


class QuotaRootResponse(types.BaseType):
    quota = wtypes.wsattr(QuotaResponse)


class QuotasRootResponse(types.BaseType):
    quotas = wtypes.wsattr([QuotaResponse])
    quotas_links = wtypes.wsattr([types.PageType])


class QuotaPUT(BaseQuotaType):
    loadbalancer = wtypes.wsattr(wtypes.IntegerType(
        minimum=consts.MIN_QUOTA, maximum=consts.MAX_QUOTA))
    # Misspelled version, deprecated in Rocky
    load_balancer = wtypes.wsattr(wtypes.IntegerType(
        minimum=consts.MIN_QUOTA, maximum=consts.MAX_QUOTA))
    listener = wtypes.wsattr(wtypes.IntegerType(
        minimum=consts.MIN_QUOTA, maximum=consts.MAX_QUOTA))
    member = wtypes.wsattr(wtypes.IntegerType(
        minimum=consts.MIN_QUOTA, maximum=consts.MAX_QUOTA))
    pool = wtypes.wsattr(wtypes.IntegerType(
        minimum=consts.MIN_QUOTA, maximum=consts.MAX_QUOTA))
    healthmonitor = wtypes.wsattr(wtypes.IntegerType(
        minimum=consts.MIN_QUOTA, maximum=consts.MAX_QUOTA))
    # Misspelled version, deprecated in Rocky
    health_monitor = wtypes.wsattr(wtypes.IntegerType(
        minimum=consts.MIN_QUOTA, maximum=consts.MAX_QUOTA))
    l7policy = wtypes.wsattr(wtypes.IntegerType(
        minimum=consts.MIN_QUOTA, maximum=consts.MAX_QUOTA))
    l7rule = wtypes.wsattr(wtypes.IntegerType(
        minimum=consts.MIN_QUOTA, maximum=consts.MAX_QUOTA))


class QuotaRootPUT(types.BaseType):
    quota = wtypes.wsattr(QuotaPUT)
