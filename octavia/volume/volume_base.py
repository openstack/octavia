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

import six


@six.add_metaclass(abc.ABCMeta)
class VolumeBase(object):

    @abc.abstractmethod
    def create_volume_from_image(self, image_id):
        """Create volume for instance

        :param image_id: ID of amphora image

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
