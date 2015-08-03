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

from octavia.amphorae.drivers.haproxy.jinja import jinja_cfg
from octavia.tests.unit import base as base
from octavia.tests.unit.common.sample_configs import sample_configs


class TestHaproxyCfg(base.TestCase):
    def setUp(self):
        super(TestHaproxyCfg, self).setUp()
        self.jinja_cfg = jinja_cfg.JinjaTemplater(
            base_amp_path='/var/lib/octavia',
            base_crt_dir='/var/lib/octavia/certs')

    def test_get_template(self):
        template = self.jinja_cfg._get_template()
        self.assertEqual('haproxy_listener.template', template.name)

    def test_render_template_tls(self):
        fe = ("frontend sample_listener_id_1\n"
              "    option tcplog\n"
              "    maxconn 98\n"
              "    option forwardfor\n"
              "    bind 10.0.0.2:443 "
              "ssl crt /var/lib/octavia/certs/"
              "sample_listener_id_1/FakeCN.pem "
              "crt /var/lib/octavia/certs/sample_listener_id_1\n"
              "    mode http\n"
              "    default_backend sample_pool_id_1\n\n")
        be = ("backend sample_pool_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    redirect scheme https if !{ ssl_fc }\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31\n"
              "    option httpchk GET /index.html\n"
              "    http-check expect rstatus 418\n"
              "    option forwardfor\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 cookie "
              "sample_member_id_2\n\n")
        tls_tupe = sample_configs.sample_tls_container_tuple(
            certificate='imaCert1', private_key='imaPrivateKey1',
            primary_cn='FakeCN')
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs.sample_listener_tuple(proto='TERMINATED_HTTPS',
                                                 tls=True, sni=True),
            tls_tupe)
        self.assertEqual(
            sample_configs.sample_base_expected_config(
                frontend=fe, backend=be),
            rendered_obj)

    def test_render_template_tls_no_sni(self):
        fe = ("frontend sample_listener_id_1\n"
              "    option tcplog\n"
              "    maxconn 98\n"
              "    option forwardfor\n"
              "    bind 10.0.0.2:443 "
              "ssl crt /var/lib/octavia/certs/"
              "sample_listener_id_1/FakeCN.pem\n"
              "    mode http\n"
              "    default_backend sample_pool_id_1\n\n")
        be = ("backend sample_pool_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    redirect scheme https if !{ ssl_fc }\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31\n"
              "    option httpchk GET /index.html\n"
              "    http-check expect rstatus 418\n"
              "    option forwardfor\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2\n\n")
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs.sample_listener_tuple(
                proto='TERMINATED_HTTPS', tls=True),
            tls_cert=sample_configs.sample_tls_container_tuple(
                certificate='ImAalsdkfjCert',
                private_key='ImAsdlfksdjPrivateKey',
                primary_cn="FakeCN"))
        self.assertEqual(
            sample_configs.sample_base_expected_config(
                frontend=fe, backend=be),
            rendered_obj)

    def test_render_template_http(self):
        be = ("backend sample_pool_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31\n"
              "    option httpchk GET /index.html\n"
              "    http-check expect rstatus 418\n"
              "    option forwardfor\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2\n\n")
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs.sample_listener_tuple())
        self.assertEqual(
            sample_configs.sample_base_expected_config(backend=be),
            rendered_obj)

    def test_render_template_https(self):
        fe = ("frontend sample_listener_id_1\n"
              "    option tcplog\n"
              "    maxconn 98\n"
              "    bind 10.0.0.2:443\n"
              "    mode tcp\n"
              "    default_backend sample_pool_id_1\n\n")
        be = ("backend sample_pool_id_1\n"
              "    mode tcp\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    timeout check 31\n"
              "    option httpchk GET /index.html\n"
              "    http-check expect rstatus 418\n"
              "    option ssl-hello-chk\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2 "
              "cookie sample_member_id_2\n\n")
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs.sample_listener_tuple(proto='HTTPS'))
        self.assertEqual(sample_configs.sample_base_expected_config(
            frontend=fe, backend=be), rendered_obj)

    def test_render_template_no_monitor_http(self):
        be = ("backend sample_pool_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    option forwardfor\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13 "
              "cookie sample_member_id_2\n\n")
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs.sample_listener_tuple(proto='HTTP', monitor=False))
        self.assertEqual(sample_configs.sample_base_expected_config(
            backend=be), rendered_obj)

    def test_render_template_no_monitor_https(self):
        fe = ("frontend sample_listener_id_1\n"
              "    option tcplog\n"
              "    maxconn 98\n"
              "    bind 10.0.0.2:443\n"
              "    mode tcp\n"
              "    default_backend sample_pool_id_1\n\n")
        be = ("backend sample_pool_id_1\n"
              "    mode tcp\n"
              "    balance roundrobin\n"
              "    cookie SRV insert indirect nocache\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13 "
              "cookie sample_member_id_1\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13 "
              "cookie sample_member_id_2\n\n")
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs.sample_listener_tuple(proto='HTTPS', monitor=False))
        self.assertEqual(sample_configs.sample_base_expected_config(
            frontend=fe, backend=be), rendered_obj)

    def test_render_template_no_persistence_https(self):
        fe = ("frontend sample_listener_id_1\n"
              "    option tcplog\n"
              "    maxconn 98\n"
              "    bind 10.0.0.2:443\n"
              "    mode tcp\n"
              "    default_backend sample_pool_id_1\n\n")
        be = ("backend sample_pool_id_1\n"
              "    mode tcp\n"
              "    balance roundrobin\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13\n\n")
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs.sample_listener_tuple(proto='HTTPS', monitor=False,
                                                 persistence=False))
        self.assertEqual(sample_configs.sample_base_expected_config(
            frontend=fe, backend=be), rendered_obj)

    def test_render_template_no_persistence_http(self):
        be = ("backend sample_pool_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    option forwardfor\n"
              "    server sample_member_id_1 10.0.0.99:82 weight 13\n"
              "    server sample_member_id_2 10.0.0.98:82 weight 13\n\n")
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs.sample_listener_tuple(proto='HTTP', monitor=False,
                                                 persistence=False))
        self.assertEqual(sample_configs.sample_base_expected_config(
            backend=be), rendered_obj)

    def test_render_template_sourceip_persistence(self):
        be = ("backend sample_pool_id_1\n"
              "    mode http\n"
              "    balance roundrobin\n"
              "    stick-table type ip size 10k\n"
              "    stick on src\n"
              "    timeout check 31\n"
              "    option httpchk GET /index.html\n"
              "    http-check expect rstatus 418\n"
              "    option forwardfor\n"
              "    server sample_member_id_1 10.0.0.99:82 "
              "weight 13 check inter 30s fall 3 rise 2\n"
              "    server sample_member_id_2 10.0.0.98:82 "
              "weight 13 check inter 30s fall 3 rise 2\n\n")
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs.sample_listener_tuple(
                persistence_type='SOURCE_IP'))
        self.assertEqual(
            sample_configs.sample_base_expected_config(backend=be),
            rendered_obj)

    def test_transform_session_persistence(self):
        in_persistence = sample_configs.sample_session_persistence_tuple()
        ret = self.jinja_cfg._transform_session_persistence(in_persistence)
        self.assertEqual(sample_configs.RET_PERSISTENCE, ret)

    def test_transform_health_monitor(self):
        in_persistence = sample_configs.sample_health_monitor_tuple()
        ret = self.jinja_cfg._transform_health_monitor(in_persistence)
        self.assertEqual(sample_configs.RET_MONITOR, ret)

    def test_transform_member(self):
        in_member = sample_configs.sample_member_tuple('sample_member_id_1',
                                                       '10.0.0.99')
        ret = self.jinja_cfg._transform_member(in_member)
        self.assertEqual(sample_configs.RET_MEMBER_1, ret)

    def test_transform_pool(self):
        in_pool = sample_configs.sample_pool_tuple()
        ret = self.jinja_cfg._transform_pool(in_pool)
        self.assertEqual(sample_configs.RET_POOL, ret)

    def test_transform_listener(self):
        in_listener = sample_configs.sample_listener_tuple()
        ret = self.jinja_cfg._transform_listener(in_listener, None)
        self.assertEqual(sample_configs.RET_LISTENER, ret)

    def test_transform_loadbalancer(self):
        in_listener = sample_configs.sample_listener_tuple()
        ret = self.jinja_cfg._transform_loadbalancer(
            in_listener.load_balancer, in_listener, None)
        self.assertEqual(sample_configs.RET_LB, ret)

    def test_expand_expected_codes(self):
        exp_codes = ''
        self.assertEqual(self.jinja_cfg._expand_expected_codes(exp_codes),
                         set([]))
        exp_codes = '200'
        self.assertEqual(
            self.jinja_cfg._expand_expected_codes(exp_codes), set(['200']))
        exp_codes = '200, 201'
        self.assertEqual(self.jinja_cfg._expand_expected_codes(exp_codes),
                         set(['200', '201']))
        exp_codes = '200, 201,202'
        self.assertEqual(self.jinja_cfg._expand_expected_codes(exp_codes),
                         set(['200', '201', '202']))
        exp_codes = '200-202'
        self.assertEqual(self.jinja_cfg._expand_expected_codes(exp_codes),
                         set(['200', '201', '202']))
        exp_codes = '200-202, 205'
        self.assertEqual(self.jinja_cfg._expand_expected_codes(exp_codes),
                         set(['200', '201', '202', '205']))
        exp_codes = '200, 201-203'
        self.assertEqual(self.jinja_cfg._expand_expected_codes(exp_codes),
                         set(['200', '201', '202', '203']))
        exp_codes = '200, 201-203, 205'
        self.assertEqual(self.jinja_cfg._expand_expected_codes(exp_codes),
                         set(['200', '201', '202', '203', '205']))
        exp_codes = '201-200, 205'
        self.assertEqual(
            self.jinja_cfg._expand_expected_codes(exp_codes), set(['205']))
