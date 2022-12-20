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


from openstack.network.v2.network_ip_availability import NetworkIPAvailability

from octavia.network import data_models as network_models


def convert_subnet_to_model(subnet):
    host_routes = [network_models.HostRoute(nexthop=hr.get('nexthop'),
                                            destination=hr.get('destination'))
                   for hr in subnet.host_routes] if subnet.host_routes else []
    return network_models.Subnet(
        id=subnet.id,
        name=subnet.name,
        network_id=subnet.network_id,
        project_id=subnet.project_id,
        gateway_ip=subnet.gateway_ip,
        cidr=subnet.cidr,
        ip_version=subnet.ip_version,
        host_routes=host_routes,
    )


def convert_port_to_model(port):
    if port.get('fixed_ips'):
        fixed_ips = [convert_fixed_ip_dict_to_model(fixed_ip)
                     for fixed_ip in port.fixed_ips]
    else:
        fixed_ips = []
    return network_models.Port(
        id=port.id,
        name=port.name,
        device_id=port.device_id,
        device_owner=port.device_owner,
        mac_address=port.mac_address,
        network_id=port.network_id,
        status=port.status,
        project_id=port.project_id,
        admin_state_up=port.is_admin_state_up,
        fixed_ips=fixed_ips,
        qos_policy_id=port.qos_policy_id,
        security_group_ids=port.security_group_ids
    )


def convert_network_to_model(nw):
    return network_models.Network(
        id=nw.id,
        name=nw.name,
        subnets=nw.subnet_ids,
        project_id=nw.project_id,
        admin_state_up=nw.is_admin_state_up,
        mtu=nw.mtu,
        provider_network_type=nw.provider_network_type,
        provider_physical_network=nw.provider_physical_network,
        provider_segmentation_id=nw.provider_segmentation_id,
        router_external=nw.is_router_external,
        port_security_enabled=nw.is_port_security_enabled,
    )


def convert_fixed_ip_dict_to_model(fixed_ip: dict):
    return network_models.FixedIP(subnet_id=fixed_ip.get('subnet_id'),
                                  ip_address=fixed_ip.get('ip_address'))


def convert_qos_policy_to_model(qos_policy):
    return network_models.QosPolicy(id=qos_policy.id)


def convert_network_ip_availability_to_model(
        nw_ip_avail: NetworkIPAvailability):
    ip_avail = network_models.Network_IP_Availability(
        network_id=nw_ip_avail.network_id,
        tenant_id=nw_ip_avail.tenant_id,
        project_id=nw_ip_avail.project_id,
        network_name=nw_ip_avail.network_name, total_ips=nw_ip_avail.total_ips,
        used_ips=nw_ip_avail.used_ips,
        subnet_ip_availability=nw_ip_avail.subnet_ip_availability)
    return ip_avail


def convert_security_group_to_model(security_group):
    if security_group.security_group_rules:
        sg_rule_ids = [rule['id'] for rule in
                       security_group.security_group_rules]
    else:
        sg_rule_ids = []
    return network_models.SecurityGroup(
        id=security_group.id,
        project_id=security_group.project_id,
        name=security_group.name,
        description=security_group.description,
        security_group_rule_ids=sg_rule_ids,
        tags=security_group.tags,
        stateful=security_group.stateful)
