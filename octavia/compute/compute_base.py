#    Copyright 2011-2014 OpenStack Foundation
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

import abc

import six


@six.add_metaclass(abc.ABCMeta)
class ComputeBase(object):

    @abc.abstractmethod
    def build(self, name="amphora_name", amphora_flavor=None,
              image_id=None, image_tag=None, image_owner=None,
              key_name=None, sec_groups=None, network_ids=None,
              config_drive_files=None, user_data=None, server_group_id=None):
        """Build a new amphora.

        :param name: Optional name for Amphora
        :param amphora_flavor: Optionally specify a flavor
        :param image_id: ID of the base image for the amphora instance
        :param image_tag: tag of the base image for the amphora instance
        :param key_name: Optionally specify a keypair
        :param sec_groups: Optionally specify list of security groups
        :param network_ids: A list of network IDs to attach to the amphora
        :param config_drive_files: An optional dict of files to overwrite on
                                   the server upon boot. Keys are file names
                                   (i.e. /etc/passwd) and values are the
                                   file contents (either as a string or as
                                   a file-like object). A maximum of five
                                   entries is allowed, and each file must be
                                   10k or less.
        :param user_data: Optional user data to pass to be exposed by the
                          metadata server this can be a file type object as
                          well or a string
        :param server_group_id: Optional server group id(uuid) which is used
                                for anti_affinity feature

        :raises ComputeBuildException: if compute failed to build amphora
        :returns: UUID of amphora
        """
        pass

    @abc.abstractmethod
    def delete(self, compute_id):
        """Delete the specified amphora

        :param compute_id: The id of the amphora to delete
        """
        pass

    @abc.abstractmethod
    def status(self, compute_id):
        """Check whether the specified amphora is up

        :param compute_id: the ID of the desired amphora
        :returns: The compute "status" response ("ONLINE" or "OFFLINE")
        """
        pass

    @abc.abstractmethod
    def get_amphora(self, compute_id):
        """Retrieve an amphora object

        :param compute_id: the id of the desired amphora
        :returns: the amphora object
        :returns: fault message or None
        """
        pass

    @abc.abstractmethod
    def create_server_group(self, name, policy):
        """Create a server group object

        :param name: the name of the server group
        :param policy: the policy of the server group
        :returns: the server group object
        """
        pass

    @abc.abstractmethod
    def delete_server_group(self, server_group_id):
        """Delete a server group object

        :param server_group_id: the uuid of a server group
        """
        pass

    @abc.abstractmethod
    def attach_network_or_port(self, compute_id, network_id=None,
                               ip_address=None, port_id=None):
        """Connects an existing amphora to an existing network.

        :param compute_id: id of an amphora in the compute service
        :param network_id: id of a network
        :param ip_address: ip address to attempt to be assigned to interface
        :param port_id: id of the neutron port
        :return: nova interface
        :raises: Exception
        """
        pass

    @abc.abstractmethod
    def detach_port(self, compute_id, port_id):
        """Disconnects an existing amphora from an existing port.

        :param compute_id: id of an amphora in the compute service
        :param port_id: id of the port
        :return: None
        :raises: Exception
        """
        pass

    @abc.abstractmethod
    def validate_flavor(self, flavor_id):
        """Validates that a compute flavor exists.

        :param flavor_id: ID of the compute flavor.
        :return: None
        :raises: NotFound
        :raises: NotImplementedError
        """
        pass
