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

import testtools

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

    def assertLinePasses(self, func, *args):
        with testtools.ExpectedException(StopIteration):
            next(func(*args))

    def assertLineFails(self, func, *args):
        self.assertIsInstance(next(func(*args)), tuple)

    def _get_factory_checks(self, factory):
        check_fns = []

        def _reg(check_fn):
            self.assertTrue(hasattr(check_fn, '__call__'))
            self.assertFalse(check_fn in check_fns)
            check_fns.append(check_fn)

        factory(_reg)
        return check_fns

    def test_factory(self):
        self.assertGreater(len(self._get_factory_checks(checks.factory)), 0)

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

    def test_no_mutable_default_args(self):
        self.assertEqual(0, len(list(checks.no_mutable_default_args(
            "def foo (bar):"))))
        self.assertEqual(1, len(list(checks.no_mutable_default_args(
            "def foo (bar=[]):"))))
        self.assertEqual(1, len(list(checks.no_mutable_default_args(
            "def foo (bar={}):"))))

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

    def test_no_log_translations(self):
        for log in checks._all_log_levels:
            for hint in checks._all_hints:
                bad = 'LOG.%s(%s("Bad"))' % (log, hint)
                self.assertEqual(
                    1, len(list(checks.no_translate_logs(bad, 'f'))))
                # Catch abuses when used with a variable and not a literal
                bad = 'LOG.%s(%s(msg))' % (log, hint)
                self.assertEqual(
                    1, len(list(checks.no_translate_logs(bad, 'f'))))
                # Do not do validations in tests
                ok = 'LOG.%s(_("OK - unit tests"))' % log
                self.assertEqual(
                    0, len(list(checks.no_translate_logs(ok, 'f/tests/f'))))

    def test_check_localized_exception_messages(self):
        f = checks.check_raised_localized_exceptions
        self.assertLineFails(f, "     raise KeyError('Error text')", '')
        self.assertLineFails(f, ' raise KeyError("Error text")', '')
        self.assertLinePasses(f, ' raise KeyError(_("Error text"))', '')
        self.assertLinePasses(f, ' raise KeyError(_ERR("Error text"))', '')
        self.assertLinePasses(f, " raise KeyError(translated_msg)", '')
        self.assertLinePasses(f, '# raise KeyError("Not translated")', '')
        self.assertLinePasses(f, 'print("raise KeyError("Not '
                                 'translated")")', '')

    def test_check_localized_exception_message_skip_tests(self):
        f = checks.check_raised_localized_exceptions
        self.assertLinePasses(f, "raise KeyError('Error text')",
                              'neutron_lib/tests/unit/mytest.py')

    def test_check_no_basestring(self):
        self.assertEqual(1, len(list(checks.check_no_basestring(
            "isinstance('foo', basestring)"))))

        self.assertEqual(0, len(list(checks.check_no_basestring(
            "isinstance('foo', six.string_types)"))))

    def test_dict_iteritems(self):
        self.assertEqual(1, len(list(checks.check_python3_no_iteritems(
            "obj.iteritems()"))))

        self.assertEqual(0, len(list(checks.check_python3_no_iteritems(
            "six.iteritems(obj)"))))

        self.assertEqual(0, len(list(checks.check_python3_no_iteritems(
            "obj.items()"))))

    def test_check_no_eventlet_imports(self):
        f = checks.check_no_eventlet_imports
        self.assertLinePasses(f, 'from not_eventlet import greenthread')
        self.assertLineFails(f, 'from eventlet import greenthread')
        self.assertLineFails(f, 'import eventlet')

    def test_line_continuation_no_backslash(self):
        results = list(checks.check_line_continuation_no_backslash(
            '', [(1, 'import', (2, 0), (2, 6), 'import \\\n'),
                 (1, 'os', (3, 4), (3, 6), '    os\n')]))
        self.assertEqual(1, len(results))
        self.assertEqual((2, 7), results[0][0])

    def test_check_no_logging_imports(self):
        f = checks.check_no_logging_imports
        self.assertLinePasses(f, 'from oslo_log import log')
        self.assertLineFails(f, 'from logging import log')
        self.assertLineFails(f, 'import logging')

    def test_revert_must_have_kwargs(self):
        f = checks.revert_must_have_kwargs
        self.assertLinePasses(f, 'def revert(self, *args, **kwargs):')
        self.assertLineFails(f, 'def revert(self, loadbalancer):')
