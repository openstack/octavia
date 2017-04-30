# Copyright 2017 EayunStack, Inc.
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
"""add proxy protocol for pool

Revision ID: 5309960964f8
Revises: 52377704420e
Create Date: 2017-04-27 01:13:38.064697

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql


# revision identifiers, used by Alembic.
revision = '5309960964f8'
down_revision = '52377704420e'

new_protocol = 'PROXY'


def upgrade():
    insert_table = sql.table(
        u'protocol',
        sql.column(u'name', sa.String),
        sql.column(u'description', sa.String)
    )

    op.bulk_insert(
        insert_table,
        [
            {'name': new_protocol}
        ]
    )
