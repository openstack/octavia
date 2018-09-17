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
from oslo_utils import excutils
import pecan
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v2.controllers import base
from octavia.api.v2.types import amphora as amp_types
from octavia.common import constants


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class AmphoraController(base.BaseController):
    RBAC_TYPE = constants.RBAC_AMPHORA

    def __init__(self):
        super(AmphoraController, self).__init__()
        self.handler = self.handler.amphora

    @wsme_pecan.wsexpose(amp_types.AmphoraRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get_one(self, id, fields=None):
        """Gets a single amphora's details."""
        context = pecan.request.context.get('octavia_context')
        db_amp = self._get_db_amp(context.session, id)

        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_GET_ONE)

        result = self._convert_db_to_type(
            db_amp, amp_types.AmphoraResponse)
        if fields is not None:
            result = self._filter_fields([result], fields)[0]
        return amp_types.AmphoraRootResponse(amphora=result)

    @wsme_pecan.wsexpose(amp_types.AmphoraeRootResponse, [wtypes.text],
                         ignore_extra_args=True)
    def get_all(self, fields=None):
        """Gets all health monitors."""
        pcontext = pecan.request.context
        context = pcontext.get('octavia_context')

        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_GET_ALL)

        db_amp, links = self.repositories.amphora.get_all_API_list(
            context.session, show_deleted=False,
            pagination_helper=pcontext.get(constants.PAGINATION_HELPER))
        result = self._convert_db_to_type(
            db_amp, [amp_types.AmphoraResponse])
        if fields is not None:
            result = self._filter_fields(result, fields)
        return amp_types.AmphoraeRootResponse(
            amphorae=result, amphorae_links=links)

    @pecan.expose()
    def _lookup(self, amphora_id, *remainder):
        """Overridden pecan _lookup method for custom routing.

        Currently it checks if this was a failover request and routes
        the request to the FailoverController.
        """
        if amphora_id and len(remainder):
            controller = remainder[0]
            remainder = remainder[1:]
            if controller == 'failover':
                return FailoverController(amp_id=amphora_id), remainder


class FailoverController(base.BaseController):
    RBAC_TYPE = constants.RBAC_AMPHORA

    def __init__(self, amp_id):
        super(FailoverController, self).__init__()
        self.handler = self.handler.amphora
        self.amp_id = amp_id

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=202)
    def put(self):
        """Fails over an amphora"""
        pcontext = pecan.request.context
        context = pcontext.get('octavia_context')
        db_amp = self._get_db_amp(context.session, self.amp_id)

        self._auth_validate_action(
            context, db_amp.load_balancer.project_id,
            constants.RBAC_PUT_FAILOVER)

        self.repositories.load_balancer.test_and_set_provisioning_status(
            context.session, db_amp.load_balancer_id,
            status=constants.PENDING_UPDATE, raise_exception=True)
        try:
            LOG.info("Sending failover request for amphora %s to the handler",
                     self.amp_id)
            self.handler.failover(db_amp)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.load_balancer.update(
                    context.session, db_amp.load_balancer.id,
                    provisioning_status=constants.ERROR)
