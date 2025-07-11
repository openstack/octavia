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

set -e

usage() {
    echo
    echo "Usage: $(basename "$0")"
    echo "            [-a **amd64** | armhf | aarch64 | ppc64le]"
    echo "            [-b **haproxy** ]"
    echo "            [-c **~/.cache/image-create** | <cache directory> ]"
    echo "            [-d **noble**/**9-stream**/**9** | <other release id> ]"
    echo "            [-e]"
    echo "            [-f]"
    echo "            [-g **repository branch** | stable/train | stable/stein | ... ]"
    echo "            [-h]"
    echo "            [-i **ubuntu-minimal** | fedora | centos-minimal | rhel | rocky ]"
    echo "            [-k <kernel package name> ]"
    echo "            [-l <log file> ]"
    echo "            [-m]"
    echo "            [-n]"
    echo "            [-o **amphora-x64-haproxy.qcow2** | <filename> ]"
    echo "            [-p]"
    echo "            [-r <root password> ]"
    echo "            [-s **2** | <size in GB> ]"
    echo "            [-t **qcow2** | tar | vhd | raw ]"
    echo "            [-v]"
    echo "            [-w <working directory> ]"
    echo "            [-x]"
    echo
    echo "        '-a' is the architecture type for the image (default: amd64)"
    echo "        '-b' is the backend type (default: haproxy)"
    echo "        '-c' is the path to the cache directory (default: ~/.cache/image-create)"
    echo "        '-d' distribution release id (default on ubuntu: noble)"
    echo "        '-e' enable complete mandatory access control systems when available (default: permissive)"
    echo "        '-f' disable tmpfs for build"
    echo "        '-g' build the image for a specific OpenStack Git branch (default: current repository branch)"
    echo "        '-h' display this help message"
    echo "        '-i' is the base OS (default: ubuntu-minimal)"
    echo "        '-k' is the kernel meta package name, currently only for ubuntu-minimal base OS (default: linux-image-virtual)"
    echo "        '-l' is output logfile (default: none)"
    echo "        '-m' enable vCPU pinning optimizations (default: disabled)"
    echo "        '-n' disable sshd (default: enabled)"
    echo "        '-o' is the output image file name"
    echo "        '-p' install amphora-agent from distribution packages (default: disabled)"
    echo "        '-r' enable the root account in the generated image (default: disabled)"
    echo "        '-s' is the image size to produce in gigabytes (default: 2)"
    echo "        '-t' is the image type (default: qcow2)"
    echo "        '-v' display the script version"
    echo "        '-w' working directory for image building (default: .)"
    echo "        '-x' enable tracing for diskimage-builder"
    echo "        '-y' enable FIPS 140-2 mode in the amphora image"
    echo
    exit 1
}

version() {
    echo "Amphora disk image creation script version:"\
        "$(cat "${OCTAVIA_REPO_PATH}/diskimage-create/version.txt")"
    exit 1
}

find_system_elements() {
    # List of possible system installation directories
    local system_prefixes="/usr/share /usr/local/share"
    for prefix in $system_prefixes; do
        if [ -d "$prefix/$1" ]; then
            echo "$prefix/$1"
            return
        fi
    done
}

# Figure out where our directory is located
if [ -z "$OCTAVIA_REPO_PATH" ]; then
    AMP_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
    OCTAVIA_REPO_PATH=${OCTAVIA_REPO_PATH:-${AMP_DIR%/*}}
fi
dib_enable_tracing=

AMP_LOGFILE=""

while getopts "a:b:c:d:efg:hi:k:l:mno:pt:r:s:vw:xy" opt; do
    case $opt in
        a)
            AMP_ARCH=$OPTARG
            if [ "$AMP_ARCH" != "amd64" ] && \
                [ "$AMP_ARCH" != "ppc64le" ] && \
                [ "$AMP_ARCH" != "aarch64" ] && \
                [ "$AMP_ARCH" != "armhf" ]; then
                echo "Error: Unsupported architecture $AMP_ARCH specified"
                exit 3
            fi
        ;;
        b)
            if [ "$OPTARG" == "haproxy" ]; then
                AMP_BACKEND=$OPTARG-octavia
            else
                echo "Error: Unsupported backend type $AMP_BACKEND specified"
                exit 3
            fi
        ;;
        c)
            AMP_CACHEDIR=$OPTARG
        ;;
        d)
            AMP_DIB_RELEASE=$OPTARG
        ;;
        e)
            AMP_ENABLE_FULL_MAC_SECURITY=1
        ;;
        f)
            AMP_DISABLE_TMP_FS='--no-tmpfs'
        ;;
        g)
            if [ -z "$DIB_REPOREF_amphora_agent" ]; then
                echo "Building image with amphora agent from $OPTARG."
                export DIB_REPOREF_amphora_agent=$OPTARG
            else
                echo "Environment variable DIB_REPOREF_amphora_agent is set. Building the image with amphora agent $DIB_REPOREF_amphora_agent."
            fi
            if [ -z "$DIB_REPOLOCATION_upper_constraints" ]; then
                echo "Using upper constraints from https://opendev.org/openstack/requirements/raw/branch/$OPTARG/upper-constraints.txt."
                export DIB_REPOLOCATION_upper_constraints="https://opendev.org/openstack/requirements/raw/branch/$OPTARG/upper-constraints.txt"
            else
                echo "Environment variable DIB_REPOLOCATION_upper_constraints is set. Building the image with upper-constraints.txt from $DIB_REPOLOCATION_upper_constraints."
            fi
        ;;
        h)
            usage
        ;;
        i)
            AMP_BASEOS=$OPTARG
            if [ "$AMP_BASEOS" != "ubuntu" ] && \
                [ "$AMP_BASEOS" != "ubuntu-minimal" ] && \
                [ "$AMP_BASEOS" != "fedora" ] && \
                [ "$AMP_BASEOS" != "centos" ] && \
                [ "$AMP_BASEOS" != "centos-minimal" ] && \
                [ "$AMP_BASEOS" != "rocky" ] && \
                [ "$AMP_BASEOS" != "rhel" ]; then
                echo "Error: Unsupported base OS $AMP_BASEOS specified"
                exit 3
            fi
            if [ "$AMP_BASEOS" == "ubuntu" ]; then
                AMP_BASEOS="ubuntu-minimal"
            fi
            if [ "$AMP_BASEOS" == "centos" ]; then
                AMP_BASEOS="centos-minimal"
            fi
            if [ "$AMP_BASEOS" == "rocky" ]; then
                AMP_BASEOS="rocky-container"
            fi
        ;;
        k)
            AMP_KERNEL=$OPTARG
        ;;
        l)
            AMP_LOGFILE="--logfile=$OPTARG"
        ;;
        m)
            AMP_ENABLE_CPUPINNING=1
        ;;
        n)
            AMP_DISABLE_SSHD=1
        ;;
        o)
            AMP_OUTPUTFILENAME=$(readlink -f "$OPTARG")
            amp_dir=$(dirname "$AMP_OUTPUTFILENAME")
            if [ ! -d "$amp_dir" ]; then
                echo "Error: Directory $amp_dir does not exist"
                exit 3
            fi
        ;;
        p)
            AMP_PACKAGE_INSTALL=1
        ;;
        r)
            AMP_ROOTPW=$OPTARG
        ;;
        s)
            AMP_IMAGESIZE=$OPTARG
            if ! [[ $AMP_IMAGESIZE =~ ^[0-9]+$ ]]; then
                echo "Error: Invalid image size $AMP_IMAGESIZE specified"
                exit 3
            fi
        ;;
        t)
            AMP_IMAGETYPE=$OPTARG
            if [ "$AMP_IMAGETYPE" != "qcow2" ] && \
                [ "$AMP_IMAGETYPE" != "tar" ] && \
                [ "$AMP_IMAGETYPE" != "vhd" ] && \
                [ "$AMP_IMAGETYPE" != "raw" ]; then
                echo "Error: Unsupported image type $AMP_IMAGETYPE specified"
                exit 3
            fi
        ;;
        v)
            version
        ;;
        w)
            AMP_WORKING_DIR=$OPTARG
        ;;
        x)  dib_enable_tracing=1
        ;;
        y)  AMP_ENABLE_FIPS=1
        ;;
        *)
            usage
        ;;
    esac
done

shift $((OPTIND-1))
if [ "$1" ]; then
    usage
fi

# Set the Octavia Amphora defaults if they aren't already set
AMP_ARCH=${AMP_ARCH:-"amd64"}

AMP_BACKEND=${AMP_BACKEND:-"haproxy-octavia"}

AMP_CACHEDIR=${AMP_CACHEDIR:-"$HOME/.cache/image-create"}
# Make sure we have an absolute path for the cache location
mkdir -p "$AMP_CACHEDIR"
AMP_CACHEDIR="$( cd "$AMP_CACHEDIR" && pwd )"

AMP_BASEOS=${AMP_BASEOS:-"ubuntu-minimal"}

if [ "$AMP_BASEOS" = "ubuntu-minimal" ]; then
    export DIB_RELEASE=${AMP_DIB_RELEASE:-"noble"}
elif [ "${AMP_BASEOS}" = "rhel" ]; then
    export DIB_RELEASE=${AMP_DIB_RELEASE:-"9"}
elif [ "${AMP_BASEOS}" = "centos-minimal" ]; then
    export DIB_RELEASE=${AMP_DIB_RELEASE:-"9-stream"}
elif [ "${AMP_BASEOS}" = "fedora" ]; then
    export DIB_RELEASE=${AMP_DIB_RELEASE:-"28"}
elif [ "${AMP_BASEOS}" = "rocky-container" ]; then
    export DIB_RELEASE=${AMP_DIB_RELEASE:-"9"}
fi

AMP_OUTPUTFILENAME=${AMP_OUTPUTFILENAME:-"$PWD/amphora-x64-haproxy.qcow2"}

AMP_IMAGETYPE=${AMP_IMAGETYPE:-"qcow2"}

AMP_IMAGESIZE=${AMP_IMAGESIZE:-2}

if [ "$AMP_BASEOS" = "ubuntu-minimal" ]; then
    export DIB_UBUNTU_KERNEL=${AMP_KERNEL:-"linux-image-virtual"}
fi

AMP_ENABLE_CPUPINNING=${AMP_ENABLE_CPUPINNING:-0}

AMP_DISABLE_SSHD=${AMP_DISABLE_SSHD:-0}

AMP_PACKAGE_INSTALL=${AMP_PACKAGE_INSTALL:-0}

AMP_ENABLE_FULL_MAC_SECURITY=${AMP_ENABLE_FULL_MAC_SECURITY:-0}

AMP_DISABLE_TMP_FS=${AMP_DISABLE_TMP_FS:-""}

AMP_ENABLE_FIPS=${AMP_ENABLE_FIPS:-0}

if [[ "$AMP_BASEOS" =~ ^(rhel|fedora)$ ]] && [[ "$AMP_IMAGESIZE" -lt 3 ]]; then
    echo "RHEL/Fedora based amphora requires an image size of at least 3GB"
    exit 1
fi

OCTAVIA_ELEMENTS_PATH=$OCTAVIA_REPO_PATH/elements

if ! [ -d "$OCTAVIA_ELEMENTS_PATH" ]; then
    SYSTEM_OCTAVIA_ELEMENTS_PATH=$(find_system_elements octavia-image-elements)
    if [ -z "${SYSTEM_OCTAVIA_ELEMENTS_PATH}" ]; then
        echo "ERROR: Octavia elements directory not found at: $OCTAVIA_ELEMENTS_PATH Exiting."
        exit 1
    fi
    OCTAVIA_ELEMENTS_PATH=${SYSTEM_OCTAVIA_ELEMENTS_PATH}
fi

DIB_REPO_PATH=${DIB_REPO_PATH:-${OCTAVIA_REPO_PATH%/*}/diskimage-builder}

if [ -d "$DIB_REPO_PATH" ]; then
    export PATH=$PATH:$DIB_REPO_PATH/bin
else
    if ! disk-image-create --version > /dev/null 2>&1; then
        echo "ERROR: diskimage-builder repo directory not found at: $DIB_REPO_PATH or in path. Exiting."
        exit 1
    fi
fi

# For system-wide installs, DIB will automatically find the elements, so we only check local path
if [ "$DIB_LOCAL_ELEMENTS_PATH" ]; then
    export ELEMENTS_PATH=$OCTAVIA_ELEMENTS_PATH:$DIB_LOCAL_ELEMENTS_PATH
else
    export ELEMENTS_PATH=$OCTAVIA_ELEMENTS_PATH
fi

# Make sure we have a value set for DIB_OCTAVIA_AMP_USE_NFTABLES
export DIB_OCTAVIA_AMP_USE_NFTABLES=${DIB_OCTAVIA_AMP_USE_NFTABLES:-True}

export CLOUD_INIT_DATASOURCES=${CLOUD_INIT_DATASOURCES:-"ConfigDrive"}

# Additional RHEL environment checks
if [ "${AMP_BASEOS}" = "rhel" ]; then
    if [ -z "${DIB_LOCAL_IMAGE}" ]; then
        echo "DIB_LOCAL_IMAGE variable must be set and point to a RHEL base cloud image. Exiting."
        echo "For more information, see the README file in ${DIB_ELEMENTS_PATH}/elements/rhel"
        exit 1
    fi
fi

# Find out what platform we are on
if [ -e /etc/os-release ]; then
    platform=$(grep '^NAME=' /etc/os-release | sed -e 's/\(NAME="\)\(.*\)\("\)/\2/g')
else
    platform=$(head -1 /etc/system-release | grep -e CentOS -e 'Red Hat Enterprise Linux' || :)
    if [ -z "$platform" ]; then
        echo -e "Unknown Host OS. Impossible to build images.\nAborting"
        exit 2
    fi
fi

if [[ "$AMP_ROOTPW" ]] && [[ "$platform" != 'Ubuntu' ]] && ! [[ "$platform" =~ "Debian" ]]; then
    if [ "$(getenforce)" == "Enforcing" ]; then
        echo "A root password cannot be enabled for images built on this platform while SELinux is enabled."
        exit 1
    fi
fi

if [ "$AMP_ROOTPW" ]; then
    echo "Warning: Using a root password in the image, NOT FOR PRODUCTION USAGE."
fi

# Make sure we have the required packages installed
if [[ "$platform" = 'Ubuntu' || "$platform" =~ 'Debian' ]]; then
    PKG_LIST="qemu-utils git kpartx debootstrap"
    for pkg in $PKG_LIST; do
        if ! dpkg --get-selections 2> /dev/null | grep -q "^${pkg}[[:space:]]*install$" >/dev/null; then
            echo "Required package $pkg is not installed.  Exiting."
            echo "Binary dependencies on this platform are: ${PKG_LIST}"
            exit 1
        fi
    done

    if [[ "$platform" = 'Ubuntu' ]]; then
        # Also check if we can build the BASEOS on this Ubuntu version
        UBUNTU_VERSION=$(lsb_release -r | awk '{print $2}')
        if [[ "$AMP_BASEOS" != "ubuntu-minimal" ]] && \
            [[ 1 -eq "$(echo "$UBUNTU_VERSION < 16.04" | bc)" ]]; then
                echo "Ubuntu minimum version 16.04 required to build $AMP_BASEOS."
                echo "Earlier versions don't support the extended attributes required."
                exit 1
        fi
    else
        # Check if we can build the BASEOS on this Debian version
        DEBIAN_VERSION=$(lsb_release -r | awk '{print $2}')
        # As minimal Ubuntu version is 14.04, for debian it is Debian 8 Jessie
        if [[ "$AMP_BASEOS" != "ubuntu-minimal" ]] && \
            [[ 1 -eq "$(echo "$DEBIAN_VERSION < 8" | bc)" ]]; then
                echo "Debian minimum version 8 required to build $AMP_BASEOS."
                echo "Earlier versions don't support the extended attributes required."
                exit 1
        fi
    fi
elif [[ $platform =~ "SUSE" ]]; then
    # OpenSUSE
    # use rpm -q to check for qemu-tools and git-core
    PKG_LIST="qemu-tools git-core"
    for pkg in $PKG_LIST; do
        if ! rpm -q "$pkg" &> /dev/null; then
            echo "Required package ${pkg/\*} is not installed.  Exiting."
            echo "Binary dependencies on this platform are: ${PKG_LIST}"
            exit 1
        fi
    done
elif [[ $platform =~ "Gentoo" ]]; then
    # Gentoo
    # Check /var/db for dev-vcs/git and app-emulation/[qemu|xen-tools] sys-fs/multipath-tools
    PKG_LIST="dev-vcs/git app-emulation/qemu|xen-tools sys-fs/multipath-tools"
    for pkg in $PKG_LIST; do
        if grep -qs '|' <<< "$pkg"; then
            c=$(cut -d / -f 1 <<<"$pkg")
            for p in $(cut -d / -f 2 <<<"$pkg" | tr "|" " "); do
                if [ -d /var/db/pkg/"$c"/"$p"-* ]; then
                    continue 2
                fi
            done
            echo "Required package ${pkg/\*} is not installed.  Exiting."
            echo "Binary dependencies on this platform are: ${PKG_LIST}"
            exit 1
        elif [ ! -d /var/db/pkg/"$pkg"-* ]; then
            echo "Required package ${pkg/\*} is not installed.  Exiting."
            echo "Binary dependencies on this platform are: ${PKG_LIST}"
            exit 1
        fi
    done
else
    # fedora/centos/rhel
    # Actual qemu-img name may be qemu-img, qemu-img-ev, qemu-img-rhev, ...
    # "dnf|yum install qemu-img" works for all, but search requires wildcard
    PKG_LIST="qemu-img* git"
    for pkg in $PKG_LIST; do
        if ! rpm -qa "$pkg" ; then
            echo "Required package ${pkg/\*} is not installed.  Exiting."
            echo "Binary dependencies on this platform are: ${PKG_LIST}"
            exit 1
        fi
    done
fi

if  [ "$AMP_WORKING_DIR" ]; then
    mkdir -p "$AMP_WORKING_DIR"
    TEMP=$(mktemp -d "$AMP_WORKING_DIR/diskimage-create.XXXXXX")
else
    TEMP=$(mktemp -d diskimage-create.XXXXXX)
fi
pushd "$TEMP" > /dev/null

# Setup the elements list

AMP_element_sequence=${AMP_element_sequence:-"base vm"}
if [ "${AMP_BASEOS}" = "rhel" ] && [ "${DIB_RELEASE}" = "8" ]; then
    export DIB_INSTALLTYPE_pip_and_virtualenv=package
fi
AMP_element_sequence="$AMP_element_sequence ${AMP_BASEOS}"

if [ "$AMP_PACKAGE_INSTALL" -eq 1 ]; then
    export DIB_INSTALLTYPE_amphora_agent=package
fi

# Add our backend element (haproxy, etc.)
AMP_element_sequence="$AMP_element_sequence $AMP_BACKEND"

if [ "$AMP_ROOTPW" ]; then
    AMP_element_sequence="$AMP_element_sequence root-passwd"
    export DIB_PASSWORD=$AMP_ROOTPW
fi

# Add the Amphora Agent and Pyroute elements
AMP_element_sequence="$AMP_element_sequence rebind-sshd"
AMP_element_sequence="$AMP_element_sequence no-resolvconf"
AMP_element_sequence="$AMP_element_sequence amphora-agent"
AMP_element_sequence="$AMP_element_sequence octavia-lib"
AMP_element_sequence="$AMP_element_sequence sos"
AMP_element_sequence="$AMP_element_sequence cloud-init-datasources"
AMP_element_sequence="$AMP_element_sequence remove-default-ints"

# SELinux systems
if [ "${AMP_BASEOS}" = "centos-minimal" ] || [ "${AMP_BASEOS}" = "fedora" ] || [ "${AMP_BASEOS}" = "rhel" ] || [ "${AMP_BASEOS}" = "rocky-container" ]; then
    if [ "$AMP_ENABLE_FULL_MAC_SECURITY" -ne 1 ]; then
        AMP_element_sequence="$AMP_element_sequence selinux-permissive"
    else
        # If SELinux is enforced, the amphora image requires the amphora-selinux policies
        AMP_element_sequence="$AMP_element_sequence amphora-selinux"
    fi
fi

# AppArmor systems
if [ "${AMP_BASEOS}" = "ubuntu-minimal" ] || [ "${AMP_BASEOS}" = "ubuntu" ]; then
    AMP_element_sequence="$AMP_element_sequence amphora-apparmor"
fi

# Disable the dnf makecache timer
if [ "${AMP_BASEOS}" = "centos-minimal" ] || [ "${AMP_BASEOS}" = "fedora" ] || [ "${AMP_BASEOS}" = "rhel" ] || [ "${AMP_BASEOS}" = "rocky-container" ]; then
    AMP_element_sequence="$AMP_element_sequence disable-makecache"
fi

if [ "${AMP_BASEOS}" = "centos-minimal" ]; then
    export DIB_YUM_MINIMAL_CREATE_INTERFACES=0
fi

# Add keepalived-octavia element
AMP_element_sequence="$AMP_element_sequence keepalived-octavia"
AMP_element_sequence="$AMP_element_sequence ipvsadmin"

# Add pip-cache element
AMP_element_sequence="$AMP_element_sequence pip-cache"

# Add certificate ramfs element
AMP_element_sequence="$AMP_element_sequence certs-ramfs"

# Add cpu-pinning element
if [ "$AMP_ENABLE_CPUPINNING" -eq 1 ]; then
    AMP_element_sequence="$AMP_element_sequence cpu-pinning"
fi

# Disable SSHD if requested
if [ "$AMP_DISABLE_SSHD" -eq 1 ]; then
    AMP_element_sequence="$AMP_element_sequence remove-sshd"
    export DIB_OCTAVIA_AMP_USE_SSH=${DIB_OCTAVIA_AMP_USE_SSH:-False}
else
    export DIB_OCTAVIA_AMP_USE_SSH=${DIB_OCTAVIA_AMP_USE_SSH:-True}
fi

# Enable FIPS if requested
if [ "$AMP_ENABLE_FIPS" -eq 1 ]; then
    AMP_element_sequence="$AMP_element_sequence amphora-fips"
fi

# Allow full elements override
if [ "$DIB_ELEMENTS" ]; then
    AMP_element_sequence="$DIB_ELEMENTS"
fi

if [ "$DIB_LOCAL_ELEMENTS" ]; then
    AMP_element_sequence="$AMP_element_sequence $DIB_LOCAL_ELEMENTS"
fi

# Set Grub timeout to 0 (no timeout) for fast boot times
export DIB_GRUB_TIMEOUT=${DIB_GRUB_TIMEOUT:-0}

# Build the image

export DIB_CLOUD_INIT_DATASOURCES=$CLOUD_INIT_DATASOURCES

dib_trace_arg=
if [ -n "$dib_enable_tracing" ]; then
    dib_trace_arg="-x"
fi

if [ "$USE_PYTHON3" = "False" ]; then
    export DIB_PYTHON_VERSION=2
fi

disk-image-create "$AMP_LOGFILE" "$dib_trace_arg" -a "$AMP_ARCH" -o "$AMP_OUTPUTFILENAME" -t \
"$AMP_IMAGETYPE" --image-size "$AMP_IMAGESIZE" --image-cache "$AMP_CACHEDIR" "$AMP_DISABLE_TMP_FS" \
"$AMP_element_sequence"

popd > /dev/null # out of $TEMP
rm -rf "$TEMP"

if [ -z "$DIB_REPOREF_amphora_agent" ]; then
    echo "Successfully built the amphora image using amphora-agent from the master branch."
else
    echo "Successfully built the amphora using the $DIB_REPOREF_amphora_agent amphora-agent."
fi
echo "Amphora image size: `stat -c "%n %s" $AMP_OUTPUTFILENAME`"
