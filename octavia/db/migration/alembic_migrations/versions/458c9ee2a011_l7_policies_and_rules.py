#    Copyright 2015 Blue Box, an IBM Company
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

"""L7 Policies and Rules

Revision ID: 458c9ee2a011
Revises: 29ff921a6eb
Create Date: 2016-01-07 11:45:45.391851

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql

# revision identifiers, used by Alembic.
revision = '458c9ee2a011'
down_revision = '29ff921a6eb'


def upgrade():
    # L7 Rule Types
    op.create_table(
        u'l7rule_type',
        sa.Column(u'name', sa.String(36), primary_key=True),
        sa.Column(u'description', sa.String(255), nullable=True)
    )

    # Create temporary table for table data seeding
    insert_table = sql.table(
        u'l7rule_type',
        sql.column(u'name', sa.String),
        sql.column(u'description', sa.String)
    )

    op.bulk_insert(
        insert_table,
        [
            {'name': 'HOST_NAME'},
            {'name': 'PATH'},
            {'name': 'FILE_TYPE'},
            {'name': 'HEADER'},
            {'name': 'COOKIE'}
        ]
    )

    # L7 Rule Compare Types
    op.create_table(
        u'l7rule_compare_type',
        sa.Column(u'name', sa.String(36), primary_key=True),
        sa.Column(u'description', sa.String(255), nullable=True)
    )

    insert_table = sql.table(
        u'l7rule_compare_type',
        sql.column(u'name', sa.String),
        sql.column(u'description', sa.String)
    )

    op.bulk_insert(
        insert_table,
        [
            {'name': 'REGEX'},
            {'name': 'STARTS_WITH'},
            {'name': 'ENDS_WITH'},
            {'name': 'CONTAINS'},
            {'name': 'EQUAL_TO'}
        ]
    )

    # L7 Policy Actions
    op.create_table(
        u'l7policy_action',
        sa.Column(u'name', sa.String(36), primary_key=True),
        sa.Column(u'description', sa.String(255), nullable=True)
    )

    insert_table = sql.table(
        u'l7policy_action',
        sql.column(u'name', sa.String),
        sql.column(u'description', sa.String)
    )

    op.bulk_insert(
        insert_table,
        [
            {'name': 'REJECT'},
            {'name': 'REDIRECT_TO_URL'},
            {'name': 'REDIRECT_TO_POOL'}
        ]
    )

    # L7 Policies
    op.create_table(
        u'l7policy',
        sa.Column(u'id', sa.String(36), nullable=False),
        sa.Column(u'name', sa.String(255), nullable=True),
        sa.Column(u'description', sa.String(255), nullable=True),
        sa.Column(u'listener_id', sa.String(36), nullable=False),
        sa.Column(u'action', sa.String(36), nullable=False),
        sa.Column(u'redirect_pool_id', sa.String(36), nullable=True),
        sa.Column(u'redirect_url', sa.String(255), nullable=True),
        sa.Column(u'position', sa.Integer, nullable=False),
        sa.Column(u'enabled', sa.Boolean(), default=True, nullable=False),

        sa.PrimaryKeyConstraint(u'id'),
        sa.ForeignKeyConstraint([u'listener_id'],
                                [u'listener.id'],
                                name=u'fk_l7policy_listener_id'),
        sa.ForeignKeyConstraint([u'redirect_pool_id'],
                                [u'pool.id'],
                                name=u'fk_l7policy_pool_id'),
        sa.ForeignKeyConstraint([u'action'],
                                [u'l7policy_action.name'],
                                name=u'fk_l7policy_l7policy_action_name')
    )

    # L7 Rules
    op.create_table(
        u'l7rule',
        sa.Column(u'id', sa.String(36), nullable=False),
        sa.Column(u'l7policy_id', sa.String(36), nullable=False),
        sa.Column(u'type', sa.String(36), nullable=False),
        sa.Column(u'compare_type', sa.String(36), nullable=False),
        sa.Column(u'key', sa.String(255), nullable=True),
        sa.Column(u'value', sa.String(255), nullable=False),
        sa.Column(u'invert', sa.Boolean(), default=False, nullable=False),
        sa.PrimaryKeyConstraint(u'id'),
        sa.ForeignKeyConstraint([u'l7policy_id'],
                                [u'l7policy.id'],
                                name=u'fk_l7rule_l7policy_id'),
        sa.ForeignKeyConstraint([u'type'],
                                [u'l7rule_type.name'],
                                name=u'fk_l7rule_l7rule_type_name'),
        sa.ForeignKeyConstraint([u'compare_type'],
                                [u'l7rule_compare_type.name'],
                                name=u'fk_l7rule_l7rule_compare_type_name')
    )
