.. _install-ubuntu:

Install and configure for Ubuntu
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure the Load-balancer
service for Ubuntu 18.04 (LTS).

Prerequisites
-------------

Before you install and configure the service, you must create a database,
service credentials, and API endpoints.

1. Create the database, complete these steps:

   * Use the database access client to connect to the database
     server as the ``root`` user:

     .. code-block:: console

        # mysql

   * Create the ``octavia`` database:

     .. code-block:: console

        CREATE DATABASE octavia;

   * Grant proper access to the ``octavia`` database:

     .. code-block:: console

        GRANT ALL PRIVILEGES ON octavia.* TO 'octavia'@'localhost' \
        IDENTIFIED BY 'OCTAVIA_DBPASS';
        GRANT ALL PRIVILEGES ON octavia.* TO 'octavia'@'%' \
        IDENTIFIED BY 'OCTAVIA_DBPASS';

     Replace OCTAVIA_DBPASS with a suitable password.

   * Exit the database access client.

     .. code-block:: console

        exit;

2. Source the ``admin`` credentials to gain access to admin-only CLI commands:

   .. code-block:: console

      $ . admin-openrc

3. To create the Octavia service credentials, complete these steps:

   * Create the ``octavia`` user:

     .. code-block:: console

        $ openstack user create --domain default --password-prompt octavia
          User Password:
          Repeat User Password:
          +---------------------+----------------------------------+
          | Field               | Value                            |
          +---------------------+----------------------------------+
          | domain_id           | default                          |
          | enabled             | True                             |
          | id                  | b18ee38e06034b748141beda8fc8bfad |
          | name                | octavia                          |
          | options             | {}                               |
          | password_expires_at | None                             |
          +---------------------+----------------------------------+

   * Add the ``admin`` role to the ``octavia`` user:

     .. code-block:: console

        $ openstack role add --project service --user octavia admin

     .. note::

        This command produces no output.

     .. note::
        The Octavia service does not require the full admin role.
        Details of how to run Octavia without the admin role will come in a future version of this document.

   * Create the octavia service entities:

     .. code-block:: console

        $ openstack service create --name octavia --description "OpenStack Octavia" load-balancer
          +-------------+----------------------------------+
          | Field       | Value                            |
          +-------------+----------------------------------+
          | description | OpenStack Octavia                |
          | enabled     | True                             |
          | id          | d854f6fff0a64f77bda8003c8dedfada |
          | name        | octavia                          |
          | type        | load-balancer                    |
          +-------------+----------------------------------+

4. Create the Load-balancer service API endpoints:

   .. code-block:: console

      $ openstack endpoint create --region RegionOne \
        load-balancer public http://controller:9876
        +--------------+----------------------------------+
        | Field        | Value                            |
        +--------------+----------------------------------+
        | enabled      | True                             |
        | id           | 47cf883de46242c39f147c52f2958ebf |
        | interface    | public                           |
        | region       | RegionOne                        |
        | region_id    | RegionOne                        |
        | service_id   | d854f6fff0a64f77bda8003c8dedfada |
        | service_name | octavia                          |
        | service_type | load-balancer                    |
        | url          | http://controller:9876           |
        +--------------+----------------------------------+

      $ openstack endpoint create --region RegionOne \
        load-balancer internal http://controller:9876
        +--------------+----------------------------------+
        | Field        | Value                            |
        +--------------+----------------------------------+
        | enabled      | True                             |
        | id           | 225aef8465ef4df48a341aaaf2b0a390 |
        | interface    | internal                         |
        | region       | RegionOne                        |
        | region_id    | RegionOne                        |
        | service_id   | d854f6fff0a64f77bda8003c8dedfada |
        | service_name | octavia                          |
        | service_type | load-balancer                    |
        | url          | http://controller:9876           |
        +--------------+----------------------------------+

      $ openstack endpoint create --region RegionOne \
        load-balancer admin http://controller:9876
        +--------------+----------------------------------+
        | Field        | Value                            |
        +--------------+----------------------------------+
        | enabled      | True                             |
        | id           | 375eb5057fb546edbdf3ee4866179672 |
        | interface    | admin                            |
        | region       | RegionOne                        |
        | region_id    | RegionOne                        |
        | service_id   | d854f6fff0a64f77bda8003c8dedfada |
        | service_name | octavia                          |
        | service_type | load-balancer                    |
        | url          | http://controller:9876           |
        +--------------+----------------------------------+

5. Create octavia-openrc file

   .. code-block:: console

      cat << EOF >> $HOME/octavia-openrc
      export OS_PROJECT_DOMAIN_NAME=Default
      export OS_USER_DOMAIN_NAME=Default
      export OS_PROJECT_NAME=service
      export OS_USERNAME=octavia
      export OS_PASSWORD=OCTAVIA_PASS
      export OS_AUTH_URL=http://controller:5000
      export OS_IDENTITY_API_VERSION=3
      export OS_IMAGE_API_VERSION=2
      export OS_VOLUME_API_VERSION=3
      EOF

   Replace OCTAVIA_PASS with the password you chose for the octavia user in
   the Identity service.

6. Source the ``octavia`` credentials to gain access to octavia CLI commands:

   .. code-block:: console

      $ . $HOME/octavia-openrc

7. Create the amphora image

   For creating amphora image, please refer to the `Building Octavia Amphora Images <https://docs.openstack.org/octavia/latest/admin/amphora-image-build.html>`_.

8. Upload the amphora image

   .. code-block:: console

      $ openstack image create --disk-format qcow2 --container-format bare \
        --private --tag amphora \
        --file <path to the amphora image> amphora-x64-haproxy

9. Create a flavor for the amphora image

   .. code-block:: console

      $ openstack flavor create --id 200 --vcpus 1 --ram 1024 \
        --disk 2 "amphora" --private

Install and configure components
--------------------------------

1. Install the packages:

   .. code-block:: console

      # apt install octavia-api octavia-health-manager octavia-housekeeping \
        octavia-worker python3-octavia python3-octaviaclient

   If octavia-common and octavia-api packages ask you to configure, choose No.

2. Create the certificates

   .. code-block:: console

      $ git clone https://opendev.org/openstack/octavia.git
      $ cd octavia/bin/
      $ source create_dual_intermediate_CA.sh
      $ sudo mkdir -p /etc/octavia/certs/private
      $ sudo chmod 755 /etc/octavia -R
      $ sudo cp -p etc/octavia/certs/server_ca.cert.pem /etc/octavia/certs
      $ sudo cp -p etc/octavia/certs/server_ca-chain.cert.pem /etc/octavia/certs
      $ sudo cp -p etc/octavia/certs/server_ca.key.pem /etc/octavia/certs/private
      $ sudo cp -p etc/octavia/certs/client_ca.cert.pem /etc/octavia/certs
      $ sudo cp -p etc/octavia/certs/client.cert-and-key.pem /etc/octavia/certs/private

   For the production environment, Please refer to the `Octavia Certificate Configuration Guide <https://docs.openstack.org/octavia/latest/admin/guides/certificates.html>`_.

3. Source the ``octavia`` credentials to gain access to octavia CLI commands:

   .. code-block:: console

      $ . octavia-openrc

4. Create security groups and their rules

   .. code-block:: console

      $ openstack security group create lb-mgmt-sec-grp
      $ openstack security group rule create --protocol icmp lb-mgmt-sec-grp
      $ openstack security group rule create --protocol tcp --dst-port 22 lb-mgmt-sec-grp
      $ openstack security group rule create --protocol tcp --dst-port 9443 lb-mgmt-sec-grp
      $ openstack security group create lb-health-mgr-sec-grp
      $ openstack security group rule create --protocol udp --dst-port 5555 lb-health-mgr-sec-grp

5. Create a key pair for logging in to the amphora instance

   .. code-block:: console

      $ openstack keypair create --public-key ~/.ssh/id_rsa.pub mykey

   .. note::

      Check whether " ~/.ssh/id_rsa.pub" file exists or not in advance.
      If the file does not exist, run the ssh-keygen command to create it.

6. Create dhclient.conf file for dhclient

   .. code-block:: console

      $ cd $HOME
      $ sudo mkdir -m755 -p /etc/dhcp/octavia
      $ sudo cp octavia/etc/dhcp/dhclient.conf /etc/dhcp/octavia

7. Create a network

   .. note::
      During the execution of the below command, please save the of
      BRNAME and MGMT_PORT_MAC in a notepad for further reference.

   .. code-block:: console

      $ OCTAVIA_MGMT_SUBNET=172.16.0.0/12
      $ OCTAVIA_MGMT_SUBNET_START=172.16.0.100
      $ OCTAVIA_MGMT_SUBNET_END=172.16.31.254
      $ OCTAVIA_MGMT_PORT_IP=172.16.0.2

      $ openstack network create lb-mgmt-net
      $ openstack subnet create --subnet-range $OCTAVIA_MGMT_SUBNET --allocation-pool \
        start=$OCTAVIA_MGMT_SUBNET_START,end=$OCTAVIA_MGMT_SUBNET_END \
        --network lb-mgmt-net lb-mgmt-subnet

      $ SUBNET_ID=$(openstack subnet show lb-mgmt-subnet -f value -c id)
      $ PORT_FIXED_IP="--fixed-ip subnet=$SUBNET_ID,ip-address=$OCTAVIA_MGMT_PORT_IP"

      $ MGMT_PORT_ID=$(openstack port create --security-group \
        lb-health-mgr-sec-grp --device-owner Octavia:health-mgr \
        --host=$(hostname) -c id -f value --network lb-mgmt-net \
        $PORT_FIXED_IP octavia-health-manager-listen-port)

      $ MGMT_PORT_MAC=$(openstack port show -c mac_address -f value \
        $MGMT_PORT_ID)

      $ sudo ip link add o-hm0 type veth peer name o-bhm0
      $ NETID=$(openstack network show lb-mgmt-net -c id -f value)
      $ BRNAME=brq$(echo $NETID|cut -c 1-11)
      $ sudo brctl addif $BRNAME o-bhm0
      $ sudo ip link set o-bhm0 up

      $ sudo ip link set dev o-hm0 address $MGMT_PORT_MAC
      $ sudo iptables -I INPUT -i o-hm0 -p udp --dport 5555 -j ACCEPT
      $ sudo dhclient -v o-hm0 -cf /etc/dhcp/octavia

8. Below settings are required to create veth pair after the host reboot

   Edit the ``/etc/systemd/network/o-hm0.network`` file

   .. code-block:: ini

      [Match]
      Name=o-hm0

      [Network]
      DHCP=yes

   Edit the ``/etc/systemd/system/octavia-interface.service`` file

   .. code-block:: ini

      [Unit]
      Description=Octavia Interface Creator
      Requires=neutron-linuxbridge-agent.service
      After=neutron-linuxbridge-agent.service

      [Service]
      Type=oneshot
      RemainAfterExit=true
      ExecStart=/opt/octavia-interface.sh start
      ExecStop=/opt/octavia-interface.sh stop

      [Install]
      WantedBy=multi-user.target

   Edit the ``/opt/octavia-interface.sh`` file

   .. code-block:: console

      #!/bin/bash

      set -ex

      MAC=$MGMT_PORT_MAC
      BRNAME=$BRNAME

      if [ "$1" == "start" ]; then
        ip link add o-hm0 type veth peer name o-bhm0
        brctl addif $BRNAME o-bhm0
        ip link set o-bhm0 up
        ip link set dev o-hm0 address $MAC
        ip link set o-hm0 up
        iptables -I INPUT -i o-hm0 -p udp --dport 5555 -j ACCEPT
      elif [ "$1" == "stop" ]; then
        ip link del o-hm0
      else
        brctl show $BRNAME
        ip a s dev o-hm0
      fi

   You need to substitute $MGMT_PORT_MAC and $BRNAME for the values in your environment.

9. Edit the ``/etc/octavia/octavia.conf`` file

   * In the ``[database]`` section, configure database access:

     .. code-block:: ini

        [database]
        connection = mysql+pymysql://octavia:OCTAVIA_DBPASS@controller/octavia

     Replace OCTAVIA_DBPASS with the password you chose for the Octavia databases.

   * In the ``[DEFAULT]`` section, configure the transport url for RabbitMQ message broker.

     .. code-block:: ini

        [DEFAULT]
        transport_url = rabbit://openstack:RABBIT_PASS@controller

     Replace RABBIT_PASS with the password you chose for the openstack account in RabbitMQ.

   * In the ``[oslo_messaging]`` section, configure the transport url for RabbitMQ message broker and topic name.

     .. code-block:: ini

        [oslo_messaging]
        ...
        topic = octavia_prov

     Replace RABBIT_PASS with the password you chose for the openstack account in RabbitMQ.

   * In the ``[api_settings]`` section, configure the host IP and port to bind to.

     .. code-block:: ini

        [api_settings]
        bind_host = 0.0.0.0
        bind_port = 9876

   * In the ``[keystone_authtoken]`` section, configure Identity service access.

     .. code-block:: ini

        [keystone_authtoken]
        www_authenticate_uri = http://controller:5000
        auth_url = http://controller:5000
        memcached_servers = controller:11211
        auth_type = password
        project_domain_name = Default
        user_domain_name = Default
        project_name = service
        username = octavia
        password = OCTAVIA_PASS

     Replace OCTAVIA_PASS with the password you chose for the octavia user in
     the Identity service.

   * In the ``[service_auth]`` section, configure credentials for using other openstack services

     .. code-block:: ini

        [service_auth]
        auth_url = http://controller:5000
        memcached_servers = controller:11211
        auth_type = password
        project_domain_name = Default
        user_domain_name = Default
        project_name = service
        username = octavia
        password = OCTAVIA_PASS

     Replace OCTAVIA_PASS with the password you chose for the octavia user in
     the Identity service.

   * In the ``[certificates]`` section, configure the absolute path to the CA Certificate, the Private Key for signing, and passphrases.

     .. code-block:: ini

        [certificates]
        ...
        server_certs_key_passphrase = insecure-key-do-not-use-this-key
        ca_private_key_passphrase = not-secure-passphrase
        ca_private_key = /etc/octavia/certs/private/server_ca.key.pem
        ca_certificate = /etc/octavia/certs/server_ca.cert.pem

     .. note::

        The values of ca_private_key_passphrase and server_certs_key_passphrase are default and should not be used in production.
        The server_certs_key_passphrase must be a base64 compatible and 32 characters long string.

   * In the ``[haproxy_amphora]`` section, configure the client certificate and the CA.

     .. code-block:: ini

        [haproxy_amphora]
        ...
        server_ca = /etc/octavia/certs/server_ca-chain.cert.pem
        client_cert = /etc/octavia/certs/private/client.cert-and-key.pem

   * In the ``[health_manager]`` section, configure the IP and port number for heartbeat.

     .. code-block:: ini

        [health_manager]
        ...
        bind_port = 5555
        bind_ip = 172.16.0.2
        controller_ip_port_list = 172.16.0.2:5555

   * In the ``[controller_worker]`` section, configure worker settings.

     .. code-block:: ini

        [controller_worker]
        ...
        amp_image_owner_id = <id of service project>
        amp_image_tag = amphora
        amp_ssh_key_name = mykey
        amp_secgroup_list = <lb-mgmt-sec-grp_id>
        amp_boot_network_list = <lb-mgmt-net_id>
        amp_flavor_id = 200
        network_driver = allowed_address_pairs_driver
        compute_driver = compute_nova_driver
        amphora_driver = amphora_haproxy_rest_driver
        client_ca = /etc/octavia/certs/client_ca.cert.pem

10. Populate the octavia database:

   .. code-block:: console

      # octavia-db-manage --config-file /etc/octavia/octavia.conf upgrade head

Finalize installation
---------------------

Restart the services:

  .. code-block:: console

     # systemctl restart octavia-api octavia-health-manager octavia-housekeeping octavia-worker
