# Copyright 2014,  Doug Wiegley,  A10 Networks.
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

from oslo_config import cfg

import octavia.common.config as config
import octavia.tests.unit.base as base


class TestConfig(base.TestCase):

    def test_sanity(self):
        config.init([])
        config.setup_logging(cfg.CONF)
        # Resetting because this will cause inconsistent errors when run with
        # other tests
        self.addCleanup(cfg.CONF.reset)
