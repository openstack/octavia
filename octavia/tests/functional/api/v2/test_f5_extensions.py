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

import mock
from oslo_utils import uuidutils

from octavia.common import constants
from octavia.network import data_models as network_models
from octavia.tests.functional.api.v2 import base


class TestF5Extensions(base.BaseAPITest):

    def test_create_member_with_conflicting_vip(self):
        # create network in which conflict will happen
        network = network_models.Network(id=uuidutils.generate_uuid())

        # create load balancer with conflicting VIP
        lb_vip = self.create_load_balancer(uuidutils.generate_uuid(),
                                           vip_network_id=network.id).get('loadbalancer')
        self.set_lb_status(lb_vip['id'])
        ip_address = lb_vip['vip_address']

        # create conflicting member
        lb_member = self.create_load_balancer(uuidutils.generate_uuid(),
                                              vip_network_id=network.id).get('loadbalancer')
        self.set_lb_status(lb_member['id'])
        pool = self.create_pool(lb_member['id'], constants.PROTOCOL_HTTP,
                                constants.LB_ALGORITHM_ROUND_ROBIN).get('pool')
        self.set_lb_status(lb_member['id'])
        member_dict = {"address": ip_address, "protocol_port": 1234}
        self.root_tag = "member"
        self.post(self.MEMBERS_PATH.format(pool_id=pool['id']),
                  self._build_body(member_dict), status=409)

    def test_create_loadbalancer_with_conflicting_vip(self):
        # create IP that will be used for member and conflicting VIP
        subnet = network_models.Subnet(id=uuidutils.generate_uuid(), cidr='10.0.0.0/8')
        network = network_models.Network(id=uuidutils.generate_uuid(), subnets=[subnet])
        ip_address = '10.1.2.3'

        # create member
        lb_member = self.create_load_balancer(
            uuidutils.generate_uuid(), vip_network_id=network.id).get('loadbalancer')
        self.set_lb_status(lb_member['id'])
        pool = self.create_pool(
            lb_member['id'], constants.PROTOCOL_HTTP, constants.LB_ALGORITHM_ROUND_ROBIN).get('pool')
        self.set_lb_status(lb_member['id'])
        member = self.create_member(pool['id'], ip_address, 80).get('member')
        self.set_lb_status(lb_member['id'])

        # create conflicting load balancer
        lb_conflict = {'project_id': self.project_id,
                       'vip_address': ip_address,
                       'vip_network_id': network.id}

        # send request
        self.root_tag = "loadbalancer"
        body = self._build_body(lb_conflict)
        with mock.patch("octavia.api.v2.controllers.load_balancer.LoadBalancersController"
                        "._validate_network_and_fill_or_validate_subnet") as validate_network:
            validate_network.return_value = None
            self.post(self.LBS_PATH, body, status=409)
