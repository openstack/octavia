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

from oslo_utils import uuidutils

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture

from octavia.common import constants
import octavia.common.context
from octavia.tests.functional.api.v2 import base


class TestFlavors(base.BaseAPITest):
    root_tag = 'flavor'
    root_tag_list = 'flavors'
    root_tag_links = 'flavors_links'

    def setUp(self):
        super(TestFlavors, self).setUp()
        self.fp = self.create_flavor_profile('test1', 'noop_driver',
                                             '{"image": "ubuntu"}')

    def _assert_request_matches_response(self, req, resp, **optionals):
        self.assertTrue(uuidutils.is_uuid_like(resp.get('id')))
        req_description = req.get('description')
        self.assertEqual(req.get('name'), resp.get('name'))
        if not req_description:
            self.assertEqual('', resp.get('description'))
        else:
            self.assertEqual(req.get('description'), resp.get('description'))
        self.assertEqual(req.get('flavor_profile_id'),
                         resp.get('flavor_profile_id'))
        self.assertEqual(req.get('enabled', True),
                         resp.get('enabled'))

    def test_empty_list(self):
        response = self.get(self.FLAVORS_PATH)
        api_list = response.json.get(self.root_tag_list)
        self.assertEqual([], api_list)

    def test_create(self):
        flavor_json = {'name': 'test1',
                       'flavor_profile_id': self.fp.get('id')}
        body = self._build_body(flavor_json)
        response = self.post(self.FLAVORS_PATH, body)
        api_flavor = response.json.get(self.root_tag)
        self._assert_request_matches_response(flavor_json, api_flavor)

    def test_create_with_missing_name(self):
        flavor_json = {'flavor_profile_id': self.fp.get('id')}
        body = self._build_body(flavor_json)
        response = self.post(self.FLAVORS_PATH, body, status=400)
        err_msg = ("Invalid input for field/attribute name. Value: "
                   "'None'. Mandatory field missing.")
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_long_name(self):
        flavor_json = {'name': 'n' * 256,
                       'flavor_profile_id': self.fp.get('id')}
        body = self._build_body(flavor_json)
        self.post(self.FLAVORS_PATH, body, status=400)

    def test_create_with_long_description(self):
        flavor_json = {'name': 'test-flavor',
                       'description': 'n' * 256,
                       'flavor_profile_id': self.fp.get('id')}
        body = self._build_body(flavor_json)
        self.post(self.FLAVORS_PATH, body, status=400)

    def test_create_with_missing_flavor_profile(self):
        flavor_json = {'name': 'xyz'}
        body = self._build_body(flavor_json)
        response = self.post(self.FLAVORS_PATH, body, status=400)
        err_msg = ("Invalid input for field/attribute flavor_profile_id. "
                   "Value: 'None'. Mandatory field missing.")
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_with_bad_flavor_profile(self):
        flavor_json = {'name': 'xyz', 'flavor_profile_id': 'bogus'}
        body = self._build_body(flavor_json)
        response = self.post(self.FLAVORS_PATH, body, status=400)
        err_msg = ("Invalid input for field/attribute flavor_profile_id. "
                   "Value: 'bogus'. Value should be UUID format")
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_duplicate_names(self):
        flavor1 = self.create_flavor('name', 'description', self.fp.get('id'),
                                     True)
        self.assertTrue(uuidutils.is_uuid_like(flavor1.get('id')))
        flavor_json = {'name': 'name',
                       'flavor_profile_id': self.fp.get('id')}
        body = self._build_body(flavor_json)
        response = self.post(self.FLAVORS_PATH, body, status=409)
        err_msg = "A flavor of name already exists."
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_create_authorized(self):
        flavor_json = {'name': 'test1',
                       'flavor_profile_id': self.fp.get('id')}
        body = self._build_body(flavor_json)
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
                response = self.post(self.FLAVORS_PATH, body)
        api_flavor = response.json.get(self.root_tag)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self._assert_request_matches_response(flavor_json, api_flavor)

    def test_create_not_authorized(self):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        flavor_json = {'name': 'name',
                       'flavor_profile_id': self.fp.get('id')}
        body = self._build_body(flavor_json)
        response = self.post(self.FLAVORS_PATH, body, status=403)
        api_flavor = response.json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, api_flavor)

    def test_create_db_failure(self):
        flavor_json = {'name': 'test1',
                       'flavor_profile_id': self.fp.get('id')}
        body = self._build_body(flavor_json)
        with mock.patch("octavia.db.repositories.FlavorRepository."
                        "create") as mock_create:
            mock_create.side_effect = Exception
            self.post(self.FLAVORS_PATH, body, status=500)

    def test_get(self):
        flavor = self.create_flavor('name', 'description', self.fp.get('id'),
                                    True)
        self.assertTrue(uuidutils.is_uuid_like(flavor.get('id')))
        response = self.get(
            self.FLAVOR_PATH.format(
                flavor_id=flavor.get('id'))).json.get(self.root_tag)
        self.assertEqual('name', response.get('name'))
        self.assertEqual('description', response.get('description'))
        self.assertEqual(flavor.get('id'), response.get('id'))
        self.assertEqual(self.fp.get('id'), response.get('flavor_profile_id'))
        self.assertTrue(response.get('enabled'))

    def test_get_one_fields_filter(self):
        flavor = self.create_flavor('name', 'description', self.fp.get('id'),
                                    True)
        self.assertTrue(uuidutils.is_uuid_like(flavor.get('id')))
        response = self.get(
            self.FLAVOR_PATH.format(flavor_id=flavor.get('id')), params={
                'fields': ['id', 'flavor_profile_id']}).json.get(self.root_tag)
        self.assertEqual(flavor.get('id'), response.get('id'))
        self.assertEqual(self.fp.get('id'), response.get('flavor_profile_id'))
        self.assertIn(u'id', response)
        self.assertIn(u'flavor_profile_id', response)
        self.assertNotIn(u'name', response)
        self.assertNotIn(u'description', response)
        self.assertNotIn(u'enabled', response)

    def test_get_authorized(self):
        flavor = self.create_flavor('name', 'description', self.fp.get('id'),
                                    True)
        self.assertTrue(uuidutils.is_uuid_like(flavor.get('id')))

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
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                response = self.get(
                    self.FLAVOR_PATH.format(
                        flavor_id=flavor.get('id'))).json.get(self.root_tag)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual('name', response.get('name'))
        self.assertEqual('description', response.get('description'))
        self.assertEqual(flavor.get('id'), response.get('id'))
        self.assertEqual(self.fp.get('id'), response.get('flavor_profile_id'))
        self.assertTrue(response.get('enabled'))

    def test_get_not_authorized(self):
        flavor = self.create_flavor('name', 'description', self.fp.get('id'),
                                    True)
        self.assertTrue(uuidutils.is_uuid_like(flavor.get('id')))
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        response = self.get(self.FLAVOR_PATH.format(
            flavor_id=flavor.get('id')), status=403).json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response)

    def test_get_all(self):
        ref_flavor_1 = {
            u'description': u'description', u'enabled': True,
            u'flavor_profile_id': u'd21bf20d-c323-4004-bf67-f90591ceced9',
            u'id': u'172ccb10-a3b7-4c73-aee8-bdb77fb51ed5',
            u'name': u'name1'}
        flavor1 = self.create_flavor('name1', 'description', self.fp.get('id'),
                                     True)
        self.assertTrue(uuidutils.is_uuid_like(flavor1.get('id')))
        ref_flavor_1 = {
            u'description': u'description', u'enabled': True,
            u'flavor_profile_id': self.fp.get('id'),
            u'id': flavor1.get('id'),
            u'name': u'name1'}
        flavor2 = self.create_flavor('name2', 'description', self.fp.get('id'),
                                     True)
        self.assertTrue(uuidutils.is_uuid_like(flavor2.get('id')))
        ref_flavor_2 = {
            u'description': u'description', u'enabled': True,
            u'flavor_profile_id': self.fp.get('id'),
            u'id': flavor2.get('id'),
            u'name': u'name2'}
        response = self.get(self.FLAVORS_PATH)
        api_list = response.json.get(self.root_tag_list)
        self.assertEqual(2, len(api_list))
        self.assertIn(ref_flavor_1, api_list)
        self.assertIn(ref_flavor_2, api_list)

    def test_get_all_fields_filter(self):
        flavor1 = self.create_flavor('name1', 'description', self.fp.get('id'),
                                     True)
        self.assertTrue(uuidutils.is_uuid_like(flavor1.get('id')))
        flavor2 = self.create_flavor('name2', 'description', self.fp.get('id'),
                                     True)
        self.assertTrue(uuidutils.is_uuid_like(flavor2.get('id')))
        response = self.get(self.FLAVORS_PATH, params={
            'fields': ['id', 'name']})
        api_list = response.json.get(self.root_tag_list)
        self.assertEqual(2, len(api_list))
        for flavor in api_list:
            self.assertIn(u'id', flavor)
            self.assertIn(u'name', flavor)
            self.assertNotIn(u'flavor_profile_id', flavor)
            self.assertNotIn(u'description', flavor)
            self.assertNotIn(u'enabled', flavor)

    def test_get_all_authorized(self):
        flavor1 = self.create_flavor('name1', 'description', self.fp.get('id'),
                                     True)
        self.assertTrue(uuidutils.is_uuid_like(flavor1.get('id')))
        flavor2 = self.create_flavor('name2', 'description', self.fp.get('id'),
                                     True)
        self.assertTrue(uuidutils.is_uuid_like(flavor2.get('id')))
        response = self.get(self.FLAVORS_PATH)

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
        flavor1 = self.create_flavor('name1', 'description', self.fp.get('id'),
                                     True)
        self.assertTrue(uuidutils.is_uuid_like(flavor1.get('id')))
        flavor2 = self.create_flavor('name2', 'description', self.fp.get('id'),
                                     True)
        self.assertTrue(uuidutils.is_uuid_like(flavor2.get('id')))
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        response = self.get(self.FLAVORS_PATH, status=403).json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response)

    def test_update(self):
        flavor_json = {'name': 'Fancy_Flavor',
                       'description': 'A great flavor. Pick me!',
                       'flavor_profile_id': self.fp.get('id')}
        body = self._build_body(flavor_json)
        response = self.post(self.FLAVORS_PATH, body)
        api_flavor = response.json.get(self.root_tag)
        flavor_id = api_flavor.get('id')

        flavor_json = {'name': 'Better_Flavor',
                       'description': 'An even better flavor. Pick me!',
                       'enabled': False}
        body = self._build_body(flavor_json)
        response = self.put(self.FLAVOR_PATH.format(flavor_id=flavor_id), body)

        updated_flavor = self.get(self.FLAVOR_PATH.format(
            flavor_id=flavor_id)).json.get(self.root_tag)
        self.assertEqual('Better_Flavor', updated_flavor.get('name'))
        self.assertEqual('An even better flavor. Pick me!',
                         updated_flavor.get('description'))
        self.assertEqual(flavor_id, updated_flavor.get('id'))
        self.assertEqual(self.fp.get('id'),
                         updated_flavor.get('flavor_profile_id'))
        self.assertFalse(updated_flavor.get('enabled'))

    def test_update_none(self):
        flavor_json = {'name': 'Fancy_Flavor',
                       'description': 'A great flavor. Pick me!',
                       'flavor_profile_id': self.fp.get('id')}
        body = self._build_body(flavor_json)
        response = self.post(self.FLAVORS_PATH, body)
        api_flavor = response.json.get(self.root_tag)
        flavor_id = api_flavor.get('id')

        flavor_json = {}
        body = self._build_body(flavor_json)
        response = self.put(self.FLAVOR_PATH.format(flavor_id=flavor_id), body)

        updated_flavor = self.get(self.FLAVOR_PATH.format(
            flavor_id=flavor_id)).json.get(self.root_tag)
        self.assertEqual('Fancy_Flavor', updated_flavor.get('name'))
        self.assertEqual('A great flavor. Pick me!',
                         updated_flavor.get('description'))
        self.assertEqual(flavor_id, updated_flavor.get('id'))
        self.assertEqual(self.fp.get('id'),
                         updated_flavor.get('flavor_profile_id'))
        self.assertTrue(updated_flavor.get('enabled'))

    def test_update_flavor_profile_id(self):
        flavor_json = {'name': 'Fancy_Flavor',
                       'description': 'A great flavor. Pick me!',
                       'flavor_profile_id': self.fp.get('id')}
        body = self._build_body(flavor_json)
        response = self.post(self.FLAVORS_PATH, body)
        api_flavor = response.json.get(self.root_tag)
        flavor_id = api_flavor.get('id')

        flavor_json = {'flavor_profile_id': uuidutils.generate_uuid()}
        body = self._build_body(flavor_json)
        response = self.put(self.FLAVOR_PATH.format(flavor_id=flavor_id),
                            body, status=400)
        updated_flavor = self.get(self.FLAVOR_PATH.format(
            flavor_id=flavor_id)).json.get(self.root_tag)
        self.assertEqual(self.fp.get('id'),
                         updated_flavor.get('flavor_profile_id'))

    def test_update_authorized(self):
        flavor_json = {'name': 'Fancy_Flavor',
                       'description': 'A great flavor. Pick me!',
                       'flavor_profile_id': self.fp.get('id')}
        body = self._build_body(flavor_json)
        response = self.post(self.FLAVORS_PATH, body)
        api_flavor = response.json.get(self.root_tag)
        flavor_id = api_flavor.get('id')

        flavor_json = {'name': 'Better_Flavor',
                       'description': 'An even better flavor. Pick me!',
                       'enabled': False}
        body = self._build_body(flavor_json)
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
                response = self.put(self.FLAVOR_PATH.format(
                    flavor_id=flavor_id), body)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        updated_flavor = self.get(self.FLAVOR_PATH.format(
            flavor_id=flavor_id)).json.get(self.root_tag)
        self.assertEqual('Better_Flavor', updated_flavor.get('name'))
        self.assertEqual('An even better flavor. Pick me!',
                         updated_flavor.get('description'))
        self.assertEqual(flavor_id, updated_flavor.get('id'))
        self.assertEqual(self.fp.get('id'),
                         updated_flavor.get('flavor_profile_id'))
        self.assertFalse(updated_flavor.get('enabled'))

    def test_update_not_authorized(self):
        flavor_json = {'name': 'Fancy_Flavor',
                       'description': 'A great flavor. Pick me!',
                       'flavor_profile_id': self.fp.get('id')}
        body = self._build_body(flavor_json)
        response = self.post(self.FLAVORS_PATH, body)
        api_flavor = response.json.get(self.root_tag)
        flavor_id = api_flavor.get('id')

        flavor_json = {'name': 'Better_Flavor',
                       'description': 'An even better flavor. Pick me!',
                       'enabled': False}
        body = self._build_body(flavor_json)

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        response = self.put(self.FLAVOR_PATH.format(flavor_id=flavor_id),
                            body, status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        updated_flavor = self.get(self.FLAVOR_PATH.format(
            flavor_id=flavor_id)).json.get(self.root_tag)
        self.assertEqual('Fancy_Flavor', updated_flavor.get('name'))
        self.assertEqual('A great flavor. Pick me!',
                         updated_flavor.get('description'))
        self.assertEqual(flavor_id, updated_flavor.get('id'))
        self.assertEqual(self.fp.get('id'),
                         updated_flavor.get('flavor_profile_id'))
        self.assertTrue(updated_flavor.get('enabled'))

    def test_delete(self):
        flavor = self.create_flavor('name1', 'description', self.fp.get('id'),
                                    True)
        self.assertTrue(uuidutils.is_uuid_like(flavor.get('id')))
        self.delete(self.FLAVOR_PATH.format(flavor_id=flavor.get('id')))
        response = self.get(self.FLAVOR_PATH.format(
            flavor_id=flavor.get('id')), status=404)
        err_msg = "Flavor %s not found." % flavor.get('id')
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_delete_authorized(self):
        flavor = self.create_flavor('name1', 'description', self.fp.get('id'),
                                    True)
        self.assertTrue(uuidutils.is_uuid_like(flavor.get('id')))
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
                self.delete(
                    self.FLAVOR_PATH.format(flavor_id=flavor.get('id')))
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        response = self.get(self.FLAVOR_PATH.format(
            flavor_id=flavor.get('id')), status=404)
        err_msg = "Flavor %s not found." % flavor.get('id')
        self.assertEqual(err_msg, response.json.get('faultstring'))

    def test_delete_not_authorized(self):
        flavor = self.create_flavor('name1', 'description', self.fp.get('id'),
                                    True)
        self.assertTrue(uuidutils.is_uuid_like(flavor.get('id')))
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)

        response = self.delete(self.FLAVOR_PATH.format(
            flavor_id=flavor.get('id')), status=403)
        api_flavor = response.json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, api_flavor)

        response = self.get(self.FLAVOR_PATH.format(
            flavor_id=flavor.get('id'))).json.get(self.root_tag)
        self.assertEqual('name1', response.get('name'))

    def test_delete_in_use(self):
        flavor = self.create_flavor('name1', 'description', self.fp.get('id'),
                                    True)
        self.assertTrue(uuidutils.is_uuid_like(flavor.get('id')))
        project_id = uuidutils.generate_uuid()
        lb_id = uuidutils.generate_uuid()
        self.create_load_balancer(lb_id, name='lb1',
                                  project_id=project_id,
                                  description='desc1',
                                  flavor_id=flavor.get('id'),
                                  admin_state_up=False)
        self.delete(self.FLAVOR_PATH.format(flavor_id=flavor.get('id')),
                    status=409)
        response = self.get(self.FLAVOR_PATH.format(
            flavor_id=flavor.get('id'))).json.get(self.root_tag)
        self.assertEqual('name1', response.get('name'))
