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

"""Make pool.lb_algorithm larger

Revision ID: 43287cd10fef
Revises: 6abb04f24c5
Create Date: 2016-01-14 10:05:27.803518

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '43287cd10fef'
down_revision = '6abb04f24c5'


def upgrade():
    op.drop_constraint(
        u'fk_pool_algorithm_name', u'pool',
        type_=u'foreignkey'
    )
    op.alter_column(u'algorithm', u'name', nullable=False,
                    existing_type=sa.String(255))
    op.alter_column(u'pool', u'lb_algorithm', nullable=False,
                    existing_type=sa.String(255))
    op.create_foreign_key(
        u'fk_pool_algorithm_name', u'pool',
        u'algorithm', [u'lb_algorithm'], [u'name']
    )
