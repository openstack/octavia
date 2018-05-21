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

    def __init__(self, require_scheme=True):
        super(URLType, self).__init__()
        self.require_scheme = require_scheme

    def validate(self, value):
        try:
            validate.url(value, require_scheme=self.require_scheme)
        except exceptions.InvalidURL:
            error = 'Value must be a valid URL string'
            raise ValueError(error)
        return value


class URLPathType(wtypes.UserType):
    basetype = unicode
    name = 'url_path'

    @staticmethod
    def validate(value):
        try:
            validate.url_path(value)
        except exceptions.InvalidURLPath:
            error = 'Value must be a valid URL Path string'
            raise ValueError(error)
        return value


class BaseMeta(wtypes.BaseMeta):
    def __new__(mcs, name, bases, dct):
        def get_tenant_id(self):
            tenant_id = getattr(self, '_tenant_id', wtypes.Unset)
            # If tenant_id was explicitly set to Unset, return that
            if tenant_id is wtypes.Unset and self._unset_tenant:
                return tenant_id
            # Otherwise, assume we can return project_id
            return self.project_id

        def set_tenant_id(self, tenant_id):
            self._tenant_id = tenant_id

            if tenant_id is wtypes.Unset:
                # Record that tenant_id was explicitly Unset
                self._unset_tenant = True
            else:
                # Reset 'unset' state, and update project_id as well
                self._unset_tenant = False
                self.project_id = tenant_id

        if 'project_id' in dct and 'tenant_id' not in dct:
            dct['tenant_id'] = wtypes.wsproperty(
                wtypes.StringType(max_length=36),
                get_tenant_id, set_tenant_id)
            # This will let us know if tenant_id was explicitly set to Unset
            dct['_unset_tenant'] = False
        return super(BaseMeta, mcs).__new__(mcs, name, bases, dct)


@six.add_metaclass(BaseMeta)
class BaseType(wtypes.Base):
    @classmethod
    def _full_response(cls):
        return False

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
            elif key in ['name', 'description'] and value is None:
                new_dict[key] = ''
            else:
                if key in dm_to_type_map:
                    new_dict[dm_to_type_map[key]] = value
                    del new_dict[key]
        return cls(**new_dict)

    @classmethod
    def translate_dict_keys_to_data_model(cls, wsme_dict):
        """Translate the keys from wsme class type, to data_model."""
        if not hasattr(cls, '_type_to_model_map'):
            return wsme_dict
        res = {}
        for (k, v) in wsme_dict.items():
            if k in cls._type_to_model_map:
                k = cls._type_to_model_map[k]
                if '.' in k:
                    parent, child = k.split('.')
                    if parent not in res:
                        res[parent] = {}
                    res[parent][child] = v
                    continue
            res[k] = v
        return res

    def to_dict(self, render_unsets=False):
        """Converts Octavia WSME type to dictionary.

        :param render_unsets: If True, will convert items that are WSME Unset
                              types to None. If False, does not add the item
        """
        # Set project_id equal tenant_id if project_id is unset and tenant_id
        # is
        if hasattr(self, 'project_id') and hasattr(self, 'tenant_id'):
            # pylint: disable=access-member-before-definition
            if (isinstance(self.project_id, wtypes.UnsetType) and
                    not isinstance(self.tenant_id, wtypes.UnsetType)):
                self.project_id = self.tenant_id
        wsme_dict = {}
        for attr in dir(self):
            if attr.startswith('_'):
                continue
            value = getattr(self, attr, None)
            # TODO(blogan): Investigate wsme types handling the duality of
            # tenant_id and project_id in a clean way.  One way could be
            # wsme.rest.json.fromjson and using the @fromjson.when_object
            # decorator.
            if attr == 'tenant_id':
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
            wsme_dict[attr] = value
        return self.translate_dict_keys_to_data_model(wsme_dict)


class IdOnlyType(BaseType):
    id = wtypes.wsattr(wtypes.UuidType(), mandatory=True)


class NameOnlyType(BaseType):
    name = wtypes.wsattr(wtypes.StringType(max_length=255), mandatory=True)


class PageType(BaseType):
    href = wtypes.StringType()
    rel = wtypes.StringType()
