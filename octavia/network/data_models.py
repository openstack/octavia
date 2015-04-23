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
