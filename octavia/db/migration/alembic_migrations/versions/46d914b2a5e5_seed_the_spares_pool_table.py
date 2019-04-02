# Copyright 2019 Michael Johnson
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

"""Seed the spares_pool table

Revision ID: 46d914b2a5e5
Revises: 6ffc710674ef
Create Date: 2019-04-03 14:03:25.596157

"""


import datetime

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '46d914b2a5e5'
down_revision = '6ffc710674ef'


def upgrade():
    # Create temporary table for table data seeding
    insert_table = sa.table(
        u'spares_pool',
        sa.column(u'updated_at', sa.DateTime),
    )

    # Note: The date/time doesn't matter, we just need to seed the table.
    op.bulk_insert(
        insert_table,
        [
            {'updated_at': datetime.datetime.now()}
        ]
    )
