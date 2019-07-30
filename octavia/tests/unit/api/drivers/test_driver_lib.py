#    Copyright 2018 Rackspace, US Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

#    Copyright 2018 Rackspace, US Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock

import octavia_lib.api.drivers.driver_lib as lib_driver_lib

from octavia.api.drivers import driver_lib
import octavia.tests.unit.base as base


class TestDriverLib(base.TestCase):

    def setUp(self):
        super(TestDriverLib, self).setUp()

    # Silly test to check that debtcollector moves is working
    @mock.patch('octavia_lib.api.drivers.driver_lib.DriverLibrary.'
                '_check_for_socket_ready')
    def test_driver_lib_exists(self, mock_ready):
        driver_lib_class = driver_lib.DriverLibrary()
        self.assertIsInstance(driver_lib_class, lib_driver_lib.DriverLibrary)
