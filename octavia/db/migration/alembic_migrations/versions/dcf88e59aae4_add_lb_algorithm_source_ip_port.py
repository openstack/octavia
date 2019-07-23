#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

"""Add LB_ALGORITHM_SOURCE_IP_PORT

Revision ID: dcf88e59aae4
Revises: da371b422669
Create Date: 2019-07-23 12:50:49.722003

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'dcf88e59aae4'
down_revision = 'da371b422669'


def migrate_pools():
    conn = op.get_bind()
    lb_table = sa.sql.table(
        'load_balancer',
        sa.sql.column('id', sa.String),
        sa.sql.column('provider', sa.String),
        sa.sql.column('provisioning_status', sa.String))
    pool_table = sa.sql.table(
        'pool',
        sa.sql.column('id', sa.String),
        sa.sql.column('load_balancer_id', sa.String),
        sa.sql.column('lb_algorithm', sa.String))

    j = pool_table.join(lb_table,
                        pool_table.c.load_balancer_id == lb_table.c.id)
    stmt = sa.select([pool_table.c.id]).select_from(j).where(
        lb_table.c.provider == 'ovn')
    result = conn.execute(stmt)

    for row in result:
        stmt = pool_table.update().values(lb_algorithm='SOURCE_IP_PORT').where(
            pool_table.c.id == row[0])
        op.execute(stmt)


def upgrade():
    insert_table = sa.table(
        u'algorithm',
        sa.column(u'name', sa.String(255)),
    )
    op.bulk_insert(
        insert_table,
        [
            {'name': 'SOURCE_IP_PORT'}
        ]
    )
    migrate_pools()
