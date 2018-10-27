# Copyright 2018 Rackspace, US Inc.
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

from functools import partial
import multiprocessing
import os
import signal
import sys

from oslo_config import cfg
from oslo_log import log as logging
from oslo_reports import guru_meditation_report as gmr

from octavia.api.drivers.driver_agent import driver_listener
from octavia.common import service
from octavia import version


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def _mutate_config(*args, **kwargs):
    CONF.mutate_config_files()


def _handle_mutate_config(status_proc_pid, stats_proc_pid, *args, **kwargs):
    LOG.info("Driver agent received HUP signal, mutating config.")
    _mutate_config()
    os.kill(status_proc_pid, signal.SIGHUP)
    os.kill(stats_proc_pid, signal.SIGHUP)


def main():
    service.prepare_service(sys.argv)

    gmr.TextGuruMeditation.setup_autorun(version)

    processes = []
    exit_event = multiprocessing.Event()

    status_listener_proc = multiprocessing.Process(
        name='status_listener', target=driver_listener.status_listener,
        args=(exit_event,))
    processes.append(status_listener_proc)

    LOG.info("Driver agent status listener process starts:")
    status_listener_proc.start()

    stats_listener_proc = multiprocessing.Process(
        name='stats_listener', target=driver_listener.stats_listener,
        args=(exit_event,))
    processes.append(stats_listener_proc)

    LOG.info("Driver agent statistics listener process starts:")
    stats_listener_proc.start()

    def process_cleanup(*args, **kwargs):
        LOG.info("Driver agent exiting due to signal")
        exit_event.set()
        status_listener_proc.join()
        stats_listener_proc.join()

    signal.signal(signal.SIGTERM, process_cleanup)
    signal.signal(signal.SIGHUP, partial(
        _handle_mutate_config, status_listener_proc.pid,
        stats_listener_proc.pid))

    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        process_cleanup()
