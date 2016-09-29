#!/usr/bin/env bash
set -ex

# Sample ``local.sh`` that configures two simple webserver instances and sets
# up a Neutron LBaaS Version 2 loadbalancer backed by Octavia.

# Keep track of the DevStack directory
TOP_DIR=$(cd $(dirname "$0") && pwd)
BOOT_DELAY=60

# Import common functions
source ${TOP_DIR}/functions

# Use openrc + stackrc for settings
source ${TOP_DIR}/stackrc

# Destination path for installation ``DEST``
DEST=${DEST:-/opt/stack}

# Polling functions
function wait_for_loadbalancer_active() {
  lb_name=$1
  while [ $(neutron lbaas-loadbalancer-list | grep $lb_name | grep ACTIVE | wc --lines) == 0 ]; do
    sleep 2
  done
}

if is_service_enabled nova; then

    # Unset DOMAIN env variables that are not needed for keystone v2 and set OpenStack demo user auth
    unset OS_USER_DOMAIN_ID
    unset OS_PROJECT_DOMAIN_ID
    source ${TOP_DIR}/openrc demo demo

    # Create an SSH key to use for the instances
    DEVSTACK_LBAAS_SSH_KEY_NAME=$(hostname)_DEVSTACK_LBAAS_SSH_KEY_RSA
    DEVSTACK_LBAAS_SSH_KEY_DIR=${TOP_DIR}
    DEVSTACK_LBAAS_SSH_KEY=${DEVSTACK_LBAAS_SSH_KEY_DIR}/${DEVSTACK_LBAAS_SSH_KEY_NAME}
    rm -f ${DEVSTACK_LBAAS_SSH_KEY}.pub ${DEVSTACK_LBAAS_SSH_KEY}
    ssh-keygen -b 2048 -t rsa -f ${DEVSTACK_LBAAS_SSH_KEY} -N ""
    nova keypair-add --pub-key=${DEVSTACK_LBAAS_SSH_KEY}.pub ${DEVSTACK_LBAAS_SSH_KEY_NAME}

    # Add tcp/22,80 and icmp to default security group
    nova secgroup-add-rule default tcp 22 22 0.0.0.0/0
    nova secgroup-add-rule default tcp 80 80 0.0.0.0/0
    nova secgroup-add-rule default icmp -1 -1 0.0.0.0/0

    # Boot some instances
    NOVA_BOOT_ARGS="--key-name ${DEVSTACK_LBAAS_SSH_KEY_NAME} --image $(openstack image list | awk '/ cirros-0.3.4-x86_64-disk / {print $2}') --flavor 1 --nic net-id=$(neutron net-list | awk '/ private / {print $2}')"

    nova boot ${NOVA_BOOT_ARGS} node1
    nova boot ${NOVA_BOOT_ARGS} node2

    echo "Waiting ${BOOT_DELAY} seconds for instances to boot"
    sleep ${BOOT_DELAY}

    IP1=$(nova show node1 | grep "private network" | awk '/private network/ {ip = substr($5, 0, length($5)-1); if (ip ~ "\\.") print ip; else print $6}')
    IP2=$(nova show node2 | grep "private network" | awk '/private network/ {ip = substr($5, 0, length($5)-1); if (ip ~ "\\.") print ip; else print $6}')

    touch ~/.ssh/known_hosts

    ssh-keygen -R ${IP1}
    ssh-keygen -R ${IP2}

    # Run a simple web server on the instances
    chmod 0755 ${TOP_DIR}/webserver.sh
    scp -i ${DEVSTACK_LBAAS_SSH_KEY} -o StrictHostKeyChecking=no ${TOP_DIR}/webserver.sh cirros@${IP1}:webserver.sh
    scp -i ${DEVSTACK_LBAAS_SSH_KEY} -o StrictHostKeyChecking=no ${TOP_DIR}/webserver.sh cirros@${IP2}:webserver.sh

    screen_process node1 "ssh -i ${DEVSTACK_LBAAS_SSH_KEY} -o StrictHostKeyChecking=no cirros@${IP1} ./webserver.sh"
    screen_process node2 "ssh -i ${DEVSTACK_LBAAS_SSH_KEY} -o StrictHostKeyChecking=no cirros@${IP2} ./webserver.sh"

fi

if is_service_enabled q-lbaasv2; then

    neutron lbaas-loadbalancer-create --name lb1 private-subnet
    wait_for_loadbalancer_active lb1

    neutron lbaas-listener-create --loadbalancer lb1 --protocol HTTP --protocol-port 80 --name listener1
    wait_for_loadbalancer_active lb1

    neutron lbaas-pool-create --lb-algorithm ROUND_ROBIN --listener listener1 --protocol HTTP --name pool1
    wait_for_loadbalancer_active lb1

    neutron lbaas-member-create  --subnet private-subnet --address ${IP1} --protocol-port 80 pool1
    wait_for_loadbalancer_active lb1

    neutron lbaas-member-create  --subnet private-subnet --address ${IP2} --protocol-port 80 pool1

fi
