# Copyright 2011 VMware, Inc., 2014 A10 Networks
# All Rights Reserved.
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

"""
Routines for configuring Octavia
"""

from oslo_config import cfg
from oslo_db import options as db_options
from oslo_log import log as logging
import oslo_messaging as messaging


from octavia.common import utils
from octavia.i18n import _LI
from octavia import version

LOG = logging.getLogger(__name__)

core_opts = [
    cfg.StrOpt('bind_host', default='0.0.0.0',
               help=_("The host IP to bind to")),
    cfg.IntOpt('bind_port', default=9876,
               help=_("The port to bind to")),
    cfg.StrOpt('api_handler', default='simulated_handler',
               help=_("The handler that the API communicates with")),
    cfg.StrOpt('api_paste_config', default="api-paste.ini",
               help=_("The API paste config file to use")),
    cfg.StrOpt('api_extensions_path', default="",
               help=_("The path for API extensions")),
    cfg.StrOpt('auth_strategy', default='keystone',
               help=_("The type of authentication to use")),
    cfg.BoolOpt('allow_bulk', default=True,
                help=_("Allow the usage of the bulk API")),
    cfg.BoolOpt('allow_pagination', default=False,
                help=_("Allow the usage of the pagination")),
    cfg.BoolOpt('allow_sorting', default=False,
                help=_("Allow the usage of the sorting")),
    cfg.StrOpt('pagination_max_limit', default="-1",
               help=_("The maximum number of items returned in a single "
                      "response, value was 'infinite' or negative integer "
                      "means no limit")),
    cfg.StrOpt('host', default=utils.get_hostname(),
               help=_("The hostname Octavia is running on")),
    cfg.StrOpt('nova_url',
               default='http://127.0.0.1:8774/v2',
               help=_('URL for connection to nova')),
    cfg.StrOpt('nova_admin_username',
               help=_('Username for connecting to nova in admin context')),
    cfg.StrOpt('nova_admin_password',
               help=_('Password for connection to nova in admin context'),
               secret=True),
    cfg.StrOpt('nova_admin_tenant_id',
               help=_('The uuid of the admin nova tenant')),
    cfg.StrOpt('nova_admin_auth_url',
               default='http://localhost:5000/v2.0',
               help=_('Authorization URL for connecting to nova in admin '
                      'context')),
    cfg.StrOpt('nova_ca_certificates_file',
               help=_('CA file for novaclient to verify server certificates')),
    cfg.BoolOpt('nova_api_insecure', default=False,
                help=_("If True, ignore any SSL validation issues")),
    cfg.StrOpt('nova_region_name',
               help=_('Name of nova region to use. Useful if keystone manages'
                      ' more than one region.')),
    cfg.StrOpt('octavia_plugins',
               default='hot_plug_plugin',
               help=_('Name of the controller plugin to use'))
]

networking_opts = [
    cfg.StrOpt('lb_network_name', help=_('Name of amphora internal network')),
]

oslo_messaging_opts = [
    cfg.StrOpt('topic'),
]

keystone_authtoken_v3_opts = [
    cfg.StrOpt('admin_user_domain', default='default',
               help=_('Admin user keystone authentication domain')),
    cfg.StrOpt('admin_project_domain', default='default',
               help=_('Admin project keystone authentication domain'))
]

haproxy_amphora_opts = [
    cfg.StrOpt('username',
               default='ubuntu',
               help=_('Name of user for access to amphora.')),
    cfg.StrOpt('key_path',
               default='/opt/stack/.ssh/id_rsa',
               help=_('Local absolute path to the private key '
                      'loaded on amphora at boot.')),
    cfg.StrOpt('base_path',
               default='/var/lib/octavia',
               help=_('Base directory for amphora files.')),
    cfg.StrOpt('base_cert_dir',
               default='/var/lib/octavia/certs',
               help=_('Base directory for cert storage.')),
    cfg.StrOpt('haproxy_template', help=_('Custom haproxy template.')),
    cfg.IntOpt('connection_max_retries',
               default=10,
               help=_('Retry threshold for connecting to amphorae.')),
    cfg.IntOpt('connection_retry_interval',
               default=5,
               help=_('Retry timeout between attempts in seconds.')),

    # REST server
    cfg.StrOpt('bind_host', default='0.0.0.0',
               help=_("The host IP to bind to")),
    cfg.IntOpt('bind_port', default=8443,
               help=_("The port to bind to")),
    cfg.StrOpt('haproxy_cmd', default='/usr/sbin/haproxy',
               help=_("The full path to haproxy")),
    cfg.IntOpt('respawn_count', default=2,
               help=_("The respawn count for haproxy's upstart script")),
    cfg.IntOpt('respawn_interval', default=2,
               help=_("The respawn interval for haproxy's upstart script")),
    cfg.StrOpt('haproxy_cert_dir', default='/tmp/',
               help=_("The directory to store haproxy cert files in")),
    cfg.StrOpt('agent_server_cert', default='/etc/octavia/certs/server.pem',
               help=_("The server certificate for the agent.py server "
                      "to use")),
    cfg.StrOpt('agent_server_ca', default='/etc/octavia/certs/client_ca.pem',
               help=_("The ca which signed the client certificates")),
    cfg.StrOpt('agent_server_network_dir',
               default='/etc/network/interfaces.d/',
               help=_("The directory where new network interfaces "
                      "are located")),
    # REST client
    cfg.StrOpt('client_cert', default='/etc/octavia/certs/client.pem',
               help=_("The client certificate to talk to the agent")),
    cfg.StrOpt('server_ca', default='/etc/octavia/certs/server_ca.pem',
               help=_("The ca which signed the server certificates")),
]

controller_worker_opts = [
    cfg.IntOpt('amp_active_retries',
               default=10,
               help=_('Retry attempts to wait for Amphora to become active')),
    cfg.IntOpt('amp_active_wait_sec',
               default=10,
               help=_('Seconds to wait for an Amphora to become active')),
    cfg.StrOpt('amp_flavor_id',
               default='',
               help=_('Nova instance flavor id for the Amphora')),
    cfg.StrOpt('amp_image_id',
               default='',
               help=_('Glance image id for the Amphora image to boot')),
    cfg.StrOpt('amp_ssh_key_name',
               default='',
               help=_('SSH key name used to boot the Amphora')),
    cfg.StrOpt('amp_network',
               default='',
               help=_('Network to attach to the Amphora')),
    cfg.ListOpt('amp_secgroup_list',
                default='',
                help=_('List of security groups to attach to the Amphora')),
    cfg.StrOpt('client_ca',
               default='/etc/octavia/certs/ca_01.pem',
               help=_('Client CA for the amphora agent to use')),
    cfg.StrOpt('amphora_driver',
               default='amphora_noop_driver',
               help=_('Name of the amphora driver to use')),
    cfg.StrOpt('compute_driver',
               default='compute_noop_driver',
               help=_('Name of the compute driver to use')),
    cfg.StrOpt('network_driver',
               default='network_noop_driver',
               help=_('Name of the network driver to use')),
    cfg.StrOpt('cert_generator',
               default='local_cert_generator',
               help=_('Name of the cert generator to use'))
]

task_flow_opts = [
    cfg.StrOpt('engine',
               default='serial',
               help=_('TaskFlow engine to use')),
    cfg.IntOpt('max_workers',
               default=5,
               help=_('The maximum number of workers'))
]

core_cli_opts = []

certificate_opts = [
    cfg.StrOpt('cert_manager',
               default='local_cert_manager',
               help='Name of the cert manager to use'),
    cfg.StrOpt('cert_generator',
               default='local_cert_generator',
               help='Name of the cert generator to use'),
]

# Register the configuration options
cfg.CONF.register_opts(core_opts)
cfg.CONF.register_opts(networking_opts, group='networking')
cfg.CONF.register_opts(oslo_messaging_opts, group='oslo_messaging')
cfg.CONF.register_opts(haproxy_amphora_opts, group='haproxy_amphora')
cfg.CONF.register_opts(controller_worker_opts, group='controller_worker')
cfg.CONF.register_opts(task_flow_opts, group='task_flow')
cfg.CONF.register_opts(oslo_messaging_opts, group='oslo_messaging')
cfg.CONF.register_cli_opts(core_cli_opts)
cfg.CONF.register_opts(certificate_opts, group='certificates')
cfg.CONF.import_group('keystone_authtoken', 'keystonemiddleware.auth_token')
cfg.CONF.register_opts(keystone_authtoken_v3_opts,
                       group='keystone_authtoken_v3')

# Ensure that the control exchange is set correctly
messaging.set_transport_defaults(control_exchange='octavia')
_SQL_CONNECTION_DEFAULT = 'sqlite://'
# Update the default QueuePool parameters. These can be tweaked by the
# configuration variables - max_pool_size, max_overflow and pool_timeout
db_options.set_defaults(cfg.CONF,
                        connection=_SQL_CONNECTION_DEFAULT,
                        sqlite_db='', max_pool_size=10,
                        max_overflow=20, pool_timeout=10)

logging.register_options(cfg.CONF)


def init(args, **kwargs):
    cfg.CONF(args=args, project='octavia',
             version='%%prog %s' % version.version_info.release_string(),
             **kwargs)


def setup_logging(conf):
    """Sets up the logging options for a log with supplied name.

    :param conf: a cfg.ConfOpts object
    """
    product_name = "octavia"
    logging.setup(conf, product_name)
    LOG.info(_LI("Logging enabled!"))


# def load_paste_app(app_name):
#     """Builds and returns a WSGI app from a paste config file.

#     :param app_name: Name of the application to load
#     :raises ConfigFilesNotFoundError when config file cannot be located
#     :raises RuntimeError when application cannot be loaded from config file
#     """

#     config_path = cfg.CONF.find_file(cfg.CONF.api_paste_config)
#     if not config_path:
#         raise cfg.ConfigFilesNotFoundError(
#             config_files=[cfg.CONF.api_paste_config])
#     config_path = os.path.abspath(config_path)
#     LOG.info(_("Config paste file: %s"), config_path)

#     try:
#         app = deploy.loadapp("config:%s" % config_path, name=app_name)
#     except (LookupError, ImportError):
#         msg = (_("Unable to load %(app_name)s from "
#                  "configuration file %(config_path)s.") %
#                {'app_name': app_name,
#                 'config_path': config_path})
#         LOG.exception(msg)
#         raise RuntimeError(msg)
#     return app
