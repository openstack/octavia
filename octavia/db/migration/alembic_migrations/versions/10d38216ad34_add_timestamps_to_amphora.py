#    Copyright 2018 GoDaddy
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

"""add timestamps to amphora

Revision ID: 10d38216ad34
Revises: 0aee2b450512
Create Date: 2018-02-26 10:04:59.133772

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '10d38216ad34'
down_revision = '0aee2b450512'


def upgrade():
    op.add_column(
        u'amphora',
        sa.Column(u'created_at', sa.DateTime(), nullable=True)
    )
    op.add_column(
        u'amphora',
        sa.Column(u'updated_at', sa.DateTime(), nullable=True)
    )
