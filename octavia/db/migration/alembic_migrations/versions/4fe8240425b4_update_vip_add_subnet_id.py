#    Copyright 2015 Rackspace
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
"""update vip add subnet id

Revision ID: 4fe8240425b4
Revises: 48660b6643f0
Create Date: 2015-07-01 14:27:44.187179

"""

# revision identifiers, used by Alembic.
revision = '4fe8240425b4'
down_revision = '48660b6643f0'

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table(u'vip') as batch_op:
        batch_op.alter_column(u'network_id', new_column_name=u'subnet_id',
                              existing_type=sa.String(36))


def downgrade():
    with op.batch_alter_table(u'vip') as batch_op:
        batch_op.alter_column(u'subnet_id', new_column_name=u'network_id',
                              existing_type=sa.String(36))
