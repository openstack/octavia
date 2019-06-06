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

from oslo_config import cfg
from oslo_log import log as logging
import six
from taskflow import task
from taskflow.types import failure

from octavia.common import constants
from octavia.common import utils
from octavia.controller.worker import task_utils
from octavia.network import base
from octavia.network import data_models as n_data_models

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class BaseNetworkTask(task.Task):
    """Base task to load drivers common to the tasks."""

    def __init__(self, **kwargs):
        super(BaseNetworkTask, self).__init__(**kwargs)
        self._network_driver = None
        self.task_utils = task_utils.TaskUtils()

    @property
    def network_driver(self):
        if self._network_driver is None:
            self._network_driver = utils.get_network_driver()
        return self._network_driver


class CalculateAmphoraDelta(BaseNetworkTask):

    default_provides = constants.DELTA

    def execute(self, loadbalancer, amphora):
        LOG.debug("Calculating network delta for amphora id: %s", amphora.id)

        # Figure out what networks we want
        # seed with lb network(s)
        vrrp_port = self.network_driver.get_port(amphora.vrrp_port_id)
        desired_network_ids = {vrrp_port.network_id}.union(
            CONF.controller_worker.amp_boot_network_list)

        for pool in loadbalancer.pools:
            member_networks = [
                self.network_driver.get_subnet(member.subnet_id).network_id
                for member in pool.members
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
        for amphora in six.moves.filter(
            lambda amp: amp.status == constants.AMPHORA_ALLOCATED,
                loadbalancer.amphorae):

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

        LOG.debug("Getting plumbed networks for amphora id: %s", amphora.id)

        return self.network_driver.get_plugged_networks(amphora.compute_id)


class PlugNetworks(BaseNetworkTask):
    """Task to plug the networks.

    This uses the delta to add all missing networks/nics
    """

    def execute(self, amphora, delta):
        """Update the amphora networks for the delta."""

        LOG.debug("Plug or unplug networks for amphora id: %s", amphora.id)

        if not delta:
            LOG.debug("No network deltas for amphora id: %s", amphora.id)
            return

        # add nics
        for nic in delta.add_nics:
            self.network_driver.plug_network(amphora.compute_id,
                                             nic.network_id)

    def revert(self, amphora, delta, *args, **kwargs):
        """Handle a failed network plug by removing all nics added."""

        LOG.warning("Unable to plug networks for amp id %s", amphora.id)
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
            LOG.debug("No network deltas for amphora id: %s", amphora.id)
            return

        for nic in delta.delete_nics:
            try:
                self.network_driver.unplug_network(amphora.compute_id,
                                                   nic.network_id)
            except base.NetworkNotFound:
                LOG.debug("Network %d not found", nic.network_id)
            except Exception:
                LOG.exception("Unable to unplug network")
                # TODO(xgerman) follow up if that makes sense


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
                if amphora.lb_network_ip == fixed_ip.ip_address:
                    break
                fixed_ip.subnet = self.network_driver.get_subnet(
                    fixed_ip.subnet_id)
            # Only add the port to the list if the IP wasn't the mgmt IP
            else:
                member_ports.append(port)
        return member_ports


class HandleNetworkDelta(BaseNetworkTask):
    """Task to plug and unplug networks

    Plug or unplug networks based on delta
    """

    def execute(self, amphora, delta):
        """Handle network plugging based off deltas."""
        added_ports = {}
        added_ports[amphora.id] = []
        for nic in delta.add_nics:
            interface = self.network_driver.plug_network(delta.compute_id,
                                                         nic.network_id)
            port = self.network_driver.get_port(interface.port_id)
            port.network = self.network_driver.get_network(port.network_id)
            for fixed_ip in port.fixed_ips:
                fixed_ip.subnet = self.network_driver.get_subnet(
                    fixed_ip.subnet_id)
            added_ports[amphora.id].append(port)
        for nic in delta.delete_nics:
            try:
                self.network_driver.unplug_network(delta.compute_id,
                                                   nic.network_id)
            except base.NetworkNotFound:
                LOG.debug("Network %d not found ", nic.network_id)
            except Exception:
                LOG.exception("Unable to unplug network")
        return added_ports

    def revert(self, result, amphora, delta, *args, **kwargs):
        """Handle a network plug or unplug failures."""

        if isinstance(result, failure.Failure):
            return

        if not delta:
            return

        LOG.warning("Unable to plug networks for amp id %s",
                    delta.amphora_id)

        for nic in delta.add_nics:
            try:
                self.network_driver.unplug_network(delta.compute_id,
                                                   nic.network_id)
            except Exception:
                pass


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
                except Exception:
                    LOG.exception("Unable to unplug network")
        return added_ports

    def revert(self, result, deltas, *args, **kwargs):
        """Handle a network plug or unplug failures."""

        if isinstance(result, failure.Failure):
            return
        for amp_id, delta in six.iteritems(deltas):
            LOG.warning("Unable to plug networks for amp id %s",
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

        LOG.debug("Plumbing VIP for loadbalancer id: %s", loadbalancer.id)

        amps_data = self.network_driver.plug_vip(loadbalancer,
                                                 loadbalancer.vip)
        return amps_data

    def revert(self, result, loadbalancer, *args, **kwargs):
        """Handle a failure to plumb a vip."""

        if isinstance(result, failure.Failure):
            return
        LOG.warning("Unable to plug VIP for loadbalancer id %s",
                    loadbalancer.id)

        try:
            # Make sure we have the current port IDs for cleanup
            for amp_data in result:
                for amphora in six.moves.filter(
                        # pylint: disable=cell-var-from-loop
                        lambda amp: amp.id == amp_data.id,
                        loadbalancer.amphorae):
                    amphora.vrrp_port_id = amp_data.vrrp_port_id
                    amphora.ha_port_id = amp_data.ha_port_id

            self.network_driver.unplug_vip(loadbalancer, loadbalancer.vip)
        except Exception as e:
            LOG.error("Failed to unplug VIP.  Resources may still "
                      "be in use from vip: %(vip)s due to error: %(except)s",
                      {'vip': loadbalancer.vip.ip_address, 'except': e})


class UpdateVIPSecurityGroup(BaseNetworkTask):
    """Task to setup SG for LB."""

    def execute(self, loadbalancer):
        """Task to setup SG for LB."""

        LOG.debug("Setup SG for loadbalancer id: %s", loadbalancer.id)

        self.network_driver.update_vip_sg(loadbalancer, loadbalancer.vip)


class GetSubnetFromVIP(BaseNetworkTask):
    """Task to plumb a VIP."""

    def execute(self, loadbalancer):
        """Plumb a vip to an amphora."""

        LOG.debug("Getting subnet for LB: %s", loadbalancer.id)

        return self.network_driver.get_subnet(loadbalancer.vip.subnet_id)


class PlugVIPAmpphora(BaseNetworkTask):
    """Task to plumb a VIP."""

    def execute(self, loadbalancer, amphora, subnet):
        """Plumb a vip to an amphora."""

        LOG.debug("Plumbing VIP for amphora id: %s", amphora.id)

        amp_data = self.network_driver.plug_aap_port(
            loadbalancer, loadbalancer.vip, amphora, subnet)
        return amp_data

    def revert(self, result, loadbalancer, amphora, subnet, *args, **kwargs):
        """Handle a failure to plumb a vip."""

        if isinstance(result, failure.Failure):
            return
        LOG.warning("Unable to plug VIP for amphora id %s "
                    "load balancer id %s",
                    amphora.id, loadbalancer.id)

        try:
            amphora.vrrp_port_id = result.vrrp_port_id
            amphora.ha_port_id = result.ha_port_id

            self.network_driver.unplug_aap_port(loadbalancer.vip,
                                                amphora, subnet)
        except Exception as e:
            LOG.error('Failed to unplug AAP port. Resources may still be in '
                      'use for VIP: %s due to error: %s', loadbalancer.vip, e)


class UnplugVIP(BaseNetworkTask):
    """Task to unplug the vip."""

    def execute(self, loadbalancer):
        """Unplug the vip."""

        LOG.debug("Unplug vip on amphora")
        try:
            self.network_driver.unplug_vip(loadbalancer, loadbalancer.vip)
        except Exception:
            LOG.exception("Unable to unplug vip from load balancer %s",
                          loadbalancer.id)


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
            LOG.exception("Unable to allocate VIP")
            return
        vip = result
        LOG.warning("Deallocating vip %s", vip.ip_address)
        try:
            self.network_driver.deallocate_vip(vip)
        except Exception as e:
            LOG.error("Failed to deallocate VIP.  Resources may still "
                      "be in use from vip: %(vip)s due to error: %(except)s",
                      {'vip': vip.ip_address, 'except': e})


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


class UpdateVIP(BaseNetworkTask):
    """Task to update a VIP."""

    def execute(self, loadbalancer):
        LOG.debug("Updating VIP of load_balancer %s.", loadbalancer.id)

        self.network_driver.update_vip(loadbalancer)


class UpdateVIPForDelete(BaseNetworkTask):
    """Task to update a VIP for listener delete flows."""

    def execute(self, loadbalancer):
        LOG.debug("Updating VIP for listener delete on load_balancer %s.",
                  loadbalancer.id)

        self.network_driver.update_vip(loadbalancer, for_delete=True)


class GetAmphoraNetworkConfigs(BaseNetworkTask):
    """Task to retrieve amphora network details."""

    def execute(self, loadbalancer, amphora=None):
        LOG.debug("Retrieving vip network details.")
        return self.network_driver.get_network_configs(loadbalancer,
                                                       amphora=amphora)


class GetAmphoraeNetworkConfigs(BaseNetworkTask):
    """Task to retrieve amphorae network details."""

    def execute(self, loadbalancer):
        LOG.debug("Retrieving vip network details.")
        return self.network_driver.get_network_configs(loadbalancer)


class FailoverPreparationForAmphora(BaseNetworkTask):
    """Task to prepare an amphora for failover."""

    def execute(self, amphora):
        LOG.debug("Prepare amphora %s for failover.", amphora.id)

        self.network_driver.failover_preparation(amphora)


class RetrievePortIDsOnAmphoraExceptLBNetwork(BaseNetworkTask):
    """Task retrieving all the port ids on an amphora, except lb network."""

    def execute(self, amphora):
        LOG.debug("Retrieve all but the lb network port id on amphora %s.",
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


class PlugPorts(BaseNetworkTask):
    """Task to plug neutron ports into a compute instance."""

    def execute(self, amphora, ports):
        for port in ports:
            LOG.debug('Plugging port ID: %(port_id)s into compute instance: '
                      '%(compute_id)s.',
                      {'port_id': port.id, 'compute_id': amphora.compute_id})
            self.network_driver.plug_port(amphora, port)


class PlugVIPPort(BaseNetworkTask):
    """Task to plug a VIP into a compute instance."""

    def execute(self, amphora, amphorae_network_config):
        vrrp_port = amphorae_network_config.get(amphora.id).vrrp_port
        LOG.debug('Plugging VIP VRRP port ID: %(port_id)s into compute '
                  'instance: %(compute_id)s.',
                  {'port_id': vrrp_port.id, 'compute_id': amphora.compute_id})
        self.network_driver.plug_port(amphora, vrrp_port)

    def revert(self, result, amphora, amphorae_network_config,
               *args, **kwargs):
        vrrp_port = None
        try:
            vrrp_port = amphorae_network_config.get(amphora.id).vrrp_port
            self.network_driver.unplug_port(amphora, vrrp_port)
        except Exception:
            LOG.warning('Failed to unplug vrrp port: %(port)s from amphora: '
                        '%(amp)s', {'port': vrrp_port.id, 'amp': amphora.id})


class WaitForPortDetach(BaseNetworkTask):
    """Task to wait for the neutron ports to detach from an amphora."""

    def execute(self, amphora):
        LOG.debug('Waiting for ports to detach from amphora: %(amp_id)s.',
                  {'amp_id': amphora.id})
        self.network_driver.wait_for_port_detach(amphora)


class ApplyQos(BaseNetworkTask):
    """Apply Quality of Services to the VIP"""

    def _apply_qos_on_vrrp_ports(self, loadbalancer, amps_data, qos_policy_id,
                                 is_revert=False, request_qos_id=None):
        """Call network driver to apply QoS Policy on the vrrp ports."""
        if not amps_data:
            amps_data = loadbalancer.amphorae

        apply_qos = ApplyQosAmphora()
        for amp_data in amps_data:
            apply_qos._apply_qos_on_vrrp_port(loadbalancer, amp_data,
                                              qos_policy_id)

    def execute(self, loadbalancer, amps_data=None, update_dict=None):
        """Apply qos policy on the vrrp ports which are related with vip."""
        qos_policy_id = loadbalancer.vip.qos_policy_id
        if not qos_policy_id and (
            update_dict and (
                'vip' not in update_dict or
                'qos_policy_id' not in update_dict['vip'])):
            return
        self._apply_qos_on_vrrp_ports(loadbalancer, amps_data, qos_policy_id)

    def revert(self, result, loadbalancer, amps_data=None, update_dict=None,
               *args, **kwargs):
        """Handle a failure to apply QoS to VIP"""
        request_qos_id = loadbalancer.vip.qos_policy_id
        orig_lb = self.task_utils.get_current_loadbalancer_from_db(
            loadbalancer.id)
        orig_qos_id = orig_lb.vip.qos_policy_id
        if request_qos_id != orig_qos_id:
            self._apply_qos_on_vrrp_ports(loadbalancer, amps_data, orig_qos_id,
                                          is_revert=True,
                                          request_qos_id=request_qos_id)


class ApplyQosAmphora(BaseNetworkTask):
    """Apply Quality of Services to the VIP"""

    def _apply_qos_on_vrrp_port(self, loadbalancer, amp_data, qos_policy_id,
                                is_revert=False, request_qos_id=None):
        """Call network driver to apply QoS Policy on the vrrp ports."""
        try:
            self.network_driver.apply_qos_on_port(qos_policy_id,
                                                  amp_data.vrrp_port_id)
        except Exception:
            if not is_revert:
                raise
            LOG.warning('Failed to undo qos policy %(qos_id)s '
                        'on vrrp port: %(port)s from '
                        'amphorae: %(amp)s',
                        {'qos_id': request_qos_id,
                            'port': amp_data.vrrp_port_id,
                            'amp': [amp.id for amp in amp_data]})

    def execute(self, loadbalancer, amp_data=None, update_dict=None):
        """Apply qos policy on the vrrp ports which are related with vip."""
        qos_policy_id = loadbalancer.vip.qos_policy_id
        if not qos_policy_id and (
            update_dict and (
                'vip' not in update_dict or
                'qos_policy_id' not in update_dict['vip'])):
            return
        self._apply_qos_on_vrrp_port(loadbalancer, amp_data, qos_policy_id)

    def revert(self, result, loadbalancer, amp_data=None, update_dict=None,
               *args, **kwargs):
        """Handle a failure to apply QoS to VIP"""
        try:
            request_qos_id = loadbalancer.vip.qos_policy_id
            orig_lb = self.task_utils.get_current_loadbalancer_from_db(
                loadbalancer.id)
            orig_qos_id = orig_lb.vip.qos_policy_id
            if request_qos_id != orig_qos_id:
                self._apply_qos_on_vrrp_port(loadbalancer, amp_data,
                                             orig_qos_id, is_revert=True,
                                             request_qos_id=request_qos_id)
        except Exception as e:
            LOG.error('Failed to remove QoS policy: %s from port: %s due '
                      'to error: %s', orig_qos_id, amp_data.vrrp_port_id, e)
