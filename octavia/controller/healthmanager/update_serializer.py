# Copyright 2014 Rackspace
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

import copy


class InfoContainer(object):
    @staticmethod
    def from_dict(dict_obj):
        return InfoContainer(dict_obj['info_type'],
                             dict_obj['info_id'],
                             dict_obj['info_payload'])

    def __init__(self, info_type, info_id, info_payload):
        self.info_type = copy.copy(info_type)
        self.info_id = copy.copy(info_id)
        self.info_payload = copy.deepcopy(info_payload)

    def to_dict(self):
        return {'info_type': self.info_type,
                'info_id': self.info_id,
                'info_payload': self.info_payload}

    def __eq__(self, other):
        if not isinstance(other, InfoContainer):
            return False
        if self.info_type != other.info_type:
            return False
        if self.info_id != other.info_id:
            return False
        if self.info_payload != other.info_payload:
            return False
        return True

    def __ne__(self, other):
        return not self == other
