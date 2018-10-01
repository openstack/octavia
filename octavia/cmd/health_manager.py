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

from functools import partial
import multiprocessing
import os
import signal
import sys

from futurist import periodics

from oslo_config import cfg
from oslo_log import log as logging
from oslo_reports import guru_meditation_report as gmr

from octavia.amphorae.drivers.health import heartbeat_udp
from octavia.common import service
from octavia.controller.healthmanager import health_manager
from octavia import version


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def _mutate_config(*args, **kwargs):
    CONF.mutate_config_files()


def hm_listener(exit_event):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGHUP, _mutate_config)
    udp_getter = heartbeat_udp.UDPStatusGetter()
    while not exit_event.is_set():
        try:
            udp_getter.check()
        except Exception as e:
            LOG.error('Health Manager listener experienced unknown error: %s',
                      e)
    LOG.info('Waiting for executor to shutdown...')
    udp_getter.health_executor.shutdown()
    udp_getter.stats_executor.shutdown()
    LOG.info('Executor shutdown finished.')


def hm_health_check(exit_event):
    hm = health_manager.HealthManager(exit_event)
    signal.signal(signal.SIGHUP, _mutate_config)

    @periodics.periodic(CONF.health_manager.health_check_interval,
                        run_immediately=True)
    def periodic_health_check():
        hm.health_check()

    health_check = periodics.PeriodicWorker(
        [(periodic_health_check, None, None)],
        schedule_strategy='aligned_last_finished')

    def hm_exit(*args, **kwargs):
        health_check.stop()
        hm.executor.shutdown()
    signal.signal(signal.SIGINT, hm_exit)
    LOG.debug("Pausing before starting health check")
    exit_event.wait(CONF.health_manager.heartbeat_timeout)
    health_check.start()


def _handle_mutate_config(listener_proc_pid, check_proc_pid, *args, **kwargs):
    LOG.info("Health Manager recieved HUP signal, mutating config.")
    _mutate_config()
    os.kill(listener_proc_pid, signal.SIGHUP)
    os.kill(check_proc_pid, signal.SIGHUP)


def main():
    service.prepare_service(sys.argv)

    gmr.TextGuruMeditation.setup_autorun(version)

    processes = []
    exit_event = multiprocessing.Event()

    hm_listener_proc = multiprocessing.Process(name='HM_listener',
                                               target=hm_listener,
                                               args=(exit_event,))
    processes.append(hm_listener_proc)
    hm_health_check_proc = multiprocessing.Process(name='HM_health_check',
                                                   target=hm_health_check,
                                                   args=(exit_event,))
    processes.append(hm_health_check_proc)

    LOG.info("Health Manager listener process starts:")
    hm_listener_proc.start()
    LOG.info("Health manager check process starts:")
    hm_health_check_proc.start()

    def process_cleanup(*args, **kwargs):
        LOG.info("Health Manager exiting due to signal")
        exit_event.set()
        os.kill(hm_health_check_proc.pid, signal.SIGINT)
        hm_health_check_proc.join()
        hm_listener_proc.join()

    signal.signal(signal.SIGTERM, process_cleanup)
    signal.signal(signal.SIGHUP, partial(
        _handle_mutate_config, hm_listener_proc.pid, hm_health_check_proc.pid))

    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        process_cleanup()
