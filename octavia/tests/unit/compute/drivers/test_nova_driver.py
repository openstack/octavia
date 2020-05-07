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
from unittest import mock

from novaclient import exceptions as nova_exceptions
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.common import constants
from octavia.common import data_models as models
from octavia.common import exceptions
import octavia.compute.drivers.nova_driver as nova_common
import octavia.tests.unit.base as base


CONF = cfg.CONF


class TestNovaClient(base.TestCase):

    def setUp(self):
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf = conf
        self.net_name = "lb-mgmt-net"
        conf.config(group="controller_worker",
                    amp_boot_network_list=['1', '2'])
        conf.config(group="controller_worker",
                    image_driver='image_noop_driver')
        self.conf = conf
        self.fake_image_uuid = uuidutils.generate_uuid()

        self.amphora = models.Amphora(
            compute_id=uuidutils.generate_uuid(),
            status='ACTIVE',
            lb_network_ip='10.0.0.1',
            image_id=self.fake_image_uuid,
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
        self.manager.availability_zone_manager = mock.MagicMock()

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

        self.volume_mock = mock.MagicMock()
        setattr(self.volume_mock, 'volumeId', '1')

        self.port_id = uuidutils.generate_uuid()
        self.compute_id = uuidutils.generate_uuid()
        self.network_id = uuidutils.generate_uuid()
        self.flavor_id = uuidutils.generate_uuid()
        self.availability_zone = 'my_test_az'

        super().setUp()

    def test_build(self):
        amphora_id = self.manager.build(amphora_flavor=1, image_tag='stout',
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
            availability_zone=None,
            block_device_mapping={}
        )

    @mock.patch('stevedore.driver.DriverManager.driver')
    def test_build_with_cinder_volume(self, mock_driver):
        self.conf.config(group="controller_worker",
                         volume_driver='volume_cinder_driver')
        self.manager.volume_driver = mock_driver
        mock_driver.create_volume_from_image.return_value = 1
        amphora_id = self.manager.build(amphora_flavor=1, image_tag='pilsner',
                                        key_name=1,
                                        sec_groups=1,
                                        network_ids=[1],
                                        port_ids=[2],
                                        user_data='Blah',
                                        config_drive_files='Files Blah')

        self.assertEqual(self.amphora.compute_id, amphora_id)
        mock_driver.create_volume_from_image.assert_called_with(1)
        self.manager.manager.create.assert_called_with(
            name="amphora_name",
            nics=[{'net-id': 1}, {'port-id': 2}],
            image=None,
            flavor=1,
            key_name=1,
            security_groups=1,
            files='Files Blah',
            userdata='Blah',
            config_drive=True,
            scheduler_hints=None,
            availability_zone=None,
            block_device_mapping={'vda': '1:::true'}
        )

    def test_build_with_availability_zone(self):
        FAKE_AZ = "my_availability_zone"

        amphora_id = self.manager.build(amphora_flavor=1, image_tag='malt',
                                        key_name=1,
                                        sec_groups=1,
                                        network_ids=[1],
                                        port_ids=[2],
                                        user_data='Blah',
                                        config_drive_files='Files Blah',
                                        availability_zone=FAKE_AZ)

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
            availability_zone=FAKE_AZ,
            block_device_mapping={}
        )

    def test_build_with_availability_zone_config(self):
        FAKE_AZ = "my_availability_zone"
        self.conf.config(group="nova", availability_zone=FAKE_AZ)

        amphora_id = self.manager.build(amphora_flavor=1, image_tag='ipa',
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
            availability_zone=FAKE_AZ,
            block_device_mapping={}
        )

    def test_build_with_random_amphora_name_length(self):
        self.conf.config(group="nova", random_amphora_name_length=15)
        self.addCleanup(self.conf.config,
                        group='nova', random_amphora_name_length=0)

        self.manager.build(name="b" * 50)
        self.assertEqual(
            15, len(self.manager.manager.create.call_args[1]['name']))

    def test_build_with_default_boot_network(self):
        self.conf.config(group="controller_worker",
                         amp_boot_network_list='')
        amphora_id = self.manager.build(amphora_flavor=1, image_tag='porter',
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
            availability_zone=None,
            block_device_mapping={}
        )

    def test_bad_build(self):
        self.manager.manager.create.side_effect = Exception
        self.assertRaises(exceptions.ComputeBuildException, self.manager.build)

    def test_build_extracts_image_id_by_tag(self):
        self.manager.build(image_tag='tag')
        self.assertEqual(1, self.manager.manager.create.call_args[1]['image'])

    def test_delete(self):
        amphora_id = self.manager.build(amphora_flavor=1, image_tag='pale_ale',
                                        key_name=1, sec_groups=1,
                                        network_ids=[1])
        self.manager.delete(amphora_id)
        self.manager.manager.delete.assert_called_with(server=amphora_id)

    def test_bad_delete(self):
        self.manager.manager.delete.side_effect = Exception
        amphora_id = self.manager.build(amphora_flavor=1, image_tag='lager',
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

    def test_get_amphora_retried(self):
        self.manager.manager.get.side_effect = [Exception, self.nova_response]
        amphora, fault = self.manager.get_amphora(self.amphora.compute_id)
        self.assertEqual(self.amphora, amphora)
        self.assertEqual(self.nova_response.fault, fault)
        self.manager.manager.get.called_with(server=amphora.id)

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

    @mock.patch('stevedore.driver.DriverManager.driver')
    def test_translate_amphora_use_cinder(self, mock_driver):
        self.conf.config(group="controller_worker",
                         volume_driver='volume_cinder_driver')
        volumes_manager = self.manager._nova_client.volumes
        volumes_manager.get_server_volumes.return_value = [self.volume_mock]
        self.manager.volume_driver = mock_driver
        mock_driver.get_image_from_volume.return_value = self.fake_image_uuid
        amphora, fault = self.manager._translate_amphora(self.nova_response)
        self.assertEqual(self.amphora, amphora)
        self.assertEqual(self.nova_response.fault, fault)
        self.nova_response.interface_list.called_with()
        volumes_manager.get_server_volumes.assert_called_with(
            self.nova_response.id)
        mock_driver.get_image_from_volume.assert_called_with('1')

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

    def test_attach_network_or_port_conflict_exception(self):
        self.manager.manager.interface_attach.side_effect = (
            nova_exceptions.Conflict('test_exception'))
        interface_mock = mock.MagicMock()
        interface_mock.id = self.port_id
        bad_interface_mock = mock.MagicMock()
        bad_interface_mock.id = uuidutils.generate_uuid()
        self.manager.manager.interface_list.side_effect = [
            [interface_mock], [bad_interface_mock], [], Exception('boom')]

        # No port specified
        self.assertRaises(exceptions.ComputeUnknownException,
                          self.manager.attach_network_or_port,
                          self.compute_id, self.network_id)

        # Port already attached
        result = self.manager.attach_network_or_port(self.compute_id,
                                                     port_id=self.port_id)
        self.assertEqual(interface_mock, result)

        # Port not found
        self.assertRaises(exceptions.ComputePortInUseException,
                          self.manager.attach_network_or_port,
                          self.compute_id, port_id=self.port_id)

        # No ports attached
        self.assertRaises(exceptions.ComputePortInUseException,
                          self.manager.attach_network_or_port,
                          self.compute_id, port_id=self.port_id)

        # Get attached ports list exception
        self.assertRaises(exceptions.ComputeUnknownException,
                          self.manager.attach_network_or_port,
                          self.compute_id, port_id=self.port_id)

    def test_attach_network_or_port_general_not_found_exception(self):
        self.manager.manager.interface_attach.side_effect = [
            nova_exceptions.NotFound('test_exception')]
        self.assertRaises(exceptions.NotFound,
                          self.manager.attach_network_or_port,
                          self.compute_id, self.network_id)

    def test_attach_network_or_port_instance_not_found_exception(self):
        self.manager.manager.interface_attach.side_effect = [
            nova_exceptions.NotFound('Instance disappeared')]
        self.assertRaises(exceptions.NotFound,
                          self.manager.attach_network_or_port,
                          self.compute_id, self.network_id)

    def test_attach_network_or_port_network_not_found_exception(self):
        self.manager.manager.interface_attach.side_effect = [
            nova_exceptions.NotFound('Network disappeared')]
        self.assertRaises(exceptions.NotFound,
                          self.manager.attach_network_or_port,
                          self.compute_id, self.network_id)

    def test_attach_network_or_port_port_not_found_exception(self):
        self.manager.manager.interface_attach.side_effect = [
            nova_exceptions.NotFound('Port disappeared')]
        self.assertRaises(exceptions.NotFound,
                          self.manager.attach_network_or_port,
                          self.compute_id, self.network_id)

    def test_attach_network_or_port_unknown_exception(self):
        self.manager.manager.interface_attach.side_effect = [Exception('boom')]
        self.assertRaises(exceptions.ComputeUnknownException,
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

    def test_validate_availability_zone(self):
        mock_az = mock.Mock()
        mock_az.zoneName = self.availability_zone
        self.manager.availability_zone_manager.list.return_value = [mock_az]
        self.manager.validate_availability_zone(self.availability_zone)
        self.manager.availability_zone_manager.list.assert_called_with(
            detailed=False)

    def test_validate_availability_zone_with_exception(self):
        self.manager.availability_zone_manager.list.return_value = []
        self.assertRaises(exceptions.InvalidSubresource,
                          self.manager.validate_availability_zone,
                          "bogus")
