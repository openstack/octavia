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

from oslo_config import cfg

CONF = cfg.CONF


class LvsListenerApiServerBase(object, metaclass=abc.ABCMeta):
    """Base LVS Listener Server API

    """

    _SUBSCRIBED_AMP_COMPILE = []

    def get_subscribed_amp_compile_info(self):
        return self._SUBSCRIBED_AMP_COMPILE

    @abc.abstractmethod
    def upload_lvs_listener_config(self, listener_id):
        """Upload the configuration for LVS.

        :param listener_id: The id of a LVS Listener

        :returns: HTTP response with status code.
        :raises Exception: If any file / directory is not found or
                            fail to create.

        """

    @abc.abstractmethod
    def get_lvs_listener_config(self, listener_id):
        """Gets the LVS Listener configuration details

        :param listener_id: the id of the LVS Listener

        :returns: HTTP response with status code.
        :raises Exception: If the listener is failed to find.

        """

    @abc.abstractmethod
    def manage_lvs_listener(self, listener_id, action):
        """Gets the LVS Listener configuration details

        :param listener_id: the id of the LVS Listener
        :param action: the operation type.

        :returns: HTTP response with status code.
        :raises Exception: If the listener is failed to find.

        """

    @abc.abstractmethod
    def get_all_lvs_listeners_status(self):
        """Gets the status of all LVS Listeners

        This method will not consult the stats socket
        so a listener might show as ACTIVE but still be
        in ERROR

        :returns: a list of LVS Listener status
        :raises Exception: If the listener pid located directory is not exist

        """

    @abc.abstractmethod
    def delete_lvs_listener(self, listener_id):
        """Delete a LVS Listener from a amphora

        :param listener_id: The id of the listener

        :returns: HTTP response with status code.
        :raises Exception: If unsupport initial system of amphora.

        """
