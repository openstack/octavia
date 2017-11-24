#    Copyright 2016 Intel Corporation
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

from octavia.api.common import pagination
from octavia.common import exceptions
from octavia.db import models
from octavia.tests.unit import base

DEFAULT_SORTS = [('created_at', 'asc'), ('id', 'asc')]


class TestPaginationHelper(base.TestCase):

    @mock.patch('octavia.api.common.pagination.request')
    def test_no_params(self, request_mock):
        params = {}
        helper = pagination.PaginationHelper(params)
        query_mock = mock.MagicMock()

        helper.apply(query_mock, models.LoadBalancer)
        self.assertEqual(DEFAULT_SORTS, helper.sort_keys)
        self.assertIsNone(helper.marker)
        self.assertEqual(1000, helper.limit)
        query_mock.order_by().order_by().limit.assert_called_with(
            1000)

    def test_sort_empty(self):
        sort_params = ""
        params = {'sort': sort_params}
        act_params = pagination.PaginationHelper(
            params).sort_keys
        self.assertEqual([], act_params)

    def test_sort_none(self):
        sort_params = None
        params = {'sort': sort_params}
        act_params = pagination.PaginationHelper(
            params).sort_keys
        self.assertEqual([], act_params)

    def test_sort_key_dir(self):
        sort_keys = "key1,key2,key3"
        sort_dirs = "asc,desc"
        ref_sort_keys = [('key1', 'asc'), ('key2', 'desc'), ('key3', 'asc')]
        params = {'sort_key': sort_keys, 'sort_dir': sort_dirs}
        helper = pagination.PaginationHelper(params)
        self.assertEqual(ref_sort_keys, helper.sort_keys)

    def test_invalid_sorts(self):
        sort_params = "shoud_fail_exception:cause:of:this"
        params = {'sort': sort_params}
        self.assertRaises(exceptions.InvalidSortKey,
                          pagination.PaginationHelper,
                          params)

        sort_params = "ke1:asc,key2:InvalidDir,key3"
        params = {'sort': sort_params}
        self.assertRaises(exceptions.InvalidSortDirection,
                          pagination.PaginationHelper,
                          params)

    def test_marker(self):
        marker = 'random_uuid'
        params = {'marker': marker}
        helper = pagination.PaginationHelper(params)

        self.assertEqual(marker, helper.marker)

    @mock.patch('octavia.api.common.pagination.request')
    def test_limit(self, request_mock):
        limit = 100
        params = {'limit': limit}
        helper = pagination.PaginationHelper(params)
        query_mock = mock.MagicMock()

        helper.apply(query_mock, models.LoadBalancer)
        query_mock.order_by().order_by().limit.assert_called_with(
            limit)

    @mock.patch('octavia.api.common.pagination.request')
    def test_filter_correct_params(self, request_mock):
        params = {'id': 'fake_id'}
        helper = pagination.PaginationHelper(params)
        query_mock = mock.MagicMock()

        helper.apply(query_mock, models.LoadBalancer)
        self.assertEqual(params, helper.filters)

    @mock.patch('octavia.api.common.pagination.request')
    def test_filter_mismatched_params(self, request_mock):
        params = {
            'id': 'fake_id',
            'fields': 'field',
            'limit': '10',
            'sort': None,
        }

        filters = {'id': 'fake_id'}

        helper = pagination.PaginationHelper(params)
        query_mock = mock.MagicMock()

        helper.apply(query_mock, models.LoadBalancer)
        self.assertEqual(filters, helper.filters)
        helper.apply(query_mock, models.LoadBalancer,
                     enforce_valid_params=True)
        self.assertEqual(filters, helper.filters)

    @mock.patch('octavia.api.common.pagination.request')
    def test_filter_with_invalid_params(self, request_mock):
        params = {'id': 'fake_id', 'no_such_param': 'id'}
        filters = {'id': 'fake_id'}
        helper = pagination.PaginationHelper(params)
        query_mock = mock.MagicMock()

        helper.apply(query_mock, models.LoadBalancer,
                     # silently ignore invalid parameter
                     enforce_valid_params=False)
        self.assertEqual(filters, helper.filters)

        self.assertRaises(
            exceptions.InvalidFilterArgument,
            pagination.PaginationHelper.apply,
            helper,
            query_mock,
            models.Amphora,
        )

    @mock.patch('octavia.api.common.pagination.request')
    def test_duplicate_argument(self, request_mock):
        params = {'loadbalacer_id': 'id1', 'load_balacer_id': 'id2'}
        query_mock = mock.MagicMock()
        helper = pagination.PaginationHelper(params)

        self.assertRaises(
            exceptions.InvalidFilterArgument,
            pagination.PaginationHelper.apply,
            helper,
            query_mock,
            models.Amphora,
        )

    @mock.patch('octavia.api.common.pagination.request')
    def test_fields_not_passed(self, request_mock):
        params = {'fields': 'id'}
        helper = pagination.PaginationHelper(params)
        query_mock = mock.MagicMock()

        helper.apply(query_mock, models.LoadBalancer)
        self.assertEqual({}, helper.filters)

    @mock.patch('octavia.api.common.pagination.request')
    def test_make_links_next(self, request_mock):
        request_mock.path = "/lbaas/v2.0/pools/1/members"
        request_mock.path_url = "http://localhost" + request_mock.path
        member1 = models.Member()
        member1.id = uuidutils.generate_uuid()
        model_list = [member1]

        params = {'limit': 1}
        helper = pagination.PaginationHelper(params)
        links = helper._make_links(model_list)
        self.assertEqual(links[0].rel, "next")
        self.assertEqual(
            links[0].href,
            "{path_url}?limit={limit}&marker={marker}".format(
                path_url=request_mock.path_url,
                limit=params['limit'],
                marker=member1.id
            ))

    @mock.patch('octavia.api.common.pagination.request')
    def test_make_links_prev(self, request_mock):
        request_mock.path = "/lbaas/v2.0/pools/1/members"
        request_mock.path_url = "http://localhost" + request_mock.path
        member1 = models.Member()
        member1.id = uuidutils.generate_uuid()
        model_list = [member1]

        params = {'limit': 1, 'marker': member1.id}
        helper = pagination.PaginationHelper(params)
        links = helper._make_links(model_list)
        self.assertEqual(links[0].rel, "previous")
        self.assertEqual(
            links[1].href,
            "{path_url}?limit={limit}&marker={marker}".format(
                path_url=request_mock.path_url,
                limit=params['limit'],
                marker=member1.id))
        self.assertEqual(links[1].rel, "next")
        self.assertEqual(
            links[1].href,
            "{path_url}?limit={limit}&marker={marker}".format(
                path_url=request_mock.path_url,
                limit=params['limit'],
                marker=member1.id))

    @mock.patch('octavia.api.common.pagination.request')
    def test_make_links_with_configured_url(self, request_mock):
        request_mock.path = "/lbaas/v2.0/pools/1/members"
        request_mock.path_url = "http://localhost" + request_mock.path
        api_base_uri = "https://127.0.0.1"
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', api_base_uri=api_base_uri)
        member1 = models.Member()
        member1.id = uuidutils.generate_uuid()
        model_list = [member1]

        params = {'limit': 1, 'marker': member1.id}
        helper = pagination.PaginationHelper(params)
        links = helper._make_links(model_list)
        self.assertEqual(links[0].rel, "previous")
        self.assertEqual(
            links[1].href,
            "{base_uri}{path}?limit={limit}&marker={marker}".format(
                base_uri=api_base_uri,
                path=request_mock.path,
                limit=params['limit'],
                marker=member1.id
            ))
        self.assertEqual(links[1].rel, "next")
        self.assertEqual(
            links[1].href,
            "{base_uri}{path}?limit={limit}&marker={marker}".format(
                base_uri=api_base_uri,
                path=request_mock.path,
                limit=params['limit'],
                marker=member1.id))
