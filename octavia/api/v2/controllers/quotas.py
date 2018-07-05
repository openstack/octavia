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

from oslo_config import cfg
import pecan
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v2.controllers import base
from octavia.api.v2.types import quotas as quota_types
from octavia.common import constants
from octavia.common import exceptions

CONF = cfg.CONF
CONF.import_group('quotas', 'octavia.common.config')


class QuotasController(base.BaseController):
    RBAC_TYPE = constants.RBAC_QUOTA

    def __init__(self):
        super(QuotasController, self).__init__()

    @wsme_pecan.wsexpose(quota_types.QuotaResponse, wtypes.text)
    def get(self, project_id):
        """Get a single project's quota details."""
        context = pecan.request.context.get('octavia_context')

        self._auth_validate_action(context, project_id, constants.RBAC_GET_ONE)

        db_quotas = self._get_db_quotas(context.session, project_id)
        return self._convert_db_to_type(db_quotas, quota_types.QuotaResponse)

    @wsme_pecan.wsexpose(quota_types.QuotaAllResponse,
                         ignore_extra_args=True)
    def get_all(self, project_id=None):
        """List all non-default quotas."""
        pcontext = pecan.request.context
        context = pcontext.get('octavia_context')

        query_filter = self._auth_get_all(context, project_id)

        db_quotas, links = self.repositories.quotas.get_all(
            context.session,
            pagination_helper=pcontext.get(constants.PAGINATION_HELPER),
            **query_filter)
        quotas = quota_types.QuotaAllResponse.from_data_model(db_quotas)
        quotas.quotas_links = links
        return quotas

    @wsme_pecan.wsexpose(quota_types.QuotaResponse, wtypes.text,
                         body=quota_types.QuotaPUT, status_code=202)
    def put(self, project_id, quotas):
        """Update any or all quotas for a project."""
        context = pecan.request.context.get('octavia_context')

        if not project_id:
            raise exceptions.MissingAPIProjectID()

        self._auth_validate_action(context, project_id, constants.RBAC_PUT)

        quotas_dict = quotas.to_dict()
        self.repositories.quotas.update(context.session, project_id,
                                        **quotas_dict)
        db_quotas = self._get_db_quotas(context.session, project_id)
        return self._convert_db_to_type(db_quotas, quota_types.QuotaResponse)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=202)
    def delete(self, project_id):
        """Reset a project's quotas to the default values."""
        context = pecan.request.context.get('octavia_context')

        if not project_id:
            raise exceptions.MissingAPIProjectID()

        self._auth_validate_action(context, project_id, constants.RBAC_DELETE)

        self.repositories.quotas.delete(context.session, project_id)
        db_quotas = self._get_db_quotas(context.session, project_id)
        return self._convert_db_to_type(db_quotas, quota_types.QuotaResponse)

    @pecan.expose()
    def _lookup(self, project_id, *remainder):
        """Overridden pecan _lookup method for routing default endpoint."""
        if project_id and remainder and remainder[0] == 'default':
            return QuotasDefaultController(project_id), ''
        return None


class QuotasDefaultController(base.BaseController):
    RBAC_TYPE = constants.RBAC_QUOTA

    def __init__(self, project_id):
        super(QuotasDefaultController, self).__init__()
        self.project_id = project_id

    @wsme_pecan.wsexpose(quota_types.QuotaResponse, wtypes.text)
    def get(self):
        """Get a project's default quota details."""
        context = pecan.request.context.get('octavia_context')

        if not self.project_id:
            raise exceptions.MissingAPIProjectID()

        self._auth_validate_action(context, self.project_id,
                                   constants.RBAC_GET_DEFAULTS)

        quotas = self._get_default_quotas(self.project_id)
        return self._convert_db_to_type(quotas, quota_types.QuotaResponse)
