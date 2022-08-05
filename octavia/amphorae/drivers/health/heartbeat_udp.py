# Copyright 2014 Rackspace
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
import time

from oslo_config import cfg
from oslo_log import log as logging

from octavia.amphorae.backends.health_daemon import status_message
from octavia.amphorae.drivers.health import heartbeat_base
from octavia.common import exceptions

UDP_MAX_SIZE = 64 * 1024
CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class UDPStatusGetter(heartbeat_base.BaseStatusGetter):
    """This class defines methods that will gather heartbeats

    The heartbeats are transmitted via UDP and this class will bind to a port
    and absorb them
    """
    def __init__(self):
        super().__init__()
        self.key = cfg.CONF.health_manager.heartbeat_key
        self.ip = cfg.CONF.health_manager.bind_ip
        self.port = cfg.CONF.health_manager.bind_port
        self.sockaddr = None
        LOG.info('attempting to listen on %(ip)s port %(port)s',
                 {'ip': self.ip, 'port': self.port})
        self.sock = None
        self.update(self.key, self.ip, self.port)

    def update(self, key, ip, port):
        """Update the running config for the udp socket server

        :param key: The hmac key used to verify the UDP packets. String
        :param ip: The ip address the UDP server will read from
        :param port: The port the UDP server will read from
        :return: None
        """
        self.key = key
        for addrinfo in socket.getaddrinfo(ip, port, 0, socket.SOCK_DGRAM):
            ai_family = addrinfo[0]
            self.sockaddr = addrinfo[4]
            if self.sock is not None:
                self.sock.close()
            self.sock = socket.socket(ai_family, socket.SOCK_DGRAM)
            self.sock.settimeout(1)
            self.sock.bind(self.sockaddr)
            if cfg.CONF.health_manager.sock_rlimit > 0:
                rlimit = cfg.CONF.health_manager.sock_rlimit
                LOG.info("setting sock rlimit to %s", rlimit)
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF,
                                     rlimit)
            break  # just used the first addr getaddrinfo finds
        if self.sock is None:
            raise exceptions.NetworkConfig("unable to find suitable socket")

    def dorecv(self, *args, **kw):
        """Waits for a UDP heart beat to be sent.

        :return: Returns the unwrapped payload and addr that sent the
                 heartbeat.
        """
        (data, srcaddr) = self.sock.recvfrom(UDP_MAX_SIZE)
        LOG.debug('Received packet from %s', srcaddr)
        try:
            obj = status_message.unwrap_envelope(data, self.key)
        except Exception as e:
            LOG.warning('Health Manager experienced an exception processing a '
                        'heartbeat message from %s. Ignoring this packet. '
                        'Exception: %s', srcaddr, str(e))
            raise exceptions.InvalidHMACException()
        obj['recv_time'] = time.time()
        return obj, srcaddr[0]
