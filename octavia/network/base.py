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

import abc

import six

from octavia.common import exceptions


class NetworkException(exceptions.OctaviaException):
    pass


class PlugVIPException(NetworkException):
    pass


class UnplugVIPException(NetworkException):
    pass


class AllocateVIPException(NetworkException):
    pass


class DeallocateVIPException(NetworkException):
    pass


class PlugNetworkException(NetworkException):
    pass


class UnplugNetworkException(NetworkException):
    pass


class VIPInUseException(NetworkException):
    pass


class PortNotFound(NetworkException):
    pass


class NetworkNotFound(NetworkException):
    pass


class VIPConfigurationNotFound(NetworkException):
    pass


class AmphoraNotFound(NetworkException):
    pass


class PluggedVIPNotFound(NetworkException):
    pass


@six.add_metaclass(abc.ABCMeta)
class AbstractNetworkDriver(object):
    """This class defines the methods for a fully functional network driver.

    Implementations of this interface can expect a rollback to occur if any of
    the non-nullipotent methods raise an exception.
    """

    @abc.abstractmethod
    def allocate_vip(self, port_id=None, network_id=None, ip_address=None):
        """Allocates a virtual ip.

        Reserves it for later use as the frontend connection of a load
        balancer.

        :param port_id: id of port that has already been created.  If this is
                        provided, it will be used regardless of the other
                        parameters.
        :param network_id: if port_id is not provided, this should be
                           provided to create the virtual ip on this network.
        :param ip_address: will attempt to allocate this specific IP address
        :return: octavia.common.data_models.VIP
        :raises: AllocateVIPException, PortNotFound, NetworkNotFound
        """
        pass

    @abc.abstractmethod
    def deallocate_vip(self, vip):
        """Removes any resources that reserved this virtual ip.

        :param vip: octavia.common.data_models.VIP instance
        :return: None
        :raises: DeallocateVIPException, VIPInUseException,
                 VIPConfiigurationNotFound
        """
        pass

    @abc.abstractmethod
    def plug_vip(self, load_balancer, vip):
        """Plugs a virtual ip as the frontend connection of a load balancer.

        Sets up the routing of traffic from the vip to the load balancer
        and its amphorae.

        :param load_balancer: octavia.common.data_models.LoadBalancer instance
        :param vip: octavia.common.data_models.VIP instance
        :return: dict consisting of amphora_id as key and bind_ip as value.
                 bind_ip is the ip that the amphora should listen on to
                 receive traffic to load balance.
        :raises: PlugVIPException
        """
        pass

    @abc.abstractmethod
    def unplug_vip(self, load_balancer, vip):
        """Unplugs a virtual ip as the frontend connection of a load balancer.

        Removes the routing of traffic from the vip to the load balancer
        and its amphorae.

        :param load_balancer: octavia.common.data_models.LoadBalancer instance
        :param vip: octavia.common.data_models.VIP instance
        :return: octavia.common.data_models.VIP instance
        :raises: UnplugVIPException, PluggedVIPNotFound
        """
        pass

    @abc.abstractmethod
    def plug_network(self, amphora_id, network_id, ip_address=None):
        """Connects an existing amphora to an existing network.

        :param amphora_id: id of an amphora in the compute service
        :param network_id: id of a network
        :param ip_address: ip address to attempt to be assigned to interface
        :return: octavia.network.data_models.Interface instance
        :raises: PlugNetworkException, AmphoraNotFound, NetworkNotFound
        """

    @abc.abstractmethod
    def unplug_network(self, amphora_id, network_id, ip_address=None):
        """Disconnects an existing amphora from an existing network.

        If ip_address is not specificed, all the interfaces plugged on
        network_id should be unplugged.

        :param amphora_id: id of an amphora in the compute service
        :param network_id: id of a network
        :param ip_address: specific ip_address to unplug
        :return: None
        :raises: UnplugNetworkException, AmphoraNotFound, NetworkNotFound
        """
        pass

    @abc.abstractmethod
    def get_plugged_networks(self, amphora_id):
        """Retrieves the current plugged networking configuration.

        :param amphora_id: id of an amphora in the compute service
        :return: [octavia.network.data_models.Instance]
        :raises: AmphoraNotFound
        """