# Copyright 2014,  Author: Min Wang,German Eichberger
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

from octavia.amphorae.drivers import driver_base as driver_base
from octavia.openstack.common import log as logging

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

    def disable(self, listener, vip):
        LOG.debug("Amphora %s no-op, suspend listener %s, vip %s",
                  self.__class__.__name__,
                  listener.protocol_port, vip.ip_address)
        self.amphoraconfig[(listener.protocol_port,
                            vip.ip_address)] = (listener, vip, 'disable')

    def delete(self, listener, vip):
        LOG.debug("Amphora %s no-op, delete listener %s, vip %s",
                  self.__class__.__name__,
                  listener.protocol_port, vip.ip_address)
        self.amphoraconfig[(listener.protocol_port,
                            vip.ip_address)] = (listener, vip, 'delete')

    def enable(self, listener, vip):
        LOG.debug("Amphora %s no-op, enable listener %s, vip %s",
                  self.__class__.__name__,
                  listener.protocol_port, vip.ip_address)
        self.amphoraconfig[(listener.protocol_port,
                            vip.ip_address)] = (listener, vip, 'enable')

    def info(self, amphora):
        LOG.debug("Amphora %s no-op, info amphora %s",
                  self.__class__.__name__, amphora.id)
        self.amphoraconfig[amphora.id] = (amphora.id, 'info')

    def get_metrics(self, amphora):
        LOG.debug("Amphora %s no-op, get metrics amphora %s",
                  self.__class__.__name__, amphora.id)
        self.amphoraconfig[amphora.id] = (amphora.id, 'get_metrics')

    def get_health(self, amphora):
        LOG.debug("Amphora %s no-op, get health amphora %s",
                  self.__class__.__name__, amphora.id)
        self.amphoraconfig[amphora.id] = (amphora.id, 'get_health')

    def get_diagnostics(self, amphora):
        LOG.debug("Amphora %s no-op, get diagnostics amphora %s",
                  self.__class__.__name__, amphora.id)
        self.amphoraconfig[amphora.id] = (amphora.id, 'get_diagnostics')


class NoopAmphoraLoadBalancerDriver(driver_base.AmphoraLoadBalancerDriver):
    def __init__(self, log):
        super(NoopAmphoraLoadBalancerDriver, self).__init__()
        self.log = log
        self.driver = NoopManager()

    def get_logger(self):

        raise NotImplementedError

    def update(self, listener, vip):

        self.driver.update(listener, vip)

    def disable(self, listener, vip):

        self.driver.disable(listener, vip)

    def enable(self, listener, vip):

        self.driver.enable(listener, vip)

    def delete(self, listener, vip):

        self.driver.delete(listener, vip)

    def info(self, amphora):

        self.driver.info(amphora)

    def get_metrics(self, amphora):

        self.driver.get_metrics(amphora)

    def get_health(self, amphora):

        self.driver.get_health(amphora)

    def get_diagnostics(self, amphora):

        self.driver.get_diagnostics(amphora)