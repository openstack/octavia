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
        'l7rule_type',
        sa.Column('name', sa.String(36), primary_key=True),
        sa.Column('description', sa.String(255), nullable=True)
    )

    # Create temporary table for table data seeding
    insert_table = sql.table(
        'l7rule_type',
        sql.column('name', sa.String),
        sql.column('description', sa.String)
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
        'l7rule_compare_type',
        sa.Column('name', sa.String(36), primary_key=True),
        sa.Column('description', sa.String(255), nullable=True)
    )

    insert_table = sql.table(
        'l7rule_compare_type',
        sql.column('name', sa.String),
        sql.column('description', sa.String)
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
        'l7policy_action',
        sa.Column('name', sa.String(36), primary_key=True),
        sa.Column('description', sa.String(255), nullable=True)
    )

    insert_table = sql.table(
        'l7policy_action',
        sql.column('name', sa.String),
        sql.column('description', sa.String)
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
        'l7policy',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('listener_id', sa.String(36), nullable=False),
        sa.Column('action', sa.String(36), nullable=False),
        sa.Column('redirect_pool_id', sa.String(36), nullable=True),
        sa.Column('redirect_url', sa.String(255), nullable=True),
        sa.Column('position', sa.Integer, nullable=False),
        sa.Column('enabled', sa.Boolean(), default=True, nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['listener_id'],
                                ['listener.id'],
                                name='fk_l7policy_listener_id'),
        sa.ForeignKeyConstraint(['redirect_pool_id'],
                                ['pool.id'],
                                name='fk_l7policy_pool_id'),
        sa.ForeignKeyConstraint(['action'],
                                ['l7policy_action.name'],
                                name='fk_l7policy_l7policy_action_name')
    )

    # L7 Rules
    op.create_table(
        'l7rule',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('l7policy_id', sa.String(36), nullable=False),
        sa.Column('type', sa.String(36), nullable=False),
        sa.Column('compare_type', sa.String(36), nullable=False),
        sa.Column('key', sa.String(255), nullable=True),
        sa.Column('value', sa.String(255), nullable=False),
        sa.Column('invert', sa.Boolean(), default=False, nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['l7policy_id'],
                                ['l7policy.id'],
                                name='fk_l7rule_l7policy_id'),
        sa.ForeignKeyConstraint(['type'],
                                ['l7rule_type.name'],
                                name='fk_l7rule_l7rule_type_name'),
        sa.ForeignKeyConstraint(['compare_type'],
                                ['l7rule_compare_type.name'],
                                name='fk_l7rule_l7rule_compare_type_name')
    )
