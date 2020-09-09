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

from oslo_config import cfg
from oslo_log import log
from taskflow.jobs import backends as job_backends
from taskflow.persistence import backends as persistence_backends

LOG = log.getLogger(__name__)
CONF = cfg.CONF


class JobboardTaskFlowDriver(object, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def job_board(self, persistence):
        """Setting up jobboard backend based on configuration setting.

        :param persistence: taskflow persistence backend instance
        :return: taskflow jobboard backend instance
        """


class MysqlPersistenceDriver(object):

    def __init__(self):
        self.persistence_conf = {
            'connection': CONF.task_flow.persistence_connection,
            'max_pool_size': CONF.database.max_pool_size,
            'max_overflow': CONF.database.max_overflow,
            'pool_timeout': CONF.database.pool_timeout,
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
        self.persistence_driver = persistence_driver

    def job_board(self, persistence):
        job_backends_hosts = ','.join(
            ['%s:%s' % (host, CONF.task_flow.jobboard_backend_port)
             for host in CONF.task_flow.jobboard_backend_hosts])
        jobboard_backend_conf = {
            'board': 'zookeeper',
            'hosts': job_backends_hosts,
            'path': '/' + CONF.task_flow.jobboard_backend_namespace,
        }
        jobboard_backend_conf.update(
            CONF.task_flow.jobboard_zookeeper_ssl_options)
        return job_backends.backend(CONF.task_flow.jobboard_backend_namespace,
                                    jobboard_backend_conf,
                                    persistence=persistence)


class RedisTaskFlowDriver(JobboardTaskFlowDriver):

    def __init__(self, persistence_driver):
        self.persistence_driver = persistence_driver

    def job_board(self, persistence):
        jobboard_backend_conf = {
            'board': 'redis',
            'host': CONF.task_flow.jobboard_backend_hosts[0],
            'port': CONF.task_flow.jobboard_backend_port,
            'password': CONF.task_flow.jobboard_backend_password,
            'namespace': CONF.task_flow.jobboard_backend_namespace,
            'sentinel': CONF.task_flow.jobboard_redis_sentinel,
        }
        jobboard_backend_conf.update(
            CONF.task_flow.jobboard_redis_backend_ssl_options)
        return job_backends.backend(
            CONF.task_flow.jobboard_backend_namespace,
            jobboard_backend_conf,
            persistence=persistence)
