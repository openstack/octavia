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

from oslo_log import log as logging

from octavia.image import image_base as driver_base

LOG = logging.getLogger(__name__)


class NoopManager(object):
    def __init__(self):
        super().__init__()
        self.imageconfig = {}

    def get_image_id_by_tag(self, image_tag, image_owner=None):
        LOG.debug("Image %s no-op, get_image_id_by_tag image tag %s, "
                  "image owner %s",
                  self.__class__.__name__, image_tag, image_owner)
        self.imageconfig[image_tag, image_owner] = (
            image_tag, image_owner, 'get_image_id_by_tag')
        return 1


class NoopImageDriver(driver_base.ImageBase):
    def __init__(self):
        super().__init__()
        self.driver = NoopManager()

    def get_image_id_by_tag(self, image_tag, image_owner=None):
        image_id = self.driver.get_image_id_by_tag(image_tag, image_owner)
        return image_id
