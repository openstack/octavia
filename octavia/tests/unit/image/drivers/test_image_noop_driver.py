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
from oslo_utils import uuidutils

from octavia.image.drivers.noop_driver import driver
import octavia.tests.unit.base as base


CONF = cfg.CONF


class TestNoopImageDriver(base.TestCase):

    def setUp(self):
        super(TestNoopImageDriver, self).setUp()
        self.driver = driver.NoopImageDriver()

    def test_get_image_id_by_tag(self):
        image_tag = 'amphora'
        image_owner = uuidutils.generate_uuid()
        image_id = self.driver.get_image_id_by_tag(image_tag, image_owner)
        self.assertEqual((image_tag, image_owner, 'get_image_id_by_tag'),
                         self.driver.driver.imageconfig[(
                             image_tag, image_owner
                         )])
        self.assertEqual(1, image_id)
