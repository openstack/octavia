#    Copyright 2020 SAP SE
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

from octavia.f5_extensions import exceptions


def check_member_for_invalid_ip(session, repositories, member_address, load_balancer):
    """When creating a pool member that has the same IP as any VIP in the same network it will lead to error messages
    on the F5 BigIP device, thus making the whole AS3 declaration fail. This function checks the IP address of the
    given member and raises an exception if it finds a conflict. """

    # get VIPs from network
    conflicts = repositories.vip.get(session, network_id=load_balancer.vip.network_id, ip_address=member_address)

    if conflicts:
        raise exceptions.MemberIpConflictingWithVipException(ip=member_address)


def check_loadbalancer_for_invalid_ip(session, repositories, vip):
    """When creating a load balancer that has the same IP as any pool member in the same network it will lead to
    error messages on the F5 BigIP device, thus making the whole AS3 declaration fail. This function checks the IP
    address of the given load balancer and raises an exception if it finds a conflict. """

    # get possibly conflicting members
    candidates = repositories.member.get_all(session, ip_address=vip.ip_address)

    # check if any of the candidates' loadbalancers is in the same network as this vip
    for candidate in candidates[0]:
        if candidate.pool.load_balancer.vip.network_id == vip.network_id:
            raise exceptions.MemberIpConflictingWithVipException(ip=vip.ip_address)
