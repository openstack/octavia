# Copyright 2020 Red Hat, Inc. All rights reserved.
#
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

from oslo_config import cfg
from oslo_log import log as logging

from octavia.common import clients
from octavia.common import constants
from octavia.common import exceptions
from octavia.image import image_base

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class ImageManager(image_base.ImageBase):
    '''Image implementation of virtual machines via Glance.'''

    def __init__(self):
        super().__init__()
        # Must initialize glance api
        self._glance_client = clients.GlanceAuth.get_glance_client(
            service_name=CONF.glance.service_name,
            endpoint=CONF.glance.endpoint,
            region=CONF.glance.region_name,
            endpoint_type=CONF.glance.endpoint_type,
            insecure=CONF.glance.insecure,
            cacert=CONF.glance.ca_certificates_file
        )
        self.manager = self._glance_client.images

    def get_image_id_by_tag(self, image_tag, image_owner=None):
        """Get image ID by image tag and owner

        :param image_tag: image tag
        :param image_owner: optional image owner
        :raises: ImageGetException if no images found with given tag
        :return: image id
        """
        filters = {'tag': [image_tag],
                   'status': constants.GLANCE_IMAGE_ACTIVE}
        if image_owner:
            filters.update({'owner': image_owner})

        images = list(self.manager.list(
            filters=filters, sort='created_at:desc', limit=2))

        if not images:
            raise exceptions.ImageGetException(tag=image_tag)
        image_id = images[0]['id']
        num_images = len(images)
        if num_images > 1:
            LOG.warning("A single Glance image should be tagged with %(tag)s "
                        "tag, but at least two were found. Using "
                        "%(image_id)s.",
                        {'tag': image_tag, 'image_id': image_id})
        return image_id
