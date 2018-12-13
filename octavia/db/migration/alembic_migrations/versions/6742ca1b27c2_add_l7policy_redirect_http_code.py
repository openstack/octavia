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

"""Add L7policy Redirect http code

Revision ID: 6742ca1b27c2
Revises: a7f187cd221f
Create Date: 2018-12-13 09:35:38.780054

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6742ca1b27c2'
down_revision = 'a7f187cd221f'


def upgrade():
    # Add collumn redirect_prefix
    op.add_column(
        u'l7policy',
        sa.Column(u'redirect_http_code', sa.Integer(), nullable=True)
    )
