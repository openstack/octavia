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
import concurrent.futures

from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture

from octavia.controller.worker.v2 import taskflow_jobboard_driver
from octavia.tests.unit import base


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


class TestZookeeperTaskFlowDriver(base.TestCase):

    def setUp(self):
        super().setUp()
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(
            group='task_flow',
            jobboard_backend_hosts=['host1.example.com', 'host2.example.com'],
            jobboard_backend_port=2181,
            jobboard_backend_namespace='octavia_jobboard',
            jobboard_zookeeper_ssl_options={'use_ssl': False,
                                            'verify_certs': True})

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'job_backends')
    @mock.patch('taskflow.utils.kazoo_utils.make_client')
    def test_first_job_board_call_creates_client(self, mock_make_client,
                                                 mock_job_backends):
        mock_client = mock.Mock()
        mock_make_client.return_value = mock_client

        driver = taskflow_jobboard_driver.ZookeeperTaskFlowDriver(mock.Mock())

        mock_make_client.assert_not_called()
        self.assertIsNone(driver._client)

        driver.job_board(mock.Mock())

        mock_make_client.assert_called_once()
        conf_arg = mock_make_client.call_args.args[0]
        self.assertEqual(
            'host1.example.com:2181,host2.example.com:2181',
            conf_arg['hosts'])
        self.assertFalse(conf_arg['use_ssl'])
        mock_client.start.assert_called_once()
        self.assertIs(driver._client, mock_client)

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'job_backends')
    @mock.patch('taskflow.utils.kazoo_utils.make_client')
    def test_job_board_passes_shared_client(self, mock_make_client,
                                            mock_job_backends):
        mock_client = mock.Mock()
        mock_make_client.return_value = mock_client

        driver = taskflow_jobboard_driver.ZookeeperTaskFlowDriver(mock.Mock())
        persistence = mock.Mock()
        driver.job_board(persistence)

        mock_job_backends.backend.assert_called_once()
        _, kwargs = mock_job_backends.backend.call_args
        self.assertIs(kwargs['client'], driver._client)
        self.assertIs(kwargs['persistence'], persistence)

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'job_backends')
    @mock.patch('taskflow.utils.kazoo_utils.make_client')
    def test_job_board_reuses_client(self, mock_make_client,
                                     mock_job_backends):
        mock_make_client.return_value = mock.Mock()
        driver = taskflow_jobboard_driver.ZookeeperTaskFlowDriver(mock.Mock())

        mock_make_client.assert_not_called()

        for _ in range(5):
            driver.job_board(mock.Mock())

        self.assertEqual(1, mock_make_client.call_count)

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'job_backends')
    @mock.patch('taskflow.utils.kazoo_utils.make_client')
    def test_concurrent_job_board_creates_single_client(self,
                                                        mock_make_client,
                                                        mock_job_backends):
        mock_client = mock.Mock()
        mock_make_client.return_value = mock_client

        driver = taskflow_jobboard_driver.ZookeeperTaskFlowDriver(mock.Mock())

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(driver.job_board, mock.Mock())
                       for _ in range(10)]
            concurrent.futures.wait(futures)

        self.assertEqual(1, mock_make_client.call_count)
        self.assertEqual(1, mock_client.start.call_count)

    @mock.patch('taskflow.utils.kazoo_utils.finalize_client')
    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'job_backends')
    @mock.patch('taskflow.utils.kazoo_utils.make_client')
    def test_shutdown_finalizes_client(self, mock_make, mock_job_backends,
                                       mock_finalize):
        mock_client = mock.Mock()
        mock_make.return_value = mock_client

        driver = taskflow_jobboard_driver.ZookeeperTaskFlowDriver(mock.Mock())

        driver.job_board(mock.Mock())
        driver.shutdown()

        mock_finalize.assert_called_once_with(mock_client)
        self.assertIsNone(driver._client)

    @mock.patch('taskflow.utils.kazoo_utils.finalize_client')
    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'job_backends')
    @mock.patch('taskflow.utils.kazoo_utils.make_client')
    def test_shutdown_before_job_board_is_safe(self, mock_make,
                                               mock_job_backends,
                                               mock_finalize):
        """shutdown() called before any job_board() must not raise."""
        driver = taskflow_jobboard_driver.ZookeeperTaskFlowDriver(mock.Mock())
        driver.shutdown()  # _client is still None here

        mock_finalize.assert_not_called()
        self.assertIsNone(driver._client)

    @mock.patch('taskflow.utils.kazoo_utils.finalize_client')
    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'job_backends')
    @mock.patch('taskflow.utils.kazoo_utils.make_client')
    def test_shutdown_idempotent(self, mock_make, mock_job_backends,
                                 mock_finalize):
        mock_client = mock.Mock()
        mock_make.return_value = mock_client

        driver = taskflow_jobboard_driver.ZookeeperTaskFlowDriver(mock.Mock())
        driver.job_board(mock.Mock())
        driver.shutdown()
        driver.shutdown()  # second call must be a no-op

        mock_finalize.assert_called_once()

    @mock.patch('taskflow.utils.kazoo_utils.finalize_client')
    @mock.patch('taskflow.utils.kazoo_utils.make_client')
    def test_ensure_client_cleans_up_if_start_fails(self, mock_make,
                                                    mock_finalize):
        mock_client = mock.Mock()
        mock_client.start.side_effect = ConnectionError("ZK unreachable")
        mock_make.return_value = mock_client

        driver = taskflow_jobboard_driver.ZookeeperTaskFlowDriver(mock.Mock())

        self.assertRaises(ConnectionError, driver._ensure_client)
        mock_finalize.assert_called_once_with(mock_client)
        self.assertIsNone(driver._client)
