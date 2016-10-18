#!/bin/bash

set -ex

function wait_for_loadbalancer_active() {
  lb_name=$1
  while [ $(neutron lbaas-loadbalancer-list \
            | grep $lb_name | grep ACTIVE \
            | wc --lines) == 0 ]; do
  sleep 2
  done
}

BUILD_DIR=$(mktemp -d)
cp $( dirname "${BASH_SOURCE[0]}" )/httpd.go ${BUILD_DIR}
pushd ${BUILD_DIR}
  go build -ldflags "-linkmode external -extldflags -static" httpd.go
popd

SEC_GROUP_ID=$( openstack security group create "app-server-sec-group" \
                                                -f value -c id)
openstack security group rule create ${SEC_GROUP_ID} --protocol tcp \
                                                     --dst-port 22
openstack security group rule create ${SEC_GROUP_ID} --protocol tcp \
                                                     --dst-port 8080

ssh-keygen -q -b 4096 -t rsa -N "" -f ${BUILD_DIR}/id_rsa
openstack keypair create "app-server-key" --public-key ${BUILD_DIR}/id_rsa.pub

PRIVATE_NET_ID=$( openstack network show private -f value -c id )

neutron lbaas-loadbalancer-create --name lb1 private-subnet
wait_for_loadbalancer_active lb
neutron lbaas-listener-create --name listener1 \
                              --loadbalancer lb1 \
                              --protocol HTTP \
                              --protocol-port 80 \
                              --connection-limit 100000
wait_for_loadbalancer_active lb1
neutron lbaas-pool-create --name pool1 \
                          --lb-algorithm ROUND_ROBIN \
                          --listener listener1 \
                          --protocol HTTP
wait_for_loadbalancer_active lb1

for NUM in $( seq -f "%02.0f" 1 3 ); do
  # For higher scale testing you may want to use a large flavor assuming your
  # environment has capacity
  SERVER_ID=$( openstack server create app${NUM} \
               --image cirros-0.3.4-x86_64-uec \
               --flavor m1.tiny \
               --security-group ${SEC_GROUP_ID} \
               --nic net-id=${PRIVATE_NET_ID} \
               --key-name "app-server-key" \
               --wait -f value -c id )
  sleep 30
  SERVER_IPV4=$( openstack server show ${SERVER_ID} \
                 -c addresses -f value \
                 | perl -ne 'print $1 if /(\d+\.\d+\.\d+\.\d+)/' )

  scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
      -i ${BUILD_DIR}/id_rsa \
      ${BUILD_DIR}/httpd cirros@${SERVER_IPV4}:/dev/shm/
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
      -i ${BUILD_DIR}/id_rsa cirros@${SERVER_IPV4} \
      sudo sh -c "ulimit -n 100000; screen -d -m /dev/shm/httpd \
                  -id ${NUM} -port 8080"

  neutron lbaas-member-create --subnet private-subnet \
                              --address ${SERVER_IPV4} \
                              --name app${NUM} \
                              --protocol-port 8080 pool1
  wait_for_loadbalancer_active lb1
done

VIP_ADDRESS=$( neutron lbaas-loadbalancer-show lb1 -f value -c vip_address )
neutron lbaas-loadbalancer-show lb1

echo -e "You can now perform a load test against this load balancer. " \
        "For example:\n  ab -n 40000 -c 10000 http://${VIP_ADDRESS}/slow"
