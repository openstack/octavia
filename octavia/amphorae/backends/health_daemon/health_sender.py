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

# TODO(barclaac) Need to decide how this hooks into rest of system,
# e.g. daemon, subprocess, thread etc.

import socket

import config
import status_message


class UDPStatusSender:
    def __init__(self):
        self.cfg = config.JSONFileConfig()
        self.dests = {}
        self.update(self.cfg['destination'], self.cfg['port'])
        self.v4sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.v6sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.key = str(self.cfg['key'])
        self.cfg.add_observer(self.config_change)

    # TODO(barclaac) Still need to reread the address list if it gets changed
    def config_change(self):
        pass

    def update(self, dest_list, port):
        for dest in dest_list:
            addrlist = socket.getaddrinfo(dest, port, 0, socket.SOCK_DGRAM)
            # addrlist = [(family, socktype, proto, canonname, sockaddr) ...]
            # e.g. 4 = sockaddr - what we actually need
            for addr in addrlist:
                self.dests[addr[4]] = addr

    def dosend(self, envelope):
        envelope_str = status_message.encode(envelope, self.key)
        for dest in self.dests.itervalues():
            # addrlist = [(family, socktype, proto, canonname, sockaddr) ...]
            # e.g. 0 = sock family, 4 = sockaddr - what we actually need
            if dest[0] == socket.AF_INET:
                self.v4sock.sendto(envelope_str, dest[4])
            elif dest[0] == socket.AF_INET6:
                self.v6sock.sendto(envelope_str, dest[4])
