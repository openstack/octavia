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

from octavia.amphorae.drivers import driver_base

LOG = logging.getLogger(__name__)


class LoggingUpdate(object):
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

    def update_amphora_listeners(self, listeners, amphora_index,
                                 amphorae, timeout_dict):
        amphora_id = amphorae[amphora_index].id
        for listener in listeners:
            LOG.debug("Amphora noop driver update_amphora_listeners, "
                      "listener %s, amphora %s, timeouts %s", listener.id,
                      amphora_id, timeout_dict)
            self.amphoraconfig[(listener.id, amphora_id)] = (
                listener, amphora_id, timeout_dict, "update_amp")

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

    def post_network_plug(self, amphora, port):
        LOG.debug("Amphora %s no-op, post network plug amphora %s, port %s",
                  self.__class__.__name__, amphora.id, port.id)
        self.amphoraconfig[amphora.id, port.id] = (amphora.id, port.id,
                                                   'post_network_plug')

    def post_vip_plug(self, amphora, load_balancer, amphorae_network_config):
        LOG.debug("Amphora %s no-op, post vip plug load balancer %s",
                  self.__class__.__name__, load_balancer.id)
        self.amphoraconfig[(load_balancer.id, id(amphorae_network_config))] = (
            load_balancer.id, amphorae_network_config, 'post_vip_plug')

    def upload_cert_amp(self, amphora, pem_file):
        LOG.debug("Amphora %s no-op, upload cert amphora %s,with pem fle %s",
                  self.__class__.__name__, amphora.id, pem_file)
        self.amphoraconfig[amphora.id, pem_file] = (amphora.id, pem_file,
                                                    'update_amp_cert_file')


class NoopAmphoraLoadBalancerDriver(
    driver_base.AmphoraLoadBalancerDriver,
        driver_base.VRRPDriverMixin):
    def __init__(self):
        super(NoopAmphoraLoadBalancerDriver, self).__init__()
        self.driver = NoopManager()

    def update_amphora_listeners(self, listeners, amphora_index,
                                 amphorae, timeout_dict):

        self.driver.update_amphora_listeners(listeners, amphora_index,
                                             amphorae, timeout_dict)

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

    def post_network_plug(self, amphora, port):

        self.driver.post_network_plug(amphora, port)

    def post_vip_plug(self, amphora, load_balancer, amphorae_network_config):

        self.driver.post_vip_plug(amphora,
                                  load_balancer, amphorae_network_config)

    def upload_cert_amp(self, amphora, pem_file):

        self.driver.upload_cert_amp(amphora, pem_file)

    def update_vrrp_conf(self, loadbalancer):
        pass

    def stop_vrrp_service(self, loadbalancer):
        pass

    def start_vrrp_service(self, loadbalancer):
        pass

    def reload_vrrp_service(self, loadbalancer):
        pass

    def get_vrrp_interface(self, amphora):
        pass
