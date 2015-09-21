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

import datetime
import sys
import threading
import time

from oslo_config import cfg
from oslo_log import log as logging

from octavia.common import service
from octavia.controller.housekeeping import house_keeping
from octavia.i18n import _LI

LOG = logging.getLogger(__name__)
CONF = cfg.CONF
CONF.import_group('house_keeping', 'octavia.common.config')

spare_amp_thread_event = threading.Event()
db_cleanup_thread_event = threading.Event()


def spare_amphora_check():
    """Initiates spare amp check with respect to configured interval."""

    # Read the interval from CONF
    interval = CONF.house_keeping.spare_check_interval
    LOG.info(_LI("Spare check interval is set to %d sec") % interval)

    spare_amp = house_keeping.SpareAmphora()
    while spare_amp_thread_event.is_set():
        LOG.debug("Initiating spare amphora check...")
        spare_amp.spare_check()
        time.sleep(interval)


def db_cleanup():
    """Perform db cleanup for old amphora."""
    # Read the interval from CONF
    interval = CONF.house_keeping.cleanup_interval
    LOG.info(_LI("DB cleanup interval is set to %d sec") % interval)
    LOG.info(_LI('Amphora expiry age is %s seconds') %
             CONF.house_keeping.amphora_expiry_age)

    db_cleanup = house_keeping.DatabaseCleanup()
    while db_cleanup_thread_event.is_set():
        LOG.debug("Initiating the cleanup of old amphora...")
        db_cleanup.delete_old_amphorae()
        time.sleep(interval)


def main():
    service.prepare_service(sys.argv)

    timestamp = str(datetime.datetime.utcnow())
    LOG.info(_LI("Starting house keeping at %s") % timestamp)

    # Thread to perform spare amphora check
    spare_amp_thread = threading.Thread(target=spare_amphora_check)
    spare_amp_thread.daemon = True
    spare_amp_thread_event.set()
    spare_amp_thread.start()

    # Thread to perform db cleanup
    db_cleanup_thread = threading.Thread(target=db_cleanup)
    db_cleanup_thread.daemon = True
    db_cleanup_thread_event.set()
    db_cleanup_thread.start()

    # Try-Exception block should be at the end to gracefully exit threads
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        LOG.info(_LI("Attempting to gracefully terminate House-Keeping"))
        spare_amp_thread_event.clear()
        db_cleanup_thread_event.clear()
        spare_amp_thread.join()
        db_cleanup_thread.join()
        LOG.info(_LI("House-Keeping process terminated"))
