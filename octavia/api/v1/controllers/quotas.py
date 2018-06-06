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

from octavia.api.v1.controllers import base
from octavia.api.v1.types import quotas as quota_types
from octavia.common import constants
from octavia.common import exceptions

CONF = cfg.CONF
CONF.import_group('quotas', 'octavia.common.config')


class QuotasController(base.BaseController):

    def __init__(self):
        super(QuotasController, self).__init__()

    @wsme_pecan.wsexpose(quota_types.QuotaResponse, wtypes.text)
    def get(self, project_id):
        """Get a single project's quota details."""
        context = pecan.request.context.get('octavia_context')
        db_quotas = self._get_db_quotas(context.session, project_id)
        return self._convert_db_to_type(db_quotas, quota_types.QuotaResponse)

    @wsme_pecan.wsexpose(quota_types.QuotaAllResponse)
    def get_all(self):
        """List all non-default quotas."""
        context = pecan.request.context.get('octavia_context')
        db_quotas, _ = self.repositories.quotas.get_all(context.session)
        quotas = quota_types.QuotaAllResponse.from_data_model(db_quotas)
        return quotas

    @wsme_pecan.wsexpose(quota_types.QuotaResponse, wtypes.text,
                         body=quota_types.QuotaPUT, status_code=202)
    def put(self, project_id, quotas):
        """Update any or all quotas for a project."""
        context = pecan.request.context.get('octavia_context')

        new_project_id = context.project_id
        if context.is_admin or (CONF.api_settings.auth_strategy ==
                                constants.NOAUTH):
            if project_id:
                new_project_id = project_id

        if not new_project_id:
            raise exceptions.MissingAPIProjectID()

        project_id = new_project_id

        quotas_dict = quotas.to_dict()
        self.repositories.quotas.update(context.session, project_id,
                                        **quotas_dict)
        db_quotas = self._get_db_quotas(context.session, project_id)
        return self._convert_db_to_type(db_quotas, quota_types.QuotaResponse)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=202)
    def delete(self, project_id):
        """Reset a project's quotas to the default values."""
        context = pecan.request.context.get('octavia_context')
        project_id = context.project_id or project_id
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

    def __init__(self, project_id):
        super(QuotasDefaultController, self).__init__()
        self.project_id = project_id

    @wsme_pecan.wsexpose(quota_types.QuotaResponse, wtypes.text)
    def get(self):
        """Get a project's default quota details."""
        context = pecan.request.context.get('octavia_context')
        project_id = context.project_id
        quotas = self._get_default_quotas(project_id)
        return self._convert_db_to_type(quotas, quota_types.QuotaResponse)
