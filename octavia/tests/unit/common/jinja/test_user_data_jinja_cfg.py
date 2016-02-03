# Copyright 2016 Rackspace
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from octavia.common.jinja import user_data_jinja_cfg
import octavia.tests.unit.base as base

TEST_CONFIG = ('[DEFAULT]\n'
               'debug = False\n'
               '[haproxy_amphora]\n'
               'base_cert_dir = /var/lib/octavia/certs\n')
EXPECTED_TEST_CONFIG = ('        [DEFAULT]\n'
                        '        debug = False\n'
                        '        [haproxy_amphora]\n'
                        '        base_cert_dir = /var/lib/octavia/certs\n')
BASE_CFG = ('#cloud-config\n'
            '# vim: syntax=yaml\n'
            '#\n'
            '# This configuration with take user-data dict and '
            'build a cloud-init\n'
            '# script utilizing the write_files module. '
            'The user-data dict should be a\n'
            '# Key Value pair where the Key is the path to store the '
            'file and the Value\n'
            '# is the data to store at that location\n'
            '#\n'
            '# Example:\n'
            '#     {\'/root/path/to/file.cfg\': \'I\'m a file, '
            'write things in me\'}\n'
            'write_files:\n')
RUN_CMD = ('runcmd:\n'
           '-   service amphora-agent restart')


class TestUserDataJinjaCfg(base.TestCase):
    def setUp(self):
        super(TestUserDataJinjaCfg, self).setUp()

    def test_build_user_data_config(self):
        udc = user_data_jinja_cfg.UserDataJinjaCfg()
        expected_config = (BASE_CFG +
                           '-   path: /test/config/path\n'
                           '    content: |\n' + EXPECTED_TEST_CONFIG + RUN_CMD)
        ud_cfg = udc.build_user_data_config({'/test/config/path': TEST_CONFIG})
        self.assertEqual(expected_config, ud_cfg)
