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
from oslo_reports import opts as gmr_opts

from octavia.amphorae.drivers.health import heartbeat_tcp
from octavia.amphorae.drivers.health import heartbeat_udp
from octavia.common import service
from octavia.controller.healthmanager import health_manager
from octavia import version

# Python 3.14 changed the default multiprocessing start method on Linux from
# "fork" to "forkserver", so the child processes no longer inherit the parsed
# configuration from the parent process.
multiproc = multiprocessing.get_context("fork")

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def _mutate_config(*args, **kwargs):
    CONF.mutate_config_files()


def hm_listener_udp(exit_event):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGHUP, _mutate_config)
    udp_getter = heartbeat_udp.UDPStatusGetter()
    while not exit_event.is_set():
        try:
            udp_getter.check()
        except Exception as e:
            LOG.error('Health Manager listener experienced unknown error: %s',
                      str(e))
    LOG.info('Waiting for executor to shutdown...')
    udp_getter.health_executor.shutdown()
    udp_getter.stats_executor.shutdown()
    LOG.info('Executor shutdown finished.')


def hm_listener_tcp(exit_event):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGHUP, _mutate_config)
    tcp_getter = heartbeat_tcp.TCPStatusGetter()
    while not exit_event.is_set():
        try:
            tcp_getter.check()
        except Exception as e:
            LOG.error('Health Manager listener (TCP) experienced unknown '
                      'error: %s',
                      str(e))
    LOG.info('Waiting for executor to shutdown...')
    tcp_getter.health_executor.shutdown()
    tcp_getter.stats_executor.shutdown()
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


def _handle_mutate_config(proc_pids, *args, **kwargs):
    LOG.info("Health Manager received HUP signal, mutating config.")
    _mutate_config()
    for pid in proc_pids:
        os.kill(pid, signal.SIGHUP)


def main():
    service.prepare_service(sys.argv)

    LOG.debug('Full set of CONF:')
    CONF.log_opt_values(LOG, logging.DEBUG)

    gmr_opts.set_defaults(CONF)
    gmr.TextGuruMeditation.setup_autorun(version, conf=CONF)

    processes = []
    exit_event = multiproc.Event()

    hm_listener_udp_proc = multiproc.Process(name='HM_listener_udp',
                                             target=hm_listener_udp,
                                             args=(exit_event,))
    processes.append(hm_listener_udp_proc)
    hm_listener_tcp_proc = None
    if CONF.health_manager.heartbeat_use_tcp_threshold >= 0:
        hm_listener_tcp_proc = multiproc.Process(name='HM_listener_tcp',
                                                 target=hm_listener_tcp,
                                                 args=(exit_event,))
        processes.append(hm_listener_tcp_proc)
    hm_health_check_proc = multiproc.Process(name='HM_health_check',
                                             target=hm_health_check,
                                             args=(exit_event,))
    processes.append(hm_health_check_proc)

    LOG.info("Health Manager listener process (UDP) starts:")
    hm_listener_udp_proc.start()
    if hm_listener_tcp_proc is not None:
        LOG.info("Health Manager listener process (TCP) starts:")
        hm_listener_tcp_proc.start()
    LOG.info("Health manager check process starts:")
    hm_health_check_proc.start()

    def process_cleanup(*args, **kwargs):
        LOG.info("Health Manager exiting due to signal")
        exit_event.set()
        os.kill(hm_health_check_proc.pid, signal.SIGINT)
        hm_health_check_proc.join()
        if hm_listener_tcp_proc is not None:
            hm_listener_tcp_proc.join()
        hm_listener_udp_proc.join()

    signal.signal(signal.SIGTERM, process_cleanup)
    pids = [process.pid for process in processes]
    signal.signal(signal.SIGHUP, partial(_handle_mutate_config, pids))

    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        process_cleanup()
