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

from oslo.config import cfg

from octavia.common import config
from octavia.i18n import _LI
from octavia.openstack.common import log

LOG = log.getLogger(__name__)


def prepare_service(argv=None):
    """Sets global config from config file and sets up logging."""
    argv = argv or []
    config.init(argv[1:])
    LOG.info(_LI('Starting Octavia API server'))
    cfg.set_defaults(log.log_opts,
                     default_log_levels=['amqp=WARN',
                                         'amqplib=WARN',
                                         'qpid.messaging=INFO',
                                         'sqlalchemy=WARN',
                                         'keystoneclient=INFO',
                                         'stevedore=INFO',
                                         'eventlet.wsgi.server=WARN',
                                         'iso8601=WARN',
                                         'paramiko=WARN',
                                         'requests=WARN',
                                         'ironic.openstack.common=WARN',
                                         ])
    config.setup_logging(cfg.CONF)
