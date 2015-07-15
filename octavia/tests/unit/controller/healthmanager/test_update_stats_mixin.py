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

import random

from oslo_utils import uuidutils
import six

from octavia.common import constants
from octavia.controller.healthmanager import update_stats_mixin as statsmixin
import octavia.tests.unit.base as base

if six.PY2:
    import mock
else:
    import unittest.mock as mock


class TestUpdateStatsMixin(base.TestCase):

    def setUp(self):
        super(TestUpdateStatsMixin, self).setUp()

        self.sm = statsmixin.UpdateStatsMixin()
        self.listener_stats_repo = mock.MagicMock()
        self.sm.listener_stats_repo = self.listener_stats_repo

        self.bytes_in = random.randrange(1000000000)
        self.bytes_out = random.randrange(1000000000)
        self.active_conns = random.randrange(1000000000)
        self.total_conns = random.randrange(1000000000)
        self.loadbalancer_id = uuidutils.generate_uuid()
        self.listener_id = uuidutils.generate_uuid()

    @mock.patch('octavia.db.api.get_session')
    def test_update_stats(self, session):

        health = {
            "id": self.loadbalancer_id,
            "listeners": {
                self.listener_id: {"status": constants.OPEN,
                                   "stats": {"conns": self.active_conns,
                                             "totconns": self.total_conns,
                                             "rx": self.bytes_in,
                                             "tx": self.bytes_out},
                                   "pools": {"pool-id-1":
                                             {"status": constants.UP,
                                              "members":
                                              {"member-id-1": constants.ONLINE}
                                              }
                                             }
                                   }}}

        session.return_value = 'blah'

        self.sm.update_stats(health)

        self.listener_stats_repo.replace.assert_called_once_with(
            'blah', self.listener_id, bytes_in=self.bytes_in,
            bytes_out=self.bytes_out, active_connections=self.active_conns,
            total_connections=self.total_conns)
