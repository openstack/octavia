#    Copyright 2014 Rackspace
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

from keystoneclient import session
import mock
import novaclient.v2
from oslo_config import cfg
from oslo_utils import uuidutils

from octavia.common import constants
from octavia.common import data_models as models
from octavia.common import exceptions
import octavia.compute.drivers.nova_driver as nova_common
import octavia.tests.unit.base as base


CONF = cfg.CONF
CONF.import_group('networking', 'octavia.common.config')


class TestNovaClient(base.TestCase):

    def setUp(self):
        net_name = uuidutils.generate_uuid()
        CONF.set_override(group='networking', name='lb_network_name',
                          override=net_name)
        self.amphora = models.Amphora(
            compute_id=uuidutils.generate_uuid(),
            status='ACTIVE',
            lb_network_ip='10.0.0.1'
        )

        self.nova_response = mock.Mock()
        self.nova_response.id = self.amphora.compute_id
        self.nova_response.status = 'ACTIVE'
        self.nova_response.addresses = {net_name: [{'addr': '10.0.0.1'}]}

        self.manager = nova_common.VirtualMachineManager()
        self.manager.manager = mock.MagicMock()
        self.manager.manager.get.return_value = self.nova_response
        self.manager.manager.create.return_value = self.nova_response

        super(TestNovaClient, self).setUp()

    def test_build(self):
        amphora_id = self.manager.build(amphora_flavor=1, image_id=1,
                                        key_name=1,
                                        sec_groups=1,
                                        network_ids=[1],
                                        user_data='Blah',
                                        config_drive_files='Files Blah')

        self.assertEqual(self.amphora.compute_id, amphora_id)

        self.manager.manager.create.assert_called_with(
            name="amphora_name",
            nics=[{'net-id': 1}],
            image=1,
            flavor=1,
            key_name=1,
            security_groups=1,
            config_drive_files='Files Blah',
            user_data='Blah',
            config_drive=True)

    def test_bad_build(self):
        self.manager.manager.create.side_effect = Exception
        self.assertRaises(exceptions.ComputeBuildException, self.manager.build)

    def test_delete(self):
        amphora_id = self.manager.build(amphora_flavor=1, image_id=1,
                                        key_name=1, sec_groups=1,
                                        network_ids=[1])
        self.manager.delete(amphora_id)
        self.manager.manager.delete.assert_called_with(server=amphora_id)

    def test_bad_delete(self):
        self.manager.manager.delete.side_effect = Exception
        amphora_id = self.manager.build(amphora_flavor=1, image_id=1,
                                        key_name=1, sec_groups=1,
                                        network_ids=[1])
        self.assertRaises(exceptions.ComputeDeleteException,
                          self.manager.delete, amphora_id)

    def test_status(self):
        status = self.manager.status(self.amphora.id)
        self.assertEqual(constants.AMPHORA_UP, status)

    def test_bad_status(self):
        self.manager.manager.get.side_effect = Exception
        self.assertRaises(exceptions.ComputeStatusException,
                          self.manager.status, self.amphora.id)

    def test_get_amphora(self):
        amphora = self.manager.get_amphora(self.amphora.compute_id)
        self.assertEqual(self.amphora, amphora)
        self.manager.manager.get.called_with(server=amphora.id)

    def test_bad_get_amphora(self):
        self.manager.manager.get.side_effect = Exception
        self.assertRaises(exceptions.ComputeGetException,
                          self.manager.get_amphora, self.amphora.id)


class TestNovaAuth(base.TestCase):

    def setUp(self):
        # Reset the session and client
        nova_common.NovaKeystoneAuth._keystone_session = None
        nova_common.NovaKeystoneAuth._nova_client = None

        super(TestNovaAuth, self).setUp()

    def test_get_keystone_client(self):
        # There should be no existing session
        self.assertIsNone(
            nova_common.NovaKeystoneAuth._keystone_session
        )

        # Get us a session
        ks1 = nova_common.NovaKeystoneAuth._get_keystone_session()

        # Our returned session should also be the saved session
        self.assertIsInstance(
            nova_common.NovaKeystoneAuth._keystone_session,
            session.Session
        )
        self.assertIs(
            nova_common.NovaKeystoneAuth._keystone_session,
            ks1
        )

        # Getting the session again should return the same object
        ks2 = nova_common.NovaKeystoneAuth._get_keystone_session()
        self.assertIs(ks1, ks2)

    def test_get_nova_client(self):
        # There should be no existing client
        self.assertIsNone(
            nova_common.NovaKeystoneAuth._nova_client
        )

        # Mock out the keystone session and get the client
        nova_common.NovaKeystoneAuth._keystone_session = (
            mock.MagicMock()
        )
        bc1 = nova_common.NovaKeystoneAuth.get_nova_client(region=None)

        # Our returned client should also be the saved client
        self.assertIsInstance(
            nova_common.NovaKeystoneAuth._nova_client,
            novaclient.v2.client.Client
        )
        self.assertIs(
            nova_common.NovaKeystoneAuth._nova_client,
            bc1
        )

        # Getting the session again should return the same object
        bc2 = nova_common.NovaKeystoneAuth.get_nova_client(
            region="test-region")
        self.assertIs(bc1, bc2)
