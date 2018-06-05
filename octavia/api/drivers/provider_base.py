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
    # name is for internal Octavia use and should not be used by drivers
    name = None

    # Load Balancer
    def create_vip_port(self, loadbalancer_id, project_id, vip_dictionary):
        """Creates a port for a load balancer VIP.

        If the driver supports creating VIP ports, the driver will create a
        VIP port and return the vip_dictionary populated with the vip_port_id.
        If the driver does not support port creation, the driver will raise
        a NotImplementedError.

        :param loadbalancer_id: ID of loadbalancer.
        :type loadbalancer_id: string
        :param project_id: The project ID to create the VIP under.
        :type project_id: string
        :param: vip_dictionary: The VIP dictionary.
        :type vip_dictionary: dict
        :returns: VIP dictionary with vip_port_id.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: The driver does not support creating
          VIP ports.
        """
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support creating VIP '
                              'ports.',
            operator_fault_string='This provider does not support creating '
                                  'VIP ports. Octavia will create it.')

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
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support creating '
                              'load balancers.',
            operator_fault_string='This provider does not support creating '
                                  'load balancers. What?')

    def loadbalancer_delete(self, loadbalancer, cascade=False):
        """Deletes a load balancer.

        :param loadbalancer: The load balancer to delete.
        :type loadbalancer: object
        :param cascade: If True, deletes all child objects (listeners,
          pools, etc.) in addition to the load balancer.
        :type cascade: bool
        :return: Nothing if the delete request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        """
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support deleting '
                              'load balancers.',
            operator_fault_string='This provider does not support deleting '
                                  'load balancers.')

    def loadbalancer_failover(self, loadbalancer_id):
        """Performs a fail over of a load balancer.

        :param loadbalancer_id: ID of the load balancer to failover.
        :type loadbalancer_id: string
        :return: Nothing if the failover request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises: NotImplementedError if driver does not support request.
        """
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support failing over '
                              'load balancers.',
            operator_fault_string='This provider does not support failing '
                                  'over load balancers.')

    def loadbalancer_update(self, old_loadbalancer, new_loadbalncer):
        """Updates a load balancer.

        :param old_loadbalancer: The baseline load balancer object.
        :type old_loadbalancer: object
        :param new_loadbalancer: The updated load balancer object.
        :type new_loadbalancer: object
        :return: Nothing if the update request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: The driver does not support request.
        :raises UnsupportedOptionError: The driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support updating '
                              'load balancers.',
            operator_fault_string='This provider does not support updating '
                                  'load balancers.')

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
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support creating '
                              'listeners.',
            operator_fault_string='This provider does not support creating '
                                  'listeners.')

    def listener_delete(self, listener):
        """Deletes a listener.

        :param listener: The listener to delete.
        :type listener: object
        :return: Nothing if the delete request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        """
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support deleting '
                              'listeners.',
            operator_fault_string='This provider does not support deleting '
                                  'listeners.')

    def listener_update(self, old_listener, new_listener):
        """Updates a listener.

        :param old_listener: The baseline listener object.
        :type old_listener: object
        :param new_listener: The updated listener object.
        :type new_listener: object
        :return: Nothing if the update request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support updating '
                              'listeners.',
            operator_fault_string='This provider does not support updating '
                                  'listeners.')

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
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support creating '
                              'pools.',
            operator_fault_string='This provider does not support creating '
                                  'pools.')

    def pool_delete(self, pool):
        """Deletes a pool and its members.

        :param pool: The pool to delete.
        :type pool: object
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        """
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support deleting '
                              'pools.',
            operator_fault_string='This provider does not support deleting '
                                  'pools.')

    def pool_update(self, old_pool, new_pool):
        """Updates a pool.

        :param pool: The baseline pool object.
        :type pool: object
        :param pool: The updated pool object.
        :type pool: object
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support updating '
                              'pools.',
            operator_fault_string='This provider does not support updating '
                                  'pools.')

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
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support creating '
                              'members.',
            operator_fault_string='This provider does not support creating '
                                  'members.')

    def member_delete(self, member):
        """Deletes a pool member.

        :param member: The member to delete.
        :type member: object
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        """
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support deleting '
                              'members.',
            operator_fault_string='This provider does not support deleting '
                                  'members.')

    def member_update(self, old_member, new_member):
        """Updates a pool member.

        :param old_member: The baseline member object.
        :type old_member: object
        :param new_member: The updated member object.
        :type new_member: object
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support updating '
                              'members.',
            operator_fault_string='This provider does not support updating '
                                  'members.')

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
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support batch '
                              'updating members.',
            operator_fault_string='This provider does not support batch '
                                  'updating members.')

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
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support creating '
                              'health monitors.',
            operator_fault_string='This provider does not support creating '
                                  'health monitors.')

    def health_monitor_delete(self, healthmonitor):
        """Deletes a healthmonitor_id.

        :param healthmonitor: The monitor to delete.
        :type healthmonitor: object
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        """
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support deleting '
                              'health monitors.',
            operator_fault_string='This provider does not support deleting '
                                  'health monitors.')

    def health_monitor_update(self, old_healthmonitor, new_healthmonitor):
        """Updates a health monitor.

        :param old_healthmonitor: The baseline health monitor object.
        :type old_healthmonitor: object
        :param new_healthmonitor: The updated health monitor object.
        :type new_healthmonitor: object
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support updating '
                              'health monitors.',
            operator_fault_string='This provider does not support updating '
                                  'health monitors.')

    # L7 Policy
    def l7policy_create(self, l7policy):
        """Creates a new L7 policy.

        :param l7policy: The L7 policy object.
        :type l7policy: object
        :return: Nothing if the create request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support creating '
                              'l7policies.',
            operator_fault_string='This provider does not support creating '
                                  'l7policies.')

    def l7policy_delete(self, l7policy):
        """Deletes an L7 policy.

        :param l7policy: The L7 policy to delete.
        :type l7policy: object
        :return: Nothing if the delete request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        """
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support deleting '
                              'l7policies.',
            operator_fault_string='This provider does not support deleting '
                                  'l7policies.')

    def l7policy_update(self, old_l7policy, new_l7policy):
        """Updates an L7 policy.

        :param old_l7policy: The baseline L7 policy object.
        :type old_l7policy: object
        :param new_l7policy: The updated L7 policy object.
        :type new_l7policy: object
        :return: Nothing if the update request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support updating '
                              'l7policies.',
            operator_fault_string='This provider does not support updating '
                                  'l7policies.')

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
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support creating '
                              'l7rules.',
            operator_fault_string='This provider does not support creating '
                                  'l7rules.')

    def l7rule_delete(self, l7rule):
        """Deletes an L7 rule.

        :param l7rule: The L7 rule to delete.
        :type l7rule: object
        :return: Nothing if the delete request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        """
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support deleting '
                              'l7rules.',
            operator_fault_string='This provider does not support deleting '
                                  'l7rules.')

    def l7rule_update(self, old_l7rule, new_l7rule):
        """Updates an L7 rule.

        :param old_l7rule: The baseline L7 rule object.
        :type old_l7rule: object
        :param new_l7rule: The updated L7 rule object.
        :type new_l7rule: object
        :return: Nothing if the update request was accepted.
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: if driver does not support request.
        :raises UnsupportedOptionError: if driver does not
          support one of the configuration options.
        """
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support updating '
                              'l7rules.',
            operator_fault_string='This provider does not support updating '
                                  'l7rules.')

    # Flavor
    def get_supported_flavor_metadata(self):
        """Returns a dict of flavor metadata keys supported by this driver.

        The returned dictionary will include key/value pairs, 'name' and
        'description.'

        :returns: The flavor metadata dictionary
        :raises DriverError: An unexpected error occurred in the driver.
        :raises NotImplementedError: The driver does not support flavors.
        """
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support getting the '
                              'supported flavor metadata.',
            operator_fault_string='This provider does not support getting '
                                  'the supported flavor metadata.')

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
        raise exceptions.NotImplementedError(
            user_fault_string='This provider does not support validating '
                              'flavors.',
            operator_fault_string='This provider does not support validating '
                                  'the supported flavor metadata.')
