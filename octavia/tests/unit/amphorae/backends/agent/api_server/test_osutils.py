# Copyright 2017 Redhat.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import shutil

import mock
from oslo_config import fixture as oslo_fixture

from octavia.amphorae.backends.agent.api_server import osutils
from octavia.common import config
from octavia.common import constants as consts
from octavia.common import exceptions as octavia_exceptions
from octavia.tests.unit import base


class TestOSUtils(base.TestCase):

    def setUp(self):
        super(TestOSUtils, self).setUp()

        self.base_os_util = osutils.BaseOS('unknown')

        with mock.patch('platform.linux_distribution',
                        return_value=['Ubuntu', 'Foo', 'Bar']):
            self.ubuntu_os_util = osutils.BaseOS.get_os_util()

        with mock.patch('platform.linux_distribution',
                        return_value=['centos', 'Foo', 'Bar']):
            self.rh_os_util = osutils.BaseOS.get_os_util()

    def test_get_os_util(self):
        with mock.patch('platform.linux_distribution',
                        return_value=['Ubuntu', 'Foo', 'Bar']):
            returned_cls = osutils.BaseOS.get_os_util()
            self.assertIsInstance(returned_cls, osutils.Ubuntu)
        with mock.patch('platform.linux_distribution',
                        return_value=['fedora', 'Foo', 'Bar']):
            returned_cls = osutils.BaseOS.get_os_util()
            self.assertIsInstance(returned_cls, osutils.RH)
        with mock.patch('platform.linux_distribution',
                        return_value=['redhat', 'Foo', 'Bar']):
            returned_cls = osutils.BaseOS.get_os_util()
            self.assertIsInstance(returned_cls, osutils.RH)
        with mock.patch('platform.linux_distribution',
                        return_value=['centos', 'Foo', 'Bar']):
            returned_cls = osutils.BaseOS.get_os_util()
            self.assertIsInstance(returned_cls, osutils.RH)
        with mock.patch('platform.linux_distribution',
                        return_value=['FakeOS', 'Foo', 'Bar']):
            self.assertRaises(
                octavia_exceptions.InvalidAmphoraOperatingSystem,
                osutils.BaseOS.get_os_util)

    def test_get_network_interface_file(self):
        conf = self.useFixture(oslo_fixture.Config(config.cfg.CONF))

        fake_agent_server_network_dir = "/path/to/interface"
        fake_agent_server_network_file = "/path/to/interfaces_file"

        base_fake_nic_path = os.path.join(fake_agent_server_network_dir,
                                          consts.NETNS_PRIMARY_INTERFACE)
        base_real_nic_path = os.path.join(
            consts.UBUNTU_AMP_NET_DIR_TEMPLATE.format(
                netns=consts.AMPHORA_NAMESPACE),
            consts.NETNS_PRIMARY_INTERFACE)

        rh_interface_name = 'ifcfg-{nic}'.format(
            nic=consts.NETNS_PRIMARY_INTERFACE)
        rh_fake_nic_path = os.path.join(fake_agent_server_network_dir,
                                        rh_interface_name)
        rh_real_nic_path = os.path.join(
            consts.RH_AMP_NET_DIR_TEMPLATE.format(
                netns=consts.AMPHORA_NAMESPACE),
            rh_interface_name)

        ubuntu_interface_name = '{nic}.cfg'.format(
            nic=consts.NETNS_PRIMARY_INTERFACE)
        ubuntu_fake_nic_path = os.path.join(fake_agent_server_network_dir,
                                            ubuntu_interface_name)
        ubuntu_real_nic_path = os.path.join(
            consts.UBUNTU_AMP_NET_DIR_TEMPLATE.format(
                netns=consts.AMPHORA_NAMESPACE),
            ubuntu_interface_name)

        # Check that agent_server_network_file is returned, when provided
        conf.config(group="amphora_agent",
                    agent_server_network_file=fake_agent_server_network_file)

        base_interface_file = (
            self.base_os_util.
            get_network_interface_file(consts.NETNS_PRIMARY_INTERFACE))
        self.assertEqual(fake_agent_server_network_file, base_interface_file)

        rh_interface_file = (
            self.rh_os_util.
            get_network_interface_file(consts.NETNS_PRIMARY_INTERFACE))
        self.assertEqual(fake_agent_server_network_file, rh_interface_file)

        ubuntu_interface_file = (
            self.ubuntu_os_util.
            get_network_interface_file(consts.NETNS_PRIMARY_INTERFACE))
        self.assertEqual(fake_agent_server_network_file, ubuntu_interface_file)

        # Check that agent_server_network_dir is used, when provided
        conf.config(group="amphora_agent", agent_server_network_file=None)
        conf.config(group="amphora_agent",
                    agent_server_network_dir=fake_agent_server_network_dir)

        base_interface_file = (
            self.base_os_util.
            get_network_interface_file(consts.NETNS_PRIMARY_INTERFACE))
        self.assertEqual(base_fake_nic_path, base_interface_file)

        rh_interface_file = (
            self.rh_os_util.
            get_network_interface_file(consts.NETNS_PRIMARY_INTERFACE))
        self.assertEqual(rh_fake_nic_path, rh_interface_file)

        ubuntu_interface_file = (
            self.ubuntu_os_util.
            get_network_interface_file(consts.NETNS_PRIMARY_INTERFACE))
        self.assertEqual(ubuntu_fake_nic_path, ubuntu_interface_file)

        # Check When neither agent_server_network_dir or
        # agent_server_network_file where provided.
        conf.config(group="amphora_agent", agent_server_network_file=None)
        conf.config(group="amphora_agent", agent_server_network_dir=None)

        base_interface_file = (
            self.base_os_util.
            get_network_interface_file(consts.NETNS_PRIMARY_INTERFACE))
        self.assertEqual(base_real_nic_path, base_interface_file)

        rh_interface_file = (
            self.rh_os_util.
            get_network_interface_file(consts.NETNS_PRIMARY_INTERFACE))
        self.assertEqual(rh_real_nic_path, rh_interface_file)

        ubuntu_interface_file = (
            self.ubuntu_os_util.
            get_network_interface_file(consts.NETNS_PRIMARY_INTERFACE))
        self.assertEqual(ubuntu_real_nic_path, ubuntu_interface_file)

    def test_cmd_get_version_of_installed_package(self):
        package_name = 'foo'
        ubuntu_cmd = "dpkg-query -W -f=${{Version}} {name}".format(
            name=package_name)
        rh_cmd = "rpm -q --queryformat %{{VERSION}} {name}".format(
            name=package_name)

        returned_ubuntu_cmd = (
            self.ubuntu_os_util.cmd_get_version_of_installed_package(
                package_name))
        self.assertEqual(ubuntu_cmd, returned_ubuntu_cmd)

        returned_rh_cmd = (self.rh_os_util.
                           cmd_get_version_of_installed_package(package_name))
        self.assertEqual(rh_cmd, returned_rh_cmd)

    def test_has_ifup_all(self):
        self.assertTrue(self.base_os_util.has_ifup_all())
        self.assertTrue(self.ubuntu_os_util.has_ifup_all())
        self.assertFalse(self.rh_os_util.has_ifup_all())

    @mock.patch('shutil.copy2')
    @mock.patch('os.makedirs')
    @mock.patch('shutil.copytree')
    def test_create_netns_dir(self, mock_copytree, mock_makedirs, mock_copy2):
        network_dir = 'foo'
        netns_network_dir = 'fake_netns_network'
        ignore = shutil.ignore_patterns('fake_eth*', 'fake_loopback*')
        self.rh_os_util.create_netns_dir(network_dir,
                                         netns_network_dir,
                                         ignore)
        mock_copytree.assert_any_call(
            network_dir,
            os.path.join('/etc/netns/',
                         consts.AMPHORA_NAMESPACE,
                         netns_network_dir),
            ignore=ignore,
            symlinks=True)

        mock_makedirs.assert_any_call(os.path.join('/etc/netns/',
                                                   consts.AMPHORA_NAMESPACE))
        mock_copy2.assert_any_call(
            '/etc/sysconfig/network',
            '/etc/netns/{netns}/sysconfig'.format(
                netns=consts.AMPHORA_NAMESPACE))

        mock_copytree.reset_mock()
        mock_makedirs.reset_mock()
        mock_copy2.reset_mock()

        self.ubuntu_os_util.create_netns_dir(network_dir,
                                             netns_network_dir,
                                             ignore)
        mock_copytree.assert_any_call(
            network_dir,
            os.path.join('/etc/netns/',
                         consts.AMPHORA_NAMESPACE,
                         netns_network_dir),
            ignore=ignore,
            symlinks=True)

        mock_makedirs.assert_any_call(os.path.join('/etc/netns/',
                                                   consts.AMPHORA_NAMESPACE))
        mock_copy2.assert_not_called()
