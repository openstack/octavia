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
import re
from unittest import mock

import cinderclient.v3
import glanceclient.v2
import novaclient.v2
from openstack import exceptions as os_exceptions
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from requests_mock.contrib import fixture as rm_fixture

from octavia.common import clients
from octavia.common import context
from octavia.common import keystone
from octavia.tests.unit import base

CONF = cfg.CONF


class TestNovaAuth(base.TestCase):

    def setUp(self):
        # Reset the session and client
        clients.NovaAuth.nova_client = None
        keystone._SESSION = None

        super().setUp()

    @mock.patch('keystoneauth1.session.Session', mock.Mock())
    def test_get_nova_client(self):
        # There should be no existing client
        self.assertIsNone(
            clients.NovaAuth.nova_client
        )

        # Mock out the keystone session and get the client
        keystone._SESSION = mock.MagicMock()
        bc1 = clients.NovaAuth.get_nova_client(region=None,
                                               endpoint_type='publicURL')

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
            region="test-region", service_name='novaEndpoint1',
            endpoint="test-endpoint", endpoint_type='adminURL', insecure=True)
        self.assertIs(bc1, bc2)


class TestGlanceAuth(base.TestCase):

    def setUp(self):
        # Reset the session and client
        clients.GlanceAuth.glance_client = None
        keystone._SESSION = None

        super().setUp()

    @mock.patch('keystoneauth1.session.Session', mock.Mock())
    def test_get_glance_client(self):
        # There should be no existing client
        self.assertIsNone(
            clients.GlanceAuth.glance_client
        )

        # Mock out the keystone session and get the client
        keystone._SESSION = mock.MagicMock()
        bc1 = clients.GlanceAuth.get_glance_client(
            region=None, endpoint_type='publicURL', insecure=True)

        # Our returned client should also be the saved client
        self.assertIsInstance(
            clients.GlanceAuth.glance_client,
            glanceclient.v2.client.Client
        )
        self.assertIs(
            clients.GlanceAuth.glance_client,
            bc1
        )

        # Getting the session again should return the same object
        bc2 = clients.GlanceAuth.get_glance_client(
            region="test-region", service_name="glanceEndpoint1",
            endpoint="test-endpoint", endpoint_type='publicURL', insecure=True)
        self.assertIs(bc1, bc2)


class TestCinderAuth(base.TestCase):

    def setUp(self):
        # Reset the session and client
        clients.CinderAuth.cinder_client = None
        keystone._SESSION = None

        super().setUp()

    @mock.patch('keystoneauth1.session.Session', mock.Mock())
    def test_get_cinder_client(self):
        # There should be no existing client
        self.assertIsNone(
            clients.CinderAuth.cinder_client
        )

        # Mock out the keystone session and get the client
        keystone._SESSION = mock.MagicMock()
        bc1 = clients.CinderAuth.get_cinder_client(
            region=None, endpoint_type='publicURL', insecure=True)

        # Our returned client should also be the saved client
        self.assertIsInstance(
            clients.CinderAuth.cinder_client,
            cinderclient.v3.client.Client
        )
        self.assertIs(
            clients.CinderAuth.cinder_client,
            bc1
        )

        # Getting the session again should return the same object
        bc2 = clients.CinderAuth.get_cinder_client(
            region="test-region", service_name="cinderEndpoint1",
            endpoint="test-endpoint", endpoint_type='publicURL', insecure=True)
        self.assertIs(bc1, bc2)


class TestUserNeutronClient(base.TestCase):

    def setUp(self):
        super().setUp()
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(group='neutron', valid_interfaces=['internal'])
        self.service_catalog = [{
            'type': 'network',
            'endpoints': [{'region': 'RegionOne',
                           'internalURL': 'http://user-neutron',
                           'publicURL': 'http://public-neutron'}]}]
        self.requests_mock = self.useFixture(rm_fixture.Fixture())
        self.requests_mock.get(
            'http://override-neutron',
            json={'versions': [{
                'id': 'v2.0', 'status': 'CURRENT',
                'links': [{'rel': 'self',
                           'href': 'http://override-neutron/v2.0/'}]}]})
        self.requests_mock.get(re.compile('/v2.0/subnets/subnet-id$'),
                               json={'subnet': {'id': 'subnet-id'}})

    def _get_subnet(self):
        user_context = mock.Mock(auth_token='user-token',
                                 service_catalog=self.service_catalog)
        user_context.get_auth_plugin.return_value = (
            context._ContextAuthPlugin('user-token', self.service_catalog))
        conn = clients.NeutronAuth.get_user_neutron_client(user_context)
        self.addCleanup(conn.close)
        return conn.network.get_subnet('subnet-id')

    def test_endpoint_from_user_catalog(self):
        self._get_subnet()

        request = self.requests_mock.last_request
        self.assertEqual('http://user-neutron/v2.0/subnets/subnet-id',
                         request.url)
        self.assertEqual('user-token', request.headers['X-Auth-Token'])

    def test_endpoint_override(self):
        self.conf.config(group='neutron',
                         endpoint_override='http://override-neutron')

        self._get_subnet()

        self.assertEqual('http://override-neutron/v2.0/subnets/subnet-id',
                         self.requests_mock.last_request.url)

    def test_no_endpoint_in_user_catalog(self):
        self.service_catalog = [{
            'type': 'compute',
            'endpoints': [{'region': 'RegionOne',
                           'internalURL': 'http://user-nova'}]}]

        self.assertRaises(os_exceptions.SDKException, self._get_subnet)
        self.assertFalse(self.requests_mock.called)

    @mock.patch('octavia.common.keystone.KeystoneSession')
    def test_no_user_catalog(self, mock_ks):
        self.service_catalog = []
        get_endpoint_data = (
            mock_ks.return_value.get_session.return_value.get_endpoint_data)
        get_endpoint_data.return_value.catalog_url = 'http://service-neutron'

        self._get_subnet()

        get_endpoint_data.assert_called_once_with(
            service_type='network', interface=['internal'], region_name=None)
        request = self.requests_mock.last_request
        self.assertEqual('http://service-neutron/v2.0/subnets/subnet-id',
                         request.url)
        self.assertEqual('user-token', request.headers['X-Auth-Token'])
