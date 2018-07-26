# Copyright 2018 Rackspace, US Inc.
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

import copy

import six

from oslo_config import cfg
from oslo_log import log as logging
from stevedore import driver as stevedore_driver

from octavia.api.drivers import data_models as driver_dm
from octavia.api.drivers import exceptions as driver_exceptions
from octavia.common import data_models
from octavia.common import exceptions
from octavia.common.tls_utils import cert_parser
from octavia.i18n import _

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def call_provider(provider, driver_method, *args, **kwargs):
    """Wrap calls to the provider driver to handle driver errors.

    This allows Octavia to return user friendly errors when a provider driver
    has an issue.

    :param driver_method: Method in the driver to call.
    :raises ProviderDriverError: Catch all driver error.
    :raises ProviderNotImplementedError: The driver doesn't support this
                                         action.
    :raises ProviderUnsupportedOptionError: The driver doesn't support a
                                            provided option.
    """

    try:
        return driver_method(*args, **kwargs)
    except driver_exceptions.DriverError as e:
        LOG.exception("Provider '%s' raised a driver error: %s",
                      provider, e.operator_fault_string)
        raise exceptions.ProviderDriverError(prov=provider,
                                             user_msg=e.user_fault_string)
    except (driver_exceptions.NotImplementedError, NotImplementedError) as e:
        LOG.info("Provider '%s' raised a not implemented error: %s",
                 provider, e.operator_fault_string)
        raise exceptions.ProviderNotImplementedError(
            prov=provider, user_msg=e.user_fault_string)
    except driver_exceptions.UnsupportedOptionError as e:
        LOG.info("Provider '%s' raised an unsupported option error: "
                 "%s", provider, e.operator_fault_string)
        raise exceptions.ProviderUnsupportedOptionError(
            prov=provider, user_msg=e.user_fault_string)
    except Exception as e:
        LOG.exception("Provider '%s' raised an unknown error: %s",
                      provider, e)
        raise exceptions.ProviderDriverError(prov=provider, user_msg=e)


def _base_to_provider_dict(current_dict, include_project_id=False):
    new_dict = copy.deepcopy(current_dict)
    if 'provisioning_status' in new_dict:
        del new_dict['provisioning_status']
    if 'operating_status' in new_dict:
        del new_dict['operating_status']
    if 'provider' in new_dict:
        del new_dict['provider']
    if 'created_at' in new_dict:
        del new_dict['created_at']
    if 'updated_at' in new_dict:
        del new_dict['updated_at']
    if 'enabled' in new_dict:
        new_dict['admin_state_up'] = new_dict.pop('enabled')
    if 'project_id' in new_dict and not include_project_id:
        del new_dict['project_id']
    if 'tenant_id' in new_dict:
        del new_dict['tenant_id']
    return new_dict


# Note: The provider dict returned from this method will have provider
#       data model objects in it.
def lb_dict_to_provider_dict(lb_dict, vip=None,
                             db_pools=None, db_listeners=None):
    new_lb_dict = _base_to_provider_dict(lb_dict, include_project_id=True)
    new_lb_dict['loadbalancer_id'] = new_lb_dict.pop('id')
    if vip:
        new_lb_dict['vip_address'] = vip.ip_address
        new_lb_dict['vip_network_id'] = vip.network_id
        new_lb_dict['vip_port_id'] = vip.port_id
        new_lb_dict['vip_subnet_id'] = vip.subnet_id
        new_lb_dict['vip_qos_policy_id'] = vip.qos_policy_id

    if db_pools:
        new_lb_dict['pools'] = db_pools_to_provider_pools(db_pools)
    if db_listeners:
        new_lb_dict['listeners'] = db_listeners_to_provider_listeners(
            db_listeners)
    return new_lb_dict


def db_loadbalancer_to_provider_loadbalancer(db_loadbalancer):
    new_loadbalancer_dict = lb_dict_to_provider_dict(
        db_loadbalancer.to_dict(recurse=True),
        db_pools=db_loadbalancer.pools,
        db_listeners=db_loadbalancer.listeners)
    for unsupported_field in ['server_group_id', 'amphorae',
                              'vrrp_group', 'topology', 'vip']:
        del new_loadbalancer_dict[unsupported_field]
    provider_loadbalancer = driver_dm.LoadBalancer.from_dict(
        new_loadbalancer_dict)
    return provider_loadbalancer


def db_listeners_to_provider_listeners(db_listeners):
    provider_listeners = []
    for listener in db_listeners:
        provider_listener = db_listener_to_provider_listener(listener)
        provider_listeners.append(provider_listener)
    return provider_listeners


def db_listener_to_provider_listener(db_listener):
    new_listener_dict = listener_dict_to_provider_dict(
        db_listener.to_dict(recurse=True))
    if ('default_pool' in new_listener_dict and
            new_listener_dict['default_pool']):
        provider_pool = db_pool_to_provider_pool(db_listener.default_pool)
        new_listener_dict['default_pool_id'] = provider_pool.pool_id
        new_listener_dict['default_pool'] = provider_pool
    if new_listener_dict.get('l7policies', None):
        new_listener_dict['l7policies'] = (
            db_l7policies_to_provider_l7policies(db_listener.l7policies))
    provider_listener = driver_dm.Listener.from_dict(new_listener_dict)
    return provider_listener


def listener_dict_to_provider_dict(listener_dict):
    new_listener_dict = _base_to_provider_dict(listener_dict)
    new_listener_dict['listener_id'] = new_listener_dict.pop('id')
    if 'load_balancer_id' in new_listener_dict:
        new_listener_dict['loadbalancer_id'] = new_listener_dict.pop(
            'load_balancer_id')

    # Pull the certs out of the certificate manager to pass to the provider
    if 'tls_certificate_id' in new_listener_dict:
        new_listener_dict['default_tls_container_ref'] = new_listener_dict.pop(
            'tls_certificate_id')
    if 'sni_containers' in new_listener_dict:
        new_listener_dict['sni_container_refs'] = new_listener_dict.pop(
            'sni_containers')
    if 'sni_container_refs' in listener_dict:
        listener_dict['sni_containers'] = listener_dict.pop(
            'sni_container_refs')
    listener_obj = data_models.Listener(**listener_dict)
    if listener_obj.tls_certificate_id or listener_obj.sni_containers:
        SNI_objs = []
        for sni in listener_obj.sni_containers:
            if isinstance(sni, dict):
                sni_obj = data_models.SNI(**sni)
                SNI_objs.append(sni_obj)
            elif isinstance(sni, six.string_types):
                sni_obj = data_models.SNI(tls_container_id=sni)
                SNI_objs.append(sni_obj)
            else:
                raise exceptions.ValidationException(
                    detail=_('Invalid SNI container on listener'))
        listener_obj.sni_containers = SNI_objs
        cert_manager = stevedore_driver.DriverManager(
            namespace='octavia.cert_manager',
            name=CONF.certificates.cert_manager,
            invoke_on_load=True,
        ).driver
        cert_dict = cert_parser.load_certificates_data(cert_manager,
                                                       listener_obj)
        if 'tls_cert' in cert_dict:
            new_listener_dict['default_tls_container_data'] = (
                cert_dict['tls_cert'].to_dict())
        if 'sni_certs' in cert_dict:
            sni_data_list = []
            for sni in cert_dict['sni_certs']:
                sni_data_list.append(sni.to_dict())
            new_listener_dict['sni_container_data'] = sni_data_list

    # Remove the DB back references
    if 'load_balancer' in new_listener_dict:
        del new_listener_dict['load_balancer']
    if 'peer_port' in new_listener_dict:
        del new_listener_dict['peer_port']
    if 'pools' in new_listener_dict:
        del new_listener_dict['pools']
    if 'stats' in new_listener_dict:
        del new_listener_dict['stats']

    if ('default_pool' in new_listener_dict and
            new_listener_dict['default_pool']):
        pool = new_listener_dict.pop('default_pool')
        new_listener_dict['default_pool'] = pool_dict_to_provider_dict(pool)
    provider_l7policies = []
    if 'l7policies' in new_listener_dict:
        l7policies = new_listener_dict.pop('l7policies')
        for l7policy in l7policies:
            provider_l7policy = l7policy_dict_to_provider_dict(l7policy)
            provider_l7policies.append(provider_l7policy)
        new_listener_dict['l7policies'] = provider_l7policies
    return new_listener_dict


def db_pools_to_provider_pools(db_pools):
    provider_pools = []
    for pool in db_pools:
        provider_pools.append(db_pool_to_provider_pool(pool))
    return provider_pools


def db_pool_to_provider_pool(db_pool):
    new_pool_dict = pool_dict_to_provider_dict(db_pool.to_dict(recurse=True))
    # Replace the sub-dicts with objects
    if 'health_monitor' in new_pool_dict:
        del new_pool_dict['health_monitor']
    if db_pool.health_monitor:
        provider_healthmonitor = db_HM_to_provider_HM(db_pool.health_monitor)
        new_pool_dict['healthmonitor'] = provider_healthmonitor
    # Don't leave a 'members' None here, we want it to pass through to Unset
    if new_pool_dict.get('members', None):
        del new_pool_dict['members']
    if db_pool.members:
        provider_members = db_members_to_provider_members(db_pool.members)
        new_pool_dict['members'] = provider_members
    db_listeners = db_pool.listeners
    if db_listeners:
        new_pool_dict['listener_id'] = db_listeners[0].id
    return driver_dm.Pool.from_dict(new_pool_dict)


def pool_dict_to_provider_dict(pool_dict):
    new_pool_dict = _base_to_provider_dict(pool_dict)
    new_pool_dict['pool_id'] = new_pool_dict.pop('id')
    # Remove the DB back references
    if ('session_persistence' in new_pool_dict and
            new_pool_dict['session_persistence']):
        if 'pool_id' in new_pool_dict['session_persistence']:
            del new_pool_dict['session_persistence']['pool_id']
        if 'pool' in new_pool_dict['session_persistence']:
            del new_pool_dict['session_persistence']['pool']
    if 'l7policies' in new_pool_dict:
        del new_pool_dict['l7policies']
    if 'listeners' in new_pool_dict:
        del new_pool_dict['listeners']
    if 'load_balancer' in new_pool_dict:
        del new_pool_dict['load_balancer']
    if 'load_balancer_id' in new_pool_dict:
        new_pool_dict['loadbalancer_id'] = new_pool_dict.pop(
            'load_balancer_id')
    if 'health_monitor' in new_pool_dict and new_pool_dict['health_monitor']:
        hm = new_pool_dict.pop('health_monitor')
        new_pool_dict['healthmonitor'] = hm_dict_to_provider_dict(hm)
    if 'members' in new_pool_dict and new_pool_dict['members']:
        members = new_pool_dict.pop('members')
        provider_members = []
        for member in members:
            provider_member = member_dict_to_provider_dict(member)
            provider_members.append(provider_member)
        new_pool_dict['members'] = provider_members
    return new_pool_dict


def db_members_to_provider_members(db_members):
    provider_members = []
    for member in db_members:
        provider_members.append(db_member_to_provider_member(member))
    return provider_members


def db_member_to_provider_member(db_member):
    new_member_dict = member_dict_to_provider_dict(db_member.to_dict())
    return driver_dm.Member.from_dict(new_member_dict)


def member_dict_to_provider_dict(member_dict):
    new_member_dict = _base_to_provider_dict(member_dict)
    new_member_dict['member_id'] = new_member_dict.pop('id')
    if 'ip_address' in new_member_dict:
        new_member_dict['address'] = new_member_dict.pop('ip_address')
    # Remove the DB back references
    if 'pool' in new_member_dict:
        del new_member_dict['pool']
    return new_member_dict


def db_HM_to_provider_HM(db_hm):
    new_HM_dict = hm_dict_to_provider_dict(db_hm.to_dict())
    return driver_dm.HealthMonitor.from_dict(new_HM_dict)


def hm_dict_to_provider_dict(hm_dict):
    new_hm_dict = _base_to_provider_dict(hm_dict)
    new_hm_dict['healthmonitor_id'] = new_hm_dict.pop('id')
    if 'fall_threshold' in new_hm_dict:
        new_hm_dict['max_retries_down'] = new_hm_dict.pop('fall_threshold')
    if 'rise_threshold' in new_hm_dict:
        new_hm_dict['max_retries'] = new_hm_dict.pop('rise_threshold')
    # Remove the DB back references
    if 'pool' in new_hm_dict:
        del new_hm_dict['pool']
    return new_hm_dict


def db_l7policies_to_provider_l7policies(db_l7policies):
    provider_l7policies = []
    for l7policy in db_l7policies:
        provider_l7policy = db_l7policy_to_provider_l7policy(l7policy)
        provider_l7policies.append(provider_l7policy)
    return provider_l7policies


def db_l7policy_to_provider_l7policy(db_l7policy):
    new_l7policy_dict = l7policy_dict_to_provider_dict(
        db_l7policy.to_dict(recurse=True))
    if 'l7rules' in new_l7policy_dict:
        del new_l7policy_dict['l7rules']
        new_l7rules = db_l7rules_to_provider_l7rules(db_l7policy.l7rules)
        new_l7policy_dict['rules'] = new_l7rules
    return driver_dm.L7Policy.from_dict(new_l7policy_dict)


def l7policy_dict_to_provider_dict(l7policy_dict):
    new_l7policy_dict = _base_to_provider_dict(l7policy_dict)
    new_l7policy_dict['l7policy_id'] = new_l7policy_dict.pop('id')
    # Remove the DB back references
    if 'listener' in new_l7policy_dict:
        del new_l7policy_dict['listener']
    if 'redirect_pool' in new_l7policy_dict:
        del new_l7policy_dict['redirect_pool']
    if 'l7rules' in new_l7policy_dict and new_l7policy_dict['l7rules']:
        rules = new_l7policy_dict.pop('l7rules')
        provider_rules = []
        for rule in rules:
            provider_rule = l7rule_dict_to_provider_dict(rule)
            provider_rules.append(provider_rule)
        new_l7policy_dict['rules'] = provider_rules
    return new_l7policy_dict


def db_l7rules_to_provider_l7rules(db_l7rules):
    provider_l7rules = []
    for l7rule in db_l7rules:
        provider_l7rule = db_l7rule_to_provider_l7rule(l7rule)
        provider_l7rules.append(provider_l7rule)
    return provider_l7rules


def db_l7rule_to_provider_l7rule(db_l7rule):
    new_l7rule_dict = l7rule_dict_to_provider_dict(db_l7rule.to_dict())
    return driver_dm.L7Rule.from_dict(new_l7rule_dict)


def l7rule_dict_to_provider_dict(l7rule_dict):
    new_l7rule_dict = _base_to_provider_dict(l7rule_dict)
    new_l7rule_dict['l7rule_id'] = new_l7rule_dict.pop('id')
    # Remove the DB back references
    if 'l7policy' in new_l7rule_dict:
        del new_l7rule_dict['l7policy']
    return new_l7rule_dict


def vip_dict_to_provider_dict(vip_dict):
    new_vip_dict = {}
    if 'ip_address' in vip_dict:
        new_vip_dict['vip_address'] = vip_dict['ip_address']
    if 'network_id' in vip_dict:
        new_vip_dict['vip_network_id'] = vip_dict['network_id']
    if 'port_id' in vip_dict:
        new_vip_dict['vip_port_id'] = vip_dict['port_id']
    if 'subnet_id' in vip_dict:
        new_vip_dict['vip_subnet_id'] = vip_dict['subnet_id']
    if 'qos_policy_id' in vip_dict:
        new_vip_dict['vip_qos_policy_id'] = vip_dict['qos_policy_id']
    return new_vip_dict


def provider_vip_dict_to_vip_obj(vip_dictionary):
    vip_obj = data_models.Vip()
    if 'vip_address' in vip_dictionary:
        vip_obj.ip_address = vip_dictionary['vip_address']
    if 'vip_network_id' in vip_dictionary:
        vip_obj.network_id = vip_dictionary['vip_network_id']
    if 'vip_port_id' in vip_dictionary:
        vip_obj.port_id = vip_dictionary['vip_port_id']
    if 'vip_subnet_id' in vip_dictionary:
        vip_obj.subnet_id = vip_dictionary['vip_subnet_id']
    if 'vip_qos_policy_id' in vip_dictionary:
        vip_obj.qos_policy_id = vip_dictionary['vip_qos_policy_id']
    return vip_obj
