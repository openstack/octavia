#!/bin/bash

set -xe

TEMPEST_CONFIG_DIR="$BASE/new/tempest/etc"
SCRIPTS_DIR="/usr/os-testr-env/bin"
OCTAVIA_DIR="$BASE/new/octavia"

# Sort out our gate args
. $(dirname "$0")/decode_args.sh

if [ "$testenv" = "apiv1" ]; then
    case "$lbaasenv" in
        minimal)
            # Temporarily just do the happy path
            test_subset="octavia.tests.tempest.v2.api.test_load_balancers_non_admin.LoadBalancersTestJSON.test_create_load_balancer(?!_) "
            test_subset+="octavia.tests.tempest.v2.api.test_load_balancers_non_admin.LoadBalancersTestJSON.test_get_load_balancer_stats(?!_) "
            test_subset+="octavia.tests.tempest.v2.api.test_load_balancers_non_admin.LoadBalancersTestJSON.test_get_load_balancer_status_tree(?!_) "
            test_subset+="octavia.tests.tempest.v2.api.test_listeners_non_admin.ListenersTestJSON.test_create_listener(?!_) "
            test_subset+="octavia.tests.tempest.v2.api.test_pools_non_admin.TestPools.test_create_pool(?!_) "
            test_subset+="octavia.tests.tempest.v2.api.test_members_non_admin.MemberTestJSON.test_add_member(?!_) "
            test_subset+="octavia.tests.tempest.v2.api.test_health_monitors_non_admin.TestHealthMonitors.test_create_health_monitor(?!_)"
            ;;
        healthmonitor)
            test_subset="health_monitor"
            ;;
        listener)
            test_subset="listeners"
            ;;
        loadbalancer)
            test_subset="load_balancers"
            ;;
        member)
            test_subset="members"
            ;;
        pool)
            test_subset="pools"
            ;;
        scenario)
            testenv="scenario"
            ;;
    esac
fi

function generate_testr_results {
    # Give job user rights to access tox logs
    sudo -H -u "$owner" chmod o+rw .
    if [ -d ".stestr" ] ; then
        sudo -H -u "$owner" chmod o+rw -R .stestr
        if [ -f ".stestr/0" ] ; then
            stestr last --subunit > ./testrepository.subunit
            $SCRIPTS_DIR/subunit2html ./testrepository.subunit testr_results.html
            gzip -9 ./testrepository.subunit
            gzip -9 ./testr_results.html
            sudo mv ./*.gz /opt/stack/logs/
        fi
    fi
}

case $testtype in
    "dsvm-functional")
        owner=stack
        sudo_env=
        ;;
    "tempest")
        owner=tempest
        # Configure the api and scenario tests to use the tempest.conf set by devstack
        sudo_env="TEMPEST_CONFIG_DIR=$TEMPEST_CONFIG_DIR"
        ;;
esac

# Set owner permissions according to job's requirements.
cd "$OCTAVIA_DIR"
sudo chown -R $owner:stack "$OCTAVIA_DIR"

# Run tests
echo "Running Octavia $testenv test suite"
set +e

sudo -H -u $owner $sudo_env tox -e $testenv -- $test_subset

testr_exit_code=$?
set -e

# Collect and parse results
generate_testr_results
exit $testr_exit_code
