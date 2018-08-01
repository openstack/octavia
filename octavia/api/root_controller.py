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
from pecan import request as pecan_request
from pecan import rest
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v1 import controllers as v1_controller
from octavia.api.v2 import controllers as v2_controller


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class RootController(rest.RestController):
    """The controller with which the pecan wsgi app should be created."""

    def __init__(self):
        super(RootController, self).__init__()
        v1_enabled = CONF.api_settings.api_v1_enabled
        v2_enabled = CONF.api_settings.api_v2_enabled
        if v1_enabled:
            self.v1 = v1_controller.V1Controller()
        if v2_enabled:
            setattr(self, 'v2.0', v2_controller.V2Controller())
            setattr(self, 'v2', v2_controller.V2Controller())
        if not (v1_enabled or v2_enabled):
            LOG.warning("Both v1 and v2 API endpoints are disabled -- is "
                        "this intentional?")
        elif v1_enabled and v2_enabled:
            LOG.warning("Both v1 and v2 API endpoints are enabled -- it is "
                        "a security risk to expose the v1 endpoint publicly,"
                        "so please make sure access to it is secured.")

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
        if CONF.api_settings.api_v1_enabled:
            self._add_a_version(versions, 'v1', 'v1', 'DEPRECATED',
                                '2014-12-11T00:00:00Z', host_url)
        if CONF.api_settings.api_v2_enabled:
            self._add_a_version(versions, 'v2.0', 'v2', 'SUPPORTED',
                                '2016-12-11T00:00:00Z', host_url)
            self._add_a_version(versions, 'v2.1', 'v2', 'SUPPORTED',
                                '2018-04-20T00:00:00Z', host_url)
            self._add_a_version(versions, 'v2.2', 'v2', 'CURRENT',
                                '2018-07-31T00:00:00Z', host_url)
        return {'versions': versions}
