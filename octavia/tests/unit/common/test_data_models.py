# Copyright 2018 Rackspace US Inc.  All rights reserved.
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

import copy
import datetime

from oslo_utils import uuidutils

from octavia.common import constants
from octavia.common import data_models
import octavia.tests.unit.base as base


class TestDataModels(base.TestCase):

    def setUp(self):

        self.LB_ID = uuidutils.generate_uuid()
        self.PROJECT_ID = uuidutils.generate_uuid()
        self.SERVER_GROUP_ID = uuidutils.generate_uuid()
        self.CREATED_AT = datetime.datetime.now()
        self.UPDATED_AT = datetime.datetime.utcnow()
        self.VIP_IP = '192.0.2.10'
        self.VIP_SUBNET_ID = uuidutils.generate_uuid()
        self.VIP_NETWORK_ID = uuidutils.generate_uuid()
        self.VIP_PORT_ID = uuidutils.generate_uuid()
        self.VIP_QOS_ID = uuidutils.generate_uuid()
        self.POOL_ID = uuidutils.generate_uuid()
        self.AMP_ID = uuidutils.generate_uuid()
        self.COMPUTE_ID = uuidutils.generate_uuid()
        self.IMAGE_ID = uuidutils.generate_uuid()

        self.LB_obj = data_models.LoadBalancer(
            id=self.LB_ID,
            project_id=self.PROJECT_ID,
            name='test-lb',
            description='test-lb-description',
            provisioning_status='great',
            operating_status='even-better',
            enabled=True,
            vip=None,
            vrrp_group=1,
            topology='infinite',
            listeners=[],
            amphorae=[],
            pools=[],
            server_group_id=self.SERVER_GROUP_ID,
            created_at=self.CREATED_AT,
            updated_at=self.UPDATED_AT)

        self.VIP_obj = data_models.Vip(
            load_balancer_id=self.LB_ID,
            ip_address=self.VIP_IP,
            subnet_id=self.VIP_SUBNET_ID,
            network_id=self.VIP_NETWORK_ID,
            port_id=self.VIP_PORT_ID,
            qos_policy_id=self.VIP_QOS_ID)

        self.POOL_obj = data_models.Pool(
            id=self.POOL_ID,
            project_id=self.PROJECT_ID,
            name='test-pool',
            description='test-pool-description',
            load_balancer_id=self.LB_ID,
            load_balancer=None,
            protocol='avian',
            lb_algorithm='UseAllofThem',
            enabled=True,
            provisioning_status='great',
            operating_status='even-better',
            members=[],
            health_monitor=None,
            session_persistence=None,
            listeners=[],
            l7policies=[],
            created_at=self.CREATED_AT,
            updated_at=self.UPDATED_AT)

        self.SP_obj = data_models.SessionPersistence(
            pool_id=self.POOL_ID,
            type='adhesive',
            cookie_name='chocolate',
            pool=None)

        self.AMP_obj = data_models.Amphora(
            id=self.AMP_ID,
            load_balancer_id=self.LB_ID,
            compute_id=self.COMPUTE_ID,
            status=constants.ACTIVE,
            lb_network_ip=None,
            vrrp_ip=None,
            ha_ip=None,
            vrrp_port_id=None,
            ha_port_id=self.VIP_PORT_ID,
            load_balancer=self.LB_obj,
            role=constants.ROLE_MASTER,
            cert_expiration=None,
            cert_busy=False,
            vrrp_interface=None,
            vrrp_id=None,
            vrrp_priority=constants.ROLE_MASTER_PRIORITY,
            cached_zone=None,
            created_at=self.CREATED_AT,
            updated_at=self.UPDATED_AT,
            image_id=self.IMAGE_ID
        )

        super(TestDataModels, self).setUp()

    def test_LoadBalancer_update(self):

        new_id = uuidutils.generate_uuid()
        new_project_id = uuidutils.generate_uuid()
        new_server_group_id = uuidutils.generate_uuid()
        new_created_at = self.CREATED_AT + datetime.timedelta(minutes=5)
        new_updated_at = self.UPDATED_AT + datetime.timedelta(minutes=10)
        new_name = 'new-test-lb'
        new_description = 'new-test-lb-description'
        new_provisioning_status = 'new-great'
        new_operating_status = 'new-even-better'
        new_enabled = False
        new_vrrp_group = 2
        new_topology = 'new-infinite'

        reference_LB_obj = data_models.LoadBalancer(
            id=new_id,
            project_id=new_project_id,
            name=new_name,
            description=new_description,
            provisioning_status=new_provisioning_status,
            operating_status=new_operating_status,
            enabled=new_enabled,
            vip=None,
            vrrp_group=new_vrrp_group,
            topology=new_topology,
            listeners=[],
            amphorae=[],
            pools=[],
            server_group_id=new_server_group_id,
            created_at=new_created_at,
            updated_at=new_updated_at)

        update_dict = {
            'id': new_id,
            'project_id': new_project_id,
            'name': new_name,
            'description': new_description,
            'provisioning_status': new_provisioning_status,
            'operating_status': new_operating_status,
            'enabled': new_enabled,
            'vrrp_group': new_vrrp_group,
            'topology': new_topology,
            'server_group_id': new_server_group_id,
            'created_at': new_created_at,
            'updated_at': new_updated_at
        }

        test_LB_obj = copy.deepcopy(self.LB_obj)

        test_LB_obj.update(update_dict)

        self.assertEqual(reference_LB_obj, test_LB_obj)

    def test_LoadBalancer_update_add_vip(self):

        new_ip = '192.0.2.44'
        new_subnet_id = uuidutils.generate_uuid()
        new_network_id = uuidutils.generate_uuid()
        new_port_id = uuidutils.generate_uuid()
        new_qos_id = uuidutils.generate_uuid()

        reference_VIP_obj = data_models.Vip(
            load_balancer_id=self.LB_ID,
            ip_address=new_ip,
            subnet_id=new_subnet_id,
            network_id=new_network_id,
            port_id=new_port_id,
            load_balancer=None,
            qos_policy_id=new_qos_id
        )

        update_dict = {
            'vip': {
                'ip_address': new_ip,
                'subnet_id': new_subnet_id,
                'network_id': new_network_id,
                'port_id': new_port_id,
                'load_balancer': None,
                'qos_policy_id': new_qos_id
            }
        }

        test_LB_obj = copy.deepcopy(self.LB_obj)

        test_LB_obj.update(update_dict)

        self.assertEqual(reference_VIP_obj, test_LB_obj.vip)

    def test_LoadBalancer_update_vip_update(self):

        new_id = uuidutils.generate_uuid()
        new_ip = '192.0.2.44'
        new_subnet_id = uuidutils.generate_uuid()
        new_network_id = uuidutils.generate_uuid()
        new_port_id = uuidutils.generate_uuid()
        new_qos_id = uuidutils.generate_uuid()

        reference_VIP_obj = data_models.Vip(
            load_balancer_id=new_id,
            ip_address=new_ip,
            subnet_id=new_subnet_id,
            network_id=new_network_id,
            port_id=new_port_id,
            qos_policy_id=new_qos_id
        )

        update_dict = {
            'vip': {
                'load_balancer_id': new_id,
                'ip_address': new_ip,
                'subnet_id': new_subnet_id,
                'network_id': new_network_id,
                'port_id': new_port_id,
                'qos_policy_id': new_qos_id
            }
        }

        test_LB_obj = copy.deepcopy(self.LB_obj)

        test_LB_obj.vip = copy.deepcopy(self.VIP_obj)

        test_LB_obj.update(update_dict)

        self.assertEqual(reference_VIP_obj, test_LB_obj.vip)

    def test_Pool_update(self):

        new_id = uuidutils.generate_uuid()
        new_project_id = uuidutils.generate_uuid()
        new_name = 'new-test-pool'
        new_description = 'new-test-pool-description'
        new_lb_id = uuidutils.generate_uuid()
        new_protocol = 'sneaker'
        new_lb_algorithm = 'JustOne'
        new_enabled = False
        new_provisioning_status = 'new-great'
        new_operating_status = 'new-even-better'
        new_created_at = self.CREATED_AT + datetime.timedelta(minutes=5)
        new_updated_at = self.UPDATED_AT + datetime.timedelta(minutes=10)

        reference_Pool_obj = data_models.Pool(
            id=new_id,
            project_id=new_project_id,
            name=new_name,
            description=new_description,
            load_balancer_id=new_lb_id,
            protocol=new_protocol,
            lb_algorithm=new_lb_algorithm,
            enabled=new_enabled,
            provisioning_status=new_provisioning_status,
            operating_status=new_operating_status,
            members=[],
            health_monitor=None,
            session_persistence=None,
            listeners=[],
            l7policies=[],
            created_at=new_created_at,
            updated_at=new_updated_at)

        update_dict = {
            'id': new_id,
            'project_id': new_project_id,
            'name': new_name,
            'description': new_description,
            'load_balancer_id': new_lb_id,
            'protocol': new_protocol,
            'lb_algorithm': new_lb_algorithm,
            'enabled': new_enabled,
            'provisioning_status': new_provisioning_status,
            'operating_status': new_operating_status,
            'created_at': new_created_at,
            'updated_at': new_updated_at}

        test_Pool_obj = copy.deepcopy(self.POOL_obj)

        test_Pool_obj.update(update_dict)

        self.assertEqual(reference_Pool_obj, test_Pool_obj)

    def test_Pool_update_add_SP(self):

        new_type = 'glue'
        new_cookie_name = 'chip'

        reference_SP_obj = data_models.SessionPersistence(
            pool_id=self.POOL_ID,
            type=new_type,
            cookie_name=new_cookie_name,
            pool=None)

        update_dict = {
            'session_persistence': {
                'type': new_type,
                'cookie_name': new_cookie_name
            }
        }

        test_Pool_obj = copy.deepcopy(self.POOL_obj)

        test_Pool_obj.update(update_dict)

        self.assertEqual(reference_SP_obj, test_Pool_obj.session_persistence)

    def test_Pool_update_delete_SP(self):

        update_dict = {'session_persistence': {}}

        test_Pool_obj = copy.deepcopy(self.POOL_obj)

        test_Pool_obj.session_persistence = copy.deepcopy(self.SP_obj)

        test_Pool_obj.session_persistence.pool = test_Pool_obj

        test_Pool_obj.update(update_dict)

        self.assertIsNone(test_Pool_obj.session_persistence)

    def test_Pool_update_SP_update(self):

        new_type = 'glue'
        new_cookie_name = 'chip'

        update_dict = {
            'session_persistence': {
                'type': new_type,
                'cookie_name': new_cookie_name
            }
        }

        test_Pool_obj = copy.deepcopy(self.POOL_obj)

        reference_SP_obj = data_models.SessionPersistence(
            pool_id=self.POOL_ID,
            type=new_type,
            cookie_name=new_cookie_name,
            pool=test_Pool_obj)

        test_Pool_obj.session_persistence = copy.deepcopy(self.SP_obj)

        test_Pool_obj.session_persistence.pool = test_Pool_obj

        test_Pool_obj.update(update_dict)

        self.assertEqual(reference_SP_obj, test_Pool_obj.session_persistence)

    def test_Amphora_update(self):

        new_id = uuidutils.generate_uuid()
        new_status = constants.ERROR
        new_role = constants.ROLE_BACKUP
        new_vrrp_priority = constants.ROLE_BACKUP_PRIORITY
        new_created_at = self.CREATED_AT + datetime.timedelta(minutes=5)
        new_updated_at = self.UPDATED_AT + datetime.timedelta(minutes=10)
        new_image_id = uuidutils.generate_uuid()

        update_dict = {
            'id': new_id,
            'status': new_status,
            'role': new_role,
            'vrrp_priority': new_vrrp_priority,
            'created_at': new_created_at,
            'updated_at': new_updated_at,
            'image_id': new_image_id
        }

        test_Amp_obj = copy.deepcopy(self.AMP_obj)

        reference_Amp_obj = data_models.Amphora(
            id=new_id,
            load_balancer_id=self.LB_ID,
            compute_id=self.COMPUTE_ID,
            status=new_status,
            lb_network_ip=None,
            vrrp_ip=None,
            ha_ip=None,
            vrrp_port_id=None,
            ha_port_id=self.VIP_PORT_ID,
            load_balancer=self.LB_obj,
            role=new_role,
            cert_expiration=None,
            cert_busy=False,
            vrrp_interface=None,
            vrrp_id=None,
            vrrp_priority=constants.ROLE_BACKUP_PRIORITY,
            cached_zone=None,
            created_at=new_created_at,
            updated_at=new_updated_at,
            image_id=new_image_id
        )

        test_Amp_obj.update(update_dict)

        self.assertEqual(reference_Amp_obj, test_Amp_obj)
