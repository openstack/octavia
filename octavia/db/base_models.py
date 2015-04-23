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

from oslo_db.sqlalchemy import models
from oslo_utils import uuidutils
import sqlalchemy as sa
from sqlalchemy.ext import declarative
from sqlalchemy.orm import collections


class OctaviaBase(models.ModelBase):

    __data_model__ = None

    def to_data_model(self, _calling_cls=None):
        """Converts to a data model.

        :param _calling_cls: Used only for internal recursion of this method.
                             Should not be called from the outside.
        """
        if not self.__data_model__:
            raise NotImplementedError
        dm_kwargs = {}
        for column in self.__table__.columns:
            dm_kwargs[column.name] = getattr(self, column.name)
        attr_names = [attr_name for attr_name in dir(self)
                      if not attr_name.startswith('_')]
        for attr_name in attr_names:
            attr = getattr(self, attr_name)
            if isinstance(attr, OctaviaBase
                          ) and attr.__class__ != _calling_cls:
                dm_kwargs[attr_name] = attr.to_data_model(
                    _calling_cls=self.__class__)
            elif isinstance(attr, collections.InstrumentedList):
                dm_kwargs[attr_name] = []
                for item in attr:
                    if isinstance(item, OctaviaBase
                                  ) and attr.__class__ != _calling_cls:
                        dm_kwargs[attr_name].append(
                            item.to_data_model(
                                _calling_cls=self.__class__))
                    elif not isinstance(item, OctaviaBase):
                        dm_kwargs[attr_name].append(item)
        return self.__data_model__(**dm_kwargs)


class LookupTableMixin(object):
    """Mixin to add to classes that are lookup tables."""
    name = sa.Column(sa.String(255), primary_key=True, nullable=False)
    description = sa.Column(sa.String(255), nullable=True)


class IdMixin(object):
    """Id mixin, add to subclasses that have a tenant."""
    id = sa.Column(sa.String(36), primary_key=True,
                   default=uuidutils.generate_uuid)


class TenantMixin(object):
    """Tenant mixin, add to subclasses that have a tenant."""
    tenant_id = sa.Column(sa.String(36))


BASE = declarative.declarative_base(cls=OctaviaBase)
