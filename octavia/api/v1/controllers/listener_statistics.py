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

import pecan
from wsmeext import pecan as wsme_pecan

from octavia.api.v1.controllers import base
from octavia.api.v1.types import listener_statistics as ls_types
from octavia.common import data_models
from octavia.common import exceptions
from octavia.i18n import _LI


LOG = logging.getLogger(__name__)


class ListenerStatisticsController(base.BaseController):

    def __init__(self, listener_id):
        super(ListenerStatisticsController, self).__init__()
        self.listener_id = listener_id

    def _get_db_ls(self, session):
        """Gets the current listener statistics object from the database."""
        db_ls = self.repositories.listener_stats.get(
            session, listener_id=self.listener_id)
        if not db_ls:
            LOG.info(_LI("Listener Statistics for Listener %s was not found"),
                     self.listener_id)
            raise exceptions.NotFound(
                resource=data_models.ListenerStatistics._name(),
                id=self.listener_id)
        return db_ls

    @wsme_pecan.wsexpose(ls_types.ListenerStatisticsResponse)
    def get_all(self):
        """Gets a single listener's statistics details."""
        # NOTE(sbalukoff): since a listener can only have one set of
        # listener statistics we are using the get_all method to only get
        # the single set of stats
        context = pecan.request.context.get('octavia_context')
        db_ls = self._get_db_ls(context.session)
        return self._convert_db_to_type(db_ls,
                                        ls_types.ListenerStatisticsResponse)
