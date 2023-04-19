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

from oslo_config import cfg
from rfc3986 import uri_reference
from rfc3986 import validators
from wsme import types as wtypes

from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.common import utils
from octavia.i18n import _

CONF = cfg.CONF
_ListenerPUT = 'octavia.api.v2.types.listener.ListenerPUT'


def url(url, require_scheme=True):
    """Raises an error if the url doesn't look like a URL."""
    validator = validators.Validator()
    if require_scheme:
        validator.allow_schemes('http', 'https')
        validator.require_presence_of('scheme', 'host')
        validator.check_validity_of('scheme', 'host', 'path')
    else:
        validator.check_validity_of('path')

    try:
        validator.validate(uri_reference(url))
    except Exception as e:
        raise exceptions.InvalidURL(url=url) from e
    return True


def url_path(url_path):
    """Raises an error if the url_path doesn't look like a URL Path."""
    validator = validators.Validator().check_validity_of('path')
    try:
        p_url = uri_reference(url_path)
        validator.validate(p_url)

        invalid_path = (
            re.search(r"\s", url_path) or
            p_url.scheme or p_url.userinfo or p_url.host or
            p_url.port or
            p_url.path is None or
            not p_url.path.startswith('/')
        )

        if invalid_path:
            raise exceptions.InvalidURLPath(url_path=url_path)
    except Exception as e:
        raise exceptions.InvalidURLPath(url_path=url_path) from e
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
            msg = 'Invalid L7rule distinguished name field.'

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


def port_exists(port_id, context=None):
    """Raises an exception when a port does not exist."""
    network_driver = utils.get_network_driver()
    try:
        port = network_driver.get_port(port_id, context=context)
    except Exception as e:
        raise exceptions.InvalidSubresource(resource='Port', id=port_id) from e
    return port


def check_port_in_use(port):
    """Raise an exception when a port is used."""
    if port.device_id:
        raise exceptions.ValidationException(detail=_(
            "Port %(port_id)s is already used by device %(device_id)s ") %
            {'port_id': port.id, 'device_id': port.device_id})
    return False


def subnet_exists(subnet_id, context=None):
    """Raises an exception when a subnet does not exist."""
    network_driver = utils.get_network_driver()
    try:
        subnet = network_driver.get_subnet(subnet_id, context=context)
    except Exception as e:
        raise exceptions.InvalidSubresource(
            resource='Subnet', id=subnet_id) from e
    return subnet


def qos_policy_exists(qos_policy_id):
    network_driver = utils.get_network_driver()
    qos_extension_enabled(network_driver)
    try:
        qos_policy = network_driver.get_qos_policy(qos_policy_id)
    except Exception as e:
        raise exceptions.InvalidSubresource(
            resource='qos_policy', id=qos_policy_id) from e
    return qos_policy


def qos_extension_enabled(network_driver):
    if not network_driver.qos_enabled():
        raise exceptions.ValidationException(detail=_(
            "VIP QoS policy is not allowed in this deployment."))


def network_exists_optionally_contains_subnet(network_id, subnet_id=None,
                                              context=None):
    """Raises an exception when a network does not exist.

    If a subnet is provided, also validate the network contains that subnet.
    """
    network_driver = utils.get_network_driver()
    try:
        network = network_driver.get_network(network_id, context=context)
    except Exception as e:
        raise exceptions.InvalidSubresource(
            resource='Network', id=network_id) from e
    if subnet_id:
        if not network.subnets or subnet_id not in network.subnets:
            raise exceptions.InvalidSubresource(resource='Subnet',
                                                id=subnet_id)
    return network


def network_allowed_by_config(network_id, valid_networks=None):
    if CONF.networking.valid_vip_networks and not valid_networks:
        valid_networks = CONF.networking.valid_vip_networks
    if valid_networks:
        valid_networks = map(str.lower, valid_networks)
        if network_id.lower() not in valid_networks:
            raise exceptions.ValidationException(detail=_(
                'Supplied VIP network_id is not allowed by the configuration '
                'of this deployment.'))


def is_ip_member_of_cidr(address, cidr):
    if ipaddress.ip_address(address) in ipaddress.ip_network(cidr):
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
    except Exception as e:
        raise exceptions.ValidationException(detail=_(
            'Invalid session_persistence provided.')) from e


def ip_not_reserved(ip_address):
    ip_address = (
        ipaddress.ip_address(ip_address).exploded.upper())
    if ip_address in CONF.networking.reserved_ips:
        raise exceptions.InvalidOption(value=ip_address,
                                       option='member address')


def check_cipher_prohibit_list(cipherstring):
    ciphers = cipherstring.split(':')
    prohibit_list = CONF.api_settings.tls_cipher_prohibit_list.split(':')
    rejected = []
    for cipher in ciphers:
        if cipher in prohibit_list:
            rejected.append(cipher)
    return rejected


def check_default_ciphers_prohibit_list_conflict():
    listener_rejected = check_cipher_prohibit_list(
        CONF.api_settings.default_listener_ciphers)
    if listener_rejected:
        raise exceptions.ValidationException(
            detail=_('Default listener ciphers conflict with prohibit list. '
                     'Conflicting ciphers: ' + ', '.join(listener_rejected)))

    pool_rejected = check_cipher_prohibit_list(
        CONF.api_settings.default_pool_ciphers)
    if pool_rejected:
        raise exceptions.ValidationException(
            detail=_('Default pool ciphers conflict with prohibit list. '
                     'Conflicting ciphers: ' + ', '.join(pool_rejected)))


def check_tls_version_list(versions):
    if versions == []:
        raise exceptions.ValidationException(
            detail=_('Empty TLS version list. Either specify at least one TLS '
                     'version or remove this parameter to use the default.'))

    # Unset action
    if versions is None:
        return

    invalid_versions = [v for v in versions
                        if v not in constants.TLS_ALL_VERSIONS]
    if invalid_versions:
        raise exceptions.ValidationException(
            detail=_('Invalid TLS versions: ' + ', '.join(invalid_versions)))


def check_tls_version_min(versions, message=None):
    """Checks a TLS version string against the configured minimum."""

    if not CONF.api_settings.minimum_tls_version:
        return

    if not message:
        message = _("Requested TLS versions are less than the minimum: ")

    min_ver_index = constants.TLS_ALL_VERSIONS.index(
        CONF.api_settings.minimum_tls_version)

    rejected = []
    for ver in versions:
        if constants.TLS_ALL_VERSIONS.index(ver) < min_ver_index:
            rejected.append(ver)
    if rejected:
        raise exceptions.ValidationException(detail=(
            message + ', '.join(rejected) + " < " +
            CONF.api_settings.minimum_tls_version))


def check_default_tls_versions_min_conflict():
    if not CONF.api_settings.minimum_tls_version:
        return

    listener_message = _("Default listener TLS versions are less than the "
                         "minimum: ")
    pool_message = _("Default pool TLS versions are less than the minimum: ")

    check_tls_version_min(CONF.api_settings.default_listener_tls_versions,
                          message=listener_message)

    check_tls_version_min(CONF.api_settings.default_pool_tls_versions,
                          message=pool_message)


def check_alpn_protocols(protocols):
    if protocols == []:
        raise exceptions.ValidationException(
            detail=_('Empty ALPN protocol list. Either specify at least one '
                     'ALPN protocol or remove this parameter to use the '
                     'default.'))

    # Unset action
    if protocols is None:
        return

    invalid_protocols = [p for p in protocols
                         if p not in constants.SUPPORTED_ALPN_PROTOCOLS]
    if invalid_protocols:
        raise exceptions.ValidationException(
            detail=_('Invalid ALPN protocol: ' + ', '.join(invalid_protocols)))


def check_hsts_options(listener: dict):
    if ((listener.get('hsts_include_subdomains') or
         listener.get('hsts_preload')) and
            not isinstance(listener.get('hsts_max_age'), int)):
        raise exceptions.ValidationException(
            detail=_('HSTS configuration options hsts_include_subdomains and '
                     'hsts_preload only make sense if hsts_max_age is '
                     'set as well.'))

    if (isinstance(listener.get('hsts_max_age'), int) and
            listener['protocol'] != constants.PROTOCOL_TERMINATED_HTTPS):
        raise exceptions.ValidationException(
            detail=_('The HSTS feature can only be used for listeners using '
                     'the TERMINATED_HTTPS protocol.'))


def check_hsts_options_put(listener: _ListenerPUT,
                           db_listener: data_models.Listener):
    hsts_disabled = all(obj.hsts_max_age in [None, wtypes.Unset] for obj
                        in (db_listener, listener))
    if ((listener.hsts_include_subdomains or listener.hsts_preload) and
            hsts_disabled):
        raise exceptions.ValidationException(
            detail=_('Cannot enable hsts_include_subdomains or hsts_preload '
                     'if hsts_max_age was not set as well.'))

    if (isinstance(listener.hsts_max_age, int) and
            db_listener.protocol != constants.PROTOCOL_TERMINATED_HTTPS):
        raise exceptions.ValidationException(
            detail=_('The HSTS feature can only be used for listeners using '
                     'the TERMINATED_HTTPS protocol.'))
