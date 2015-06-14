#    Copyright 2014 Rackspace
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from neutronclient.common import exceptions as neutron_client_exceptions
from neutronclient.neutron import client as neutron_client
from novaclient import client as nova_client
from novaclient import exceptions as nova_client_exceptions
from oslo_log import log as logging

from octavia.common import data_models
from octavia.common import keystone
from octavia.i18n import _LE, _LI
from octavia.network import base
from octavia.network import data_models as network_models


LOG = logging.getLogger(__name__)
NEUTRON_VERSION = '2.0'
NOVA_VERSION = '2'
AAP_EXT_ALIAS = 'allowed-address-pairs'
SEC_GRP_EXT_ALIAS = 'security-group'
VIP_SECURITY_GRP_PREFIX = 'lb-'


class AllowedAddressPairsDriver(base.AbstractNetworkDriver):

    def __init__(self):
        self.sec_grp_enabled = True
        self.neutron_client = neutron_client.Client(
            NEUTRON_VERSION, session=keystone.get_session())
        self._check_extensions_loaded()
        self.nova_client = nova_client.Client(
            NOVA_VERSION, session=keystone.get_session())

    def _check_extensions_loaded(self):
        extensions = self.neutron_client.list_extensions()
        extensions = extensions.get('extensions')
        aliases = [ext.get('alias') for ext in extensions]
        if AAP_EXT_ALIAS not in aliases:
            raise base.NetworkException(
                'The {alias} extension is not enabled in neutron.  This '
                'driver cannot be used with the {alias} extension '
                'disabled.'.format(alias=AAP_EXT_ALIAS))
        if SEC_GRP_EXT_ALIAS not in aliases:
            LOG.info(_LI('Neutron security groups are disabled.  This driver'
                         'will not manage any security groups.'))
            self.sec_grp_enabled = False

    def _port_to_vip(self, port, load_balancer_id=None):
        port = port['port']
        ip_address = port['fixed_ips'][0]['ip_address']
        network_id = port['network_id']
        port_id = port['id']
        return data_models.Vip(ip_address=ip_address,
                               network_id=network_id,
                               port_id=port_id,
                               load_balancer_id=load_balancer_id)

    def _nova_interface_to_octavia_interface(self, amphora_id, nova_interface):
        ip_address = nova_interface.fixed_ips[0]['ip_address']
        return network_models.Interface(amphora_id=amphora_id,
                                        network_id=nova_interface.net_id,
                                        port_id=nova_interface.port_id,
                                        ip_address=ip_address)

    def _get_interfaces_to_unplug(self, interfaces, network_id,
                                  ip_address=None):
        ret = []
        for interface_ in interfaces:
            if interface_.net_id == network_id:
                if ip_address:
                    for fixed_ip in interface_.fixed_ips:
                        if ip_address == fixed_ip.get('ip_address'):
                            ret.append(interface_)
                else:
                    ret.append(interface_)
        return ret

    def _get_plugged_interface(self, compute_id, network_id):
        interfaces = self.get_plugged_networks(compute_id)
        for interface in interfaces:
            if interface.network_id == network_id:
                return interface

    def _plug_amphora_vip(self, compute_id, network_id):
        try:
            interface = self.plug_network(compute_id, network_id)
        except Exception:
            message = _LE('Error plugging amphora (compute_id: {compute_id}) '
                          'into vip network {network_id}.').format(
                              compute_id=compute_id,
                              network_id=network_id)
            LOG.exception(message)
            raise base.PlugVIPException(message)
        return interface

    def _add_vip_address_pair(self, port_id, vip_address):
        try:
            aap = {
                'port': {
                    'allowed_address_pairs': [
                        {'ip_address': vip_address}
                    ]
                }
            }
            self.neutron_client.update_port(port_id, aap)
        except neutron_client_exceptions.PortNotFoundClient as e:
                raise base.PortNotFound(e.message)
        except Exception:
            message = _LE('Error adding allowed address pair {ip} '
                          'to port {port_id}.').format(ip=vip_address,
                                                       port_id=port_id)
            LOG.exception(message)
            raise base.PlugVIPException(message)

    def _get_lb_security_group(self, load_balancer_id):
        sec_grp_name = VIP_SECURITY_GRP_PREFIX + load_balancer_id
        sec_grps = self.neutron_client.list_security_groups(name=sec_grp_name)
        if len(sec_grps.get('security_groups')):
            return sec_grps.get('security_groups')[0]

    def _update_security_group_rules(self, load_balancer, sec_grp_id):
        rules = self.neutron_client.list_security_group_rules(
            security_group_id=sec_grp_id)
        updated_ports = [listener.protocol_port
                         for listener in load_balancer.listeners]
        # Just going to use port_range_max for now because we can assume that
        # port_range_max and min will be the same since this driver is
        # responsible for creating these rules
        old_ports = [rule.get('port_range_max')
                     for rule in rules.get('security_group_rules', [])]
        add_ports = set(updated_ports) - set(old_ports)
        del_ports = set(old_ports) - set(updated_ports)
        for rule in rules.get('security_group_rules', []):
            if rule.get('port_range_max') in del_ports:
                self.neutron_client.delete_security_group_rule(rule.get('id'))

        for port in add_ports:
            rule = {
                'security_group_rule': {
                    'security_group_id': sec_grp_id,
                    'direction': 'ingress',
                    'protocol': 'TCP',
                    'port_range_min': port,
                    'port_range_max': port
                }
            }
            self.neutron_client.create_security_group_rule(rule)

    def _update_vip_security_group(self, load_balancer, vip):
        sec_grp = self._get_lb_security_group(load_balancer.id)
        if not sec_grp:
            sec_grp_name = VIP_SECURITY_GRP_PREFIX + load_balancer.id
            new_sec_grp = {'security_group': {'name': sec_grp_name}}
            sec_grp = self.neutron_client.create_security_group(new_sec_grp)
            sec_grp = sec_grp['security_group']
        self._update_security_group_rules(load_balancer, sec_grp.get('id'))
        port_update = {'port': {'security_groups': [sec_grp.get('id')]}}
        try:
            self.neutron_client.update_port(vip.port_id, port_update)
        except neutron_client_exceptions.PortNotFoundClient as e:
            raise base.PortNotFound(e.message)
        except Exception as e:
            raise base.PlugVIPException(e.message)

    def _add_vip_security_group_to_amphorae(self, load_balancer_id, amphora):
        sec_grp = self._get_lb_security_group(load_balancer_id)
        self.nova_client.servers.add_security_group(
            amphora.compute_id, sec_grp.get('id'))

    def _map_network_to_data_model(self, network):
        nw = network.get('network')
        return network_models.Network(
            id=nw.get('id'), name=nw.get('name'), subnets=nw.get('subnets'),
            tenant_id=nw.get('tenant_id'),
            admin_state_up=nw.get('admin_state_up'), mtu=nw.get('mtu'),
            provider_network_type=nw.get('provider:network_type'),
            provider_physical_network=nw.get('provider:physical_network'),
            provider_segmentation_id=nw.get('provider:segmentation_id'),
            router_external=nw.get('router:external'))

    def deallocate_vip(self, vip):
        port = self.neutron_client.show_port(vip.port_id)
        admin_tenant_id = keystone.get_session().get_project_id()
        if port.get('port').get('tenant_id') != admin_tenant_id:
            LOG.info(_LI("Port {0} will not be deleted by Octavia as it was "
                         "not created by Octavia.").format(vip.port_id))
            return
        try:
            self.neutron_client.delete_port(vip.port_id)
        except neutron_client_exceptions.PortNotFoundClient as e:
            raise base.VIPConfigurationNotFound(e.message)
        except Exception:
            message = _LE('Error deleting VIP port_id {port_id} from '
                          'neutron').format(port_id=vip.port_id)
            LOG.exception(message)
            raise base.DeallocateVIPException(message)

    def plug_vip(self, load_balancer, vip):
        if self.sec_grp_enabled:
            self._update_vip_security_group(load_balancer, vip)
        plugged_amphorae = []
        for amphora in load_balancer.amphorae:
            interface = self._get_plugged_interface(amphora.compute_id,
                                                    vip.network_id)
            if not interface:
                interface = self._plug_amphora_vip(amphora.compute_id,
                                                   vip.network_id)
            self._add_vip_address_pair(interface.port_id, vip.ip_address)
            if self.sec_grp_enabled:
                self._add_vip_security_group_to_amphorae(
                    load_balancer.id, amphora)
            plugged_amphorae.append(data_models.Amphora(
                id=amphora.id,
                compute_id=amphora.compute_id,
                vrrp_ip=interface.ip_address,
                ha_ip=vip.ip_address))
        return plugged_amphorae

    def allocate_vip(self, load_balancer):
        if not load_balancer.vip.port_id and not load_balancer.vip.network_id:
            raise base.AllocateVIPException('Cannot allocate a vip '
                                            'without a port_id or '
                                            'a network_id.')
        if load_balancer.vip.port_id:
            LOG.info(_LI('Port {port_id} already exists. Nothing to be '
                         'done.').format(port_id=load_balancer.vip.port_id))
            try:
                port = self.neutron_client.show_port(load_balancer.vip.port_id)
            except neutron_client_exceptions.PortNotFoundClient as e:
                raise base.PortNotFound(e.message)
            except Exception:
                message = _LE('Error retrieving info about port '
                              '{port_id}.').format(
                    port_id=load_balancer.vip.port_id)
                LOG.exception(message)
                raise base.AllocateVIPException(message)
            return self._port_to_vip(port)

        # It can be assumed that network_id exists
        port = {'port': {'name': 'octavia-lb-' + load_balancer.id,
                         'network_id': load_balancer.vip.network_id,
                         'admin_state_up': False,
                         'device_id': '',
                         'device_owner': ''}}
        try:
            new_port = self.neutron_client.create_port(port)
        except neutron_client_exceptions.NetworkNotFoundClient as e:
            raise base.NetworkNotFound(e.message)
        except Exception:
            message = _LE('Error creating neutron port on network '
                          '{network_id}.').format(
                network_id=load_balancer.vip.network_id)
            LOG.exception(message)
            raise base.AllocateVIPException(message)
        return self._port_to_vip(new_port)

    def unplug_vip(self, load_balancer, vip):
        for amphora in load_balancer.amphorae:
            interface = self._get_plugged_interface(amphora.compute_id,
                                                    vip.network_id)
            if not interface:
                # Thought about raising PluggedVIPNotFound exception but
                # then that wouldn't evaluate all amphorae, so just continue
                continue
            try:
                self.unplug_network(amphora.compute_id, vip.network_id)
            except Exception:
                pass
            try:
                aap_update = {'port': {
                    'allowed_address_pairs': []
                }}
                self.neutron_client.update_port(interface.port_id,
                                                aap_update)
            except Exception:
                message = _LE('Error unplugging VIP. Could not clear '
                              'allowed address pairs from port '
                              '{port_id}.').format(port_id=vip.port_id)
                LOG.exception(message)
                raise base.UnplugVIPException(message)

    def plug_network(self, compute_id, network_id, ip_address=None):
        try:
            interface_ = self.nova_client.servers.interface_attach(
                server=compute_id, net_id=network_id, fixed_ip=ip_address,
                port_id=None)
        except nova_client_exceptions.NotFound as e:
            if 'Instance' in e.message:
                raise base.AmphoraNotFound(e.message)
            if 'Network' in e.message:
                raise base.NetworkNotFound(e.message)
        except Exception:
            message = _LE('Error plugging amphora (compute_id: {compute_id}) '
                          'into network {network_id}.').format(
                              compute_id=compute_id,
                              network_id=network_id)
            LOG.exception(message)
            raise base.PlugNetworkException(message)

        return self._nova_interface_to_octavia_interface(compute_id,
                                                         interface_)

    def get_plugged_networks(self, amphora_id):
        try:
            interfaces = self.nova_client.servers.interface_list(
                server=amphora_id)
        except Exception:
            message = _LE('Error retrieving plugged networks for amphora '
                          '{amphora_id}.').format(amphora_id=amphora_id)
            LOG.exception(message)
            raise base.NetworkException(message)
        return [self._nova_interface_to_octavia_interface(
                amphora_id, interface_) for interface_ in interfaces]

    def unplug_network(self, compute_id, network_id, ip_address=None):
        try:
            interfaces = self.nova_client.servers.interface_list(
                server=compute_id)
        except nova_client_exceptions.NotFound as e:
            raise base.AmphoraNotFound(e.message)
        except Exception:
            message = _LE('Error retrieving nova interfaces for amphora '
                          '(compute_id: {compute_id}) on network {network_id} '
                          'with ip {ip_address}.').format(
                compute_id=compute_id,
                network_id=network_id,
                ip_address=ip_address)
            LOG.exception(message)
            raise base.NetworkException(message)
        unpluggers = self._get_interfaces_to_unplug(interfaces, network_id,
                                                    ip_address=ip_address)
        try:
            for index, unplugger in enumerate(unpluggers):
                self.nova_client.servers.interface_detach(
                    server=compute_id, port_id=unplugger.port_id)
        except Exception:
            message = _LE('Error unplugging amphora {amphora_id} from network '
                          '{network_id}.').format(amphora_id=compute_id,
                                                  network_id=network_id)
            if len(unpluggers) > 1:
                message = _LE('{base} Other interfaces have been successfully '
                              'unplugged: ').format(base=message)
                unpluggeds = unpluggers[:index]
                for unplugged in unpluggeds:
                    message = _LE('{base} neutron port '
                                  '{port_id} ').format(
                                      base=message, port_id=unplugged.port_id)
            else:
                message = _LE('{base} No other networks were '
                              'unplugged.').format(base=message)
            LOG.exception(message)
            raise base.UnplugNetworkException(message)

    def update_vip(self, load_balancer):
        sec_grp = self._get_lb_security_group(load_balancer.id)
        self._update_security_group_rules(load_balancer, sec_grp.get('id'))

    def get_network(self, network_id=None, subnet_id=None):
        network = None
        try:
            if network_id:
                network = self.neutron_client.show_network(network_id)
            elif subnet_id:
                subnet = (self.neutron_client.show_subnet(subnet_id)
                          .get('subnet').get('network_id'))
                network = self.neutron_client.show_network(subnet)
        except base.NetworkNotFound:
            message = _LE('Network not found '
                          '(network id: {network_id} '
                          'and subnet id: {subnet_id}.').format(
                network_id=network_id,
                subnet_id=subnet_id)
            LOG.exception(message)
            raise base.NetworkNotFound(message)
        except Exception:
            message = _LE('Error retrieving network '
                          '(network id: {network_id} '
                          'and subnet id: {subnet_id}.').format(
                network_id=network_id,
                subnet_id=subnet_id)
            LOG.exception(message)
            raise base.NetworkException(message)

        return self._map_network_to_data_model(network)
