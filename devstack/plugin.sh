#!/usr/bin/env bash

# devstack plugin for octavia

function octavia_install {

    setup_develop $OCTAVIA_DIR
    if ! [ "$DISABLE_AMP_IMAGE_BUILD" == 'True' ]; then
        install_package qemu kpartx
        git_clone $TRIPLEO_IMAGE_ELEMENTS_REPO $TRIPLEO_IMAGE_ELEMENTS_DIR $TRIPLEO_IMAGE_ELEMENTS_BRANCH
    fi
}

function build_octavia_worker_image {

    # pull the agent code from the current code zuul has a reference to
    export DIB_REPOLOCATION_amphora_agent=$OCTAVIA_DIR
    export DIB_REPOREF_amphora_agent=$(git -C "$OCTAVIA_DIR" log -1 --pretty="format:%H")
    TOKEN=$(openstack token issue | grep ' id ' | get_field 2)
    die_if_not_set $LINENO TOKEN "Keystone failed to get token."

    if ! [ -f $OCTAVIA_AMP_IMAGE_FILE ]; then
        $OCTAVIA_DIR/diskimage-create/diskimage-create.sh -s 2 -o $OCTAVIA_AMP_IMAGE_FILE
    fi
    upload_image file://${OCTAVIA_AMP_IMAGE_FILE} $TOKEN

    image_id=$(glance image-list --property-filter name=${OCTAVIA_AMP_IMAGE_NAME} | awk '/ amphora-x64-haproxy / {print $2}')
    owner_id=$(glance image-show ${image_id} | awk '/ owner / {print $4}')
    iniset $OCTAVIA_CONF controller_worker amp_image_owner_id ${owner_id}

}

function create_octavia_accounts {
        create_service_user "neutron"

        if [[ "$KEYSTONE_CATALOG_BACKEND" = 'sql' ]]; then

            local neutron_service=$(get_or_create_service "octavia" \
                "octavia" "Octavia Service")
            get_or_create_endpoint $neutron_service \
                "$REGION_NAME" \
                "$OCTAVIA_PROTOCOL://$SERVICE_HOST:$OCTAVIA_PORT/" \
                "$OCTAVIA_PROTOCOL://$SERVICE_HOST:$OCTAVIA_PORT/" \
                "$OCTAVIA_PROTOCOL://$SERVICE_HOST:$OCTAVIA_PORT/"
        fi
}

function octavia_configure {

    sudo mkdir -m 755 -p $OCTAVIA_CONF_DIR
    safe_chown $STACK_USER $OCTAVIA_CONF_DIR

    if ! [ -e $OCTAVIA_CONF ] ; then
        cp $OCTAVIA_DIR/etc/octavia.conf $OCTAVIA_CONF
    fi

    # Change bind host
    iniset $OCTAVIA_CONF DEFAULT bind_host $SERVICE_HOST

    iniset $OCTAVIA_CONF database connection "mysql+pymysql://${DATABASE_USER}:${DATABASE_PASSWORD}@${DATABASE_HOST}:3306/octavia"

    if [ "$OCTAVIA_AUTH_VERSION" == "2" ] ; then
        AUTH_URI=${KEYSTONE_AUTH_URI%/v3}/v2.0
    else
        AUTH_URI=${KEYSTONE_AUTH_URI}
    fi
    iniset $OCTAVIA_CONF keystone_authtoken auth_uri ${AUTH_URI}
    iniset $OCTAVIA_CONF keystone_authtoken admin_user ${OCTAVIA_ADMIN_USER}
    iniset $OCTAVIA_CONF keystone_authtoken admin_tenant_name ${OCTAVIA_ADMIN_TENANT_NAME}
    iniset $OCTAVIA_CONF keystone_authtoken admin_password ${OCTAVIA_ADMIN_PASSWORD}
    iniset $OCTAVIA_CONF keystone_authtoken auth_version ${OCTAVIA_AUTH_VERSION}

    iniset $OCTAVIA_CONF controller_worker amp_flavor_id ${OCTAVIA_AMP_FLAVOR_ID}

    # Setting other required default options
    iniset $OCTAVIA_CONF controller_worker amphora_driver ${OCTAVIA_AMPHORA_DRIVER}
    iniset $OCTAVIA_CONF controller_worker compute_driver ${OCTAVIA_COMPUTE_DRIVER}
    iniset $OCTAVIA_CONF controller_worker network_driver ${OCTAVIA_NETWORK_DRIVER}

    iniuncomment $OCTAVIA_CONF health_manager heartbeat_key
    iniset $OCTAVIA_CONF health_manager heartbeat_key ${OCTAVIA_HEALTH_KEY}

    iniset $OCTAVIA_CONF house_keeping amphora_expiry_age ${OCTAVIA_AMP_EXPIRY_AGE}
    iniset $OCTAVIA_CONF house_keeping load_balancer_expiry_age ${OCTAVIA_LB_EXPIRY_AGE}

    iniset $OCTAVIA_CONF DEFAULT api_handler queue_producer

    iniset $OCTAVIA_CONF DEFAULT transport_url $(get_transport_url)

    iniset $OCTAVIA_CONF oslo_messaging rpc_thread_pool_size 2
    iniset $OCTAVIA_CONF oslo_messaging topic octavia_prov

    # Setting neutron request_poll_timeout
    iniset $NEUTRON_CONF octavia request_poll_timeout 3000
    iniset $NEUTRON_CONF octavia base_url http://$SERVICE_HOST:9876

    # Uncomment other default options
    iniuncomment $OCTAVIA_CONF haproxy_amphora base_path
    iniuncomment $OCTAVIA_CONF haproxy_amphora base_cert_dir
    iniuncomment $OCTAVIA_CONF haproxy_amphora connection_max_retries
    iniuncomment $OCTAVIA_CONF haproxy_amphora connection_retry_interval

    # devstack optimizations for tempest runs
    iniset $OCTAVIA_CONF haproxy_amphora connection_max_retries 1500
    iniset $OCTAVIA_CONF haproxy_amphora connection_retry_interval 1
    iniset $OCTAVIA_CONF controller_worker amp_active_retries 100
    iniset $OCTAVIA_CONF controller_worker amp_active_wait_sec 1

    if [[ -a $OCTAVIA_SSH_DIR ]] ; then
        rm -rf $OCTAVIA_SSH_DIR
    fi

    mkdir -m755 $OCTAVIA_SSH_DIR

    if [[ "$(trueorfalse False OCTAVIA_USE_PREGENERATED_SSH_KEY)" == "True" ]]; then
        cp -fp ${OCTAVIA_PREGENERATED_SSH_KEY_PATH} ${OCTAVIA_AMP_SSH_KEY_PATH}
        cp -fp ${OCTAVIA_PREGENERATED_SSH_KEY_PATH}.pub ${OCTAVIA_AMP_SSH_KEY_PATH}.pub
        chmod 0600 ${OCTAVIA_AMP_SSH_KEY_PATH}
    else
        ssh-keygen -b $OCTAVIA_AMP_SSH_KEY_BITS -t $OCTAVIA_AMP_SSH_KEY_TYPE -N "" -f ${OCTAVIA_AMP_SSH_KEY_PATH}
    fi
    iniset $OCTAVIA_CONF controller_worker amp_ssh_key_name ${OCTAVIA_AMP_SSH_KEY_NAME}

    # Used to communicate with the amphora over the mgmt network, may differ from amp_ssh_key in a real deployment.
    iniset $OCTAVIA_CONF haproxy_amphora key_path ${OCTAVIA_AMP_SSH_KEY_PATH}

    if [ $OCTAVIA_NODE == 'main' ] || [ $OCTAVIA_NODE == 'standalone' ] ; then
        recreate_database_mysql octavia
        octavia-db-manage upgrade head
    fi

    if [[ -a $OCTAVIA_CERTS_DIR ]] ; then
        rm -rf $OCTAVIA_CERTS_DIR
    fi

    if [[ "$(trueorfalse False OCTAVIA_USE_PREGENERATED_CERTS)" == "True" ]]; then
        cp -rfp ${OCTAVIA_PREGENERATED_CERTS_DIR} ${OCTAVIA_CERTS_DIR}
    else
        source $OCTAVIA_DIR/bin/create_certificates.sh $OCTAVIA_CERTS_DIR $OCTAVIA_DIR/etc/certificates/openssl.cnf
    fi

    iniset $OCTAVIA_CONF haproxy_amphora client_cert ${OCTAVIA_CERTS_DIR}/client.pem
    iniset $OCTAVIA_CONF haproxy_amphora server_ca ${OCTAVIA_CERTS_DIR}/ca_01.pem
    iniset $OCTAVIA_CONF certificates ca_certificate ${OCTAVIA_CERTS_DIR}/ca_01.pem
    iniset $OCTAVIA_CONF certificates ca_private_key ${OCTAVIA_CERTS_DIR}/private/cakey.pem
    iniset $OCTAVIA_CONF certificates ca_private_key_passphrase foobar

    # create dhclient.conf file for dhclient
    mkdir -m755 -p $OCTAVIA_DHCLIENT_DIR
    cp $OCTAVIA_DIR/etc/dhcp/dhclient.conf $OCTAVIA_DHCLIENT_CONF

}

function create_mgmt_network_interface {
    # Create security group and rules
    neutron security-group-create lb-health-mgr-sec-grp
    neutron security-group-rule-create --protocol udp --port-range-min $OCTAVIA_HM_LISTEN_PORT --port-range-max $OCTAVIA_HM_LISTEN_PORT lb-health-mgr-sec-grp

    id_and_mac=$(neutron port-create --name octavia-health-manager-$OCTAVIA_NODE-listen-port --security-group lb-health-mgr-sec-grp --device-owner Octavia:health-mgr --binding:host_id=$(hostname) lb-mgmt-net | awk '/ id | mac_address / {print $4}')

    id_and_mac=($id_and_mac)
    MGMT_PORT_ID=${id_and_mac[0]}
    MGMT_PORT_MAC=${id_and_mac[1]}
    MGMT_PORT_IP=$(neutron port-show $MGMT_PORT_ID | awk '/ "ip_address": / {print $7; exit}' | sed -e 's/"//g' -e 's/,//g' -e 's/}//g')
    sudo ovs-vsctl -- --may-exist add-port ${OVS_BRIDGE:-br-int} o-hm0 -- set Interface o-hm0 type=internal -- set Interface o-hm0 external-ids:iface-status=active -- set Interface o-hm0 external-ids:attached-mac=$MGMT_PORT_MAC -- set Interface o-hm0 external-ids:iface-id=$MGMT_PORT_ID
    sudo ip link set dev o-hm0 address $MGMT_PORT_MAC
    sudo dhclient -v o-hm0 -cf $OCTAVIA_DHCLIENT_CONF
    sudo iptables -I INPUT -i o-hm0 -p udp --dport 5555 -j ACCEPT

    if [ $OCTAVIA_CONTROLLER_IP_PORT_LIST == 'auto' ] ; then
        iniset $OCTAVIA_CONF health_manager controller_ip_port_list $MGMT_PORT_IP:$OCTAVIA_HM_LISTEN_PORT
    else
        iniset $OCTAVIA_CONF health_manager controller_ip_port_list $OCTAVIA_CONTROLLER_IP_PORT_LIST
    fi

    iniset $OCTAVIA_CONF health_manager bind_ip $MGMT_PORT_IP
    iniset $OCTAVIA_CONF health_manager bind_port $OCTAVIA_HM_LISTEN_PORT
}

function build_mgmt_network {
    # Create network and attach a subnet
    OCTAVIA_AMP_NETWORK_ID=$(neutron net-create lb-mgmt-net | awk '/ id / {print $4}')
    OCTAVIA_AMP_SUBNET_ID=$(neutron subnet-create --name lb-mgmt-subnet --allocation-pool start=$OCTAVIA_MGMT_SUBNET_START,end=$OCTAVIA_MGMT_SUBNET_END lb-mgmt-net $OCTAVIA_MGMT_SUBNET | awk '/ id / {print $4}')

    # Create security group and rules
    neutron security-group-create lb-mgmt-sec-grp
    neutron security-group-rule-create --protocol icmp lb-mgmt-sec-grp
    neutron security-group-rule-create --protocol tcp --port-range-min 22 --port-range-max 22 lb-mgmt-sec-grp
    neutron security-group-rule-create --protocol tcp --port-range-min 9443 --port-range-max 9443 lb-mgmt-sec-grp

    OCTAVIA_MGMT_SEC_GRP_ID=$(nova secgroup-list | awk ' / lb-mgmt-sec-grp / {print $2}')
    iniset ${OCTAVIA_CONF} controller_worker amp_secgroup_list ${OCTAVIA_MGMT_SEC_GRP_ID}

}

function configure_octavia_tempest {
    # Load the amp_boot_network_list to tempest.conf and copy to tree

    # TODO (ptoohill): remove check when tempest structure merges
    if ! [ $OCTAVIA_TEMPEST == 'disabled' ] ; then
        iniset $TEMPEST_CONFIG controller_worker amp_boot_network_list [$1]
        cp $TEMPEST_CONFIG $OCTAVIA_TEMPEST_DIR/etc
    fi
}

function create_amphora_flavor {
    nova flavor-create --is-public False m1.amphora ${OCTAVIA_AMP_FLAVOR_ID} 1024 2 1
}

function configure_octavia_api_haproxy {

    cp ${OCTAVIA_DIR}/devstack/etc/octavia/haproxy.cfg ${OCTAVIA_CONF_DIR}/haproxy.cfg

    sed -i.bak "s/OCTAVIA_PORT/${OCTAVIA_PORT}/" ${OCTAVIA_CONF_DIR}/haproxy.cfg

    iniset $OCTAVIA_CONF DEFAULT bind_port ${OCTAVIA_HA_PORT}

    NODES=(${OCTAVIA_NODES//,/ })

    for NODE in ${NODES[@]}; do
       DATA=(${NODE//:/ })
       NAME=$(echo -e "${DATA[0]}" | tr -d '[[:space:]]')
       IP=$(echo -e "${DATA[1]}" | tr -d '[[:space:]]')
       echo "   server octavia-${NAME} ${IP}:${OCTAVIA_HA_PORT} weight 1" >> ${OCTAVIA_CONF_DIR}/haproxy.cfg
    done

}

function octavia_start {

    # Several steps in this function would more logically be in the configure function, but
    # we need nova, glance, and neutron to be running.

    if [ $OCTAVIA_NODE != 'main' ] && [ $OCTAVIA_NODE != 'standalone' ] ; then
        # without the other services enabled apparently we don't have
        # credentials at this point
        TOP_DIR=$(cd $(dirname "$0") && pwd)
        source ${TOP_DIR}/openrc admin admin
    fi

    if [ $OCTAVIA_NODE == 'main' ] || [ $OCTAVIA_NODE == 'standalone' ] ; then
        # things that should only happen on the ha main node / or once
        nova keypair-add --pub-key ${OCTAVIA_AMP_SSH_KEY_PATH}.pub ${OCTAVIA_AMP_SSH_KEY_NAME}

        if ! [ "$DISABLE_AMP_IMAGE_BUILD" == 'True' ]; then
            build_octavia_worker_image
        fi

        OCTAVIA_AMP_IMAGE_ID=$(glance image-list | grep ${OCTAVIA_AMP_IMAGE_NAME} | awk '{print $2}')

        if [ -n "$OCTAVIA_AMP_IMAGE_ID" ]; then
            glance image-tag-update ${OCTAVIA_AMP_IMAGE_ID} ${OCTAVIA_AMP_IMAGE_TAG}
        fi
        create_amphora_flavor

        # Create a management network.
        build_mgmt_network

        create_octavia_accounts

        # Adds service and endpoint
        if is_service_enabled tempest; then
            configure_octavia_tempest ${OCTAVIA_AMP_NETWORK_ID}
        fi
    else
        OCTAVIA_AMP_IMAGE_ID=$(glance image-list | grep ${OCTAVIA_AMP_IMAGE_NAME} | awk '{print $2}')
    fi

    create_mgmt_network_interface

    iniset $OCTAVIA_CONF controller_worker amp_image_tag ${OCTAVIA_AMP_IMAGE_TAG}

    OCTAVIA_AMP_NETWORK_ID=$(neutron net-list | awk '/ lb-mgmt-net / {print $2}')

    iniset $OCTAVIA_CONF controller_worker amp_boot_network_list ${OCTAVIA_AMP_NETWORK_ID}

    if [ $OCTAVIA_NODE == 'main' ]; then
        configure_octavia_api_haproxy
        run_process $OCTAVIA_API_HAPROXY "/usr/sbin/haproxy -db -V -f ${OCTAVIA_CONF_DIR}/haproxy.cfg"
    fi

    run_process $OCTAVIA_API  "$OCTAVIA_API_BINARY $OCTAVIA_API_ARGS"
    run_process $OCTAVIA_CONSUMER  "$OCTAVIA_CONSUMER_BINARY $OCTAVIA_CONSUMER_ARGS"
    run_process $OCTAVIA_HOUSEKEEPER  "$OCTAVIA_HOUSEKEEPER_BINARY $OCTAVIA_HOUSEKEEPER_ARGS"
    run_process $OCTAVIA_HEALTHMANAGER  "$OCTAVIA_HEALTHMANAGER_BINARY $OCTAVIA_HEALTHMANAGER_ARGS"

}

function octavia_stop {
    # octavia-specific stop actions

    # Kill dhclient process started for o-hm0 interface
    pids=$(ps aux | awk '/o-hm0/ { print $2 }')
    [ ! -z "$pids" ] && sudo kill $pids
}
function octavia_configure_common {
    if is_service_enabled $OCTAVIA_SERVICE && [ $OCTAVIA_NODE == 'main' ] || [ $OCTAVIA_NODE = 'standalone' ] ; then
        inicomment $NEUTRON_LBAAS_CONF service_providers service_provider
        iniadd $NEUTRON_LBAAS_CONF service_providers service_provider $OCTAVIA_SERVICE_PROVIDER
    fi
}
function octavia_cleanup {

    if [ ${OCTAVIA_AMP_IMAGE_NAME}x != x ] ; then
         rm -rf ${OCTAVIA_AMP_IMAGE_NAME}*
    fi
    if [ ${OCTAVIA_AMP_SSH_KEY_NAME}x != x ] ; then
         rm -f  ${OCTAVIA_AMP_SSH_KEY_NAME}*
    fi
    if [ ${OCTAVIA_SSH_DIR}x != x ] ; then
         rm -rf ${OCTAVIA_SSH_DIR}
    fi
    if [ ${OCTAVIA_CONF_DIR}x != x ] ; then
         sudo rm -rf ${OCTAVIA_CONF_DIR}
    fi
    if [ ${OCTAVIA_AMP_SSH_KEY_PATH}x != x ] ; then
        rm -f ${OCTAVIA_AMP_SSH_KEY_PATH} ${OCTAVIA_AMP_SSH_KEY_PATH}.pub
    fi
    if [ $OCTAVIA_NODE == 'main' ] || [ $OCTAVIA_NODE == 'standalone' ] ; then
        if [ ${OCTAVIA_AMP_SSH_KEY_NAME}x != x ] ; then
            nova keypair-delete ${OCTAVIA_AMP_SSH_KEY_NAME}
        fi
    fi
}

# check for service enabled
if is_service_enabled $OCTAVIA; then
    if [ $OCTAVIA_NODE == 'main' ] || [ $OCTAVIA_NODE == 'standalone' ] ; then # main-ha node stuff only
        if ! is_service_enabled $Q_SVC; then
            die "The neutron $Q_SVC service must be enabled to use $OCTAVIA"
        fi

        # Check if an amphora image is already loaded
        AMPHORA_IMAGE_NAME=$(glance image-list | awk '/ amphora-x64-haproxy / {print $4}')
        export AMPHORA_IMAGE_NAME

        if [ "$DISABLE_AMP_IMAGE_BUILD" == 'True' ]; then
            echo "Found DISABLE_AMP_IMAGE_BUILD == True"
            echo "Skipping amphora image build"
        fi

        if [ "$AMPHORA_IMAGE_NAME" == 'amphora-x64-haproxy' ]; then
            echo "Found existing amphora image: $AMPHORA_IMAGE_NAME"
            echo "Skipping amphora image build"
            DISABLE_AMP_IMAGE_BUILD=True
            export DISABLE_AMP_IMAGE_BUILD
        fi
    fi

    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        # Perform installation of service source
        echo_summary "Installing octavia"
        octavia_install

    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        # Configure after the other layer 1 and 2 services have been configured
        # TODO: need to make sure this runs after LBaaS V2 configuration
        echo_summary "Configuring octavia"
        # octavia_configure_common
        octavia_configure

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize and start the octavia service
        echo_summary "Initializing octavia"
        octavia_start
    fi
fi

if [[ "$1" == "unstack" ]]; then
    # Shut down Octavia services
    if is_service_enabled $OCTAVIA; then
        echo_summary "Stopping octavia"
        octavia_stop
    fi
fi

if [[ "$1" == "clean" ]]; then
    # Remember clean.sh first calls unstack.sh
    if is_service_enabled $OCTAVIA; then
        echo_summary "Cleaning up octavia"
        octavia_cleanup
    fi
fi
