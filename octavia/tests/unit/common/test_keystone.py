#  Copyright Red Hat
#
#     Licensed under the Apache License, Version 2.0 (the "License"); you may
#     not use this file except in compliance with the License. You may obtain
#     a copy of the License at
#
#          http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#     WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#     License for the specific language governing permissions and limitations
#     under the License.
from unittest import mock
from unittest.mock import call

from keystoneauth1 import exceptions as ks_exceptions
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture

import octavia.common.keystone as ks
import octavia.tests.unit.base as base


class TestKeystoneSession(base.TestCase):

    @mock.patch("oslo_config.cfg.ConfigOpts.get_location", return_value=None)
    @mock.patch("octavia.common.keystone.ks_loading"
                ".load_auth_from_conf_options")
    @mock.patch("octavia.common.keystone.LOG")
    def test_get_auth_neutron_override(self, mock_log, mock_load_auth,
                                       mock_get_location):
        opt_mock = mock.MagicMock()
        opt_mock.dest = "foo"
        conf = oslo_fixture.Config(cfg.CONF)
        conf.conf.service_auth.cafile = "bar"

        mock_load_auth.side_effect = [
            ks_exceptions.auth_plugins.MissingRequiredOptions(
                [opt_mock]),
            None,
            None
        ]

        sess = ks.KeystoneSession("neutron")
        sess.get_auth()

        mock_load_auth.assert_has_calls([call(cfg.CONF, 'neutron'),
                                         call(cfg.CONF, 'service_auth'),
                                         call(cfg.CONF, 'neutron')])
        mock_log.debug.assert_has_calls(
            [call("Overriding [%s].%s with '%s'", 'neutron', 'cafile',
                  'bar')]
        )
