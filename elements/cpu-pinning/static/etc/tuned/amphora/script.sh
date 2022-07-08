#!/bin/sh

# Comment the line in ...tuned/functions that fails on the amp:
# DISKS_SYS="$(command ls -d1 /sys/block/{sd,cciss,dm-,vd,dasd,xvd}* 2>/dev/null)"
sed -i 's/^DISKS_SYS=/#&/' /usr/lib/tuned/functions
. /usr/lib/tuned/functions

start() {
    setup_kvm_mod_low_latency
    disable_ksm

    return "$?"
}

stop() {
    if [ "$1" = "full_rollback" ]; then
        teardown_kvm_mod_low_latency
        enable_ksm
    fi
    return "$?"
}

process $@
