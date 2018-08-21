# Copyright 2014 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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
#

import collections

from oslo_config import cfg

from octavia.common import constants
from octavia.tests.unit.common.sample_configs import sample_certs

CONF = cfg.CONF


def sample_amphora_tuple():
    in_amphora = collections.namedtuple(
        'amphora', 'id, lb_network_ip, vrrp_ip, ha_ip, vrrp_port_id, '
                   'ha_port_id, role, status, vrrp_interface,'
                   'vrrp_priority')
    return in_amphora(
        id='sample_amphora_id_1',
        lb_network_ip='10.0.1.1',
        vrrp_ip='10.1.1.1',
        ha_ip='192.168.10.1',
        vrrp_port_id='1234',
        ha_port_id='1234',
        role=None,
        status='ACTIVE',
        vrrp_interface=None,
        vrrp_priority=None)

RET_PERSISTENCE = {
    'type': 'HTTP_COOKIE',
    'cookie_name': None}

RET_MONITOR_1 = {
    'id': 'sample_monitor_id_1',
    'type': 'HTTP',
    'delay': 30,
    'timeout': 31,
    'fall_threshold': 3,
    'rise_threshold': 2,
    'http_method': 'GET',
    'url_path': '/index.html',
    'expected_codes': '418',
    'enabled': True}

RET_MONITOR_2 = {
    'id': 'sample_monitor_id_2',
    'type': 'HTTP',
    'delay': 30,
    'timeout': 31,
    'fall_threshold': 3,
    'rise_threshold': 2,
    'http_method': 'GET',
    'url_path': '/healthmon.html',
    'expected_codes': '418',
    'enabled': True}

RET_MEMBER_1 = {
    'id': 'sample_member_id_1',
    'address': '10.0.0.99',
    'protocol_port': 82,
    'weight': 13,
    'subnet_id': '10.0.0.1/24',
    'enabled': True,
    'operating_status': 'ACTIVE',
    'monitor_address': None,
    'monitor_port': None,
    'backup': False}

RET_MEMBER_2 = {
    'id': 'sample_member_id_2',
    'address': '10.0.0.98',
    'protocol_port': 82,
    'weight': 13,
    'subnet_id': '10.0.0.1/24',
    'enabled': True,
    'operating_status': 'ACTIVE',
    'monitor_address': None,
    'monitor_port': None,
    'backup': False}

RET_MEMBER_3 = {
    'id': 'sample_member_id_3',
    'address': '10.0.0.97',
    'protocol_port': 82,
    'weight': 13,
    'subnet_id': '10.0.0.1/24',
    'enabled': True,
    'operating_status': 'ACTIVE',
    'monitor_address': None,
    'monitor_port': None,
    'backup': False}

RET_POOL_1 = {
    'id': 'sample_pool_id_1',
    'protocol': 'http',
    'lb_algorithm': 'roundrobin',
    'members': [RET_MEMBER_1, RET_MEMBER_2],
    'health_monitor': RET_MONITOR_1,
    'session_persistence': RET_PERSISTENCE,
    'enabled': True,
    'operating_status': 'ACTIVE',
    'stick_size': '10k'}

RET_POOL_2 = {
    'id': 'sample_pool_id_2',
    'protocol': 'http',
    'lb_algorithm': 'roundrobin',
    'members': [RET_MEMBER_3],
    'health_monitor': RET_MONITOR_2,
    'session_persistence': RET_PERSISTENCE,
    'enabled': True,
    'operating_status': 'ACTIVE',
    'stick_size': '10k'}

RET_DEF_TLS_CONT = {'id': 'cont_id_1', 'allencompassingpem': 'imapem',
                    'primary_cn': 'FakeCn'}
RET_SNI_CONT_1 = {'id': 'cont_id_2', 'allencompassingpem': 'imapem2',
                  'primary_cn': 'FakeCn'}
RET_SNI_CONT_2 = {'id': 'cont_id_3', 'allencompassingpem': 'imapem3',
                  'primary_cn': 'FakeCn2'}

RET_L7RULE_1 = {
    'id': 'sample_l7rule_id_1',
    'type': constants.L7RULE_TYPE_PATH,
    'compare_type': constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
    'key': None,
    'value': '/api',
    'invert': False,
    'enabled': True}

RET_L7RULE_2 = {
    'id': 'sample_l7rule_id_2',
    'type': constants.L7RULE_TYPE_HEADER,
    'compare_type': constants.L7RULE_COMPARE_TYPE_CONTAINS,
    'key': 'Some-header',
    'value': 'This\\ string\\\\\\ with\\ stuff',
    'invert': True,
    'enabled': True}

RET_L7RULE_3 = {
    'id': 'sample_l7rule_id_3',
    'type': constants.L7RULE_TYPE_COOKIE,
    'compare_type': constants.L7RULE_COMPARE_TYPE_REGEX,
    'key': 'some-cookie',
    'value': 'this.*|that',
    'invert': False,
    'enabled': True}

RET_L7RULE_4 = {
    'id': 'sample_l7rule_id_4',
    'type': constants.L7RULE_TYPE_FILE_TYPE,
    'compare_type': constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
    'key': None,
    'value': 'jpg',
    'invert': False,
    'enabled': True}

RET_L7RULE_5 = {
    'id': 'sample_l7rule_id_5',
    'type': constants.L7RULE_TYPE_HOST_NAME,
    'compare_type': constants.L7RULE_COMPARE_TYPE_ENDS_WITH,
    'key': None,
    'value': '.example.com',
    'invert': False,
    'enabled': True}

RET_L7RULE_6 = {
    'id': 'sample_l7rule_id_6',
    'type': constants.L7RULE_TYPE_HOST_NAME,
    'compare_type': constants.L7RULE_COMPARE_TYPE_ENDS_WITH,
    'key': None,
    'value': '.example.com',
    'invert': False,
    'enabled': False}

RET_L7POLICY_1 = {
    'id': 'sample_l7policy_id_1',
    'action': constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
    'redirect_pool': RET_POOL_2,
    'redirect_url': None,
    'enabled': True,
    'l7rules': [RET_L7RULE_1]}

RET_L7POLICY_2 = {
    'id': 'sample_l7policy_id_2',
    'action': constants.L7POLICY_ACTION_REDIRECT_TO_URL,
    'redirect_pool': None,
    'redirect_url': 'http://www.example.com',
    'enabled': True,
    'l7rules': [RET_L7RULE_2, RET_L7RULE_3]}

RET_L7POLICY_3 = {
    'id': 'sample_l7policy_id_3',
    'action': constants.L7POLICY_ACTION_REJECT,
    'redirect_pool': None,
    'redirect_url': None,
    'enabled': True,
    'l7rules': [RET_L7RULE_4, RET_L7RULE_5]}

RET_L7POLICY_4 = {
    'id': 'sample_l7policy_id_4',
    'action': constants.L7POLICY_ACTION_REJECT,
    'redirect_pool': None,
    'redirect_url': None,
    'enabled': True,
    'l7rules': []}

RET_L7POLICY_5 = {
    'id': 'sample_l7policy_id_5',
    'action': constants.L7POLICY_ACTION_REJECT,
    'redirect_pool': None,
    'redirect_url': None,
    'enabled': False,
    'l7rules': [RET_L7RULE_5]}

RET_L7POLICY_6 = {
    'id': 'sample_l7policy_id_6',
    'action': constants.L7POLICY_ACTION_REJECT,
    'redirect_pool': None,
    'redirect_url': None,
    'enabled': True,
    'l7rules': []}

RET_LISTENER = {
    'id': 'sample_listener_id_1',
    'protocol_port': '80',
    'protocol': 'HTTP',
    'protocol_mode': 'http',
    'default_pool': RET_POOL_1,
    'connection_limit': constants.HAPROXY_MAX_MAXCONN,
    'amphorae': [sample_amphora_tuple()],
    'peer_port': 1024,
    'topology': 'SINGLE',
    'pools': [RET_POOL_1],
    'l7policies': [],
    'enabled': True,
    'insert_headers': {},
    'timeout_client_data': 50000,
    'timeout_member_connect': 5000,
    'timeout_member_data': 50000,
    'timeout_tcp_inspect': 0,
}

RET_LISTENER_L7 = {
    'id': 'sample_listener_id_1',
    'protocol_port': '80',
    'protocol': 'HTTP',
    'protocol_mode': 'http',
    'default_pool': RET_POOL_1,
    'connection_limit': constants.HAPROXY_MAX_MAXCONN,
    'amphorae': [sample_amphora_tuple()],
    'peer_port': 1024,
    'topology': 'SINGLE',
    'pools': [RET_POOL_1, RET_POOL_2],
    'l7policies': [RET_L7POLICY_1, RET_L7POLICY_2, RET_L7POLICY_3,
                   RET_L7POLICY_4, RET_L7POLICY_5, RET_L7POLICY_6],
    'enabled': True,
    'insert_headers': {},
    'timeout_client_data': 50000,
    'timeout_member_connect': 5000,
    'timeout_member_data': 50000,
    'timeout_tcp_inspect': 0,
}

RET_LISTENER_TLS = {
    'id': 'sample_listener_id_1',
    'protocol_port': '443',
    'protocol': 'TERMINATED_HTTPS',
    'protocol_mode': 'http',
    'default_pool': RET_POOL_1,
    'connection_limit': constants.HAPROXY_MAX_MAXCONN,
    'tls_certificate_id': 'cont_id_1',
    'default_tls_path': '/etc/ssl/sample_loadbalancer_id_1/fakeCN.pem',
    'default_tls_container': RET_DEF_TLS_CONT,
    'pools': [RET_POOL_1],
    'l7policies': [],
    'enabled': True,
    'insert_headers': {}}

RET_LISTENER_TLS_SNI = {
    'id': 'sample_listener_id_1',
    'protocol_port': '443',
    'protocol': 'http',
    'protocol': 'TERMINATED_HTTPS',
    'default_pool': RET_POOL_1,
    'connection_limit': constants.HAPROXY_MAX_MAXCONN,
    'tls_certificate_id': 'cont_id_1',
    'default_tls_path': '/etc/ssl/sample_loadbalancer_id_1/fakeCN.pem',
    'default_tls_container': RET_DEF_TLS_CONT,
    'crt_dir': '/v2/sample_loadbalancer_id_1',
    'sni_container_ids': ['cont_id_2', 'cont_id_3'],
    'sni_containers': [RET_SNI_CONT_1, RET_SNI_CONT_2],
    'pools': [RET_POOL_1],
    'l7policies': [],
    'enabled': True,
    'insert_headers': {}}

RET_AMPHORA = {
    'id': 'sample_amphora_id_1',
    'lb_network_ip': '10.0.1.1',
    'vrrp_ip': '10.1.1.1',
    'ha_ip': '192.168.10.1',
    'vrrp_port_id': '1234',
    'ha_port_id': '1234',
    'role': None,
    'status': 'ACTIVE',
    'vrrp_interface': None,
    'vrrp_priority': None}

RET_LB = {
    'host_amphora': RET_AMPHORA,
    'id': 'sample_loadbalancer_id_1',
    'vip_address': '10.0.0.2',
    'listener': RET_LISTENER,
    'topology': 'SINGLE',
    'enabled': True,
    'global_connection_limit': constants.HAPROXY_MAX_MAXCONN}

RET_LB_L7 = {
    'host_amphora': RET_AMPHORA,
    'id': 'sample_loadbalancer_id_1',
    'vip_address': '10.0.0.2',
    'listener': RET_LISTENER_L7,
    'topology': 'SINGLE',
    'enabled': True,
    'global_connection_limit': constants.HAPROXY_MAX_MAXCONN}

UDP_SOURCE_IP_BODY = {
    'type': constants.SESSION_PERSISTENCE_SOURCE_IP,
    'persistence_timeout': 33,
    'persistence_granularity': '255.0.0.0'
}

RET_UDP_HEALTH_MONITOR = {
    'id': 'sample_monitor_id_1',
    'type': constants.HEALTH_MONITOR_UDP_CONNECT,
    'delay': 30,
    'timeout': 31,
    'enabled': True,
    'fall_threshold': 3,
    'check_script_path': (CONF.haproxy_amphora.base_path +
                          '/lvs/check/udp_check.sh')
}

UDP_HEALTH_MONITOR_NO_SCRIPT = {
    'id': 'sample_monitor_id_1',
    'check_script_path': None,
    'delay': 30,
    'enabled': True,
    'fall_threshold': 3,
    'timeout': 31,
    'type': 'UDP'
}

RET_UDP_MEMBER = {
    'id': 'member_id_1',
    'address': '192.0.2.10',
    'protocol_port': 82,
    'weight': 13,
    'enabled': True
}

UDP_MEMBER_1 = {
    'id': 'sample_member_id_1',
    'address': '10.0.0.99',
    'enabled': True,
    'protocol_port': 82,
    'weight': 13
}

UDP_MEMBER_2 = {
    'id': 'sample_member_id_2',
    'address': '10.0.0.98',
    'enabled': True,
    'protocol_port': 82,
    'weight': 13
}

RET_UDP_POOL = {
    'id': 'sample_pool_id_1',
    'enabled': True,
    'health_monitor': UDP_HEALTH_MONITOR_NO_SCRIPT,
    'lb_algorithm': 'rr',
    'members': [UDP_MEMBER_1, UDP_MEMBER_2],
    'protocol': 'udp',
    'session_persistence': UDP_SOURCE_IP_BODY
}

RET_UDP_LISTENER = {
    'connection_limit': 98,
    'default_pool': {
        'id': 'sample_pool_id_1',
        'enabled': True,
        'health_monitor': RET_UDP_HEALTH_MONITOR,
        'lb_algorithm': 'rr',
        'members': [UDP_MEMBER_1, UDP_MEMBER_2],
        'protocol': 'udp',
        'session_persistence': UDP_SOURCE_IP_BODY
    },
    'enabled': True,
    'id': 'sample_listener_id_1',
    'protocol_mode': 'udp',
    'protocol_port': '80'
}


def sample_loadbalancer_tuple(proto=None, monitor=True, persistence=True,
                              persistence_type=None, tls=False, sni=False,
                              topology=None, l7=False, enabled=True):
    proto = 'HTTP' if proto is None else proto
    topology = 'SINGLE' if topology is None else topology
    in_lb = collections.namedtuple(
        'load_balancer', 'id, name, protocol, vip, listeners, amphorae,'
        ' enabled')
    return in_lb(
        id='sample_loadbalancer_id_1',
        name='test-lb',
        protocol=proto,
        vip=sample_vip_tuple(),
        topology=topology,
        listeners=[sample_listener_tuple(proto=proto, monitor=monitor,
                                         persistence=persistence,
                                         persistence_type=persistence_type,
                                         tls=tls,
                                         sni=sni,
                                         l7=l7,
                                         enabled=enabled)],
        enabled=enabled
    )


def sample_listener_loadbalancer_tuple(proto=None, topology=None,
                                       enabled=True):
    proto = 'HTTP' if proto is None else proto
    topology = 'SINGLE' if topology is None else topology
    in_lb = collections.namedtuple(
        'load_balancer', 'id, name, protocol, vip, amphorae, topology, '
        'enabled')
    return in_lb(
        id='sample_loadbalancer_id_1',
        name='test-lb',
        protocol=proto,
        vip=sample_vip_tuple(),
        amphorae=[sample_amphora_tuple()],
        topology=topology,
        enabled=enabled
    )


def sample_vrrp_group_tuple():
    in_vrrp_group = collections.namedtuple(
        'vrrp_group', 'load_balancer_id, vrrp_auth_type, vrrp_auth_pass, '
                      'advert_int, smtp_server, smtp_connect_timeout, '
                      'vrrp_group_name')
    return in_vrrp_group(
        vrrp_group_name='sample_loadbalancer_id_1',
        load_balancer_id='sample_loadbalancer_id_1',
        vrrp_auth_type='PASS',
        vrrp_auth_pass='123',
        advert_int='1',
        smtp_server='',
        smtp_connect_timeout='')


def sample_vip_tuple():
    vip = collections.namedtuple('vip', 'ip_address')
    return vip(ip_address='10.0.0.2')


def sample_listener_tuple(proto=None, monitor=True, alloc_default_pool=True,
                          persistence=True, persistence_type=None,
                          persistence_cookie=None, persistence_timeout=None,
                          persistence_granularity=None,
                          tls=False, sni=False, peer_port=None, topology=None,
                          l7=False, enabled=True, insert_headers=None,
                          be_proto=None, monitor_ip_port=False,
                          monitor_proto=None, backup_member=False,
                          disabled_member=False, connection_limit=-1,
                          timeout_client_data=50000,
                          timeout_member_connect=5000,
                          timeout_member_data=50000,
                          timeout_tcp_inspect=0):
    proto = 'HTTP' if proto is None else proto
    if be_proto is None:
        be_proto = 'HTTP' if proto is 'TERMINATED_HTTPS' else proto
    topology = 'SINGLE' if topology is None else topology
    port = '443' if proto is 'HTTPS' or proto is 'TERMINATED_HTTPS' else '80'
    peer_port = 1024 if peer_port is None else peer_port
    insert_headers = insert_headers or {}
    in_listener = collections.namedtuple(
        'listener', 'id, project_id, protocol_port, protocol, default_pool, '
                    'connection_limit, tls_certificate_id, '
                    'sni_container_ids, default_tls_container, '
                    'sni_containers, load_balancer, peer_port, pools, '
                    'l7policies, enabled, insert_headers, timeout_client_data,'
                    'timeout_member_connect, timeout_member_data, '
                    'timeout_tcp_inspect',)
    if l7:
        pools = [
            sample_pool_tuple(
                proto=be_proto, monitor=monitor, persistence=persistence,
                persistence_type=persistence_type,
                persistence_cookie=persistence_cookie,
                monitor_ip_port=monitor_ip_port, monitor_proto=monitor_proto),
            sample_pool_tuple(
                proto=be_proto, monitor=monitor, persistence=persistence,
                persistence_type=persistence_type,
                persistence_cookie=persistence_cookie, sample_pool=2,
                monitor_ip_port=monitor_ip_port, monitor_proto=monitor_proto)]
        l7policies = [
            sample_l7policy_tuple('sample_l7policy_id_1', sample_policy=1),
            sample_l7policy_tuple('sample_l7policy_id_2', sample_policy=2),
            sample_l7policy_tuple('sample_l7policy_id_3', sample_policy=3),
            sample_l7policy_tuple('sample_l7policy_id_4', sample_policy=4),
            sample_l7policy_tuple('sample_l7policy_id_5', sample_policy=5),
            sample_l7policy_tuple('sample_l7policy_id_6', sample_policy=6)]
    else:
        pools = [
            sample_pool_tuple(
                proto=be_proto, monitor=monitor, persistence=persistence,
                persistence_type=persistence_type,
                persistence_cookie=persistence_cookie,
                monitor_ip_port=monitor_ip_port, monitor_proto=monitor_proto,
                backup_member=backup_member, disabled_member=disabled_member)]
        l7policies = []
    return in_listener(
        id='sample_listener_id_1',
        project_id='12345',
        protocol_port=port,
        protocol=proto,
        load_balancer=sample_listener_loadbalancer_tuple(proto=proto,
                                                         topology=topology),
        peer_port=peer_port,
        default_pool=sample_pool_tuple(
            proto=be_proto, monitor=monitor, persistence=persistence,
            persistence_type=persistence_type,
            persistence_cookie=persistence_cookie,
            persistence_timeout=persistence_timeout,
            persistence_granularity=persistence_granularity,
            monitor_ip_port=monitor_ip_port,
            monitor_proto=monitor_proto) if alloc_default_pool else '',
        connection_limit=connection_limit,
        tls_certificate_id='cont_id_1' if tls else '',
        sni_container_ids=['cont_id_2', 'cont_id_3'] if sni else [],
        default_tls_container=sample_tls_container_tuple(
            id='cont_id_1', certificate=sample_certs.X509_CERT,
            private_key=sample_certs.X509_CERT_KEY,
            intermediates=sample_certs.X509_IMDS_LIST,
            primary_cn=sample_certs.X509_CERT_CN
        ) if tls else '',
        sni_containers=[
            sample_tls_sni_container_tuple(
                tls_container_id='cont_id_2',
                tls_container=sample_tls_container_tuple(
                    id='cont_id_2', certificate=sample_certs.X509_CERT_2,
                    private_key=sample_certs.X509_CERT_KEY_2,
                    intermediates=sample_certs.X509_IMDS_LIST,
                    primary_cn=sample_certs.X509_CERT_CN_2)),
            sample_tls_sni_container_tuple(
                tls_container_id='cont_id_3',
                tls_container=sample_tls_container_tuple(
                    id='cont_id_3', certificate=sample_certs.X509_CERT_3,
                    private_key=sample_certs.X509_CERT_KEY_3,
                    intermediates=sample_certs.X509_IMDS_LIST,
                    primary_cn=sample_certs.X509_CERT_CN_3))]
        if sni else [],
        pools=pools,
        l7policies=l7policies,
        enabled=enabled,
        insert_headers=insert_headers,
        timeout_client_data=timeout_client_data,
        timeout_member_connect=timeout_member_connect,
        timeout_member_data=timeout_member_data,
        timeout_tcp_inspect=timeout_tcp_inspect
    )


def sample_tls_sni_container_tuple(tls_container_id=None, tls_container=None):
    sc = collections.namedtuple('sni_container', 'tls_container_id, '
                                                 'tls_container')
    return sc(tls_container_id=tls_container_id, tls_container=tls_container)


def sample_tls_sni_containers_tuple(tls_container_id=None, tls_container=None):
    sc = collections.namedtuple('sni_containers', 'tls_container_id, '
                                                  'tls_container')
    return [sc(tls_container_id=tls_container_id, tls_container=tls_container)]


def sample_tls_container_tuple(id='cont_id_1', certificate=None,
                               private_key=None, intermediates=None,
                               primary_cn=None):
    sc = collections.namedtuple(
        'tls_container',
        'id, certificate, private_key, intermediates, primary_cn')
    return sc(id=id, certificate=certificate, private_key=private_key,
              intermediates=intermediates or [], primary_cn=primary_cn)


def sample_pool_tuple(proto=None, monitor=True, persistence=True,
                      persistence_type=None, persistence_cookie=None,
                      persistence_timeout=None, persistence_granularity=None,
                      sample_pool=1, monitor_ip_port=False,
                      monitor_proto=None, backup_member=False,
                      disabled_member=False):
    proto = 'HTTP' if proto is None else proto
    monitor_proto = proto if monitor_proto is None else monitor_proto
    in_pool = collections.namedtuple(
        'pool', 'id, protocol, lb_algorithm, members, health_monitor,'
                'session_persistence, enabled, operating_status')
    if (proto == constants.PROTOCOL_UDP and
            persistence_type == constants.SESSION_PERSISTENCE_SOURCE_IP):
        kwargs = {'persistence_type': persistence_type,
                  'persistence_timeout': persistence_timeout,
                  'persistence_granularity': persistence_granularity}
    else:
        kwargs = {'persistence_type': persistence_type,
                  'persistence_cookie': persistence_cookie}
    persis = sample_session_persistence_tuple(**kwargs)
    mon = None
    if sample_pool == 1:
        id = 'sample_pool_id_1'
        members = [sample_member_tuple('sample_member_id_1', '10.0.0.99',
                                       monitor_ip_port=monitor_ip_port),
                   sample_member_tuple('sample_member_id_2', '10.0.0.98',
                                       monitor_ip_port=monitor_ip_port,
                                       backup=backup_member,
                                       enabled=not disabled_member)]
        if monitor is True:
            mon = sample_health_monitor_tuple(proto=monitor_proto)
    elif sample_pool == 2:
        id = 'sample_pool_id_2'
        members = [sample_member_tuple('sample_member_id_3', '10.0.0.97',
                                       monitor_ip_port=monitor_ip_port)]
        if monitor is True:
            mon = sample_health_monitor_tuple(proto=monitor_proto, sample_hm=2)
    return in_pool(
        id=id,
        protocol=proto,
        lb_algorithm='ROUND_ROBIN',
        members=members,
        health_monitor=mon,
        session_persistence=persis if persistence is True else None,
        enabled=True,
        operating_status='ACTIVE')


def sample_member_tuple(id, ip, enabled=True, operating_status='ACTIVE',
                        monitor_ip_port=False, backup=False):
    in_member = collections.namedtuple('member',
                                       'id, ip_address, protocol_port, '
                                       'weight, subnet_id, '
                                       'enabled, operating_status, '
                                       'monitor_address, monitor_port, '
                                       'backup')
    monitor_address = '192.168.1.1' if monitor_ip_port else None
    monitor_port = 9000 if monitor_ip_port else None
    return in_member(
        id=id,
        ip_address=ip,
        protocol_port=82,
        weight=13,
        subnet_id='10.0.0.1/24',
        enabled=enabled,
        operating_status=operating_status,
        monitor_address=monitor_address,
        monitor_port=monitor_port,
        backup=backup)


def sample_session_persistence_tuple(persistence_type=None,
                                     persistence_cookie=None,
                                     persistence_timeout=None,
                                     persistence_granularity=None):
    spersistence = collections.namedtuple('SessionPersistence',
                                          'type, cookie_name, '
                                          'persistence_timeout, '
                                          'persistence_granularity')
    pt = 'HTTP_COOKIE' if persistence_type is None else persistence_type
    return spersistence(type=pt,
                        cookie_name=persistence_cookie,
                        persistence_timeout=persistence_timeout,
                        persistence_granularity=persistence_granularity)


def sample_health_monitor_tuple(proto='HTTP', sample_hm=1):
    proto = 'HTTP' if proto is 'TERMINATED_HTTPS' else proto
    monitor = collections.namedtuple(
        'monitor', 'id, type, delay, timeout, fall_threshold, rise_threshold,'
                   'http_method, url_path, expected_codes, enabled, '
                   'check_script_path')

    if sample_hm == 1:
        id = 'sample_monitor_id_1'
        url_path = '/index.html'
    elif sample_hm == 2:
        id = 'sample_monitor_id_2'
        url_path = '/healthmon.html'
    kwargs = {
        'id': id,
        'type': proto,
        'delay': 30,
        'timeout': 31,
        'fall_threshold': 3,
        'rise_threshold': 2,
        'http_method': 'GET',
        'url_path': url_path,
        'expected_codes': '418',
        'enabled': True
    }
    if proto == constants.HEALTH_MONITOR_UDP_CONNECT:
        kwargs['check_script_path'] = (CONF.haproxy_amphora.base_path +
                                       'lvs/check/' + 'udp_check.sh')
    else:
        kwargs['check_script_path'] = None
    return monitor(**kwargs)


def sample_l7policy_tuple(id,
                          action=constants.L7POLICY_ACTION_REJECT,
                          redirect_pool=None, redirect_url=None,
                          enabled=True, sample_policy=1):
    in_l7policy = collections.namedtuple('l7policy',
                                         'id, action, redirect_pool, '
                                         'redirect_url, l7rules, enabled')
    l7rules = []
    if sample_policy == 1:
        action = constants.L7POLICY_ACTION_REDIRECT_TO_POOL
        redirect_pool = sample_pool_tuple(sample_pool=2)
        l7rules = [sample_l7rule_tuple('sample_l7rule_id_1')]
    elif sample_policy == 2:
        action = constants.L7POLICY_ACTION_REDIRECT_TO_URL
        redirect_url = 'http://www.example.com'
        l7rules = [sample_l7rule_tuple('sample_l7rule_id_2', sample_rule=2),
                   sample_l7rule_tuple('sample_l7rule_id_3', sample_rule=3)]
    elif sample_policy == 3:
        action = constants.L7POLICY_ACTION_REJECT
        l7rules = [sample_l7rule_tuple('sample_l7rule_id_4', sample_rule=4),
                   sample_l7rule_tuple('sample_l7rule_id_5', sample_rule=5)]
    elif sample_policy == 4:
        action = constants.L7POLICY_ACTION_REJECT
    elif sample_policy == 5:
        action = constants.L7POLICY_ACTION_REJECT
        enabled = False
        l7rules = [sample_l7rule_tuple('sample_l7rule_id_5', sample_rule=5)]
    elif sample_policy == 6:
        action = constants.L7POLICY_ACTION_REJECT
        l7rules = [sample_l7rule_tuple('sample_l7rule_id_6', sample_rule=6)]
    return in_l7policy(
        id=id,
        action=action,
        redirect_pool=redirect_pool,
        redirect_url=redirect_url,
        l7rules=l7rules,
        enabled=enabled)


def sample_l7rule_tuple(id,
                        type=constants.L7RULE_TYPE_PATH,
                        compare_type=constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                        key=None,
                        value='/api',
                        invert=False,
                        enabled=True,
                        sample_rule=1):
    in_l7rule = collections.namedtuple('l7rule',
                                       'id, type, compare_type, '
                                       'key, value, invert, enabled')
    if sample_rule == 2:
        type = constants.L7RULE_TYPE_HEADER
        compare_type = constants.L7RULE_COMPARE_TYPE_CONTAINS
        key = 'Some-header'
        value = 'This string\\ with stuff'
        invert = True
        enabled = True
    if sample_rule == 3:
        type = constants.L7RULE_TYPE_COOKIE
        compare_type = constants.L7RULE_COMPARE_TYPE_REGEX
        key = 'some-cookie'
        value = 'this.*|that'
        invert = False
        enabled = True
    if sample_rule == 4:
        type = constants.L7RULE_TYPE_FILE_TYPE
        compare_type = constants.L7RULE_COMPARE_TYPE_EQUAL_TO
        key = None
        value = 'jpg'
        invert = False
        enabled = True
    if sample_rule == 5:
        type = constants.L7RULE_TYPE_HOST_NAME
        compare_type = constants.L7RULE_COMPARE_TYPE_ENDS_WITH
        key = None
        value = '.example.com'
        invert = False
        enabled = True
    if sample_rule == 6:
        type = constants.L7RULE_TYPE_HOST_NAME
        compare_type = constants.L7RULE_COMPARE_TYPE_ENDS_WITH
        key = None
        value = '.example.com'
        invert = False
        enabled = False
    return in_l7rule(
        id=id,
        type=type,
        compare_type=compare_type,
        key=key,
        value=value,
        invert=invert,
        enabled=enabled)


def sample_base_expected_config(frontend=None, backend=None,
                                peers=None, global_opts=None, defaults=None):
    if frontend is None:
        frontend = ("frontend sample_listener_id_1\n"
                    "    option httplog\n"
                    "    maxconn {maxconn}\n"
                    "    bind 10.0.0.2:80\n"
                    "    mode http\n"
                    "    default_backend sample_pool_id_1\n"
                    "    timeout client 50000\n\n").format(
            maxconn=constants.HAPROXY_MAX_MAXCONN)
    if backend is None:
        backend = ("backend sample_pool_id_1\n"
                   "    mode http\n"
                   "    balance roundrobin\n"
                   "    cookie SRV insert indirect nocache\n"
                   "    timeout check 31s\n"
                   "    option httpchk GET /index.html\n"
                   "    http-check expect rstatus 418\n"
                   "    fullconn {maxconn}\n"
                   "    option allbackups\n"
                   "    timeout connect 5000\n"
                   "    timeout server 50000\n"
                   "    server sample_member_id_1 10.0.0.99:82 weight 13 "
                   "check inter 30s fall 3 rise 2 cookie sample_member_id_1\n"
                   "    server sample_member_id_2 10.0.0.98:82 weight 13 "
                   "check inter 30s fall 3 rise 2 cookie sample_member_id_2\n"
                   "\n").format(maxconn=constants.HAPROXY_MAX_MAXCONN)

    if peers is None:
        peers = "\n\n"
    if global_opts is None:
        global_opts = "    maxconn {maxconn}\n\n".format(
            maxconn=constants.HAPROXY_MAX_MAXCONN)
    if defaults is None:
        defaults = ("defaults\n"
                    "    log global\n"
                    "    retries 3\n"
                    "    option redispatch\n\n")
    return ("# Configuration for loadbalancer sample_loadbalancer_id_1\n"
            "global\n"
            "    daemon\n"
            "    user nobody\n"
            "    log /dev/log local0\n"
            "    log /dev/log local1 notice\n"
            "    stats socket /var/lib/octavia/sample_listener_id_1.sock"
            " mode 0666 level user\n" +
            global_opts + defaults + peers + frontend + backend)
