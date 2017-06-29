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

import six


@six.add_metaclass(abc.ABCMeta)
class AmphoraLoadBalancerDriver(object):

    @abc.abstractmethod
    def update(self, listener, vip):
        """Update the amphora with a new configuration.

        :param listener: listener object,
                         need to use its protocol_port property
        :type listener: object
        :param vip: vip object, need to use its ip_address property
        :type vip: object
        :returns: return a value list (listener, vip, status flag--update)

        At this moment, we just build the basic structure for testing, will
        add more function along with the development.
        """
        pass

    @abc.abstractmethod
    def stop(self, listener, vip):
        """Stop the listener on the vip.

        :param listener: listener object,
                         need to use its protocol_port property
        :type listener: object
        :param vip: vip object, need to use its ip_address property
        :type vip: object
        :returns: return a value list (listener, vip, status flag--suspend)

        At this moment, we just build the basic structure for testing, will
        add more function along with the development.
        """
        pass

    @abc.abstractmethod
    def start(self, listener, vip):
        """Start the listener on the vip.

        :param listener: listener object,
                         need to use its protocol_port property
        :type listener: object
        :param vip: vip object, need to use its ip_address property
        :type vip: object
        :returns: return a value list (listener, vip, status flag--enable)

        At this moment, we just build the basic structure for testing, will
        add more function along with the development.
        """
        pass

    @abc.abstractmethod
    def delete(self, listener, vip):
        """Delete the listener on the vip.

        :param listener: listener object,
                         need to use its protocol_port property
        :type listener: object
        :param vip: vip object, need to use its ip_address property
        :type vip: object
        :returns: return a value list (listener, vip, status flag--delete)

        At this moment, we just build the basic structure for testing, will
        add more function along with the development.
        """
        pass

    @abc.abstractmethod
    def get_info(self, amphora):
        """Returns information about the amphora.

        :param amphora: amphora object, need to use its id property
        :type amphora: object
        :returns: return a value list (amphora.id, status flag--'info')

        At this moment, we just build the basic structure for testing, will
        add more function along with the development, eventually, we want it
        to return information as:
        {"Rest Interface": "1.0", "Amphorae": "1.0",
        "packages":{"ha proxy":"1.5"}}
        some information might come from querying the amphora
        """
        pass

    @abc.abstractmethod
    def get_diagnostics(self, amphora):
        """Return ceilometer ready diagnostic data.

        :param amphora: amphora object, need to use its id property
        :type amphora: object
        :returns: return a value list (amphora.id, status flag--'ge
                  t_diagnostics')

        At this moment, we just build the basic structure for testing, will
        add more function along with the development, eventually, we want it
        run some expensive self tests to determine if the amphora and the lbs
        are healthy the idea is that those tests are triggered more infrequent
        than the health gathering.
        """
        pass

    @abc.abstractmethod
    def finalize_amphora(self, amphora):
        """Finalize the amphora before any listeners are configured.

        :param amphora: amphora object, need to use its id property
        :type amphora: object
        :returns: None

        At this moment, we just build the basic structure for testing, will
        add more function along with the development. This is a hook for
        drivers who need to do additional work before an amphora becomes ready
        to accept listeners. Please keep in mind that amphora might be kept in
        an offline pool after this call.
        """
        pass

    def post_vip_plug(self, amphora, load_balancer, amphorae_network_config):
        """Called after network driver has allocated and plugged the VIP

        :param load_balancer: A load balancer that just had its vip allocated
                              and plugged in the network driver.
        :type load_balancer: octavia.common.data_models.LoadBalancer
        :param amphorae_network_config: A data model containing information
                                        about the subnets and ports that an
                                        amphorae owns.
        :type vip_network: octavia.network.data_models.AmphoraNetworkConfig
        :returns: None

        This is to do any additional work needed on the amphorae to plug
        the vip, such as bring up interfaces.
        """
        pass

    def post_network_plug(self, amphora, port):
        """Called after amphora added to network

        :param amphora: amphora object, needs id and network ip(s)
        :type amphora: object
        :param port: contains information of the plugged port
        :type port: octavia.network.data_models.Port

        This method is optional to implement.  After adding an amphora to a
        network, there may be steps necessary on the amphora to allow it to
        access said network.  Ex: creating an interface on an amphora for a
        neutron network to utilize.
        """
        pass

    def start_health_check(self, health_mixin):
        """Start health checks.

        :param health_mixin: health mixin object
        :type amphora: object

        Starts listener process and calls HealthMixin to update
        databases information.
        """
        pass

    def stop_health_check(self):
        """Stop health checks.

        Stops listener process and calls HealthMixin to update
        databases information.
        """
        pass

    def upload_cert_amp(self, amphora, pem_file):
        """Upload cert info to the amphora.

        :param amphora: amphora object, needs id and network ip(s)
        :type amphora: object
        :param pem_file: a certificate file
        :type pem_file: file object

        Upload cert file to amphora for Controller Communication.
        """
        pass


@six.add_metaclass(abc.ABCMeta)
class HealthMixin(object):
    @abc.abstractmethod
    def update_health(self, health):
        """Return ceilometer ready health

        :param health: health information emitted from the amphora
        :type health: bool
        :returns: return health

        At this moment, we just build the basic structure for testing, will
        add more function along with the development, eventually, we want it
        return:
        map: {"amphora-status":HEALTHY, loadbalancers: {"loadbalancer-id":
        {"loadbalancer-status": HEALTHY,
        "listeners":{"listener-id":{"listener-status":HEALTHY,
        "nodes":{"node-id":HEALTHY, ...}}, ...}, ...}}
        only items whose health has changed need to be submitted
        awesome update code
        """
        pass


@six.add_metaclass(abc.ABCMeta)
class StatsMixin(object):
    @abc.abstractmethod
    def update_stats(self, stats):
        """Return ceilometer ready stats

        :param stats: statistic information emitted from the amphora
        :type stats: string
        :returns: return stats

        At this moment, we just build the basic structure for testing, will
        add more function along with the development, eventually, we want it
        return:
        uses map {"loadbalancer-id":{"listener-id":
        {"bytes-in": 123, "bytes_out":123, "active_connections":123,
        "total_connections", 123}, ...}
        elements are named to keep it extsnsible for future versions
        awesome update code and code to send to ceilometer
        """
        pass


@six.add_metaclass(abc.ABCMeta)
class VRRPDriverMixin(object):
    """Abstract mixin class for VRRP support in loadbalancer amphorae

    Usage: To plug VRRP support in another service driver XYZ, use:
    @plug_mixin(XYZ)
    class XYZ: ...
    """
    @abc.abstractmethod
    def update_vrrp_conf(self, loadbalancer):
        """Update amphorae of the loadbalancer with a new VRRP configuration

        :param loadbalancer: loadbalancer object
        """
        pass

    @abc.abstractmethod
    def stop_vrrp_service(self, loadbalancer):
        """Stop the vrrp services running on the loadbalancer's amphorae

        :param loadbalancer: loadbalancer object
        """
        pass

    @abc.abstractmethod
    def start_vrrp_service(self, loadbalancer):
        """Start the VRRP services of all amphorae of the loadbalancer

        :param loadbalancer: loadbalancer object
        """
        pass

    @abc.abstractmethod
    def reload_vrrp_service(self, loadbalancer):
        """Reload the VRRP services of all amphorae of the loadbalancer

        :param loadbalancer: loadbalancer object
        """
        pass

    @abc.abstractmethod
    def get_vrrp_interface(self, amphora):
        """Get the VRRP interface object for a specific amphora

        :param amphora: amphora object
        """
        pass
