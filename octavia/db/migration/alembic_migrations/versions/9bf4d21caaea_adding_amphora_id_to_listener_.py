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

"""adding Amphora ID to listener_statistics table

Revision ID: 9bf4d21caaea
Revises: 8c0851bdf6c3
Create Date: 2016-05-02 07:50:12.888263

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9bf4d21caaea'
down_revision = '8c0851bdf6c3'


def upgrade():
    op.add_column('listener_statistics',
                  sa.Column('amphora_id',
                            sa.String(36),
                            nullable=False)
                  )

    op.drop_constraint('fk_listener_statistics_listener_id',
                       'listener_statistics',
                       type_='foreignkey')
    op.drop_constraint('PRIMARY',
                       'listener_statistics',
                       type_='primary')

    op.create_primary_key('pk_listener_statistics', 'listener_statistics',
                          ['listener_id', 'amphora_id'])
    op.create_foreign_key('fk_listener_statistics_listener_id',
                          'listener_statistics',
                          'listener',
                          ['listener_id'],
                          ['id'])
    op.create_foreign_key('fk_listener_statistic_amphora_id',
                          'listener_statistics',
                          'amphora',
                          ['amphora_id'],
                          ['id'])
