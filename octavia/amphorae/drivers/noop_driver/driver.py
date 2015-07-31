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

from oslo_log import log as logging

from octavia.amphorae.drivers import driver_base as driver_base

LOG = logging.getLogger(__name__)


class LoggingMixIn(driver_base.HealthMixin, driver_base.StatsMixin):
    def update_stats(self, stats):
        LOG.debug("Amphora %s no-op, update stats %s",
                  self.__class__.__name__, stats)
        self.stats = stats

    def update_health(self, health):
        LOG.debug("Amphora %s no-op, update health %s",
                  self.__class__.__name__, health)
        self.health = health


class NoopManager(object):

    def __init__(self):
        super(NoopManager, self).__init__()
        self.amphoraconfig = {}

    def update(self, listener, vip):
        LOG.debug("Amphora %s no-op, update listener %s, vip %s",
                  self.__class__.__name__, listener.protocol_port,
                  vip.ip_address)
        self.amphoraconfig[(listener.protocol_port,
                            vip.ip_address)] = (listener, vip, 'active')

    def stop(self, listener, vip):
        LOG.debug("Amphora %s no-op, stop listener %s, vip %s",
                  self.__class__.__name__,
                  listener.protocol_port, vip.ip_address)
        self.amphoraconfig[(listener.protocol_port,
                            vip.ip_address)] = (listener, vip, 'stop')

    def start(self, listener, vip):
        LOG.debug("Amphora %s no-op, start listener %s, vip %s",
                  self.__class__.__name__,
                  listener.protocol_port, vip.ip_address)
        self.amphoraconfig[(listener.protocol_port,
                            vip.ip_address)] = (listener, vip, 'start')

    def delete(self, listener, vip):
        LOG.debug("Amphora %s no-op, delete listener %s, vip %s",
                  self.__class__.__name__,
                  listener.protocol_port, vip.ip_address)
        self.amphoraconfig[(listener.protocol_port,
                            vip.ip_address)] = (listener, vip, 'delete')

    def get_info(self, amphora):
        LOG.debug("Amphora %s no-op, info amphora %s",
                  self.__class__.__name__, amphora.id)
        self.amphoraconfig[amphora.id] = (amphora.id, 'get_info')

    def get_diagnostics(self, amphora):
        LOG.debug("Amphora %s no-op, get diagnostics amphora %s",
                  self.__class__.__name__, amphora.id)
        self.amphoraconfig[amphora.id] = (amphora.id, 'get_diagnostics')

    def finalize_amphora(self, amphora):
        LOG.debug("Amphora %s no-op, finalize amphora %s",
                  self.__class__.__name__, amphora.id)
        self.amphoraconfig[amphora.id] = (amphora.id, 'finalize amphora')

    def post_network_plug(self, amphora):
        LOG.debug("Amphora %s no-op, post network plug amphora %s",
                  self.__class__.__name__, amphora.id)
        self.amphoraconfig[amphora.id] = (amphora.id, 'post_network_plug')

    def post_vip_plug(self, load_balancer, amphorae_network_config):
        LOG.debug("Amphora %s no-op, post vip plug load balancer %s",
                  self.__class__.__name__, load_balancer.id)
        self.amphoraconfig[(load_balancer.id, id(amphorae_network_config))] = (
            load_balancer.id, amphorae_network_config, 'post_vip_plug')


class NoopAmphoraLoadBalancerDriver(driver_base.AmphoraLoadBalancerDriver):
    def __init__(self):
        super(NoopAmphoraLoadBalancerDriver, self).__init__()
        self.driver = NoopManager()

    def update(self, listener, vip):

        self.driver.update(listener, vip)

    def stop(self, listener, vip):

        self.driver.stop(listener, vip)

    def start(self, listener, vip):

        self.driver.start(listener, vip)

    def delete(self, listener, vip):

        self.driver.delete(listener, vip)

    def get_info(self, amphora):

        self.driver.get_info(amphora)

    def get_diagnostics(self, amphora):

        self.driver.get_diagnostics(amphora)

    def finalize_amphora(self, amphora):

        self.driver.finalize_amphora(amphora)

    def post_network_plug(self, amphora):

        self.driver.post_network_plug(amphora)

    def post_vip_plug(self, load_balancer, amphorae_network_config):

        self.driver.post_vip_plug(load_balancer, amphorae_network_config)
