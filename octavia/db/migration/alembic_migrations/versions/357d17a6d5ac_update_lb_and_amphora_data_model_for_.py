# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

"""update lb and amphora data model for active passive

Revision ID: 357d17a6d5ac
Revises: 298eac0640a7
Create Date: 2015-07-16 17:41:49.029145

"""

# revision identifiers, used by Alembic.
revision = '357d17a6d5ac'
down_revision = '298eac0640a7'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql


def upgrade():
    op.create_table(
        u'lb_topology',
        sa.Column(u'name', sa.String(36), primary_key=True),
        sa.Column(u'description', sa.String(255), nullable=True)
    )

    insert_table = sql.table(
        u'lb_topology',
        sql.column(u'name', sa.String),
        sql.column(u'description', sa.String)
    )

    op.bulk_insert(
        insert_table,
        [
            {'name': 'SINGLE'},
            {'name': 'ACTIVE_STANDBY'}
        ]
    )

    op.create_table(
        u'amphora_roles',
        sa.Column(u'name', sa.String(36), primary_key=True),
        sa.Column(u'description', sa.String(255), nullable=True)
    )

    insert_table = sql.table(
        u'amphora_roles',
        sql.column(u'name', sa.String),
        sql.column(u'description', sa.String)
    )

    op.bulk_insert(
        insert_table,
        [
            {'name': 'MASTER'},
            {'name': 'BACKUP'},
            {'name': 'STANDALONE'}
        ]
    )

    op.add_column(
        u'load_balancer',
        sa.Column(u'topology', sa.String(36),
                  sa.ForeignKey(u'lb_topology.name',
                                name=u'fk_lb_topology_name'),
                  nullable=True)
    )

    op.add_column(
        u'amphora',
        sa.Column(u'role', sa.String(36),
                  sa.ForeignKey(u'amphora_roles.name',
                                name=u'fk_amphora_roles_name'),
                  nullable=True)
    )
