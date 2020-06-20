# Copyright 2011-2014 OpenStack Foundation,author: Min Wang,German Eichberger
# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import abc


class AmphoraLoadBalancerDriver(object, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def update_amphora_listeners(self, loadbalancer, amphora,
                                 timeout_dict):
        """Update the amphora with a new configuration.

        :param loadbalancer: List of listeners to update.
        :type loadbalancer: list(octavia.db.models.Listener)
        :param amphora: The index of the specific amphora to update
        :type amphora: octavia.db.models.Amphora
        :param timeout_dict: Dictionary of timeout values for calls to the
                             amphora. May contain: req_conn_timeout,
                             req_read_timeout, conn_max_retries,
                             conn_retry_interval
        :type timeout_dict: dict
        :returns: None

        Builds a new configuration, pushes it to the amphora, and reloads
        the listener on one amphora.
        """

    @abc.abstractmethod
    def update(self, loadbalancer):
        """Update the amphora with a new configuration.

        :param loadbalancer: loadbalancer object, need to use its
                             vip.ip_address property
        :type loadbalancer: octavia.db.models.LoadBalancer
        :returns: None

        At this moment, we just build the basic structure for testing, will
        add more function along with the development.
        """

    @abc.abstractmethod
    def start(self, loadbalancer, amphora, timeout_dict=None):
        """Start the listeners on the amphora.

        :param loadbalancer: loadbalancer object to start listeners
        :type loadbalancer: octavia.db.models.LoadBalancer
        :param amphora: Amphora to start. If None, start on all amphora
        :type amphora: octavia.db.models.Amphora
        :param timeout_dict: Dictionary of timeout values for calls to the
                             amphora. May contain: req_conn_timeout,
                             req_read_timeout, conn_max_retries,
                             conn_retry_interval
        :type timeout_dict: dict
        :returns: return a value list (listener, vip, status flag--enable)

        At this moment, we just build the basic structure for testing, will
        add more function along with the development.
        """

    @abc.abstractmethod
    def reload(self, loadbalancer, amphora, timeout_dict=None):
        """Reload the listeners on the amphora.

        :param loadbalancer: loadbalancer object to reload listeners
        :type loadbalancer: octavia.db.models.LoadBalancer
        :param amphora: Amphora to start. If None, reload on all amphora
        :type amphora: octavia.db.models.Amphora
        :param timeout_dict: Dictionary of timeout values for calls to the
                             amphora. May contain: req_conn_timeout,
                             req_read_timeout, conn_max_retries,
                             conn_retry_interval
        :type timeout_dict: dict
        :returns: return a value list (listener, vip, status flag--enable)

        At this moment, we just build the basic structure for testing, will
        add more function along with the development.
        """

    @abc.abstractmethod
    def delete(self, listener):
        """Delete the listener on the vip.

        :param listener: listener object,
                         need to use its protocol_port property
        :type listener: octavia.db.models.Listener
        :returns: return a value list (listener, vip, status flag--delete)

        At this moment, we just build the basic structure for testing, will
        add more function along with the development.
        """

    @abc.abstractmethod
    def get_info(self, amphora, raise_retry_exception=False):
        """Returns information about the amphora.

        :param amphora: amphora object, need to use its id property
        :type amphora: octavia.db.models.Amphora
        :param raise_retry_exception: Flag if outside task should be retried
        :type boolean: False by default
        :returns: return a value list (amphora.id, status flag--'info')

        At this moment, we just build the basic structure for testing, will
        add more function along with the development, eventually, we want it
        to return information as:
        {"Rest Interface": "1.0", "Amphorae": "1.0",
        "packages":{"ha proxy":"1.5"}}
        some information might come from querying the amphora
        """

    @abc.abstractmethod
    def get_diagnostics(self, amphora):
        """Return ceilometer ready diagnostic data.

        :param amphora: amphora object, need to use its id property
        :type amphora: octavia.db.models.Amphora
        :returns: return a value list (amphora.id, status flag--'ge
                  t_diagnostics')

        At this moment, we just build the basic structure for testing, will
        add more function along with the development, eventually, we want it
        run some expensive self tests to determine if the amphora and the lbs
        are healthy the idea is that those tests are triggered more infrequent
        than the health gathering.
        """

    @abc.abstractmethod
    def finalize_amphora(self, amphora):
        """Finalize the amphora before any listeners are configured.

        :param amphora: amphora object, need to use its id property
        :type amphora: octavia.db.models.Amphora
        :returns: None

        At this moment, we just build the basic structure for testing, will
        add more function along with the development. This is a hook for
        drivers who need to do additional work before an amphora becomes ready
        to accept listeners. Please keep in mind that amphora might be kept in
        an offline pool after this call.
        """

    def post_vip_plug(self, amphora, load_balancer, amphorae_network_config,
                      vrrp_port=None, vip_subnet=None):
        """Called after network driver has allocated and plugged the VIP

        :param amphora:
        :type amphora: octavia.db.models.Amphora
        :param load_balancer: A load balancer that just had its vip allocated
                              and plugged in the network driver.
        :type load_balancer: octavia.common.data_models.LoadBalancer
        :param amphorae_network_config: A data model containing information
                                        about the subnets and ports that an
                                        amphorae owns.
        :param vrrp_port: VRRP port associated with the load balancer
        :type vrrp_port: octavia.network.data_models.Port

        :param vip_subnet: VIP subnet associated with the load balancer
        :type vip_subnet: octavia.network.data_models.Subnet

        :type vip_network: octavia.network.data_models.AmphoraNetworkConfig
        :returns: None

        This is to do any additional work needed on the amphorae to plug
        the vip, such as bring up interfaces.
        """

    def post_network_plug(self, amphora, port):
        """Called after amphora added to network

        :param amphora: amphora object, needs id and network ip(s)
        :type amphora: octavia.db.models.Amphora
        :param port: contains information of the plugged port
        :type port: octavia.network.data_models.Port

        This method is optional to implement.  After adding an amphora to a
        network, there may be steps necessary on the amphora to allow it to
        access said network.  Ex: creating an interface on an amphora for a
        neutron network to utilize.
        """

    def upload_cert_amp(self, amphora, pem_file):
        """Upload cert info to the amphora.

        :param amphora: amphora object, needs id and network ip(s)
        :type amphora: octavia.db.models.Amphora
        :param pem_file: a certificate file
        :type pem_file: file object

        Upload cert file to amphora for Controller Communication.
        """

    def update_amphora_agent_config(self, amphora, agent_config):
        """Upload and update the amphora agent configuration.

        :param amphora: amphora object, needs id and network ip(s)
        :type amphora: octavia.db.models.Amphora
        :param agent_config: The new amphora agent configuration file.
        :type agent_config: string
        """

    @abc.abstractmethod
    def get_interface_from_ip(self, amphora, ip_address, timeout_dict=None):
        """Get the interface name from an IP address.

        :param amphora: The amphora to query.
        :type amphora: octavia.db.models.Amphora
        :param ip_address: The IP address to lookup. (IPv4 or IPv6)
        :type ip_address: string
        :param timeout_dict: Dictionary of timeout values for calls to the
                             amphora. May contain: req_conn_timeout,
                             req_read_timeout, conn_max_retries,
                             conn_retry_interval
        :type timeout_dict: dict
        """


class VRRPDriverMixin(object, metaclass=abc.ABCMeta):
    """Abstract mixin class for VRRP support in loadbalancer amphorae

    Usage: To plug VRRP support in another service driver XYZ, use:
    @plug_mixin(XYZ)
    class XYZ: ...
    """
    @abc.abstractmethod
    def update_vrrp_conf(self, loadbalancer, amphorae_network_config, amphora,
                         timeout_dict=None):
        """Update amphorae of the loadbalancer with a new VRRP configuration

        :param loadbalancer: loadbalancer object
        :param amphorae_network_config: amphorae network configurations
        :param amphora: The amphora object to update.
        :param timeout_dict: Dictionary of timeout values for calls to the
                             amphora. May contain: req_conn_timeout,
                             req_read_timeout, conn_max_retries,
                             conn_retry_interval
        """

    @abc.abstractmethod
    def stop_vrrp_service(self, loadbalancer):
        """Stop the vrrp services running on the loadbalancer's amphorae

        :param loadbalancer: loadbalancer object
        """

    @abc.abstractmethod
    def start_vrrp_service(self, amphora, timeout_dict=None):
        """Start the VRRP services on the amphora

        :param amphora: The amphora object to start the service on.
        :param timeout_dict: Dictionary of timeout values for calls to the
                             amphora. May contain: req_conn_timeout,
                             req_read_timeout, conn_max_retries,
                             conn_retry_interval
        """

    @abc.abstractmethod
    def reload_vrrp_service(self, loadbalancer):
        """Reload the VRRP services of all amphorae of the loadbalancer

        :param loadbalancer: loadbalancer object
        """
