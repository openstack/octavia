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
from wsgiref import simple_server

from oslo_config import cfg
from oslo_log import log as logging
from oslo_reports import guru_meditation_report as gmr
from oslo_reports import opts as gmr_opts

from octavia.api import app as api_app
from octavia.common import constants
from octavia import version


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def main():
    # TODO(tkajinam): We should consider adding this to wsgi app too so that
    # GMR can be used even when api is run by uwsgi/mod_wsgi/etc.
    gmr_opts.set_defaults(CONF)
    gmr.TextGuruMeditation.setup_autorun(version, conf=CONF)

    app = api_app.setup_app(argv=sys.argv)

    host = CONF.api_settings.bind_host
    port = CONF.api_settings.bind_port
    LOG.info("Starting API server on %(host)s:%(port)s",
             {"host": host, "port": port})
    if CONF.api_settings.auth_strategy != constants.KEYSTONE:
        LOG.warning('Octavia configuration [api_settings] auth_strategy is '
                    'not set to "keystone". This is not a normal '
                    'configuration and you may get "Missing project ID" '
                    'errors from API calls."')
    LOG.warning('You are running the Octavia API wsgi application using '
                'simple_server. We do not recommend this outside of simple '
                'testing. We recommend you run the Octavia API wsgi with '
                'a more full function server such as gunicorn or uWSGI.')
    srv = simple_server.make_server(host, port, app)

    srv.serve_forever()
