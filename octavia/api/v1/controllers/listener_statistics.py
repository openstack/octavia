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

import pecan
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v1.controllers import base
from octavia.api.v1.types import listener_statistics as ls_types
from octavia.common import constants
from octavia.common import stats


class ListenerStatisticsController(base.BaseController,
                                   stats.StatsMixin):

    def __init__(self, listener_id):
        super(ListenerStatisticsController, self).__init__()
        self.listener_id = listener_id

    @wsme_pecan.wsexpose({wtypes.text: ls_types.ListenerStatisticsResponse})
    def get_all(self):
        """Gets a single listener's statistics details."""
        # NOTE(sbalukoff): since a listener can only have one set of
        # listener statistics we are using the get_all method to only get
        # the single set of stats
        context = pecan.request.context.get('octavia_context')
        data_stats = self.get_listener_stats(
            context.session, self.listener_id)
        return {constants.LISTENER: self._convert_db_to_type(
            data_stats, ls_types.ListenerStatisticsResponse)}
