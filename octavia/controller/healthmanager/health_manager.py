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
#

from concurrent import futures
import functools

from oslo_config import cfg
from oslo_db import exception as db_exc
from oslo_log import log as logging
from oslo_utils import excutils

from octavia.controller.worker import controller_worker as cw
from octavia.db import api as db_api
from octavia.db import repositories as repo

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def wait_done_or_dead(futs, dead, check_timeout=1):
    while True:
        _done, not_done = futures.wait(futs, timeout=check_timeout)
        if len(not_done) == 0:
            break
        if dead.is_set():
            for fut in not_done:
                # This may not actually be able to cancel, but try to
                # if we can.
                fut.cancel()


def update_stats_on_done(stats, fut):
    # This utilizes the fact that python, non-primitive types are
    # passed by reference (not by value)...
    stats['failover_attempted'] += 1
    try:
        fut.result()
    except futures.CancelledError:
        stats['failover_cancelled'] += 1
    except Exception:
        stats['failover_failed'] += 1


class HealthManager(object):
    def __init__(self, exit_event):
        self.cw = cw.ControllerWorker()
        self.threads = CONF.health_manager.failover_threads
        self.executor = futures.ThreadPoolExecutor(max_workers=self.threads)
        self.amp_health_repo = repo.AmphoraHealthRepository()
        self.dead = exit_event

    def health_check(self):
        stats = {
            'failover_attempted': 0,
            'failover_failed': 0,
            'failover_cancelled': 0,
        }
        futs = []
        while not self.dead.is_set():
            lock_session = db_api.get_session(autocommit=False)
            amp = None
            try:
                amp = self.amp_health_repo.get_stale_amphora(lock_session)
                lock_session.commit()
            except db_exc.DBDeadlock:
                LOG.debug('Database reports deadlock. Skipping.')
                lock_session.rollback()
            except db_exc.RetryRequest:
                LOG.debug('Database is requesting a retry. Skipping.')
                lock_session.rollback()
            except Exception:
                with excutils.save_and_reraise_exception():
                    lock_session.rollback()

            if amp is None:
                break

            LOG.info("Stale amphora's id is: %s", amp.amphora_id)
            fut = self.executor.submit(
                self.cw.failover_amphora, amp.amphora_id)
            fut.add_done_callback(
                functools.partial(update_stats_on_done, stats)
            )
            futs.append(fut)
            if len(futs) == self.threads:
                break
        if futs:
            LOG.info("Waiting for %s failovers to finish",
                     len(futs))
            wait_done_or_dead(futs, self.dead)
        if stats['failover_attempted'] > 0:
            LOG.info("Attempted %s failovers of amphora",
                     stats['failover_attempted'])
            LOG.info("Failed at %s failovers of amphora",
                     stats['failover_failed'])
            LOG.info("Cancelled %s failovers of amphora",
                     stats['failover_cancelled'])
            happy_failovers = stats['failover_attempted']
            happy_failovers -= stats['failover_cancelled']
            happy_failovers -= stats['failover_failed']
            LOG.info("Successfully completed %s failovers of amphora",
                     happy_failovers)
