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

from keystoneauth1 import loading as ks_loading
from oslo_config import cfg
from oslo_log import log as logging

from octavia.common import constants

LOG = logging.getLogger(__name__)


class KeystoneSession:

    def __init__(self, section=constants.SERVICE_AUTH):
        self._session = None

        self.section = section
        ks_loading.register_auth_conf_options(cfg.CONF, self.section)
        ks_loading.register_session_conf_options(cfg.CONF, self.section)

    def get_session(self):
        """Initializes a Keystone session.

        :return: a Keystone Session object
        """
        if not self._session:
            self._auth = ks_loading.load_auth_from_conf_options(
                cfg.CONF, self.section)
            self._session = ks_loading.load_session_from_conf_options(
                cfg.CONF, self.section, auth=self._auth)

        return self._session
