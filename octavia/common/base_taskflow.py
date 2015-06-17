# Copyright 2014-2015 Hewlett-Packard Development Company, L.P.
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
#

import concurrent.futures
from oslo_config import cfg
from taskflow import engines as tf_engines


CONF = cfg.CONF
CONF.import_group('task_flow', 'octavia.common.config')


class BaseTaskFlowEngine(object):
    """This is the task flow engine

    Use this engine to start/load flows in the
    code
    """

    def __init__(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=CONF.task_flow.max_workers)

    def _taskflow_load(self, flow, **kwargs):
        eng = tf_engines.load(
            flow,
            engine_conf=CONF.task_flow.engine,
            executor=self.executor,
            **kwargs)
        eng.compile()
        eng.prepare()

        return eng
