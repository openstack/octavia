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

from octavia.api.drivers import exceptions
import octavia.tests.unit.base as base


class TestProviderExceptions(base.TestCase):

    def setUp(self):
        super(TestProviderExceptions, self).setUp()
        self.user_fault_string = 'Bad driver'
        self.operator_fault_string = 'Fix bad driver.'

    def test_DriverError(self):
        driver_error = exceptions.DriverError(
            user_fault_string=self.user_fault_string,
            operator_fault_string=self.operator_fault_string)

        self.assertEqual(self.user_fault_string,
                         driver_error.user_fault_string)
        self.assertEqual(self.operator_fault_string,
                         driver_error.operator_fault_string)
        self.assertIsInstance(driver_error, Exception)

    def test_NotImplementedError(self):
        not_implemented_error = exceptions.NotImplementedError(
            user_fault_string=self.user_fault_string,
            operator_fault_string=self.operator_fault_string)

        self.assertEqual(self.user_fault_string,
                         not_implemented_error.user_fault_string)
        self.assertEqual(self.operator_fault_string,
                         not_implemented_error.operator_fault_string)
        self.assertIsInstance(not_implemented_error, Exception)

    def test_UnsupportedOptionError(self):
        unsupported_option_error = exceptions.UnsupportedOptionError(
            user_fault_string=self.user_fault_string,
            operator_fault_string=self.operator_fault_string)

        self.assertEqual(self.user_fault_string,
                         unsupported_option_error.user_fault_string)
        self.assertEqual(self.operator_fault_string,
                         unsupported_option_error.operator_fault_string)
        self.assertIsInstance(unsupported_option_error, Exception)
