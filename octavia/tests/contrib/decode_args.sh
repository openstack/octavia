#!/bin/bash

# This file is meant to be sourced by the other hooks

# Legacy values for $1, $2 and $3:
# $1 - dsvm-functional, tempest (testtype)
# $2 - lbaasv2, lbaasv1 (octaviaversion)
# $3 - scenario, minimal, api, healthmonitor, listener, loadbalancer, member, pool (octaviatest)

# Args being phased in:
# $1 - same
# $2 - same
# $3 - test-driver, with any missing -driver being "octavia"
#    scenario-octavia
#    minimal-octavia
#    api-namespace
#    api-{thirdparty}
#    healthmonitor-octavia
#    listener-octavia
#    loadbalancer-octavia
#    member-octavia
#    pool-octavia




testtype="$1"
octaviaversion="$2"
octaviatest="$3"

case $testtype in
    "dsvm-functional")
        testenv=$testtype
        ;;

    "tempest")
        lbaasenv=$(echo "$octaviatest" | perl -ne '/^(.*)-([^-]+)$/ && print "$1";')
        if [ -z "$lbaasenv" ]; then
            lbaasenv=$octaviatest
        fi
        lbaasdriver=$(echo "$octaviatest" | perl -ne '/^(.*)-([^-]+)$/ && print "$2";')
        if [ -z "$lbaasdriver" ]; then
            lbaasdriver='octavia'
        fi

        testenv=${octaviatest:-"apiv1"}

        if [ "$octaviaversion" = "v1" ]; then
            case "$lbaasenv" in
                "api"|"healthmonitor"|"listener"|"loadbalancer"|"member"|"minimal"|"pool")
                    testenv="apiv1"
                    ;;
                "scenario")
                    testenv="scenario"
                    ;;
                *)
                    echo "Unrecognized env $lbaasenv".
                    exit 1
                    ;;
            esac
        fi
        ;;
esac
