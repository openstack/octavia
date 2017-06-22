#    Copyright 2017 GoDaddy
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

"""add ping and tls-hello monitor types

Revision ID: e6672bda93bf
Revises: 27e54d00c3cd
Create Date: 2017-06-21 16:13:09.615651

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql

# revision identifiers, used by Alembic.
revision = 'e6672bda93bf'
down_revision = '27e54d00c3cd'


def upgrade():
    insert_table = sql.table(
        u'health_monitor_type',
        sql.column(u'name', sa.String),
        sql.column(u'description', sa.String)
    )

    op.bulk_insert(
        insert_table,
        [
            {'name': 'PING'},
            {'name': 'TLS-HELLO'}
        ]
    )
