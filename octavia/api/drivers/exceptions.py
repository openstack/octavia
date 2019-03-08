# Copyright 2018 Rackspace, US Inc.
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

from octavia_lib.api.drivers import exceptions as lib_exceptions


warnings.simplefilter('default', DeprecationWarning)

DriverError = moves.moved_class(lib_exceptions.DriverError, 'DriverError',
                                __name__, version='Stein', removal_version='U')

NotImplementedError = moves.moved_class(
    lib_exceptions.NotImplementedError, 'NotImplementedError', __name__,
    version='Stein', removal_version='U')

UnsupportedOptionError = moves.moved_class(
    lib_exceptions.UnsupportedOptionError, 'UnsupportedOptionError', __name__,
    version='Stein', removal_version='U')

UpdateStatusError = moves.moved_class(
    lib_exceptions.UpdateStatusError, 'UpdateStatusError', __name__,
    version='Stein', removal_version='U')

UpdateStatisticsError = moves.moved_class(
    lib_exceptions.UpdateStatisticsError, 'UpdateStatisticsError', __name__,
    version='Stein', removal_version='U')
