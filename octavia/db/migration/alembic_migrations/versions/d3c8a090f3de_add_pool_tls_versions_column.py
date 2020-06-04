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

"""add pool tls versions column

Revision ID: d3c8a090f3de
Revises: e5493ae5f9a7
Create Date: 2020-04-21 13:17:10.861932

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd3c8a090f3de'
down_revision = 'e5493ae5f9a7'


def upgrade():
    op.add_column(
        'pool',
        sa.Column('tls_versions', sa.String(512), nullable=True)
    )
