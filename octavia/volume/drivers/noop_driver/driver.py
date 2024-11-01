# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_log import log as logging
from oslo_utils import uuidutils

from octavia.volume import volume_base as driver_base

LOG = logging.getLogger(__name__)


class NoopManager:
    def __init__(self):
        super().__init__()
        self.volumeconfig = {}

    def create_volume_from_image(self, image_id, availability_zone=None):
        LOG.debug("Volume %s no-op, image id %s, availability zone %s",
                  self.__class__.__name__, image_id, availability_zone)
        self.volumeconfig[image_id] = (image_id,
                                       availability_zone,
                                       'create_volume_from_image')
        volume_id = uuidutils.generate_uuid()
        return volume_id

    def delete_volume(self, volume_id):
        LOG.debug("Volume %s no-op, volume id %s",
                  self.__class__.__name__, volume_id)
        self.volumeconfig[volume_id] = (volume_id, 'delete')

    def get_image_from_volume(self, volume_id):
        LOG.debug("Volume %s no-op, volume id %s",
                  self.__class__.__name__, volume_id)
        self.volumeconfig[volume_id] = (volume_id, 'get_image_from_volume')
        image_id = uuidutils.generate_uuid()
        return image_id

    def validate_availability_zone(self, availability_zone):
        LOG.debug("Volume %s no-op, validate_availability_zone name %s",
                  self.__class__.__name__, availability_zone)
        self.volumeconfig[availability_zone] = (
            availability_zone, 'validate_availability_zone')


class NoopVolumeDriver(driver_base.VolumeBase):
    def __init__(self):
        super().__init__()
        self.driver = NoopManager()

    def create_volume_from_image(self, image_id, availability_zone=None):
        volume_id = self.driver.create_volume_from_image(
            image_id, availability_zone)
        return volume_id

    def delete_volume(self, volume_id):
        self.driver.delete_volume(volume_id)

    def get_image_from_volume(self, volume_id):
        image_id = self.driver.get_image_from_volume(volume_id)
        return image_id

    def validate_availability_zone(self, availability_zone):
        self.driver.validate_availability_zone(availability_zone)
