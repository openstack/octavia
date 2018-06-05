#    Copyright 2018 Rackspace, US Inc.
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

from copy import deepcopy

from oslo_utils import uuidutils

from octavia.api.drivers import data_models
import octavia.tests.unit.base as base


class TestProviderDataModels(base.TestCase):

    def setUp(self):
        super(TestProviderDataModels, self).setUp()

        self.loadbalancer_id = uuidutils.generate_uuid()
        self.project_id = uuidutils.generate_uuid()
        self.vip_address = '192.0.2.83'
        self.vip_network_id = uuidutils.generate_uuid()
        self.vip_port_id = uuidutils.generate_uuid()
        self.vip_subnet_id = uuidutils.generate_uuid()
        self.listener_id = uuidutils.generate_uuid()
        self.vip_qos_policy_id = uuidutils.generate_uuid()
        self.default_tls_container_ref = uuidutils.generate_uuid()
        self.sni_container_ref_1 = uuidutils.generate_uuid()
        self.sni_container_ref_2 = uuidutils.generate_uuid()

        self.ref_listener = data_models.Listener(
            admin_state_up=True,
            connection_limit=5000,
            default_pool_id=None,
            default_tls_container_data='default_cert_data',
            default_tls_container_ref=self.default_tls_container_ref,
            description=data_models.Unset,
            insert_headers={'X-Forwarded-For': 'true'},
            l7policies=[],
            listener_id=self.listener_id,
            loadbalancer_id=self.loadbalancer_id,
            name='super_listener',
            protocol='avian',
            protocol_port=42,
            sni_container_data=['sni_cert_data_1', 'sni_cert_data_2'],
            sni_container_refs=[self.sni_container_ref_1,
                                self.sni_container_ref_2])

        self.ref_lb = data_models.LoadBalancer(
            admin_state_up=False,
            description='One great load balancer',
            flavor={'cake': 'chocolate'},
            listeners=[self.ref_listener],
            loadbalancer_id=self.loadbalancer_id,
            name='favorite_lb',
            project_id=self.project_id,
            vip_address=self.vip_address,
            vip_network_id=self.vip_network_id,
            vip_port_id=self.vip_port_id,
            vip_subnet_id=self.vip_subnet_id,
            vip_qos_policy_id=self.vip_qos_policy_id)

        self.ref_lb_dict = {'project_id': self.project_id,
                            'flavor': {'cake': 'chocolate'},
                            'vip_network_id': self.vip_network_id,
                            'admin_state_up': False,
                            'loadbalancer_id': self.loadbalancer_id,
                            'vip_port_id': self.vip_port_id,
                            'vip_address': self.vip_address,
                            'description': 'One great load balancer',
                            'vip_subnet_id': self.vip_subnet_id,
                            'name': 'favorite_lb',
                            'vip_qos_policy_id': self.vip_qos_policy_id}

        self.ref_listener = {
            'admin_state_up': True,
            'connection_limit': 5000,
            'default_pool_id': None,
            'default_tls_container_data': 'default_cert_data',
            'default_tls_container_ref': self.default_tls_container_ref,
            'insert_headers': {'X-Forwarded-For': 'true'},
            'listener_id': self.listener_id,
            'l7policies': [],
            'loadbalancer_id': self.loadbalancer_id,
            'name': 'super_listener',
            'protocol': 'avian',
            'protocol_port': 42,
            'sni_container_data': ['sni_cert_data_1', 'sni_cert_data_2'],
            'sni_container_refs': [self.sni_container_ref_1,
                                   self.sni_container_ref_2]}

        self.ref_lb_dict_with_listener = {
            'admin_state_up': False,
            'description': 'One great load balancer',
            'flavor': {'cake': 'chocolate'},
            'listeners': [self.ref_listener],
            'loadbalancer_id': self.loadbalancer_id,
            'name': 'favorite_lb',
            'project_id': self.project_id,
            'vip_address': self.vip_address,
            'vip_network_id': self.vip_network_id,
            'vip_port_id': self.vip_port_id,
            'vip_subnet_id': self.vip_subnet_id,
            'vip_qos_policy_id': self.vip_qos_policy_id}

    def test_equality(self):
        second_ref_lb = deepcopy(self.ref_lb)

        self.assertTrue(self.ref_lb == second_ref_lb)

        second_ref_lb.admin_state_up = True

        self.assertFalse(self.ref_lb == second_ref_lb)

        self.assertFalse(self.ref_lb == self.loadbalancer_id)

    def test_inequality(self):
        second_ref_lb = deepcopy(self.ref_lb)

        self.assertFalse(self.ref_lb != second_ref_lb)

        second_ref_lb.admin_state_up = True

        self.assertTrue(self.ref_lb != second_ref_lb)

        self.assertTrue(self.ref_lb != self.loadbalancer_id)

    def test_to_dict(self):
        ref_lb_converted_to_dict = self.ref_lb.to_dict()

        self.assertEqual(self.ref_lb_dict, ref_lb_converted_to_dict)

    def test_to_dict_private_attrs(self):
        private_dict = {'_test': 'foo'}
        ref_lb_converted_to_dict = self.ref_lb.to_dict(**private_dict)

        self.assertEqual(self.ref_lb_dict, ref_lb_converted_to_dict)

    def test_to_dict_partial(self):
        ref_lb = data_models.LoadBalancer(loadbalancer_id=self.loadbalancer_id)
        ref_lb_dict = {'loadbalancer_id': self.loadbalancer_id}
        ref_lb_converted_to_dict = ref_lb.to_dict()

        self.assertEqual(ref_lb_dict, ref_lb_converted_to_dict)

    def test_to_dict_render_unsets(self):

        ref_lb_converted_to_dict = self.ref_lb.to_dict(render_unsets=True)

        new_ref_lib_dict = deepcopy(self.ref_lb_dict)
        new_ref_lib_dict['pools'] = None
        new_ref_lib_dict['listeners'] = None

        self.assertEqual(new_ref_lib_dict, ref_lb_converted_to_dict)

    def test_to_dict_recursive(self):
        ref_lb_converted_to_dict = self.ref_lb.to_dict(recurse=True)

        self.assertEqual(self.ref_lb_dict_with_listener,
                         ref_lb_converted_to_dict)

    def test_to_dict_recursive_partial(self):
        ref_lb = data_models.LoadBalancer(
            loadbalancer_id=self.loadbalancer_id,
            listeners=[self.ref_listener])

        ref_lb_dict_with_listener = {
            'loadbalancer_id': self.loadbalancer_id,
            'listeners': [self.ref_listener]}

        ref_lb_converted_to_dict = ref_lb.to_dict(recurse=True)

        self.assertEqual(ref_lb_dict_with_listener, ref_lb_converted_to_dict)

    def test_to_dict_recursive_render_unset(self):
        ref_lb = data_models.LoadBalancer(
            admin_state_up=False,
            description='One great load balancer',
            flavor={'cake': 'chocolate'},
            listeners=[self.ref_listener],
            loadbalancer_id=self.loadbalancer_id,
            project_id=self.project_id,
            vip_address=self.vip_address,
            vip_network_id=self.vip_network_id,
            vip_port_id=self.vip_port_id,
            vip_subnet_id=self.vip_subnet_id,
            vip_qos_policy_id=self.vip_qos_policy_id)

        ref_lb_dict_with_listener = deepcopy(self.ref_lb_dict_with_listener)
        ref_lb_dict_with_listener['pools'] = None
        ref_lb_dict_with_listener['name'] = None

        ref_lb_converted_to_dict = ref_lb.to_dict(recurse=True,
                                                  render_unsets=True)

        self.assertEqual(ref_lb_dict_with_listener,
                         ref_lb_converted_to_dict)

    def test_from_dict(self):
        lb_object = data_models.LoadBalancer.from_dict(self.ref_lb_dict)

        self.assertEqual(self.ref_lb, lb_object)

    def test_unset_bool(self):
        self.assertFalse(data_models.Unset)

    def test_unset_repr(self):
        self.assertEqual('Unset', repr(data_models.Unset))
