#    Copyright 2016 Intel Corporation
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
import itertools

from oslo_log import log as logging
from pecan import request
import sqlalchemy
from sqlalchemy.orm import aliased
import sqlalchemy.sql as sa_sql

from octavia.api.common import types
from octavia.common.config import cfg
from octavia.common import constants
from octavia.common import exceptions
from octavia.db import base_models
from octavia.db import models

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class PaginationHelper(object):
    """Class helping to interact with pagination functionality

    Pass this class to `db.repositories` to apply it on query
    """
    _auxiliary_arguments = ('limit', 'marker',
                            'sort', 'sort_key', 'sort_dir',
                            'fields', 'page_reverse',
                            )

    def __init__(self, params, sort_dir=constants.DEFAULT_SORT_DIR):
        """Pagination Helper takes params and a default sort direction

        :param params: Contains the following:
                       limit: maximum number of items to return
                       marker: the last item of the previous page; we return
                               the next results after this value.
                       sort: array of attr by which results should be sorted
        :param sort_dir: default direction to sort (asc, desc)
        """
        self.marker = params.get('marker')
        self.sort_dir = self._validate_sort_dir(sort_dir)
        self.limit = self._parse_limit(params)
        self.sort_keys = self._parse_sort_keys(params)
        self.params = params
        self.filters = None
        self.page_reverse = params.get('page_reverse', 'False')

    @staticmethod
    def _parse_limit(params):
        if CONF.api_settings.pagination_max_limit == 'infinite':
            page_max_limit = None
        else:
            page_max_limit = int(CONF.api_settings.pagination_max_limit)
        limit = params.get('limit', page_max_limit)
        try:
            # Deal with limit being a string or int meaning 'Unlimited'
            if limit == 'infinite' or int(limit) < 1:
                limit = None
            # If we don't have a max, just use whatever limit is specified
            elif page_max_limit is None:
                limit = int(limit)
            # Otherwise, we need to compare against the max
            else:
                limit = min(int(limit), page_max_limit)
        except ValueError:
            raise exceptions.InvalidLimit(key=limit)
        return limit

    def _parse_sort_keys(self, params):
        sort_keys_dirs = []
        sort = params.get('sort')
        sort_keys = params.get('sort_key')
        if sort:
            for sort_dir_key in sort.split(","):
                comps = sort_dir_key.split(":")
                if len(comps) == 1:  # Use default sort order
                    sort_keys_dirs.append((comps[0], self.sort_dir))
                elif len(comps) == 2:
                    sort_keys_dirs.append(
                        (comps[0], self._validate_sort_dir(comps[1])))
                else:
                    raise exceptions.InvalidSortKey(key=comps)
        elif sort_keys:
            sort_keys = sort_keys.split(',')
            sort_dirs = params.get('sort_dir')
            if not sort_dirs:
                sort_dirs = [self.sort_dir] * len(sort_keys)
            else:
                sort_dirs = sort_dirs.split(',')

            if len(sort_dirs) < len(sort_keys):
                sort_dirs += [self.sort_dir] * (len(sort_keys) -
                                                len(sort_dirs))
            for sk, sd in zip(sort_keys, sort_dirs):
                sort_keys_dirs.append((sk, self._validate_sort_dir(sd)))

        return sort_keys_dirs

    def _parse_marker(self, session, model):
        return session.query(model).filter_by(id=self.marker).one_or_none()

    @staticmethod
    def _get_default_column_value(column_type):
        """Return the default value of the columns from DB table

        In postgreDB case, if no right default values are being set, an
        psycopg2.DataError will be thrown.
        """
        type_schema = {
            'datetime': None,
            'big_integer': 0,
            'integer': 0,
            'string': ''
        }

        if isinstance(column_type, sa_sql.type_api.Variant):
            return PaginationHelper._get_default_column_value(column_type.impl)

        return type_schema[column_type.__visit_name__]

    @staticmethod
    def _validate_sort_dir(sort_dir):
        sort_dir = sort_dir.lower()
        if sort_dir not in constants.ALLOWED_SORT_DIR:
            raise exceptions.InvalidSortDirection(key=sort_dir)
        return sort_dir

    def _make_links(self, model_list):
        if CONF.api_settings.api_base_uri:
            path_url = "{api_base_url}{path}".format(
                api_base_url=CONF.api_settings.api_base_uri.rstrip('/'),
                path=request.path)
        else:
            path_url = request.path_url
        links = []
        if model_list:
            prev_attr = ["limit={}".format(self.limit)]
            if self.params.get('sort'):
                prev_attr.append("sort={}".format(self.params.get('sort')))
            if self.params.get('sort_key'):
                prev_attr.append("sort_key={}".format(
                    self.params.get('sort_key')))
            next_attr = copy.copy(prev_attr)
            if self.marker:
                prev_attr.append("marker={}".format(model_list[0].get('id')))
                prev_attr.append("page_reverse=True")
                prev_link = {
                    "rel": "previous",
                    "href": "{url}?{params}".format(
                        url=path_url,
                        params="&".join(prev_attr))
                }
                links.append(prev_link)
            # TODO(rm_work) Do we need to know when there are more vs exact?
            # We safely know if we have a full page, but it might include the
            # last element or it might not, it is unclear
            if len(model_list) >= self.limit:
                next_attr.append("marker={}".format(model_list[-1].get('id')))
                next_link = {
                    "rel": "next",
                    "href": "{url}?{params}".format(
                        url=path_url,
                        params="&".join(next_attr))
                }
                links.append(next_link)
        links = [types.PageType(**link) for link in links]
        return links

    def _apply_tags_filtering(self, params, model, query):
        if not getattr(model, "_tags", None):
            return query

        if 'tags' in params:
            tags = params.pop('tags')

            for tag in tags:
                # This requires a multi-join to the tags table,
                # so me must use aliases for each one.
                tag_alias = aliased(base_models.Tags)
                query = query.join(tag_alias, model._tags)
                query = query.filter(tag_alias.tag == tag)

        if 'tags-any' in params:
            tags = params.pop('tags-any')
            tag_alias = aliased(base_models.Tags)
            query = query.join(tag_alias, model._tags)
            query = query.filter(tag_alias.tag.in_(tags))

        if 'not-tags' in params:
            tags = params.pop('not-tags')
            subq = query.session.query(model.id)
            for tag in tags:
                tag_alias = aliased(base_models.Tags)
                subq = subq.join(tag_alias, model._tags)
                subq = subq.filter(tag_alias.tag == tag)

            query = query.filter(~model.id.in_(subq))

        if 'not-tags-any' in params:
            tags = params.pop('not-tags-any')
            query = query.filter(
                ~model._tags.any(base_models.Tags.tag.in_(tags)))

        return query

    @staticmethod
    def _prepare_tags_list(param):
        """Split comma seperated tags and return a flat list of tags."""
        if not isinstance(param, list):
            param = [param]
        return list(itertools.chain.from_iterable(
            tag.split(',') for tag in param))

    def apply(self, query, model, enforce_valid_params=True):
        """Returns a query with sorting / pagination criteria added.

        Pagination works by requiring a unique sort_key specified by sort_keys.
        (If sort_keys is not unique, then we risk looping through values.)
        We use the last row in the previous page as the pagination 'marker'.
        So we must return values that follow the passed marker in the order.
        With a single-valued sort_key, this would be easy: sort_key > X.
        With a compound-values sort_key, (k1, k2, k3) we must do this to repeat
        the lexicographical ordering:
        (k1 > X1) or (k1 == X1 && k2 > X2) or (k1 == X1 && k2 == X2 && k3 > X3)
        We also have to cope with different sort_directions.
        Typically, the id of the last row is used as the client-facing
        pagination marker, then the actual marker object must be fetched from
        the db and passed in to us as marker.
        :param query: the query object to which we should add
        paging/sorting/filtering
        :param model: the ORM model class
        :param enforce_valid_params: check for invalid enteries in self.params

        :rtype: sqlalchemy.orm.query.Query
        :returns: The query with sorting/pagination/filtering added.
        """

        # Add filtering
        if CONF.api_settings.allow_filtering:
            # Exclude (valid) arguments that are not used for data filtering
            filter_params = {k: v for k, v in self.params.items()
                             if k not in self._auxiliary_arguments}

            secondary_query_filter = filter_params.pop(
                "project_id", None) if (model == models.Amphora) else None

            # Tranlate arguments from API standard to data model's field name
            filter_params = (
                model.__v2_wsme__.translate_dict_keys_to_data_model(
                    filter_params)
            )
            if 'loadbalancer_id' in filter_params:
                filter_params['load_balancer_id'] = filter_params.pop(
                    'loadbalancer_id')

            # Pop the 'tags' related parameters off before handling the
            # other filters. Then apply the 'tags' filters after the
            # other filters have been applied.
            tag_params = {}
            if 'tags' in filter_params:
                tag_params['tags'] = self._prepare_tags_list(
                    filter_params.pop('tags'))
            if 'tags-any' in filter_params:
                tag_params['tags-any'] = self._prepare_tags_list(
                    filter_params.pop('tags-any'))
            if 'not-tags' in filter_params:
                tag_params['not-tags'] = self._prepare_tags_list(
                    filter_params.pop('not-tags'))
            if 'not-tags-any' in filter_params:
                tag_params['not-tags-any'] = self._prepare_tags_list(
                    filter_params.pop('not-tags-any'))

            # Drop invalid arguments
            self.filters = {k: v for (k, v) in filter_params.items()
                            if k in vars(model.__data_model__())}

            if enforce_valid_params and (
                len(self.filters) < len(filter_params)
            ):
                raise exceptions.InvalidFilterArgument()

            query = model.apply_filter(query, model, self.filters)
            if secondary_query_filter is not None:
                query = query.filter(model.load_balancer.has(
                    project_id=secondary_query_filter))

            # Apply tags filtering for the models which support tags.
            query = self._apply_tags_filtering(tag_params, model, query)

        # Add sorting
        if CONF.api_settings.allow_sorting:
            # Add default sort keys (if they are OK for the model)
            keys_only = [k[0] for k in self.sort_keys]
            for key in constants.DEFAULT_SORT_KEYS:
                if key not in keys_only and hasattr(model, key):
                    self.sort_keys.append((key, self.sort_dir))

            for current_sort_key, current_sort_dir in self.sort_keys:
                sort_dir_func = {
                    constants.ASC: sqlalchemy.asc,
                    constants.DESC: sqlalchemy.desc,
                }[current_sort_dir]

                try:
                    sort_key_attr = getattr(model, current_sort_key)
                except AttributeError:
                    raise exceptions.InvalidSortKey(key=current_sort_key)
                query = query.order_by(sort_dir_func(sort_key_attr))

        # Add pagination
        if CONF.api_settings.allow_pagination:
            default = ''  # Default to an empty string if NULL
            if self.marker is not None:
                marker_object = self._parse_marker(query.session, model)
                if not marker_object:
                    raise exceptions.InvalidMarker(key=self.marker)
                marker_values = []
                for sort_key, _ in self.sort_keys:
                    v = getattr(marker_object, sort_key)
                    if v is None:
                        v = default
                    marker_values.append(v)

                # Build up an array of sort criteria as in the docstring
                criteria_list = []
                for i in range(len(self.sort_keys)):
                    crit_attrs = []
                    for j in range(i):
                        model_attr = getattr(model, self.sort_keys[j][0])
                        default = PaginationHelper._get_default_column_value(
                            model_attr.property.columns[0].type)
                        attr = sa_sql.expression.case(
                            [(model_attr != None,  # noqa: E711 # pylint: disable=singleton-comparison
                              model_attr), ], else_=default)
                        crit_attrs.append((attr == marker_values[j]))

                    model_attr = getattr(model, self.sort_keys[i][0])
                    default = PaginationHelper._get_default_column_value(
                        model_attr.property.columns[0].type)
                    attr = sa_sql.expression.case(
                        [(model_attr != None,  # noqa: E711 # pylint: disable=singleton-comparison
                          model_attr), ], else_=default)
                    this_sort_dir = self.sort_keys[i][1]
                    if this_sort_dir == constants.DESC:
                        if self.page_reverse == "True":
                            crit_attrs.append((attr > marker_values[i]))
                        else:
                            crit_attrs.append((attr < marker_values[i]))
                    elif this_sort_dir == constants.ASC:
                        if self.page_reverse == "True":
                            crit_attrs.append((attr < marker_values[i]))
                        else:
                            crit_attrs.append((attr > marker_values[i]))
                    else:
                        raise exceptions.InvalidSortDirection(
                            key=this_sort_dir)

                    criteria = sa_sql.and_(*crit_attrs)
                    criteria_list.append(criteria)

                f = sa_sql.or_(*criteria_list)
                query = query.filter(f)

            if self.limit is not None:
                query = query.limit(self.limit)

        model_list = query.all()

        links = None
        if CONF.api_settings.allow_pagination:
            links = self._make_links(model_list)

        return model_list, links
