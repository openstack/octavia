#    Copyright 2011-2014 OpenStack Foundation
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

import octavia.common.constants as constants


@six.add_metaclass(abc.ABCMeta)
class ComputeBase(object):

    @abc.abstractmethod
    def get_logger(self):
        """Return logger to be used

        :returns: the logger.
        """
        pass

    @abc.abstractmethod
    def build(self, amphora_type=constants.AMPHORA_VM, amphora_flavor=None,
              image_id=None, keys=None, sec_groups=None, network_ids=None):
        """Build a new amphora.

        :param amphora_type: The type of amphora to create (ex: VM)
        :param amphora_flavor: Optionally specify a flavor
        :param image_id: ID of the base image for the amphora instance
        :param keys: Optionally specify a list of ssh public keys
        :param sec_groups: Optionally specify list of security
        groups
        :param network_ids: A list of network IDs to attach to the amphora
        :returns: The id of the new instance.
        """
        pass

    @abc.abstractmethod
    def delete(self, amphora_id):
        """Delete the specified amphora

        :param amphora_id: The id of the amphora to delete
        """
        pass

    @abc.abstractmethod
    def status(self, amphora_id):
        """Check whether the specified amphora is up

        :param amphora_id: the ID of the desired amphora
        :returns: The nova "status" response ("ONLINE" or "OFFLINE")
        """
        pass

    @abc.abstractmethod
    def get_amphora(self, amphora_id):
        """Retrieve an amphora object

        :param amphora_id: the id of the desired amphora
        :returns: the amphora object
        """
        pass