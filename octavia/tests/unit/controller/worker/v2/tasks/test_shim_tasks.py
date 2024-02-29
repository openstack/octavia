# Copyright 2024 Red Hat
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
from octavia.common import constants
from octavia.controller.worker.v2.tasks import shim_tasks
import octavia.tests.unit.base as base


class TestShimTasks(base.TestCase):

    def test_amphora_to_amphorae_with_vrrp_ip(self):

        amp_to_amps = shim_tasks.AmphoraToAmphoraeWithVRRPIP()

        base_port = {constants.FIXED_IPS:
                     [{constants.IP_ADDRESS: '192.0.2.43'}]}
        amphora = {constants.ID: '123456'}
        expected_amphora = [{constants.ID: '123456',
                             constants.VRRP_IP: '192.0.2.43'}]

        self.assertEqual(expected_amphora,
                         amp_to_amps.execute(amphora, base_port))
