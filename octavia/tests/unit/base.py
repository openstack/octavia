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
import fixtures
import mock
from oslo_config import cfg
import oslo_messaging as messaging
from oslo_messaging import conffixture as messaging_conffixture
import testtools

from octavia.common import clients
from octavia.common import rpc

# needed for tests to function when run independently:
from octavia.common import config  # noqa: F401


class TestCase(testtools.TestCase):

    def setUp(self):
        super(TestCase, self).setUp()
        self.addCleanup(mock.patch.stopall)
        self.addCleanup(self.clean_caches)

    def clean_caches(self):
        clients.NovaAuth.nova_client = None
        clients.NeutronAuth.neutron_client = None


class TestRpc(testtools.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestRpc, self).__init__(*args, **kwargs)
        self._buses = {}

    def _fake_create_transport(self, url):
        if url not in self._buses:
            self._buses[url] = messaging.get_rpc_transport(
                cfg.CONF,
                url=url)
        return self._buses[url]

    def setUp(self):
        super(TestRpc, self).setUp()
        self.addCleanup(rpc.cleanup)
        self.messaging_conf = messaging_conffixture.ConfFixture(cfg.CONF)
        self.messaging_conf.transport_url = 'fake:/'
        self.useFixture(self.messaging_conf)
        self.useFixture(fixtures.MonkeyPatch(
            'octavia.common.rpc.create_transport',
            self._fake_create_transport))
        with mock.patch('octavia.common.rpc.get_transport_url') as mock_gtu:
            mock_gtu.return_value = None
            rpc.init()
