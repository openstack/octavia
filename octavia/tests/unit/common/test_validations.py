# Copyright 2016 Blue Box, an IBM Company
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

import octavia.common.exceptions as exceptions
import octavia.common.validate as validate
import octavia.tests.unit.base as base


class TestValidations(base.TestCase):
    # Note that particularly complex validation testing is handled via
    # functional tests elsewhere (ex. repository tests)

    def test_validate_url(self):
        ret = validate.url('http://example.com')
        self.assertTrue(ret)

    def test_validate_bad_url(self):
        self.assertRaises(exceptions.InvalidURL, validate.url, 'bad url')

    def test_validate_header_name(self):
        ret = validate.header_name('Some-header')
        self.assertTrue(ret)

    def test_validate_bad_header_name(self):
        self.assertRaises(exceptions.InvalidString,
                          validate.cookie_value_string,
                          'bad header')

    def test_validate_cookie_value_string(self):
        ret = validate.cookie_value_string('some-cookie')
        self.assertTrue(ret)

    def test_validate_bad_cookie_value_string(self):
        self.assertRaises(exceptions.InvalidString,
                          validate.cookie_value_string,
                          'bad cookie value;')

    def test_validate_header_value_string(self):
        ret = validate.header_value_string('some-value')
        self.assertTrue(ret)

    def test_validate_header_value_string_quoted(self):
        ret = validate.header_value_string('"some value"')
        self.assertTrue(ret)

    def test_validate_bad_header_value_string(self):
        self.assertRaises(exceptions.InvalidString,
                          validate.header_value_string,
                          '\x18')

    def test_validate_regex(self):
        ret = validate.regex('some regex.*')
        self.assertTrue(ret)

    def test_validate_bad_regex(self):
        self.assertRaises(exceptions.InvalidRegex, validate.regex,
                          'bad regex\\')
