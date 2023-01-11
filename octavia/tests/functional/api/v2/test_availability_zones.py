#    Copyright 2019 Verizon Media
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

from unittest import mock

from oslo_utils import uuidutils

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture

from octavia.common import constants
import octavia.common.context
from octavia.common import exceptions
from octavia.tests.functional.api.v2 import base


class TestAvailabilityZones(base.BaseAPITest):
    root_tag = 'availability_zone'
    root_tag_list = 'availability_zones'
    root_tag_links = 'availability_zones_links'

    def setUp(self):
        super().setUp()
        self.azp = self.create_availability_zone_profile(
            'test1', 'noop_driver', '{"compute_zone": "my_az_1"}')

    def _assert_request_matches_response(self, req, resp, **optionals):
        self.assertNotIn('id', resp)  # AZs do not expose an ID
        req_description = req.get('description')
        self.assertEqual(req.get('name'), resp.get('name'))
        if not req_description:
            self.assertEqual('', resp.get('description'))
        else:
            self.assertEqual(req.get('description'), resp.get('description'))
        self.assertEqual(req.get('availability_zone_profile_id'),
                         resp.get('availability_zone_profile_id'))
        self.assertEqual(req.get('enabled', True),
                         resp.get('enabled'))

    def test_empty_list(self):
        response = self.get(self.AZS_PATH)
        api_list = response.json.get(self.root_tag_list)
        self.assertEqual([], api_list)

    def test_create(self):
        az_json = {'name': 'test1',
                   'availability_zone_profile_id': self.azp.get('id')}
        body = self._build_body(az_json)
        response = self.post(self.AZS_PATH, body)
        api_az = response.json.get(self.root_tag)
        self._assert_request_matches_response(az_json, api_az)

    def test_create_with_missing_name(self):
        az_json = {'availability_zone_profile_id': self.azp.get('id')}
        body = self._build_body(az_json)
        response = self.post(self.AZS_PATH, body, status=400)
        err_msg = ("Invalid input for field/attribute name. Value: "
                   "'None'. Mandatory field missing.")
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_long_name(self):
        az_json = {'name': 'n' * 256,
                   'availability_zone_profile_id': self.azp.get('id')}
        body = self._build_body(az_json)
        self.post(self.AZS_PATH, body, status=400)

    def test_create_with_long_description(self):
        az_json = {'name': 'test-az',
                   'description': 'n' * 256,
                   'availability_zone_profile_id': self.azp.get('id')}
        body = self._build_body(az_json)
        self.post(self.AZS_PATH, body, status=400)

    def test_create_with_missing_availability_zone_profile(self):
        az_json = {'name': 'xyz'}
        body = self._build_body(az_json)
        response = self.post(self.AZS_PATH, body, status=400)
        err_msg = (
            "Invalid input for field/attribute availability_zone_profile_id. "
            "Value: 'None'. Mandatory field missing.")
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_bad_availability_zone_profile(self):
        az_json = {'name': 'xyz', 'availability_zone_profile_id': 'bogus'}
        body = self._build_body(az_json)
        response = self.post(self.AZS_PATH, body, status=400)
        err_msg = (
            "Invalid input for field/attribute availability_zone_profile_id. "
            "Value: 'bogus'. Value should be UUID format")
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_duplicate_names(self):
        self.create_availability_zone(
            'name', 'description', self.azp.get('id'), True)
        az_json = {'name': 'name',
                   'availability_zone_profile_id': self.azp.get('id')}
        body = self._build_body(az_json)
        response = self.post(self.AZS_PATH, body, status=409)
        err_msg = "A availability zone of name already exists."
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_authorized(self):
        az_json = {'name': 'test1',
                   'availability_zone_profile_id': self.azp.get('id')}
        body = self._build_body(az_json)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        project_id = uuidutils.generate_uuid()
        with mock.patch.object(octavia.common.context.RequestContext,
                               'project_id',
                               project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': True,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                response = self.post(self.AZS_PATH, body)
        api_az = response.json.get(self.root_tag)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self._assert_request_matches_response(az_json, api_az)

    def test_create_not_authorized(self):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        az_json = {'name': 'name',
                   'availability_zone_profile_id': self.azp.get('id')}
        body = self._build_body(az_json)
        response = self.post(self.AZS_PATH, body, status=403)
        api_az = response.json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, api_az)

    def test_create_db_failure(self):
        az_json = {'name': 'test1',
                   'availability_zone_profile_id': self.azp.get('id')}
        body = self._build_body(az_json)
        with mock.patch("octavia.db.repositories.AvailabilityZoneRepository."
                        "create") as mock_create:
            mock_create.side_effect = Exception
            self.post(self.AZS_PATH, body, status=500)

    def test_get(self):
        az = self.create_availability_zone(
            'name', 'description', self.azp.get('id'), True)
        response = self.get(
            self.AZ_PATH.format(
                az_name=az.get('name'))).json.get(self.root_tag)
        self.assertEqual('name', response.get('name'))
        self.assertEqual('description', response.get('description'))
        self.assertEqual(az.get('name'), response.get('name'))
        self.assertEqual(self.azp.get('id'),
                         response.get('availability_zone_profile_id'))
        self.assertTrue(response.get('enabled'))

    def test_get_one_fields_filter(self):
        az = self.create_availability_zone(
            'name', 'description', self.azp.get('id'), True)
        response = self.get(
            self.AZ_PATH.format(az_name=az.get('name')), params={
                'fields': ['name', 'availability_zone_profile_id']}
        ).json.get(self.root_tag)
        self.assertEqual(az.get('name'), response.get('name'))
        self.assertEqual(self.azp.get('id'),
                         response.get('availability_zone_profile_id'))
        self.assertIn(u'availability_zone_profile_id', response)
        self.assertNotIn(u'description', response)
        self.assertNotIn(u'enabled', response)

    def test_get_one_deleted_name(self):
        response = self.get(
            self.AZ_PATH.format(az_name=constants.NIL_UUID), status=404)
        self.assertEqual(
            'Availability Zone {} not found.'.format(constants.NIL_UUID),
            response.json.get('faultstring'))

    def test_get_authorized(self):
        az = self.create_availability_zone(
            'name', 'description', self.azp.get('id'), True)

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        project_id = uuidutils.generate_uuid()
        with mock.patch.object(octavia.common.context.RequestContext,
                               'project_id',
                               project_id):
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
                'project_id': project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                response = self.get(
                    self.AZ_PATH.format(
                        az_name=az.get('name'))).json.get(self.root_tag)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual('name', response.get('name'))
        self.assertEqual('description', response.get('description'))
        self.assertEqual(self.azp.get('id'),
                         response.get('availability_zone_profile_id'))
        self.assertTrue(response.get('enabled'))

    def test_get_not_authorized(self):
        az = self.create_availability_zone(
            'name', 'description', self.azp.get('id'), True)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        response = self.get(self.AZ_PATH.format(
            az_name=az.get('name')), status=403).json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response)

    def test_get_all(self):
        self.create_availability_zone(
            'name1', 'description', self.azp.get('id'), True)
        ref_az_1 = {
            u'description': u'description', u'enabled': True,
            u'availability_zone_profile_id': self.azp.get('id'),
            u'name': u'name1'}
        self.create_availability_zone(
            'name2', 'description', self.azp.get('id'), True)
        ref_az_2 = {
            u'description': u'description', u'enabled': True,
            u'availability_zone_profile_id': self.azp.get('id'),
            u'name': u'name2'}
        response = self.get(self.AZS_PATH)
        api_list = response.json.get(self.root_tag_list)
        self.assertEqual(2, len(api_list))
        self.assertIn(ref_az_1, api_list)
        self.assertIn(ref_az_2, api_list)

    def test_get_all_fields_filter(self):
        self.create_availability_zone(
            'name1', 'description', self.azp.get('id'), True)
        self.create_availability_zone(
            'name2', 'description', self.azp.get('id'), True)
        response = self.get(self.AZS_PATH, params={
            'fields': ['id', 'name']})
        api_list = response.json.get(self.root_tag_list)
        self.assertEqual(2, len(api_list))
        for az in api_list:
            self.assertIn(u'name', az)
            self.assertNotIn(u'availability_zone_profile_id', az)
            self.assertNotIn(u'description', az)
            self.assertNotIn(u'enabled', az)

    def test_get_all_authorized(self):
        self.create_availability_zone(
            'name1', 'description', self.azp.get('id'), True)
        self.create_availability_zone(
            'name2', 'description', self.azp.get('id'), True)
        response = self.get(self.AZS_PATH)

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        project_id = uuidutils.generate_uuid()
        with mock.patch.object(octavia.common.context.RequestContext,
                               'project_id',
                               project_id):
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
                'project_id': project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                api_list = response.json.get(self.root_tag_list)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(2, len(api_list))

    def test_get_all_not_authorized(self):
        self.create_availability_zone(
            'name1', 'description', self.azp.get('id'), True)
        self.create_availability_zone(
            'name2', 'description', self.azp.get('id'), True)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        response = self.get(self.AZS_PATH, status=403).json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response)

    def test_update(self):
        az_json = {'name': 'Fancy_Availability_Zone',
                   'description': 'A great az. Pick me!',
                   'availability_zone_profile_id': self.azp.get('id')}
        body = self._build_body(az_json)
        response = self.post(self.AZS_PATH, body)
        api_az = response.json.get(self.root_tag)
        availability_zone_name = api_az.get('name')

        az_json = {'description': 'An even better az. Pick me!',
                   'enabled': False}
        body = self._build_body(az_json)
        self.put(self.AZ_PATH.format(az_name=availability_zone_name), body)

        updated_az = self.get(self.AZ_PATH.format(
            az_name=availability_zone_name)).json.get(self.root_tag)
        self.assertEqual('An even better az. Pick me!',
                         updated_az.get('description'))
        self.assertEqual(availability_zone_name, updated_az.get('name'))
        self.assertEqual(self.azp.get('id'),
                         updated_az.get('availability_zone_profile_id'))
        self.assertFalse(updated_az.get('enabled'))

    def test_update_deleted_name(self):
        update_json = {'description': 'fake_desc'}
        body = self._build_body(update_json)
        response = self.put(
            self.AZ_PATH.format(az_name=constants.NIL_UUID), body,
            status=404)
        self.assertEqual(
            'Availability Zone {} not found.'.format(constants.NIL_UUID),
            response.json.get('faultstring'))

    def test_update_none(self):
        az_json = {'name': 'Fancy_Availability_Zone',
                   'description': 'A great az. Pick me!',
                   'availability_zone_profile_id': self.azp.get('id')}
        body = self._build_body(az_json)
        response = self.post(self.AZS_PATH, body)
        api_az = response.json.get(self.root_tag)
        availability_zone_name = api_az.get('name')

        az_json = {}
        body = self._build_body(az_json)
        self.put(self.AZ_PATH.format(az_name=availability_zone_name), body)

        updated_az = self.get(self.AZ_PATH.format(
            az_name=availability_zone_name)).json.get(self.root_tag)
        self.assertEqual('Fancy_Availability_Zone', updated_az.get('name'))
        self.assertEqual('A great az. Pick me!',
                         updated_az.get('description'))
        self.assertEqual(availability_zone_name, updated_az.get('name'))
        self.assertEqual(self.azp.get('id'),
                         updated_az.get('availability_zone_profile_id'))
        self.assertTrue(updated_az.get('enabled'))

    def test_update_availability_zone_profile_id(self):
        az_json = {'name': 'Fancy_Availability_Zone',
                   'description': 'A great az. Pick me!',
                   'availability_zone_profile_id': self.azp.get('id')}
        body = self._build_body(az_json)
        response = self.post(self.AZS_PATH, body)
        api_az = response.json.get(self.root_tag)
        availability_zone_name = api_az.get('name')

        az_json = {'availability_zone_profile_id': uuidutils.generate_uuid()}
        body = self._build_body(az_json)
        self.put(self.AZ_PATH.format(az_name=availability_zone_name),
                 body, status=400)
        updated_az = self.get(self.AZ_PATH.format(
            az_name=availability_zone_name)).json.get(self.root_tag)
        self.assertEqual(self.azp.get('id'),
                         updated_az.get('availability_zone_profile_id'))

    def test_update_authorized(self):
        az_json = {'name': 'Fancy_Availability_Zone',
                   'description': 'A great az. Pick me!',
                   'availability_zone_profile_id': self.azp.get('id')}
        body = self._build_body(az_json)
        response = self.post(self.AZS_PATH, body)
        api_az = response.json.get(self.root_tag)
        availability_zone_name = api_az.get('name')

        az_json = {'description': 'An even better az. Pick me!',
                   'enabled': False}
        body = self._build_body(az_json)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        project_id = uuidutils.generate_uuid()
        with mock.patch.object(octavia.common.context.RequestContext,
                               'project_id',
                               project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': True,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                self.put(self.AZ_PATH.format(az_name=availability_zone_name),
                         body)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        updated_az = self.get(self.AZ_PATH.format(
            az_name=availability_zone_name)).json.get(self.root_tag)
        self.assertEqual('An even better az. Pick me!',
                         updated_az.get('description'))
        self.assertEqual(availability_zone_name, updated_az.get('name'))
        self.assertEqual(self.azp.get('id'),
                         updated_az.get('availability_zone_profile_id'))
        self.assertFalse(updated_az.get('enabled'))

    def test_update_not_authorized(self):
        az_json = {'name': 'Fancy_Availability_Zone',
                   'description': 'A great az. Pick me!',
                   'availability_zone_profile_id': self.azp.get('id')}
        body = self._build_body(az_json)
        response = self.post(self.AZS_PATH, body)
        api_az = response.json.get(self.root_tag)
        availability_zone_name = api_az.get('name')

        az_json = {'description': 'An even better az. Pick me!',
                   'enabled': False}
        body = self._build_body(az_json)

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        self.put(self.AZ_PATH.format(az_name=availability_zone_name),
                 body, status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        updated_az = self.get(self.AZ_PATH.format(
            az_name=availability_zone_name)).json.get(self.root_tag)
        self.assertEqual('A great az. Pick me!',
                         updated_az.get('description'))
        self.assertEqual(availability_zone_name, updated_az.get('name'))
        self.assertEqual(self.azp.get('id'),
                         updated_az.get('availability_zone_profile_id'))
        self.assertTrue(updated_az.get('enabled'))

    @mock.patch('octavia.db.repositories.AvailabilityZoneRepository.update')
    def test_update_exception(self, mock_update):
        mock_update.side_effect = [exceptions.OctaviaException()]
        update_json = {'description': 'Some availability zone.'}
        body = self._build_body(update_json)
        response = self.put(self.AZ_PATH.format(az_name='bogus'), body,
                            status=500)
        self.assertEqual('An unknown exception occurred.',
                         response.json.get('faultstring'))

    def test_delete(self):
        az = self.create_availability_zone(
            'name1', 'description', self.azp.get('id'), True)
        self.delete(self.AZ_PATH.format(az_name=az.get('name')))
        response = self.get(self.AZ_PATH.format(az_name=az.get('name')),
                            status=404)
        err_msg = "Availability Zone %s not found." % az.get('name')
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_delete_nonexistent_name(self):
        response = self.delete(
            self.AZ_PATH.format(az_name='bogus_name'), status=404)
        self.assertEqual('Availability Zone bogus_name not found.',
                         response.json.get('faultstring'))

    def test_delete_deleted_name(self):
        response = self.delete(
            self.AZ_PATH.format(az_name=constants.NIL_UUID), status=404)
        self.assertEqual(
            'Availability Zone {} not found.'.format(constants.NIL_UUID),
            response.json.get('faultstring'))

    def test_delete_authorized(self):
        az = self.create_availability_zone(
            'name1', 'description', self.azp.get('id'), True)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        project_id = uuidutils.generate_uuid()
        with mock.patch.object(octavia.common.context.RequestContext,
                               'project_id',
                               project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': True,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                self.delete(
                    self.AZ_PATH.format(az_name=az.get('name')))
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        response = self.get(self.AZ_PATH.format(az_name=az.get('name')),
                            status=404)
        err_msg = "Availability Zone %s not found." % az.get('name')
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_delete_not_authorized(self):
        az = self.create_availability_zone(
            'name1', 'description', self.azp.get('id'), True)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)

        response = self.delete(self.AZ_PATH.format(az_name=az.get('name')),
                               status=403)
        api_az = response.json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, api_az)

        response = self.get(self.AZ_PATH.format(
            az_name=az.get('name'))).json.get(self.root_tag)
        self.assertEqual('name1', response.get('name'))

    def test_delete_in_use(self):
        az = self.create_availability_zone(
            'name1', 'description', self.azp.get('id'), True)
        project_id = uuidutils.generate_uuid()
        lb_id = uuidutils.generate_uuid()
        self.create_load_balancer(lb_id, name='lb1',
                                  project_id=project_id,
                                  description='desc1',
                                  availability_zone=az.get('name'),
                                  admin_state_up=False)
        self.delete(self.AZ_PATH.format(az_name=az.get('name')),
                    status=409)
        response = self.get(self.AZ_PATH.format(
            az_name=az.get('name'))).json.get(self.root_tag)
        self.assertEqual('name1', response.get('name'))

    @mock.patch('octavia.db.repositories.AvailabilityZoneRepository.delete')
    def test_delete_exception(self, mock_delete):
        mock_delete.side_effect = [exceptions.OctaviaException()]
        response = self.delete(self.AZ_PATH.format(az_name='bogus'),
                               status=500)
        self.assertEqual('An unknown exception occurred.',
                         response.json.get('faultstring'))
