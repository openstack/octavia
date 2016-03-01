#!/usr/bin/env bash

# devstack plugin for octavia

function octavia_install {

    setup_develop $OCTAVIA_DIR
    if ! [ "$DISABLE_AMP_IMAGE_BUILD" == 'True' ]; then
        install_package qemu kpartx
        git_clone https://git.openstack.org/openstack/diskimage-builder.git $DEST/diskimage-builder master
        git_clone https://git.openstack.org/openstack/tripleo-image-elements.git $DEST/tripleo-image-elements master
        sudo -H -E pip install -r $DEST/diskimage-builder/requirements.txt
    fi
}

function build_octavia_worker_image {

    TOKEN=$(openstack token issue | grep ' id ' | get_field 2)
    die_if_not_set $LINENO TOKEN "Keystone failed to get token."

    # TODO(ptoohill): Tempfix..? -o option stopped working and it no longer saves image to working dir...
    if ! [ -f $OCTAVIA_AMP_IMAGE_FILE ]; then
        $OCTAVIA_DIR/diskimage-create/diskimage-create.sh -s 2
        # $OCTAVIA_DIR/diskimage-create/diskimage-create.sh -o $OCTAVIA_AMP_IMAGE_NAME
    fi
    upload_image file://${OCTAVIA_AMP_IMAGE_FILE} $TOKEN
    # upload_image file://${OCTAVIA_AMP_IMAGE_NAME}.qcow2 $TOKEN
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

    iniset $OCTAVIA_CONF database connection "mysql+pymysql://${DATABASE_USER}:${DATABASE_PASSWORD}@${DATABASE_HOST}:3306/octavia"

    iniset $OCTAVIA_CONF keystone_authtoken auth_uri ${KEYSTONE_AUTH_URI}/v2.0
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

    iniset $OCTAVIA_CONF DEFAULT api_handler queue_producer

    iniset $OCTAVIA_CONF oslo_messaging_rabbit rabbit_port 5672
    iniset $OCTAVIA_CONF oslo_messaging_rabbit rabbit_hosts localhost:5672

    iniset $OCTAVIA_CONF oslo_messaging rpc_thread_pool_size 2
    iniset $OCTAVIA_CONF oslo_messaging topic octavia_prov

    # Setting neutron request_poll_timeout
    iniset $NEUTRON_CONF octavia request_poll_timeout 3000

    # Uncomment other default options
    iniuncomment $OCTAVIA_CONF haproxy_amphora username
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
    ssh-keygen -b $OCTAVIA_AMP_SSH_KEY_BITS -t $OCTAVIA_AMP_SSH_KEY_TYPE -N "" -f ${OCTAVIA_AMP_SSH_KEY_PATH}
    iniset $OCTAVIA_CONF controller_worker amp_ssh_key_name ${OCTAVIA_AMP_SSH_KEY_NAME}

    # Used to communicate with the amphora over the mgmt network, may differ from amp_ssh_key in a real deployment.
    iniset $OCTAVIA_CONF haproxy_amphora key_path ${OCTAVIA_AMP_SSH_KEY_PATH}

    recreate_database_mysql octavia
    iniset $OCTAVIA_DIR/octavia/db/migration/alembic.ini alembic sqlalchemy.url "mysql+pymysql://${DATABASE_USER}:${DATABASE_PASSWORD}@${DATABASE_HOST}:3306/octavia"
    alembic -c $OCTAVIA_DIR/octavia/db/migration/alembic.ini upgrade head

    if [[ -a $OCTAVIA_CERTS_DIR ]] ; then
        rm -rf $OCTAVIA_CERTS_DIR
    fi
    source $OCTAVIA_DIR/bin/create_certificates.sh $OCTAVIA_CERTS_DIR $OCTAVIA_DIR/etc/certificates/openssl.cnf
    iniset $OCTAVIA_CONF haproxy_amphora client_cert ${OCTAVIA_CERTS_DIR}/client.pem
    iniset $OCTAVIA_CONF haproxy_amphora server_ca ${OCTAVIA_CERTS_DIR}/ca_01.pem
    iniset $OCTAVIA_CONF certificates ca_certificate ${OCTAVIA_CERTS_DIR}/ca_01.pem
    iniset $OCTAVIA_CONF certificates ca_private_key ${OCTAVIA_CERTS_DIR}/private/cakey.pem
    iniset $OCTAVIA_CONF certificates ca_private_key_passphrase foobar

}

function create_mgmt_network_interface {
    id_and_mac=$(neutron port-create --name octavia-health-manager-listen-port --binding:host_id=$(hostname) lb-mgmt-net | awk '/ id | mac_address / {print $4}')
    id_and_mac=($id_and_mac)
    MGMT_PORT_ID=${id_and_mac[0]}
    MGMT_PORT_MAC=${id_and_mac[1]}
    MGMT_PORT_IP=$(neutron port-show $MGMT_PORT_ID | awk '/ "ip_address": / {print $7; exit}' | sed -e 's/"//g' -e 's/,//g' -e 's/}//g')
    sudo ovs-vsctl -- --may-exist add-port br-int o-hm0 -- set Interface o-hm0 type=internal -- set Interface o-hm0 external-ids:iface-status=active -- set Interface o-hm0 external-ids:attached-mac=$MGMT_PORT_MAC -- set Interface o-hm0 external-ids:iface-id=$MGMT_PORT_ID
    sudo ip link set dev o-hm0 address $MGMT_PORT_MAC
    sudo dhclient -v o-hm0
    iniset $OCTAVIA_CONF health_manager controller_ip_port_list $MGMT_PORT_IP:$OCTAVIA_HM_LISTEN_PORT
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

    create_mgmt_network_interface
}

function configure_octavia_tempest {
    # Load the amp_network_list to tempest.conf and copy to tree

    # TODO (ptoohill): remove check when tempest structure merges
    if ! [ $OCTAVIA_TEMPEST == 'disabled' ] ; then
        iniset $TEMPEST_CONFIG controller_worker amp_network $1
        cp $TEMPEST_CONFIG $OCTAVIA_TEMPEST_DIR/etc
    fi
}

function create_amphora_flavor {
    nova flavor-create --is-public False m1.amphora ${OCTAVIA_AMP_FLAVOR_ID} 1024 2 1
}

function octavia_start {

    # Several steps in this function would more logically be in the configure function, but
    # we need nova, glance, and neutron to be running.

    nova keypair-add --pub-key ${OCTAVIA_AMP_SSH_KEY_PATH}.pub ${OCTAVIA_AMP_SSH_KEY_NAME}

    if ! [ "$DISABLE_AMP_IMAGE_BUILD" == 'True' ]; then
        build_octavia_worker_image
    fi

    OCTAVIA_AMP_IMAGE_ID=$(glance image-list | grep ${OCTAVIA_AMP_IMAGE_NAME} | awk '{print $2}')
    if [ -n "$OCTAVIA_AMP_IMAGE_ID" ]; then
        glance image-tag-update ${OCTAVIA_AMP_IMAGE_ID} ${OCTAVIA_AMP_IMAGE_TAG}
    fi
    iniset $OCTAVIA_CONF controller_worker amp_image_tag ${OCTAVIA_AMP_IMAGE_TAG}

    create_amphora_flavor

    # Create a management network.
    build_mgmt_network
    OCTAVIA_AMP_NETWORK_ID=$(neutron net-list | awk '/ lb-mgmt-net / {print $2}')

    iniset $OCTAVIA_CONF controller_worker amp_network ${OCTAVIA_AMP_NETWORK_ID}

    if is_service_enabled tempest; then
        configure_octavia_tempest ${OCTAVIA_AMP_NETWORK_ID}
    fi

    # Adds service and endpoint
    create_octavia_accounts

    run_process $OCTAVIA_API  "$OCTAVIA_API_BINARY $OCTAVIA_API_ARGS"
    run_process $OCTAVIA_CONSUMER  "$OCTAVIA_CONSUMER_BINARY $OCTAVIA_CONSUMER_ARGS"
    run_process $OCTAVIA_HOUSEKEEPER  "$OCTAVIA_HOUSEKEEPER_BINARY $OCTAVIA_HOUSEKEEPER_ARGS"
    run_process $OCTAVIA_HEALTHMANAGER  "$OCTAVIA_HEALTHMANAGER_BINARY $OCTAVIA_HEALTHMANAGER_ARGS"

}

function octavia_stop {
    # octavia-specific stop actions
    # TODO (ajmiller): If octavia behaves similarly to the neutron-lbaas driver,
    # there will be haproxy processes running as daemons.  The neutron-lbaas stop
    # code searches for and kills all haproxy procs.  That seems like a very
    # blunt club, is there a better way to do this?
    pids=$(ps aux | awk '/haproxy/ { print $2 }')
    [ ! -z "$pids" ] && sudo kill $pids
}
function octavia_configure_common {
    if is_service_enabled $OCTAVIA_SERVICE; then
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
    if [ ${OCTAVIA_AMP_SSH_KEY_NAME}x != x ] ; then
        nova keypair-delete ${OCTAVIA_AMP_SSH_KEY_NAME}
    fi
}

# check for service enabled
if is_service_enabled $OCTAVIA; then

    if ! is_service_enabled $Q_SVC || ! is_service_enabled $LBAAS_V2; then
        die "The neutron $Q_SVC and $LBAAS_V2 services must be enabled to use $OCTAVIA"
    fi

    # Check if an amphora image is already loaded
    AMPHORA_IMAGE_NAME=$(nova image-list | awk '/ amphora-x64-haproxy / {print $4}')
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

    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        # Perform installation of service source
        echo_summary "Installing octavia"
        octavia_install

    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        # Configure after the other layer 1 and 2 services have been configured
        # TODO: need to make sure this runs after LBaaS V2 configuration
        echo_summary "Configuring octavia"
        octavia_configure_common
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
