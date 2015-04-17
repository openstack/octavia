#!/usr/bin/env python

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

from octavia.api import app as api_app
from octavia.common import service as octavia_service
from octavia.i18n import _LI


LOG = logging.getLogger(__name__)


def main():
    octavia_service.prepare_service(sys.argv)
    app = api_app.setup_app()

    host, port = cfg.CONF.bind_host, cfg.CONF.bind_port
    LOG.info(_LI("Starting API server on %(host)s:%(port)s") %
             {"host": host, "port": port})
    srv = simple_server.make_server(host, port, app)

    srv.serve_forever()
