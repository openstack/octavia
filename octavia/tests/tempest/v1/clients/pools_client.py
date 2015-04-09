# Copyright 2016 Rackspace US Inc.  All rights reserved.
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

from oslo_serialization import jsonutils
from six.moves.urllib import parse
from tempest.lib.common import rest_client


class PoolsClient(rest_client.RestClient):
    """Test Pools API."""

    _POOLS_URL = "v1/loadbalancers/{lb_id}/pools"
    _POOL_URL = "{base_url}/{{pool_id}}".format(base_url=_POOLS_URL)

    def list_pools(self, lb_id, listener_id=None, params=None):
        """List all pools. Filter by listener id if provided."""
        url = self._POOLS_URL.format(lb_id=lb_id)
        params['listener_id'] = str(listener_id)
        if params:
            url = '{0}?{1}'.format(url, parse.urlencode(params))
        resp, body = self.get(url)
        body = jsonutils.loads(body)
        self.expected_success(200, resp.status)
        return rest_client.ResponseBodyList(resp, body)

    def get_pool(self, lb_id, pool_id, params=None):
        """Get pool details."""
        url = self._POOL_URL.format(lb_id=lb_id, pool_id=pool_id)
        if params:
            url = '{0}?{1}'.format(url, parse.urlencode(params))
        resp, body = self.get(url)
        body = jsonutils.loads(body)
        self.expected_success(200, resp.status)
        return rest_client.ResponseBody(resp, body)

    def create_pool(self, lb_id, **kwargs):
        """Create a pool."""
        url = self._POOLS_URL.format(lb_id=lb_id)
        post_body = jsonutils.dumps(kwargs)
        resp, body = self.post(url, post_body)
        body = jsonutils.loads(body)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def update_pool(self, lb_id, pool_id, **kwargs):
        """Update a pool."""
        url = self._POOL_URL.format(lb_id=lb_id, pool_id=pool_id)
        post_body = jsonutils.dumps(kwargs)
        resp, body = self.put(url, post_body)
        body = jsonutils.loads(body)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def delete_pool(self, lb_id, pool_id):
        """Delete a pool."""
        url = self._POOL_URL.format(lb_id=lb_id, pool_id=pool_id)
        resp, body = self.delete(url)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)
