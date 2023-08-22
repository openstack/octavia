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

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging
from oslo_utils import excutils
from pecan import expose as pecan_expose
from pecan import request as pecan_request
from sqlalchemy.orm import exc as sa_exception
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v2.controllers import base
from octavia.api.v2.types import amphora as amp_types
from octavia.common import constants
from octavia.common import exceptions
from octavia.common import rpc

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class AmphoraController(base.BaseController):
    RBAC_TYPE = constants.RBAC_AMPHORA

    def __init__(self):
        super().__init__()
        topic = cfg.CONF.oslo_messaging.topic
        self.target = messaging.Target(
            namespace=constants.RPC_NAMESPACE_CONTROLLER_AGENT,
            topic=topic, version="1.0", fanout=False)
        self.client = rpc.get_client(self.target)

    @wsme_pecan.wsexpose(amp_types.AmphoraRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get_one(self, id, fields=None):
        """Gets a single amphora's details."""
        context = pecan_request.context.get('octavia_context')
        with context.session.begin():
            db_amp = self._get_db_amp(context.session, id, show_deleted=False)

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
        """Gets all amphorae."""
        pcontext = pecan_request.context
        context = pcontext.get('octavia_context')

        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_GET_ALL)

        with context.session.begin():
            db_amp, links = self.repositories.amphora.get_all_API_list(
                context.session, show_deleted=False,
                pagination_helper=pcontext.get(constants.PAGINATION_HELPER))
        result = self._convert_db_to_type(
            db_amp, [amp_types.AmphoraResponse])
        if fields is not None:
            result = self._filter_fields(result, fields)
        return amp_types.AmphoraeRootResponse(
            amphorae=result, amphorae_links=links)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=204)
    def delete(self, id):
        """Deletes an amphora."""
        context = pecan_request.context.get('octavia_context')

        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_DELETE)

        with context.session.begin():
            try:
                self.repositories.amphora.test_and_set_status_for_delete(
                    context.session, id)
            except sa_exception.NoResultFound as e:
                raise exceptions.NotFound(resource='Amphora', id=id) from e

            LOG.info("Sending delete amphora %s to the queue.", id)
            payload = {constants.AMPHORA_ID: id}
            self.client.cast({}, 'delete_amphora', **payload)

    @pecan_expose()
    def _lookup(self, amphora_id, *remainder):
        """Overridden pecan _lookup method for custom routing.

        Currently it checks if this was a failover request and routes
        the request to the FailoverController.
        """
        if amphora_id and remainder:
            controller = remainder[0]
            remainder = remainder[1:]
            if controller == 'config':
                return AmphoraUpdateController(amp_id=amphora_id), remainder
            if controller == 'failover':
                return FailoverController(amp_id=amphora_id), remainder
            if controller == 'stats':
                return AmphoraStatsController(amp_id=amphora_id), remainder
        return None


class FailoverController(base.BaseController):
    RBAC_TYPE = constants.RBAC_AMPHORA

    def __init__(self, amp_id):
        super().__init__()
        topic = constants.TOPIC_AMPHORA_V2
        version = "2.0"
        self.target = messaging.Target(
            namespace=constants.RPC_NAMESPACE_CONTROLLER_AGENT,
            topic=topic, version=version, fanout=False)
        self.client = rpc.get_client(self.target)
        self.amp_id = amp_id

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=202)
    def put(self):
        """Fails over an amphora"""
        pcontext = pecan_request.context
        context = pcontext.get('octavia_context')
        with context.session.begin():
            db_amp = self._get_db_amp(context.session, self.amp_id,
                                      show_deleted=False)

        self._auth_validate_action(
            context, db_amp.load_balancer.project_id,
            constants.RBAC_PUT_FAILOVER)

        with context.session.begin():
            self.repositories.load_balancer.test_and_set_provisioning_status(
                context.session, db_amp.load_balancer_id,
                status=constants.PENDING_UPDATE, raise_exception=True)

            try:
                LOG.info("Sending failover request for amphora %s to the "
                         "queue", self.amp_id)
                payload = {constants.AMPHORA_ID: db_amp.id}
                self.client.cast({}, 'failover_amphora', **payload)
            except Exception:
                with excutils.save_and_reraise_exception(reraise=False):
                    self.repositories.load_balancer.update(
                        context.session, db_amp.load_balancer.id,
                        provisioning_status=constants.ERROR)


class AmphoraUpdateController(base.BaseController):
    RBAC_TYPE = constants.RBAC_AMPHORA

    def __init__(self, amp_id):
        super().__init__()

        topic = constants.TOPIC_AMPHORA_V2
        version = "2.0"
        self.target = messaging.Target(
            namespace=constants.RPC_NAMESPACE_CONTROLLER_AGENT,
            topic=topic, version=version, fanout=False)
        self.client = rpc.get_client(self.target)
        self.amp_id = amp_id

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=202)
    def put(self):
        """Update amphora agent configuration"""
        pcontext = pecan_request.context
        context = pcontext.get('octavia_context')
        with context.session.begin():
            db_amp = self._get_db_amp(context.session, self.amp_id,
                                      show_deleted=False)

        self._auth_validate_action(
            context, db_amp.load_balancer.project_id,
            constants.RBAC_PUT_CONFIG)

        try:
            LOG.info("Sending amphora agent update request for amphora %s to "
                     "the queue.", self.amp_id)
            payload = {constants.AMPHORA_ID: db_amp.id}
            self.client.cast({}, 'update_amphora_agent_config', **payload)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=True):
                LOG.error("Unable to send amphora agent update request for "
                          "amphora %s to the queue.", self.amp_id)


class AmphoraStatsController(base.BaseController):
    RBAC_TYPE = constants.RBAC_AMPHORA

    def __init__(self, amp_id):
        super().__init__()
        self.amp_id = amp_id

    @wsme_pecan.wsexpose(amp_types.StatisticsRootResponse, wtypes.text,
                         status_code=200)
    def get(self):
        context = pecan_request.context.get('octavia_context')

        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_GET_STATS)

        with context.session.begin():
            stats = self.repositories.get_amphora_stats(context.session,
                                                        self.amp_id)
        if not stats:
            raise exceptions.NotFound(resource='Amphora stats for',
                                      id=self.amp_id)

        wsme_stats = []
        for stat in stats:
            wsme_stats.append(amp_types.AmphoraStatisticsResponse(**stat))
        return amp_types.StatisticsRootResponse(amphora_stats=wsme_stats)
