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
import time

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from taskflow import task
from taskflow.types import failure
import tenacity

from octavia.common import constants
from octavia.common import data_models
from octavia.common import utils
from octavia.controller.worker import task_utils
from octavia.db import api as db_apis
from octavia.db import repositories as repo
from octavia.network import base
from octavia.network import data_models as n_data_models

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class BaseNetworkTask(task.Task):
    """Base task to load drivers common to the tasks."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._network_driver = None
        self.task_utils = task_utils.TaskUtils()
        self.loadbalancer_repo = repo.LoadBalancerRepository()
        self.amphora_repo = repo.AmphoraRepository()

    @property
    def network_driver(self):
        if self._network_driver is None:
            self._network_driver = utils.get_network_driver()
        return self._network_driver


class CalculateAmphoraDelta(BaseNetworkTask):

    default_provides = constants.DELTA

    def execute(self, loadbalancer, amphora, availability_zone,
                vrrp_port=None):
        LOG.debug("Calculating network delta for amphora id: %s",
                  amphora.get(constants.ID))

        if vrrp_port is None:
            vrrp_port = self.network_driver.get_port(
                amphora[constants.VRRP_PORT_ID])
            vrrp_port_network_id = vrrp_port.network_id
        else:
            vrrp_port_network_id = vrrp_port[constants.NETWORK_ID]

        # Figure out what networks we want
        # seed with lb network(s)
        if availability_zone:
            management_nets = (
                [availability_zone.get(constants.MANAGEMENT_NETWORK)] or
                CONF.controller_worker.amp_boot_network_list)
        else:
            management_nets = CONF.controller_worker.amp_boot_network_list
        desired_network_ids = {vrrp_port_network_id}.union(management_nets)
        db_lb = self.loadbalancer_repo.get(
            db_apis.get_session(), id=loadbalancer[constants.LOADBALANCER_ID])
        for pool in db_lb.pools:
            member_networks = [
                self.network_driver.get_subnet(member.subnet_id).network_id
                for member in pool.members
                if member.subnet_id
            ]
            desired_network_ids.update(member_networks)

        nics = self.network_driver.get_plugged_networks(
            amphora[constants.COMPUTE_ID])
        # assume we don't have two nics in the same network
        actual_network_nics = dict((nic.network_id, nic) for nic in nics)

        del_ids = set(actual_network_nics) - desired_network_ids
        delete_nics = list(
            n_data_models.Interface(network_id=net_id) for net_id in del_ids)

        add_ids = desired_network_ids - set(actual_network_nics)
        add_nics = list(n_data_models.Interface(
            network_id=net_id) for net_id in add_ids)
        delta = n_data_models.Delta(
            amphora_id=amphora[constants.ID],
            compute_id=amphora[constants.COMPUTE_ID],
            add_nics=add_nics, delete_nics=delete_nics)
        return delta.to_dict(recurse=True)


class CalculateDelta(BaseNetworkTask):
    """Task to calculate the delta between

    the nics on the amphora and the ones
    we need. Returns a list for
    plumbing them.
    """

    default_provides = constants.DELTAS

    def execute(self, loadbalancer, availability_zone):
        """Compute which NICs need to be plugged

        for the amphora to become operational.

        :param loadbalancer: the loadbalancer to calculate deltas for all
                             amphorae
        :param availability_zone: availability zone metadata dict

        :returns: dict of octavia.network.data_models.Delta keyed off amphora
                  id
        """

        calculate_amp = CalculateAmphoraDelta()
        deltas = {}
        db_lb = self.loadbalancer_repo.get(
            db_apis.get_session(), id=loadbalancer[constants.LOADBALANCER_ID])
        for amphora in filter(
            lambda amp: amp.status == constants.AMPHORA_ALLOCATED,
                db_lb.amphorae):

            delta = calculate_amp.execute(loadbalancer, amphora.to_dict(),
                                          availability_zone)
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

        LOG.debug("Getting plumbed networks for amphora id: %s",
                  amphora[constants.ID])

        return self.network_driver.get_plugged_networks(
            amphora[constants.COMPUTE_ID])


class PlugNetworks(BaseNetworkTask):
    """Task to plug the networks.

    This uses the delta to add all missing networks/nics
    """

    def execute(self, amphora, delta):
        """Update the amphora networks for the delta."""

        LOG.debug("Plug or unplug networks for amphora id: %s",
                  amphora[constants.ID])

        if not delta:
            LOG.debug("No network deltas for amphora id: %s",
                      amphora[constants.ID])
            return

        # add nics
        for nic in delta[constants.ADD_NICS]:
            self.network_driver.plug_network(amphora[constants.COMPUTE_ID],
                                             nic[constants.NETWORK_ID])

    def revert(self, amphora, delta, *args, **kwargs):
        """Handle a failed network plug by removing all nics added."""

        LOG.warning("Unable to plug networks for amp id %s",
                    amphora[constants.ID])
        if not delta:
            return

        for nic in delta[constants.ADD_NICS]:
            try:
                self.network_driver.unplug_network(
                    amphora[constants.COMPUTE_ID],
                    nic[constants.NETWORK_ID])
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
            LOG.debug("No network deltas for amphora id: %s",
                      amphora[constants.ID])
            return

        for nic in delta[constants.DELETE_NICS]:
            try:
                self.network_driver.unplug_network(
                    amphora[constants.COMPUTE_ID], nic[constants.NETWORK_ID])
            except base.NetworkNotFound:
                LOG.debug("Network %d not found", nic[constants.NETWORK_ID])
            except Exception:
                LOG.exception("Unable to unplug network")
                # TODO(xgerman) follow up if that makes sense


class GetMemberPorts(BaseNetworkTask):

    def execute(self, loadbalancer, amphora):
        vip_port = self.network_driver.get_port(loadbalancer['vip_port_id'])
        member_ports = []
        interfaces = self.network_driver.get_plugged_networks(
            amphora[constants.COMPUTE_ID])
        for interface in interfaces:
            port = self.network_driver.get_port(interface.port_id)
            if vip_port.network_id == port.network_id:
                continue
            port.network = self.network_driver.get_network(port.network_id)
            for fixed_ip in port.fixed_ips:
                if amphora['lb_network_ip'] == fixed_ip.ip_address:
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
        added_ports[amphora[constants.ID]] = []
        for nic in delta[constants.ADD_NICS]:
            interface = self.network_driver.plug_network(
                delta[constants.COMPUTE_ID], nic[constants.NETWORK_ID])
            port = self.network_driver.get_port(interface.port_id)
            port.network = self.network_driver.get_network(port.network_id)
            for fixed_ip in port.fixed_ips:
                fixed_ip.subnet = self.network_driver.get_subnet(
                    fixed_ip.subnet_id)
            added_ports[amphora[constants.ID]].append(port.to_dict(
                recurse=True))
        for nic in delta[constants.DELETE_NICS]:
            try:
                self.network_driver.unplug_network(
                    delta[constants.COMPUTE_ID], nic[constants.NETWORK_ID])
            except base.NetworkNotFound:
                LOG.debug("Network %d not found ", nic[constants.NETWORK_ID])
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
                    delta['amphora_id'])

        for nic in delta[constants.ADD_NICS]:
            try:
                self.network_driver.unplug_network(delta[constants.COMPUTE_ID],
                                                   nic[constants.NETWORK_ID])
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
        for amp_id, delta in deltas.items():
            added_ports[amp_id] = []
            for nic in delta[constants.ADD_NICS]:
                interface = self.network_driver.plug_network(
                    delta[constants.COMPUTE_ID], nic[constants.NETWORK_ID])
                port = self.network_driver.get_port(interface.port_id)
                port.network = self.network_driver.get_network(port.network_id)
                for fixed_ip in port.fixed_ips:
                    fixed_ip.subnet = self.network_driver.get_subnet(
                        fixed_ip.subnet_id)
                added_ports[amp_id].append(port.to_dict(recurse=True))
            for nic in delta[constants.DELETE_NICS]:
                try:
                    self.network_driver.unplug_network(
                        delta[constants.COMPUTE_ID],
                        nic[constants.NETWORK_ID])
                except base.NetworkNotFound:
                    LOG.debug("Network %d not found ",
                              nic[constants.NETWORK_ID])
                except Exception:
                    LOG.exception("Unable to unplug network")
        return added_ports

    def revert(self, result, deltas, *args, **kwargs):
        """Handle a network plug or unplug failures."""

        if isinstance(result, failure.Failure):
            return
        for amp_id, delta in deltas.items():
            LOG.warning("Unable to plug networks for amp id %s",
                        delta[constants.AMPHORA_ID])
            if not delta:
                return

            for nic in delta[constants.ADD_NICS]:
                try:
                    self.network_driver.unplug_network(
                        delta[constants.COMPUTE_ID],
                        nic[constants.NETWORK_ID])
                except base.NetworkNotFound:
                    pass


class PlugVIP(BaseNetworkTask):
    """Task to plumb a VIP."""

    def execute(self, loadbalancer):
        """Plumb a vip to an amphora."""

        LOG.debug("Plumbing VIP for loadbalancer id: %s",
                  loadbalancer[constants.LOADBALANCER_ID])
        db_lb = self.loadbalancer_repo.get(
            db_apis.get_session(),
            id=loadbalancer[constants.LOADBALANCER_ID])
        amps_data = self.network_driver.plug_vip(db_lb,
                                                 db_lb.vip)
        return [amp.to_dict() for amp in amps_data]

    def revert(self, result, loadbalancer, *args, **kwargs):
        """Handle a failure to plumb a vip."""

        if isinstance(result, failure.Failure):
            return
        LOG.warning("Unable to plug VIP for loadbalancer id %s",
                    loadbalancer[constants.LOADBALANCER_ID])

        db_lb = self.loadbalancer_repo.get(
            db_apis.get_session(),
            id=loadbalancer[constants.LOADBALANCER_ID])
        try:
            # Make sure we have the current port IDs for cleanup
            for amp_data in result:
                for amphora in filter(
                        # pylint: disable=cell-var-from-loop
                        lambda amp: amp.id == amp_data['id'],
                        db_lb.amphorae):
                    amphora.vrrp_port_id = amp_data['vrrp_port_id']
                    amphora.ha_port_id = amp_data['ha_port_id']

            self.network_driver.unplug_vip(db_lb, db_lb.vip)
        except Exception as e:
            LOG.error("Failed to unplug VIP.  Resources may still "
                      "be in use from vip: %(vip)s due to error: %(except)s",
                      {'vip': loadbalancer['vip_address'], 'except': str(e)})


class UpdateVIPSecurityGroup(BaseNetworkTask):
    """Task to setup SG for LB."""

    def execute(self, loadbalancer_id):
        """Task to setup SG for LB."""

        LOG.debug("Setup SG for loadbalancer id: %s", loadbalancer_id)
        db_lb = self.loadbalancer_repo.get(
            db_apis.get_session(), id=loadbalancer_id)
        return self.network_driver.update_vip_sg(db_lb, db_lb.vip)


class GetSubnetFromVIP(BaseNetworkTask):
    """Task to plumb a VIP."""

    def execute(self, loadbalancer):
        """Plumb a vip to an amphora."""

        LOG.debug("Getting subnet for LB: %s",
                  loadbalancer[constants.LOADBALANCER_ID])

        return self.network_driver.get_subnet(
            loadbalancer['vip_subnet_id']).to_dict()


class PlugVIPAmphora(BaseNetworkTask):
    """Task to plumb a VIP."""

    def execute(self, loadbalancer, amphora, subnet):
        """Plumb a vip to an amphora."""

        LOG.debug("Plumbing VIP for amphora id: %s",
                  amphora.get(constants.ID))
        db_amp = self.amphora_repo.get(db_apis.get_session(),
                                       id=amphora.get(constants.ID))
        db_subnet = self.network_driver.get_subnet(subnet[constants.ID])
        db_lb = self.loadbalancer_repo.get(
            db_apis.get_session(), id=loadbalancer[constants.LOADBALANCER_ID])
        amp_data = self.network_driver.plug_aap_port(
            db_lb, db_lb.vip, db_amp, db_subnet)
        return amp_data.to_dict()

    def revert(self, result, loadbalancer, amphora, subnet, *args, **kwargs):
        """Handle a failure to plumb a vip."""
        if isinstance(result, failure.Failure):
            return
        LOG.warning("Unable to plug VIP for amphora id %s "
                    "load balancer id %s",
                    amphora.get(constants.ID),
                    loadbalancer[constants.LOADBALANCER_ID])

        try:
            db_amp = self.amphora_repo.get(db_apis.get_session(),
                                           id=amphora.get(constants.ID))
            db_amp.vrrp_port_id = result[constants.VRRP_PORT_ID]
            db_amp.ha_port_id = result[constants.HA_PORT_ID]
            db_lb = self.loadbalancer_repo.get(
                db_apis.get_session(),
                id=loadbalancer[constants.LOADBALANCER_ID])

            self.network_driver.unplug_aap_port(db_lb.vip,
                                                db_amp, subnet)
        except Exception as e:
            LOG.error('Failed to unplug AAP port. Resources may still be in '
                      'use for VIP: %s due to error: %s', db_lb.vip, str(e))


class UnplugVIP(BaseNetworkTask):
    """Task to unplug the vip."""

    def execute(self, loadbalancer):
        """Unplug the vip."""

        LOG.debug("Unplug vip on amphora")
        try:
            db_lb = self.loadbalancer_repo.get(
                db_apis.get_session(),
                id=loadbalancer[constants.LOADBALANCER_ID])
            self.network_driver.unplug_vip(db_lb, db_lb.vip)
        except Exception:
            LOG.exception("Unable to unplug vip from load balancer %s",
                          loadbalancer[constants.LOADBALANCER_ID])


class AllocateVIP(BaseNetworkTask):
    """Task to allocate a VIP."""

    def execute(self, loadbalancer):
        """Allocate a vip to the loadbalancer."""

        LOG.debug("Allocate_vip port_id %s, subnet_id %s,"
                  "ip_address %s",
                  loadbalancer[constants.VIP_PORT_ID],
                  loadbalancer[constants.VIP_SUBNET_ID],
                  loadbalancer[constants.VIP_ADDRESS])
        db_lb = self.loadbalancer_repo.get(
            db_apis.get_session(), id=loadbalancer[constants.LOADBALANCER_ID])
        vip = self.network_driver.allocate_vip(db_lb)
        return vip.to_dict()

    def revert(self, result, loadbalancer, *args, **kwargs):
        """Handle a failure to allocate vip."""

        if isinstance(result, failure.Failure):
            LOG.exception("Unable to allocate VIP")
            return
        vip = data_models.Vip(**result)
        LOG.warning("Deallocating vip %s", vip.ip_address)
        try:
            self.network_driver.deallocate_vip(vip)
        except Exception as e:
            LOG.error("Failed to deallocate VIP.  Resources may still "
                      "be in use from vip: %(vip)s due to error: %(except)s",
                      {'vip': vip.ip_address, 'except': str(e)})


class AllocateVIPforFailover(AllocateVIP):
    """Task to allocate/validate the VIP for a failover flow."""

    def revert(self, result, loadbalancer, *args, **kwargs):
        """Handle a failure to allocate vip."""

        if isinstance(result, failure.Failure):
            LOG.exception("Unable to allocate VIP")
            return
        vip = data_models.Vip(**result)
        LOG.info("Failover revert is not deallocating vip %s because this is "
                 "a failover.", vip.ip_address)


class DeallocateVIP(BaseNetworkTask):
    """Task to deallocate a VIP."""

    def execute(self, loadbalancer):
        """Deallocate a VIP."""

        LOG.debug("Deallocating a VIP %s", loadbalancer[constants.VIP_ADDRESS])

        # NOTE(blogan): this is kind of ugly but sufficient for now.  Drivers
        # will need access to the load balancer that the vip is/was attached
        # to.  However the data model serialization for the vip does not give a
        # backref to the loadbalancer if accessed through the loadbalancer.
        db_lb = self.loadbalancer_repo.get(
            db_apis.get_session(), id=loadbalancer[constants.LOADBALANCER_ID])
        vip = db_lb.vip
        vip.load_balancer = db_lb
        self.network_driver.deallocate_vip(vip)


class UpdateVIP(BaseNetworkTask):
    """Task to update a VIP."""

    def execute(self, listeners):
        loadbalancer = self.loadbalancer_repo.get(
            db_apis.get_session(), id=listeners[0][constants.LOADBALANCER_ID])

        LOG.debug("Updating VIP of load_balancer %s.", loadbalancer.id)

        self.network_driver.update_vip(loadbalancer)


class UpdateVIPForDelete(BaseNetworkTask):
    """Task to update a VIP for listener delete flows."""

    def execute(self, loadbalancer_id):
        loadbalancer = self.loadbalancer_repo.get(
            db_apis.get_session(), id=loadbalancer_id)
        LOG.debug("Updating VIP for listener delete on load_balancer %s.",
                  loadbalancer.id)
        self.network_driver.update_vip(loadbalancer, for_delete=True)


class GetAmphoraNetworkConfigs(BaseNetworkTask):
    """Task to retrieve amphora network details."""

    def execute(self, loadbalancer, amphora=None):
        LOG.debug("Retrieving vip network details.")
        db_amp = self.amphora_repo.get(db_apis.get_session(),
                                       id=amphora.get(constants.ID))
        db_lb = self.loadbalancer_repo.get(
            db_apis.get_session(), id=loadbalancer[constants.LOADBALANCER_ID])
        db_configs = self.network_driver.get_network_configs(
            db_lb, amphora=db_amp)
        provider_dict = {}
        for amp_id, amp_conf in db_configs.items():
            provider_dict[amp_id] = amp_conf.to_dict(recurse=True)
        return provider_dict


class GetAmphoraNetworkConfigsByID(BaseNetworkTask):
    """Task to retrieve amphora network details."""

    def execute(self, loadbalancer_id, amphora_id=None):
        LOG.debug("Retrieving vip network details.")
        loadbalancer = self.loadbalancer_repo.get(db_apis.get_session(),
                                                  id=loadbalancer_id)
        amphora = self.amphora_repo.get(db_apis.get_session(), id=amphora_id)
        db_configs = self.network_driver.get_network_configs(loadbalancer,
                                                             amphora=amphora)
        provider_dict = {}
        for amp_id, amp_conf in db_configs.items():
            provider_dict[amp_id] = amp_conf.to_dict(recurse=True)
        return provider_dict


class GetAmphoraeNetworkConfigs(BaseNetworkTask):
    """Task to retrieve amphorae network details."""

    def execute(self, loadbalancer_id):
        LOG.debug("Retrieving vip network details.")
        db_lb = self.loadbalancer_repo.get(
            db_apis.get_session(), id=loadbalancer_id)
        db_configs = self.network_driver.get_network_configs(db_lb)
        provider_dict = {}
        for amp_id, amp_conf in db_configs.items():
            provider_dict[amp_id] = amp_conf.to_dict(recurse=True)
        return provider_dict


class FailoverPreparationForAmphora(BaseNetworkTask):
    """Task to prepare an amphora for failover."""

    def execute(self, amphora):
        db_amp = self.amphora_repo.get(db_apis.get_session(),
                                       id=amphora[constants.ID])
        LOG.debug("Prepare amphora %s for failover.", amphora[constants.ID])

        self.network_driver.failover_preparation(db_amp)


class RetrievePortIDsOnAmphoraExceptLBNetwork(BaseNetworkTask):
    """Task retrieving all the port ids on an amphora, except lb network."""

    def execute(self, amphora):
        LOG.debug("Retrieve all but the lb network port id on amphora %s.",
                  amphora[constants.ID])

        interfaces = self.network_driver.get_plugged_networks(
            compute_id=amphora[constants.COMPUTE_ID])

        ports = []
        for interface_ in interfaces:
            if interface_.port_id not in ports:
                port = self.network_driver.get_port(port_id=interface_.port_id)
                ips = port.fixed_ips
                lb_network = False
                for ip in ips:
                    if ip.ip_address == amphora[constants.LB_NETWORK_IP]:
                        lb_network = True
                if not lb_network:
                    ports.append(port)

        return ports


class PlugPorts(BaseNetworkTask):
    """Task to plug neutron ports into a compute instance."""

    def execute(self, amphora, ports):
        db_amp = self.amphora_repo.get(db_apis.get_session(),
                                       id=amphora[constants.ID])
        for port in ports:
            LOG.debug('Plugging port ID: %(port_id)s into compute instance: '
                      '%(compute_id)s.',
                      {constants.PORT_ID: port.id,
                       constants.COMPUTE_ID: amphora[constants.COMPUTE_ID]})
            self.network_driver.plug_port(db_amp, port)


class ApplyQos(BaseNetworkTask):
    """Apply Quality of Services to the VIP"""

    def _apply_qos_on_vrrp_ports(self, loadbalancer, amps_data, qos_policy_id,
                                 is_revert=False, request_qos_id=None):
        """Call network driver to apply QoS Policy on the vrrp ports."""

        if not amps_data:
            db_lb = self.loadbalancer_repo.get(
                db_apis.get_session(),
                id=loadbalancer[constants.LOADBALANCER_ID])
            amps_data = db_lb.amphorae

        apply_qos = ApplyQosAmphora()
        for amp_data in amps_data:
            apply_qos._apply_qos_on_vrrp_port(loadbalancer, amp_data.to_dict(),
                                              qos_policy_id)

    def execute(self, loadbalancer, amps_data=None, update_dict=None):
        """Apply qos policy on the vrrp ports which are related with vip."""
        db_lb = self.loadbalancer_repo.get(
            db_apis.get_session(),
            id=loadbalancer[constants.LOADBALANCER_ID])

        qos_policy_id = db_lb.vip.qos_policy_id
        if not qos_policy_id and (
            not update_dict or (
                'vip' not in update_dict or
                'qos_policy_id' not in update_dict[constants.VIP])):
            return
        if update_dict and update_dict.get(constants.VIP):
            vip_dict = update_dict[constants.VIP]
            if vip_dict.get(constants.QOS_POLICY_ID):
                qos_policy_id = vip_dict[constants.QOS_POLICY_ID]

        self._apply_qos_on_vrrp_ports(loadbalancer, amps_data, qos_policy_id)

    def revert(self, result, loadbalancer, amps_data=None, update_dict=None,
               *args, **kwargs):
        """Handle a failure to apply QoS to VIP"""

        request_qos_id = loadbalancer['vip_qos_policy_id']
        orig_lb = self.task_utils.get_current_loadbalancer_from_db(
            loadbalancer[constants.LOADBALANCER_ID])
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
            self.network_driver.apply_qos_on_port(
                qos_policy_id,
                amp_data[constants.VRRP_PORT_ID])
        except Exception:
            if not is_revert:
                raise
            LOG.warning('Failed to undo qos policy %(qos_id)s '
                        'on vrrp port: %(port)s from '
                        'amphorae: %(amp)s',
                        {'qos_id': request_qos_id,
                         'port': amp_data[constants.VRRP_PORT_ID],
                         'amp': [amp.get(constants.ID) for amp in amp_data]})

    def execute(self, loadbalancer, amp_data=None, update_dict=None):
        """Apply qos policy on the vrrp ports which are related with vip."""
        qos_policy_id = loadbalancer['vip_qos_policy_id']
        if not qos_policy_id and (
            update_dict and (
                'vip' not in update_dict or
                'qos_policy_id' not in update_dict[constants.VIP])):
            return
        self._apply_qos_on_vrrp_port(loadbalancer, amp_data, qos_policy_id)

    def revert(self, result, loadbalancer, amp_data=None, update_dict=None,
               *args, **kwargs):
        """Handle a failure to apply QoS to VIP"""
        try:
            request_qos_id = loadbalancer['vip_qos_policy_id']
            orig_lb = self.task_utils.get_current_loadbalancer_from_db(
                loadbalancer[constants.LOADBALANCER_ID])
            orig_qos_id = orig_lb.vip.qos_policy_id
            if request_qos_id != orig_qos_id:
                self._apply_qos_on_vrrp_port(loadbalancer, amp_data,
                                             orig_qos_id, is_revert=True,
                                             request_qos_id=request_qos_id)
        except Exception as e:
            LOG.error('Failed to remove QoS policy: %s from port: %s due '
                      'to error: %s', orig_qos_id,
                      amp_data[constants.VRRP_PORT_ID], str(e))


class DeletePort(BaseNetworkTask):
    """Task to delete a network port."""

    @tenacity.retry(retry=tenacity.retry_if_exception_type(),
                    stop=tenacity.stop_after_attempt(
                        CONF.networking.max_retries),
                    wait=tenacity.wait_exponential(
                        multiplier=CONF.networking.retry_backoff,
                        min=CONF.networking.retry_interval,
                        max=CONF.networking.retry_max), reraise=True)
    def execute(self, port_id, passive_failure=False):
        """Delete the network port."""
        if port_id is None:
            return
        if self.execute.retry.statistics.get(constants.ATTEMPT_NUMBER, 1) == 1:
            LOG.debug("Deleting network port %s", port_id)
        else:
            LOG.warning('Retrying network port %s delete attempt %s of %s.',
                        port_id,
                        self.execute.retry.statistics[
                            constants.ATTEMPT_NUMBER],
                        self.execute.retry.stop.max_attempt_number)
        # Let the Taskflow engine know we are working and alive
        # Don't use get with a default for 'attempt_number', we need to fail
        # if that number is missing.
        self.update_progress(
            self.execute.retry.statistics[constants.ATTEMPT_NUMBER] /
            self.execute.retry.stop.max_attempt_number)
        try:
            self.network_driver.delete_port(port_id)
        except Exception:
            if (self.execute.retry.statistics[constants.ATTEMPT_NUMBER] !=
                    self.execute.retry.stop.max_attempt_number):
                LOG.warning('Network port delete for port id: %s failed. '
                            'Retrying.', port_id)
                raise
            if passive_failure:
                LOG.exception('Network port delete for port ID: %s failed. '
                              'This resource will be abandoned and should '
                              'manually be cleaned up once the '
                              'network service is functional.', port_id)
                # Let's at least attempt to disable it so if the instance
                # comes back from the dead it doesn't conflict with anything.
                try:
                    self.network_driver.admin_down_port(port_id)
                    LOG.info('Successfully disabled (admin down) network port '
                             '%s that failed to delete.', port_id)
                except Exception:
                    LOG.warning('Attempt to disable (admin down) network port '
                                '%s failed. The network service has failed. '
                                'Continuing.', port_id)
            else:
                LOG.exception('Network port delete for port ID: %s failed. '
                              'The network service has failed. '
                              'Aborting and reverting.', port_id)
                raise


class CreateVIPBasePort(BaseNetworkTask):
    """Task to create the VIP base port for an amphora."""

    @tenacity.retry(retry=tenacity.retry_if_exception_type(),
                    stop=tenacity.stop_after_attempt(
                        CONF.networking.max_retries),
                    wait=tenacity.wait_exponential(
                        multiplier=CONF.networking.retry_backoff,
                        min=CONF.networking.retry_interval,
                        max=CONF.networking.retry_max), reraise=True)
    def execute(self, vip, vip_sg_id, amphora_id):
        port_name = constants.AMP_BASE_PORT_PREFIX + amphora_id
        fixed_ips = [{constants.SUBNET_ID: vip[constants.SUBNET_ID]}]
        sg_id = []
        if vip_sg_id:
            sg_id = [vip_sg_id]
        port = self.network_driver.create_port(
            vip[constants.NETWORK_ID], name=port_name, fixed_ips=fixed_ips,
            secondary_ips=[vip[constants.IP_ADDRESS]],
            security_group_ids=sg_id,
            qos_policy_id=vip[constants.QOS_POLICY_ID])
        LOG.info('Created port %s with ID %s for amphora %s',
                 port_name, port.id, amphora_id)
        return port.to_dict(recurse=True)

    def revert(self, result, vip, vip_sg_id, amphora_id, *args, **kwargs):
        if isinstance(result, failure.Failure):
            return
        try:
            port_name = constants.AMP_BASE_PORT_PREFIX + amphora_id
            for port in result:
                self.network_driver.delete_port(port.id)
                LOG.info('Deleted port %s with ID %s for amphora %s due to a '
                         'revert.', port_name, port.id, amphora_id)
        except Exception as e:
            LOG.error('Failed to delete port %s. Resources may still be in '
                      'use for a port intended for amphora %s due to error '
                      '%s. Search for a port named %s',
                      result, amphora_id, str(e), port_name)


class AdminDownPort(BaseNetworkTask):

    def execute(self, port_id):
        try:
            self.network_driver.set_port_admin_state_up(port_id, False)
        except base.PortNotFound:
            return
        for i in range(CONF.networking.max_retries):
            port = self.network_driver.get_port(port_id)
            if port.status == constants.DOWN:
                LOG.debug('Disabled port: %s', port_id)
                return
            LOG.debug('Port %s is %s instead of DOWN, waiting.',
                      port_id, port.status)
            time.sleep(CONF.networking.retry_interval)
        LOG.error('Port %s failed to go DOWN. Port status is still %s. '
                  'Ignoring and continuing.', port_id, port.status)

    def revert(self, result, port_id, *args, **kwargs):
        if isinstance(result, failure.Failure):
            return
        try:
            self.network_driver.set_port_admin_state_up(port_id, True)
        except Exception as e:
            LOG.error('Failed to bring port %s admin up on revert due to: %s.',
                      port_id, str(e))


class GetVIPSecurityGroupID(BaseNetworkTask):

    def execute(self, loadbalancer_id):
        sg_name = utils.get_vip_security_group_name(loadbalancer_id)
        try:
            security_group = self.network_driver.get_security_group(sg_name)
            if security_group:
                return security_group.id
        except base.SecurityGroupNotFound:
            with excutils.save_and_reraise_exception() as ctxt:
                if self.network_driver.sec_grp_enabled:
                    LOG.error('VIP security group %s was not found.', sg_name)
                else:
                    ctxt.reraise = False
        return None
