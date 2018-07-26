#    Copyright (c) 2014 Rackspace
#    Copyright (c) 2016 Blue Box, an IBM Company
#    Copyright 2018 Rackspace, US Inc.
#    All Rights Reserved.
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

import six

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class BaseDataModel(object):
    def to_dict(self, calling_classes=None, recurse=False,
                render_unsets=False, **kwargs):
        """Converts a data model to a dictionary."""
        calling_classes = calling_classes or []
        ret = {}
        for attr in self.__dict__:
            if attr.startswith('_') or not kwargs.get(attr, True):
                continue
            value = self.__dict__[attr]

            if recurse:
                if isinstance(getattr(self, attr), list):
                    ret[attr] = []
                    for item in value:
                        if isinstance(item, BaseDataModel):
                            if type(self) not in calling_classes:
                                ret[attr].append(
                                    item.to_dict(calling_classes=(
                                        calling_classes + [type(self)]),
                                        recurse=True,
                                        render_unsets=render_unsets))
                            else:
                                ret[attr].append(None)
                        else:
                            ret[attr].append(item)
                elif isinstance(getattr(self, attr), BaseDataModel):
                    if type(self) not in calling_classes:
                        ret[attr] = value.to_dict(
                            render_unsets=render_unsets,
                            calling_classes=calling_classes + [type(self)])
                    else:
                        ret[attr] = None
                elif six.PY2 and isinstance(value, six.text_type):
                    ret[attr.encode('utf8')] = value.encode('utf8')
                elif isinstance(value, UnsetType):
                    if render_unsets:
                        ret[attr] = None
                    else:
                        continue
                else:
                    ret[attr] = value
            else:
                if (isinstance(getattr(self, attr), (BaseDataModel, list)) or
                        isinstance(value, UnsetType)):
                    if render_unsets:
                        ret[attr] = None
                    else:
                        continue
                else:
                    ret[attr] = value

        return ret

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.to_dict() == other.to_dict()
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @classmethod
    def from_dict(cls, dict):
        return cls(**dict)


class UnsetType(object):
    def __bool__(self):
        return False
    __nonzero__ = __bool__

    def __repr__(self):
        return 'Unset'


Unset = UnsetType()


class LoadBalancer(BaseDataModel):
    def __init__(self, admin_state_up=Unset, description=Unset, flavor=Unset,
                 listeners=Unset, loadbalancer_id=Unset, name=Unset,
                 pools=Unset, project_id=Unset, vip_address=Unset,
                 vip_network_id=Unset, vip_port_id=Unset, vip_subnet_id=Unset,
                 vip_qos_policy_id=Unset):

        self.admin_state_up = admin_state_up
        self.description = description
        self.flavor = flavor
        self.listeners = listeners
        self.loadbalancer_id = loadbalancer_id
        self.name = name
        self.pools = pools
        self.project_id = project_id
        self.vip_address = vip_address
        self.vip_network_id = vip_network_id
        self.vip_port_id = vip_port_id
        self.vip_subnet_id = vip_subnet_id
        self.vip_qos_policy_id = vip_qos_policy_id


class Listener(BaseDataModel):
    def __init__(self, admin_state_up=Unset, connection_limit=Unset,
                 default_pool=Unset, default_pool_id=Unset,
                 default_tls_container_ref=Unset,
                 default_tls_container_data=Unset, description=Unset,
                 insert_headers=Unset, l7policies=Unset, listener_id=Unset,
                 loadbalancer_id=Unset, name=Unset, protocol=Unset,
                 protocol_port=Unset, sni_container_refs=Unset,
                 sni_container_data=Unset, timeout_client_data=Unset,
                 timeout_member_connect=Unset, timeout_member_data=Unset,
                 timeout_tcp_inspect=Unset):

        self.admin_state_up = admin_state_up
        self.connection_limit = connection_limit
        self.default_pool = default_pool
        self.default_pool_id = default_pool_id
        self.default_tls_container_data = default_tls_container_data
        self.default_tls_container_ref = default_tls_container_ref
        self.description = description
        self.insert_headers = insert_headers
        self.l7policies = l7policies
        self.listener_id = listener_id
        self.loadbalancer_id = loadbalancer_id
        self.name = name
        self.protocol = protocol
        self.protocol_port = protocol_port
        self.sni_container_data = sni_container_data
        self.sni_container_refs = sni_container_refs
        self.timeout_client_data = timeout_client_data
        self.timeout_member_connect = timeout_member_connect
        self.timeout_member_data = timeout_member_data
        self.timeout_tcp_inspect = timeout_tcp_inspect


class Pool(BaseDataModel):
    def __init__(self, admin_state_up=Unset, description=Unset,
                 healthmonitor=Unset, lb_algorithm=Unset,
                 loadbalancer_id=Unset, members=Unset, name=Unset,
                 pool_id=Unset, listener_id=Unset, protocol=Unset,
                 session_persistence=Unset):

        self.admin_state_up = admin_state_up
        self.description = description
        self.healthmonitor = healthmonitor
        self.lb_algorithm = lb_algorithm
        self.loadbalancer_id = loadbalancer_id
        self.members = members
        self.name = name
        self.pool_id = pool_id
        self.listener_id = listener_id
        self.protocol = protocol
        self.session_persistence = session_persistence


class Member(BaseDataModel):
    def __init__(self, address=Unset, admin_state_up=Unset, member_id=Unset,
                 monitor_address=Unset, monitor_port=Unset, name=Unset,
                 pool_id=Unset, protocol_port=Unset, subnet_id=Unset,
                 weight=Unset, backup=Unset):

        self.address = address
        self.admin_state_up = admin_state_up
        self.member_id = member_id
        self.monitor_address = monitor_address
        self.monitor_port = monitor_port
        self.name = name
        self.pool_id = pool_id
        self.protocol_port = protocol_port
        self.subnet_id = subnet_id
        self.weight = weight
        self.backup = backup


class HealthMonitor(BaseDataModel):
    def __init__(self, admin_state_up=Unset, delay=Unset, expected_codes=Unset,
                 healthmonitor_id=Unset, http_method=Unset, max_retries=Unset,
                 max_retries_down=Unset, name=Unset, pool_id=Unset,
                 timeout=Unset, type=Unset, url_path=Unset):

        self.admin_state_up = admin_state_up
        self.delay = delay
        self.expected_codes = expected_codes
        self.healthmonitor_id = healthmonitor_id
        self.http_method = http_method
        self.max_retries = max_retries
        self.max_retries_down = max_retries_down
        self.name = name
        self.pool_id = pool_id
        self.timeout = timeout
        self.type = type
        self.url_path = url_path


class L7Policy(BaseDataModel):
    def __init__(self, action=Unset, admin_state_up=Unset, description=Unset,
                 l7policy_id=Unset, listener_id=Unset, name=Unset,
                 position=Unset, redirect_pool_id=Unset, redirect_url=Unset,
                 rules=Unset):

        self.action = action
        self.admin_state_up = admin_state_up
        self.description = description
        self.l7policy_id = l7policy_id
        self.listener_id = listener_id
        self.name = name
        self.position = position
        self.redirect_pool_id = redirect_pool_id
        self.redirect_url = redirect_url
        self.rules = rules


class L7Rule(BaseDataModel):
    def __init__(self, admin_state_up=Unset, compare_type=Unset, invert=Unset,
                 key=Unset, l7policy_id=Unset, l7rule_id=Unset, type=Unset,
                 value=Unset):

        self.admin_state_up = admin_state_up
        self.compare_type = compare_type
        self.invert = invert
        self.key = key
        self.l7policy_id = l7policy_id
        self.l7rule_id = l7rule_id
        self.type = type
        self.value = value


class VIP(BaseDataModel):
    def __init__(self, vip_address=Unset, vip_network_id=Unset,
                 vip_port_id=Unset, vip_subnet_id=Unset,
                 vip_qos_policy_id=Unset):

        self.vip_address = vip_address
        self.vip_network_id = vip_network_id
        self.vip_port_id = vip_port_id
        self.vip_subnet_id = vip_subnet_id
        self.vip_qos_policy_id = vip_qos_policy_id
