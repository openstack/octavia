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

"""update member address column

Revision ID: 4faaa983e7a9
Revises: 13500e2e978d
Create Date: 2014-09-29 11:22:16.565071

"""

# revision identifiers, used by Alembic.
revision = '4faaa983e7a9'
down_revision = '13500e2e978d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column(u'member', u'address', new_column_name=u'ip_address',
                    existing_type=sa.String(64))


def downgrade():
    op.alter_column(u'member', u'ip_address', new_column_name=u'address',
                    existing_type=sa.String(64))
