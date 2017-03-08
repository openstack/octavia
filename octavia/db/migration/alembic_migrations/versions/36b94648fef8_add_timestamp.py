#    Copyright 2016 Catalyst IT
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

"""add timestamp

Revision ID: 36b94648fef8
Revises: 4d9cf7d32f2
Create Date: 2016-04-21 10:45:32.278433

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '36b94648fef8'
down_revision = '4d9cf7d32f2'

tables = ['member', 'pool', 'load_balancer', 'listener']


def upgrade():
    for table in tables:
        op.add_column(
            table,
            sa.Column(u'created_at', sa.DateTime(), nullable=True)
        )
        op.add_column(
            table,
            sa.Column(u'updated_at', sa.DateTime(), nullable=True)
        )
