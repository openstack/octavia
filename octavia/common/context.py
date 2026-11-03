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

from keystoneauth1.access import service_catalog as ksa_service_catalog
from keystoneauth1 import plugin
from oslo_config import cfg
from oslo_context import context as common_context

from octavia.common import constants
from octavia.common import policy
from octavia.db import api as db_api

CONF = cfg.CONF


class _ContextAuthPlugin(plugin.BaseAuthPlugin):
    """Authenticates with the request token and the request user's catalog.

    The token is used as-is, as it may be trust scoped and unusable to
    initialize a new keystone session.
    """

    def __init__(self, auth_token, service_catalog):
        super().__init__()
        self.auth_token = auth_token
        self.service_catalog = ksa_service_catalog.ServiceCatalogV2(
            service_catalog)

    def get_token(self, *args, **kwargs):
        return self.auth_token

    def get_endpoint(self, session, service_type=None, interface=None,
                     region_name=None, service_name=None, **kwargs):
        return self.service_catalog.url_for(service_type=service_type,
                                            service_name=service_name,
                                            interface=interface,
                                            region_name=region_name)


class RequestContext(common_context.RequestContext):

    _session = None

    def __init__(self, user_id=None, service_catalog=None, **kwargs):
        super().__init__(**kwargs)
        # The catalog in the keystonemiddleware X-Service-Catalog format.
        self.service_catalog = service_catalog or []
        self.is_admin = (policy.get_enforcer().check_is_admin(self) or
                         CONF.api_settings.auth_strategy == constants.NOAUTH)

    @property
    def session(self):
        if self._session is None:
            self._session = db_api.get_session()
        return self._session

    def get_auth_plugin(self):
        return _ContextAuthPlugin(self.auth_token, self.service_catalog)
