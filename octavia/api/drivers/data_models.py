#    Copyright (c) 2014 Rackspace
#    Copyright (c) 2016 Blue Box, an IBM Company
#    Copyright 2018 Rackspace, US Inc.
#    All Rights Reserved.
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

import warnings

from debtcollector import moves

from octavia_lib.api.drivers import data_models as lib_data_models


warnings.simplefilter('default', DeprecationWarning)

BaseDataModel = moves.moved_class(lib_data_models.BaseDataModel,
                                  'BaseDataModel', __name__,
                                  version='Stein', removal_version='U')

UnsetType = moves.moved_class(lib_data_models.UnsetType, 'UnsetType', __name__,
                              version='Stein', removal_version='U')

LoadBalancer = moves.moved_class(lib_data_models.LoadBalancer, 'LoadBalancer',
                                 __name__, version='Stein',
                                 removal_version='U')

Listener = moves.moved_class(lib_data_models.Listener, 'Listener', __name__,
                             version='Stein', removal_version='U')

Pool = moves.moved_class(lib_data_models.Pool, 'Pool', __name__,
                         version='Stein', removal_version='U')

Member = moves.moved_class(lib_data_models.Member, 'Member', __name__,
                           version='Stein', removal_version='U')

HealthMonitor = moves.moved_class(lib_data_models.HealthMonitor,
                                  'HealthMonitor', __name__,
                                  version='Stein', removal_version='U')

L7Policy = moves.moved_class(lib_data_models.L7Policy, 'L7Policy', __name__,
                             version='Stein', removal_version='U')

L7Rule = moves.moved_class(lib_data_models.L7Rule, 'L7Rule', __name__,
                           version='Stein', removal_version='U')

VIP = moves.moved_class(lib_data_models.VIP, 'VIP', __name__,
                        version='Stein', removal_version='U')
