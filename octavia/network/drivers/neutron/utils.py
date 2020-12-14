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


from octavia.common import constants
from octavia.network import data_models as network_models


def convert_subnet_dict_to_model(subnet_dict):
    subnet = subnet_dict.get('subnet', subnet_dict)
    subnet_hrs = subnet.get('host_routes', [])
    host_routes = [network_models.HostRoute(nexthop=hr.get('nexthop'),
                                            destination=hr.get('destination'))
                   for hr in subnet_hrs]
    return network_models.Subnet(id=subnet.get(constants.ID),
                                 name=subnet.get(constants.NAME),
                                 network_id=subnet.get('network_id'),
                                 project_id=subnet.get(constants.TENANT_ID),
                                 gateway_ip=subnet.get('gateway_ip'),
                                 cidr=subnet.get('cidr'),
                                 ip_version=subnet.get('ip_version'),
                                 host_routes=host_routes
                                 )


def convert_port_dict_to_model(port_dict):
    port = port_dict.get('port', port_dict)
    fixed_ips = [network_models.FixedIP(subnet_id=fixed_ip.get('subnet_id'),
                                        ip_address=fixed_ip.get('ip_address'))
                 for fixed_ip in port.get('fixed_ips', [])]
    return network_models.Port(
        id=port.get(constants.ID),
        name=port.get(constants.NAME),
        device_id=port.get('device_id'),
        device_owner=port.get('device_owner'),
        mac_address=port.get('mac_address'),
        network_id=port.get('network_id'),
        status=port.get('status'),
        project_id=port.get(constants.TENANT_ID),
        admin_state_up=port.get('admin_state_up'),
        fixed_ips=fixed_ips,
        qos_policy_id=port.get('qos_policy_id'),
        security_group_ids=port.get(constants.SECURITY_GROUPS, [])
    )


def convert_network_dict_to_model(network_dict):
    nw = network_dict.get('network', network_dict)
    return network_models.Network(
        id=nw.get(constants.ID),
        name=nw.get(constants.NAME),
        subnets=nw.get('subnets'),
        project_id=nw.get(constants.TENANT_ID),
        admin_state_up=nw.get('admin_state_up'),
        mtu=nw.get('mtu'),
        provider_network_type=nw.get('provider:network_type'),
        provider_physical_network=nw.get('provider:physical_network'),
        provider_segmentation_id=nw.get('provider:segmentation_id'),
        router_external=nw.get('router:external'),
        port_security_enabled=nw.get('port_security_enabled')
    )


def convert_fixed_ip_dict_to_model(fixed_ip_dict):
    fixed_ip = fixed_ip_dict.get('fixed_ip', fixed_ip_dict)
    return network_models.FixedIP(subnet_id=fixed_ip.get('subnet_id'),
                                  ip_address=fixed_ip.get('ip_address'))


def convert_qos_policy_dict_to_model(qos_policy_dict):
    qos_policy = qos_policy_dict.get('policy', qos_policy_dict)
    return network_models.QosPolicy(id=qos_policy.get(constants.ID))


# We can't use "floating_ip" because we need to match the neutron client method
def convert_floatingip_dict_to_model(floating_ip_dict):
    floating_ip = floating_ip_dict.get('floatingip', floating_ip_dict)
    return network_models.FloatingIP(
        id=floating_ip.get(constants.ID),
        description=floating_ip.get(constants.DESCRIPTION),
        project_id=floating_ip.get(constants.PROJECT_ID,
                                   floating_ip.get(constants.TENANT_ID)),
        status=floating_ip.get('status'),
        router_id=floating_ip.get('router_id'),
        port_id=floating_ip.get('port_id'),
        floating_network_id=floating_ip.get('floating_network_id'),
        floating_ip_address=floating_ip.get('floating_ip_address'),
        fixed_ip_address=floating_ip.get('fixed_ip_address'),
        fixed_port_id=floating_ip.get('fixed_port_id')
    )


def convert_network_ip_availability_dict_to_model(
        network_ip_availability_dict):
    nw_ip_avail = network_ip_availability_dict.get(
        'network_ip_availability', network_ip_availability_dict)
    ip_avail = network_models.Network_IP_Availability.from_dict(nw_ip_avail)
    ip_avail.subnet_ip_availability = nw_ip_avail.get('subnet_ip_availability')
    return ip_avail


def convert_security_group_dict_to_model(security_group_dict):
    sg_rule_ids = [rule.get(constants.ID) for rule in
                   security_group_dict.get(constants.SECURITY_GROUP_RULES, [])]
    return network_models.SecurityGroup(
        id=security_group_dict.get(constants.ID),
        project_id=security_group_dict.get(
            constants.PROJECT_ID,
            security_group_dict.get(constants.TENANT_ID)),
        name=security_group_dict.get(constants.NAME),
        description=security_group_dict.get(constants.DESCRIPTION),
        security_group_rule_ids=sg_rule_ids,
        tags=security_group_dict.get(constants.TAGS, []),
        stateful=security_group_dict.get('stateful'))
