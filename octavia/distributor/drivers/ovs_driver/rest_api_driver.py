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

import functools
import time

from oslo_log import log as logging
import requests
import six
from stevedore import driver as stevedore_driver
from taskflow.patterns import linear_flow

from octavia.amphorae.driver_exceptions import exceptions as driver_except
from octavia.amphorae.drivers.haproxy import exceptions as exc
from octavia.common.config import cfg
from octavia.distributor.drivers import driver_base as driver_base
from octavia.controller.worker.v2.tasks import distributor_tasks
from octavia.i18n import _

LOG = logging.getLogger(__name__)
API_VERSION = '0.5'
OCTAVIA_API_CLIENT = (
    "Octavia Distributor Rest Client/{version} "
    "(https://wiki.openstack.org/wiki/Octavia)").format(version=API_VERSION)
CONF = cfg.CONF
CONF.import_group('distributor', 'octavia.common.config')
CONF.import_group('haproxy_amphora', 'octavia.common.config')


class OVSDistributorDriver(driver_base.DistributorDriver):
    def __init__(self):
        super(OVSDistributorDriver, self).__init__()
        self.client = DistributorAPIClient()
        self.network_driver = stevedore_driver.DriverManager(
            namespace='octavia.network.drivers',
            name=CONF.controller_worker.network_driver,
            invoke_on_load=True
        ).driver

    def get_info(self, distributor):
        return self.client.get_info(distributor)

    def get_diagnostics(self, distributor):
        return self.client.get_diagnostics(distributor)

    def get_create_distributor_subflow(self):
        return linear_flow.Flow('ovs-create-distributor')

    def get_delete_distributor_subflow(self):
        return linear_flow.Flow('ovs-delete-distributor')

    def get_add_vip_subflow(self):
        flow = linear_flow.Flow('ovs-add-vip')
        flow.add(distributor_tasks.DistributorAddVIP(
            self, requires=('distributor_id', 'loadbalancer', 'vip')))
        return flow

    def get_remove_vip_subflow(self):
        flow = linear_flow.Flow('ovs-remove-vip')
        flow.add(distributor_tasks.DistributorRemoveVIP(
            self, requires=('distributor_id', 'loadbalancer')))
        return flow

    def get_register_amphorae_subflow(self):
        flow = linear_flow.Flow('ovs-register-amphorae')
        flow.add(distributor_tasks.DistributorRegisterAmphorae(
            self, requires=('distributor_id', 'loadbalancer', 'amphorae')))
        return flow

    def get_drain_amphorae_subflow(self):
        return linear_flow.Flow('ovs-drain-amphorae')

    def get_unregister_amphorae_subflow(self):
        flow = linear_flow.Flow('ovs-unregister-amphorae')
        flow.add(distributor_tasks.DistributorUnregisterAmphorae(
            self, requires=('distributor_id', 'loadbalancer', 'amphorae')))
        return flow

    def post_vip_plug(self, distributor, load_balancer, distributor_mac,
                      cluster_alg_type, cluster_min_size):
        subnet = self.network_driver.get_subnet(load_balancer.vip.subnet_id)
        extras = {'subnet_cidr': subnet.cidr,
                  'gateway': subnet.gateway_ip,
                  'mac_address': distributor_mac,
                  'interface': CONF.distributor.frontend_interface,
                  'lb_id': load_balancer.id,
                  'cluster_alg_type': cluster_alg_type,
                  'cluster_min_size': cluster_min_size}
        LOG.debug("OVS_DRIVER / REST / post_vip_plug with json: [%s]",
                  repr(extras))
        try:
            self.client.post_plug_vip(distributor,
                                      load_balancer.vip.ip_address,
                                      extras)
        except Exception as e:
            LOG.debug("post_vip_plug failed: %s", e)
            raise

    def pre_vip_unplug(self, distributor, load_balancer):
        extras = {'lb_id': load_balancer.id}
        LOG.debug("OVS_DRIVER / REST / pre_vip_unplug with json: [%s]",
                  repr(extras))
        try:
            self.client.pre_unplug_vip(distributor,
                                       load_balancer.vip.ip_address,
                                       extras)
        except Exception as e:
            LOG.debug("pre_vip_unplug failed: %s", e)
            raise

    def register_amphora(self, distributor, load_balancer, amphora,
                         cluster_alg_type, cluster_min_size):
        subnet = self.network_driver.get_subnet(load_balancer.vip.subnet_id)
        amphora_mac = self.network_driver.get_port(
            amphora.vrrp_port_id).mac_address
        extras = {'subnet_cidr': subnet.cidr,
                  'gateway': subnet.gateway_ip,
                  'lb_id': load_balancer.id,
                  'amphora_id': amphora.id,
                  'amphora_mac': amphora_mac,
                  'cluster_alg_type': cluster_alg_type,
                  'cluster_min_size': cluster_min_size}
        LOG.debug("OVS_DRIVER / REST / register_amphora with json: [%s]",
                  repr(extras))
        try:
            self.client.register_amphora(distributor,
                                         load_balancer.vip.ip_address,
                                         extras)
        except Exception as e:
            LOG.debug("register_amphora failed: %s", e)
            raise

    def unregister_amphora(self, distributor, load_balancer, amphora,
                           cluster_alg_type, cluster_min_size):
        subnet = self.network_driver.get_subnet(load_balancer.vip.subnet_id)
        extras = {'subnet_cidr': subnet.cidr,
                  'gateway': subnet.gateway_ip,
                  'lb_id': load_balancer.id,
                  'amphora_id': amphora.id,
                  'cluster_alg_type': cluster_alg_type,
                  'cluster_min_size': cluster_min_size}
        LOG.debug("OVS_DRIVER / REST / unregister_amphora with json: [%s]",
                  repr(extras))
        try:
            self.client.unregister_amphora(distributor,
                                           load_balancer.vip.ip_address,
                                           extras)
        except Exception as e:
            LOG.debug("unregister_amphora failed: %s", e)
            raise


# Check a custom hostname
class CustomHostNameCheckingAdapter(requests.adapters.HTTPAdapter):
    def cert_verify(self, conn, url, verify, cert):
        conn.assert_hostname = self.uuid
        return super(CustomHostNameCheckingAdapter,
                     self).cert_verify(conn, url, verify, cert)


class DistributorAPIClient(object):
    def __init__(self):
        super(DistributorAPIClient, self).__init__()

        self.get = functools.partial(self.request, 'get')
        self.post = functools.partial(self.request, 'post')
        self.put = functools.partial(self.request, 'put')
        self.delete = functools.partial(self.request, 'delete')
        self.head = functools.partial(self.request, 'head')

        self.session = requests.Session()
        self.session.cert = CONF.distributor.client_cert
        self.ssl_adapter = CustomHostNameCheckingAdapter()
        self.session.mount('https://', self.ssl_adapter)

    def _base_url(self, ip):
        return "https://{ip}:{port}/{version}/".format(
            ip=ip,
            port=CONF.distributor.bind_port,
            version=API_VERSION)

    def request(self, method, distributor, path='/', **kwargs):

        if isinstance(distributor, tuple):
            dist = distributor[0]
        else:
            dist = distributor
        _request = getattr(self.session, method.lower())
        _url = self._base_url(dist.lb_network_ip) + path

        LOG.debug("OVS_DRIVER / REST / Request [%s] from url [%s]",
                  method,
                  _url)

        reqargs = {
            'verify': CONF.distributor.client_ca,
            'url': _url, }
        reqargs.update(kwargs)
        headers = reqargs.setdefault('headers', {})

        headers['User-Agent'] = OCTAVIA_API_CLIENT
        self.ssl_adapter.uuid = dist.id
        # Keep retrying
        for a in six.moves.xrange(CONF.haproxy_amphora.connection_max_retries):
            try:
                r = _request(**reqargs)
            except requests.ConnectionError:
                LOG.warning(_("Could not talk to distributor instance"))
                time.sleep(CONF.haproxy_amphora.connection_retry_interval)
                if a >= CONF.haproxy_amphora.connection_max_retries:
                    raise driver_except.TimeOutException()
            else:
                LOG.debug("OVS_DRIVER / REST / "
                          "Got response {resp}".format(resp=r))
                return r
        raise driver_except.UnavailableException()

    def get_info(self, distributor):
        r = self.get(distributor, "info")
        if exc.check_exception(r):
            return r.json()

    def get_diagnostics(self, distributor):
        r = self.get(distributor, "diagnostics")
        if exc.check_exception(r):
            return r.json()

    def post_plug_vip(self, distributor, vip, extras):
        """Called after network driver has allocated and plugged the VIP

        :param distributor: distributor object, need to use its id property
        :type distributor: object

        :param vip: IP address of VIP
        :type vip: String

        :param extras: json object holding following sections:
                  (a) port_info - {MAC, subnet_cidr, gateway}
                  (b) lb_id - unique IF of LoadBalancer
                  (c) algorithm extras defined by the specific topology manager
        :returns: None
        """
        r = self.post(distributor,
                      'plug/vip/{vip}'.format(vip=vip),
                      json=extras)
        return exc.check_exception(r)

    def pre_unplug_vip(self, distributor, vip, extras):
        """Called before network driver has deallocated and unplugged the VIP

        :param distributor: distributor object, need to use its id property
        :type distributor: object

        :param vip: IP address of VIP
        :type vip: String

        :param extras: json object holding following sections:
                  lb_id - unique ID of LoadBalancer

        :returns: None
        """
        r = self.post(distributor,
                      'unplug/vip/{vip}'.format(vip=vip),
                      json=extras)
        return exc.check_exception(r)

    def register_amphora(self, distributor, vip, extras):
        """Called after amphora is configured and ready

        :param distributor: distributor object, need to use its id property
        :type distributor: object

        :param vip: IP address of VIP
        :type vip: String

        :param extras: json object holding following sections:
                  (a) port_info - {subnet_cidr, gateway}
                  (b) lb_id - unique ID of LoadBalancer
                  (c) amphora_info - includes amphora_id and amphora_mac
                  (d) algorithm extras defined by the specific topology manager
        :returns: None
        """
        r = self.post(distributor,
                      'register/vip/{vip}'.format(vip=vip),
                      json=extras)
        return exc.check_exception(r)

    def unregister_amphora(self, distributor, vip, extras):
        """Called after amphora is configured and ready

        :param distributor: distributor object, need to use its id property
        :type distributor: object

        :param vip: IP address of VIP
        :type vip: String

        :param extras: json object holding following sections:
                  (a) port_info - {subnet_cidr, gateway}
                  (b) lb_id - unique ID of LoadBalancer
                  (c) amphora_info - amphora_id only
                  (d) algorithm extras defined by the specific topology manager
        :returns: None
        """
        r = self.post(distributor,
                      'unregister/vip/{vip}'.format(vip=vip),
                      json=extras)
        return exc.check_exception(r)
