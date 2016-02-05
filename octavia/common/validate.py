# Copyright 2016 Blue Box, an IBM Company
# All Rights Reserved.
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

"""
Several handy validation functions that go beyond simple type checking.
Defined here so these can also be used at deeper levels than the API.
"""

import re


from octavia.common import constants
from octavia.common import exceptions


def url(url):
    """Raises an error if the url doesn't look like a URL."""
    p = re.compile(constants.URL_REGEX)
    if not p.match(url):
        raise exceptions.InvalidURL(url=url)
    return True


def header_name(header, what=None):
    """Raises an error if header does not look like an HTML header name."""
    p = re.compile(constants.HTTP_HEADER_NAME_REGEX)
    if not p.match(header):
        raise exceptions.InvalidString(what=what)
    return True


def cookie_value_string(value, what=None):
    """Raises an error if the value string contains invalid characters."""
    p = re.compile(constants.HTTP_COOKIE_VALUE_REGEX)
    if not p.match(value):
        raise exceptions.InvalidString(what=what)
    return True


def header_value_string(value, what=None):
    """Raises an error if the value string contains invalid characters."""
    p = re.compile(constants.HTTP_HEADER_VALUE_REGEX)
    q = re.compile(constants.HTTP_QUOTED_HEADER_VALUE_REGEX)
    if not p.match(value) and not q.match(value):
        raise exceptions.InvalidString(what=what)
    return True


def regex(regex):
    """Raises an error if the string given is not a valid regex."""
    try:
        re.compile(regex)
    except Exception as e:
        raise exceptions.InvalidRegex(e=str(e))
    return True


# Note that we can evaluate this outside the context of any L7 Policy because
# L7 rules must be internally consistent.
def l7rule_data(l7rule):
    """Raises an error if the l7rule given is invalid in some way."""
    if l7rule.type == constants.L7RULE_TYPE_HEADER:
        if not l7rule.key:
            raise exceptions.InvalidL7Rule(msg='L7 rule type requires a key')
        header_name(l7rule.key, what='key')
        if l7rule.compare_type == constants.L7RULE_COMPARE_TYPE_REGEX:
            regex(l7rule.value)
        elif l7rule.compare_type in (
                constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                constants.L7RULE_COMPARE_TYPE_ENDS_WITH,
                constants.L7RULE_COMPARE_TYPE_CONTAINS,
                constants.L7RULE_COMPARE_TYPE_EQUAL_TO):
            header_value_string(l7rule.value, what='header value')
        else:
            raise exceptions.InvalidL7Rule(msg='invalid comparison type '
                                           'for rule type')

    elif l7rule.type == constants.L7RULE_TYPE_COOKIE:
        if not l7rule.key:
            raise exceptions.InvalidL7Rule(msg='L7 rule type requires a key')
        header_name(l7rule.key, what='key')
        if l7rule.compare_type == constants.L7RULE_COMPARE_TYPE_REGEX:
            regex(l7rule.value)
        elif l7rule.compare_type in (
                constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                constants.L7RULE_COMPARE_TYPE_ENDS_WITH,
                constants.L7RULE_COMPARE_TYPE_CONTAINS,
                constants.L7RULE_COMPARE_TYPE_EQUAL_TO):
            cookie_value_string(l7rule.value, what='cookie value')
        else:
            raise exceptions.InvalidL7Rule(msg='invalid comparison type '
                                           'for rule type')

    elif l7rule.type in (constants.L7RULE_TYPE_HOST_NAME,
                         constants.L7RULE_TYPE_PATH):
        if l7rule.compare_type in (
                constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                constants.L7RULE_COMPARE_TYPE_ENDS_WITH,
                constants.L7RULE_COMPARE_TYPE_CONTAINS,
                constants.L7RULE_COMPARE_TYPE_EQUAL_TO):
            header_value_string(l7rule.value, what='comparison value')
        elif l7rule.compare_type == constants.L7RULE_COMPARE_TYPE_REGEX:
            regex(l7rule.value)
        else:
            raise exceptions.InvalidL7Rule(msg='invalid comparison type '
                                           'for rule type')

    elif l7rule.type == constants.L7RULE_TYPE_FILE_TYPE:
        if l7rule.compare_type == constants.L7RULE_COMPARE_TYPE_REGEX:
            regex(l7rule.value)
        elif l7rule.compare_type == constants.L7RULE_COMPARE_TYPE_EQUAL_TO:
            header_value_string(l7rule.value, what='comparison value')
        else:
            raise exceptions.InvalidL7Rule(msg='invalid comparison type '
                                           'for rule type')

    else:
        raise exceptions.InvalidL7Rule(msg='invalid rule type')
    return True
