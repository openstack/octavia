# Copyright 2024 Red Hat
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
#
from taskflow import task

from octavia.common import constants


class AmphoraToAmphoraeWithVRRPIP(task.Task):
    """A shim class to convert a single Amphora instance to a list."""

    def execute(self, amphora: dict, base_port: dict):
        # The VRRP_IP has not been stamped on the Amphora at this point in the
        # flow, so inject it from our port create call in a previous task.
        amphora[constants.VRRP_IP] = (
            base_port[constants.FIXED_IPS][0][constants.IP_ADDRESS])
        return [amphora]
