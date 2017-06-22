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

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.common import constants
from octavia.common import exceptions
from octavia.controller.worker.tasks import compute_tasks
from octavia.tests.common import utils as test_utils
import octavia.tests.unit.base as base


AMP_FLAVOR_ID = '10'
AMP_IMAGE_ID = '11'
AMP_IMAGE_TAG = 'glance_tag'
AMP_SSH_KEY_NAME = None
AMP_NET = [uuidutils.generate_uuid()]
AMP_SEC_GROUPS = []
AMP_WAIT = 12
AMPHORA_ID = uuidutils.generate_uuid()
COMPUTE_ID = uuidutils.generate_uuid()
LB_NET_IP = '192.0.2.1'
PORT_ID = uuidutils.generate_uuid()
SERVER_GRPOUP_ID = uuidutils.generate_uuid()


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
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(
            group="controller_worker", amp_flavor_id=AMP_FLAVOR_ID)
        self.conf.config(
            group="controller_worker", amp_image_id=AMP_IMAGE_ID)
        self.conf.config(
            group="controller_worker", amp_image_tag=AMP_IMAGE_TAG)
        self.conf.config(
            group="controller_worker", amp_ssh_key_name=AMP_SSH_KEY_NAME)
        self.conf.config(
            group="controller_worker", amp_boot_network_list=AMP_NET)
        self.conf.config(
            group="controller_worker", amp_active_wait_sec=AMP_WAIT)
        self.conf.config(
            group="controller_worker", amp_secgroup_list=AMP_SEC_GROUPS)
        self.conf.config(group="controller_worker", amp_image_owner_id='')

        _amphora_mock.id = AMPHORA_ID
        _amphora_mock.status = constants.AMPHORA_ALLOCATED

        logging_mock = mock.MagicMock()
        compute_tasks.LOG = logging_mock

        super(TestComputeTasks, self).setUp()

    @mock.patch('jinja2.Environment.get_template')
    @mock.patch('octavia.amphorae.backends.agent.'
                'agent_jinja_cfg.AgentJinjaTemplater.'
                'build_agent_config', return_value='test_conf')
    @mock.patch('stevedore.driver.DriverManager.driver')
    def test_compute_create(self, mock_driver, mock_conf, mock_jinja):

        image_owner_id = uuidutils.generate_uuid()
        self.conf.config(
            group="controller_worker", amp_image_owner_id=image_owner_id)

        createcompute = compute_tasks.ComputeCreate()

        mock_driver.build.return_value = COMPUTE_ID
        # Test execute()
        compute_id = createcompute.execute(_amphora_mock.id, ports=[_port],
                                           server_group_id=SERVER_GRPOUP_ID)

        # Validate that the build method was called properly
        mock_driver.build.assert_called_once_with(
            name="amphora-" + _amphora_mock.id,
            amphora_flavor=AMP_FLAVOR_ID,
            image_id=AMP_IMAGE_ID,
            image_tag=AMP_IMAGE_TAG,
            image_owner=image_owner_id,
            key_name=AMP_SSH_KEY_NAME,
            sec_groups=AMP_SEC_GROUPS,
            network_ids=AMP_NET,
            port_ids=[PORT_ID],
            config_drive_files={'/etc/octavia/'
                                'amphora-agent.conf': 'test_conf'},
            user_data=None,
            server_group_id=SERVER_GRPOUP_ID)

        # Make sure it returns the expected compute_id
        self.assertEqual(COMPUTE_ID, compute_id)

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
    @mock.patch('octavia.common.jinja.'
                'user_data_jinja_cfg.UserDataJinjaCfg.'
                'build_user_data_config', return_value='test_conf')
    @mock.patch('stevedore.driver.DriverManager.driver')
    def test_compute_create_user_data(self, mock_driver,
                                      mock_ud_conf, mock_conf, mock_jinja):

        self.conf.config(
            group="controller_worker", user_data_config_drive=True)
        mock_ud_conf.return_value = 'test_ud_conf'
        createcompute = compute_tasks.ComputeCreate()

        mock_driver.build.return_value = COMPUTE_ID
        # Test execute()
        compute_id = createcompute.execute(_amphora_mock.id, ports=[_port])

        # Validate that the build method was called properly
        mock_driver.build.assert_called_once_with(
            name="amphora-" + _amphora_mock.id,
            amphora_flavor=AMP_FLAVOR_ID,
            image_id=AMP_IMAGE_ID,
            image_tag=AMP_IMAGE_TAG,
            image_owner='',
            key_name=AMP_SSH_KEY_NAME,
            sec_groups=AMP_SEC_GROUPS,
            network_ids=AMP_NET,
            port_ids=[PORT_ID],
            config_drive_files=None,
            user_data='test_ud_conf',
            server_group_id=None)

        # Make sure it returns the expected compute_id
        self.assertEqual(COMPUTE_ID, compute_id)

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
    def test_compute_create_without_ssh_access(self, mock_driver,
                                               mock_conf, mock_jinja):

        createcompute = compute_tasks.ComputeCreate()

        mock_driver.build.return_value = COMPUTE_ID
        self.conf.config(
            group="controller_worker", amp_ssh_access_allowed=False)
        self.conf.config(
            group="controller_worker", user_data_config_drive=False)

        # Test execute()
        compute_id = createcompute.execute(_amphora_mock.id, ports=[_port],
                                           server_group_id=SERVER_GRPOUP_ID)

        # Validate that the build method was called properly
        mock_driver.build.assert_called_once_with(
            name="amphora-" + _amphora_mock.id,
            amphora_flavor=AMP_FLAVOR_ID,
            image_id=AMP_IMAGE_ID,
            image_tag=AMP_IMAGE_TAG,
            image_owner='',
            key_name=None,
            sec_groups=AMP_SEC_GROUPS,
            network_ids=AMP_NET,
            port_ids=[PORT_ID],
            config_drive_files={'/etc/octavia/'
                                'amphora-agent.conf': 'test_conf'},
            user_data=None,
            server_group_id=SERVER_GRPOUP_ID)

        self.assertEqual(COMPUTE_ID, compute_id)

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
        path = '/etc/octavia/certs/ca_01.pem'
        self.useFixture(test_utils.OpenFixture(path, 'test'))

        # Test execute()
        compute_id = createcompute.execute(_amphora_mock.id, 'test_cert',
                                           server_group_id=SERVER_GRPOUP_ID
                                           )

        # Validate that the build method was called properly
        mock_driver.build.assert_called_once_with(
            name="amphora-" + _amphora_mock.id,
            amphora_flavor=AMP_FLAVOR_ID,
            image_id=AMP_IMAGE_ID,
            image_tag=AMP_IMAGE_TAG,
            image_owner='',
            key_name=AMP_SSH_KEY_NAME,
            sec_groups=AMP_SEC_GROUPS,
            network_ids=AMP_NET,
            port_ids=[],
            user_data=None,
            config_drive_files={
                '/etc/octavia/certs/server.pem': 'test_cert',
                '/etc/octavia/certs/client_ca.pem': 'test',
                '/etc/octavia/amphora-agent.conf': 'test_conf'},
            server_group_id=SERVER_GRPOUP_ID)

        self.assertEqual(COMPUTE_ID, compute_id)

        # Test that a build exception is raised
        self.useFixture(test_utils.OpenFixture(path, 'test'))

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
        mock_driver.delete.assert_called_once_with(COMPUTE_ID)

        # Test that a delete exception is not raised

        createcompute.revert(COMPUTE_ID, _amphora_mock.id)

    @mock.patch('octavia.controller.worker.amphora_rate_limit'
                '.AmphoraBuildRateLimit.remove_from_build_req_queue')
    @mock.patch('stevedore.driver.DriverManager.driver')
    @mock.patch('time.sleep')
    def test_compute_wait(self,
                          mock_time_sleep,
                          mock_driver,
                          mock_remove_from_build_queue):

        self.conf.config(group='haproxy_amphora', build_rate_limit=5)
        _amphora_mock.compute_id = COMPUTE_ID
        _amphora_mock.status = constants.ACTIVE
        _amphora_mock.lb_network_ip = LB_NET_IP

        mock_driver.get_amphora.return_value = _amphora_mock, None

        computewait = compute_tasks.ComputeWait()
        computewait.execute(COMPUTE_ID, AMPHORA_ID)

        mock_driver.get_amphora.assert_called_once_with(COMPUTE_ID)

        _amphora_mock.status = constants.DELETED

        self.assertRaises(exceptions.ComputeWaitTimeoutException,
                          computewait.execute,
                          _amphora_mock, AMPHORA_ID)

    @mock.patch('octavia.controller.worker.amphora_rate_limit'
                '.AmphoraBuildRateLimit.remove_from_build_req_queue')
    @mock.patch('stevedore.driver.DriverManager.driver')
    @mock.patch('time.sleep')
    def test_compute_wait_error_status(self,
                                       mock_time_sleep,
                                       mock_driver,
                                       mock_remove_from_build_queue):

        self.conf.config(group='haproxy_amphora', build_rate_limit=5)
        _amphora_mock.compute_id = COMPUTE_ID
        _amphora_mock.status = constants.ACTIVE
        _amphora_mock.lb_network_ip = LB_NET_IP

        mock_driver.get_amphora.return_value = _amphora_mock, None

        computewait = compute_tasks.ComputeWait()
        computewait.execute(COMPUTE_ID, AMPHORA_ID)

        mock_driver.get_amphora.assert_called_once_with(COMPUTE_ID)

        _amphora_mock.status = constants.ERROR

        self.assertRaises(exceptions.ComputeBuildException,
                          computewait.execute,
                          _amphora_mock, AMPHORA_ID)

    @mock.patch('octavia.controller.worker.amphora_rate_limit'
                '.AmphoraBuildRateLimit.remove_from_build_req_queue')
    @mock.patch('stevedore.driver.DriverManager.driver')
    @mock.patch('time.sleep')
    def test_compute_wait_skipped(self,
                                  mock_time_sleep,
                                  mock_driver,
                                  mock_remove_from_build_queue):
        _amphora_mock.compute_id = COMPUTE_ID
        _amphora_mock.status = constants.ACTIVE
        _amphora_mock.lb_network_ip = LB_NET_IP

        mock_driver.get_amphora.return_value = _amphora_mock, None

        computewait = compute_tasks.ComputeWait()
        computewait.execute(COMPUTE_ID, AMPHORA_ID)

        mock_driver.get_amphora.assert_called_once_with(COMPUTE_ID)
        mock_remove_from_build_queue.assert_not_called()

    @mock.patch('stevedore.driver.DriverManager.driver')
    def test_delete_amphorae_on_load_balancer(self, mock_driver):

        delete_amps = compute_tasks.DeleteAmphoraeOnLoadBalancer()
        delete_amps.execute(_load_balancer_mock)

        mock_driver.delete.assert_called_once_with(COMPUTE_ID)

    @mock.patch('stevedore.driver.DriverManager.driver')
    def test_compute_delete(self, mock_driver):

        delete_compute = compute_tasks.ComputeDelete()
        delete_compute.execute(_amphora_mock)

        mock_driver.delete.assert_called_once_with(COMPUTE_ID)

    @mock.patch('stevedore.driver.DriverManager.driver')
    def test_nova_server_group_create(self, mock_driver):
        nova_sever_group_obj = compute_tasks.NovaServerGroupCreate()

        server_group_test_id = '6789'
        fake_server_group = mock.MagicMock()
        fake_server_group.id = server_group_test_id
        fake_server_group.policy = 'anti-affinity'
        mock_driver.create_server_group.return_value = fake_server_group

        # Test execute()
        sg_id = nova_sever_group_obj.execute('123')

        # Validate that the build method was called properly
        mock_driver.create_server_group.assert_called_once_with(
            'octavia-lb-123', 'anti-affinity')

        # Make sure it returns the expected server group_id
        self.assertEqual(server_group_test_id, sg_id)

        # Test revert()
        nova_sever_group_obj.revert(sg_id)

        # Validate that the delete_server_group method was called properly
        mock_driver.delete_server_group.assert_called_once_with(sg_id)

        # Test revert with exception
        mock_driver.reset_mock()
        mock_driver.delete_server_group.side_effect = Exception('DelSGExcept')
        nova_sever_group_obj.revert(sg_id)
        mock_driver.delete_server_group.assert_called_once_with(sg_id)

    @mock.patch('stevedore.driver.DriverManager.driver')
    def test_nova_server_group_delete_with_sever_group_id(self, mock_driver):
        nova_sever_group_obj = compute_tasks.NovaServerGroupDelete()
        sg_id = '6789'
        nova_sever_group_obj.execute(sg_id)
        mock_driver.delete_server_group.assert_called_once_with(sg_id)

    @mock.patch('stevedore.driver.DriverManager.driver')
    def test_nova_server_group_delete_with_None(self, mock_driver):
        nova_sever_group_obj = compute_tasks.NovaServerGroupDelete()
        sg_id = None
        nova_sever_group_obj.execute(sg_id)
        self.assertFalse(mock_driver.delete_server_group.called, sg_id)
