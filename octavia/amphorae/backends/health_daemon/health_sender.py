#    Copyright 2014 Hewlett-Packard Development Company, L.P.
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

import socket
import struct

from oslo_config import cfg
from oslo_log import log as logging

from octavia.amphorae.backends.health_daemon import status_message
from octavia.common import constants

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def round_robin_addr(addrinfo_list):
    if not addrinfo_list:
        return None
    addrinfo = addrinfo_list.pop(0)
    addrinfo_list.append(addrinfo)
    return addrinfo


class BaseStatusSender:
    def __init__(self):
        self._update_dests()

    def update(self, dest, port):
        addrlist = socket.getaddrinfo(dest, port, 0, self.socket_type)
        # addrlist = [(family, socktype, proto, canonname, sockaddr) ...]
        # e.g. 4 = sockaddr - what we actually need
        for addr in addrlist:
            self.dests.append(addr)  # Just grab the first match
            break

    # The ip/port list configuration has mutated, reload it.
    def _update_dests(self):
        self.dests = []
        for ipport in CONF.health_manager.controller_ip_port_list:
            try:
                ip, port = ipport.rsplit(':', 1)
                if ip and ip[0] == '[' and ip[-1] == ']':
                    ip = ip[1:-1]
            except ValueError:
                LOG.error("Invalid ip and port '%s' in health_manager "
                          "controller_ip_port_list", ipport)
                break
            self.update(ip, port)
        self.current_controller_ip_port_list = (
            CONF.health_manager.controller_ip_port_list)

    def dosend(self, msg):
        # Check for controller_ip_port_list mutation
        if not (self.current_controller_ip_port_list ==
                CONF.health_manager.controller_ip_port_list):
            self._update_dests()
        dest = round_robin_addr(self.dests)
        if dest is None:
            LOG.error('No controller address found. Unable to send heartbeat.')
            return

        try:
            self._send_msg(dest, msg)
        except OSError:
            # Pass here as on amp boot it will get one or more
            # error: [Errno 101] Network is unreachable
            # while the networks are coming up
            # No harm in trying to send as it will still failover
            # if the message isn't received
            pass


class UDPStatusSender(BaseStatusSender):
    socket_type = socket.SOCK_DGRAM

    def __init__(self):
        super().__init__()
        self.v4sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.v6sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

    def _send_msg(self, dest, msg):
        # dest = (family, socktype, proto, canonname, sockaddr)
        # e.g. 0 = sock family, 4 = sockaddr - what we actually need
        if dest[0] == socket.AF_INET:
            self.v4sock.sendto(msg, dest[4])
        elif dest[0] == socket.AF_INET6:
            self.v6sock.sendto(msg, dest[4])


class TCPStatusSender(BaseStatusSender):
    socket_type = socket.SOCK_STREAM

    def _send_msg(self, dest, msg):
        with socket.socket(dest[0], socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            sock.connect(dest[4])

            # Add header to convey the length of the message
            header = struct.pack(">II", constants.AMP_HEARTBEAT_HEADER,
                                 len(msg) + 8)
            sock.sendall(header + msg)


class StatusSender:
    def __init__(self):
        self.udp_sender = UDPStatusSender()
        self.tcp_sender = TCPStatusSender()

    def dosend(self, obj):
        # Note: heartbeat_key is mutable and must be looked up for each call
        envelope_str = status_message.wrap_envelope(
            obj, str(CONF.health_manager.heartbeat_key))

        threshold = CONF.health_manager.heartbeat_use_tcp_threshold
        # threshold < 0 means: always UDP
        if 0 <= threshold <= len(envelope_str):
            self.tcp_sender.dosend(envelope_str)
        else:
            self.udp_sender.dosend(envelope_str)
