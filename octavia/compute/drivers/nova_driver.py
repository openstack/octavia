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

from oslo_config import cfg
from oslo_log import log as logging

from octavia.common import clients
from octavia.common import constants
from octavia.common import data_models as models
from octavia.common import exceptions
from octavia.compute import compute_base
from octavia.i18n import _LE

LOG = logging.getLogger(__name__)

CONF = cfg.CONF
CONF.import_group('keystone_authtoken', 'octavia.common.config')
CONF.import_group('networking', 'octavia.common.config')


class VirtualMachineManager(compute_base.ComputeBase):
    '''Compute implementation of virtual machines via nova.'''

    def __init__(self, region=None):
        super(VirtualMachineManager, self).__init__()
        # Must initialize nova api
        self._nova_client = clients.NovaAuth.get_nova_client(region)
        self.manager = self._nova_client.servers

    def build(self, name="amphora_name", amphora_flavor=None, image_id=None,
              key_name=None, sec_groups=None, network_ids=None,
              port_ids=None, config_drive_files=None, user_data=None):
        '''Create a new virtual machine.

        :param name: optional name for amphora
        :param amphora_flavor: image flavor for virtual machine
        :param image_id: image ID for virtual machine
        :param key_name: keypair to add to the virtual machine
        :param sec_groups: Security group IDs for virtual machine
        :param network_ids: Network IDs to include on virtual machine
        :param port_ids: Port IDs to include on virtual machine
        :param config_drive_files:  An optional dict of files to overwrite on
        the server upon boot. Keys are file names (i.e. /etc/passwd)
        and values are the file contents (either as a string or as
        a file-like object). A maximum of five entries is allowed,
        and each file must be 10k or less.
        :param user_data: Optional user data to pass to be exposed by the
        metadata server this can be a file type object as well or
        a string

        :raises NovaBuildException: if nova failed to build virtual machine
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

            amphora = self.manager.create(
                name=name, image=image_id, flavor=amphora_flavor,
                key_name=key_name, security_groups=sec_groups,
                nics=nics,
                files=config_drive_files,
                userdata=user_data,
                config_drive=True
            )

            return amphora.id
        except Exception:
            LOG.exception(_LE("Error building nova virtual machine."))
            raise exceptions.ComputeBuildException()

    def delete(self, compute_id):
        '''Delete a virtual machine.

        :param compute_id: virtual machine UUID
        '''
        try:
            self.manager.delete(server=compute_id)
        except Exception:
            LOG.exception(_LE("Error deleting nova virtual machine."))
            raise exceptions.ComputeDeleteException()

    def status(self, amphora_id):
        '''Retrieve the status of a virtual machine.

        :param amphora_id: virtual machine UUID
        :returns: constant of amphora status
        '''
        try:
            amphora = self.get_amphora(amphora_id=amphora_id)
            if amphora and amphora.status == 'ACTIVE':
                return constants.UP
        except Exception:
            LOG.exception(_LE("Error retrieving nova virtual machine status."))
            raise exceptions.ComputeStatusException()
        return constants.DOWN

    def get_amphora(self, amphora_id):
        '''Retrieve the information in nova of a virtual machine.

        :param amphora_id: virtual machine UUID
        :returns: an amphora object
        '''
        # utilize nova client ServerManager 'get' method to retrieve info
        try:
            amphora = self.manager.get(amphora_id)
        except Exception:
            LOG.exception(_LE("Error retrieving nova virtual machine."))
            raise exceptions.ComputeGetException()
        return self._translate_amphora(amphora)

    def _translate_amphora(self, nova_response):
        '''Convert a nova virtual machine into an amphora object.

        :param nova_response: JSON response from nova
        :returns: an amphora object
        '''
        # Extract information from nova response to populate desired amphora
        # fields

        net_name = self._nova_client.networks.get(
            CONF.controller_worker.amp_network).label
        lb_network_ip = None
        if net_name in nova_response.addresses:
            lb_network_ip = nova_response.addresses[net_name][0]['addr']

        response = models.Amphora(
            compute_id=nova_response.id,
            status=nova_response.status,
            lb_network_ip=lb_network_ip
        )
        return response
