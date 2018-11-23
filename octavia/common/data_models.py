#    Copyright (c) 2014 Rackspace
#    Copyright (c) 2016 Blue Box, an IBM Company
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

import six
from sqlalchemy.orm import collections

from octavia.common import constants


class BaseDataModel(object):
    def to_dict(self, calling_classes=None, recurse=False, **kwargs):
        """Converts a data model to a dictionary."""
        calling_classes = calling_classes or []
        ret = {}
        for attr in self.__dict__:
            if attr.startswith('_') or not kwargs.get(attr, True):
                continue
            value = self.__dict__[attr]
            if attr == 'tags':
                # tags is a list, it doesn't need recurse
                ret[attr] = value
                continue

            if recurse:
                if isinstance(getattr(self, attr), list):
                    ret[attr] = []
                    for item in value:
                        if isinstance(item, BaseDataModel):
                            if type(self) not in calling_classes:
                                ret[attr].append(
                                    item.to_dict(calling_classes=(
                                        calling_classes + [type(self)]),
                                        recurse=recurse))
                            else:
                                # TODO(rm_work): Is the idea that if this list
                                #  contains ANY BaseDataModel, that all of them
                                #  are data models, and we may as well quit?
                                #  Or, were we supposed to append a `None` for
                                #  each one? I assume the former?
                                ret[attr] = None
                                break
                        else:
                            ret[attr].append(item)
                elif isinstance(getattr(self, attr), BaseDataModel):
                    if type(self) not in calling_classes:
                        ret[attr] = value.to_dict(
                            calling_classes=calling_classes + [type(self)],
                            recurse=recurse)
                    else:
                        ret[attr] = None
                elif six.PY2 and isinstance(value, six.text_type):
                    ret[attr.encode('utf8')] = value.encode('utf8')
                else:
                    ret[attr] = value
            else:
                if isinstance(getattr(self, attr), BaseDataModel):
                    ret[attr] = None
                elif isinstance(getattr(self, attr), list):
                    ret[attr] = []
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

    @classmethod
    def _name(cls):
        """Returns class name in a more human readable form."""
        # Split the class name up by capitalized words
        return ' '.join(re.findall('[A-Z][^A-Z]*', cls.__name__))

    def _get_unique_key(self, obj=None):
        """Returns a unique key for passed object for data model building."""
        obj = obj or self
        # First handle all objects with their own ID, then handle subordinate
        # objects.
        if obj.__class__.__name__ in ['Member', 'Pool', 'LoadBalancer',
                                      'Listener', 'Amphora', 'L7Policy',
                                      'L7Rule']:
            return obj.__class__.__name__ + obj.id
        if obj.__class__.__name__ in ['SessionPersistence', 'HealthMonitor']:
            return obj.__class__.__name__ + obj.pool_id
        if obj.__class__.__name__ in ['ListenerStatistics']:
            return obj.__class__.__name__ + obj.listener_id + obj.amphora_id
        if obj.__class__.__name__ in ['ListenerCidr']:
            return obj.__class__.__name__ + obj.listener_id + obj.cidr
        if obj.__class__.__name__ in ['VRRPGroup', 'Vip']:
            return obj.__class__.__name__ + obj.load_balancer_id
        if obj.__class__.__name__ in ['AmphoraHealth']:
            return obj.__class__.__name__ + obj.amphora_id
        if obj.__class__.__name__ in ['SNI']:
            return (obj.__class__.__name__ +
                    obj.listener_id + obj.tls_container_id)
        raise NotImplementedError

    def _find_in_graph(self, key, _visited_nodes=None):
        """Locates an object with the given unique key in the current

        object graph and returns a reference to it.
        """
        _visited_nodes = _visited_nodes or []
        mykey = self._get_unique_key()
        if mykey in _visited_nodes:
            # Seen this node already, don't traverse further
            return None
        if mykey == key:
            return self
        _visited_nodes.append(mykey)
        attr_names = [attr_name for attr_name in dir(self)
                      if not attr_name.startswith('_')]
        for attr_name in attr_names:
            attr = getattr(self, attr_name)
            if isinstance(attr, BaseDataModel):
                result = attr._find_in_graph(
                    key, _visited_nodes=_visited_nodes)
                if result is not None:
                    return result
            elif isinstance(attr, (collections.InstrumentedList, list)):
                for item in attr:
                    if isinstance(item, BaseDataModel):
                        result = item._find_in_graph(
                            key, _visited_nodes=_visited_nodes)
                        if result is not None:
                            return result
        # If we are here we didn't find it.
        return None

    def update(self, update_dict):
        """Generic update method which works for simple,

        non-relational attributes.
        """
        for key, value in update_dict.items():
            setattr(self, key, value)


class SessionPersistence(BaseDataModel):

    def __init__(self, pool_id=None, type=None, cookie_name=None,
                 pool=None, persistence_timeout=None,
                 persistence_granularity=None):
        self.pool_id = pool_id
        self.type = type
        self.cookie_name = cookie_name
        self.pool = pool
        self.persistence_timeout = persistence_timeout
        self.persistence_granularity = persistence_granularity

    def delete(self):
        self.pool.session_persistence = None


class ListenerStatistics(BaseDataModel):

    def __init__(self, listener_id=None, amphora_id=None, bytes_in=0,
                 bytes_out=0, active_connections=0,
                 total_connections=0, request_errors=0):
        self.listener_id = listener_id
        self.amphora_id = amphora_id
        self.bytes_in = bytes_in
        self.bytes_out = bytes_out
        self.active_connections = active_connections
        self.total_connections = total_connections
        self.request_errors = request_errors

    def get_stats(self):
        stats = {
            'bytes_in': self.bytes_in,
            'bytes_out': self.bytes_out,
            'active_connections': self.active_connections,
            'total_connections': self.total_connections,
            'request_errors': self.request_errors,
        }
        return stats

    def __iadd__(self, other):

        if isinstance(other, ListenerStatistics):
            self.bytes_in += other.bytes_in
            self.bytes_out += other.bytes_out
            self.request_errors += other.request_errors
            self.total_connections += other.total_connections

        return self


class LoadBalancerStatistics(BaseDataModel):

    def __init__(self, bytes_in=0, bytes_out=0, active_connections=0,
                 total_connections=0, request_errors=0, listeners=None):
        self.bytes_in = bytes_in
        self.bytes_out = bytes_out
        self.active_connections = active_connections
        self.total_connections = total_connections
        self.request_errors = request_errors
        self.listeners = listeners or []

    def get_stats(self):
        stats = {
            'bytes_in': self.bytes_in,
            'bytes_out': self.bytes_out,
            'active_connections': self.active_connections,
            'total_connections': self.total_connections,
            'request_errors': self.request_errors,
        }
        return stats


class HealthMonitor(BaseDataModel):

    def __init__(self, id=None, project_id=None, pool_id=None, type=None,
                 delay=None, timeout=None, fall_threshold=None,
                 rise_threshold=None, http_method=None, url_path=None,
                 expected_codes=None, enabled=None, pool=None, name=None,
                 provisioning_status=None, operating_status=None,
                 created_at=None, updated_at=None, tags=None,
                 http_version=None, domain_name=None):
        self.id = id
        self.project_id = project_id
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
        self.provisioning_status = provisioning_status
        self.operating_status = operating_status
        self.name = name
        self.created_at = created_at
        self.updated_at = updated_at
        self.tags = tags
        self.http_version = http_version
        self.domain_name = domain_name

    def delete(self):
        self.pool.health_monitor = None


class Pool(BaseDataModel):
    def __init__(self, id=None, project_id=None, name=None, description=None,
                 protocol=None, lb_algorithm=None, enabled=None,
                 operating_status=None, members=None, health_monitor=None,
                 session_persistence=None, load_balancer_id=None,
                 load_balancer=None, listeners=None, l7policies=None,
                 created_at=None, updated_at=None, provisioning_status=None,
                 tags=None, tls_certificate_id=None,
                 ca_tls_certificate_id=None, crl_container_id=None,
                 tls_enabled=None):
        self.id = id
        self.project_id = project_id
        self.name = name
        self.description = description
        self.load_balancer_id = load_balancer_id
        self.load_balancer = load_balancer
        self.protocol = protocol
        self.lb_algorithm = lb_algorithm
        self.enabled = enabled
        self.operating_status = operating_status
        self.members = members or []
        self.health_monitor = health_monitor
        self.session_persistence = session_persistence
        self.listeners = listeners or []
        self.l7policies = l7policies or []
        self.created_at = created_at
        self.updated_at = updated_at
        self.provisioning_status = provisioning_status
        self.tags = tags
        self.tls_certificate_id = tls_certificate_id
        self.ca_tls_certificate_id = ca_tls_certificate_id
        self.crl_container_id = crl_container_id
        self.tls_enabled = tls_enabled

    def update(self, update_dict):
        for key, value in update_dict.items():
            if key == 'session_persistence':
                if value is None or value == {}:
                    if self.session_persistence is not None:
                        self.session_persistence.delete()
                elif self.session_persistence is not None:
                    self.session_persistence.update(value)
                else:
                    value.update({'pool_id': self.id})
                    self.session_persistence = SessionPersistence(**value)
            else:
                setattr(self, key, value)

    def delete(self):
        for listener in self.listeners:
            if listener.default_pool_id == self.id:
                listener.default_pool = None
                listener.default_pool_id = None
            for pool in listener.pools:
                if pool.id == self.id:
                    listener.pools.remove(pool)
                    break
        for pool in self.load_balancer.pools:
            if pool.id == self.id:
                self.load_balancer.pools.remove(pool)
                break
        for l7policy in self.l7policies:
            if l7policy.redirect_pool_id == self.id:
                # Technically this should never happen, as we block deletion
                # of pools in use by L7Policies at the API. However, we should
                # probably keep this here in case the data model gets
                # manipulated in some other way in the future.
                l7policy.action = constants.L7POLICY_ACTION_REJECT
                l7policy.redirect_pool = None
                l7policy.redirect_pool_id = None


class Member(BaseDataModel):

    def __init__(self, id=None, project_id=None, pool_id=None, ip_address=None,
                 protocol_port=None, weight=None, backup=None, enabled=None,
                 subnet_id=None, operating_status=None, pool=None,
                 created_at=None, updated_at=None, provisioning_status=None,
                 name=None, monitor_address=None, monitor_port=None,
                 tags=None):
        self.id = id
        self.project_id = project_id
        self.pool_id = pool_id
        self.ip_address = ip_address
        self.protocol_port = protocol_port
        self.weight = weight
        self.backup = backup
        self.enabled = enabled
        self.subnet_id = subnet_id
        self.operating_status = operating_status
        self.pool = pool
        self.created_at = created_at
        self.updated_at = updated_at
        self.provisioning_status = provisioning_status
        self.name = name
        self.monitor_address = monitor_address
        self.monitor_port = monitor_port
        self.tags = tags

    def delete(self):
        for mem in self.pool.members:
            if mem.id == self.id:
                self.pool.members.remove(mem)
                break


class Listener(BaseDataModel):

    def __init__(self, id=None, project_id=None, name=None, description=None,
                 default_pool_id=None, load_balancer_id=None, protocol=None,
                 protocol_port=None, connection_limit=None,
                 enabled=None, provisioning_status=None, operating_status=None,
                 tls_certificate_id=None, stats=None, default_pool=None,
                 load_balancer=None, sni_containers=None, peer_port=None,
                 l7policies=None, pools=None, insert_headers=None,
                 created_at=None, updated_at=None,
                 timeout_client_data=None, timeout_member_connect=None,
                 timeout_member_data=None, timeout_tcp_inspect=None,
                 tags=None, client_ca_tls_certificate_id=None,
                 client_authentication=None, client_crl_container_id=None,
                 allowed_cidrs=None):
        self.id = id
        self.project_id = project_id
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
        self.sni_containers = sni_containers or []
        self.peer_port = peer_port
        self.l7policies = l7policies or []
        self.insert_headers = insert_headers or {}
        self.pools = pools or []
        self.created_at = created_at
        self.updated_at = updated_at
        self.timeout_client_data = timeout_client_data
        self.timeout_member_connect = timeout_member_connect
        self.timeout_member_data = timeout_member_data
        self.timeout_tcp_inspect = timeout_tcp_inspect
        self.tags = tags
        self.client_ca_tls_certificate_id = client_ca_tls_certificate_id
        self.client_authentication = client_authentication
        self.client_crl_container_id = client_crl_container_id
        self.allowed_cidrs = allowed_cidrs or []

    def update(self, update_dict):
        for key, value in update_dict.items():
            setattr(self, key, value)
            if key == 'default_pool_id':
                if self.default_pool is not None:
                    l7_pool_ids = [p.redirect_pool_id for p in self.l7policies
                                   if p.redirect_pool_id is not None and
                                   p.l7rules and p.enabled is True]
                    old_pool = self.default_pool
                    if old_pool.id not in l7_pool_ids:
                        if old_pool in self.pools:
                            self.pools.remove(old_pool)
                        if self in old_pool.listeners:
                            old_pool.listeners.remove(self)
                if value is not None:
                    pool = self._find_in_graph('Pool' + value)
                    if pool not in self.pools:
                        self.pools.append(pool)
                    if self not in pool.listeners:
                        pool.listeners.append(self)
                else:
                    pool = None
                setattr(self, 'default_pool', pool)

    def delete(self):
        for listener in self.load_balancer.listeners:
            if listener.id == self.id:
                self.load_balancer.listeners.remove(listener)
                break
        for pool in self.pools:
            pool.listeners.remove(self)


class LoadBalancer(BaseDataModel):

    def __init__(self, id=None, project_id=None, name=None, description=None,
                 provisioning_status=None, operating_status=None, enabled=None,
                 topology=None, vip=None, listeners=None, amphorae=None,
                 pools=None, vrrp_group=None, server_group_id=None,
                 created_at=None, updated_at=None, provider=None, tags=None,
                 flavor_id=None):

        self.id = id
        self.project_id = project_id
        self.name = name
        self.description = description
        self.provisioning_status = provisioning_status
        self.operating_status = operating_status
        self.enabled = enabled
        self.vip = vip
        self.vrrp_group = vrrp_group
        self.topology = topology
        self.listeners = listeners or []
        self.amphorae = amphorae or []
        self.pools = pools or []
        self.server_group_id = server_group_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.provider = provider
        self.tags = tags or []
        self.flavor_id = flavor_id

    def update(self, update_dict):
        for key, value in update_dict.items():
            if key == 'vip':
                if self.vip is not None:
                    self.vip.update(value)
                else:
                    value.update({'load_balancer_id': self.id})
                    self.vip = Vip(**value)
            else:
                setattr(self, key, value)


class VRRPGroup(BaseDataModel):

    def __init__(self, load_balancer_id=None, vrrp_group_name=None,
                 vrrp_auth_type=None, vrrp_auth_pass=None, advert_int=None,
                 smtp_server=None, smtp_connect_timeout=None,
                 load_balancer=None):
        self.load_balancer_id = load_balancer_id
        self.vrrp_group_name = vrrp_group_name
        self.vrrp_auth_type = vrrp_auth_type
        self.vrrp_auth_pass = vrrp_auth_pass
        self.advert_int = advert_int
        self.load_balancer = load_balancer


class Vip(BaseDataModel):

    def __init__(self, load_balancer_id=None, ip_address=None,
                 subnet_id=None, network_id=None, port_id=None,
                 load_balancer=None, qos_policy_id=None, octavia_owned=None):
        self.load_balancer_id = load_balancer_id
        self.ip_address = ip_address
        self.subnet_id = subnet_id
        self.network_id = network_id
        self.port_id = port_id
        self.load_balancer = load_balancer
        self.qos_policy_id = qos_policy_id
        self.octavia_owned = octavia_owned


class SNI(BaseDataModel):

    def __init__(self, listener_id=None, position=None, listener=None,
                 tls_container_id=None):
        self.listener_id = listener_id
        self.position = position
        self.listener = listener
        self.tls_container_id = tls_container_id


class TLSContainer(BaseDataModel):

    def __init__(self, id=None, primary_cn=None, certificate=None,
                 private_key=None, passphrase=None, intermediates=None):
        self.id = id
        self.primary_cn = primary_cn
        self.certificate = certificate
        self.private_key = private_key
        self.passphrase = passphrase
        self.intermediates = intermediates or []


class Amphora(BaseDataModel):

    def __init__(self, id=None, load_balancer_id=None, compute_id=None,
                 status=None, lb_network_ip=None, vrrp_ip=None,
                 ha_ip=None, vrrp_port_id=None, ha_port_id=None,
                 load_balancer=None, role=None, cert_expiration=None,
                 cert_busy=False, vrrp_interface=None, vrrp_id=None,
                 vrrp_priority=None, cached_zone=None, created_at=None,
                 updated_at=None, image_id=None, compute_flavor=None):
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
        self.vrrp_interface = vrrp_interface
        self.vrrp_id = vrrp_id
        self.vrrp_priority = vrrp_priority
        self.load_balancer = load_balancer
        self.cert_expiration = cert_expiration
        self.cert_busy = cert_busy
        self.cached_zone = cached_zone
        self.created_at = created_at
        self.updated_at = updated_at
        self.image_id = image_id
        self.compute_flavor = compute_flavor

    def delete(self):
        for amphora in self.load_balancer.amphorae:
            if amphora.id == self.id:
                self.load_balancer.amphorae.remove(amphora)
                break


class AmphoraHealth(BaseDataModel):

    def __init__(self, amphora_id=None, last_update=None, busy=False):
        self.amphora_id = amphora_id
        self.last_update = last_update
        self.busy = busy


class L7Rule(BaseDataModel):

    def __init__(self, id=None, l7policy_id=None, type=None, enabled=None,
                 compare_type=None, key=None, value=None, l7policy=None,
                 invert=False, provisioning_status=None, operating_status=None,
                 project_id=None, created_at=None, updated_at=None, tags=None):
        self.id = id
        self.l7policy_id = l7policy_id
        self.type = type
        self.compare_type = compare_type
        self.key = key
        self.value = value
        self.l7policy = l7policy
        self.invert = invert
        self.provisioning_status = provisioning_status
        self.operating_status = operating_status
        self.project_id = project_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.enabled = enabled
        self.tags = tags

    def delete(self):
        if len(self.l7policy.l7rules) == 1:
            # l7policy should disappear from pool and listener lists. Since
            # we are operating only on the data model, we can fake this by
            # calling the policy's delete method.
            self.l7policy.delete()
        for r in self.l7policy.l7rules:
            if r.id == self.id:
                self.l7policy.l7rules.remove(r)
                break


class L7Policy(BaseDataModel):

    def __init__(self, id=None, name=None, description=None, listener_id=None,
                 action=None, redirect_pool_id=None, redirect_url=None,
                 position=None, listener=None, redirect_pool=None,
                 enabled=None, l7rules=None, provisioning_status=None,
                 operating_status=None, project_id=None, created_at=None,
                 updated_at=None, redirect_prefix=None, tags=None,
                 redirect_http_code=None):
        self.id = id
        self.name = name
        self.description = description
        self.listener_id = listener_id
        self.action = action
        self.redirect_pool_id = redirect_pool_id
        self.redirect_url = redirect_url
        self.position = position
        self.listener = listener
        self.redirect_pool = redirect_pool
        self.enabled = enabled
        self.l7rules = l7rules or []
        self.provisioning_status = provisioning_status
        self.operating_status = operating_status
        self.project_id = project_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.redirect_prefix = redirect_prefix
        self.tags = tags
        self.redirect_http_code = redirect_http_code

    def _conditionally_remove_pool_links(self, pool):
        """Removes links to the given pool from parent objects.

        Note this only happens if our listener isn't referencing the pool
        via its default_pool or another active l7policy's redirect_pool_id.
        """
        if (self.listener.default_pool is not None and
                pool is not None and
                pool.id != self.listener.default_pool.id and
                pool in self.listener.pools):
            listener_l7pools = [
                p.redirect_pool for p in self.listener.l7policies
                if p.redirect_pool is not None and
                p.l7rules and p.enabled is True and
                p.id != self.id]
            if pool not in listener_l7pools:
                self.listener.pools.remove(pool)
                pool.listeners.remove(self.listener)

    def update(self, update_dict):
        for key, value in update_dict.items():
            if key == 'redirect_pool_id' and value is not None:
                self._conditionally_remove_pool_links(self.redirect_pool)
                self.action = constants.L7POLICY_ACTION_REDIRECT_TO_POOL
                self.redirect_url = None
                self.redirect_http_code = None
                pool = self._find_in_graph('Pool' + value)
                self.redirect_pool = pool
                if self.l7rules and (self.enabled is True or (
                        'enabled' in update_dict.keys() and
                        update_dict['enabled'] is True)):
                    if pool not in self.listener.pools:
                        self.listener.pools.append(pool)
                    if self.listener not in pool.listeners:
                        pool.listeners.append(self.listener)
            elif key == 'redirect_url' and value is not None:
                self.action = constants.L7POLICY_ACTION_REDIRECT_TO_URL
                self._conditionally_remove_pool_links(self.redirect_pool)
                self.redirect_pool = None
                self.redirect_pool_id = None
            elif key == 'action' and value == constants.L7POLICY_ACTION_REJECT:
                self.redirect_url = None
                self._conditionally_remove_pool_links(self.redirect_pool)
                self.redirect_pool = None
                self.redirect_pool_id = None
                self.redirect_http_code = None
            elif key == 'position':
                self.listener.l7policies.remove(self)
                self.listener.l7policies.insert(value - 1, self)
            elif key == 'enabled':
                if (value is True and self.action ==
                        constants.L7POLICY_ACTION_REDIRECT_TO_POOL and
                        self.redirect_pool is not None and
                        self.l7rules and
                        self.redirect_pool not in self.listener.pools):
                    self.listener.pools.append(self.redirect_pool)
                    self.redirect_pool.listeners.append(self.listener)
                elif (value is False and self.action ==
                        constants.L7POLICY_ACTION_REDIRECT_TO_POOL and
                        self.redirect_pool is not None):
                    self._conditionally_remove_pool_links(
                        self.redirect_pool)
            setattr(self, key, value)

    def delete(self):
        self._conditionally_remove_pool_links(self.redirect_pool)
        if self.redirect_pool:
            for p in self.redirect_pool.l7policies:
                if p.id == self.id:
                    self.redirect_pool.l7policies.remove(p)
        for p in self.listener.l7policies:
            if p.id == self.id:
                self.listener.l7policies.remove(p)
                break


class Quotas(BaseDataModel):

    def __init__(self,
                 project_id=None,
                 load_balancer=None,
                 listener=None,
                 pool=None,
                 health_monitor=None,
                 member=None,
                 in_use_health_monitor=None,
                 in_use_listener=None,
                 in_use_load_balancer=None,
                 in_use_member=None,
                 in_use_pool=None):
        self.project_id = project_id
        self.health_monitor = health_monitor
        self.listener = listener
        self.load_balancer = load_balancer
        self.pool = pool
        self.member = member
        self.in_use_health_monitor = in_use_health_monitor
        self.in_use_listener = in_use_listener
        self.in_use_load_balancer = in_use_load_balancer
        self.in_use_member = in_use_member
        self.in_use_pool = in_use_pool


class Flavor(BaseDataModel):

    def __init__(self, id=None, name=None,
                 description=None, enabled=None,
                 flavor_profile_id=None):
        self.id = id
        self.name = name
        self.description = description
        self.enabled = enabled
        self.flavor_profile_id = flavor_profile_id


class FlavorProfile(BaseDataModel):

    def __init__(self, id=None, name=None, provider_name=None,
                 flavor_data=None):
        self.id = id
        self.name = name
        self.provider_name = provider_name
        self.flavor_data = flavor_data


class ListenerCidr(BaseDataModel):

    def __init__(self, listener_id=None, cidr=None):
        self.listener_id = listener_id
        self.cidr = cidr

    # SQLAlchemy kindly attaches the whole listener object so
    # let's keep this simple by overriding the to_dict for this
    # object. Otherwise we recurse down the "ghost" listener object.
    def to_dict(self, **kwargs):
        return {'cidr': self.cidr, 'listener_id': self.listener_id}
