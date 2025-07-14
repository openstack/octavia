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

import pecan
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v2.controllers import base
from octavia.api.v2.types import quotas as quota_types
from octavia.common import constants


class QuotaUsageController(base.BaseController):
    RBAC_TYPE = constants.RBAC_QUOTA

    def __init__(self):
        super(QuotaUsageController, self).__init__()

    @wsme_pecan.wsexpose(quota_types.QuotaUsageResponse, wtypes.text)
    def get(self, project_id):
        """Get a single project's quota usage."""
        context = pecan.request.context.get('octavia_context')

        self._auth_validate_action(context, project_id, constants.RBAC_GET_ONE)
        with context.session.begin():
            db_quota_usage = self._get_db_quota_usage(context.session, project_id)
        return self._convert_db_to_type(
            db_quota_usage, quota_types.QuotaUsageResponse)
