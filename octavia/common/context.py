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
from oslo_context import context as common_context

from octavia.common import constants
from octavia.common import policy
from octavia.db import api as db_api

CONF = cfg.CONF


class Context(common_context.RequestContext):

    _session = None

    def __init__(self, user_id=None, project_id=None, **kwargs):

        if project_id:
            kwargs['tenant'] = project_id

        super(Context, self).__init__(**kwargs)

        self.is_admin = (policy.get_enforcer().check_is_admin(self) or
                         CONF.api_settings.auth_strategy == constants.NOAUTH)

    @property
    def session(self):
        if self._session is None:
            self._session = db_api.get_session()
        return self._session

    @property
    def project_id(self):
        return self.tenant
