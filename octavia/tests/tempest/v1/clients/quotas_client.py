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


class QuotasClient(rest_client.RestClient):
    """Tests Quotas API."""

    _QUOTAS_URL = "v1/{project_id}/quotas"

    def list_quotas(self, params=None):
        """List all non-default quotas."""
        url = "v1/quotas"
        if params:
            url = '{0}?{1}'.format(url, parse.urlencode(params))
        resp, body = self.get(url)
        body = jsonutils.loads(body)
        self.expected_success(200, resp.status)
        return rest_client.ResponseBodyList(resp, body)

    def get_quotas(self, project_id, params=None):
        """Get Quotas for a project."""
        url = self._QUOTAS_URL.format(project_id=project_id)
        if params:
            url = '{0}?{1}'.format(url, parse.urlencode(params))
        resp, body = self.get(url)
        body = jsonutils.loads(body)
        self.expected_success(200, resp.status)
        return rest_client.ResponseBody(resp, body)

    def update_quotas(self, project_id, **kwargs):
        """Update a Quotas for a project."""
        url = self._QUOTAS_URL.format(project_id=project_id)
        put_body = jsonutils.dumps(kwargs)
        resp, body = self.put(url, put_body)
        body = jsonutils.loads(body)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def delete_quotas(self, project_id):
        """Delete an Quotas for a project."""
        url = self._QUOTAS_URL.format(project_id=project_id)
        resp, body = self.delete(url)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)
