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

from octavia.amphorae.drivers import driver_base as driver_base
from octavia.db import api as db_api
from octavia.db import repositories as repo

import six

LOG = logging.getLogger(__name__)


class UpdateStatsMixin(driver_base.StatsMixin):

    def __init__(self):
        super(UpdateStatsMixin, self).__init__()
        self.listener_stats_repo = repo.ListenerStatisticsRepository()

    def update_stats(self, health_message):
        """This function is to update the db with listener stats

        :param health_message: The health message containing the listener stats
        :type map: string
        :returns: null

        health = {
            "id": self.FAKE_UUID_1,
            "listeners": {
                "listener-id-1": {"status": constants.OPEN,
                                  'stats': {'conns': 0,
                                            'totconns': 0,
                                            'rx': 0,
                                            'tx': 0},
                                  "pools": {
                    "pool-id-1": {"status": constants.UP,
                                  "members": {"member-id-1": constants.ONLINE}
                                  }
                }
                }
            }
        }

        """
        session = db_api.get_session()

        listeners = health_message['listeners']
        for listener_id, listener in six.iteritems(listeners):

            stats = listener.get('stats')

            self.listener_stats_repo.replace(session, listener_id,
                                             bytes_in=stats['rx'],
                                             bytes_out=stats['tx'],
                                             active_connections=stats['conns'],
                                             total_connections=(
                                                 stats['totconns']))
