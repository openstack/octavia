#  Copyright 2019 Red Hat, Inc. All rights reserved.
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

import time

from oslo_log import log as logging
from taskflow import retry

LOG = logging.getLogger(__name__)


class SleepingRetryTimesController(retry.Times):
    """A retry controller to attempt subflow retries a number of times.

    This retry controller overrides the Times on_failure to inject a
    sleep interval between retries.
    It also adds a log message when all of the retries are exhausted.

    :param attempts: number of attempts to retry the associated subflow
                        before giving up
    :type attempts: int
    :param name: Meaningful name for this atom, should be something that is
                 distinguishable and understandable for notification,
                 debugging, storing and any other similar purposes.
    :param provides: A set, string or list of items that
                     this will be providing (or could provide) to others, used
                     to correlate and associate the thing/s this atom
                     produces, if it produces anything at all.
    :param requires: A set or list of required inputs for this atom's
                     ``execute`` method.
    :param rebind: A dict of key/value pairs used to define argument
                   name conversions for inputs to this atom's ``execute``
                   method.
    :param revert_all: when provided this will cause the full flow to revert
                       when the number of attempts that have been tried
                       has been reached (when false, it will only locally
                       revert the associated subflow)
    :type revert_all: bool
    :param interval: Interval, in seconds, between retry attempts.
    :type interval: int
    """

    def __init__(self, attempts=1, name=None, provides=None, requires=None,
                 auto_extract=True, rebind=None, revert_all=False, interval=1):
        super(SleepingRetryTimesController, self).__init__(
            attempts, name, provides, requires, auto_extract, rebind,
            revert_all)
        self._interval = interval

    def on_failure(self, history, *args, **kwargs):
        if len(history) < self._attempts:
            LOG.warning('%s attempt %s of %s failed. Sleeping %s seconds and '
                        'retrying.',
                        self.name[self.name.startswith('retry-') and
                                  len('retry-'):], len(history),
                        self._attempts, self._interval)
            time.sleep(self._interval)
            return retry.RETRY
        return self._revert_action

    def revert(self, history, *args, **kwargs):
        LOG.error('%s retries with interval %s seconds have failed for %s. '
                  'Giving up.', len(history), self._interval, self.name)
