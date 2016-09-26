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


class ListenersClient(rest_client.RestClient):
    """Tests Listeners API."""

    _LISTENERS_URL = "v1/loadbalancers/{lb_id}/listeners"
    _LISTENER_URL = "{base_url}/{{listener_id}}".format(
        base_url=_LISTENERS_URL)
    _LISTENER_STATS_URL = "{base_url}/stats".format(base_url=_LISTENER_URL)

    def list_listeners(self, lb_id, params=None):
        """List all listeners."""
        url = self._LISTENERS_URL.format(lb_id=lb_id)
        if params:
            url = '{0}?{1}'.format(url, parse.urlencode(params))
        resp, body = self.get(url)
        body = jsonutils.loads(body)
        self.expected_success(200, resp.status)
        return rest_client.ResponseBodyList(resp, body)

    def get_listener(self, lb_id, listener_id, params=None):
        """Get listener details."""
        url = self._LISTENER_URL.format(lb_id=lb_id, listener_id=listener_id)
        if params:
            url = '{0}?{1}'.format(url, parse.urlencode(params))
        resp, body = self.get(url)
        body = jsonutils.loads(body)
        self.expected_success(200, resp.status)
        return rest_client.ResponseBody(resp, body)

    def create_listener(self, lb_id, **kwargs):
        """Create a listener build."""
        url = self._LISTENERS_URL.format(lb_id=lb_id)
        post_body = jsonutils.dumps(kwargs)
        resp, body = self.post(url, post_body)
        body = jsonutils.loads(body)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def update_listener(self, lb_id, listener_id, **kwargs):
        """Update an listener build."""
        url = self._LISTENER_URL.format(lb_id=lb_id, listener_id=listener_id)
        put_body = jsonutils.dumps(kwargs)
        resp, body = self.put(url, put_body)
        body = jsonutils.loads(body)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def delete_listener(self, lb_id, listener_id):
        """Delete an existing listener build."""
        url = self._LISTENER_URL.format(lb_id=lb_id, listener_id=listener_id)
        resp, body = self.delete(url)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def get_listener_stats(self, lb_id, listener_id, params=None):
        """Get listener statistics."""
        url = self._LISTENER_STATS_URL.format(lb_id=lb_id,
                                              listener_id=listener_id)
        if params:
            url = '{0}?{1}'.format(url, parse.urlencode(params))
        resp, body = self.get(url)
        body = jsonutils.loads(body)
        self.expected_success(200, resp.status)
        return rest_client.ResponseBody(resp, body)
