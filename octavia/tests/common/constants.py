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

MOCK_NETWORK_ID = 'mock-network-1'
MOCK_NETWORK_ID2 = 'mock-network-2'
MOCK_NETWORK_NAME = 'TestNet1'
MOCK_SUBNET_ID = 'mock-subnet-1'
MOCK_SUBNET_ID2 = 'mock-subnet-2'
MOCK_SUBNET_NAME = 'TestSubnet1'
MOCK_PORT_ID = 'mock-port-1'
MOCK_PORT_ID2 = 'mock-port-2'
MOCK_PORT_NAME = 'TestPort1'
MOCK_COMPUTE_ID = 'mock-compute-1'
MOCK_IP_ADDRESS = '10.0.0.1'
MOCK_IP_ADDRESS2 = '10.0.0.2'
MOCK_CIDR = '10.0.0.0/24'
MOCK_MAC_ADDR = 'fe:16:3e:00:95:5c'
MOCK_NOVA_INTERFACE = MockNovaInterface()
MOCK_SUBNET = {'subnet': {'id': MOCK_SUBNET_ID, 'network_id': MOCK_NETWORK_ID}}
MOCK_NOVA_INTERFACE.net_id = MOCK_NETWORK_ID
MOCK_NOVA_INTERFACE.port_id = MOCK_PORT_ID
MOCK_NOVA_INTERFACE.fixed_ips = [{'ip_address': MOCK_IP_ADDRESS}]
MOCK_NOVA_INTERFACE2 = MockNovaInterface()
MOCK_SUBNET2 = {'subnet': {'id': MOCK_SUBNET_ID2,
                           'network_id': MOCK_NETWORK_ID2}}
MOCK_NOVA_INTERFACE2.net_id = MOCK_NETWORK_ID2
MOCK_NOVA_INTERFACE2.port_id = MOCK_PORT_ID2
MOCK_NOVA_INTERFACE2.fixed_ips = [{'ip_address': MOCK_IP_ADDRESS2}]
MOCK_DEVICE_OWNER = 'Moctavia'
MOCK_DEVICE_ID = 'Moctavia123'

MOCK_NEUTRON_PORT = {'port': {'network_id': MOCK_NETWORK_ID,
                              'device_id': MOCK_COMPUTE_ID,
                              'device_owner': MOCK_DEVICE_OWNER,
                              'id': MOCK_PORT_ID,
                              'fixed_ips': [{'ip_address': MOCK_IP_ADDRESS,
                                             'subnet_id': MOCK_SUBNET_ID}]}}

MOCK_AMP_ID1 = 'amp1-id'
MOCK_AMP_ID2 = 'amp2-id'
MOCK_AMP_COMPUTE_ID1 = 'amp1-compute-id'
MOCK_AMP_COMPUTE_ID2 = 'amp2-compute-id'

MOCK_MANAGEMENT_SUBNET_ID = 'mgmt-subnet-1'
MOCK_MANAGEMENT_NET_ID = 'mgmt-net-1'
MOCK_MANAGEMENT_PORT_ID1 = 'mgmt-port-1'
MOCK_MANAGEMENT_PORT_ID2 = 'mgmt-port-2'
# These IPs become lb_network_ip
MOCK_MANAGEMENT_IP1 = '99.99.99.1'
MOCK_MANAGEMENT_IP2 = '99.99.99.2'

MOCK_MANAGEMENT_FIXED_IPS1 = [{'ip_address': MOCK_MANAGEMENT_IP1,
                               'subnet_id': MOCK_MANAGEMENT_SUBNET_ID}]
MOCK_MANAGEMENT_FIXED_IPS2 = [{'ip_address': MOCK_MANAGEMENT_IP2,
                               'subnet_id': MOCK_MANAGEMENT_SUBNET_ID}]

MOCK_MANAGEMENT_INTERFACE1 = MockNovaInterface()
MOCK_MANAGEMENT_INTERFACE1.net_id = MOCK_MANAGEMENT_NET_ID
MOCK_MANAGEMENT_INTERFACE1.port_id = MOCK_MANAGEMENT_PORT_ID1
MOCK_MANAGEMENT_INTERFACE1.fixed_ips = MOCK_MANAGEMENT_FIXED_IPS1
MOCK_MANAGEMENT_INTERFACE2 = MockNovaInterface()
MOCK_MANAGEMENT_INTERFACE2.net_id = MOCK_MANAGEMENT_NET_ID
MOCK_MANAGEMENT_INTERFACE2.port_id = MOCK_MANAGEMENT_PORT_ID2
MOCK_MANAGEMENT_INTERFACE2.fixed_ips = MOCK_MANAGEMENT_FIXED_IPS2

MOCK_MANAGEMENT_PORT1 = {'port': {'network_id': MOCK_MANAGEMENT_NET_ID,
                                  'device_id': MOCK_AMP_COMPUTE_ID1,
                                  'device_owner': MOCK_DEVICE_OWNER,
                                  'id': MOCK_MANAGEMENT_PORT_ID1,
                                  'fixed_ips': MOCK_MANAGEMENT_FIXED_IPS1}}

MOCK_MANAGEMENT_PORT2 = {'port': {'network_id': MOCK_MANAGEMENT_NET_ID,
                                  'device_id': MOCK_AMP_COMPUTE_ID2,
                                  'device_owner': MOCK_DEVICE_OWNER,
                                  'id': MOCK_MANAGEMENT_PORT_ID2,
                                  'fixed_ips': MOCK_MANAGEMENT_FIXED_IPS2}}

MOCK_VIP_SUBNET_ID = 'vip-subnet-1'
MOCK_VIP_NET_ID = 'vip-net-1'
MOCK_VRRP_PORT_ID1 = 'vrrp-port-1'
MOCK_VRRP_PORT_ID2 = 'vrrp-port-2'
# These IPs become vrrp_ip
MOCK_VRRP_IP1 = '55.55.55.1'
MOCK_VRRP_IP2 = '55.55.55.2'

MOCK_VRRP_FIXED_IPS1 = [{'ip_address': MOCK_VRRP_IP1,
                         'subnet_id': MOCK_VIP_SUBNET_ID}]
MOCK_VRRP_FIXED_IPS2 = [{'ip_address': MOCK_VRRP_IP2,
                         'subnet_id': MOCK_VIP_SUBNET_ID}]

MOCK_VRRP_INTERFACE1 = MockNovaInterface()
MOCK_VRRP_INTERFACE1.net_id = MOCK_VIP_NET_ID
MOCK_VRRP_INTERFACE1.port_id = MOCK_VRRP_PORT_ID1
MOCK_VRRP_INTERFACE1.fixed_ips = MOCK_VRRP_FIXED_IPS1
MOCK_VRRP_INTERFACE2 = MockNovaInterface()
MOCK_VRRP_INTERFACE2.net_id = MOCK_VIP_NET_ID
MOCK_VRRP_INTERFACE2.port_id = MOCK_VRRP_PORT_ID2
MOCK_VRRP_INTERFACE2.fixed_ips = MOCK_VRRP_FIXED_IPS2

MOCK_VRRP_PORT1 = {'port': {'network_id': MOCK_VIP_NET_ID,
                            'device_id': MOCK_AMP_COMPUTE_ID1,
                            'device_owner': MOCK_DEVICE_OWNER,
                            'id': MOCK_VRRP_PORT_ID1,
                            'fixed_ips': MOCK_VRRP_FIXED_IPS1}}

MOCK_VRRP_PORT2 = {'port': {'network_id': MOCK_VIP_NET_ID,
                            'device_id': MOCK_AMP_COMPUTE_ID2,
                            'device_owner': MOCK_DEVICE_OWNER,
                            'id': MOCK_VRRP_PORT_ID2,
                            'fixed_ips': MOCK_VRRP_FIXED_IPS2}}
