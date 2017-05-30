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
from oslo_utils import strutils
from oslo_utils import uuidutils
import sqlalchemy as sa
from sqlalchemy.ext import declarative
from sqlalchemy.orm import collections


class OctaviaBase(models.ModelBase):

    __data_model__ = None

    @staticmethod
    def _get_unique_key(obj):
        """Returns a unique key for passed object for data model building."""
        # First handle all objects with their own ID, then handle subordinate
        # objects.
        if obj.__class__.__name__ in ['Member', 'Pool', 'LoadBalancer',
                                      'Listener', 'Amphora', 'L7Policy',
                                      'L7Rule']:
            return obj.__class__.__name__ + obj.id
        elif obj.__class__.__name__ in ['SessionPersistence', 'HealthMonitor']:
            return obj.__class__.__name__ + obj.pool_id
        elif obj.__class__.__name__ in ['ListenerStatistics']:
            return obj.__class__.__name__ + obj.listener_id + obj.amphora_id
        elif obj.__class__.__name__ in ['VRRPGroup', 'Vip']:
            return obj.__class__.__name__ + obj.load_balancer_id
        elif obj.__class__.__name__ in ['AmphoraHealth']:
            return obj.__class__.__name__ + obj.amphora_id
        elif obj.__class__.__name__ in ['SNI']:
            return (obj.__class__.__name__ +
                    obj.listener_id + obj.tls_container_id)
        elif obj.__class__.__name__ in ['Quotas']:
            return obj.__class__.__name__ + obj.project_id
        else:
            raise NotImplementedError

    def to_data_model(self, _graph_nodes=None):
        """Converts to a data model graph.

        In order to make the resulting data model graph usable no matter how
        many internal references are followed, we generate a complete graph of
        OctaviaBase nodes connected to the object passed to this method.

        :param _graph_nodes: Used only for internal recursion of this
                             method. Should not be called from the outside.
                             Contains a dictionary of all OctaviaBase type
                             objects in the generated graph
        """
        _graph_nodes = _graph_nodes or {}
        if not self.__data_model__:
            raise NotImplementedError
        dm_kwargs = {}
        for column in self.__table__.columns:
            dm_kwargs[column.name] = getattr(self, column.name)

        attr_names = [attr_name for attr_name in dir(self)
                      if not attr_name.startswith('_')]
        # Appending early, as any unique ID should be defined already and
        # the rest of this object will get filled out more fully later on,
        # and we need to add ourselves to the _graph_nodes before we
        # attempt recursion.
        dm_self = self.__data_model__(**dm_kwargs)
        dm_key = self._get_unique_key(dm_self)
        _graph_nodes.update({dm_key: dm_self})
        for attr_name in attr_names:
            attr = getattr(self, attr_name)
            if isinstance(attr, OctaviaBase) and attr.__class__:
                # If this attr is already in the graph node list, just
                # reference it there and don't recurse.
                ukey = self._get_unique_key(attr)
                if ukey in _graph_nodes.keys():
                    setattr(dm_self, attr_name, _graph_nodes[ukey])
                else:
                    setattr(dm_self, attr_name, attr.to_data_model(
                        _graph_nodes=_graph_nodes))
            elif isinstance(attr, (collections.InstrumentedList, list)):
                setattr(dm_self, attr_name, [])
                listref = getattr(dm_self, attr_name)
                for item in attr:
                    if isinstance(item, OctaviaBase) and item.__class__:
                        ukey = self._get_unique_key(item)
                        if ukey in _graph_nodes.keys():
                            listref.append(_graph_nodes[ukey])
                        else:
                            listref.append(
                                item.to_data_model(_graph_nodes=_graph_nodes))
                    elif not isinstance(item, OctaviaBase):
                        listref.append(item)
        return dm_self

    @staticmethod
    def apply_filter(query, model, filters):
        translated_filters = {}
        child_map = {}
        # Convert admin_state_up to proper type
        if 'admin_state_up' in filters:
            filters['admin_state_up'] = strutils.bool_from_string(
                filters['admin_state_up'])
        for attr, name_map in model.__v2_wsme__._child_map.items():
            for k, v in name_map.items():
                if v in filters:
                    child_map[attr] = {k: filters.pop(v)}
        for k, v in model.__v2_wsme__._type_to_model_map.items():
            if k in filters:
                translated_filters[v] = filters.pop(k)
        translated_filters.update(filters)
        if translated_filters:
            query = query.filter_by(**translated_filters)
        for k, v in child_map.items():
            query = query.join(getattr(model, k)).filter_by(**v)
        return query


class LookupTableMixin(object):
    """Mixin to add to classes that are lookup tables."""
    name = sa.Column(sa.String(255), primary_key=True, nullable=False)
    description = sa.Column(sa.String(255), nullable=True)


class IdMixin(object):
    """Id mixin, add to subclasses that have an id."""
    id = sa.Column(sa.String(36), primary_key=True,
                   default=uuidutils.generate_uuid)


class ProjectMixin(object):
    """Tenant mixin, add to subclasses that have a project."""
    project_id = sa.Column(sa.String(36))


class NameMixin(object):
    """Name mixin to add to classes which need a name."""
    name = sa.Column(sa.String(255), nullable=True)


BASE = declarative.declarative_base(cls=OctaviaBase)
