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

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_db import exception as odb_exceptions
from oslo_utils import uuidutils

from octavia.common import constants
import octavia.common.context
from octavia.tests.functional.api.v2 import base


class TestAvailabilityZoneProfiles(base.BaseAPITest):
    root_tag = 'availability_zone_profile'
    root_tag_list = 'availability_zone_profiles'
    root_tag_links = 'availability_zone_profile_links'

    def _assert_request_matches_response(self, req, resp, **optionals):
        self.assertTrue(uuidutils.is_uuid_like(resp.get('id')))
        self.assertEqual(req.get('name'), resp.get('name'))
        self.assertEqual(req.get(constants.PROVIDER_NAME),
                         resp.get(constants.PROVIDER_NAME))
        self.assertEqual(req.get(constants.AVAILABILITY_ZONE_DATA),
                         resp.get(constants.AVAILABILITY_ZONE_DATA))

    def test_empty_list(self):
        response = self.get(self.AZPS_PATH)
        api_list = response.json.get(self.root_tag_list)
        self.assertEqual([], api_list)

    def test_create(self):
        az_json = {'name': 'test1', constants.PROVIDER_NAME: 'noop_driver',
                   constants.AVAILABILITY_ZONE_DATA: '{"hello": "world"}'}
        body = self._build_body(az_json)
        response = self.post(self.AZPS_PATH, body)
        api_azp = response.json.get(self.root_tag)
        self._assert_request_matches_response(az_json, api_azp)

    def test_create_with_missing_name(self):
        az_json = {constants.PROVIDER_NAME: 'pr1',
                   constants.AVAILABILITY_ZONE_DATA: '{"x": "y"}'}
        body = self._build_body(az_json)
        response = self.post(self.AZPS_PATH, body, status=400)
        err_msg = ("Invalid input for field/attribute name. Value: "
                   "'None'. Mandatory field missing.")
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_missing_provider(self):
        az_json = {'name': 'xyz',
                   constants.AVAILABILITY_ZONE_DATA: '{"x": "y"}'}
        body = self._build_body(az_json)
        response = self.post(self.AZPS_PATH, body, status=400)
        err_msg = ("Invalid input for field/attribute provider_name. "
                   "Value: 'None'. Mandatory field missing.")
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_missing_availability_zone_data(self):
        az_json = {'name': 'xyz', constants.PROVIDER_NAME: 'pr1'}
        body = self._build_body(az_json)
        response = self.post(self.AZPS_PATH, body, status=400)
        err_msg = ("Invalid input for field/attribute availability_zone_data. "
                   "Value: 'None'. Mandatory field missing.")
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_empty_availability_zone_data(self):
        az_json = {'name': 'test1', constants.PROVIDER_NAME: 'noop_driver',
                   constants.AVAILABILITY_ZONE_DATA: '{}'}
        body = self._build_body(az_json)
        response = self.post(self.AZPS_PATH, body)
        api_azp = response.json.get(self.root_tag)
        self._assert_request_matches_response(az_json, api_azp)

    def test_create_with_long_name(self):
        az_json = {'name': 'n' * 256, constants.PROVIDER_NAME: 'test1',
                   constants.AVAILABILITY_ZONE_DATA: '{"hello": "world"}'}
        body = self._build_body(az_json)
        self.post(self.AZPS_PATH, body, status=400)

    def test_create_with_long_provider(self):
        az_json = {'name': 'name1', constants.PROVIDER_NAME: 'n' * 256,
                   constants.AVAILABILITY_ZONE_DATA: '{"hello": "world"}'}
        body = self._build_body(az_json)
        self.post(self.AZPS_PATH, body, status=400)

    def test_create_with_long_availability_zone_data(self):
        az_json = {'name': 'name1', constants.PROVIDER_NAME: 'amp',
                   constants.AVAILABILITY_ZONE_DATA: 'n' * 4097}
        body = self._build_body(az_json)
        self.post(self.AZPS_PATH, body, status=400)

    def test_create_authorized(self):
        az_json = {'name': 'test1', constants.PROVIDER_NAME: 'noop_driver',
                   constants.AVAILABILITY_ZONE_DATA: '{"hello": "world"}'}
        body = self._build_body(az_json)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        project_id = uuidutils.generate_uuid()
        with mock.patch.object(octavia.common.context.Context, 'project_id',
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
                response = self.post(self.AZPS_PATH, body)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        api_azp = response.json.get(self.root_tag)
        self._assert_request_matches_response(az_json, api_azp)

    def test_create_not_authorized(self):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        az_json = {'name': 'name',
                   constants.PROVIDER_NAME: 'xyz',
                   constants.AVAILABILITY_ZONE_DATA: '{"x": "y"}'}
        body = self._build_body(az_json)
        response = self.post(self.AZPS_PATH, body, status=403)
        api_azp = response.json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, api_azp)

    def test_create_db_failure(self):
        az_json = {'name': 'test1', constants.PROVIDER_NAME: 'noop_driver',
                   constants.AVAILABILITY_ZONE_DATA: '{"hello": "world"}'}
        body = self._build_body(az_json)
        with mock.patch(
                "octavia.db.repositories.AvailabilityZoneProfileRepository."
                "create") as mock_create:
            mock_create.side_effect = Exception
            self.post(self.AZPS_PATH, body, status=500)

            mock_create.side_effect = odb_exceptions.DBDuplicateEntry
            self.post(self.AZPS_PATH, body, status=409)

    def test_create_with_invalid_json(self):
        az_json = {'name': 'test1', constants.PROVIDER_NAME: 'noop_driver',
                   constants.AVAILABILITY_ZONE_DATA: '{hello: "world"}'}
        body = self._build_body(az_json)
        self.post(self.AZPS_PATH, body, status=400)

    def test_get(self):
        azp = self.create_availability_zone_profile(
            'name', 'noop_driver', '{"x": "y"}')
        self.assertTrue(uuidutils.is_uuid_like(azp.get('id')))
        response = self.get(
            self.AZP_PATH.format(
                azp_id=azp.get('id'))).json.get(self.root_tag)
        self.assertEqual('name', response.get('name'))
        self.assertEqual(azp.get('id'), response.get('id'))

    def test_get_one_deleted_id(self):
        response = self.get(self.AZP_PATH.format(azp_id=constants.NIL_UUID),
                            status=404)
        self.assertEqual('Availability Zone Profile {} not found.'.format(
            constants.NIL_UUID), response.json.get('faultstring'))

    def test_get_one_fields_filter(self):
        azp = self.create_availability_zone_profile(
            'name', 'noop_driver', '{"x": "y"}')
        self.assertTrue(uuidutils.is_uuid_like(azp.get('id')))
        response = self.get(
            self.AZP_PATH.format(azp_id=azp.get('id')), params={
                'fields': ['id', constants.PROVIDER_NAME]}
        ).json.get(self.root_tag)
        self.assertEqual(azp.get('id'), response.get('id'))
        self.assertIn(u'id', response)
        self.assertIn(constants.PROVIDER_NAME, response)
        self.assertNotIn(u'name', response)
        self.assertNotIn(constants.AVAILABILITY_ZONE_DATA, response)

    def test_get_authorized(self):
        azp = self.create_availability_zone_profile(
            'name', 'noop_driver', '{"x": "y"}')
        self.assertTrue(uuidutils.is_uuid_like(azp.get('id')))
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        project_id = uuidutils.generate_uuid()
        with mock.patch.object(octavia.common.context.Context, 'project_id',
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
                response = self.get(
                    self.AZP_PATH.format(
                        azp_id=azp.get('id'))).json.get(self.root_tag)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual('name', response.get('name'))
        self.assertEqual(azp.get('id'), response.get('id'))

    def test_get_not_authorized(self):
        azp = self.create_availability_zone_profile(
            'name', 'noop_driver', '{"x": "y"}')
        self.assertTrue(uuidutils.is_uuid_like(azp.get('id')))
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        self.get(self.AZP_PATH.format(azp_id=azp.get('id')), status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

    def test_get_all(self):
        fp1 = self.create_availability_zone_profile(
            'test1', 'noop_driver', '{"compute_zone": "my_az_1"}')
        ref_fp_1 = {u'availability_zone_data': u'{"compute_zone": "my_az_1"}',
                    u'id': fp1.get('id'), u'name': u'test1',
                    constants.PROVIDER_NAME: u'noop_driver'}
        self.assertTrue(uuidutils.is_uuid_like(fp1.get('id')))
        fp2 = self.create_availability_zone_profile(
            'test2', 'noop_driver-alt', '{"compute_zone": "my_az_1"}')
        ref_fp_2 = {u'availability_zone_data': u'{"compute_zone": "my_az_1"}',
                    u'id': fp2.get('id'), u'name': u'test2',
                    constants.PROVIDER_NAME: u'noop_driver-alt'}
        self.assertTrue(uuidutils.is_uuid_like(fp2.get('id')))

        response = self.get(self.AZPS_PATH)
        api_list = response.json.get(self.root_tag_list)
        self.assertEqual(2, len(api_list))
        self.assertIn(ref_fp_1, api_list)
        self.assertIn(ref_fp_2, api_list)

    def test_get_all_fields_filter(self):
        fp1 = self.create_availability_zone_profile(
            'test1', 'noop_driver', '{"compute_zone": "my_az_1"}')
        self.assertTrue(uuidutils.is_uuid_like(fp1.get('id')))
        fp2 = self.create_availability_zone_profile(
            'test2', 'noop_driver-alt', '{"compute_zone": "my_az_1"}')
        self.assertTrue(uuidutils.is_uuid_like(fp2.get('id')))

        response = self.get(self.AZPS_PATH, params={
            'fields': ['id', 'name']})
        api_list = response.json.get(self.root_tag_list)
        self.assertEqual(2, len(api_list))
        for profile in api_list:
            self.assertIn(u'id', profile)
            self.assertIn(u'name', profile)
            self.assertNotIn(constants.PROVIDER_NAME, profile)
            self.assertNotIn(constants.AVAILABILITY_ZONE_DATA, profile)

    def test_get_all_authorized(self):
        fp1 = self.create_availability_zone_profile(
            'test1', 'noop_driver', '{"compute_zone": "my_az_1"}')
        self.assertTrue(uuidutils.is_uuid_like(fp1.get('id')))
        fp2 = self.create_availability_zone_profile(
            'test2', 'noop_driver-alt', '{"compute_zone": "my_az_1"}')
        self.assertTrue(uuidutils.is_uuid_like(fp2.get('id')))
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        project_id = uuidutils.generate_uuid()
        with mock.patch.object(octavia.common.context.Context, 'project_id',
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
                response = self.get(self.AZPS_PATH)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        api_list = response.json.get(self.root_tag_list)
        self.assertEqual(2, len(api_list))

    def test_get_all_not_authorized(self):
        fp1 = self.create_availability_zone_profile(
            'test1', 'noop_driver', '{"compute_zone": "my_az_1"}')
        self.assertTrue(uuidutils.is_uuid_like(fp1.get('id')))
        fp2 = self.create_availability_zone_profile(
            'test2', 'noop_driver-alt', '{"compute_zone": "my_az_1"}')
        self.assertTrue(uuidutils.is_uuid_like(fp2.get('id')))

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        self.get(self.AZPS_PATH, status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

    def test_update(self):
        azp = self.create_availability_zone_profile(
            'test_profile', 'noop_driver', '{"x": "y"}')
        update_data = {'name': 'the_profile',
                       constants.PROVIDER_NAME: 'noop_driver-alt',
                       constants.AVAILABILITY_ZONE_DATA: '{"hello": "world"}'}
        body = self._build_body(update_data)
        self.put(self.AZP_PATH.format(azp_id=azp.get('id')), body)
        response = self.get(
            self.AZP_PATH.format(azp_id=azp.get('id'))).json.get(self.root_tag)
        self.assertEqual('the_profile', response.get('name'))
        self.assertEqual('noop_driver-alt',
                         response.get(constants.PROVIDER_NAME))
        self.assertEqual('{"hello": "world"}',
                         response.get(constants.AVAILABILITY_ZONE_DATA))

    def test_update_deleted_id(self):
        update_data = {'name': 'fake_profile'}
        body = self._build_body(update_data)
        response = self.put(self.AZP_PATH.format(azp_id=constants.NIL_UUID),
                            body, status=404)
        self.assertEqual('Availability Zone Profile {} not found.'.format(
            constants.NIL_UUID), response.json.get('faultstring'))

    def test_update_nothing(self):
        azp = self.create_availability_zone_profile(
            'test_profile', 'noop_driver', '{"x": "y"}')
        body = self._build_body({})
        self.put(self.AZP_PATH.format(azp_id=azp.get('id')), body)
        response = self.get(
            self.AZP_PATH.format(azp_id=azp.get('id'))).json.get(self.root_tag)
        self.assertEqual('test_profile', response.get('name'))
        self.assertEqual('noop_driver', response.get(constants.PROVIDER_NAME))
        self.assertEqual('{"x": "y"}',
                         response.get(constants.AVAILABILITY_ZONE_DATA))

    def test_update_name_none(self):
        self._test_update_param_none(constants.NAME)

    def test_update_provider_name_none(self):
        self._test_update_param_none(constants.PROVIDER_NAME)

    def test_update_availability_zone_data_none(self):
        self._test_update_param_none(constants.AVAILABILITY_ZONE_DATA)

    def _test_update_param_none(self, param_name):
        azp = self.create_availability_zone_profile(
            'test_profile', 'noop_driver', '{"x": "y"}')
        expect_error_msg = ("None is not a valid option for %s" %
                            param_name)
        body = self._build_body({param_name: None})
        response = self.put(self.AZP_PATH.format(azp_id=azp.get('id')), body,
                            status=400)
        self.assertEqual(expect_error_msg, response.json['faultstring'])

    def test_update_no_availability_zone_data(self):
        azp = self.create_availability_zone_profile(
            'test_profile', 'noop_driver', '{"x": "y"}')
        update_data = {'name': 'the_profile',
                       constants.PROVIDER_NAME: 'noop_driver-alt'}
        body = self._build_body(update_data)
        response = self.put(self.AZP_PATH.format(azp_id=azp.get('id')), body)
        response = self.get(
            self.AZP_PATH.format(azp_id=azp.get('id'))).json.get(self.root_tag)
        self.assertEqual('the_profile', response.get('name'))
        self.assertEqual('noop_driver-alt',
                         response.get(constants.PROVIDER_NAME))
        self.assertEqual('{"x": "y"}',
                         response.get(constants.AVAILABILITY_ZONE_DATA))

    def test_update_authorized(self):
        azp = self.create_availability_zone_profile(
            'test_profile', 'noop_driver', '{"x": "y"}')
        update_data = {'name': 'the_profile',
                       constants.PROVIDER_NAME: 'noop_driver-alt',
                       constants.AVAILABILITY_ZONE_DATA: '{"hello": "world"}'}
        body = self._build_body(update_data)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        project_id = uuidutils.generate_uuid()
        with mock.patch.object(octavia.common.context.Context, 'project_id',
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
                response = self.put(self.AZP_PATH.format(azp_id=azp.get('id')),
                                    body)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        response = self.get(
            self.AZP_PATH.format(azp_id=azp.get('id'))).json.get(self.root_tag)
        self.assertEqual('the_profile', response.get('name'))
        self.assertEqual('noop_driver-alt',
                         response.get(constants.PROVIDER_NAME))
        self.assertEqual('{"hello": "world"}',
                         response.get(constants.AVAILABILITY_ZONE_DATA))

    def test_update_not_authorized(self):
        azp = self.create_availability_zone_profile(
            'test_profile', 'noop_driver', '{"x": "y"}')
        update_data = {'name': 'the_profile', constants.PROVIDER_NAME: 'amp',
                       constants.AVAILABILITY_ZONE_DATA: '{"hello": "world"}'}
        body = self._build_body(update_data)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        response = self.put(self.AZP_PATH.format(azp_id=azp.get('id')),
                            body, status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        response = self.get(
            self.AZP_PATH.format(azp_id=azp.get('id'))).json.get(self.root_tag)
        self.assertEqual('test_profile', response.get('name'))
        self.assertEqual('noop_driver', response.get(constants.PROVIDER_NAME))
        self.assertEqual('{"x": "y"}',
                         response.get(constants.AVAILABILITY_ZONE_DATA))

    def test_update_in_use(self):
        azp = self.create_availability_zone_profile(
            'test_profile', 'noop_driver', '{"x": "y"}')
        self.create_availability_zone(
            'name1', 'description', azp.get('id'), True)

        # Test updating provider while in use is not allowed
        update_data = {'name': 'the_profile',
                       constants.PROVIDER_NAME: 'noop_driver-alt'}
        body = self._build_body(update_data)
        response = self.put(self.AZP_PATH.format(azp_id=azp.get('id')), body,
                            status=409)
        err_msg = ("Availability Zone Profile {} is in use and cannot be "
                   "modified.".format(azp.get('id')))
        self.assertEqual(err_msg, response.json.get('faultstring'))
        response = self.get(
            self.AZP_PATH.format(azp_id=azp.get('id'))).json.get(self.root_tag)
        self.assertEqual('test_profile', response.get('name'))
        self.assertEqual('noop_driver', response.get(constants.PROVIDER_NAME))
        self.assertEqual('{"x": "y"}',
                         response.get(constants.AVAILABILITY_ZONE_DATA))

        # Test updating availability zone data while in use is not allowed
        update_data = {'name': 'the_profile',
                       constants.AVAILABILITY_ZONE_DATA: '{"hello": "world"}'}
        body = self._build_body(update_data)
        response = self.put(self.AZP_PATH.format(azp_id=azp.get('id')), body,
                            status=409)
        err_msg = ("Availability Zone Profile {} is in use and cannot be "
                   "modified.".format(azp.get('id')))
        self.assertEqual(err_msg, response.json.get('faultstring'))
        response = self.get(
            self.AZP_PATH.format(azp_id=azp.get('id'))).json.get(self.root_tag)
        self.assertEqual('test_profile', response.get('name'))
        self.assertEqual('noop_driver', response.get(constants.PROVIDER_NAME))
        self.assertEqual('{"x": "y"}',
                         response.get(constants.AVAILABILITY_ZONE_DATA))

        # Test that you can still update the name when in use
        update_data = {'name': 'the_profile'}
        body = self._build_body(update_data)
        response = self.put(self.AZP_PATH.format(azp_id=azp.get('id')), body)
        response = self.get(
            self.AZP_PATH.format(azp_id=azp.get('id'))).json.get(self.root_tag)
        self.assertEqual('the_profile', response.get('name'))
        self.assertEqual('noop_driver', response.get(constants.PROVIDER_NAME))
        self.assertEqual('{"x": "y"}',
                         response.get(constants.AVAILABILITY_ZONE_DATA))

    def test_delete(self):
        azp = self.create_availability_zone_profile(
            'test1', 'noop_driver', '{"compute_zone": "my_az_1"}')
        self.assertTrue(uuidutils.is_uuid_like(azp.get('id')))
        self.delete(self.AZP_PATH.format(azp_id=azp.get('id')))
        response = self.get(self.AZP_PATH.format(
            azp_id=azp.get('id')), status=404)
        err_msg = "Availability Zone Profile %s not found." % azp.get('id')
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_delete_deleted_id(self):
        response = self.delete(self.AZP_PATH.format(azp_id=constants.NIL_UUID),
                               status=404)
        self.assertEqual('Availability Zone Profile {} not found.'.format(
            constants.NIL_UUID), response.json.get('faultstring'))

    def test_delete_nonexistent_id(self):
        response = self.delete(self.AZP_PATH.format(azp_id='bogus_id'),
                               status=404)
        self.assertEqual('Availability Zone Profile bogus_id not found.',
                         response.json.get('faultstring'))

    def test_delete_authorized(self):
        azp = self.create_availability_zone_profile(
            'test1', 'noop_driver', '{"compute_zone": "my_az_1"}')
        self.assertTrue(uuidutils.is_uuid_like(azp.get('id')))
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        project_id = uuidutils.generate_uuid()
        with mock.patch.object(octavia.common.context.Context, 'project_id',
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
                self.delete(self.AZP_PATH.format(azp_id=azp.get('id')))
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        response = self.get(self.AZP_PATH.format(
            azp_id=azp.get('id')), status=404)
        err_msg = "Availability Zone Profile %s not found." % azp.get('id')
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_delete_not_authorized(self):
        azp = self.create_availability_zone_profile(
            'test1', 'noop_driver', '{"compute_zone": "my_az_1"}')
        self.assertTrue(uuidutils.is_uuid_like(azp.get('id')))
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)

        response = self.delete(self.AZP_PATH.format(
            azp_id=azp.get('id')), status=403)
        api_azp = response.json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, api_azp)
        response = self.get(
            self.AZP_PATH.format(azp_id=azp.get('id'))).json.get(self.root_tag)
        self.assertEqual('test1', response.get('name'))

    def test_delete_in_use(self):
        azp = self.create_availability_zone_profile(
            'test1', 'noop_driver', '{"compute_zone": "my_az_1"}')
        self.create_availability_zone(
            'name1', 'description', azp.get('id'), True)
        response = self.delete(self.AZP_PATH.format(azp_id=azp.get('id')),
                               status=409)
        err_msg = ("Availability Zone Profile {} is in use and cannot be "
                   "modified.".format(azp.get('id')))
        self.assertEqual(err_msg, response.json.get('faultstring'))
        response = self.get(
            self.AZP_PATH.format(azp_id=azp.get('id'))).json.get(self.root_tag)
        self.assertEqual('test1', response.get('name'))
