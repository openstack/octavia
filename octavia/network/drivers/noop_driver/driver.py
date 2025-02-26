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

import typing

from oslo_log import log as logging
from oslo_utils import uuidutils
from sqlalchemy import Column
from sqlalchemy import create_engine
from sqlalchemy import delete
from sqlalchemy import event
from sqlalchemy import insert
from sqlalchemy import MetaData
from sqlalchemy import select
from sqlalchemy import String
from sqlalchemy import Table

from octavia.common import constants
from octavia.common import data_models
from octavia.network import base as driver_base
from octavia.network import data_models as network_models

if typing.TYPE_CHECKING:
    from octavia.common import context

LOG = logging.getLogger(__name__)

_NOOP_MANAGER_VARS = {
    'networks': {},
    'subnets': {},
    'ports': {},
    'interfaces': {},
    'current_network': None
}


class NoopManager:

    def __init__(self):
        super().__init__()
        self.networkconfigconfig = {}
        self._qos_extension_enabled = True

        # The controller worker can run with multiple processes, so we
        # need to have a persistent and shared store for the no-op driver.
        self.engine = create_engine('sqlite:////tmp/octavia-network-noop.db')

        # TODO(johnsom) work around pysqlite locking issues per:
        # https://github.com/sqlalchemy/sqlalchemy/discussions/12330
        @event.listens_for(self.engine, "connect")
        def do_connect(dbapi_connection, connection_record):
            # disable pysqlite's emitting of the BEGIN statement entirely.
            # also stops it from emitting COMMIT before any DDL.
            dbapi_connection.isolation_level = None

        @event.listens_for(self.engine, "begin")
        def do_begin(conn):
            conn.exec_driver_sql("BEGIN EXCLUSIVE")

        metadata_obj = MetaData()

        self.interfaces_table = Table(
            'interfaces',
            metadata_obj,
            Column('port_id', String(36)),
            Column('network_id', String(36)),
            Column('compute_id', String(36)),
            Column('vnic_type', String(6)))
        self.fixed_ips_table = Table(
            'fixed_ips',
            metadata_obj,
            Column('port_id', String(36)),
            Column('subnet_id', String(36)),
            Column('ip_address', String(64)))
        metadata_obj.create_all(self.engine)

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
        return_vip = data_models.Vip(ip_address=ip_address,
                                     subnet_id=subnet_id,
                                     network_id=network_id,
                                     port_id=port_id,
                                     load_balancer_id=loadbalancer.id)
        additional_vips = [
            data_models.AdditionalVip(
                ip_address=add_vip.ip_address,
                subnet_id=add_vip.subnet_id,
                network_id=network_id,
                port_id=port_id,
                load_balancer=loadbalancer,
                load_balancer_id=loadbalancer.id)
            for add_vip in loadbalancer.additional_vips]
        return return_vip, additional_vips

    def deallocate_vip(self, vip):
        LOG.debug("Network %s no-op, deallocate_vip vip %s",
                  self.__class__.__name__, vip.ip_address)
        self.networkconfigconfig[vip.ip_address] = (vip,
                                                    'deallocate_vip')

    def update_vip_sg(self, load_balancer, vip):
        LOG.debug("Network %s no-op, update_vip_sg loadbalancer %s, vip %s",
                  self.__class__.__name__,
                  load_balancer.id, vip.ip_address)
        self.networkconfigconfig[(load_balancer.id,
                                  vip.ip_address)] = (load_balancer, vip,
                                                      'update_vip_sg')

    def update_aap_port_sg(self,
                           load_balancer: data_models.LoadBalancer,
                           amphora: data_models.Amphora,
                           vip: data_models.Vip):
        LOG.debug("Network %s no-op, update_aap_port_sg load_balancer %s, "
                  " vip %s, amphora %s", self.__class__.__name__,
                  load_balancer.id, vip.ip_address, amphora)
        self.networkconfigconfig[(amphora.id,
                                  vip.ip_address)] = (load_balancer, vip,
                                                      amphora,
                                                      'update_aap_port_sg')

    def plug_aap_port(self, load_balancer, vip, amphora, subnet):
        LOG.debug("Network %s no-op, plug_aap_port loadbalancer %s, vip %s,"
                  " amphora %s, subnet %s",
                  self.__class__.__name__,
                  load_balancer.id, vip.ip_address, amphora, subnet)
        self.networkconfigconfig[(amphora.id,
                                  vip.ip_address)] = (
            load_balancer, vip, amphora, subnet,
            'plug_aap_port')

        fixed_ips = [network_models.FixedIP(subnet_id=subnet.id,
                                            ip_address=vip.ip_address)]

        port_id = uuidutils.generate_uuid()
        LOG.debug("Network %s no-op, plug_aap_port loadbalancer %s is using "
                  "base port ID %s",
                  self.__class__.__name__,
                  load_balancer.id, port_id)

        # Store the interface information in the no-op DB
        with self.engine.connect() as connection:
            connection.execute(insert(self.interfaces_table).values(
                port_id=port_id, network_id=vip.network_id,
                compute_id=amphora.compute_id,
                vnic_type=constants.VNIC_TYPE_NORMAL))
            for fixed_ip in fixed_ips:
                connection.execute(insert(self.fixed_ips_table).values(
                    port_id=port_id, subnet_id=fixed_ip.subnet_id,
                    ip_address=fixed_ip.ip_address))
            connection.commit()

        return data_models.Amphora(
            id=amphora.id,
            compute_id=amphora.compute_id,
            vrrp_ip='198.51.100.1',
            ha_ip='198.51.100.1',
            vrrp_port_id=port_id,
            ha_port_id=uuidutils.generate_uuid()
        )

    def unplug_vip(self, loadbalancer, vip):
        LOG.debug("Network %s no-op, unplug_vip loadbalancer %s, vip %s",
                  self.__class__.__name__,
                  loadbalancer.id, vip.ip_address)
        self.networkconfigconfig[(loadbalancer.id,
                                  vip.ip_address)] = (loadbalancer, vip,
                                                      'unplug_vip')

    def unplug_aap_port(self, vip, amphora, subnet):
        LOG.debug("Network %s no-op, unplug_aap_port vip %s amp: %s "
                  "subnet: %s",
                  self.__class__.__name__,
                  vip.ip_address, amphora.id, subnet.id)
        self.networkconfigconfig[(amphora.id,
                                  vip.ip_address)] = (vip, amphora, subnet,
                                                      'unplug_aap_port')

    def unplug_network(self, compute_id, network_id):
        LOG.debug("Network %s no-op, unplug_network compute_id %s, "
                  "network_id %s",
                  self.__class__.__name__, compute_id, network_id)
        self.networkconfigconfig[(compute_id, network_id)] = (
            compute_id, network_id, 'unplug_network')

    def get_plugged_networks(self, compute_id):
        LOG.debug("Network %s no-op, get_plugged_networks compute_id %s",
                  self.__class__.__name__, compute_id)
        self.networkconfigconfig[compute_id] = (
            compute_id, 'get_plugged_networks')

        # Retrieve the interfaces from the no-op DB for this compute_id
        interfaces = []
        with self.engine.connect() as connection:
            int_results = connection.execute(
                select(self.interfaces_table)
                .where(self.interfaces_table.c.compute_id == compute_id))
            # Walk through the matching interfaces
            for interface in int_results:
                fixed_ips = []
                # Get the fixed IPs on each interface
                fixed_ip_results = connection.execute(
                    select(self.fixed_ips_table)
                    .where(
                        self.fixed_ips_table.c.port_id == interface.port_id))
                # Build the FixedIP objects for the interface
                for fixed_ip in fixed_ip_results:
                    fixed_ips.append(network_models.FixedIP(
                        subnet_id=fixed_ip.subnet_id,
                        ip_address=fixed_ip.ip_address))
                # Add the interface object to the list
                interfaces.append(network_models.Interface(
                    compute_id=interface.compute_id,
                    network_id=interface.network_id,
                    port_id=interface.port_id, fixed_ips=fixed_ips,
                    vnic_type=interface.vnic_type))
        return interfaces

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
        if network_id in _NOOP_MANAGER_VARS['networks']:
            return _NOOP_MANAGER_VARS['networks'][network_id]

        network = network_models.Network(id=network_id,
                                         port_security_enabled=True)

        class ItIsInsideMe(list):
            known_subnets = None

            def __init__(self, network, parent):
                super().__init__()
                self.network = network
                self.parent = parent
                self.known_subnets = {}

            def to_dict(self, **kwargs):
                return [{}]

            def __contains__(self, item):
                self.known_subnets[item] = self.parent.get_subnet(item)
                self.known_subnets[item].network_id = self.network.id
                return True

            def __len__(self):
                return len(self.known_subnets) + 1

            def __iter__(self):
                yield from self.known_subnets
                subnet = network_models.Subnet(id=uuidutils.generate_uuid(),
                                               network_id=self.network.id)
                self.known_subnets[subnet.id] = subnet
                _NOOP_MANAGER_VARS['subnets'][subnet.id] = subnet
                yield subnet.id

        network.subnets = ItIsInsideMe(network, self)
        _NOOP_MANAGER_VARS['networks'][network_id] = network
        _NOOP_MANAGER_VARS['current_network'] = network_id
        return network

    def get_subnet(self, subnet_id):
        LOG.debug("Subnet %s no-op, get_subnet subnet_id %s",
                  self.__class__.__name__, subnet_id)
        self.networkconfigconfig[subnet_id] = (subnet_id, 'get_subnet')
        if subnet_id in _NOOP_MANAGER_VARS['subnets']:
            return _NOOP_MANAGER_VARS['subnets'][subnet_id]

        subnet = network_models.Subnet(
            id=subnet_id,
            network_id=_NOOP_MANAGER_VARS['current_network'])
        _NOOP_MANAGER_VARS['subnets'][subnet_id] = subnet
        return subnet

    def get_port(self, port_id):
        LOG.debug("Port %s no-op, get_port port_id %s",
                  self.__class__.__name__, port_id)
        self.networkconfigconfig[port_id] = (port_id, 'get_port')
        if port_id in _NOOP_MANAGER_VARS['ports']:
            return _NOOP_MANAGER_VARS['ports'][port_id]

        port = network_models.Port(id=port_id)
        _NOOP_MANAGER_VARS['ports'][port_id] = port
        return port

    def get_security_group_by_id(self, sg_id: str,
                                 context: 'context.RequestContext' = None) -> (
            'network_models.SecurityGroup'):
        LOG.debug("Network %s no-op, get_security_group_by_id %s",
                  self.__class__.__name__, sg_id)
        self.networkconfigconfig[sg_id] = (sg_id, 'get_security_group_by_id')
        return network_models.SecurityGroup(id=sg_id)

    def get_network_by_name(self, network_name):
        LOG.debug("Network %s no-op, get_network_by_name network_name %s",
                  self.__class__.__name__, network_name)
        self.networkconfigconfig[network_name] = (network_name,
                                                  'get_network_by_name')
        by_name = {n.name: n for n in _NOOP_MANAGER_VARS['networks'].values()}
        if network_name in by_name:
            return by_name[network_name]

        network = network_models.Network(id=uuidutils.generate_uuid(),
                                         port_security_enabled=True,
                                         name=network_name)
        _NOOP_MANAGER_VARS['networks'][network.id] = network
        _NOOP_MANAGER_VARS['current_network'] = network.id
        return network

    def get_subnet_by_name(self, subnet_name):
        LOG.debug("Subnet %s no-op, get_subnet_by_name subnet_name %s",
                  self.__class__.__name__, subnet_name)
        self.networkconfigconfig[subnet_name] = (subnet_name,
                                                 'get_subnet_by_name')
        by_name = {s.name: s for s in _NOOP_MANAGER_VARS['subnets'].values()}
        if subnet_name in by_name:
            return by_name[subnet_name]

        subnet = network_models.Subnet(
            id=uuidutils.generate_uuid(),
            name=subnet_name,
            network_id=_NOOP_MANAGER_VARS['current_network'])
        _NOOP_MANAGER_VARS['subnets'][subnet.id] = subnet
        return subnet

    def get_port_by_name(self, port_name):
        LOG.debug("Port %s no-op, get_port_by_name port_name %s",
                  self.__class__.__name__, port_name)
        self.networkconfigconfig[port_name] = (port_name, 'get_port_by_name')
        by_name = {p.name: p for p in _NOOP_MANAGER_VARS['ports'].values()}
        if port_name in by_name:
            return by_name[port_name]

        port = network_models.Port(id=uuidutils.generate_uuid(),
                                   name=port_name)
        _NOOP_MANAGER_VARS['ports'][port.id] = port
        return port

    def get_port_by_net_id_device_id(self, network_id, device_id):
        LOG.debug("Port %s no-op, get_port_by_net_id_device_id network_id %s"
                  " device_id %s",
                  self.__class__.__name__, network_id, device_id)
        self.networkconfigconfig[(network_id, device_id)] = (
            network_id, device_id, 'get_port_by_net_id_device_id')
        by_net_dev_id = {(p.network_id, p.device_id): p
                         for p in _NOOP_MANAGER_VARS['ports'].values()}
        if (network_id, device_id) in by_net_dev_id:
            return by_net_dev_id[(network_id, device_id)]

        port = network_models.Port(id=uuidutils.generate_uuid(),
                                   network_id=network_id,
                                   device_id=device_id)
        _NOOP_MANAGER_VARS['ports'][port.id] = port
        return port

    def get_security_group(self, sg_name):
        LOG.debug("Network %s no-op, get_security_group name %s",
                  self.__class__.__name__, sg_name)
        self.networkconfigconfig[(sg_name)] = (sg_name, 'get_security_group')
        return network_models.SecurityGroup(id=uuidutils.generate_uuid())

    def failover_preparation(self, amphora):
        LOG.debug("failover %s no-op, failover_preparation, amphora id %s",
                  self.__class__.__name__, amphora.id)

    def plug_port(self, amphora, port):
        LOG.debug("Network %s no-op, plug_port amphora.id %s, port_id "
                  "%s", self.__class__.__name__, amphora.id, port.id)
        self.networkconfigconfig[(amphora.id, port.id)] = (
            amphora, port, 'plug_port')

    def _get_amp_net_configs(self, amp, amp_configs, vip_subnet, vip_port):
        vrrp_port = self.get_port(amp.vrrp_port_id)
        ha_port = self.get_port(amp.ha_port_id)
        amp_configs[amp.id] = network_models.AmphoraNetworkConfig(
            amphora=amp,
            vrrp_subnet=self.get_subnet(
                vrrp_port.get_subnet_id(amp.vrrp_ip)),
            vrrp_port=vrrp_port,
            ha_subnet=self.get_subnet(
                ha_port.get_subnet_id(amp.ha_ip)),
            ha_port=ha_port)

    def get_network_configs(self, loadbalancer, amphora=None):
        amphora_id = amphora.id if amphora else None
        LOG.debug("Network %s no-op, get_network_configs loadbalancer id "
                  "%s amphora id: %s", self.__class__.__name__,
                  loadbalancer.id, amphora_id)
        self.networkconfigconfig[(loadbalancer.id)] = (
            loadbalancer, 'get_network_configs')
        vip_subnet = self.get_subnet(loadbalancer.vip.subnet_id)
        vip_port = self.get_port(loadbalancer.vip.port_id)

        amp_configs = {}
        if amphora:
            self._get_amp_net_configs(amphora, amp_configs,
                                      vip_subnet, vip_port)
        else:
            for amp in loadbalancer.amphorae:
                self._get_amp_net_configs(amp, amp_configs,
                                          vip_subnet, vip_port)

        return amp_configs

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

    def get_network_ip_availability(self, network):
        LOG.debug("Network %s no-op, network_ip_availability network_id %s",
                  self.__class__.__name__, network.id)
        self.networkconfigconfig[(network.id, 'ip_availability')] = (
            network.id, 'get_network_ip_availability')
        ip_avail = network_models.Network_IP_Availability(
            network_id=network.id)
        subnet_ip_availability = []
        for subnet_id in list(network.subnets):
            subnet_ip_availability.append({'subnet_id': subnet_id,
                                          'used_ips': 0, 'total_ips': 254})
        ip_avail.subnet_ip_availability = subnet_ip_availability
        return ip_avail

    def delete_port(self, port_id):
        LOG.debug("Network %s no-op, delete_port port_id %s",
                  self.__class__.__name__, port_id)
        self.networkconfigconfig[port_id] = (port_id, 'delete_port')

        # Remove the port from the no-op DB
        with self.engine.connect() as connection:
            connection.execute(delete(self.interfaces_table)
                               .where(
                                   self.interfaces_table.c.port_id == port_id))
            connection.execute(delete(self.fixed_ips_table)
                               .where(
                                   self.fixed_ips_table.c.port_id == port_id))
            connection.commit()

    def set_port_admin_state_up(self, port_id, state):
        LOG.debug("Network %s no-op, set_port_admin_state_up port_id %s, "
                  "state %s", self.__class__.__name__, port_id, state)
        self.networkconfigconfig[(port_id, state)] = (port_id, state,
                                                      'admin_down_port')

    def create_port(self, network_id, name=None, fixed_ips=(),
                    secondary_ips=(), security_group_ids=(),
                    admin_state_up=True, qos_policy_id=None,
                    vnic_type=constants.VNIC_TYPE_NORMAL):
        LOG.debug("Network %s no-op, create_port network_id %s",
                  self.__class__.__name__, network_id)
        if not name:
            name = 'no-op-port'
        port_id = uuidutils.generate_uuid()
        project_id = uuidutils.generate_uuid()

        fixed_ip_obj_list = []
        for fixed_ip in fixed_ips:
            if fixed_ip and not fixed_ip.get('ip_address'):
                fixed_ip_obj_list.append(
                    network_models.FixedIP(subnet_id=fixed_ip.get('subnet_id'),
                                           ip_address='198.51.100.56'))
            else:
                fixed_ip_obj_list.append(
                    network_models.FixedIP(
                        subnet_id=fixed_ip.get('subnet_id'),
                        ip_address=fixed_ip.get('ip_address')))
        if not fixed_ip_obj_list:
            fixed_ip_obj_list = [network_models.FixedIP(
                subnet_id=uuidutils.generate_uuid(),
                ip_address='198.51.100.56')]

        self.networkconfigconfig[(network_id, 'create_port')] = (
            network_id, name, fixed_ip_obj_list, secondary_ips,
            security_group_ids, admin_state_up, qos_policy_id, vnic_type)

        # Store the interface information in the no-op DB
        with self.engine.connect() as connection:
            connection.execute(insert(self.interfaces_table).values(
                port_id=port_id, network_id=network_id, vnic_type=vnic_type))
            for fixed_ip in fixed_ip_obj_list:
                connection.execute(insert(self.fixed_ips_table).values(
                    port_id=port_id, subnet_id=fixed_ip.subnet_id,
                    ip_address=fixed_ip.ip_address))
            connection.commit()

        return network_models.Port(
            id=port_id, name=name, device_id='no-op-device-id',
            device_owner='Octavia', mac_address='00:00:5E:00:53:05',
            network_id=network_id, status='UP', project_id=project_id,
            admin_state_up=admin_state_up, fixed_ips=fixed_ip_obj_list,
            qos_policy_id=qos_policy_id, security_group_ids=security_group_ids,
            vnic_type=vnic_type)

    def plug_fixed_ip(self, port_id, subnet_id, ip_address=None):
        LOG.debug("Network %s no-op, plug_fixed_ip port_id %s, subnet_id "
                  "%s, ip_address %s", self.__class__.__name__, port_id,
                  subnet_id, ip_address)
        self.networkconfigconfig[(port_id, subnet_id)] = (
            port_id, subnet_id, ip_address, 'plug_fixed_ip')

        port = network_models.Port(id=port_id,
                                   network_id=uuidutils.generate_uuid())
        _NOOP_MANAGER_VARS['ports'][port.id] = port
        return port

    def unplug_fixed_ip(self, port_id, subnet_id):
        LOG.debug("Network %s no-op, unplug_fixed_ip port_id %s, subnet_id "
                  "%s", self.__class__.__name__, port_id,
                  subnet_id)
        self.networkconfigconfig[(port_id, subnet_id)] = (
            port_id, subnet_id, 'unplug_fixed_ip')

        return _NOOP_MANAGER_VARS['ports'].pop(port_id, None)


class NoopNetworkDriver(driver_base.AbstractNetworkDriver):
    def __init__(self):
        super().__init__()
        self.driver = NoopManager()

    def allocate_vip(self, loadbalancer):
        return self.driver.allocate_vip(loadbalancer)

    def deallocate_vip(self, vip):
        self.driver.deallocate_vip(vip)

    def unplug_vip(self, loadbalancer, vip):
        self.driver.unplug_vip(loadbalancer, vip)

    def unplug_network(self, compute_id, network_id):
        self.driver.unplug_network(compute_id, network_id)

    def get_plugged_networks(self, compute_id):
        return self.driver.get_plugged_networks(compute_id)

    def update_vip(self, loadbalancer, for_delete=False):
        self.driver.update_vip(loadbalancer, for_delete)

    def get_network(self, network_id, context=None):
        return self.driver.get_network(network_id)

    def get_subnet(self, subnet_id, context=None):
        return self.driver.get_subnet(subnet_id)

    def get_port(self, port_id, context=None):
        return self.driver.get_port(port_id)

    def get_security_group_by_id(self, sg_id: str,
                                 context: 'context.RequestContext' = None) -> (
            'network_models.SecurityGroup'):
        return self.driver.get_security_group_by_id(sg_id, context=context)

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

    def get_security_group(self, sg_name):
        return self.driver.get_security_group(sg_name)

    def failover_preparation(self, amphora):
        self.driver.failover_preparation(amphora)

    def plug_port(self, amphora, port):
        return self.driver.plug_port(amphora, port)

    def get_network_configs(self, loadbalancer, amphora=None):
        return self.driver.get_network_configs(loadbalancer, amphora)

    def apply_qos_on_port(self, qos_id, port_id):
        self.driver.apply_qos_on_port(qos_id, port_id)

    def update_vip_sg(self, load_balancer, vip):
        self.driver.update_vip_sg(load_balancer, vip)

    def update_aap_port_sg(self,
                           load_balancer: data_models.LoadBalancer,
                           amphora: data_models.Amphora,
                           vip: data_models.Vip):
        self.driver.update_aap_port_sg(load_balancer, amphora, vip)

    def plug_aap_port(self, load_balancer, vip, amphora, subnet):
        return self.driver.plug_aap_port(load_balancer, vip, amphora, subnet)

    def unplug_aap_port(self, vip, amphora, subnet):
        self.driver.unplug_aap_port(vip, amphora, subnet)

    def qos_enabled(self):
        return self.driver.qos_enabled()

    def get_network_ip_availability(self, network):
        return self.driver.get_network_ip_availability(network)

    def delete_port(self, port_id):
        self.driver.delete_port(port_id)

    def set_port_admin_state_up(self, port_id, state):
        self.driver.set_port_admin_state_up(port_id, state)

    def create_port(self, network_id, name=None, fixed_ips=(),
                    secondary_ips=(), security_group_ids=(),
                    admin_state_up=True, qos_policy_id=None,
                    vnic_type=constants.VNIC_TYPE_NORMAL):
        return self.driver.create_port(
            network_id, name, fixed_ips, secondary_ips, security_group_ids,
            admin_state_up, qos_policy_id, vnic_type)

    def plug_fixed_ip(self, port_id, subnet_id, ip_address=None):
        return self.driver.plug_fixed_ip(port_id, subnet_id, ip_address)

    def unplug_fixed_ip(self, port_id, subnet_id):
        return self.driver.unplug_fixed_ip(port_id, subnet_id)
