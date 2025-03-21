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

from collections import namedtuple

from oslo_log import log as logging
from oslo_utils import uuidutils
from sqlalchemy import Column
from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import update

from octavia.common import constants
from octavia.common import data_models
from octavia.compute import compute_base as driver_base
from octavia.network import data_models as network_models

LOG = logging.getLogger(__name__)


NoopServerGroup = namedtuple('ServerGroup', ['id'])


class NoopManager:
    def __init__(self):
        super().__init__()
        self.computeconfig = {}

        # Get a DB engine for the network no-op DB
        # Required to update the ports when a port is attached to a compute
        self.engine = create_engine('sqlite:////tmp/octavia-network-noop.db',
                                    isolation_level='SERIALIZABLE')
        metadata_obj = MetaData()

        self.interfaces_table = Table(
            'interfaces',
            metadata_obj,
            Column('port_id', String(36)),
            Column('network_id', String(36)),
            Column('compute_id', String(36)),
            Column('vnic_type', String(6)))

    def build(self, name="amphora_name", amphora_flavor=None,
              image_tag=None, image_owner=None, key_name=None, sec_groups=None,
              network_ids=None, config_drive_files=None, user_data=None,
              port_ids=None, server_group_id=None, availability_zone=None):
        LOG.debug("Compute %s no-op, build name %s, amphora_flavor %s, "
                  "image_tag %s, image_owner %s, key_name %s, sec_groups %s, "
                  "network_ids %s, config_drive_files %s, user_data %s, "
                  "port_ids %s, server_group_id %s, availability_zone %s",
                  self.__class__.__name__,
                  name, amphora_flavor, image_tag, image_owner,
                  key_name, sec_groups, network_ids, config_drive_files,
                  user_data, port_ids, server_group_id, availability_zone)
        self.computeconfig[(name, amphora_flavor, image_tag,
                            image_owner, key_name, user_data,
                            server_group_id)] = (
            name, amphora_flavor,
            image_tag, image_owner, key_name, sec_groups,
            network_ids, config_drive_files, user_data, port_ids,
            server_group_id, 'build')
        compute_id = uuidutils.generate_uuid()
        return compute_id

    def delete(self, compute_id):
        LOG.debug("Compute %s no-op, compute_id %s",
                  self.__class__.__name__, compute_id)
        self.computeconfig[compute_id] = (compute_id, 'delete')

    def status(self, compute_id):
        LOG.debug("Compute %s no-op, compute_id %s",
                  self.__class__.__name__, compute_id)
        self.computeconfig[compute_id] = (compute_id, 'status')
        return constants.UP

    def get_amphora(self, compute_id, management_network_id=None):
        LOG.debug("Compute %s no-op, compute_id %s, management_network_id %s",
                  self.__class__.__name__, compute_id, management_network_id)
        self.computeconfig[(compute_id, management_network_id)] = (
            compute_id, management_network_id, 'get_amphora')
        return data_models.Amphora(
            compute_id=compute_id,
            status=constants.ACTIVE,
            lb_network_ip='192.0.2.1'
        ), None

    def create_server_group(self, name, policy):
        LOG.debug("Create Server Group %s no-op, name %s, policy %s ",
                  self.__class__.__name__, name, policy)
        self.computeconfig[(name, policy)] = (name, policy, 'create')
        return NoopServerGroup(id=uuidutils.generate_uuid())

    def delete_server_group(self, server_group_id):
        LOG.debug("Delete Server Group %s no-op, id %s ",
                  self.__class__.__name__, server_group_id)
        self.computeconfig[server_group_id] = (server_group_id, 'delete')

    def attach_network_or_port(self, compute_id, network_id=None,
                               ip_address=None, port_id=None):
        LOG.debug("Compute %s no-op, attach_network_or_port compute_id %s,"
                  "network_id %s, ip_address %s, port_id %s",
                  self.__class__.__name__, compute_id,
                  network_id, ip_address, port_id)
        self.computeconfig[(compute_id, network_id, ip_address, port_id)] = (
            compute_id, network_id, ip_address, port_id,
            'attach_network_or_port')

        # Update the port in the network no-op DB
        with self.engine.connect() as connection:
            connection.execute(update(self.interfaces_table).where(
                self.interfaces_table.c.port_id == port_id).values(
                    compute_id=compute_id))
            connection.commit()

        return network_models.Interface(
            id=uuidutils.generate_uuid(),
            compute_id=compute_id,
            network_id=network_id,
            fixed_ips=[],
            port_id=uuidutils.generate_uuid(),
            vnic_type=constants.VNIC_TYPE_NORMAL
        )

    def detach_port(self, compute_id, port_id):
        LOG.debug("Compute %s no-op, detach_network compute_id %s, "
                  "port_id %s",
                  self.__class__.__name__, compute_id, port_id)
        self.computeconfig[(compute_id, port_id)] = (
            compute_id, port_id, 'detach_port')

    def validate_flavor(self, flavor_id):
        LOG.debug("Compute %s no-op, validate_flavor flavor_id %s",
                  self.__class__.__name__, flavor_id)
        self.computeconfig[flavor_id] = (flavor_id, 'validate_flavor')

    def validate_availability_zone(self, availability_zone):
        LOG.debug("Compute %s no-op, validate_availability_zone name %s",
                  self.__class__.__name__, availability_zone)
        self.computeconfig[availability_zone] = (
            availability_zone, 'validate_availability_zone')


class NoopComputeDriver(driver_base.ComputeBase):
    def __init__(self):
        super().__init__()
        self.driver = NoopManager()

    def build(self, name="amphora_name", amphora_flavor=None,
              image_tag=None, image_owner=None, key_name=None, sec_groups=None,
              network_ids=None, config_drive_files=None, user_data=None,
              port_ids=None, server_group_id=None, availability_zone=None):

        compute_id = self.driver.build(name, amphora_flavor,
                                       image_tag, image_owner,
                                       key_name, sec_groups, network_ids,
                                       config_drive_files, user_data, port_ids,
                                       server_group_id, availability_zone)
        return compute_id

    def delete(self, compute_id):
        self.driver.delete(compute_id)

    def status(self, compute_id):
        return self.driver.status(compute_id)

    def get_amphora(self, compute_id, management_network_id=None):
        return self.driver.get_amphora(compute_id, management_network_id)

    def create_server_group(self, name, policy):
        return self.driver.create_server_group(name, policy)

    def delete_server_group(self, server_group_id):
        self.driver.delete_server_group(server_group_id)

    def attach_network_or_port(self, compute_id, network_id=None,
                               ip_address=None, port_id=None):
        self.driver.attach_network_or_port(compute_id, network_id, ip_address,
                                           port_id)

    def detach_port(self, compute_id, port_id):
        self.driver.detach_port(compute_id, port_id)

    def validate_flavor(self, flavor_id):
        self.driver.validate_flavor(flavor_id)

    def validate_availability_zone(self, availability_zone):
        self.driver.validate_availability_zone(availability_zone)
