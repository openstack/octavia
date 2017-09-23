# Copyright 2012 OpenStack Foundation
# Copyright 2013 IBM Corp.
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

import subprocess

import netaddr
from oslo_log import log
from oslo_utils import netutils

from tempest.common import compute
from tempest.common.utils.linux import remote_client
from tempest.common.utils import net_utils
from tempest.common import waiters
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib.common.utils import test_utils
from tempest.lib import exceptions as lib_exc
import tempest.test

CONF = config.CONF

LOG = log.getLogger(__name__)


class ScenarioTest(tempest.test.BaseTestCase):
    """Base class for scenario tests. Uses tempest own clients. """

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(ScenarioTest, cls).setup_clients()
        # Clients (in alphabetical order)
        cls.keypairs_client = cls.manager.keypairs_client
        cls.servers_client = cls.manager.servers_client
        # Neutron network client
        cls.networks_client = cls.manager.networks_client
        cls.ports_client = cls.manager.ports_client
        cls.routers_client = cls.manager.routers_client
        cls.subnets_client = cls.manager.subnets_client
        cls.floating_ips_client = cls.manager.floating_ips_client
        cls.security_groups_client = cls.manager.security_groups_client
        cls.security_group_rules_client = (
            cls.manager.security_group_rules_client)

    # ## Test functions library
    #
    # The create_[resource] functions only return body and discard the
    # resp part which is not used in scenario tests

    def _create_port(self, network_id, client=None, namestart='port-quotatest',
                     **kwargs):
        if not client:
            client = self.ports_client
        name = data_utils.rand_name(namestart)
        result = client.create_port(
            name=name,
            network_id=network_id,
            **kwargs)
        self.assertIsNotNone(result, 'Unable to allocate port')
        port = result['port']
        self.addCleanup(test_utils.call_and_ignore_notfound_exc,
                        client.delete_port, port['id'])
        return port

    def create_keypair(self, client=None):
        if not client:
            client = self.keypairs_client
        name = data_utils.rand_name(self.__class__.__name__)
        # We don't need to create a keypair by pubkey in scenario
        body = client.create_keypair(name=name)
        self.addCleanup(client.delete_keypair, name)
        return body['keypair']

    def create_server(self, name=None, image_id=None, flavor=None,
                      validatable=False, wait_until='ACTIVE',
                      clients=None, **kwargs):
        """Wrapper utility that returns a test server.

        This wrapper utility calls the common create test server and
        returns a test server. The purpose of this wrapper is to minimize
        the impact on the code of the tests already using this
        function.
        """

        # NOTE(jlanoux): As a first step, ssh checks in the scenario
        # tests need to be run regardless of the run_validation and
        # validatable parameters and thus until the ssh validation job
        # becomes voting in CI. The test resources management and IP
        # association are taken care of in the scenario tests.
        # Therefore, the validatable parameter is set to false in all
        # those tests. In this way create_server just return a standard
        # server and the scenario tests always perform ssh checks.

        # Needed for the cross_tenant_traffic test:
        if clients is None:
            clients = self.manager

        if name is None:
            name = data_utils.rand_name(self.__class__.__name__ + "-server")

        vnic_type = CONF.network.port_vnic_type

        # If vnic_type is configured create port for
        # every network
        if vnic_type:
            ports = []

            create_port_body = {'binding:vnic_type': vnic_type,
                                'namestart': 'port-smoke'}
            if kwargs:
                # Convert security group names to security group ids
                # to pass to create_port
                if 'security_groups' in kwargs:
                    security_groups = (
                        clients.security_groups_client.list_security_groups(
                        ).get('security_groups'))
                    sec_dict = dict([(s['name'], s['id'])
                                    for s in security_groups])

                    sec_groups_names = [s['name'] for s in kwargs.pop(
                        'security_groups')]
                    security_groups_ids = [sec_dict[s]
                                           for s in sec_groups_names]

                    if security_groups_ids:
                        create_port_body[
                            'security_groups'] = security_groups_ids
                networks = kwargs.pop('networks', [])
            else:
                networks = []

            # If there are no networks passed to us we look up
            # for the project's private networks and create a port.
            # The same behaviour as we would expect when passing
            # the call to the clients with no networks
            if not networks:
                networks = clients.networks_client.list_networks(
                    **{'router:external': False, 'fields': 'id'})['networks']

            # It's net['uuid'] if networks come from kwargs
            # and net['id'] if they come from
            # clients.networks_client.list_networks
            for net in networks:
                net_id = net.get('uuid', net.get('id'))
                if 'port' not in net:
                    port = self._create_port(network_id=net_id,
                                             client=clients.ports_client,
                                             **create_port_body)
                    ports.append({'port': port['id']})
                else:
                    ports.append({'port': net['port']})
            if ports:
                kwargs['networks'] = ports
            self.ports = ports

        tenant_network = self.get_tenant_network()

        body, servers = compute.create_test_server(
            clients,
            tenant_network=tenant_network,
            wait_until=wait_until,
            name=name, flavor=flavor,
            image_id=image_id, **kwargs)

        self.addCleanup(waiters.wait_for_server_termination,
                        clients.servers_client, body['id'])
        self.addCleanup(test_utils.call_and_ignore_notfound_exc,
                        clients.servers_client.delete_server, body['id'])
        server = clients.servers_client.show_server(body['id'])['server']
        return server

    def get_remote_client(self, ip_address, username=None, private_key=None):
        """Get a SSH client to a remote server

        @param ip_address the server floating or fixed IP address to use
                          for ssh validation
        @param username name of the Linux account on the remote server
        @param private_key the SSH private key to use
        @return a RemoteClient object
        """

        if username is None:
            username = CONF.validation.image_ssh_user
        # Set this with 'keypair' or others to log in with keypair or
        # username/password.
        if CONF.validation.auth_method == 'keypair':
            password = None
            if private_key is None:
                private_key = self.keypair['private_key']
        else:
            password = CONF.validation.image_ssh_password
            private_key = None
        linux_client = remote_client.RemoteClient(ip_address, username,
                                                  pkey=private_key,
                                                  password=password)
        try:
            linux_client.validate_authentication()
        except Exception as e:
            message = ('Initializing SSH connection to %(ip)s failed. '
                       'Error: %(error)s' % {'ip': ip_address,
                                             'error': e})
            caller = test_utils.find_test_caller()
            if caller:
                message = '(%s) %s' % (caller, message)
            LOG.exception(message)
            self._log_console_output()
            raise

        return linux_client

    def _log_console_output(self, servers=None):
        if not CONF.compute_feature_enabled.console_output:
            LOG.debug('Console output not supported, cannot log')
            return
        if not servers:
            servers = self.servers_client.list_servers()
            servers = servers['servers']
        for server in servers:
            try:
                console_output = self.servers_client.get_console_output(
                    server['id'])['output']
                LOG.debug('Console output for %s\nbody=\n%s',
                          server['id'], console_output)
            except lib_exc.NotFound:
                LOG.debug("Server %s disappeared(deleted) while looking "
                          "for the console log", server['id'])

    def _log_net_info(self, exc):
        # network debug is called as part of ssh init
        if not isinstance(exc, lib_exc.SSHTimeout):
            LOG.debug('Network information on a devstack host')

    def ping_ip_address(self, ip_address, should_succeed=True,
                        ping_timeout=None, mtu=None):
        timeout = ping_timeout or CONF.validation.ping_timeout
        cmd = ['ping', '-c1', '-w1']

        if mtu:
            cmd += [
                # don't fragment
                '-M', 'do',
                # ping receives just the size of ICMP payload
                '-s', str(net_utils.get_ping_payload_size(mtu, 4))
            ]
        cmd.append(ip_address)

        def ping():
            proc = subprocess.Popen(cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            proc.communicate()

            return (proc.returncode == 0) == should_succeed

        caller = test_utils.find_test_caller()
        LOG.debug('%(caller)s begins to ping %(ip)s in %(timeout)s sec and the'
                  ' expected result is %(should_succeed)s', {
                      'caller': caller, 'ip': ip_address, 'timeout': timeout,
                      'should_succeed':
                      'reachable' if should_succeed else 'unreachable'
                  })
        result = test_utils.call_until_true(ping, timeout, 1)
        LOG.debug('%(caller)s finishes ping %(ip)s in %(timeout)s sec and the '
                  'ping result is %(result)s', {
                      'caller': caller, 'ip': ip_address, 'timeout': timeout,
                      'result': 'expected' if result else 'unexpected'
                  })
        return result

    def check_vm_connectivity(self, ip_address,
                              username=None,
                              private_key=None,
                              should_connect=True,
                              mtu=None):
        """Check server connectivity

        :param ip_address: server to test against
        :param username: server's ssh username
        :param private_key: server's ssh private key to be used
        :param should_connect: True/False indicates positive/negative test
            positive - attempt ping and ssh
            negative - attempt ping and fail if succeed
        :param mtu: network MTU to use for connectivity validation

        :raises AssertError: if the result of the connectivity check does
            not match the value of the should_connect param
        """
        if should_connect:
            msg = "Timed out waiting for %s to become reachable" % ip_address
        else:
            msg = "ip address %s is reachable" % ip_address
        self.assertTrue(self.ping_ip_address(ip_address,
                                             should_succeed=should_connect,
                                             mtu=mtu),
                        msg=msg)
        if should_connect:
            # no need to check ssh for negative connectivity
            self.get_remote_client(ip_address, username, private_key)

    def check_public_network_connectivity(self, ip_address, username,
                                          private_key, should_connect=True,
                                          msg=None, servers=None, mtu=None):
        # The target login is assumed to have been configured for
        # key-based authentication by cloud-init.
        LOG.debug('checking network connections to IP %s with user: %s',
                  ip_address, username)
        try:
            self.check_vm_connectivity(ip_address,
                                       username,
                                       private_key,
                                       should_connect=should_connect,
                                       mtu=mtu)
        except Exception:
            ex_msg = 'Public network connectivity check failed'
            if msg:
                ex_msg += ": " + msg
            LOG.exception(ex_msg)
            self._log_console_output(servers)
            raise


class NetworkScenarioTest(ScenarioTest):
    """Base class for network scenario tests.

    This class provide helpers for network scenario tests, using the neutron
    API. Helpers from ancestor which use the nova network API are overridden
    with the neutron API.

    This Class also enforces using Neutron instead of novanetwork.
    Subclassed tests will be skipped if Neutron is not enabled

    """

    credentials = ['primary', 'admin']

    @classmethod
    def skip_checks(cls):
        super(NetworkScenarioTest, cls).skip_checks()
        if not CONF.service_available.neutron:
            raise cls.skipException('Neutron not available')

    def _create_network(self, networks_client=None,
                        tenant_id=None,
                        namestart='network-smoke-',
                        port_security_enabled=True):
        if not networks_client:
            networks_client = self.networks_client
        if not tenant_id:
            tenant_id = networks_client.tenant_id
        name = data_utils.rand_name(namestart)
        network_kwargs = dict(name=name, tenant_id=tenant_id)
        # Neutron disables port security by default so we have to check the
        # config before trying to create the network with port_security_enabled
        if CONF.network_feature_enabled.port_security:
            network_kwargs['port_security_enabled'] = port_security_enabled
        result = networks_client.create_network(**network_kwargs)
        network = result['network']

        self.assertEqual(network['name'], name)
        self.addCleanup(test_utils.call_and_ignore_notfound_exc,
                        networks_client.delete_network,
                        network['id'])
        return network

    def _create_subnet(self, network, subnets_client=None,
                       routers_client=None, namestart='subnet-smoke',
                       **kwargs):
        """Create a subnet for the given network

        within the cidr block configured for tenant networks.
        """
        if not subnets_client:
            subnets_client = self.subnets_client
        if not routers_client:
            routers_client = self.routers_client

        def cidr_in_use(cidr, tenant_id):
            """Check cidr existence

            :returns: True if subnet with cidr already exist in tenant
                  False else
            """
            cidr_in_use = self.os_admin.subnets_client.list_subnets(
                tenant_id=tenant_id, cidr=cidr)['subnets']
            return len(cidr_in_use) != 0

        ip_version = kwargs.pop('ip_version', 4)

        if ip_version == 6:
            tenant_cidr = netaddr.IPNetwork(
                CONF.network.project_network_v6_cidr)
            num_bits = CONF.network.project_network_v6_mask_bits
        else:
            tenant_cidr = netaddr.IPNetwork(CONF.network.project_network_cidr)
            num_bits = CONF.network.project_network_mask_bits

        result = None
        str_cidr = None
        # Repeatedly attempt subnet creation with sequential cidr
        # blocks until an unallocated block is found.
        for subnet_cidr in tenant_cidr.subnet(num_bits):
            str_cidr = str(subnet_cidr)
            if cidr_in_use(str_cidr, tenant_id=network['tenant_id']):
                continue

            subnet = dict(
                name=data_utils.rand_name(namestart),
                network_id=network['id'],
                tenant_id=network['tenant_id'],
                cidr=str_cidr,
                ip_version=ip_version,
                **kwargs
            )
            try:
                result = subnets_client.create_subnet(**subnet)
                break
            except lib_exc.Conflict as e:
                is_overlapping_cidr = 'overlaps with another subnet' in str(e)
                if not is_overlapping_cidr:
                    raise
        self.assertIsNotNone(result, 'Unable to allocate tenant network')

        subnet = result['subnet']
        self.assertEqual(subnet['cidr'], str_cidr)

        self.addCleanup(test_utils.call_and_ignore_notfound_exc,
                        subnets_client.delete_subnet, subnet['id'])

        return subnet

    def _get_server_port_id_and_ip4(self, server, ip_addr=None):
        ports = self.os_admin.ports_client.list_ports(
            device_id=server['id'], fixed_ip=ip_addr)['ports']
        # A port can have more than one IP address in some cases.
        # If the network is dual-stack (IPv4 + IPv6), this port is associated
        # with 2 subnets
        p_status = ['ACTIVE']
        # NOTE(vsaienko) With Ironic, instances live on separate hardware
        # servers. Neutron does not bind ports for Ironic instances, as a
        # result the port remains in the DOWN state.
        # TODO(vsaienko) remove once bug: #1599836 is resolved.
        if getattr(CONF.service_available, 'ironic', False):
            p_status.append('DOWN')
        port_map = [(p["id"], fxip["ip_address"])
                    for p in ports
                    for fxip in p["fixed_ips"]
                    if netutils.is_valid_ipv4(fxip["ip_address"]) and
                    p['status'] in p_status]
        inactive = [p for p in ports if p['status'] != 'ACTIVE']
        if inactive:
            LOG.warning("Instance has ports that are not ACTIVE: %s", inactive)

        self.assertNotEqual(0, len(port_map),
                            "No IPv4 addresses found in: %s" % ports)
        self.assertEqual(len(port_map), 1,
                         "Found multiple IPv4 addresses: %s. "
                         "Unable to determine which port to target."
                         % port_map)
        return port_map[0]

    def _get_network_by_name(self, network_name):
        net = self.os_admin.networks_client.list_networks(
            name=network_name)['networks']
        self.assertNotEqual(len(net), 0,
                            "Unable to get network by name: %s" % network_name)
        return net[0]

    def create_floating_ip(self, thing, external_network_id=None,
                           port_id=None, client=None):
        """Create a floating IP and associates to a resource/port on Neutron"""
        if not external_network_id:
            external_network_id = CONF.network.public_network_id
        if not client:
            client = self.floating_ips_client
        if not port_id:
            port_id, ip4 = self._get_server_port_id_and_ip4(thing)
        else:
            ip4 = None
        result = client.create_floatingip(
            floating_network_id=external_network_id,
            port_id=port_id,
            tenant_id=thing['tenant_id'],
            fixed_ip_address=ip4
        )
        floating_ip = result['floatingip']
        self.addCleanup(test_utils.call_and_ignore_notfound_exc,
                        client.delete_floatingip,
                        floating_ip['id'])
        return floating_ip

    def _associate_floating_ip(self, floating_ip, server):
        port_id, _ = self._get_server_port_id_and_ip4(server)
        kwargs = dict(port_id=port_id)
        floating_ip = self.floating_ips_client.update_floatingip(
            floating_ip['id'], **kwargs)['floatingip']
        self.assertEqual(port_id, floating_ip['port_id'])
        return floating_ip

    def _disassociate_floating_ip(self, floating_ip):
        """:param floating_ip: floating_ips_client.create_floatingip"""
        kwargs = dict(port_id=None)
        floating_ip = self.floating_ips_client.update_floatingip(
            floating_ip['id'], **kwargs)['floatingip']
        self.assertIsNone(floating_ip['port_id'])
        return floating_ip

    def check_floating_ip_status(self, floating_ip, status):
        """Verifies floatingip reaches the given status

        :param dict floating_ip: floating IP dict to check status
        :param status: target status
        :raises AssertionError: if status doesn't match
        """
        floatingip_id = floating_ip['id']

        def refresh():
            result = (self.floating_ips_client.
                      show_floatingip(floatingip_id)['floatingip'])
            return status == result['status']

        test_utils.call_until_true(refresh,
                                   CONF.network.build_timeout,
                                   CONF.network.build_interval)
        floating_ip = self.floating_ips_client.show_floatingip(
            floatingip_id)['floatingip']
        self.assertEqual(status, floating_ip['status'],
                         message="FloatingIP: {fp} is at status: {cst}. "
                                 "failed  to reach status: {st}"
                         .format(fp=floating_ip, cst=floating_ip['status'],
                                 st=status))
        LOG.info('FloatingIP: %(fp)s is at status: %(st)s',
                 {'fp': floating_ip, 'st': status})

    def _check_tenant_network_connectivity(self, server,
                                           username,
                                           private_key,
                                           should_connect=True,
                                           servers_for_debug=None):
        if not CONF.network.project_networks_reachable:
            msg = 'Tenant networks not configured to be reachable.'
            LOG.info(msg)
            return
        # The target login is assumed to have been configured for
        # key-based authentication by cloud-init.
        try:
            for net_name, ip_addresses in server['addresses'].items():
                for ip_address in ip_addresses:
                    self.check_vm_connectivity(ip_address['addr'],
                                               username,
                                               private_key,
                                               should_connect=should_connect)
        except Exception as e:
            LOG.exception('Tenant network connectivity check failed')
            self._log_console_output(servers_for_debug)
            self._log_net_info(e)
            raise

    def _check_remote_connectivity(self, source, dest, should_succeed=True,
                                   nic=None):
        """check ping server via source ssh connection

        :param source: RemoteClient: an ssh connection from which to ping
        :param dest: and IP to ping against
        :param should_succeed: boolean should ping succeed or not
        :param nic: specific network interface to ping from
        :returns: boolean -- should_succeed == ping
        :returns: ping is false if ping failed
        """
        def ping_remote():
            try:
                source.ping_host(dest, nic=nic)
            except lib_exc.SSHExecCommandFailed:
                LOG.warning('Failed to ping IP: %s via a ssh connection '
                            'from: %s.', dest, source.ssh_client.host)
                return not should_succeed
            return should_succeed

        return test_utils.call_until_true(ping_remote,
                                          CONF.validation.ping_timeout,
                                          1)

    def _create_security_group(self, security_group_rules_client=None,
                               tenant_id=None,
                               namestart='secgroup-smoke',
                               security_groups_client=None):
        if security_group_rules_client is None:
            security_group_rules_client = self.security_group_rules_client
        if security_groups_client is None:
            security_groups_client = self.security_groups_client
        if tenant_id is None:
            tenant_id = security_groups_client.tenant_id
        secgroup = self._create_empty_security_group(
            namestart=namestart, client=security_groups_client,
            tenant_id=tenant_id)

        # Add rules to the security group
        rules = self._create_loginable_secgroup_rule(
            security_group_rules_client=security_group_rules_client,
            secgroup=secgroup,
            security_groups_client=security_groups_client)
        for rule in rules:
            self.assertEqual(tenant_id, rule['tenant_id'])
            self.assertEqual(secgroup['id'], rule['security_group_id'])
        return secgroup

    def _create_empty_security_group(self, client=None, tenant_id=None,
                                     namestart='secgroup-smoke'):
        """Create a security group without rules.

        Default rules will be created:
         - IPv4 egress to any
         - IPv6 egress to any

        :param tenant_id: secgroup will be created in this tenant
        :returns: the created security group
        """
        if client is None:
            client = self.security_groups_client
        if not tenant_id:
            tenant_id = client.tenant_id
        sg_name = data_utils.rand_name(namestart)
        sg_desc = sg_name + " description"
        sg_dict = dict(name=sg_name,
                       description=sg_desc)
        sg_dict['tenant_id'] = tenant_id
        result = client.create_security_group(**sg_dict)

        secgroup = result['security_group']
        self.assertEqual(secgroup['name'], sg_name)
        self.assertEqual(tenant_id, secgroup['tenant_id'])
        self.assertEqual(secgroup['description'], sg_desc)

        self.addCleanup(test_utils.call_and_ignore_notfound_exc,
                        client.delete_security_group, secgroup['id'])
        return secgroup

    def _default_security_group(self, client=None, tenant_id=None):
        """Get default secgroup for given tenant_id.

        :returns: default secgroup for given tenant
        """
        if client is None:
            client = self.security_groups_client
        if not tenant_id:
            tenant_id = client.tenant_id
        sgs = [
            sg for sg in list(client.list_security_groups().values())[0]
            if sg['tenant_id'] == tenant_id and sg['name'] == 'default'
        ]
        msg = "No default security group for tenant %s." % (tenant_id)
        self.assertGreater(len(sgs), 0, msg)
        return sgs[0]

    def _create_security_group_rule(self, secgroup=None,
                                    sec_group_rules_client=None,
                                    tenant_id=None,
                                    security_groups_client=None, **kwargs):
        """Create a rule from a dictionary of rule parameters.

        Create a rule in a secgroup. if secgroup not defined will search for
        default secgroup in tenant_id.

        :param secgroup: the security group.
        :param tenant_id: if secgroup not passed -- the tenant in which to
            search for default secgroup
        :param kwargs: a dictionary containing rule parameters:
            for example, to allow incoming ssh:
            rule = {
                    direction: 'ingress'
                    protocol:'tcp',
                    port_range_min: 22,
                    port_range_max: 22
                    }
        """
        if sec_group_rules_client is None:
            sec_group_rules_client = self.security_group_rules_client
        if security_groups_client is None:
            security_groups_client = self.security_groups_client
        if not tenant_id:
            tenant_id = security_groups_client.tenant_id
        if secgroup is None:
            secgroup = self._default_security_group(
                client=security_groups_client, tenant_id=tenant_id)

        ruleset = dict(security_group_id=secgroup['id'],
                       tenant_id=secgroup['tenant_id'])
        ruleset.update(kwargs)

        sg_rule = sec_group_rules_client.create_security_group_rule(**ruleset)
        sg_rule = sg_rule['security_group_rule']

        self.assertEqual(secgroup['tenant_id'], sg_rule['tenant_id'])
        self.assertEqual(secgroup['id'], sg_rule['security_group_id'])

        return sg_rule

    def _create_loginable_secgroup_rule(self, security_group_rules_client=None,
                                        secgroup=None,
                                        security_groups_client=None):
        """Create loginable security group rule

        This function will create:
        1. egress and ingress tcp port 22 allow rule in order to allow ssh
        access for ipv4.
        2. egress and ingress ipv6 icmp allow rule, in order to allow icmpv6.
        3. egress and ingress ipv4 icmp allow rule, in order to allow icmpv4.
        """

        if security_group_rules_client is None:
            security_group_rules_client = self.security_group_rules_client
        if security_groups_client is None:
            security_groups_client = self.security_groups_client
        rules = []
        rulesets = [
            dict(
                # ssh
                protocol='tcp',
                port_range_min=22,
                port_range_max=22,
            ),
            dict(
                # ping
                protocol='icmp',
            ),
            dict(
                # ipv6-icmp for ping6
                protocol='icmp',
                ethertype='IPv6',
            )
        ]
        sec_group_rules_client = security_group_rules_client
        for ruleset in rulesets:
            for r_direction in ['ingress', 'egress']:
                ruleset['direction'] = r_direction
                try:
                    sg_rule = self._create_security_group_rule(
                        sec_group_rules_client=sec_group_rules_client,
                        secgroup=secgroup,
                        security_groups_client=security_groups_client,
                        **ruleset)
                except lib_exc.Conflict as ex:
                    # if rule already exist - skip rule and continue
                    msg = 'Security group rule already exists'
                    if msg not in ex._error_string:
                        raise ex
                else:
                    self.assertEqual(r_direction, sg_rule['direction'])
                    rules.append(sg_rule)

        return rules

    def _get_router(self, client=None, tenant_id=None):
        """Retrieve a router for the given tenant id.

        If a public router has been configured, it will be returned.

        If a public router has not been configured, but a public
        network has, a tenant router will be created and returned that
        routes traffic to the public network.
        """
        if not client:
            client = self.routers_client
        if not tenant_id:
            tenant_id = client.tenant_id
        router_id = CONF.network.public_router_id
        network_id = CONF.network.public_network_id
        if router_id:
            body = client.show_router(router_id)
            return body['router']
        elif network_id:
            router = self._create_router(client, tenant_id)
            kwargs = {'external_gateway_info': dict(network_id=network_id)}
            router = client.update_router(router['id'], **kwargs)['router']
            return router
        else:
            raise Exception("Neither of 'public_router_id' or "
                            "'public_network_id' has been defined.")

    def _create_router(self, client=None, tenant_id=None,
                       namestart='router-smoke'):
        if not client:
            client = self.routers_client
        if not tenant_id:
            tenant_id = client.tenant_id
        name = data_utils.rand_name(namestart)
        result = client.create_router(name=name,
                                      admin_state_up=True,
                                      tenant_id=tenant_id)
        router = result['router']
        self.assertEqual(router['name'], name)
        self.addCleanup(test_utils.call_and_ignore_notfound_exc,
                        client.delete_router,
                        router['id'])
        return router

    def _update_router_admin_state(self, router, admin_state_up):
        kwargs = dict(admin_state_up=admin_state_up)
        router = self.routers_client.update_router(
            router['id'], **kwargs)['router']
        self.assertEqual(admin_state_up, router['admin_state_up'])

    def create_networks(self, networks_client=None,
                        routers_client=None, subnets_client=None,
                        tenant_id=None, dns_nameservers=None,
                        port_security_enabled=True):
        """Create a network with a subnet connected to a router.

        The baremetal driver is a special case since all nodes are
        on the same shared network.

        :param tenant_id: id of tenant to create resources in.
        :param dns_nameservers: list of dns servers to send to subnet.
        :returns: network, subnet, router
        """
        if CONF.network.shared_physical_network:
            # NOTE(Shrews): This exception is for environments where tenant
            # credential isolation is available, but network separation is
            # not (the current baremetal case). Likely can be removed when
            # test account mgmt is reworked:
            # https://blueprints.launchpad.net/tempest/+spec/test-accounts
            if not CONF.compute.fixed_network_name:
                m = 'fixed_network_name must be specified in config'
                raise lib_exc.InvalidConfiguration(m)
            network = self._get_network_by_name(
                CONF.compute.fixed_network_name)
            router = None
            subnet = None
        else:
            network = self._create_network(
                networks_client=networks_client,
                tenant_id=tenant_id,
                port_security_enabled=port_security_enabled)
            router = self._get_router(client=routers_client,
                                      tenant_id=tenant_id)
            subnet_kwargs = dict(network=network,
                                 subnets_client=subnets_client,
                                 routers_client=routers_client)
            # use explicit check because empty list is a valid option
            if dns_nameservers is not None:
                subnet_kwargs['dns_nameservers'] = dns_nameservers
            subnet = self._create_subnet(**subnet_kwargs)
            if not routers_client:
                routers_client = self.routers_client
            router_id = router['id']
            routers_client.add_router_interface(router_id,
                                                subnet_id=subnet['id'])

            # save a cleanup job to remove this association between
            # router and subnet
            self.addCleanup(test_utils.call_and_ignore_notfound_exc,
                            routers_client.remove_router_interface, router_id,
                            subnet_id=subnet['id'])
        return network, subnet, router
