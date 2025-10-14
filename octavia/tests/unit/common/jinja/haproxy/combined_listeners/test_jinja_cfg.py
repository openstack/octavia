# Copyright 2014 OpenStack Foundation
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

import copy
import os
from unittest import mock

from octavia_lib.common import constants as lib_consts
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture

from octavia.common import constants
from octavia.common.jinja.haproxy.combined_listeners import jinja_cfg
from octavia.tests.unit import base
from octavia.tests.unit.common.sample_configs import sample_configs_combined

CONF = cfg.CONF


class TestHaproxyCfg(base.TestCase):
    def setUp(self):
        super().setUp()
        self.jinja_cfg = jinja_cfg.JinjaTemplater(
            base_amp_path='/var/lib/octavia',
            base_crt_dir='/var/lib/octavia/certs')

    def test_get_template(self):
        template = self.jinja_cfg._get_template()
        self.assertEqual('haproxy.cfg.j2', template.name)

    def test_render_template_tls(self):
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group="haproxy_amphora", base_cert_dir='/fake_cert_dir')
        FAKE_CRT_LIST_FILENAME = os.path.join(
            CONF.haproxy_amphora.base_cert_dir,
            'sample_loadbalancer_id_1/sample_listener_id_1.pem')
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn {maxconn}\n"
              "    redirect scheme https if !{{ ssl_fc }}\n"
              "    http-response set-header Strict-Transport-Security "
              "\"max-age=10000000; includeSubDomains; preload;\"\n"
              "    bind 10.0.0.2:443 "
              "ssl crt-list {crt_list} "
              "ca-file /var/lib/octavia/certs/sample_loadbalancer_id_1/"
              "client_ca.pem verify required crl-file /var/lib/octavia/"
              "certs/sample_loadbalancer_id_1/SHA_ID.pem ciphers {ciphers} "
              "no-sslv3 no-tlsv10 no-tlsv11 alpn {alpn}\n"
              "    mode http\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 50000\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
            crt_list=FAKE_CRT_LIST_FILENAME,
            ciphers=constants.CIPHERS_OWASP_SUITE_B,
            alpn=",".join(constants.AMPHORA_SUPPORTED_ALPN_PROTOCOLS))
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 cookie "
              "sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        tls_tupe = {'cont_id_1':
                    sample_configs_combined.sample_tls_container_tuple(
                        id='tls_container_id',
                        certificate='imaCert1', private_key='imaPrivateKey1',
                        primary_cn='FakeCN'),
                    'cont_id_ca': 'client_ca.pem',
                    'cont_id_crl': 'SHA_ID.pem'}
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='TERMINATED_HTTPS', tls=True, sni=True,
                client_ca_cert=True, client_crl_cert=True)],
            tls_tupe)
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(
                frontend=fe, backend=be),
            rendered_obj)

    def test_render_template_tls_no_sni(self):
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group="haproxy_amphora", base_cert_dir='/fake_cert_dir')
        FAKE_CRT_LIST_FILENAME = os.path.join(
            CONF.haproxy_amphora.base_cert_dir,
            'sample_loadbalancer_id_1/sample_listener_id_1.pem')
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn {maxconn}\n"
              "    redirect scheme https if !{{ ssl_fc }}\n"
              "    http-response set-header Strict-Transport-Security "
              "\"max-age=10000000; includeSubDomains; preload;\"\n"
              "    bind 10.0.0.2:443 ssl crt-list {crt_list}"
              "   ciphers {ciphers} no-sslv3 no-tlsv10 no-tlsv11 alpn {alpn}\n"
              "    mode http\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 50000\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
            crt_list=FAKE_CRT_LIST_FILENAME,
            ciphers=constants.CIPHERS_OWASP_SUITE_B,
            alpn=",".join(constants.AMPHORA_SUPPORTED_ALPN_PROTOCOLS))
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='TERMINATED_HTTPS', tls=True)],
            tls_certs={'cont_id_1':
                       sample_configs_combined.sample_tls_container_tuple(
                           id='tls_container_id',
                           certificate='ImAalsdkfjCert',
                           private_key='ImAsdlfksdjPrivateKey',
                           primary_cn="FakeCN")})
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(
                frontend=fe, backend=be),
            rendered_obj)

    def test_render_template_tls_no_ciphers(self):
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group="haproxy_amphora", base_cert_dir='/fake_cert_dir')
        FAKE_CRT_LIST_FILENAME = os.path.join(
            CONF.haproxy_amphora.base_cert_dir,
            'sample_loadbalancer_id_1/sample_listener_id_1.pem')
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn {maxconn}\n"
              "    redirect scheme https if !{{ ssl_fc }}\n"
              "    http-response set-header Strict-Transport-Security "
              "\"max-age=10000000; includeSubDomains; preload;\"\n"
              "    bind 10.0.0.2:443 ssl crt-list {crt_list}    "
              "no-sslv3 no-tlsv10 no-tlsv11 alpn {alpn}\n"
              "    mode http\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 50000\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
            crt_list=FAKE_CRT_LIST_FILENAME,
            alpn=",".join(constants.AMPHORA_SUPPORTED_ALPN_PROTOCOLS))
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='TERMINATED_HTTPS', tls=True, tls_ciphers=None)],
            tls_certs={'cont_id_1':
                       sample_configs_combined.sample_tls_container_tuple(
                           id='tls_container_id',
                           certificate='ImAalsdkfjCert',
                           private_key='ImAsdlfksdjPrivateKey',
                           primary_cn="FakeCN")})
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(
                frontend=fe, backend=be),
            rendered_obj)

    def test_render_template_tls_no_versions(self):
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group="haproxy_amphora", base_cert_dir='/fake_cert_dir')
        FAKE_CRT_LIST_FILENAME = os.path.join(
            CONF.haproxy_amphora.base_cert_dir,
            'sample_loadbalancer_id_1/sample_listener_id_1.pem')
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn {maxconn}\n"
              "    redirect scheme https if !{{ ssl_fc }}\n"
              "    http-response set-header Strict-Transport-Security "
              "\"max-age=10000000; includeSubDomains; preload;\"\n"
              "    bind 10.0.0.2:443 "
              "ssl crt-list {crt_list} "
              "ca-file /var/lib/octavia/certs/sample_loadbalancer_id_1/"
              "client_ca.pem verify required crl-file /var/lib/octavia/"
              "certs/sample_loadbalancer_id_1/SHA_ID.pem ciphers {ciphers} "
              "alpn {alpn}\n"
              "    mode http\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 50000\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
            crt_list=FAKE_CRT_LIST_FILENAME,
            ciphers=constants.CIPHERS_OWASP_SUITE_B,
            alpn=",".join(constants.AMPHORA_SUPPORTED_ALPN_PROTOCOLS))
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 cookie "
              "sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        tls_tupe = {'cont_id_1':
                    sample_configs_combined.sample_tls_container_tuple(
                        id='tls_container_id',
                        certificate='imaCert1', private_key='imaPrivateKey1',
                        primary_cn='FakeCN'),
                    'cont_id_ca': 'client_ca.pem',
                    'cont_id_crl': 'SHA_ID.pem'}
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='TERMINATED_HTTPS', tls=True, sni=True,
                client_ca_cert=True, client_crl_cert=True, tls_versions=None)],
            tls_tupe)
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(
                frontend=fe, backend=be),
            rendered_obj)

    def test_render_template_tls_no_ciphers_or_versions(self):
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group="haproxy_amphora", base_cert_dir='/fake_cert_dir')
        FAKE_CRT_LIST_FILENAME = os.path.join(
            CONF.haproxy_amphora.base_cert_dir,
            'sample_loadbalancer_id_1/sample_listener_id_1.pem')
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn {maxconn}\n"
              "    redirect scheme https if !{{ ssl_fc }}\n"
              "    http-response set-header Strict-Transport-Security "
              "\"max-age=10000000; includeSubDomains; preload;\"\n"
              "    bind 10.0.0.2:443 ssl crt-list {crt_list}    "
              "alpn {alpn}\n"
              "    mode http\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 50000\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
            crt_list=FAKE_CRT_LIST_FILENAME,
            alpn=",".join(constants.AMPHORA_SUPPORTED_ALPN_PROTOCOLS))
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='TERMINATED_HTTPS', tls=True, tls_ciphers=None,
                tls_versions=None)],
            tls_certs={'cont_id_1':
                       sample_configs_combined.sample_tls_container_tuple(
                           id='tls_container_id',
                           certificate='ImAalsdkfjCert',
                           private_key='ImAsdlfksdjPrivateKey',
                           primary_cn="FakeCN")})
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(
                frontend=fe, backend=be),
            rendered_obj)

    def test_render_template_tls_alpn(self):
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group="haproxy_amphora", base_cert_dir='/fake_cert_dir')
        FAKE_CRT_LIST_FILENAME = os.path.join(
            CONF.haproxy_amphora.base_cert_dir,
            'sample_loadbalancer_id_1/sample_listener_id_1.pem')
        alpn_protocols = ['chip', 'dale']
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn {maxconn}\n"
              "    redirect scheme https if !{{ ssl_fc }}\n"
              "    http-response set-header Strict-Transport-Security "
              "\"max-age=10000000; includeSubDomains; preload;\"\n"
              "    bind 10.0.0.2:443 ssl crt-list {crt_list}   "
              "ciphers {ciphers} no-sslv3 no-tlsv10 no-tlsv11 alpn {alpn}\n"
              "    mode http\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 50000\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
            crt_list=FAKE_CRT_LIST_FILENAME,
            ciphers=constants.CIPHERS_OWASP_SUITE_B,
            alpn=",".join(alpn_protocols))
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='TERMINATED_HTTPS', tls=True,
                alpn_protocols=alpn_protocols)],
            tls_certs={'cont_id_1':
                       sample_configs_combined.sample_tls_container_tuple(
                           id='tls_container_id',
                           certificate='ImAalsdkfjCert',
                           private_key='ImAsdlfksdjPrivateKey',
                           primary_cn="FakeCN")})
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(
                frontend=fe, backend=be),
            rendered_obj)

    def test_render_template_tls_no_alpn(self):
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group="haproxy_amphora", base_cert_dir='/fake_cert_dir')
        FAKE_CRT_LIST_FILENAME = os.path.join(
            CONF.haproxy_amphora.base_cert_dir,
            'sample_loadbalancer_id_1/sample_listener_id_1.pem')
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn {maxconn}\n"
              "    redirect scheme https if !{{ ssl_fc }}\n"
              "    http-response set-header Strict-Transport-Security "
              "\"max-age=10000000; includeSubDomains; preload;\"\n"
              "    bind 10.0.0.2:443 ssl crt-list {crt_list}   "
              "ciphers {ciphers} no-sslv3 no-tlsv10 no-tlsv11\n"
              "    mode http\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 50000\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
            crt_list=FAKE_CRT_LIST_FILENAME,
            ciphers=constants.CIPHERS_OWASP_SUITE_B)
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='TERMINATED_HTTPS', tls=True,
                alpn_protocols=None)],
            tls_certs={'cont_id_1':
                       sample_configs_combined.sample_tls_container_tuple(
                           id='tls_container_id',
                           certificate='ImAalsdkfjCert',
                           private_key='ImAsdlfksdjPrivateKey',
                           primary_cn="FakeCN")})
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(
                frontend=fe, backend=be),
            rendered_obj)

    def test_render_template_tls_no_alpn_hsts_max_age_only(self):
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group="haproxy_amphora", base_cert_dir='/fake_cert_dir')
        FAKE_CRT_LIST_FILENAME = os.path.join(
            CONF.haproxy_amphora.base_cert_dir,
            'sample_loadbalancer_id_1/sample_listener_id_1.pem')
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn {maxconn}\n"
              "    redirect scheme https if !{{ ssl_fc }}\n"
              "    http-response set-header Strict-Transport-Security "
              "\"max-age=10000000;\"\n"
              "    bind 10.0.0.2:443 ssl crt-list {crt_list}   "
              "ciphers {ciphers} no-sslv3 no-tlsv10 no-tlsv11\n"
              "    mode http\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 50000\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
            crt_list=FAKE_CRT_LIST_FILENAME,
            ciphers=constants.CIPHERS_OWASP_SUITE_B)
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='TERMINATED_HTTPS', tls=True,
                alpn_protocols=None, hsts_include_subdomains=False,
                hsts_preload=False)],
            tls_certs={'cont_id_1':
                       sample_configs_combined.sample_tls_container_tuple(
                           id='tls_container_id',
                           certificate='ImAalsdkfjCert',
                           private_key='ImAsdlfksdjPrivateKey',
                           primary_cn="FakeCN")})
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(
                frontend=fe, backend=be),
            rendered_obj)

    def test_render_template_tls_no_hsts(self):
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group="haproxy_amphora", base_cert_dir='/fake_cert_dir')
        FAKE_CRT_LIST_FILENAME = os.path.join(
            CONF.haproxy_amphora.base_cert_dir,
            'sample_loadbalancer_id_1/sample_listener_id_1.pem')
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn {maxconn}\n"
              "    redirect scheme https if !{{ ssl_fc }}\n"
              "    bind 10.0.0.2:443 "
              "ssl crt-list {crt_list} "
              "ca-file /var/lib/octavia/certs/sample_loadbalancer_id_1/"
              "client_ca.pem verify required crl-file /var/lib/octavia/"
              "certs/sample_loadbalancer_id_1/SHA_ID.pem ciphers {ciphers} "
              "no-sslv3 no-tlsv10 no-tlsv11 alpn {alpn}\n"
              "    mode http\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 50000\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
            crt_list=FAKE_CRT_LIST_FILENAME,
            ciphers=constants.CIPHERS_OWASP_SUITE_B,
            alpn=",".join(constants.AMPHORA_SUPPORTED_ALPN_PROTOCOLS))
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 cookie "
              "sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        tls_tupe = {'cont_id_1':
                    sample_configs_combined.sample_tls_container_tuple(
                        id='tls_container_id',
                        certificate='imaCert1', private_key='imaPrivateKey1',
                        primary_cn='FakeCN'),
                    'cont_id_ca': 'client_ca.pem',
                    'cont_id_crl': 'SHA_ID.pem'}
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='TERMINATED_HTTPS', tls=True, sni=True,
                client_ca_cert=True, client_crl_cert=True,
                hsts_max_age=None)],
            tls_tupe)
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(
                frontend=fe, backend=be),
            rendered_obj)

    def test_render_template_http(self):
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple()])
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(backend=be),
            rendered_obj)

    def test_render_template_prometheus(self):
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn {maxconn}\n"
              "    bind 10.0.0.2:80\n"
              "    mode http\n"
              "    timeout client 50000\n"
              "    default_backend prometheus-exporter-internal\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        be = ""
        defaults = ("defaults\n"
                    "    log global\n"
                    "    retries 3\n"
                    "    option redispatch\n"
                    "    option splice-request\n"
                    "    option splice-response\n"
                    "    option http-keep-alive\n\n\n\n"
                    "frontend prometheus-exporter-internal-endpoint\n"
                    "    bind 127.0.0.1:9101\n"
                    "    mode http\n"
                    "    no log\n"
                    "    option http-use-htx\n"
                    "    http-request use-service prometheus-exporter if { "
                    "path /metrics }\n"
                    "    http-request reject\n"
                    "    timeout http-request 5s\n"
                    "    timeout client 5s\n"
                    "backend prometheus-exporter-internal\n"
                    "    mode http\n"
                    "    no log\n"
                    "    balance first\n"
                    "    timeout connect 5s\n"
                    "    timeout server 5s\n"
                    "    server prometheus-internal 127.0.0.1:9102")
        logging = ("    log-format 12345\\ sample_loadbalancer_id_1\\ %f\\ "
                   "%ci\\ %cp\\ %t\\ -\\ -\\ %B\\ %U\\ "
                   "%[ssl_c_verify]\\ %{+Q}[ssl_c_s_dn]\\ %b\\ %s\\ %Tt\\ "
                   "%tsc\n\n")

        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto=lib_consts.PROTOCOL_PROMETHEUS, include_pools=False)],
            feature_compatibility={lib_consts.PROTOCOL_PROMETHEUS: True})

        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(
                frontend=fe, backend=be, logging=logging, defaults=defaults),
            rendered_obj)

    def test_render_template_additional_vips(self):
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn {maxconn}\n"
              "    bind 10.0.0.2:80\n"
              "    bind 10.0.1.2:80\n"
              "    bind 2001:db8::2:80\n"
              "    mode http\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 50000\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                additional_vips=True)])
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(frontend=fe),
            rendered_obj)

    def test_render_template_member_backup(self):
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "addr 192.168.1.1 port 9000 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "addr 192.168.1.1 port 9000 "
              "cookie sample_member_id_2 backup\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                monitor_ip_port=True, backup_member=True)])
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(backend=be),
            rendered_obj)

    def test_render_template_custom_timeouts(self):
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn {maxconn}\n"
              "    bind 10.0.0.2:80\n"
              "    mode http\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 2\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 1\n"
              "    timeout server 3\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13 "
              "check inter 30s fall 3 rise 2 cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13 "
              "check inter 30s fall 3 rise 2 cookie "
              "sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                timeout_member_connect=1, timeout_client_data=2,
                timeout_member_data=3)])
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(
                frontend=fe, backend=be),
            rendered_obj)

    def test_render_template_null_timeouts(self):
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn {maxconn}\n"
              "    bind 10.0.0.2:80\n"
              "    mode http\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 50000\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13 "
              "check inter 30s fall 3 rise 2 cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13 "
              "check inter 30s fall 3 rise 2 cookie "
              "sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                timeout_member_connect=None, timeout_client_data=None,
                timeout_member_data=None)])
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(
                frontend=fe, backend=be),
            rendered_obj)

    def test_render_template_member_monitor_addr_port(self):
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "addr 192.168.1.1 port 9000 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "addr 192.168.1.1 port 9000 "
              "cookie sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                monitor_ip_port=True)])
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(backend=be),
            rendered_obj)

    def test_render_template_https_real_monitor(self):
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn {maxconn}\n"
              "    bind 10.0.0.2:443\n"
              "    mode tcp\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 50000\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        lg = ("    log-format 12345\\ sample_loadbalancer_id_1\\ %f\\ "
              "%ci\\ %cp\\ %t\\ -\\ -\\ %B\\ %U\\ "
              "%[ssl_c_verify]\\ %{+Q}[ssl_c_s_dn]\\ %b\\ %s\\ %Tt\\ "
              "%tsc\n\n")
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode tcp\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check check-ssl verify none inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check check-ssl verify none inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(proto='HTTPS')])
        self.assertEqual(sample_configs_combined.sample_base_expected_config(
            frontend=fe, logging=lg, backend=be), rendered_obj)

    def test_render_template_https_hello_monitor(self):
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn {maxconn}\n"
              "    bind 10.0.0.2:443\n"
              "    mode tcp\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 50000\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        lg = ("    log-format 12345\\ sample_loadbalancer_id_1\\ %f\\ "
              "%ci\\ %cp\\ %t\\ -\\ -\\ %B\\ %U\\ "
              "%[ssl_c_verify]\\ %{+Q}[ssl_c_s_dn]\\ %b\\ %s\\ %Tt\\ "
              "%tsc\n\n")
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode tcp\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='HTTPS', monitor_proto='TLS-HELLO')])
        self.assertEqual(sample_configs_combined.sample_base_expected_config(
            frontend=fe, logging=lg, backend=be), rendered_obj)

    def test_render_template_no_monitor_http(self):
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13 "
              "cookie sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(proto='HTTP',
                                                           monitor=False)])
        self.assertEqual(sample_configs_combined.sample_base_expected_config(
            backend=be), rendered_obj)

    def test_render_template_disabled_member(self):
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13 "
              "cookie sample_member_id_2 disabled\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='HTTP', monitor=False, disabled_member=True)])
        self.assertEqual(sample_configs_combined.sample_base_expected_config(
            backend=be), rendered_obj)

    def test_render_template_ping_monitor_http(self):
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option external-check\n"
              "    external-check command /var/lib/octavia/ping-wrapper.sh\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        go = "    maxconn {maxconn}\n    external-check\n\n".format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='HTTP', monitor_proto='PING')])
        self.assertEqual(sample_configs_combined.sample_base_expected_config(
            backend=be, global_opts=go), rendered_obj)

    def test_render_template_ping_monitor_http_insecure_fork(self):
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    load-server-state-from-file global\n"
              "    timeout check 31s\n"
              "    option external-check\n"
              "    external-check command /var/lib/octavia/ping-wrapper.sh\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        go = (
            "    server-state-file /var/lib/octavia/sample_loadbalancer_id_1/"
            "servers-state\n"
            f"    maxconn {constants.HAPROXY_DEFAULT_MAXCONN}\n"
            "    external-check\n    insecure-fork-wanted\n\n")
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='HTTP', monitor_proto='PING')],
            feature_compatibility={
                "requires_insecure_fork": True,
                constants.SERVER_STATE_FILE: True})
        self.assertEqual(sample_configs_combined.sample_base_expected_config(
            backend=be, global_opts=go), rendered_obj)

    def test_render_template_no_monitor_https(self):
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn {maxconn}\n"
              "    bind 10.0.0.2:443\n"
              "    mode tcp\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 50000\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        lg = ("    log-format 12345\\ sample_loadbalancer_id_1\\ %f\\ "
              "%ci\\ %cp\\ %t\\ -\\ -\\ %B\\ %U\\ "
              "%[ssl_c_verify]\\ %{+Q}[ssl_c_s_dn]\\ %b\\ %s\\ %Tt\\ "
              "%tsc\n\n")
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode tcp\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13 "
              "cookie sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(proto='HTTPS',
                                                           monitor=False)])
        self.assertEqual(sample_configs_combined.sample_base_expected_config(
            frontend=fe, logging=lg, backend=be), rendered_obj)

    def test_render_template_health_monitor_http_check(self):
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.1\\r\\nHost:\\ "
              "testlab.com\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='HTTP', monitor_proto='HTTP', hm_host_http_check=True)])
        self.assertEqual(sample_configs_combined.sample_base_expected_config(
            backend=be), rendered_obj)

    def test_render_template_no_persistence_https(self):
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn {maxconn}\n"
              "    bind 10.0.0.2:443\n"
              "    mode tcp\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 50000\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        lg = ("    log-format 12345\\ sample_loadbalancer_id_1\\ %f\\ "
              "%ci\\ %cp\\ %t\\ -\\ -\\ %B\\ %U\\ "
              "%[ssl_c_verify]\\ %{+Q}[ssl_c_s_dn]\\ %b\\ %s\\ %Tt\\ "
              "%tsc\n\n")
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode tcp\n"
              "    balance roundrobin\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13\n\n").format(
                  maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='HTTPS', monitor=False, persistence=False)])
        self.assertEqual(sample_configs_combined.sample_base_expected_config(
            frontend=fe, logging=lg, backend=be), rendered_obj)

    def test_render_template_no_persistence_http(self):
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13\n\n").format(
                  maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='HTTP', monitor=False, persistence=False)])
        self.assertEqual(sample_configs_combined.sample_base_expected_config(
            backend=be), rendered_obj)

    def test_render_template_sourceip_persistence(self):
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    stick-table type ipv6 size 10k\n"
              "    stick on src\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                persistence_type='SOURCE_IP')])
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(backend=be),
            rendered_obj)

    def test_render_template_appcookie_persistence(self):
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    stick-table type string len 64 size 10k\n"
              "    stick store-response res.cook(JSESSIONID)\n"
              "    stick match req.cook(JSESSIONID)\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                persistence_type='APP_COOKIE',
                persistence_cookie='JSESSIONID')])
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(backend=be),
            rendered_obj)

    def test_render_template_unlimited_connections(self):
        sample_amphora = sample_configs_combined.sample_amphora_tuple()
        sample_listener = sample_configs_combined.sample_listener_tuple(
            proto='HTTPS', monitor=False)
        fe = ("frontend {listener_id}\n"
              "    maxconn {maxconn}\n"
              "    bind 10.0.0.2:443\n"
              "    mode tcp\n"
              "    default_backend {pool_id}:{listener_id}\n"
              "    timeout client 50000\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
            pool_id=sample_listener.default_pool.id,
            listener_id=sample_listener.id)
        lg = ("    log-format 12345\\ sample_loadbalancer_id_1\\ %f\\ "
              "%ci\\ %cp\\ %t\\ -\\ -\\ %B\\ %U\\ "
              "%[ssl_c_verify]\\ %{+Q}[ssl_c_s_dn]\\ %b\\ %s\\ %Tt\\ "
              "%tsc\n\n")
        be = ("backend {pool_id}:{listener_id}\n"
              "    mode tcp\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13 "
              "cookie sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
            pool_id=sample_listener.default_pool.id,
            listener_id=sample_listener.id)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_amphora,
            [sample_listener])
        self.assertEqual(sample_configs_combined.sample_base_expected_config(
            frontend=fe, logging=lg, backend=be), rendered_obj)

    def test_render_template_limited_connections(self):
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn 2014\n"
              "    bind 10.0.0.2:443\n"
              "    mode tcp\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 50000\n")
        lg = ("    log-format 12345\\ sample_loadbalancer_id_1\\ %f\\ "
              "%ci\\ %cp\\ %t\\ -\\ -\\ %B\\ %U\\ "
              "%[ssl_c_verify]\\ %{+Q}[ssl_c_s_dn]\\ %b\\ %s\\ %Tt\\ "
              "%tsc\n\n")
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode tcp\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    fullconn 2014\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13 "
              "cookie sample_member_id_2\n\n")
        g_opts = "    maxconn 2014\n\n"
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='HTTPS', monitor=False, connection_limit=2014)])
        self.assertEqual(sample_configs_combined.sample_base_expected_config(
            frontend=fe, logging=lg, backend=be, global_opts=g_opts),
            rendered_obj)

    def test_render_template_tls_cachesize(self):
        g_opts = (f"    maxconn {constants.HAPROXY_DEFAULT_MAXCONN}\n"
                  f"    tune.ssl.cachesize 101722232\n\n")
        fe = ("frontend sample_listener_id_1\n"
              f"    maxconn {constants.HAPROXY_DEFAULT_MAXCONN}\n"
              "    redirect scheme https if !{ ssl_fc }\n"
              "    http-response set-header Strict-Transport-Security "
              "\"max-age=10000000; includeSubDomains; preload;\"\n"
              "    bind 10.0.0.2:443 "
              f"ciphers {constants.CIPHERS_OWASP_SUITE_B} "
              "no-sslv3 no-tlsv10 no-tlsv11 alpn "
              f"{','.join(constants.AMPHORA_SUPPORTED_ALPN_PROTOCOLS)}\n"
              "    mode http\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 50000\n")
        tls_tupe = {'cont_id_1':
                    sample_configs_combined.sample_tls_container_tuple(
                        id='tls_container_id',
                        certificate='imaCert1', private_key='imaPrivateKey1',
                        primary_cn='FakeCN'),
                    'cont_id_ca': 'client_ca.pem',
                    'cont_id_crl': 'SHA_ID.pem'}
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='TERMINATED_HTTPS')],
            tls_tupe,
            # 32GiB total
            amp_details={"memory": {
                "free": 32864004,
                "buffers": 32312392 // 2,
                "cached": 32312392 // 2,
            }})
        self.assertEqual(sample_configs_combined.sample_base_expected_config(
            frontend=fe, global_opts=g_opts), rendered_obj)

    def test_render_template_l7policies(self):
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn {maxconn}\n"
              "    bind 10.0.0.2:80\n"
              "    mode http\n"
              "        acl sample_l7rule_id_1 path -m beg /api\n"
              "    use_backend sample_pool_id_2:sample_listener_id_1"
              " if sample_l7rule_id_1\n"
              "        acl sample_l7rule_id_2 req.hdr(Some-header) -m sub "
              "This\\ string\\\\\\ with\\ stuff\n"
              "        acl sample_l7rule_id_3 req.cook(some-cookie) -m reg "
              "this.*|that\n"
              "    redirect code 302 location http://www.example.com if "
              "!sample_l7rule_id_2 sample_l7rule_id_3\n"
              "        acl sample_l7rule_id_4 path_end  jpg\n"
              "        acl sample_l7rule_id_5 req.hdr(host) -i -m end "
              ".example.com\n"
              "    http-request deny if sample_l7rule_id_4 "
              "sample_l7rule_id_5\n"
              "        acl sample_l7rule_id_2 req.hdr(Some-header) -m sub "
              "This\\ string\\\\\\ with\\ stuff\n"
              "        acl sample_l7rule_id_3 req.cook(some-cookie) -m reg "
              "this.*|that\n"
              "    redirect code 302 prefix https://example.com if "
              "!sample_l7rule_id_2 sample_l7rule_id_3\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 50000\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13 check "
              "inter 30s fall 3 rise 2 cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13 check "
              "inter 30s fall 3 rise 2 cookie sample_member_id_2\n"
              "\n"
              "backend sample_pool_id_2:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /healthmon.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_3 10.0.0.97:82 weight 13 check "
              "inter 30s fall 3 rise 2 cookie sample_member_id_3\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(l7=True)])
        self.assertEqual(sample_configs_combined.sample_base_expected_config(
            frontend=fe, backend=be), rendered_obj)

    def test_render_template_http_xff(self):
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    option forwardfor\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                insert_headers={'X-Forwarded-For': 'true'})])
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(backend=be),
            rendered_obj)

    def test_render_template_http_xff_xfport(self):
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    option forwardfor\n"
              "    http-request set-header X-Forwarded-Port %[dst_port]\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                insert_headers={'X-Forwarded-For': 'true',
                                'X-Forwarded-Port': 'true'})])
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(backend=be),
            rendered_obj)

    def test_render_template_pool_proxy_protocol(self):
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1 send-proxy\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2 send-proxy\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(be_proto='PROXY')])
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(backend=be),
            rendered_obj)

    def test_render_template_pool_cert(self):
        feature_compatibility = {constants.POOL_ALPN: True}
        cert_file_path = os.path.join(self.jinja_cfg.base_crt_dir,
                                      'sample_listener_id_1', 'fake path')
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13 "
              "check check-alpn {alpn} inter 30s fall 3 rise 2 cookie "
              "sample_member_id_1 {opts} alpn {alpn}\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13 "
              "check check-alpn {alpn} inter 30s fall 3 rise 2 cookie "
              "sample_member_id_2 {opts} alpn {alpn}\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
            opts="ssl crt %s verify none sni ssl_fc_sni" % cert_file_path +
                 " ciphers " + constants.CIPHERS_OWASP_SUITE_B +
                 " no-sslv3 no-tlsv10 no-tlsv11",
            alpn=",".join(constants.AMPHORA_SUPPORTED_ALPN_PROTOCOLS))
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                pool_cert=True, tls_enabled=True,
                backend_tls_ciphers=constants.CIPHERS_OWASP_SUITE_B)],
            tls_certs={
                'sample_pool_id_1':
                    {'client_cert': cert_file_path,
                     'ca_cert': None, 'crl': None}},
            feature_compatibility=feature_compatibility)
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(backend=be),
            rendered_obj)

    def test_render_template_pool_cert_no_alpn(self):
        feature_compatibility = {constants.POOL_ALPN: False}
        cert_file_path = os.path.join(self.jinja_cfg.base_crt_dir,
                                      'sample_listener_id_1', 'fake path')
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13 "
              "check inter 30s fall 3 rise 2 cookie sample_member_id_1 "
              "{opts}\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13 "
              "check inter 30s fall 3 rise 2 cookie sample_member_id_2 "
              "{opts}\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
            opts="ssl crt %s verify none sni ssl_fc_sni" % cert_file_path +
                 " ciphers " + constants.CIPHERS_OWASP_SUITE_B +
                 " no-sslv3 no-tlsv10 no-tlsv11")
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                pool_cert=True, tls_enabled=True,
                backend_tls_ciphers=constants.CIPHERS_OWASP_SUITE_B)],
            tls_certs={
                'sample_pool_id_1':
                    {'client_cert': cert_file_path,
                     'ca_cert': None, 'crl': None}},
            feature_compatibility=feature_compatibility)
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(backend=be),
            rendered_obj)

    def test_render_template_pool_cert_no_versions(self):
        feature_compatibility = {constants.POOL_ALPN: True}
        cert_file_path = os.path.join(self.jinja_cfg.base_crt_dir,
                                      'sample_listener_id_1', 'fake path')
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13 "
              "check check-alpn {alpn} inter 30s fall 3 rise 2 cookie "
              "sample_member_id_1 {opts} alpn {alpn}\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13 "
              "check check-alpn {alpn} inter 30s fall 3 rise 2 cookie "
              "sample_member_id_2 {opts} alpn {alpn}\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
            opts="ssl crt %s verify none sni ssl_fc_sni" % cert_file_path +
                 " ciphers " + constants.CIPHERS_OWASP_SUITE_B,
            alpn=",".join(constants.AMPHORA_SUPPORTED_ALPN_PROTOCOLS))
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                pool_cert=True, tls_enabled=True,
                backend_tls_ciphers=constants.CIPHERS_OWASP_SUITE_B,
                backend_tls_versions=None)],
            tls_certs={
                'sample_pool_id_1':
                    {'client_cert': cert_file_path,
                     'ca_cert': None, 'crl': None}},
            feature_compatibility=feature_compatibility)
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(backend=be),
            rendered_obj)

    def test_render_template_pool_cert_no_ciphers(self):
        feature_compatibility = {constants.POOL_ALPN: True}
        cert_file_path = os.path.join(self.jinja_cfg.base_crt_dir,
                                      'sample_listener_id_1', 'fake path')
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13 "
              "check check-alpn {alpn} inter 30s fall 3 rise 2 cookie "
              "sample_member_id_1 {opts} alpn {alpn}\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13 "
              "check check-alpn {alpn} inter 30s fall 3 rise 2 cookie "
              "sample_member_id_2 {opts} alpn {alpn}\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
            opts="ssl crt %s verify none sni ssl_fc_sni" % cert_file_path +
                 " no-sslv3 no-tlsv10 no-tlsv11",
            alpn=",".join(constants.AMPHORA_SUPPORTED_ALPN_PROTOCOLS))
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                pool_cert=True, tls_enabled=True)],
            tls_certs={
                'sample_pool_id_1':
                    {'client_cert': cert_file_path,
                     'ca_cert': None, 'crl': None}},
            feature_compatibility=feature_compatibility)
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(backend=be),
            rendered_obj)

    def test_render_template_pool_cert_no_ciphers_or_versions_or_alpn(self):
        cert_file_path = os.path.join(self.jinja_cfg.base_crt_dir,
                                      'sample_listener_id_1', 'fake path')
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13 "
              "check inter 30s fall 3 rise 2 cookie sample_member_id_1 "
              "{opts}\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13 "
              "check inter 30s fall 3 rise 2 cookie sample_member_id_2 "
              "{opts}\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
            opts="ssl crt %s verify none sni ssl_fc_sni" % cert_file_path)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                pool_cert=True, tls_enabled=True, backend_tls_versions=None,
                backend_alpn_protocols=None)],
            tls_certs={
                'sample_pool_id_1':
                    {'client_cert': cert_file_path,
                     'ca_cert': None, 'crl': None}})
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(backend=be),
            rendered_obj)

    def test_render_template_pool_no_alpn(self):
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13 "
              "check inter 30s fall 3 rise 2 cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13 "
              "check inter 30s fall 3 rise 2 cookie sample_member_id_2"
              "\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                backend_alpn_protocols=None)])
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(backend=be),
            rendered_obj)

    def test_render_template_with_full_pool_cert(self):
        feature_compatibility = {constants.POOL_ALPN: True}
        pool_client_cert = '/foo/cert.pem'
        pool_ca_cert = '/foo/ca.pem'
        pool_crl = '/foo/crl.pem'
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13 "
              "check check-alpn {alpn} inter 30s fall 3 rise 2 cookie "
              "sample_member_id_1 {opts} alpn {alpn}\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13 "
              "check check-alpn {alpn} inter 30s fall 3 rise 2 cookie "
              "sample_member_id_2 {opts} alpn {alpn}\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
            opts="%s %s %s %s %s %s" % (
                "ssl", "crt", pool_client_cert,
                "ca-file %s" % pool_ca_cert,
                "crl-file %s" % pool_crl,
                "verify required sni ssl_fc_sni no-sslv3 no-tlsv10 no-tlsv11"),
            alpn=",".join(constants.AMPHORA_SUPPORTED_ALPN_PROTOCOLS))
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                pool_cert=True, pool_ca_cert=True, pool_crl=True,
                tls_enabled=True)],
            tls_certs={
                'sample_pool_id_1':
                    {'client_cert': pool_client_cert,
                     'ca_cert': pool_ca_cert,
                     'crl': pool_crl}},
            feature_compatibility=feature_compatibility)
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(backend=be),
            rendered_obj)

    def test_transform_session_persistence(self):
        in_persistence = (
            sample_configs_combined.sample_session_persistence_tuple())
        ret = self.jinja_cfg._transform_session_persistence(
            in_persistence, {})
        self.assertEqual(sample_configs_combined.RET_PERSISTENCE, ret)

    def test_transform_health_monitor(self):
        in_persistence = sample_configs_combined.sample_health_monitor_tuple()
        ret = self.jinja_cfg._transform_health_monitor(in_persistence, {})
        self.assertEqual(sample_configs_combined.RET_MONITOR_1, ret)

    def test_transform_member(self):
        in_member = sample_configs_combined.sample_member_tuple(
            'sample_member_id_1', '10.0.0.99')
        ret = self.jinja_cfg._transform_member(in_member, {})
        self.assertEqual(sample_configs_combined.RET_MEMBER_1, ret)

    def test_transform_pool(self):
        in_pool = sample_configs_combined.sample_pool_tuple()
        ret = self.jinja_cfg._transform_pool(in_pool, {}, False)
        self.assertEqual(sample_configs_combined.RET_POOL_1, ret)

    def test_transform_pool_2(self):
        in_pool = sample_configs_combined.sample_pool_tuple(sample_pool=2)
        ret = self.jinja_cfg._transform_pool(in_pool, {}, False)
        self.assertEqual(sample_configs_combined.RET_POOL_2, ret)

    def test_transform_pool_http_reuse(self):
        in_pool = sample_configs_combined.sample_pool_tuple(sample_pool=2)
        ret = self.jinja_cfg._transform_pool(
            in_pool, {constants.HTTP_REUSE: True}, False)
        expected_config = copy.copy(sample_configs_combined.RET_POOL_2)
        expected_config[constants.HTTP_REUSE] = True
        self.assertEqual(expected_config, ret)

    def test_transform_pool_cert(self):
        in_pool = sample_configs_combined.sample_pool_tuple(pool_cert=True)
        cert_path = os.path.join(self.jinja_cfg.base_crt_dir,
                                 'test_listener_id', 'pool_cert.pem')
        ret = self.jinja_cfg._transform_pool(
            in_pool, {}, False, pool_tls_certs={'client_cert': cert_path})
        expected_config = copy.copy(sample_configs_combined.RET_POOL_1)
        expected_config['client_cert'] = cert_path
        self.assertEqual(expected_config, ret)

    def test_transform_listener(self):
        in_listener = sample_configs_combined.sample_listener_tuple()
        ret = self.jinja_cfg._transform_listener(in_listener, None, {},
                                                 in_listener.load_balancer)
        self.assertEqual(sample_configs_combined.RET_LISTENER, ret)

    def test_transform_listener_with_l7(self):
        in_listener = sample_configs_combined.sample_listener_tuple(l7=True)
        ret = self.jinja_cfg._transform_listener(in_listener, None, {},
                                                 in_listener.load_balancer)
        self.assertEqual(sample_configs_combined.RET_LISTENER_L7, ret)

    def test_transform_listener_PROMETHEUS(self):
        in_listener = sample_configs_combined.sample_listener_tuple()
        ret = self.jinja_cfg._transform_listener(
            in_listener, None, {lib_consts.PROTOCOL_PROMETHEUS: True},
            in_listener.load_balancer)
        expected_config = copy.copy(sample_configs_combined.RET_LISTENER)
        expected_config[lib_consts.PROTOCOL_PROMETHEUS] = True
        self.assertEqual(expected_config, ret)

    def test_transform_loadbalancer(self):
        in_amphora = sample_configs_combined.sample_amphora_tuple()
        in_listener = sample_configs_combined.sample_listener_tuple()
        ret = self.jinja_cfg._transform_loadbalancer(
            in_amphora, in_listener.load_balancer, [in_listener], None, {})
        self.assertEqual(sample_configs_combined.RET_LB, ret)

    def test_transform_two_loadbalancers(self):
        in_amphora = sample_configs_combined.sample_amphora_tuple()
        in_listener1 = sample_configs_combined.sample_listener_tuple()
        in_listener2 = sample_configs_combined.sample_listener_tuple()

        ret = self.jinja_cfg._transform_loadbalancer(
            in_amphora, in_listener1.load_balancer,
            [in_listener1, in_listener2], None, {})
        self.assertEqual(ret['global_connection_limit'],
                         constants.HAPROXY_DEFAULT_MAXCONN +
                         constants.HAPROXY_DEFAULT_MAXCONN)

    def test_transform_many_loadbalancers(self):
        in_amphora = sample_configs_combined.sample_amphora_tuple()

        in_listeners = []

        # Create many listeners, until the sum of connection_limits
        # is greater than MAX_MAXCONN
        connection_limit_sum = 0
        while connection_limit_sum <= constants.HAPROXY_MAX_MAXCONN:
            in_listener = (
                sample_configs_combined.sample_listener_tuple())
            connection_limit_sum += constants.HAPROXY_DEFAULT_MAXCONN

            in_listeners.append(in_listener)

        ret = self.jinja_cfg._transform_loadbalancer(
            in_amphora, in_listeners[0].load_balancer,
            in_listeners, None, {})
        self.assertEqual(ret['global_connection_limit'],
                         constants.HAPROXY_MAX_MAXCONN)
        self.assertLess(ret['global_connection_limit'],
                        connection_limit_sum)

    def test_transform_with_disabled_listeners(self):
        in_amphora = sample_configs_combined.sample_amphora_tuple()

        in_listeners = []

        connection_limit_sum = 0

        in_listener = (
            sample_configs_combined.sample_listener_tuple())
        connection_limit_sum += constants.HAPROXY_DEFAULT_MAXCONN
        in_listeners.append(in_listener)

        disabled_listener = (
            sample_configs_combined.sample_listener_tuple(enabled=False))
        in_listeners.append(disabled_listener)

        ret = self.jinja_cfg._transform_loadbalancer(
            in_amphora, in_listeners[0].load_balancer,
            in_listeners, None, {})
        self.assertEqual(ret['global_connection_limit'],
                         connection_limit_sum)

    def test_transform_amphora(self):
        in_amphora = sample_configs_combined.sample_amphora_tuple()
        ret = self.jinja_cfg._transform_amphora(in_amphora, {})
        self.assertEqual(sample_configs_combined.RET_AMPHORA, ret)

    def test_transform_loadbalancer_with_l7(self):
        in_amphora = sample_configs_combined.sample_amphora_tuple()
        in_listener = sample_configs_combined.sample_listener_tuple(l7=True)
        ret = self.jinja_cfg._transform_loadbalancer(
            in_amphora, in_listener.load_balancer, [in_listener], None, {})
        self.assertEqual(sample_configs_combined.RET_LB_L7, ret)

    def test_transform_l7policy(self):
        in_l7policy = sample_configs_combined.sample_l7policy_tuple(
            'sample_l7policy_id_1')
        ret = self.jinja_cfg._transform_l7policy(in_l7policy, {}, False)
        self.assertEqual(sample_configs_combined.RET_L7POLICY_1, ret)

    def test_transform_l7policy_2_8(self):
        in_l7policy = sample_configs_combined.sample_l7policy_tuple(
            'sample_l7policy_id_2', sample_policy=2)
        ret = self.jinja_cfg._transform_l7policy(in_l7policy, {}, False)
        self.assertEqual(sample_configs_combined.RET_L7POLICY_2, ret)

        # test invalid action without redirect_http_code
        in_l7policy = sample_configs_combined.sample_l7policy_tuple(
            'sample_l7policy_id_8', sample_policy=2, redirect_http_code=None)
        ret = self.jinja_cfg._transform_l7policy(in_l7policy, {}, False)
        self.assertEqual(sample_configs_combined.RET_L7POLICY_8, ret)

    def test_transform_l7policy_disabled_rule(self):
        in_l7policy = sample_configs_combined.sample_l7policy_tuple(
            'sample_l7policy_id_6', sample_policy=6)
        ret = self.jinja_cfg._transform_l7policy(in_l7policy, {}, False)
        self.assertEqual(sample_configs_combined.RET_L7POLICY_6, ret)

    def test_escape_haproxy_config_string(self):
        self.assertEqual(self.jinja_cfg._escape_haproxy_config_string(
            'string_with_none'), 'string_with_none')
        self.assertEqual(self.jinja_cfg._escape_haproxy_config_string(
            'string with spaces'), 'string\\ with\\ spaces')
        self.assertEqual(self.jinja_cfg._escape_haproxy_config_string(
            'string\\with\\backslashes'), 'string\\\\with\\\\backslashes')
        self.assertEqual(self.jinja_cfg._escape_haproxy_config_string(
            'string\\ with\\ all'), 'string\\\\\\ with\\\\\\ all')

    def test_render_template_no_log(self):
        j_cfg = jinja_cfg.JinjaTemplater(
            base_amp_path='/var/lib/octavia',
            base_crt_dir='/var/lib/octavia/certs',
            connection_logging=False)
        defaults = ("defaults\n"
                    "    no log\n"
                    "    retries 3\n"
                    "    option redispatch\n"
                    "    option splice-request\n"
                    "    option splice-response\n"
                    "    option http-keep-alive\n\n\n")
        rendered_obj = j_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple()]
        )
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(
                defaults=defaults, logging="\n"),
            rendered_obj)

    def test_render_template_amp_details(self):
        j_cfg = jinja_cfg.JinjaTemplater(
            base_amp_path='/var/lib/octavia',
            base_crt_dir='/var/lib/octavia/certs',
            connection_logging=False)
        rendered_obj = j_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple()],
            amp_details={"cpu_count": 7,
                         "active_tuned_profiles": 'virtual-guest '
                                                  'optimize-serial-console '
                                                  'amphora'}
        )
        defaults = ("defaults\n"
                    "    no log\n"
                    "    retries 3\n"
                    "    option redispatch\n"
                    "    option splice-request\n"
                    "    option splice-response\n"
                    "    option http-keep-alive\n\n\n")
        global_opts = ("    maxconn 50000\n"
                       "    nbthread 6\n"
                       "    cpu-map auto:1/1-6 1-6\n")
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(
                defaults=defaults, logging="\n", global_opts=global_opts),
            rendered_obj)

    def test_render_template_amp_details_cpu_count_none(self):
        j_cfg = jinja_cfg.JinjaTemplater(
            base_amp_path='/var/lib/octavia',
            base_crt_dir='/var/lib/octavia/certs',
            connection_logging=False)
        rendered_obj = j_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple()],
            amp_details={"cpu_count": None},
        )
        defaults = ("defaults\n"
                    "    no log\n"
                    "    retries 3\n"
                    "    option redispatch\n"
                    "    option splice-request\n"
                    "    option splice-response\n"
                    "    option http-keep-alive\n\n\n")
        global_opts = "    maxconn 50000\n\n"
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(
                defaults=defaults, logging="\n", global_opts=global_opts),
            rendered_obj)

    def test_haproxy_cfg_1_8_vs_1_5(self):
        j_cfg = jinja_cfg.JinjaTemplater(
            base_amp_path='/var/lib/octavia',
            base_crt_dir='/var/lib/octavia/certs')

        sample_amphora = sample_configs_combined.sample_amphora_tuple()
        sample_proxy_listener = sample_configs_combined.sample_listener_tuple(
            be_proto='PROXY')
        # With http-reuse and server-state-file
        go = (
            "    server-state-file /var/lib/octavia/sample_loadbalancer_id_1/"
            "servers-state\n"
            "    maxconn {maxconn}\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN)
        be = ("backend {pool_id}:{listener_id}\n"
              "    mode http\n"
              "    http-reuse safe\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    load-server-state-from-file global\n"
              "    timeout check 31s\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1 send-proxy\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2 send-proxy\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
            pool_id=sample_proxy_listener.default_pool.id,
            listener_id=sample_proxy_listener.id)
        rendered_obj = j_cfg.build_config(
            sample_amphora,
            [sample_proxy_listener],
            tls_certs=None,
            haproxy_versions=("1", "8", "1"),
            amp_details=None)
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(
                global_opts=go, backend=be),
            rendered_obj)

        # Without http-reuse and server-state-file
        be = ("backend {pool_id}:{listener_id}\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1 send-proxy\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2 send-proxy\n\n").format(
            maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
            pool_id=sample_proxy_listener.default_pool.id,
            listener_id=sample_proxy_listener.id)
        rendered_obj = j_cfg.build_config(
            sample_amphora,
            [sample_proxy_listener],
            tls_certs=None,
            haproxy_versions=("1", "5", "18"),
            amp_details=None)
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(backend=be),
            rendered_obj)

    def test_ssl_types_l7rules(self):
        j_cfg = jinja_cfg.JinjaTemplater(
            base_amp_path='/var/lib/octavia',
            base_crt_dir='/var/lib/octavia/certs')
        fe = ("frontend sample_listener_id_1\n"
              "    maxconn {maxconn}\n"
              "    redirect scheme https if !{{ ssl_fc }}\n"
              "    http-response set-header Strict-Transport-Security "
              "\"max-age=10000000; includeSubDomains; preload;\"\n"
              "    bind 10.0.0.2:443 ciphers {ciphers} "
              "no-sslv3 no-tlsv10 no-tlsv11 alpn {alpn}\n"
              "    mode http\n"
              "        acl sample_l7rule_id_1 path -m beg /api\n"
              "    use_backend sample_pool_id_2:sample_listener_id_1"
              " if sample_l7rule_id_1\n"
              "        acl sample_l7rule_id_2 req.hdr(Some-header) -m sub "
              "This\\ string\\\\\\ with\\ stuff\n"
              "        acl sample_l7rule_id_3 req.cook(some-cookie) -m reg "
              "this.*|that\n"
              "    redirect code 302 location http://www.example.com "
              "if !sample_l7rule_id_2 sample_l7rule_id_3\n"
              "        acl sample_l7rule_id_4 path_end  jpg\n"
              "        acl sample_l7rule_id_5 req.hdr(host) -i -m end "
              ".example.com\n"
              "    http-request deny "
              "if sample_l7rule_id_4 sample_l7rule_id_5\n"
              "        acl sample_l7rule_id_2 req.hdr(Some-header) -m sub "
              "This\\ string\\\\\\ with\\ stuff\n"
              "        acl sample_l7rule_id_3 req.cook(some-cookie) -m reg "
              "this.*|that\n"
              "    redirect code 302 prefix https://example.com "
              "if !sample_l7rule_id_2 sample_l7rule_id_3\n"
              "        acl sample_l7rule_id_7 ssl_c_used\n"
              "        acl sample_l7rule_id_8 ssl_c_verify eq 1\n"
              "        acl sample_l7rule_id_9 ssl_c_s_dn(STREET) -m reg "
              "^STREET.*NO\\\\.$\n"
              "        acl sample_l7rule_id_10 ssl_c_s_dn(OU-3) -m beg "
              "Orgnization\\ Bala\n"
              "        acl sample_l7rule_id_11 path -m beg /api\n"
              "    redirect code 302 location "
              "http://www.ssl-type-l7rule-test.com "
              "if sample_l7rule_id_7 !sample_l7rule_id_8 !sample_l7rule_id_9 "
              "!sample_l7rule_id_10 sample_l7rule_id_11\n"
              "    default_backend sample_pool_id_1:sample_listener_id_1\n"
              "    timeout client 50000\n".format(
                  maxconn=constants.HAPROXY_DEFAULT_MAXCONN,
                  ciphers=constants.CIPHERS_OWASP_SUITE_B,
                  alpn=",".join(constants.AMPHORA_SUPPORTED_ALPN_PROTOCOLS)))
        be = ("backend sample_pool_id_1:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /index.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13 check "
              "inter 30s fall 3 rise 2 cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13 check "
              "inter 30s fall 3 rise 2 cookie sample_member_id_2\n\n"
              "backend sample_pool_id_2:sample_listener_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31s\n"
              "    option httpchk GET /healthmon.html HTTP/1.0\\r\\n\n"
              "    http-check expect rstatus 418\n"
              "    fullconn {maxconn}\n"
              "    option allbackups\n"
              "    timeout connect 5000\n"
              "    timeout server 50000\n"
              "    server sample_member_id_3 10.0.0.97:82 weight 13 check "
              "inter 30s fall 3 rise 2 cookie sample_member_id_3\n\n".format(
                  maxconn=constants.HAPROXY_DEFAULT_MAXCONN))
        sample_listener = sample_configs_combined.sample_listener_tuple(
            proto=constants.PROTOCOL_TERMINATED_HTTPS, l7=True,
            ssl_type_l7=True)
        rendered_obj = j_cfg.build_config(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_listener],
            tls_certs=None,
            haproxy_versions=("1", "5", "18"),
            amp_details=None)
        self.assertEqual(
            sample_configs_combined.sample_base_expected_config(
                frontend=fe, backend=be),
            rendered_obj)

    @mock.patch("octavia.common.jinja.haproxy.combined_listeners.jinja_cfg."
                "JinjaTemplater.render_loadbalancer_obj")
    def test_build_config(self, mock_render_loadbalancer_obj):
        mock_amp = mock.Mock()
        mock_listeners = mock.Mock()
        mock_tls_certs = mock.Mock()
        mock_socket_path = mock.Mock()

        j_cfg = jinja_cfg.JinjaTemplater()
        j_cfg.build_config(mock_amp, mock_listeners, mock_tls_certs,
                           haproxy_versions=("0", "7", "0"),
                           socket_path=mock_socket_path, amp_details=None)

        expected_fc = {}
        mock_render_loadbalancer_obj.assert_called_once_with(
            mock_amp, mock_listeners, tls_certs=mock_tls_certs,
            socket_path=mock_socket_path, amp_details=None,
            feature_compatibility=expected_fc)

        mock_render_loadbalancer_obj.reset_mock()

        j_cfg.build_config(mock_amp, mock_listeners, mock_tls_certs,
                           haproxy_versions=("1", "6", "0"),
                           socket_path=mock_socket_path, amp_details=None)

        expected_fc = {
            constants.HTTP_REUSE: True,
            constants.SERVER_STATE_FILE: True
        }
        mock_render_loadbalancer_obj.assert_called_once_with(
            mock_amp, mock_listeners, tls_certs=mock_tls_certs,
            socket_path=mock_socket_path, amp_details=None,
            feature_compatibility=expected_fc)

        mock_render_loadbalancer_obj.reset_mock()

        j_cfg.build_config(mock_amp, mock_listeners, mock_tls_certs,
                           haproxy_versions=("1", "9", "0"),
                           socket_path=mock_socket_path, amp_details=None)

        expected_fc = {
            constants.HTTP_REUSE: True,
            constants.POOL_ALPN: True,
            constants.SERVER_STATE_FILE: True
        }
        mock_render_loadbalancer_obj.assert_called_once_with(
            mock_amp, mock_listeners, tls_certs=mock_tls_certs,
            socket_path=mock_socket_path, amp_details=None,
            feature_compatibility=expected_fc)

        mock_render_loadbalancer_obj.reset_mock()

        j_cfg.build_config(mock_amp, mock_listeners, mock_tls_certs,
                           haproxy_versions=("2", "1", "1"),
                           socket_path=mock_socket_path, amp_details=None)

        expected_fc = {
            constants.HTTP_REUSE: True,
            constants.POOL_ALPN: True,
            lib_consts.PROTOCOL_PROMETHEUS: True,
            constants.SERVER_STATE_FILE: True
        }
        mock_render_loadbalancer_obj.assert_called_once_with(
            mock_amp, mock_listeners, tls_certs=mock_tls_certs,
            socket_path=mock_socket_path, amp_details=None,
            feature_compatibility=expected_fc)

        mock_render_loadbalancer_obj.reset_mock()

        j_cfg.build_config(mock_amp, mock_listeners, mock_tls_certs,
                           haproxy_versions=("2", "2", "1"), amp_details=None,
                           socket_path=mock_socket_path)

        expected_fc = {
            constants.HTTP_REUSE: True,
            constants.POOL_ALPN: True,
            lib_consts.PROTOCOL_PROMETHEUS: True,
            constants.INSECURE_FORK: True,
            constants.SERVER_STATE_FILE: True
        }
        mock_render_loadbalancer_obj.assert_called_once_with(
            mock_amp, mock_listeners, tls_certs=mock_tls_certs,
            socket_path=mock_socket_path, amp_details=None,
            feature_compatibility=expected_fc)

        mock_render_loadbalancer_obj.reset_mock()

        j_cfg.build_config(mock_amp, mock_listeners, mock_tls_certs,
                           haproxy_versions=("2", "4", "0"),
                           socket_path=mock_socket_path, amp_details=None)

        mock_render_loadbalancer_obj.assert_called_once_with(
            mock_amp, mock_listeners, tls_certs=mock_tls_certs,
            socket_path=mock_socket_path, amp_details=None,
            feature_compatibility=expected_fc)

        mock_render_loadbalancer_obj.reset_mock()

        j_cfg.build_config(mock_amp, mock_listeners, mock_tls_certs,
                           haproxy_versions=("3", "1", "0"),
                           socket_path=mock_socket_path, amp_details=None)

        mock_render_loadbalancer_obj.assert_called_once_with(
            mock_amp, mock_listeners, tls_certs=mock_tls_certs,
            socket_path=mock_socket_path, amp_details=None,
            feature_compatibility=expected_fc)
