#    Copyright 2014 Hewlett-Packard Development Company, L.P.
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

from octavia.tests.unit import base


class TestSender(base.TestCase):
    def setUp(self):
        super(TestSender, self).setUp()
        self.setupConfigFile()
        self.addCleanup(self.removeConfigFile)

    def setupConfigFile(self):
        self.sampleconfig = tempfile.mkstemp()
        conffile = os.fdopen(self.sampleconfig[0], 'w+')
        cdata = {'delay': 10,
                 'target': ['127.0.0.1', '::1'],
                 'psk': 'fubar',
                 'dport': 12345}
        json.dump(cdata, conffile)
        conffile.close()

    def removeConfigFile(self):
        os.unlink(self.sampleconfig[1])

    def test_message_output(self):
        pass
