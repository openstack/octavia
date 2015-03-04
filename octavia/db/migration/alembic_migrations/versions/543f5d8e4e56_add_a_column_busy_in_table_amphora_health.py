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
"""Add a column busy in table amphora health

Revision ID: 543f5d8e4e56
Revises: 2351ea316465
Create Date: 2015-07-27 11:32:16.685383

"""

# revision identifiers, used by Alembic.
revision = '543f5d8e4e56'
down_revision = '2351ea316465'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(u'amphora_health',
                  sa.Column(u'busy', sa.Boolean(), nullable=False))
