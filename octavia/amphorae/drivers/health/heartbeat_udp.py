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

from concurrent import futures
from oslo_config import cfg
from oslo_log import log as logging

from octavia.amphorae.backends.health_daemon import status_message
from octavia.common import exceptions
from octavia.db import repositories
from octavia.i18n import _LI


UDP_MAX_SIZE = 64 * 1024
LOG = logging.getLogger(__name__)


class UDPStatusGetter(object):
    """This class defines methods that will gather heatbeats

    The heartbeats are transmitted via UDP and this class will bind to a port
    and absorb them
    """
    def __init__(self, health_update, stats_update):
        self.stats_update = stats_update
        self.health_update = health_update
        self.key = cfg.CONF.health_manager.heartbeat_key
        self.ip = cfg.CONF.health_manager.bind_ip
        self.port = cfg.CONF.health_manager.bind_port
        self.sockaddr = None
        LOG.info(_LI(
            'attempting to listen on {0} port {1}').format(
                self.ip, self.port))
        self.sock = None
        self.update(self.key, self.ip, self.port)

        self.executor = futures.ThreadPoolExecutor(
            max_workers=cfg.CONF.health_manager.status_update_threads)
        self.repo = repositories.Repositories().amphorahealth

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
            self.sock.bind((ip, port))
            if cfg.CONF.health_manager.sock_rlimit > 0:
                rlimit = cfg.CONF.health_manager.sock_rlimit
                LOG.info(_LI("setting sock rlimit to {0}").format(rlimit))
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF,
                                     rlimit)
            break  # just used the first addr getaddrinfo finds
        if self.sock is None:
            raise exceptions.NetworkConfig("unable to find suitable socket")

    def dorecv(self, *args, **kw):
        """Waits for a UDP heart beat to be sent.

        :return: Returns the unwrapped payload and addr that sent the \
                 heart beat. The format of the obj from the UDP sender is of
                 the form. Not that listener_1 has not pools and listener_4
                 has no nodes.

        {"listeners": {
        "listener_uuid_1": {
            "pools": {},
            "status": "OPEN",
            "stats": {
                "conns": 0,
                "rx": 0,
                "tx": 0
            }
        },
        "listener_uuid_2": {
            "pools": {
                "pool_uuid_1": {
                    "members": [
                        {
                            "member_uuid_1": "DOWN"
                        },
                        {
                            "member_uuid_2": "DOWN"
                        },
                        {
                            "member_uuid_3": "DOWN"
                        },
                        {
                            "member_uuid_4": "DOWN"
                        }
                    ]
                }
            },
            "status": "OPEN",
            "stats": {
                "conns": 0,
                "rx": 0,
                "tx": 0
            }
        },
        "listener_uuid_3": {
            "pools": {
                "pool_uuid_2": {
                    "members": [
                        {
                            "member_uuid_5": "DOWN"
                        },
                        {
                            "member_uuid_6": "DOWN"
                        },
                        {
                            "member_uuid_7": "DOWN"
                        },
                        {
                            "member_uuid_8": "DOWN"
                        }
                    ]
                }
            },
            "status": "OPEN",
            "stats": {
                "conns": 0,
                "rx": 0,
                "tx": 0
            }
        },
        "listener_uuid_4": {
            "pools": {
                "pool_uuid_3": {
                    "members": []
                }
            },
            "status": "OPEN",
            "stats": {
                "conns": 0,
                "rx": 0,
                "tx": 0
            }
        }
    },
    "id": "amphora_uuid",
    "seq": 1033
}

        """
        (data, srcaddr) = self.sock.recvfrom(UDP_MAX_SIZE)
        obj = status_message.unwrap_envelope(data, self.key)
        return obj, srcaddr

    def check(self):
        try:
            (obj, srcaddr) = self.dorecv()
            if self.health_update:
                self.executor.submit(self.health_update.update_health, obj)
            if self.stats_update:
                self.executor.submit(self.stats_update.update_stats, obj)
        except exceptions.InvalidHMACException:
            # Pass here as the packet was dropped and logged already
            pass
