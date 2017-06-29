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

from octavia.common import clients
from octavia.common import constants
from octavia.common import data_models as models
from octavia.common import exceptions
from octavia.compute import compute_base

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


def _extract_amp_image_id_by_tag(client, image_tag, image_owner):
    if image_owner:
        images = list(client.images.list(
            filters={'tag': [image_tag],
                     'owner': image_owner,
                     'status': constants.GLANCE_IMAGE_ACTIVE},
            sort='created_at:desc',
            limit=2))
    else:
        images = list(client.images.list(
            filters={'tag': [image_tag],
                     'status': constants.GLANCE_IMAGE_ACTIVE},
            sort='created_at:desc',
            limit=2))

    if not images:
        raise exceptions.GlanceNoTaggedImages(tag=image_tag)
    image_id = images[0]['id']
    num_images = len(images)
    if num_images > 1:
        LOG.warning("A single Glance image should be tagged with %(tag)s tag, "
                    "but at least two were found. Using %(image_id)s.",
                    {'tag': image_tag, 'image_id': image_id})
    return image_id


def _get_image_uuid(client, image_id, image_tag, image_owner):
    if image_id:
        if image_tag:
            LOG.warning("Both amp_image_id and amp_image_tag options defined. "
                        "Using the amp_image_id.")
        return image_id

    return _extract_amp_image_id_by_tag(client, image_tag, image_owner)


class VirtualMachineManager(compute_base.ComputeBase):
    '''Compute implementation of virtual machines via nova.'''

    def __init__(self):
        super(VirtualMachineManager, self).__init__()
        # Must initialize nova api
        self._nova_client = clients.NovaAuth.get_nova_client(
            endpoint=CONF.nova.endpoint,
            region=CONF.nova.region_name,
            endpoint_type=CONF.nova.endpoint_type,
            insecure=CONF.nova.insecure,
            cacert=CONF.nova.ca_certificates_file)
        self._glance_client = clients.GlanceAuth.get_glance_client(
            service_name=CONF.glance.service_name,
            endpoint=CONF.glance.endpoint,
            region=CONF.glance.region_name,
            endpoint_type=CONF.glance.endpoint_type,
            insecure=CONF.glance.insecure,
            cacert=CONF.glance.ca_certificates_file)
        self.manager = self._nova_client.servers
        self.server_groups = self._nova_client.server_groups

    def build(self, name="amphora_name", amphora_flavor=None,
              image_id=None, image_tag=None, image_owner=None,
              key_name=None, sec_groups=None, network_ids=None,
              port_ids=None, config_drive_files=None, user_data=None,
              server_group_id=None):
        '''Create a new virtual machine.

        :param name: optional name for amphora
        :param amphora_flavor: image flavor for virtual machine
        :param image_id: image ID for virtual machine
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

        :raises ComputeBuildException: if nova failed to build virtual machine
        :returns: UUID of amphora

        '''

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

            image_id = _get_image_uuid(
                self._glance_client, image_id, image_tag, image_owner)

            if CONF.nova.random_amphora_name_length:
                r = random.SystemRandom()
                name = "a{}".format("".join(
                    [r.choice(string.ascii_uppercase + string.digits)
                     for i in range(CONF.nova.random_amphora_name_length - 1)]
                ))

            amphora = self.manager.create(
                name=name, image=image_id, flavor=amphora_flavor,
                key_name=key_name, security_groups=sec_groups,
                nics=nics,
                files=config_drive_files,
                userdata=user_data,
                config_drive=True,
                scheduler_hints=server_group,
                availability_zone=CONF.nova.availability_zone
            )

            return amphora.id
        except Exception as e:
            LOG.exception("Nova failed to build the instance due to: %s", e)
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
        except Exception:
            LOG.exception("Error deleting nova virtual machine.")
            raise exceptions.ComputeDeleteException()

    def status(self, compute_id):
        '''Retrieve the status of a virtual machine.

        :param compute_id: virtual machine UUID
        :returns: constant of amphora status
        '''
        try:
            amphora, fault = self.get_amphora(compute_id)
            if amphora and amphora.status == 'ACTIVE':
                return constants.UP
        except Exception:
            LOG.exception("Error retrieving nova virtual machine status.")
            raise exceptions.ComputeStatusException()
        return constants.DOWN

    def get_amphora(self, compute_id):
        '''Retrieve the information in nova of a virtual machine.

        :param amphora_id: virtual machine UUID
        :returns: an amphora object
        :returns: fault message or None
        '''
        # utilize nova client ServerManager 'get' method to retrieve info
        try:
            amphora = self.manager.get(compute_id)
        except Exception:
            LOG.exception("Error retrieving nova virtual machine.")
            raise exceptions.ComputeGetException()
        return self._translate_amphora(amphora)

    def _translate_amphora(self, nova_response):
        '''Convert a nova virtual machine into an amphora object.

        :param nova_response: JSON response from nova
        :returns: an amphora object
        :returns: fault message or None
        '''
        # Extract interfaces of virtual machine to populate desired amphora
        # fields

        lb_network_ip = None
        fault = None

        try:
            inf_list = nova_response.interface_list()
            no_boot_networks = (
                not CONF.controller_worker.amp_boot_network_list)
            for interface in inf_list:
                net_id = interface.net_id
                is_boot_network = (
                    net_id in CONF.controller_worker.amp_boot_network_list)
                # Pick the first fixed_ip if this is a boot network or if
                # there are no boot networks configured (use default network)
                if is_boot_network or no_boot_networks:
                    lb_network_ip = interface.fixed_ips[0]['ip_address']
                    break
            fault = getattr(nova_response, 'fault', None)
        except Exception:
            LOG.debug('Extracting virtual interfaces through nova '
                      'os-interfaces extension failed.')

        response = models.Amphora(
            compute_id=nova_response.id,
            status=nova_response.status,
            lb_network_ip=lb_network_ip
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
        except Exception:
            LOG.exception("Error create server group instance.")
            raise exceptions.ServerGroupObjectCreateException()

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
        except Exception:
            LOG.exception("Error delete server group instance.")
            raise exceptions.ServerGroupObjectDeleteException()
