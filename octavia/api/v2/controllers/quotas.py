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

    def __init__(self):
        super(QuotasController, self).__init__()

    @wsme_pecan.wsexpose(quota_types.QuotaResponse, wtypes.text)
    def get(self, project_id):
        """Get a single project's quota details."""
        context = pecan.request.context.get('octavia_context')

        # Check that the user is authorized to show this quota
        action = '{rbac_obj}{action}'.format(
            rbac_obj=constants.RBAC_QUOTA, action='get_one')
        target = {'project_id': project_id}
        context.policy.authorize(action, target)

        db_quotas = self._get_db_quotas(context.session, project_id)
        return self._convert_db_to_type(db_quotas, quota_types.QuotaResponse)

    @wsme_pecan.wsexpose(quota_types.QuotaAllResponse,
                         ignore_extra_args=True)
    def get_all(self, project_id=None):
        """List all non-default quotas."""
        pcontext = pecan.request.context
        context = pcontext.get('octavia_context')

        # Check that the user is authorized to list quotas under all projects
        action = '{rbac_obj}{action}'.format(
            rbac_obj=constants.RBAC_QUOTA, action='get_all-global')
        target = {'project_id': project_id}
        if not context.policy.authorize(action, target, do_raise=False):
            # Not a global observer or admin
            if project_id is None:
                project_id = context.project_id

            # Check if user is authorized to list quota under this project
            action = '{rbac_obj}{action}'.format(
                rbac_obj=constants.RBAC_QUOTA, action='get_all')
            target = {'project_id': project_id}
            context.policy.authorize(action, target)

        if project_id is None:
            query_filter = {}
        else:
            query_filter = {'project_id': project_id}

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

        # Check that the user is authorized to update this quota
        action = '{rbac_obj}{action}'.format(
            rbac_obj=constants.RBAC_QUOTA, action='put')
        target = {'project_id': project_id}
        context.policy.authorize(action, target)

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

        # Check that the user is authorized to delete this quota
        action = '{rbac_obj}{action}'.format(
            rbac_obj=constants.RBAC_QUOTA, action='delete')
        target = {'project_id': project_id}
        context.policy.authorize(action, target)

        self.repositories.quotas.delete(context.session, project_id)
        db_quotas = self._get_db_quotas(context.session, project_id)
        return self._convert_db_to_type(db_quotas, quota_types.QuotaResponse)

    @pecan.expose()
    def _lookup(self, project_id, *remainder):
        """Overridden pecan _lookup method for routing default endpoint."""
        if project_id and len(remainder) and remainder[0] == 'default':
            return QuotasDefaultController(project_id), ''


class QuotasDefaultController(base.BaseController):

    def __init__(self, project_id):
        super(QuotasDefaultController, self).__init__()
        self.project_id = project_id

    @wsme_pecan.wsexpose(quota_types.QuotaResponse, wtypes.text)
    def get(self):
        """Get a project's default quota details."""
        context = pecan.request.context.get('octavia_context')

        if not self.project_id:
            raise exceptions.MissingAPIProjectID()

        # Check that the user is authorized to see quota defaults
        action = '{rbac_obj}{action}'.format(
            rbac_obj=constants.RBAC_QUOTA, action='get_defaults')
        target = {'project_id': self.project_id}
        context.policy.authorize(action, target)

        quotas = self._get_default_quotas(self.project_id)
        return self._convert_db_to_type(quotas, quota_types.QuotaResponse)
