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

import sys

from oslo_config import cfg

from octavia.amphorae.backends.utils import interface
from octavia.common import config
from octavia.common import exceptions


class InterfaceException(exceptions.OctaviaException):
    message = "Could not configure interface: %(msg)s"


def interfaces_find(interface_controller, name):
    all_interfaces = interface_controller.list()

    if name == "all":
        return all_interfaces.values()

    if name in all_interfaces:
        return [all_interfaces[name]]

    msg = "Could not find interface '{}'.".format(name)
    raise InterfaceException(msg=msg)


def interfaces_update(interfaces, action_fn, action_str):
    errors = []

    for iface in interfaces:
        try:
            action_fn(iface)
        except Exception as e:
            errors.append("Error on action '{}' for interface {}: {}.".format(
                action_str, iface.name, e))

    if errors:
        raise InterfaceException(msg=", ".join(errors))


def interface_cmd(interface_name, action):
    interface_controller = interface.InterfaceController()

    if action == "up":
        action_fn = interface_controller.up
    elif action == "down":
        action_fn = interface_controller.down
    else:
        raise InterfaceException(
            msg="Unknown action '{}'".format(action))

    interfaces = interfaces_find(interface_controller,
                                 interface_name)
    interfaces_update(interfaces, action_fn, action)


def main():
    config.init(sys.argv[1:-2])
    config.setup_logging(cfg.CONF)

    try:
        action = sys.argv[-2]
        interface_name = sys.argv[-1]
    except IndexError:
        print("usage: {} [up|down] <interface>".format(sys.argv[0]))
        sys.exit(1)

    try:
        interface_cmd(interface_name, action)
    except Exception as e:
        print("Error: {}".format(e))
        sys.exit(2)


if __name__ == "__main__":
    main()
