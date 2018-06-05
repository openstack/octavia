#    Copyright 2018 Rackspace, US Inc.
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

from oslo_config import cfg
import pecan
import six
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v2.controllers import base
from octavia.api.v2.types import provider as provider_types
from octavia.common import constants

CONF = cfg.CONF


class ProviderController(base.BaseController):
    RBAC_TYPE = constants.RBAC_PROVIDER

    def __init__(self):
        super(ProviderController, self).__init__()

    @wsme_pecan.wsexpose(provider_types.ProvidersRootResponse, [wtypes.text],
                         ignore_extra_args=True)
    def get_all(self, fields=None):
        """List enabled provider drivers and their descriptions."""
        pcontext = pecan.request.context
        context = pcontext.get('octavia_context')

        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_GET_ALL)

        enabled_providers = CONF.api_settings.enabled_provider_drivers
        response_list = [
            provider_types.ProviderResponse(name=key, description=value) for
            key, value in six.iteritems(enabled_providers)]
        if fields is not None:
            response_list = self._filter_fields(response_list, fields)
        return provider_types.ProvidersRootResponse(providers=response_list)
