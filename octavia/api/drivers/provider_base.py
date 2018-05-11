# Copyright 2018 Rackspace, US Inc.
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

from octavia.api.drivers import exceptions

# This class describes the abstraction of a provider driver interface.
# Load balancing provider drivers will implement this interface.


class ProviderDriver(object):
    # Load Balancer
    def create_vip_port(self, loadbalancer_id, vip_dictionary):
        """Creates a port for a load balancer VIP.

        If the driver supports creating VIP ports, the driver will create a
        VIP port and return the vip_dictionary populated with the vip_port_id.
        If the driver does not support port creation, the driver will raise
        a NotImplementedError.

        :param loadbalancer_id: ID of loadbalancer.
        :type loadbalancer_id: string
        :param: vip_dictionary: The VIP dictionary.
        :type vip_dictionary: dict
        :returns: VIP dictionary with vip_port_id.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: The driver does not support creating
          VIP ports.
        """
        raise exceptions.NotImplementedError()

    def loadbalancer_create(self, loadbalancer):
        """Creates a new load balancer.

        :param loadbalancer: The load balancer object.
        :type loadbalancer: object
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: The driver does not support create.
        :raises UnsupportedOptionError: The driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError()

    def loadbalancer_delete(self, loadbalancer_id, cascade=False):
        """Deletes a load balancer.

        :param loadbalancer_id: ID of the load balancer to delete.
        :type loadbalancer_id: string
        :param cascade: If True, deletes all child objects (listeners,
          pools, etc.) in addition to the load balancer.
        :type cascade: bool
        :return: Nothing if the delete request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        """
        raise exceptions.NotImplementedError()

    def loadbalancer_failover(self, loadbalancer_id):
        """Performs a fail over of a load balancer.

        :param loadbalancer_id: ID of the load balancer to failover.
        :type loadbalancer_id: string
        :return: Nothing if the failover request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises: NotImplementedError if driver does not support request.
        """
        raise exceptions.NotImplementedError()

    def loadbalancer_update(self, loadbalancer):
        """Updates a load balancer.

        :param loadbalancer: The load balancer object.
        :type loadbalancer: object
        :return: Nothing if the update request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: The driver does not support request.
        :raises UnsupportedOptionError: The driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError()

    # Listener
    def listener_create(self, listener):
        """Creates a new listener.

        :param listener: The listener object.
        :type listener: object
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError()

    def listener_delete(self, listener_id):
        """Deletes a listener.

        :param listener_id: ID of the listener to delete.
        :type listener_id: string
        :return: Nothing if the delete request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        """
        raise exceptions.NotImplementedError()

    def listener_update(self, listener):
        """Updates a listener.

        :param listener: The listener object.
        :type listener: object
        :return: Nothing if the update request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError()

    # Pool
    def pool_create(self, pool):
        """Creates a new pool.

        :param pool: The pool object.
        :type pool: object
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError()

    def pool_delete(self, pool_id):
        """Deletes a pool and its members.

        :param pool_id: ID of the pool to delete.
        :type pool_id: string
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        """
        raise exceptions.NotImplementedError()

    def pool_update(self, pool):
        """Updates a pool.

        :param pool: The pool object.
        :type pool: object
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError()

    # Member
    def member_create(self, member):
        """Creates a new member for a pool.

        :param member: The member object.
        :type member: object
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError()

    def member_delete(self, member_id):
        """Deletes a pool member.

        :param member_id: ID of the member to delete.
        :type member_id: string
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        """
        raise exceptions.NotImplementedError()

    def member_update(self, member):
        """Updates a pool member.

        :param member: The member object.
        :type member: object
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError()

    def member_batch_update(self, members):
        """Creates, updates, or deletes a set of pool members.

        :param members: List of member objects.
        :type members: list
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError()

    # Health Monitor
    def health_monitor_create(self, healthmonitor):
        """Creates a new health monitor.

        :param healthmonitor: The health monitor object.
        :type healthmonitor: object
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError()

    def health_monitor_delete(self, healthmonitor_id):
        """Deletes a healthmonitor_id.

        :param healthmonitor_id: ID of the monitor to delete.
        :type healthmonitor_id: string
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        """
        raise exceptions.NotImplementedError()

    def health_monitor_update(self, healthmonitor):
        """Updates a health monitor.

        :param healthmonitor: The health monitor object.
        :type healthmonitor: object
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError()

    # L7 Policy
    def l7policy_create(self, l7policy):
        """Creates a new L7 policy.

        :param l7policy: The l7policy object.
        :type l7policy: object
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError()

    def l7policy_delete(self, l7policy_id):
        """Deletes an L7 policy.

        :param l7policy_id: ID of the L7 policy to delete.
        :type l7policy_id: string
        :return: Nothing if the delete request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        """
        raise exceptions.NotImplementedError()

    def l7policy_update(self, l7policy):
        """Updates an L7 policy.

        :param l7policy: The l7policy object.
        :type l7policy: object
        :return: Nothing if the update request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError()

    # L7 Rule
    def l7rule_create(self, l7rule):
        """Creates a new L7 rule.

        :param l7rule: The L7 rule object.
        :type l7rule: object
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError()

    def l7rule_delete(self, l7rule_id):
        """Deletes an L7 rule.

        :param l7rule_id: ID of the L7 rule to delete.
        :type l7rule_id: string
        :return: Nothing if the delete request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        """
        raise exceptions.NotImplementedError()

    def l7rule_update(self, l7rule):
        """Updates an L7 rule.

        :param l7rule: The L7 rule object.
        :type l7rule: object
        :return: Nothing if the update request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError()

    # Flavor
    def get_supported_flavor_metadata(self):
        """Returns a dict of flavor metadata keys supported by this driver.

        The returned dictionary will include key/value pairs, 'name' and
        'description.'

        :returns: The flavor metadata dictionary
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: The driver does not support flavors.
        """
        raise exceptions.NotImplementedError()

    def validate_flavor(self, flavor_metadata):
        """Validates if driver can support the flavor.

        :param flavor_metadata: Dictionary with flavor metadata.
        :type flavor_metadata: dict
        :return: Nothing if the flavor is valid and supported.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: The driver does not support flavors.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError()
