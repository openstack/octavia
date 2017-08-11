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
from oslo_db import exception as db_exc
from oslo_log import log as logging
from oslo_utils import excutils

from octavia.controller.worker import controller_worker as cw
from octavia.db import api as db_api
from octavia.db import repositories as repo

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class HealthManager(object):
    def __init__(self):
        self.cw = cw.ControllerWorker()
        self.threads = CONF.health_manager.failover_threads

    def health_check(self):
        amp_health_repo = repo.AmphoraHealthRepository()

        with futures.ThreadPoolExecutor(max_workers=self.threads) as executor:
            # Don't start checking immediately, as the health manager may
            # have been down for a while and amphorae not able to check in.
            LOG.debug("Pausing before starting health check")
            time.sleep(CONF.health_manager.heartbeat_timeout)
            while True:
                LOG.debug("Starting amphora health check")
                failover_count = 0
                while True:

                    lock_session = db_api.get_session(autocommit=False)
                    amp = None
                    try:
                        amp = amp_health_repo.get_stale_amphora(lock_session)
                        lock_session.commit()
                    except db_exc.DBDeadlock:
                        LOG.debug('Database reports deadlock. Skipping.')
                        try:
                            lock_session.rollback()
                        except Exception:
                            pass
                    except db_exc.RetryRequest:
                        LOG.debug('Database is requesting a retry. Skipping.')
                        try:
                            lock_session.rollback()
                        except Exception:
                            pass
                    except Exception:
                        with excutils.save_and_reraise_exception():
                            try:
                                lock_session.rollback()
                            except Exception:
                                pass

                    if amp is None:
                        break
                    failover_count += 1
                    LOG.info("Stale amphora's id is: %s",
                             amp.amphora_id)
                    executor.submit(self.cw.failover_amphora,
                                    amp.amphora_id)
                if failover_count > 0:
                    LOG.info("Failed over %s amphora",
                             failover_count)
                time.sleep(CONF.health_manager.health_check_interval)
