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

import re


class BaseDataModel(object):

    # NOTE(brandon-logan) This does not discover dicts for relationship
    # attributes.
    def to_dict(self):
        """Converts a data model to a dictionary."""
        ret = {}
        for attr in self.__dict__:
            if attr.startswith('_'):
                continue
            if isinstance(getattr(self, attr), (BaseDataModel, list)):
                ret[attr] = None
            else:
                ret[attr] = self.__dict__[attr]
        return ret

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.to_dict() == other.to_dict()
        return False

    @classmethod
    def from_dict(cls, dict):
        return cls(**dict)

    @classmethod
    def _name(cls):
        """Returns class name in a more human readable form."""
        # Split the class name up by capitalized words
        return ' '.join(re.findall('[A-Z][^A-Z]*', cls.__name__))


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

    def delete(self):
        self.pool.health_monitor = None


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

    def delete(self):
        self.listener.default_pool = None
        self.listener.default_pool_id = None


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

    def delete(self):
        for mem in self.pool.members:
            if mem.id == self.id:
                self.pool.members.remove(mem)
                break


class Listener(BaseDataModel):

    def __init__(self, id=None, tenant_id=None, name=None, description=None,
                 default_pool_id=None, load_balancer_id=None, protocol=None,
                 protocol_port=None, connection_limit=None,
                 enabled=None, provisioning_status=None, operating_status=None,
                 tls_certificate_id=None, stats=None, default_pool=None,
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
        self.tls_certificate_id = tls_certificate_id
        self.stats = stats
        self.default_pool = default_pool
        self.load_balancer = load_balancer
        self.sni_containers = sni_containers


class LoadBalancer(BaseDataModel):

    def __init__(self, id=None, tenant_id=None, name=None, description=None,
                 provisioning_status=None, operating_status=None, enabled=None,
                 topology=None, vip=None, listeners=None, amphorae=None):
        self.id = id
        self.tenant_id = tenant_id
        self.name = name
        self.description = description
        self.provisioning_status = provisioning_status
        self.operating_status = operating_status
        self.enabled = enabled
        self.vip = vip
        self.topology = topology
        self.listeners = listeners or []
        self.amphorae = amphorae or []


class Vip(BaseDataModel):

    def __init__(self, load_balancer_id=None, ip_address=None,
                 subnet_id=None, port_id=None, load_balancer=None):
        self.load_balancer_id = load_balancer_id
        self.ip_address = ip_address
        self.subnet_id = subnet_id
        self.port_id = port_id
        self.load_balancer = load_balancer


class SNI(BaseDataModel):

    def __init__(self, listener_id=None, position=None, listener=None,
                 tls_container_id=None):
        self.listener_id = listener_id
        self.position = position
        self.listener = listener
        self.tls_container_id = tls_container_id


class TLSContainer(BaseDataModel):

    def __init__(self, id=None, primary_cn=None, certificate=None,
                 private_key=None, passphrase=None, intermediates=[]):
        self.id = id
        self.primary_cn = primary_cn
        self.certificate = certificate
        self.private_key = private_key
        self.passphrase = passphrase
        self.intermediates = intermediates


class Amphora(BaseDataModel):

    def __init__(self, id=None, load_balancer_id=None, compute_id=None,
                 status=None, lb_network_ip=None, vrrp_ip=None,
                 ha_ip=None, vrrp_port_id=None, ha_port_id=None,
                 load_balancer=None, role=None):
        self.id = id
        self.load_balancer_id = load_balancer_id
        self.compute_id = compute_id
        self.status = status
        self.lb_network_ip = lb_network_ip
        self.vrrp_ip = vrrp_ip
        self.ha_ip = ha_ip
        self.vrrp_port_id = vrrp_port_id
        self.ha_port_id = ha_port_id
        self.role = role
        self.load_balancer = load_balancer


class AmphoraHealth(BaseDataModel):

    def __init__(self, amphora_id=None, last_update=None, busy=False):
        self.amphora_id = amphora_id
        self.last_update = last_update
        self.busy = busy
