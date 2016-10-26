#    Copyright 2016 IBM
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
from octavia.api.v1.types import load_balancer_statistics as lb_types
from octavia.common import constants
from octavia.common import stats


class LoadBalancerStatisticsController(base.BaseController,
                                       stats.StatsMixin):

    def __init__(self, loadbalancer_id):
        super(LoadBalancerStatisticsController, self).__init__()
        self.loadbalancer_id = loadbalancer_id

    @wsme_pecan.wsexpose(
        {wtypes.text: lb_types.LoadBalancerStatisticsResponse})
    def get(self):
        """Gets a single loadbalancer's statistics details."""
        context = pecan.request.context.get('octavia_context')
        data_stats = self.get_loadbalancer_stats(
            context.session, self.loadbalancer_id)
        return {constants.LOADBALANCER: self._convert_db_to_type(
            data_stats, lb_types.LoadBalancerStatisticsResponse)}
