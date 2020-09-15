# Copyright 2020 Red Hat, Inc. All rights reserved.
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

"""add pool alpn protocols column

Revision ID: be9fdc039b51
Revises: 8b47b2546312
Create Date: 2020-09-15 09:30:00.521760

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'be9fdc039b51'
down_revision = '8b47b2546312'


def upgrade():
    op.add_column(
        'pool',
        sa.Column('alpn_protocols', sa.String(512), nullable=True)
    )
