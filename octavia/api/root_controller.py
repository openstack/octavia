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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_middleware import healthcheck
from pecan import abort as pecan_abort
from pecan import expose as pecan_expose
from pecan import request as pecan_request
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v2 import controllers as v2_controller

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class RootController(object):
    """The controller with which the pecan wsgi app should be created."""

    def __init__(self):
        super().__init__()
        setattr(self, 'v2.0', v2_controller.V2Controller())
        setattr(self, 'v2', v2_controller.V2Controller())
        if CONF.api_settings.healthcheck_enabled:
            self.healthcheck_obj = healthcheck.Healthcheck.app_factory(None)

    # Run the oslo middleware healthcheck for /healthcheck
    @pecan_expose('json')
    @pecan_expose(content_type='plain/text')
    @pecan_expose(content_type='text/html')
    def healthcheck(self):  # pylint: disable=inconsistent-return-statements
        if CONF.api_settings.healthcheck_enabled:
            if pecan_request.method not in ['GET', 'HEAD']:
                pecan_abort(405)
            return self.healthcheck_obj.process_request(pecan_request)
        pecan_abort(404)

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
    def index(self):
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
        self._add_a_version(versions, 'v2.13', 'v2', 'SUPPORTED',
                            '2019-09-13T00:00:00Z', host_url)
        # Availability Zones
        self._add_a_version(versions, 'v2.14', 'v2', 'SUPPORTED',
                            '2019-11-10T00:00:00Z', host_url)
        # TLS cipher options
        self._add_a_version(versions, 'v2.15', 'v2', 'SUPPORTED',
                            '2020-03-10T00:00:00Z', host_url)
        # Additional UDP Healthcheck Types (HTTP/TCP)
        self._add_a_version(versions, 'v2.16', 'v2', 'SUPPORTED',
                            '2020-03-15T00:00:00Z', host_url)
        # Listener TLS versions
        self._add_a_version(versions, 'v2.17', 'v2', 'SUPPORTED',
                            '2020-04-29T00:00:00Z', host_url)
        # Pool TLS versions
        self._add_a_version(versions, 'v2.18', 'v2', 'SUPPORTED',
                            '2020-04-29T01:00:00Z', host_url)
        # Add quota support to octavia's l7policy and l7rule
        self._add_a_version(versions, 'v2.19', 'v2', 'SUPPORTED',
                            '2020-05-12T00:00:00Z', host_url)
        # ALPN protocols (listener)
        self._add_a_version(versions, 'v2.20', 'v2', 'SUPPORTED',
                            '2020-08-02T00:00:00Z', host_url)
        # Amphora delete
        self._add_a_version(versions, 'v2.21', 'v2', 'SUPPORTED',
                            '2020-09-03T00:00:00Z', host_url)
        # Add PROXYV2 pool protocol
        self._add_a_version(versions, 'v2.22', 'v2', 'SUPPORTED',
                            '2020-09-04T00:00:00Z', host_url)
        # SCTP protocol
        self._add_a_version(versions, 'v2.23', 'v2', 'SUPPORTED',
                            '2020-09-07T00:00:00Z', host_url)
        # ALPN protocols (pool)
        self._add_a_version(versions, 'v2.24', 'v2', 'SUPPORTED',
                            '2020-10-15T00:00:00Z', host_url)
        # PROMETHEUS listeners
        self._add_a_version(versions, 'v2.25', 'v2', 'CURRENT',
                            '2021-10-02T00:00:00Z', host_url)
        return {'versions': versions}
