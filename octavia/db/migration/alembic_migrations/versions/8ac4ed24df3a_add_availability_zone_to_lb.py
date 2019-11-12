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

"""add availability_zone to lb

Revision ID: 8ac4ed24df3a
Revises: c761c8a71579
Create Date: 2019-11-13 08:37:39.392163

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8ac4ed24df3a'
down_revision = 'c761c8a71579'


def upgrade():
    op.add_column(u'load_balancer',
                  sa.Column(u'availability_zone',
                            sa.String(255),
                            nullable=True)
                  )

    op.create_foreign_key(
        u'fk_load_balancer_availability_zone_name', u'load_balancer',
        u'availability_zone', [u'availability_zone'], [u'name']
    )
