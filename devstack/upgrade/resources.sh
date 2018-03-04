#!/bin/bash

set -o errexit

source $GRENADE_DIR/grenaderc
source $GRENADE_DIR/functions

source $TOP_DIR/openrc admin demo

set -o xtrace

OCTAVIA_GRENADE_DIR=$(dirname $0)
INSTANCE_USER_DATA_FILE=$OCTAVIA_GRENADE_DIR/vm_user_data.sh
DEFAULT_INSTANCE_FLAVOR=${DEFAULT_INSTANCE_FLAVOR:-m1.tiny}
PUBLIC_SUBNET_NAME=${PUBLIC_SUBNET_NAME:-"public-subnet"}
PRIVATE_NETWORK_NAME=${PRIVATE_NETWORK_NAME:-"private"}
PRIVATE_SUBNET_NAME=${PRIVATE_SUBNET_NAME:-"private-subnet"}

# $1: desired provisioning_status
# $2: desired operating_status
# $3..n: command with arguments and parameters
# TODO(cgoncalves): set timeout
function _wait_for_status {
    while :
    do
        eval $("${@:3}" -f shell -c provisioning_status -c operating_status)
        [[ $operating_status == "ONLINE" && $provisioning_status == "ACTIVE" ]] && break
        if [ $provisioning_status == "ERROR" ]; then
            die $LINENO "ERROR creating load balancer"
        fi
        sleep 10
    done
}

function create {
    # TODO(cgoncalves): make create idempotent for resiliancy in testing

    # NOTE(cgoncalves): OS_USERNAME=demo is set to overcome security group name collision
    sc_rule_id=$(OS_USERNAME=demo openstack security group rule create -f value -c id --protocol tcp --ingress --dst-port 80 default)
    resource_save octavia sc_rule_id $sc_rule_id

    # create VMs
    vm1_ips=$(openstack server create -f value -c addresses --user-data $INSTANCE_USER_DATA_FILE --flavor $DEFAULT_INSTANCE_FLAVOR --image $DEFAULT_IMAGE_NAME --network $PRIVATE_NETWORK_NAME --wait vm1)
    vm2_ips=$(openstack server create -f value -c addresses --user-data $INSTANCE_USER_DATA_FILE --flavor $DEFAULT_INSTANCE_FLAVOR --image $DEFAULT_IMAGE_NAME --network $PRIVATE_NETWORK_NAME --wait vm2)
    vm1_ipv4=$(echo $vm1_ips | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
    vm2_ipv4=$(echo $vm2_ips | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')

    openstack loadbalancer create --name lb1 --vip-subnet-id $PUBLIC_SUBNET_NAME
    _wait_for_status "ACTIVE" "ONLINE" openstack loadbalancer show lb1

    openstack loadbalancer listener create --name listener1 --protocol HTTP --protocol-port 80 lb1
    _wait_for_status "ACTIVE" "ONLINE" openstack loadbalancer listener show listener1

    openstack loadbalancer pool create --name pool1 --lb-algorithm ROUND_ROBIN --listener listener1 --protocol HTTP
    _wait_for_status "ACTIVE" "ONLINE" openstack loadbalancer pool show pool1

    openstack loadbalancer healthmonitor create --delay 5 --max-retries 4 --timeout 10 --type HTTP --url-path / --name hm1 pool1
    _wait_for_status "ACTIVE" "ONLINE" openstack loadbalancer healthmonitor show hm1

    openstack loadbalancer member create --subnet-id $PRIVATE_SUBNET_NAME --address $vm1_ipv4 --protocol-port 80 pool1 --name member1
    _wait_for_status "ACTIVE" "ONLINE" openstack loadbalancer member show pool1 member1

    openstack loadbalancer member create --subnet-id $PRIVATE_SUBNET_NAME --address $vm2_ipv4 --protocol-port 80 pool1 --name member2
    _wait_for_status "ACTIVE" "ONLINE" openstack loadbalancer member show pool1 member2

    lb_vip_ip=$(openstack loadbalancer show -f value -c vip_address lb1)
    resource_save octavia lb_vip_ip $lb_vip_ip

    echo "Octavia create: SUCCESS"
}

function verify {
    # verify control plane
    openstack loadbalancer show -f value -c operating_status lb1 | grep  -q ONLINE
    openstack loadbalancer listener show  -f value -c operating_status listener1 | grep  -q ONLINE
    openstack loadbalancer pool show  -f value -c operating_status pool1 | grep  -q ONLINE
    openstack loadbalancer healthmonitor show  -f value -c operating_status hm1 | grep  -q ONLINE
    openstack loadbalancer member show -f value -c operating_status pool1 member1 | grep  -q ONLINE
    openstack loadbalancer member show -f value -c operating_status pool1 member2 | grep  -q ONLINE

    # verify data plane
    lb_vip_ip=$(resource_get octavia lb_vip_ip)
    curl --include -D lb.out $lb_vip_ip
    grep -q "^HTTP/1.1 200 OK" lb.out

    echo "Octavia verify: SUCCESS"
}

function verify_noapi {
    # verify data plane
    lb_vip_ip=$(resource_get octavia lb_vip_ip)
    curl --include -D lb.out $lb_vip_ip
    grep -q "^HTTP/1.1 200 OK" lb.out

    echo "Octavia verify_noapi: SUCCESS"
}

function destroy {
    sc_rule_id=$(resource_get octavia sc_rule_id)

    # make destroy idempotent for resiliancy in testing
    openstack loadbalancer show lb1 && openstack loadbalancer delete --cascade lb1
    openstack server show vm1 && openstack server delete vm1
    openstack server show vm2 && openstack server delete vm2
    openstack security group rule show $sc_rule_id && openstack security group rule delete $sc_rule_id

    echo "Octavia destroy: SUCCESS"
}

# Dispatcher
case $1 in
    "create")
        create
        ;;
    "verify_noapi")
        verify_noapi
        ;;
    "verify")
        verify
        ;;
    "destroy")
        destroy
        ;;
    "force_destroy")
        set +o errexit
        destroy
        ;;
esac
