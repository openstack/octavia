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

import mock
import neutronclient.v2_0
import novaclient.v2
from oslo_config import cfg

from octavia.common import clients
from octavia.common import keystone
from octavia.tests.unit import base

CONF = cfg.CONF


class TestNovaAuth(base.TestCase):

    def setUp(self):
        CONF.set_override(group='keystone_authtoken', name='auth_version',
                          override='2')
        # Reset the session and client
        clients.NovaAuth.nova_client = None
        keystone._SESSION = None

        super(TestNovaAuth, self).setUp()

    def test_get_nova_client(self):
        # There should be no existing client
        self.assertIsNone(
            clients.NovaAuth.nova_client
        )

        # Mock out the keystone session and get the client
        keystone._SESSION = mock.MagicMock()
        bc1 = clients.NovaAuth.get_nova_client(region=None)

        # Our returned client should also be the saved client
        self.assertIsInstance(
            clients.NovaAuth.nova_client,
            novaclient.v2.client.Client
        )
        self.assertIs(
            clients.NovaAuth.nova_client,
            bc1
        )

        # Getting the session again should return the same object
        bc2 = clients.NovaAuth.get_nova_client(
            region="test-region")
        self.assertIs(bc1, bc2)


class TestNeutronAuth(base.TestCase):

    def setUp(self):
        CONF.set_override(group='keystone_authtoken', name='auth_version',
                          override='2')
        # Reset the session and client
        clients.NeutronAuth.neutron_client = None
        keystone._SESSION = None

        super(TestNeutronAuth, self).setUp()

    def test_get_neutron_client(self):
        # There should be no existing client
        self.assertIsNone(
            clients.NeutronAuth.neutron_client
        )

        # Mock out the keystone session and get the client
        keystone._SESSION = mock.MagicMock()
        bc1 = clients.NeutronAuth.get_neutron_client(region=None)

        # Our returned client should also be the saved client
        self.assertIsInstance(
            clients.NeutronAuth.neutron_client,
            neutronclient.v2_0.client.Client
        )
        self.assertIs(
            clients.NeutronAuth.neutron_client,
            bc1
        )

        # Getting the session again should return the same object
        bc2 = clients.NeutronAuth.get_neutron_client(
            region="test-region")
        self.assertIs(bc1, bc2)
