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
import time

from oslo_config import cfg
from oslo_db import exception as db_exc
from oslo_log import log as logging
from oslo_utils import excutils

from octavia.common import constants
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
        self.amp_repo = repo.AmphoraRepository()
        self.amp_health_repo = repo.AmphoraHealthRepository()
        self.lb_repo = repo.LoadBalancerRepository()
        self.dead = exit_event

    def _test_and_set_failover_prov_status(self, lock_session, lb_id):
        if self.lb_repo.set_status_for_failover(lock_session, lb_id,
                                                constants.PENDING_UPDATE):
            return True
        else:
            db_lb = self.lb_repo.get(lock_session, id=lb_id)
            prov_status = db_lb.provisioning_status
            LOG.warning("Load balancer %(id)s is in immutable state "
                        "%(state)s. Skipping failover.",
                        {"state": prov_status, "id": db_lb.id})
            return False

    def health_check(self):
        stats = {
            'failover_attempted': 0,
            'failover_failed': 0,
            'failover_cancelled': 0,
        }
        futs = []
        while not self.dead.is_set():
            amp_health = None
            lock_session = None
            try:
                lock_session = db_api.get_session(autocommit=False)
                amp = None
                amp_health = self.amp_health_repo.get_stale_amphora(
                    lock_session)
                if amp_health:
                    amp = self.amp_repo.get(lock_session,
                                            id=amp_health.amphora_id)
                    # If there is an associated LB, attempt to set it to
                    # PENDING_UPDATE. If it is already immutable, skip the
                    # amphora on this cycle
                    if amp and amp.load_balancer_id:
                        if not self._test_and_set_failover_prov_status(
                                lock_session, amp.load_balancer_id):
                            lock_session.rollback()
                            break
                lock_session.commit()
            except db_exc.DBDeadlock:
                LOG.debug('Database reports deadlock. Skipping.')
                lock_session.rollback()
                amp_health = None
            except db_exc.RetryRequest:
                LOG.debug('Database is requesting a retry. Skipping.')
                lock_session.rollback()
                amp_health = None
            except db_exc.DBConnectionError:
                db_api.wait_for_connection(self.dead)
                lock_session.rollback()
                amp_health = None
                if not self.dead.is_set():
                    # amphora heartbeat timestamps should also be outdated
                    # while DB is unavailable and soon after DB comes back
                    # online. Sleeping off the full "heartbeat_timeout"
                    # interval to give the amps a chance to check in before
                    # we start failovers.
                    time.sleep(CONF.health_manager.heartbeat_timeout)
            except Exception:
                with excutils.save_and_reraise_exception():
                    if lock_session:
                        lock_session.rollback()

            if amp_health is None:
                break

            LOG.info("Stale amphora's id is: %s", amp_health.amphora_id)
            fut = self.executor.submit(
                self.cw.failover_amphora, amp_health.amphora_id)
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
