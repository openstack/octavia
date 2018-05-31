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
        self.fault_object = 'MCP'
        self.fault_object_id = '-1'
        self.fault_record = 'skip'

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

    def test_UpdateStatusError(self):
        update_status_error = exceptions.UpdateStatusError(
            fault_string=self.user_fault_string,
            status_object=self.fault_object,
            status_object_id=self.fault_object_id,
            status_record=self.fault_record)

        self.assertEqual(self.user_fault_string,
                         update_status_error.fault_string)
        self.assertEqual(self.fault_object, update_status_error.status_object)
        self.assertEqual(self.fault_object_id,
                         update_status_error.status_object_id)
        self.assertEqual(self.fault_record, update_status_error.status_record)

    def test_UpdateStatisticsError(self):
        update_stats_error = exceptions.UpdateStatisticsError(
            fault_string=self.user_fault_string,
            stats_object=self.fault_object,
            stats_object_id=self.fault_object_id,
            stats_record=self.fault_record)

        self.assertEqual(self.user_fault_string,
                         update_stats_error.fault_string)
        self.assertEqual(self.fault_object, update_stats_error.stats_object)
        self.assertEqual(self.fault_object_id,
                         update_stats_error.stats_object_id)
        self.assertEqual(self.fault_record, update_stats_error.stats_record)
