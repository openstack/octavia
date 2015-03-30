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

from oslo_log import log as logging
import sqlalchemy
from sqlalchemy.sql import func

from octavia.amphorae.drivers import driver_base as driver_base
from octavia.common import constants
from octavia.db import api as db_api
from octavia.db import repositories as repo

import six

LOG = logging.getLogger(__name__)


class UpdateHealthMixin(driver_base.HealthMixin):

    def __init__(self):
        super(UpdateHealthMixin, self).__init__()
        # first setup repo for amphora, listener,member(nodes),pool repo
        self.amphora_health_repo = repo.AmphoraHealthRepository()
        self.listener_repo = repo.ListenerRepository()
        self.member_repo = repo.MemberRepository()
        self.pool_repo = repo.PoolRepository()

    def update_health(self, health):
        """This function is to update db info based on amphora status

        :param health: map object that contains amphora, listener, member info
        :type map: string
        :returns: null

        This function has the following 3 goals:
        1)Update the health_manager table based on amphora status is up/down
        2)Update related DB status to be ERROR/DOWN when amphora is down
        3)Update related DB status to be ACTIVATE/UP when amphora is up
        4)Track the status of the members

        The input health data structure is shown as below:

        health = {
            "amphora-status": "AMPHORA_UP",
            "amphora-id": FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"listener-status": "ONLINE",
                                  "members": {
                                      "member-id-1": "ONLINE",
                                      "member-id-2": "ONLINE"
                                  }
                },
                "listener-id-2": {"listener-status": "ONLINE",
                                  "members": {
                                      "member-id-3": "ERROR",
                                      "member-id-4": "ERROR",
                                      "member-id-5": "ONLINE"
                                  }
                }
            }
        }
        """
        session = db_api.get_session()

        # if the input amphora is healthy, we update its db info
        # before update db, we need to check if the db has been created,
        # if not, we need to create first
        if health["amphora-status"] == constants.AMPHORA_UP:
            amphora_id = health["amphora-id"]
            amphora = self.amphora_health_repo.get(
                session, amphora_id=amphora_id)
            if amphora is None:
                self.amphora_health_repo.create(session,
                                                amphora_id=amphora_id,
                                                last_update=func.now())
            else:
                self.amphora_health_repo.update(session, amphora_id,
                                                last_update=func.now())

        # update listener and nodes db information
        listeners = health['listeners']
        for listener_id, listener in six.iteritems(listeners):

            if listener.get("listener-status") == constants.ONLINE:
                try:
                    self.listener_repo.update(
                        session, listener_id,
                        operating_status=constants.ONLINE)
                except sqlalchemy.orm.exc.NoResultFound:
                    LOG.debug("Listener %s is not in DB", listener_id)

            elif listener.get("listener-status") == constants.ERROR:
                try:
                    self.listener_repo.update(session, listener_id,
                                              operating_status=constants.ERROR)
                except sqlalchemy.orm.exc.NoResultFound:
                    LOG.debug("Listener %s is not in DB", listener_id)
            members = listener['members']
            for member_id, member in six.iteritems(members):
                    if member in constants.SUPPORTED_OPERATING_STATUSES:
                        try:
                            self.member_repo.update(
                                session, id=member_id,
                                operating_status=member)
                        except sqlalchemy.orm.exc.NoResultFound:
                            LOG.DEBUG("Member %s is not able to update in DB",
                                      member_id)
