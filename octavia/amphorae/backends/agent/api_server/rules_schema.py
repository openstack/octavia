# Copyright 2024 Red Hat, Inc. All rights reserved.
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
from octavia_lib.common import constants as lib_consts

from octavia.common import constants as consts

# This is a JSON schema validation dictionary
# https://json-schema.org/latest/json-schema-validation.html

SUPPORTED_RULES_SCHEMA = {
    '$schema': 'http://json-schema.org/draft-07/schema#',
    'title': 'Octavia Amphora NFTables Rules Schema',
    'description': 'This schema is used to validate an nftables rules JSON '
                   'document sent from a controller.',
    'type': 'array',
    'items': {
        'additionalProperties': False,
        'properties': {
            consts.PROTOCOL: {
                'type': 'string',
                'description': 'The protocol for the rule. One of: '
                               'TCP, UDP, VRRP, SCTP',
                'enum': list((lib_consts.PROTOCOL_SCTP,
                              lib_consts.PROTOCOL_TCP,
                              lib_consts.PROTOCOL_UDP,
                              consts.VRRP))
            },
            consts.CIDR: {
                'type': ['string', 'null'],
                'description': 'The allowed source CIDR.'
            },
            consts.PORT: {
                'type': 'number',
                'description': 'The protocol port number.',
                'minimum': 1,
                'maximum': 65535
            }
        },
        'required': [consts.PROTOCOL, consts.CIDR, consts.PORT]
    }
}
