#!/usr/bin/env bash

# devstack plugin for octavia

GET_PIP_CACHE_LOCATION=/opt/stack/cache/files/get-pip.py

function octavia_install {
    setup_develop $OCTAVIA_DIR
    if [ $OCTAVIA_NODE == 'main' ] || [ $OCTAVIA_NODE == 'standalone' ] ; then
        if ! [ "$DISABLE_AMP_IMAGE_BUILD" == 'True' ]; then
            if [[ ${DISTRO} =~ "rhel7" ]]; then
                # Installing qemu would bring in the default OS qemu package,
                # which is too old for Pike and later releases
                # See https://review.openstack.org/#/c/438325 for details
                install_package qemu-kvm
            else
                install_package qemu
            fi
        fi
    fi
}

function octaviaclient_install {
    if use_library_from_git "python-octaviaclient"; then
        git_clone_by_name "python-octaviaclient"
        setup_dev_lib "python-octaviaclient"
    else
        pip_install_gr python-octaviaclient
    fi
}

function install_diskimage_builder {
    if use_library_from_git "diskimage-builder"; then
        GITREPO["diskimage-builder"]=$DISKIMAGE_BUILDER_REPO_URL
        GITDIR["diskimage-builder"]=$DISKIMAGE_BUILDER_DIR
        GITBRANCH["diskimage-builder"]=$DISKIMAGE_BUILDER_REPO_REF
        git_clone_by_name "diskimage-builder"
        setup_dev_lib "diskimage-builder"
    fi
}

function set_octavia_worker_image_owner_id {
    image_id=$(openstack image list --property name=${OCTAVIA_AMP_IMAGE_NAME} -f value -c ID)
    owner_id=$(openstack image show ${image_id} -c owner -f value)
    iniset $OCTAVIA_CONF controller_worker amp_image_owner_id ${owner_id}
}

function build_octavia_worker_image {
    # set up diskimage-builder if we need to
    install_diskimage_builder

    # pull the agent code from the current code zuul has a reference to
    if [ -n "$DIB_REPOLOCATION_pip_and_virtualenv" ]; then
        export DIB_REPOLOCATION_pip_and_virtualenv=$DIB_REPOLOCATION_pip_and_virtualenv
    elif [ -f $GET_PIP_CACHE_LOCATION ] ; then
        export DIB_REPOLOCATION_pip_and_virtualenv=file://$GET_PIP_CACHE_LOCATION
    fi
    export DIB_REPOLOCATION_amphora_agent=$OCTAVIA_DIR
    export DIB_REPOREF_amphora_agent=$(git --git-dir="$OCTAVIA_DIR/.git" log -1 --pretty="format:%H")

    TOKEN=$(openstack token issue -f value -c id)
    die_if_not_set $LINENO TOKEN "Keystone failed to get token."

    octavia_dib_tracing_arg=
    if [ "$OCTAVIA_DIB_TRACING" != "0" ]; then
        octavia_dib_tracing_arg="-x"
    fi
    if [[ ${OCTAVIA_AMP_BASE_OS:+1} ]] ; then
    export PARAM_OCTAVIA_AMP_BASE_OS='-i '$OCTAVIA_AMP_BASE_OS
    fi
    if [[ ${OCTAVIA_AMP_DISTRIBUTION_RELEASE_ID:+1} ]] ; then
    export PARAM_OCTAVIA_AMP_DISTRIBUTION_RELEASE_ID='-d '$OCTAVIA_AMP_DISTRIBUTION_RELEASE_ID
    fi
    if [[ ${OCTAVIA_AMP_IMAGE_SIZE:+1} ]] ; then
    export PARAM_OCTAVIA_AMP_IMAGE_SIZE='-s '$OCTAVIA_AMP_IMAGE_SIZE
    fi
    if ! [ -f $OCTAVIA_AMP_IMAGE_FILE ]; then
        $OCTAVIA_DIR/diskimage-create/diskimage-create.sh $octavia_dib_tracing_arg -o $OCTAVIA_AMP_IMAGE_FILE ${PARAM_OCTAVIA_AMP_BASE_OS:-} ${PARAM_OCTAVIA_AMP_DISTRIBUTION_RELEASE_ID:-} ${PARAM_OCTAVIA_AMP_IMAGE_SIZE:-}
    fi
    upload_image file://${OCTAVIA_AMP_IMAGE_FILE} $TOKEN

}

function _configure_octavia_apache_wsgi {

    # Make sure mod_wsgi is enabled in apache
    # This is important for multinode where other services have not yet
    # enabled it.
    install_apache_wsgi

    local octavia_apache_conf
    octavia_apache_conf=$(apache_site_config_for octavia)

    # Use the alternate port if we are running multinode behind haproxy
    if [ $OCTAVIA_NODE != 'standalone' ] && [ $OCTAVIA_NODE != 'api' ]; then
        local octavia_api_port=$OCTAVIA_HA_PORT
    else
        local octavia_api_port=$OCTAVIA_PORT
    fi
    local octavia_ssl=""
    local octavia_certfile=""
    local octavia_keyfile=""
    local venv_path=""

    if is_ssl_enabled_service octavia; then
        octavia_ssl="SSLEngine On"
        octavia_certfile="SSLCertificateFile $OCTAVIA_SSL_CERT"
        octavia_keyfile="SSLCertificateKeyFile $OCTAVIA_SSL_KEY"
    fi

    if [[ ${USE_VENV} = True ]]; then
        venv_path="python-path=${PROJECT_VENV["octavia"]}/lib/$(python_version)/site-packages"
    fi

    sudo cp ${OCTAVIA_DIR}/devstack/files/wsgi/octavia-api.template $octavia_apache_conf
    sudo sed -e "
        s|%OCTAVIA_SERVICE_PORT%|$octavia_api_port|g;
        s|%USER%|$APACHE_USER|g;
        s|%APACHE_NAME%|$APACHE_NAME|g;
        s|%SSLENGINE%|$octavia_ssl|g;
        s|%SSLCERTFILE%|$octavia_certfile|g;
        s|%SSLKEYFILE%|$octavia_keyfile|g;
        s|%VIRTUALENV%|$venv_path|g
        s|%APIWORKERS%|$API_WORKERS|g;
    " -i $octavia_apache_conf

}

function _configure_octavia_apache_uwsgi {
    write_uwsgi_config "$OCTAVIA_UWSGI_CONF" "$OCTAVIA_UWSGI_APP" "/$OCTAVIA_SERVICE_TYPE"
}


function _cleanup_octavia_apache_wsgi {
    if [[ "$WSGI_MODE" == "uwsgi" ]]; then
        remove_uwsgi_config "$OCTAVIA_UWSGI_CONF" "$OCTAVIA_UWSGI_APP"
        restart_apache_server
    else
        sudo rm -f $(apache_site_config_for octavia)
        restart_apache_server
    fi
}

function _start_octavia_apache_wsgi {
    if [[ "$WSGI_MODE" == "uwsgi" ]]; then
        run_process o-api "$OCTAVIA_BIN_DIR/uwsgi --ini $OCTAVIA_UWSGI_CONF"
        enable_apache_site octavia-wsgi
    else
        enable_apache_site octavia
        restart_apache_server
    fi
}

function _stop_octavia_apache_wsgi {
    if [[ "$WSGI_MODE" == "uwsgi" ]]; then
        disable_apache_site octavia-wsgi
        stop_process o-api
    else
        disable_apache_site octavia
        restart_apache_server
    fi
}

function create_octavia_accounts {
    create_service_user $OCTAVIA

    # Increase the service account secgroups quota
    # This is imporant for concurrent tempest testing
    openstack quota set --secgroups 100 $SERVICE_PROJECT_NAME

    local octavia_service=$(get_or_create_service "octavia" \
        $OCTAVIA_SERVICE_TYPE "Octavia Load Balancing Service")

    if [[ "$WSGI_MODE" == "uwsgi" ]]; then
        get_or_create_endpoint $octavia_service \
            "$REGION_NAME" \
            "$OCTAVIA_PROTOCOL://$SERVICE_HOST/$OCTAVIA_SERVICE_TYPE" \
            "$OCTAVIA_PROTOCOL://$SERVICE_HOST/$OCTAVIA_SERVICE_TYPE" \
            "$OCTAVIA_PROTOCOL://$SERVICE_HOST/$OCTAVIA_SERVICE_TYPE"
    else
        get_or_create_endpoint $octavia_service \
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

    # Use devstack logging configuration
    setup_logging $OCTAVIA_CONF

    # Change bind host
    iniset $OCTAVIA_CONF DEFAULT bind_host $SERVICE_HOST

    iniset $OCTAVIA_CONF database connection "mysql+pymysql://${DATABASE_USER}:${DATABASE_PASSWORD}@${DATABASE_HOST}:3306/octavia"

    # Configure keystone auth_token for all users
    configure_auth_token_middleware $OCTAVIA_CONF octavia

    # Ensure config is set up properly for authentication as admin
    iniset $OCTAVIA_CONF service_auth auth_url $OS_AUTH_URL
    iniset $OCTAVIA_CONF service_auth auth_type password
    iniset $OCTAVIA_CONF service_auth username $OCTAVIA_USERNAME
    iniset $OCTAVIA_CONF service_auth password $OCTAVIA_PASSWORD
    iniset $OCTAVIA_CONF service_auth user_domain_name $OCTAVIA_USER_DOMAIN_NAME
    iniset $OCTAVIA_CONF service_auth project_name $OCTAVIA_PROJECT_NAME
    iniset $OCTAVIA_CONF service_auth project_domain_name $OCTAVIA_PROJECT_DOMAIN_NAME
    iniset $OCTAVIA_CONF service_auth cafile $SSL_BUNDLE_FILE
    iniset $OCTAVIA_CONF service_auth memcached_servers $SERVICE_HOST:11211

    # Setting other required default options
    iniset $OCTAVIA_CONF controller_worker amphora_driver ${OCTAVIA_AMPHORA_DRIVER}
    iniset $OCTAVIA_CONF controller_worker compute_driver ${OCTAVIA_COMPUTE_DRIVER}
    iniset $OCTAVIA_CONF controller_worker network_driver ${OCTAVIA_NETWORK_DRIVER}
    iniset $OCTAVIA_CONF controller_worker amp_image_tag ${OCTAVIA_AMP_IMAGE_TAG}

    iniuncomment $OCTAVIA_CONF health_manager heartbeat_key
    iniset $OCTAVIA_CONF health_manager heartbeat_key ${OCTAVIA_HEALTH_KEY}

    iniset $OCTAVIA_CONF house_keeping amphora_expiry_age ${OCTAVIA_AMP_EXPIRY_AGE}
    iniset $OCTAVIA_CONF house_keeping load_balancer_expiry_age ${OCTAVIA_LB_EXPIRY_AGE}

    iniset $OCTAVIA_CONF DEFAULT api_handler queue_producer

    iniset $OCTAVIA_CONF DEFAULT transport_url $(get_transport_url)

    iniset $OCTAVIA_CONF oslo_messaging rpc_thread_pool_size 2
    iniset $OCTAVIA_CONF oslo_messaging topic octavia_prov

    # TODO(nmagnezi): Remove this when neutron-lbaas gets deprecated
    # Setting neutron request_poll_timeout
    iniset $NEUTRON_CONF octavia request_poll_timeout 3000
    if [[ "$WSGI_MODE" == "uwsgi" ]]; then
        iniadd $NEUTRON_CONF octavia base_url "$OCTAVIA_PROTOCOL://$SERVICE_HOST/$OCTAVIA_SERVICE_TYPE"
    else
        iniadd $NEUTRON_CONF octavia base_url "$OCTAVIA_PROTOCOL://$SERVICE_HOST:$OCTAVIA_PORT/"
    fi

    # Uncomment other default options
    iniuncomment $OCTAVIA_CONF haproxy_amphora base_path
    iniuncomment $OCTAVIA_CONF haproxy_amphora base_cert_dir
    iniuncomment $OCTAVIA_CONF haproxy_amphora connection_max_retries
    iniuncomment $OCTAVIA_CONF haproxy_amphora connection_retry_interval
    iniuncomment $OCTAVIA_CONF haproxy_amphora rest_request_conn_timeout
    iniuncomment $OCTAVIA_CONF haproxy_amphora rest_request_read_timeout
    iniuncomment $OCTAVIA_CONF controller_worker amp_active_retries
    iniuncomment $OCTAVIA_CONF controller_worker amp_active_wait_sec
    iniuncomment $OCTAVIA_CONF controller_worker workers
    iniuncomment $OCTAVIA_CONF controller_worker loadbalancer_topology

    iniset $OCTAVIA_CONF controller_worker loadbalancer_topology ${OCTAVIA_LB_TOPOLOGY}

    # devstack optimizations for tempest runs
    iniset $OCTAVIA_CONF haproxy_amphora connection_max_retries 1500
    iniset $OCTAVIA_CONF haproxy_amphora connection_retry_interval 1
    iniset $OCTAVIA_CONF haproxy_amphora rest_request_conn_timeout ${OCTAVIA_AMP_CONN_TIMEOUT}
    iniset $OCTAVIA_CONF haproxy_amphora rest_request_read_timeout ${OCTAVIA_AMP_READ_TIMEOUT}
    iniset $OCTAVIA_CONF controller_worker amp_active_retries 100
    iniset $OCTAVIA_CONF controller_worker amp_active_wait_sec 2
    iniset $OCTAVIA_CONF controller_worker workers 2

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

    if [ $OCTAVIA_NODE == 'main' ] || [ $OCTAVIA_NODE == 'standalone' ] || [ $OCTAVIA_NODE == 'api' ]; then
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
    iniset $OCTAVIA_CONF certificates server_certs_key_passphrase insecure-key-do-not-use-this-key

    if [[ "$OCTAVIA_USE_LEGACY_RBAC" == "True" ]]; then
        cp $OCTAVIA_DIR/etc/policy/admin_or_owner-policy.json $OCTAVIA_CONF_DIR/policy.json
    fi

    # create dhclient.conf file for dhclient
    sudo mkdir -m755 -p $OCTAVIA_DHCLIENT_DIR
    sudo cp $OCTAVIA_DIR/etc/dhcp/dhclient.conf $OCTAVIA_DHCLIENT_CONF

    if [[ "$OCTAVIA_USE_MOD_WSGI" == "True" ]]; then
        if [[ "$WSGI_MODE" == "uwsgi" ]]; then
            _configure_octavia_apache_uwsgi
        else
            _configure_octavia_apache_wsgi
        fi
    fi

    if [ $OCTAVIA_NODE == 'main' ]; then
        configure_octavia_api_haproxy
        # make sure octavia is reachable from haproxy
        iniset $OCTAVIA_CONF DEFAULT bind_port ${OCTAVIA_HA_PORT}
        iniset $OCTAVIA_CONF DEFAULT bind_host 0.0.0.0
    fi
    if [ $OCTAVIA_NODE != 'main' ] && [ $OCTAVIA_NODE != 'standalone' ] ; then
        # make sure octavia is reachable from haproxy from main node
        iniset $OCTAVIA_CONF DEFAULT bind_port ${OCTAVIA_HA_PORT}
        iniset $OCTAVIA_CONF DEFAULT bind_host 0.0.0.0
    fi
}

function create_mgmt_network_interface {
    if [ $OCTAVIA_MGMT_PORT_IP != 'auto' ]; then
        SUBNET_ID=$(openstack subnet show lb-mgmt-subnet -f value -c id)
        PORT_FIXED_IP="--fixed-ip subnet=$SUBNET_ID,ip-address=$OCTAVIA_MGMT_PORT_IP"
    fi

    MGMT_PORT_ID=$(openstack port create --security-group lb-health-mgr-sec-grp --device-owner Octavia:health-mgr --host=$(hostname) -c id -f value --network lb-mgmt-net $PORT_FIXED_IP octavia-health-manager-$OCTAVIA_NODE-listen-port)
    MGMT_PORT_MAC=$(openstack port show -c mac_address -f value $MGMT_PORT_ID)

    # TODO(johnsom) This gets the IPv4 address, should be updated for IPv6
    MGMT_PORT_IP=$(openstack port show -f value -c fixed_ips $MGMT_PORT_ID | awk '{FS=",| "; gsub(",",""); gsub("'\''",""); for(i = 1; i <= NF; ++i) {if ($i ~ /^ip_address/) {n=index($i, "="); if (substr($i, n+1) ~ "\\.") print substr($i, n+1)}}}')
    if function_exists octavia_create_network_interface_device ; then
        octavia_create_network_interface_device o-hm0 $MGMT_PORT_ID $MGMT_PORT_MAC
    elif [[ $NEUTRON_AGENT == "openvswitch" || $Q_AGENT == "openvswitch" ]]; then
        sudo ovs-vsctl -- --may-exist add-port ${OVS_BRIDGE:-br-int} o-hm0 -- set Interface o-hm0 type=internal -- set Interface o-hm0 external-ids:iface-status=active -- set Interface o-hm0 external-ids:attached-mac=$MGMT_PORT_MAC -- set Interface o-hm0 external-ids:iface-id=$MGMT_PORT_ID -- set Interface o-hm0 external-ids:skip_cleanup=true
    elif [[ $NEUTRON_AGENT == "linuxbridge" || $Q_AGENT == "linuxbridge" ]]; then
        if ! ip link show o-hm0 ; then
            sudo ip link add o-hm0 type veth peer name o-bhm0
            NETID=$(openstack network show lb-mgmt-net -c id -f value)
            BRNAME=brq$(echo $NETID|cut -c 1-11)
            sudo brctl addif $BRNAME o-bhm0
            sudo ip link set o-bhm0 up
        fi
    else
        die "Unknown network controller. Please define octavia_create_network_interface_device"
    fi
    sudo ip link set dev o-hm0 address $MGMT_PORT_MAC
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
    OCTAVIA_AMP_NETWORK_ID=$(openstack network create lb-mgmt-net -f value -c id)
    OCTAVIA_AMP_SUBNET_ID=$(openstack subnet create --subnet-range $OCTAVIA_MGMT_SUBNET --allocation-pool start=$OCTAVIA_MGMT_SUBNET_START,end=$OCTAVIA_MGMT_SUBNET_END --network lb-mgmt-net lb-mgmt-subnet -f value -c id)

    # Create security group and rules
    openstack security group create lb-mgmt-sec-grp
    openstack security group rule create --protocol icmp lb-mgmt-sec-grp
    openstack security group rule create --protocol tcp --dst-port 22 lb-mgmt-sec-grp
    openstack security group rule create --protocol tcp --dst-port 9443 lb-mgmt-sec-grp
    if [ $IPV6_ENABLED == 'true' ] ; then
        openstack security group rule create --protocol icmpv6 --ethertype IPv6 --remote-ip ::/0 lb-mgmt-sec-grp
        openstack security group rule create --protocol tcp --dst-port 22 --ethertype IPv6 --remote-ip ::/0 lb-mgmt-sec-grp
        openstack security group rule create --protocol tcp --dst-port 9443 --ethertype IPv6 --remote-ip ::/0 lb-mgmt-sec-grp
    fi

    # Create security group and rules
    openstack security group create lb-health-mgr-sec-grp
    openstack security group rule create --protocol udp --dst-port $OCTAVIA_HM_LISTEN_PORT lb-health-mgr-sec-grp
    if [ $IPV6_ENABLED == 'true' ] ; then
        openstack security group rule create --protocol udp --dst-port $OCTAVIA_HM_LISTEN_PORT --ethertype IPv6 --remote-ip ::/0 lb-health-mgr-sec-grp
    fi
}

function configure_lb_mgmt_sec_grp {
    OCTAVIA_MGMT_SEC_GRP_ID=$(openstack security group show lb-mgmt-sec-grp -f value -c id)
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
    openstack flavor create --id auto --ram 1024 --disk ${OCTAVIA_AMP_IMAGE_SIZE:-2} --vcpus 1 --private m1.amphora -f value -c id || true
    amp_flavor_id=$(openstack flavor show m1.amphora -f value -c id)
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

    if  ! ps aux | grep -q [o]-hm0 && [ $OCTAVIA_NODE != 'api' ] ; then
        sudo dhclient -v o-hm0 -cf $OCTAVIA_DHCLIENT_CONF
    fi

    if [ $OCTAVIA_NODE == 'main' ]; then
        run_process $OCTAVIA_API_HAPROXY "/usr/sbin/haproxy -db -V -f ${OCTAVIA_CONF_DIR}/haproxy.cfg"
    fi

    if [[ "$OCTAVIA_USE_MOD_WSGI" == "True" ]]; then
        _start_octavia_apache_wsgi
    else
        run_process $OCTAVIA_API  "$OCTAVIA_API_BINARY $OCTAVIA_API_ARGS"
    fi

    run_process $OCTAVIA_CONSUMER  "$OCTAVIA_CONSUMER_BINARY $OCTAVIA_CONSUMER_ARGS"
    run_process $OCTAVIA_HOUSEKEEPER  "$OCTAVIA_HOUSEKEEPER_BINARY $OCTAVIA_HOUSEKEEPER_ARGS"
    run_process $OCTAVIA_HEALTHMANAGER  "$OCTAVIA_HEALTHMANAGER_BINARY $OCTAVIA_HEALTHMANAGER_ARGS"
}

function octavia_stop {
    # octavia-specific stop actions
    if [[ "$OCTAVIA_USE_MOD_WSGI" == "True" ]]; then
        _stop_octavia_apache_wsgi
    else
        stop_process $OCTAVIA_API
    fi
    stop_process $OCTAVIA_CONSUMER
    stop_process $OCTAVIA_HOUSEKEEPER
    stop_process $OCTAVIA_HEALTHMANAGER

    # Kill dhclient process started for o-hm0 interface
    pids=$(ps aux | awk '/[o]-hm0/ { print $2 }')
    [ ! -z "$pids" ] && sudo kill $pids
    if function_exists octavia_delete_network_interface_device ; then
        octavia_delete_network_interface_device o-hm0
    elif [[ $NEUTRON_AGENT == "openvswitch" || $Q_AGENT == "openvswitch" ]]; then
        :  # Do nothing
    elif [[ $NEUTRON_AGENT == "linuxbridge" || $Q_AGENT == "linuxbridge" ]]; then
        if ip link show o-hm0 ; then
            sudo ip link del o-hm0
        fi
    else
        die "Unknown network controller. Please define octavia_delete_network_interface_device"
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
    if [[ "$OCTAVIA_USE_MOD_WSGI" == "True" ]]; then
        _cleanup_octavia_apache_wsgi
    fi

    sudo rm -rf $NOVA_STATE_PATH $NOVA_AUTH_CACHE_DIR
}

function add_load-balancer_roles {
    openstack role create load-balancer_observer
    openstack role create load-balancer_global_observer
    openstack role create load-balancer_member
    openstack role create load-balancer_admin
    openstack role create load-balancer_quota_admin
    openstack role add --user demo --project demo load-balancer_member
}

function octavia_init {
   if [ $OCTAVIA_NODE != 'main' ] && [ $OCTAVIA_NODE != 'standalone' ]  && [ $OCTAVIA_NODE != 'api' ]; then
       # without the other services enabled apparently we don't have
       # credentials at this point
       TOP_DIR=$(cd $(dirname "$0") && pwd)
       source ${TOP_DIR}/openrc admin admin
   fi

   if [ $OCTAVIA_NODE == 'main' ] || [ $OCTAVIA_NODE == 'standalone' ] ; then
       # things that should only happen on the ha main node / or once
       if ! openstack keypair show ${OCTAVIA_AMP_SSH_KEY_NAME} ; then
           openstack keypair create --public-key ${OCTAVIA_AMP_SSH_KEY_PATH}.pub ${OCTAVIA_AMP_SSH_KEY_NAME}
       fi

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
       OCTAVIA_AMP_NETWORK_ID=$(openstack network show lb-mgmt-net -f value -c id)
       iniset $OCTAVIA_CONF controller_worker amp_boot_network_list ${OCTAVIA_AMP_NETWORK_ID}

       create_octavia_accounts

       # Adds service and endpoint
       if is_service_enabled tempest; then
           configure_octavia_tempest ${OCTAVIA_AMP_NETWORK_ID}
       fi

       add_load-balancer_roles
   elif [ $OCTAVIA_NODE == 'api' ] ; then
       create_octavia_accounts

       # Adds service and endpoint
       if is_service_enabled tempest; then
           configure_octavia_tempest ${OCTAVIA_AMP_NETWORK_ID}
       fi

       add_load-balancer_roles
   fi

   if [ $OCTAVIA_NODE != 'api' ] ; then
       create_mgmt_network_interface
       create_amphora_flavor
       configure_lb_mgmt_sec_grp
   fi

   if ! [ "$DISABLE_AMP_IMAGE_BUILD" == 'True' ]; then
       set_octavia_worker_image_owner_id
   fi
}

# check for service enabled
if is_service_enabled $OCTAVIA; then
    if [ $OCTAVIA_NODE == 'main' ] || [ $OCTAVIA_NODE == 'standalone' ] ; then # main-ha node stuff only
        if ! is_service_enabled $NEUTRON_ANY; then
            die "The neutron-api/q-svc service must be enabled to use $OCTAVIA"
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
        octaviaclient_install

    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        # Configure after the other layer 1 and 2 services have been configured
        # TODO: need to make sure this runs after LBaaS V2 configuration
        echo_summary "Configuring octavia"
        octavia_configure

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize and start the octavia service
        echo_summary "Initializing Octavia"
        octavia_init

        echo_summary "Starting Octavia"
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
