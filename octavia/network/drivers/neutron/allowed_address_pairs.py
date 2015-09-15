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

import time

from neutronclient.common import exceptions as neutron_client_exceptions
from novaclient import exceptions as nova_client_exceptions
from oslo_config import cfg
from oslo_log import log as logging

from octavia.common import clients
from octavia.common import constants
from octavia.common import data_models
from octavia.i18n import _LE, _LI, _LW
from octavia.network import base
from octavia.network.drivers.neutron import base as neutron_base
from octavia.network.drivers.neutron import utils


LOG = logging.getLogger(__name__)
AAP_EXT_ALIAS = 'allowed-address-pairs'
VIP_SECURITY_GRP_PREFIX = 'lb-'
OCTAVIA_OWNER = 'Octavia'


class AllowedAddressPairsDriver(neutron_base.BaseNeutronDriver):

    def __init__(self, region=None):
        super(AllowedAddressPairsDriver, self).__init__(region=region)
        self._check_aap_loaded()
        self.nova_client = clients.NovaAuth.get_nova_client(region)

    def _check_aap_loaded(self):
        aliases = [ext.get('alias') for ext in self._extensions]
        if AAP_EXT_ALIAS not in aliases:
            raise base.NetworkException(
                'The {alias} extension is not enabled in neutron.  This '
                'driver cannot be used with the {alias} extension '
                'disabled.'.format(alias=AAP_EXT_ALIAS))

    def _get_interfaces_to_unplug(self, interfaces, network_id,
                                  ip_address=None):
        ret = []
        for interface in interfaces:
            if interface.network_id == network_id:
                if ip_address:
                    for fixed_ip in interface.fixed_ips:
                        if ip_address == fixed_ip.ip_address:
                            ret.append(interface)
                else:
                    ret.append(interface)
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
            self._add_allowed_address_pair_to_port(port_id, vip_address)
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
        if sec_grps and sec_grps.get('security_groups'):
            return sec_grps.get('security_groups')[0]

    def _update_security_group_rules(self, load_balancer, sec_grp_id):
        rules = self.neutron_client.list_security_group_rules(
            security_group_id=sec_grp_id)
        updated_ports = [
            listener.protocol_port for listener in load_balancer.listeners
            if listener.provisioning_status != constants.PENDING_DELETE]
        # Just going to use port_range_max for now because we can assume that
        # port_range_max and min will be the same since this driver is
        # responsible for creating these rules
        old_ports = [rule.get('port_range_max')
                     for rule in rules.get('security_group_rules', [])
                     if rule.get('direction') != 'egress']
        add_ports = set(updated_ports) - set(old_ports)
        del_ports = set(old_ports) - set(updated_ports)
        for rule in rules.get('security_group_rules', []):
            if rule.get('port_range_max') in del_ports:
                self.neutron_client.delete_security_group_rule(rule.get('id'))

        for port in add_ports:
            self._create_security_group_rule(sec_grp_id, 'TCP', port_min=port,
                                             port_max=port)

    def _update_vip_security_group(self, load_balancer, vip):
        sec_grp = self._get_lb_security_group(load_balancer.id)
        if not sec_grp:
            sec_grp_name = VIP_SECURITY_GRP_PREFIX + load_balancer.id
            sec_grp = self._create_security_group(sec_grp_name)
        self._update_security_group_rules(load_balancer, sec_grp.get('id'))
        self._add_vip_security_group_to_port(load_balancer.id, vip.port_id)

    def _add_vip_security_group_to_port(self, load_balancer_id, port_id):
        sec_grp = self._get_lb_security_group(load_balancer_id)
        try:
            self._add_security_group_to_port(sec_grp.get('id'), port_id)
        except base.PortNotFound as e:
            raise e
        except base.NetworkException as e:
            raise base.PlugVIPException(str(e))

    def _delete_vip_security_group(self, sec_grp):
        """Deletes a security group in neutron.

        Retries upon an exception because removing a security group from
        a neutron port does not happen immediately.
        """
        attempts = 0
        while attempts <= cfg.CONF.networking.max_retries:
            try:
                self.neutron_client.delete_security_group(sec_grp)
                LOG.info(_LI("Deleted security group {0}.").format(
                    sec_grp))
                return
            except neutron_client_exceptions.NotFound:
                message = _LI("Security group {0} not found, will assume it is"
                              " already deleted").format(sec_grp)
                LOG.info(message)
                return
            except Exception:
                message = _LW("Attempt {0} to remove security group {1} "
                              "failed.").format(attempts + 1, sec_grp)
                LOG.warning(message)
            attempts += 1
            time.sleep(cfg.CONF.networking.retry_interval)
        message = _LE("All attempts to remove security group {0} have "
                      "failed.").format(sec_grp)
        LOG.exception(message)
        raise base.DeallocateVIPException(message)

    def deallocate_vip(self, vip):
        try:
            port = self.get_port(vip.port_id)
        except base.PortNotFound:
            msg = ("Can't deallocate VIP because the vip port {0} cannot be "
                   "found in neutron".format(vip.port_id))
            raise base.VIPConfigurationNotFound(msg)
        if port.device_owner != OCTAVIA_OWNER:
            LOG.info(_LI("Port {0} will not be deleted by Octavia as it was "
                         "not created by Octavia.").format(vip.port_id))
            if self.sec_grp_enabled:
                sec_grp = self._get_lb_security_group(vip.load_balancer.id)
                sec_grp = sec_grp.get('id')
                LOG.info(_LI("Removing security group {0} from port "
                             "{1}").format(sec_grp, vip.port_id))
                raw_port = self.neutron_client.show_port(port.id)
                sec_grps = raw_port.get('port', {}).get('security_groups', [])
                if sec_grp in sec_grps:
                    sec_grps.remove(sec_grp)
                port_update = {'port': {'security_groups': sec_grps}}
                self.neutron_client.update_port(port.id, port_update)
                self._delete_vip_security_group(sec_grp)
            return
        try:
            self.neutron_client.delete_port(vip.port_id)
        except Exception:
            message = _LE('Error deleting VIP port_id {port_id} from '
                          'neutron').format(port_id=vip.port_id)
            LOG.exception(message)
            raise base.DeallocateVIPException(message)
        if self.sec_grp_enabled:
            sec_grp = self._get_lb_security_group(vip.load_balancer.id)
            sec_grp = sec_grp.get('id')
            self._delete_vip_security_group(sec_grp)

    def plug_vip(self, load_balancer, vip):
        if self.sec_grp_enabled:
            self._update_vip_security_group(load_balancer, vip)
        plugged_amphorae = []
        subnet = self.get_subnet(vip.subnet_id)
        for amphora in load_balancer.amphorae:
            interface = self._get_plugged_interface(amphora.compute_id,
                                                    subnet.network_id)
            if not interface:
                interface = self._plug_amphora_vip(amphora.compute_id,
                                                   subnet.network_id)
            self._add_vip_address_pair(interface.port_id, vip.ip_address)
            if self.sec_grp_enabled:
                self._add_vip_security_group_to_port(load_balancer.id,
                                                     interface.port_id)
            vrrp_ip = None
            for fixed_ip in interface.fixed_ips:
                if fixed_ip.subnet_id == subnet.id:
                    vrrp_ip = fixed_ip.ip_address
                    break
            plugged_amphorae.append(data_models.Amphora(
                id=amphora.id,
                compute_id=amphora.compute_id,
                vrrp_ip=vrrp_ip,
                ha_ip=vip.ip_address,
                vrrp_port_id=interface.port_id,
                ha_port_id=vip.port_id))
        return plugged_amphorae

    def allocate_vip(self, load_balancer):
        if not load_balancer.vip.port_id and not load_balancer.vip.subnet_id:
            raise base.AllocateVIPException('Cannot allocate a vip '
                                            'without a port_id or '
                                            'a subnet_id.')
        if load_balancer.vip.port_id:
            LOG.info(_LI('Port {port_id} already exists. Nothing to be '
                         'done.').format(port_id=load_balancer.vip.port_id))
            port = self.get_port(load_balancer.vip.port_id)
            return self._port_to_vip(port, load_balancer)

        # Must retrieve the network_id from the subnet
        subnet = self.get_subnet(load_balancer.vip.subnet_id)

        # It can be assumed that network_id exists
        port = {'port': {'name': 'octavia-lb-' + load_balancer.id,
                         'network_id': subnet.network_id,
                         'admin_state_up': False,
                         'device_id': 'lb-{0}'.format(load_balancer.id),
                         'device_owner': OCTAVIA_OWNER}}
        try:
            new_port = self.neutron_client.create_port(port)
        except Exception:
            message = _LE('Error creating neutron port on network '
                          '{network_id}.').format(
                network_id=subnet.network_id)
            LOG.exception(message)
            raise base.AllocateVIPException(message)
        new_port = utils.convert_port_dict_to_model(new_port)
        return self._port_to_vip(new_port, load_balancer)

    def unplug_vip(self, load_balancer, vip):
        try:
            subnet = self.get_subnet(vip.subnet_id)
        except base.SubnetNotFound:
            msg = ("Can't unplug vip because vip subnet {0} was not "
                   "found").format(vip.subnet_id)
            raise base.PluggedVIPNotFound(msg)
        for amphora in load_balancer.amphorae:
            interface = self._get_plugged_interface(amphora.compute_id,
                                                    subnet.network_id)
            if not interface:
                # Thought about raising PluggedVIPNotFound exception but
                # then that wouldn't evaluate all amphorae, so just continue
                continue
            try:
                self.unplug_network(amphora.compute_id, subnet.network_id)
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
            interface = self.nova_client.servers.interface_attach(
                server=compute_id, net_id=network_id, fixed_ip=ip_address,
                port_id=None)
        except nova_client_exceptions.NotFound as e:
            if 'Instance' in e.message:
                raise base.AmphoraNotFound(e.message)
            elif 'Network' in e.message:
                raise base.NetworkNotFound(e.message)
            else:
                raise base.PlugNetworkException(e.message)
        except Exception:
            message = _LE('Error plugging amphora (compute_id: {compute_id}) '
                          'into network {network_id}.').format(
                              compute_id=compute_id,
                              network_id=network_id)
            LOG.exception(message)
            raise base.PlugNetworkException(message)

        return self._nova_interface_to_octavia_interface(compute_id, interface)

    def unplug_network(self, compute_id, network_id, ip_address=None):
        interfaces = self.get_plugged_networks(compute_id)
        if not interfaces:
            msg = ('Amphora with compute id {compute_id} does not have any '
                   'plugged networks').format(compute_id=compute_id)
            raise base.AmphoraNotFound(msg)

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

    def failover_preparation(self, amphora):
        interfaces = self.get_plugged_networks(compute_id=amphora.compute_id)

        ports = []
        for interface_ in interfaces:
            port = self.get_port(port_id=interface_.port_id)
            ips = port.fixed_ips
            lb_network = False
            for ip in ips:
                if ip.ip_address == amphora.lb_network_ip:
                    lb_network = True
            if not lb_network:
                ports.append(port)

        for port in ports:
            try:
                self.neutron_client.update_port(port.id,
                                                {'port': {'device_id': ''}})
            except neutron_client_exceptions.NotFound:
                raise base.PortNotFound()
