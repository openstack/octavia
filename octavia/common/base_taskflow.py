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
import time

from oslo_config import cfg
from oslo_log import log
from oslo_utils import uuidutils
from taskflow.conductors.backends import impl_blocking
from taskflow import engines
from taskflow import exceptions as taskflow_exc
from taskflow.jobs.base import Job
from taskflow.listeners import base
from taskflow.listeners import logging
from taskflow.persistence import models
from taskflow import states

from octavia.amphorae.driver_exceptions import exceptions as drv_exceptions
from octavia.common import exceptions

LOG = log.getLogger(__name__)

CONF = cfg.CONF


# We do not need to log retry exception information. Warning "Could not connect
#  to instance" will be logged as usual.
def retryMaskFilter(record):
    if record.exc_info is not None and isinstance(
            record.exc_info[1], (
                drv_exceptions.AmpConnectionRetry,
                exceptions.ComputeWaitTimeoutException)):
        return False
    return True


LOG.logger.addFilter(retryMaskFilter)


def _details_filter(obj):
    if isinstance(obj, dict):
        ret = {}
        for key in obj:
            if (key in ('certificate', 'private_key', 'passphrase') and
                    isinstance(obj[key], str)):
                ret[key] = '***'
            elif key == 'intermediates' and isinstance(obj[key], list):
                ret[key] = ['***'] * len(obj[key])
            else:
                ret[key] = _details_filter(obj[key])
        return ret
    if isinstance(obj, list):
        return [_details_filter(e) for e in obj]
    return obj


class FilteredJob(Job):
    def __str__(self):
        # Override the detault __str__ method from taskflow.job.base.Job,
        # filter out private information from details
        cls_name = type(self).__name__
        details = _details_filter(self.details)
        return "%s: %s (priority=%s, uuid=%s, details=%s)" % (
            cls_name, self.name, self.priority,
            self.uuid, details)


class JobDetailsFilter(log.logging.Filter):
    def filter(self, record):
        # If the first arg is a Job, convert it now to a string with our custom
        # method
        if isinstance(record.args[0], Job):
            arg0 = record.args[0]
            record.args = (FilteredJob.__str__(arg0),) + record.args[1:]
        return True


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
            if job.book:
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

        # Install filter for taskflow executor logger
        taskflow_logger = log.logging.getLogger(
            "taskflow.conductors.backends.impl_executor")
        taskflow_logger.addFilter(JobDetailsFilter())

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
        for job in job_board.iterjobs():
            LOG.debug("Waiting for job %s to finish", job.name)
            job.wait()

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

                waiter_th = concurrent.futures.ThreadPoolExecutor(
                    max_workers=1)
                waiter_th.submit(self._waiter, conductor)

                conductor.run()

    def _extend_jobs(self, conductor, expiration_time):
        conductor_name = conductor._name

        with self.driver.persistence_driver.get_persistence() as persistence:
            with self.driver.job_board(persistence) as board:
                for job in board.iterjobs():
                    try:
                        owner = board.find_owner(job)
                    except TypeError:
                        # taskflow throws an exception if a job is not owned
                        # (probably a bug in taskflow)
                        continue
                    # Only extend expiry for jobs that are owner by our
                    # conductor (from the same process)
                    if owner == conductor_name:
                        if job.expires_in() < expiration_time / 2:
                            LOG.debug("Extend expiry for job %s", job.name)
                            job.extend_expiry(expiration_time)

    def _waiter(self, conductor):
        expiration_time = CONF.task_flow.jobboard_expiration_time

        while True:
            self._extend_jobs(conductor, expiration_time)

            time.sleep(expiration_time / 4)
