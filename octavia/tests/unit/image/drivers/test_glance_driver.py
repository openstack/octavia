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

from unittest import mock

from oslo_utils import uuidutils

from octavia.common import exceptions
import octavia.image.drivers.glance_driver as glance_common
import octavia.tests.unit.base as base


class TestGlanceClient(base.TestCase):

    def setUp(self):
        self.manager = glance_common.ImageManager()
        self.manager.manager = mock.MagicMock()

        super(TestGlanceClient, self).setUp()

    def test_no_images(self):
        self.manager.manager.list.return_value = []
        self.assertRaises(
            exceptions.ImageGetException,
            self.manager.get_image_id_by_tag, 'faketag')

    def test_single_image(self):
        images = [
            {'id': uuidutils.generate_uuid(), 'tag': 'faketag'}
        ]
        self.manager.manager.list.return_value = images
        image_id = self.manager.get_image_id_by_tag('faketag', None)
        self.assertEqual(image_id, images[0]['id'])

    def test_single_image_owner(self):
        owner = uuidutils.generate_uuid()
        images = [
            {'id': uuidutils.generate_uuid(),
             'tag': 'faketag',
             'owner': owner}
        ]
        self.manager.manager.list.return_value = images
        image_id = self.manager.get_image_id_by_tag('faketag', owner)
        self.assertEqual(image_id, images[0]['id'])
        self.assertEqual(owner, images[0]['owner'])

    def test_multiple_images_returns_one_of_images(self):
        images = [
            {'id': image_id, 'tag': 'faketag'}
            for image_id in [uuidutils.generate_uuid() for i in range(10)]
        ]
        self.manager.manager.list.return_value = images
        image_id = self.manager.get_image_id_by_tag('faketag', None)
        self.assertIn(image_id, [image['id'] for image in images])
