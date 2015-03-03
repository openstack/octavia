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

RET_PERSISTENCE = {
    'type': 'HTTP_COOKIE',
    'cookie_name': 'HTTP_COOKIE'}

RET_MONITOR = {
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

RET_MEMBER_1 = {
    'id': 'sample_member_id_1',
    'address': '10.0.0.99',
    'protocol_port': 82,
    'weight': 13,
    'subnet_id': '10.0.0.1/24',
    'enabled': True,
    'operating_status': 'ACTIVE'}

RET_MEMBER_2 = {
    'id': 'sample_member_id_2',
    'address': '10.0.0.98',
    'protocol_port': 82,
    'weight': 13,
    'subnet_id': '10.0.0.1/24',
    'enabled': True,
    'operating_status': 'ACTIVE'}

RET_POOL = {
    'id': 'sample_pool_id_1',
    'protocol': 'http',
    'lb_algorithm': 'roundrobin',
    'members': [RET_MEMBER_1, RET_MEMBER_2],
    'health_monitor': RET_MONITOR,
    'session_persistence': RET_PERSISTENCE,
    'enabled': True,
    'operating_status': 'ACTIVE'}

RET_DEF_TLS_CONT = {'id': 'cont_id_1', 'allencompassingpem': 'imapem',
                    'primary_cn': 'FakeCn'}
RET_SNI_CONT_1 = {'id': 'cont_id_2', 'allencompassingpem': 'imapem2',
                  'primary_cn': 'FakeCn'}
RET_SNI_CONT_2 = {'id': 'cont_id_3', 'allencompassingpem': 'imapem3',
                  'primary_cn': 'FakeCn2'}

RET_LISTENER = {
    'id': 'sample_listener_id_1',
    'protocol_port': '80',
    'protocol': 'HTTP',
    'protocol_mode': 'http',
    'default_pool': RET_POOL,
    'connection_limit': 98}

RET_LISTENER_TLS = {
    'id': 'sample_listener_id_1',
    'protocol_port': '443',
    'protocol': 'TERMINATED_HTTPS',
    'protocol_mode': 'http',
    'default_pool': RET_POOL,
    'connection_limit': 98,
    'tls_certificate_id': 'cont_id_1',
    'default_tls_path': '/etc/ssl/sample_loadbalancer_id_1/fakeCN.pem',
    'default_tls_container': RET_DEF_TLS_CONT}

RET_LISTENER_TLS_SNI = {
    'id': 'sample_listener_id_1',
    'protocol_port': '443',
    'protocol': 'http',
    'protocol': 'TERMINATED_HTTPS',
    'default_pool': RET_POOL,
    'connection_limit': 98,
    'tls_certificate_id': 'cont_id_1',
    'default_tls_path': '/etc/ssl/sample_loadbalancer_id_1/fakeCN.pem',
    'default_tls_container': RET_DEF_TLS_CONT,
    'crt_dir': '/v2/sample_loadbalancer_id_1',
    'sni_container_ids': ['cont_id_2', 'cont_id_3'],
    'sni_containers': [RET_SNI_CONT_1, RET_SNI_CONT_2]}

RET_LB = {
    'name': 'test-lb',
    'vip_address': '10.0.0.2',
    'listener': RET_LISTENER}

RET_LB_TLS = {
    'name': 'test-lb',
    'vip_address': '10.0.0.2',
    'listener': RET_LISTENER_TLS}

RET_LB_TLS_SNI = {
    'name': 'test-lb',
    'vip_address': '10.0.0.2',
    'listener': RET_LISTENER_TLS_SNI}


def sample_loadbalancer_tuple(proto=None, monitor=True, persistence=True,
                              persistence_type=None, tls=False, sni=False):
    proto = 'HTTP' if proto is None else proto
    in_lb = collections.namedtuple(
        'load_balancer', 'id, name, protocol, vip, listeners, amphorae')
    return in_lb(
        id='sample_loadbalancer_id_1',
        name='test-lb',
        protocol=proto,
        vip=sample_vip_tuple(),
        listeners=[sample_listener_tuple(proto=proto, monitor=monitor,
                                         persistence=persistence,
                                         persistence_type=persistence_type,
                                         tls=tls,
                                         sni=sni)]
    )


def sample_listener_loadbalancer_tuple(proto=None):
    proto = 'HTTP' if proto is None else proto
    in_lb = collections.namedtuple(
        'load_balancer', 'id, name, protocol, vip, amphorae')
    return in_lb(
        id='sample_loadbalancer_id_1',
        name='test-lb',
        protocol=proto,
        vip=sample_vip_tuple(),
        amphorae=[sample_amphora_tuple()]
    )


def sample_vip_tuple():
    vip = collections.namedtuple('vip', 'ip_address')
    return vip(ip_address='10.0.0.2')


def sample_listener_tuple(proto=None, monitor=True, persistence=True,
                          persistence_type=None, tls=False, sni=False):
    proto = 'HTTP' if proto is None else proto
    port = '443' if proto is 'HTTPS' or proto is 'TERMINATED_HTTPS' else '80'
    in_listener = collections.namedtuple(
        'listener', 'id, protocol_port, protocol, default_pool, '
                    'connection_limit, tls_certificate_id, '
                    'sni_container_ids, default_tls_container, '
                    'sni_containers, load_balancer')
    return in_listener(
        id='sample_listener_id_1',
        protocol_port=port,
        protocol=proto,
        load_balancer=sample_listener_loadbalancer_tuple(proto=proto),
        default_pool=sample_pool_tuple(
            proto=proto, monitor=monitor, persistence=persistence,
            persistence_type=persistence_type),
        connection_limit=98,
        tls_certificate_id='cont_id_1' if tls else '',
        sni_container_ids=['cont_id_2', 'cont_id_3'] if sni else [],
        default_tls_container=sample_tls_container_tuple(
            id='cont_id_1', certificate='--imapem1--\n',
            private_key='--imakey1--\n', intermediates=[
                '--imainter1--\n', '--imainter1too--\n'],
            primary_cn='aFakeCN'
        ) if tls else '',
        sni_containers=[
            sample_tls_sni_container_tuple(
                tls_container=sample_tls_container_tuple(
                    id='cont_id_2', certificate='--imapem2--\n',
                    private_key='--imakey2--\n', intermediates=[
                        '--imainter2--\n', '--imainter2too--\n'
                    ], primary_cn='aFakeCN')),
            sample_tls_sni_container_tuple(
                tls_container=sample_tls_container_tuple(
                    id='cont_id_3', certificate='--imapem3--\n',
                    private_key='--imakey3--\n', intermediates=[
                        '--imainter3--\n', '--imainter3too--\n'
                    ], primary_cn='aFakeCN'))]
        if sni else []
    )


def sample_tls_sni_container_tuple(tls_container=None):
    sc = collections.namedtuple('sni_container', 'tls_container')
    return sc(tls_container=tls_container)


def sample_tls_sni_containers_tuple(tls_container=None):
    sc = collections.namedtuple('sni_containers', 'tls_container')
    return [sc(tls_container=tls_container)]


def sample_tls_container_tuple(id='cont_id_1', certificate=None,
                               private_key=None, intermediates=[],
                               primary_cn=None):
    sc = collections.namedtuple(
        'tls_container',
        'id, certificate, private_key, intermediates, primary_cn')
    return sc(id=id, certificate=certificate, private_key=private_key,
              intermediates=intermediates, primary_cn=primary_cn)


def sample_pool_tuple(proto=None, monitor=True, persistence=True,
                      persistence_type=None):
    proto = 'HTTP' if proto is None else proto
    in_pool = collections.namedtuple(
        'pool', 'id, protocol, lb_algorithm, members, health_monitor,'
                'session_persistence, enabled, operating_status')
    mon = sample_health_monitor_tuple(proto=proto) if monitor is True else None
    persis = sample_session_persistence_tuple(
        persistence_type=persistence_type) if persistence is True else None
    return in_pool(
        id='sample_pool_id_1',
        protocol=proto,
        lb_algorithm='ROUND_ROBIN',
        members=[sample_member_tuple('sample_member_id_1', '10.0.0.99'),
                 sample_member_tuple('sample_member_id_2', '10.0.0.98')],
        health_monitor=mon,
        session_persistence=persis,
        enabled=True,
        operating_status='ACTIVE')


def sample_member_tuple(id, ip, enabled=True, operating_status='ACTIVE'):
    in_member = collections.namedtuple('member',
                                       'id, ip_address, protocol_port, '
                                       'weight, subnet_id, '
                                       'enabled, operating_status')
    return in_member(
        id=id,
        ip_address=ip,
        protocol_port=82,
        weight=13,
        subnet_id='10.0.0.1/24',
        enabled=enabled,
        operating_status=operating_status)


def sample_session_persistence_tuple(persistence_type=None):
    spersistence = collections.namedtuple('SessionPersistence',
                                          'type, cookie_name')
    pt = 'HTTP_COOKIE' if persistence_type is None else persistence_type
    return spersistence(type=pt,
                        cookie_name=pt)


def sample_health_monitor_tuple(proto='HTTP'):
    proto = 'HTTP' if proto is 'TERMINATED_HTTPS' else proto
    monitor = collections.namedtuple(
        'monitor', 'id, type, delay, timeout, fall_threshold, rise_threshold,'
                   'http_method, url_path, expected_codes, enabled')

    return monitor(id='sample_monitor_id_1', type=proto, delay=30,
                   timeout=31, fall_threshold=3, rise_threshold=2,
                   http_method='GET', url_path='/index.html',
                   expected_codes='418', enabled=True)


def sample_amphora_tuple():
    amphora = collections.namedtuple('amphora', 'id, load_balancer_id, '
                                                'compute_id, status,'
                                                'lb_network_ip')
    return amphora(id='sample_amp_id_1', load_balancer_id='sample_lb_id_1',
                   compute_id='sample_compute_id_1', status='ACTIVE',
                   lb_network_ip='10.0.0.1')


def sample_base_expected_config(frontend=None, backend=None):
    if frontend is None:
        frontend = ("frontend sample_listener_id_1\n"
                    "    option tcplog\n"
                    "    maxconn 98\n"
                    "    option forwardfor\n"
                    "    bind 10.0.0.2:80\n"
                    "    mode http\n"
                    "    default_backend sample_pool_id_1\n\n")
    if backend is None:
        backend = ("backend sample_pool_id_1\n"
                   "    mode http\n"
                   "    balance roundrobin\n"
                   "    cookie SRV insert indirect nocache\n"
                   "    timeout check 31\n"
                   "    option httpchk GET /index.html\n"
                   "    http-check expect rstatus 418\n"
                   "    server sample_member_id_1 10.0.0.99:82 weight 13 "
                   "check inter 30s fall 3 rise 2 cookie sample_member_id_1\n"
                   "    server sample_member_id_2 10.0.0.98:82 weight 13 "
                   "check inter 30s fall 3 rise 2 cookie sample_member_id_2\n")
    return ("# Configuration for test-lb\n"
            "global\n"
            "    daemon\n"
            "    user nobody\n"
            "    group nogroup\n"
            "    log /dev/log local0\n"
            "    log /dev/log local1 notice\n"
            "    stats socket /var/lib/octavia/sample_listener_id_1.sock"
            " mode 0666 level user\n\n"
            "defaults\n"
            "    log global\n"
            "    retries 3\n"
            "    option redispatch\n"
            "    timeout connect 5000\n"
            "    timeout client 50000\n"
            "    timeout server 50000\n\n" + frontend + backend)
