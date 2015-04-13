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

from octavia.compute import compute_base as driver_base

LOG = logging.getLogger(__name__)


class NoopManager(object):
    def __init__(self):
        super(NoopManager, self).__init__()
        self.computeconfig = {}

    def build(self, name="amphora_name", amphora_flavor=None, image_id=None,
              key_name=None, sec_groups=None, network_ids=None,
              config_drive_files=None, user_data=None):
        LOG.debug("Compute %s no-op, build name %s, amphora_flavor %s, "
                  "image_id %s, key_name %s, sec_groups %s, network_ids %s,"
                  "config_drive_files %s, user_data %s",
                  self.__class__.__name__, name, amphora_flavor, image_id,
                  key_name, sec_groups, network_ids, config_drive_files,
                  user_data)
        self.computeconfig[(name, amphora_flavor, image_id, key_name,
                            sec_groups, network_ids, config_drive_files,
                            user_data)] = (name, amphora_flavor,
                                           image_id, key_name, sec_groups,
                                           network_ids, config_drive_files,
                                           user_data, 'build')

    def delete(self, amphora_id):
        LOG.debug("Compute %s no-op, amphora_id %s",
                  self.__class__.__name__, amphora_id)
        self.computeconfig[amphora_id] = (amphora_id, 'delete')

    def status(self, amphora_id):
        LOG.debug("Compute %s no-op, amphora_id %s",
                  self.__class__.__name__, amphora_id)
        self.computeconfig[amphora_id] = (amphora_id, 'status')

    def get_amphora(self, amphora_id):
        LOG.debug("Compute %s no-op, amphora_id %s",
                  self.__class__.__name__, amphora_id)
        self.computeconfig[amphora_id] = (amphora_id, 'get_amphora')


class NoopComputeDriver(driver_base.ComputeBase):
    def __init__(self, region=None):
        super(NoopComputeDriver, self).__init__()
        self.driver = NoopManager()

    def build(self, name="amphora_name", amphora_flavor=None, image_id=None,
              key_name=None, sec_groups=None, network_ids=None,
              config_drive_files=None, user_data=None):

        self.driver.build(name, amphora_flavor, image_id, key_name,
                          sec_groups, network_ids, config_drive_files,
                          user_data)

    def delete(self, amphora_id):
        self.driver.delete(amphora_id)

    def status(self, amphora_id):
        self.driver.status(amphora_id)

    def get_amphora(self, amphora_id):
        self.driver.get_amphora(amphora_id)
