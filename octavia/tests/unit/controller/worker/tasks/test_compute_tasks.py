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

import time

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils
import six

from octavia.common import constants
from octavia.common import exceptions
from octavia.controller.worker.tasks import compute_tasks
import octavia.tests.unit.base as base

if six.PY2:
    import mock
else:
    import unittest.mock as mock

BUILTINS = '__builtin__'
if six.PY3:
    BUILTINS = 'builtins'

AMP_FLAVOR_ID = 10
AMP_IMAGE_ID = 11
AMP_SSH_KEY_NAME = None
AMP_NET = uuidutils.generate_uuid()
AMP_SEC_GROUPS = []
AMP_WAIT = 12
AMPHORA_ID = uuidutils.generate_uuid()
COMPUTE_ID = uuidutils.generate_uuid()
LB_NET_IP = '192.0.2.1'
PORT_ID = uuidutils.generate_uuid()
AUTH_VERSION = '2'


class TestException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

_amphora_mock = mock.MagicMock()
_amphora_mock.id = AMPHORA_ID
_amphora_mock.compute_id = COMPUTE_ID
_load_balancer_mock = mock.MagicMock()
_load_balancer_mock.amphorae = [_amphora_mock]
_port = mock.MagicMock()
_port.id = PORT_ID


class TestComputeTasks(base.TestCase):

    def setUp(self):
        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="controller_worker", amp_flavor_id=AMP_FLAVOR_ID)
        conf.config(group="controller_worker", amp_image_id=AMP_IMAGE_ID)
        conf.config(group="controller_worker",
                    amp_ssh_key_name=AMP_SSH_KEY_NAME)
        conf.config(group="controller_worker", amp_network=AMP_NET)
        conf.config(group="controller_worker", amp_active_wait_sec=AMP_WAIT)
        conf.config(group="keystone_authtoken", auth_version=AUTH_VERSION)

        _amphora_mock.id = AMPHORA_ID

        logging_mock = mock.MagicMock()
        compute_tasks.LOG = logging_mock

        super(TestComputeTasks, self).setUp()

    @mock.patch('jinja2.Environment.get_template')
    @mock.patch('octavia.amphorae.backends.agent.'
                'agent_jinja_cfg.AgentJinjaTemplater.'
                'build_agent_config', return_value='test_conf')
    @mock.patch('stevedore.driver.DriverManager.driver')
    def test_compute_create(self, mock_driver, mock_conf, mock_jinja):

        createcompute = compute_tasks.ComputeCreate()

        mock_driver.build.return_value = COMPUTE_ID
        # Test execute()
        compute_id = createcompute.execute(_amphora_mock.id, ports=[_port])

        # Validate that the build method was called properly
        mock_driver.build.assert_called_once_with(
            name="amphora-" + _amphora_mock.id,
            amphora_flavor=AMP_FLAVOR_ID,
            image_id=AMP_IMAGE_ID,
            key_name=AMP_SSH_KEY_NAME,
            sec_groups=AMP_SEC_GROUPS,
            network_ids=[AMP_NET],
            port_ids=[PORT_ID],
            config_drive_files={'/etc/octavia/'
                                'amphora-agent.conf': 'test_conf'})

        # Make sure it returns the expected compute_id
        assert(compute_id == COMPUTE_ID)

        # Test that a build exception is raised
        createcompute = compute_tasks.ComputeCreate()

        self.assertRaises(TypeError,
                          createcompute.execute,
                          _amphora_mock, config_drive_files='test_cert')

        # Test revert()

        _amphora_mock.compute_id = COMPUTE_ID

        createcompute = compute_tasks.ComputeCreate()
        createcompute.revert(compute_id, _amphora_mock.id)

        # Validate that the delete method was called properly
        mock_driver.delete.assert_called_once_with(
            COMPUTE_ID)

        # Test that a delete exception is not raised

        createcompute.revert(COMPUTE_ID, _amphora_mock.id)

    @mock.patch('jinja2.Environment.get_template')
    @mock.patch('octavia.amphorae.backends.agent.'
                'agent_jinja_cfg.AgentJinjaTemplater.'
                'build_agent_config', return_value='test_conf')
    @mock.patch('stevedore.driver.DriverManager.driver')
    def test_compute_create_cert(self, mock_driver, mock_conf, mock_jinja):

        createcompute = compute_tasks.CertComputeCreate()

        mock_driver.build.return_value = COMPUTE_ID
        m = mock.mock_open(read_data='test')
        with mock.patch('%s.open' % BUILTINS, m, create=True):
            # Test execute()
            compute_id = createcompute.execute(_amphora_mock.id,
                                               'test_cert')

            # Validate that the build method was called properly
            mock_driver.build.assert_called_once_with(
                name="amphora-" + _amphora_mock.id,
                amphora_flavor=AMP_FLAVOR_ID,
                image_id=AMP_IMAGE_ID,
                key_name=AMP_SSH_KEY_NAME,
                sec_groups=AMP_SEC_GROUPS,
                network_ids=[AMP_NET],
                port_ids=[],
                config_drive_files={
                    '/etc/octavia/certs/server.pem': 'test_cert',
                    '/etc/octavia/certs/client_ca.pem': m.return_value,
                    '/etc/octavia/amphora-agent.conf': 'test_conf'})

        # Make sure it returns the expected compute_id
        assert(compute_id == COMPUTE_ID)

        # Test that a build exception is raised
        with mock.patch('%s.open' % BUILTINS, m, create=True):
            createcompute = compute_tasks.ComputeCreate()
            self.assertRaises(TypeError,
                              createcompute.execute,
                              _amphora_mock,
                              config_drive_files='test_cert')

        # Test revert()

        _amphora_mock.compute_id = COMPUTE_ID

        createcompute = compute_tasks.ComputeCreate()
        createcompute.revert(compute_id, _amphora_mock.id)

        # Validate that the delete method was called properly
        mock_driver.delete.assert_called_once_with(
            COMPUTE_ID)

        # Test that a delete exception is not raised

        createcompute.revert(COMPUTE_ID, _amphora_mock.id)

    @mock.patch('stevedore.driver.DriverManager.driver')
    @mock.patch('time.sleep')
    def test_compute_wait(self,
                          mock_time_sleep,
                          mock_driver):

        _amphora_mock.compute_id = COMPUTE_ID
        _amphora_mock.status = constants.ACTIVE
        _amphora_mock.lb_network_ip = LB_NET_IP

        mock_driver.get_amphora.return_value = _amphora_mock

        computewait = compute_tasks.ComputeWait()
        computewait.execute(COMPUTE_ID)

        time.sleep.assert_called_once_with(AMP_WAIT)

        mock_driver.get_amphora.assert_called_once_with(COMPUTE_ID)

        _amphora_mock.status = constants.DELETED

        self.assertRaises(exceptions.ComputeWaitTimeoutException,
                          computewait.execute,
                          _amphora_mock)

    @mock.patch('stevedore.driver.DriverManager.driver')
    def test_delete_amphorae_on_load_balancer(self, mock_driver):

        delete_amps = compute_tasks.DeleteAmphoraeOnLoadBalancer()
        delete_amps.execute(_load_balancer_mock)

        mock_driver.delete.assert_called_once_with(compute_id=COMPUTE_ID)

    @mock.patch('stevedore.driver.DriverManager.driver')
    def test_compute_delete(self, mock_driver):

        delete_compute = compute_tasks.ComputeDelete()
        delete_compute.execute(_amphora_mock)

        mock_driver.delete.assert_called_once_with(compute_id=COMPUTE_ID)
