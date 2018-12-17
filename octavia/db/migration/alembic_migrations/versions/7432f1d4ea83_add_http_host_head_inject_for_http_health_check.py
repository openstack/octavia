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
#

"""add l7policy action redirect prefix

Revision ID: 7432f1d4ea83
Revises: 6742ca1b27c2
Create Date: 2018-09-09 20:35:38.780054

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7432f1d4ea83'
down_revision = '6742ca1b27c2'


def upgrade():
    op.add_column(
        u'health_monitor',
        sa.Column(u'http_version', sa.Float(), nullable=True)
    )
    op.add_column(
        u'health_monitor',
        sa.Column(u'domain_name', sa.String(255), nullable=True)
    )
