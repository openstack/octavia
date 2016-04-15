# Copyright 2016 Hewlett Packard Enterprise Development Company LP
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

"""create_amphora_build_rate_limit_tables

Revision ID: fc5582da7d8a
Revises: 443fe6676637
Create Date: 2016-04-07 19:42:28.171902

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql

# revision identifiers, used by Alembic.
revision = 'fc5582da7d8a'
down_revision = '443fe6676637'


def upgrade():
    op.create_table(
        u'amphora_build_slots',
        sa.Column(u'id', sa.Integer(), primary_key=True),
        sa.Column(u'slots_used', sa.Integer(), default=0)
    )

    # Create temporary table for table data seeding
    insert_table = sql.table(
        u'amphora_build_slots',
        sql.column(u'id', sa.Integer),
        sql.column(u'slots_used', sa.Integer)
    )

    op.bulk_insert(
        insert_table,
        [
            {'id': 1, 'slots_used': 0}
        ]
    )

    op.create_table(
        u'amphora_build_request',
        sa.Column(u'amphora_id', sa.String(36), nullable=True,
                  primary_key=True),
        sa.Column(u'priority', sa.Integer()),
        sa.Column(u'created_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column(u'status', sa.String(16), default='WAITING', nullable=False)
    )


def downgrade():
    pass
