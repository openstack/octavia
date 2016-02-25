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

import mock
from novaclient import exceptions as nova_exceptions
from oslo_config import cfg
from oslo_utils import uuidutils

from octavia.common import clients
from octavia.common import constants
from octavia.common import data_models as models
from octavia.common import exceptions
import octavia.compute.drivers.nova_driver as nova_common
import octavia.tests.unit.base as base


CONF = cfg.CONF


class Test_GetImageUuid(base.TestCase):

    def test__get_image_uuid_tag(self):
        client = mock.Mock()
        with mock.patch.object(nova_common,
                               '_extract_amp_image_id_by_tag',
                               return_value='fakeid') as extract:
            image_id = nova_common._get_image_uuid(client, '', 'faketag')
        self.assertEqual('fakeid', image_id)
        extract.assert_called_with(client, 'faketag')

    def test__get_image_uuid_notag(self):
        client = mock.Mock()
        image_id = nova_common._get_image_uuid(client, 'fakeid', '')
        self.assertEqual('fakeid', image_id)

    def test__get_image_uuid_id_beats_tag(self):
        client = mock.Mock()
        image_id = nova_common._get_image_uuid(client, 'fakeid', 'faketag')
        self.assertEqual('fakeid', image_id)


class Test_ExtractAmpImageIdByTag(base.TestCase):

    def setUp(self):
        super(Test_ExtractAmpImageIdByTag, self).setUp()
        client_mock = mock.patch.object(clients.GlanceAuth,
                                        'get_glance_client')
        self.client = client_mock.start().return_value

    def test_no_images(self):
        self.client.images.list.return_value = []
        self.assertRaises(
            exceptions.GlanceNoTaggedImages,
            nova_common._extract_amp_image_id_by_tag, self.client, 'faketag')

    def test_single_image(self):
        images = [
            {'id': uuidutils.generate_uuid(), 'tag': 'faketag'}
        ]
        self.client.images.list.return_value = images
        image_id = nova_common._extract_amp_image_id_by_tag(self.client,
                                                            'faketag')
        self.assertIn(image_id, images[0]['id'])

    def test_multiple_images_returns_one_of_images(self):
        images = [
            {'id': image_id, 'tag': 'faketag'}
            for image_id in [uuidutils.generate_uuid() for i in range(10)]
        ]
        self.client.images.list.return_value = images
        image_id = nova_common._extract_amp_image_id_by_tag(self.client,
                                                            'faketag')
        self.assertIn(image_id, [image['id'] for image in images])


class TestNovaClient(base.TestCase):

    def setUp(self):
        CONF.set_override(group='keystone_authtoken', name='auth_version',
                          override='2', enforce_type=True)
        self.net_name = "lb-mgmt-net"
        CONF.set_override(group='networking', name='lb_network_name',
                          override=self.net_name, enforce_type=True)

        self.amphora = models.Amphora(
            compute_id=uuidutils.generate_uuid(),
            status='ACTIVE',
            lb_network_ip='10.0.0.1'
        )

        self.nova_response = mock.Mock()
        self.nova_response.id = self.amphora.compute_id
        self.nova_response.status = 'ACTIVE'

        self.interface_list = mock.MagicMock()
        self.interface_list.net_id = CONF.controller_worker.amp_network
        self.interface_list.fixed_ips = [mock.MagicMock()]
        self.interface_list.fixed_ips[0] = {'ip_address': '10.0.0.1'}

        self.loadbalancer_id = uuidutils.generate_uuid()
        self.server_group_policy = constants.ANTI_AFFINITY
        self.server_group_id = uuidutils.generate_uuid()

        self.manager = nova_common.VirtualMachineManager()
        self.manager.manager = mock.MagicMock()
        self.manager.server_groups = mock.MagicMock()
        self.manager._nova_client = mock.MagicMock()

        self.nova_response.interface_list.side_effect = [[self.interface_list]]
        self.manager.manager.get.return_value = self.nova_response
        self.manager.manager.create.return_value = self.nova_response
        self.manager.server_groups.create.return_value = mock.Mock()

        self.nova_response.addresses = {self.net_name: [{'addr': '10.0.0.1'}]}

        self.nova_network = mock.Mock()
        self.nova_network.label = self.net_name

        self.server_group_name = 'octavia-lb-' + self.loadbalancer_id
        self.server_group_kwargs = {'name': self.server_group_name,
                                    'policies': [self.server_group_policy]}

        self.server_group_mock = mock.Mock()
        self.server_group_mock.name = self.server_group_name
        self.server_group_mock.policy = self.server_group_policy
        self.server_group_mock.id = self.server_group_id

        super(TestNovaClient, self).setUp()

    def test_build(self):
        amphora_id = self.manager.build(amphora_flavor=1, image_id=1,
                                        key_name=1,
                                        sec_groups=1,
                                        network_ids=[1],
                                        port_ids=[2],
                                        user_data='Blah',
                                        config_drive_files='Files Blah')

        self.assertEqual(self.amphora.compute_id, amphora_id)

        self.manager.manager.create.assert_called_with(
            name="amphora_name",
            nics=[{'net-id': 1}, {'port-id': 2}],
            image=1,
            flavor=1,
            key_name=1,
            security_groups=1,
            files='Files Blah',
            userdata='Blah',
            config_drive=True,
            scheduler_hints=None)

    def test_bad_build(self):
        self.manager.manager.create.side_effect = Exception
        self.assertRaises(exceptions.ComputeBuildException, self.manager.build)

    def test_build_extracts_image_id_by_tag(self):
        expected_id = 'fakeid-by-tag'
        with mock.patch.object(nova_common, '_get_image_uuid',
                               return_value=expected_id):
            self.manager.build(image_id='fakeid', image_tag='tag')

        self.assertEqual(expected_id,
                         self.manager.manager.create.call_args[1]['image'])

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
        self.assertEqual(constants.UP, status)

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

    def test_translate_amphora(self):
        amphora = self.manager._translate_amphora(self.nova_response)
        self.assertEqual(self.amphora, amphora)
        self.nova_response.interface_list.called_with()

    def test_bad_translate_amphora(self):
        self.nova_response.interface_list.side_effect = Exception
        self.manager._nova_client.networks.get.side_effect = Exception
        self.assertIsNone(
            self.manager._translate_amphora(self.nova_response).lb_network_ip)
        self.nova_response.interface_list.called_with()

    def test_translate_amphora_nova_networks(self):
        self.nova_response.interface_list.side_effect = Exception
        self.manager._nova_client.networks.get.return_value = self.nova_network
        amphora = self.manager._translate_amphora(self.nova_response)
        self.assertEqual(self.amphora, amphora)
        self.assertTrue(self.nova_response.interface_list.called)
        self.manager._nova_client.networks.get.called_with(self.net_name)

    def test_create_server_group(self):
        self.manager.server_groups.create.return_value = self.server_group_mock

        sg = self.manager.create_server_group(self.server_group_name,
                                              self.server_group_policy)

        self.assertEqual(sg.id, self.server_group_id)
        self.assertEqual(sg.name, self.server_group_name)
        self.assertEqual(sg.policy, self.server_group_policy)
        self.manager.server_groups.create.called_with(
            **self.server_group_kwargs)

    def test_bad_create_server_group(self):
        self.manager.server_groups.create.side_effect = Exception
        self.assertRaises(exceptions.ServerGroupObjectCreateException,
                          self.manager.create_server_group,
                          self.server_group_name, self.server_group_policy)
        self.manager.server_groups.create.called_with(
            **self.server_group_kwargs)

    def test_delete_server_group(self):
        self.manager.delete_server_group(self.server_group_id)
        self.manager.server_groups.delete.called_with(self.server_group_id)

    def test_bad_delete_server_group(self):
        self.manager.server_groups.delete.side_effect = [
            nova_exceptions.NotFound('test_exception'), Exception]

        # NotFound should not raise an exception

        self.manager.delete_server_group(self.server_group_id)
        self.manager.server_groups.delete.called_with(self.server_group_id)

        # Catch the exception for server group object delete exception

        self.assertRaises(exceptions.ServerGroupObjectDeleteException,
                          self.manager.delete_server_group,
                          self.server_group_id)
        self.manager.server_groups.delete.called_with(self.server_group_id)
