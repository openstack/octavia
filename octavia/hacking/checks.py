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

import re

from hacking import core


_all_log_levels = {'critical', 'error', 'exception', 'info', 'warning'}
_all_hints = {'_LC', '_LE', '_LI', '_', '_LW'}

_log_translation_hint = re.compile(
    r".*LOG\.({levels})\(\s*({hints})\(".format(
        levels='|'.join(_all_log_levels),
        hints='|'.join(_all_hints),
    ))

assert_equal_with_true_re = re.compile(
    r"assertEqual\(True,")
assert_equal_with_false_re = re.compile(
    r"assertEqual\(False,")
mutable_default_args = re.compile(r"^\s*def .+\((.+=\{\}|.+=\[\])")
revert_must_have_kwargs_re = re.compile(
    r'[ ]*def revert\(.+,[ ](?!\*\*kwargs)\w+\):')
untranslated_exception_re = re.compile(r"raise (?:\w*)\((.*)\)")
no_eventlet_re = re.compile(r'(import|from)\s+[(]?eventlet')
no_line_continuation_backslash_re = re.compile(r'.*(\\)\n')
no_logging_re = re.compile(r'(import|from)\s+[(]?logging')


def _translation_checks_not_enforced(filename):
    # Do not do these validations on tests
    return any(pat in filename for pat in ["/tests/", "rally-jobs/plugins/"])


@core.flake8ext
def assert_equal_true_or_false(logical_line):
    """Check for assertEqual(True, A) or assertEqual(False, A) sentences

    O323
    """
    res = (assert_equal_with_true_re.search(logical_line) or
           assert_equal_with_false_re.search(logical_line))
    if res:
        yield (0, "O323: assertEqual(True, A) or assertEqual(False, A) "
               "sentences not allowed")


@core.flake8ext
def no_mutable_default_args(logical_line):
    msg = "O324: Method's default argument shouldn't be mutable!"
    if mutable_default_args.match(logical_line):
        yield (0, msg)


@core.flake8ext
def no_log_warn(logical_line):
    """Disallow 'LOG.warn('

    O339
    """
    if logical_line.startswith('LOG.warn('):
        yield (0, "O339:Use LOG.warning() rather than LOG.warn()")


@core.flake8ext
def no_translate_logs(logical_line, filename):
    """O341 - Don't translate logs.

    Check for 'LOG.*(_(' and 'LOG.*(_Lx('

    Translators don't provide translations for log messages, and operators
    asked not to translate them.

    * This check assumes that 'LOG' is a logger.

    :param logical_line: The logical line to check.
    :param filename: The file name where the logical line exists.
    :returns: None if the logical line passes the check, otherwise a tuple
              is yielded that contains the offending index in logical line
              and a message describe the check validation failure.
    """
    if _translation_checks_not_enforced(filename):
        return

    msg = "O341: Log messages should not be translated!"
    match = _log_translation_hint.match(logical_line)
    if match:
        yield (logical_line.index(match.group()), msg)


@core.flake8ext
def check_raised_localized_exceptions(logical_line, filename):
    """O342 - Untranslated exception message.

    :param logical_line: The logical line to check.
    :param filename: The file name where the logical line exists.
    :returns: None if the logical line passes the check, otherwise a tuple
              is yielded that contains the offending index in logical line
              and a message describe the check validation failure.
    """
    if _translation_checks_not_enforced(filename):
        return

    logical_line = logical_line.strip()
    raised_search = untranslated_exception_re.match(logical_line)
    if raised_search:
        exception_msg = raised_search.groups()[0]
        if exception_msg.startswith("\"") or exception_msg.startswith("\'"):
            msg = "O342: Untranslated exception message."
            yield (logical_line.index(exception_msg), msg)


@core.flake8ext
def check_no_eventlet_imports(logical_line):
    """O345 - Usage of Python eventlet module not allowed.

    :param logical_line: The logical line to check.
    :returns: None if the logical line passes the check, otherwise a tuple
              is yielded that contains the offending index in logical line
              and a message describe the check validation failure.
    """
    if no_eventlet_re.match(logical_line):
        msg = 'O345 Usage of Python eventlet module not allowed'
        yield logical_line.index('eventlet'), msg


@core.flake8ext
def check_line_continuation_no_backslash(logical_line, tokens):
    """O346 - Don't use backslashes for line continuation.

    :param logical_line: The logical line to check. Not actually used.
    :param tokens: List of tokens to check.
    :returns: None if the tokens don't contain any issues, otherwise a tuple
              is yielded that contains the offending index in the logical
              line and a message describe the check validation failure.
    """
    backslash = None
    for token_type, text, start, end, orig_line in tokens:
        m = no_line_continuation_backslash_re.match(orig_line)
        if m:
            backslash = (start[0], m.start(1))
            break

    if backslash is not None:
        msg = 'O346 Backslash line continuations not allowed'
        yield backslash, msg


@core.flake8ext
def revert_must_have_kwargs(logical_line):
    """O347 - Taskflow revert methods must have \\*\\*kwargs.

    :param logical_line: The logical line to check.
    :returns: None if the logical line passes the check, otherwise a tuple
              is yielded that contains the offending index in logical line
              and a message describe the check validation failure.
    """
    if revert_must_have_kwargs_re.match(logical_line):
        msg = 'O347 Taskflow revert methods must have **kwargs'
        yield 0, msg


@core.flake8ext
def check_no_logging_imports(logical_line):
    """O348 - Usage of Python logging module not allowed.

    :param logical_line: The logical line to check.
    :returns: None if the logical line passes the check, otherwise a tuple
              is yielded that contains the offending index in logical line
              and a message describe the check validation failure.
    """
    if no_logging_re.match(logical_line):
        msg = 'O348 Usage of Python logging module not allowed, use oslo_log'
        yield logical_line.index('logging'), msg
