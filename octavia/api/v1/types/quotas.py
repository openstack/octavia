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


class QuotaBase(base.BaseType):
    """Individual quota definitions."""
    load_balancer = wtypes.wsattr(wtypes.IntegerType())
    listener = wtypes.wsattr(wtypes.IntegerType())
    member = wtypes.wsattr(wtypes.IntegerType())
    pool = wtypes.wsattr(wtypes.IntegerType())
    health_monitor = wtypes.wsattr(wtypes.IntegerType())


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
    tenant_id = wtypes.wsattr(wtypes.StringType())
    load_balancer = wtypes.wsattr(wtypes.IntegerType())
    listener = wtypes.wsattr(wtypes.IntegerType())
    member = wtypes.wsattr(wtypes.IntegerType())
    pool = wtypes.wsattr(wtypes.IntegerType())
    health_monitor = wtypes.wsattr(wtypes.IntegerType())

    @classmethod
    def from_data_model(cls, data_model, children=False):
        quotas = super(QuotaAllBase, cls).from_data_model(
            data_model, children=children)
        quotas.tenant_id = quotas.project_id
        return quotas


class QuotaAllResponse(base.BaseType):
    quotas = wtypes.wsattr([QuotaAllBase])

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
