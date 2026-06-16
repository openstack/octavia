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

import abc
import contextlib
import threading

from oslo_config import cfg
from oslo_log import log
from oslo_utils import netutils
from oslo_utils import strutils
from taskflow.jobs import backends as job_backends
from taskflow.persistence import backends as persistence_backends

LOG = log.getLogger(__name__)
CONF = cfg.CONF


class JobboardTaskFlowDriver(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def job_board(self, persistence):
        """Setting up jobboard backend based on configuration setting.

        :param persistence: taskflow persistence backend instance
        :return: taskflow jobboard backend instance
        """

    def shutdown(self):
        """Release any long-lived resources held by the driver.

        Subclasses with cleanup needs (e.g. persistent client
        connections) should override. Default is a no-op.
        """


class MysqlPersistenceDriver:

    def __init__(self):
        self.persistence_conf = {
            'connection': CONF.task_flow.persistence_connection,
            'max_pool_size': CONF.database.max_pool_size,
            'max_overflow': CONF.database.max_overflow,
            'pool_timeout': CONF.database.pool_timeout,
            'idle_timeout': CONF.database.connection_recycle_time
        }

    def initialize(self):
        # Run migrations once on service start.
        backend = persistence_backends.fetch(self.persistence_conf)
        with contextlib.closing(backend):
            with contextlib.closing(backend.get_connection()) as connection:
                connection.upgrade()

    @contextlib.contextmanager
    def get_persistence(self):
        # Rewrite taskflow get backend, so it won't run migrations on each call
        backend = persistence_backends.fetch(self.persistence_conf)
        with contextlib.closing(backend):
            with contextlib.closing(backend.get_connection()) as conn:
                conn.validate()
            yield backend


class ZookeeperTaskFlowDriver(JobboardTaskFlowDriver):

    def __init__(self, persistence_driver):
        # Lazy import: kazoo is only required when this driver is selected
        # pylint: disable=import-outside-toplevel
        from taskflow.utils import kazoo_utils
        # pylint: enable=import-outside-toplevel
        self._kazoo_utils = kazoo_utils
        self.persistence_driver = persistence_driver
        self._hosts_str = ','.join(
            [f'{host}:{CONF.task_flow.jobboard_backend_port}'
             for host in CONF.task_flow.jobboard_backend_hosts])
        self._client = None
        self._client_lock = threading.Lock()

    def _ensure_client(self):
        # NOTE: The lock is intentionally held for the duration of
        # client.start() so that concurrent job_board() callers block
        # rather than racing to create multiple clients. The connection
        # delay (~seconds) is acceptable at first use.
        with self._client_lock:
            if self._client is None:
                conf = {'hosts': self._hosts_str}
                conf.update(CONF.task_flow.jobboard_zookeeper_ssl_options)
                client = self._kazoo_utils.make_client(conf)
                try:
                    client.start()
                except Exception:
                    self._kazoo_utils.finalize_client(client)
                    raise
                self._client = client
            return self._client

    def job_board(self, persistence):
        jobboard_backend_conf = {
            'board': 'zookeeper',
            'path': '/' + CONF.task_flow.jobboard_backend_namespace,
        }
        return job_backends.backend(
            CONF.task_flow.jobboard_backend_namespace,
            jobboard_backend_conf,
            persistence=persistence,
            client=self._ensure_client(),
        )

    def shutdown(self):
        with self._client_lock:
            if self._client is not None:
                LOG.debug("Finalizing shared KazooClient")
                self._kazoo_utils.finalize_client(self._client)
                self._client = None


class RedisTaskFlowDriver(JobboardTaskFlowDriver):

    def __init__(self, persistence_driver):
        self.persistence_driver = persistence_driver

    def job_board(self, persistence):

        jobboard_backend_conf = {
            'board': 'redis',
            'host': CONF.task_flow.jobboard_backend_hosts[0],
            'port': CONF.task_flow.jobboard_backend_port,
            'db': CONF.task_flow.jobboard_redis_backend_db,
            'namespace': CONF.task_flow.jobboard_backend_namespace,
            'sentinel': CONF.task_flow.jobboard_redis_sentinel,
            'sentinel_fallbacks': [
                '%s:%d' % (netutils.escape_ipv6(host),
                           CONF.task_flow.jobboard_backend_port)
                for host in CONF.task_flow.jobboard_backend_hosts[1:]
            ]
        }
        if CONF.task_flow.jobboard_backend_username is not None:
            jobboard_backend_conf['username'] = (
                CONF.task_flow.jobboard_backend_username)
        if CONF.task_flow.jobboard_backend_password is not None:
            jobboard_backend_conf['password'] = (
                CONF.task_flow.jobboard_backend_password)
        jobboard_backend_conf.update(
            CONF.task_flow.jobboard_redis_backend_ssl_options)

        sentinel_kwargs = CONF.task_flow.jobboard_redis_sentinel_ssl_options
        if 'ssl' in sentinel_kwargs:
            sentinel_kwargs['ssl'] = strutils.bool_from_string(
                sentinel_kwargs['ssl'])
        if CONF.task_flow.jobboard_redis_sentinel_username is not None:
            sentinel_kwargs['username'] = (
                CONF.task_flow.jobboard_redis_sentinel_username)
        if CONF.task_flow.jobboard_redis_sentinel_password is not None:
            sentinel_kwargs['password'] = (
                CONF.task_flow.jobboard_redis_sentinel_password)
        jobboard_backend_conf['sentinel_kwargs'] = sentinel_kwargs

        return job_backends.backend(
            CONF.task_flow.jobboard_backend_namespace,
            jobboard_backend_conf,
            persistence=persistence)


class EtcdTaskFlowDriver(JobboardTaskFlowDriver):

    def __init__(self, persistence_driver):
        self.persistence_driver = persistence_driver

    def job_board(self, persistence):
        jobboard_backend_conf = {
            'board': 'etcd',
            'host': CONF.task_flow.jobboard_backend_hosts[0],
            'port': CONF.task_flow.jobboard_backend_port,
            'path': CONF.task_flow.jobboard_backend_namespace,
            'ttl': CONF.task_flow.jobboard_expiration_time,
        }
        if CONF.task_flow.jobboard_etcd_ssl_options['use_ssl']:
            jobboard_backend_conf.update(
                CONF.task_flow.jobboard_etcd_ssl_options)
            jobboard_backend_conf.pop('use_ssl')
            jobboard_backend_conf['protocol'] = 'https'
        if CONF.task_flow.jobboard_etcd_timeout is not None:
            jobboard_backend_conf['timeout'] = (
                CONF.task_flow.jobboard_etcd_timeout)
        if CONF.task_flow.jobboard_etcd_api_path is not None:
            jobboard_backend_conf['api_path'] = (
                CONF.task_flow.jobboard_etcd_api_path)

        return job_backends.backend(CONF.task_flow.jobboard_backend_namespace,
                                    jobboard_backend_conf,
                                    persistence=persistence)
