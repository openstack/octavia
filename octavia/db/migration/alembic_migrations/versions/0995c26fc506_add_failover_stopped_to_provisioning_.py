# Copyright Red Hat
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
"""Add FAILOVER_STOPPED to provisioning_status table

Revision ID: 0995c26fc506
Revises: 31f7653ded67
Create Date: 2022-03-24 04:53:10.768658

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0995c26fc506'
down_revision = '31f7653ded67'


def upgrade():
    insert_table = sa.sql.table(
        'provisioning_status',
        sa.sql.column('name', sa.String),
        sa.sql.column('description', sa.String)
    )

    op.bulk_insert(
        insert_table,
        [
            {'name': 'FAILOVER_STOPPED'},
        ]
    )
