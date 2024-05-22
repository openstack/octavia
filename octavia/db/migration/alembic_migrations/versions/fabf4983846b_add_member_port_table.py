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

"""add_member_port_table

Revision ID: fabf4983846b
Revises: 8db7a6443785
Create Date: 2024-08-30 23:12:01.713217

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fabf4983846b'
down_revision = '8db7a6443785'


def upgrade():
    op.create_table(
        'amphora_member_port',
        sa.Column('port_id', sa.String(36), primary_key=True),
        sa.Column('amphora_id', sa.String(36), nullable=False, index=True),
        sa.Column('network_id', sa.String(36)),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime())
    )
    op.create_foreign_key(
        'fk_member_port_amphora_id', 'amphora_member_port',
        'amphora', ['amphora_id'], ['id']
    )
