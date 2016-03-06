#!/bin/bash

set -ex

GATE_DEST=$BASE/new
DEVSTACK_PATH=$GATE_DEST/devstack

export DEVSTACK_LOCAL_CONFIG+="
enable_plugin neutron-lbaas https://git.openstack.org/openstack/neutron-lbaas
enable_plugin barbican https://git.openstack.org/openstack/barbican
enable_plugin octavia https://git.openstack.org/openstack/octavia"

# Below projects are required for setting up environment
case $PROJECTS in
    *openstack/barbican* )
        ;;
    * )
        export PROJECTS="openstack/barbican $PROJECTS"
        export PROJECTS="openstack/python-barbicanclient $PROJECTS"
        ;;
esac

# These are not needed for api and scenario tests
ENABLED_SERVICES+="-c-api,-c-bak,-c-sch,-c-vol,-cinder"
ENABLED_SERVICES+=",-s-account,-s-container,-s-object,-s-proxy"

# Disable lbaasv1 and enable lbaasv2
ENABLED_SERVICES+="q-lbaasv2,-q-lbaas,octavia,o-cw,o-hk,o-hm,o-api"

export ENABLED_SERVICES

#REGEX is required for running octavia specific tempest tests
export DEVSTACK_GATE_TEMPEST_REGEX="^octavia\."

$GATE_DEST/devstack-gate/devstack-vm-gate.sh