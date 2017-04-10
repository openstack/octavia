# Copyright 2016 Hewlett Packard Enterprise Development Company
# Copyright 2016 Rackspace Inc.
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

import os

from tempest.test_discover import plugins

import octavia
from octavia.tests.tempest import config as octavia_config


class OctaviaTempestPlugin(plugins.TempestPlugin):

    def load_tests(self):
        base_path = os.path.split(os.path.dirname(
            os.path.abspath(octavia.__file__)))[0]
        test_dir = "octavia/tests/tempest"
        full_test_dir = os.path.join(base_path, test_dir)
        return full_test_dir, base_path

    def register_opts(self, conf):
        conf.register_group(octavia_config.octavia_group)
        conf.register_opts(octavia_config.OctaviaGroup, group='octavia')
        conf.register_opt(octavia_config.service_option,
                          group='service_available')

    def get_opt_lists(self):
        return [('octavia', octavia_config.OctaviaGroup),
                ('service_available', [octavia_config.service_option])]
