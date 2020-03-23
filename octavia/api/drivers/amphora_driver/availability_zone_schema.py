# Copyright 2018 Rackspace US Inc.  All rights reserved.
# Copyright 2019 Verizon Media
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from octavia.common import constants as consts

# This is a JSON schema validation dictionary
# https://json-schema.org/latest/json-schema-validation.html
#
# Note: This is used to generate the amphora driver "supported availability
#       zone metadata" dictionary. Each property should include a description
#       for the user to understand what this availability zone setting does.
#
# Where possible, the property name should match the configuration file name
# for the setting. The configuration file setting is the default when a
# setting is not defined in an availability zone profile.

SUPPORTED_AVAILABILITY_ZONE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Octavia Amphora Driver Availability Zone Metadata Schema",
    "description": "This schema is used to validate new availability zone "
                   "profiles submitted for use in an amphora driver "
                   "availability zone.",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        consts.COMPUTE_ZONE: {
            "type": "string",
            "description": "The compute availability zone."
        },
        consts.MANAGEMENT_NETWORK: {
            "type": "string",
            "description": "The management network ID for the amphora."
        },
        consts.VALID_VIP_NETWORKS: {
            "type": "array",
            "description": "List of network IDs that are allowed for VIP use. "
                           "This overrides/replaces the list of allowed "
                           "networks configured in `octavia.conf`."
        }
    }
}
