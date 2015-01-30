# Copyright 2014 Hewlett-Packard Development Company, L.P.
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

"""add new states for amphora

Revision ID: 48660b6643f0
Revises: 3e5b37a0bdb9
Create Date: 2015-01-20 13:31:30.017959

"""

# revision identifiers, used by Alembic.
revision = '48660b6643f0'
down_revision = '3e5b37a0bdb9'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql


def upgrade():
    insert_table = sql.table(
        u'provisioning_status',
        sql.column(u'name', sa.String),
        sql.column(u'description', sa.String)
    )

    op.bulk_insert(
        insert_table,
        [
            {'name': 'READY'},
            {'name': 'BOOTING'},
            {'name': 'ALLOCATED'}
        ]
    )


def downgrade():
    pass
