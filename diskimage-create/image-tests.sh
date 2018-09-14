#!/bin/bash
#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

# This file is necessary because tox cannot handle pipes in commands

echo "Examining the Amphora image.  This will take some time."

if [ "$1" -a -f "$1" ]; then
    AMP_IMAGE_LOCATION=$1
elif [ "$1" ]; then
    AMP_IMAGE_LOCATION=$1/amphora-x64-haproxy.qcow2
else
    AMP_IMAGE_LOCATION=amphora-x64-haproxy.qcow2
fi

if ! [ -f $AMP_IMAGE_LOCATION ]; then
    echo "ERROR: Amphora image not found at: $AMP_IMAGE_LOCATION"
    exit 1
fi

# Check the image size (rounded in GB)
AMP_IMAGE_SIZE=$(virt-filesystems --long --csv --blkdevs -a $AMP_IMAGE_LOCATION | \
    awk -F ',' '$1 == "/dev/sda" { print int($3/1024^3 + 0.5)}')
if [ $AMP_IMAGE_SIZE != 2 ]; then
    echo "ERROR: Amphora image did not pass the default size test"
    echo "On Ubuntu you may need to run 'sudo chmod 0644 /boot/vmlinuz*' for libguestfs"
    exit 1
else
    echo "Amphora image size is correct"
fi

# Get image information
AMP_IMAGE_INFO=$(virt-inspector $AMP_IMAGE_LOCATION)
# Check the kernel
echo $AMP_IMAGE_INFO | \
    virt-inspector --xpath \
    '/operatingsystems/operatingsystem/distro' \
    | grep -q '<distro>ubuntu</distro>'
if [ $? != 0 ]; then
    echo "ERROR: Amphora image is using the wrong default distribution"
    exit 1
else
    echo "Amphora image is using the correct distribution"
fi

echo $AMP_IMAGE_INFO | \
    virt-inspector --xpath \
    '/operatingsystems/operatingsystem/arch' \
    | grep -q '<arch>x86_64</arch>'
if [ $? != 0 ]; then
    echo "ERROR: Amphora image is using the wrong default architecture"
    exit 1
else
    echo "Amphora image is using the correct architecture"
fi

echo $AMP_IMAGE_INFO | \
    virt-inspector --xpath \
    '/operatingsystems/operatingsystem/format' \
    | grep -q '<format>installed</format>'
if [ $? != 0 ]; then
    echo "ERROR: Amphora image is in the wrong format (should be installed)"
    exit 1
else
    echo "Amphora image is using the correct format"
fi

# Check for HAProxy
echo $AMP_IMAGE_INFO | \
    virt-inspector --xpath \
    '/operatingsystems/operatingsystem/applications/application/name[text()="haproxy"]' \
    | grep -q '<name>haproxy</name>'
if [ $? != 0 ]; then
    echo "ERROR: Amphora image is missing the haproxy package"
    exit 1
else
    echo "HAProxy package found in the Amphora image"
fi

# Check for KeepAlived
echo $AMP_IMAGE_INFO | \
    virt-inspector --xpath \
    '/operatingsystems/operatingsystem/applications/application/name[text()="keepalived"]' \
    | grep -q '<name>keepalived</name>'
if [ $? != 0 ]; then
    echo "ERROR: Amphora image is missing the keepalived package"
    exit 1
else
    echo "keepalived package found in the Amphora image"
fi
echo "Amphora image looks good."

exit 0
