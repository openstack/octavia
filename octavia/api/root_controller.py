#    Copyright 2014 Rackspace
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

from oslo_log import log as logging
from pecan import request as pecan_request
from pecan import rest
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v2 import controllers as v2_controller


LOG = logging.getLogger(__name__)


class RootController(rest.RestController):
    """The controller with which the pecan wsgi app should be created."""

    def __init__(self):
        super(RootController, self).__init__()
        setattr(self, 'v2.0', v2_controller.V2Controller())
        setattr(self, 'v2', v2_controller.V2Controller())

    def _add_a_version(self, versions, version, url_version, status,
                       timestamp, base_url):
        versions.append({
            'id': version,
            'status': status,
            'updated': timestamp,
            'links': [{
                'href': base_url + url_version,
                'rel': 'self'
            }]
        })

    @wsme_pecan.wsexpose(wtypes.text)
    def get(self):
        host_url = pecan_request.path_url

        if not host_url.endswith('/'):
            host_url = '{}/'.format(host_url)

        versions = []
        self._add_a_version(versions, 'v2.0', 'v2', 'SUPPORTED',
                            '2016-12-11T00:00:00Z', host_url)
        self._add_a_version(versions, 'v2.1', 'v2', 'SUPPORTED',
                            '2018-04-20T00:00:00Z', host_url)
        self._add_a_version(versions, 'v2.2', 'v2', 'SUPPORTED',
                            '2018-07-31T00:00:00Z', host_url)
        self._add_a_version(versions, 'v2.3', 'v2', 'SUPPORTED',
                            '2018-12-18T00:00:00Z', host_url)
        # amp statistics
        self._add_a_version(versions, 'v2.4', 'v2', 'SUPPORTED',
                            '2018-12-19T00:00:00Z', host_url)
        # Tags
        self._add_a_version(versions, 'v2.5', 'v2', 'SUPPORTED',
                            '2019-01-21T00:00:00Z', host_url)
        # Flavors
        self._add_a_version(versions, 'v2.6', 'v2', 'SUPPORTED',
                            '2019-01-25T00:00:00Z', host_url)
        # Amphora Config update
        self._add_a_version(versions, 'v2.7', 'v2', 'SUPPORTED',
                            '2018-01-25T12:00:00Z', host_url)
        # TLS client authentication
        self._add_a_version(versions, 'v2.8', 'v2', 'SUPPORTED',
                            '2019-02-12T00:00:00Z', host_url)
        # HTTP Redirect code
        self._add_a_version(versions, 'v2.9', 'v2', 'SUPPORTED',
                            '2019-03-04T00:00:00Z', host_url)
        # Healthmonitor host header
        self._add_a_version(versions, 'v2.10', 'v2', 'SUPPORTED',
                            '2019-03-05T00:00:00Z', host_url)
        # Additive batch member update
        self._add_a_version(versions, 'v2.11', 'v2', 'SUPPORTED',
                            '2019-06-24T00:00:00Z', host_url)
        # VIP ACL
        self._add_a_version(versions, 'v2.12', 'v2', 'SUPPORTED',
                            '2019-09-11T00:00:00Z', host_url)
        # SOURCE_IP_PORT algorithm
        self._add_a_version(versions, 'v2.13', 'v2', 'CURRENT',
                            '2019-09-13T00:00:00Z', host_url)
        return {'versions': versions}
