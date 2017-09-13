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
  while [ $(openstack loadbalancer show $lb_name -f value -c provisioning_status) != "ACTIVE" ]; do
    sleep 2
  done
}

if is_service_enabled nova; then

    # Unset DOMAIN env variables that are not needed for keystone v2 and set OpenStack demo user auth
    unset OS_USER_DOMAIN_ID
    unset OS_PROJECT_DOMAIN_ID
    source ${TOP_DIR}/openrc demo demo

    # Create an SSH key to use for the instances
    DEVSTACK_LBAAS_SSH_KEY_NAME=DEVSTACK_LBAAS_SSH_KEY_RSA
    DEVSTACK_LBAAS_SSH_KEY_DIR=${TOP_DIR}
    DEVSTACK_LBAAS_SSH_KEY=${DEVSTACK_LBAAS_SSH_KEY_DIR}/${DEVSTACK_LBAAS_SSH_KEY_NAME}
    rm -f ${DEVSTACK_LBAAS_SSH_KEY}.pub ${DEVSTACK_LBAAS_SSH_KEY}
    ssh-keygen -b 2048 -t rsa -f ${DEVSTACK_LBAAS_SSH_KEY} -N ""
    openstack keypair create --public-key=${DEVSTACK_LBAAS_SSH_KEY}.pub ${DEVSTACK_LBAAS_SSH_KEY_NAME}

    # Add tcp/22,80 and icmp to default security group
    openstack security group rule create --protocol tcp --dst-port 22:22 default
    openstack security group rule create --protocol tcp --dst-port 80:80 default
    openstack security group rule create --protocol icmp default

    # Boot some instances
    NOVA_BOOT_ARGS="--key-name ${DEVSTACK_LBAAS_SSH_KEY_NAME} --image $(openstack image show cirros-0.3.5-x86_64-disk -f value -c id) --flavor 1 --nic net-id=$(openstack network show private -f value -c id)"

    openstack server create ${NOVA_BOOT_ARGS} node1
    openstack server create ${NOVA_BOOT_ARGS} node2

    echo "Waiting ${BOOT_DELAY} seconds for instances to boot"
    sleep ${BOOT_DELAY}

    IP1=$(openstack server show node1 | awk '/private/ {ip = substr($4, 9, length($4)-9) ; if (ip ~ "\\.") print ip ; else print $5}')
    IP2=$(openstack server show node2 | awk '/private/ {ip = substr($4, 9, length($4)-9) ; if (ip ~ "\\.") print ip ; else print $5}')

    touch ~/.ssh/known_hosts

    ssh-keygen -R ${IP1}
    ssh-keygen -R ${IP2}


    # Get Neutron router namespace details
    NAMESPACE_NAME='qrouter-'$(openstack router show router1 -f value -c id)
    NAMESPACE_CMD_PREFIX='sudo ip netns exec'

    # Run a simple web server on the instances
    chmod 0755 ${TOP_DIR}/webserver.sh
    $NAMESPACE_CMD_PREFIX $NAMESPACE_NAME scp -i ${DEVSTACK_LBAAS_SSH_KEY} -o StrictHostKeyChecking=no ${TOP_DIR}/webserver.sh cirros@${IP1}:webserver.sh
    $NAMESPACE_CMD_PREFIX $NAMESPACE_NAME scp -i ${DEVSTACK_LBAAS_SSH_KEY} -o StrictHostKeyChecking=no ${TOP_DIR}/webserver.sh cirros@${IP2}:webserver.sh
    $NAMESPACE_CMD_PREFIX $NAMESPACE_NAME ssh -o UserKnownHostsFile=/dev/null -i ${DEVSTACK_LBAAS_SSH_KEY} -o StrictHostKeyChecking=no -q cirros@${IP1} "screen -d -m sh webserver.sh"
    $NAMESPACE_CMD_PREFIX $NAMESPACE_NAME ssh -o UserKnownHostsFile=/dev/null -i ${DEVSTACK_LBAAS_SSH_KEY} -o StrictHostKeyChecking=no -q cirros@${IP2} "screen -d -m sh webserver.sh"

fi

if is_service_enabled octavia; then

    SUBNET_ID=$(openstack subnet show private-subnet -f value -c id)
    openstack loadbalancer create --name lb1 --vip-subnet-id $SUBNET_ID
    wait_for_loadbalancer_active lb1

    openstack loadbalancer listener create lb1 --protocol HTTP --protocol-port 80 --name listener1
    wait_for_loadbalancer_active lb1

    openstack loadbalancer pool create --lb-algorithm ROUND_ROBIN --listener listener1 --protocol HTTP --name pool1
    wait_for_loadbalancer_active lb1

    openstack loadbalancer member create --subnet-id $SUBNET_ID --address ${IP1} --protocol-port 80 pool1
    wait_for_loadbalancer_active lb1

    openstack loadbalancer member create --subnet-id $SUBNET_ID --address ${IP2} --protocol-port 80 pool1

fi

echo "How to test load balancing:"
echo ""
echo "${NAMESPACE_CMD_PREFIX} ${NAMESPACE_NAME} curl $(openstack loadbalancer show lb1 -f value -c vip_address)"
echo ""
