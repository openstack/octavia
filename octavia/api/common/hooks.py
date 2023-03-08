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
from webob import acceptparse
from webob import exc

from octavia.api.common import pagination
from octavia.api.common import utils
from octavia.common import constants
from octavia.common import context
from octavia.i18n import _

_HEALTHCHECK_PATHS = ['/healthcheck', '/load-balancer/healthcheck']


class ContentTypeHook(hooks.PecanHook):
    """Force the request content type to JSON if that is acceptable."""

    def on_route(self, state):
        # Oslo healthcheck middleware has its own content type handling
        # so we need to bypass the Octavia content type restrictions.
        if state.request.path in _HEALTHCHECK_PATHS:
            return
        # TODO(johnsom) Testing for an empty string is a workaround for an
        #               openstacksdk bug present up to the initial
        #               antelope release of openstacksdk. This means the
        #               octavia dashboard would also be impacted.
        #               This can be removed once antelope is EOL.
        # See: https://review.opendev.org/c/openstack/openstacksdk/+/876669
        if state.request.accept and state.request.accept.header_value != '':
            best_matches = state.request.accept.acceptable_offers(
                [constants.APPLICATION_JSON])
            if not best_matches:
                # The API reference says we always respond with JSON
                state.request.accept = acceptparse.create_accept_header(
                    constants.APPLICATION_JSON)
                msg = _('Only content type %s is accepted.')
                raise exc.HTTPNotAcceptable(
                    msg % constants.APPLICATION_JSON,
                    json_formatter=utils.json_error_formatter)

        # Force application/json with no other options for the request
        state.request.accept = acceptparse.create_accept_header(
            constants.APPLICATION_JSON)


class ContextHook(hooks.PecanHook):
    """Configures a request context and attaches it to the request."""

    def on_route(self, state):
        context_obj = context.RequestContext.from_environ(
            state.request.environ)
        state.request.context['octavia_context'] = context_obj


class QueryParametersHook(hooks.PecanHook):

    def before(self, state):
        if state.request.method != 'GET':
            return

        state.request.context[
            constants.PAGINATION_HELPER] = pagination.PaginationHelper(
            state.request.params.mixed())
