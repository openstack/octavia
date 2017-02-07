# Copyright 2017 Intel Corporation
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
#

"""Add ID column to Healthmonitor table

Revision ID: fac584114642
Revises: fc5582da7d8a
Create Date: 2017-02-07 20:47:52.405865

"""


from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fac584114642'
down_revision = 'fc5582da7d8a'


def upgrade():
    op.add_column('health_monitor',
                  sa.Column('id',
                            sa.String(length=36),
                            nullable=True,
                            ))

    op.drop_constraint('fk_health_monitor_pool_id',
                       'health_monitor',
                       type_='foreignkey',)

    op.execute("UPDATE health_monitor SET id = pool_id")

    op.execute("ALTER TABLE health_monitor MODIFY id varchar(36) NOT NULL")

    op.execute("ALTER TABLE health_monitor DROP PRIMARY KEY,"
               "ADD PRIMARY KEY(id);")

    op.create_foreign_key('fk_health_monitor_pool_id', 'health_monitor',
                          'pool', ['pool_id'], ['id'])

    op.create_index('uq_health_monitor_pool',
                    'health_monitor', ['pool_id'],
                    unique=True)
