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

"""Tenant id to project id

Revision ID: 6abb04f24c5
Revises: 5a3ee5472c31
Create Date: 2015-12-03 15:22:25.390595

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6abb04f24c5'
down_revision = '1e4c1d83044c'


def upgrade():
    op.alter_column('load_balancer', 'tenant_id', new_column_name='project_id',
                    existing_type=sa.String(36))
    op.alter_column('listener', 'tenant_id', new_column_name='project_id',
                    existing_type=sa.String(36))
    op.alter_column('pool', 'tenant_id', new_column_name='project_id',
                    existing_type=sa.String(36))
    op.alter_column('member', 'tenant_id', new_column_name='project_id',
                    existing_type=sa.String(36))
    op.add_column('health_monitor', sa.Column('project_id', sa.String(36)))
