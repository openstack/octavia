# Copyright 2021 Red Hat, Inc. All rights reserved.
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
"""Add prometheus listener protocol

Revision ID: 6ac558d7fc21
Revises: b8bd389cbae7
Create Date: 2021-10-01 20:06:46.813842

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql

# revision identifiers, used by Alembic.
revision = '6ac558d7fc21'
down_revision = 'b8bd389cbae7'

new_protocol = 'PROMETHEUS'


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
