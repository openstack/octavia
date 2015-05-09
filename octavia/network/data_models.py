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

from octavia.common import data_models


class Interface(data_models.BaseDataModel):

    def __init__(self, id=None, amphora_id=None, network_id=None,
                 ip_address=None, port_id=None):
        self.id = id
        self.amphora_id = amphora_id
        self.network_id = network_id
        self.port_id = port_id
        self.ip_address = ip_address


class Delta(data_models.BaseDataModel):

    def __init__(self, amphora_id=None, compute_id=None,
                 add_nics=None, delete_nics=None):
        self.compute_id = compute_id
        self.amphora_id = amphora_id
        self.add_nics = add_nics
        self.delete_nics = delete_nics


class Network(data_models.BaseDataModel):

    def __init__(self, id=None, name=None, subnets=None,
                 tenant_id=None, admin_state_up=None, mtu=None,
                 provider_network_type=None,
                 provider_physical_network=None,
                 provider_segmentation_id=None,
                 router_external=None):
        self.id = id
        self.name = name
        self.subnets = subnets
        self.tenant_id = tenant_id
        self.admin_state_up = admin_state_up
        self.provider_network_type = provider_network_type
        self.provider_physical_network = provider_physical_network
        self.provider_segmentation_id = provider_segmentation_id
        self.router_external = router_external
