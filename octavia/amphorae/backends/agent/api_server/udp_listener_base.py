#    Copyright 2018 OpenStack Foundation
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


import abc

import six

from oslo_config import cfg
from stevedore import driver as stevedore_driver

CONF = cfg.CONF
UDP_SERVER_NAMESPACE = 'octavia.amphora.udp_api_server'


@six.add_metaclass(abc.ABCMeta)
class UdpListenerApiServerBase(object):
    """Base UDP Listener Server API

    """

    _SUBSCRIBED_AMP_COMPILE = []
    SERVER_INSTANCE = None

    @classmethod
    def get_server_driver(cls):
        if not cls.SERVER_INSTANCE:
            cls.SERVER_INSTANCE = stevedore_driver.DriverManager(
                namespace=UDP_SERVER_NAMESPACE,
                name=CONF.amphora_agent.amphora_udp_driver,
                invoke_on_load=True,
            ).driver
        return cls.SERVER_INSTANCE

    def get_subscribed_amp_compile_info(self):
        return self._SUBSCRIBED_AMP_COMPILE

    @abc.abstractmethod
    def upload_udp_listener_config(self, listener_id):
        """Upload the configuration for UDP.

        :param listener_id: The id of a UDP Listener

        :returns: HTTP response with status code.
        :raises Exception: If any file / directory is not found or
                            fail to create.

        """
        pass

    @abc.abstractmethod
    def get_udp_listener_config(self, listener_id):
        """Gets the UDP Listener configuration details

        :param listener_id: the id of the UDP Listener

        :returns: HTTP response with status code.
        :raises Exception: If the listener is failed to find.

        """
        pass

    @abc.abstractmethod
    def manage_udp_listener(self, listener_id, action):
        """Gets the UDP Listener configuration details

        :param listener_id: the id of the UDP Listener
        :param action: the operation type.

        :returns: HTTP response with status code.
        :raises Exception: If the listener is failed to find.

        """
        pass

    @abc.abstractmethod
    def get_all_udp_listeners_status(self):
        """Gets the status of all UDP Listeners

        This method will not consult the stats socket
        so a listener might show as ACTIVE but still be
        in ERROR

        :returns: a list of UDP Listener status
        :raises Exception: If the listener pid located directory is not exist

        """
        pass

    @abc.abstractmethod
    def get_udp_listener_status(self, listener_id):
        """Gets the status of a UDP listener

        :param listener_id: The id of the listener

        :returns: HTTP response with status code.
        :raises Exception: If the listener is failed to find.

        """
        pass

    @abc.abstractmethod
    def delete_udp_listener(self, listener_id):
        """Delete a UDP Listener from a amphora

        :param listener_id: The id of the listener

        :returns: HTTP response with status code.
        :raises Exception: If unsupport initial system of amphora.

        """
        pass
