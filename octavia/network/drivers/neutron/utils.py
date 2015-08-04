#    Copyright 2015 Rackspace
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

from oslo_log import log as logging

from octavia.network import data_models as network_models


LOG = logging.getLogger(__name__)


def convert_subnet_dict_to_model(subnet_dict):
    subnet = subnet_dict.get('subnet', subnet_dict)
    return network_models.Subnet(id=subnet.get('id'), name=subnet.get('name'),
                                 network_id=subnet.get('network_id'),
                                 tenant_id=subnet.get('tenant_id'),
                                 gateway_ip=subnet.get('gateway_ip'),
                                 cidr=subnet.get('cidr'),
                                 ip_version=subnet.get('ip_version')
                                 )


def convert_port_dict_to_model(port_dict):
    port = port_dict.get('port', port_dict)
    fixed_ips = [network_models.FixedIP(subnet_id=fixed_ip.get('subnet_id'),
                                        ip_address=fixed_ip.get('ip_address'))
                 for fixed_ip in port.get('fixed_ips', [])]
    return network_models.Port(
        id=port.get('id'),
        name=port.get('name'),
        device_id=port.get('device_id'),
        device_owner=port.get('device_owner'),
        mac_address=port.get('mac_address'),
        network_id=port.get('network_id'),
        status=port.get('status'),
        tenant_id=port.get('tenant_id'),
        admin_state_up=port.get('admin_state_up'),
        fixed_ips=fixed_ips
    )


def convert_network_dict_to_model(network_dict):
    nw = network_dict.get('network', network_dict)
    return network_models.Network(
        id=nw.get('id'),
        name=nw.get('name'),
        subnets=nw.get('subnets'),
        tenant_id=nw.get('tenant_id'),
        admin_state_up=nw.get('admin_state_up'),
        mtu=nw.get('mtu'),
        provider_network_type=nw.get('provider:network_type'),
        provider_physical_network=nw.get('provider:physical_network'),
        provider_segmentation_id=nw.get('provider:segmentation_id'),
        router_external=nw.get('router:external')
    )


def convert_fixed_ip_dict_to_model(fixed_ip_dict):
    fixed_ip = fixed_ip_dict.get('fixed_ip', fixed_ip_dict)
    return network_models.FixedIP(subnet_id=fixed_ip.get('subnet_id'),
                                  ip_address=fixed_ip.get('ip_address'))
