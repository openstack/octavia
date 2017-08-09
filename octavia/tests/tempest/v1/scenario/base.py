# Copyright 2016 Rackspace Inc.
# All Rights Reserved.
#
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

try:
    from http import cookiejar as cookielib
except ImportError:
    import cookielib
import os
import shlex
import shutil
import socket
import subprocess
import tempfile
import threading
import time

from oslo_log import log as logging
import six
from six.moves.urllib import error
from six.moves.urllib import request as urllib2
from tempest import clients
from tempest.common import credentials_factory
from tempest.common import waiters
from tempest import config
from tempest.lib.common.utils import test_utils
from tempest.lib import exceptions as lib_exc
from tempest import test


from octavia.i18n import _
from octavia.tests.tempest.common import manager
from octavia.tests.tempest.v1.clients import health_monitors_client
from octavia.tests.tempest.v1.clients import listeners_client
from octavia.tests.tempest.v1.clients import load_balancers_client
from octavia.tests.tempest.v1.clients import members_client
from octavia.tests.tempest.v1.clients import pools_client
from octavia.tests.tempest.v1.clients import quotas_client

config = config.CONF

LOG = logging.getLogger(__name__)
HTTPD_SRC = os.path.abspath(
    os.path.join(os.path.dirname(__file__),
                 '../../../contrib/httpd.go'))


class BaseTestCase(manager.NetworkScenarioTest):

    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.servers_keypairs = {}
        self.servers = {}
        self.members = []
        self.floating_ips = {}
        self.servers_floating_ips = {}
        self.server_ips = {}
        self.start_port = 80
        self.num = 50
        self.server_fixed_ips = {}

        mgr = self.get_client_manager()

        auth_provider = mgr.auth_provider
        region = config.network.region or config.identity.region
        self.client_args = [auth_provider, 'load-balancer', region]
        self.load_balancers_client = (
            load_balancers_client.LoadBalancersClient(*self.client_args))
        self.listeners_client = (
            listeners_client.ListenersClient(*self.client_args))
        self.pools_client = pools_client.PoolsClient(*self.client_args)
        self.members_client = members_client.MembersClient(
            *self.client_args)
        self.health_monitors_client = (
            health_monitors_client.HealthMonitorsClient(
                *self.client_args))
        self.quotas_client = quotas_client.QuotasClient(*self.client_args)

        self._create_security_group_for_test()
        self._set_net_and_subnet()

        # admin network client needed for assigning octavia port to flip
        os_admin = clients.Manager(
            credentials_factory.get_configured_admin_credentials())
        os_admin.auth_provider.fill_credentials()
        self.floating_ips_client_admin = os_admin.floating_ips_client
        self.ports_client_admin = os_admin.ports_client

    @classmethod
    def skip_checks(cls):
        super(BaseTestCase, cls).skip_checks()
        cfg = config.network
        if not test.is_extension_enabled('lbaasv2', 'network'):
            msg = 'LBaaS Extension is not enabled'
            raise cls.skipException(msg)
        if not (cfg.project_networks_reachable or cfg.public_network_id):
            msg = ('Either project_networks_reachable must be "true", or '
                   'public_network_id must be defined.')
            raise cls.skipException(msg)

    def _set_net_and_subnet(self):
        """Set Network and Subnet

        Query and set appropriate network and subnet attributes to be used
        for the test. Existing tenant networks are used if they are found.
        The configured private network and associated subnet is used as a
        fallback in absence of tenant networking.
        """
        tenant_id = self.load_balancers_client.tenant_id
        try:
            tenant_net = self.os_admin.networks_client.list_networks(
                tenant_id=tenant_id)['networks'][0]
        except IndexError:
            tenant_net = None

        if tenant_net:
            tenant_subnet = self.os_admin.subnets_client.list_subnets(
                tenant_id=tenant_id)['subnets'][0]
            self.subnet = tenant_subnet
            self.network = tenant_net
        else:
            self.network = self._get_network_by_name(
                config.compute.fixed_network_name)
            # We are assuming that the first subnet associated
            # with the fixed network is the one we want.  In the future, we
            # should instead pull a subnet id from config, which is set by
            # devstack/admin/etc.
            subnet = self.os_admin.subnets_client.list_subnets(
                network_id=self.network['id'])['subnets'][0]
            self.subnet = subnet

    def _create_security_group_for_test(self):
        self.security_group = self._create_security_group(
            tenant_id=self.load_balancers_client.tenant_id)
        self._create_security_group_rules_for_port(self.start_port)
        self._create_security_group_rules_for_port(self.start_port + 1)

    def _create_security_group_rules_for_port(self, port):
        rule = {
            'direction': 'ingress',
            'protocol': 'tcp',
            'port_range_min': port,
            'port_range_max': port,
        }
        self._create_security_group_rule(
            secgroup=self.security_group,
            tenant_id=self.load_balancers_client.tenant_id,
            **rule)

    def _ipv6_subnet(self, address6_mode):
        tenant_id = self.load_balancers_client.tenant_id
        router = self._get_router(tenant_id=tenant_id)
        self.network = self._create_network(tenant_id=tenant_id)
        self.subnet = self._create_subnet(network=self.network,
                                          namestart='sub6',
                                          ip_version=6,
                                          ipv6_ra_mode=address6_mode,
                                          ipv6_address_mode=address6_mode)
        self.subnet.add_to_router(router_id=router['id'])
        self.addCleanup(self.subnet.delete)

    def _create_server(self, name):
        keypair = self.create_keypair()
        security_groups = [{'name': self.security_group['name']}]
        create_kwargs = {
            'networks': [
                {'uuid': self.network['id']},
            ],
            'key_name': keypair['name'],
            'security_groups': security_groups,
        }
        net_name = self.network['name']
        server = self.create_server(name=name, **create_kwargs)
        waiters.wait_for_server_status(self.servers_client,
                                       server['id'], 'ACTIVE')
        server = self.servers_client.show_server(server['id'])
        server = server['server']
        self.servers_keypairs[server['id']] = keypair

        LOG.info('servers_keypairs looks like this(format): %s',
                 self.servers_keypairs)

        if (config.network.public_network_id and not
                config.network.project_networks_reachable):
            public_network_id = config.network.public_network_id
            floating_ip = self._create_floating_ip(
                server, public_network_id)
            self.floating_ips[floating_ip['id']] = server
            self.server_ips[server['id']] = floating_ip['floating_ip_address']

        else:
            self.server_ips[server['id']] = (
                server['addresses'][net_name][0]['addr'])

        self.server_fixed_ips[server['id']] = (
            server['addresses'][net_name][0]['addr'])
        self.assertTrue(self.servers_keypairs)
        self.servers[name] = server['id']
        return server

    def _create_servers(self, num=2):
        for count in range(num):
            name = "server%s" % (count + 1)
            self.server = self._create_server(name=name)
        self.assertEqual(len(self.servers_keypairs), num)

    def _stop_server(self, name):
        for sname, value in six.iteritems(self.servers):
            if sname == name:
                LOG.info('STOPPING SERVER: %s', sname)
                self.servers_client.stop_server(value)
                waiters.wait_for_server_status(self.servers_client,
                                               value, 'SHUTOFF')
        LOG.info('STOPPING SERVER COMPLETED!')

    def _start_server(self, name):
        for sname, value in six.iteritems(self.servers):
            if sname == name:
                self.servers_client.start(value)
                waiters.wait_for_server_status(self.servers_client,
                                               value, 'ACTIVE')

    def _build_static_httpd(self):
        """Compile test httpd as a static binary

        returns file path of resulting binary file
        """
        builddir = tempfile.mkdtemp()
        shutil.copyfile(HTTPD_SRC, os.path.join(builddir, 'httpd.go'))
        self.execute('go build -ldflags '
                     '"-linkmode external -extldflags -static" '
                     'httpd.go', cwd=builddir)
        return os.path.join(builddir, 'httpd')

    def _start_backend_httpd_processes(self, backend, ports=None):
        """Start one or more webservers on a given backend server

        1. SSH to the backend
        2. Start http backends listening on the given ports
        """
        ports = ports or [80, 81]
        httpd = self._build_static_httpd()
        backend_id = self.servers[backend]
        for server_id, ip in six.iteritems(self.server_ips):
            if server_id != backend_id:
                continue
            private_key = self.servers_keypairs[server_id]['private_key']
            username = config.validation.image_ssh_user
            ssh_client = self.get_remote_client(
                ip_address=ip,
                private_key=private_key)

            with tempfile.NamedTemporaryFile() as key:
                key.write(private_key.encode('utf-8'))
                key.flush()
                self.copy_file_to_host(httpd,
                                       "/dev/shm/httpd",
                                       ip,
                                       username, key.name)

            # Start httpd
            start_server = ('sudo sh -c "ulimit -n 100000; screen -d -m '
                            '/dev/shm/httpd -id %(id)s -port %(port)s"')
            for i in range(len(ports)):
                cmd = start_server % {'id': backend + "_" + str(i),
                                      'port': ports[i]}
                ssh_client.exec_command(cmd)
            # Allow ssh_client connection to fall out of scope

    def _create_listener(self, load_balancer_id, default_pool_id=None):
        """Create a listener with HTTP protocol listening on port 80."""
        self.create_listener_kwargs = {'protocol': 'HTTP',
                                       'protocol_port': 80,
                                       'default_pool_id': default_pool_id}
        self.listener = self.listeners_client.create_listener(
            lb_id=load_balancer_id,
            **self.create_listener_kwargs)
        self.assertTrue(self.listener)
        self.addCleanup(self._cleanup_listener, self.listener['id'],
                        load_balancer_id)
        LOG.info('Waiting for lb status on create listener id: %s',
                 self.listener['id'])
        self._wait_for_load_balancer_status(load_balancer_id)

        return self.listener

    def _create_health_monitor(self):
        """Create a HTTP health monitor."""
        self.hm = self.health_monitors_client.create_health_monitor(
            type='HTTP', delay=3, timeout=5,
            fall_threshold=5, rise_threshold=5,
            lb_id=self.load_balancer['id'],
            pool_id=self.pool['id'])
        self.assertTrue(self.hm)
        self.addCleanup(self._cleanup_health_monitor,
                        pool_id=self.pool['id'],
                        load_balancer_id=self.load_balancer['id'])
        self._wait_for_load_balancer_status(self.load_balancer['id'])

        # add clean up members prior to clean up of health monitor
        # see bug 1547609
        members = self.members_client.list_members(self.load_balancer['id'],
                                                   self.pool['id'])
        self.assertTrue(members)
        for member in members:
            self.addCleanup(self._cleanup_member,
                            load_balancer_id=self.load_balancer['id'],
                            pool_id=self.pool['id'],
                            member_id=member['id'])

    def _create_pool(self, load_balancer_id,
                     persistence_type=None, cookie_name=None):
        """Create a pool with ROUND_ROBIN algorithm."""
        create_pool_kwargs = {
            'lb_algorithm': 'ROUND_ROBIN',
            'protocol': 'HTTP'
        }
        if persistence_type:
            create_pool_kwargs.update(
                {'session_persistence': {'type': persistence_type}})
        if cookie_name:
            create_pool_kwargs.update(
                {'session_persistence': {'cookie_name': cookie_name}})
        self.pool = self.pools_client.create_pool(lb_id=load_balancer_id,
                                                  **create_pool_kwargs)
        self.assertTrue(self.pool)
        self.addCleanup(self._cleanup_pool, self.pool['id'], load_balancer_id)
        LOG.info('Waiting for lb status on create pool id: %s',
                 self.pool['id'])
        self._wait_for_load_balancer_status(load_balancer_id)
        return self.pool

    def _cleanup_load_balancer(self, load_balancer_id):
        test_utils.call_and_ignore_notfound_exc(
            self.load_balancers_client.delete_load_balancer, load_balancer_id)
        self._wait_for_load_balancer_status(load_balancer_id, delete=True)

    def _delete_load_balancer_cascade(self, load_balancer_id):
        self.load_balancers_client.delete_load_balancer_cascade(
            load_balancer_id)
        self._wait_for_load_balancer_status(load_balancer_id, delete=True)

    def _cleanup_listener(self, listener_id, load_balancer_id=None):
        test_utils.call_and_ignore_notfound_exc(
            self.listeners_client.delete_listener, load_balancer_id,
            listener_id)
        if load_balancer_id:
            self._wait_for_load_balancer_status(load_balancer_id, delete=True)

    def _cleanup_pool(self, pool_id, load_balancer_id=None):
        test_utils.call_and_ignore_notfound_exc(
            self.pools_client.delete_pool, load_balancer_id, pool_id)
        if load_balancer_id:
            self._wait_for_load_balancer_status(load_balancer_id, delete=True)

    def _cleanup_health_monitor(self, hm_id, load_balancer_id=None):
        test_utils.call_and_ignore_notfound_exc(
            self.health_monitors_client.delete_health_monitor, hm_id)
        if load_balancer_id:
            self._wait_for_load_balancer_status(load_balancer_id, delete=True)

    def _create_members(self, load_balancer_id, pool_id, backend, ports=None,
                        subnet_id=None):
        """Create one or more Members based on the given backend

        :backend: The backend server the members will be on
        :param ports: List of listening ports on the backend server
        """
        ports = ports or [80, 81]
        backend_id = self.servers[backend]
        for server_id, ip in six.iteritems(self.server_fixed_ips):
            if server_id != backend_id:
                continue
            for port in ports:
                create_member_kwargs = {
                    'ip_address': ip,
                    'protocol_port': port,
                    'weight': 50,
                    'subnet_id': subnet_id
                }
                member = self.members_client.create_member(
                    lb_id=load_balancer_id,
                    pool_id=pool_id,
                    **create_member_kwargs)
                LOG.info('Waiting for lb status on create member...')
                self._wait_for_load_balancer_status(load_balancer_id)
                self.members.append(member)
            self.assertTrue(self.members)

    def _assign_floating_ip_to_lb_vip(self, lb):
        public_network_id = config.network.public_network_id

        LOG.info('assign_floating_ip_to_lb_vip  lb: %s type: %s', lb, type(lb))
        port_id = lb['vip']['port_id']

        floating_ip = self._create_floating_ip(
            thing=lb,
            external_network_id=public_network_id,
            port_id=port_id,
            client=self.floating_ips_client_admin,
            tenant_id=self.floating_ips_client_admin.tenant_id)

        self.floating_ips.setdefault(lb['id'], [])
        self.floating_ips[lb['id']].append(floating_ip)
        # Check for floating ip status before you check load-balancer
        #
        # We need the admin client here and this method utilizes the non-admin
        # self.check_floating_ip_status(floating_ip, 'ACTIVE')
        self.check_flip_status(floating_ip, 'ACTIVE')

    def check_flip_status(self, floating_ip, status):
        """Verifies floatingip reaches the given status

        :param dict floating_ip: floating IP dict to check status
        :param status: target status
        :raises AssertionError: if status doesn't match
        """

        # TODO(ptoohill): Find a way to utilze the proper client method

        floatingip_id = floating_ip['id']

        def refresh():
            result = (self.floating_ips_client_admin.
                      show_floatingip(floatingip_id)['floatingip'])
            return status == result['status']

        test_utils.call_until_true(refresh, 100, 1)

        floating_ip = self.floating_ips_client_admin.show_floatingip(
            floatingip_id)['floatingip']
        self.assertEqual(status, floating_ip['status'],
                         message="FloatingIP: {fp} is at status: {cst}. "
                                 "failed  to reach status: {st}"
                         .format(fp=floating_ip, cst=floating_ip['status'],
                                 st=status))
        LOG.info('FloatingIP: %(fp)s is at status: %(st)s',
                 {'fp': floating_ip, 'st': status})

    def _create_load_balancer(self, ip_version=4, persistence_type=None):
        """Create a load balancer.

        Also assigns a floating IP to the created load balancer.

        :param ip_version: IP version to be used for the VIP IP
        :returns: ID of the created load balancer
        """
        self.create_lb_kwargs = {
            'vip': {'subnet_id': self.subnet['id']},
            'project_id': self.load_balancers_client.tenant_id}
        self.load_balancer = self.load_balancers_client.create_load_balancer(
            **self.create_lb_kwargs)
        lb_id = self.load_balancer['id']
        self.addCleanup(self._cleanup_load_balancer, lb_id)
        LOG.info('Waiting for lb status on create load balancer id: %s', lb_id)
        self.load_balancer = self._wait_for_load_balancer_status(
            load_balancer_id=lb_id,
            provisioning_status='ACTIVE',
            operating_status='ONLINE')

        self.vip_ip = self.load_balancer['vip'].get('ip_address')

        # if the ipv4 is used for lb, then fetch the right values from
        # tempest.conf file
        if ip_version == 4:
            if (config.network.public_network_id and not
                    config.network.project_networks_reachable):
                load_balancer = self.load_balancer
                self._assign_floating_ip_to_lb_vip(load_balancer)
                self.vip_ip = self.floating_ips[
                    load_balancer['id']][0]['floating_ip_address']

        # Currently the ovs-agent is not enforcing security groups on the
        # vip port - see https://bugs.launchpad.net/neutron/+bug/1163569
        # However the linuxbridge-agent does, and it is necessary to add a
        # security group with a rule that allows tcp port 80 to the vip port.
        self.ports_client_admin.update_port(
            self.load_balancer['vip']['port_id'],
            security_groups=[self.security_group['id']])
        return lb_id

    def _create_load_balancer_over_quota(self):
        """Attempt to create a load balancer over quota.

        Creates two load balancers one after the other expecting
        the second create to exceed the configured quota.

        :returns: Response body from the request
        """
        self.create_lb_kwargs = {
            'vip': {'subnet_id': self.subnet['id']},
            'project_id': self.load_balancers_client.tenant_id}
        self.load_balancer = self.load_balancers_client.create_load_balancer(
            **self.create_lb_kwargs)
        lb_id = self.load_balancer['id']
        self.addCleanup(self._cleanup_load_balancer, lb_id)

        self.create_lb_kwargs = {
            'vip': {'subnet_id': self.subnet['id']},
            'project_id': self.load_balancers_client.tenant_id}
        lb_client = self.load_balancers_client
        lb_client.create_load_balancer_over_quota(
            **self.create_lb_kwargs)

        LOG.info('Waiting for lb status on create load balancer id: %s',
                 lb_id)
        self.load_balancer = self._wait_for_load_balancer_status(
            load_balancer_id=lb_id,
            provisioning_status='ACTIVE',
            operating_status='ONLINE')

    def _wait_for_load_balancer_status(self, load_balancer_id,
                                       provisioning_status='ACTIVE',
                                       operating_status='ONLINE',
                                       delete=False):
        interval_time = config.octavia.lb_build_interval
        timeout = config.octavia.lb_build_timeout
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                lb = self.load_balancers_client.get_load_balancer(
                    load_balancer_id)
            except lib_exc.NotFound as e:
                if delete:
                    return
                else:
                    raise e

            LOG.info('provisioning_status: %s operating_status: %s',
                     lb.get('provisioning_status'),
                     lb.get('operating_status'))

            if delete and lb.get('provisioning_status') == 'DELETED':
                break
            elif (lb.get('provisioning_status') == provisioning_status and
                    lb.get('operating_status') == operating_status):
                break
            elif (lb.get('provisioning_status') == 'ERROR' or
                    lb.get('operating_status') == 'ERROR'):
                raise Exception(
                    _("Wait for load balancer for load balancer: {lb_id} "
                      "ran for {timeout} seconds and an ERROR was encountered "
                      "with provisioning status: {provisioning_status} and "
                      "operating status: {operating_status}").format(
                          timeout=timeout,
                          lb_id=lb.get('id'),
                          provisioning_status=provisioning_status,
                          operating_status=operating_status))
            time.sleep(interval_time)
        else:
            raise Exception(
                _("Wait for load balancer ran for {timeout} seconds and did "
                  "not observe {lb_id} reach {provisioning_status} "
                  "provisioning status and {operating_status} "
                  "operating status.").format(
                      timeout=timeout,
                      lb_id=lb.get('id'),
                      provisioning_status=provisioning_status,
                      operating_status=operating_status))
        return lb

    def _wait_for_pool_session_persistence(self, pool_id, sp_type=None):
        interval_time = config.octavia.build_interval
        timeout = config.octavia.build_timeout
        end_time = time.time() + timeout
        while time.time() < end_time:
            pool = self.pools_client.get_pool(self.load_balancer['id'],
                                              pool_id)
            sp = pool.get('session_persistence', None)
            if (not (sp_type or sp) or
                    pool['session_persistence']['type'] == sp_type):
                return pool
            time.sleep(interval_time)
        raise Exception(
            _("Wait for pool ran for {timeout} seconds and did "
              "not observe {pool_id} update session persistence type "
              "to {type}.").format(
                  timeout=timeout,
                  pool_id=pool_id,
                  type=sp_type))

    def _check_members_balanced(self, members=None):
        """Check that back-end members are load balanced.

        1. Send requests on the floating ip associated with the VIP
        2. Check that the requests are shared between the members given
        3. Check that no unexpected members were balanced.
        """
        members = members or ['server1_0', 'server1_1']
        members = list(map(
            lambda x: six.b(x) if type(x) == six.text_type else x, members))
        LOG.info(_('Checking all members are balanced...'))
        self._wait_for_http_service(self.vip_ip)
        LOG.info(_('Connection to %(vip)s is valid'), {'vip': self.vip_ip})
        counters = self._send_concurrent_requests(self.vip_ip)
        for member, counter in six.iteritems(counters):
            LOG.info(_('Member %(member)s saw %(counter)s requests.'),
                     {'member': member, 'counter': counter})
            self.assertGreater(counter, 0,
                               'Member %s never balanced' % member)
        for member in members:
            if member not in list(counters):
                raise Exception(
                    _("Member {member} was never balanced.").format(
                        member=member))
        for member in list(counters):
            if member not in members:
                raise Exception(
                    _("Member {member} was balanced when it should not "
                      "have been.").format(member=member))
        LOG.info(_('Done checking all members are balanced...'))

    def _wait_for_http_service(self, check_ip, port=80):
        def try_connect(check_ip, port):
            try:
                LOG.info('checking connection to ip: %s port: %d',
                         check_ip, port)
                resp = urllib2.urlopen("http://{0}:{1}/".format(check_ip,
                                                                port))
                if resp.getcode() == 200:
                    return True
                return False
            except IOError as e:
                LOG.info('Got IOError in check connection: %s', e)
                return False
            except error.HTTPError as e:
                LOG.info('Got HTTPError in check connection: %s', e)
                return False

        timeout = config.validation.ping_timeout
        start = time.time()
        while not try_connect(check_ip, port):
            if (time.time() - start) > timeout:
                message = "Timed out trying to connect to %s" % check_ip
                raise lib_exc.TimeoutException(message)
            time.sleep(1)

    def _send_requests(self, vip_ip, path=''):
        counters = dict()
        for i in range(self.num):
            try:
                server = urllib2.urlopen("http://{0}/{1}".format(vip_ip, path),
                                         None, 2).read()
                if server not in counters:
                    counters[server] = 1
                else:
                    counters[server] += 1
            # HTTP exception means fail of server, so don't increase counter
            # of success and continue connection tries
            except (error.HTTPError, error.URLError,
                    socket.timeout, socket.error) as e:
                LOG.info('Got Error in sending request: %s', e)
                continue
        return counters

    def _send_concurrent_requests(self, vip_ip, path='', clients=5,
                                  timeout=None):
        class ClientThread(threading.Thread):
            def __init__(self, test_case, cid, vip_ip, path=''):
                super(ClientThread, self).__init__(
                    name='ClientThread-{0}'.format(cid))
                self.vip_ip = vip_ip
                self.path = path
                self.test_case = test_case
                self.counters = dict()

            def run(self):
                # NOTE(dlundquist): _send_requests() does not mutate
                # BaseTestCase so concurrent uses of _send_requests does not
                # require a mutex.
                self.counters = self.test_case._send_requests(self.vip_ip,
                                                              path=self.path)

            def join(self, timeout=None):
                start = time.time()
                super(ClientThread, self).join(timeout)
                return time.time() - start

        client_threads = [ClientThread(self, i, vip_ip, path=path)
                          for i in range(clients)]
        for ct in client_threads:
            ct.start()
        if timeout is None:
            # timeout for all client threads defaults to 400ms per request
            timeout = self.num * 0.4
        total_counters = dict()
        for ct in client_threads:
            timeout -= ct.join(timeout)
            if timeout <= 0:
                LOG.error('Client thread %s timed out', ct.name)
                return dict()
            for server in list(ct.counters):
                if server not in total_counters:
                    total_counters[server] = 0
                total_counters[server] += ct.counters[server]
        return total_counters

    def _check_load_balancing_after_deleting_resources(self):
        """Check load balancer after deleting resources

        Assert that no traffic is sent to any backend servers
        """
        counters = self._send_requests(self.vip_ip)
        if counters:
            for server, counter in six.iteritems(counters):
                self.assertEqual(
                    counter, 0,
                    'Server %s saw requests when it should not have' % server)

    def _check_source_ip_persistence(self):
        """Check source ip session persistence.

        Verify that all requests from our ip are answered by the same server
        that handled it the first time.
        """
        # Check that backends are reachable
        self._wait_for_http_service(self.vip_ip)

        resp = []
        for count in range(10):
            resp.append(
                urllib2.urlopen("http://{0}/".format(self.vip_ip)).read())
        self.assertEqual(len(set(resp)), 1)

    def _update_pool_session_persistence(self, persistence_type=None,
                                         cookie_name=None):
        """Update a pool with new session persistence type and cookie name."""

        update_data = {}
        if persistence_type:
            update_data = {"session_persistence": {
                "type": persistence_type}}
        if cookie_name:
            update_data['session_persistence'].update(
                {"cookie_name": cookie_name})
        self.pools_client.update_pool(self.load_balancer['id'],
                                      self.pool['id'], **update_data)
        self.pool = self._wait_for_pool_session_persistence(
            self.load_balancer['id'],
            self.pool['id'],
            persistence_type)
        self._wait_for_load_balancer_status(self.load_balancer['id'])
        if persistence_type:
            self.assertEqual(persistence_type,
                             self.pool['session_persistence']['type'])
        if cookie_name:
            self.assertEqual(cookie_name,
                             self.pool['session_persistence']['cookie_name'])

    def _check_cookie_session_persistence(self):
        """Check cookie persistence types by injecting cookies in requests."""

        # Send first request and get cookie from the server's response
        cj = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        opener.open("http://{0}/".format(self.vip_ip))
        resp = []
        # Send 10 subsequent requests with the cookie inserted in the headers.
        for count in range(10):
            request = urllib2.Request("http://{0}/".format(self.vip_ip))
            cj.add_cookie_header(request)
            response = urllib2.urlopen(request)
            resp.append(response.read())
        self.assertEqual(len(set(resp)), 1, message=resp)

    def _create_floating_ip(self, thing, external_network_id=None,
                            port_id=None, client=None, tenant_id=None):
        """Create a floating IP and associate to a resource/port on Neutron."""

        if not tenant_id:
            try:
                tenant_id = thing['tenant_id']
            except Exception:
                # Thing probably migrated to project_id, grab that...
                tenant_id = thing['project_id']

        if not external_network_id:
            external_network_id = config.network.public_network_id
        if not client:
            client = self.floating_ips_client
        if not port_id:
            port_id, ip4 = self._get_server_port_id_and_ip4(thing)
        else:
            ip4 = None
        result = client.create_floatingip(
            floating_network_id=external_network_id,
            port_id=port_id,
            tenant_id=tenant_id,
            fixed_ip_address=ip4
        )
        floating_ip = result['floatingip']
        self.addCleanup(test_utils.call_and_ignore_notfound_exc,
                        self.floating_ips_client.delete_floatingip,
                        floating_ip['id'])
        return floating_ip

    def copy_file_to_host(self, file_from, dest, host, username, pkey):
        dest = "%s@%s:%s" % (username, host, dest)
        cmd = ("scp -v -o UserKnownHostsFile=/dev/null "
               "-o StrictHostKeyChecking=no "
               "-i %(pkey)s %(file1)s %(dest)s" % {'pkey': pkey,
                                                   'file1': file_from,
                                                   'dest': dest})
        return self.execute(cmd)

    def execute(self, cmd, cwd=None):
        args = shlex.split(cmd)
        subprocess_args = {'stdout': subprocess.PIPE,
                           'stderr': subprocess.STDOUT,
                           'cwd': cwd}
        proc = subprocess.Popen(args, **subprocess_args)
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            LOG.error('Command %s returned with exit status %s,output %s, '
                      'error %s', cmd, proc.returncode, stdout, stderr)
        return stdout

    def _set_quotas(self, project_id=None, load_balancer=20, listener=20,
                    pool=20, health_monitor=20, member=20):
        if not project_id:
            project_id = self.networks_client.tenant_id
        body = {'quota': {
            'load_balancer': load_balancer, 'listener': listener,
            'pool': pool, 'health_monitor': health_monitor, 'member': member}}
        return self.quotas_client.update_quotas(project_id, **body)

    def _create_load_balancer_tree(self, ip_version=4, cleanup=True):
        # TODO(ptoohill): remove or null out project ID when Octavia supports
        # keystone auth and automatically populates it for us.
        project_id = self.networks_client.tenant_id

        create_members = self._create_members_kwargs(self.subnet['id'])
        create_pool = {'project_id': project_id,
                       'lb_algorithm': 'ROUND_ROBIN',
                       'protocol': 'HTTP',
                       'members': create_members}
        create_listener = {'project_id': project_id,
                           'protocol': 'HTTP',
                           'protocol_port': 80,
                           'default_pool': create_pool}
        create_lb = {'project_id': project_id,
                     'vip': {'subnet_id': self.subnet['id']},
                     'listeners': [create_listener]}

        # Set quotas back and finish the test
        self._set_quotas(project_id=project_id)
        self.load_balancer = (self.load_balancers_client
                              .create_load_balancer_graph(create_lb))

        load_balancer_id = self.load_balancer['id']
        if cleanup:
            self.addCleanup(self._cleanup_load_balancer, load_balancer_id)
        LOG.info('Waiting for lb status on create load balancer id: %s',
                 load_balancer_id)
        self.load_balancer = self._wait_for_load_balancer_status(
            load_balancer_id)

        self.vip_ip = self.load_balancer['vip'].get('ip_address')

        # if the ipv4 is used for lb, then fetch the right values from
        # tempest.conf file
        if ip_version == 4:
            if (config.network.public_network_id and
                    not config.network.project_networks_reachable):
                load_balancer = self.load_balancer
                self._assign_floating_ip_to_lb_vip(load_balancer)
                self.vip_ip = self.floating_ips[
                    load_balancer['id']][0]['floating_ip_address']

        # Currently the ovs-agent is not enforcing security groups on the
        # vip port - see https://bugs.launchpad.net/neutron/+bug/1163569
        # However the linuxbridge-agent does, and it is necessary to add a
        # security group with a rule that allows tcp port 80 to the vip port.
        self.ports_client_admin.update_port(
            self.load_balancer['vip']['port_id'],
            security_groups=[self.security_group['id']])

    def _create_members_kwargs(self, subnet_id=None):
        """Create one or more Members

        In case there is only one server, create both members with the same ip
        but with different ports to listen on.
        """
        create_member_kwargs = []
        for server_id, ip in six.iteritems(self.server_fixed_ips):
            create_member_kwargs.append({'ip_address': ip,
                                         'protocol_port': 80,
                                         'weight': 50,
                                         'subnet_id': subnet_id})
        return create_member_kwargs
