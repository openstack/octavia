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

from octavia.api.common import types as base
from octavia.common import constants as consts


class QuotaBase(base.BaseType):
    """Individual quota definitions."""
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

    def to_dict(self, render_unsets=False):
        quota_dict = super(QuotaBase, self).to_dict(render_unsets)
        if 'loadbalancer' in quota_dict:
            quota_dict['load_balancer'] = quota_dict.pop('loadbalancer')
        if 'healthmonitor' in quota_dict:
            quota_dict['health_monitor'] = quota_dict.pop('healthmonitor')
        return quota_dict


class QuotaResponse(base.BaseType):
    """Wrapper object for quotas responses."""
    quota = wtypes.wsattr(QuotaBase)

    @classmethod
    def from_data_model(cls, data_model, children=False):
        quotas = super(QuotaResponse, cls).from_data_model(
            data_model, children=children)
        quotas.quota = QuotaBase.from_data_model(data_model)
        return quotas


class QuotaAllBase(base.BaseType):
    """Wrapper object for get all quotas responses."""
    project_id = wtypes.wsattr(wtypes.StringType())
    loadbalancer = wtypes.wsattr(wtypes.IntegerType())
    # Misspelled version, deprecated in Rocky, remove in T
    load_balancer = wtypes.wsattr(wtypes.IntegerType())
    listener = wtypes.wsattr(wtypes.IntegerType())
    member = wtypes.wsattr(wtypes.IntegerType())
    pool = wtypes.wsattr(wtypes.IntegerType())
    healthmonitor = wtypes.wsattr(wtypes.IntegerType())
    # Misspelled version, deprecated in Rocky, remove in T
    health_monitor = wtypes.wsattr(wtypes.IntegerType())

    _type_to_model_map = {'loadbalancer': 'load_balancer',
                          'healthmonitor': 'health_monitor'}
    _child_map = {}

    @classmethod
    def from_data_model(cls, data_model, children=False):
        quotas = super(QuotaAllBase, cls).from_data_model(
            data_model, children=children)
        # For backwards compatibility, remove in T
        quotas.load_balancer = quotas.loadbalancer
        # For backwards compatibility, remove in T
        quotas.health_monitor = quotas.healthmonitor
        return quotas


class QuotaAllResponse(base.BaseType):
    quotas = wtypes.wsattr([QuotaAllBase])
    quotas_links = wtypes.wsattr([base.PageType])

    @classmethod
    def from_data_model(cls, data_model, children=False):
        quotalist = QuotaAllResponse()
        quotalist.quotas = [
            QuotaAllBase.from_data_model(obj)
            for obj in data_model]
        return quotalist


class QuotaPUT(base.BaseType):
    """Overall object for quota PUT request."""
    quota = wtypes.wsattr(QuotaBase)
