# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.

"""Run the OVS distributor REST agent."""

import ssl
import sys

import gunicorn.app.base
from oslo_reports import guru_meditation_report as gmr
from oslo_config import cfg

from octavia.common import service
from octavia.common import utils
from octavia.distributor.backend.agent.api_server import server
from octavia import version

CONF = cfg.CONF


class DistributorAgent(gunicorn.app.base.BaseApplication):
    def __init__(self, app, options=None):
        self.application = app
        self.options = options or {}
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


def _post_fork(gunicorn_server, worker):
    # The agent uses gunicorn preload_app=True.  Start the reconciler after
    # the worker fork so the thread belongs to the serving worker rather than
    # disappearing with the preloaded master process.
    del gunicorn_server, worker
    server.start_reconciler()


def main():
    service.prepare_service(sys.argv)
    if not CONF.distributor.agent_server_cert:
        raise RuntimeError('distributor.agent_server_cert is required')
    if not CONF.distributor.agent_server_ca:
        raise RuntimeError('distributor.agent_server_ca is required')
    gmr.TextGuruMeditation.setup_autorun(version)
    app = server.Server().app
    options = {
        'bind': utils.ip_port_str(CONF.distributor.bind_host,
                                  CONF.distributor.bind_port),
        'workers': 1,
        'timeout': 120,
        'certfile': CONF.distributor.agent_server_cert,
        'ca_certs': CONF.distributor.agent_server_ca,
        'cert_reqs': ssl.CERT_REQUIRED,
        'preload_app': True,
        'post_fork': _post_fork,
        'accesslog': '-',
        'errorlog': '-',
        'loglevel': 'info',
    }
    DistributorAgent(app, options).run()
