#    Copyright 2011-2019 OpenStack Foundation
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


class VolumeBase(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def create_volume_from_image(self, image_id, availability_zone=None):
        """Create volume for instance

        :param image_id: ID of amphora image
        :param availability_zone: Availability zone data dict

        :return volume id
        """

    @abc.abstractmethod
    def delete_volume(self, volume_id):
        """Delete volume

        :param volume_id: ID of amphora volume
        """

    @abc.abstractmethod
    def get_image_from_volume(self, volume_id):
        """Get cinder volume

        :param volume_id: ID of amphora volume

        :return image id
        """

    @abc.abstractmethod
    def validate_availability_zone(self, availability_zone):
        """Validates that a volume availability zone exists.

        :param availability_zone: Name of the availability zone to lookup.
        :returns: None
        :raises: NotFound
        :raises: NotImplementedError
        """
