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

import uuid

from octavia.amphorae.backends.health_daemon import status_message
from octavia.common import exceptions
from octavia.tests.unit import base


class TestEnvelope(base.TestCase):
    def setUp(self):
        super(TestEnvelope, self).setUp()

    def test_message_hmac(self):
        seq = 42
        for i in range(0, 16):
            statusMsg = {'seq': seq,
                         'status': 'OK',
                         'id': str(uuid.uuid4())}
            envelope = status_message.wrap_envelope(statusMsg, 'samplekey1')
            obj = status_message.unwrap_envelope(envelope, 'samplekey1')
            self.assertEqual(obj['status'], 'OK')
            self.assertEqual(obj['seq'], seq)
            seq += 1
            args = (envelope, 'samplekey?')
            self.assertRaises(exceptions.InvalidHMACException,
                              status_message.unwrap_envelope, *args)
