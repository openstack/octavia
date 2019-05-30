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

import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.common import constants
import octavia.common.context
from octavia.common import data_models
from octavia.common import exceptions
from octavia.db import repositories
from octavia.tests.functional.api.v2 import base


class TestHealthMonitor(base.BaseAPITest):

    root_tag = 'healthmonitor'
    root_tag_list = 'healthmonitors'
    root_tag_links = 'healthmonitors_links'

    def setUp(self):
        super(TestHealthMonitor, self).setUp()
        self.lb = self.create_load_balancer(
            uuidutils.generate_uuid()).get('loadbalancer')
        self.lb_id = self.lb.get('id')
        self.project_id = self.lb.get('project_id')
        self.set_lb_status(self.lb_id)
        self.listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80,
            self.lb_id).get('listener')
        self.listener_id = self.listener.get('id')
        self.set_lb_status(self.lb_id)
        self.pool = self.create_pool(self.lb_id, constants.PROTOCOL_HTTP,
                                     constants.LB_ALGORITHM_ROUND_ROBIN)
        self.pool_id = self.pool.get('pool').get('id')
        self.set_lb_status(self.lb_id)
        self.pool_with_listener = self.create_pool(
            self.lb_id, constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN, listener_id=self.listener_id)
        self.pool_with_listener_id = (
            self.pool_with_listener.get('pool').get('id'))
        self.set_lb_status(self.lb_id)
        self.pool_repo = repositories.PoolRepository()
        self._setup_udp_lb_resources()

    def _setup_udp_lb_resources(self):
        self.udp_lb = self.create_load_balancer(uuidutils.generate_uuid()).get(
            'loadbalancer')
        self.udp_lb_id = self.udp_lb.get('id')
        self.set_lb_status(self.udp_lb_id)

        self.udp_listener = self.create_listener(
            constants.PROTOCOL_UDP, 8888,
            self.udp_lb_id).get('listener')
        self.udp_listener_id = self.udp_listener.get('id')
        self.set_lb_status(self.udp_lb_id)

        self.udp_pool_with_listener = self.create_pool(
            None, constants.PROTOCOL_UDP, constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=self.udp_listener_id)
        self.udp_pool_with_listener_id = (
            self.udp_pool_with_listener.get('pool').get('id'))
        self.set_lb_status(self.udp_lb_id)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(
            group='api_settings',
            udp_connect_min_interval_health_monitor='3')

    def test_get(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1, tags=['test_tag']).get(self.root_tag)
        # Set status to ACTIVE/ONLINE because set_lb_status did it in the db
        api_hm['provisioning_status'] = constants.ACTIVE
        api_hm['operating_status'] = constants.ONLINE
        api_hm.pop('updated_at')
        self.set_lb_status(self.lb_id)
        response = self.get(self.HM_PATH.format(
            healthmonitor_id=api_hm.get('id'))).json.get(self.root_tag)
        response.pop('updated_at')
        self.assertEqual(api_hm, response)

    def test_get_authorized(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        # Set status to ACTIVE/ONLINE because set_lb_status did it in the db
        api_hm['provisioning_status'] = constants.ACTIVE
        api_hm['operating_status'] = constants.ONLINE
        api_hm.pop('updated_at')
        self.set_lb_status(self.lb_id)

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):

                response = self.get(self.HM_PATH.format(
                    healthmonitor_id=api_hm.get('id'))).json.get(self.root_tag)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        response.pop('updated_at')
        self.assertEqual(api_hm, response)

    def test_get_not_authorized(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        # Set status to ACTIVE/ONLINE because set_lb_status did it in the db
        api_hm['provisioning_status'] = constants.ACTIVE
        api_hm['operating_status'] = constants.ONLINE
        api_hm.pop('updated_at')
        self.set_lb_status(self.lb_id)

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            response = self.get(self.HM_PATH.format(
                healthmonitor_id=api_hm.get('id')), status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response.json)

    def test_get_deleted_gives_404(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)

        self.set_object_status(self.health_monitor_repo, api_hm.get('id'),
                               provisioning_status=constants.DELETED)
        self.get(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                 status=404)

    def test_bad_get(self):
        self.get(self.HM_PATH.format(
            healthmonitor_id=uuidutils.generate_uuid()), status=404)

    def test_get_all(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1, tags=['test_tag']).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        hms = self.get(self.HMS_PATH).json.get(self.root_tag_list)
        self.assertIsInstance(hms, list)
        self.assertEqual(1, len(hms))
        self.assertEqual(api_hm.get('id'), hms[0].get('id'))
        self.assertEqual(api_hm['tags'], hms[0]['tags'])

    def test_get_all_not_authorized(self):
        self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)

        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            hms = self.get(self.HMS_PATH, status=403).json

        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, hms)

    def test_get_all_admin(self):
        project_id = uuidutils.generate_uuid()
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(), name='lb1',
                                        project_id=project_id)
        lb1_id = lb1.get('loadbalancer').get('id')
        self.set_lb_status(lb1_id)
        pool1 = self.create_pool(
            lb1_id, constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN).get('pool')
        self.set_lb_status(lb1_id)
        pool2 = self.create_pool(
            lb1_id, constants.PROTOCOL_HTTPS,
            constants.LB_ALGORITHM_ROUND_ROBIN).get('pool')
        self.set_lb_status(lb1_id)
        pool3 = self.create_pool(
            lb1_id, constants.PROTOCOL_TCP,
            constants.LB_ALGORITHM_ROUND_ROBIN).get('pool')
        self.set_lb_status(lb1_id)
        hm1 = self.create_health_monitor(
            pool1.get('id'), constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(lb1_id)
        hm2 = self.create_health_monitor(
            pool2.get('id'), constants.HEALTH_MONITOR_PING,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(lb1_id)
        hm3 = self.create_health_monitor(
            pool3.get('id'), constants.HEALTH_MONITOR_TLS_HELLO,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(lb1_id)
        hms = self.get(self.HMS_PATH).json.get(self.root_tag_list)
        self.assertEqual(3, len(hms))
        hm_id_protocols = [(hm.get('id'), hm.get('type')) for hm in hms]
        self.assertIn((hm1.get('id'), hm1.get('type')), hm_id_protocols)
        self.assertIn((hm2.get('id'), hm2.get('type')), hm_id_protocols)
        self.assertIn((hm3.get('id'), hm3.get('type')), hm_id_protocols)

    def test_get_all_non_admin(self):
        project_id = uuidutils.generate_uuid()
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(), name='lb1',
                                        project_id=project_id)
        lb1_id = lb1.get('loadbalancer').get('id')
        self.set_lb_status(lb1_id)
        pool1 = self.create_pool(
            lb1_id, constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN).get('pool')
        self.set_lb_status(lb1_id)
        pool2 = self.create_pool(
            lb1_id, constants.PROTOCOL_HTTPS,
            constants.LB_ALGORITHM_ROUND_ROBIN).get('pool')
        self.set_lb_status(lb1_id)
        self.create_health_monitor(
            pool1.get('id'), constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(lb1_id)
        self.create_health_monitor(
            pool2.get('id'), constants.HEALTH_MONITOR_PING,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(lb1_id)
        hm3 = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_TCP,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)

        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings',
                         auth_strategy=constants.KEYSTONE)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               hm3['project_id']):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                hms = self.get(self.HMS_PATH).json.get(self.root_tag_list)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        self.assertEqual(1, len(hms))
        hm_id_protocols = [(hm.get('id'), hm.get('type')) for hm in hms]
        self.assertIn((hm3.get('id'), hm3.get('type')), hm_id_protocols)

    def test_get_all_non_admin_global_observer(self):
        project_id = uuidutils.generate_uuid()
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(), name='lb1',
                                        project_id=project_id)
        lb1_id = lb1.get('loadbalancer').get('id')
        self.set_lb_status(lb1_id)
        pool1 = self.create_pool(
            lb1_id, constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN).get('pool')
        self.set_lb_status(lb1_id)
        pool2 = self.create_pool(
            lb1_id, constants.PROTOCOL_HTTPS,
            constants.LB_ALGORITHM_ROUND_ROBIN).get('pool')
        self.set_lb_status(lb1_id)
        pool3 = self.create_pool(
            lb1_id, constants.PROTOCOL_TCP,
            constants.LB_ALGORITHM_ROUND_ROBIN).get('pool')
        self.set_lb_status(lb1_id)
        hm1 = self.create_health_monitor(
            pool1.get('id'), constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(lb1_id)
        hm2 = self.create_health_monitor(
            pool2.get('id'), constants.HEALTH_MONITOR_PING,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(lb1_id)
        hm3 = self.create_health_monitor(
            pool3.get('id'), constants.HEALTH_MONITOR_TCP,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(lb1_id)

        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings',
                         auth_strategy=constants.KEYSTONE)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               hm3['project_id']):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_global_observer'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):

                hms = self.get(self.HMS_PATH).json.get(self.root_tag_list)

        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(3, len(hms))
        hm_id_protocols = [(hm.get('id'), hm.get('type')) for hm in hms]
        self.assertIn((hm1.get('id'), hm1.get('type')), hm_id_protocols)
        self.assertIn((hm2.get('id'), hm2.get('type')), hm_id_protocols)
        self.assertIn((hm3.get('id'), hm3.get('type')), hm_id_protocols)

    def test_get_all_hides_deleted(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)

        response = self.get(self.HMS_PATH)
        objects = response.json.get(self.root_tag_list)
        self.assertEqual(len(objects), 1)
        self.set_object_status(self.health_monitor_repo, api_hm.get('id'),
                               provisioning_status=constants.DELETED)
        response = self.get(self.HMS_PATH)
        objects = response.json.get(self.root_tag_list)
        self.assertEqual(len(objects), 0)

    def test_get_by_project_id(self):
        project1_id = uuidutils.generate_uuid()
        project2_id = uuidutils.generate_uuid()
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(), name='lb1',
                                        project_id=project1_id)
        lb1_id = lb1.get('loadbalancer').get('id')
        self.set_lb_status(lb1_id)
        lb2 = self.create_load_balancer(uuidutils.generate_uuid(), name='lb2',
                                        project_id=project2_id)
        lb2_id = lb2.get('loadbalancer').get('id')
        self.set_lb_status(lb2_id)
        pool1 = self.create_pool(
            lb1_id, constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN).get('pool')
        self.set_lb_status(lb1_id)
        pool2 = self.create_pool(
            lb1_id, constants.PROTOCOL_HTTPS,
            constants.LB_ALGORITHM_ROUND_ROBIN).get('pool')
        self.set_lb_status(lb1_id)
        pool3 = self.create_pool(
            lb2_id, constants.PROTOCOL_TCP,
            constants.LB_ALGORITHM_ROUND_ROBIN).get('pool')
        self.set_lb_status(lb2_id)
        hm1 = self.create_health_monitor(
            pool1.get('id'), constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(lb1_id)
        hm2 = self.create_health_monitor(
            pool2.get('id'), constants.HEALTH_MONITOR_PING,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(lb1_id)
        hm3 = self.create_health_monitor(
            pool3.get('id'), constants.HEALTH_MONITOR_TCP,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(lb2_id)
        hms = self.get(
            self.HMS_PATH,
            params={'project_id': project1_id}).json.get(self.root_tag_list)

        self.assertEqual(2, len(hms))
        hm_id_protocols = [(hm.get('id'), hm.get('type')) for hm in hms]
        self.assertIn((hm1.get('id'), hm1.get('type')), hm_id_protocols)
        self.assertIn((hm2.get('id'), hm2.get('type')), hm_id_protocols)
        hms = self.get(
            self.HMS_PATH,
            params={'project_id': project2_id}).json.get(self.root_tag_list)
        self.assertEqual(1, len(hms))
        hm_id_protocols = [(hm.get('id'), hm.get('type')) for hm in hms]
        self.assertIn((hm3.get('id'), hm3.get('type')), hm_id_protocols)

    def test_get_all_sorted(self):
        pool1 = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            name='pool1').get('pool')
        self.set_lb_status(self.lb_id)
        pool2 = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            name='pool2').get('pool')
        self.set_lb_status(self.lb_id)
        pool3 = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            name='pool3').get('pool')
        self.set_lb_status(self.lb_id)
        self.create_health_monitor(
            pool1.get('id'), constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1, name='hm1').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_health_monitor(
            pool2.get('id'), constants.HEALTH_MONITOR_PING,
            1, 1, 1, 1, name='hm2').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_health_monitor(
            pool3.get('id'), constants.HEALTH_MONITOR_TCP,
            1, 1, 1, 1, name='hm3').get(self.root_tag)
        self.set_lb_status(self.lb_id)

        response = self.get(self.HMS_PATH, params={'sort': 'name:desc'})
        hms_desc = response.json.get(self.root_tag_list)
        response = self.get(self.HMS_PATH, params={'sort': 'name:asc'})
        hms_asc = response.json.get(self.root_tag_list)

        self.assertEqual(3, len(hms_desc))
        self.assertEqual(3, len(hms_asc))

        hm_id_names_desc = [(hm.get('id'), hm.get('name')) for hm in hms_desc]
        hm_id_names_asc = [(hm.get('id'), hm.get('name')) for hm in hms_asc]
        self.assertEqual(hm_id_names_asc, list(reversed(hm_id_names_desc)))

    def test_get_all_limited(self):
        pool1 = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            name='pool1').get('pool')
        self.set_lb_status(self.lb_id)
        pool2 = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            name='pool2').get('pool')
        self.set_lb_status(self.lb_id)
        pool3 = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            name='pool3').get('pool')
        self.set_lb_status(self.lb_id)
        self.create_health_monitor(
            pool1.get('id'), constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1, name='hm1').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_health_monitor(
            pool2.get('id'), constants.HEALTH_MONITOR_PING,
            1, 1, 1, 1, name='hm2').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_health_monitor(
            pool3.get('id'), constants.HEALTH_MONITOR_TCP,
            1, 1, 1, 1, name='hm3').get(self.root_tag)
        self.set_lb_status(self.lb_id)

        # First two -- should have 'next' link
        first_two = self.get(self.HMS_PATH, params={'limit': 2}).json
        objs = first_two[self.root_tag_list]
        links = first_two[self.root_tag_links]
        self.assertEqual(2, len(objs))
        self.assertEqual(1, len(links))
        self.assertEqual('next', links[0]['rel'])

        # Third + off the end -- should have previous link
        third = self.get(self.HMS_PATH, params={
            'limit': 2,
            'marker': first_two[self.root_tag_list][1]['id']}).json
        objs = third[self.root_tag_list]
        links = third[self.root_tag_links]
        self.assertEqual(1, len(objs))
        self.assertEqual(1, len(links))
        self.assertEqual('previous', links[0]['rel'])

        # Middle -- should have both links
        middle = self.get(self.HMS_PATH, params={
            'limit': 1,
            'marker': first_two[self.root_tag_list][0]['id']}).json
        objs = middle[self.root_tag_list]
        links = middle[self.root_tag_links]
        self.assertEqual(1, len(objs))
        self.assertEqual(2, len(links))
        self.assertItemsEqual(['previous', 'next'], [l['rel'] for l in links])

    def test_get_all_fields_filter(self):
        pool1 = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            name='pool1').get('pool')
        self.set_lb_status(self.lb_id)
        pool2 = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            name='pool2').get('pool')
        self.set_lb_status(self.lb_id)
        pool3 = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            name='pool3').get('pool')
        self.set_lb_status(self.lb_id)
        self.create_health_monitor(
            pool1.get('id'), constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1, name='hm1').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_health_monitor(
            pool2.get('id'), constants.HEALTH_MONITOR_PING,
            1, 1, 1, 1, name='hm2').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_health_monitor(
            pool3.get('id'), constants.HEALTH_MONITOR_TCP,
            1, 1, 1, 1, name='hm3').get(self.root_tag)
        self.set_lb_status(self.lb_id)

        hms = self.get(self.HMS_PATH, params={
            'fields': ['id', 'project_id']}).json
        for hm in hms['healthmonitors']:
            self.assertIn(u'id', hm)
            self.assertIn(u'project_id', hm)
            self.assertNotIn(u'description', hm)

    def test_get_one_fields_filter(self):
        pool1 = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            name='pool1').get('pool')
        self.set_lb_status(self.lb_id)

        self.set_lb_status(self.lb_id)
        hm1 = self.create_health_monitor(
            pool1.get('id'), constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1, name='hm1').get(self.root_tag)
        self.set_lb_status(self.lb_id)

        hm = self.get(
            self.HM_PATH.format(healthmonitor_id=hm1.get('id')),
            params={'fields': ['id', 'project_id']}).json.get(self.root_tag)
        self.assertIn(u'id', hm)
        self.assertIn(u'project_id', hm)
        self.assertNotIn(u'description', hm)

    def test_get_all_filter(self):
        pool1 = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            name='pool1').get('pool')
        self.set_lb_status(self.lb_id)
        pool2 = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            name='pool2').get('pool')
        self.set_lb_status(self.lb_id)
        pool3 = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            name='pool3').get('pool')
        self.set_lb_status(self.lb_id)
        hm1 = self.create_health_monitor(
            pool1.get('id'), constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1, name='hm1').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_health_monitor(
            pool2.get('id'), constants.HEALTH_MONITOR_PING,
            1, 1, 1, 1, name='hm2').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_health_monitor(
            pool3.get('id'), constants.HEALTH_MONITOR_TCP,
            1, 1, 1, 1, name='hm3').get(self.root_tag)
        self.set_lb_status(self.lb_id)

        hms = self.get(self.HMS_PATH, params={
            'id': hm1['id']}).json
        self.assertEqual(1, len(hms['healthmonitors']))
        self.assertEqual(hm1['id'],
                         hms['healthmonitors'][0]['id'])

    def test_get_all_tags_filter(self):
        pool1 = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            name='pool1').get('pool')
        self.set_lb_status(self.lb_id)
        pool2 = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            name='pool2').get('pool')
        self.set_lb_status(self.lb_id)
        pool3 = self.create_pool(
            self.lb_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            name='pool3').get('pool')
        self.set_lb_status(self.lb_id)
        hm1 = self.create_health_monitor(
            pool1.get('id'), constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1, tags=['test_tag1', 'test_tag2']).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        hm2 = self.create_health_monitor(
            pool2.get('id'), constants.HEALTH_MONITOR_PING,
            1, 1, 1, 1, tags=['test_tag2', 'test_tag3']).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        hm3 = self.create_health_monitor(
            pool3.get('id'), constants.HEALTH_MONITOR_TCP,
            1, 1, 1, 1, tags=['test_tag4', 'test_tag5']).get(self.root_tag)
        self.set_lb_status(self.lb_id)

        hms = self.get(
            self.HMS_PATH,
            params={'tags': 'test_tag2'}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(hms, list)
        self.assertEqual(2, len(hms))
        self.assertEqual(
            [hm1.get('id'), hm2.get('id')],
            [hm.get('id') for hm in hms]
        )

        hms = self.get(
            self.HMS_PATH,
            params={'tags': ['test_tag2', 'test_tag3']}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(hms, list)
        self.assertEqual(1, len(hms))
        self.assertEqual(
            [hm2.get('id')],
            [hm.get('id') for hm in hms]
        )

        hms = self.get(
            self.HMS_PATH,
            params={'tags-any': 'test_tag2'}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(hms, list)
        self.assertEqual(2, len(hms))
        self.assertEqual(
            [hm1.get('id'), hm2.get('id')],
            [hm.get('id') for hm in hms]
        )

        hms = self.get(
            self.HMS_PATH,
            params={'not-tags': 'test_tag2'}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(hms, list)
        self.assertEqual(1, len(hms))
        self.assertEqual(
            [hm3.get('id')],
            [hm.get('id') for hm in hms]
        )

        hms = self.get(
            self.HMS_PATH,
            params={'not-tags-any': ['test_tag2', 'test_tag4']}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(hms, list)
        self.assertEqual(0, len(hms))

        hms = self.get(
            self.HMS_PATH,
            params={'tags': 'test_tag2',
                    'tags-any': ['test_tag1', 'test_tag3']}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(hms, list)
        self.assertEqual(2, len(hms))
        self.assertEqual(
            [hm1.get('id'), hm2.get('id')],
            [hm.get('id') for hm in hms]
        )

        hms = self.get(
            self.HMS_PATH,
            params={'tags': 'test_tag2', 'not-tags': 'test_tag2'}
        ).json.get(self.root_tag_list)
        self.assertIsInstance(hms, list)
        self.assertEqual(0, len(hms))

    def test_empty_get_all(self):
        response = self.get(self.HMS_PATH).json.get(self.root_tag_list)
        self.assertIsInstance(response, list)
        self.assertEqual(0, len(response))

    def test_create_http_monitor_with_relative_path(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1, url_path="/").get(self.root_tag)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.ACTIVE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_CREATE,
            hm_op_status=constants.OFFLINE)

    def test_create_http_monitor_with_url_path(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1, url_path="/v2/api/index").get(self.root_tag)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.ACTIVE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_CREATE,
            hm_op_status=constants.OFFLINE)

    def test_create_sans_listener(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.ACTIVE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_CREATE,
            hm_op_status=constants.OFFLINE)
        self.set_lb_status(self.lb_id)
        self.assertEqual(constants.HEALTH_MONITOR_HTTP, api_hm.get('type'))
        self.assertEqual(1, api_hm.get('delay'))
        self.assertEqual(1, api_hm.get('timeout'))
        self.assertEqual(1, api_hm.get('max_retries_down'))
        self.assertEqual(1, api_hm.get('max_retries'))
        # Verify optional field defaults
        self.assertEqual('GET', api_hm.get('http_method'))
        self.assertEqual('/', api_hm.get('url_path'))
        self.assertEqual('200', api_hm.get('expected_codes'))

    def test_create_http_full(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1, admin_state_up=False, expected_codes='200',
            http_method='GET', name='Test HM', url_path='/').get(self.root_tag)
        self.assertEqual(constants.HEALTH_MONITOR_HTTP, api_hm.get('type'))
        self.assertEqual(1, api_hm.get('delay'))
        self.assertEqual(1, api_hm.get('timeout'))
        self.assertEqual(1, api_hm.get('max_retries_down'))
        self.assertEqual(1, api_hm.get('max_retries'))
        self.assertFalse(api_hm.get('admin_state_up'))
        self.assertEqual('Test HM', api_hm.get('name'))
        self.assertEqual('GET', api_hm.get('http_method'))
        self.assertEqual('/', api_hm.get('url_path'))
        self.assertEqual('200', api_hm.get('expected_codes'))

    def test_create_https_full(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTPS,
            1, 1, 1, 1, admin_state_up=False, expected_codes='200',
            http_method='GET', name='Test HM', url_path='/').get(self.root_tag)
        self.assertEqual(constants.HEALTH_MONITOR_HTTPS, api_hm.get('type'))
        self.assertEqual(1, api_hm.get('delay'))
        self.assertEqual(1, api_hm.get('timeout'))
        self.assertEqual(1, api_hm.get('max_retries_down'))
        self.assertEqual(1, api_hm.get('max_retries'))
        self.assertFalse(api_hm.get('admin_state_up'))
        self.assertEqual('Test HM', api_hm.get('name'))
        self.assertEqual('GET', api_hm.get('http_method'))
        self.assertEqual('/', api_hm.get('url_path'))
        self.assertEqual('200', api_hm.get('expected_codes'))

    def test_create_udp_case(self):
        api_hm = self.create_health_monitor(
            self.udp_pool_with_listener_id,
            constants.HEALTH_MONITOR_UDP_CONNECT,
            3, 1, 1, 1).get(self.root_tag)
        self.assert_correct_status(
            lb_id=self.udp_lb_id, listener_id=self.udp_listener_id,
            pool_id=self.udp_pool_with_listener_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_CREATE,
            hm_op_status=constants.OFFLINE)
        self.set_lb_status(self.udp_lb_id)
        self.assertEqual(constants.HEALTH_MONITOR_UDP_CONNECT,
                         api_hm.get('type'))
        self.assertEqual(3, api_hm.get('delay'))
        self.assertEqual(1, api_hm.get('timeout'))
        self.assertEqual(1, api_hm.get('max_retries_down'))
        self.assertEqual(1, api_hm.get('max_retries'))
        # Verify the L7 fields is None
        self.assertIsNone(api_hm.get('http_method'))
        self.assertIsNone(api_hm.get('url_path'))
        self.assertIsNone(api_hm.get('expected_codes'))

    def test_udp_case_when_udp_connect_min_interval_health_monitor_set(self):
        # negative case first
        req_dict = {'pool_id': self.udp_pool_with_listener_id,
                    'type': constants.HEALTH_MONITOR_UDP_CONNECT,
                    'delay': 1,
                    'timeout': 1,
                    'max_retries_down': 1,
                    'max_retries': 1}
        res = self.post(self.HMS_PATH, self._build_body(req_dict), status=400,
                        expect_errors=True)
        expect_error_msg = ("Validation failure: The request delay value 1 "
                            "should be larger than 3 for %s health monitor "
                            "type.") % constants.HEALTH_MONITOR_UDP_CONNECT

        self.assertEqual(expect_error_msg, res.json['faultstring'])
        self.assert_correct_status(
            lb_id=self.udp_lb_id, listener_id=self.udp_listener_id,
            pool_id=self.udp_pool_with_listener_id)

        # pass cases
        self.conf.config(
            group='api_settings',
            udp_connect_min_interval_health_monitor='-3')
        res = self.post(self.HMS_PATH, self._build_body(req_dict))
        self.assert_correct_status(
            lb_id=self.udp_lb_id, listener_id=self.udp_listener_id,
            pool_id=self.udp_pool_with_listener_id,
            hm_id=res.json['healthmonitor']['id'],
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_CREATE,
            hm_op_status=constants.OFFLINE)

    def test_negative_create_udp_case(self):
        req_dict = {'pool_id': self.udp_pool_with_listener_id,
                    'delay': 3,
                    'timeout': 1,
                    'max_retries_down': 1,
                    'max_retries': 1}
        expect_error_msg = ("Validation failure: The associated pool protocol "
                            "is %(pool_protocol)s, so only a %(type)s health "
                            "monitor is supported.") % {
            'pool_protocol': constants.PROTOCOL_UDP,
            'type': constants.HEALTH_MONITOR_UDP_CONNECT}

        # Not allowed types, url_path, expected_codes specified.
        update_req = {'type': constants.HEALTH_MONITOR_TCP}
        req_dict.update(update_req)
        res = self.post(self.HMS_PATH, self._build_body(req_dict), status=400,
                        expect_errors=True)
        self.assertEqual(expect_error_msg, res.json['faultstring'])
        self.assert_correct_status(
            lb_id=self.udp_lb_id, listener_id=self.udp_listener_id,
            pool_id=self.udp_pool_with_listener_id)

        update_req = {'type': constants.HEALTH_MONITOR_UDP_CONNECT}
        req_dict.update(update_req)
        for req in [{'http_method':
                     constants.HEALTH_MONITOR_HTTP_METHOD_GET},
                    {'url_path': constants.HEALTH_MONITOR_DEFAULT_URL_PATH},
                    {'expected_codes':
                        constants.HEALTH_MONITOR_DEFAULT_EXPECTED_CODES}]:
            req_dict.update(req)
            res = self.post(self.HMS_PATH, self._build_body(req_dict),
                            status=400,
                            expect_errors=True)
            self.assertEqual(expect_error_msg, res.json['faultstring'])
            self.assert_correct_status(
                lb_id=self.udp_lb_id, listener_id=self.udp_listener_id,
                pool_id=self.udp_pool_with_listener_id)

        # Hit error during create with a non-UDP pool
        req_dict = {'pool_id': self.pool_with_listener_id,
                    'delay': 1,
                    'timeout': 1,
                    'max_retries_down': 1,
                    'max_retries': 1,
                    'type': constants.HEALTH_MONITOR_UDP_CONNECT}
        expect_error_msg = ("Validation failure: The %(type)s type is only "
                            "supported for pools of type "
                            "%(protocol)s.") % {
            'type': constants.HEALTH_MONITOR_UDP_CONNECT,
            'protocol': constants.PROTOCOL_UDP}
        res = self.post(self.HMS_PATH, self._build_body(req_dict),
                        status=400,
                        expect_errors=True)
        self.assertEqual(expect_error_msg, res.json['faultstring'])
        self.assert_correct_status(
            lb_id=self.udp_lb_id, listener_id=self.udp_listener_id,
            pool_id=self.udp_pool_with_listener_id)

    def test_ensure_L7_fields_filled_during_create(self):
        # Create a health monitor with a load balancer pool
        api_hm = self.create_health_monitor(
            self.pool_id,
            constants.PROTOCOL_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_CREATE,
            hm_op_status=constants.OFFLINE)
        self.set_lb_status(self.lb_id)
        self.assertEqual(constants.HEALTH_MONITOR_HTTP_DEFAULT_METHOD,
                         api_hm.get('http_method'))
        self.assertEqual(constants.HEALTH_MONITOR_DEFAULT_URL_PATH,
                         api_hm.get('url_path'))
        self.assertEqual(constants.HEALTH_MONITOR_DEFAULT_EXPECTED_CODES,
                         api_hm.get('expected_codes'))

    def test_create_authorized(self):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)

        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):

                api_hm = self.create_health_monitor(
                    self.pool_id, constants.HEALTH_MONITOR_HTTP,
                    1, 1, 1, 1).get(self.root_tag)

        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.ACTIVE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_CREATE,
            hm_op_status=constants.OFFLINE)
        self.set_lb_status(self.lb_id)
        self.assertEqual(constants.HEALTH_MONITOR_HTTP, api_hm.get('type'))
        self.assertEqual(1, api_hm.get('delay'))
        self.assertEqual(1, api_hm.get('timeout'))
        self.assertEqual(1, api_hm.get('max_retries_down'))
        self.assertEqual(1, api_hm.get('max_retries'))
        # Verify optional field defaults
        self.assertEqual('GET', api_hm.get('http_method'))
        self.assertEqual('/', api_hm.get('url_path'))
        self.assertEqual('200', api_hm.get('expected_codes'))

    def test_create_not_authorized(self):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)

        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            api_hm = self.create_health_monitor(
                self.pool_id, constants.HEALTH_MONITOR_HTTP,
                1, 1, 1, 1, status=403)

        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, api_hm)

    def test_create_pool_in_error(self):
        project_id = uuidutils.generate_uuid()
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(), name='lb1',
                                        project_id=project_id)
        lb1_id = lb1.get('loadbalancer').get('id')
        self.set_lb_status(lb1_id)
        pool1 = self.create_pool(
            lb1_id, constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN).get('pool')
        pool1_id = pool1.get('id')
        self.set_lb_status(lb1_id)
        self.set_object_status(self.pool_repo, pool1_id,
                               provisioning_status=constants.ERROR)
        api_hm = self.create_health_monitor(
            pool1_id, constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1, status=409)
        ref_msg = 'Pool %s is immutable and cannot be updated.' % pool1_id
        self.assertEqual(ref_msg, api_hm.get('faultstring'))

    def test_create_with_listener(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_CREATE,
            hm_op_status=constants.OFFLINE)
        self.set_lb_status(self.lb_id)
        self.assertEqual(constants.HEALTH_MONITOR_HTTP, api_hm.get('type'))
        self.assertEqual(1, api_hm.get('delay'))
        self.assertEqual(1, api_hm.get('timeout'))
        self.assertEqual(1, api_hm.get('max_retries_down'))
        self.assertEqual(1, api_hm.get('max_retries'))
        # Verify optional field defaults
        self.assertEqual('GET', api_hm.get('http_method'))
        self.assertEqual('/', api_hm.get('url_path'))
        self.assertEqual('200', api_hm.get('expected_codes'))

    def test_pool_returns_hm_id(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        pool = self.get(self.POOL_PATH.format(
            pool_id=self.pool_id)).json.get("pool")
        self.assertEqual(pool.get('healthmonitor_id'), api_hm.get('id'))

    # TODO(rm_work) Remove after deprecation of project_id in POST (R series)
    def test_create_with_project_id_is_ignored(self):
        pid = uuidutils.generate_uuid()
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1,
            project_id=pid).get(self.root_tag)
        self.assertEqual(self.project_id, api_hm.get('project_id'))

    def test_create_with_default_http_version(self):
        # Use the default HTTP/1.0
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1, admin_state_up=False, expected_codes='200',
            http_method='GET', name='Test HM', url_path='/',
            http_version='1.0').get(self.root_tag)
        self.assertEqual(1.0, api_hm.get('http_version'))

    def test_create_without_http_version(self):
        # Check the default http_version is 1.0
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1, admin_state_up=False, expected_codes='200',
            http_method='GET', name='Test HM', url_path='/').get(self.root_tag)
        self.assertIsNone(api_hm.get('http_version'))

    def test_create_with_http_version_11_and_domain_name(self):
        # Create with http_version 1.1 and domain_name
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTPS,
            1, 1, 1, 1, admin_state_up=False, expected_codes='200',
            http_method='GET', name='Test HM', url_path='/',
            http_version=1.1, domain_name='testlab.com').get(self.root_tag)
        self.assertEqual(1.1, api_hm.get('http_version'))
        self.assertEqual('testlab.com', api_hm.get('domain_name'))

    def test_create_with_http_version_11(self):
        # Create with http_version 1.1
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTPS,
            1, 1, 1, 1, admin_state_up=False, expected_codes='200',
            http_method='GET', name='Test HM', url_path='/',
            http_version=1.1).get(self.root_tag)
        self.assertEqual(1.1, api_hm.get('http_version'))

    def test_bad_create(self):
        hm_json = {'name': 'test1', 'pool_id': self.pool_id}
        self.post(self.HMS_PATH, self._build_body(hm_json), status=400)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id)

    def test_bad_create_with_invalid_url_path(self):
        req_dict = {'pool_id': self.pool_id,
                    'type': constants.HEALTH_MONITOR_HTTP,
                    'delay': 1,
                    'timeout': 1,
                    'max_retries_down': 1,
                    'max_retries': 1,
                    'url_path': 'https://openstack.org'}
        self.post(self.HMS_PATH, self._build_body(req_dict), status=400)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id)

    def test_create_ping_when_ping_disabled(self):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(group='api_settings',
                         allow_ping_health_monitors=False)
        req_dict = {'pool_id': self.pool_id,
                    'type': constants.HEALTH_MONITOR_PING,
                    'delay': 1,
                    'timeout': 1,
                    'max_retries_down': 1,
                    'max_retries': 1}
        self.post(self.HMS_PATH, self._build_body(req_dict), status=400)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id)

    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_create_with_bad_provider(self, mock_provider):
        mock_provider.side_effect = exceptions.ProviderDriverError(
            prov='bad_driver', user_msg='broken')
        req_dict = {'pool_id': self.pool_id,
                    'type': constants.HEALTH_MONITOR_HTTP,
                    'delay': 1,
                    'timeout': 1,
                    'max_retries_down': 1,
                    'max_retries': 1,
                    'url_path': '/foo'}
        response = self.post(self.HMS_PATH, self._build_body(req_dict),
                             status=500)
        self.assertIn('Provider \'bad_driver\' reports error: broken',
                      response.json.get('faultstring'))

    def test_create_with_type_none(self):
        req_dict = {'pool_id': self.pool_id,
                    'type': None,
                    'delay': 1,
                    'timeout': 1,
                    'max_retries_down': 1,
                    'max_retries': 1,
                    'url_path': '/'}
        self.post(self.HMS_PATH, self._build_body(req_dict), status=400)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id)

    def test_create_with_delay_none(self):
        req_dict = {'pool_id': self.pool_id,
                    'type': constants.HEALTH_MONITOR_HTTP,
                    'delay': None,
                    'timeout': 1,
                    'max_retries_down': 1,
                    'max_retries': 1,
                    'url_path': '/'}
        self.post(self.HMS_PATH, self._build_body(req_dict), status=400)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id)

    def test_create_with_max_retries_none(self):
        req_dict = {'pool_id': self.pool_id,
                    'type': constants.HEALTH_MONITOR_HTTP,
                    'delay': 1,
                    'timeout': 1,
                    'max_retries_down': 1,
                    'max_retries': None,
                    'url_path': '/'}
        self.post(self.HMS_PATH, self._build_body(req_dict), status=400)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id)

    def test_create_with_timeout_none(self):
        req_dict = {'pool_id': self.pool_id,
                    'type': constants.HEALTH_MONITOR_HTTP,
                    'delay': 1,
                    'timeout': None,
                    'max_retries_down': 1,
                    'max_retries': 1,
                    'url_path': '/'}
        self.post(self.HMS_PATH, self._build_body(req_dict), status=400)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id)

    def test_create_with_pool_id_none(self):
        req_dict = {'pool_id': None,
                    'type': constants.HEALTH_MONITOR_HTTP,
                    'delay': 1,
                    'timeout': 1,
                    'max_retries_down': 1,
                    'max_retries': 1,
                    'url_path': '/'}
        self.post(self.HMS_PATH, self._build_body(req_dict), status=404)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id)

    def test_create_TCP_with_http_method(self):
        req_dict = {'pool_id': self.pool_id,
                    'type': constants.HEALTH_MONITOR_TCP,
                    'delay': 1,
                    'timeout': 1,
                    'max_retries_down': 1,
                    'max_retries': 1,
                    'http_method': constants.HEALTH_MONITOR_HTTP_METHOD_GET}
        self.post(self.HMS_PATH, self._build_body(req_dict), status=400)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id)

    def test_create_TCP_with_url_path(self):
        req_dict = {'pool_id': self.pool_id,
                    'type': constants.HEALTH_MONITOR_TCP,
                    'delay': 1,
                    'timeout': 1,
                    'max_retries_down': 1,
                    'max_retries': 1,
                    'url_path': '/'}
        self.post(self.HMS_PATH, self._build_body(req_dict), status=400)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id)

    def test_create_TCP_with_expected_codes(self):
        req_dict = {'pool_id': self.pool_id,
                    'type': constants.HEALTH_MONITOR_TCP,
                    'delay': 1,
                    'timeout': 1,
                    'max_retries_down': 1,
                    'max_retries': 1,
                    'expected_codes': '200'}
        self.post(self.HMS_PATH, self._build_body(req_dict), status=400)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_id)

    def test_duplicate_create(self):
        self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1)
        self.set_lb_status(self.lb_id)
        self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1,
            status=409)

    def test_create_over_quota(self):
        self.start_quota_mock(data_models.HealthMonitor)
        hm = {'pool_id': self.pool_id,
              'type': constants.HEALTH_MONITOR_HTTP,
              'delay': 1,
              'timeout': 1,
              'max_retries_down': 1,
              'max_retries': 1}
        self.post(self.HMS_PATH, self._build_body(hm), status=403)

    def test_bad_create_with_http_version_and_domain_name_cases(self):
        hm_json = {'pool_id': self.pool_id,
                   'type': constants.HEALTH_MONITOR_HTTP,
                   'delay': 1,
                   'timeout': 1,
                   'max_retries_down': 1,
                   'max_retries': 1,
                   'expected_codes': '200',
                   'http_version': 1.00, 'domain_name': 'testlab.com'}
        api_hm = self.post(
            self.HMS_PATH, self._build_body(hm_json), status=400).json
        expect_error_msg = ("http_version 1.0 is not a valid option for "
                            "health monitors HTTP 1.1 domain name health "
                            "check")
        self.assertEqual(expect_error_msg, api_hm['faultstring'])
        for bad_case in [{'http_version': 1.0, 'domain_name': '^testla&b.com'},
                         {'http_version': 1.1,
                          'domain_name': 'testla\nb.com'}]:
            hm_json = {'pool_id': self.pool_id,
                       'type': constants.HEALTH_MONITOR_HTTP,
                       'delay': 1,
                       'timeout': 1,
                       'max_retries_down': 1,
                       'max_retries': 1,
                       'expected_codes': '200'}
            hm_json.update(bad_case)
            api_hm = self.post(
                self.HMS_PATH, self._build_body(hm_json), status=400).json
            expect_error_msg = (
                "Invalid input for field/attribute domain_name. Value: '%s'. "
                "Value should match the pattern %s") % (bad_case[
                    'domain_name'], constants.DOMAIN_NAME_REGEX)
            self.assertEqual(expect_error_msg, api_hm['faultstring'])

    def test_update(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1,
            tags=['old_tag']).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_hm = {'max_retries': 2, 'tags': ['new_tag']}
        self.put(
            self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
            self._build_body(new_hm))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_UPDATE)
        response = self.get(self.HM_PATH.format(
            healthmonitor_id=api_hm.get('id'))).json.get(self.root_tag)
        self.assertEqual(2, response[constants.MAX_RETRIES])
        self.assertEqual(['new_tag'], response['tags'])

    def test_update_HTTPS(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_HTTPS, 1, 1, 1, 1,
            admin_state_up=False, expected_codes='200',
            http_method='GET', name='Test HM', url_path='/').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.assertEqual('/', api_hm[constants.URL_PATH])
        new_hm = {constants.URL_PATH: '/health'}
        self.put(
            self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
            self._build_body(new_hm))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_UPDATE)
        response = self.get(self.HM_PATH.format(
            healthmonitor_id=api_hm.get('id'))).json.get(self.root_tag)
        self.assertEqual('/health', response[constants.URL_PATH])

    def test_update_http_version_and_domain_name(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1, admin_state_up=False, expected_codes='200',
            http_method='GET', name='Test HM', url_path='/').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_hm = {'http_version': 1.1, 'domain_name': 'testlab.com'}
        self.put(
            self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
            self._build_body(new_hm))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_UPDATE)
        response = self.get(self.HM_PATH.format(
            healthmonitor_id=api_hm.get('id'))).json.get(self.root_tag)
        self.assertEqual(1.1, response['http_version'])
        self.assertEqual('testlab.com', response['domain_name'])

    def test_update_TCP(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_TCP, 1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_hm = {'max_retries': 2}
        self.put(
            self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
            self._build_body(new_hm))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_UPDATE)
        response = self.get(self.HM_PATH.format(
            healthmonitor_id=api_hm.get('id'))).json.get(self.root_tag)
        self.assertEqual(2, response[constants.MAX_RETRIES])

    def test_update_authorized(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_hm = {'max_retries': 2}
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):

                self.put(
                    self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                    self._build_body(new_hm))

        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_UPDATE)

    def test_update_not_authorized(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_hm = {'max_retries': 2}
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            response = self.put(
                self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                self._build_body(new_hm), status=403)

        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response.json)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.ACTIVE,
            listener_prov_status=constants.ACTIVE,
            pool_prov_status=constants.ACTIVE,
            hm_prov_status=constants.ACTIVE)

    def test_update_udp_case(self):
        api_hm = self.create_health_monitor(
            self.udp_pool_with_listener_id,
            constants.HEALTH_MONITOR_UDP_CONNECT, 3, 1, 1, 1).get(
            self.root_tag)
        self.set_lb_status(self.udp_lb_id)
        new_hm = {'max_retries': 2}
        self.put(
            self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
            self._build_body(new_hm))
        self.assert_correct_status(
            lb_id=self.udp_lb_id, listener_id=self.udp_listener_id,
            pool_id=self.udp_pool_with_listener_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_UPDATE)

    def test_negative_update_udp_case(self):
        api_hm = self.create_health_monitor(
            self.udp_pool_with_listener_id,
            constants.HEALTH_MONITOR_UDP_CONNECT, 3, 1, 1, 1).get(
            self.root_tag)
        self.set_lb_status(self.udp_lb_id)

        # Hit error during update with invalid parameter
        req_dict = {'delay': 3,
                    'timeout': 1,
                    'max_retries_down': 1,
                    'max_retries': 1,
                    'http_method': constants.HEALTH_MONITOR_HTTP_METHOD_GET}
        expect_error_msg = (("http_method is not a valid option for health "
                             "monitors of type %s") %
                            constants.HEALTH_MONITOR_UDP_CONNECT)
        res = self.put(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                       self._build_body(req_dict),
                       status=400, expect_errors=True)
        self.assertEqual(expect_error_msg, res.json['faultstring'])
        self.assert_correct_status(
            lb_id=self.udp_lb_id, listener_id=self.udp_listener_id,
            pool_id=self.udp_pool_with_listener_id)

        # Hit error during update with smaller delay value
        req_dict = {'delay': 1}
        expect_error_msg = ("Validation failure: The request delay value 1 "
                            "should be larger than 3 for %s health monitor "
                            "type.") % constants.HEALTH_MONITOR_UDP_CONNECT
        res = self.put(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                       self._build_body(req_dict),
                       status=400, expect_errors=True)
        self.assertEqual(expect_error_msg, res.json['faultstring'])
        self.assert_correct_status(
            lb_id=self.udp_lb_id, listener_id=self.udp_listener_id,
            pool_id=self.udp_pool_with_listener_id)

    def test_bad_update(self):
        api_hm = self.create_health_monitor(self.pool_with_listener_id,
                                            constants.HEALTH_MONITOR_HTTP,
                                            1, 1, 1, 1).get(self.root_tag)
        new_hm = {'http_method': 'bad_method', 'delay': 2}
        self.set_lb_status(self.lb_id)
        self.put(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                 self._build_body(new_hm), status=400)

    def test_update_delay_none(self):
        api_hm = self.create_health_monitor(self.pool_with_listener_id,
                                            constants.HEALTH_MONITOR_HTTP,
                                            1, 1, 1, 1).get(self.root_tag)
        new_hm = {constants.DELAY: None}
        self.set_lb_status(self.lb_id)
        expect_error_msg = ("None is not a valid option for %s" %
                            constants.DELAY)
        res = self.put(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                       self._build_body(new_hm), status=400)
        self.assertEqual(expect_error_msg, res.json['faultstring'])

    def test_update_max_retries_none(self):
        api_hm = self.create_health_monitor(self.pool_with_listener_id,
                                            constants.HEALTH_MONITOR_HTTP,
                                            1, 1, 1, 1).get(self.root_tag)
        new_hm = {constants.MAX_RETRIES: None}
        self.set_lb_status(self.lb_id)
        expect_error_msg = ("None is not a valid option for %s" %
                            constants.MAX_RETRIES)
        res = self.put(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                       self._build_body(new_hm), status=400)
        self.assertEqual(expect_error_msg, res.json['faultstring'])

    def test_update_timeout_none(self):
        api_hm = self.create_health_monitor(self.pool_with_listener_id,
                                            constants.HEALTH_MONITOR_HTTP,
                                            1, 1, 1, 1).get(self.root_tag)
        new_hm = {constants.TIMEOUT: None}
        self.set_lb_status(self.lb_id)
        expect_error_msg = ("None is not a valid option for %s" %
                            constants.TIMEOUT)
        res = self.put(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                       self._build_body(new_hm), status=400)
        self.assertEqual(expect_error_msg, res.json['faultstring'])

    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_update_with_bad_provider(self, mock_provider):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_hm = {'max_retries': 2}
        mock_provider.side_effect = exceptions.ProviderDriverError(
            prov='bad_driver', user_msg='broken')
        response = self.put(
            self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
            self._build_body(new_hm), status=500)
        self.assertIn('Provider \'bad_driver\' reports error: broken',
                      response.json.get('faultstring'))

    def test_update_TCP_setting_http_method(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_TCP, 1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_hm = {'http_method': constants.HEALTH_MONITOR_HTTP_METHOD_GET}
        self.put(
            self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
            self._build_body(new_hm), status=400)

    def test_update_TCP_setting_url_path(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_TCP, 1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_hm = {'url_path': '/'}
        self.put(
            self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
            self._build_body(new_hm), status=400)

    def test_update_TCP_setting_expected_codes(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_TCP, 1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_hm = {'expected_codes': '200'}
        self.put(
            self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
            self._build_body(new_hm), status=400)

    def test_update_HTTP_http_method_none(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_hm = {'http_method': None}
        self.put(
            self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
            self._build_body(new_hm))
        response = self.get(self.HM_PATH.format(
            healthmonitor_id=api_hm.get('id'))).json.get(self.root_tag)
        self.assertEqual(constants.HEALTH_MONITOR_HTTP_METHOD_GET,
                         response['http_method'])

    def test_update_HTTP_url_path_none(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_hm = {'url_path': None}
        self.put(
            self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
            self._build_body(new_hm))
        response = self.get(self.HM_PATH.format(
            healthmonitor_id=api_hm.get('id'))).json.get(self.root_tag)
        self.assertEqual(constants.HEALTH_MONITOR_DEFAULT_URL_PATH,
                         response['url_path'])

    def test_update_HTTP_expected_codes_none(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_hm = {'expected_codes': None}
        self.put(
            self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
            self._build_body(new_hm))
        response = self.get(self.HM_PATH.format(
            healthmonitor_id=api_hm.get('id'))).json.get(self.root_tag)
        self.assertEqual(constants.HEALTH_MONITOR_DEFAULT_EXPECTED_CODES,
                         response['expected_codes'])

    def test_bad_update_http_version_and_domain_name(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1, admin_state_up=False, expected_codes='200',
            http_method='GET', name='Test HM', url_path='/').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_hm = {'http_version': 1.0, 'domain_name': 'testlab.com'}
        response = self.put(
            self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
            self._build_body(new_hm), status=400)
        expect_error_msg = ("http_version 1.0 is not a valid option for "
                            "health monitors HTTP 1.1 domain name health "
                            "check")
        self.assertEqual(expect_error_msg, response.json['faultstring'])

        new_hm = {'http_version': 1.0, 'domain_name': '^testla&b.com'}
        response = self.put(
            self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
            self._build_body(new_hm), status=400)
        expect_error_msg = (
            "Invalid input for field/attribute domain_name. Value: '%s'. "
            "Value should match the pattern %s") % (new_hm[
                'domain_name'], constants.DOMAIN_NAME_REGEX)
        self.assertEqual(expect_error_msg, response.json['faultstring'])

    def test_update_unset_defaults(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1, name='test', domain_name='test.example.com',
            expected_codes='400', http_method='HEAD', http_version='1.1',
            url_path='/test').get(self.root_tag)
        new_hm = {constants.DOMAIN_NAME: None, constants.EXPECTED_CODES: None,
                  constants.HTTP_METHOD: None, constants.HTTP_VERSION: None,
                  constants.MAX_RETRIES_DOWN: None, 'name': None,
                  constants.URL_PATH: None}
        self.set_lb_status(self.lb_id)
        res = self.put(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                       self._build_body(new_hm)).json.get(self.root_tag)
        self.assertIsNone(res[constants.DOMAIN_NAME])
        self.assertEqual(constants.HEALTH_MONITOR_DEFAULT_EXPECTED_CODES,
                         res[constants.EXPECTED_CODES])
        self.assertEqual(constants.HEALTH_MONITOR_HTTP_DEFAULT_METHOD,
                         res[constants.HTTP_METHOD])
        self.assertIsNone(res[constants.HTTP_VERSION])
        self.assertEqual(constants.DEFAULT_MAX_RETRIES_DOWN,
                         res[constants.MAX_RETRIES_DOWN])
        self.assertEqual('', res['name'])
        self.assertEqual(constants.HEALTH_MONITOR_DEFAULT_URL_PATH,
                         res[constants.URL_PATH])

    def test_delete(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        hm = self.get(self.HM_PATH.format(
            healthmonitor_id=api_hm.get('id'))).json.get(self.root_tag)
        api_hm['provisioning_status'] = constants.ACTIVE
        api_hm['operating_status'] = constants.ONLINE
        self.assertIsNone(api_hm.pop('updated_at'))
        self.assertIsNotNone(hm.pop('updated_at'))
        self.assertEqual(api_hm, hm)
        self.delete(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_DELETE)

    def test_delete_authorized(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        hm = self.get(self.HM_PATH.format(
            healthmonitor_id=api_hm.get('id'))).json.get(self.root_tag)
        api_hm['provisioning_status'] = constants.ACTIVE
        api_hm['operating_status'] = constants.ONLINE
        self.assertIsNone(api_hm.pop('updated_at'))
        self.assertIsNotNone(hm.pop('updated_at'))
        self.assertEqual(api_hm, hm)

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                self.delete(
                    self.HM_PATH.format(healthmonitor_id=api_hm.get('id')))
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            pool_prov_status=constants.PENDING_UPDATE,
            hm_prov_status=constants.PENDING_DELETE)

    def test_delete_not_authorized(self):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        hm = self.get(self.HM_PATH.format(
            healthmonitor_id=api_hm.get('id'))).json.get(self.root_tag)
        api_hm['provisioning_status'] = constants.ACTIVE
        api_hm['operating_status'] = constants.ONLINE
        self.assertIsNone(api_hm.pop('updated_at'))
        self.assertIsNotNone(hm.pop('updated_at'))
        self.assertEqual(api_hm, hm)

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            self.delete(
                self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            pool_id=self.pool_with_listener_id, hm_id=api_hm.get('id'),
            lb_prov_status=constants.ACTIVE,
            listener_prov_status=constants.ACTIVE,
            pool_prov_status=constants.ACTIVE,
            hm_prov_status=constants.ACTIVE)

    def test_bad_delete(self):
        self.delete(
            self.HM_PATH.format(healthmonitor_id=uuidutils.generate_uuid()),
            status=404)

    @mock.patch('octavia.api.drivers.utils.call_provider')
    def test_delete_with_bad_provider(self, mock_provider):
        api_hm = self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        hm = self.get(self.HM_PATH.format(
            healthmonitor_id=api_hm.get('id'))).json.get(self.root_tag)
        api_hm['provisioning_status'] = constants.ACTIVE
        api_hm['operating_status'] = constants.ONLINE
        self.assertIsNone(api_hm.pop('updated_at'))
        self.assertIsNotNone(hm.pop('updated_at'))
        self.assertEqual(api_hm, hm)

        mock_provider.side_effect = exceptions.ProviderDriverError(
            prov='bad_driver', user_msg='broken')
        self.delete(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                    status=500)

    def test_create_when_lb_pending_update(self):
        self.put(self.LB_PATH.format(lb_id=self.lb_id),
                 body={'loadbalancer': {'name': 'test_name_change'}})
        self.create_health_monitor(
            self.pool_with_listener_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1, status=409)

    def test_update_when_lb_pending_update(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.put(self.LB_PATH.format(lb_id=self.lb_id),
                 body={'loadbalancer': {'name': 'test_name_change'}})
        new_hm = {'max_retries': 2}
        self.put(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                 body=self._build_body(new_hm), status=409)

    def test_delete_when_lb_pending_update(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.put(self.LB_PATH.format(lb_id=self.lb_id),
                 body={'loadbalancer': {'name': 'test_name_change'}})
        self.delete(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                    status=409)

    def test_create_when_lb_pending_delete(self):
        self.delete(self.LB_PATH.format(lb_id=self.lb_id),
                    params={'cascade': "true"})
        self.create_health_monitor(
            self.pool_id,
            constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1, status=409)

    def test_update_when_lb_pending_delete(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.delete(self.LB_PATH.format(lb_id=self.lb_id),
                    params={'cascade': "true"})
        new_hm = {'max_retries': 2}
        self.put(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                 body=self._build_body(new_hm), status=409)

    def test_update_already_deleted(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        # This updates the child objects
        self.set_lb_status(self.lb_id, status=constants.DELETED)
        self.put(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                 body=self._build_body({'max_retries': 2}), status=404)

    def test_delete_when_lb_pending_delete(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.delete(self.LB_PATH.format(lb_id=self.lb_id),
                    params={'cascade': "true"})
        self.delete(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                    status=409)

    def test_delete_already_deleted(self):
        api_hm = self.create_health_monitor(
            self.pool_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1).get(self.root_tag)
        # This updates the child objects
        self.set_lb_status(self.lb_id, status=constants.DELETED)
        self.delete(self.HM_PATH.format(healthmonitor_id=api_hm.get('id')),
                    status=404)
