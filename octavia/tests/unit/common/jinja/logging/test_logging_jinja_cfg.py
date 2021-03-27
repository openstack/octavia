# Copyright 2018 Rackspace, US Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from octavia_lib.common import constants as lib_consts
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture

from octavia.common.jinja.logging import logging_jinja_cfg
import octavia.tests.unit.base as base


class LoggingJinjaTestCase(base.TestCase):
    def test_build_agent_config(self):
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(debug=False)
        conf.config(
            group="amphora_agent",
            admin_log_targets='192.0.2.17:10514,192.51.100.4:10514')
        conf.config(
            group="amphora_agent",
            tenant_log_targets='192.0.2.7:20514,192.51.100.9:20514')
        conf.config(group="amphora_agent",
                    log_protocol=lib_consts.PROTOCOL_UDP)
        conf.config(group="amphora_agent", log_retry_count=5)
        conf.config(group="amphora_agent", log_retry_interval=2)
        conf.config(group="amphora_agent", log_queue_size=10000)

        lj = logging_jinja_cfg.LoggingJinjaTemplater()
        expected_config = (
            u'local0.=info action(type="omfwd" target="192.0.2.7" '
            'port="20514" protocol="UDP" action.resumeRetryCount="5" '
            'action.resumeInterval="2" queue.type="linkedList" '
            'queue.size="10000" )&action(type="omfwd" target="192.51.100.9" '
            'port="20514" protocol="UDP" action.resumeRetryCount="5" '
            'action.resumeInterval="2" queue.type="linkedList" '
            'queue.size="10000" action.execOnlyWhenPreviousIsSuspended="on")\n'
            'local1.* action(type="omfwd" target="192.0.2.17" port="10514" '
            'protocol="UDP" action.resumeRetryCount="5" '
            'action.resumeInterval="2" queue.type="linkedList" '
            'queue.size="10000" )&action(type="omfwd" target="192.51.100.4" '
            'port="10514" protocol="UDP" action.resumeRetryCount="5" '
            'action.resumeInterval="2" queue.type="linkedList" '
            'queue.size="10000" action.execOnlyWhenPreviousIsSuspended="on")')

        logging_cfg = lj.build_logging_config()

        self.assertEqual(expected_config, logging_cfg)

    def test_build_agent_config_disable_logs(self):
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(debug=False)
        conf.config(
            group="amphora_agent",
            disable_local_log_storage=True)

        lj = logging_jinja_cfg.LoggingJinjaTemplater()
        expected_config = (
            u'*.* stop')

        logging_cfg = lj.build_logging_config()

        self.assertEqual(expected_config, logging_cfg)
