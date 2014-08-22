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

'''update url and name size

Revision ID: 13500e2e978d
Revises: 4c094013699a
Create Date: 2014-09-18 16:07:04.859812

'''

# revision identifiers, used by Alembic.
revision = '13500e2e978d'
down_revision = '4c094013699a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column(u'provisioning_status', u'name',
                    existing_type=sa.String(255))
    op.alter_column(u'operating_status', u'name',
                    existing_type=sa.String(255))
    op.alter_column(u'health_monitor_type', u'name',
                    existing_type=sa.String(255))
    op.alter_column(u'protocol', u'name',
                    existing_type=sa.String(255))
    op.alter_column(u'algorithm', u'name',
                    existing_type=sa.String(255))
    op.alter_column(u'session_persistence_type', u'name',
                    existing_type=sa.String(255))


def downgrade():
    op.alter_column(u'provisioning_status', u'name',
                    existing_type=sa.String(30))
    op.alter_column(u'operating_status', u'name',
                    existing_type=sa.String(30))
    op.alter_column(u'health_monitor_type', u'name',
                    existing_type=sa.String(30))
    op.alter_column(u'protocol', u'name',
                    existing_type=sa.String(30))
    op.alter_column(u'algorithm', u'name',
                    existing_type=sa.String(30))
    op.alter_column(u'session_persistence_type', u'name',
                    existing_type=sa.String(30))
