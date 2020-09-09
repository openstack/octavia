# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_config import cfg
from oslo_log import log as logging

from octavia.db import api as db_api
from octavia.db import repositories as repo
from octavia.statistics import stats_base

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class StatsUpdateDb(stats_base.StatsDriverMixin):

    def __init__(self):
        super().__init__()
        self.listener_stats_repo = repo.ListenerStatisticsRepository()

    def update_stats(self, listener_stats, deltas=False):
        """This function is to update the db with listener stats"""
        session = db_api.get_session()
        for stats_object in listener_stats:
            LOG.debug("Updating listener stats in db for listener `%s` / "
                      "amphora `%s`: %s",
                      stats_object.listener_id, stats_object.amphora_id,
                      stats_object.get_stats())
            if deltas:
                self.listener_stats_repo.increment(session, stats_object)
            else:
                self.listener_stats_repo.replace(session, stats_object)
