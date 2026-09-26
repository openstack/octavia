# Copyright 2016 IBM Corp.
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

import mock
from oslo_utils import uuidutils
import requests_mock

from octavia.amphorae.drivers.haproxy import exceptions as exc
from octavia.common import data_models
from octavia.db import models
from octavia.distributor.drivers.ovs_driver import rest_api_driver as driver
from octavia.network import data_models as network_models
from octavia.tests.common import data_model_helpers as dmh
from octavia.tests.unit import base as base


FAKE_CIDR = '10.0.0.0/24'
FAKE_GATEWAY = '10.0.0.1'
FAKE_IP = 'fake'
FAKE_PEM_FILENAME = "file_name"
FAKE_SUBNET_INFO = {'subnet_cidr': FAKE_CIDR,
                    'gateway': FAKE_GATEWAY,
                    'mac_address': '123'}
FAKE_UUID_1 = uuidutils.generate_uuid()
FAKE_VRRP_IP = '10.1.0.1'

SUBNET_ID_1 = "5"
PORT_ID = uuidutils.generate_uuid()


class TestOVSDistributorDriverTest(base.TestCase):

    def setUp(self):
        super(TestOVSDistributorDriverTest, self).setUp()
        # Do not initialize the real Neutron driver in a unit test. Its
        # constructor resolves an OpenStack SDK session and therefore needs
        # deployment credentials and a service catalog.
        with mock.patch.object(driver.stevedore_driver, 'DriverManager') \
                as driver_manager:
            driver_manager.return_value.driver = mock.Mock()
            self.driver = driver.OVSDistributorDriver()
        self.driver.client = mock.MagicMock()
        self.driver.network_driver = self

        # Build sample Listener and VIP configs
        self.lb = dmh.generate_load_balancer_tree()
        self.amp = self.lb.amphorae[0]
        self.distributor = data_models.Distributor()
        self.vip = self.lb.vip
        self.alg_extras = "some_extras"
        self.port = network_models.Port(mac_address='123')
        self.subnet = network_models.Subnet(cidr=FAKE_CIDR,
                                            gateway_ip=FAKE_GATEWAY)
        self.cluster_alg_type = "TEST"
        self.cluster_min_size = 0

    def get_subnet(self, subnet_id):
        return self.subnet

    def get_port(self, port_id):
        return self.port

    def test_get_info(self):
        self.driver.get_info(self.distributor)
        self.driver.client.get_info.assert_called_once_with(
            self.distributor)

    def test_get_diagnostics(self):
        self.driver.get_diagnostics(self.distributor)
        self.driver.client.get_diagnostics.assert_called_once_with(
            self.distributor)

    def test_post_vip_plug(self):
        extras = {'subnet_cidr': self.subnet.cidr,
                  'gateway': self.subnet.gateway_ip,
                  'mac_address': self.port.mac_address,
                  'interface': 'auto',
                  'lb_id': self.lb.id,
                  'cluster_alg_type': self.cluster_alg_type,
                  'cluster_min_size': self.cluster_min_size}

        self.driver.post_vip_plug(self.distributor, self.lb,
                                  self.port.mac_address,
                                  self.cluster_alg_type, self.cluster_min_size)
        self.driver.client.post_plug_vip.assert_called_once_with(
            self.distributor, self.lb.vip.ip_address, extras)

    def test_pre_vip_unplug(self):
        extras = {'lb_id': self.lb.id}
        self.driver.pre_vip_unplug(self.distributor, self.lb)
        self.driver.client.pre_unplug_vip.assert_called_once_with(
            self.distributor, self.lb.vip.ip_address, extras)

    def test_register_amphora(self):
        extras = {'subnet_cidr': self.subnet.cidr,
                  'gateway': self.subnet.gateway_ip,
                  'lb_id': self.lb.id,
                  'amphora_id': self.amp.id,
                  'amphora_mac': self.port.mac_address,
                  'cluster_alg_type': self.cluster_alg_type,
                  'cluster_min_size': self.cluster_min_size}
        self.driver.register_amphora(self.distributor, self.lb,
                                     self.amp, self.cluster_alg_type,
                                     self.cluster_min_size)
        self.driver.client.register_amphora.assert_called_once_with(
            self.distributor, self.lb.vip.ip_address, extras)

    def test_unregister_amphora(self):
        extras = {'subnet_cidr': self.subnet.cidr,
                  'gateway': self.subnet.gateway_ip,
                  'lb_id': self.lb.id,
                  'amphora_id': self.amp.id,
                  'cluster_alg_type': self.cluster_alg_type,
                  'cluster_min_size': self.cluster_min_size}
        self.driver.unregister_amphora(self.distributor, self.lb,
                                       self.amp, self.cluster_alg_type,
                                       self.cluster_min_size)
        self.driver.client.unregister_amphora.assert_called_once_with(
            self.distributor, self.lb.vip.ip_address, extras)


class TestDistributorAPIClientTest(base.TestCase):

    def setUp(self):
        super(TestDistributorAPIClientTest, self).setUp()
        self.driver = driver.DistributorAPIClient()
        self.base_url = "https://127.0.0.1:9442/0.5"
        self.dist = models.Distributor(lb_network_ip='127.0.0.1',
                                       compute_id='123')
        self.port_info = dict(mac_address='123')
        self.vip = '10.0.0.10'

    @requests_mock.mock()
    def test_get_info(self, m):
        info = {"hostname": "some_hostname", "version": "some_version",
                "api_version": "0.5", "uuid": FAKE_UUID_1}
        m.get("{base}/info".format(base=self.base_url),
              json=info)
        information = self.driver.get_info(self.dist)
        self.assertEqual(info, information)

    @requests_mock.mock()
    def test_get_info_unauthorized(self, m):
        m.get("{base}/info".format(base=self.base_url),
              status_code=401)
        self.assertRaises(exc.Unauthorized, self.driver.get_info, self.dist)

    @requests_mock.mock()
    def test_get_info_missing(self, m):
        m.get("{base}/info".format(base=self.base_url),
              status_code=404)
        self.assertRaises(exc.NotFound, self.driver.get_info, self.dist)

    @requests_mock.mock()
    def test_get_info_service_unavailable(self, m):
        m.get("{base}/info".format(base=self.base_url),
              status_code=503)
        self.assertRaises(exc.ServiceUnavailable, self.driver.get_info,
                          self.dist)

    @requests_mock.mock()
    def test_get_diagnostics(self, m):
        details = {"hostname": "some_hostname", "version": "some_version",
                   "api_version": "0.5", "uuid": FAKE_UUID_1,
                   "network_tx": "some_tx", "network_rx": "some_rx",
                   "active": True, "lb_count": 10}
        m.get("{base}/diagnostics".format(base=self.base_url),
              json=details)
        dist_details = self.driver.get_diagnostics(self.dist)
        self.assertEqual(details, dist_details)

    @requests_mock.mock()
    def test_get_diagnostics_unauthorized(self, m):
        m.get("{base}/diagnostics".format(base=self.base_url),
              status_code=401)
        self.assertRaises(exc.Unauthorized, self.driver.get_diagnostics,
                          self.dist)

    @requests_mock.mock()
    def test_get_diagnostics_missing(self, m):
        m.get("{base}/diagnostics".format(base=self.base_url),
              status_code=404)
        self.assertRaises(exc.NotFound, self.driver.get_diagnostics,
                          self.dist)

    @requests_mock.mock()
    def test_get_diagnostics_server_error(self, m):
        m.get("{base}/diagnostics".format(base=self.base_url),
              status_code=500)
        self.assertRaises(exc.InternalServerError, self.driver.get_diagnostics,
                          self.dist)

    @requests_mock.mock()
    def test_get_diagnostics_service_unavailable(self, m):
        m.get("{base}/diagnostics".format(base=self.base_url),
              status_code=503)
        self.assertRaises(exc.ServiceUnavailable, self.driver.get_diagnostics,
                          self.dist)

    @requests_mock.mock()
    def test_post_plug_vip(self, m):
        m.post("{base}/plug/vip/{vip}".format(base=self.base_url,
                                              vip=self.vip),
               status_code=200)
        self.driver.post_plug_vip(self.dist, self.vip, {})
        self.assertTrue(m.called)

    @requests_mock.mock()
    def test_post_plug_vip_unauthorized(self, m):
        m.post("{base}/plug/vip/{vip}".format(base=self.base_url,
                                              vip=self.vip),
               status_code=401)
        self.assertRaises(exc.Unauthorized, self.driver.post_plug_vip,
                          self.dist, self.vip, {})

    @requests_mock.mock()
    def test_post_plug_vip_server_error(self, m):
        m.post("{base}/plug/vip/{vip}".format(base=self.base_url,
                                              vip=self.vip),
               status_code=500)
        self.assertRaises(exc.InternalServerError, self.driver.post_plug_vip,
                          self.dist, self.vip, {})

    @requests_mock.mock()
    def test_post_plug_vip_service_unavailable(self, m):
        m.post("{base}/plug/vip/{vip}".format(base=self.base_url,
                                              vip=self.vip),
               status_code=503)
        self.assertRaises(exc.ServiceUnavailable, self.driver.post_plug_vip,
                          self.dist, self.vip, {})

    @requests_mock.mock()
    def test_post_plug_vip_missing(self, m):
        m.post("{base}/plug/vip/{vip}".format(base=self.base_url,
                                              vip=self.vip),
               status_code=404)
        self.assertRaises(exc.NotFound, self.driver.post_plug_vip,
                          self.dist, self.vip, {})

    @requests_mock.mock()
    def test_post_plug_vip_invalid_values(self, m):
        m.post("{base}/plug/vip/{vip}".format(base=self.base_url,
                                              vip=self.vip),
               status_code=400)
        self.assertRaises(exc.InvalidRequest, self.driver.post_plug_vip,
                          self.dist, self.vip, {})

    @requests_mock.mock()
    def test_pre_unplug_vip(self, m):
        m.post("{base}/unplug/vip/{vip}".format(base=self.base_url,
                                                vip=self.vip),
               status_code=200)
        self.driver.pre_unplug_vip(self.dist, self.vip, {})
        self.assertTrue(m.called)

    @requests_mock.mock()
    def test_pre_unplug_vip_unauthorized(self, m):
        m.post("{base}/unplug/vip/{vip}".format(base=self.base_url,
                                                vip=self.vip),
               status_code=401)
        self.assertRaises(exc.Unauthorized, self.driver.pre_unplug_vip,
                          self.dist, self.vip, {})

    @requests_mock.mock()
    def test_pre_unplug_vip_server_error(self, m):
        m.post("{base}/unplug/vip/{vip}".format(base=self.base_url,
                                                vip=self.vip),
               status_code=500)
        self.assertRaises(exc.InternalServerError, self.driver.pre_unplug_vip,
                          self.dist, self.vip, {})

    @requests_mock.mock()
    def test_pre_unplug_vip_service_unavailable(self, m):
        m.post("{base}/unplug/vip/{vip}".format(base=self.base_url,
                                                vip=self.vip),
               status_code=503)
        self.assertRaises(exc.ServiceUnavailable, self.driver.pre_unplug_vip,
                          self.dist, self.vip, {})

    @requests_mock.mock()
    def test_pre_unplug_missing(self, m):
        m.post("{base}/unplug/vip/{vip}".format(base=self.base_url,
                                                vip=self.vip),
               status_code=404)
        self.assertRaises(exc.NotFound, self.driver.pre_unplug_vip,
                          self.dist, self.vip, {})

    @requests_mock.mock()
    def test_pre_unplug_vip_invalid_values(self, m):
        m.post("{base}/unplug/vip/{vip}".format(base=self.base_url,
                                                vip=self.vip),
               status_code=400)
        self.assertRaises(exc.InvalidRequest, self.driver.pre_unplug_vip,
                          self.dist, self.vip, {})

    @requests_mock.mock()
    def test_register_amphora(self, m):
        m.post("{base}/register/vip/{vip}".format(base=self.base_url,
                                                  vip=self.vip),
               status_code=200)
        self.driver.register_amphora(self.dist, self.vip, {})
        self.assertTrue(m.called)

    @requests_mock.mock()
    def test_register_amphora_unauthorized(self, m):
        m.post("{base}/register/vip/{vip}".format(base=self.base_url,
                                                  vip=self.vip),
               status_code=401)
        self.assertRaises(exc.Unauthorized, self.driver.register_amphora,
                          self.dist, self.vip, {})

    @requests_mock.mock()
    def test_register_amphora_server_error(self, m):
        m.post("{base}/register/vip/{vip}".format(base=self.base_url,
                                                  vip=self.vip),
               status_code=500)
        self.assertRaises(exc.InternalServerError,
                          self.driver.register_amphora, self.dist,
                          self.vip, {})

    @requests_mock.mock()
    def test_register_amphora_service_unavailable(self, m):
        m.post("{base}/register/vip/{vip}".format(base=self.base_url,
                                                  vip=self.vip),
               status_code=503)
        self.assertRaises(exc.ServiceUnavailable, self.driver.register_amphora,
                          self.dist, self.vip, {})

    @requests_mock.mock()
    def test_register_amphora_missing(self, m):
        m.post("{base}/register/vip/{vip}".format(base=self.base_url,
                                                  vip=self.vip),
               status_code=404)
        self.assertRaises(exc.NotFound, self.driver.register_amphora,
                          self.dist, self.vip, {})

    @requests_mock.mock()
    def test_register_amphora_invalid_values(self, m):
        m.post("{base}/register/vip/{vip}".format(base=self.base_url,
                                                  vip=self.vip),
               status_code=400)
        self.assertRaises(exc.InvalidRequest, self.driver.register_amphora,
                          self.dist, self.vip, {})

    @requests_mock.mock()
    def test_unregister_amphora(self, m):
        m.post("{base}/unregister/vip/{vip}".format(base=self.base_url,
                                                    vip=self.vip),
               status_code=200)
        self.driver.unregister_amphora(self.dist, self.vip, {})
        self.assertTrue(m.called)

    @requests_mock.mock()
    def test_unregister_amphora_unauthorized(self, m):
        m.post("{base}/unregister/vip/{vip}".format(base=self.base_url,
                                                    vip=self.vip),
               status_code=401)
        self.assertRaises(exc.Unauthorized, self.driver.unregister_amphora,
                          self.dist, self.vip, {})

    @requests_mock.mock()
    def test_unregister_amphora_server_error(self, m):
        m.post("{base}/unregister/vip/{vip}".format(base=self.base_url,
                                                    vip=self.vip),
               status_code=500)
        self.assertRaises(exc.InternalServerError,
                          self.driver.unregister_amphora,
                          self.dist, self.vip, {})

    @requests_mock.mock()
    def test_unregister_amphora_service_unavailable(self, m):
        m.post("{base}/unregister/vip/{vip}".format(base=self.base_url,
                                                    vip=self.vip),
               status_code=503)
        self.assertRaises(exc.ServiceUnavailable,
                          self.driver.unregister_amphora, self.dist,
                          self.vip, {})

    @requests_mock.mock()
    def test_unregister_amphora_missing(self, m):
        m.post("{base}/unregister/vip/{vip}".format(base=self.base_url,
                                                    vip=self.vip),
               status_code=404)
        self.assertRaises(exc.NotFound, self.driver.unregister_amphora,
                          self.dist, self.vip, {})

    @requests_mock.mock()
    def test_unregister_amphora_invalid_values(self, m):
        m.post("{base}/unregister/vip/{vip}".format(base=self.base_url,
                                                    vip=self.vip),
               status_code=400)
        self.assertRaises(exc.InvalidRequest, self.driver.unregister_amphora,
                          self.dist, self.vip, {})
