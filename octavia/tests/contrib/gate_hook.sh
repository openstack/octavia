#!/bin/bash

set -ex

GATE_DEST=$BASE/new

_DEVSTACK_LOCAL_CONFIG_TAIL=

# Inject config from hook
function load_conf_hook {
    local hook="$1"
    local GATE_HOOKS=$GATE_DEST/octavia/octavia/tests/contrib/hooks

    _DEVSTACK_LOCAL_CONFIG_TAIL+=$'\n'"$(cat $GATE_HOOKS/$hook)"
}

# Work around a devstack issue:https://review.openstack.org/#/c/435106
export DEVSTACK_LOCAL_CONFIG+=$'\n'"DEFAULT_IMAGE_NAME=cirros-0.3.5-x86_64-disk"$'\n'

export DEVSTACK_LOCAL_CONFIG+=$'\n'"enable_plugin barbican https://git.openstack.org/openstack/barbican"$'\n'

# Allow testing against diskimage-builder changes with depends-on
export DEVSTACK_LOCAL_CONFIG+=$'\n'"LIBS_FROM_GIT+=,diskimage-builder"$'\n'

# Sort out our gate args
. $(dirname "$0")/decode_args.sh

# Note: The check for OVH instances is temporary until they
# resolve the KVM failures as logged here:
# https://bugzilla.kernel.org/show_bug.cgi?id=192521
# However, this may be resolved at OVH before the kernel bug is resolved.
if $(egrep --quiet '(vmx|svm)' /proc/cpuinfo) && [[ ! $(hostname) =~ "ovh" ]]; then
    export DEVSTACK_GATE_LIBVIRT_TYPE=kvm
fi

function _setup_octavia_multinode {

    PRIMARY_NODE_IP=$(cat /etc/nodepool/primary_node_private)
    SUBNODE_IP=$(head -n1 /etc/nodepool/sub_nodes_private)

    # OCTAVIA_CONTROLLER_IP_PORT_LIST are the ips inside the
    # lb-mgmt network that the amphoras reach via heartbeats
    COMMON_MULTINODE_CONFIG="
OCTAVIA_USE_PREGENERATED_CERTS=True
OCTAVIA_USE_PREGENERATED_SSH_KEY=True
OCTAVIA_CONTROLLER_IP_PORT_LIST=192.168.0.3:5555,192.168.0.4:5555

# Embedded fix for devstack bug/1629133 , this line can be removed once
# that bug is fixed
SUBNETPOOL_PREFIX_V4=10.0.0.0/16"$'\n'

    export DEVSTACK_LOCAL_CONFIG+="$COMMON_MULTINODE_CONFIG
OCTAVIA_NODE=main
OCTAVIA_NODES=main:$PRIMARY_NODE_IP,second:$SUBNODE_IP
enable_service o-api-ha
OCTAVIA_MGMT_PORT_IP=192.168.0.3"$'\n'

    export DEVSTACK_SUBNODE_CONFIG+="$COMMON_MULTINODE_CONFIG
OCTAVIA_NODE=second
enable_plugin octavia https://git.openstack.org/openstack/octavia
OCTAVIA_MGMT_PORT_IP=192.168.0.4"$'\n'
}

function _setup_octavia {
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"OCTAVIA_DIB_TRACING=True"$'\n'
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"enable_plugin octavia https://git.openstack.org/openstack/octavia"$'\n'
    # Use infra's cached version of the file
    if [ -f /opt/stack/new/devstack/files/get-pip.py ]; then
            export DEVSTACK_LOCAL_CONFIG+=$'\n'"DIB_REPOLOCATION_pip_and_virtualenv=file:///opt/stack/new/devstack/files/get-pip.py"$'\n'
    fi
    if [ "$testenv" != "apiv1" ]; then
        ENABLED_SERVICES+="octavia,o-cw,o-hk,o-hm,o-api,"
        if [ "$DEVSTACK_GATE_TOPOLOGY" == "multinode" ]; then
            _setup_octavia_multinode
        fi
    fi
    if [ "$testenv" = "apiv1" ]; then
        load_conf_hook apiv1
    fi

    if [ "$testenv" = "scenario" ]; then
        load_conf_hook scenario
    fi
}

# Make sure lbaasv2 is listed as enabled for tempest
load_conf_hook api_extensions

case "$testtype" in

    "dsvm-functional")
        PROJECT_NAME=octavia
        OCTAVIA_PATH=$GATE_DEST/$PROJECT_NAME
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
            export DEVSTACK_LOCAL_CONFIG+=$'\n'"DISABLE_AMP_IMAGE_BUILD=True"$'\n'
            # Not needed for API tests
            ENABLED_SERVICES+="-horizon,-ceilometer-acentral,-ceilometer-acompute,"
            ENABLED_SERVICES+="-ceilometer-alarm-evaluator,-ceilometer-alarm-notifier,"
            ENABLED_SERVICES+="-ceilometer-anotification,-ceilometer-api,"
            ENABLED_SERVICES+="-ceilometer-collector,"
        fi

        if [ "$lbaasdriver" = "namespace" ]; then
            export DEVSTACK_LOCAL_CONFIG+=$'\n'"NEUTRON_LBAAS_SERVICE_PROVIDERV2=LOADBALANCERV2:Haproxy:neutron_lbaas.drivers.haproxy.plugin_driver.HaproxyOnHostPluginDriver:default"$'\n'
        fi

        if [ "$lbaasdriver" = "octavia" ]; then
            _setup_octavia
        fi

        export ENABLED_SERVICES
        export DEVSTACK_LOCAL_CONFIG+=$'\n'"$_DEVSTACK_LOCAL_CONFIG_TAIL"
        "$GATE_DEST"/devstack-gate/devstack-vm-gate.sh
        ;;

    *)
        echo "Unrecognized test type $testtype".
        exit 1
        ;;
esac
