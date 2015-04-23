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

from pecan import rest
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v1 import controllers


class RootController(rest.RestController):
    """The controller in which the pecan wsgi app should be created with."""
    v1 = controllers.V1Controller()

    @staticmethod
    @wsme_pecan.wsexpose(wtypes.text)
    def get():
        # TODO(blogan): once a decision is made on how to do versions, do that
        # here
        return {'versions': [{'status': 'CURRENT',
                              'updated': '2014-12-11T00:00:00Z',
                              'id': 'v1'}]}
