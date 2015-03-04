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
import multiprocessing
import sys
import time

from oslo_config import cfg
from oslo_log import log as logging

from octavia.common import service
from octavia.controller.healthmanager import health_manager
from octavia.i18n import _LI

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
CONF.import_group('health_manager', 'octavia.common.config')


def HM_listener():
    while True:
        time.sleep(5)
        # to do by Carlos


def HM_health_check():
    while True:
        time.sleep(CONF.health_manager.interval)
        hm = health_manager.HealthManager()
        hm.health_check()


def main():
    service.prepare_service(sys.argv)
    processes = []

    HM_listener_proc = multiprocessing.Process(name='HM_listener',
                                               target=HM_listener)
    processes.append(HM_listener_proc)
    HM_health_check_proc = multiprocessing.Process(name='HM_health_check',
                                                   target=HM_health_check)
    processes.append(HM_health_check_proc)
    LOG.info(_LI("Health Manager listener process starts:"))
    HM_listener_proc.start()
    LOG.info(_LI("Health manager check process starts:"))
    HM_health_check_proc.start()

    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        LOG.info(_LI("Health Manager existing due to signal"))
        HM_listener_proc.terminate()
        HM_health_check_proc.terminate()
