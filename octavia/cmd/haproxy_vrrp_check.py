# Copyright 2015 Hewlett Packard Enterprise Development Company LP
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

import socket
import sys

SOCKET_TIMEOUT = 5


def get_status(sock_address):
    """Query haproxy stat socket

    Only VRRP fail over if the stats socket is not responding.

    :param sock_address: unix socket file
    :return: 0 if haproxy responded
    """
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(SOCKET_TIMEOUT)
    s.connect(sock_address)
    s.send(b'show stat -1 -1 -1\n')
    data = b''
    while True:
        x = s.recv(1024)
        if not x:
            break
        data += x
    s.close()
    # if get nothing, means has no response
    if len(data) == 0:
        return 1
    return 0


def health_check(sock_addresses):
    """Invoke queries for all defined listeners

    :param sock_addresses:
    :return:
    """
    status = 0
    for address in sock_addresses:
        status += get_status(address)
    return status


def main():
    # usage python haproxy_vrrp_check.py <list_of_stat_sockets>
    # Note: for performance, this script loads minimal number of module.
    # Loading octavia modules or any other complex construct MUST be avoided.
    listeners_sockets = sys.argv[1:]
    try:
        status = health_check(listeners_sockets)
    except Exception:
        sys.exit(1)
    sys.exit(status)
