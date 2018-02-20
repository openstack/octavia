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

from octavia.controller.healthmanager.health_drivers import update_base

LOG = logging.getLogger(__name__)


class HealthUpdateLogger(update_base.HealthUpdateBase):
    def update_health(self, health):
        LOG.info("Health update triggered for: %s", health.get('id'))


class StatsUpdateLogger(update_base.StatsUpdateBase):
    def update_stats(self, health_message):
        LOG.info("Stats update triggered for: %s", health_message.get('id'))
