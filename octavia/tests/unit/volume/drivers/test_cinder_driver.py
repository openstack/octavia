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

from cinderclient import exceptions as cinder_exceptions
import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.common import exceptions
import octavia.tests.unit.base as base
import octavia.volume.drivers.cinder_driver as cinder_common


CONF = cfg.CONF


class TestCinderClient(base.TestCase):

    def setUp(self):
        fake_uuid1 = uuidutils.generate_uuid()
        fake_uuid2 = uuidutils.generate_uuid()
        fake_uuid3 = uuidutils.generate_uuid()

        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf = conf

        self.manager = cinder_common.VolumeManager()
        self.manager.manager = mock.MagicMock()

        self.cinder_response = mock.Mock()
        self.cinder_response.id = fake_uuid1

        self.manager.manager.get.return_value.status = 'available'
        self.manager.manager.create.return_value = self.cinder_response
        self.image_id = fake_uuid2
        self.volume_id = fake_uuid3

        super(TestCinderClient, self).setUp()

    def test_create_volume_from_image(self):
        self.conf.config(group="controller_worker",
                         volume_driver='volume_cinder_driver')
        self.conf.config(group="cinder", volume_create_retry_interval=0)
        self.manager.create_volume_from_image(self.image_id)
        self.manager.manager.create.assert_called_with(
            size=16,
            volume_type=None,
            availability_zone=None,
            imageRef=self.image_id)

    def test_create_volume_from_image_error(self):
        self.conf.config(group="controller_worker",
                         volume_driver='volume_cinder_driver')
        self.conf.config(group="cinder", volume_create_retry_interval=0)
        self.manager.manager.get.return_value.status = 'error'
        self.assertRaises(cinder_exceptions.ResourceInErrorState,
                          self.manager.create_volume_from_image,
                          self.image_id)

    def test_build_cinder_volume_timeout(self):
        self.conf.config(group="controller_worker",
                         volume_driver='volume_cinder_driver')
        self.conf.config(group="cinder", volume_create_timeout=0)
        self.conf.config(group="cinder", volume_create_retry_interval=0)
        self.manager.manager.get.return_value.status = 'build'
        self.manager.create_volume_from_image.retry.sleep = mock.Mock()
        self.assertRaises(cinder_exceptions.TimeoutException,
                          self.manager.create_volume_from_image,
                          self.image_id)

    def test_get_image_from_volume(self):
        self.conf.config(group="controller_worker",
                         volume_driver='volume_cinder_driver')
        self.conf.config(group="cinder",
                         volume_create_retry_interval=0)
        self.manager.get_image_from_volume(self.volume_id)
        self.manager.manager.get.assert_called_with(
            self.volume_id)

    def test_get_image_from_volume_error(self):
        self.conf.config(group="controller_worker",
                         volume_driver='volume_cinder_driver')
        self.conf.config(group="cinder",
                         volume_create_retry_interval=0)
        self.manager.manager.get.side_effect = [
            exceptions.VolumeGetException('test_exception')]
        self.assertRaises(exceptions.VolumeGetException,
                          self.manager.get_image_from_volume,
                          self.volume_id)
