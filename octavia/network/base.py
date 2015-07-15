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


class SubnetNotFound(NetworkException):
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
    def allocate_vip(self, load_balancer):
        """Allocates a virtual ip.

        Reserves it for later use as the frontend connection of a load
        balancer.

        :param load_balancer: octavia.common.data_models.LoadBalancer instance
        :return: octavia.common.data_models.VIP
        :raises: AllocateVIPException, PortNotFound, SubnetNotFound
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
        :raises: PlugVIPException, PortNotFound
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
    def plug_network(self, compute_id, network_id, ip_address=None):
        """Connects an existing amphora to an existing network.

        :param compute_id: id of an amphora in the compute service
        :param network_id: id of a network
        :param ip_address: ip address to attempt to be assigned to interface
        :return: octavia.network.data_models.Interface instance
        :raises: PlugNetworkException, AmphoraNotFound, NetworkNotFound
        """

    @abc.abstractmethod
    def unplug_network(self, compute_id, network_id, ip_address=None):
        """Disconnects an existing amphora from an existing network.

        If ip_address is not specificed, all the interfaces plugged on
        network_id should be unplugged.

        :param compute_id: id of an amphora in the compute service
        :param network_id: id of a network
        :param ip_address: specific ip_address to unplug
        :return: None
        :raises: UnplugNetworkException, AmphoraNotFound, NetworkNotFound,
                 NetworkException
        """
        pass

    @abc.abstractmethod
    def get_plugged_networks(self, compute_id):
        """Retrieves the current plugged networking configuration.

        :param compute_id: id of an amphora in the compute service
        :return: [octavia.network.data_models.Instance]
        """

    def update_vip(self, load_balancer):
        """Hook for the driver to update the VIP information.

        This method will be called upon the change of a load_balancer
        configuration. It is an optional method to be implemented by drivers.
        It allows the driver to update any VIP information based on the
        state of the passed in load_balancer.

        :param load_balancer: octavia.common.data_models.LoadBalancer instance
        :return: None
        """
        pass

    @abc.abstractmethod
    def get_network(self, network_id):
        """Retrieves network from network id.

        :param network_id: id of an network to retrieve
        :return: octavia.network.data_models.Network
        :raises: NetworkException, NetworkNotFound
        """
        pass

    @abc.abstractmethod
    def get_subnet(self, subnet_id):
        """Retrieves subnet from subnet id.

        :param subnet_id: id of a subnet to retrieve
        :return: octavia.network.data_models.Subnet
        :raises: NetworkException, SubnetNotFound
        """
        pass

    @abc.abstractmethod
    def get_port(self, port_id):
        """Retrieves port from port id.

        :param port_id: id of a port to retrieve
        :return: octavia.network.data_models.Port
        :raises: NetworkException, PortNotFound
        """
        pass

    @abc.abstractmethod
    def failover_preparation(self, amphora):
        """Prepare an amphora for failover.

        :param amphora: amphora object to failover
        :return: None
        :raises: PortNotFound
        """
        pass
