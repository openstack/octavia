#    Copyright 2020 Dawson Coleman
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

"""add listener ciphers column

Revision ID: 7c36b277bfb0
Revises: 8ac4ed24df3a
Create Date: 2020-03-11 02:23:49.097485

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7c36b277bfb0'
down_revision = '8ac4ed24df3a'


def upgrade():
    op.add_column(
        'listener',
        sa.Column('tls_ciphers', sa.String(2048), nullable=True)
    )
