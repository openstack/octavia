#    Copyright 2016 Rackspace
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

"""adding name column to member and health monitor

Revision ID: 44a2414dd683
Revises: c11292016060
Create Date: 2016-12-19 13:14:58.879793

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '44a2414dd683'
down_revision = 'c11292016060'


tables = ['member', 'health_monitor']


def upgrade():
    for table in tables:
        op.add_column(
            table,
            sa.Column(u'name', sa.String(255), nullable=True)
        )
