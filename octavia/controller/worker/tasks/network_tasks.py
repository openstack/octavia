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
#

import logging

from oslo_config import cfg
import six
from stevedore import driver as stevedore_driver
from taskflow import task
from taskflow.types import failure

from octavia.common import constants
from octavia.i18n import _LW, _LE
from octavia.network import base
from octavia.network import data_models as n_data_models

LOG = logging.getLogger(__name__)
CONF = cfg.CONF
CONF.import_group('controller_worker', 'octavia.common.config')


class BaseNetworkTask(task.Task):
    """Base task to load drivers common to the tasks."""

    def __init__(self, **kwargs):
        super(BaseNetworkTask, self).__init__(**kwargs)

        self.network_driver = stevedore_driver.DriverManager(
            namespace='octavia.network.drivers',
            name=CONF.controller_worker.network_driver,
            invoke_on_load=True,
            invoke_kwds={'region': CONF.os_region_name}
        ).driver


class CalculateAmphoraDelta(BaseNetworkTask):

    default_provides = constants.DELTA

    def execute(self, loadbalancer, amphora):
        LOG.debug("Calculating network delta for amphora id: %s" % amphora.id)

        # Figure out what networks we want
        # seed with lb network(s)
        subnet = self.network_driver.get_subnet(loadbalancer.vip.subnet_id)
        desired_network_ids = {CONF.controller_worker.amp_network,
                               subnet.network_id}

        if not loadbalancer.listeners:
            return None

        for listener in loadbalancer.listeners:
            if (not listener.default_pool) or (
                    not listener.default_pool.members):
                continue
            member_networks = [
                self.network_driver.get_subnet(member.subnet_id).network_id
                for member in listener.default_pool.members
                if member.subnet_id
            ]
            desired_network_ids.update(member_networks)

        nics = self.network_driver.get_plugged_networks(amphora.compute_id)
        # assume we don't have two nics in the same network
        actual_network_nics = dict((nic.network_id, nic) for nic in nics)

        del_ids = set(actual_network_nics) - desired_network_ids
        delete_nics = list(
            actual_network_nics[net_id] for net_id in del_ids)

        add_ids = desired_network_ids - set(actual_network_nics)
        add_nics = list(n_data_models.Interface(
            network_id=net_id) for net_id in add_ids)
        delta = n_data_models.Delta(
            amphora_id=amphora.id, compute_id=amphora.compute_id,
            add_nics=add_nics, delete_nics=delete_nics)
        return delta


class CalculateDelta(BaseNetworkTask):
    """Task to calculate the delta between

    the nics on the amphora and the ones
    we need. Returns a list for
    plumbing them.
    """

    default_provides = constants.DELTAS

    def execute(self, loadbalancer):
        """Compute which NICs need to be plugged

        for the amphora to become operational.
        :param loadbalancer: the loadbalancer to calculate deltas for all
                              amphorae
        :returns: dict of octavia.network.data_models.Delta keyed off amphora
                  id
        """

        calculate_amp = CalculateAmphoraDelta()
        deltas = {}
        for amphora in loadbalancer.amphorae:
            delta = calculate_amp.execute(loadbalancer, amphora)
            deltas[amphora.id] = delta
        return deltas


class GetPlumbedNetworks(BaseNetworkTask):
    """Task to figure out the NICS on an amphora.

    This will likely move into the amphora driver
    :returns: Array of networks
    """

    default_provides = constants.NICS

    def execute(self, amphora):
        """Get plumbed networks for the amphora."""

        LOG.debug("Getting plumbed networks for amphora id: %s" % amphora.id)

        return self.network_driver.get_plugged_networks(amphora.compute_id)


class PlugNetworks(BaseNetworkTask):
    """Task to plug the networks.

    This uses the delta to add all missing networks/nics
    """

    def execute(self, amphora, delta):
        """Update the amphora networks for the delta."""

        LOG.debug("Plug or unplug networks for amphora id: %s" % amphora.id)

        if not delta:
            LOG.debug("No network deltas for amphora id: %s" % amphora.id)
            return None

        # add nics
        for nic in delta.add_nics:
            self.network_driver.plug_network(amphora.compute_id,
                                             nic.network_id)

    def revert(self, amphora, delta):
        """Handle a failed network plug by removing all nics added."""

        LOG.warn(_LW("Unable to plug networks for amp id %s"), amphora.id)
        if not delta:
            return

        for nic in delta.add_nics:
            try:
                self.network_driver.unplug_network(amphora.compute_id,
                                                   nic.network_id)
            except base.NetworkNotFound:
                pass


class UnPlugNetworks(BaseNetworkTask):
    """Task to unplug the networks

    Loop over all nics and unplug them
    based on delta
    """

    def execute(self, amphora, delta):
        """Unplug the networks."""

        LOG.debug("Unplug network for amphora")
        if not delta:
            LOG.debug("No network deltas for amphora id: %s" % amphora.id)
            return None

        for nic in delta.delete_nics:
            try:
                self.network_driver.unplug_network(amphora.compute_id,
                                                   nic.network_id)
            except base.NetworkNotFound as e:
                LOG.debug("Network %d not found ", nic.network_id)
                pass
            except Exception as e:
                LOG.error(
                    _LE("Unable to unplug network - exception: %s"),
                    str(e))
                pass  # Todo(german) follow up if that makes sense


class GetMemberPorts(BaseNetworkTask):

    def execute(self, loadbalancer, amphora):
        vip_port = self.network_driver.get_port(loadbalancer.vip.port_id)
        member_ports = []
        interfaces = self.network_driver.get_plugged_networks(
            amphora.compute_id)
        for interface in interfaces:
            port = self.network_driver.get_port(interface.port_id)
            if vip_port.network_id == port.network_id:
                continue
            port.network = self.network_driver.get_network(port.network_id)
            for fixed_ip in port.fixed_ips:
                fixed_ip.subnet = self.network_driver.get_subnet(
                    fixed_ip.subnet_id)
            member_ports.append(port)
        return member_ports


class HandleNetworkDeltas(BaseNetworkTask):
    """Task to plug and unplug networks

    Loop through the deltas and plug or unplug
    networks based on delta
    """

    def execute(self, deltas):
        """Handle network plugging based off deltas."""

        added_ports = {}
        for amp_id, delta in six.iteritems(deltas):
            added_ports[amp_id] = []
            for nic in delta.add_nics:
                interface = self.network_driver.plug_network(delta.compute_id,
                                                             nic.network_id)
                port = self.network_driver.get_port(interface.port_id)
                port.network = self.network_driver.get_network(port.network_id)
                for fixed_ip in port.fixed_ips:
                    fixed_ip.subnet = self.network_driver.get_subnet(
                        fixed_ip.subnet_id)
                added_ports[amp_id].append(port)
            for nic in delta.delete_nics:
                try:
                    self.network_driver.unplug_network(delta.compute_id,
                                                       nic.network_id)
                except base.NetworkNotFound:
                    LOG.debug("Network %d not found ", nic.network_id)
                except Exception as e:
                    LOG.error(
                        _LE("Unable to unplug network - exception: %s"), e)
        return added_ports

    def revert(self, result, deltas):
        """Handle a network plug or unplug failures."""

        if isinstance(result, failure.Failure):
            return
        for amp_id, delta in six.iteritems(deltas):
            LOG.warn(_LW("Unable to plug networks for amp id %s"),
                     delta.amphora_id)
            if not delta:
                return

            for nic in delta.add_nics:
                try:
                    self.network_driver.unplug_network(delta.compute_id,
                                                       nic.network_id)
                except base.NetworkNotFound:
                    pass


class PlugVIP(BaseNetworkTask):
    """Task to plumb a VIP."""

    def execute(self, loadbalancer):
        """Plumb a vip to an amphora."""

        LOG.debug("Plumbing VIP for loadbalancer id: %s" % loadbalancer.id)

        amps_data = self.network_driver.plug_vip(loadbalancer,
                                                 loadbalancer.vip)
        return amps_data

    def revert(self, result, loadbalancer, *args, **kwargs):
        """Handle a failure to plumb a vip."""

        if isinstance(result, failure.Failure):
            return
        LOG.warn(_LW("Unable to plug VIP for loadbalancer id %s"),
                 loadbalancer.id)

        self.network_driver.unplug_vip(loadbalancer, loadbalancer.vip)


class UnplugVIP(BaseNetworkTask):
    """Task to unplug the vip."""

    def execute(self, loadbalancer):
        """Unplug the vip."""

        LOG.debug("Unplug vip on amphora")
        try:
            self.network_driver.unplug_vip(loadbalancer, loadbalancer.vip)
        except Exception as e:
            LOG.error(_LE("Unable to unplug vip from load balancer"
                          "{id}: exception: {ex}").format(id=loadbalancer.id,
                                                          ex=e.message))


class AllocateVIP(BaseNetworkTask):
    """Task to allocate a VIP."""

    def execute(self, loadbalancer):
        """Allocate a vip to the loadbalancer."""

        LOG.debug("Allocate_vip port_id %s, subnet_id %s,"
                  "ip_address %s",
                  loadbalancer.vip.port_id,
                  loadbalancer.vip.subnet_id,
                  loadbalancer.vip.ip_address)
        return self.network_driver.allocate_vip(loadbalancer)

    def revert(self, result, loadbalancer, *args, **kwargs):
        """Handle a failure to allocate vip."""

        if isinstance(result, failure.Failure):
            LOG.exception(_LE("Unable to allocate VIP"))
            return
        vip = result
        LOG.warn(_LW("Deallocating vip %s"), vip.ip_address)
        self.network_driver.deallocate_vip(vip)


class DeallocateVIP(BaseNetworkTask):
    """Task to deallocate a VIP."""

    def execute(self, loadbalancer):
        """Deallocate a VIP."""

        LOG.debug("Deallocating a VIP %s", loadbalancer.vip.ip_address)

        # NOTE(blogan): this is kind of ugly but sufficient for now.  Drivers
        # will need access to the load balancer that the vip is/was attached
        # to.  However the data model serialization for the vip does not give a
        # backref to the loadbalancer if accessed through the loadbalancer.
        vip = loadbalancer.vip
        vip.load_balancer = loadbalancer
        self.network_driver.deallocate_vip(vip)
        return


class UpdateVIP(BaseNetworkTask):
    """Task to update a VIP."""

    def execute(self, loadbalancer):
        LOG.debug("Updating VIP of load_balancer %s." % loadbalancer.id)

        self.network_driver.update_vip(loadbalancer)


class GetAmphoraeNetworkConfigs(BaseNetworkTask):
    """Task to retrieve amphorae network details."""

    def execute(self, loadbalancer):
        LOG.debug("Retrieving vip network details.")
        vip_subnet = self.network_driver.get_subnet(loadbalancer.vip.subnet_id)
        vip_port = self.network_driver.get_port(loadbalancer.vip.port_id)
        amp_net_configs = {}
        for amp in loadbalancer.amphorae:
            if amp.status != constants.DELETED:
                LOG.debug("Retrieving network details for "
                          "amphora {0}".format(amp.id))
                vrrp_port = self.network_driver.get_port(amp.vrrp_port_id)
                vrrp_subnet = self.network_driver.get_subnet(
                    vrrp_port.get_subnet_id(amp.vrrp_ip))
                ha_port = self.network_driver.get_port(amp.ha_port_id)
                ha_subnet = self.network_driver.get_subnet(
                    ha_port.get_subnet_id(amp.ha_ip))
                amp_net_configs[amp.id] = n_data_models.AmphoraNetworkConfig(
                    amphora=amp,
                    vip_subnet=vip_subnet,
                    vip_port=vip_port,
                    vrrp_subnet=vrrp_subnet,
                    vrrp_port=vrrp_port,
                    ha_subnet=ha_subnet,
                    ha_port=ha_port
                )
        return amp_net_configs


class FailoverPreparationForAmphora(BaseNetworkTask):
    """Task to prepare an amphora for failover."""

    def execute(self, amphora):
        LOG.debug("Prepare amphora %s for failover." % amphora.id)

        self.network_driver.failover_preparation(amphora)


class RetrievePortIDsOnAmphoraExceptLBNetwork(BaseNetworkTask):
    """Task retrieving all the port ids on an amphora, except lb network."""

    def execute(self, amphora):
        LOG.debug("Retrieve all but the lb network port id on amphora %s." %
                  amphora.id)

        interfaces = self.network_driver.get_plugged_networks(
            compute_id=amphora.compute_id)

        ports = []
        for interface_ in interfaces:
            if interface_.port_id not in ports:
                port = self.network_driver.get_port(port_id=interface_.port_id)
                ips = port.fixed_ips
                lb_network = False
                for ip in ips:
                    if ip.ip_address == amphora.lb_network_ip:
                        lb_network = True
                if not lb_network:
                    ports.append(port)

        return ports
