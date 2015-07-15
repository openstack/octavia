#!/usr/bin/env python

# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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

# make sure PYTHONPATH includes the home directory if you didn't install

import logging
import multiprocessing as multiproc
import os
import ssl
import sys

from oslo_config import cfg
from werkzeug import serving

from octavia.amphorae.backends.agent.api_server import server
from octavia.amphorae.backends.health_daemon import health_daemon
from octavia.common import service

LOG = logging.getLogger(__name__)
CONF = cfg.CONF
CONF.import_group('amphora_agent', 'octavia.common.config')
CONF.import_group('haproxy_amphora', 'octavia.common.config')
HM_SENDER_CMD_QUEUE = multiproc.Queue()


# Hack: Use werkzeugs context
# also http://stackoverflow.com/questions/23262768/
# two-way-ssl-authentication-for-flask
class OctaviaSSLContext(serving._SSLContext):
    def __init__(self, protocol):
        self._ca_certs = None
        super(OctaviaSSLContext, self).__init__(protocol)

    def load_cert_chain(self, certfile, keyfile=None, password=None, ca=None):
        self._ca_certs = ca
        super(OctaviaSSLContext, self).load_cert_chain(
            certfile, keyfile, password)

    def wrap_socket(self, sock, **kwargs):
        return super(OctaviaSSLContext, self).wrap_socket(
            sock,
            # Comment out for debugging if you want to connect without
            # a client cert
            cert_reqs=ssl.CERT_REQUIRED,
            ca_certs=self._ca_certs
        )


# start api server
def main():
    # comment out to improve logging
    service.prepare_service(sys.argv)

    # Workaround for an issue with the auto-reload used below in werkzeug
    # Without it multiple health senders get started when werkzeug reloads
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        health_sender_proc = multiproc.Process(name='HM_sender',
                                               target=health_daemon.run_sender,
                                               args=(HM_SENDER_CMD_QUEUE,))
        health_sender_proc.daemon = True
        health_sender_proc.start()

    # We will only enforce that the client cert is from the good authority
    # todo(german): Watch this space for security improvements
    ctx = OctaviaSSLContext(ssl.PROTOCOL_SSLv23)

    ctx.load_cert_chain(CONF.amphora_agent.agent_server_cert,
                        ca=CONF.amphora_agent.agent_server_ca)

    # This will trigger a reload if any files change and
    # in particular the certificate file
    serving.run_simple(hostname=CONF.haproxy_amphora.bind_host,
                       port=CONF.haproxy_amphora.bind_port,
                       application=server.app,
                       use_debugger=CONF.debug,
                       ssl_context=ctx,
                       use_reloader=True,
                       extra_files=[CONF.amphora_agent.agent_server_cert])
