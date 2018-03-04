#!/bin/bash

set -o errexit

source $GRENADE_DIR/grenaderc
source $GRENADE_DIR/functions

# We need base DevStack functions for this
source $BASE_DEVSTACK_DIR/functions
source $BASE_DEVSTACK_DIR/stackrc # needed for status directory
source $BASE_DEVSTACK_DIR/lib/tls
source $BASE_DEVSTACK_DIR/lib/apache
source $BASE_DEVSTACK_DIR/lib/neutron

OCTAVIA_DEVSTACK_DIR=$(dirname $(dirname $0))
source $OCTAVIA_DEVSTACK_DIR/settings
source $OCTAVIA_DEVSTACK_DIR/plugin.sh

set -o xtrace

octavia_stop

# sanity check that service is actually down
ensure_services_stopped o-api o-cw o-hk o-hm
