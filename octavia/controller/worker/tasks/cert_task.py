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
#


import logging

from oslo_config import cfg
from stevedore import driver as stevedore_driver
from taskflow import task

CONF = cfg.CONF
CONF.import_group('controller_worker', 'octavia.common.config')
LOG = logging.getLogger(__name__)
CERT_VALIDITY = 2 * 365 * 24 * 60 * 60


class BaseCertTask(task.Task):
    """Base task to load drivers common to the tasks."""

    def __init__(self, **kwargs):
        super(BaseCertTask, self).__init__(**kwargs)
        self.cert_generator = stevedore_driver.DriverManager(
            namespace='octavia.cert_generator',
            name=CONF.controller_worker.cert_generator,
            invoke_on_load=True,
        ).driver


class GenerateServerPEMTask(BaseCertTask):
    """Create the server certs for the agent comm

    Use the amphora_id for the CN
    """

    def execute(self, amphora_id):
        cert = self.cert_generator.generate_cert_key_pair(
            cn=amphora_id,
            validity=CERT_VALIDITY)

        return cert.certificate + cert.private_key
