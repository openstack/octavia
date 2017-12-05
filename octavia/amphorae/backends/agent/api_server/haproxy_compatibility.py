# Copyright 2017 Rackspace, US Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging
import re
import subprocess

LOG = logging.getLogger(__name__)


def get_haproxy_versions():
    """Get major and minor version number from haproxy

    :returns major_version: The major version digit
    :returns minor_version: The minor version digit
    """
    cmd = "haproxy -v"

    version = subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)

    version_re = re.search('.*version (.+?)\.(.+?)\..*',
                           version.decode('utf-8'))

    major_version = int(version_re.group(1))
    minor_version = int(version_re.group(2))

    return major_version, minor_version


def process_cfg_for_version_compat(haproxy_cfg):

    major, minor = get_haproxy_versions()

    # Versions less than 1.6 do not support external health checks
    # Removed those configuration times
    if major < 2 and minor < 6:
        LOG.warning("Found %(major)s.%(minor)s version of haproxy. "
                    "Disabling external checks. Health monitor of type "
                    "PING will revert to TCP.",
                    {'major': major, 'minor': minor})
        haproxy_cfg = re.sub(r" * ?.*external-check ?.*\s", "", haproxy_cfg)

    return haproxy_cfg
