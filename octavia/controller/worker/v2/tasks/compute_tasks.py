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

import random
import time

from cryptography import fernet
from oslo_config import cfg
from oslo_log import log as logging
from stevedore import driver as stevedore_driver
from taskflow import retry
from taskflow import task
from taskflow.types import failure
import tenacity

from octavia.amphorae.backends.agent import agent_jinja_cfg
from octavia.common import constants
from octavia.common import exceptions
from octavia.common.jinja.logging import logging_jinja_cfg
from octavia.common.jinja import user_data_jinja_cfg
from octavia.common import utils
from octavia.controller.worker import amphora_rate_limit
from octavia.db import api as db_apis
from octavia.db import repositories as repo

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class BaseComputeTask(task.Task):
    """Base task to load drivers common to the tasks."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.compute = stevedore_driver.DriverManager(
            namespace='octavia.compute.drivers',
            name=CONF.controller_worker.compute_driver,
            invoke_on_load=True
        ).driver
        self.loadbalancer_repo = repo.LoadBalancerRepository()
        self.amphora_repo = repo.AmphoraRepository()
        self.az_repo = repo.AvailabilityZoneRepository()
        self.rate_limit = amphora_rate_limit.AmphoraBuildRateLimit()


class ComputeRetry(retry.Times):

    def on_failure(self, history, *args, **kwargs):
        last_errors = history[-1][1]
        max_retry_attempt = CONF.controller_worker.amp_active_retries
        for task_name, ex_info in last_errors.items():
            if len(history) <= max_retry_attempt:
                # When taskflow persistance is enabled and flow/task state is
                # saved in the backend. If flow(task) is restored(restart of
                # worker,etc) we are getting ex_info as None - we need to RETRY
                # task to check its real state.
                if ex_info is None or ex_info._exc_info is None:
                    return retry.RETRY
                excp = ex_info._exc_info[1]
                if isinstance(excp, exceptions.ComputeWaitTimeoutException):
                    return retry.RETRY

        return retry.REVERT_ALL


class ComputeCreate(BaseComputeTask):
    """Create the compute instance for a new amphora."""

    def execute(self, amphora_id, server_group_id, config_drive_files=None,
                build_type_priority=constants.LB_CREATE_NORMAL_PRIORITY,
                ports=None, flavor=None, availability_zone=None,
                loadbalancer_id=None):
        """Create an amphora

        :param availability_zone: availability zone metadata dictionary
        :param loadbalancer_id: ID of creating loadbalancer

        :returns: an amphora
        """
        ports = ports or []
        network_ids = CONF.controller_worker.amp_boot_network_list[:]
        config_drive_files = config_drive_files or {}
        user_data = None
        LOG.debug("Compute create execute for amphora with id %s", amphora_id)

        user_data_config_drive = CONF.controller_worker.user_data_config_drive
        key_name = CONF.controller_worker.amp_ssh_key_name

        # Apply an Octavia flavor customizations
        if flavor:
            topology = flavor.get(constants.LOADBALANCER_TOPOLOGY,
                                  CONF.controller_worker.loadbalancer_topology)
            lb_flavor_zones = flavor.get(constants.AVAILABILITY_ZONES)
            lb_flvaor_comp_zones = flavor.get(constants.COMPUTE_ZONES)
            amp_compute_flavor = flavor.get(
                constants.COMPUTE_FLAVOR, CONF.controller_worker.amp_flavor_id)
            amp_image_tag = flavor.get(
                constants.AMP_IMAGE_TAG, CONF.controller_worker.amp_image_tag)
        else:
            lb_flavor_zones = None
            lb_flvaor_comp_zones = None
            topology = CONF.controller_worker.loadbalancer_topology
            amp_compute_flavor = CONF.controller_worker.amp_flavor_id
            amp_image_tag = CONF.controller_worker.amp_image_tag

        # Availability zone source order: arg, flavor, conf worker, conf nova
        if availability_zone:
            # az info from arg...
            # Here we get AZ context and not actual availability zone data, so
            # in order to standartize the logic, we need to form AZ dict.
            az_conf_name = availability_zone.get(constants.COMPUTE_ZONE)
            az_conf_net = availability_zone.get(constants.MANAGEMENT_NETWORK)
            conf_zones = [az_conf_name]
            az_config = {
                az_conf_name: {
                    constants.COMPUTE_ZONE: az_conf_name,
                    constants.MANAGEMENT_NETWORK: az_conf_net}}
        elif lb_flavor_zones:
            # az info from flavor
            conf_zones = lb_flavor_zones
            az_config = self._get_zones_metadata(lb_flavor_zones)
        elif lb_flvaor_comp_zones:
            conf_zones = lb_flvaor_comp_zones
            az_config = self._form_az_config_dict(conf_zones)
        elif CONF.controller_worker.availability_zones:
            conf_zones = CONF.controller_worker.availability_zones
            az_config = self._get_zones_metadata(conf_zones)
        else:
            # az info from config
            # if we have multiple nova availability zones defined use multiple
            # otherwise fallback to a single defailt. And form fake metadata
            if CONF.nova.availability_zones:
                conf_zones = CONF.nova.availability_zones
            else:
                conf_zones = [CONF.nova.availability_zone]
            az_config = self._form_az_config_dict(conf_zones)

        if len(conf_zones) > 1:
            # Multiple availability zones should result in anti-affinity
            LOG.debug("Using zone anti-affinity. Found configured zones: %s",
                      conf_zones)
            # We have multiple availability zones. For master and standalone
            # we can just pick random, while for the backup we should not
            # choose the same with the master. loadbalancer_id is already
            # random enough as it is uuid. So its hash could be used to chose
            master_zone = conf_zones[hash(loadbalancer_id) % len(conf_zones)]
            available_zones = list(set(conf_zones) - set([master_zone]))
            # Failover should preserve current AZ
            if ((constants.FAILOVER_LOADBALANCER_FLOW in self.name) or
                    (constants.FAILOVER_AMPHORA_FLOW in self.name)):
                all_comp_zones = self._get_list_of_comp_az(az_config)
                amp_old_zone = self._get_az_for_failover(all_comp_zones,
                                                         loadbalancer_id)
                # find a name in az_config based on availability_zone name
                for azname, config in az_config.items():
                    if config[constants.COMPUTE_ZONE] == amp_old_zone:
                        choosed_zone = azname
                        break
                else:
                    choosed_zone = amp_old_zone
                    az_config[amp_old_zone] = {constants.COMPUTE_ZONE:
                                               amp_old_zone}
            elif constants.ROLE_BACKUP in self.name:
                choosed_zone = random.choice(available_zones)
            else:
                # Just create master for any other option
                choosed_zone = master_zone
        else:
            choosed_zone = conf_zones[0] if conf_zones else None

        if choosed_zone:
            amp_az_meta = az_config[choosed_zone]
            amp_availability_zone = amp_az_meta[constants.COMPUTE_ZONE]
            amp_network = az_config[choosed_zone].get(
                constants.MANAGEMENT_NETWORK)
            if amp_network:
                network_ids = [amp_network]
            LOG.debug("Placing amphora in AZ: %s", amp_availability_zone)
        else:
            amp_availability_zone = None

        try:
            if CONF.haproxy_amphora.build_rate_limit != -1:
                self.rate_limit.add_to_build_request_queue(
                    amphora_id, build_type_priority)

            agent_cfg = agent_jinja_cfg.AgentJinjaTemplater()
            config_drive_files['/etc/octavia/amphora-agent.conf'] = (
                agent_cfg.build_agent_config(amphora_id, topology))

            logging_cfg = logging_jinja_cfg.LoggingJinjaTemplater(
                CONF.amphora_agent.logging_template_override)
            config_drive_files['/etc/rsyslog.d/10-rsyslog.conf'] = (
                logging_cfg.build_logging_config())

            udtemplater = user_data_jinja_cfg.UserDataJinjaCfg()
            user_data = udtemplater.build_user_data_config(
                config_drive_files if user_data_config_drive else {})
            if user_data_config_drive:
                config_drive_files = None

            compute_id = self.compute.build(
                name="amphora-" + amphora_id,
                amphora_flavor=amp_compute_flavor,
                image_tag=amp_image_tag,
                image_owner=CONF.controller_worker.amp_image_owner_id,
                key_name=key_name,
                sec_groups=CONF.controller_worker.amp_secgroup_list,
                network_ids=network_ids,
                port_ids=[port.id for port in ports],
                config_drive_files=config_drive_files,
                user_data=user_data,
                server_group_id=server_group_id,
                availability_zone=amp_availability_zone)

            LOG.info("Server created with id: %s for amphora id: %s",
                     compute_id, amphora_id)
            return compute_id

        except Exception:
            LOG.exception("Compute create for amphora id: %s failed",
                          amphora_id)
            raise

    def _get_zones_metadata(self, zones):
        """Get AZ details from availability zone profile. Form dict

        :param zones: list of strings. Octavia availability zone names
        """
        config = {
            zone: self.az_repo.get_availability_zone_metadata_dict(
                db_apis.get_session(), zone)
            for zone in zones}
        return config

    def _get_az_for_failover(self, compute_zones, loadbalancer_id):
        """Calculate AZ where to create a new amphora.

        When the failover happens we need to find amphora we are replacing to
        place a new one exactly on the same AZ

        :param compute_zones: A list of allowed compute availability zones
        :param loadbalancer_id: uuid of the loadbalancer
        """
        current_amps = self.amphora_repo.get_all(
            db_apis.get_session(), load_balancer_id=loadbalancer_id)[0]
        pending_amp = [
            amp for amp in current_amps
            if amp.status == constants.PENDING_DELETE]
        allocated_amp_computes = [
            amp.compute_id for amp in current_amps
            if amp.status == constants.AMPHORA_ALLOCATED]
        if len(pending_amp) == 1:
            pending_compute_id = pending_amp[0].compute_id
            return self.compute.manager.find(
                id=pending_compute_id).to_dict().get(
                    'OS-EXT-AZ:availability_zone')
        used_zones = [
            self.compute.manager.find(amp.compute_id).to_dict().get(
                'OS-EXT-AZ:availability_zone')
            for amp in allocated_amp_computes
        ]
        available_zones = compute_zones - used_zones
        if len(available_zones) < 1:
            return compute_zones[0]
        return random.choice(available_zones)

    @staticmethod
    def _form_az_config_dict(zones):
        return {zone: {constants.COMPUTE_ZONE: zone} for zone in zones}

    @staticmethod
    def _get_list_of_comp_az(zones):
        return [zone[constants.COMPUTE_ZONE] for zone in zones.values()]

    def revert(self, result, amphora_id, *args, **kwargs):
        """This method will revert the creation of the

        amphora. So it will just delete it in this flow
        """
        if isinstance(result, failure.Failure):
            return
        compute_id = result
        LOG.warning("Reverting compute create for amphora with id "
                    "%(amp)s and compute id: %(comp)s",
                    {'amp': amphora_id, 'comp': compute_id})
        try:
            self.compute.delete(compute_id)
        except Exception:
            LOG.exception("Reverting compute create failed")


class CertComputeCreate(ComputeCreate):
    def execute(self, amphora_id, server_pem, server_group_id,
                build_type_priority=constants.LB_CREATE_NORMAL_PRIORITY,
                ports=None, flavor=None, availability_zone=None,
                loadbalancer_id=None):
        """Create an amphora

        :param availability_zone: availability zone metadata dictionary

        :returns: an amphora
        """

        # load client certificate
        with open(CONF.controller_worker.client_ca,
                  'r', encoding='utf-8') as client_ca:
            ca = client_ca.read()

        key = utils.get_compatible_server_certs_key_passphrase()
        fer = fernet.Fernet(key)
        config_drive_files = {
            '/etc/octavia/certs/server.pem': fer.decrypt(
                server_pem.encode("utf-8")).decode("utf-8"),
            '/etc/octavia/certs/client_ca.pem': ca}
        return super().execute(
            amphora_id, config_drive_files=config_drive_files,
            build_type_priority=build_type_priority,
            server_group_id=server_group_id, ports=ports, flavor=flavor,
            availability_zone=availability_zone,
            loadbalancer_id=loadbalancer_id)


class DeleteAmphoraeOnLoadBalancer(BaseComputeTask):
    """Delete the amphorae on a load balancer.

    Iterate through amphorae, deleting them
    """

    def execute(self, loadbalancer):
        session = db_apis.get_session()
        with session.begin():
            db_lb = self.loadbalancer_repo.get(
                session, id=loadbalancer[constants.LOADBALANCER_ID])
        for amp in db_lb.amphorae:
            # The compute driver will already handle NotFound
            try:
                self.compute.delete(amp.compute_id)
            except Exception:
                LOG.exception("Compute delete for amphora id: %s failed",
                              amp.id)
                raise


class ComputeDelete(BaseComputeTask):
    @tenacity.retry(retry=tenacity.retry_if_exception_type(),
                    stop=tenacity.stop_after_attempt(CONF.compute.max_retries),
                    wait=tenacity.wait_exponential(
                        multiplier=CONF.compute.retry_backoff,
                        min=CONF.compute.retry_interval,
                        max=CONF.compute.retry_max), reraise=True)
    def execute(self, amphora, passive_failure=False):

        amphora_id = amphora.get(constants.ID)
        compute_id = amphora[constants.COMPUTE_ID]

        if self.execute.retry.statistics.get(constants.ATTEMPT_NUMBER, 1) == 1:
            LOG.debug('Compute delete execute for amphora with ID %s and '
                      'compute ID: %s', amphora_id, compute_id)
        else:
            LOG.warning('Retrying compute delete of %s attempt %s of %s.',
                        compute_id,
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
            self.compute.delete(compute_id)
        except Exception:
            if (self.execute.retry.statistics[constants.ATTEMPT_NUMBER] !=
                    self.execute.retry.stop.max_attempt_number):
                LOG.warning('Compute delete for amphora id: %s failed. '
                            'Retrying.', amphora_id)
                raise
            if passive_failure:
                LOG.exception('Compute delete for compute ID: %s on amphora '
                              'ID: %s failed. This resource will be abandoned '
                              'and should manually be cleaned up once the '
                              'compute service is functional.',
                              compute_id, amphora_id)
            else:
                LOG.exception('Compute delete for compute ID: %s on amphora '
                              'ID: %s failed. The compute service has failed. '
                              'Aborting and reverting.', compute_id,
                              amphora_id)
                raise


class ComputeWait(BaseComputeTask):
    """Wait for the compute driver to mark the amphora active."""

    def execute(self, compute_id, amphora_id, availability_zone):
        """Wait for the compute driver to mark the amphora active

        :param compute_id: virtual machine UUID
        :param amphora_id: id of the amphora object
        :param availability_zone: availability zone metadata dictionary

        :raises: Generic exception if the amphora is not active
        :returns: An amphora object
        """
        if availability_zone:
            amp_network = availability_zone.get(constants.MANAGEMENT_NETWORK)
        else:
            amp_network = None

        amp, fault = self.compute.get_amphora(compute_id, amp_network)
        if amp.status == constants.ACTIVE:
            if CONF.haproxy_amphora.build_rate_limit != -1:
                self.rate_limit.remove_from_build_req_queue(amphora_id)
            return amp.to_dict()
        if amp.status == constants.ERROR:
            raise exceptions.ComputeBuildException(fault=fault)

        time.sleep(CONF.controller_worker.amp_active_wait_sec)
        raise exceptions.ComputeWaitTimeoutException(id=compute_id)


class NovaServerGroupCreate(BaseComputeTask):
    def execute(self, loadbalancer_id):
        """Create a server group by nova client api

        :param loadbalancer_id: will be used for server group's name
        :param policy: will used for server group's policy
        :raises: Generic exception if the server group is not created
        :returns: server group's id
        """

        name = 'octavia-lb-' + loadbalancer_id
        server_group = self.compute.create_server_group(
            name, CONF.nova.anti_affinity_policy)
        LOG.debug("Server Group created with id: %s for load balancer id: "
                  "%s", server_group.id, loadbalancer_id)
        return server_group.id

    def revert(self, result, *args, **kwargs):
        """This method will revert the creation of the

        :param result: here it refers to server group id
        """
        server_group_id = result
        LOG.warning("Reverting server group create with id:%s",
                    server_group_id)
        try:
            self.compute.delete_server_group(server_group_id)
        except Exception as e:
            LOG.error("Failed to delete server group.  Resources may "
                      "still be in use for server group: %(sg)s due to "
                      "error: %(except)s",
                      {'sg': server_group_id, 'except': str(e)})


class NovaServerGroupDelete(BaseComputeTask):
    def execute(self, server_group_id):
        if server_group_id is not None:
            self.compute.delete_server_group(server_group_id)
        else:
            return


class AttachPort(BaseComputeTask):
    def execute(self, amphora, port):
        """Attach a port to an amphora instance.

        :param amphora: The amphora to attach the port to.
        :param port: The port to attach to the amphora.
        :returns: None
        """
        LOG.debug('Attaching port: %s to compute: %s',
                  port[constants.ID], amphora[constants.COMPUTE_ID])
        self.compute.attach_network_or_port(amphora[constants.COMPUTE_ID],
                                            port_id=port[constants.ID])

    def revert(self, amphora, port, *args, **kwargs):
        """Revert our port attach.

        :param amphora: The amphora to detach the port from.
        :param port: The port to attach to the amphora.
        """
        LOG.warning('Reverting port: %s attach to compute: %s',
                    port[constants.ID], amphora[constants.COMPUTE_ID])
        try:
            self.compute.detach_port(amphora[constants.COMPUTE_ID],
                                     port[constants.ID])
        except Exception as e:
            LOG.error('Failed to detach port %s from compute %s for revert '
                      'due to %s.', port[constants.ID],
                      amphora[constants.COMPUTE_ID], str(e))
