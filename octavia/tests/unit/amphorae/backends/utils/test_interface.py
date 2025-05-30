# Copyright 2020 Red Hat, Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import errno
import os
import socket
import subprocess
from unittest import mock

import pyroute2

from octavia.amphorae.backends.utils import interface
from octavia.amphorae.backends.utils import interface_file
from octavia.common import constants as consts
from octavia.common import exceptions
from octavia.tests.common import utils as test_utils
import octavia.tests.unit.base as base


class TestInterface(base.TestCase):
    @mock.patch('os.listdir')
    @mock.patch('octavia.amphorae.backends.utils.interface_file.'
                'InterfaceFile.get_directory')
    def test_interface_file_list(self, mock_get_directory, mock_listdir):
        mock_get_directory.return_value = consts.AMP_NET_DIR_TEMPLATE

        ifaces = ('eth0', 'eth7', 'eth8')
        mock_listdir.return_value = [
            f"{iface}.json"
            for iface in ifaces
        ]
        mock_listdir.return_value.extend(["invalidfile"])

        controller = interface.InterfaceController()
        r = controller.interface_file_list()
        config_file_list = list(r)

        for iface in ifaces:
            f = os.path.join(consts.AMP_NET_DIR_TEMPLATE,
                             f"{iface}.json")
            self.assertIn(f, config_file_list)

        # unsupported file
        f = os.path.join(consts.AMP_NET_DIR_TEMPLATE,
                         "invalidfile")
        self.assertNotIn(f, config_file_list)

        # non existing file
        f = os.path.join(consts.AMP_NET_DIR_TEMPLATE,
                         "eth2.json")
        self.assertNotIn(f, config_file_list)

    @mock.patch('os.listdir')
    @mock.patch('octavia.amphorae.backends.utils.interface_file.'
                'InterfaceFile.get_directory')
    def test_list(self, mock_get_directory, mock_listdir):
        mock_get_directory.return_value = consts.AMP_NET_DIR_TEMPLATE
        mock_listdir.return_value = ["fakeiface.json"]

        content = ('{\n'
                   '"addresses": [\n'
                   '{"address": "10.0.0.2",\n'
                   '"prefixlen": 24}\n'
                   '],\n'
                   '"mtu": 1450,\n'
                   '"name": "eth1",\n'
                   '"if_type": "mytype",\n'
                   '"routes": [\n'
                   '{"dst": "0.0.0.0/0",\n'
                   '"gateway": "10.0.0.1"},\n'
                   '{"dst": "10.11.0.0/16",\n'
                   '"gateway": "10.0.0.24"}\n'
                   '],\n'
                   '"rules": [\n'
                   '{"src": "10.0.0.2",\n'
                   '"src_len": 32,\n'
                   '"table": 100}\n'
                   '],\n'
                   '"scripts": {\n'
                   '"up": [\n'
                   '{"command": "up-script"}],\n'
                   '"down": [\n'
                   '{"command": "down-script"}]\n'
                   '}}\n')

        filename = os.path.join(consts.AMP_NET_DIR_TEMPLATE,
                                "fakeiface.json")

        self.useFixture(
            test_utils.OpenFixture(filename,
                                   contents=content))

        controller = interface.InterfaceController()
        ifaces = controller.list()

        self.assertIn("eth1", ifaces)
        iface = ifaces["eth1"]

        expected_dict = {
            consts.NAME: "eth1",
            consts.IF_TYPE: "mytype",
            consts.MTU: 1450,
            consts.ADDRESSES: [{
                consts.ADDRESS: "10.0.0.2",
                consts.PREFIXLEN: 24
            }],
            consts.ROUTES: [{
                consts.DST: "0.0.0.0/0",
                consts.GATEWAY: "10.0.0.1"
            }, {
                consts.DST: "10.11.0.0/16",
                consts.GATEWAY: "10.0.0.24"
            }],
            consts.RULES: [{
                consts.SRC: "10.0.0.2",
                consts.SRC_LEN: 32,
                consts.TABLE: 100
            }],
            consts.SCRIPTS: {
                consts.IFACE_UP: [{
                    consts.COMMAND: "up-script"
                }],
                consts.IFACE_DOWN: [{
                    consts.COMMAND: "down-script"
                }]
            }
        }

        self.assertEqual(expected_dict[consts.NAME], iface.name)
        self.assertEqual(expected_dict[consts.MTU], iface.mtu)
        test_utils.assert_address_lists_equal(
            self, expected_dict[consts.ADDRESSES], iface.addresses)
        test_utils.assert_rule_lists_equal(
            self, expected_dict[consts.RULES], iface.rules)
        test_utils.assert_script_lists_equal(
            self, expected_dict[consts.SCRIPTS], iface.scripts)

    def test__ipr_command(self):
        mock_ipr_addr = mock.MagicMock()

        controller = interface.InterfaceController()
        controller._ipr_command(mock_ipr_addr,
                                controller.ADD,
                                arg1=1, arg2=2)

        mock_ipr_addr.assert_called_once_with('add', arg1=1, arg2=2)

    def test__ipr_command_add_eexist(self):
        mock_ipr_addr = mock.MagicMock()
        mock_ipr_addr.side_effect = [
            pyroute2.NetlinkError(code=errno.EEXIST)
        ]

        controller = interface.InterfaceController()
        controller._ipr_command(mock_ipr_addr,
                                controller.ADD,
                                arg1=1, arg2=2)

        mock_ipr_addr.assert_called_once_with('add', arg1=1, arg2=2)

    def test__ipr_command_add_retry(self):
        mock_ipr_addr = mock.MagicMock()
        mock_ipr_addr.side_effect = [
            pyroute2.NetlinkError(code=errno.EINVAL),
            pyroute2.NetlinkError(code=errno.EINVAL),
            pyroute2.NetlinkError(code=errno.EINVAL),
            None
        ]

        controller = interface.InterfaceController()
        controller._ipr_command(mock_ipr_addr,
                                controller.ADD,
                                retry_on_invalid_argument=True,
                                retry_interval=0,
                                arg1=1, arg2=2)

        mock_ipr_addr.assert_has_calls([
            mock.call('add', arg1=1, arg2=2),
            mock.call('add', arg1=1, arg2=2),
            mock.call('add', arg1=1, arg2=2),
            mock.call('add', arg1=1, arg2=2)])

    def test__ipr_command_add_einval_failed(self):
        mock_ipr_addr = mock.MagicMock()
        mock_ipr_addr.__name__ = "addr"
        mock_ipr_addr.side_effect = [
            pyroute2.NetlinkError(code=errno.EINVAL)
        ] * 21

        controller = interface.InterfaceController()
        self.assertRaises(exceptions.AmphoraNetworkConfigException,
                          controller._ipr_command,
                          mock_ipr_addr,
                          controller.ADD,
                          retry_on_invalid_argument=True,
                          max_retries=20,
                          retry_interval=0,
                          arg1=1, arg2=2)
        mock_ipr_addr.assert_has_calls([
            mock.call('add', arg1=1, arg2=2)
        ] * 20)

    def test__ipr_command_add_failed(self):
        mock_ipr_addr = mock.MagicMock()
        mock_ipr_addr.__name__ = "addr"
        mock_ipr_addr.side_effect = [
            pyroute2.NetlinkError(code=errno.ENOENT)
        ]

        controller = interface.InterfaceController()
        self.assertRaises(exceptions.AmphoraNetworkConfigException,
                          controller._ipr_command,
                          mock_ipr_addr,
                          controller.ADD,
                          retry_on_invalid_argument=True,
                          max_retries=20,
                          retry_interval=0,
                          arg1=1, arg2=2)
        mock_ipr_addr.assert_called_once_with(
            'add', arg1=1, arg2=2)

    def test__ipr_command_delete_failed_no_raise(self):
        mock_ipr_addr = mock.MagicMock()
        mock_ipr_addr.__name__ = "addr"
        mock_ipr_addr.side_effect = [
            pyroute2.NetlinkError(code=errno.EINVAL)
        ]

        controller = interface.InterfaceController()
        controller._ipr_command(mock_ipr_addr,
                                controller.DELETE,
                                retry_on_invalid_argument=True,
                                max_retries=0,
                                raise_on_error=False,
                                arg1=1, arg2=2)
        mock_ipr_addr.assert_called_once_with(
            'delete', arg1=1, arg2=2)

    def test__ipr_command_add_failed_retry_no_raise(self):
        mock_ipr_addr = mock.MagicMock()
        mock_ipr_addr.__name__ = "addr"
        mock_ipr_addr.side_effect = [
            pyroute2.NetlinkError(code=errno.ENOENT)
        ]

        controller = interface.InterfaceController()
        controller._ipr_command(mock_ipr_addr,
                                controller.ADD,
                                max_retries=20,
                                retry_interval=0,
                                raise_on_error=False,
                                arg1=1, arg2=2)
        mock_ipr_addr.assert_called_once_with(
            'add', arg1=1, arg2=2)

    @mock.patch('subprocess.check_output')
    def test__dhclient_up(self, mock_check_output):
        iface = "iface2"

        controller = interface.InterfaceController()
        controller._dhclient_up(iface)

        mock_check_output.assert_called_once_with(
            ["/sbin/dhclient",
             "-lf",
             f"/var/lib/dhclient/dhclient-{iface}.leases",
             "-pf",
             f"/run/dhclient-{iface}.pid",
             iface], stderr=subprocess.STDOUT)

    @mock.patch('subprocess.check_output')
    def test__dhclient_down(self, mock_check_output):
        iface = "iface2"

        controller = interface.InterfaceController()
        controller._dhclient_down(iface)

        mock_check_output.assert_called_once_with(
            ["/sbin/dhclient",
             "-r",
             "-lf",
             f"/var/lib/dhclient/dhclient-{iface}.leases",
             "-pf",
             f"/run/dhclient-{iface}.pid",
             iface], stderr=subprocess.STDOUT)

    @mock.patch('subprocess.check_output')
    def test__ipv6auto_up(self, mock_check_output):
        iface = "iface2"

        controller = interface.InterfaceController()
        controller._ipv6auto_up(iface)

        mock_check_output.assert_has_calls([
            mock.call(["/sbin/sysctl", "-w",
                       "net.ipv6.conf.iface2.accept_ra=2"],
                      stderr=subprocess.STDOUT),
            mock.call(["/sbin/sysctl", "-w",
                       "net.ipv6.conf.iface2.autoconf=1"],
                      stderr=subprocess.STDOUT)])

    @mock.patch('subprocess.check_output')
    def test__ipv6auto_down(self, mock_check_output):
        iface = "iface2"

        controller = interface.InterfaceController()
        controller._ipv6auto_down(iface)

        mock_check_output.assert_has_calls([
            mock.call(["/sbin/sysctl", "-w",
                       "net.ipv6.conf.iface2.accept_ra=0"],
                      stderr=subprocess.STDOUT),
            mock.call(["/sbin/sysctl", "-w",
                       "net.ipv6.conf.iface2.autoconf=0"],
                      stderr=subprocess.STDOUT)])

    @mock.patch('pyroute2.IPRoute.rule', create=True)
    @mock.patch('pyroute2.IPRoute.route', create=True)
    @mock.patch('pyroute2.IPRoute.addr', create=True)
    @mock.patch('pyroute2.IPRoute.link', create=True)
    @mock.patch('pyroute2.IPRoute.get_links', create=True)
    @mock.patch('pyroute2.IPRoute.link_lookup', create=True)
    @mock.patch('subprocess.check_output')
    def test_up(self, mock_check_output, mock_link_lookup, mock_get_links,
                mock_link, mock_addr, mock_route, mock_rule):
        iface = interface_file.InterfaceFile(
            name="eth1",
            if_type="vip",
            mtu=1450,
            addresses=[{
                consts.ADDRESS: '1.2.3.4',
                consts.PREFIXLEN: 24
            }, {
                consts.ADDRESS: '10.2.3.4',
                consts.PREFIXLEN: 16
            }, {
                consts.ADDRESS: '2001:db8::3',
                consts.PREFIXLEN: 64
            }],
            routes=[{
                consts.DST: '10.0.0.0/8',
                consts.GATEWAY: '1.0.0.1',
                consts.TABLE: 10,
                consts.ONLINK: True
            }, {
                consts.DST: '20.0.0.0/8',
                consts.GATEWAY: '1.0.0.2',
                consts.PREFSRC: '1.2.3.4',
                consts.SCOPE: 'link'
            }, {
                consts.DST: '2001:db8:2::1/128',
                consts.GATEWAY: '2001:db8::1'
            }],
            rules=[{
                consts.SRC: '1.1.1.1',
                consts.SRC_LEN: 32,
                consts.TABLE: 20,
            }, {
                consts.SRC: '2001:db8::1',
                consts.SRC_LEN: 128,
                consts.TABLE: 40,
            }],
            scripts={
                consts.IFACE_UP: [{
                    consts.COMMAND: "post-up eth1"
                }],
                consts.IFACE_DOWN: [{
                    consts.COMMAND: "post-down eth1"
                }],
            })

        idx = mock.MagicMock()
        mock_link_lookup.return_value = [idx]

        mock_get_links.return_value = [{
            consts.STATE: consts.IFACE_DOWN
        }]

        controller = interface.InterfaceController()
        controller.up(iface)

        mock_link.assert_called_once_with(
            controller.SET,
            index=idx,
            state=consts.IFACE_UP,
            mtu=1450)

        mock_addr.assert_has_calls([
            mock.call(controller.ADD,
                      index=idx,
                      address='1.2.3.4',
                      prefixlen=24,
                      family=socket.AF_INET),
            mock.call(controller.ADD,
                      index=idx,
                      address='10.2.3.4',
                      prefixlen=16,
                      family=socket.AF_INET),
            mock.call(controller.ADD,
                      index=idx,
                      address='2001:db8::3',
                      prefixlen=64,
                      family=socket.AF_INET6)
        ])

        mock_route.assert_has_calls([
            mock.call(controller.ADD,
                      oif=idx,
                      dst='10.0.0.0/8',
                      gateway='1.0.0.1',
                      table=10,
                      onlink=True,
                      family=socket.AF_INET),
            mock.call(controller.ADD,
                      oif=idx,
                      dst='20.0.0.0/8',
                      gateway='1.0.0.2',
                      prefsrc='1.2.3.4',
                      scope='link',
                      family=socket.AF_INET),
            mock.call(controller.ADD,
                      oif=idx,
                      dst='2001:db8:2::1/128',
                      gateway='2001:db8::1',
                      family=socket.AF_INET6)])

        mock_rule.assert_has_calls([
            mock.call(controller.ADD,
                      src="1.1.1.1",
                      src_len=32,
                      table=20,
                      family=socket.AF_INET),
            mock.call(controller.ADD,
                      src="2001:db8::1",
                      src_len=128,
                      table=40,
                      family=socket.AF_INET6)])

        mock_check_output.assert_has_calls([
            mock.call(["post-up", "eth1"])
        ])

    @mock.patch('octavia.amphorae.backends.utils.network_namespace.'
                'NetworkNamespace')
    @mock.patch('octavia.amphorae.backends.utils.nftable_utils.'
                'write_nftable_rules_file')
    @mock.patch('pyroute2.IPRoute.rule', create=True)
    @mock.patch('pyroute2.IPRoute.route', create=True)
    @mock.patch('pyroute2.IPRoute.addr', create=True)
    @mock.patch('pyroute2.IPRoute.link', create=True)
    @mock.patch('pyroute2.IPRoute.get_links', create=True)
    @mock.patch('pyroute2.IPRoute.link_lookup', create=True)
    @mock.patch('subprocess.check_output')
    def test_up_sriov(self, mock_check_output, mock_link_lookup,
                      mock_get_links, mock_link, mock_addr, mock_route,
                      mock_rule, mock_nftable, mock_netns):
        iface = interface_file.InterfaceFile(
            name="fake-eth1",
            if_type="vip",
            mtu=1450,
            addresses=[{
                consts.ADDRESS: '192.0.2.4',
                consts.PREFIXLEN: 24
            }, {
                consts.ADDRESS: '198.51.100.4',
                consts.PREFIXLEN: 16
            }, {
                consts.ADDRESS: '2001:db8::3',
                consts.PREFIXLEN: 64
            }],
            routes=[{
                consts.DST: '203.0.113.0/24',
                consts.GATEWAY: '192.0.2.1',
                consts.TABLE: 10,
                consts.ONLINK: True
            }, {
                consts.DST: '198.51.100.0/24',
                consts.GATEWAY: '192.0.2.2',
                consts.PREFSRC: '192.0.2.4',
                consts.SCOPE: 'link'
            }, {
                consts.DST: '2001:db8:2::1/128',
                consts.GATEWAY: '2001:db8::1'
            }],
            rules=[{
                consts.SRC: '203.0.113.1',
                consts.SRC_LEN: 32,
                consts.TABLE: 20,
            }, {
                consts.SRC: '2001:db8::1',
                consts.SRC_LEN: 128,
                consts.TABLE: 40,
            }],
            scripts={
                consts.IFACE_UP: [{
                    consts.COMMAND: "post-up fake-eth1"
                }],
                consts.IFACE_DOWN: [{
                    consts.COMMAND: "post-down fake-eth1"
                }],
            },
            is_sriov=True)

        idx = mock.MagicMock()
        mock_link_lookup.return_value = [idx]

        mock_get_links.return_value = [{
            consts.STATE: consts.IFACE_DOWN
        }]

        controller = interface.InterfaceController()
        controller.up(iface)

        mock_link.assert_called_once_with(
            controller.SET,
            index=idx,
            state=consts.IFACE_UP,
            mtu=1450)

        mock_addr.assert_has_calls([
            mock.call(controller.ADD,
                      index=idx,
                      address='192.0.2.4',
                      prefixlen=24,
                      family=socket.AF_INET),
            mock.call(controller.ADD,
                      index=idx,
                      address='198.51.100.4',
                      prefixlen=16,
                      family=socket.AF_INET),
            mock.call(controller.ADD,
                      index=idx,
                      address='2001:db8::3',
                      prefixlen=64,
                      family=socket.AF_INET6)
        ])

        mock_route.assert_has_calls([
            mock.call(controller.ADD,
                      oif=idx,
                      dst='203.0.113.0/24',
                      gateway='192.0.2.1',
                      table=10,
                      onlink=True,
                      family=socket.AF_INET),
            mock.call(controller.ADD,
                      oif=idx,
                      dst='198.51.100.0/24',
                      gateway='192.0.2.2',
                      prefsrc='192.0.2.4',
                      scope='link',
                      family=socket.AF_INET),
            mock.call(controller.ADD,
                      oif=idx,
                      dst='2001:db8:2::1/128',
                      gateway='2001:db8::1',
                      family=socket.AF_INET6)])

        mock_rule.assert_has_calls([
            mock.call(controller.ADD,
                      src="203.0.113.1",
                      src_len=32,
                      table=20,
                      family=socket.AF_INET),
            mock.call(controller.ADD,
                      src="2001:db8::1",
                      src_len=128,
                      table=40,
                      family=socket.AF_INET6)])

        mock_check_output.assert_has_calls([
            mock.call([consts.NFT_CMD, '-o', '-f', consts.NFT_RULES_FILE],
                      stderr=subprocess.STDOUT),
            mock.call(["post-up", "fake-eth1"])
        ])

        mock_nftable.assert_called_once_with('fake-eth1', [])

    @mock.patch('pyroute2.IPRoute.rule', create=True)
    @mock.patch('pyroute2.IPRoute.get_routes', create=True)
    @mock.patch('pyroute2.IPRoute.addr', create=True)
    @mock.patch('pyroute2.IPRoute.link', create=True)
    @mock.patch('pyroute2.IPRoute.get_links', create=True)
    @mock.patch('pyroute2.IPRoute.link_lookup', create=True)
    @mock.patch('pyroute2.IPRoute.get_rules', create=True)
    @mock.patch('subprocess.check_output')
    def test_up_backend(self, mock_check_output, mock_get_rules,
                        mock_link_lookup, mock_get_links, mock_link, mock_addr,
                        mock_get_routes, mock_rule):
        iface = interface_file.InterfaceFile(
            name="eth1",
            if_type="backend",
            mtu=1450,
            addresses=[{
                consts.ADDRESS: '1.2.3.4',
                consts.PREFIXLEN: 24
            }],
            routes=[],
            rules=[],
            scripts={
                consts.IFACE_UP: [{
                    consts.COMMAND: "post-up eth1"
                }],
                consts.IFACE_DOWN: [{
                    consts.COMMAND: "post-down eth1"
                }],
            })

        idx = mock.MagicMock()
        mock_link_lookup.return_value = [idx]

        mock_get_links.return_value = [{
            consts.STATE: consts.IFACE_DOWN
        }]
        mock_get_rules.return_value = [{
            'src_len': 32,
            'attrs': {
                'FRA_SRC': '1.1.1.1',
                'FRA_TABLE': 20,
                'FRA_PROTOCOL': 0
            }
        }]

        controller = interface.InterfaceController()
        controller.up(iface)

        mock_link.assert_called_once_with(
            controller.SET,
            index=idx,
            state=consts.IFACE_UP,
            mtu=1450)

        mock_addr.assert_has_calls([
            mock.call(controller.ADD,
                      index=idx,
                      address='1.2.3.4',
                      prefixlen=24,
                      family=socket.AF_INET),
        ])

        mock_get_routes.assert_called_once_with(oif=idx)

        # for 'backend' iface, we don't update the rules
        mock_rule.assert_not_called()

        mock_check_output.assert_has_calls([
            mock.call(["post-up", "eth1"])
        ])

    @mock.patch('pyroute2.IPRoute.rule', create=True)
    @mock.patch('pyroute2.IPRoute.route', create=True)
    @mock.patch('pyroute2.IPRoute.addr', create=True)
    @mock.patch('pyroute2.IPRoute.link', create=True)
    @mock.patch('pyroute2.IPRoute.get_links', create=True)
    @mock.patch('pyroute2.IPRoute.get_rules', create=True)
    @mock.patch('pyroute2.IPRoute.get_routes', create=True)
    @mock.patch('pyroute2.IPRoute.get_addr', create=True)
    @mock.patch('pyroute2.IPRoute.link_lookup', create=True)
    @mock.patch('subprocess.check_output')
    @mock.patch('octavia.amphorae.backends.utils.interface.'
                'InterfaceController._wait_tentative')
    def test_up_update(self, mock_wait_tentative, mock_check_output,
                       mock_link_lookup, mock_get_addr, mock_get_routes,
                       mock_get_rules, mock_get_links, mock_link, mock_addr,
                       mock_route, mock_rule):
        iface = interface_file.InterfaceFile(
            name="eth1",
            if_type="vip",
            mtu=1450,
            addresses=[{
                consts.ADDRESS: '1.2.3.4',
                consts.PREFIXLEN: 24
            }, {
                consts.ADDRESS: '10.2.3.4',
                consts.PREFIXLEN: 16
            }, {
                consts.ADDRESS: '10.4.3.2',
                consts.PREFIXLEN: 16,
                consts.OCTAVIA_OWNED: False
            }, {
                consts.ADDRESS: '2001:db8::3',
                consts.PREFIXLEN: 64
            }],
            routes=[{
                consts.DST: '10.0.0.0/8',
                consts.GATEWAY: '1.0.0.1',
                consts.TABLE: 10,
                consts.ONLINK: True
            }, {
                consts.DST: '20.0.0.0/8',
                consts.GATEWAY: '1.0.0.2',
                consts.PREFSRC: '1.2.3.4',
                consts.SCOPE: 'link'
            }, {
                consts.DST: '2001:db8:2::1/128',
                consts.GATEWAY: '2001:db8::1'
            }],
            rules=[{
                consts.SRC: '1.1.1.1',
                consts.SRC_LEN: 32,
                consts.TABLE: 20,
            }, {
                consts.SRC: '2001:db8::1',
                consts.SRC_LEN: 128,
                consts.TABLE: 40,
            }],
            scripts={
                consts.IFACE_UP: [{
                    consts.COMMAND: "post-up eth1"
                }],
                consts.IFACE_DOWN: [{
                    consts.COMMAND: "post-down eth1"
                }],
            })

        idx = mock.MagicMock()
        mock_link_lookup.return_value = [idx]

        mock_get_links.return_value = [{
            consts.STATE: consts.IFACE_UP
        }]

        mock_get_addr.return_value = [{
            'prefixlen': 24,
            'attrs': {
                'IFA_ADDRESS': '2.0.0.1',
                'IFA_FLAGS': 0x80  # IFA_F_PERMANENT
            }
        }, {
            'prefixlen': 16,
            'attrs': {
                'IFA_ADDRESS': '10.2.3.4',
                'IFA_FLAGS': 0x80  # IFA_F_PERMANENT
            }
        }, {
            'prefixlen': 16,
            'attrs': {
                'IFA_ADDRESS': '10.2.3.5',
                'IFA_FLAGS': 0x0  # not IFA_F_PERMANENT
            }
        }]

        mock_get_routes.return_value = [{
            'dst_len': 16,
            'family': 2,
            'proto': 4,  # STATIC
            'attrs': {
                'RTA_DST': '24.24.0.0',
                'RTA_GATEWAY': '2.0.0.254',
                'RTA_PREFSRC': '2.0.0.1',
                'RTA_TABLE': 254
            }
        }, {
            'dst_len': 8,
            'family': 2,
            'proto': 4,  # STATIC
            'attrs': {
                'RTA_DST': '20.0.0.0',
                'RTA_GATEWAY': '1.0.0.2',
                'RTA_PREFSRC': '1.2.3.4',
                'RTA_TABLE': 254
            }
        }]

        mock_get_rules.return_value = [{
            'src_len': 32,
            'attrs': {
                'FRA_SRC': '1.1.1.1',
                'FRA_TABLE': 20,
                'FRA_PROTOCOL': 0
            }
        }, {
            'src_len': 32,
            'attrs': {
                'FRA_SRC': '2.2.2.2',
                'FRA_TABLE': 254,
                'FRA_PROTOCOL': 18  # Keepalived
            }
        }, {
            'src_len': 32,
            'attrs': {
                'FRA_SRC': '3.3.3.3',
                'FRA_TABLE': 254,
                'FRA_PROTOCOL': 0
            }
        }]

        controller = interface.InterfaceController()
        controller.up(iface)

        mock_link.assert_not_called()

        mock_addr.assert_has_calls([
            mock.call(controller.ADD,
                      index=idx,
                      address='1.2.3.4',
                      prefixlen=24,
                      family=socket.AF_INET),
            mock.call(controller.ADD,
                      index=idx,
                      address='2001:db8::3',
                      prefixlen=64,
                      family=socket.AF_INET6),
            mock.call(controller.DELETE,
                      index=idx,
                      address='2.0.0.1',
                      prefixlen=24,
                      family=socket.AF_INET)
        ])

        mock_route.assert_has_calls([
            mock.call(controller.ADD,
                      oif=idx,
                      dst='10.0.0.0/8',
                      gateway='1.0.0.1',
                      table=10,
                      onlink=True,
                      family=socket.AF_INET),
            mock.call(controller.ADD,
                      oif=idx,
                      dst='2001:db8:2::1/128',
                      gateway='2001:db8::1',
                      family=socket.AF_INET6),
            mock.call(controller.DELETE,
                      oif=idx,
                      dst='24.24.0.0/16',
                      gateway='2.0.0.254',
                      prefsrc='2.0.0.1',
                      table=254,
                      family=socket.AF_INET)])

        mock_rule.assert_has_calls([
            mock.call(controller.ADD,
                      src="2001:db8::1",
                      src_len=128,
                      table=40,
                      family=socket.AF_INET6),
            mock.call(controller.DELETE,
                      src='3.3.3.3',
                      src_len=32,
                      table=254,
                      family=socket.AF_INET)])

        mock_check_output.assert_has_calls([
            mock.call(["post-up", "eth1"])
        ])

    @mock.patch('pyroute2.IPRoute.rule', create=True)
    @mock.patch('pyroute2.IPRoute.route', create=True)
    @mock.patch('pyroute2.IPRoute.addr', create=True)
    @mock.patch('pyroute2.IPRoute.link', create=True)
    @mock.patch('pyroute2.IPRoute.get_links', create=True)
    @mock.patch('pyroute2.IPRoute.get_rules', create=True)
    @mock.patch('pyroute2.IPRoute.get_routes', create=True)
    @mock.patch('pyroute2.IPRoute.get_addr', create=True)
    @mock.patch('pyroute2.IPRoute.link_lookup', create=True)
    @mock.patch('subprocess.check_output')
    @mock.patch('octavia.amphorae.backends.utils.interface.'
                'InterfaceController._wait_tentative')
    def test_up_auto(self, mock_wait_tentative, mock_check_output,
                     mock_link_lookup, mock_get_addr, mock_get_routes,
                     mock_get_rules, mock_get_links, mock_link, mock_addr,
                     mock_route, mock_rule):
        iface = interface_file.InterfaceFile(
            name="eth1",
            if_type="vip",
            mtu=1450,
            addresses=[{
                consts.DHCP: True,
                consts.IPV6AUTO: True
            }],
            routes=[],
            rules=[],
            scripts={
                consts.IFACE_UP: [{
                    consts.COMMAND: "post-up eth1"
                }],
                consts.IFACE_DOWN: [{
                    consts.COMMAND: "post-down eth1"
                }],
            })

        idx = mock.MagicMock()
        mock_link_lookup.return_value = [idx]

        mock_get_links.return_value = [{
            consts.STATE: consts.IFACE_DOWN
        }]

        controller = interface.InterfaceController()
        controller.up(iface)

        mock_link.assert_called_once_with(
            controller.SET,
            index=idx,
            state=consts.IFACE_UP,
            mtu=1450)

        mock_addr.assert_not_called()
        mock_route.assert_not_called()
        mock_rule.assert_not_called()

        mock_check_output.assert_has_calls([
            mock.call(["/sbin/dhclient",
                       "-lf",
                       f"/var/lib/dhclient/dhclient-{iface.name}.leases",
                       "-pf",
                       f"/run/dhclient-{iface.name}.pid",
                       iface.name], stderr=subprocess.STDOUT),
            mock.call(["/sbin/sysctl", "-w",
                       f"net.ipv6.conf.{iface.name}.accept_ra=2"],
                      stderr=subprocess.STDOUT),
            mock.call(["/sbin/sysctl", "-w",
                       f"net.ipv6.conf.{iface.name}.autoconf=1"],
                      stderr=subprocess.STDOUT),
            mock.call(["post-up", iface.name])
        ])

    @mock.patch('pyroute2.IPRoute.rule', create=True)
    @mock.patch('pyroute2.IPRoute.route', create=True)
    @mock.patch('pyroute2.IPRoute.addr', create=True)
    @mock.patch('pyroute2.IPRoute.link', create=True)
    @mock.patch('pyroute2.IPRoute.get_links', create=True)
    @mock.patch('pyroute2.IPRoute.link_lookup', create=True)
    @mock.patch('subprocess.check_output')
    def test_down(self, mock_check_output, mock_link_lookup, mock_get_links,
                  mock_link, mock_addr, mock_route, mock_rule):
        iface = interface_file.InterfaceFile(
            name="eth1",
            if_type="vip",
            mtu=1450,
            addresses=[{
                consts.ADDRESS: '1.2.3.4',
                consts.PREFIXLEN: 24
            }, {
                consts.ADDRESS: '10.2.3.4',
                consts.PREFIXLEN: 16
            }, {
                consts.ADDRESS: '2001:db8::3',
                consts.PREFIXLEN: 64
            }],
            routes=[{
                consts.DST: '10.0.0.0/8',
                consts.GATEWAY: '1.0.0.1',
                consts.TABLE: 10,
                consts.ONLINK: True
            }, {
                consts.DST: '20.0.0.0/8',
                consts.GATEWAY: '1.0.0.2',
                consts.PREFSRC: '1.2.3.4',
                consts.SCOPE: 'link'
            }, {
                consts.DST: '2001:db8:2::1/128',
                consts.GATEWAY: '2001:db8::1'
            }],
            rules=[{
                consts.SRC: '1.1.1.1',
                consts.SRC_LEN: 32,
                consts.TABLE: 20,
            }, {
                consts.SRC: '2001:db8::1',
                consts.SRC_LEN: 128,
                consts.TABLE: 40,
            }],
            scripts={
                consts.IFACE_UP: [{
                    consts.COMMAND: "post-up eth1"
                }],
                consts.IFACE_DOWN: [{
                    consts.COMMAND: "post-down eth1"
                }],
            })

        idx = mock.MagicMock()
        mock_link_lookup.return_value = [idx]

        mock_get_links.return_value = [{
            consts.STATE: consts.IFACE_UP
        }]

        controller = interface.InterfaceController()
        controller.down(iface)

        mock_link.assert_called_once_with(
            controller.SET,
            index=idx,
            state=consts.IFACE_DOWN)

        mock_addr.assert_has_calls([
            mock.call(controller.DELETE,
                      index=idx,
                      address='1.2.3.4',
                      prefixlen=24,
                      family=socket.AF_INET),
            mock.call(controller.DELETE,
                      index=idx,
                      address='10.2.3.4',
                      prefixlen=16,
                      family=socket.AF_INET),
            mock.call(controller.DELETE,
                      index=idx,
                      address='2001:db8::3',
                      prefixlen=64,
                      family=socket.AF_INET6)
        ])

        mock_route.assert_has_calls([
            mock.call(controller.DELETE,
                      oif=idx,
                      dst='10.0.0.0/8',
                      gateway='1.0.0.1',
                      table=10,
                      onlink=True,
                      family=socket.AF_INET),
            mock.call(controller.DELETE,
                      oif=idx,
                      dst='20.0.0.0/8',
                      gateway='1.0.0.2',
                      prefsrc='1.2.3.4',
                      scope='link',
                      family=socket.AF_INET),
            mock.call(controller.DELETE,
                      oif=idx,
                      dst='2001:db8:2::1/128',
                      gateway='2001:db8::1',
                      family=socket.AF_INET6)])

        mock_rule.assert_has_calls([
            mock.call(controller.DELETE,
                      src="1.1.1.1",
                      src_len=32,
                      table=20,
                      family=socket.AF_INET),
            mock.call(controller.DELETE,
                      src="2001:db8::1",
                      src_len=128,
                      table=40,
                      family=socket.AF_INET6)])

        mock_check_output.assert_has_calls([
            mock.call(["post-down", "eth1"])
        ])

    @mock.patch('pyroute2.IPRoute.rule', create=True)
    @mock.patch('pyroute2.IPRoute.route', create=True)
    @mock.patch('pyroute2.IPRoute.addr', create=True)
    @mock.patch('pyroute2.IPRoute.flush_addr', create=True)
    @mock.patch('pyroute2.IPRoute.link', create=True)
    @mock.patch('pyroute2.IPRoute.get_links', create=True)
    @mock.patch('pyroute2.IPRoute.link_lookup', create=True)
    @mock.patch('subprocess.check_output')
    def test_down_with_errors(self, mock_check_output, mock_link_lookup,
                              mock_get_links, mock_link, mock_flush_addr,
                              mock_addr, mock_route, mock_rule):
        iface = interface_file.InterfaceFile(
            name="eth1",
            if_type="vip",
            mtu=1450,
            addresses=[{
                consts.ADDRESS: '1.2.3.4',
                consts.PREFIXLEN: 24
            }, {
                consts.ADDRESS: '10.2.3.4',
                consts.PREFIXLEN: 16
            }, {
                consts.ADDRESS: '2001:db8::3',
                consts.PREFIXLEN: 64
            }],
            routes=[{
                consts.DST: '10.0.0.0/8',
                consts.GATEWAY: '1.0.0.1',
                consts.TABLE: 10,
                consts.ONLINK: True
            }, {
                consts.DST: '20.0.0.0/8',
                consts.GATEWAY: '1.0.0.2',
                consts.PREFSRC: '1.2.3.4',
                consts.SCOPE: 'link'
            }, {
                consts.DST: '2001:db8:2::1/128',
                consts.GATEWAY: '2001:db8::1'
            }],
            rules=[{
                consts.SRC: '1.1.1.1',
                consts.SRC_LEN: 32,
                consts.TABLE: 20,
            }, {
                consts.SRC: '2001:db8::1',
                consts.SRC_LEN: 128,
                consts.TABLE: 40,
            }],
            scripts={
                consts.IFACE_UP: [{
                    consts.COMMAND: "post-up eth1"
                }],
                consts.IFACE_DOWN: [{
                    consts.COMMAND: "post-down eth1"
                }],
            })

        idx = mock.MagicMock()
        mock_link_lookup.return_value = [idx]

        mock_get_links.return_value = [{
            consts.STATE: consts.IFACE_UP
        }]
        mock_addr.side_effect = [
            pyroute2.NetlinkError(123),
            pyroute2.NetlinkError(123),
            pyroute2.NetlinkError(123),
        ]
        mock_flush_addr.side_effect = [
            pyroute2.NetlinkError(123)
        ]
        mock_route.side_effect = [
            pyroute2.NetlinkError(123),
            pyroute2.NetlinkError(123),
            pyroute2.NetlinkError(123)
        ]
        mock_rule.side_effect = [
            pyroute2.NetlinkError(123),
            pyroute2.NetlinkError(123),
        ]
        mock_check_output.side_effect = [
            Exception()
        ]

        controller = interface.InterfaceController()
        controller.down(iface)

        mock_link.assert_called_once_with(
            controller.SET,
            index=idx,
            state=consts.IFACE_DOWN)

        mock_addr.assert_has_calls([
            mock.call(controller.DELETE,
                      index=idx,
                      address='1.2.3.4',
                      prefixlen=24,
                      family=socket.AF_INET),
            mock.call(controller.DELETE,
                      index=idx,
                      address='10.2.3.4',
                      prefixlen=16,
                      family=socket.AF_INET),
            mock.call(controller.DELETE,
                      index=idx,
                      address='2001:db8::3',
                      prefixlen=64,
                      family=socket.AF_INET6)
        ])

        mock_flush_addr.assert_has_calls([
            mock.call(index=idx)
        ])

        mock_route.assert_has_calls([
            mock.call(controller.DELETE,
                      oif=idx,
                      dst='10.0.0.0/8',
                      gateway='1.0.0.1',
                      table=10,
                      onlink=True,
                      family=socket.AF_INET),
            mock.call(controller.DELETE,
                      oif=idx,
                      dst='20.0.0.0/8',
                      gateway='1.0.0.2',
                      prefsrc='1.2.3.4',
                      scope='link',
                      family=socket.AF_INET),
            mock.call(controller.DELETE,
                      oif=idx,
                      dst='2001:db8:2::1/128',
                      gateway='2001:db8::1',
                      family=socket.AF_INET6)])

        mock_rule.assert_has_calls([
            mock.call(controller.DELETE,
                      src="1.1.1.1",
                      src_len=32,
                      table=20,
                      family=socket.AF_INET),
            mock.call(controller.DELETE,
                      src="2001:db8::1",
                      src_len=128,
                      table=40,
                      family=socket.AF_INET6)])

        mock_check_output.assert_has_calls([
            mock.call(["post-down", "eth1"])
        ])

    @mock.patch('pyroute2.IPRoute.rule', create=True)
    @mock.patch('pyroute2.IPRoute.route', create=True)
    @mock.patch('pyroute2.IPRoute.addr', create=True)
    @mock.patch('pyroute2.IPRoute.link', create=True)
    @mock.patch('pyroute2.IPRoute.get_links', create=True)
    @mock.patch('pyroute2.IPRoute.link_lookup', create=True)
    @mock.patch('subprocess.check_output')
    def test_down_already_down(self, mock_check_output, mock_link_lookup,
                               mock_get_links, mock_link, mock_addr,
                               mock_route, mock_rule):
        iface = interface_file.InterfaceFile(
            name="eth1",
            if_type="vip",
            mtu=1450,
            addresses=[{
                consts.ADDRESS: '1.2.3.4',
                consts.PREFIXLEN: 24
            }, {
                consts.ADDRESS: '10.2.3.4',
                consts.PREFIXLEN: 16
            }, {
                consts.ADDRESS: '2001:db8::3',
                consts.PREFIXLEN: 64
            }],
            routes=[{
                consts.DST: '10.0.0.0/8',
                consts.GATEWAY: '1.0.0.1',
                consts.TABLE: 10,
                consts.ONLINK: True
            }, {
                consts.DST: '20.0.0.0/8',
                consts.GATEWAY: '1.0.0.2',
                consts.PREFSRC: '1.2.3.4',
                consts.SCOPE: 'link'
            }, {
                consts.DST: '2001:db8:2::1/128',
                consts.GATEWAY: '2001:db8::1'
            }],
            rules=[{
                consts.SRC: '1.1.1.1',
                consts.SRC_LEN: 32,
                consts.TABLE: 20,
            }, {
                consts.SRC: '2001:db8::1',
                consts.SRC_LEN: 128,
                consts.TABLE: 40,
            }],
            scripts={
                consts.IFACE_UP: [{
                    consts.COMMAND: "post-up eth1"
                }],
                consts.IFACE_DOWN: [{
                    consts.COMMAND: "post-down eth1"
                }],
            })

        idx = mock.MagicMock()
        mock_link_lookup.return_value = [idx]

        mock_get_links.return_value = [{
            consts.STATE: consts.IFACE_DOWN
        }]

        controller = interface.InterfaceController()
        controller.down(iface)

        mock_link.assert_not_called()
        mock_addr.assert_not_called()
        mock_route.assert_not_called()
        mock_rule.assert_not_called()
        mock_check_output.assert_not_called()

    @mock.patch('pyroute2.IPRoute.rule', create=True)
    @mock.patch('pyroute2.IPRoute.route', create=True)
    @mock.patch('pyroute2.IPRoute.addr', create=True)
    @mock.patch('pyroute2.IPRoute.flush_addr', create=True)
    @mock.patch('pyroute2.IPRoute.link', create=True)
    @mock.patch('pyroute2.IPRoute.get_links', create=True)
    @mock.patch('pyroute2.IPRoute.link_lookup', create=True)
    @mock.patch('subprocess.check_output')
    def test_down_auto(self, mock_check_output, mock_link_lookup,
                       mock_get_links, mock_link, mock_flush_addr,
                       mock_addr, mock_route, mock_rule):
        iface = interface_file.InterfaceFile(
            name="eth1",
            if_type="vip",
            mtu=1450,
            addresses=[{
                consts.DHCP: True,
                consts.IPV6AUTO: True
            }],
            routes=[],
            rules=[],
            scripts={
                consts.IFACE_UP: [{
                    consts.COMMAND: "post-up eth1"
                }],
                consts.IFACE_DOWN: [{
                    consts.COMMAND: "post-down eth1"
                }],
            })

        idx = mock.MagicMock()
        mock_link_lookup.return_value = [idx]

        mock_get_links.return_value = [{
            consts.STATE: consts.IFACE_UP
        }]

        controller = interface.InterfaceController()
        controller.down(iface)

        mock_link.assert_called_once_with(
            controller.SET,
            index=idx,
            state=consts.IFACE_DOWN)

        mock_addr.assert_not_called()
        mock_route.assert_not_called()
        mock_rule.assert_not_called()

        mock_flush_addr.assert_called_once()

        mock_check_output.assert_has_calls([
            mock.call(["/sbin/dhclient",
                       "-r",
                       "-lf",
                       f"/var/lib/dhclient/dhclient-{iface.name}.leases",
                       "-pf",
                       f"/run/dhclient-{iface.name}.pid",
                       iface.name], stderr=subprocess.STDOUT),
            mock.call(["/sbin/sysctl", "-w",
                       f"net.ipv6.conf.{iface.name}.accept_ra=0"],
                      stderr=subprocess.STDOUT),
            mock.call(["/sbin/sysctl", "-w",
                       f"net.ipv6.conf.{iface.name}.autoconf=0"],
                      stderr=subprocess.STDOUT),
            mock.call(["post-down", iface.name])
        ])

    @mock.patch("time.time")
    @mock.patch("time.sleep")
    def test__wait_tentative(self, mock_time_sleep, mock_time_time):
        mock_ipr = mock.MagicMock()
        mock_ipr.get_addr.side_effect = [
            ({'family': socket.AF_INET,
              'flags': 0},
             {'family': socket.AF_INET6,
              'flags': 0x40},  # tentative
             {'family': socket.AF_INET6,
              'flags': 0}),
            ({'family': socket.AF_INET,
              'flags': 0},
             {'family': socket.AF_INET6,
              'flags': 0},
             {'family': socket.AF_INET6,
              'flags': 0})
        ]

        mock_time_time.return_value = 0

        controller = interface.InterfaceController()
        idx = 4

        controller._wait_tentative(mock_ipr, idx)
        mock_time_sleep.assert_called_once()

    @mock.patch("time.time")
    @mock.patch("time.sleep")
    def test__wait_tentative_timeout(self, mock_time_sleep,
                                     mock_time_time):
        mock_ipr = mock.MagicMock()
        mock_ipr.get_addr.return_value = (
            {'family': socket.AF_INET6,
             'flags': 0x40},  # tentative
            {'family': socket.AF_INET6,
             'flags': 0}
        )

        mock_time_time.side_effect = [0, 0, 1, 2, 29, 30, 31]

        controller = interface.InterfaceController()
        idx = 4

        controller._wait_tentative(mock_ipr, idx)
        self.assertEqual(4, len(mock_time_sleep.mock_calls))

    def test__normalize_ip_address(self):
        controller = interface.InterfaceController()

        # Simple IPv4 address
        addr = controller._normalize_ip_address('192.168.0.1')
        self.assertEqual('192.168.0.1', addr)

        # Simple IPv6 address
        addr = controller._normalize_ip_address('2001::1')
        self.assertEqual('2001::1', addr)

        # Uncompressed IPv6 address
        addr = controller._normalize_ip_address(
            '2001:0000:0000:0000:0000:0000:0000:0001')
        self.assertEqual('2001::1', addr)

        addr = controller._normalize_ip_address(None)
        self.assertIsNone(addr)

    def test__normalize_ip_network(self):
        controller = interface.InterfaceController()

        # Simple IP address
        addr = controller._normalize_ip_network('192.168.0.1')
        self.assertEqual('192.168.0.1/32', addr)

        # "Normal" network
        addr = controller._normalize_ip_network('10.0.0.0/16')
        self.assertEqual('10.0.0.0/16', addr)

        # Network with hostbits set
        addr = controller._normalize_ip_network('10.0.0.10/16')
        self.assertEqual('10.0.0.0/16', addr)

        # IPv6 network with hostbits set
        addr = controller._normalize_ip_network('2001::1/64')
        self.assertEqual('2001::/64', addr)

        # Uncompressed IPv6 network
        addr = controller._normalize_ip_network(
            '2001:0000:0000:0000:0000:0000:0000:0001/64')
        self.assertEqual('2001::/64', addr)

        addr = controller._normalize_ip_network(None)
        self.assertIsNone(addr)
