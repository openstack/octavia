#    Copyright 2019 Michael Johnson
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

"""Spares pool table

Revision ID: 6ffc710674ef
Revises: 7432f1d4ea83
Create Date: 2019-03-11 10:45:43.296236

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6ffc710674ef'
down_revision = '7432f1d4ea83'


def upgrade():
    op.create_table(
        u'spares_pool',
        sa.Column(u'updated_at', sa.DateTime(), nullable=True,
                  server_default=sa.func.current_timestamp()))
