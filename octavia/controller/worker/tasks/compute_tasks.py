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
import time

from oslo_config import cfg
from stevedore import driver as stevedore_driver
from taskflow import task
from taskflow.types import failure

from octavia.amphorae.backends.agent import agent_jinja_cfg
from octavia.common import constants
from octavia.common import exceptions
from octavia.i18n import _LE, _LW

CONF = cfg.CONF
CONF.import_group('controller_worker', 'octavia.common.config')
LOG = logging.getLogger(__name__)


class BaseComputeTask(task.Task):
    """Base task to load drivers common to the tasks."""

    def __init__(self, **kwargs):
        super(BaseComputeTask, self).__init__(**kwargs)
        self.compute = stevedore_driver.DriverManager(
            namespace='octavia.compute.drivers',
            name=CONF.controller_worker.compute_driver,
            invoke_on_load=True,
            invoke_kwds={'region': CONF.os_region_name}
        ).driver


class ComputeCreate(BaseComputeTask):
    """Create the compute instance for a new amphora."""

    def execute(self, amphora_id, ports=None, config_drive_files=None):
        """Create an amphora

        :returns: an amphora
        """
        ports = ports or []
        config_drive_files = config_drive_files or {}
        LOG.debug("Compute create execute for amphora with id %s", amphora_id)

        ssh_access = CONF.controller_worker.amp_ssh_access_allowed
        ssh_key = CONF.controller_worker.amp_ssh_key_name
        key_name = None if not ssh_access else ssh_key

        try:
            agent_cfg = agent_jinja_cfg.AgentJinjaTemplater()
            config_drive_files['/etc/octavia/amphora-agent.conf'] = (
                agent_cfg.build_agent_config(amphora_id))
            compute_id = self.compute.build(
                name="amphora-" + amphora_id,
                amphora_flavor=CONF.controller_worker.amp_flavor_id,
                image_id=CONF.controller_worker.amp_image_id,
                key_name=key_name,
                sec_groups=CONF.controller_worker.amp_secgroup_list,
                network_ids=[CONF.controller_worker.amp_network],
                port_ids=[port.id for port in ports],
                config_drive_files=config_drive_files)

            LOG.debug("Server created with id: %s for amphora id: %s",
                      compute_id, amphora_id)
            return compute_id

        except Exception:
            LOG.exception(_LE("Compute create for amphora id: %s failed"),
                          amphora_id)
            raise

    def revert(self, result, amphora_id, *args, **kwargs):
        """This method will revert the creation of the

        amphora. So it will just delete it in this flow
        """
        if isinstance(result, failure.Failure):
            return
        compute_id = result
        LOG.warn(_LW("Reverting compute create for amphora with id"
                     "%(amp)s and compute id: %(comp)s"),
                 {'amp': amphora_id, 'comp': compute_id})
        try:
            self.compute.delete(compute_id)
        except Exception:
            LOG.exception(_LE("Reverting compute create failed"))


class CertComputeCreate(ComputeCreate):
    def execute(self, amphora_id, server_pem, ports=None):
        """Create an amphora

        :returns: an amphora
        """

        # load client certificate
        with open(CONF.controller_worker.client_ca, 'r') as client_ca:
            config_drive_files = {
                # '/etc/octavia/octavia.conf'
                '/etc/octavia/certs/server.pem': server_pem,
                '/etc/octavia/certs/client_ca.pem': client_ca}
            return super(CertComputeCreate, self).execute(
                amphora_id, ports=ports, config_drive_files=config_drive_files)


class DeleteAmphoraeOnLoadBalancer(BaseComputeTask):
    """Delete the amphorae on a load balancer.

    Iterate through amphorae, deleting them
    """

    def execute(self, loadbalancer):
        for amp in loadbalancer.amphorae:
            try:
                self.compute.delete(amp.compute_id)
            except Exception:
                LOG.exception(_LE("Compute delete for amphora id: %s failed"),
                              amp.id)
                raise


class ComputeDelete(BaseComputeTask):
    def execute(self, amphora):
        LOG.debug("Compute Delete execute for amphora with id %s", amphora.id)

        try:
            self.compute.delete(amphora.compute_id)
        except Exception:
            LOG.exception(_LE("Compute delete for amphora id: %s failed"),
                          amphora.id)
            raise


class ComputeWait(BaseComputeTask):
    """Wait for the compute driver to mark the amphora active."""

    def execute(self, compute_id):
        """Wait for the compute driver to mark the amphora active

        :raises: Generic exception if the amphora is not active
        :returns: An amphora object
        """
        for i in range(CONF.controller_worker.amp_active_retries):
            amp = self.compute.get_amphora(compute_id)
            if amp.status == constants.ACTIVE:
                return amp
            elif amp.status == constants.ERROR:
                raise exceptions.ComputeBuildException()
            time.sleep(CONF.controller_worker.amp_active_wait_sec)

        raise exceptions.ComputeWaitTimeoutException()
