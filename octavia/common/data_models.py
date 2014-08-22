#    Copyright (c) 2014 Rackspace
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


class BaseDataModel(object):

    # NOTE(brandon-logan) This does not discover dicts for relationship
    # attributes.
    def to_dict(self):
        ret = {}
        for attr in self.__dict__:
            if (attr.startswith('_') or
                    isinstance(getattr(self, attr), BaseDataModel)):
                continue
            ret[attr] = self.__dict__[attr]
        return ret

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.to_dict() == other.to_dict()
        return False


class SessionPersistence(BaseDataModel):

    def __init__(self, pool_id=None, type=None, cookie_name=None,
                 pool=None):
        self.pool_id = pool_id
        self.type = type
        self.cookie_name = cookie_name
        self.pool = pool


class ListenerStatistics(BaseDataModel):

    def __init__(self, listener_id=None, bytes_in=None, bytes_out=None,
                 active_connections=None, total_connections=None,
                 listener=None):
        self.listener_id = listener_id
        self.bytes_in = bytes_in
        self.bytes_out = bytes_out
        self.active_connections = active_connections
        self.total_connections = total_connections
        self.listener = listener


class HealthMonitor(BaseDataModel):

    def __init__(self, id=None, tenant_id=None, pool_id=None, type=None,
                 delay=None, timeout=None, fall_threshold=None,
                 rise_threshold=None, http_method=None, url_path=None,
                 expected_codes=None, enabled=None, pool=None):
        self.id = id
        self.tenant_id = tenant_id
        self.pool_id = pool_id
        self.type = type
        self.delay = delay
        self.timeout = timeout
        self.fall_threshold = fall_threshold
        self.rise_threshold = rise_threshold
        self.http_method = http_method
        self.url_path = url_path
        self.expected_codes = expected_codes
        self.enabled = enabled
        self.pool = pool


class Pool(BaseDataModel):

    def __init__(self, id=None, tenant_id=None, name=None, description=None,
                 protocol=None, lb_algorithm=None, enabled=None,
                 operating_status=None, members=None, health_monitor=None,
                 session_persistence=None, listener=None):
        self.id = id
        self.tenant_id = tenant_id
        self.name = name
        self.description = description
        self.protocol = protocol
        self.lb_algorithm = lb_algorithm
        self.enabled = enabled
        self.operating_status = operating_status
        self.members = members or []
        self.health_monitor = health_monitor
        self.session_persistence = session_persistence
        self.listener = listener


class Member(BaseDataModel):

    def __init__(self, id=None, tenant_id=None, pool_id=None, ip_address=None,
                 protocol_port=None, weight=None, enabled=None,
                 subnet_id=None, operating_status=None, pool=None):
        self.id = id
        self.tenant_id = tenant_id
        self.pool_id = pool_id
        self.ip_address = ip_address
        self.protocol_port = protocol_port
        self.weight = weight
        self.enabled = enabled
        self.subnet_id = subnet_id
        self.operating_status = operating_status
        self.pool = pool


class Listener(BaseDataModel):

    def __init__(self, id=None, tenant_id=None, name=None, description=None,
                 default_pool_id=None, load_balancer_id=None, protocol=None,
                 protocol_port=None, connection_limit=None,
                 enabled=None, provisioning_status=None, operating_status=None,
                 default_tls_container_id=None, stats=None, default_pool=None,
                 load_balancer=None, sni_containers=None):
        self.id = id
        self.tenant_id = tenant_id
        self.name = name
        self.description = description
        self.default_pool_id = default_pool_id
        self.load_balancer_id = load_balancer_id
        self.protocol = protocol
        self.protocol_port = protocol_port
        self.connection_limit = connection_limit
        self.enabled = enabled
        self.provisioning_status = provisioning_status
        self.operating_status = operating_status
        self.default_tls_container_id = default_tls_container_id
        self.stats = stats
        self.default_pool = default_pool
        self.load_balancer = load_balancer
        self.sni_containers = sni_containers


class LoadBalancer(BaseDataModel):

    def __init__(self, id=None, tenant_id=None, name=None, description=None,
                 provisioning_status=None, operating_status=None, enabled=None,
                 vip=None, listeners=None, amphorae=None):
        self.id = id
        self.tenant_id = tenant_id
        self.name = name
        self.description = description
        self.provisioning_status = provisioning_status
        self.operating_status = operating_status
        self.enabled = enabled
        self.vip = vip
        self.listeners = listeners or []
        self.amphorae = amphorae or []


class Vip(BaseDataModel):

    def __init__(self, load_balancer_id=None, ip_address=None,
                 net_port_id=None, subnet_id=None, floating_ip_id=None,
                 floating_ip_network_id=None, load_balancer=None):
        self.load_balancer_id = load_balancer_id
        self.ip_address = ip_address
        self.net_port_id = net_port_id
        self.subnet_id = subnet_id
        self.floating_ip_id = floating_ip_id
        self.floating_ip_network_id = floating_ip_network_id
        self.load_balancer = load_balancer


class SNI(BaseDataModel):

    def __init__(self, listener_id=None, position=None, listener=None,
                 tls_container_id=None):
        self.listener_id = listener_id
        self.position = position
        self.listener = listener
        self.tls_container_id = tls_container_id


class Amphora(BaseDataModel):

    def __init__(self, id=None, load_balancer_id=None, host_id=None,
                 status=None, load_balancer=None):
        self.id = id
        self.load_balancer_id = load_balancer_id
        self.host_id = host_id
        self.status = status
        self.load_balancer = load_balancer