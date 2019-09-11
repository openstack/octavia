#    Copyright 2019 Red Hat, Inc. All rights reserved.
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

LOG = logging.getLogger(__name__)


def noop_provider_agent(exit_event):
    LOG.info('No-Op provider agent has started.')
    while not exit_event.is_set():
        time.sleep(1)
    LOG.info('No-Op provider agent is exiting.')
