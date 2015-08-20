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


class MockNovaInterface(object):
    net_id = None
    port_id = None
    fixed_ips = []

MOCK_NETWORK_ID = '1'
MOCK_SUBNET_ID = '2'
MOCK_PORT_ID = '3'
MOCK_COMPUTE_ID = '4'
MOCK_IP_ADDRESS = '10.0.0.1'
MOCK_CIDR = '10.0.0.0/24'
MOCK_MAC_ADDR = 'fe:16:3e:00:95:5c'
MOCK_NOVA_INTERFACE = MockNovaInterface()
MOCK_SUBNET = {'subnet': {'id': MOCK_SUBNET_ID, 'network_id': MOCK_NETWORK_ID}}
MOCK_NOVA_INTERFACE.net_id = MOCK_NETWORK_ID
MOCK_NOVA_INTERFACE.port_id = MOCK_PORT_ID
MOCK_NOVA_INTERFACE.fixed_ips = [{'ip_address': MOCK_IP_ADDRESS}]
MOCK_DEVICE_OWNER = 'Moctavia'

MOCK_NEUTRON_PORT = {'port': {'network_id': MOCK_NETWORK_ID,
                              'device_id': MOCK_COMPUTE_ID,
                              'device_owner': MOCK_DEVICE_OWNER,
                              'id': MOCK_PORT_ID,
                              'fixed_ips': [{'ip_address': MOCK_IP_ADDRESS,
                                             'subnet_id': MOCK_SUBNET_ID}]}}
