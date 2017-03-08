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
"""create quotas table

Revision ID: 3f8ff3be828e
Revises: 44a2414dd683
Create Date: 2016-09-01 13:59:20.723621

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3f8ff3be828e'
down_revision = '44a2414dd683'


def upgrade():
    op.create_table(
        u'quotas',
        sa.Column(u'project_id', sa.String(36), primary_key=True,
                  nullable=False),
        sa.Column(u'health_monitor', sa.Integer(), nullable=True),
        sa.Column(u'load_balancer', sa.Integer(), nullable=True),
        sa.Column(u'listener', sa.Integer(), nullable=True),
        sa.Column(u'member', sa.Integer(), nullable=True),
        sa.Column(u'pool', sa.Integer(), nullable=True),
        sa.Column(u'in_use_health_monitor', sa.Integer(), nullable=True),
        sa.Column(u'in_use_load_balancer', sa.Integer(), nullable=True),
        sa.Column(u'in_use_listener', sa.Integer(), nullable=True),
        sa.Column(u'in_use_member', sa.Integer(), nullable=True),
        sa.Column(u'in_use_pool', sa.Integer(), nullable=True),
    )
