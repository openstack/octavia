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

import time

from concurrent import futures
from oslo_config import cfg
from oslo_log import log as logging

from octavia.controller.worker import controller_worker as cw
from octavia.db import api as db_api
from octavia.db import repositories as repo
from octavia.i18n import _LI

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
CONF.import_group('health_manager', 'octavia.common.config')


class HealthManager(object):
    def __init__(self):
        self.cw = cw.ControllerWorker()
        self.threads = CONF.health_manager.failover_threads

    def health_check(self):
        amp_health_repo = repo.AmphoraHealthRepository()

        with futures.ThreadPoolExecutor(max_workers=self.threads) as executor:
            try:
                while True:
                    time.sleep(CONF.health_manager.health_check_interval)
                    session = db_api.get_session()
                    LOG.debug("Starting amphora health check")
                    failover_count = 0
                    while True:
                        amp = amp_health_repo.get_stale_amphora(session)
                        if amp is None:
                            break
                        failover_count += 1
                        LOG.info(_LI("Stale amphora's id is: %s") %
                                 amp.amphora_id)
                        executor.submit(self.cw.failover_amphora,
                                        amp.amphora_id)
                    if failover_count > 0:
                        LOG.info(_LI("Failed over %s amphora") %
                                 failover_count)
            finally:
                executor.shutdown(wait=True)
