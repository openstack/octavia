# Copyright 2015 Hewlett Packard Enterprise Development Company LP
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

from oslo_log import log as logging
import six

from octavia.amphorae.drivers import driver_base
from octavia.amphorae.drivers.keepalived.jinja import jinja_cfg
from octavia.common import constants

LOG = logging.getLogger(__name__)
API_VERSION = constants.API_VERSION


class KeepalivedAmphoraDriverMixin(driver_base.VRRPDriverMixin):
    def __init__(self):
        super(KeepalivedAmphoraDriverMixin, self).__init__()

        # The Mixed class must define a self.client object for the
        # AmphoraApiClient

    def update_vrrp_conf(self, loadbalancer):
        """Update amphorae of the loadbalancer with a new VRRP configuration

        :param loadbalancer: loadbalancer object
        """
        templater = jinja_cfg.KeepalivedJinjaTemplater()

        LOG.debug("Update loadbalancer %s amphora VRRP configuration.",
                  loadbalancer.id)

        for amp in six.moves.filter(
            lambda amp: amp.status == constants.AMPHORA_ALLOCATED,
                loadbalancer.amphorae):
            # Generate Keepalived configuration from loadbalancer object
            config = templater.build_keepalived_config(loadbalancer, amp)
            self.client.upload_vrrp_config(amp, config)

    def stop_vrrp_service(self, loadbalancer):
        """Stop the vrrp services running on the loadbalancer's amphorae

        :param loadbalancer: loadbalancer object
        """
        LOG.info("Stop loadbalancer %s amphora VRRP Service.",
                 loadbalancer.id)

        for amp in six.moves.filter(
            lambda amp: amp.status == constants.AMPHORA_ALLOCATED,
                loadbalancer.amphorae):

            self.client.stop_vrrp(amp)

    def start_vrrp_service(self, loadbalancer):
        """Start the VRRP services of all amphorae of the loadbalancer

        :param loadbalancer: loadbalancer object
        """
        LOG.info("Start loadbalancer %s amphora VRRP Service.",
                 loadbalancer.id)

        for amp in six.moves.filter(
            lambda amp: amp.status == constants.AMPHORA_ALLOCATED,
                loadbalancer.amphorae):

            LOG.debug("Start VRRP Service on amphora %s .", amp.lb_network_ip)
            self.client.start_vrrp(amp)

    def reload_vrrp_service(self, loadbalancer):
        """Reload the VRRP services of all amphorae of the loadbalancer

        :param loadbalancer: loadbalancer object
        """
        LOG.info("Reload loadbalancer %s amphora VRRP Service.",
                 loadbalancer.id)

        for amp in six.moves.filter(
            lambda amp: amp.status == constants.AMPHORA_ALLOCATED,
                loadbalancer.amphorae):

            self.client.reload_vrrp(amp)

    def get_vrrp_interface(self, amphora, timeout_dict=None):
        return self.client.get_interface(
            amphora, amphora.vrrp_ip, timeout_dict=timeout_dict)['interface']
