#    Copyright 2017 Walmart Stores Inc.
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
from oslo_db import exception as odb_exceptions
from oslo_utils import uuidutils

from octavia.common import constants
import octavia.common.context
from octavia.tests.functional.api.v2 import base


class TestFlavorProfiles(base.BaseAPITest):
    root_tag = 'flavorprofile'
    root_tag_list = 'flavorprofiles'
    root_tag_links = 'flavorprofile_links'

    def _assert_request_matches_response(self, req, resp, **optionals):
        self.assertTrue(uuidutils.is_uuid_like(resp.get('id')))
        self.assertEqual(req.get('name'), resp.get('name'))
        self.assertEqual(req.get('provider_name'),
                         resp.get('provider_name'))
        self.assertEqual(req.get(constants.FLAVOR_DATA),
                         resp.get(constants.FLAVOR_DATA))

    def test_empty_list(self):
        response = self.get(self.FPS_PATH)
        api_list = response.json.get(self.root_tag_list)
        self.assertEqual([], api_list)

    def test_create(self):
        fp_json = {'name': 'test1', 'provider_name': 'noop_driver',
                   constants.FLAVOR_DATA: '{"hello": "world"}'}
        body = self._build_body(fp_json)
        response = self.post(self.FPS_PATH, body)
        api_fp = response.json.get(self.root_tag)
        self._assert_request_matches_response(fp_json, api_fp)

    def test_create_with_missing_name(self):
        fp_json = {'provider_name': 'pr1', constants.FLAVOR_DATA: '{"x": "y"}'}
        body = self._build_body(fp_json)
        response = self.post(self.FPS_PATH, body, status=400)
        err_msg = ("Invalid input for field/attribute name. Value: "
                   "'None'. Mandatory field missing.")
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_missing_provider(self):
        fp_json = {'name': 'xyz', constants.FLAVOR_DATA: '{"x": "y"}'}
        body = self._build_body(fp_json)
        response = self.post(self.FPS_PATH, body, status=400)
        err_msg = ("Invalid input for field/attribute provider_name. "
                   "Value: 'None'. Mandatory field missing.")
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_missing_flavor_data(self):
        fp_json = {'name': 'xyz', 'provider_name': 'pr1'}
        body = self._build_body(fp_json)
        response = self.post(self.FPS_PATH, body, status=400)
        err_msg = ("Invalid input for field/attribute flavor_data. "
                   "Value: 'None'. Mandatory field missing.")
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_empty_flavor_data(self):
        fp_json = {'name': 'test1', 'provider_name': 'noop_driver',
                   constants.FLAVOR_DATA: '{}'}
        body = self._build_body(fp_json)
        response = self.post(self.FPS_PATH, body)
        api_fp = response.json.get(self.root_tag)
        self._assert_request_matches_response(fp_json, api_fp)

    def test_create_with_long_name(self):
        fp_json = {'name': 'n' * 256, 'provider_name': 'test1',
                   constants.FLAVOR_DATA: '{"hello": "world"}'}
        body = self._build_body(fp_json)
        self.post(self.FPS_PATH, body, status=400)

    def test_create_with_long_provider(self):
        fp_json = {'name': 'name1', 'provider_name': 'n' * 256,
                   constants.FLAVOR_DATA: '{"hello": "world"}'}
        body = self._build_body(fp_json)
        self.post(self.FPS_PATH, body, status=400)

    def test_create_with_long_flavor_data(self):
        fp_json = {'name': 'name1', 'provider_name': 'amp',
                   constants.FLAVOR_DATA: 'n' * 4097}
        body = self._build_body(fp_json)
        self.post(self.FPS_PATH, body, status=400)

    def test_create_authorized(self):
        fp_json = {'name': 'test1', 'provider_name': 'noop_driver',
                   constants.FLAVOR_DATA: '{"hello": "world"}'}
        body = self._build_body(fp_json)
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
                response = self.post(self.FPS_PATH, body)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        api_fp = response.json.get(self.root_tag)
        self._assert_request_matches_response(fp_json, api_fp)

    def test_create_not_authorized(self):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        fp_json = {'name': 'name',
                   'provider_name': 'xyz', constants.FLAVOR_DATA: '{"x": "y"}'}
        body = self._build_body(fp_json)
        response = self.post(self.FPS_PATH, body, status=403)
        api_fp = response.json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, api_fp)

    def test_create_db_failure(self):
        fp_json = {'name': 'test1', 'provider_name': 'noop_driver',
                   constants.FLAVOR_DATA: '{"hello": "world"}'}
        body = self._build_body(fp_json)
        with mock.patch("octavia.db.repositories.FlavorProfileRepository."
                        "create") as mock_create:
            mock_create.side_effect = Exception
            self.post(self.FPS_PATH, body, status=500)

            mock_create.side_effect = odb_exceptions.DBDuplicateEntry
            self.post(self.FPS_PATH, body, status=409)

    def test_create_with_invalid_json(self):
        fp_json = {'name': 'test1', 'provider_name': 'noop_driver',
                   constants.FLAVOR_DATA: '{hello: "world"}'}
        body = self._build_body(fp_json)
        self.post(self.FPS_PATH, body, status=400)

    def test_get(self):
        fp = self.create_flavor_profile('name', 'noop_driver',
                                        '{"x": "y"}')
        self.assertTrue(uuidutils.is_uuid_like(fp.get('id')))
        response = self.get(
            self.FP_PATH.format(
                fp_id=fp.get('id'))).json.get(self.root_tag)
        self.assertEqual('name', response.get('name'))
        self.assertEqual(fp.get('id'), response.get('id'))

    def test_get_one_fields_filter(self):
        fp = self.create_flavor_profile('name', 'noop_driver',
                                        '{"x": "y"}')
        self.assertTrue(uuidutils.is_uuid_like(fp.get('id')))
        response = self.get(
            self.FP_PATH.format(fp_id=fp.get('id')), params={
                'fields': ['id', 'provider_name']}).json.get(self.root_tag)
        self.assertEqual(fp.get('id'), response.get('id'))
        self.assertIn(u'id', response)
        self.assertIn(u'provider_name', response)
        self.assertNotIn(u'name', response)
        self.assertNotIn(constants.FLAVOR_DATA, response)

    def test_get_authorized(self):
        fp = self.create_flavor_profile('name', 'noop_driver',
                                        '{"x": "y"}')
        self.assertTrue(uuidutils.is_uuid_like(fp.get('id')))
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
                    self.FP_PATH.format(
                        fp_id=fp.get('id'))).json.get(self.root_tag)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual('name', response.get('name'))
        self.assertEqual(fp.get('id'), response.get('id'))

    def test_get_not_authorized(self):
        fp = self.create_flavor_profile('name', 'noop_driver',
                                        '{"x": "y"}')
        self.assertTrue(uuidutils.is_uuid_like(fp.get('id')))
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        self.get(self.FP_PATH.format(fp_id=fp.get('id')), status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

    def test_get_all(self):
        fp1 = self.create_flavor_profile('test1', 'noop_driver',
                                         '{"image": "ubuntu"}')
        ref_fp_1 = {u'flavor_data': u'{"image": "ubuntu"}',
                    u'id': fp1.get('id'), u'name': u'test1',
                    u'provider_name': u'noop_driver'}
        self.assertTrue(uuidutils.is_uuid_like(fp1.get('id')))
        fp2 = self.create_flavor_profile('test2', 'noop_driver-alt',
                                         '{"image": "ubuntu"}')
        ref_fp_2 = {u'flavor_data': u'{"image": "ubuntu"}',
                    u'id': fp2.get('id'), u'name': u'test2',
                    u'provider_name': u'noop_driver-alt'}
        self.assertTrue(uuidutils.is_uuid_like(fp2.get('id')))

        response = self.get(self.FPS_PATH)
        api_list = response.json.get(self.root_tag_list)
        self.assertEqual(2, len(api_list))
        self.assertIn(ref_fp_1, api_list)
        self.assertIn(ref_fp_2, api_list)

    def test_get_all_fields_filter(self):
        fp1 = self.create_flavor_profile('test1', 'noop_driver',
                                         '{"image": "ubuntu"}')
        self.assertTrue(uuidutils.is_uuid_like(fp1.get('id')))
        fp2 = self.create_flavor_profile('test2', 'noop_driver-alt',
                                         '{"image": "ubuntu"}')
        self.assertTrue(uuidutils.is_uuid_like(fp2.get('id')))

        response = self.get(self.FPS_PATH, params={
            'fields': ['id', 'name']})
        api_list = response.json.get(self.root_tag_list)
        self.assertEqual(2, len(api_list))
        for profile in api_list:
            self.assertIn(u'id', profile)
            self.assertIn(u'name', profile)
            self.assertNotIn(u'provider_name', profile)
            self.assertNotIn(constants.FLAVOR_DATA, profile)

    def test_get_all_authorized(self):
        fp1 = self.create_flavor_profile('test1', 'noop_driver',
                                         '{"image": "ubuntu"}')
        self.assertTrue(uuidutils.is_uuid_like(fp1.get('id')))
        fp2 = self.create_flavor_profile('test2', 'noop_driver-alt',
                                         '{"image": "ubuntu"}')
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
                response = self.get(self.FPS_PATH)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        api_list = response.json.get(self.root_tag_list)
        self.assertEqual(2, len(api_list))

    def test_get_all_not_authorized(self):
        fp1 = self.create_flavor_profile('test1', 'noop_driver',
                                         '{"image": "ubuntu"}')
        self.assertTrue(uuidutils.is_uuid_like(fp1.get('id')))
        fp2 = self.create_flavor_profile('test2', 'noop_driver-alt',
                                         '{"image": "ubuntu"}')
        self.assertTrue(uuidutils.is_uuid_like(fp2.get('id')))

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        self.get(self.FPS_PATH, status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

    def test_update(self):
        fp = self.create_flavor_profile('test_profile', 'noop_driver',
                                        '{"x": "y"}')
        update_data = {'name': 'the_profile',
                       'provider_name': 'noop_driver-alt',
                       constants.FLAVOR_DATA: '{"hello": "world"}'}
        body = self._build_body(update_data)
        response = self.put(self.FP_PATH.format(fp_id=fp.get('id')), body)
        response = self.get(
            self.FP_PATH.format(fp_id=fp.get('id'))).json.get(self.root_tag)
        self.assertEqual('the_profile', response.get('name'))
        self.assertEqual('noop_driver-alt', response.get('provider_name'))
        self.assertEqual('{"hello": "world"}',
                         response.get(constants.FLAVOR_DATA))

    def test_update_none(self):
        fp = self.create_flavor_profile('test_profile', 'noop_driver',
                                        '{"x": "y"}')
        body = self._build_body({})
        response = self.put(self.FP_PATH.format(fp_id=fp.get('id')), body)
        response = self.get(
            self.FP_PATH.format(fp_id=fp.get('id'))).json.get(self.root_tag)
        self.assertEqual('test_profile', response.get('name'))
        self.assertEqual('noop_driver', response.get('provider_name'))
        self.assertEqual('{"x": "y"}',
                         response.get(constants.FLAVOR_DATA))

    def test_update_no_flavor_data(self):
        fp = self.create_flavor_profile('test_profile', 'noop_driver',
                                        '{"x": "y"}')
        update_data = {'name': 'the_profile',
                       'provider_name': 'noop_driver-alt'}
        body = self._build_body(update_data)
        response = self.put(self.FP_PATH.format(fp_id=fp.get('id')), body)
        response = self.get(
            self.FP_PATH.format(fp_id=fp.get('id'))).json.get(self.root_tag)
        self.assertEqual('the_profile', response.get('name'))
        self.assertEqual('noop_driver-alt', response.get('provider_name'))
        self.assertEqual('{"x": "y"}', response.get(constants.FLAVOR_DATA))

    def test_update_authorized(self):
        fp = self.create_flavor_profile('test_profile', 'noop_driver',
                                        '{"x": "y"}')
        update_data = {'name': 'the_profile',
                       'provider_name': 'noop_driver-alt',
                       constants.FLAVOR_DATA: '{"hello": "world"}'}
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
                response = self.put(self.FP_PATH.format(fp_id=fp.get('id')),
                                    body)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        response = self.get(
            self.FP_PATH.format(fp_id=fp.get('id'))).json.get(self.root_tag)
        self.assertEqual('the_profile', response.get('name'))
        self.assertEqual('noop_driver-alt', response.get('provider_name'))
        self.assertEqual('{"hello": "world"}',
                         response.get(constants.FLAVOR_DATA))

    def test_update_not_authorized(self):
        fp = self.create_flavor_profile('test_profile', 'noop_driver',
                                        '{"x": "y"}')
        update_data = {'name': 'the_profile', 'provider_name': 'amp',
                       constants.FLAVOR_DATA: '{"hello": "world"}'}
        body = self._build_body(update_data)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        response = self.put(self.FP_PATH.format(fp_id=fp.get('id')),
                            body, status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        response = self.get(
            self.FP_PATH.format(fp_id=fp.get('id'))).json.get(self.root_tag)
        self.assertEqual('test_profile', response.get('name'))
        self.assertEqual('noop_driver', response.get('provider_name'))
        self.assertEqual('{"x": "y"}',
                         response.get(constants.FLAVOR_DATA))

    def test_update_in_use(self):
        fp = self.create_flavor_profile('test_profile', 'noop_driver',
                                        '{"x": "y"}')
        self.create_flavor('name1', 'description', fp.get('id'), True)

        # Test updating provider while in use is not allowed
        update_data = {'name': 'the_profile',
                       'provider_name': 'noop_driver-alt'}
        body = self._build_body(update_data)
        response = self.put(self.FP_PATH.format(fp_id=fp.get('id')), body,
                            status=409)
        err_msg = ("Flavor profile {} is in use and cannot be "
                   "modified.".format(fp.get('id')))
        self.assertEqual(err_msg, response.json.get('faultstring'))
        response = self.get(
            self.FP_PATH.format(fp_id=fp.get('id'))).json.get(self.root_tag)
        self.assertEqual('test_profile', response.get('name'))
        self.assertEqual('noop_driver', response.get('provider_name'))
        self.assertEqual('{"x": "y"}', response.get(constants.FLAVOR_DATA))

        # Test updating flavor data while in use is not allowed
        update_data = {'name': 'the_profile',
                       constants.FLAVOR_DATA: '{"hello": "world"}'}
        body = self._build_body(update_data)
        response = self.put(self.FP_PATH.format(fp_id=fp.get('id')), body,
                            status=409)
        err_msg = ("Flavor profile {} is in use and cannot be "
                   "modified.".format(fp.get('id')))
        self.assertEqual(err_msg, response.json.get('faultstring'))
        response = self.get(
            self.FP_PATH.format(fp_id=fp.get('id'))).json.get(self.root_tag)
        self.assertEqual('test_profile', response.get('name'))
        self.assertEqual('noop_driver', response.get('provider_name'))
        self.assertEqual('{"x": "y"}', response.get(constants.FLAVOR_DATA))

        # Test that you can still update the name when in use
        update_data = {'name': 'the_profile'}
        body = self._build_body(update_data)
        response = self.put(self.FP_PATH.format(fp_id=fp.get('id')), body)
        response = self.get(
            self.FP_PATH.format(fp_id=fp.get('id'))).json.get(self.root_tag)
        self.assertEqual('the_profile', response.get('name'))
        self.assertEqual('noop_driver', response.get('provider_name'))
        self.assertEqual('{"x": "y"}', response.get(constants.FLAVOR_DATA))

    def test_delete(self):
        fp = self.create_flavor_profile('test1', 'noop_driver',
                                        '{"image": "ubuntu"}')
        self.assertTrue(uuidutils.is_uuid_like(fp.get('id')))
        self.delete(self.FP_PATH.format(fp_id=fp.get('id')))
        response = self.get(self.FP_PATH.format(
            fp_id=fp.get('id')), status=404)
        err_msg = "Flavor Profile %s not found." % fp.get('id')
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_delete_authorized(self):
        fp = self.create_flavor_profile('test1', 'noop_driver',
                                        '{"image": "ubuntu"}')
        self.assertTrue(uuidutils.is_uuid_like(fp.get('id')))
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
                self.delete(self.FP_PATH.format(fp_id=fp.get('id')))
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        response = self.get(self.FP_PATH.format(
            fp_id=fp.get('id')), status=404)
        err_msg = "Flavor Profile %s not found." % fp.get('id')
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_delete_not_authorized(self):
        fp = self.create_flavor_profile('test1', 'noop_driver',
                                        '{"image": "ubuntu"}')
        self.assertTrue(uuidutils.is_uuid_like(fp.get('id')))
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)

        response = self.delete(self.FP_PATH.format(
            fp_id=fp.get('id')), status=403)
        api_fp = response.json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, api_fp)
        response = self.get(
            self.FP_PATH.format(fp_id=fp.get('id'))).json.get(self.root_tag)
        self.assertEqual('test1', response.get('name'))

    def test_delete_in_use(self):
        fp = self.create_flavor_profile('test1', 'noop_driver',
                                        '{"image": "ubuntu"}')
        self.create_flavor('name1', 'description', fp.get('id'), True)
        response = self.delete(self.FP_PATH.format(fp_id=fp.get('id')),
                               status=409)
        err_msg = ("Flavor profile {} is in use and cannot be "
                   "modified.".format(fp.get('id')))
        self.assertEqual(err_msg, response.json.get('faultstring'))
        response = self.get(
            self.FP_PATH.format(fp_id=fp.get('id'))).json.get(self.root_tag)
        self.assertEqual('test1', response.get('name'))
