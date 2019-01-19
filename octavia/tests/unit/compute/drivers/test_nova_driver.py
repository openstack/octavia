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
from oslo_config import fixture as oslo_fixture
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
            image_id = nova_common._get_image_uuid(client, '', 'faketag', None)
        self.assertEqual('fakeid', image_id)
        extract.assert_called_with(client, 'faketag', None)

    def test__get_image_uuid_notag(self):
        client = mock.Mock()
        image_id = nova_common._get_image_uuid(client, 'fakeid', '', None)
        self.assertEqual('fakeid', image_id)

    def test__get_image_uuid_id_beats_tag(self):
        client = mock.Mock()
        image_id = nova_common._get_image_uuid(client, 'fakeid',
                                               'faketag', None)
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
            nova_common._extract_amp_image_id_by_tag, self.client,
            'faketag', None)

    def test_single_image(self):
        images = [
            {'id': uuidutils.generate_uuid(), 'tag': 'faketag'}
        ]
        self.client.images.list.return_value = images
        image_id = nova_common._extract_amp_image_id_by_tag(self.client,
                                                            'faketag', None)
        self.assertIn(image_id, images[0]['id'])

    def test_multiple_images_returns_one_of_images(self):
        images = [
            {'id': image_id, 'tag': 'faketag'}
            for image_id in [uuidutils.generate_uuid() for i in range(10)]
        ]
        self.client.images.list.return_value = images
        image_id = nova_common._extract_amp_image_id_by_tag(self.client,
                                                            'faketag', None)
        self.assertIn(image_id, [image['id'] for image in images])


class TestNovaClient(base.TestCase):

    def setUp(self):
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf = conf
        self.net_name = "lb-mgmt-net"
        conf.config(group="controller_worker",
                    amp_boot_network_list=['1', '2'])
        self.conf = conf

        self.amphora = models.Amphora(
            compute_id=uuidutils.generate_uuid(),
            status='ACTIVE',
            lb_network_ip='10.0.0.1',
            image_id=uuidutils.generate_uuid(),
            compute_flavor=uuidutils.generate_uuid()
        )

        self.nova_response = mock.Mock()
        self.nova_response.id = self.amphora.compute_id
        self.nova_response.status = 'ACTIVE'
        self.nova_response.fault = 'FAKE_FAULT'
        setattr(self.nova_response, 'OS-EXT-AZ:availability_zone', None)
        self.nova_response.image = {'id': self.amphora.image_id}
        self.nova_response.flavor = {'id': self.amphora.compute_flavor}

        self.interface_list = mock.MagicMock()
        self.interface_list.net_id = '1'
        self.interface_list.fixed_ips = [mock.MagicMock()]
        self.interface_list.fixed_ips[0] = {'ip_address': '10.0.0.1'}

        self.loadbalancer_id = uuidutils.generate_uuid()
        self.server_group_policy = constants.ANTI_AFFINITY
        self.server_group_id = uuidutils.generate_uuid()

        self.manager = nova_common.VirtualMachineManager()
        self.manager.manager = mock.MagicMock()
        self.manager.server_groups = mock.MagicMock()
        self.manager._nova_client = mock.MagicMock()
        self.manager.flavor_manager = mock.MagicMock()
        self.manager.flavor_manager.get = mock.MagicMock()

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

        self.port_id = uuidutils.generate_uuid()
        self.compute_id = uuidutils.generate_uuid()
        self.network_id = uuidutils.generate_uuid()
        self.flavor_id = uuidutils.generate_uuid()

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
            scheduler_hints=None,
            availability_zone=None
        )

    def test_build_with_availability_zone(self):
        FAKE_AZ = "my_availability_zone"
        self.conf.config(group="nova", availability_zone=FAKE_AZ)

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
            scheduler_hints=None,
            availability_zone=FAKE_AZ
        )

    def test_build_with_random_amphora_name_length(self):
        self.conf.config(group="nova", random_amphora_name_length=15)
        self.addCleanup(self.conf.config,
                        group='nova', random_amphora_name_length=0)

        self.manager.build(name="b" * 50, image_id=1)
        self.assertEqual(
            15, len(self.manager.manager.create.call_args[1]['name']))

    def test_build_with_default_boot_network(self):
        self.conf.config(group="controller_worker",
                         amp_boot_network_list='')
        amphora_id = self.manager.build(amphora_flavor=1, image_id=1,
                                        key_name=1,
                                        sec_groups=1,
                                        network_ids=None,
                                        port_ids=[2],
                                        user_data='Blah',
                                        config_drive_files='Files Blah')

        self.assertEqual(self.amphora.compute_id, amphora_id)

        self.manager.manager.create.assert_called_with(
            name="amphora_name",
            nics=[{'port-id': 2}],
            image=1,
            flavor=1,
            key_name=1,
            security_groups=1,
            files='Files Blah',
            userdata='Blah',
            config_drive=True,
            scheduler_hints=None,
            availability_zone=None
        )

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
        amphora, fault = self.manager.get_amphora(self.amphora.compute_id)
        self.assertEqual(self.amphora, amphora)
        self.assertEqual(self.nova_response.fault, fault)
        self.manager.manager.get.called_with(server=amphora.id)

    def test_bad_get_amphora(self):
        self.manager.manager.get.side_effect = Exception
        self.assertRaises(exceptions.ComputeGetException,
                          self.manager.get_amphora, self.amphora.id)

    def test_translate_amphora(self):
        amphora, fault = self.manager._translate_amphora(self.nova_response)
        self.assertEqual(self.amphora, amphora)
        self.assertEqual(self.nova_response.fault, fault)
        self.nova_response.interface_list.called_with()

    def test_translate_amphora_no_availability_zone(self):
        delattr(self.nova_response, 'OS-EXT-AZ:availability_zone')
        amphora, fault = self.manager._translate_amphora(self.nova_response)
        self.assertEqual(self.amphora, amphora)
        self.assertEqual(self.nova_response.fault, fault)
        self.nova_response.interface_list.called_with()

    def test_bad_translate_amphora(self):
        self.nova_response.interface_list.side_effect = Exception
        self.manager._nova_client.networks.get.side_effect = Exception
        amphora, fault = self.manager._translate_amphora(self.nova_response)
        self.assertIsNone(amphora.lb_network_ip)
        self.nova_response.interface_list.called_with()

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

    def test_attach_network_or_port(self):
        self.manager.attach_network_or_port(self.compute_id,
                                            self.network_id)
        self.manager.manager.interface_attach.assert_called_with(
            server=self.compute_id, net_id=self.network_id, fixed_ip=None,
            port_id=None)

    def test_attach_network_or_port_exception(self):
        self.manager.manager.interface_attach.side_effect = [
            nova_exceptions.NotFound('test_exception')]
        self.assertRaises(nova_exceptions.NotFound,
                          self.manager.attach_network_or_port,
                          self.compute_id, self.network_id)

    def test_detach_network(self):
        self.manager.detach_port(self.compute_id,
                                 self.port_id)
        self.manager.manager.interface_detach.assert_called_with(
            server=self.compute_id, port_id=self.port_id)

    def test_detach_network_with_exception(self):
        self.manager.manager.interface_detach.side_effect = [Exception]
        self.manager.detach_port(self.compute_id,
                                 self.port_id)

    def test_validate_flavor(self):
        self.manager.validate_flavor(self.flavor_id)
        self.manager.flavor_manager.get.assert_called_with(self.flavor_id)

    def test_validate_flavor_with_exception(self):
        self.manager.flavor_manager.get.side_effect = [
            nova_exceptions.NotFound(404), exceptions.OctaviaException]
        self.assertRaises(exceptions.InvalidSubresource,
                          self.manager.validate_flavor,
                          "bogus")
        self.assertRaises(exceptions.OctaviaException,
                          self.manager.validate_flavor,
                          "bogus")
