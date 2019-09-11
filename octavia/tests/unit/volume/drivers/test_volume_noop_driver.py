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

from oslo_config import cfg
from oslo_utils import uuidutils

import octavia.tests.unit.base as base
from octavia.volume.drivers.noop_driver import driver


CONF = cfg.CONF


class TestNoopVolumeDriver(base.TestCase):
    FAKE_UUID_1 = uuidutils.generate_uuid()
    FAKE_UUID_2 = uuidutils.generate_uuid()

    def setUp(self):
        super(TestNoopVolumeDriver, self).setUp()
        self.driver = driver.NoopVolumeDriver()

        self.image_id = self.FAKE_UUID_1
        self.volume_id = self.FAKE_UUID_2

    def test_create_volume_from_image(self):
        self.driver.create_volume_from_image(self.image_id)
        self.assertEqual((self.image_id, 'create_volume_from_image'),
                         self.driver.driver.volumeconfig[(
                             self.image_id
                         )])

    def test_get_image_from_volume(self):
        self.driver.get_image_from_volume(self.volume_id)
        self.assertEqual((self.volume_id, 'get_image_from_volume'),
                         self.driver.driver.volumeconfig[(
                             self.volume_id
                         )])
