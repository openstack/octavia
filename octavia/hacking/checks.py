# Copyright (c) 2014 OpenStack Foundation.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import re

import pep8
import six

"""
Guidelines for writing new hacking checks

 - Use only for Octavia specific tests. OpenStack general tests
   should be submitted to the common 'hacking' module.
 - Pick numbers in the range O3xx. Find the current test with
   the highest allocated number and then pick the next value.
 - Keep the test method code in the source file ordered based
   on the O3xx value.
 - List the new rule in the top level HACKING.rst file
 - Add test cases for each new rule to
   octavia/tests/unit/test_hacking.py

"""

log_translation = re.compile(
    r"(.)*LOG\.(audit|error|info|warn|warning|critical|exception)\(\s*('|\")")
author_tag_re = (re.compile("^\s*#\s*@?(a|A)uthor"),
                 re.compile("^\.\.\s+moduleauthor::"))
_all_hints = set(['_', '_LI', '_LE', '_LW', '_LC'])
_all_log_levels = {
    # NOTE(yamamoto): Following nova which uses _() for audit.
    'audit': '_',
    'error': '_LE',
    'info': '_LI',
    'warn': '_LW',
    'warning': '_LW',
    'critical': '_LC',
    'exception': '_LE',
}
log_translation_hints = []
for level, hint in six.iteritems(_all_log_levels):
    r = "(.)*LOG\.%(level)s\(\s*((%(wrong_hints)s)\(|'|\")" % {
        'level': level,
        'wrong_hints': '|'.join(_all_hints - set([hint])),
    }
    log_translation_hints.append(re.compile(r))

assert_trueinst_re = re.compile(
    r"(.)*assertTrue\(isinstance\((\w|\.|\'|\"|\[|\])+, "
    "(\w|\.|\'|\"|\[|\])+\)\)")
assert_equal_in_end_with_true_or_false_re = re.compile(
    r"assertEqual\((\w|[][.'\"])+ in (\w|[][.'\", ])+, (True|False)\)")
assert_equal_in_start_with_true_or_false_re = re.compile(
    r"assertEqual\((True|False), (\w|[][.'\"])+ in (\w|[][.'\", ])+\)")
assert_equal_with_true_re = re.compile(
    r"assertEqual\(True,")
assert_equal_with_false_re = re.compile(
    r"assertEqual\(False,")
mutable_default_args = re.compile(r"^\s*def .+\((.+=\{\}|.+=\[\])")
assert_equal_end_with_none_re = re.compile(r"(.)*assertEqual\(.+, None\)")
assert_equal_start_with_none_re = re.compile(r".*assertEqual\(None, .+\)")
assert_not_equal_end_with_none_re = re.compile(
    r"(.)*assertNotEqual\(.+, None\)")
assert_not_equal_start_with_none_re = re.compile(
    r"(.)*assertNotEqual\(None, .+\)")
assert_no_xrange_re = re.compile(
    r"\s*xrange\s*\(")


def _directory_to_check_translation(filename):
    return True


def assert_true_instance(logical_line):
    """Check for assertTrue(isinstance(a, b)) sentences

    O316
    """
    if assert_trueinst_re.match(logical_line):
        yield (0, "O316: assertTrue(isinstance(a, b)) sentences not allowed")


def assert_equal_or_not_none(logical_line):
    """Check for assertEqual(A, None) or assertEqual(None, A) sentences,

    assertNotEqual(A, None) or assertNotEqual(None, A) sentences

    O318
    """
    msg = ("O318: assertEqual/assertNotEqual(A, None) or "
           "assertEqual/assertNotEqual(None, A) sentences not allowed")
    res = (assert_equal_start_with_none_re.match(logical_line) or
           assert_equal_end_with_none_re.match(logical_line) or
           assert_not_equal_start_with_none_re.match(logical_line) or
           assert_not_equal_end_with_none_re.match(logical_line))
    if res:
        yield (0, msg)


def no_translate_debug_logs(logical_line, filename):
    """Check for 'LOG.debug(_('

    As per our translation policy,
    https://wiki.openstack.org/wiki/LoggingStandards#Log_Translation
    we shouldn't translate debug level logs.

    * This check assumes that 'LOG' is a logger.
    O319
    """
    if _directory_to_check_translation(filename) and logical_line.startswith(
            "LOG.debug(_("):
        yield(0, "O319 Don't translate debug level logs")


def validate_log_translations(logical_line, physical_line, filename):
    # Translations are not required in the test directory
    if "octavia/tests" in filename:
        return
    if pep8.noqa(physical_line):
        return
    msg = "O320: Log messages require translations!"
    if log_translation.match(logical_line):
        yield (0, msg)

    if _directory_to_check_translation(filename):
        msg = "O320: Log messages require translation hints!"
        for log_translation_hint in log_translation_hints:
            if log_translation_hint.match(logical_line):
                yield (0, msg)


def use_jsonutils(logical_line, filename):
    msg = "O321: jsonutils.%(fun)s must be used instead of json.%(fun)s"

    # Some files in the tree are not meant to be run from inside Octavia
    # itself, so we should not complain about them not using jsonutils
    json_check_skipped_patterns = [
    ]

    for pattern in json_check_skipped_patterns:
        if pattern in filename:
            return

    if "json." in logical_line:
        json_funcs = ['dumps(', 'dump(', 'loads(', 'load(']
        for f in json_funcs:
            pos = logical_line.find('json.%s' % f)
            if pos != -1:
                yield (pos, msg % {'fun': f[:-1]})


def no_author_tags(physical_line):
    for regex in author_tag_re:
        if regex.match(physical_line):
            physical_line = physical_line.lower()
            pos = physical_line.find('moduleauthor')
            if pos < 0:
                pos = physical_line.find('author')
            return pos, "O322: Don't use author tags"


def assert_equal_true_or_false(logical_line):
    """Check for assertEqual(True, A) or assertEqual(False, A) sentences

    O323
    """
    res = (assert_equal_with_true_re.search(logical_line) or
           assert_equal_with_false_re.search(logical_line))
    if res:
        yield (0, "O323: assertEqual(True, A) or assertEqual(False, A) "
               "sentences not allowed")


def no_mutable_default_args(logical_line):
    msg = "O324: Method's default argument shouldn't be mutable!"
    if mutable_default_args.match(logical_line):
        yield (0, msg)


def assert_equal_in(logical_line):
    """Check for assertEqual(A in B, True), assertEqual(True, A in B),

    assertEqual(A in B, False) or assertEqual(False, A in B) sentences

    O338
    """
    res = (assert_equal_in_start_with_true_or_false_re.search(logical_line) or
           assert_equal_in_end_with_true_or_false_re.search(logical_line))
    if res:
        yield (0, "O338: Use assertIn/NotIn(A, B) rather than "
               "assertEqual(A in B, True/False) when checking collection "
               "contents.")


def no_log_warn(logical_line):
    """Disallow 'LOG.warn('

    O339
    """
    if logical_line.startswith('LOG.warn('):
        yield(0, "O339:Use LOG.warning() rather than LOG.warn()")


def no_xrange(logical_line):
    """Disallow 'xrange()'

    O340
    """
    if assert_no_xrange_re.match(logical_line):
        yield(0, "O340: Do not use xrange().")


def factory(register):
    register(assert_true_instance)
    register(assert_equal_or_not_none)
    register(no_translate_debug_logs)
    register(validate_log_translations)
    register(use_jsonutils)
    register(no_author_tags)
    register(assert_equal_true_or_false)
    register(no_mutable_default_args)
    register(assert_equal_in)
    register(no_log_warn)
    register(no_xrange)
