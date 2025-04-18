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

import sys

# Try using custom auditmiddleware
try:
    import auditmiddleware as audit_middleware
except ImportError:
    import keystonemiddleware.audit as audit_middleware

from oslo_config import cfg
from oslo_log import log as logging
from oslo_middleware import cors
from oslo_middleware import http_proxy_to_wsgi
from oslo_middleware import request_id
from oslo_middleware import sizelimit
from pecan import configuration as pecan_configuration
from pecan import make_app as pecan_make_app
from oslo_utils import importutils

from octavia.api import config as app_config
from octavia.api.drivers import driver_factory
from octavia.common import constants
from octavia.common import exceptions
from octavia.common import keystone
from octavia.common import service as octavia_service

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

# sapcc/openstack-watcher-middleware
watcher_errors = importutils.try_import('watcher.errors')
watcher_middleware = importutils.try_import('watcher.watcher')


def get_pecan_config():
    """Returns the pecan config."""
    filename = app_config.__file__.replace('.pyc', '.py')
    return pecan_configuration.conf_from_file(filename)


def _init_drivers():
    """Initialize provider drivers."""
    for provider in CONF.api_settings.enabled_provider_drivers:
        driver_factory.get_driver(provider)


def setup_app(pecan_config=None, debug=False, argv=None):
    """Creates and returns a pecan wsgi app."""
    if argv is None:
        argv = sys.argv
    octavia_service.prepare_service(argv)
    cfg.CONF.log_opt_values(LOG, logging.INFO)

    _init_drivers()

    if not pecan_config:
        pecan_config = get_pecan_config()
    pecan_configuration.set_config(dict(pecan_config), overwrite=True)

    return pecan_make_app(
        pecan_config.app.root,
        wrap_app=_wrap_app,
        debug=debug,
        hooks=pecan_config.app.hooks,
        wsme=pecan_config.wsme
    )


def _wrap_app(app):
    """Wraps wsgi app with additional middlewares."""
    app = request_id.RequestId(app)

    if CONF.audit.enabled:
        try:
            app = audit_middleware.AuditMiddleware(
                app,
                audit_map_file=CONF.audit.audit_map_file,
                ignore_req_list=CONF.audit.ignore_req_list
            )
        except (OSError, audit_middleware.PycadfAuditApiConfigError) as e:
            raise exceptions.InputFileError(
                file_name=CONF.audit.audit_map_file,
                reason=e
            )

    # sapcc/openstack-watcher-middleware
    if watcher_errors and watcher_middleware and CONF.watcher.enabled:
        LOG.info("Openstack-Watcher-Middleware activated")
        try:
            app = watcher_middleware.OpenStackWatcherMiddleware(
                app,
                config=dict(CONF.watcher)
            )
        except (EnvironmentError, OSError,
                watcher_errors.ConfigError) as e:
            raise exceptions.InputFileError(
                file_name=CONF.watcher.config_file,
                reason=e
            )

    if cfg.CONF.api_settings.auth_strategy == constants.KEYSTONE:
        app = keystone.SkippingAuthProtocol(app, {})

    app = http_proxy_to_wsgi.HTTPProxyToWSGI(app)

    # This should be the last middleware in the list (which results in
    # it being the first in the middleware chain). This is to ensure
    # that any errors thrown by other middleware, such as an auth
    # middleware - are annotated with CORS headers, and thus accessible
    # by the browser.
    app = cors.CORS(app, cfg.CONF)
    cors.set_defaults(
        allow_headers=['X-Auth-Token', 'X-Openstack-Request-Id'],
        allow_methods=['GET', 'PUT', 'POST', 'DELETE'],
        expose_headers=['X-Auth-Token', 'X-Openstack-Request-Id']
    )

    app = sizelimit.RequestBodySizeLimiter(app, cfg.CONF)

    return app
