#    Copyright 2016 Rackspace
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

from oslo_config import cfg
from oslo_utils import uuidutils

from octavia.api.v2.types import l7rule
from octavia.common import constants
from octavia.common import exceptions
from octavia.common import validate

CONF = cfg.CONF


def create_load_balancer(lb_dict):
    if not lb_dict.get('id'):
        lb_dict['id'] = uuidutils.generate_uuid()
    if lb_dict.get('vip'):
        lb_dict['vip']['load_balancer_id'] = lb_dict.get('id')
    lb_dict[constants.PROVISIONING_STATUS] = constants.PENDING_CREATE
    lb_dict[constants.OPERATING_STATUS] = constants.OFFLINE

    # Set defaults later possibly overridden by flavors later
    lb_dict['topology'] = CONF.controller_worker.loadbalancer_topology

    return lb_dict


def create_listener(listener_dict, lb_id):
    if not listener_dict.get('id'):
        listener_dict['id'] = uuidutils.generate_uuid()
    if 'loadbalancer_id' in listener_dict:
        listener_dict['load_balancer_id'] = listener_dict.pop(
            'loadbalancer_id')
    else:
        listener_dict['load_balancer_id'] = lb_id

    listener_dict[constants.PROVISIONING_STATUS] = constants.PENDING_CREATE
    listener_dict[constants.OPERATING_STATUS] = constants.OFFLINE
    # NOTE(blogan): Throwing away because we should not store secure data
    # in the database nor should we send it to a handler.
    if 'tls_termination' in listener_dict:
        del listener_dict['tls_termination']

    if 'sni_containers' in listener_dict:
        sni_container_ids = listener_dict.pop('sni_containers') or []
    elif 'sni_container_refs' in listener_dict:
        sni_container_ids = listener_dict.pop('sni_container_refs') or []
    else:
        sni_container_ids = []
    sni_containers = [{'listener_id': listener_dict.get('id'),
                       'tls_container_id': sni_container_id}
                      for sni_container_id in sni_container_ids]
    listener_dict['sni_containers'] = sni_containers

    if 'client_authentication' not in listener_dict:
        listener_dict['client_authentication'] = constants.CLIENT_AUTH_NONE

    if listener_dict['protocol'] == constants.PROTOCOL_TERMINATED_HTTPS:
        if ('tls_ciphers' not in listener_dict or
                listener_dict['tls_ciphers'] is None):
            listener_dict['tls_ciphers'] = (
                CONF.api_settings.default_listener_ciphers)
        if ('tls_versions' not in listener_dict or
                listener_dict['tls_versions'] is None):
            listener_dict['tls_versions'] = (
                CONF.api_settings.default_listener_tls_versions)
        if ('alpn_protocols' not in listener_dict or
                listener_dict['alpn_protocols'] is None):
            listener_dict['alpn_protocols'] = (
                CONF.api_settings.default_listener_alpn_protocols)

    if listener_dict.get('timeout_client_data') is None:
        listener_dict['timeout_client_data'] = (
            CONF.haproxy_amphora.timeout_client_data)
    if listener_dict.get('timeout_member_connect') is None:
        listener_dict['timeout_member_connect'] = (
            CONF.haproxy_amphora.timeout_member_connect)
    if listener_dict.get('timeout_member_data') is None:
        listener_dict['timeout_member_data'] = (
            CONF.haproxy_amphora.timeout_member_data)
    if listener_dict.get('timeout_tcp_inspect') is None:
        listener_dict['timeout_tcp_inspect'] = (
            CONF.haproxy_amphora.timeout_tcp_inspect)

    return listener_dict


def create_l7policy(l7policy_dict, lb_id, listener_id):
    l7policy_dict = validate.sanitize_l7policy_api_args(l7policy_dict,
                                                        create=True)
    l7policy_dict[constants.PROVISIONING_STATUS] = constants.PENDING_CREATE
    l7policy_dict[constants.OPERATING_STATUS] = constants.OFFLINE
    if not l7policy_dict.get('id'):
        l7policy_dict['id'] = uuidutils.generate_uuid()
    l7policy_dict['listener_id'] = listener_id
    if l7policy_dict.get('redirect_pool'):
        pool_dict = l7policy_dict.pop('redirect_pool')
        prepped_pool = create_pool(pool_dict, lb_id)
        l7policy_dict['redirect_pool'] = prepped_pool
        l7policy_dict['redirect_pool_id'] = prepped_pool['id']
    rules = l7policy_dict.pop('rules', None)
    if rules:
        l7policy_dict['l7rules'] = rules
    if l7policy_dict.get('l7rules'):
        if (len(l7policy_dict.get('l7rules')) >
                constants.MAX_L7RULES_PER_L7POLICY):
            raise exceptions.TooManyL7RulesOnL7Policy(id=l7policy_dict['id'])
        prepped_l7rules = []
        for l7rule_dict in l7policy_dict.get('l7rules'):
            try:
                validate.l7rule_data(l7rule.L7RulePOST(**l7rule_dict))
            except Exception as e:
                raise exceptions.L7RuleValidation(error=e)
            prepped_l7rule = create_l7rule(l7rule_dict, l7policy_dict['id'])
            prepped_l7rules.append(prepped_l7rule)
    return l7policy_dict


def create_l7rule(l7rule_dict, l7policy_id):
    l7rule_dict[constants.PROVISIONING_STATUS] = constants.PENDING_CREATE
    l7rule_dict[constants.OPERATING_STATUS] = constants.OFFLINE
    if not l7rule_dict.get('id'):
        l7rule_dict['id'] = uuidutils.generate_uuid()
    l7rule_dict['l7policy_id'] = l7policy_id
    if 'enabled' not in l7rule_dict:
        l7rule_dict['enabled'] = True
    return l7rule_dict


def create_pool(pool_dict, lb_id=None):
    if not pool_dict.get('id'):
        pool_dict['id'] = uuidutils.generate_uuid()
    if 'loadbalancer_id' in pool_dict:
        pool_dict['load_balancer_id'] = pool_dict.pop('loadbalancer_id')
    else:
        pool_dict['load_balancer_id'] = lb_id
    if pool_dict.get('session_persistence'):
        pool_dict['session_persistence']['pool_id'] = pool_dict.get('id')
    if 'members' in pool_dict and not pool_dict.get('members'):
        del pool_dict['members']
    elif pool_dict.get('members'):
        prepped_members = []
        for member_dict in pool_dict.get('members'):
            prepped_members.append(create_member(member_dict, pool_dict['id']))
    if pool_dict['tls_enabled'] is True:
        if pool_dict['tls_ciphers'] is None:
            pool_dict['tls_ciphers'] = CONF.api_settings.default_pool_ciphers
        if pool_dict['tls_versions'] is None:
            pool_dict['tls_versions'] = (
                CONF.api_settings.default_pool_tls_versions)
        if pool_dict['alpn_protocols'] is None:
            pool_dict['alpn_protocols'] = (
                CONF.api_settings.default_pool_alpn_protocols)
    pool_dict[constants.PROVISIONING_STATUS] = constants.PENDING_CREATE
    pool_dict[constants.OPERATING_STATUS] = constants.OFFLINE
    return pool_dict


def create_member(member_dict, pool_id, has_health_monitor=False):
    if not member_dict.get('id'):
        member_dict['id'] = uuidutils.generate_uuid()
    member_dict['pool_id'] = pool_id
    member_dict[constants.PROVISIONING_STATUS] = constants.PENDING_CREATE
    if has_health_monitor:
        member_dict[constants.OPERATING_STATUS] = constants.OFFLINE
    else:
        member_dict[constants.OPERATING_STATUS] = constants.NO_MONITOR
    if 'backup' not in member_dict:
        member_dict['backup'] = False
    return member_dict


def create_health_monitor(hm_dict, pool_id=None):
    hm_dict[constants.PROVISIONING_STATUS] = constants.PENDING_CREATE
    hm_dict[constants.OPERATING_STATUS] = constants.OFFLINE
    if pool_id:
        hm_dict['id'] = pool_id
        hm_dict['pool_id'] = pool_id
    else:
        if not hm_dict.get('id'):
            hm_dict['id'] = uuidutils.generate_uuid()
    return hm_dict
