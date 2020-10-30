# Copyright 2021 Red Hat, Inc. All rights reserved.
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
from unittest import mock

from octavia.amphorae.backends.utils import interface_file
from octavia.cmd import interface
from octavia.tests.unit import base


class TestInterfaceCMD(base.TestCase):

    def setUp(self):
        super().setUp()

        self.interface1 = interface_file.InterfaceFile("eth1")
        self.interface2 = interface_file.InterfaceFile("eth2")

    def test_interfaces_find(self):
        controller = mock.Mock()
        controller.list = mock.Mock()
        controller.list.return_value = {
            "eth1": self.interface1,
            "eth2": self.interface2
        }

        ret = interface.interfaces_find(controller, "eth2")
        self.assertCountEqual([self.interface2], ret)
        controller.list.assert_called_once()

    def test_interfaces_find_all(self):
        controller = mock.Mock()
        controller.list = mock.Mock()
        controller.list.return_value = {
            "eth1": self.interface1,
            "eth2": self.interface2
        }

        ret = interface.interfaces_find(controller, "all")
        self.assertCountEqual([self.interface1, self.interface2], ret)
        controller.list.assert_called_once()

    def test_interfaces_find_all_empty(self):
        controller = mock.Mock()
        controller.list = mock.Mock()
        controller.list.return_value = {}

        ret = interface.interfaces_find(controller, "all")
        self.assertEqual(0, len(ret))
        controller.list.assert_called_once()

    def test_interfaces_find_not_found(self):
        controller = mock.Mock()
        controller.list = mock.Mock()
        controller.list.return_value = {
            "eth1": self.interface1,
            "eth2": self.interface2
        }

        self.assertRaisesRegex(
            interface.InterfaceException,
            "Could not find interface 'eth3'.",
            interface.interfaces_find,
            controller, "eth3")
        controller.list.assert_called_once()

    def test_interfaces_update(self):
        action_fn = mock.Mock()
        action_str = mock.Mock()
        interfaces = [self.interface1, self.interface2]

        interface.interfaces_update(interfaces, action_fn, action_str)
        self.assertEqual(2, len(action_fn.mock_calls))
        action_fn.assert_called_with(self.interface2)

    def test_interfaces_update_with_errors(self):
        action_fn = mock.Mock()
        action_str = mock.Mock()
        interfaces = [self.interface1, self.interface2]
        action_fn.side_effect = [None, Exception("error msg")]

        self.assertRaisesRegex(
            interface.InterfaceException,
            "Could not configure interface:.*eth2.*error msg",
            interface.interfaces_update,
            interfaces, action_fn, action_str)
        self.assertEqual(2, len(action_fn.mock_calls))

    @mock.patch("octavia.amphorae.backends.utils.interface."
                "InterfaceController")
    @mock.patch("octavia.cmd.interface.interfaces_find")
    @mock.patch("octavia.cmd.interface.interfaces_update")
    def test_interface_cmd(self, mock_interfaces_update,
                           mock_interfaces_find, mock_controller):
        controller = mock.Mock()
        controller.up = mock.Mock()
        controller.down = mock.Mock()
        mock_controller.return_value = controller
        mock_interfaces_find.return_value = [self.interface1]

        interface.interface_cmd("eth1", "up")

        mock_interfaces_find.assert_called_once_with(
            controller, "eth1")
        mock_interfaces_update.assert_called_once_with(
            [self.interface1], mock_controller.return_value.up, "up")

        mock_interfaces_find.reset_mock()
        mock_interfaces_update.reset_mock()

        mock_interfaces_find.return_value = [self.interface2]

        interface.interface_cmd("eth2", "down")

        mock_interfaces_find.assert_called_once_with(
            controller, "eth2")
        mock_interfaces_update.assert_called_once_with(
            [self.interface2], mock_controller.return_value.down, "down")

    @mock.patch("octavia.amphorae.backends.utils.interface."
                "InterfaceController")
    def test_interface_cmd_invalid_action(self, mock_controller):
        self.assertRaisesRegex(
            interface.InterfaceException,
            "Unknown action.*invalidaction",
            interface.interface_cmd,
            "eth1", "invalidaction")
