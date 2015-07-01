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
from stevedore import driver as stevedore_driver
from taskflow import task
from taskflow.types import failure

from octavia.common import constants
from octavia.i18n import _LW, _LE
from octavia.network import base
from octavia.network import data_models

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
            invoke_on_load=True
        ).driver


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
        :param amphora - the amphora configuration we
            want to achieve
        :param nics - the nics on the real amphora
        :returns the delta
        """

        deltas = []
        for amphora in loadbalancer.amphorae:

            LOG.debug("Calculating network delta for amphora id: %s"
                      % amphora.id)

            # Figure out what networks we want
            # seed with lb network(s)
            desired_network_ids = {CONF.controller_worker.amp_network,
                                   loadbalancer.vip.network_id}

            if not loadbalancer.listeners:
                return []

            for listener in loadbalancer.listeners:
                if (not listener.default_pool) or (
                        not listener.default_pool.members):
                    continue
                desired_network_ids.update(
                    list(
                        self.network_driver.get_network(
                            subnet_id=member.subnet_id).id
                        for member in listener.default_pool.members
                        if member.subnet_id
                    )
                )

            nics = self.network_driver.get_plugged_networks(amphora.compute_id)
            # assume we don't have two nics in the same network
            actual_network_nics = dict((nic.network_id, nic) for nic in nics)

            del_ids = set(actual_network_nics) - desired_network_ids
            delete_nics = list(
                actual_network_nics[net_id] for net_id in del_ids)

            add_ids = desired_network_ids - set(actual_network_nics)
            add_nics = list(data_models.Interface(
                network_id=net_id) for net_id in add_ids)
            deltas.append(data_models.Delta(amphora_id=amphora.id,
                                            compute_id=amphora.compute_id,
                                            add_nics=add_nics,
                                            delete_nics=delete_nics))

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


class HandleNetworkDeltas(BaseNetworkTask):
    """Task to plug and unplug networks

    Loop through the deltas and plug or unplug
    networks based on delta
    """

    def execute(self, deltas):
        """Handle network plugging based off deltas."""

        for delta in deltas:
            for nic in delta.add_nics:
                self.network_driver.plug_network(delta.compute_id,
                                                 nic.network_id)

            for nic in delta.delete_nics:
                try:
                    self.network_driver.unplug_network(delta.compute_id,
                                                       nic.network_id)
                except base.NetworkNotFound as e:
                    LOG.debug("Network %d not found ", nic.network_id)
                    pass
                except Exception as e:
                    LOG.error(
                        _LE("Unable to unplug network - exception: %s"),
                        str(e))
                    pass

    def revert(self, deltas):
        """Handle a network plug or unplug failures."""

        for delta in deltas:
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
            LOG.error(_LE("Unable to unplug vip from load balancer %(id)s: "
                          "exception: %(ex)s"), id=loadbalancer.id,
                      ex=e.message)


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

        self.network_driver.deallocate_vip(loadbalancer.vip)
        return


class UpdateVIP(BaseNetworkTask):
    """Task to update a VIP."""

    def execute(self, loadbalancer):
        LOG.debug("Updating VIP of load_balancer %s." % loadbalancer.id)

        self.network_driver.update_vip(loadbalancer)
