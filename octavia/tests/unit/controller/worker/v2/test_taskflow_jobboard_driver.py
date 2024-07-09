# Copyright 2024 NTT DATA Group Corporation
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
from unittest import mock

from oslo_config import cfg

from octavia.controller.worker.v2 import taskflow_jobboard_driver
import octavia.tests.unit.base as base


class TestRedisTaskFlowDriver(base.TestCase):

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'job_backends')
    def test_job_board_default(self, mock_job_backends):
        driver = taskflow_jobboard_driver.RedisTaskFlowDriver(mock.Mock())
        driver.job_board(None)
        mock_job_backends.backend.assert_called_once_with(
            'octavia_jobboard',
            {
                'board': 'redis',
                'host': '127.0.0.1',
                'port': 6379,
                'db': 0,
                'namespace': 'octavia_jobboard',
                'sentinel': None,
                'sentinel_fallbacks': [],
                'ssl': False,
                'ssl_keyfile': None,
                'ssl_certfile': None,
                'ssl_ca_certs': None,
                'ssl_cert_reqs': 'required',
                'sentinel_kwargs': {
                    'ssl': False,
                    'ssl_keyfile': None,
                    'ssl_certfile': None,
                    'ssl_ca_certs': None,
                    'ssl_cert_reqs': 'required',
                }
            },
            persistence=None
        )

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'job_backends')
    def test_job_board_password(self, mock_job_backends):
        driver = taskflow_jobboard_driver.RedisTaskFlowDriver(mock.Mock())
        cfg.CONF.set_override('jobboard_backend_password', 'redispass',
                              group='task_flow')
        driver.job_board(None)
        mock_job_backends.backend.assert_called_once_with(
            'octavia_jobboard',
            {
                'board': 'redis',
                'host': '127.0.0.1',
                'port': 6379,
                'db': 0,
                'namespace': 'octavia_jobboard',
                'password': 'redispass',
                'sentinel': None,
                'sentinel_fallbacks': [],
                'ssl': False,
                'ssl_keyfile': None,
                'ssl_certfile': None,
                'ssl_ca_certs': None,
                'ssl_cert_reqs': 'required',
                'sentinel_kwargs': {
                    'ssl': False,
                    'ssl_keyfile': None,
                    'ssl_certfile': None,
                    'ssl_ca_certs': None,
                    'ssl_cert_reqs': 'required',
                }
            },
            persistence=None
        )

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'job_backends')
    def test_job_board_username(self, mock_job_backends):
        driver = taskflow_jobboard_driver.RedisTaskFlowDriver(mock.Mock())
        cfg.CONF.set_override('jobboard_backend_password', 'redispass',
                              group='task_flow')
        cfg.CONF.set_override('jobboard_backend_username', 'redisuser',
                              group='task_flow')
        driver.job_board(None)
        mock_job_backends.backend.assert_called_once_with(
            'octavia_jobboard',
            {
                'board': 'redis',
                'host': '127.0.0.1',
                'port': 6379,
                'db': 0,
                'namespace': 'octavia_jobboard',
                'username': 'redisuser',
                'password': 'redispass',
                'sentinel': None,
                'sentinel_fallbacks': [],
                'ssl': False,
                'ssl_keyfile': None,
                'ssl_certfile': None,
                'ssl_ca_certs': None,
                'ssl_cert_reqs': 'required',
                'sentinel_kwargs': {
                    'ssl': False,
                    'ssl_keyfile': None,
                    'ssl_certfile': None,
                    'ssl_ca_certs': None,
                    'ssl_cert_reqs': 'required',
                }
            },
            persistence=None
        )

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'job_backends')
    def test_job_board_ssl(self, mock_job_backends):
        driver = taskflow_jobboard_driver.RedisTaskFlowDriver(mock.Mock())
        cfg.CONF.set_override(
            'jobboard_redis_backend_ssl_options',
            {
                'ssl': True,
                'ssl_keyfile': 'rediskey',
                'ssl_certfile': 'rediscert',
                'ssl_ca_certs': 'redisca',
                'ssl_cert_reqs': 'required'
            },
            group='task_flow')
        driver.job_board(None)
        mock_job_backends.backend.assert_called_once_with(
            'octavia_jobboard',
            {
                'board': 'redis',
                'host': '127.0.0.1',
                'port': 6379,
                'db': 0,
                'namespace': 'octavia_jobboard',
                'sentinel': None,
                'sentinel_fallbacks': [],
                'ssl': True,
                'ssl_keyfile': 'rediskey',
                'ssl_certfile': 'rediscert',
                'ssl_ca_certs': 'redisca',
                'ssl_cert_reqs': 'required',
                'sentinel_kwargs': {
                    'ssl': False,
                    'ssl_keyfile': None,
                    'ssl_certfile': None,
                    'ssl_ca_certs': None,
                    'ssl_cert_reqs': 'required',
                }
            },
            persistence=None
        )

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'job_backends')
    def test_job_board_sentinel(self, mock_job_backends):
        driver = taskflow_jobboard_driver.RedisTaskFlowDriver(mock.Mock())
        cfg.CONF.set_override('jobboard_redis_sentinel', 'mymaster',
                              group='task_flow')
        cfg.CONF.set_override('jobboard_backend_hosts',
                              ['host1', 'host2', 'host3'],
                              group='task_flow')
        cfg.CONF.set_override('jobboard_backend_port', 26379,
                              group='task_flow')
        driver.job_board(None)
        mock_job_backends.backend.assert_called_once_with(
            'octavia_jobboard',
            {
                'board': 'redis',
                'host': 'host1',
                'port': 26379,
                'db': 0,
                'namespace': 'octavia_jobboard',
                'sentinel': 'mymaster',
                'sentinel_fallbacks': ['host2:26379', 'host3:26379'],
                'ssl': False,
                'ssl_keyfile': None,
                'ssl_certfile': None,
                'ssl_ca_certs': None,
                'ssl_cert_reqs': 'required',
                'sentinel_kwargs': {
                    'ssl': False,
                    'ssl_keyfile': None,
                    'ssl_certfile': None,
                    'ssl_ca_certs': None,
                    'ssl_cert_reqs': 'required',
                }
            },
            persistence=None
        )

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'job_backends')
    def test_job_board_sentinel_password(self, mock_job_backends):
        driver = taskflow_jobboard_driver.RedisTaskFlowDriver(mock.Mock())
        cfg.CONF.set_override('jobboard_redis_sentinel', 'mymaster',
                              group='task_flow')
        cfg.CONF.set_override('jobboard_backend_hosts',
                              ['host1', 'host2', 'host3'],
                              group='task_flow')
        cfg.CONF.set_override('jobboard_backend_port', 26379,
                              group='task_flow')
        cfg.CONF.set_override('jobboard_backend_password', 'redispass',
                              group='task_flow')
        cfg.CONF.set_override('jobboard_redis_sentinel_password',
                              'sentinelpass', group='task_flow')
        driver.job_board(None)
        mock_job_backends.backend.assert_called_once_with(
            'octavia_jobboard',
            {
                'board': 'redis',
                'host': 'host1',
                'port': 26379,
                'db': 0,
                'namespace': 'octavia_jobboard',
                'password': 'redispass',
                'sentinel': 'mymaster',
                'sentinel_fallbacks': ['host2:26379', 'host3:26379'],
                'ssl': False,
                'ssl_keyfile': None,
                'ssl_certfile': None,
                'ssl_ca_certs': None,
                'ssl_cert_reqs': 'required',
                'sentinel_kwargs': {
                    'password': 'sentinelpass',
                    'ssl': False,
                    'ssl_keyfile': None,
                    'ssl_certfile': None,
                    'ssl_ca_certs': None,
                    'ssl_cert_reqs': 'required',
                }
            },
            persistence=None
        )

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'job_backends')
    def test_job_board_sentinel_username(self, mock_job_backends):
        driver = taskflow_jobboard_driver.RedisTaskFlowDriver(mock.Mock())
        cfg.CONF.set_override('jobboard_redis_sentinel', 'mymaster',
                              group='task_flow')
        cfg.CONF.set_override('jobboard_backend_hosts',
                              ['host1', 'host2', 'host3'],
                              group='task_flow')
        cfg.CONF.set_override('jobboard_backend_port', 26379,
                              group='task_flow')
        cfg.CONF.set_override('jobboard_backend_username', 'redisuser',
                              group='task_flow')
        cfg.CONF.set_override('jobboard_backend_password', 'redispass',
                              group='task_flow')
        cfg.CONF.set_override('jobboard_redis_sentinel_username',
                              'sentineluser', group='task_flow')
        cfg.CONF.set_override('jobboard_redis_sentinel_password',
                              'sentinelpass', group='task_flow')
        driver.job_board(None)
        mock_job_backends.backend.assert_called_once_with(
            'octavia_jobboard',
            {
                'board': 'redis',
                'host': 'host1',
                'port': 26379,
                'db': 0,
                'namespace': 'octavia_jobboard',
                'username': 'redisuser',
                'password': 'redispass',
                'sentinel': 'mymaster',
                'sentinel_fallbacks': ['host2:26379', 'host3:26379'],
                'ssl': False,
                'ssl_keyfile': None,
                'ssl_certfile': None,
                'ssl_ca_certs': None,
                'ssl_cert_reqs': 'required',
                'sentinel_kwargs': {
                    'username': 'sentineluser',
                    'password': 'sentinelpass',
                    'ssl': False,
                    'ssl_keyfile': None,
                    'ssl_certfile': None,
                    'ssl_ca_certs': None,
                    'ssl_cert_reqs': 'required',
                }
            },
            persistence=None
        )

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'job_backends')
    def test_job_board_sentinel_ssl(self, mock_job_backends):
        driver = taskflow_jobboard_driver.RedisTaskFlowDriver(mock.Mock())
        cfg.CONF.set_override('jobboard_redis_sentinel', 'mymaster',
                              group='task_flow')
        cfg.CONF.set_override('jobboard_backend_hosts',
                              ['host1', 'host2', 'host3'],
                              group='task_flow')
        cfg.CONF.set_override('jobboard_backend_port', 26379,
                              group='task_flow')
        cfg.CONF.set_override(
            'jobboard_redis_backend_ssl_options',
            {
                'ssl': True,
                'ssl_keyfile': 'rediskey',
                'ssl_certfile': 'rediscert',
                'ssl_ca_certs': 'redisca',
                'ssl_cert_reqs': 'required'
            },
            group='task_flow')
        cfg.CONF.set_override(
            'jobboard_redis_sentinel_ssl_options',
            {
                'ssl': True,
                'ssl_keyfile': 'sentinelkey',
                'ssl_certfile': 'sentinelcert',
                'ssl_ca_certs': 'sentinelca',
                'ssl_cert_reqs': 'required'
            },
            group='task_flow')
        driver.job_board(None)
        mock_job_backends.backend.assert_called_once_with(
            'octavia_jobboard',
            {
                'board': 'redis',
                'host': 'host1',
                'port': 26379,
                'db': 0,
                'namespace': 'octavia_jobboard',
                'sentinel': 'mymaster',
                'sentinel_fallbacks': ['host2:26379', 'host3:26379'],
                'ssl': True,
                'ssl_keyfile': 'rediskey',
                'ssl_certfile': 'rediscert',
                'ssl_ca_certs': 'redisca',
                'ssl_cert_reqs': 'required',
                'sentinel_kwargs': {
                    'ssl': True,
                    'ssl_keyfile': 'sentinelkey',
                    'ssl_certfile': 'sentinelcert',
                    'ssl_ca_certs': 'sentinelca',
                    'ssl_cert_reqs': 'required'
                }
            },
            persistence=None
        )
