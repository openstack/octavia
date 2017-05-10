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

from octavia.api.common import pagination
from octavia.common import constants
from octavia.common import context


class ContextHook(hooks.PecanHook):
    """Configures a request context and attaches it to the request."""

    def on_route(self, state):
        context_obj = context.Context.from_environ(state.request.environ)
        state.request.context['octavia_context'] = context_obj


class QueryParametersHook(hooks.PecanHook):

    def before(self, state):
        if state.request.method != 'GET':
            return

        state.request.context[
            constants.PAGINATION_HELPER] = pagination.PaginationHelper(
            state.request.params.mixed())
