# Copyright 2015 Hewlett Packard Enterprise Development Company LP
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
"""Keepalived configuration datamodel

Revision ID: 1e4c1d83044c
Revises: 5a3ee5472c31
Create Date: 2015-08-06 10:39:54.998797

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql

# revision identifiers, used by Alembic.
revision = '1e4c1d83044c'
down_revision = '5a3ee5472c31'


def upgrade():
    op.create_table(
        'vrrp_auth_method',
        sa.Column('name', sa.String(36), primary_key=True),
        sa.Column('description', sa.String(255), nullable=True)
    )

    insert_table = sql.table(
        'vrrp_auth_method',
        sql.column('name', sa.String),
        sql.column('description', sa.String)
    )

    op.bulk_insert(
        insert_table,
        [
            {'name': 'PASS'},
            {'name': 'AH'}
        ]
    )

    op.create_table(
        'vrrp_group',
        sa.Column('load_balancer_id', sa.String(36), nullable=False),
        sa.Column('vrrp_group_name', sa.String(36), nullable=True),
        sa.Column('vrrp_auth_type', sa.String(16), nullable=True),
        sa.Column('vrrp_auth_pass', sa.String(36), nullable=True),
        sa.Column('advert_int', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('load_balancer_id'),
        sa.ForeignKeyConstraint(['load_balancer_id'], ['load_balancer.id'],
                                name='fk_vrrp_group_load_balancer_id'),
        sa.ForeignKeyConstraint(['vrrp_auth_type'],
                                ['vrrp_auth_method.name'],
                                name='fk_load_balancer_vrrp_auth_method_name')
    )

    op.add_column(
        'listener',
        sa.Column('peer_port', sa.Integer(), nullable=True)
    )

    op.add_column(
        'amphora',
        sa.Column('vrrp_interface', sa.String(16), nullable=True)
    )

    op.add_column(
        'amphora',
        sa.Column('vrrp_id', sa.Integer(), nullable=True)
    )

    op.add_column(
        'amphora',
        sa.Column('vrrp_priority', sa.Integer(), nullable=True)
    )
