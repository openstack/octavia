# Copyright 2018 Rackspace US Inc.  All rights reserved.
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
# Note: This is used to generate the amphora driver "supported flavor
#       metadata" dictionary. Each property should include a description
#       for the user to understand what this flavor setting does.
#
# Where possible, the property name should match the configuration file name
# for the setting. The configuration file setting is the default when a
# setting is not defined in a flavor profile.

SUPPORTED_FLAVOR_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Octavia Amphora Driver Flavor Metadata Schema",
    "description": "This schema is used to validate new flavor profiles "
                   "submitted for use in an amphora driver flavor profile.",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        consts.LOADBALANCER_TOPOLOGY: {
            "type": "string",
            "description": "The load balancer topology. One of: "
                           "SINGLE - One amphora per load balancer. "
                           "ACTIVE_STANDBY - Two amphora per load balancer.",
            "enum": list(consts.SUPPORTED_LB_TOPOLOGIES)
        },
        consts.COMPUTE_FLAVOR: {
            "type": "string",
            "description": "The compute driver flavor ID."
        }
    }
}
