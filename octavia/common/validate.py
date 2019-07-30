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


import ipaddress
import re

import netaddr
from oslo_config import cfg
import rfc3986
import six
from wsme import types as wtypes

from octavia.common import constants
from octavia.common import exceptions
from octavia.common import utils
from octavia.i18n import _

CONF = cfg.CONF


def url(url, require_scheme=True):
    """Raises an error if the url doesn't look like a URL."""
    try:
        if not rfc3986.is_valid_uri(url, require_scheme=require_scheme):
            raise exceptions.InvalidURL(url=url)
        p_url = rfc3986.urlparse(rfc3986.normalize_uri(url))
        if require_scheme:
            if p_url.scheme != 'http' and p_url.scheme != 'https':
                raise exceptions.InvalidURL(url=url)
    except Exception:
        raise exceptions.InvalidURL(url=url)
    return True


def url_path(url_path):
    """Raises an error if the url_path doesn't look like a URL Path."""
    try:
        p_url = rfc3986.urlparse(rfc3986.normalize_uri(url_path))

        invalid_path = (
            p_url.scheme or p_url.userinfo or p_url.host or
            p_url.port or
            p_url.path is None or
            not p_url.path.startswith('/')
        )

        if invalid_path:
            raise exceptions.InvalidURLPath(url_path=url_path)
    except Exception:
        raise exceptions.InvalidURLPath(url_path=url_path)
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
    if not l7rule.value:
        raise exceptions.InvalidL7Rule(msg=_('L7 rule type requires a value'))
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

    elif l7rule.type in [constants.L7RULE_TYPE_SSL_CONN_HAS_CERT,
                         constants.L7RULE_TYPE_SSL_VERIFY_RESULT,
                         constants.L7RULE_TYPE_SSL_DN_FIELD]:
        validate_l7rule_ssl_types(l7rule)

    else:
        raise exceptions.InvalidL7Rule(msg='invalid rule type')
    return True


def validate_l7rule_ssl_types(l7rule):
    if not l7rule.type or l7rule.type not in [
       constants.L7RULE_TYPE_SSL_CONN_HAS_CERT,
       constants.L7RULE_TYPE_SSL_VERIFY_RESULT,
       constants.L7RULE_TYPE_SSL_DN_FIELD]:
        return

    rule_type = None if l7rule.type == wtypes.Unset else l7rule.type
    req_key = None if l7rule.key == wtypes.Unset else l7rule.key
    req_value = None if l7rule.value == wtypes.Unset else l7rule.value
    compare_type = (None if l7rule.compare_type == wtypes.Unset else
                    l7rule.compare_type)
    msg = None
    if rule_type == constants.L7RULE_TYPE_SSL_CONN_HAS_CERT:
        # key and value are not allowed
        if req_key:
            # log error or raise
            msg = 'L7rule type {0} does not use the "key" field.'.format(
                rule_type)
        elif req_value.lower() != 'true':
            msg = 'L7rule value {0} is not a boolean True string.'.format(
                req_value)
        elif compare_type != constants.L7RULE_COMPARE_TYPE_EQUAL_TO:
            msg = 'L7rule type {0} only supports the {1} compare type.'.format(
                rule_type, constants.L7RULE_COMPARE_TYPE_EQUAL_TO)

    if rule_type == constants.L7RULE_TYPE_SSL_VERIFY_RESULT:
        if req_key:
            # log or raise req_key not used
            msg = 'L7rule type {0} does not use the "key" field.'.format(
                rule_type)
        elif not req_value.isdigit() or int(req_value) < 0:
            # log or raise req_value must be int
            msg = 'L7rule type {0} needs a int value, which is >= 0'.format(
                rule_type)
        elif compare_type != constants.L7RULE_COMPARE_TYPE_EQUAL_TO:
            msg = 'L7rule type {0} only supports the {1} compare type.'.format(
                rule_type, constants.L7RULE_COMPARE_TYPE_EQUAL_TO)

    if rule_type == constants.L7RULE_TYPE_SSL_DN_FIELD:
        dn_regex = re.compile(constants.DISTINGUISHED_NAME_FIELD_REGEX)
        if compare_type == constants.L7RULE_COMPARE_TYPE_REGEX:
            regex(l7rule.value)

        if not req_key or not req_value:
            # log or raise key and value must be specified.
            msg = 'L7rule type {0} needs to specify a key and a value.'.format(
                rule_type)
        # log or raise the key must be splited by '-'
        elif not dn_regex.match(req_key):
            msg = ('Invalid L7rule distinguished name field.')

    if msg:
        raise exceptions.InvalidL7Rule(msg=msg)


def sanitize_l7policy_api_args(l7policy, create=False):
    """Validate and make consistent L7Policy API arguments.

    This method is mainly meant to sanitize L7 Policy create and update
    API dictionaries, so that we strip 'None' values that don't apply for
    our particular update. This method does *not* verify that any
    redirect_pool_id exists in the database, but will raise an
    error if a redirect_url doesn't look like a URL.

    :param l7policy: The L7 Policy dictionary we are santizing / validating
    """
    if 'action' in l7policy.keys():
        if l7policy['action'] == constants.L7POLICY_ACTION_REJECT:
            l7policy.update({'redirect_url': None})
            l7policy.update({'redirect_pool_id': None})
            l7policy.pop('redirect_pool', None)
        elif l7policy['action'] == constants.L7POLICY_ACTION_REDIRECT_TO_URL:
            if not l7policy.get('redirect_url'):
                raise exceptions.InvalidL7PolicyArgs(
                    msg='redirect_url must not be None')
            l7policy.update({'redirect_pool_id': None})
            l7policy.pop('redirect_pool', None)
        elif l7policy['action'] == constants.L7POLICY_ACTION_REDIRECT_TO_POOL:
            if (not l7policy.get('redirect_pool_id') and
                    not l7policy.get('redirect_pool')):
                raise exceptions.InvalidL7PolicyArgs(
                    msg='redirect_pool_id or redirect_pool must not be None')
            l7policy.update({'redirect_url': None})
        elif l7policy['action'] == constants.L7POLICY_ACTION_REDIRECT_PREFIX:
            if not l7policy.get('redirect_prefix'):
                raise exceptions.InvalidL7PolicyArgs(
                    msg='redirect_prefix must not be None')
        else:
            raise exceptions.InvalidL7PolicyAction(
                action=l7policy['action'])
    if ((l7policy.get('redirect_pool_id') or l7policy.get('redirect_pool')) and
            (l7policy.get('redirect_url') or l7policy.get('redirect_prefix'))):
        raise exceptions.InvalidL7PolicyArgs(
            msg='Cannot specify redirect_pool_id and redirect_url or '
                'redirect_prefix at the same time')
    if l7policy.get('redirect_pool_id'):
        l7policy.update({
            'action': constants.L7POLICY_ACTION_REDIRECT_TO_POOL})
        l7policy.update({'redirect_url': None})
        l7policy.pop('redirect_pool', None)
        l7policy.update({'redirect_prefix': None})
        l7policy.update({'redirect_http_code': None})
    if l7policy.get('redirect_pool'):
        l7policy.update({
            'action': constants.L7POLICY_ACTION_REDIRECT_TO_POOL})
        l7policy.update({'redirect_url': None})
        l7policy.pop('redirect_pool_id', None)
        l7policy.update({'redirect_prefix': None})
        l7policy.update({'redirect_http_code': None})
    if l7policy.get('redirect_url'):
        url(l7policy['redirect_url'])
        l7policy.update({
            'action': constants.L7POLICY_ACTION_REDIRECT_TO_URL})
        l7policy.update({'redirect_pool_id': None})
        l7policy.update({'redirect_prefix': None})
        l7policy.pop('redirect_pool', None)
        if not l7policy.get('redirect_http_code'):
            l7policy.update({'redirect_http_code': 302})
    if l7policy.get('redirect_prefix'):
        url(l7policy['redirect_prefix'])
        l7policy.update({
            'action': constants.L7POLICY_ACTION_REDIRECT_PREFIX})
        l7policy.update({'redirect_pool_id': None})
        l7policy.update({'redirect_url': None})
        l7policy.pop('redirect_pool', None)
        if not l7policy.get('redirect_http_code'):
            l7policy.update({'redirect_http_code': 302})

    # If we are creating, we need an action at this point
    if create and 'action' not in l7policy.keys():
        raise exceptions.InvalidL7PolicyAction(action='None')

    # See if we have anything left after that...
    if not l7policy.keys():
        raise exceptions.InvalidL7PolicyArgs(msg='Invalid update options')
    return l7policy


def port_exists(port_id):
    """Raises an exception when a port does not exist."""
    network_driver = utils.get_network_driver()
    try:
        port = network_driver.get_port(port_id)
    except Exception:
        raise exceptions.InvalidSubresource(resource='Port', id=port_id)
    return port


def check_port_in_use(port):
    """Raise an exception when a port is used."""
    if port.device_id:
        raise exceptions.ValidationException(detail=_(
            "Port %(port_id)s is already used by device %(device_id)s ") %
            {'port_id': port.id, 'device_id': port.device_id})
    return False


def subnet_exists(subnet_id):
    """Raises an exception when a subnet does not exist."""
    network_driver = utils.get_network_driver()
    try:
        subnet = network_driver.get_subnet(subnet_id)
    except Exception:
        raise exceptions.InvalidSubresource(resource='Subnet', id=subnet_id)
    return subnet


def qos_policy_exists(qos_policy_id):
    network_driver = utils.get_network_driver()
    qos_extension_enabled(network_driver)
    try:
        qos_policy = network_driver.get_qos_policy(qos_policy_id)
    except Exception:
        raise exceptions.InvalidSubresource(resource='qos_policy',
                                            id=qos_policy_id)
    return qos_policy


def qos_extension_enabled(network_driver):
    if not network_driver.qos_enabled():
        raise exceptions.ValidationException(detail=_(
            "VIP QoS policy is not allowed in this deployment."))


def network_exists_optionally_contains_subnet(network_id, subnet_id=None):
    """Raises an exception when a network does not exist.

    If a subnet is provided, also validate the network contains that subnet.
    """
    network_driver = utils.get_network_driver()
    try:
        network = network_driver.get_network(network_id)
    except Exception:
        raise exceptions.InvalidSubresource(resource='Network', id=network_id)
    if subnet_id:
        if not network.subnets or subnet_id not in network.subnets:
            raise exceptions.InvalidSubresource(resource='Subnet',
                                                id=subnet_id)
    return network


def network_allowed_by_config(network_id):
    if CONF.networking.valid_vip_networks:
        valid_networks = map(str.lower, CONF.networking.valid_vip_networks)
        if network_id not in valid_networks:
            raise exceptions.ValidationException(detail=_(
                'Supplied VIP network_id is not allowed by the configuration '
                'of this deployment.'))


def is_ip_member_of_cidr(address, cidr):
    if netaddr.IPAddress(address) in netaddr.IPNetwork(cidr):
        return True
    return False


def check_session_persistence(SP_dict):
    try:
        if SP_dict['cookie_name']:
            if SP_dict['type'] != constants.SESSION_PERSISTENCE_APP_COOKIE:
                raise exceptions.ValidationException(detail=_(
                    'Field "cookie_name" can only be specified with session '
                    'persistence of type "APP_COOKIE".'))
            bad_cookie_name = re.compile(r'[\x00-\x20\x22\x28-\x29\x2c\x2f'
                                         r'\x3a-\x40\x5b-\x5d\x7b\x7d\x7f]+')
            valid_chars = re.compile(r'[\x00-\xff]+')
            if (bad_cookie_name.search(SP_dict['cookie_name']) or
                    not valid_chars.search(SP_dict['cookie_name'])):
                raise exceptions.ValidationException(detail=_(
                    'Supplied "cookie_name" is invalid.'))
        if (SP_dict['type'] == constants.SESSION_PERSISTENCE_APP_COOKIE and
                not SP_dict['cookie_name']):
            raise exceptions.ValidationException(detail=_(
                'Field "cookie_name" must be specified when using the '
                '"APP_COOKIE" session persistence type.'))
    except exceptions.ValidationException:
        raise
    except Exception:
        raise exceptions.ValidationException(detail=_(
            'Invalid session_persistence provided.'))


def ip_not_reserved(ip_address):
    ip_address = (
        ipaddress.ip_address(six.text_type(ip_address)).exploded.upper())
    if ip_address in CONF.networking.reserved_ips:
        raise exceptions.InvalidOption(value=ip_address,
                                       option='member address')


def is_flavor_spares_compatible(flavor):
    if flavor:
        # If a compute flavor is specified, the flavor is not spares compatible
        if flavor.get(constants.COMPUTE_FLAVOR, None):
            return False
    return True
