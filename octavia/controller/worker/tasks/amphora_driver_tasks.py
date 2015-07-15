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
from octavia.db import api as db_apis
from octavia.db import repositories as repo
from octavia.i18n import _LW

CONF = cfg.CONF
CONF.import_group('controller_worker', 'octavia.common.config')
LOG = logging.getLogger(__name__)


class BaseAmphoraTask(task.Task):
    """Base task to load drivers common to the tasks."""

    def __init__(self, **kwargs):
        super(BaseAmphoraTask, self).__init__(**kwargs)
        self.amphora_driver = stevedore_driver.DriverManager(
            namespace='octavia.amphora.drivers',
            name=CONF.controller_worker.amphora_driver,
            invoke_on_load=True
        ).driver
        self.amphora_repo = repo.AmphoraRepository()
        self.listener_repo = repo.ListenerRepository()
        self.loadbalancer_repo = repo.LoadBalancerRepository()


class ListenerUpdate(BaseAmphoraTask):
    """Task to update an amphora with new configuration for the listener."""

    def execute(self, listener, vip):
        """Execute listener update routines for an amphora."""
        self.amphora_driver.update(listener, vip)
        LOG.debug("Updated amphora with new configuration for listener")

    def revert(self, listener, *args, **kwargs):
        """Handle a failed listener update."""

        LOG.warn(_LW("Reverting listener update."))
        self.listener_repo.update(db_apis.get_session(), id=listener.id,
                                  provisioning_status=constants.ERROR)
        return None


class ListenersUpdate(BaseAmphoraTask):
    """Task to update amphora with all listeners' configurations."""

    def execute(self, listeners, vip):
        """Execute updates per listener for an amphora."""
        for listener in listeners:
            self.amphora_driver.update(listener, vip)

    def revert(self, listeners, *args, **kwargs):
        """Handle failed listeners updates."""

        LOG.warn(_LW("Reverting listeners updates."))
        for listener in listeners:
            self.listener_repo.update(db_apis.get_session(), id=listener.id,
                                      provisioning_status=constants.ERROR)
        return None


class ListenerStop(BaseAmphoraTask):
    """Task to stop the listener on the vip."""

    def execute(self, listener, vip):
        """Execute listener stop routines for an amphora."""
        self.amphora_driver.stop(listener, vip)
        LOG.debug("Stopped the listener on the vip")

    def revert(self, listener, *args, **kwargs):
        """Handle a failed listener stop."""

        LOG.warn(_LW("Reverting listener stop."))
        self.listener_repo.update(db_apis.get_session(), id=listener.id,
                                  provisioning_status=constants.ERROR)
        return None


class ListenerStart(BaseAmphoraTask):
    """Task to start the listener on the vip."""

    def execute(self, listener, vip):
        """Execute listener start routines for an amphora."""
        self.amphora_driver.start(listener, vip)
        LOG.debug("Started the listener on the vip")

    def revert(self, listener, *args, **kwargs):
        """Handle a failed listener start."""

        LOG.warn(_LW("Reverting listener start."))
        self.listener_repo.update(db_apis.get_session(), id=listener.id,
                                  provisioning_status=constants.ERROR)
        return None


class ListenersStart(BaseAmphoraTask):
    """Task to start all listeners on the vip."""

    def execute(self, listeners, vip):
        """Execute listener start routines for listeners on an amphora."""
        for listener in listeners:
            self.amphora_driver.start(listener, vip)
        LOG.debug("Started the listeners on the vip")

    def revert(self, listeners, *args, **kwargs):
        """Handle failed listeners starts."""

        LOG.warn(_LW("Reverting listeners starts."))
        for listener in listeners:
            self.listener_repo.update(db_apis.get_session(), id=listener.id,
                                      provisioning_status=constants.ERROR)
        return None


class ListenerDelete(BaseAmphoraTask):
    """Task to delete the listener on the vip."""

    def execute(self, listener, vip):
        """Execute listener delete routines for an amphora."""
        self.amphora_driver.delete(listener, vip)
        LOG.debug("Deleted the listener on the vip")

    def revert(self, listener, *args, **kwargs):
        """Handle a failed listener delete."""

        LOG.warn(_LW("Reverting listener delete."))
        self.listener_repo.update(db_apis.get_session(), id=listener.id,
                                  provisioning_status=constants.ERROR)


class AmphoraGetInfo(BaseAmphoraTask):
    """Task to get information on an amphora."""

    def execute(self, amphora):
        """Execute get_info routine for an amphora."""
        self.amphora_driver.get_info(amphora)


class AmphoraGetDiagnostics(BaseAmphoraTask):
    """Task to get diagnostics on the amphora and the loadbalancers."""

    def execute(self, amphora):
        """Execute get_diagnostic routine for an amphora."""
        self.amphora_driver.get_diagnostics(amphora)


class AmphoraFinalize(BaseAmphoraTask):
    """Task to finalize the amphora before any listeners are configured."""

    def execute(self, amphora):
        """Execute finalize_amphora routine."""
        self.amphora_driver.finalize_amphora(amphora)
        LOG.debug("Finalized the amphora.")

    def revert(self, result, amphora, *args, **kwargs):
        """Handle a failed amphora finalize."""
        if isinstance(result, failure.Failure):
            return
        LOG.warn(_LW("Reverting amphora finalize."))
        self.amphora_repo.update(db_apis.get_session(), id=amphora.id,
                                 status=constants.ERROR)


class AmphoraPostNetworkPlug(BaseAmphoraTask):
    """Task to notify the amphora post network plug."""

    def execute(self, amphora, ports):
        """Execute post_network_plug routine."""
        for port in ports:
            self.amphora_driver.post_network_plug(amphora, port)
            LOG.debug("post_network_plug called on compute instance "
                      "{compute_id} for port {port_id}".format(
                          compute_id=amphora.compute_id, port_id=port.id))

    def revert(self, result, amphora, *args, **kwargs):
        """Handle a failed post network plug."""
        if isinstance(result, failure.Failure):
            return
        LOG.warn(_LW("Reverting post network plug."))
        self.amphora_repo.update(db_apis.get_session(), id=amphora.id,
                                 status=constants.ERROR)


class AmphoraePostNetworkPlug(BaseAmphoraTask):
    """Task to notify the amphorae post network plug."""

    def execute(self, loadbalancer, added_ports):
        """Execute post_network_plug routine."""
        amp_post_plug = AmphoraPostNetworkPlug()
        for amphora in loadbalancer.amphorae:
            if amphora.id in added_ports:
                amp_post_plug.execute(amphora, added_ports[amphora.id])

    def revert(self, result, loadbalancer, added_ports, *args, **kwargs):
        """Handle a failed post network plug."""
        if isinstance(result, failure.Failure):
            return
        LOG.warn(_LW("Reverting post network plug."))
        for amphora in loadbalancer.amphorae:
            self.amphora_repo.update(db_apis.get_session(), id=amphora.id,
                                     status=constants.ERROR)


class AmphoraPostVIPPlug(BaseAmphoraTask):
    """Task to notify the amphora post VIP plug."""

    def execute(self, loadbalancer, amphorae_network_config):
        """Execute post_vip_routine."""
        self.amphora_driver.post_vip_plug(
            loadbalancer, amphorae_network_config)
        LOG.debug("Notfied amphora of vip plug")

    def revert(self, result, loadbalancer, *args, **kwargs):
        """Handle a failed amphora vip plug notification."""
        if isinstance(result, failure.Failure):
            return
        LOG.warn(_LW("Reverting post vip plug."))
        self.loadbalancer_repo.update(db_apis.get_session(),
                                      id=loadbalancer.id,
                                      status=constants.ERROR)
