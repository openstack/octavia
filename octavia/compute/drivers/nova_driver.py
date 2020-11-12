# Copyright 2014 Rackspace
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

import random
import string

from novaclient import exceptions as nova_exceptions
from oslo_config import cfg
from oslo_log import log as logging
from stevedore import driver as stevedore_driver

from octavia.common import clients
from octavia.common import constants
from octavia.common import data_models as models
from octavia.common import exceptions
from octavia.compute import compute_base

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class VirtualMachineManager(compute_base.ComputeBase):
    '''Compute implementation of virtual machines via nova.'''

    def __init__(self):
        super().__init__()
        # Must initialize nova api
        self._nova_client = clients.NovaAuth.get_nova_client(
            endpoint=CONF.nova.endpoint,
            region=CONF.nova.region_name,
            endpoint_type=CONF.nova.endpoint_type,
            insecure=CONF.nova.insecure,
            cacert=CONF.nova.ca_certificates_file)
        self.manager = self._nova_client.servers
        self.server_groups = self._nova_client.server_groups
        self.flavor_manager = self._nova_client.flavors
        self.availability_zone_manager = self._nova_client.availability_zones
        self.volume_driver = stevedore_driver.DriverManager(
            namespace='octavia.volume.drivers',
            name=CONF.controller_worker.volume_driver,
            invoke_on_load=True
        ).driver
        self.image_driver = stevedore_driver.DriverManager(
            namespace='octavia.image.drivers',
            name=CONF.controller_worker.image_driver,
            invoke_on_load=True
        ).driver

    def build(self, name="amphora_name", amphora_flavor=None,
              image_tag=None, image_owner=None, key_name=None, sec_groups=None,
              network_ids=None, port_ids=None, config_drive_files=None,
              user_data=None, server_group_id=None, availability_zone=None):
        '''Create a new virtual machine.

        :param name: optional name for amphora
        :param amphora_flavor: image flavor for virtual machine
        :param image_tag: image tag for virtual machine
        :param key_name: keypair to add to the virtual machine
        :param sec_groups: Security group IDs for virtual machine
        :param network_ids: Network IDs to include on virtual machine
        :param port_ids: Port IDs to include on virtual machine
        :param config_drive_files:  An optional dict of files to overwrite on
                                    the server upon boot. Keys are file names
                                    (i.e. /etc/passwd) and values are the file
                                    contents (either as a string or as a
                                    file-like object). A maximum of five
                                    entries is allowed, and each file must be
                                    10k or less.
        :param user_data: Optional user data to pass to be exposed by the
                          metadata server this can be a file type object as
                          well or a string
        :param server_group_id: Optional server group id(uuid) which is used
                                for anti_affinity feature
        :param availability_zone: Name of the compute availability zone.

        :raises ComputeBuildException: if nova failed to build virtual machine
        :returns: UUID of amphora

        '''

        volume_id = None
        try:
            network_ids = network_ids or []
            port_ids = port_ids or []
            nics = []
            if network_ids:
                nics.extend([{"net-id": net_id} for net_id in network_ids])
            if port_ids:
                nics.extend([{"port-id": port_id} for port_id in port_ids])

            server_group = None if server_group_id is None else {
                "group": server_group_id}
            az_name = availability_zone or CONF.nova.availability_zone

            image_id = self.image_driver.get_image_id_by_tag(
                image_tag, image_owner)

            if CONF.nova.random_amphora_name_length:
                r = random.SystemRandom()
                name = "a{}".format("".join(
                    [r.choice(string.ascii_uppercase + string.digits)
                     for i in range(CONF.nova.random_amphora_name_length - 1)]
                ))
            block_device_mapping = {}
            if (CONF.controller_worker.volume_driver !=
                    constants.VOLUME_NOOP_DRIVER):
                # creating volume
                LOG.debug('Creating volume for amphora from image %s',
                          image_id)
                volume_id = self.volume_driver.create_volume_from_image(
                    image_id)
                LOG.debug('Created boot volume %s for amphora', volume_id)
                # If use volume based, does not require image ID anymore
                image_id = None
                # Boot from volume with parameters: target device name = vda,
                # device id = volume_id, device type and size unspecified,
                # delete-on-terminate = true (volume will be deleted by Nova
                # on instance termination)
                block_device_mapping = {'vda': '%s:::true' % volume_id}
            amphora = self.manager.create(
                name=name, image=image_id, flavor=amphora_flavor,
                block_device_mapping=block_device_mapping,
                key_name=key_name, security_groups=sec_groups,
                nics=nics,
                files=config_drive_files,
                userdata=user_data,
                config_drive=True,
                scheduler_hints=server_group,
                availability_zone=az_name
            )

            return amphora.id
        except Exception as e:
            if (CONF.controller_worker.volume_driver !=
                    constants.VOLUME_NOOP_DRIVER):
                self.volume_driver.delete_volume(volume_id)
            LOG.exception("Nova failed to build the instance due to: %s",
                          str(e))
            raise exceptions.ComputeBuildException(fault=e)

    def delete(self, compute_id):
        '''Delete a virtual machine.

        :param compute_id: virtual machine UUID
        '''
        try:
            self.manager.delete(server=compute_id)
        except nova_exceptions.NotFound:
            LOG.warning("Nova instance with id: %s not found. "
                        "Assuming already deleted.", compute_id)
        except Exception as e:
            LOG.exception("Error deleting nova virtual machine.")
            raise exceptions.ComputeDeleteException(compute_msg=str(e))

    def status(self, compute_id):
        '''Retrieve the status of a virtual machine.

        :param compute_id: virtual machine UUID
        :returns: constant of amphora status
        '''
        try:
            amphora, fault = self.get_amphora(compute_id)
            if amphora and amphora.status == 'ACTIVE':
                return constants.UP
        except Exception as e:
            LOG.exception("Error retrieving nova virtual machine status.")
            raise exceptions.ComputeStatusException() from e
        return constants.DOWN

    def get_amphora(self, compute_id, management_network_id=None):
        '''Retrieve the information in nova of a virtual machine.

        :param compute_id: virtual machine UUID
        :param management_network_id: ID of the management network
        :returns: an amphora object
        :returns: fault message or None
        '''
        # utilize nova client ServerManager 'get' method to retrieve info
        try:
            amphora = self.manager.get(compute_id)
        except Exception as e:
            LOG.exception("Error retrieving nova virtual machine.")
            raise exceptions.ComputeGetException() from e
        return self._translate_amphora(amphora, management_network_id)

    def _translate_amphora(self, nova_response, management_network_id=None):
        '''Convert a nova virtual machine into an amphora object.

        :param nova_response: JSON response from nova
        :param management_network_id: ID of the management network
        :returns: an amphora object
        :returns: fault message or None
        '''
        # Extract interfaces of virtual machine to populate desired amphora
        # fields

        lb_network_ip = None
        availability_zone = None
        image_id = None

        if management_network_id:
            boot_networks = [management_network_id]
        else:
            boot_networks = CONF.controller_worker.amp_boot_network_list

        try:
            inf_list = nova_response.interface_list()
            for interface in inf_list:
                net_id = interface.net_id
                # Pick the first fixed_ip if this is a boot network or if
                # there are no boot networks configured (use default network)
                if net_id in boot_networks or not boot_networks:
                    lb_network_ip = interface.fixed_ips[0]['ip_address']
                    break
            try:
                availability_zone = getattr(
                    nova_response, 'OS-EXT-AZ:availability_zone')
            except AttributeError:
                LOG.info('No availability zone listed for server %s',
                         nova_response.id)
        except Exception:
            LOG.debug('Extracting virtual interfaces through nova '
                      'os-interfaces extension failed.')

        fault = getattr(nova_response, 'fault', None)
        if (CONF.controller_worker.volume_driver ==
                constants.VOLUME_NOOP_DRIVER):
            image_id = nova_response.image.get("id")
        else:
            try:
                volumes = self._nova_client.volumes.get_server_volumes(
                    nova_response.id)
            except Exception:
                LOG.debug('Extracting volumes through nova '
                          'os-volumes extension failed.')
                volumes = []
            if not volumes:
                LOG.warning('Boot volume not found for volume backed '
                            'amphora instance %s ', nova_response.id)
            else:
                if len(volumes) > 1:
                    LOG.warning('Found more than one (%s) volumes '
                                'for amphora instance %s',
                                len(volumes), nova_response.id)
                volume_id = volumes[0].volumeId
                image_id = self.volume_driver.get_image_from_volume(volume_id)

        response = models.Amphora(
            compute_id=nova_response.id,
            status=nova_response.status,
            lb_network_ip=lb_network_ip,
            cached_zone=availability_zone,
            image_id=image_id,
            compute_flavor=nova_response.flavor.get("id")
        )
        return response, fault

    def create_server_group(self, name, policy):
        """Create a server group object

        :param name: the name of the server group
        :param policy: the policy of the server group
        :raises: Generic exception if the server group is not created
        :returns: the server group object
        """
        kwargs = {'name': name,
                  'policies': [policy]}
        try:
            server_group_obj = self.server_groups.create(**kwargs)
            return server_group_obj
        except Exception as e:
            LOG.exception("Error create server group instance.")
            raise exceptions.ServerGroupObjectCreateException() from e

    def delete_server_group(self, server_group_id):
        """Delete a server group object

        :raises: Generic exception if the server group is not deleted
        :param server_group_id: the uuid of a server group
        """
        try:
            self.server_groups.delete(server_group_id)

        except nova_exceptions.NotFound:
            LOG.warning("Server group instance with id: %s not found. "
                        "Assuming already deleted.", server_group_id)
        except Exception as e:
            LOG.exception("Error delete server group instance.")
            raise exceptions.ServerGroupObjectDeleteException() from e

    def attach_network_or_port(self, compute_id, network_id=None,
                               ip_address=None, port_id=None):
        """Attaching a port or a network to an existing amphora

        :param compute_id: id of an amphora in the compute service
        :param network_id: id of a network
        :param ip_address: ip address to attempt to be assigned to interface
        :param port_id: id of the neutron port
        :return: nova interface instance
        :raises ComputePortInUseException: The port is in use somewhere else
        :raises ComputeUnknownException: Unknown nova error
        """
        try:
            interface = self.manager.interface_attach(
                server=compute_id, net_id=network_id, fixed_ip=ip_address,
                port_id=port_id)
        except nova_exceptions.Conflict as e:
            # The port is already in use.
            if port_id:
                # Check if the port we want is already attached
                try:
                    interfaces = self.manager.interface_list(compute_id)
                    for interface in interfaces:
                        if interface.id == port_id:
                            return interface
                except Exception as e:
                    raise exceptions.ComputeUnknownException(exc=str(e))

                raise exceptions.ComputePortInUseException(port=port_id)

            # Nova should have created the port, so something is really
            # wrong in nova if we get here.
            raise exceptions.ComputeUnknownException(exc=str(e))
        except nova_exceptions.NotFound as e:
            if 'Instance' in str(e):
                raise exceptions.NotFound(resource='Instance', id=compute_id)
            if 'Network' in str(e):
                raise exceptions.NotFound(resource='Network', id=network_id)
            if 'Port' in str(e):
                raise exceptions.NotFound(resource='Port', id=port_id)
            raise exceptions.NotFound(resource=str(e), id=compute_id)
        except Exception as e:
            LOG.error('Error attaching network %(network_id)s with ip '
                      '%(ip_address)s and port %(port)s to amphora '
                      '(compute_id: %(compute_id)s) ',
                      {
                          'compute_id': compute_id,
                          'network_id': network_id,
                          'ip_address': ip_address,
                          'port': port_id
                      })
            raise exceptions.ComputeUnknownException(exc=str(e))
        return interface

    def detach_port(self, compute_id, port_id):
        """Detaches a port from an existing amphora.

        :param compute_id: id of an amphora in the compute service
        :param port_id: id of the port
        :return: None
        """
        try:
            self.manager.interface_detach(server=compute_id,
                                          port_id=port_id)
        except Exception:
            LOG.error('Error detaching port %(port_id)s from amphora '
                      'with compute ID %(compute_id)s. '
                      'Skipping.',
                      {
                          'port_id': port_id,
                          'compute_id': compute_id
                      })

    def validate_flavor(self, flavor_id):
        """Validates that a flavor exists in nova.

        :param flavor_id: ID of the flavor to lookup in nova.
        :raises: NotFound
        :returns: None
        """
        try:
            self.flavor_manager.get(flavor_id)
        except nova_exceptions.NotFound as e:
            LOG.info('Flavor %s was not found in nova.', flavor_id)
            raise exceptions.InvalidSubresource(resource='Nova flavor',
                                                id=flavor_id) from e
        except Exception as e:
            LOG.exception('Nova reports a failure getting flavor details for '
                          'flavor ID %s: %s', flavor_id, str(e))
            raise

    def validate_availability_zone(self, availability_zone):
        """Validates that an availability zone exists in nova.

        :param availability_zone: Name of the availability zone to lookup.
        :raises: NotFound
        :returns: None
        """
        try:
            compute_zones = [
                a.zoneName for a in self.availability_zone_manager.list(
                    detailed=False)]
            if availability_zone not in compute_zones:
                LOG.info('Availability zone %s was not found in nova. %s',
                         availability_zone, compute_zones)
                raise exceptions.InvalidSubresource(
                    resource='Nova availability zone', id=availability_zone)
        except Exception as e:
            LOG.exception('Nova reports a failure getting listing '
                          'availability zones: %s', str(e))
            raise
