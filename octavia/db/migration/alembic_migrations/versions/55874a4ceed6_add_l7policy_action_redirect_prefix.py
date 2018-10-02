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

"""add l7policy action redirect prefix

Revision ID: 55874a4ceed6
Revises: 76aacf2e176c
Create Date: 2018-09-09 20:35:38.780054

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql

# revision identifiers, used by Alembic.
revision = '55874a4ceed6'
down_revision = '76aacf2e176c'


def upgrade():
    # Add collumn redirect_prefix
    op.add_column(
        u'l7policy',
        sa.Column(u'redirect_prefix', sa.String(255), nullable=True)
    )
    insert_table = sql.table(
        u'l7policy_action',
        sql.column(u'name', sa.String),
        sql.column(u'description', sa.String)
    )

    op.bulk_insert(
        insert_table,
        [
            {'name': 'REDIRECT_PREFIX'}
        ]
    )
