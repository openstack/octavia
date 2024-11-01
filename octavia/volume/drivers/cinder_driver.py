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

import time

from cinderclient import exceptions as cinder_exceptions
from oslo_config import cfg
from oslo_log import log as logging
from tenacity import retry
from tenacity import stop_after_attempt

from octavia.common import clients
from octavia.common import constants
from octavia.common import exceptions
from octavia.volume import volume_base

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class VolumeManager(volume_base.VolumeBase):
    '''Volume implementation of virtual machines via cinder.'''

    def __init__(self):
        super().__init__()
        # Must initialize cinder api
        self._cinder_client = clients.CinderAuth.get_cinder_client(
            service_name=CONF.cinder.service_name,
            endpoint=CONF.cinder.endpoint,
            region=CONF.cinder.region_name,
            endpoint_type=CONF.cinder.endpoint_type,
            insecure=CONF.cinder.insecure,
            cacert=CONF.cinder.ca_certificates_file
        )
        self.manager = self._cinder_client.volumes
        self.availability_zone_manager = self._cinder_client.availability_zones

    @retry(reraise=True,
           stop=stop_after_attempt(CONF.cinder.volume_create_max_retries))
    def create_volume_from_image(self, image_id, availability_zone=None):
        """Create cinder volume

        :param image_id: ID of amphora image
        :param availability_zone: Availability zone data dict

        :return volume id
        """

        if availability_zone:
            az_name = availability_zone.get(
                constants.VOLUME_ZONE, CONF.cinder.availability_zone)
        else:
            az_name = CONF.cinder.availability_zone

        volume = self.manager.create(
            size=CONF.cinder.volume_size,
            volume_type=CONF.cinder.volume_type,
            availability_zone=az_name,
            imageRef=image_id)
        resource_status = self.manager.get(volume.id).status

        status = constants.CINDER_STATUS_AVAILABLE
        start = int(time.time())

        while resource_status != status:
            time.sleep(CONF.cinder.volume_create_retry_interval)
            instance_volume = self.manager.get(volume.id)
            resource_status = instance_volume.status
            if resource_status == constants.CINDER_STATUS_ERROR:
                LOG.error('Error creating %s', instance_volume.id)
                instance_volume.delete()
                raise cinder_exceptions.ResourceInErrorState(
                    obj=volume, fault_msg='Cannot create volume')
            if int(time.time()) - start >= CONF.cinder.volume_create_timeout:
                LOG.error('Timed out waiting to create cinder volume %s',
                          instance_volume.id)
                instance_volume.delete()
                raise cinder_exceptions.TimeoutException(
                    obj=volume, action=constants.CINDER_ACTION_CREATE_VOLUME)
        return volume.id

    def delete_volume(self, volume_id):
        """Get glance image from volume

        :param volume_id: ID of amphora boot volume

        :return image id
        """
        LOG.debug('Deleting cinder volume %s', volume_id)
        try:
            instance_volume = self.manager.get(volume_id)
            try:
                instance_volume.delete()
                LOG.debug("Deleted volume %s", volume_id)
            except Exception as e:
                LOG.exception("Error deleting cinder volume %s",
                              volume_id)
                raise exceptions.VolumeDeleteException() from e
        except cinder_exceptions.NotFound:
            LOG.warning("Volume %s not found: assuming already deleted",
                        volume_id)

    def get_image_from_volume(self, volume_id):
        """Get glance image from volume

        :param volume_id: ID of amphora boot volume

        :return image id
        """
        image_id = None
        LOG.debug('Get glance image for volume %s', volume_id)
        try:
            instance_volume = self.manager.get(volume_id)
        except cinder_exceptions.NotFound as e:
            LOG.exception("Volume %s not found", volume_id)
            raise exceptions.VolumeGetException() from e
        if hasattr(instance_volume, 'volume_image_metadata'):
            image_id = instance_volume.volume_image_metadata.get("image_id")
        else:
            LOG.error("Volume %s has no image metadata", volume_id)
            image_id = None
        return image_id

    def validate_availability_zone(self, availability_zone):
        """Validates that an availability zone exists in cinder.

        :param availability_zone: Name of the availability zone to lookup.
        :raises: NotFound
        :returns: None
        """
        try:
            volume_zones = [
                a.zoneName for a in self.availability_zone_manager.list(
                    detailed=False)]
            if availability_zone not in volume_zones:
                LOG.info('Availability zone %s was not found in cinder. %s',
                         availability_zone, volume_zones)
                raise exceptions.InvalidSubresource(
                    resource='Cinder availability zone', id=availability_zone)
        except Exception as e:
            LOG.exception('Cinder reports a failure getting listing '
                          'availability zones: %s', str(e))
            raise
