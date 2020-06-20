# Copyright 2018 GoDaddy
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

from oslo_log import log as logging

from octavia.statistics import stats_base

LOG = logging.getLogger(__name__)


class StatsLogger(stats_base.StatsDriverMixin):
    def update_stats(self, listener_stats, deltas=False):
        for stats_object in listener_stats:
            LOG.info("Logging listener stats%s for listener `%s` / "
                     "amphora `%s`: %s",
                     ' deltas' if deltas else '',
                     stats_object.listener_id, stats_object.amphora_id,
                     stats_object.get_stats())
