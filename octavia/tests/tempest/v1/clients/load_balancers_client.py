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
from tempest.lib import exceptions as tempest_exceptions


class LoadBalancersClient(rest_client.RestClient):
    """Tests Load Balancers API."""

    _LOAD_BALANCERS_URL = "v1/loadbalancers"
    _LOAD_BALANCER_URL = "{base_url}/{{lb_id}}".format(
        base_url=_LOAD_BALANCERS_URL)
    _LOAD_BALANCER_CASCADE_DELETE_URL = "{lb_url}/delete_cascade".format(
        lb_url=_LOAD_BALANCER_URL)

    def list_load_balancers(self, params=None):
        """List all load balancers."""
        url = self._LOAD_BALANCERS_URL
        if params:
            url = '{0}?{1}'.format(url, parse.urlencode(params))
        resp, body = self.get(url)
        body = jsonutils.loads(body)
        self.expected_success(200, resp.status)
        return rest_client.ResponseBodyList(resp, body)

    def get_load_balancer(self, lb_id, params=None):
        """Get load balancer details."""
        url = self._LOAD_BALANCER_URL.format(lb_id=lb_id)
        if params:
            url = '{0}?{1}'.format(url, parse.urlencode(params))
        resp, body = self.get(url)
        body = jsonutils.loads(body)
        self.expected_success(200, resp.status)
        return rest_client.ResponseBody(resp, body)

    def create_load_balancer(self, **kwargs):
        """Create a load balancer build."""
        url = self._LOAD_BALANCERS_URL
        post_body = jsonutils.dumps(kwargs)
        resp, body = self.post(url, post_body)
        body = jsonutils.loads(body)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def create_load_balancer_graph(self, lbgraph):
        """Create a load balancer graph build."""
        url = self._LOAD_BALANCERS_URL
        post_body = jsonutils.dumps(lbgraph)
        resp, body = self.post(url, post_body)
        body = jsonutils.loads(body)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def update_load_balancer(self, lb_id, **kwargs):
        """Update a load balancer build."""
        url = self._LOAD_BALANCER_URL.format(lb_id=lb_id)
        put_body = jsonutils.dumps(kwargs)
        resp, body = self.put(url, put_body)
        body = jsonutils.loads(body)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def delete_load_balancer(self, lb_id):
        """Delete an existing load balancer build."""
        url = self._LOAD_BALANCER_URL.format(lb_id=lb_id)
        resp, body = self.delete(url)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def delete_load_balancer_cascade(self, lb_id):
        """Delete an existing load balancer (cascading)."""
        url = self._LOAD_BALANCER_CASCADE_DELETE_URL.format(lb_id=lb_id)
        resp, body = self.delete(url)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def create_load_balancer_over_quota(self, **kwargs):
        """Attempt to build a load balancer over quota."""
        url = self._LOAD_BALANCERS_URL
        post_body = jsonutils.dumps(kwargs)
        try:
            resp, body = self.post(url, post_body)
        except tempest_exceptions.Forbidden:
            # This is what we expect to happen
            return
        assert resp.status == 403, "Expected over quota 403 response"
        return rest_client.ResponseBody(resp, body)
