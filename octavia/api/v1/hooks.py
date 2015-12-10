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

from pecan import hooks

from octavia.common import context


class ContextHook(hooks.PecanHook):

    def on_route(self, state):
        user_id = state.request.headers.get('X-User-Id')
        user_id = state.request.headers.get('X-User', user_id)
        project = state.request.headers.get('X-Tenant-Id')
        project = state.request.headers.get('X-Tenant', project)
        project = state.request.headers.get('X-Project-Id', project)
        project = state.request.headers.get('X-Project', project)
        auth_token = state.request.headers.get('X-Auth-Token')
        state.request.context['octavia_context'] = context.Context(
            user_id=user_id, project_id=project, auth_token=auth_token)
