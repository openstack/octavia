# Copyright 2015 Hewlett-Packard Development Company, L.P.
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
"""Adding TERMINATED_HTTPS support and TLS ref ID char length increase

Revision ID: 2351ea316465
Revises: 48660b6643f0
Create Date: 2015-05-22 11:57:04.703910

"""

# revision identifiers, used by Alembic.
revision = '2351ea316465'
down_revision = '357d17a6d5ac'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql


new_protocol = 'TERMINATED_HTTPS'


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
    op.alter_column(u'listener', u'tls_certificate_id',
                    existing_type=sa.String(255), nullable=True)
