#    Copyright 2015 Rackspace
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

from keystoneclient.auth.identity import v2 as v2_client
from keystoneclient.auth.identity import v3 as v3_client
from keystoneclient import session
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils

from octavia.i18n import _LE


LOG = logging.getLogger(__name__)

cfg.CONF.import_group('keystone_authtoken', 'keystonemiddleware.auth_token')
cfg.CONF.import_group('keystone_authtoken_v3', 'octavia.common.config')

_SESSION = None


def get_session():
    """Initializes a Keystone session.

    :return: a Keystone Session object
    :raises Exception: if the session cannot be established
    """
    global _SESSION
    if not _SESSION:

        kwargs = {'auth_url': cfg.CONF.keystone_authtoken.auth_uri,
                  'username': cfg.CONF.keystone_authtoken.admin_user,
                  'password': cfg.CONF.keystone_authtoken.admin_password}

        if cfg.CONF.keystone_authtoken.auth_version == '2':
            client = v2_client
            kwargs['tenant_name'] = (cfg.CONF.keystone_authtoken.
                                     admin_tenant_name)
        elif cfg.CONF.keystone_authtoken.auth_version == '3':
            client = v3_client
            kwargs['project_name'] = (cfg.CONF.keystone_authtoken.
                                      admin_tenant_name)
            kwargs['user_domain_name'] = (cfg.CONF.keystone_authtoken_v3.
                                          admin_user_domain)
            kwargs['project_domain_name'] = (cfg.CONF.keystone_authtoken_v3.
                                             admin_project_domain)
        else:
            raise Exception('Unknown keystone version!')

        try:
            kc = client.Password(**kwargs)
            _SESSION = session.Session(
                auth=kc, verify=not cfg.CONF.keystone_authtoken.insecure)
        except Exception:
            with excutils.save_and_reraise_exception():
                LOG.exception(_LE("Error creating Keystone session."))

    return _SESSION
