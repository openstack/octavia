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

from oslo_config import cfg
from oslo_log import log as logging

from octavia.amphorae.drivers.health import heartbeat_udp
from octavia.common import service
from octavia.controller.healthmanager import health_manager
from octavia.controller.healthmanager import update_health_mixin
from octavia.controller.healthmanager import update_stats_mixin
from octavia.i18n import _LI

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
CONF.import_group('health_manager', 'octavia.common.config')


def hm_listener():
    # TODO(german): steved'or load those drivers
    udp_getter = heartbeat_udp.UDPStatusGetter(
        update_health_mixin.UpdateHealthMixin(),
        update_stats_mixin.UpdateStatsMixin())
    while True:
        udp_getter.check()


def hm_health_check():
    hm = health_manager.HealthManager()
    while True:
        hm.health_check()


def main():
    service.prepare_service(sys.argv)
    processes = []

    hm_listener_proc = multiprocessing.Process(name='HM_listener',
                                               target=hm_listener)
    processes.append(hm_listener_proc)
    hm_health_check_proc = multiprocessing.Process(name='HM_health_check',
                                                   target=hm_health_check)
    processes.append(hm_health_check_proc)
    LOG.info(_LI("Health Manager listener process starts:"))
    hm_listener_proc.start()
    LOG.info(_LI("Health manager check process starts:"))
    hm_health_check_proc.start()

    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        LOG.info(_LI("Health Manager existing due to signal"))
        hm_listener_proc.terminate()
        hm_health_check_proc.terminate()
