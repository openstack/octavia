# Copyright 2015 Hewlett-Packard Development Company, L.P.
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
from oslo_utils import uuidutils

from octavia.common import constants
from octavia.common import data_models
from octavia.compute import compute_base as driver_base

LOG = logging.getLogger(__name__)


class NoopManager(object):
    def __init__(self):
        super(NoopManager, self).__init__()
        self.computeconfig = {}

    def build(self, name="amphora_name", amphora_flavor=None, image_id=None,
              key_name=None, sec_groups=None, network_ids=None,
              config_drive_files=None, user_data=None, port_ids=None):
        LOG.debug("Compute %s no-op, build name %s, amphora_flavor %s, "
                  "image_id %s, key_name %s, sec_groups %s, network_ids %s,"
                  "config_drive_files %s, user_data %s, port_ids %s",
                  self.__class__.__name__, name, amphora_flavor, image_id,
                  key_name, sec_groups, network_ids, config_drive_files,
                  user_data, port_ids)
        self.computeconfig[(name, amphora_flavor, image_id, key_name,
                            user_data)] = (
            name, amphora_flavor,
            image_id, key_name, sec_groups,
            network_ids, config_drive_files,
            user_data, port_ids, 'build')
        compute_id = uuidutils.generate_uuid()
        return compute_id

    def delete(self, amphora_id):
        LOG.debug("Compute %s no-op, amphora_id %s",
                  self.__class__.__name__, amphora_id)
        self.computeconfig[amphora_id] = (amphora_id, 'delete')

    def status(self, amphora_id):
        LOG.debug("Compute %s no-op, amphora_id %s",
                  self.__class__.__name__, amphora_id)
        self.computeconfig[amphora_id] = (amphora_id, 'status')
        return constants.UP

    def get_amphora(self, amphora_id):
        LOG.debug("Compute %s no-op, amphora_id %s",
                  self.__class__.__name__, amphora_id)
        self.computeconfig[amphora_id] = (amphora_id, 'get_amphora')
        return data_models.Amphora(
            compute_id=amphora_id,
            status=constants.ACTIVE,
            lb_network_ip='192.0.2.1'
        )


class NoopComputeDriver(driver_base.ComputeBase):
    def __init__(self, region=None):
        super(NoopComputeDriver, self).__init__()
        self.driver = NoopManager()

    def build(self, name="amphora_name", amphora_flavor=None, image_id=None,
              key_name=None, sec_groups=None, network_ids=None,
              config_drive_files=None, user_data=None, port_ids=None):

        compute_id = self.driver.build(name, amphora_flavor, image_id,
                                       key_name, sec_groups, network_ids,
                                       config_drive_files, user_data, port_ids)
        return compute_id

    def delete(self, amphora_id):
        self.driver.delete(amphora_id)

    def status(self, amphora_id):
        return self.driver.status(amphora_id)

    def get_amphora(self, amphora_id):
        return self.driver.get_amphora(amphora_id)
