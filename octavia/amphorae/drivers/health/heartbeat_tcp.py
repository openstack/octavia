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
import struct
import time

from oslo_config import cfg
from oslo_log import log as logging

from octavia.amphorae.backends.health_daemon import status_message
from octavia.amphorae.drivers.health import heartbeat_base
from octavia.common import constants
from octavia.common import exceptions

LOG = logging.getLogger(__name__)
TCP_LISTEN_BACKLOG = 10


class TCPStatusGetter(heartbeat_base.BaseStatusGetter):
    """This class defines methods that will gather heartbeats

    Heartbeats may be transmitted via TCP and this class will bind to a port,
    accept TCP connections and absorb the messages.
    """
    def __init__(self):
        super().__init__()
        self.key = cfg.CONF.health_manager.heartbeat_key
        self.ip = cfg.CONF.health_manager.bind_ip
        self.port = cfg.CONF.health_manager.bind_port
        self.sockaddr = None
        LOG.info('attempting to listen on %(ip)s TCP port %(port)s',
                 {'ip': self.ip, 'port': self.port})
        self.sock = None
        self.update(self.key, self.ip, self.port)

    def update(self, key, ip, port):
        """Update the running config for the TCP socket server

        :param key: The hmac key used to verify the TCP messages. String
        :param ip: The ip address the TCP server will listen on
        :param port: The port the TCP server will listen on
        :return: None
        """
        self.key = key
        for addrinfo in socket.getaddrinfo(ip, port, 0, socket.SOCK_STREAM):
            ai_family = addrinfo[0]
            self.sockaddr = addrinfo[4]
            if self.sock is not None:
                self.sock.close()
            self.sock = socket.socket(ai_family, socket.SOCK_STREAM)
            self.sock.settimeout(1)
            self.sock.bind(self.sockaddr)
            self.sock.listen(TCP_LISTEN_BACKLOG)
            break  # just used the first addr getaddrinfo finds
        if self.sock is None:
            raise exceptions.NetworkConfig(  # noqa: O342
                "unable to find suitable socket")

    def read_n(self, sock, n):
        data = b""
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if len(chunk) == 0:
                raise exceptions.HealthMessageIncomplete()
            data += chunk
        return data

    def read_header(self, sock):
        raw = self.read_n(sock, 8)
        magic, totallen = struct.unpack(">II", raw)
        if magic != constants.AMP_HEARTBEAT_HEADER:
            raise exceptions.HealthMessageBadHeader()
        if totallen > 0xFFFFFF:
            # as a safeguard: don't try to read insanely huge messages
            raise exceptions.HealthMessageBadHeader()
        if totallen < 9:
            raise exceptions.HealthMessageBadHeader()
        return totallen - 8

    def dorecv(self, *args, **kw):
        """Waits for a TCP heart beat to be sent.

        :return: Returns the unwrapped payload and addr that sent the
                 heartbeat.
        """
        (conn, srcaddr) = self.sock.accept()
        with conn:
            conn.settimeout(5)
            LOG.debug('Accepted connection from %s', srcaddr)

            msglen = self.read_header(conn)
            data = self.read_n(conn, msglen)
            LOG.debug('Received message from %s', srcaddr)
            try:
                obj = status_message.unwrap_envelope(data, self.key)
            except Exception as e:
                LOG.warning('Health Manager experienced an exception '
                            'processing a heartbeat message from %s. '
                            'Ignoring this message. Exception: %s',
                            srcaddr, str(e))
                raise exceptions.InvalidHMACException()
            obj['recv_time'] = time.time()
            return obj, srcaddr[0]
