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

from oslo_config import cfg
from oslo_log import log as logging

from octavia.amphorae.backends.health_daemon import status_message
from octavia.i18n import _LE

CONF = cfg.CONF
CONF.import_group('health_manager', 'octavia.common.config')
LOG = logging.getLogger(__name__)


def round_robin_addr(addrinfo_list):
    if len(addrinfo_list) <= 0:
        return None
    addrinfo = addrinfo_list.pop(0)
    addrinfo_list.append(addrinfo)
    return addrinfo


class UDPStatusSender(object):
    def __init__(self):
        self.dests = []
        for ipport in CONF.health_manager.controller_ip_port_list:
            parts = ipport.split(':')
            self.update(parts[0], parts[1])
        self.v4sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.v6sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.key = str(CONF.health_manager.heartbeat_key)

    def update(self, dest, port):
        addrlist = socket.getaddrinfo(dest, port, 0, socket.SOCK_DGRAM)
        # addrlist = [(family, socktype, proto, canonname, sockaddr) ...]
        # e.g. 4 = sockaddr - what we actually need
        for addr in addrlist:
            self.dests.append(addr)  # Just grab the first match
            break

    def dosend(self, obj):
        envelope_str = status_message.wrap_envelope(obj, self.key)
        addrinfo = round_robin_addr(self.dests)
        # dest = (family, socktype, proto, canonname, sockaddr)
        # e.g. 0 = sock family, 4 = sockaddr - what we actually need
        if addrinfo is None:
            LOG.error(_LE('No controller address found. '
                          'Unable to send heartbeat.'))
            return
        try:
            if addrinfo[0] == socket.AF_INET:
                self.v4sock.sendto(envelope_str, addrinfo[4])
            elif addrinfo[0] == socket.AF_INET6:
                self.v6sock.sendto(envelope_str, addrinfo[4])
        except socket.error:
            # Pass here as on amp boot it will get one or more
            # error: [Errno 101] Network is unreachable
            # while the networks are coming up
            # No harm in trying to send as it will still failover
            # if the message isn't received
            pass
