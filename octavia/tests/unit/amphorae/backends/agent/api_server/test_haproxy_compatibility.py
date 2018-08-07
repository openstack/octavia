# Copyright 2017 Rackspace, US Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock

from octavia.amphorae.backends.agent.api_server import haproxy_compatibility
from octavia.common import constants
import octavia.tests.unit.base as base
from octavia.tests.unit.common.sample_configs import sample_configs


class HAProxyCompatTestCase(base.TestCase):
    def setUp(self):
        super(HAProxyCompatTestCase, self).setUp()
        self.old_haproxy_global = (
            "# Configuration for loadbalancer sample_loadbalancer_id_1\n"
            "global\n"
            "    daemon\n"
            "    user nobody\n"
            "    log /dev/log local0\n"
            "    log /dev/log local1 notice\n"
            "    stats socket /var/lib/octavia/sample_listener_id_1.sock"
            " mode 0666 level user\n"
            "    maxconn {maxconn}\n\n"
            "defaults\n"
            "    log global\n"
            "    retries 3\n"
            "    option redispatch\n\n\n\n"
            "frontend sample_listener_id_1\n"
            "    option httplog\n"
            "    maxconn {maxconn}\n"
            "    bind 10.0.0.2:80\n"
            "    mode http\n"
            "    default_backend sample_pool_id_1\n"
            "    timeout client 50000\n\n").format(
            maxconn=constants.HAPROXY_MAX_MAXCONN)
        self.backend_without_external = (
            "backend sample_pool_id_1\n"
            "    mode http\n"
            "    balance roundrobin\n"
            "    cookie SRV insert indirect nocache\n"
            "    timeout check 31\n"
            "    option httpchk GET /index.html\n"
            "    http-check expect rstatus 418\n"
            "    fullconn {maxconn}\n"
            "    option allbackups\n"
            "    timeout connect 5000\n"
            "    timeout server 50000\n"
            "    server sample_member_id_1 10.0.0.99:82 weight 13 "
            "check inter 30s fall 3 rise 2 cookie sample_member_id_1\n"
            "    server sample_member_id_2 10.0.0.98:82 weight 13 "
            "check inter 30s fall 3 rise 2 cookie "
            "sample_member_id_2\n").format(
            maxconn=constants.HAPROXY_MAX_MAXCONN)
        self.backend_with_external = (
            "backend sample_pool_id_1\n"
            "    mode http\n"
            "    balance roundrobin\n"
            "    cookie SRV insert indirect nocache\n"
            "    timeout check 31\n"
            "    option httpchk GET /index.html\n"
            "    http-check expect rstatus 418\n"
            "    option external-check\n"
            "    external-check command /var/lib/octavia/ping-wrapper.sh\n"
            "    fullconn {maxconn}\n"
            "    option allbackups\n"
            "    timeout connect 5000\n"
            "    timeout server 50000\n"
            "    server sample_member_id_1 10.0.0.99:82 weight 13 "
            "check inter 30s fall 3 rise 2 cookie sample_member_id_1\n"
            "    server sample_member_id_2 10.0.0.98:82 weight 13 "
            "check inter 30s fall 3 rise 2 cookie "
            "sample_member_id_2\n").format(
            maxconn=constants.HAPROXY_MAX_MAXCONN)

    @mock.patch('subprocess.check_output')
    def test_get_haproxy_versions(self, mock_process):
        mock_process.return_value = (
            b"THIS-App version 1.6.3 2099/10/12\n"
            b"Some other data here <test@example.com>\n")
        major, minor = haproxy_compatibility.get_haproxy_versions()
        self.assertEqual(1, major)
        self.assertEqual(6, minor)

    @mock.patch('octavia.amphorae.backends.agent.api_server.'
                'haproxy_compatibility.get_haproxy_versions')
    def test_process_cfg_for_version_compat(self, mock_get_version):
        # Test 1.6 version path, no change to config expected
        mock_get_version.return_value = [1, 6]
        test_config = sample_configs.sample_base_expected_config(
            backend=self.backend_with_external)
        result_config = haproxy_compatibility.process_cfg_for_version_compat(
            test_config)
        self.assertEqual(test_config, result_config)

        # Test 1.5 version path, external-check should be removed
        mock_get_version.return_value = [1, 5]
        test_config = sample_configs.sample_base_expected_config(
            backend=self.backend_with_external)
        result_config = haproxy_compatibility.process_cfg_for_version_compat(
            test_config)
        expected_config = (self.old_haproxy_global +
                           self.backend_without_external)
        self.assertEqual(expected_config, result_config)
