# Copyright 2014,  Doug Wiegley,  A10 Networks.
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

import tempfile

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture

import octavia.common.config as config
import octavia.tests.unit.base as base


class TestConfig(base.TestCase):

    def test_sanity(self):
        config.init([])
        config.setup_logging(cfg.CONF)
        # Resetting because this will cause inconsistent errors when run with
        # other tests
        self.addCleanup(cfg.CONF.reset)

    def test_validate_server_certs_key_passphrase(self):
        conf = self.useFixture(oslo_fixture.Config(config.cfg.CONF))
        conf.config(
            group="certificates",
            server_certs_key_passphrase="insecure-key-do-not-use-this-key"
        )

        # Test too short
        self.assertRaises(ValueError, conf.config,
                          group="certificates",
                          server_certs_key_passphrase="short_passphrase")

        # Test too long
        self.assertRaises(
            ValueError, conf.config, group="certificates",
            server_certs_key_passphrase="long-insecure-key-do-not-use-this")

        # Test invalid characters
        self.assertRaises(
            ValueError, conf.config, group="certificates",
            server_certs_key_passphrase="insecure-key-do-not-u$e-this-key")

    def test_active_connection_retry_interval(self):
        conf = self.useFixture(oslo_fixture.Config(config.cfg.CONF))

        # Test new name
        with tempfile.NamedTemporaryFile(mode='w', delete=True) as tmp:
            tmp.write("[haproxy_amphora]\n"
                      "active_connection_retry_interval=4\n")
            tmp.flush()

            conf.set_config_files([tmp.name])

        self.assertEqual(
            4,
            conf.conf.haproxy_amphora.active_connection_retry_interval)

        # Test deprecated name
        with tempfile.NamedTemporaryFile(mode='w', delete=True) as tmp:
            tmp.write("[haproxy_amphora]\n"
                      "active_connection_rety_interval=3\n")
            tmp.flush()

            conf.set_config_files([tmp.name])

        self.assertEqual(
            3,
            conf.conf.haproxy_amphora.active_connection_retry_interval)

    def test_handle_neutron_deprecations(self):
        conf = self.useFixture(oslo_fixture.Config(config.cfg.CONF))

        # The deprecated settings are copied to the new settings
        conf.config(endpoint='my_endpoint',
                    endpoint_type='internal',
                    ca_certificates_file='/path/to/certs',
                    group='neutron')

        config.handle_neutron_deprecations()

        self.assertEqual('my_endpoint', conf.conf.neutron.endpoint_override)
        self.assertEqual(['internal'], conf.conf.neutron.valid_interfaces)
        self.assertEqual('/path/to/certs', conf.conf.neutron.cafile)

    # Test case for https://bugs.launchpad.net/octavia/+bug/2051604
    def test_handle_neutron_deprecations_with_precedence(self):
        conf = self.useFixture(oslo_fixture.Config(config.cfg.CONF))

        # The deprecated settings should not override the new settings when
        # they exist
        conf.config(endpoint='my_old_endpoint',
                    endpoint_type='old_type',
                    ca_certificates_file='/path/to/old_certs',
                    endpoint_override='my_endpoint',
                    valid_interfaces=['internal'],
                    cafile='/path/to/certs',
                    group='neutron')

        config.handle_neutron_deprecations()

        self.assertEqual('my_endpoint', conf.conf.neutron.endpoint_override)
        self.assertEqual(['internal'], conf.conf.neutron.valid_interfaces)
        self.assertEqual('/path/to/certs', conf.conf.neutron.cafile)
