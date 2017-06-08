#    Copyright 2015
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

from oslotest import base

from octavia.hacking import checks


class HackingTestCase(base.BaseTestCase):
    """Hacking test class.

    This class tests the hacking checks in octavia.hacking.checks by passing
    strings to the check methods like the pep8/flake8 parser would. The parser
    loops over each line in the file and then passes the parameters to the
    check method. The parameter names in the check method dictate what type of
    object is passed to the check method. The parameter types are::

        logical_line: A processed line with the following modifications:
            - Multi-line statements converted to a single line.
            - Stripped left and right.
            - Contents of strings replaced with "xxx" of same length.
            - Comments removed.
        physical_line: Raw line of text from the input file.
        lines: a list of the raw lines from the input file
        tokens: the tokens that contribute to this logical line
        line_number: line number in the input file
        total_lines: number of lines in the input file
        blank_lines: blank lines before this one
        indent_char: indentation character in this file (" " or "\t")
        indent_level: indentation (with tabs expanded to multiples of 8)
        previous_indent_level: indentation on previous line
        previous_logical: previous logical line
        filename: Path of the file being run through pep8

    When running a test on a check method the return will be False/None if
    there is no violation in the sample input. If there is an error a tuple is
    returned with a position in the line, and a message. So to check the result
    just assertTrue if the check is expected to fail and assertFalse if it
    should pass.
    """

    def test_assert_true_instance(self):
        self.assertEqual(1, len(list(checks.assert_true_instance(
            "self.assertTrue(isinstance(e, "
            "exception.BuildAbortException))"))))

        self.assertEqual(0, len(list(checks.assert_true_instance(
            "self.assertTrue()"))))

    def test_assert_equal_or_not_none(self):
        self.assertEqual(1, len(list(checks.assert_equal_or_not_none(
            "self.assertEqual(A, None)"))))

        self.assertEqual(1, len(list(checks.assert_equal_or_not_none(
            "self.assertEqual(None, A)"))))

        self.assertEqual(1, len(list(checks.assert_equal_or_not_none(
            "self.assertNotEqual(A, None)"))))

        self.assertEqual(1, len(list(checks.assert_equal_or_not_none(
            "self.assertNotEqual(None, A)"))))

        self.assertEqual(0,
                         len(list(checks.assert_equal_or_not_none(
                             "self.assertIsNone()"))))

        self.assertEqual(0,
                         len(list(checks.assert_equal_or_not_none(
                             "self.assertIsNotNone()"))))

    def test_assert_equal_in(self):
        self.assertEqual(1, len(list(checks.assert_equal_in(
            "self.assertEqual(a in b, True)"))))

        self.assertEqual(1, len(list(checks.assert_equal_in(
            "self.assertEqual('str' in 'string', True)"))))

        self.assertEqual(0, len(list(checks.assert_equal_in(
            "self.assertEqual(any(a==1 for a in b), True)"))))

        self.assertEqual(1, len(list(checks.assert_equal_in(
            "self.assertEqual(True, a in b)"))))

        self.assertEqual(1, len(list(checks.assert_equal_in(
            "self.assertEqual(True, 'str' in 'string')"))))

        self.assertEqual(0, len(list(checks.assert_equal_in(
            "self.assertEqual(True, any(a==1 for a in b))"))))

        self.assertEqual(1, len(list(checks.assert_equal_in(
            "self.assertEqual(a in b, False)"))))

        self.assertEqual(1, len(list(checks.assert_equal_in(
            "self.assertEqual('str' in 'string', False)"))))

        self.assertEqual(0, len(list(checks.assert_equal_in(
            "self.assertEqual(any(a==1 for a in b), False)"))))

        self.assertEqual(1, len(list(checks.assert_equal_in(
            "self.assertEqual(False, a in b)"))))

        self.assertEqual(1, len(list(checks.assert_equal_in(
            "self.assertEqual(False, 'str' in 'string')"))))

        self.assertEqual(0, len(list(checks.assert_equal_in(
            "self.assertEqual(False, any(a==1 for a in b))"))))

    def test_assert_equal_true_or_false(self):
        self.assertEqual(1, len(list(checks.assert_equal_true_or_false(
            "self.assertEqual(True, A)"))))

        self.assertEqual(1, len(list(checks.assert_equal_true_or_false(
            "self.assertEqual(False, A)"))))

        self.assertEqual(0, len(list(checks.assert_equal_true_or_false(
            "self.assertTrue()"))))

        self.assertEqual(0, len(list(checks.assert_equal_true_or_false(
            "self.assertFalse()"))))

    def test_no_log_warn(self):
        self.assertEqual(1, len(list(checks.no_log_warn(
            "LOG.warn()"))))

        self.assertEqual(0, len(list(checks.no_log_warn(
            "LOG.warning()"))))

    def test_no_xrange(self):
        self.assertEqual(1, len(list(checks.no_xrange(
            "xrange(45)"))))

        self.assertEqual(0, len(list(checks.no_xrange(
            "range(45)"))))

    def test_line_continuation_no_backslash(self):
        results = list(checks.check_line_continuation_no_backslash(
            '', [(1, 'import', (2, 0), (2, 6), 'import \\\n'),
                 (1, 'os', (3, 4), (3, 6), '    os\n')]))
        self.assertEqual(1, len(results))
        self.assertEqual((2, 7), results[0][0])
