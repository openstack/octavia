# Copyright 2018 Huawei
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
#

"""Extend some necessary fields for udp support

Revision ID: 76aacf2e176c
Revises: ebbcc72b4e5e
Create Date: 2018-01-01 20:47:52.405865

"""


from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql

# revision identifiers, used by Alembic.
revision = '76aacf2e176c'
down_revision = 'ebbcc72b4e5e'

tables = [u'protocol', u'health_monitor_type']
new_fields = ['UDP', 'UDP-CONNECT']


def upgrade():
    # New UDP protocol addition.
    # New UDP_CONNNECT healthmonitor type addition.
    for table, new_field in zip(tables, new_fields):
        insert_table = sql.table(
            table,
            sql.column(u'name', sa.String),
            sql.column(u'description', sa.String)
        )

        op.bulk_insert(
            insert_table,
            [
                {'name': new_field}
            ]
        )

    # Two new columns add to session_persistence table
    op.add_column('session_persistence',
                  sa.Column('persistence_timeout',
                            sa.Integer(),
                            nullable=True, server_default=None))
    op.add_column('session_persistence',
                  sa.Column('persistence_granularity',
                            sa.String(length=64),
                            nullable=True, server_default=None))
