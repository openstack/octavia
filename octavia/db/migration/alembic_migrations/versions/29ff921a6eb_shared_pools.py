#    Copyright 2016 Blue Box, an IBM Company
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

"""Shared pools

Revision ID: 29ff921a6eb
Revises: 43287cd10fef
Create Date: 2015-12-09 10:32:12.712932

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '29ff921a6eb'
down_revision = '43287cd10fef'


def upgrade():
    conn = op.get_bind()
    # Minimal examples of the tables we need to manipulate
    listener = sa.sql.table(
        'listener',
        sa.sql.column('load_balancer_id', sa.String),
        sa.sql.column('default_pool_id', sa.String))
    pool = sa.sql.table(
        'pool',
        sa.sql.column('load_balancer_id', sa.String),
        sa.sql.column('id', sa.String))

    # This foreign key does not need to be unique anymore. To remove the
    # uniqueness but keep the foreign key we have to do some juggling.
    op.drop_constraint('fk_listener_pool_id', 'listener',
                       type_='foreignkey')
    op.drop_constraint('uq_listener_default_pool_id', 'listener',
                       type_='unique')
    op.create_foreign_key('fk_listener_pool_id', 'listener',
                          'pool', ['default_pool_id'], ['id'])

    op.add_column(u'pool',
                  sa.Column('load_balancer_id', sa.String(36),
                            sa.ForeignKey('load_balancer.id'), nullable=True))

    # Populate this new column appropriately
    select_obj = sa.select([listener.c.load_balancer_id,
                           listener.c.default_pool_id]).where(
                               listener.c.default_pool_id is not None)
    result = conn.execute(select_obj)
    for row in result:
        stmt = pool.update().values(load_balancer_id=row[0]).where(
            pool.c.id == row[1])
        op.execute(stmt)

# For existing installations, the above ETL should populate the above column
# using the following procedure:
#
# Get the output from this:
#
# SELECT default_pool_id, load_balancer_id l_id FROM listener WHERE
# default_pool_id IS NOT NULL;
#
# Then for every row returned run:
#
# UPDATE pool SET load_balancer_id = l_id WHERE id = default_pool_id;
