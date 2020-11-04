# Copyright 2020 Yovole
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

"""update default value in l7rule table

Revision ID: b8bd389cbae7
Revises: 8b47b2546312
Create Date: 2020-12-03 13:40:00.520336

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b8bd389cbae7'
down_revision = 'be9fdc039b51'


def upgrade():
    op.alter_column(
        'l7rule',
        'enabled',
        existing_nullable=False,
        server_default=sa.sql.expression.true())
