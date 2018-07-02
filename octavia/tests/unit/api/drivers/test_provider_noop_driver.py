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

from oslo_utils import uuidutils

from octavia.api.drivers import data_models
from octavia.api.drivers.noop_driver import driver
import octavia.tests.unit.base as base


class TestNoopProviderDriver(base.TestCase):

    def setUp(self):
        super(TestNoopProviderDriver, self).setUp()
        self.driver = driver.NoopProviderDriver()

        self.loadbalancer_id = uuidutils.generate_uuid()
        self.vip_address = '192.0.2.10'
        self.vip_network_id = uuidutils.generate_uuid()
        self.vip_port_id = uuidutils.generate_uuid()
        self.vip_subnet_id = uuidutils.generate_uuid()
        self.listener_id = uuidutils.generate_uuid()
        self.pool_id = uuidutils.generate_uuid()
        self.member_id = uuidutils.generate_uuid()
        self.member_subnet_id = uuidutils.generate_uuid()
        self.healthmonitor_id = uuidutils.generate_uuid()
        self.l7policy_id = uuidutils.generate_uuid()
        self.l7rule_id = uuidutils.generate_uuid()
        self.project_id = uuidutils.generate_uuid()
        self.default_tls_container_ref = uuidutils.generate_uuid()
        self.sni_container_ref_1 = uuidutils.generate_uuid()
        self.sni_container_ref_2 = uuidutils.generate_uuid()

        self.ref_vip = data_models.VIP(
            vip_address=self.vip_address,
            vip_network_id=self.vip_network_id,
            vip_port_id=self.vip_port_id,
            vip_subnet_id=self.vip_subnet_id)

        self.ref_member = data_models.Member(
            address='198.51.100.4',
            admin_state_up=True,
            member_id=self.member_id,
            monitor_address='203.0.113.2',
            monitor_port=66,
            name='jacket',
            pool_id=self.pool_id,
            protocol_port=99,
            subnet_id=self.member_subnet_id,
            weight=55)

        self.ref_healthmonitor = data_models.HealthMonitor(
            admin_state_up=False,
            delay=2,
            expected_codes="500",
            healthmonitor_id=self.healthmonitor_id,
            http_method='TRACE',
            max_retries=1,
            max_retries_down=0,
            name='doc',
            pool_id=self.pool_id,
            timeout=3,
            type='PHD',
            url_path='/index.html')

        self.ref_pool = data_models.Pool(
            admin_state_up=True,
            description='Olympic swimming pool',
            healthmonitor=self.ref_healthmonitor,
            lb_algorithm='A_Fast_One',
            loadbalancer_id=self.loadbalancer_id,
            listener_id=self.listener_id,
            members=[self.ref_member],
            name='Osborn',
            pool_id=self.pool_id,
            protocol='avian',
            session_persistence={'type': 'glue'})

        self.ref_l7rule = data_models.L7Rule(
            admin_state_up=True,
            compare_type='store_brand',
            invert=True,
            key='board',
            l7policy_id=self.l7policy_id,
            l7rule_id=self.l7rule_id,
            type='strict',
            value='gold')

        self.ref_l7policy = data_models.L7Policy(
            action='packed',
            admin_state_up=False,
            description='Corporate policy',
            l7policy_id=self.l7policy_id,
            listener_id=self.listener_id,
            name='more_policy',
            position=1,
            redirect_pool_id=self.pool_id,
            redirect_url='/hr',
            rules=[self.ref_l7rule])

        self.ref_listener = data_models.Listener(
            admin_state_up=False,
            connection_limit=5,
            default_pool=self.ref_pool,
            default_pool_id=self.pool_id,
            default_tls_container_data='default_cert_data',
            default_tls_container_ref=self.default_tls_container_ref,
            description='The listener',
            insert_headers={'X-Forwarded-For': 'true'},
            l7policies=[self.ref_l7policy],
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
            vip_subnet_id=self.vip_subnet_id)

        self.ref_flavor_metadata = {
            'amp_image_tag': 'The glance image tag to use for this load '
            'balancer.'}

    def test_create_vip_port(self):
        vip_dict = self.driver.create_vip_port(self.loadbalancer_id,
                                               self.project_id,
                                               self.ref_vip.to_dict())

        self.assertEqual(self.ref_vip.to_dict(), vip_dict)

    def test_loadbalancer_create(self):
        self.driver.loadbalancer_create(self.ref_lb)

        self.assertEqual((self.ref_lb, 'loadbalancer_create'),
                         self.driver.driver.driverconfig[self.loadbalancer_id])

    def test_loadbalancer_delete(self):
        self.driver.loadbalancer_delete(self.ref_lb, cascade=True)

        self.assertEqual((self.loadbalancer_id, True, 'loadbalancer_delete'),
                         self.driver.driver.driverconfig[self.loadbalancer_id])

    def test_loadbalancer_failover(self):
        self.driver.loadbalancer_failover(self.loadbalancer_id)

        self.assertEqual((self.loadbalancer_id, 'loadbalancer_failover'),
                         self.driver.driver.driverconfig[self.loadbalancer_id])

    def test_loadbalancer_update(self):
        self.driver.loadbalancer_update(self.ref_lb, self.ref_lb)

        self.assertEqual((self.ref_lb, 'loadbalancer_update'),
                         self.driver.driver.driverconfig[self.loadbalancer_id])

    def test_listener_create(self):
        self.driver.listener_create(self.ref_listener)

        self.assertEqual((self.ref_listener, 'listener_create'),
                         self.driver.driver.driverconfig[self.listener_id])

    def test_listener_delete(self):
        self.driver.listener_delete(self.ref_listener)

        self.assertEqual((self.listener_id, 'listener_delete'),
                         self.driver.driver.driverconfig[self.listener_id])

    def test_listener_update(self):
        self.driver.listener_update(self.ref_listener, self.ref_listener)

        self.assertEqual((self.ref_listener, 'listener_update'),
                         self.driver.driver.driverconfig[self.listener_id])

    def test_pool_create(self):
        self.driver.pool_create(self.ref_pool)

        self.assertEqual((self.ref_pool, 'pool_create'),
                         self.driver.driver.driverconfig[self.pool_id])

    def test_pool_delete(self):
        self.driver.pool_delete(self.ref_pool)

        self.assertEqual((self.pool_id, 'pool_delete'),
                         self.driver.driver.driverconfig[self.pool_id])

    def test_pool_update(self):
        self.driver.pool_update(self.ref_pool, self.ref_pool)

        self.assertEqual((self.ref_pool, 'pool_update'),
                         self.driver.driver.driverconfig[self.pool_id])

    def test_member_create(self):
        self.driver.member_create(self.ref_member)

        self.assertEqual((self.ref_member, 'member_create'),
                         self.driver.driver.driverconfig[self.member_id])

    def test_member_delete(self):
        self.driver.member_delete(self.ref_member)

        self.assertEqual((self.member_id, 'member_delete'),
                         self.driver.driver.driverconfig[self.member_id])

    def test_member_update(self):
        self.driver.member_update(self.ref_member, self.ref_member)

        self.assertEqual((self.ref_member, 'member_update'),
                         self.driver.driver.driverconfig[self.member_id])

    def test_member_batch_update(self):
        self.driver.member_batch_update([self.ref_member])

        self.assertEqual((self.ref_member, 'member_batch_update'),
                         self.driver.driver.driverconfig[self.member_id])

    def test_health_monitor_create(self):
        self.driver.health_monitor_create(self.ref_healthmonitor)

        self.assertEqual(
            (self.ref_healthmonitor, 'health_monitor_create'),
            self.driver.driver.driverconfig[self.healthmonitor_id])

    def test_health_monitor_delete(self):
        self.driver.health_monitor_delete(self.ref_healthmonitor)

        self.assertEqual(
            (self.healthmonitor_id, 'health_monitor_delete'),
            self.driver.driver.driverconfig[self.healthmonitor_id])

    def test_health_monitor_update(self):
        self.driver.health_monitor_update(self.ref_healthmonitor,
                                          self.ref_healthmonitor)

        self.assertEqual(
            (self.ref_healthmonitor, 'health_monitor_update'),
            self.driver.driver.driverconfig[self.healthmonitor_id])

    def test_l7policy_create(self):
        self.driver.l7policy_create(self.ref_l7policy)

        self.assertEqual((self.ref_l7policy, 'l7policy_create'),
                         self.driver.driver.driverconfig[self.l7policy_id])

    def test_l7policy_delete(self):
        self.driver.l7policy_delete(self.ref_l7policy)

        self.assertEqual((self.l7policy_id, 'l7policy_delete'),
                         self.driver.driver.driverconfig[self.l7policy_id])

    def test_l7policy_update(self):
        self.driver.l7policy_update(self.ref_l7policy, self.ref_l7policy)

        self.assertEqual((self.ref_l7policy, 'l7policy_update'),
                         self.driver.driver.driverconfig[self.l7policy_id])

    def test_l7rule_create(self):
        self.driver.l7rule_create(self.ref_l7rule)

        self.assertEqual((self.ref_l7rule, 'l7rule_create'),
                         self.driver.driver.driverconfig[self.l7rule_id])

    def test_l7rule_delete(self):
        self.driver.l7rule_delete(self.ref_l7rule)

        self.assertEqual((self.l7rule_id, 'l7rule_delete'),
                         self.driver.driver.driverconfig[self.l7rule_id])

    def test_l7rule_update(self):
        self.driver.l7rule_update(self.ref_l7rule, self.ref_l7rule)

        self.assertEqual((self.ref_l7rule, 'l7rule_update'),
                         self.driver.driver.driverconfig[self.l7rule_id])

    def test_get_supported_flavor_metadata(self):
        metadata = self.driver.get_supported_flavor_metadata()

        self.assertEqual(self.ref_flavor_metadata, metadata)

    def test_validate_flavor(self):
        self.driver.validate_flavor(self.ref_flavor_metadata)

        flavor_hash = hash(frozenset(self.ref_flavor_metadata.items()))
        self.assertEqual((self.ref_flavor_metadata, 'validate_flavor'),
                         self.driver.driver.driverconfig[flavor_hash])
