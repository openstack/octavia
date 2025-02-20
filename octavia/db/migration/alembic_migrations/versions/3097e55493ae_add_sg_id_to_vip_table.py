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

"""add sg_id to vip table

Revision ID: 3097e55493ae
Revises: db2a73e82626
Create Date: 2024-04-05 10:04:32.015445

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3097e55493ae'
down_revision = 'db2a73e82626'


def upgrade():
    op.create_table(
        "vip_security_group",
        sa.Column("load_balancer_id", sa.String(36), nullable=False),
        sa.Column("sg_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["load_balancer_id"],
                                ["vip.load_balancer_id"],
                                name="fk_vip_sg_vip_lb_id"),
        sa.PrimaryKeyConstraint("load_balancer_id", "sg_id")
    )
