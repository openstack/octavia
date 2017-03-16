# Copyright 2016 Hewlett-Packard Development Company, L.P.
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

import time

from oslo_config import cfg
from oslo_log import log as logging

from octavia.common import exceptions
from octavia.db import api as db_apis
from octavia.db import repositories as repo

LOG = logging.getLogger(__name__)

CONF = cfg.CONF
CONF.import_group('haproxy_amphora', 'octavia.common.config')


class AmphoraBuildRateLimit(object):

    def __init__(self):
        self.amp_build_slots_repo = repo.AmphoraBuildSlotsRepository()
        self.amp_build_req_repo = repo.AmphoraBuildReqRepository()

    def add_to_build_request_queue(self, amphora_id, build_priority):
        self.amp_build_req_repo.add_to_build_queue(
            db_apis.get_session(),
            amphora_id=amphora_id,
            priority=build_priority)
        LOG.debug("Added build request for %s to the queue", amphora_id)
        self.wait_for_build_slot(amphora_id)

    def has_build_slot(self):
        build_rate_limit = CONF.haproxy_amphora.build_rate_limit
        session = db_apis.get_session()
        with session.begin(subtransactions=True):
            used_build_slots = (self.amp_build_slots_repo
                                .get_used_build_slots_count(session))
            available_build_slots = build_rate_limit - used_build_slots
            LOG.debug("Available build slots %d", available_build_slots)
            return available_build_slots > 0

    def has_highest_priority(self, amphora_id):
        session = db_apis.get_session()
        with session.begin(subtransactions=True):
            highest_priority_build_req = (
                self.amp_build_req_repo.get_highest_priority_build_req(
                    session))
            LOG.debug("Highest priority req: %s, Current req: %s",
                      highest_priority_build_req, amphora_id)
            return amphora_id == highest_priority_build_req

    def update_build_status_and_available_build_slots(self, amphora_id):
        session = db_apis.get_session()
        with session.begin(subtransactions=True):
            self.amp_build_slots_repo.update_count(session, action='increment')
            self.amp_build_req_repo.update_req_status(session, amphora_id)

    def remove_from_build_req_queue(self, amphora_id):
        session = db_apis.get_session()
        with session.begin(subtransactions=True):
            self.amp_build_req_repo.delete(session, amphora_id=amphora_id)
            self.amp_build_slots_repo.update_count(session, action='decrement')
            LOG.debug("Removed request for %s from queue"
                      " and released the build slot", amphora_id)

    def remove_all_from_build_req_queue(self):
        session = db_apis.get_session()
        with session.begin(subtransactions=True):
            self.amp_build_req_repo.delete_all(session)
            self.amp_build_slots_repo.update_count(session, action='reset')
            LOG.debug("Removed all the build requests and "
                      "released the build slots")

    def wait_for_build_slot(self, amphora_id):
        LOG.debug("Waiting for a build slot")
        for i in range(CONF.haproxy_amphora.build_active_retries):
            if (self.has_build_slot() and
                    self.has_highest_priority(amphora_id)):
                self.update_build_status_and_available_build_slots(amphora_id)
                return
            time.sleep(CONF.haproxy_amphora.build_retry_interval)
        self.remove_all_from_build_req_queue()
        raise exceptions.ComputeBuildQueueTimeoutException()
