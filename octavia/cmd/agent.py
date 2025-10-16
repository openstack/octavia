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

import multiprocessing as multiproc
import ssl
import sys

import gunicorn.app.base
from oslo_config import cfg
from oslo_reports import guru_meditation_report as gmr

from octavia.amphorae.backends.agent.api_server import server
from octavia.amphorae.backends.health_daemon import health_daemon
from octavia.common import service
from octavia.common import utils
from octavia import version


CONF = cfg.CONF


class AmphoraAgent(gunicorn.app.base.BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


# start api server
def main():
    # comment out to improve logging
    service.prepare_service(sys.argv)

    gmr.TextGuruMeditation.setup_autorun(version)

    # Setup a multiprocessing manager and queue to share between the
    # health manager sender and the workers. This allows us to reload the
    # configuration into the health manager sender process.
    hm_queue = multiproc.Manager().Queue()

    health_sender_proc = multiproc.Process(name='HM_sender',
                                           target=health_daemon.run_sender,
                                           args=(hm_queue,))
    health_sender_proc.daemon = True
    health_sender_proc.start()

    # Initiate server class
    server_instance = server.Server(hm_queue)

    bind_ip_port = utils.ip_port_str(CONF.haproxy_amphora.bind_host,
                                     CONF.haproxy_amphora.bind_port)
    proto = CONF.amphora_agent.agent_tls_protocol.replace('.', '_')
    options = {
        'bind': bind_ip_port,
        'workers': 1,
        'timeout': CONF.amphora_agent.agent_request_read_timeout,
        'certfile': CONF.amphora_agent.agent_server_cert,
        'ca_certs': CONF.amphora_agent.agent_server_ca,
        'cert_reqs': ssl.CERT_REQUIRED,
        'ssl_version': getattr(ssl, f"PROTOCOL_{proto}"),
        'preload_app': True,
        'accesslog': '/var/log/amphora-agent.log',
        'errorlog': '/var/log/amphora-agent.log',
        'loglevel': 'debug',
        'syslog': True,
        'syslog_facility': (
            f'local{CONF.amphora_agent.administrative_log_facility}'),
        'syslog_addr': 'unix://run/rsyslog/octavia/log#dgram',

    }
    AmphoraAgent(server_instance.app, options).run()
