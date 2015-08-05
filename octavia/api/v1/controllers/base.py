#    Copyright 2014 Rackspace
#
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
from pecan import rest
from stevedore import driver as stevedore_driver

from octavia.api.v1.types import listener as listener_types
from octavia.api.v1.types import load_balancer as lb_types
from octavia.api.v1.types import pool as pool_types
from octavia.db import repositories

CONF = cfg.CONF


class BaseController(rest.RestController):

    def __init__(self):
        self.repositories = repositories.Repositories()
        self.handler = stevedore_driver.DriverManager(
            namespace='octavia.api.handlers',
            name=CONF.api_handler,
            invoke_on_load=True
        ).driver

    @staticmethod
    def _convert_db_to_type(db_entity, to_type):
        """Converts a data model into a Octavia WSME type

        :param db_entity: data model to convert
        :param to_type: converts db_entity to this time
        """
        if isinstance(to_type, list):
            to_type = to_type[0]

        def _convert(db_obj):
            api_type = to_type.from_data_model(db_obj)
            if to_type == lb_types.LoadBalancerResponse:
                api_type.vip = lb_types.VIP.from_data_model(db_obj.vip)
            elif (to_type == pool_types.PoolResponse
                  and db_obj.session_persistence):
                api_type.session_persistence = (
                    pool_types.SessionPersistenceResponse.from_data_model(
                        db_obj.session_persistence))
            elif to_type == listener_types.ListenerResponse:
                api_type.sni_containers = [sni_c.tls_container_id
                                           for sni_c in db_obj.sni_containers]
            return api_type
        if isinstance(db_entity, list):
            converted = [_convert(db_obj) for db_obj in db_entity]
        else:
            converted = _convert(db_entity)
        return converted
