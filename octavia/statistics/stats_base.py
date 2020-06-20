# Copyright 2011-2014 OpenStack Foundation,author: Min Wang,German Eichberger
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

import abc

from oslo_config import cfg
from oslo_log import log as logging
from stevedore import named as stevedore_named

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
_STATS_HANDLERS = None


def _get_stats_handlers():
    global _STATS_HANDLERS
    if _STATS_HANDLERS is None:
        _STATS_HANDLERS = stevedore_named.NamedExtensionManager(
            namespace='octavia.statistics.drivers',
            names=CONF.controller_worker.statistics_drivers,
            invoke_on_load=True,
            propagate_map_exceptions=False
        )
    return _STATS_HANDLERS


def update_stats_via_driver(listener_stats, deltas=False):
    """Send listener stats to the enabled stats driver(s)

    :param listener_stats: A list of ListenerStatistics objects
    :type listener_stats: list
    :param deltas: Indicates whether the stats are deltas (false==absolute)
    :type deltas: bool
    """
    handlers = _get_stats_handlers()
    handlers.map_method('update_stats', listener_stats, deltas=deltas)


class StatsDriverMixin(object, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def update_stats(self, listener_stats, deltas=False):
        """Return a stats object formatted for a generic backend

        :param listener_stats: A list of data_model.ListenerStatistics objects
        :type listener_stats: list
        :param deltas: Indicates whether the stats are deltas (false==absolute)
        :type deltas: bool
        """
