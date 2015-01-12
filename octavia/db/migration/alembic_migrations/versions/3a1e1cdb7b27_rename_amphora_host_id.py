#    Copyright 2014 Rackspace
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

"""rename amphora host id

Revision ID: 3a1e1cdb7b27
Revises: 4faaa983e7a9
Create Date: 2015-01-10 02:01:04.997336

"""

# revision identifiers, used by Alembic.
revision = '3a1e1cdb7b27'
down_revision = '4faaa983e7a9'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column(u'amphora', u'host_id', new_column_name='compute_id',
                    existing_type=sa.String(36), nullable=True)


def downgrade():
    op.alter_column(u'amphora', u'compute_id', new_column_name='host_id',
                    existing_type=sa.String(36), nullable=False)
