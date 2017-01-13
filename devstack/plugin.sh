#!/usr/bin/env bash

# devstack plugin for octavia

GET_PIP_CACHE_LOCATION=/opt/stack/cache/files/get-pip.py

function octavia_install {

    setup_develop $OCTAVIA_DIR
    if [ $OCTAVIA_NODE == 'main' ] || [ $OCTAVIA_NODE == 'standalone' ] ; then
        if ! [ "$DISABLE_AMP_IMAGE_BUILD" == 'True' ]; then
            install_package qemu kpartx
            git_clone $DISKIMAGE_BUILDER_REPO $DISKIMAGE_BUILDER_DIR $DISKIMAGE_BUILDER_BRANCH
            sudo -H -E pip install -r $DEST/diskimage-builder/requirements.txt
        fi
    fi
}

function set_octavia_worker_image_owner_id {
    image_id=$(openstack image list --property name=${OCTAVIA_AMP_IMAGE_NAME} -f value -c ID)
    owner_id=$(openstack image show ${image_id} -c owner -f value)
    iniset $OCTAVIA_CONF controller_worker amp_image_owner_id ${owner_id}
}

function build_octavia_worker_image {

    # pull the agent code from the current code zuul has a reference to
    if [ -n "$DIB_REPOLOCATION_pip_and_virtualenv" ]; then
        export DIB_REPOLOCATION_pip_and_virtualenv=$DIB_REPOLOCATION_pip_and_virtualenv
    elif [ -f $GET_PIP_CACHE_LOCATION ] ; then
        export DIB_REPOLOCATION_pip_and_virtualenv=file://$GET_PIP_CACHE_LOCATION
    fi
    export DIB_REPOLOCATION_amphora_agent=$OCTAVIA_DIR
    export DIB_REPOREF_amphora_agent=$(git -C "$OCTAVIA_DIR" log -1 --pretty="format:%H")
    TOKEN=$(openstack token issue | grep ' id ' | get_field 2)
    die_if_not_set $LINENO TOKEN "Keystone failed to get token."

    octavia_dib_tracing_arg=
    if [ "$OCTAVIA_DIB_TRACING" != "0" ]; then
        octavia_dib_tracing_arg="-x"
    fi
    if ! [ -f $OCTAVIA_AMP_IMAGE_FILE ]; then
        $OCTAVIA_DIR/diskimage-create/diskimage-create.sh $octavia_dib_tracing_arg -s 2 -o $OCTAVIA_AMP_IMAGE_FILE
    fi
    upload_image file://${OCTAVIA_AMP_IMAGE_FILE} $TOKEN

}

function create_octavia_accounts {
    create_service_user "octavia"

    local octavia_service=$(get_or_create_service "octavia" \
        "octavia" "Octavia Service")
    get_or_create_endpoint $octavia_service \
        "$REGION_NAME" \
        "$OCTAVIA_PROTOCOL://$SERVICE_HOST:$OCTAVIA_PORT/" \
        "$OCTAVIA_PROTOCOL://$SERVICE_HOST:$OCTAVIA_PORT/" \
        "$OCTAVIA_PROTOCOL://$SERVICE_HOST:$OCTAVIA_PORT/"
}

function octavia_configure {

    create_octavia_cache_dir

    sudo mkdir -m 755 -p $OCTAVIA_CONF_DIR
    safe_chown $STACK_USER $OCTAVIA_CONF_DIR

    if ! [ -e $OCTAVIA_CONF ] ; then
        cp $OCTAVIA_DIR/etc/octavia.conf $OCTAVIA_CONF
    fi

    # Change bind host
    iniset $OCTAVIA_CONF DEFAULT bind_host $SERVICE_HOST

    iniset $OCTAVIA_CONF database connection "mysql+pymysql://${DATABASE_USER}:${DATABASE_PASSWORD}@${DATABASE_HOST}:3306/octavia"

    # Configure keystone auth_token for all users
    configure_auth_token_middleware $OCTAVIA_CONF octavia $OCTAVIA_AUTH_CACHE_DIR

    # Ensure config is set up properly for authentication as admin
    iniset $OCTAVIA_CONF service_auth auth_url $KEYSTONE_AUTH_URI
    iniset $OCTAVIA_CONF service_auth auth_type password
    iniset $OCTAVIA_CONF service_auth username $OCTAVIA_USERNAME
    iniset $OCTAVIA_CONF service_auth password $OCTAVIA_PASSWORD
    iniset $OCTAVIA_CONF service_auth user_domain_name $OCTAVIA_USER_DOMAIN_NAME
    iniset $OCTAVIA_CONF service_auth project_name $OCTAVIA_PROJECT_NAME
    iniset $OCTAVIA_CONF service_auth project_domain_name $OCTAVIA_PROJECT_DOMAIN_NAME
    iniset $OCTAVIA_CONF service_auth cafile $SSL_BUNDLE_FILE
    iniset $OCTAVIA_CONF service_auth signing_dir $signing_dir
    iniset $OCTAVIA_CONF service_auth memcached_servers $SERVICE_HOST:11211

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
    iniuncomment $OCTAVIA_CONF haproxy_amphora rest_request_conn_timeout
    iniuncomment $OCTAVIA_CONF haproxy_amphora rest_request_read_timeout
    iniuncomment $OCTAVIA_CONF controller_worker amp_active_retries
    iniuncomment $OCTAVIA_CONF controller_worker amp_active_wait_sec

    # devstack optimizations for tempest runs
    iniset $OCTAVIA_CONF haproxy_amphora connection_max_retries 1500
    iniset $OCTAVIA_CONF haproxy_amphora connection_retry_interval 1
    iniset $OCTAVIA_CONF haproxy_amphora rest_request_conn_timeout ${OCTAVIA_AMP_CONN_TIMEOUT}
    iniset $OCTAVIA_CONF haproxy_amphora rest_request_read_timeout ${OCTAVIA_AMP_READ_TIMEOUT}
    iniset $OCTAVIA_CONF controller_worker amp_active_retries 100
    iniset $OCTAVIA_CONF controller_worker amp_active_wait_sec 2

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
    if [ $OCTAVIA_MGMT_PORT_IP != 'auto' ]; then
        SUBNET_ID=$(neutron subnet-show lb-mgmt-subnet | awk '/ id / {print $4}')
        PORT_FIXED_IP="--fixed-ip subnet_id=$SUBNET_ID,ip_address=$OCTAVIA_MGMT_PORT_IP"
    fi

    # TODO(johnsom) Change this to OSC when security group is working
    id_and_mac=$(neutron port-create --name octavia-health-manager-$OCTAVIA_NODE-listen-port --security-group lb-health-mgr-sec-grp --device-owner Octavia:health-mgr --binding:host_id=$(hostname) lb-mgmt-net $PORT_FIXED_IP | awk '/ id | mac_address / {print $4}')

    id_and_mac=($id_and_mac)
    MGMT_PORT_ID=${id_and_mac[0]}
    MGMT_PORT_MAC=${id_and_mac[1]}
    # TODO(johnsom) This gets the IPv4 address, should be updated for IPv6
    MGMT_PORT_IP=$(openstack port show -f value -c fixed_ips $MGMT_PORT_ID | awk '{FS=",| "; gsub(",",""); gsub("'\''",""); for(i = 1; i <= NF; ++i) {if ($i ~ /^ip_address/) {n=index($i, "="); if (substr($i, n+1) ~ "\\.") print substr($i, n+1)}}}')
    if [[ $Q_AGENT == "openvswitch" ]]; then
        sudo ovs-vsctl -- --may-exist add-port ${OVS_BRIDGE:-br-int} o-hm0 -- set Interface o-hm0 type=internal -- set Interface o-hm0 external-ids:iface-status=active -- set Interface o-hm0 external-ids:attached-mac=$MGMT_PORT_MAC -- set Interface o-hm0 external-ids:iface-id=$MGMT_PORT_ID
    elif [[ $Q_AGENT == "linuxbridge" ]]; then
        if ! ip link show o-hm0 ; then
            sudo ip link add o-hm0 type veth peer name o-bhm0
            NETID=$(openstack network show lb-mgmt-net -c id -f value)
            BRNAME=brq$(echo $NETID|cut -c 1-11)
            sudo brctl addif $BRNAME o-bhm0
            sudo ip link set o-bhm0 up
        fi
    fi
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
    OCTAVIA_AMP_NETWORK_ID=$(openstack network create lb-mgmt-net | awk '/ id / {print $4}')
    OCTAVIA_AMP_SUBNET_ID=$(openstack subnet create --subnet-range $OCTAVIA_MGMT_SUBNET --allocation-pool start=$OCTAVIA_MGMT_SUBNET_START,end=$OCTAVIA_MGMT_SUBNET_END --network lb-mgmt-net lb-mgmt-subnet | awk '/ id / {print $4}')

    # Create security group and rules
    openstack security group create lb-mgmt-sec-grp
    openstack security group rule create --protocol icmp lb-mgmt-sec-grp
    openstack security group rule create --protocol tcp --dst-port 22 lb-mgmt-sec-grp
    openstack security group rule create --protocol tcp --dst-port 9443 lb-mgmt-sec-grp
    openstack security group rule create --protocol icmpv6 --ethertype IPv6 --remote-ip ::/0 lb-mgmt-sec-grp
    openstack security group rule create --protocol tcp --dst-port 22 --ethertype IPv6 --remote-ip ::/0 lb-mgmt-sec-grp
    openstack security group rule create --protocol tcp --dst-port 9443 --ethertype IPv6 --remote-ip ::/0 lb-mgmt-sec-grp

    # Create security group and rules
    openstack security group create lb-health-mgr-sec-grp
    openstack security group rule create --protocol udp --dst-port $OCTAVIA_HM_LISTEN_PORT lb-health-mgr-sec-grp
    openstack security group rule create --protocol udp --dst-port $OCTAVIA_HM_LISTEN_PORT --ethertype IPv6 --remote-ip ::/0 lb-health-mgr-sec-grp
}

function configure_lb_mgmt_sec_grp {
    OCTAVIA_MGMT_SEC_GRP_ID=$(openstack security group list | awk ' / lb-mgmt-sec-grp / {print $2}')
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
    # Pass even if it exists to avoid race condition on multinode
    openstack flavor create --id auto --ram 1024 --disk 2 --vcpus 1 --private m1.amphora -f value -c id || true
    amp_flavor_id=$(openstack flavor list --all -c ID -c Name | awk ' / m1.amphora / {print $2}')
    iniset $OCTAVIA_CONF controller_worker amp_flavor_id $amp_flavor_id
}

function configure_octavia_api_haproxy {

    install_package haproxy

    cp ${OCTAVIA_DIR}/devstack/etc/octavia/haproxy.cfg ${OCTAVIA_CONF_DIR}/haproxy.cfg

    sed -i.bak "s/OCTAVIA_PORT/${OCTAVIA_PORT}/" ${OCTAVIA_CONF_DIR}/haproxy.cfg

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
        openstack keypair create --public-key ${OCTAVIA_AMP_SSH_KEY_PATH}.pub ${OCTAVIA_AMP_SSH_KEY_NAME}

        # Check if an amphora image is already loaded
        AMPHORA_IMAGE_NAME=$(openstack image list --property name=${OCTAVIA_AMP_IMAGE_NAME} -f value -c Name)
        export AMPHORA_IMAGE_NAME

        if [ "$AMPHORA_IMAGE_NAME" == ${OCTAVIA_AMP_IMAGE_NAME} ]; then
            echo "Found existing amphora image: $AMPHORA_IMAGE_NAME"
            echo "Skipping amphora image build"
            export DISABLE_AMP_IMAGE_BUILD=True
        fi

        if ! [ "$DISABLE_AMP_IMAGE_BUILD" == 'True' ]; then
            build_octavia_worker_image
        fi

        OCTAVIA_AMP_IMAGE_ID=$(openstack image list -f value --property name=${OCTAVIA_AMP_IMAGE_NAME} -c ID)

        if [ -n "$OCTAVIA_AMP_IMAGE_ID" ]; then
            openstack image set --tag ${OCTAVIA_AMP_IMAGE_TAG} ${OCTAVIA_AMP_IMAGE_ID}
        fi

        # Create a management network.
        build_mgmt_network

        create_octavia_accounts

        # Adds service and endpoint
        if is_service_enabled tempest; then
            configure_octavia_tempest ${OCTAVIA_AMP_NETWORK_ID}
        fi
    fi

    if ! [ "$DISABLE_AMP_IMAGE_BUILD" == 'True' ]; then
        set_octavia_worker_image_owner_id
    fi
    create_amphora_flavor

    create_mgmt_network_interface
    configure_lb_mgmt_sec_grp

    iniset $OCTAVIA_CONF controller_worker amp_image_tag ${OCTAVIA_AMP_IMAGE_TAG}

    OCTAVIA_AMP_NETWORK_ID=$(openstack network list | awk '/ lb-mgmt-net / {print $2}')

    iniset $OCTAVIA_CONF controller_worker amp_boot_network_list ${OCTAVIA_AMP_NETWORK_ID}

    if [ $OCTAVIA_NODE == 'main' ]; then
        configure_octavia_api_haproxy
        run_process $OCTAVIA_API_HAPROXY "/usr/sbin/haproxy -db -V -f ${OCTAVIA_CONF_DIR}/haproxy.cfg"
        # make sure octavia is reachable from haproxy
        iniset $OCTAVIA_CONF DEFAULT bind_port ${OCTAVIA_HA_PORT}
        iniset $OCTAVIA_CONF DEFAULT bind_host 0.0.0.0
    fi
    if [ $OCTAVIA_NODE != 'main' ] && [ $OCTAVIA_NODE != 'standalone' ] ; then
        # make sure octavia is reachable from haproxy from main node
        iniset $OCTAVIA_CONF DEFAULT bind_port ${OCTAVIA_HA_PORT}
        iniset $OCTAVIA_CONF DEFAULT bind_host 0.0.0.0
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
    if [[ $Q_AGENT == "linuxbridge" ]]; then
        if ip link show o-hm0 ; then
            sudo ip link del o-hm0
        fi
    fi
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
            openstack keypair delete ${OCTAVIA_AMP_SSH_KEY_NAME}
        fi
    fi

    sudo rm -rf $NOVA_STATE_PATH $NOVA_AUTH_CACHE_DIR
}

# create_octavia_cache_dir() - Part of the configure_octavia() process
function create_octavia_cache_dir {
    # Create cache dir
    sudo install -d -o $STACK_USER $OCTAVIA_AUTH_CACHE_DIR
    rm -f $OCTAVIA_AUTH_CACHE_DIR/*
}

# check for service enabled
if is_service_enabled $OCTAVIA; then
    if [ $OCTAVIA_NODE == 'main' ] || [ $OCTAVIA_NODE == 'standalone' ] ; then # main-ha node stuff only
        if ! is_service_enabled $Q_SVC; then
            die "The neutron $Q_SVC service must be enabled to use $OCTAVIA"
        fi

        if [ "$DISABLE_AMP_IMAGE_BUILD" == 'True' ]; then
            echo "Found DISABLE_AMP_IMAGE_BUILD == True"
            echo "Skipping amphora image build"
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
