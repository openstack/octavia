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
import time

from oslo_config import cfg
from oslo_log import log as logging
from oslo_reports import guru_meditation_report as gmr
import setproctitle
from stevedore import enabled as stevedore_enabled

from octavia.api.drivers.driver_agent import driver_listener
from octavia.common import service
from octavia import version

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
PROVIDER_AGENT_PROCESSES = []


def _mutate_config(*args, **kwargs):
    CONF.mutate_config_files()


def _handle_mutate_config(status_proc_pid, stats_proc_pid, *args, **kwargs):
    LOG.info("Driver agent received HUP signal, mutating config.")
    _mutate_config()
    os.kill(status_proc_pid, signal.SIGHUP)
    os.kill(stats_proc_pid, signal.SIGHUP)


def _check_if_provider_agent_enabled(extension):
    if extension.name in CONF.driver_agent.enabled_provider_agents:
        return True
    return False


def _process_wrapper(exit_event, proc_name, function, agent_name=None):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGHUP, _mutate_config)
    if agent_name:
        process_title = 'octavia-driver-agent - {} -- {}'.format(
            proc_name, agent_name)
    else:
        process_title = 'octavia-driver-agent - {}'.format(proc_name)
    setproctitle.setproctitle(process_title)
    while not exit_event.is_set():
        try:
            function(exit_event)
        except Exception as e:
            if agent_name:
                LOG.exception('Provider agent "%s" raised exception: %s. '
                              'Restarting the "%s" provider agent.',
                              agent_name, str(e), agent_name)
            else:
                LOG.exception('%s raised exception: %s. '
                              'Restarting %s.',
                              proc_name, str(e), proc_name)
            time.sleep(1)
            continue
        break


def _start_provider_agents(exit_event):
    extensions = stevedore_enabled.EnabledExtensionManager(
        namespace='octavia.driver_agent.provider_agents',
        check_func=_check_if_provider_agent_enabled)
    for ext in extensions:
        ext_process = multiprocessing.Process(
            name=ext.name, target=_process_wrapper,
            args=(exit_event, 'provider_agent', ext.plugin),
            kwargs={'agent_name': ext.name})
        PROVIDER_AGENT_PROCESSES.append(ext_process)
        ext_process.start()
        LOG.info('Started enabled provider agent: "%s" with PID: %d.',
                 ext.name, ext_process.pid)


def main():
    service.prepare_service(sys.argv)

    gmr.TextGuruMeditation.setup_autorun(version)

    processes = []
    exit_event = multiprocessing.Event()

    status_listener_proc = multiprocessing.Process(
        name='status_listener', target=_process_wrapper,
        args=(exit_event, 'status_listener', driver_listener.status_listener))
    processes.append(status_listener_proc)

    LOG.info("Driver agent status listener process starts:")
    status_listener_proc.start()

    stats_listener_proc = multiprocessing.Process(
        name='stats_listener', target=_process_wrapper,
        args=(exit_event, 'stats_listener', driver_listener.stats_listener))
    processes.append(stats_listener_proc)

    LOG.info("Driver agent statistics listener process starts:")
    stats_listener_proc.start()

    get_listener_proc = multiprocessing.Process(
        name='get_listener', target=_process_wrapper,
        args=(exit_event, 'get_listener', driver_listener.get_listener))
    processes.append(get_listener_proc)

    LOG.info("Driver agent get listener process starts:")
    get_listener_proc.start()

    _start_provider_agents(exit_event)

    def process_cleanup(*args, **kwargs):
        LOG.info("Driver agent exiting due to signal.")
        exit_event.set()
        status_listener_proc.join()
        stats_listener_proc.join()
        get_listener_proc.join()

        for proc in PROVIDER_AGENT_PROCESSES:
            LOG.info('Waiting up to %s seconds for provider agent "%s" to '
                     'shutdown.',
                     CONF.driver_agent.provider_agent_shutdown_timeout,
                     proc.name)
            try:
                proc.join(CONF.driver_agent.provider_agent_shutdown_timeout)
                if proc.exitcode is None:
                    # TODO(johnsom) Change to proc.kill() once
                    #               python 3.7 or newer only
                    os.kill(proc.pid, signal.SIGKILL)
                    LOG.warning(
                        'Forcefully killed "%s" provider agent because it '
                        'failed to shutdown in %s seconds.', proc.name,
                        CONF.driver_agent.provider_agent_shutdown_timeout)
            except Exception as e:
                LOG.warning('Unknown error "%s" while shutting down "%s", '
                            'ignoring and continuing shutdown process.',
                            str(e), proc.name)
            else:
                LOG.info('Provider agent "%s" has succesfully shutdown.',
                         proc.name)

    signal.signal(signal.SIGTERM, process_cleanup)
    signal.signal(signal.SIGHUP, partial(
        _handle_mutate_config, status_listener_proc.pid,
        stats_listener_proc.pid, get_listener_proc.pid))

    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        process_cleanup()
