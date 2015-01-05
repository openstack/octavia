#    Copyright 2014 Hewlett-Packard Development-Company, L.P.
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

import json
import os
import tempfile

from testtools import matchers

from octavia.amphorae.backends.health_daemon import config
from octavia.tests.unit import base


class TestConfig(base.TestCase):
    def setUp(self):
        super(TestConfig, self).setUp()
        self.setup_config_file()
        self.addCleanup(self.remove_config_file)

    def test_noconfig(self):
        cfg = config.JSONFileConfig()
        self.assertThat(lambda: cfg.set_filename('/doesnotexist'),
                        matchers.raises(IOError))

    def test_config(self):
        cfg = config.JSONFileConfig()
        cfg.set_filename(self.sampleconfig[1])

        # Check the singleton decorator
        self.assertIs(cfg, config.JSONFileConfig())

        cfg.add_observer(self.check_update)

        self.update_called = False
        cfg.check_update()
        self.assertTrue(self.update_called)

        self.assertIs(cfg['delay'], 10)

        # First test - change the existing file - same file, no change
        with open(self.sampleconfig[1], 'w+') as f:
            cdata = {'delay': 5}
            json.dump(cdata, f)

        self.update_called = False
        cfg.check_update()
        self.assertTrue(self.update_called)

        self.assertIs(cfg['delay'], 5)

        # Check for removing an observer - Thanks Stephen
        cfg.remove_observer(self.check_update)
        self.update_called = False
        cfg.check_update()
        self.assertFalse(self.update_called)

        # Better add it back for the next test
        cfg.add_observer(self.check_update)

        # Next, replace the file (new inode)
        self.remove_config_file()
        with open(self.sampleconfig[1], 'w+') as f:
            cdata = {'delay': 3}
            json.dump(cdata, f)

        self.update_called = False
        cfg.check_update()
        self.assertTrue(self.update_called)

        self.assertIs(cfg['delay'], 3)

    def check_update(self):
        self.assertFalse(self.update_called)
        self.update_called = True

    def setup_config_file(self):
        self.sampleconfig = tempfile.mkstemp()
        conffile = os.fdopen(self.sampleconfig[0], 'w+')
        cdata = {'delay': 10}
        json.dump(cdata, conffile)
        conffile.close()

    def remove_config_file(self):
        os.unlink(self.sampleconfig[1])
