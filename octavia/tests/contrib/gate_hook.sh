#!/bin/bash

set -ex

GATE_DEST=$BASE/new
DEVSTACK_PATH=$GATE_DEST/devstack

export DEVSTACK_LOCAL_CONFIG+="
enable_plugin barbican https://git.openstack.org/openstack/barbican
"

# Sort out our gate args
. $(dirname "$0")/decode_args.sh

if egrep --quiet '(vmx|svm)' /proc/cpuinfo; then
    export DEVSTACK_GATE_LIBVIRT_TYPE=kvm
fi


function _setup_octavia {
    export DEVSTACK_LOCAL_CONFIG+="
        enable_plugin octavia https://git.openstack.org/openstack/octavia
        "
    if [ "$testenv" != "apiv1" ]; then
        ENABLED_SERVICES+="octavia,o-cw,o-hk,o-hm,o-api,"
    fi
    if [ "$testenv" = "apiv1" ]; then
       cat > "$DEVSTACK_PATH/local.conf" <<EOF
[[post-config|/etc/octavia/octavia.conf]]
[DEFAULT]
debug = True

[controller_worker]
amphora_driver = amphora_noop_driver
compute_driver = compute_noop_driver
network_driver = network_noop_driver

EOF

    fi

    if [ "$testenv" = "scenario" ]; then
       cat > "$DEVSTACK_PATH/local.conf" <<EOF
[[post-config|/etc/octavia/octavia.conf]]
[DEFAULT]
debug = True

EOF

    fi
}


case "$testtype" in

    "dsvm-functional")
        PROJECT_NAME=octavia
        OCTAVIA_PATH=$GATE_DEST/$PROJECT_NAME
        DEVSTACK_PATH=$GATE_DEST/devstack
        IS_GATE=True
        USE_CONSTRAINT_ENV=False
        export LOG_COLOR=False
        source "$OCTAVIA"/tools/configure_for_lbaas_func_testing.sh

        # Make the workspace owned by the stack user
        sudo chown -R "$STACK_USER":"$STACK_USER" "$BASE"

        configure_host_for_lbaas_func_testing
        ;;

    "tempest")
        # These are not needed with either v1 or v2
        ENABLED_SERVICES+="-c-api,-c-bak,-c-sch,-c-vol,-cinder,"
        ENABLED_SERVICES+="-s-account,-s-container,-s-object,-s-proxy,"

        if [ "$testenv" != "scenario" ]; then
            export DEVSTACK_LOCAL_CONFIG+="
        DISABLE_AMP_IMAGE_BUILD=True
        "
            # Not needed for API tests
            ENABLED_SERVICES+="-horizon,-ceilometer-acentral,-ceilometer-acompute,"
            ENABLED_SERVICES+="-ceilometer-alarm-evaluator,-ceilometer-alarm-notifier,"
            ENABLED_SERVICES+="-ceilometer-anotification,-ceilometer-api,"
            ENABLED_SERVICES+="-ceilometer-collector,"
        fi

        if [ "$lbaasdriver" = "namespace" ]; then
            export DEVSTACK_LOCAL_CONFIG+="
        NEUTRON_LBAAS_SERVICE_PROVIDERV2=LOADBALANCERV2:Haproxy:neutron_lbaas.drivers.haproxy.plugin_driver.HaproxyOnHostPluginDriver:default
    "
        fi

        if [ "$lbaasdriver" = "octavia" ]; then
            _setup_octavia
        fi

        export ENABLED_SERVICES
        "$GATE_DEST"/devstack-gate/devstack-vm-gate.sh
        ;;

    *)
        echo "Unrecognized test type $testtype".
        exit 1
        ;;
esac
