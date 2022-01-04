# Copyright 2014-2015 Hewlett-Packard Development Company, L.P.
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

import concurrent.futures
import datetime
import functools

from oslo_config import cfg
from oslo_log import log
from oslo_utils import uuidutils
from taskflow.conductors.backends import impl_blocking
from taskflow import engines
from taskflow import exceptions as taskflow_exc
from taskflow.listeners import base
from taskflow.listeners import logging
from taskflow.persistence import models
from taskflow import states

from octavia.amphorae.driver_exceptions import exceptions

LOG = log.getLogger(__name__)

CONF = cfg.CONF


# We do not need to log retry exception information. Warning "Could not connect
#  to instance" will be logged as usual.
def retryMaskFilter(record):
    if record.exc_info is not None and isinstance(
            record.exc_info[1], exceptions.AmpConnectionRetry):
        return False
    return True


LOG.logger.addFilter(retryMaskFilter)


class BaseTaskFlowEngine(object):
    """This is the task flow engine

    Use this engine to start/load flows in the
    code
    """

    def __init__(self):
        # work around for https://bugs.python.org/issue7980
        datetime.datetime.strptime('2014-06-19 22:47:16', '%Y-%m-%d %H:%M:%S')
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=CONF.task_flow.max_workers)

    def taskflow_load(self, flow, **kwargs):
        eng = engines.load(
            flow,
            engine=CONF.task_flow.engine,
            executor=self.executor,
            never_resolve=CONF.task_flow.disable_revert,
            **kwargs)
        eng.compile()
        eng.prepare()

        return eng


class ExtendExpiryListener(base.Listener):

    def __init__(self, engine, job):
        super().__init__(engine)
        self.job = job

    def _task_receiver(self, state, details):
        self.job.extend_expiry(cfg.CONF.task_flow.jobboard_expiration_time)

    def _flow_receiver(self, state, details):
        self.job.extend_expiry(cfg.CONF.task_flow.jobboard_expiration_time)

    def _retry_receiver(self, state, details):
        self.job.extend_expiry(cfg.CONF.task_flow.jobboard_expiration_time)


class DynamicLoggingConductor(impl_blocking.BlockingConductor):

    def _listeners_from_job(self, job, engine):
        listeners = super()._listeners_from_job(
            job, engine)
        listeners.append(logging.DynamicLoggingListener(engine, log=LOG))

        return listeners

    def _on_job_done(self, job, fut):
        super()._on_job_done(job, fut)
        # Double check that job is complete.
        if (not CONF.task_flow.jobboard_save_logbook and
                job.state == states.COMPLETE):
            LOG.debug("Job %s is complete. Cleaning up job logbook.", job.name)
            try:
                self._persistence.get_connection().destroy_logbook(
                    job.book.uuid)
            except taskflow_exc.NotFound:
                LOG.debug("Logbook for job %s has been already cleaned up",
                          job.name)


class RedisDynamicLoggingConductor(DynamicLoggingConductor):

    def _listeners_from_job(self, job, engine):
        listeners = super()._listeners_from_job(job, engine)
        listeners.append(ExtendExpiryListener(engine, job))
        return listeners


class TaskFlowServiceController(object):

    def __init__(self, driver):
        self.driver = driver

    def run_poster(self, flow_factory, *args, **kwargs):
        with self.driver.persistence_driver.get_persistence() as persistence:
            with self.driver.job_board(persistence) as job_board:
                job_id = uuidutils.generate_uuid()
                job_name = '-'.join([flow_factory.__name__, job_id])
                job_logbook = models.LogBook(job_name)
                flow_detail = models.FlowDetail(
                    job_name, job_id)
                job_details = {
                    'store': kwargs.pop('store')
                }
                job_logbook.add(flow_detail)
                persistence.get_connection().save_logbook(job_logbook)
                engines.save_factory_details(flow_detail, flow_factory,
                                             args, kwargs,
                                             backend=persistence)

                job_board.post(job_name, book=job_logbook,
                               details=job_details)
                self._wait_for_job(job_board)

                return job_id

    def _wait_for_job(self, job_board):
        # Wait for job to its complete state
        expiration_time = CONF.task_flow.jobboard_expiration_time

        need_wait = True
        while need_wait:
            need_wait = False
            for job in job_board.iterjobs():
                # If job hasn't finished in expiration_time/2 seconds,
                # extend its TTL
                if not job.wait(timeout=expiration_time / 2):
                    job.extend_expiry(expiration_time)
                    need_wait = True

    def run_conductor(self, name):
        with self.driver.persistence_driver.get_persistence() as persistence:
            with self.driver.job_board(persistence) as board:
                # Redis do not expire jobs by default, so jobs won't be resumed
                # with restart of controller. Add expiry for board and use
                # special listener.
                if (CONF.task_flow.jobboard_backend_driver ==
                        'redis_taskflow_driver'):
                    conductor = RedisDynamicLoggingConductor(
                        name, board, persistence=persistence,
                        engine=CONF.task_flow.engine,
                        engine_options={
                            'max_workers': CONF.task_flow.max_workers
                        })
                    board.claim = functools.partial(
                        board.claim,
                        expiry=CONF.task_flow.jobboard_expiration_time)
                else:
                    conductor = DynamicLoggingConductor(
                        name, board, persistence=persistence,
                        engine=CONF.task_flow.engine)

                conductor.run()
