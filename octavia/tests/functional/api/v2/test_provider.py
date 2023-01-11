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


from unittest import mock

from octavia_lib.api.drivers import exceptions as lib_exceptions
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.common import constants
import octavia.common.context
from octavia.tests.functional.api.v2 import base


class TestProvider(base.BaseAPITest):

    root_tag_list = 'providers'

    def setUp(self):
        super().setUp()

    def test_get_all_providers(self):
        octavia_dict = {u'description': u'Octavia driver.',
                        u'name': u'octavia'}
        amphora_dict = {u'description': u'Amp driver.', u'name': u'amphora'}
        noop_dict = {u'description': u'NoOp driver.', u'name': u'noop_driver'}
        providers = self.get(self.PROVIDERS_PATH).json.get(self.root_tag_list)
        self.assertEqual(4, len(providers))
        self.assertIn(octavia_dict, providers)
        self.assertIn(amphora_dict, providers)
        self.assertIn(noop_dict, providers)

    def test_get_all_providers_fields(self):
        octavia_dict = {u'name': u'octavia'}
        amphora_dict = {u'name': u'amphora'}
        noop_dict = {u'name': u'noop_driver'}
        providers = self.get(self.PROVIDERS_PATH, params={'fields': ['name']})
        providers_list = providers.json.get(self.root_tag_list)
        self.assertEqual(4, len(providers_list))
        self.assertIn(octavia_dict, providers_list)
        self.assertIn(amphora_dict, providers_list)
        self.assertIn(noop_dict, providers_list)


class TestFlavorCapabilities(base.BaseAPITest):

    root_tag = 'flavor_capabilities'

    def setUp(self):
        super().setUp()

    def test_nonexistent_provider(self):
        self.get(self.FLAVOR_CAPABILITIES_PATH.format(provider='bogus'),
                 status=400)

    def test_noop_provider(self):
        ref_capabilities = [{'description': 'The glance image tag to use for '
                             'this load balancer.', 'name': 'amp_image_tag'}]

        result = self.get(
            self.FLAVOR_CAPABILITIES_PATH.format(provider='noop_driver'))
        self.assertEqual(ref_capabilities, result.json.get(self.root_tag))

    def test_amphora_driver(self):
        ref_description = ("The load balancer topology. One of: SINGLE - One "
                           "amphora per load balancer. ACTIVE_STANDBY - Two "
                           "amphora per load balancer.")
        result = self.get(
            self.FLAVOR_CAPABILITIES_PATH.format(provider='amphora'))
        capabilities = result.json.get(self.root_tag)
        capability_dict = [i for i in capabilities if
                           i['name'] == 'loadbalancer_topology'][0]
        self.assertEqual(ref_description,
                         capability_dict['description'])

    # Some drivers might not have implemented this yet, test that case
    @mock.patch('octavia.api.drivers.noop_driver.driver.NoopProviderDriver.'
                'get_supported_flavor_metadata')
    def test_not_implemented(self, mock_get_metadata):
        mock_get_metadata.side_effect = lib_exceptions.NotImplementedError()
        self.get(self.FLAVOR_CAPABILITIES_PATH.format(provider='noop_driver'),
                 status=501)

    def test_authorized(self):
        ref_capabilities = [{'description': 'The glance image tag to use '
                             'for this load balancer.',
                             'name': 'amp_image_tag'}]
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
                result = self.get(self.FLAVOR_CAPABILITIES_PATH.format(
                    provider='noop_driver'))
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(ref_capabilities, result.json.get(self.root_tag))

    def test_not_authorized(self):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        self.get(self.FLAVOR_CAPABILITIES_PATH.format(provider='noop_driver'),
                 status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

    def test_amphora_driver_one_filter(self):
        ref_description = ("The compute driver flavor ID.")
        result = self.get(
            self.FLAVOR_CAPABILITIES_PATH.format(provider=constants.AMPHORA),
            params={constants.NAME: 'compute_flavor'})
        capabilities = result.json.get(self.root_tag)
        self.assertEqual(1, len(capabilities))
        self.assertEqual(2, len(capabilities[0]))
        self.assertEqual(ref_description,
                         capabilities[0][constants.DESCRIPTION])

    def test_amphora_driver_two_filters(self):
        ref_description = ("The compute driver flavor ID.")
        result = self.get(
            self.FLAVOR_CAPABILITIES_PATH.format(provider=constants.AMPHORA),
            params={constants.NAME: 'compute_flavor',
                    constants.DESCRIPTION: ref_description})
        capabilities = result.json.get(self.root_tag)
        self.assertEqual(1, len(capabilities))
        self.assertEqual(ref_description,
                         capabilities[0][constants.DESCRIPTION])

    def test_amphora_driver_filter_no_match(self):
        result = self.get(
            self.FLAVOR_CAPABILITIES_PATH.format(provider=constants.AMPHORA),
            params={constants.NAME: 'bogus'})
        capabilities = result.json.get(self.root_tag)
        self.assertEqual([], capabilities)

    def test_amphora_driver_one_filter_one_field(self):
        result = self.get(
            self.FLAVOR_CAPABILITIES_PATH.format(provider=constants.AMPHORA),
            params={constants.NAME: 'compute_flavor',
                    constants.FIELDS: constants.NAME})
        capabilities = result.json.get(self.root_tag)
        self.assertEqual(1, len(capabilities))
        self.assertEqual(1, len(capabilities[0]))
        self.assertEqual('compute_flavor', capabilities[0][constants.NAME])


class TestAvailabilityZoneCapabilities(base.BaseAPITest):

    root_tag = 'availability_zone_capabilities'

    def setUp(self):
        super().setUp()

    def test_nonexistent_provider(self):
        self.get(self.AVAILABILITY_ZONE_CAPABILITIES_PATH.format(
            provider='bogus'), status=400)

    def test_noop_provider(self):
        ref_capabilities = [{'description': 'The compute availability zone to '
                                            'use for this loadbalancer.',
                             'name': constants.COMPUTE_ZONE}]

        result = self.get(
            self.AVAILABILITY_ZONE_CAPABILITIES_PATH.format(
                provider='noop_driver'))
        self.assertEqual(ref_capabilities, result.json.get(self.root_tag))

    def test_amphora_driver(self):
        ref_description1 = 'The compute availability zone.'
        ref_description2 = 'The management network ID for the amphora.'
        result = self.get(
            self.AVAILABILITY_ZONE_CAPABILITIES_PATH.format(
                provider='amphora'))
        capabilities = result.json.get(self.root_tag)
        capability_dict = [i for i in capabilities if
                           i['name'] == constants.COMPUTE_ZONE][0]
        self.assertEqual(ref_description1,
                         capability_dict['description'])
        capability_dict = [i for i in capabilities if
                           i['name'] == constants.MANAGEMENT_NETWORK][0]
        self.assertEqual(ref_description2,
                         capability_dict['description'])

    # Some drivers might not have implemented this yet, test that case
    @mock.patch('octavia.api.drivers.noop_driver.driver.NoopProviderDriver.'
                'get_supported_availability_zone_metadata')
    def test_not_implemented(self, mock_get_metadata):
        mock_get_metadata.side_effect = lib_exceptions.NotImplementedError()
        self.get(self.AVAILABILITY_ZONE_CAPABILITIES_PATH.format(
            provider='noop_driver'), status=501)

    def test_authorized(self):
        ref_capabilities = [{'description': 'The compute availability zone to '
                                            'use for this loadbalancer.',
                             'name': constants.COMPUTE_ZONE}]
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
                result = self.get(
                    self.AVAILABILITY_ZONE_CAPABILITIES_PATH.format(
                        provider='noop_driver'))
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(ref_capabilities, result.json.get(self.root_tag))

    def test_not_authorized(self):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        self.get(self.AVAILABILITY_ZONE_CAPABILITIES_PATH.format(
            provider='noop_driver'), status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

    def test_amphora_driver_one_filter(self):
        ref_description = 'The compute availability zone.'
        result = self.get(
            self.AVAILABILITY_ZONE_CAPABILITIES_PATH.format(
                provider=constants.AMPHORA),
            params={constants.NAME: constants.COMPUTE_ZONE})
        capabilities = result.json.get(self.root_tag)
        self.assertEqual(1, len(capabilities))
        self.assertEqual(2, len(capabilities[0]))
        self.assertEqual(ref_description,
                         capabilities[0][constants.DESCRIPTION])

        ref_description = 'The management network ID for the amphora.'
        result = self.get(
            self.AVAILABILITY_ZONE_CAPABILITIES_PATH.format(
                provider=constants.AMPHORA),
            params={constants.NAME: constants.MANAGEMENT_NETWORK})
        capabilities = result.json.get(self.root_tag)
        self.assertEqual(1, len(capabilities))
        self.assertEqual(2, len(capabilities[0]))
        self.assertEqual(ref_description,
                         capabilities[0][constants.DESCRIPTION])

    def test_amphora_driver_two_filters(self):
        ref_description = 'The compute availability zone.'
        result = self.get(
            self.AVAILABILITY_ZONE_CAPABILITIES_PATH.format(
                provider=constants.AMPHORA),
            params={constants.NAME: constants.COMPUTE_ZONE,
                    constants.DESCRIPTION: ref_description})
        capabilities = result.json.get(self.root_tag)
        self.assertEqual(1, len(capabilities))
        self.assertEqual(ref_description,
                         capabilities[0][constants.DESCRIPTION])

    def test_amphora_driver_filter_no_match(self):
        result = self.get(
            self.AVAILABILITY_ZONE_CAPABILITIES_PATH.format(
                provider=constants.AMPHORA),
            params={constants.NAME: 'bogus'})
        capabilities = result.json.get(self.root_tag)
        self.assertEqual([], capabilities)

    def test_amphora_driver_one_filter_one_field(self):
        result = self.get(
            self.AVAILABILITY_ZONE_CAPABILITIES_PATH.format(
                provider=constants.AMPHORA),
            params={constants.NAME: constants.COMPUTE_ZONE,
                    constants.FIELDS: constants.NAME})
        capabilities = result.json.get(self.root_tag)
        self.assertEqual(1, len(capabilities))
        self.assertEqual(1, len(capabilities[0]))
        self.assertEqual(constants.COMPUTE_ZONE,
                         capabilities[0][constants.NAME])
