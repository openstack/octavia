# Copyright 2016 IBM
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

from octavia.common import constants
from octavia.common import data_models
from octavia.db import repositories as repo

LOG = logging.getLogger(__name__)


class StatsMixin(object):

    def __init__(self):
        super(StatsMixin, self).__init__()
        self.listener_stats_repo = repo.ListenerStatisticsRepository()
        self.repo_amphora = repo.AmphoraRepository()
        self.repo_loadbalancer = repo.LoadBalancerRepository()

    def get_listener_stats(self, session, listener_id):
        """Gets the listener statistics data_models object."""
        db_ls, _ = self.listener_stats_repo.get_all(
            session, listener_id=listener_id)
        if not db_ls:
            LOG.warning("Listener Statistics for Listener %s was not found",
                        listener_id)

        statistics = data_models.ListenerStatistics(listener_id=listener_id)

        for db_l in db_ls:
            statistics += db_l

            amp = self.repo_amphora.get(session, id=db_l.amphora_id)
            if amp and amp.status == constants.AMPHORA_ALLOCATED:
                statistics.active_connections += db_l.active_connections
        return statistics

    def get_loadbalancer_stats(self, session, loadbalancer_id):
        statistics = data_models.LoadBalancerStatistics()
        lb_db = self.repo_loadbalancer.get(session, id=loadbalancer_id)

        for listener in lb_db.listeners:
            data = self.get_listener_stats(session, listener.id)
            statistics.bytes_in += data.bytes_in
            statistics.bytes_out += data.bytes_out
            statistics.request_errors += data.request_errors
            statistics.active_connections += data.active_connections
            statistics.total_connections += data.total_connections
            statistics.listeners.append(data)
        return statistics
