#    Copyright 2014 Rackspace
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

import six
from wsme import types as wtypes

from octavia.common import exceptions
from octavia.common import validate

if six.PY3:
    unicode = str


class IPAddressType(wtypes.UserType):
    basetype = unicode
    name = 'ipaddress'

    @staticmethod
    def validate(value):
        """Validates whether value is an IPv4 or IPv6 address."""
        try:
            wtypes.IPv4AddressType.validate(value)
            return value
        except ValueError:
            try:
                wtypes.IPv6AddressType.validate(value)
                return value
            except ValueError:
                error = 'Value should be IPv4 or IPv6 format'
                raise ValueError(error)


class URLType(wtypes.UserType):
    basetype = unicode
    name = 'url'

    @staticmethod
    def validate(value):
        try:
            validate.url(value)
        except exceptions.InvalidURL:
            error = 'Value must be a valid URL string'
            raise ValueError(error)
        return value


class BaseType(wtypes.Base):
    @classmethod
    def from_data_model(cls, data_model, children=False):
        """Converts data_model to Octavia WSME type.

        :param data_model: data model to convert from
        :param children: convert child data models
        """
        if not hasattr(cls, '_type_to_model_map'):
            return cls(**data_model.to_dict())

        dm_to_type_map = {value: key
                          for key, value in cls._type_to_model_map.items()}
        type_dict = data_model.to_dict()
        new_dict = copy.deepcopy(type_dict)
        for key, value in type_dict.items():
            if isinstance(value, dict):
                for child_key, child_value in value.items():
                    if '.'.join([key, child_key]) in dm_to_type_map:
                        new_dict['_'.join([key, child_key])] = child_value
            else:
                if key in dm_to_type_map:
                    new_dict[dm_to_type_map[key]] = value
                    del new_dict[key]
        return cls(**new_dict)

    def to_dict(self, render_unsets=False):
        """Converts Octavia WSME type to dictionary.

        :param render_unsets: If True, will convert items that are WSME Unset
                              types to None. If False, does not add the item
        """
        ret_dict = {}
        for attr in dir(self):
            if attr.startswith('_'):
                continue
            value = getattr(self, attr, None)
            # TODO(blogan): Investigate wsme types handling the duality of
            # tenant_id and project_id in a clean way.  One way could be
            # wsme.rest.json.fromjson and using the @fromjson.when_object
            # decorator.
            if attr == 'tenant_id':
                ret_dict['project_id'] = value
                continue
            if value and callable(value):
                    continue
            if value and isinstance(value, BaseType):
                value = value.to_dict(render_unsets=render_unsets)
            if value and isinstance(value, list):
                value = [val.to_dict(render_unsets=render_unsets)
                         if isinstance(val, BaseType) else val
                         for val in value]
            if isinstance(value, wtypes.UnsetType):
                if render_unsets:
                    value = None
                else:
                    continue
            attr_name = attr
            if (hasattr(self, '_type_to_model_map')
                    and attr in self._type_to_model_map):
                renamed = self._type_to_model_map[attr]
                if '.' in renamed:
                    parent, child = renamed.split('.')
                    if parent not in ret_dict:
                        ret_dict[parent] = {}
                    ret_dict[parent][child] = value
                    continue
                attr_name = renamed
            ret_dict[attr_name] = value
        return ret_dict
