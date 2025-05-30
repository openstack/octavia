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

import copy
from typing import List
from typing import Optional

from oslo_config import cfg
from oslo_log import log as logging
from stevedore import driver as stevedore_driver
from taskflow import retry
from taskflow import task
from taskflow.types import failure

from octavia.amphorae.backends.agent import agent_jinja_cfg
from octavia.amphorae.driver_exceptions import exceptions as driver_except
from octavia.common import constants
from octavia.common import utils
from octavia.controller.worker import task_utils as task_utilities
from octavia.db import api as db_apis
from octavia.db import repositories as repo
from octavia.network import data_models

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class BaseAmphoraTask(task.Task):
    """Base task to load drivers common to the tasks."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.amphora_driver = stevedore_driver.DriverManager(
            namespace='octavia.amphora.drivers',
            name=CONF.controller_worker.amphora_driver,
            invoke_on_load=True
        ).driver
        self.amphora_repo = repo.AmphoraRepository()
        self.listener_repo = repo.ListenerRepository()
        self.loadbalancer_repo = repo.LoadBalancerRepository()
        self.task_utils = task_utilities.TaskUtils()


class AmpRetry(retry.Times):

    def on_failure(self, history, *args, **kwargs):
        last_errors = history[-1][1]
        max_retry_attempt = CONF.haproxy_amphora.connection_max_retries
        for task_name, ex_info in last_errors.items():
            if len(history) <= max_retry_attempt:
                # When taskflow persistence is enabled and flow/task state is
                # saved in the backend. If flow(task) is restored(restart of
                # worker,etc) we are getting ex_info as None - we need to RETRY
                # task to check its real state.
                if ex_info is None or ex_info._exc_info is None:
                    return retry.RETRY
                excp = ex_info._exc_info[1]
                if isinstance(excp, driver_except.AmpConnectionRetry):
                    return retry.RETRY

        return retry.REVERT_ALL


class AmpListenersUpdate(BaseAmphoraTask):
    """Task to update the listeners on one amphora."""

    def execute(self, loadbalancer, amphora, timeout_dict=None):
        # Note, we don't want this to cause a revert as it may be used
        # in a failover flow with both amps failing. Skip it and let
        # health manager fix it.
        # TODO(johnsom) Optimize this to use the dicts and not need the
        #               DB lookups
        try:
            session = db_apis.get_session()
            with session.begin():
                db_amp = self.amphora_repo.get(session,
                                               id=amphora[constants.ID])
                db_lb = self.loadbalancer_repo.get(
                    session,
                    id=loadbalancer[constants.LOADBALANCER_ID])
            self.amphora_driver.update_amphora_listeners(
                db_lb, db_amp, timeout_dict)
        except Exception as e:
            LOG.error('Failed to update listeners on amphora %s. Skipping '
                      'this amphora as it is failing to update due to: %s',
                      db_amp.id, str(e))
            with session.begin():
                self.amphora_repo.update(session, db_amp.id,
                                         status=constants.ERROR)


class AmphoraIndexListenerUpdate(BaseAmphoraTask):
    """Task to update the listeners on one amphora."""

    def execute(self, loadbalancer, amphora_index, amphorae,
                amphorae_status: dict, new_amphora_id: str, timeout_dict=()):
        # Note, we don't want this to cause a revert as it may be used
        # in a failover flow with both amps failing. Skip it and let
        # health manager fix it.

        amphora_id = amphorae[amphora_index].get(constants.ID)
        amphora_status = amphorae_status.get(amphora_id, {})
        if amphora_status.get(constants.UNREACHABLE):
            LOG.warning("Skipping listener update because amphora %s "
                        "is not reachable.", amphora_id)
            return

        try:
            # TODO(johnsom) Optimize this to use the dicts and not need the
            #               DB lookups
            session = db_apis.get_session()
            with session.begin():
                db_amp = self.amphora_repo.get(
                    session,
                    id=amphorae[amphora_index][constants.ID])
                db_lb = self.loadbalancer_repo.get(
                    session,
                    id=loadbalancer[constants.LOADBALANCER_ID])
            self.amphora_driver.update_amphora_listeners(
                db_lb, db_amp, timeout_dict)
        except Exception as e:
            LOG.error('Failed to update listeners on amphora %s. Skipping '
                      'this amphora as it is failing to update due to: %s',
                      amphora_id, str(e))
            # Update only the status of the newly created amphora during the
            # failover
            if amphora_id == new_amphora_id:
                session = db_apis.get_session()
                with session.begin():
                    self.amphora_repo.update(session, amphora_id,
                                             status=constants.ERROR)


class ListenersUpdate(BaseAmphoraTask):
    """Task to update amphora with all specified listeners' configurations."""

    def execute(self, loadbalancer_id):
        """Execute updates per listener for an amphora."""
        session = db_apis.get_session()
        with session.begin():
            loadbalancer = self.loadbalancer_repo.get(session,
                                                      id=loadbalancer_id)
        if loadbalancer:
            self.amphora_driver.update(loadbalancer)
        else:
            LOG.error('Load balancer %s for listeners update not found. '
                      'Skipping update.', loadbalancer_id)

    def revert(self, loadbalancer_id, *args, **kwargs):
        """Handle failed listeners updates."""

        LOG.warning("Reverting listeners updates.")
        session = db_apis.get_session()
        with session.begin():
            loadbalancer = self.loadbalancer_repo.get(session,
                                                      id=loadbalancer_id)
        for listener in loadbalancer.listeners:
            self.task_utils.mark_listener_prov_status_error(
                listener.id)


class ListenersStart(BaseAmphoraTask):
    """Task to start all listeners on the vip."""

    def execute(self, loadbalancer, amphora=None):
        """Execute listener start routines for listeners on an amphora."""
        session = db_apis.get_session()
        with session.begin():
            db_lb = self.loadbalancer_repo.get(
                session, id=loadbalancer[constants.LOADBALANCER_ID])
        if db_lb.listeners:
            if amphora is not None:
                with session.begin():
                    db_amp = self.amphora_repo.get(session,
                                                   id=amphora[constants.ID])
            else:
                db_amp = amphora
            self.amphora_driver.start(db_lb, db_amp)
            LOG.debug("Started the listeners on the vip")

    def revert(self, loadbalancer, *args, **kwargs):
        """Handle failed listeners starts."""

        LOG.warning("Reverting listeners starts.")
        session = db_apis.get_session()
        with session.begin():
            db_lb = self.loadbalancer_repo.get(
                session, id=loadbalancer[constants.LOADBALANCER_ID])
        for listener in db_lb.listeners:
            self.task_utils.mark_listener_prov_status_error(listener.id)


class AmphoraIndexListenersReload(BaseAmphoraTask):
    """Task to reload all listeners on an amphora."""

    def execute(self, loadbalancer, amphora_index, amphorae,
                amphorae_status: dict, new_amphora_id: str, timeout_dict=None):
        """Execute listener reload routines for listeners on an amphora."""
        if amphorae is None:
            return

        amphora_id = amphorae[amphora_index].get(constants.ID)
        amphora_status = amphorae_status.get(amphora_id, {})
        if amphora_status.get(constants.UNREACHABLE):
            LOG.warning("Skipping listener reload because amphora %s "
                        "is not reachable.", amphora_id)
            return

        # TODO(johnsom) Optimize this to use the dicts and not need the
        #               DB lookups
        session = db_apis.get_session()
        with session.begin():
            db_amp = self.amphora_repo.get(
                session, id=amphorae[amphora_index][constants.ID])
            db_lb = self.loadbalancer_repo.get(
                session,
                id=loadbalancer[constants.LOADBALANCER_ID])
        if db_lb.listeners:
            try:
                self.amphora_driver.reload(db_lb, db_amp, timeout_dict)
            except Exception as e:
                LOG.warning('Failed to reload listeners on amphora %s. '
                            'Skipping this amphora as it is failing to '
                            'reload due to: %s', amphora_id, str(e))
                # Update only the status of the newly created amphora during
                # the failover
                if amphora_id == new_amphora_id:
                    with session.begin():
                        self.amphora_repo.update(session, amphora_id,
                                                 status=constants.ERROR)


class ListenerDelete(BaseAmphoraTask):
    """Task to delete the listener on the vip."""

    def execute(self, listener):
        """Execute listener delete routines for an amphora."""
        session = db_apis.get_session()
        with session.begin():
            db_listener = self.listener_repo.get(
                session, id=listener[constants.LISTENER_ID])
        self.amphora_driver.delete(db_listener)
        LOG.debug("Deleted the listener on the vip")

    def revert(self, listener, *args, **kwargs):
        """Handle a failed listener delete."""

        LOG.warning("Reverting listener delete.")

        self.task_utils.mark_listener_prov_status_error(
            listener[constants.LISTENER_ID])


class AmphoraGetInfo(BaseAmphoraTask):
    """Task to get information on an amphora."""

    def execute(self, amphora):
        """Execute get_info routine for an amphora."""
        session = db_apis.get_session()
        with session.begin():
            db_amp = self.amphora_repo.get(session,
                                           id=amphora[constants.ID])
        self.amphora_driver.get_info(db_amp)


class AmphoraGetDiagnostics(BaseAmphoraTask):
    """Task to get diagnostics on the amphora and the loadbalancers."""

    def execute(self, amphora):
        """Execute get_diagnostic routine for an amphora."""
        self.amphora_driver.get_diagnostics(amphora)


class AmphoraFinalize(BaseAmphoraTask):
    """Task to finalize the amphora before any listeners are configured."""

    def execute(self, amphora):
        """Execute finalize_amphora routine."""
        session = db_apis.get_session()
        with session.begin():
            db_amp = self.amphora_repo.get(session,
                                           id=amphora.get(constants.ID))
        self.amphora_driver.finalize_amphora(db_amp)
        LOG.debug("Finalized the amphora.")

    def revert(self, result, amphora, *args, **kwargs):
        """Handle a failed amphora finalize."""
        if isinstance(result, failure.Failure):
            return
        LOG.warning("Reverting amphora finalize.")
        self.task_utils.mark_amphora_status_error(
            amphora.get(constants.ID))


class AmphoraPostNetworkPlug(BaseAmphoraTask):
    """Task to notify the amphora post network plug."""

    def execute(self, amphora, ports, amphora_network_config):
        """Execute post_network_plug routine."""
        session = db_apis.get_session()
        with session.begin():
            db_amp = self.amphora_repo.get(session,
                                           id=amphora[constants.ID])

        for port in ports:
            net = data_models.Network(**port.pop(constants.NETWORK))
            ips = port.pop(constants.FIXED_IPS)
            fixed_ips = []
            for ip in ips:
                subnet_arg = ip.pop(constants.SUBNET)
                host_routes = subnet_arg.get('host_routes')
                if host_routes:
                    subnet_arg['host_routes'] = [
                        data_models.HostRoute(**hr)
                        for hr in host_routes
                    ]
                fixed_ips.append(data_models.FixedIP(
                    subnet=data_models.Subnet(**subnet_arg), **ip))
            self.amphora_driver.post_network_plug(
                db_amp,
                data_models.Port(network=net, fixed_ips=fixed_ips, **port),
                amphora_network_config)

            LOG.debug("post_network_plug called on compute instance "
                      "%(compute_id)s for port %(port_id)s",
                      {"compute_id": amphora[constants.COMPUTE_ID],
                       "port_id": port[constants.ID]})

    def revert(self, result, amphora, *args, **kwargs):
        """Handle a failed post network plug."""
        if isinstance(result, failure.Failure):
            return
        LOG.warning("Reverting post network plug.")
        self.task_utils.mark_amphora_status_error(amphora.get(constants.ID))


class AmphoraePostNetworkPlug(BaseAmphoraTask):
    """Task to notify the amphorae post network plug."""

    def execute(self, loadbalancer, updated_ports, amphorae_network_config):
        """Execute post_network_plug routine."""
        amp_post_plug = AmphoraPostNetworkPlug()
        session = db_apis.get_session()
        with session.begin():
            db_lb = self.loadbalancer_repo.get(
                session, id=loadbalancer[constants.LOADBALANCER_ID])
        for amphora in db_lb.amphorae:
            if amphora.id in updated_ports:
                amp_post_plug.execute(amphora.to_dict(),
                                      updated_ports[amphora.id],
                                      amphorae_network_config[amphora.id])

    def revert(self, result, loadbalancer, updated_ports, *args, **kwargs):
        """Handle a failed post network plug."""
        if isinstance(result, failure.Failure):
            return
        session = db_apis.get_session()
        with session.begin():
            db_lb = self.loadbalancer_repo.get(
                session, id=loadbalancer[constants.LOADBALANCER_ID])
        LOG.warning("Reverting post network plug.")
        for amphora in filter(
            lambda amp: amp.status == constants.AMPHORA_ALLOCATED,
                db_lb.amphorae):

            self.task_utils.mark_amphora_status_error(amphora.id)


class AmphoraPostVIPPlug(BaseAmphoraTask):
    """Task to notify the amphora post VIP plug."""

    def execute(self, amphora, loadbalancer, amphorae_network_config):
        """Execute post_vip_routine."""
        session = db_apis.get_session()
        with session.begin():
            db_amp = self.amphora_repo.get(session,
                                           id=amphora.get(constants.ID))
            db_lb = self.loadbalancer_repo.get(
                session, id=loadbalancer[constants.LOADBALANCER_ID])
        vrrp_port = data_models.Port(
            **amphorae_network_config[
                amphora.get(constants.ID)][constants.VRRP_PORT])
        # Required for noop-case
        vip_arg = copy.deepcopy(
            amphorae_network_config[
                amphora.get(constants.ID)][constants.VIP_SUBNET])
        if vip_arg:
            host_routes = vip_arg.get('host_routes')
            if host_routes:
                vip_arg['host_routes'] = [
                    data_models.HostRoute(**hr)
                    for hr in host_routes
                ]
            vip_subnet = data_models.Subnet(**vip_arg)
        else:
            vip_subnet = data_models.Subnet()

        additional_vip_data = []
        for add_vip in amphorae_network_config[
                amphora[constants.ID]]['additional_vip_data']:

            subnet_arg = copy.deepcopy(add_vip['subnet'])
            subnet_arg['host_routes'] = [
                data_models.HostRoute(**hr)
                for hr in subnet_arg['host_routes']]
            subnet = data_models.Subnet(**subnet_arg)

            additional_vip_data.append(
                data_models.AdditionalVipData(
                    ip_address=add_vip['ip_address'],
                    subnet=subnet))

        self.amphora_driver.post_vip_plug(
            db_amp, db_lb, amphorae_network_config, vrrp_port,
            vip_subnet, additional_vip_data=additional_vip_data)
        LOG.debug("Notified amphora of vip plug")

    def revert(self, result, amphora, loadbalancer, *args, **kwargs):
        """Handle a failed amphora vip plug notification."""
        if isinstance(result, failure.Failure):
            return
        LOG.warning("Reverting post vip plug.")
        self.task_utils.mark_amphora_status_error(amphora.get(constants.ID))


class AmphoraePostVIPPlug(BaseAmphoraTask):
    """Task to notify the amphorae post VIP plug."""

    def execute(self, loadbalancer, amphorae_network_config):
        """Execute post_vip_plug across the amphorae."""
        amp_post_vip_plug = AmphoraPostVIPPlug()
        session = db_apis.get_session()
        with session.begin():
            db_lb = self.loadbalancer_repo.get(
                session, id=loadbalancer[constants.LOADBALANCER_ID])
        for amphora in db_lb.amphorae:
            amp_post_vip_plug.execute(amphora.to_dict(),
                                      loadbalancer,
                                      amphorae_network_config)


class AmphoraCertUpload(BaseAmphoraTask):
    """Upload a certificate to the amphora."""

    def execute(self, amphora, server_pem):
        """Execute cert_update_amphora routine."""
        LOG.debug("Upload cert in amphora REST driver")
        fer = utils.get_server_certs_key_passphrases_fernet()
        session = db_apis.get_session()
        with session.begin():
            db_amp = self.amphora_repo.get(session,
                                           id=amphora.get(constants.ID))
        self.amphora_driver.upload_cert_amp(
            db_amp, fer.decrypt(server_pem.encode('utf-8')))


# TODO(johnsom) REMOVE ME!
class AmphoraUpdateVRRPInterface(BaseAmphoraTask):
    """Task to get and update the VRRP interface device name from amphora."""

    def execute(self, amphora, timeout_dict=None):
        try:
            # TODO(johnsom) Optimize this to use the dicts and not need the
            #               DB lookups
            session = db_apis.get_session()
            with session.begin():
                db_amp = self.amphora_repo.get(session,
                                               id=amphora[constants.ID])
            interface = self.amphora_driver.get_interface_from_ip(
                db_amp, db_amp.vrrp_ip, timeout_dict=timeout_dict)
        except Exception as e:
            # This can occur when an active/standby LB has no listener
            LOG.error('Failed to get amphora VRRP interface on amphora '
                      '%s. Skipping this amphora as it is failing due to: '
                      '%s', amphora.get(constants.ID), str(e))
            with session.begin():
                self.amphora_repo.update(session,
                                         amphora.get(constants.ID),
                                         status=constants.ERROR)
            return None

        with session.begin():
            self.amphora_repo.update(session, amphora[constants.ID],
                                     vrrp_interface=interface)
        return interface


class AmphoraIndexUpdateVRRPInterface(BaseAmphoraTask):
    """Task to get and update the VRRP interface device name from amphora."""

    def execute(self, amphora_index, amphorae, amphorae_status: dict,
                new_amphora_id: str, timeout_dict=None):
        amphora_id = amphorae[amphora_index][constants.ID]
        amphora_status = amphorae_status.get(amphora_id, {})
        if amphora_status.get(constants.UNREACHABLE):
            LOG.warning("Skipping VRRP interface update because amphora %s "
                        "is not reachable.", amphora_id)
            return None

        try:
            # TODO(johnsom) Optimize this to use the dicts and not need the
            #               DB lookups
            session = db_apis.get_session()
            with session.begin():
                db_amp = self.amphora_repo.get(session,
                                               id=amphora_id)
            interface = self.amphora_driver.get_interface_from_ip(
                db_amp, db_amp.vrrp_ip, timeout_dict=timeout_dict)
        except Exception as e:
            # This can occur when an active/standby LB has no listener
            LOG.error('Failed to get amphora VRRP interface on amphora '
                      '%s. Skipping this amphora as it is failing due to: '
                      '%s', amphora_id, str(e))
            # Update only the status of the newly created amphora during the
            # failover
            if amphora_id == new_amphora_id:
                with session.begin():
                    self.amphora_repo.update(session, amphora_id,
                                             status=constants.ERROR)
            return None

        with session.begin():
            self.amphora_repo.update(session, amphora_id,
                                     vrrp_interface=interface)
        return interface


class AmphoraVRRPUpdate(BaseAmphoraTask):
    """Task to update the VRRP configuration of an amphora."""

    def execute(self, loadbalancer_id, amphorae_network_config, amphora,
                amp_vrrp_int, timeout_dict=None):
        """Execute update_vrrp_conf."""
        # Note, we don't want this to cause a revert as it may be used
        # in a failover flow with both amps failing. Skip it and let
        # health manager fix it.
        amphora_id = amphora[constants.ID]
        try:
            # TODO(johnsom) Optimize this to use the dicts and not need the
            #               DB lookups
            session = db_apis.get_session()
            with session.begin():
                db_amp = self.amphora_repo.get(session,
                                               id=amphora_id)
                loadbalancer = self.loadbalancer_repo.get(session,
                                                          id=loadbalancer_id)
            db_amp.vrrp_interface = amp_vrrp_int
            self.amphora_driver.update_vrrp_conf(
                loadbalancer, amphorae_network_config, db_amp, timeout_dict)
        except Exception as e:
            LOG.error('Failed to update VRRP configuration amphora %s. '
                      'Skipping this amphora as it is failing to update due '
                      'to: %s', amphora_id, str(e))
            with session.begin():
                self.amphora_repo.update(session, amphora_id,
                                         status=constants.ERROR)

        LOG.debug("Uploaded VRRP configuration of amphora %s.", amphora_id)


class AmphoraIndexVRRPUpdate(BaseAmphoraTask):
    """Task to update the VRRP configuration of an amphora."""

    def execute(self, loadbalancer_id, amphorae_network_config, amphora_index,
                amphorae, amphorae_status: dict, amp_vrrp_int: Optional[str],
                new_amphora_id: str, timeout_dict=None):
        """Execute update_vrrp_conf."""
        # Note, we don't want this to cause a revert as it may be used
        # in a failover flow with both amps failing. Skip it and let
        # health manager fix it.
        amphora_id = amphorae[amphora_index][constants.ID]
        amphora_status = amphorae_status.get(amphora_id, {})
        if amphora_status.get(constants.UNREACHABLE):
            LOG.warning("Skipping VRRP configuration because amphora %s "
                        "is not reachable.", amphora_id)
            return

        try:
            # TODO(johnsom) Optimize this to use the dicts and not need the
            #               DB lookups
            session = db_apis.get_session()
            with session.begin():
                db_amp = self.amphora_repo.get(session,
                                               id=amphora_id)
                loadbalancer = self.loadbalancer_repo.get(session,
                                                          id=loadbalancer_id)
            db_amp.vrrp_interface = amp_vrrp_int
            self.amphora_driver.update_vrrp_conf(
                loadbalancer, amphorae_network_config, db_amp, timeout_dict)
        except Exception as e:
            LOG.error('Failed to update VRRP configuration amphora %s. '
                      'Skipping this amphora as it is failing to update due '
                      'to: %s', amphora_id, str(e))
            # Update only the status of the newly created amphora during the
            # failover
            if amphora_id == new_amphora_id:
                with session.begin():
                    self.amphora_repo.update(session, amphora_id,
                                             status=constants.ERROR)
            return
        LOG.debug("Uploaded VRRP configuration of amphora %s.", amphora_id)


class AmphoraVRRPStart(BaseAmphoraTask):
    """Task to start keepalived on an amphora.

    This will reload keepalived if it is already running.
    """

    def execute(self, amphora, timeout_dict=None):
        # TODO(johnsom) Optimize this to use the dicts and not need the
        #               DB lookups
        session = db_apis.get_session()
        with session.begin():
            db_amp = self.amphora_repo.get(
                session, id=amphora[constants.ID])
        self.amphora_driver.start_vrrp_service(db_amp, timeout_dict)
        LOG.debug("Started VRRP on amphora %s.", amphora[constants.ID])


class AmphoraIndexVRRPStart(BaseAmphoraTask):
    """Task to start keepalived on an amphora.

    This will reload keepalived if it is already running.
    """

    def execute(self, amphora_index, amphorae, amphorae_status: dict,
                new_amphora_id: str, timeout_dict=None):
        # TODO(johnsom) Optimize this to use the dicts and not need the
        #               DB lookups
        amphora_id = amphorae[amphora_index][constants.ID]
        amphora_status = amphorae_status.get(amphora_id, {})
        if amphora_status.get(constants.UNREACHABLE):
            LOG.warning("Skipping VRRP start because amphora %s "
                        "is not reachable.", amphora_id)
            return

        session = db_apis.get_session()
        with session.begin():
            db_amp = self.amphora_repo.get(session, id=amphora_id)
        try:
            self.amphora_driver.start_vrrp_service(db_amp, timeout_dict)
        except Exception as e:
            LOG.error('Failed to start VRRP on amphora %s. '
                      'Skipping this amphora as it is failing to start due '
                      'to: %s', amphora_id, str(e))
            # Update only the status of the newly created amphora during the
            # failover
            if amphora_id == new_amphora_id:
                with session.begin():
                    self.amphora_repo.update(session, amphora_id,
                                             status=constants.ERROR)
            return
        LOG.debug("Started VRRP on amphora %s.",
                  amphorae[amphora_index][constants.ID])


class AmphoraComputeConnectivityWait(BaseAmphoraTask):
    """Task to wait for the compute instance to be up."""

    def execute(self, amphora, raise_retry_exception=False):
        """Execute get_info routine for an amphora until it responds."""
        try:
            session = db_apis.get_session()
            with session.begin():
                db_amphora = self.amphora_repo.get(
                    session, id=amphora.get(constants.ID))
            amp_info = self.amphora_driver.get_info(
                db_amphora, raise_retry_exception=raise_retry_exception)
            LOG.debug('Successfuly connected to amphora %s: %s',
                      amphora.get(constants.ID), amp_info)
        except driver_except.TimeOutException:
            LOG.error("Amphora compute instance failed to become reachable. "
                      "This either means the compute driver failed to fully "
                      "boot the instance inside the timeout interval or the "
                      "instance is not reachable via the lb-mgmt-net.")
            with session.begin():
                self.amphora_repo.update(session,
                                         amphora.get(constants.ID),
                                         status=constants.ERROR)
            raise


class AmphoraConfigUpdate(BaseAmphoraTask):
    """Task to push a new amphora agent configuration to the amphora."""

    def execute(self, amphora, flavor):
        # Extract any flavor based settings
        if flavor:
            topology = flavor.get(constants.LOADBALANCER_TOPOLOGY,
                                  CONF.controller_worker.loadbalancer_topology)
        else:
            topology = CONF.controller_worker.loadbalancer_topology

        # Build the amphora agent config
        agent_cfg_tmpl = agent_jinja_cfg.AgentJinjaTemplater()
        agent_config = agent_cfg_tmpl.build_agent_config(
            amphora.get(constants.ID), topology)
        session = db_apis.get_session()
        with session.begin():
            db_amp = self.amphora_repo.get(session,
                                           id=amphora[constants.ID])
        # Push the new configuration to the amphora
        try:
            self.amphora_driver.update_amphora_agent_config(db_amp,
                                                            agent_config)
        except driver_except.AmpDriverNotImplementedError:
            LOG.error('Amphora {} does not support agent configuration '
                      'update. Please update the amphora image for this '
                      'amphora. Skipping.'.
                      format(amphora.get(constants.ID)))


class AmphoraeGetConnectivityStatus(BaseAmphoraTask):
    """Task that checks amphorae connectivity status.

    Check and return the connectivity status of both amphorae in ACTIVE STANDBY
    load balancers
    """

    def execute(self, amphorae: List[dict], new_amphora_id: str,
                timeout_dict=None):
        amphorae_status = {}

        for amphora in amphorae:
            amphora_id = amphora[constants.ID]
            amphorae_status[amphora_id] = {}

            session = db_apis.get_session()
            with session.begin():
                db_amp = self.amphora_repo.get(session, id=amphora_id)

            try:
                # Verify if the amphora is reachable
                self.amphora_driver.check(db_amp, timeout_dict=timeout_dict)
            except Exception as e:
                LOG.exception("Cannot get status for amphora %s",
                              amphora_id)
                # In case it fails and the tested amphora is the newly created
                # amphora, it's not a normal error handling, re-raise the
                # exception
                if amphora_id == new_amphora_id:
                    raise e
                amphorae_status[amphora_id][constants.UNREACHABLE] = True
            else:
                amphorae_status[amphora_id][constants.UNREACHABLE] = False

        return amphorae_status


class SetAmphoraFirewallRules(BaseAmphoraTask):
    """Task to push updated firewall ruls to an amphora."""

    def execute(self, amphorae: List[dict], amphora_index: int,
                amphora_firewall_rules: List[dict], amphorae_status: dict,
                timeout_dict=None):

        if (amphora_firewall_rules and
                amphora_firewall_rules[0].get('non-sriov-vip', False)):
            # Not an SRIOV VIP, so skip setting firewall rules.
            # This is already logged in GetAmphoraFirewallRules.
            return

        amphora_id = amphorae[amphora_index][constants.ID]
        amphora_status = amphorae_status.get(amphora_id, {})
        if amphora_status.get(constants.UNREACHABLE):
            LOG.warning("Skipping firewall rules update because amphora %s "
                        "is not reachable.", amphora_id)
            return

        session = db_apis.get_session()
        with session.begin():
            db_amp = self.amphora_repo.get(session, id=amphora_id)

        self.amphora_driver.set_interface_rules(
            db_amp,
            amphorae[amphora_index][constants.VRRP_IP],
            amphora_firewall_rules, timeout_dict=timeout_dict)
