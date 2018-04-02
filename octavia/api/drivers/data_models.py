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


class BaseDataModel(object):
    def to_dict(self, calling_classes=None, recurse=False, **kwargs):
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
                                        calling_classes + [type(self)])))
                            else:
                                ret[attr] = None
                        else:
                            ret[attr] = item
                elif isinstance(getattr(self, attr), BaseDataModel):
                    if type(self) not in calling_classes:
                        ret[attr] = value.to_dict(
                            calling_classes=calling_classes + [type(self)])
                    else:
                        ret[attr] = None
                elif six.PY2 and isinstance(value, six.text_type):
                    ret[attr.encode('utf8')] = value.encode('utf8')
                else:
                    ret[attr] = value
            else:
                if isinstance(getattr(self, attr), (BaseDataModel, list)):
                    ret[attr] = None
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


class LoadBalancer(BaseDataModel):
    def __init__(self, admin_state_up=None, description=None, flavor=None,
                 listeners=None, loadbalancer_id=None, name=None,
                 project_id=None, vip_address=None, vip_network_id=None,
                 vip_port_id=None, vip_subnet_id=None):

        self.admin_state_up = admin_state_up
        self.description = description
        self.flavor = flavor or {}
        self.listeners = listeners or []
        self.loadbalancer_id = loadbalancer_id
        self.name = name
        self.project_id = project_id
        self.vip_address = vip_address
        self.vip_network_id = vip_network_id
        self.vip_port_id = vip_port_id
        self.vip_subnet_id = vip_subnet_id


class Listener(BaseDataModel):
    def __init__(self, admin_state_up=None, connection_limit=None,
                 default_pool=None, default_pool_id=None,
                 default_tls_container=None, description=None,
                 insert_headers=None, l7policies=None, listener_id=None,
                 loadbalancer_id=None, name=None, protocol=None,
                 protocol_port=None, sni_containers=None):

        self.admin_state_up = admin_state_up
        self.connection_limit = connection_limit
        self.default_pool = default_pool
        self.default_pool_id = default_pool_id
        self.default_tls_container = default_tls_container
        self.description = description
        self.insert_headers = insert_headers or {}
        self.l7policies = l7policies or []
        self.listener_id = listener_id
        self.loadbalancer_id = loadbalancer_id
        self.name = name
        self.protocol = protocol
        self.protocol_port = protocol_port
        self.sni_containers = sni_containers


class Pool(BaseDataModel):
    def __init__(self, admin_state_up=None, description=None,
                 healthmonitor=None, lb_algorithm=None, listener_id=None,
                 loadbalancer_id=None, members=None, name=None, pool_id=None,
                 protocol=None, session_persistence=None):

        self.admin_state_up = admin_state_up
        self.description = description
        self.healthmonitor = healthmonitor
        self.lb_algorithm = lb_algorithm
        self.listener_id = listener_id
        self.loadbalancer_id = loadbalancer_id
        self.members = members or []
        self.name = name
        self.pool_id = pool_id
        self.protocol = protocol
        self.session_persistence = session_persistence or {}


class Member(BaseDataModel):
    def __init__(self, address=None, admin_state_up=None, member_id=None,
                 monitor_address=None, monitor_port=None, name=None,
                 pool_id=None, protocol_port=None, subnet_id=None,
                 weight=None):

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


class HealthMonitor(BaseDataModel):
    def __init__(self, admin_state_up=None, delay=None, expected_codes=None,
                 healthmonitor_id=None, http_method=None, max_retries=None,
                 max_retries_down=None, name=None, pool_id=None, timeout=None,
                 type=None, url_path=None):

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
    def __init__(self, action=None, admin_state_up=None, description=None,
                 l7policy_id=None, listener_id=None, name=None, position=None,
                 redirect_pool_id=None, redirect_url=None, rules=None):

        self.action = action
        self.admin_state_up = admin_state_up
        self.description = description
        self.l7policy_id = l7policy_id
        self.listener_id = listener_id
        self.name = name
        self.position = position
        self.redirect_pool_id = redirect_pool_id
        self.redirect_url = redirect_url
        self.rules = rules or []


class L7Rule(BaseDataModel):
    def __init__(self, admin_state_up=None, compare_type=None, invert=None,
                 key=None, l7policy_id=None, l7rule_id=None, type=None,
                 value=None):

        self.admin_state_up = admin_state_up
        self.compare_type = compare_type
        self.invert = invert
        self.key = key
        self.l7policy_id = l7policy_id
        self.l7rule_id = l7rule_id
        self.type = type
        self.value = value


class VIP(BaseDataModel):
    def __init__(self, vip_address=None, vip_network_id=None, vip_port_id=None,
                 vip_subnet_id=None):

        self.vip_address = vip_address
        self.vip_network_id = vip_network_id
        self.vip_port_id = vip_port_id
        self.vip_subnet_id = vip_subnet_id
