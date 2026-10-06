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

from octavia.db import types as db_types
from octavia.tests.unit import base


class TestScalarListType(base.TestCase):

    def setUp(self):
        super().setUp()
        self.type = db_types.ScalarListType()

    def test_cache_ok(self):
        self.assertTrue(self.type.cache_ok)

    def test_process_bind_param_none(self):
        self.assertIsNone(self.type.process_bind_param(None, None))

    def test_process_bind_param_empty(self):
        self.assertEqual('', self.type.process_bind_param([], None))

    def test_process_bind_param_list(self):
        self.assertEqual(
            'TLSv1.2,TLSv1.3',
            self.type.process_bind_param(['TLSv1.2', 'TLSv1.3'], None)
        )

    def test_process_bind_param_separator_in_value(self):
        self.assertRaises(
            ValueError,
            self.type.process_bind_param,
            ['TLSv1.2,bad'],
            None
        )

    def test_process_result_value_none(self):
        self.assertIsNone(self.type.process_result_value(None, None))

    def test_process_result_value_empty(self):
        self.assertEqual([], self.type.process_result_value('', None))

    def test_process_result_value_string(self):
        self.assertEqual(
            ['TLSv1.2', 'TLSv1.3'],
            self.type.process_result_value('TLSv1.2,TLSv1.3', None)
        )

    def test_process_result_value_single(self):
        self.assertEqual(
            ['TLSv1.2'],
            self.type.process_result_value('TLSv1.2', None)
        )

    def test_custom_separator(self):
        custom_type = db_types.ScalarListType(separator=';')
        self.assertEqual(
            'a;b',
            custom_type.process_bind_param(['a', 'b'], None)
        )
        self.assertEqual(
            ['a', 'b'],
            custom_type.process_result_value('a;b', None)
        )
        self.assertRaises(
            ValueError,
            custom_type.process_bind_param,
            ['a;b'],
            None
        )
