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
from oslo_utils import uuidutils

from octavia.common import data_models
from octavia.network import base as driver_base
from octavia.network import data_models as network_models

LOG = logging.getLogger(__name__)


class NoopManager(object):
    def __init__(self):
        super(NoopManager, self).__init__()
        self.networkconfigconfig = {}
        self._qos_extension_enabled = True

    def allocate_vip(self, loadbalancer):
        LOG.debug("Network %s no-op, allocate_vip loadbalancer %s",
                  self.__class__.__name__, loadbalancer)
        self.networkconfigconfig[loadbalancer.id] = (
            loadbalancer, 'allocate_vip')
        subnet_id = uuidutils.generate_uuid()
        network_id = uuidutils.generate_uuid()
        port_id = uuidutils.generate_uuid()
        ip_address = '198.51.100.1'
        if loadbalancer.vip:
            subnet_id = loadbalancer.vip.subnet_id or subnet_id
            network_id = loadbalancer.vip.network_id or network_id
            port_id = loadbalancer.vip.port_id or port_id
            ip_address = loadbalancer.vip.ip_address or ip_address
        return data_models.Vip(ip_address=ip_address,
                               subnet_id=subnet_id,
                               network_id=network_id,
                               port_id=port_id,
                               load_balancer_id=loadbalancer.id)

    def deallocate_vip(self, vip):
        LOG.debug("Network %s no-op, deallocate_vip vip %s",
                  self.__class__.__name__, vip.ip_address)
        self.networkconfigconfig[vip.ip_address] = (vip,
                                                    'deallocate_vip')

    def plug_vip(self, loadbalancer, vip):
        LOG.debug("Network %s no-op, plug_vip loadbalancer %s, vip %s",
                  self.__class__.__name__,
                  loadbalancer.id, vip.ip_address)
        self.networkconfigconfig[(loadbalancer.id,
                                  vip.ip_address)] = (loadbalancer, vip,
                                                      'plug_vip')
        amps = []
        for amphora in loadbalancer.amphorae:
            amps.append(data_models.Amphora(
                id=amphora.id,
                compute_id=amphora.compute_id,
                vrrp_ip='198.51.100.1',
                ha_ip='198.51.100.1',
                vrrp_port_id=uuidutils.generate_uuid(),
                ha_port_id=uuidutils.generate_uuid()
            ))
        return amps

    def unplug_vip(self, loadbalancer, vip):
        LOG.debug("Network %s no-op, unplug_vip loadbalancer %s, vip %s",
                  self.__class__.__name__,
                  loadbalancer.id, vip.ip_address)
        self.networkconfigconfig[(loadbalancer.id,
                                  vip.ip_address)] = (loadbalancer, vip,
                                                      'unplug_vip')

    def plug_network(self, compute_id, network_id, ip_address=None):
        LOG.debug("Network %s no-op, plug_network compute_id %s, network_id "
                  "%s, ip_address %s", self.__class__.__name__, compute_id,
                  network_id, ip_address)
        self.networkconfigconfig[(compute_id, network_id, ip_address)] = (
            compute_id, network_id, ip_address, 'plug_network')
        return network_models.Interface(
            id=uuidutils.generate_uuid(),
            compute_id=compute_id,
            network_id=network_id,
            fixed_ips=[],
            port_id=uuidutils.generate_uuid()
        )

    def unplug_network(self, compute_id, network_id, ip_address=None):
        LOG.debug("Network %s no-op, unplug_network compute_id %s, "
                  "network_id %s",
                  self.__class__.__name__, compute_id, network_id)
        self.networkconfigconfig[(compute_id, network_id, ip_address)] = (
            compute_id, network_id, ip_address, 'unplug_network')

    def get_plugged_networks(self, compute_id):
        LOG.debug("Network %s no-op, get_plugged_networks amphora_id %s",
                  self.__class__.__name__, compute_id)
        self.networkconfigconfig[compute_id] = (
            compute_id, 'get_plugged_networks')
        return []

    def update_vip(self, loadbalancer, for_delete=False):
        LOG.debug("Network %s no-op, update_vip loadbalancer %s "
                  "with for delete %s",
                  self.__class__.__name__, loadbalancer, for_delete)
        self.networkconfigconfig[loadbalancer.id] = (
            loadbalancer, for_delete, 'update_vip')

    def get_network(self, network_id):
        LOG.debug("Network %s no-op, get_network network_id %s",
                  self.__class__.__name__, network_id)
        self.networkconfigconfig[network_id] = (network_id, 'get_network')
        network = network_models.Network(id=uuidutils.generate_uuid())

        class ItIsInsideMe(object):
            def __contains__(self, item):
                return True

            def __iter__(self):
                yield uuidutils.generate_uuid()

        network.subnets = ItIsInsideMe()
        return network

    def get_subnet(self, subnet_id):
        LOG.debug("Subnet %s no-op, get_subnet subnet_id %s",
                  self.__class__.__name__, subnet_id)
        self.networkconfigconfig[subnet_id] = (subnet_id, 'get_subnet')
        return network_models.Subnet(id=uuidutils.generate_uuid())

    def get_port(self, port_id):
        LOG.debug("Port %s no-op, get_port port_id %s",
                  self.__class__.__name__, port_id)
        self.networkconfigconfig[port_id] = (port_id, 'get_port')
        return network_models.Port(id=uuidutils.generate_uuid())

    def get_network_by_name(self, network_name):
        LOG.debug("Network %s no-op, get_network_by_name network_name %s",
                  self.__class__.__name__, network_name)
        self.networkconfigconfig[network_name] = (network_name,
                                                  'get_network_by_name')
        return network_models.Network(id=uuidutils.generate_uuid())

    def get_subnet_by_name(self, subnet_name):
        LOG.debug("Subnet %s no-op, get_subnet_by_name subnet_name %s",
                  self.__class__.__name__, subnet_name)
        self.networkconfigconfig[subnet_name] = (subnet_name,
                                                 'get_subnet_by_name')
        return network_models.Subnet(id=uuidutils.generate_uuid())

    def get_port_by_name(self, port_name):
        LOG.debug("Port %s no-op, get_port_by_name port_name %s",
                  self.__class__.__name__, port_name)
        self.networkconfigconfig[port_name] = (port_name, 'get_port_by_name')
        return network_models.Port(id=uuidutils.generate_uuid())

    def get_port_by_net_id_device_id(self, network_id, device_id):
        LOG.debug("Port %s no-op, get_port_by_net_id_device_id network_id %s"
                  " device_id %s",
                  self.__class__.__name__, network_id, device_id)
        self.networkconfigconfig[(network_id, device_id)] = (
            network_id, device_id, 'get_port_by_net_id_device_id')
        return network_models.Port(id=uuidutils.generate_uuid())

    def failover_preparation(self, amphora):
        LOG.debug("failover %s no-op, failover_preparation, amphora id %s",
                  self.__class__.__name__, amphora.id)

    def plug_port(self, amphora, port):
        LOG.debug("Network %s no-op, plug_port amphora.id %s, port_id "
                  "%s", self.__class__.__name__, amphora.id, port.id)
        self.networkconfigconfig[(amphora.id, port.id)] = (
            amphora, port, 'plug_port')

    def get_network_configs(self, loadbalancer):
        LOG.debug("Network %s no-op, get_network_configs loadbalancer id %s ",
                  self.__class__.__name__, loadbalancer.id)
        self.networkconfigconfig[(loadbalancer.id)] = (
            loadbalancer, 'get_network_configs')

        amp_configs = {}
        for amp in loadbalancer.amphorae:
            vrrp_port = self.get_port(amp.vrrp_port_id)
            ha_port = self.get_port(amp.ha_port_id)
            amp_configs[amp.id] = network_models.AmphoraNetworkConfig(
                amphora=amp,
                vip_subnet=self.get_subnet(loadbalancer.vip.subnet_id),
                vip_port=self.get_port(loadbalancer.vip.port_id),
                vrrp_subnet=self.get_subnet(
                    vrrp_port.get_subnet_id(amp.vrrp_ip)),
                vrrp_port=vrrp_port,
                ha_subnet=self.get_subnet(
                    ha_port.get_subnet_id(amp.ha_ip)),
                ha_port=ha_port)
        return amp_configs

    def wait_for_port_detach(self, amphora):
        LOG.debug("failover %s no-op, wait_for_port_detach, amphora id %s",
                  self.__class__.__name__, amphora.id)

    def get_qos_policy(self, qos_policy_id):
        LOG.debug("Qos Policy %s no-op, get_qos_policy qos_policy_id %s",
                  self.__class__.__name__, qos_policy_id)
        self.networkconfigconfig[qos_policy_id] = (qos_policy_id,
                                                   'get_qos_policy')
        return qos_policy_id

    def apply_qos_on_port(self, qos_id, port_id):
        LOG.debug("Network %s no-op, apply_qos_on_port qos_id %s, port_id "
                  "%s", self.__class__.__name__, qos_id, port_id)
        self.networkconfigconfig[(qos_id, port_id)] = (
            qos_id, port_id, 'apply_qos_on_port')

    def qos_enabled(self):
        return self._qos_extension_enabled


class NoopNetworkDriver(driver_base.AbstractNetworkDriver):
    def __init__(self):
        super(NoopNetworkDriver, self).__init__()
        self.driver = NoopManager()

    def allocate_vip(self, loadbalancer):
        return self.driver.allocate_vip(loadbalancer)

    def deallocate_vip(self, vip):
        self.driver.deallocate_vip(vip)

    def plug_vip(self, loadbalancer, vip):
        return self.driver.plug_vip(loadbalancer, vip)

    def unplug_vip(self, loadbalancer, vip):
        self.driver.unplug_vip(loadbalancer, vip)

    def plug_network(self, amphora_id, network_id, ip_address=None):
        return self.driver.plug_network(amphora_id, network_id, ip_address)

    def unplug_network(self, amphora_id, network_id, ip_address=None):
        self.driver.unplug_network(amphora_id, network_id,
                                   ip_address=ip_address)

    def get_plugged_networks(self, amphora_id):
        return self.driver.get_plugged_networks(amphora_id)

    def update_vip(self, loadbalancer, for_delete=False):
        self.driver.update_vip(loadbalancer, for_delete)

    def get_network(self, network_id):
        return self.driver.get_network(network_id)

    def get_subnet(self, subnet_id):
        return self.driver.get_subnet(subnet_id)

    def get_port(self, port_id):
        return self.driver.get_port(port_id)

    def get_qos_policy(self, qos_policy_id):
        return self.driver.get_qos_policy(qos_policy_id)

    def get_network_by_name(self, network_name):
        return self.driver.get_network_by_name(network_name)

    def get_subnet_by_name(self, subnet_name):
        return self.driver.get_subnet_by_name(subnet_name)

    def get_port_by_name(self, port_name):
        return self.driver.get_port_by_name(port_name)

    def get_port_by_net_id_device_id(self, network_id, device_id):
        return self.driver.get_port_by_net_id_device_id(network_id, device_id)

    def failover_preparation(self, amphora):
        self.driver.failover_preparation(amphora)

    def plug_port(self, amphora, port):
        return self.driver.plug_port(amphora, port)

    def get_network_configs(self, loadbalancer):
        return self.driver.get_network_configs(loadbalancer)

    def wait_for_port_detach(self, amphora):
        self.driver.wait_for_port_detach(amphora)

    def apply_qos_on_port(self, qos_id, port_id):
        self.driver.apply_qos_on_port(qos_id, port_id)

    def qos_enabled(self):
        return self.driver.qos_enabled()
