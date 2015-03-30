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

from oslo_context import context as common_context

from octavia.db import api as db_api


class Context(common_context.RequestContext):
    def __init__(self, user_id, tenant_id, is_admin=False, auth_token=None):
        super(Context, self).__init__(tenant=tenant_id, auth_token=auth_token,
                                      is_admin=is_admin, user=user_id)
        self._session = None

    @property
    def session(self):
        if self._session is None:
            self._session = db_api.get_session()
        return self._session
