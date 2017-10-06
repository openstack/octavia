#    Copyright 2014 Rackspace
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

import logging

from oslo_config import cfg
import pecan
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v2.controllers import base
from octavia.api.v2.types import amphora as amp_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class AmphoraController(base.BaseController):
    RBAC_TYPE = constants.RBAC_AMPHORA

    def _get_db_amp(self, session, amp_id):
        """Gets the current amphora object from the database."""
        db_amp = self.repositories.amphora.get(
            session, id=amp_id)
        if not db_amp:
            LOG.info("Amphora %s was not found", amp_id)
            raise exceptions.NotFound(
                resource=data_models.Amphora._name(),
                id=amp_id)
        return db_amp

    @wsme_pecan.wsexpose(amp_types.AmphoraRootResponse, wtypes.text,
                         wtypes.text)
    def get_one(self, id):
        """Gets a single amphora's details."""
        context = pecan.request.context.get('octavia_context')
        db_amp = self._get_db_amp(context.session, id)

        self._auth_validate_action(context, db_amp.load_balancer.project_id,
                                   constants.RBAC_GET_ONE)

        result = self._convert_db_to_type(
            db_amp, amp_types.AmphoraResponse)
        return amp_types.AmphoraRootResponse(amphora=result)

    @wsme_pecan.wsexpose(amp_types.AmphoraeRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get_all(self, fields=None):
        """Gets all health monitors."""
        pcontext = pecan.request.context
        context = pcontext.get('octavia_context')

        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_GET_ALL)

        db_amp, links = self.repositories.amphora.get_all(
            context.session, show_deleted=False,
            pagination_helper=pcontext.get(constants.PAGINATION_HELPER))
        result = self._convert_db_to_type(
            db_amp, [amp_types.AmphoraResponse])
        if fields is not None:
            result = self._filter_fields(result, fields)
        return amp_types.AmphoraeRootResponse(
            amphorae=result, amphorae_links=links)
